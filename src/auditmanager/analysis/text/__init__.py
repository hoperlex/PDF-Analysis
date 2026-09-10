"""``text_analysis`` - the one visible AI stage of PC-01.

It answers exactly one product question, from ``PROTOTYPE_PROFILE.md`` section 7.1:

    Does the text state conflicting values or claims about the same project attribute
    in different places, or leave an explicit placeholder that requires expert
    attention?

Two categories, ``internal_contradiction`` and ``explicit_placeholder``, and no third.
The stage does not decide compliance with external norms, does not infer facts from
drawings, and does not claim that a missing statement was legally required. **The
model never writes a verdict**: it proposes observations that a human accepts or
rejects.

Where to look:

* :mod:`.prompt` and :mod:`.profile` - the immutable prompt bundle and analysis
  profile, content-hashed and resolved by identity.
* :mod:`.anchors` and :mod:`.textlayer` - the offset rule. One document-global
  sequence, no separator between pages, Unicode code points, one declared
  normalization applied once by ``B2`` and never again here.
* :mod:`.adapter`, :mod:`.live`, :mod:`.recorded` - the two adapters and the request
  checksum that keys a recording.
* :mod:`.provenance` and :mod:`.config` - why a recorded run cannot be presented as a
  live one.
* :mod:`.cost` - the ``OD-03`` per-run ceiling and its ``cost_budget_exceeded`` halt.
* :mod:`.stage` - the entry point, ``run_text_analysis``.
"""

from __future__ import annotations

from auditmanager.analysis.text.adapter import (
    PROVIDER,
    ModelAdapter,
    ModelRequest,
    ModelResponse,
    build_request,
)
from auditmanager.analysis.text.anchors import BlockIndex, ResolvedAnchor, UnresolvedAnchor
from auditmanager.analysis.text.artifact import (
    ARTIFACT_ROLE,
    ARTIFACT_VERSION,
    Observation,
    build_text_observations,
)
from auditmanager.analysis.text.config import (
    DEFAULT_RUN_COST_CEILING_USD,
    DEPENDENCY_NAME,
    ENV_API_KEY,
    ENV_COST_CEILING,
    ENV_MODEL_ID,
    ENV_PROVIDER_MODE,
    ProviderConfig,
    ProviderMode,
    load_provider_config,
)
from auditmanager.analysis.text.cost import CostMeter
from auditmanager.analysis.text.live import LiveAdapter
from auditmanager.analysis.text.lock import STAGE_ID, ModelPin, ProviderLock, provider_lock
from auditmanager.analysis.text.profile import AR_TEXT_PROFILE, AnalysisProfile, resolve_profile
from auditmanager.analysis.text.prompt import AR_TEXT_PROMPT_BUNDLE, CATEGORIES, PromptBundle
from auditmanager.analysis.text.provenance import ModelCallRecord, assert_consistent_mode
from auditmanager.analysis.text.recorded import RecordedAdapter, recording_document
from auditmanager.analysis.text.stage import (
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCEEDED,
    TextAnalysisOutcome,
    run_text_analysis,
)
from auditmanager.analysis.text.textlayer import TextLayer, load_text_layer

__all__ = [
    "ARTIFACT_ROLE",
    "ARTIFACT_VERSION",
    "AR_TEXT_PROFILE",
    "AR_TEXT_PROMPT_BUNDLE",
    "CATEGORIES",
    "DEFAULT_RUN_COST_CEILING_USD",
    "DEPENDENCY_NAME",
    "ENV_API_KEY",
    "ENV_COST_CEILING",
    "ENV_MODEL_ID",
    "ENV_PROVIDER_MODE",
    "PROVIDER",
    "STAGE_ID",
    "STATUS_FAILED",
    "STATUS_PARTIAL",
    "STATUS_SUCCEEDED",
    "AnalysisProfile",
    "BlockIndex",
    "CostMeter",
    "LiveAdapter",
    "ModelAdapter",
    "ModelCallRecord",
    "ModelPin",
    "ModelRequest",
    "ModelResponse",
    "Observation",
    "PromptBundle",
    "ProviderConfig",
    "ProviderLock",
    "ProviderMode",
    "RecordedAdapter",
    "ResolvedAnchor",
    "TextAnalysisOutcome",
    "TextLayer",
    "UnresolvedAnchor",
    "assert_consistent_mode",
    "build_request",
    "build_text_observations",
    "load_provider_config",
    "load_text_layer",
    "provider_lock",
    "recording_document",
    "resolve_profile",
    "run_text_analysis",
]
