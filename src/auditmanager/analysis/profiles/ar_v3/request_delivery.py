"""Pure bridge from a sealed AR v3 beta request to every model transport.

The caller must first prove Run, Attempt and retrieval-set custody, then call
``prepare_beta_v3_request`` with those saved bytes. This bridge has no I/O and
does not grant that authority. Its one output is the existing ``ModelRequest``
that HTTP, pull and SSH adapters already consume.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Mapping

from auditmanager.analysis.profiles.ar_v3.scope_partition import scope_membership
from auditmanager.analysis.profiles.ar_v3.v3_profile import (
    BetaV3ProfileRefused,
    SealedV3Request,
    resolve_beta_v3_profile,
)
from auditmanager.analysis.text.adapter import ModelRequest


class V3DeliveryRefused(ValueError):
    """The sealed material or transport generation pins are not usable."""


_MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,255}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_EFFORTS = frozenset({"low", "medium", "high", "max"})


@dataclass(frozen=True, slots=True)
class V3GenerationSettings:
    """Explicit provider settings; neither the v1 bundle nor a transport picks them."""

    max_output_tokens: int
    effort: str
    thinking: Mapping[str, str]

    def __post_init__(self) -> None:
        if (type(self.max_output_tokens) is not int
                or not 1 <= self.max_output_tokens <= 64_000
                or not isinstance(self.effort, str)
                or self.effort not in _EFFORTS
                or not isinstance(self.thinking, Mapping)
                or dict(self.thinking) != {"type": "adaptive"}):
            raise V3DeliveryRefused("v3_generation_settings_invalid")


def _checked_seal(sealed: SealedV3Request) -> dict[str, object]:
    if not isinstance(sealed, SealedV3Request):
        raise V3DeliveryRefused("v3_sealed_request_required")
    try:
        profile = resolve_beta_v3_profile(
            sealed.profile.analysis_profile_id, sealed.profile.prompt_bundle_id
        )
        candidate = sealed.candidate
        membership = scope_membership(candidate.scope_id)
    except (AttributeError, BetaV3ProfileRefused, ValueError) as exc:
        raise V3DeliveryRefused("v3_profile_or_scope_invalid") from exc
    if (sealed.profile != profile
            or candidate.system_prompt != profile.system_prompt
            or candidate.response_schema_json != profile.response_schema_json
            or candidate.norms_snapshot_id != profile.snapshot_id
            or candidate.composition_sha256 != profile.composition_sha256
            or candidate.scope_id not in profile.scopes
            or candidate.item_ids != membership.item_ids
            or not isinstance(candidate.user_prompt, str)
            or not candidate.user_prompt
            or not isinstance(candidate.version_uid, str)
            or not candidate.version_uid
            or any(not isinstance(value, str) or _SHA256.fullmatch(value) is None for value in (
                candidate.request_sha256, candidate.map_sha256, candidate.set_sha256,
            ))):
        raise V3DeliveryRefused("v3_sealed_candidate_invalid")
    expected = {
        "format": "ar-v3-beta-request/1",
        "analysis_profile_id": str(profile.analysis_profile_id),
        "prompt_bundle_id": str(profile.prompt_bundle_id),
        "profile_content_sha256": profile.content_sha256,
        "bundle_sha256": profile.bundle_sha256,
        "request_sha256": candidate.request_sha256,
        "scope_id": candidate.scope_id,
        "item_ids": list(candidate.item_ids),
        "composition_sha256": candidate.composition_sha256,
        "version_uid": candidate.version_uid,
        "norms_snapshot_id": candidate.norms_snapshot_id,
        "map_sha256": candidate.map_sha256,
        "set_sha256": candidate.set_sha256,
        "system_prompt": candidate.system_prompt,
        "user_prompt": candidate.user_prompt,
        "response_schema_json": candidate.response_schema_json,
    }
    canonical = json.dumps(
        expected, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    if (sealed.material_json != canonical
            or hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            != sealed.material_sha256):
        raise V3DeliveryRefused("v3_material_seal_invalid")
    try:
        schema = json.loads(candidate.response_schema_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise V3DeliveryRefused("v3_response_schema_invalid") from exc
    if not isinstance(schema, dict):
        raise V3DeliveryRefused("v3_response_schema_invalid")
    return schema


def build_v3_model_request(
    sealed: SealedV3Request,
    *,
    model_identity: str,
    settings: V3GenerationSettings,
    idempotency_scope: str | None = None,
) -> ModelRequest:
    """Return the one provider body and checksum for an already sealed scope.

    ``candidate.request_sha256`` binds the draft prompt/set identities;
    ``ModelRequest.request_sha256`` binds the exact provider body including
    model and generation settings. The future executor must record both.
    """
    schema = _checked_seal(sealed)
    if (not isinstance(model_identity, str)
            or _MODEL_ID.fullmatch(model_identity) is None
            or model_identity.lower() in {"stub", "placeholder", "unknown"}):
        raise V3DeliveryRefused("v3_model_identity_invalid")
    if not isinstance(settings, V3GenerationSettings):
        raise V3DeliveryRefused("v3_generation_settings_required")
    V3GenerationSettings(settings.max_output_tokens, settings.effort, settings.thinking)
    if idempotency_scope is not None and (
        not isinstance(idempotency_scope, str) or not idempotency_scope
    ):
        raise V3DeliveryRefused("v3_idempotency_scope_invalid")
    body = {
        "model": model_identity,
        "max_tokens": settings.max_output_tokens,
        "system": sealed.candidate.system_prompt,
        "messages": [{"role": "user", "content": sealed.candidate.user_prompt}],
        "thinking": dict(settings.thinking),
        "output_config": {
            "effort": settings.effort,
            "format": {"type": "json_schema", "schema": schema},
        },
    }
    return ModelRequest(
        model_id=model_identity, body=body, idempotency_scope=idempotency_scope
    )


__all__ = ["V3DeliveryRefused", "V3GenerationSettings", "build_v3_model_request"]
