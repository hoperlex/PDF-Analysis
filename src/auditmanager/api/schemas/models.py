"""The 83 ``components.schemas`` of ``contracts/api/v1/openapi.json``, as Pydantic models.

`T-1` makes FastAPI generate the served document, and `W13-CONF`'s conformance gate compares
that document against the frozen contract. **The contract stays the authority**: every class
here is named exactly as its ``components.schemas`` key, and every keyword it emits is the
one the contract writes. Where the two could drift the gate says so on every run; this module
is the side that has to move.

Three spellings in here are deliberate and are the reason the generated document matches:

* **``Field(default=None, json_schema_extra=optional_property)``** for a property the contract
  declares *optional but not nullable* -- ``StartRunRequest.provider_mode``,
  ``Project.document_count``, ``UploadDocumentRequest.display_title`` and the rest.
  Pydantic's ordinary spelling for "may be absent" is ``X | None = None``, which emits a
  ``{"type": "null"}`` branch **and** a ``"default": null`` the contract does not declare.
  Both are semantic: a null branch admits ``{"provider_mode": null}``, which the contract
  refuses, and ``default`` is compared by the gate
  (``test_a_changed_parameter_default_is_caught``). The field's *type* stays the declared
  one, so a present value is still validated against it, and an absent one is ``None`` --
  which is what the previous parser forwarded and what `W13-BASE` section 7 pins across
  baseline cases ``04``, ``05`` and ``05b``.
* **A ``TypeAliasType`` per scalar newtype** -- ``ProjectUid``, ``Sha256``, ``Cursor``, ... --
  because a bare ``Annotated[str, ...]`` is inlined by Pydantic and the contract spells
  these as ``$ref``s into ``components.schemas``. A resolved ``$ref`` is exactly the drift
  `W13-CONF` refuses to normalize away (`N1` resolves component *parameters*, *responses*
  and *headers*, and deliberately not schemas).
* **``extra="forbid"`` on every object**, because every object schema in the contract
  declare ``additionalProperties: false``. There is no object schema here that does not.

Nothing in this module renders a response. The wire bytes are produced by the ``*_body``
functions beside it, which the response baseline pins byte for byte; these models declare
the *document*, and validate the declared request bodies.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import UploadFile
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, WithJsonSchema
from typing_extensions import TypeAliasType

__all__ = [
    "Account",
    "AccountPage",
    "AnalysisProfileId",
    "ApproveRegistrationRequest",
    "AppendDecisionRequest",
    "AppendDecisionResponse",
    "BlockGeometry",
    "CorrelationId",
    "CostBasis",
    "CreateProjectRequest",
    "Cursor",
    "DecisionEvent",
    "DecisionEventPage",
    "DecisionRecord",
    "DecisionRecordPage",
    "DecisionEventType",
    "DecisionId",
    "DocumentUid",
    "DocumentVersion",
    "DocumentVersionPage",
    "ErrorCode",
    "ErrorEnvelope",
    "Evidence",
    "Finding",
    "FindingCategory",
    "FindingDetail",
    "FindingObservation",
    "FindingObservationId",
    "FindingPage",
    "FindingUid",
    "IdempotencyKey",
    "InputManifestEntry",
    "ModelCallId",
    "ObservationProvenance",
    "PageInfo",
    "PersonNames",
    "Project",
    "ProjectPage",
    "ProjectUid",
    "PromptBundleId",
    "ProviderMode",
    "RegistrationRequest",
    "RegistrationRequestId",
    "RegistrationRequestPage",
    "RegistrationStatus",
    "RegistrationStatusResponse",
    "RejectRegistrationRequest",
    "ResetUserPasswordRequest",
    "Role",
    "ProductVersion",
    "ReleaseNoteKind",
    "ReleaseNoteItem",
    "ReleaseEntry",
    "ReleaseList",
    "MarkReleaseNotesReadRequest",
    "RunId",
    "JobId",
    "RunState",
    "RunStatus",
    "RunStatusPage",
    "ExecutionQueueItem",
    "ExecutionQueuePage",
    "ExecutionJournalEntry",
    "ExecutionJournalPage",
    "SetJobPriorityRequest",
    "SetExecutionPausedRequest",
    "ExecutionDispatchStatus",
    "Sha256",
    "StageId",
    "StageState",
    "StageStatus",
    "StartRunRequest",
    "SubmitRegistrationRequest",
    "UpdateMyProfileRequest",
    "UpdateUserRequest",
    "UploadDocumentRequest",
    "UserUid",
    "Verdict",
    "VersionBlockIndex",
    "VersionUid",
    "optional_property",
]


def optional_property(schema: dict[str, Any]) -> None:
    """Drop the ``default`` Pydantic emits for a field that merely may be absent.

    A callable ``json_schema_extra`` is handed the generated property schema to mutate. The
    contract declares no ``default`` on any property, and the conformance gate compares
    ``default``, so emitting one would be a difference -- and a wrong one: ``default: null``
    says the server substitutes ``null``, which is not what an absent property means here.

    **Measured, and it is belt and braces rather than load-bearing.** Replacing this body
    with ``pass`` changes the generated document by **nothing**: with
    ``separate_input_output_schemas=False`` FastAPI generates one schema per model in
    *serialization* mode, and Pydantic omits ``default`` there. ``model_json_schema()``
    alone -- validation mode -- does emit it, which is what this was written against.

    It is kept, and said out loud rather than quietly deleted, because the property it
    declares is the contract's and the mode FastAPI happens to choose is not.
    ``test_no_schema_property_declares_a_default`` pins the property itself, which is the
    thing worth guarding; this function is the declaration of intent beside it. The half of
    the spelling that **is** load-bearing is the type: ``ProviderMode`` with
    ``default=None`` rather than ``ProviderMode | None``, which the sweep's ``M16``
    reddens at two dotted locations.
    """
    schema.pop("default", None)


#: ``#/components/schemas/ErrorEnvelope.properties.details``, verbatim.
#:
#: Pydantic has no spelling for ``maxProperties`` or ``propertyNames``, and this schema is
#: not a validation surface in this application in any case: the envelope is built by
#: :mod:`auditmanager.shared.errors` and screened by its own detail-key rules, which is
#: where that bound is actually enforced. The declaration is written out so the *document*
#: still carries the contract's constraint rather than a looser one.
_DETAILS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "maxProperties": 16,
    "propertyNames": {"pattern": "^[a-z][a-z0-9_]{0,63}$"},
    "additionalProperties": {
        "type": ["string", "number", "integer", "boolean", "null"],
        "maxLength": 256,
    },
}

#: ``#/components/schemas/BlockGeometry.properties.bbox``, verbatim. A plain nested
#: ``BaseModel`` would make FastAPI mint a fourth top-level ``components.schemas`` entry
#: (``Bbox``) that the frozen contract does not declare, the same drift ``_DETAILS_SCHEMA``
#: exists to avoid one property up. The bbox is inline in the contract and stays inline here.
_BBOX_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["x0", "y0", "x1", "y1"],
    "properties": {
        "x0": {"type": "number"},
        "y0": {"type": "number"},
        "x1": {"type": "number"},
        "y1": {"type": "number"},
    },
}

#: ``{"type": "string", "format": "binary"}`` -- how the contract spells an opaque byte
#: payload, in ``UploadDocumentRequest.file`` and in the two binary response bodies.
#: FastAPI's ``UploadFile`` generates OpenAPI 3.1's other spelling for the same thing,
#: ``{"type": "string", "contentMediaType": "application/octet-stream"}``, which is a
#: *different media type* as well as a different keyword. The contract is the authority and
#: this is what it says.
_BINARY_STRING: dict[str, Any] = {"type": "string", "format": "binary"}

#: Every identity in this contract is a prefixed Crockford base32 ULID of 26 characters.
_ULID = "[0-9A-HJKMNP-TV-Z]{26}"


class _Object(BaseModel):
    """Every object schema in this contract is closed."""

    model_config = ConfigDict(extra="forbid")


# --- the scalar newtypes -----------------------------------------------------------
#
# ``TypeAliasType`` and not ``RootModel``. Both give the contract's ``$ref`` into
# ``components.schemas`` -- which is what these are, since a resolved ``$ref`` is exactly
# the drift `W13-CONF` refuses to normalize away (`N1` resolves component *parameters*,
# *responses* and *headers*, and deliberately not schemas). Only the alias is also a
# **scalar** to FastAPI, so the same declaration serves ``Path``, ``Query`` and ``Header``
# parameters: a ``RootModel`` in a path parameter is an outright
# ``AssertionError: Path params must be of one of the supported types`` at import, and
# spelling the constraint inline instead would put a second copy of every pattern in the
# document beside the one the ``$ref`` names.


ProjectUid = TypeAliasType(
    "ProjectUid", Annotated[str, Field(pattern=rf"^prj_{_ULID}$")]
)
DocumentUid = TypeAliasType(
    "DocumentUid", Annotated[str, Field(pattern=rf"^doc_{_ULID}$")]
)
VersionUid = TypeAliasType(
    "VersionUid", Annotated[str, Field(pattern=rf"^ver_{_ULID}$")]
)
RunId = TypeAliasType("RunId", Annotated[str, Field(pattern=rf"^run_{_ULID}$")])
JobId = TypeAliasType("JobId", Annotated[str, Field(pattern=rf"^job_{_ULID}$")])
FindingUid = TypeAliasType(
    "FindingUid", Annotated[str, Field(pattern=rf"^fnd_{_ULID}$")]
)
FindingObservationId = TypeAliasType(
    "FindingObservationId", Annotated[str, Field(pattern=rf"^fobs_{_ULID}$")]
)
DecisionId = TypeAliasType(
    "DecisionId", Annotated[str, Field(pattern=rf"^dec_{_ULID}$")]
)
AnalysisProfileId = TypeAliasType(
    "AnalysisProfileId", Annotated[str, Field(pattern=rf"^ap_{_ULID}$")]
)
PromptBundleId = TypeAliasType(
    "PromptBundleId", Annotated[str, Field(pattern=rf"^pb_{_ULID}$")]
)
ModelCallId = TypeAliasType(
    "ModelCallId", Annotated[str, Field(pattern=rf"^mc_{_ULID}$")]
)
#: `W49-SEAL-01`. The account and the registration request crossed the wire, so their
#: identities entered ``contracts/domain/v1/identifiers.json`` and are spelled here like
#: every other one.
UserUid = TypeAliasType("UserUid", Annotated[str, Field(pattern=rf"^usr_{_ULID}$")])
RegistrationRequestId = TypeAliasType(
    "RegistrationRequestId", Annotated[str, Field(pattern=rf"^reg_{_ULID}$")]
)
CorrelationId = TypeAliasType(
    "CorrelationId",
    Annotated[
        str,
        Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$", min_length=1, max_length=128),
    ],
)
IdempotencyKey = TypeAliasType(
    "IdempotencyKey",
    Annotated[
        str,
        Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$", min_length=1, max_length=128),
    ],
)
Sha256 = TypeAliasType("Sha256", Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")])
Cursor = TypeAliasType("Cursor", Annotated[str, Field(min_length=1, max_length=512)])


# --- the closed enumerations -------------------------------------------------------


class ErrorCode(str, enum.Enum):
    """Exactly the key set of ``contracts/domain/v1/error-codes.json``.

    Twenty-three codes since `W49-SEAL-01` added ``rate_limited``, which only the edge in
    front of ``/api/v1`` answers; the twenty-second was ``staged_upload_lost``, added by
    `W20-CODE` under owner ruling `R-8`, settling `D-18`, and the twenty-first
    ``dependency_credential_refused``, added at `e6d0a6a` under `R-3`. The catalog is the
    authority;
    ``tests/contract/shared_kernel/test_error_kernel.py`` refuses a disagreement at import.
    """

    VALIDATION_FAILED = "validation_failed"
    NOT_FOUND = "not_found"
    AUTHENTICATION_REQUIRED = "authentication_required"
    PERMISSION_DENIED = "permission_denied"
    CONFLICT = "conflict"
    STATE_TRANSITION_NOT_ALLOWED = "state_transition_not_allowed"
    IDEMPOTENCY_KEY_REUSE = "idempotency_key_reuse"
    IDEMPOTENCY_KEY_IN_PROGRESS = "idempotency_key_in_progress"
    IDEMPOTENCY_KEY_STALE = "idempotency_key_stale"
    UNSUPPORTED_CONTRACT_VERSION = "unsupported_contract_version"
    STORAGE_INTEGRITY_ERROR = "storage_integrity_error"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    DEPENDENCY_CREDENTIAL_REFUSED = "dependency_credential_refused"
    STAGED_UPLOAD_LOST = "staged_upload_lost"
    REQUIRED_NORM_UNAVAILABLE = "required_norm_unavailable"
    ANALYSIS_INPUT_INVALID = "analysis_input_invalid"
    ANALYSIS_FAILED = "analysis_failed"
    PARTIAL_RESULT_NOT_PUBLISHABLE = "partial_result_not_publishable"
    COST_BUDGET_EXCEEDED = "cost_budget_exceeded"
    STALE_ATTEMPT = "stale_attempt"
    EXECUTION_TOKEN_INVALID = "execution_token_invalid"
    RATE_LIMITED = "rate_limited"
    INTERNAL_ERROR = "internal_error"


class RunState(str, enum.Enum):
    """The success terminal is ``published``. There is deliberately no ``succeeded``."""

    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    VALIDATING = "validating"
    PUBLISHED = "published"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageStatus(str, enum.Enum):
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageId(str, enum.Enum):
    SOURCE_PREPARATION = "source_preparation"
    PAGE_GEOMETRY_EXTRACTION = "page_geometry_extraction"
    DOCUMENT_CONTEXT_BUILD = "document_context_build"
    TEXT_ANALYSIS = "text_analysis"
    BLOCK_ANALYSIS = "block_analysis"
    FINDING_MERGE = "finding_merge"
    FINDING_REVIEW = "finding_review"
    FINDING_CORRECTION = "finding_correction"
    NORM_VERIFICATION = "norm_verification"


class ProviderMode(str, enum.Enum):
    LIVE = "live"
    RECORDED = "recorded"


class CostBasis(str, enum.Enum):
    """How well a published cost figure is known. `D-21`.

    ``measured`` means every provider call the figure sums reported its own cost.
    ``estimated`` means at least one did not, so the total is derived. The value is an
    aggregate over every contributing call and never the last one's basis -- see
    ``auditmanager.runs.repository.RunCost`` and `DEBT_REGISTER.md` `D-15`.
    """

    MEASURED = "measured"
    ESTIMATED = "estimated"


class FindingCategory(str, enum.Enum):
    INTERNAL_CONTRADICTION = "internal_contradiction"
    EXPLICIT_PLACEHOLDER = "explicit_placeholder"


class Verdict(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"


class DecisionEventType(str, enum.Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    COMMENT = "comment"
    REVOKE = "revoke"


class ProjectSection(str, enum.Enum):
    """Legacy's fourteen project sections (`D-56`, `R-40`).

    ``backend/app/pipeline/stages/prepare/task_builder.py:1362`` names these fourteen;
    ``db/migrations/versions/20260925_0011_document_section.py`` restates them in the
    ``document.section`` CHECK, and ``tests/contract/domain_p02/test_project_section_catalog.py``
    is what keeps the two from disagreeing. A document with no section is not a fifteenth
    member of this enum -- it is ``UploadDocumentRequest.section`` or
    ``DocumentVersion.section`` absent, which is a different, equally real fact.
    """

    AR = "AR"
    AI = "AI"
    KM = "KM"
    KJ = "KJ"
    OV = "OV"
    EOM = "EOM"
    VK = "VK"
    PT = "PT"
    PB = "PB"
    SS = "SS"
    ITP = "ITP"
    GP = "GP"
    TX = "TX"
    POS = "POS"


class Role(str, enum.Enum):
    """`R-55`, `R-60`. The closed role vocabulary; an account holds a set of these."""

    EXPERT = "expert"
    ADMIN = "admin"


class RegistrationStatus(str, enum.Enum):
    """The ``registration_request`` machine's states (``state-machines.json``)."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# --- the shared envelopes ----------------------------------------------------------


class PageInfo(_Object):
    next_cursor: Cursor | None


class ErrorEnvelope(_Object):
    """The one failure shape. Rendered by ``envelope_response`` and by nothing else."""

    contract_version: Literal["1.0.0-draft.1"]
    error_code: ErrorCode
    message: Annotated[str, Field(min_length=1, max_length=512)]
    correlation_id: CorrelationId
    retryable: bool
    details: Annotated[
        dict[str, str | float | int | bool | None] | None,
        WithJsonSchema(_DETAILS_SCHEMA),
    ] = Field(default=None, json_schema_extra=optional_property)


# --- projects ----------------------------------------------------------------------


class CreateProjectRequest(_Object):
    name: Annotated[str, Field(min_length=1, max_length=200)]


class Project(_Object):
    project_uid: ProjectUid
    name: Annotated[str, Field(min_length=1, max_length=200)]
    created_at: datetime
    document_count: Annotated[int, Field(ge=0)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


class ProjectPage(_Object):
    items: list[Project]
    page: PageInfo


# --- documents ---------------------------------------------------------------------


class UploadDocumentRequest(_Object):
    """The multipart body. ``file`` is ``format: binary``; ``FastAPI.UploadFile`` emits that.

    The ``encoding.file.contentType: application/pdf`` the contract declares beside this
    schema is **not** generated by FastAPI and is restored with ``openapi_extra`` on the
    operation -- `W13-CONF` measured its absence and
    ``test_a_dropped_multipart_encoding_is_caught`` is the case that keeps it restored.
    """

    file: Annotated[UploadFile, WithJsonSchema(_BINARY_STRING)]
    display_title: Annotated[str, Field(min_length=1, max_length=400)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    #: `R-40`. Optional, like ``display_title`` beside it and for the same reason: a
    #: caller that does not yet know which of the fourteen sections a document belongs
    #: in gets a document with none, not a refused upload. See
    #: ``db/migrations/versions/20260925_0011_document_section.py``.
    section: ProjectSection = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class InputManifestEntry(_Object):
    role: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")]
    sha256: Sha256
    size_bytes: Annotated[int, Field(ge=0)]
    media_type: str


class DocumentVersion(_Object):
    version_uid: VersionUid
    document_uid: DocumentUid
    project_uid: ProjectUid
    version_ordinal: Annotated[int, Field(ge=1)]
    display_title: Annotated[str, Field(min_length=1, max_length=400)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    #: `R-40`. See ``UploadDocumentRequest.section``: optional for the same reason, and
    #: never defaulted to one of the fourteen when a document was uploaded with none.
    section: ProjectSection = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    source_filename: str | None = Field(default=None, json_schema_extra=optional_property)
    media_type: Literal["application/pdf"]
    byte_size: Annotated[int, Field(ge=0)]
    sha256: Sha256
    page_count: Annotated[int, Field(ge=1, le=30)]
    published_at: datetime
    input_manifest: list[InputManifestEntry]


class DocumentVersionPage(_Object):
    items: list[DocumentVersion]
    page: PageInfo


class BlockGeometry(_Object):
    block_id: Annotated[str, Field(pattern=r"^b_[0-9]{6}$")]
    page_number: Annotated[int, Field(ge=1)]
    block_ordinal: Annotated[int, Field(ge=0)]
    bbox: Annotated[dict[str, float], WithJsonSchema(_BBOX_SCHEMA)]
    bbox_unit: Literal["pt"]
    bbox_origin: Literal["top_left"]
    char_start: Annotated[int, Field(ge=0)]
    char_end: Annotated[int, Field(ge=1)]


class VersionBlockIndex(_Object):
    version_uid: VersionUid
    status: Literal["produced", "not_produced"]
    #: Required and nullable, not optional: the contract's ``VersionBlockIndex`` carries
    #: both fields on every answer, null exactly when ``status`` is ``not_produced``. A
    #: plain ``X | None`` with no default -- unlike ``Evidence.block_id`` above -- is what
    #: makes Pydantic require the key in the emitted document rather than merely permit it.
    produced_by_run_id: RunId | None
    text_layer_sha256: Sha256 | None
    block_count: Annotated[int, Field(ge=0)]
    blocks: list[BlockGeometry]


# --- runs --------------------------------------------------------------------------


class StartRunRequest(_Object):
    version_uid: VersionUid
    provider_mode: ProviderMode = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class StageState(_Object):
    stage_id: StageId
    stage_version: Annotated[str, Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    status: StageStatus
    error_code: str | None = Field(default=None, json_schema_extra=optional_property)
    started_at: datetime | None = Field(default=None, json_schema_extra=optional_property)
    finished_at: datetime | None = Field(default=None, json_schema_extra=optional_property)


class RunStatus(_Object):
    run_id: RunId
    reaudit_of_run_id: RunId = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    project_uid: ProjectUid
    version_uid: VersionUid
    state: RunState
    provider_mode: ProviderMode
    analysis_profile_id: AnalysisProfileId = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    prompt_bundle_id: PromptBundleId = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    stages: list[StageState]
    degradation_set: list[StageId] = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    terminal_reason: ErrorCode | None = Field(default=None, json_schema_extra=optional_property)
    #: `D-46`. **The same shape as ``ErrorEnvelope.details``, and the same constant**: it
    #: is the same rule -- safe scalar classifiers, restricted to the ``safe_detail_keys``
    #: the catalog declares for the reported code -- applied to the code in
    #: ``terminal_reason`` instead of to the code in ``error_code``. A second spelling of
    #: one constraint is a second thing to get wrong, so there is one.
    terminal_detail: Annotated[
        dict[str, str | float | int | bool | None] | None,
        WithJsonSchema(_DETAILS_SCHEMA),
    ] = Field(default=None, json_schema_extra=optional_property)
    interrupted_reason: str | None = Field(default=None, json_schema_extra=optional_property)
    published_finding_count: Annotated[int, Field(ge=0)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    diagnostic_observation_count: Annotated[int, Field(ge=0)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    cost_micros: Annotated[int, Field(ge=0)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    cost_basis: CostBasis = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    model_call_count: Annotated[int, Field(ge=0)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]
    created_at: datetime
    terminal_at: datetime | None = Field(default=None, json_schema_extra=optional_property)


class RunStatusPage(_Object):
    items: list[RunStatus]
    page: PageInfo


class ExecutionQueueItem(_Object):
    job_id: JobId
    run_id: RunId
    state: str
    priority: int
    created_at: datetime
    available_at: datetime


class ExecutionQueuePage(_Object):
    items: list[ExecutionQueueItem]
    page: PageInfo
    paused: bool


class ExecutionJournalEntry(_Object):
    event_id: str
    run_id: RunId
    aggregate_type: str
    aggregate_id: str
    event_type: str
    occurred_at: datetime
    payload: dict[str, str | int | float | bool | None]


class ExecutionJournalPage(_Object):
    items: list[ExecutionJournalEntry]
    page: PageInfo


class SetJobPriorityRequest(_Object):
    priority: Annotated[int, Field(ge=-100, le=100)]


class SetExecutionPausedRequest(_Object):
    paused: bool


class ExecutionDispatchStatus(_Object):
    paused: bool
    changed_at: datetime


# --- findings ----------------------------------------------------------------------


class Evidence(_Object):
    evidence_ordinal: Annotated[int, Field(ge=0)]
    page_number: Annotated[int, Field(ge=1)]
    quote: Annotated[str, Field(min_length=1, max_length=2000)]
    char_start: Annotated[int, Field(ge=0)]
    char_end: Annotated[int, Field(ge=1)]
    block_id: Annotated[str, Field(pattern=r"^b_[0-9]{6}$")] | None = Field(
        default=None, json_schema_extra=optional_property
    )


class ObservationProvenance(_Object):
    stage_id: StageId
    analysis_profile_id: AnalysisProfileId
    prompt_bundle_id: PromptBundleId
    provider_mode: ProviderMode
    model_call_id: ModelCallId | None = Field(default=None, json_schema_extra=optional_property)
    model_identity: str | None = Field(default=None, json_schema_extra=optional_property)


class FindingObservation(_Object):
    finding_observation_id: FindingObservationId
    run_id: RunId
    category: FindingCategory
    finding_text: Annotated[str, Field(min_length=1, max_length=4000)]
    recommendation_text: Annotated[str, Field(min_length=1, max_length=4000)]
    evidence: Annotated[list[Evidence], Field(min_length=1)]
    provenance: ObservationProvenance


class Finding(_Object):
    finding_uid: FindingUid
    project_uid: ProjectUid
    version_uid: VersionUid
    run_id: RunId
    category: FindingCategory
    observation: FindingObservation
    current_verdict: Verdict
    latest_decision_id: DecisionId | None = Field(default=None, json_schema_extra=optional_property)
    decision_recorded_at: datetime | None = Field(default=None, json_schema_extra=optional_property)


class FindingDetail(_Object):
    """``Finding``'s property set restated, plus exactly two.

    It is restated and not composed with ``allOf``: under JSON Schema 2020-12 an
    ``additionalProperties: false`` sees only its own schema object's properties, so an
    ``allOf`` branch over the closed ``Finding`` would reject the two this adds.
    ``tests/contract/api_v1/test_finding_detail_composition.py`` pins it.
    """

    finding_uid: FindingUid
    project_uid: ProjectUid
    version_uid: VersionUid
    run_id: RunId
    category: FindingCategory
    observation: FindingObservation
    current_verdict: Verdict
    latest_decision_id: DecisionId | None = Field(default=None, json_schema_extra=optional_property)
    decision_recorded_at: datetime | None = Field(default=None, json_schema_extra=optional_property)
    latest_comment: str | None = Field(default=None, json_schema_extra=optional_property)
    decision_event_count: Annotated[int, Field(ge=0)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


class FindingPage(_Object):
    items: list[Finding]
    page: PageInfo


# --- decisions ---------------------------------------------------------------------


class AppendDecisionRequest(_Object):
    event_type: DecisionEventType
    finding_observation_id: FindingObservationId
    comment: Annotated[str, Field(min_length=1, max_length=4000)] | None = Field(
        default=None, json_schema_extra=optional_property
    )


class DecisionEvent(_Object):
    decision_id: DecisionId
    finding_uid: FindingUid
    finding_observation_id: FindingObservationId
    event_type: DecisionEventType
    verdict: Verdict | None = Field(default=None, json_schema_extra=optional_property)
    comment: str | None = Field(default=None, json_schema_extra=optional_property)
    author_label: Annotated[str, Field(min_length=1, max_length=128)]
    recorded_at: datetime


class AppendDecisionResponse(_Object):
    event: DecisionEvent
    current_verdict: Verdict


class DecisionEventPage(_Object):
    items: list[DecisionEvent]
    page: PageInfo


class DecisionRecord(_Object):
    """``DecisionEvent``'s property set restated, plus the finding context.

    Restated and not composed with ``allOf``, for the reason ``FindingDetail`` gives:
    under JSON Schema 2020-12 an ``additionalProperties: false`` sees only its own schema
    object's properties, so an ``allOf`` branch over the closed ``DecisionEvent`` would
    reject the six this adds.

    The six are required, and ``FindingDetail.decision_event_count`` is not: there the
    count describes a finding that may never have been decided, and here every record IS
    an event, so the count is at least one and its absence would mean nothing.
    """

    decision_id: DecisionId
    finding_uid: FindingUid
    finding_observation_id: FindingObservationId
    event_type: DecisionEventType
    verdict: Verdict | None = Field(default=None, json_schema_extra=optional_property)
    comment: str | None = Field(default=None, json_schema_extra=optional_property)
    author_label: Annotated[str, Field(min_length=1, max_length=128)]
    recorded_at: datetime
    project_uid: ProjectUid
    run_id: RunId
    category: FindingCategory
    finding_text: Annotated[str, Field(min_length=1, max_length=4000)]
    current_verdict: Verdict
    decision_event_count: Annotated[int, Field(ge=0)]


class DecisionRecordPage(_Object):
    items: list[DecisionRecord]
    page: PageInfo


# --- dashboard -----------------------------------------------------------------------
#
# `R-44`. One aggregate read across the whole deployment; see ``getDashboardSummary`` in
# ``api/routers/dashboard.py`` for what it answers and ``docs/program/W46-SEAL.md``
# section 3 for the argument.


class ProjectDocumentCount(_Object):
    """One row of the "documents per project" panel. Same fact ``Project.document_count``
    already publishes, gathered here for every project in one read."""

    project_uid: ProjectUid
    name: Annotated[str, Field(min_length=1, max_length=200)]
    document_count: Annotated[int, Field(ge=0)]


class VerdictCount(_Object):
    """How many findings, across every project, currently stand at one verdict.

    Every member of ``Verdict`` is present. A verdict nobody has recorded is ``count: 0``,
    not an absent row -- absent is not empty.
    """

    verdict: Verdict
    count: Annotated[int, Field(ge=0)]


class RunStateCount(_Object):
    """How many runs, across every project, currently sit in one state.

    Every member of ``RunState`` is present, for the same reason ``VerdictCount`` states.
    """

    state: RunState
    count: Annotated[int, Field(ge=0)]


class RunActivitySpend(_Object):
    """What every run, across every project, has spent at the provider so far.

    The same conservative rule ``RunStatus``'s own ``cost_basis`` applies to one run,
    computed here over every ``model_call`` row that exists: ``measured`` only when every
    contributing row reported a measured cost.
    """

    model_call_count: Annotated[int, Field(ge=0)]
    cost_micros: Annotated[int, Field(ge=0)]
    cost_basis: CostBasis


class RunActivity(_Object):
    by_state: list[RunStateCount]
    #: Optional, not nullable -- absent on a deployment with no ``model_call`` row at
    #: all. ``RunRepository.cost()`` answers ``None`` for the identical state on one run
    #: and says why in its own docstring; this aggregate now keeps that branch rather
    #: than reporting a zero labelled ``measured`` over an empty table (`F-1`,
    #: ``docs/program/reviews/W46-JUDGE-A.md`` section 3).
    spend: RunActivitySpend = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class SectionDocumentCount(_Object):
    """How many published documents carry one project section (`R-40`, `D-56`).

    ``section`` is optional, exactly as ``DocumentVersion.section`` is, and its absence on
    one row of this list means the same thing it means there: this row is the
    unclassified bucket, not a fifteenth section. Every one of the fourteen frozen codes
    is present even at ``document_count: 0`` -- "a section with no documents" is the
    dispatch brief's own example of absent not being empty.
    """

    document_count: Annotated[int, Field(ge=0)]
    section: ProjectSection = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class DashboardSummary(_Object):
    """``getDashboardSummary``'s whole answer. All four panels, one read, no filter."""

    documents_by_project: list[ProjectDocumentCount]
    findings_by_verdict: list[VerdictCount]
    run_activity: RunActivity
    section_breakdown: list[SectionDocumentCount]


# --- accounts and registration requests ------------------------------------------------
#
# `W49-SEAL-01`, owner rulings `R-55` ... `R-61`. The operations are in
# ``api/routers/me.py``, ``api/routers/registrations.py`` and ``api/routers/users.py``; the
# rules they answer by are ``auditmanager.access``'s and are not restated here. What is
# restated is the bound a transport schema states for a body: a name is 1..60 characters,
# a login as typed is at most 320 (the exchange's own bound; ``access`` folds and checks the
# stored 254), a password 1..1024, a rejection reason 1..256.


def _unique_roles(value: list[Any]) -> list[Any]:
    """``uniqueItems: true``, enforced and not only declared: a role named twice is a
    refused request, never a silently de-duplicated one."""
    from pydantic_core import PydanticCustomError

    if len(set(value)) != len(value):
        raise PydanticCustomError("unique_items", "the roles must be distinct")
    return value


_PersonName = Annotated[str, Field(min_length=1, max_length=60)]

def _declare_unique_items(schema: dict[str, Any]) -> None:
    """``uniqueItems: true`` in the document. A callable rather than a dict, so it composes
    with :func:`optional_property` on the one optional role set (``UpdateUserRequest``)."""
    schema["uniqueItems"] = True


def _optional_unique_items(schema: dict[str, Any]) -> None:
    """Both of the above for an optional role set: an outer ``json_schema_extra`` replaces
    the inner one rather than composing with it, so the two are applied together here."""
    optional_property(schema)
    _declare_unique_items(schema)


#: A role set on the wire: a JSON array of distinct ``Role`` values.
_RoleSet = Annotated[
    list[Role],
    AfterValidator(_unique_roles),
    Field(json_schema_extra=_declare_unique_items),
]


class Account(_Object):
    """One account, as the account itself and an administrator read it."""

    user_uid: UserUid
    login: Annotated[str, Field(min_length=1, max_length=254)]
    display_label: Annotated[str, Field(min_length=1, max_length=254)]
    last_name: _PersonName | None
    first_name: _PersonName | None
    middle_name: _PersonName | None
    roles: _RoleSet
    profile_complete: bool
    is_default_credential: bool
    archived_at: datetime | None


class AccountPage(_Object):
    items: list[Account]
    page: PageInfo


class ProductVersion(_Object):
    product_version: str
    build_id: str
    contract_version: str


class ReleaseNoteKind(str, enum.Enum):
    new = "new"
    improved = "improved"
    fixed = "fixed"


class ReleaseNoteItem(_Object):
    kind: ReleaseNoteKind
    screen: str
    where: str
    text: str


class ReleaseEntry(_Object):
    version: str
    revision: Annotated[int, Field(ge=1)]
    date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    title: str
    is_archive: bool
    range_label: str | None
    items: list[ReleaseNoteItem]


class ReleaseList(_Object):
    items: list[ReleaseEntry]
    whats_new: list[str]


class MarkReleaseNotesReadRequest(_Object):
    read_through: str


class PersonNames(_Object):
    last_name: _PersonName
    first_name: _PersonName
    middle_name: _PersonName = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class UpdateMyProfileRequest(_Object):
    last_name: _PersonName
    first_name: _PersonName
    middle_name: _PersonName = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    email: Annotated[str, Field(min_length=1, max_length=320)] = Field(
        default=None, json_schema_extra=optional_property
    )  # type: ignore[assignment]


class UpdateUserRequest(_Object):
    names: PersonNames = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]
    roles: _RoleSet = Field(default=None, json_schema_extra=_optional_unique_items)  # type: ignore[assignment]


class ResetUserPasswordRequest(_Object):
    temporary_password: Annotated[str, Field(min_length=1, max_length=1024)]


class SubmitRegistrationRequest(_Object):
    login: Annotated[str, Field(min_length=1, max_length=320)]
    password: Annotated[str, Field(min_length=1, max_length=1024)]
    last_name: _PersonName
    first_name: _PersonName
    middle_name: _PersonName = Field(default=None, json_schema_extra=optional_property)  # type: ignore[assignment]


class RegistrationStatusResponse(_Object):
    """`R-56` with its 2026-10-06 addendum: the only status ever shown is ``pending``."""

    status: Literal["pending"]


class RegistrationRequest(_Object):
    request_id: RegistrationRequestId
    login: Annotated[str, Field(min_length=1, max_length=254)]
    display_label: Annotated[str, Field(min_length=1, max_length=66)]
    last_name: _PersonName
    first_name: _PersonName
    middle_name: _PersonName | None
    status: RegistrationStatus
    submitted_at: datetime
    decided_at: datetime | None
    decided_by: UserUid | None
    rejection_reason: Annotated[str, Field(min_length=1, max_length=256)] | None
    created_user_uid: UserUid | None


class RegistrationRequestPage(_Object):
    items: list[RegistrationRequest]
    page: PageInfo
    pending_total: Annotated[int, Field(ge=0)]


class ApproveRegistrationRequest(_Object):
    roles: Annotated[_RoleSet, Field(min_length=1)]


class RejectRegistrationRequest(_Object):
    reason: Annotated[str, Field(min_length=1, max_length=256)]
