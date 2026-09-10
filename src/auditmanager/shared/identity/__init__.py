"""Opaque identifier value types for the frozen domain catalog.

Import identities from here::

    from auditmanager.shared.identity import ProjectUid, RunId

Everything exported is either an entity identity (a subclass of
:class:`OpaqueId`) or an explicitly non-identity value from
:mod:`auditmanager.shared.identity.non_identity`. Nothing else belongs in this
package: a path, an object key, a file name, a display ordinal and a checksum are
addresses, presentation values or verification values, and the contract forbids any
of them from being an identity.
"""

from __future__ import annotations

from auditmanager.shared.identity.errors import (
    IdentifierFormatError,
    IdentifierPrefixError,
    IdentityError,
)
from auditmanager.shared.identity.ids import (
    IDENTIFIER_FORMAT,
    IDENTIFIER_PATTERN,
    IDENTITY_TYPES_BY_ENTITY,
    IDENTITY_TYPES_BY_PREFIX,
    PREFIX_PATTERN,
    UNALLOCATED_IN_PC01,
    AnalysisProfileId,
    AttemptId,
    AuditEventId,
    BlobId,
    CommandId,
    ComparisonId,
    DecisionId,
    DisciplineUid,
    DocumentUid,
    ErasureRequestId,
    ExportId,
    FindingObservationId,
    FindingUid,
    ImportId,
    JobId,
    LeaseId,
    ModelCallId,
    NormsSnapshotId,
    ObjectUid,
    OpaqueId,
    ProjectUid,
    PromptBundleId,
    RunId,
    SheetLinkId,
    VersionUid,
    WorkerId,
    identity_type_for_prefix,
    pattern_for,
)
from auditmanager.shared.identity.non_identity import (
    CORRELATION_PATTERN,
    IDEMPOTENCY_KEY_PATTERN,
    SHA256_PATTERN,
    CorrelationId,
    IdempotencyKey,
    PayloadFingerprint,
    Sha256,
)
from auditmanager.shared.identity.ulid import (
    ULID_LENGTH,
    UlidFormatError,
    is_valid_ulid,
    new_ulid,
)

__all__ = [
    "CORRELATION_PATTERN",
    "IDEMPOTENCY_KEY_PATTERN",
    "IDENTIFIER_FORMAT",
    "IDENTIFIER_PATTERN",
    "IDENTITY_TYPES_BY_ENTITY",
    "IDENTITY_TYPES_BY_PREFIX",
    "PREFIX_PATTERN",
    "SHA256_PATTERN",
    "ULID_LENGTH",
    "UNALLOCATED_IN_PC01",
    "AnalysisProfileId",
    "AttemptId",
    "AuditEventId",
    "BlobId",
    "CommandId",
    "ComparisonId",
    "CorrelationId",
    "DecisionId",
    "DisciplineUid",
    "DocumentUid",
    "ErasureRequestId",
    "ExportId",
    "FindingObservationId",
    "FindingUid",
    "IdempotencyKey",
    "IdentifierFormatError",
    "IdentifierPrefixError",
    "IdentityError",
    "ImportId",
    "JobId",
    "LeaseId",
    "ModelCallId",
    "NormsSnapshotId",
    "ObjectUid",
    "OpaqueId",
    "PayloadFingerprint",
    "ProjectUid",
    "PromptBundleId",
    "RunId",
    "Sha256",
    "SheetLinkId",
    "UlidFormatError",
    "VersionUid",
    "WorkerId",
    "identity_type_for_prefix",
    "is_valid_ulid",
    "new_ulid",
    "pattern_for",
]
