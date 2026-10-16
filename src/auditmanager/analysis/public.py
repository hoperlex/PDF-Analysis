"""The public surface of the analysis boundary.

Everything another package needs is here; everything else is an implementation
detail. ``P2-RUN-01`` calls :func:`run_stage` and persists the returned results
without reaching inside a stage; ``P2-AI-01`` registers ``text_analysis`` on the same
seam; ``P2-FND-01`` resolves evidence anchors against the text layer and block index
only, and :func:`document_text` is the one implementation of what "the document-global
character sequence" means.

There is no ``JobPackage`` and no ``ResultPackage`` on this surface. Those envelopes
carry attempt authority because they cross a remote-dispatch boundary; ``PC-01`` runs
stages in process, and this seam requires no attempt authority at all.
"""

from __future__ import annotations

from auditmanager.analysis.engine.registry import (
    StageDefinition,
    StageRegistry,
    default_registry,
)
from auditmanager.analysis.engine.result import (
    CONTRACT_VERSION,
    ArtifactRef,
    StageError,
    StageResult,
    StageStatus,
)
from auditmanager.analysis.engine.runner import run_stage
from auditmanager.analysis.engine.serialization import (
    ARTIFACT_MEDIA_TYPE, canonical_bytes, sha256_hex,
)
from auditmanager.analysis.ports.artifacts import (
    ARTIFACT_VERSION,
    ROLE_BLOCK_INDEX,
    ROLE_DOCUMENT_GRAPH,
    ROLE_PAGE_CROPS,
    ROLE_PAGE_INVENTORY,
    ROLE_RECOGNISED_TEXT,
    ROLE_SOURCE_DOCUMENT,
    ROLE_SOURCE_MARKDOWN,
    ROLE_SOURCE_STRUCTURED_COMPANION,
    ROLE_TEXT_LAYER,
    blob_role_for,
    publish_artifact,
    read_artifact,
)
from auditmanager.analysis.ports.stage import StageContext, StageHandler, StageProduction
from auditmanager.analysis.profiles.ar_v2.merge_input import MergePreparation, prepare_merge
from auditmanager.analysis.profiles.ar_v2.proposal_grounding import (
    ProposalGroundingResult,
    RejectedProposal,
)
from auditmanager.analysis.profiles.ar_v2.response import ProposedObservation
from auditmanager.analysis.profiles.ar_v2.recognised_context import RecognisedContext
from auditmanager.analysis.profiles.ar_v2.recorded_input import (
    RecordedV2Input,
    prepare_recorded_v2_input,
)
from auditmanager.analysis.profiles.ar_v2.recorded_request import RecordedGenerationSettings
from auditmanager.analysis.profiles.ar_v2.recorded_artifact import (
    ARTIFACT_ROLE as RECORDED_OBSERVATION_ARTIFACT_ROLE,
    ARTIFACT_VERSION as RECORDED_OBSERVATION_ARTIFACT_VERSION,
    BuiltRecordedArtifact,
    RecordedArtifactError,
    RecordedMergeInput,
    build_recorded_observation_artifact,
    read_recorded_merge_input,
)
from auditmanager.analysis.profiles.ar_v2.recorded_call import (
    RecordedCallFacts,
    build_recorded_call_facts,
)
from auditmanager.analysis.profiles.ar_v2.recorded_response import (
    RecordedReplayResult,
    replay_recorded_response,
)
from auditmanager.analysis.profiles.ar_v2.recorded_stage_result import (
    seal_recorded_v2_stage_result,
)
from auditmanager.analysis.profiles.ar_v2.registered import (
    PROFILE_ID as AR_V2_RECORDED_PROFILE_ID,
    PROMPT_BUNDLE_ID as AR_V2_RECORDED_BUNDLE_ID,
    RecordedProfileError,
    resolve_recorded_profile,
)
from auditmanager.analysis.profiles.ar_v2.response_pipeline import FinishedV2Response, finish_response
from auditmanager.analysis.profiles.ar_v2.response_schema import CATEGORIES as AR_V2_CATEGORIES
from auditmanager.analysis.profiles.ar_v2.response_schema import SEVERITIES as AR_V2_SEVERITIES
from auditmanager.analysis.stages.finding_merge import (
    ARTIFACT_ROLE as MERGE_ARTIFACT_ROLE,
    ARTIFACT_VERSION as MERGE_ARTIFACT_VERSION,
    MERGE_RULE_VERSION,
    merge_grounded,
)
from auditmanager.analysis.stages.extraction import (
    NORMALIZATION_DESCRIPTION,
    NORMALIZATION_ID,
)
from auditmanager.analysis.stages.source_preparation import document_text
from auditmanager.analysis.text import (
    AR_TEXT_PROFILE,
    ARTIFACT_ROLE,
    CostMeter,
    ModelAdapter,
    ModelCallJournal,
    ModelCallRecord,
    ModelRequest,
    ModelResponse,
    ProviderConfig,
    ProviderMode,
    ProxyAdapter,
    ProxySettings,
    TextAnalysisOutcome,
    load_provider_config,
    run_text_analysis,
)
from auditmanager.analysis.text.budget import REFERENCE_DOCUMENT_CHARACTERS, input_budget_characters
from auditmanager.analysis.recognised import KIND_PORTAL_DESCRIPTION, KIND_RECOGNISED_TEXT, QUOTE_SOURCE_RECOGNISED  # W55B-RECOGNISED-01
from auditmanager.analysis.ports.artifacts import ROLE_CROP_IMAGE, ROLE_PORTAL_BLOCKS  # W55B-GEOMETRY-01
from auditmanager.analysis.geometry.saved_crop_custody import (
    CheckedCropBytes,
    RunScopedGeometryStage,
    SavedCropCustodyRefused,
    check_saved_crop_bytes,
)
from auditmanager.analysis.text.proxy import ProxyDispatchError
from auditmanager.analysis.text.recorded import RecordedAdapter
from auditmanager.analysis.text.stage import STAGE_VERSION as TEXT_STAGE_VERSION
from auditmanager.analysis.text.anchors import BlockIndex, ResolvedAnchor
from auditmanager.analysis.text.textlayer import TextLayer

__all__ = [
    "ARTIFACT_MEDIA_TYPE",
    "ARTIFACT_VERSION",
    "ARTIFACT_ROLE",
    "AR_TEXT_PROFILE",
    "AR_V2_CATEGORIES",
    "AR_V2_RECORDED_BUNDLE_ID",
    "AR_V2_RECORDED_PROFILE_ID",
    "AR_V2_SEVERITIES",
    "BlockIndex",
    "BuiltRecordedArtifact",
    "CheckedCropBytes",
    "CONTRACT_VERSION",
    "KIND_PORTAL_DESCRIPTION",
    "KIND_RECOGNISED_TEXT",
    "NORMALIZATION_DESCRIPTION",
    "NORMALIZATION_ID",
    "QUOTE_SOURCE_RECOGNISED",
    "RECORDED_OBSERVATION_ARTIFACT_ROLE",
    "RECORDED_OBSERVATION_ARTIFACT_VERSION",
    "REFERENCE_DOCUMENT_CHARACTERS",
    "ROLE_BLOCK_INDEX",
    "ROLE_CROP_IMAGE",
    "ROLE_DOCUMENT_GRAPH",
    "ROLE_PAGE_CROPS",
    "ROLE_PAGE_INVENTORY",
    "ROLE_PORTAL_BLOCKS",
    "ROLE_RECOGNISED_TEXT",
    "ROLE_SOURCE_DOCUMENT",
    "ROLE_SOURCE_MARKDOWN",
    "ROLE_SOURCE_STRUCTURED_COMPANION",
    "ROLE_TEXT_LAYER",
    "ArtifactRef",
    "CostMeter",
    "FinishedV2Response",
    "ModelAdapter",
    "ModelCallJournal",
    "ModelCallRecord",
    "ModelRequest",
    "ModelResponse",
    "MergePreparation",
    "MERGE_ARTIFACT_ROLE",
    "MERGE_ARTIFACT_VERSION",
    "MERGE_RULE_VERSION",
    "ProposalGroundingResult",
    "ProposedObservation",
    "ProviderConfig",
    "ProviderMode",
    "ProxyAdapter",
    "ProxyDispatchError",
    "ProxySettings",
    "RejectedProposal",
    "RecognisedContext",
    "RecordedGenerationSettings",
    "RecordedMergeInput",
    "RecordedAdapter",
    "RecordedArtifactError",
    "RecordedCallFacts",
    "RecordedReplayResult",
    "RecordedV2Input",
    "RecordedProfileError",
    "ResolvedAnchor",
    "RunScopedGeometryStage",
    "SavedCropCustodyRefused",
    "TextLayer",
    "TEXT_STAGE_VERSION",
    "StageContext",
    "StageDefinition",
    "StageError",
    "StageHandler",
    "StageProduction",
    "StageRegistry",
    "StageResult",
    "StageStatus",
    "TextAnalysisOutcome",
    "default_registry",
    "document_text",
    "finish_response",
    "input_budget_characters",
    "load_provider_config",
    "publish_artifact",
    "prepare_merge",
    "build_recorded_call_facts",
    "build_recorded_observation_artifact",
    "check_saved_crop_bytes",
    "blob_role_for",
    "canonical_bytes",
    "prepare_recorded_v2_input",
    "read_artifact",
    "read_recorded_merge_input",
    "replay_recorded_response",
    "resolve_recorded_profile",
    "run_stage",
    "run_text_analysis",
    "seal_recorded_v2_stage_result",
    "sha256_hex",
    "merge_grounded",
]
