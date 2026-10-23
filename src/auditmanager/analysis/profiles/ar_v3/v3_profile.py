"""Immutable, unserved AR v3 beta profile and scoped request material.

The caller must prove Run/Attempt authority and retrieval-set Blob custody.
This seal verifies its own prompt/policy bytes and the supplied set identity;
it does not approve a norm, choose a provider or publish a finding.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Final

from auditmanager.analysis.profiles.ar_v2.content import (
    ProfileContentError,
    reviewed_content_sha256,
)
from auditmanager.analysis.profiles.ar_v2.registered import (
    PROFILE_ID as V2_PROFILE_ID,
    PROMPT_BUNDLE_ID as V2_BUNDLE_ID,
)
from auditmanager.analysis.profiles.ar_v2.recognised_context import RecognisedContext
from auditmanager.analysis.profiles.ar_v3.norm_map.beta_sources import (
    BetaSourcePolicyRefused,
    COMPOSITION_SHA256,
    POLICY_SHA256,
    SCENARIO,
    SNAPSHOT_ID,
    load_beta_source_policy,
)
from auditmanager.analysis.profiles.ar_v3.prompt_material import (
    V3PromptRefused,
    render_v3_system_prompt,
)
from auditmanager.analysis.profiles.ar_v3.request_candidate import (
    SCOPED_REQUEST_FORMAT_VERSION,
    V3RequestCandidate,
    V3RequestRefused,
    prepare_v3_scoped_request_candidate,
)
from auditmanager.analysis.profiles.ar_v3.response_schema import response_schema
from auditmanager.analysis.profiles.ar_v3.scope_partition import scope_membership
from auditmanager.analysis.text.profile import ANALYSIS_PROFILE_ID as V1_PROFILE_ID
from auditmanager.analysis.text.prompt import PROMPT_BUNDLE_ID as V1_BUNDLE_ID
from auditmanager.analysis.text.textlayer import TextLayer
from auditmanager.shared.identity import AnalysisProfileId, PromptBundleId


class BetaV3ProfileRefused(ValueError):
    """The profile identity, sealed material or scoped input is not exact."""


PROFILE_ID: Final[AnalysisProfileId] = AnalysisProfileId.parse(
    "ap_01M5M28ZCDD8VPSP1BTAEW92YE"
)
PROMPT_BUNDLE_ID: Final[PromptBundleId] = PromptBundleId.parse(
    "pb_01M5M28ZCDVCR37BX1884JGSPM"
)
PROFILE_VERSION: Final[str] = "3.0.0-beta.1"
SCOPES: Final[tuple[str, ...]] = ("F1", "F2", "A1", "A2", "S1", "S2")
ORIGINAL_TOPICS_SHA256: Final[str] = (
    "df2ee31f57d52a3c597cc8b56713da1a4f6af08c3bf420cf6e3129a8b678a477"
)
REVIEWED_CONTENT_SHA256: Final[str] = (
    "0b560e485a07f96af511e3879740d1db0a0fc3f15fc013ab63507d609e3870ee"
)
SYSTEM_PROMPT_SHA256: Final[str] = (
    "ef19193e2eddbf5236d754888bbd3346286900c9beed5e51c30bc3f22d617ac7"
)
RESPONSE_SCHEMA_SHA256: Final[str] = (
    "38b963621f219f6c6518e319c03cbc0085345e163e8c83665a7349017bc33ae5"
)
BUNDLE_CONTENT_SHA256: Final[str] = (
    "d979b2e2a025d4f353cc002d3332778e26d45848f53d8865f2c607ca116a4bbd"
)
PROFILE_CONTENT_SHA256: Final[str] = (
    "0ddec73897c39882f1405f82115195c96983a6b365245f22c28e30ca5a843e08"
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _bundle_digest(system_prompt: str, schema_json: str) -> str:
    return _digest({
        "format": "ar-v3-beta-bundle/1",
        "prompt_bundle_id": str(PROMPT_BUNDLE_ID),
        "profile_version": PROFILE_VERSION,
        "scenario": SCENARIO,
        "snapshot_id": SNAPSHOT_ID,
        "policy_sha256": POLICY_SHA256,
        "composition_sha256": COMPOSITION_SHA256,
        "scopes": [
            {"scope_id": scope, "item_ids": scope_membership(scope).item_ids}
            for scope in SCOPES
        ],
        "request_format": SCOPED_REQUEST_FORMAT_VERSION,
        "original_topics_sha256": ORIGINAL_TOPICS_SHA256,
        "reviewed_content_sha256": REVIEWED_CONTENT_SHA256,
        "system_prompt": system_prompt,
        "response_schema_json": schema_json,
    })


def _profile_digest(bundle_sha256: str) -> str:
    return _digest({
        "format": "ar-v3-beta-profile/1",
        "analysis_profile_id": str(PROFILE_ID),
        "prompt_bundle_id": str(PROMPT_BUNDLE_ID),
        "profile_version": PROFILE_VERSION,
        "bundle_sha256": bundle_sha256,
    })


@dataclass(frozen=True, slots=True)
class BetaV3Profile:
    analysis_profile_id: AnalysisProfileId
    prompt_bundle_id: PromptBundleId
    profile_version: str
    content_sha256: str
    bundle_sha256: str
    system_prompt: str
    response_schema_json: str
    scenario: str
    snapshot_id: str
    policy_sha256: str
    composition_sha256: str
    scopes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SealedV3Request:
    profile: BetaV3Profile
    candidate: V3RequestCandidate
    material_json: str
    material_sha256: str


def resolve_beta_v3_profile(
    analysis_profile_id: AnalysisProfileId | str,
    prompt_bundle_id: PromptBundleId | str,
) -> BetaV3Profile:
    """Resolve only this identity pair after checking current source bytes."""
    if (str(analysis_profile_id) != str(PROFILE_ID)
            or str(prompt_bundle_id) != str(PROMPT_BUNDLE_ID)):
        raise BetaV3ProfileRefused("v3_profile_identity_unknown")
    if (str(PROFILE_ID) in {str(V1_PROFILE_ID), str(V2_PROFILE_ID)}
            or str(PROMPT_BUNDLE_ID) in {str(V1_BUNDLE_ID), str(V2_BUNDLE_ID)}):
        raise BetaV3ProfileRefused("v3_profile_identity_collision")
    try:
        policy = load_beta_source_policy()
        system_prompt = render_v3_system_prompt()
        reviewed_digest = reviewed_content_sha256()
        schema_json = _canonical(response_schema()).decode("utf-8")
    except (BetaSourcePolicyRefused, V3PromptRefused, ProfileContentError) as exc:
        raise BetaV3ProfileRefused("v3_profile_source_invalid") from exc
    if (policy.sha256 != POLICY_SHA256 or policy.scenario != SCENARIO
            or policy.snapshot_id != SNAPSHOT_ID
            or policy.composition_sha256 != COMPOSITION_SHA256
            or reviewed_digest != REVIEWED_CONTENT_SHA256
            or any(scope_membership(scope).composition_sha256 != COMPOSITION_SHA256
                   for scope in SCOPES)
            or hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()
            != SYSTEM_PROMPT_SHA256
            or hashlib.sha256(schema_json.encode("utf-8")).hexdigest()
            != RESPONSE_SCHEMA_SHA256):
        raise BetaV3ProfileRefused("v3_profile_material_changed")
    bundle_digest = _bundle_digest(system_prompt, schema_json)
    if (bundle_digest != BUNDLE_CONTENT_SHA256
            or _profile_digest(bundle_digest) != PROFILE_CONTENT_SHA256):
        raise BetaV3ProfileRefused("v3_profile_digest_changed")
    return BetaV3Profile(
        analysis_profile_id=PROFILE_ID,
        prompt_bundle_id=PROMPT_BUNDLE_ID,
        profile_version=PROFILE_VERSION,
        content_sha256=PROFILE_CONTENT_SHA256,
        bundle_sha256=BUNDLE_CONTENT_SHA256,
        system_prompt=system_prompt,
        response_schema_json=schema_json,
        scenario=SCENARIO,
        snapshot_id=SNAPSHOT_ID,
        policy_sha256=POLICY_SHA256,
        composition_sha256=COMPOSITION_SHA256,
        scopes=SCOPES,
    )


def prepare_beta_v3_request(
    text_layer: TextLayer,
    set_bytes: bytes,
    *,
    analysis_profile_id: AnalysisProfileId | str,
    prompt_bundle_id: PromptBundleId | str,
    expected_version_uid: str,
    expected_set_sha256: str,
    expected_snapshot_id: str,
    expected_map_sha256: str,
    scope_id: str,
    expected_composition_sha256: str,
    recognised_context: tuple[RecognisedContext, ...] = (),
) -> SealedV3Request:
    """Build exact scoped model material from independently trusted pins."""
    profile = resolve_beta_v3_profile(analysis_profile_id, prompt_bundle_id)
    if (expected_snapshot_id != profile.snapshot_id
            or expected_composition_sha256 != profile.composition_sha256
            or scope_id not in profile.scopes):
        raise BetaV3ProfileRefused("v3_profile_scope_or_snapshot_mismatch")
    try:
        candidate = prepare_v3_scoped_request_candidate(
            text_layer, set_bytes,
            expected_version_uid=expected_version_uid,
            expected_set_sha256=expected_set_sha256,
            expected_snapshot_id=expected_snapshot_id,
            expected_map_sha256=expected_map_sha256,
            scope_id=scope_id,
            expected_composition_sha256=expected_composition_sha256,
            recognised_context=recognised_context,
        )
    except V3RequestRefused as exc:
        raise BetaV3ProfileRefused(str(exc)) from exc
    if (candidate.system_prompt != profile.system_prompt
            or candidate.response_schema_json != profile.response_schema_json
            or candidate.scope_id != scope_id
            or candidate.composition_sha256 != profile.composition_sha256):
        raise BetaV3ProfileRefused("v3_profile_request_material_mismatch")
    material = _canonical({
        "format": "ar-v3-beta-request/1",
        "analysis_profile_id": str(profile.analysis_profile_id),
        "prompt_bundle_id": str(profile.prompt_bundle_id),
        "profile_content_sha256": profile.content_sha256,
        "bundle_sha256": profile.bundle_sha256,
        "request_sha256": candidate.request_sha256,
        "scope_id": scope_id,
        "item_ids": candidate.item_ids,
        "composition_sha256": candidate.composition_sha256,
        "version_uid": candidate.version_uid,
        "norms_snapshot_id": candidate.norms_snapshot_id,
        "map_sha256": candidate.map_sha256,
        "set_sha256": candidate.set_sha256,
        "system_prompt": candidate.system_prompt,
        "user_prompt": candidate.user_prompt,
        "response_schema_json": candidate.response_schema_json,
    })
    return SealedV3Request(
        profile=profile,
        candidate=candidate,
        material_json=material.decode("utf-8"),
        material_sha256=hashlib.sha256(material).hexdigest(),
    )


__all__ = [
    "BUNDLE_CONTENT_SHA256", "PROFILE_CONTENT_SHA256", "PROFILE_ID",
    "PROMPT_BUNDLE_ID", "BetaV3Profile", "BetaV3ProfileRefused",
    "SealedV3Request", "prepare_beta_v3_request", "resolve_beta_v3_profile",
]
