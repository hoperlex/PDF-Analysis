"""The ``StageResult`` value and the artifact reference it carries.

This is the whole return surface of the stage runner. It maps onto
``contracts/analysis/v1/stage-result.schema.json`` and onto nothing else: this task
constructs no ``JobPackage`` and no ``ResultPackage``, because those envelopes exist
for *remote dispatch* and ``PC-01`` does not dispatch remotely. A ``StageResult``
therefore carries no attempt authority, no execution token and no worker identity,
and there is no field here in which one could be smuggled.

Two schema rules are enforced in :meth:`StageResult.to_document` rather than left to
the validator, so a malformed result cannot be constructed in the first place:

* ``succeeded`` forbids an error. The key is *absent*, not ``null``: the schema says
  ``not: {required: ["error"]}``, which a ``null`` would still satisfy the wrong way.
* ``failed``, ``partial`` and ``skipped`` require one.

An ``ArtifactRef`` is content-addressed and nothing else. It has no ``bucket``,
``key``, ``uri``, ``url``, ``path`` or ``credential`` field, mirroring
``storage.models.PublishedBlob``, and adding one would be a freeze-break rather than
an implementation detail.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Final, Mapping

from auditmanager.shared.errors import DomainError, ErrorCode

#: The one contract version this package speaks. A consumer reading anything else
#: fails closed rather than guessing.
CONTRACT_VERSION: Final[str] = "1.0.0-draft.1"

_METRIC_KEY: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_ARTIFACT_ROLE: Final[re.Pattern[str]] = re.compile(
    r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$"
)
_SHA256: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
_BLOB_ID: Final[re.Pattern[str]] = re.compile(r"^blob_[0-9A-HJKMNP-TV-Z]{26}$")

#: Scalars the schema admits in ``metrics`` and in ``error.details``.
MetricValue = float | int | str | bool | None


class StageStatus(str, Enum):
    """The closed status set of the stage-result contract.

    All four members exist because the contract declares four and a consumer must be
    able to name any of them. That is not the same as the runner being able to
    *produce* any of them: ``partial`` and ``skipped`` have no constructor on
    :class:`StageResult` at all, and the registry's per-stage ``status_policy`` is
    checked before a result is built. See ``engine.runner``.
    """

    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    """A published artifact, addressed only by ``blob_id`` and verified by checksum."""

    role: str
    blob_id: str
    sha256: str
    size_bytes: int
    media_type: str

    def __post_init__(self) -> None:
        if not _ARTIFACT_ROLE.match(self.role):
            raise ValueError(f"artifact role {self.role!r} is not contract-shaped")
        if not _BLOB_ID.match(self.blob_id):
            raise ValueError("blob_id is not a contract-shaped blob identifier")
        if not _SHA256.match(self.sha256):
            raise ValueError("sha256 must be 64 lowercase hex characters")
        if self.size_bytes < 0:
            raise ValueError("size_bytes may not be negative")

    def to_document(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "blob_id": self.blob_id,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "media_type": self.media_type,
        }


@dataclass(frozen=True, slots=True)
class StageError:
    """The typed reason carrier a non-succeeded status requires.

    ``code`` and ``retryable`` are taken from the shared catalog rather than chosen
    here: ``retryable`` is a catalog property, so no call site can disagree with it.
    """

    code: ErrorCode
    message: str
    retryable: bool
    details: Mapping[str, MetricValue] = field(default_factory=dict)

    @classmethod
    def from_domain_error(cls, error: DomainError) -> "StageError":
        """Carry a :class:`DomainError` across the seam without inventing a type."""
        safe = error.code.safe_detail_keys
        details = {
            key: value
            for key, value in error.detail_fields.items()
            if key in safe and isinstance(value, (str, int, float, bool, type(None)))
        }
        return cls(
            code=error.code,
            message=str(error),
            retryable=error.code.retryable,
            details=details,
        )

    def to_document(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "code": self.code.value,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.details:
            for key in self.details:
                if not _METRIC_KEY.match(key):
                    raise ValueError(f"error detail key {key!r} is not contract-shaped")
            document["details"] = dict(self.details)
        return document


@dataclass(frozen=True, slots=True)
class StageResult:
    """The result of exactly one canonical registry stage."""

    stage_id: str
    stage_version: str
    status: StageStatus
    artifacts: tuple[ArtifactRef, ...] = ()
    metrics: Mapping[str, MetricValue] = field(default_factory=dict)
    error: StageError | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.status is StageStatus.SUCCEEDED and self.error is not None:
            raise ValueError("a succeeded stage result may not carry an error")
        if self.status is not StageStatus.SUCCEEDED and self.error is None:
            raise ValueError(f"a {self.status.value} stage result requires an error")
        if self.status is StageStatus.SKIPPED and self.artifacts:
            raise ValueError("a skipped stage result may not carry an artifact")

    def artifact(self, role: str) -> ArtifactRef:
        """Return the artifact published under ``role``, or raise."""
        for ref in self.artifacts:
            if ref.role == role:
                return ref
        raise KeyError(f"no artifact was published under role {role!r}")

    @property
    def roles(self) -> frozenset[str]:
        return frozenset(ref.role for ref in self.artifacts)

    def to_document(self) -> dict[str, Any]:
        """The JSON object the stage-result schema validates.

        The ``error`` key is omitted entirely on success. A ``null`` would still
        satisfy ``required: ["error"]`` and so would pass a check the contract means
        to fail.
        """
        for key in self.metrics:
            if not _METRIC_KEY.match(key):
                raise ValueError(f"metric key {key!r} is not contract-shaped")

        document: dict[str, Any] = {
            "contract_version": self.contract_version,
            "stage_id": self.stage_id,
            "stage_version": self.stage_version,
            "status": self.status.value,
            "artifacts": [ref.to_document() for ref in self.artifacts],
            "metrics": dict(self.metrics),
        }
        if self.error is not None:
            document["error"] = self.error.to_document()
        if self.started_at is not None:
            document["started_at"] = _isoformat(self.started_at)
        if self.finished_at is not None:
            document["finished_at"] = _isoformat(self.finished_at)
        return document


def _isoformat(moment: datetime) -> str:
    """RFC 3339 with a ``Z`` offset, which is what ``format: date-time`` expects."""
    text = moment.isoformat()
    return text.replace("+00:00", "Z")


__all__ = [
    "CONTRACT_VERSION",
    "ArtifactRef",
    "MetricValue",
    "StageError",
    "StageResult",
    "StageStatus",
]
