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
from auditmanager.analysis.profiles.ar_shared.recognised_context import RecognisedContext
from auditmanager.analysis.profiles.ar_v3.local_evaluation import (
    LocalV3Evaluation,
    SuppliedV3Response,
    V3LocalEvaluationRefused,
    evaluate_v3_supplied_response,
)
from auditmanager.analysis.profiles.ar_v3.v3_profile import (
    PROFILE_ID as AR_V3_BETA_PROFILE_ID,
    PROMPT_BUNDLE_ID as AR_V3_BETA_BUNDLE_ID,
    BetaV3Profile,
    BetaV3ProfileRefused,
    SealedV3Request,
    prepare_beta_v3_request,
    resolve_beta_v3_profile,
)
from auditmanager.analysis.profiles.ar_v3.request_delivery import (
    V3DeliveryRefused,
    V3GenerationSettings,
    build_v3_model_request,
)
from auditmanager.analysis.profiles.ar_v3.request_candidate import (
    V3RequestCandidate,
    V3RequestRefused,
    prepare_v3_request_candidate,
    prepare_v3_scoped_request_candidate,
)
from auditmanager.analysis.profiles.ar_v3.norm_map.beta_sources import (
    BetaSourcePolicyRefused,
    load_beta_source_policy,
)
from auditmanager.analysis.profiles.ar_v3.set_input import (
    V3SetInputRefused,
    parse_v3_set_input,
)
from auditmanager.analysis.stages.extraction import (
    NORMALIZATION_DESCRIPTION,
    NORMALIZATION_ID,
)
from auditmanager.analysis.stages.source_preparation import document_text
from auditmanager.analysis.text import (
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
from auditmanager.analysis.text.budget import (
    MAX_ANALYSIS_WINDOWS,
    REFERENCE_DOCUMENT_CHARACTERS,
    input_budget_characters,
    windowed_budget_characters,
)
from auditmanager.analysis.text.windowed import run_text_analysis_windows  # SECTION-CHUNKED-ANALYSIS-01
from auditmanager.analysis.text.windows import (  # SECTION-CHUNKED-ANALYSIS-01
    PARAM_COUNT as TEXT_WINDOW_PARAM_COUNT,
    PARAM_FIRST_PAGE as TEXT_WINDOW_PARAM_FIRST_PAGE,
    PARAM_INDEX as TEXT_WINDOW_PARAM_INDEX,
    PARAM_KEY as TEXT_WINDOW_PARAM_KEY,
    PARAM_LAST_PAGE as TEXT_WINDOW_PARAM_LAST_PAGE,
    PARAM_REPLY_BLOB_ID as TEXT_WINDOW_PARAM_REPLY_BLOB_ID,
    PARAM_REPLY_BLOB_SHA256 as TEXT_WINDOW_PARAM_REPLY_BLOB_SHA256,
    PARAM_REPLY_BLOB_SIZE as TEXT_WINDOW_PARAM_REPLY_BLOB_SIZE,
    RecoveredWindow,
    WindowCustody,
    WindowIdentity,
    WindowPolicy,
    text_window_policy,
)
from auditmanager.analysis.recognised import KIND_PORTAL_DESCRIPTION, KIND_RECOGNISED_TEXT, QUOTE_SOURCE_RECOGNISED  # W55B-RECOGNISED-01
from auditmanager.analysis.ports.artifacts import ROLE_CROP_IMAGE, ROLE_PORTAL_BLOCKS  # W55B-GEOMETRY-01
from auditmanager.analysis.geometry.saved_crop_custody import (
    CheckedCropBytes,
    CheckedCropItem,
    PreparedCropItem,
    RunScopedGeometryStage,
    SavedCropCustodyRefused,
    check_saved_crop_bytes,
    check_saved_crop_item_bytes,
    prepare_saved_crop_item,
)
from auditmanager.analysis.recognised.region_candidate import (
    RecognisedRegionCandidate,
    RecognisedRegionRefused,
    bind_recognised_region_candidate,
)
from auditmanager.analysis.text.saved_window_custody import (
    CheckedRunTextWindowInput,
    RunScopedTextStage,
    SavedTextCustodyRefused,
    check_run_text_window_input,
    select_run_text_layer_ref,
)
from auditmanager.analysis.text.source_bytes import (
    SuppliedTextSourceRefused,
    check_supplied_text_layer_bytes,
)
from auditmanager.analysis.text.chunk_preflight import ChunkPreflightError
from auditmanager.analysis.text.proxy import ProxyDispatchError
from auditmanager.analysis.text.lock import ModelPin, pinned_models
from auditmanager.analysis.text.recorded import RecordedAdapter
from auditmanager.analysis.text.stage import STAGE_VERSION as TEXT_STAGE_VERSION
from auditmanager.analysis.text.anchors import BlockIndex, ResolvedAnchor
from auditmanager.analysis.text.textlayer import TextLayer

__all__ = [
    "BetaV3Profile",
    "BetaV3ProfileRefused",
    "SealedV3Request",
    "prepare_beta_v3_request",
    "V3DeliveryRefused",
    "V3GenerationSettings",
    "build_v3_model_request",
    "resolve_beta_v3_profile",
    "ARTIFACT_MEDIA_TYPE",
    "ARTIFACT_VERSION",
    "ARTIFACT_ROLE",
    "AR_V3_BETA_BUNDLE_ID",
    "AR_V3_BETA_PROFILE_ID",
    "BlockIndex",
    "CheckedCropBytes",
    "CheckedCropItem",
    "CheckedRunTextWindowInput",
    "ChunkPreflightError",
    "CONTRACT_VERSION",
    "KIND_PORTAL_DESCRIPTION",
    "KIND_RECOGNISED_TEXT",
    "NORMALIZATION_DESCRIPTION",
    "NORMALIZATION_ID",
    "QUOTE_SOURCE_RECOGNISED",
    "MAX_ANALYSIS_WINDOWS",
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
    "ModelAdapter",
    "ModelPin",
    "ModelCallJournal",
    "ModelCallRecord",
    "ModelRequest",
    "ModelResponse",
    "pinned_models",
    "PreparedCropItem",
    "ProviderConfig",
    "ProviderMode",
    "ProxyAdapter",
    "ProxyDispatchError",
    "ProxySettings",
    "RecognisedContext",
    "RecordedAdapter",
    "RecoveredWindow",
    "RecognisedRegionCandidate",
    "RecognisedRegionRefused",
    "ResolvedAnchor",
    "RunScopedGeometryStage",
    "RunScopedTextStage",
    "SavedCropCustodyRefused",
    "SavedTextCustodyRefused",
    "SuppliedTextSourceRefused",
    "TextLayer",
    "TEXT_STAGE_VERSION",
    "TEXT_WINDOW_PARAM_COUNT",
    "TEXT_WINDOW_PARAM_FIRST_PAGE",
    "TEXT_WINDOW_PARAM_INDEX",
    "TEXT_WINDOW_PARAM_KEY",
    "TEXT_WINDOW_PARAM_LAST_PAGE",
    "TEXT_WINDOW_PARAM_REPLY_BLOB_ID",
    "TEXT_WINDOW_PARAM_REPLY_BLOB_SHA256",
    "TEXT_WINDOW_PARAM_REPLY_BLOB_SIZE",
    "WindowCustody",
    "WindowIdentity",
    "WindowPolicy",
    "StageContext",
    "StageDefinition",
    "StageError",
    "StageHandler",
    "StageProduction",
    "StageRegistry",
    "StageResult",
    "StageStatus",
    "TextAnalysisOutcome",
    "LocalV3Evaluation",
    "BetaSourcePolicyRefused",
    "SuppliedV3Response",
    "V3LocalEvaluationRefused",
    "V3RequestCandidate",
    "V3RequestRefused",
    "V3SetInputRefused",
    "default_registry",
    "document_text",
    "input_budget_characters",
    "load_provider_config",
    "load_beta_source_policy",
    "publish_artifact",
    "prepare_v3_request_candidate",
    "prepare_v3_scoped_request_candidate",
    "parse_v3_set_input",
    "evaluate_v3_supplied_response",
    "check_saved_crop_bytes",
    "check_saved_crop_item_bytes",
    "check_run_text_window_input",
    "check_supplied_text_layer_bytes",
    "bind_recognised_region_candidate",
    "blob_role_for",
    "canonical_bytes",
    "read_artifact",
    "run_stage",
    "run_text_analysis",
    "run_text_analysis_windows",
    "select_run_text_layer_ref",
    "text_window_policy",
    "windowed_budget_characters",
    "sha256_hex",
    "prepare_saved_crop_item",
]
