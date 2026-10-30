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
from auditmanager.analysis.profiles.ar_shared.recognised_context import (
    RecognisedContext,
    RecognisedContextError,
    select_context as select_recognised_context,  # SECTION-CATEGORY-OCR-01
)
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
from auditmanager.analysis.stages.source_preparation import (
    document_text, run_source_preparation_with_progress,
)
from auditmanager.analysis.stages.pdf_precheck import PdfPrecheckProgress
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
from auditmanager.analysis.text.profile_registry import relaxed_profile_pair
from auditmanager.analysis.text.recognised_input import (  # SECTION-CATEGORY-OCR-01
    RecognisedPage,
    total_characters as recognised_total_characters,
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
    relaxed_window_characters,
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
from auditmanager.analysis.text.cost import model_rate_sha256, require_approved_model, request_cost_upper_usd
from auditmanager.analysis.text.recorded import RecordedAdapter
from auditmanager.analysis.text.wire_schema import to_wire_schema, with_wire_schema  # AR-V3-WIRE-SCHEMA-01
from auditmanager.analysis.text.stage import STAGE_VERSION as TEXT_STAGE_VERSION
from auditmanager.analysis.text.anchors import BlockIndex, ResolvedAnchor
from auditmanager.analysis.text.textlayer import TextLayer

from auditmanager.analysis.geometry.render import (  # CMP-PROFILE-01
    FULL_PAGE_MAX_PIXELS,
    PdfiumDocument,
    page_raster_size,
)

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
    "relaxed_profile_pair",
    "relaxed_window_characters",
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
    "model_rate_sha256",
    "request_cost_upper_usd",
    "require_approved_model",
    "PreparedCropItem",
    "ProviderConfig",
    "ProviderMode",
    "ProxyAdapter",
    "ProxyDispatchError",
    "ProxySettings",
    "RecognisedContext",
    "RecognisedContextError",
    "RecognisedPage",
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
    "to_wire_schema",
    "with_wire_schema",
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
    "run_source_preparation_with_progress",
    "PdfPrecheckProgress",
    "recognised_total_characters",
    "run_text_analysis",
    "run_text_analysis_windows",
    "select_recognised_context",
    "select_run_text_layer_ref",
    "text_window_policy",
    "windowed_budget_characters",
    "sha256_hex",
    "prepare_saved_crop_item",
    "FULL_PAGE_MAX_PIXELS",
    "PdfiumDocument",
    "page_raster_size",
]

# HOTFIX-ANALYSIS-1030: bounded preliminary review method.
from auditmanager.analysis.extended import (
    PLAN_VERSION as EXTENDED_REVIEW_VERSION,
    REPLY_ROLE as EXTENDED_REPLY_ROLE,
    RESULT_ROLE as EXTENDED_REVIEW_ROLE,
    block_payload as extended_block_payload,
    build_request as build_extended_request,
    canonical as extended_canonical,
    digest as extended_digest,
    enabled as extended_review_enabled,
    finalize_items as finalize_extended_items,
    parse_reply as parse_extended_reply,
    plan_inputs as plan_extended_inputs,
)
from auditmanager.analysis.ports.artifacts import envelope as extended_artifact_envelope

__all__.extend([
    "EXTENDED_REVIEW_VERSION", "EXTENDED_REPLY_ROLE", "EXTENDED_REVIEW_ROLE",
    "extended_block_payload", "build_extended_request", "extended_canonical",
    "extended_digest", "extended_review_enabled", "finalize_extended_items",
    "parse_extended_reply", "plan_extended_inputs", "extended_artifact_envelope",
])


# Full ordinary workflow seams; imports stay lazy until the procedure is selected.
def prepare_native_page_sources(**kwargs):
    from auditmanager.analysis.extended.native_pages import prepare_native_page_sources as prepare
    return prepare(**kwargs)


def extended_workflow_procedures(**kwargs):
    from auditmanager.analysis.extended.workflow import workflow_procedures
    return workflow_procedures(**kwargs)


def build_comprehensive_request(**kwargs):
    from auditmanager.analysis.extended.workflow import build_comprehensive_request as build
    return build(**kwargs)


def deterministic_extended_merge(*args, **kwargs):
    from auditmanager.analysis.extended.workflow import deterministic_lossless_merge
    return deterministic_lossless_merge(*args, **kwargs)


__all__.extend(["prepare_native_page_sources", "extended_workflow_procedures",
                "build_comprehensive_request", "deterministic_extended_merge"])


def build_norm_review_request(**kwargs):
    from auditmanager.analysis.extended.workflow import build_norm_review_request as build
    return build(**kwargs)


def parse_norm_review(*args, **kwargs):
    from auditmanager.analysis.extended.workflow import parse_norm_review as parse
    return parse(*args, **kwargs)


__all__.extend(["build_norm_review_request", "parse_norm_review"])


def estimate_extended_visual_scope(**kwargs):
    from auditmanager.analysis.extended.estimate import estimate_visual_scope
    return estimate_visual_scope(**kwargs)


def extended_workflow_procedures_v3(**kwargs):
    from auditmanager.analysis.extended.workflow import workflow_procedures_v3
    return workflow_procedures_v3(**kwargs)


def build_comprehensive_request_v3(**kwargs):
    from auditmanager.analysis.extended.workflow import build_comprehensive_request_v3 as build
    return build(**kwargs)


def build_extended_critic_request(**kwargs):
    from auditmanager.analysis.extended.review import build_critic_request
    return build_critic_request(**kwargs)


def parse_extended_critic_reply(*args, **kwargs):
    from auditmanager.analysis.extended.review import parse_critic_reply
    return parse_critic_reply(*args, **kwargs)


def build_extended_corrector_request(**kwargs):
    from auditmanager.analysis.extended.review import build_corrector_request
    return build_corrector_request(**kwargs)


def parse_extended_corrector_reply(*args, **kwargs):
    from auditmanager.analysis.extended.review import parse_corrector_reply
    return parse_corrector_reply(*args, **kwargs)


def extended_review_bundle_digest(section):
    from auditmanager.analysis.extended.workflow import review_bundle_digest
    return review_bundle_digest(section)


__all__.extend(["estimate_extended_visual_scope", "extended_workflow_procedures_v3",
    "build_comprehensive_request_v3", "build_extended_critic_request", "parse_extended_critic_reply",
    "build_extended_corrector_request", "parse_extended_corrector_reply", "extended_review_bundle_digest"])


# Explicit workflow-oriented spellings consumed by the v3 orchestrator.
build_critic_request = build_extended_critic_request
parse_critic_reply = parse_extended_critic_reply
build_corrector_request = build_extended_corrector_request
parse_corrector_reply = parse_extended_corrector_reply

__all__.extend(["build_critic_request", "parse_critic_reply",
                "build_corrector_request", "parse_corrector_reply"])


def build_norm_review_request_v3(**kwargs):
    from auditmanager.analysis.extended.workflow import build_norm_review_request_v3 as build
    return build(**kwargs)


def deterministic_extended_merge_v3(*args, **kwargs):
    from auditmanager.analysis.extended.workflow import deterministic_lossless_merge_v3
    return deterministic_lossless_merge_v3(*args, **kwargs)


__all__.extend(["build_norm_review_request_v3", "deterministic_extended_merge_v3"])


def build_extended_request_v3(**kwargs):
    from auditmanager.analysis.extended.core import build_request_v3
    return build_request_v3(**kwargs)


__all__.append("build_extended_request_v3")


def empty_native_text_observations(**kwargs):
    from auditmanager.analysis.text.artifact import empty_native_text_observations as empty
    return empty(**kwargs)


__all__.append("empty_native_text_observations")


def run_document_context_with_visual_pages(context, *, allow_visual_only_pages=False):
    from auditmanager.analysis.stages.document_context_build import run
    return run(context, allow_visual_only_pages=allow_visual_only_pages)


__all__.append("run_document_context_with_visual_pages")



def extended_coverage_policy():
    """Fresh source-bound allowance for durable extended-review batches."""
    from auditmanager.analysis.extended.coverage import coverage_policy
    return coverage_policy()


def validate_extended_coverage_policy(policy):
    from auditmanager.analysis.extended.coverage import validate_coverage_policy
    return validate_coverage_policy(policy)


def plan_extended_coverage(**kwargs):
    from auditmanager.analysis.extended.coverage import plan_extended_coverage as plan
    return plan(**kwargs)


__all__.extend(["extended_coverage_policy", "validate_extended_coverage_policy", "plan_extended_coverage"])


def build_comprehensive_request_batched_v3(**kwargs):
    from auditmanager.analysis.extended.workflow import build_comprehensive_request_batched_v3 as build
    return build(**kwargs)


__all__.append("build_comprehensive_request_batched_v3")


def build_norm_review_request_batched_v3(**kwargs):
    from auditmanager.analysis.extended.workflow import build_norm_review_request_batched_v3 as build
    return build(**kwargs)


def parse_norm_review_batched_v3(*args, **kwargs):
    from auditmanager.analysis.extended.workflow import parse_norm_review_batched_v3 as parse
    return parse(*args, **kwargs)


__all__.extend(["build_norm_review_request_batched_v3", "parse_norm_review_batched_v3"])


def consolidate_extended_observations(observations, *, sources, version_uid):
    from auditmanager.analysis.extended.consolidation import consolidate_observations
    return consolidate_observations(observations, sources=sources, version_uid=version_uid)


__all__.append("consolidate_extended_observations")
