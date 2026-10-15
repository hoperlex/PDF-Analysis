"""Immutable, recorded-only AR v2 profile registration.

This descriptor binds reviewed request material to opaque identities. Resolving
it verifies the current bytes; it does not select a model or activate a run.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Final

from auditmanager.analysis.profiles.ar_v2.content import reviewed_content_sha256
from auditmanager.analysis.profiles.ar_v2.prompt_material import material_sha256
from auditmanager.analysis.profiles.ar_v2.response_schema import CATEGORIES, response_schema
from auditmanager.shared.identity import AnalysisProfileId, PromptBundleId


class RecordedProfileError(ValueError):
    """The requested registration or its reviewed material has changed."""


PROFILE_ID: Final[AnalysisProfileId] = AnalysisProfileId.parse(
    "ap_01K7F4N2A9R8T6V5W3X2Y1Z0QH"
)
PROMPT_BUNDLE_ID: Final[PromptBundleId] = PromptBundleId.parse(
    "pb_01K7F4N2A9R8T6V5W3X2Y1Z0QJ"
)
PROFILE_VERSION: Final[str] = "2.0.0-recorded"
PROVIDER_MODE: Final[str] = "recorded"
STAGE_PLAN: Final[tuple[str, ...]] = (
    "source_preparation",
    "page_geometry_extraction",
    "document_context_build",
    "text_analysis",
    "finding_merge",
)
REVIEWED_CONTENT_SHA256: Final[str] = (
    "0b560e485a07f96af511e3879740d1db0a0fc3f15fc013ab63507d609e3870ee"
)
SCHEMA_SHA256: Final[str] = (
    "031083983b7497852ebddad44207fa4adf59db8924a3ffc9fe705c85ac27906d"
)
MATERIAL_SHA256: Final[str] = (
    "01bee01f8c7f1c59227ff6c17398f1034f5094c9c3b8e26fc66ab5130a4ca610"
)


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class RecordedArV2Profile:
    analysis_profile_id: AnalysisProfileId
    prompt_bundle_id: PromptBundleId
    profile_version: str
    provider_mode: str
    categories: tuple[str, ...]
    stage_plan: tuple[str, ...]
    reviewed_content_sha256: str
    response_schema_sha256: str
    material_sha256: str
    content_sha256: str


def _profile_content_sha256() -> str:
    return _canonical_sha256(
        {
            "analysis_profile_id": str(PROFILE_ID),
            "prompt_bundle_id": str(PROMPT_BUNDLE_ID),
            "profile_version": PROFILE_VERSION,
            "provider_mode": PROVIDER_MODE,
            "categories": CATEGORIES,
            "stage_plan": STAGE_PLAN,
            "reviewed_content_sha256": REVIEWED_CONTENT_SHA256,
            "response_schema_sha256": SCHEMA_SHA256,
            "material_sha256": MATERIAL_SHA256,
        }
    )


PROFILE_CONTENT_SHA256: Final[str] = (
    "73cc187ef0aecd5a84d0ec98588552247382158bfd0cbe0ec3b78de55ac56647"
)


def resolve_recorded_profile(
    analysis_profile_id: AnalysisProfileId | str,
    prompt_bundle_id: PromptBundleId | str,
) -> RecordedArV2Profile:
    """Resolve exact AR v2 identities after verifying all reviewed inputs.

    The descriptor is a content-bound registration, not a model/provider pin.
    Callers must obtain these identities independently of a persisted run row.
    """
    if (
        str(analysis_profile_id) != str(PROFILE_ID)
        or str(prompt_bundle_id) != str(PROMPT_BUNDLE_ID)
    ):
        raise RecordedProfileError("AR v2 profile or bundle identity is not registered")
    if (
        reviewed_content_sha256() != REVIEWED_CONTENT_SHA256
        or _canonical_sha256(response_schema()) != SCHEMA_SHA256
        or material_sha256() != MATERIAL_SHA256
        or _profile_content_sha256() != PROFILE_CONTENT_SHA256
    ):
        raise RecordedProfileError("recorded AR v2 profile material has changed")
    return RecordedArV2Profile(
        analysis_profile_id=PROFILE_ID,
        prompt_bundle_id=PROMPT_BUNDLE_ID,
        profile_version=PROFILE_VERSION,
        provider_mode=PROVIDER_MODE,
        categories=CATEGORIES,
        stage_plan=STAGE_PLAN,
        reviewed_content_sha256=REVIEWED_CONTENT_SHA256,
        response_schema_sha256=SCHEMA_SHA256,
        material_sha256=MATERIAL_SHA256,
        content_sha256=PROFILE_CONTENT_SHA256,
    )
