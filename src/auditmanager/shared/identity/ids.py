"""Opaque, prefixed identifier value types.

Source of truth: ``contracts/domain/v1/identifiers.json`` (read-only for this
session). Every entity declared there gets exactly one type here, carrying exactly
the contract prefix. ``tests/contract/domain_p02/test_identifier_catalog.py``
asserts the two sets are equal in both directions, so a catalog entry that gains a
type here without a contract entry, or the reverse, is a test failure rather than a
review question.

Three properties are enforced by construction rather than by convention:

* **Opacity.** The type exposes the identifier as a string and nothing else. There
  is no ``timestamp`` property, no ``created_at`` derivation and no ordering
  operator, because the contract forbids decoding the ULID body for business
  meaning. ``ulid.py`` ships no decoder either, so there is nothing to call.
* **Type separation.** ``ProjectUid.parse("doc_...")`` raises. A well-formed
  identifier of the wrong entity is rejected at construction, so a mis-wired
  foreign key is a ``ValueError`` at the boundary rather than a row that points at
  the wrong table.
* **Non-identity exclusion.** No type is defined for a filesystem path, an object
  key, an uploaded file name, a display ordinal, a checksum or an idempotency key.
  The contract lists those as non-identities; they are ordinary attributes and are
  never modelled as one of these types.

Identifiers carry no secret. They are safe to log, to place in error-envelope
details and to return to an authorized caller.
"""

from __future__ import annotations

import re
from typing import ClassVar, Final, Self

from auditmanager.shared.identity.errors import (
    IdentifierFormatError,
    IdentifierPrefixError,
)
from auditmanager.shared.identity.ulid import ULID_LENGTH, is_valid_ulid, new_ulid

#: ``format`` and ``id_pattern`` from the contract, restated so the code can be read
#: without the catalog open. The contract test pins both against the catalog.
IDENTIFIER_FORMAT: Final[str] = "<prefix>_<ULID>"
IDENTIFIER_PATTERN: Final[str] = r"^[a-z][a-z0-9]{1,7}_[0-9A-HJKMNP-TV-Z]{26}$"
PREFIX_PATTERN: Final[str] = r"^[a-z][a-z0-9]{1,7}$"

_PREFIX_RE: Final[re.Pattern[str]] = re.compile(PREFIX_PATTERN)

_REGISTRY: Final[dict[str, type["OpaqueId"]]] = {}


def pattern_for(prefix: str) -> str:
    """The contract's ``pattern_template`` instantiated for one prefix.

    This is the single source of the regular expression used by the value types
    *and* by the CHECK constraints in the migration, so the database and the
    application cannot drift apart on what a well-formed identifier is.
    """
    if not _PREFIX_RE.match(prefix):
        raise ValueError(f"prefix {prefix!r} does not match {PREFIX_PATTERN}")
    return rf"^{prefix}_[0-9A-HJKMNP-TV-Z]{{{ULID_LENGTH}}}$"


class OpaqueId:
    """Base class for every entity identity in the domain catalog.

    Instances are immutable and compare by exact string equality. Two instances of
    *different* subclasses never compare equal, even if their prefixes were somehow
    made to coincide: identity is (type, value), never value alone.
    """

    __slots__ = ("_value",)

    #: Contract prefix. Set on every concrete subclass; empty on the base.
    prefix: ClassVar[str] = ""
    #: The entity name this identity belongs to, as spelled in the contract.
    entity: ClassVar[str] = ""

    def __init_subclass__(cls, /, prefix: str = "", entity: str = "", **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if not prefix:
            raise TypeError(f"{cls.__name__} must declare a contract prefix")
        if not entity:
            raise TypeError(f"{cls.__name__} must declare its contract entity name")
        existing = _REGISTRY.get(prefix)
        if existing is not None:
            raise TypeError(
                f"prefix {prefix!r} is already bound to {existing.__name__}; "
                "the contract requires prefixes to be globally unique"
            )
        cls.prefix = prefix
        cls.entity = entity
        cls._pattern = re.compile(pattern_for(prefix))  # type: ignore[attr-defined]
        _REGISTRY[prefix] = cls

    def __init__(self, value: str) -> None:
        cls = type(self)
        if not cls.prefix:
            raise TypeError("OpaqueId is abstract; construct a concrete identity type")
        if not isinstance(value, str):
            raise IdentifierFormatError(
                f"{cls.entity} identity must be a string, got {type(value).__name__}"
            )
        if not cls._pattern.match(value):  # type: ignore[attr-defined]
            head, separator, body = value.partition("_")
            if separator and head != cls.prefix and _PREFIX_RE.match(head) and is_valid_ulid(body):
                raise IdentifierPrefixError(
                    f"expected a {cls.entity} identity with prefix {cls.prefix!r}, "
                    f"got prefix {head!r}"
                )
            raise IdentifierFormatError(
                f"{value!r} does not match the contract pattern for {cls.entity} "
                f"({pattern_for(cls.prefix)})"
            )
        object.__setattr__(self, "_value", value)

    # -- construction ---------------------------------------------------------
    @classmethod
    def new(cls) -> Self:
        """Allocate a fresh identity. Generated once; never reused, never re-issued."""
        return cls(f"{cls.prefix}_{new_ulid()}")

    @classmethod
    def parse(cls, value: str) -> Self:
        """Validate an externally supplied string as this entity's identity."""
        return cls(value)

    @classmethod
    def parse_optional(cls, value: str | None) -> Self | None:
        """``None`` passes through; anything else is validated."""
        return None if value is None else cls(value)

    # -- value semantics ------------------------------------------------------
    @property
    def value(self) -> str:
        """The identifier as stored, transported and logged."""
        return self._value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._value!r})"

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        return self._value == other._value  # type: ignore[attr-defined]

    def __hash__(self) -> int:
        return hash((type(self).__name__, self._value))

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable")


# ---------------------------------------------------------------------------
# The 25 declared entity identities, in catalog order.
# ---------------------------------------------------------------------------


class ObjectUid(OpaqueId, prefix="obj", entity="Object"):
    """Identity of a construction object."""


class DisciplineUid(OpaqueId, prefix="dsc", entity="Discipline"):
    """Identity of a design discipline."""


class ProjectUid(OpaqueId, prefix="prj", entity="Project"):
    """Identity of a project."""


class DocumentUid(OpaqueId, prefix="doc", entity="Document"):
    """Identity of a document, independent of any one of its versions."""


class VersionUid(OpaqueId, prefix="ver", entity="DocumentVersion"):
    """Identity of one immutable published input state."""


class ImportId(OpaqueId, prefix="imp", entity="Import"):
    """Identity of an ingest operation. Not allocated anywhere in PC-01."""


class BlobId(OpaqueId, prefix="blob", entity="Blob"):
    """Identity of durable content bytes. The object key is never the identity."""


class RunId(OpaqueId, prefix="run", entity="AuditRun"):
    """Identity of one audit execution request and its result history."""


class JobId(OpaqueId, prefix="job", entity="Job"):
    """Identity of a durable schedulable work item. Not allocated in PC-01."""


class AttemptId(OpaqueId, prefix="att", entity="Attempt"):
    """Identity of one leased execution. Not allocated in PC-01."""


class LeaseId(OpaqueId, prefix="lse", entity="Lease"):
    """Identity of an execution lease. Not allocated in PC-01."""


class CommandId(OpaqueId, prefix="cmd", entity="CommandRecord"):
    """Identity of the durable record that makes a command safe to repeat."""


class FindingUid(OpaqueId, prefix="fnd", entity="Finding"):
    """Durable semantic issue identity that carries expert history across reruns."""


class FindingObservationId(OpaqueId, prefix="fobs", entity="FindingObservation"):
    """Immutable evidence emitted by exactly one run."""


class DecisionId(OpaqueId, prefix="dec", entity="ExpertDecision"):
    """Identity of one appended expert decision event. Never reused or updated."""


class AnalysisProfileId(OpaqueId, prefix="ap", entity="AnalysisProfile"):
    """Identity of an immutable analysis profile."""


class PromptBundleId(OpaqueId, prefix="pb", entity="PromptBundle"):
    """Identity of an immutable prompt bundle."""


class NormsSnapshotId(OpaqueId, prefix="ns", entity="NormsSnapshot"):
    """Identity of a norms snapshot. Not allocated in PC-01."""


class ModelCallId(OpaqueId, prefix="mc", entity="ModelCallRecord"):
    """Identity of one provider call record."""


class ComparisonId(OpaqueId, prefix="cmp", entity="Comparison"):
    """Identity of a comparison. Not allocated in PC-01."""


class SheetLinkId(OpaqueId, prefix="sln", entity="SheetLink"):
    """Identity of a sheet link. Not allocated in PC-01."""


class ExportId(OpaqueId, prefix="exp", entity="ExportRequest"):
    """Identity of an export request. Not allocated in PC-01: the CSV is computed."""


class WorkerId(OpaqueId, prefix="wrk", entity="Worker"):
    """Identity of a worker. Not allocated in PC-01."""


class AuditEventId(OpaqueId, prefix="evt", entity="AuditEvent"):
    """Identity of one appended audit event."""


class ErasureRequestId(OpaqueId, prefix="era", entity="ErasureRequest"):
    """Identity of an erasure request. Not allocated in PC-01."""


#: Every concrete identity type, keyed by contract entity name.
IDENTITY_TYPES_BY_ENTITY: Final[dict[str, type[OpaqueId]]] = {
    identity.entity: identity for identity in _REGISTRY.values()
}

#: Every concrete identity type, keyed by contract prefix.
IDENTITY_TYPES_BY_PREFIX: Final[dict[str, type[OpaqueId]]] = dict(_REGISTRY)

#: Identifiers PC-01 deliberately allocates nowhere. Recorded here, and in
#: ``docs/program/P02_SEAMS.md`` section 9, so the catalog does not silently promise
#: an aggregate nobody builds. The type exists; no PC-01 code path calls ``new()``.
UNALLOCATED_IN_PC01: Final[tuple[str, ...]] = (
    "import_id",
    "job_id",
    "attempt_id",
    "lease_id",
    "worker_id",
    "export_id",
    "comparison_id",
    "sheet_link_id",
    "norms_snapshot_id",
    "erasure_request_id",
    "object_uid",
    "discipline_uid",
)


def identity_type_for_prefix(prefix: str) -> type[OpaqueId]:
    """Look up the identity type bound to a contract prefix."""
    try:
        return _REGISTRY[prefix]
    except KeyError:
        raise IdentifierFormatError(f"no declared identity type for prefix {prefix!r}") from None
