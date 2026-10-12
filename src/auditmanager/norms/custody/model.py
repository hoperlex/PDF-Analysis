"""Value types of norm-corpus custody. No persistence, no object store, no clock."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import BinaryIO, Final, Iterable, Mapping, Protocol

#: R-76 / E-7: a dispatch try that fails is retried after these delays; the fifth failed
#: try leaves the admission ``poisoned`` (``ADMISSION_MAX_ATTEMPTS`` in migration 0018).
MAX_ATTEMPTS: Final[int] = 5
RETRY_DELAYS_SECONDS: Final[tuple[int, ...]] = (30, 300, 1800, 7200)


class AdmissionState(str, Enum):
    """``pending -> confirmed | poisoned | rejected``, ``poisoned -> pending | rejected``."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    POISONED = "poisoned"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class CustodySlot:
    """One binding slot: a role, its target and an opaque anchor. Not an identity."""

    role: str
    target_kind: str
    target_id: str
    anchor_kind: str
    anchor: str


@dataclass(frozen=True, slots=True)
class DeclaredContent:
    """What the verified manifest says the bytes of one slot are."""

    sha256: str
    size: int
    media_type: str


class CustodyManifest(Protocol):
    """The verified bundle manifest, as custody reads it: one declaration per slot.

    The bundle importer verifies the manifest (its own digests, every file's SHA-256 and
    size) before it admits anything; custody then refuses any admission the manifest does
    not name exactly. The drop is never a custody manifest (`R-104`).
    """

    def declared(self, slot: CustodySlot) -> DeclaredContent | None: ...


@dataclass(frozen=True, slots=True)
class ManifestIndex:
    """The simplest :class:`CustodyManifest`: an in-memory mapping from slot to content."""

    entries: Mapping[CustodySlot, DeclaredContent]

    def declared(self, slot: CustodySlot) -> DeclaredContent | None:
        return self.entries.get(slot)


class CustodySource(Protocol):
    """Where the dispatcher reads an admission's bytes from (the staged bundle)."""

    def open(self, admission: "Admission") -> bytes | BinaryIO: ...


@dataclass(frozen=True, slots=True)
class AdmissionRequest:
    """Phase one's input: a slot and the content the manifest declares for it."""

    role: str
    target_id: str
    anchor_kind: str
    anchor: str
    sha256: str
    size: int
    media_type: str

    @property
    def content(self) -> DeclaredContent:
        return DeclaredContent(sha256=self.sha256, size=self.size, media_type=self.media_type)


@dataclass(frozen=True, slots=True)
class Admission:
    """One ``norm_custody_admission`` row: the intent and its outbox entry."""

    admission_id: str
    role: str
    target_kind: str
    target_id: str
    anchor_kind: str
    anchor: str
    blob_id: str
    declared_size_bytes: int
    declared_sha256: str
    media_type: str
    state: AdmissionState
    attempt_count: int
    available_at: datetime
    last_failure: str | None
    created_at: datetime
    confirmed_at: datetime | None

    @property
    def slot(self) -> CustodySlot:
        return CustodySlot(
            role=self.role,
            target_kind=self.target_kind,
            target_id=self.target_id,
            anchor_kind=self.anchor_kind,
            anchor=self.anchor,
        )

    @property
    def content(self) -> DeclaredContent:
        return DeclaredContent(
            sha256=self.declared_sha256,
            size=self.declared_size_bytes,
            media_type=self.media_type,
        )


@dataclass(frozen=True, slots=True)
class AdmitOutcome:
    """``replayed`` is true when an identical live admission already held the slot."""

    admission: Admission
    replayed: bool


@dataclass(frozen=True, slots=True)
class Binding:
    """One immutable ``norm_custody_binding`` row."""

    binding_id: str
    admission_id: str
    role: str
    target_kind: str
    target_id: str
    anchor_kind: str
    anchor: str
    blob_id: str
    bound_at: datetime


@dataclass(frozen=True, slots=True)
class BindingPublication:
    """What one ``publish_bindings`` call made visible, and what was already visible."""

    bound: tuple[Binding, ...]
    already_bound: int


class DispatchResult(str, Enum):
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    RETRY_SCHEDULED = "retry_scheduled"
    POISONED = "poisoned"
    SETTLED_ELSEWHERE = "settled_elsewhere"


@dataclass(frozen=True, slots=True)
class DispatchStep:
    """One admission the dispatcher took, and how the try ended."""

    admission_id: str
    result: DispatchResult
    failure: str | None = None


@dataclass(frozen=True, slots=True)
class DispatchReport:
    """One ``dispatch --until-idle`` pass. ``pending`` counts what is still due later."""

    steps: tuple[DispatchStep, ...]
    pending: int
    poisoned: int

    def ids(self, result: DispatchResult) -> tuple[str, ...]:
        return tuple(step.admission_id for step in self.steps if step.result is result)

    @property
    def is_idle_and_complete(self) -> bool:
        """Every admission this pass could reach is settled and none waits or is poisoned."""
        return self.pending == 0 and self.poisoned == 0


@dataclass(frozen=True, slots=True)
class BindingDigestEntry:
    role: str
    target_kind: str
    target_id: str
    blob_id: str
    anchor_kind: str
    anchor: str


def binding_digest(entries: Iterable[BindingDigestEntry]) -> str:
    """SHA-256 over the sorted bindings (role, target, ``blob_id``, anchor), plan §3.5.

    One line per binding, fields separated by U+001F and lines by ``\\n``, sorted by the
    line itself. The bundle export computes the same digest over its manifest, so ``report``
    can compare the two without either side knowing the other's storage.
    """
    lines = sorted(
        "\x1f".join(
            (
                entry.role,
                entry.target_kind,
                entry.target_id,
                entry.blob_id,
                entry.anchor_kind,
                entry.anchor,
            )
        )
        + "\n"
        for entry in entries
    )
    digest = hashlib.sha256()
    for line in lines:
        digest.update(line.encode("utf-8"))
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class RejectedBlob:
    """A ``rejected`` Blob row (`D-143`) and whether any custody admission names it."""

    blob_id: str
    named_by_custody: bool


@dataclass(frozen=True, slots=True)
class CustodyReport:
    """``custody report``: read-only, computed from rows, never from the object store."""

    counts: Mapping[AdmissionState, int]
    poisoned: tuple[Admission, ...]
    rejected_admissions: tuple[Admission, ...]
    unbound_confirmed: tuple[Admission, ...]
    binding_count: int
    binding_digest: str
    rejected_blobs: tuple[RejectedBlob, ...] = field(default=())

    def count(self, state: AdmissionState) -> int:
        return int(self.counts.get(state, 0))

    @property
    def rejected_blob_count(self) -> int:
        return len(self.rejected_blobs)

    @property
    def all_confirmed(self) -> bool:
        return self.count(AdmissionState.PENDING) == 0 and self.count(AdmissionState.POISONED) == 0


class IncidentKind(str, Enum):
    OBJECT_MISSING = "object_missing"
    OBJECT_UNVERIFIABLE = "object_unverifiable"
    OBJECT_METADATA_DIFFERS = "object_metadata_differs"
    BLOB_ROW_NOT_AVAILABLE = "blob_row_not_available"


@dataclass(frozen=True, slots=True)
class CustodyIncident:
    """A confirmed admission (bound or not) whose canonical bytes the store cannot vouch for."""

    kind: IncidentKind
    admission_id: str
    binding_id: str | None
    blob_id: str


@dataclass(frozen=True, slots=True)
class CustodyReconciliation:
    """``custody reconcile``: incidents are reported, never repaired by guessing."""

    incidents: tuple[CustodyIncident, ...]
    redrive_due: tuple[str, ...]
    checked_blobs: int

    @property
    def is_clean(self) -> bool:
        return not self.incidents


__all__ = [
    "MAX_ATTEMPTS",
    "RETRY_DELAYS_SECONDS",
    "Admission",
    "AdmissionRequest",
    "AdmissionState",
    "AdmitOutcome",
    "Binding",
    "BindingDigestEntry",
    "BindingPublication",
    "CustodyIncident",
    "CustodyManifest",
    "CustodyReconciliation",
    "CustodyReport",
    "CustodySlot",
    "CustodySource",
    "DeclaredContent",
    "DispatchReport",
    "DispatchResult",
    "DispatchStep",
    "IncidentKind",
    "ManifestIndex",
    "RejectedBlob",
    "binding_digest",
]
