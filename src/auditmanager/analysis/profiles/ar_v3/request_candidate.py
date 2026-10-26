"""Pure, unserved AR v3 request candidate from pinned input identities.

The caller must first prove Run/Attempt authority and retrieval-set Blob custody.
This module checks supplied bytes against those expected identities, but cannot
establish their provenance. It does not choose a model, output cap or verdict.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Final

from auditmanager.analysis.profiles.ar_shared.recognised_context import RecognisedContext
from auditmanager.analysis.profiles.ar_v3.prompt_material import (
    V3PromptRefused,
    prepare_v3_prompt,
)
from auditmanager.analysis.profiles.ar_v3.response_schema import response_schema
from auditmanager.analysis.profiles.ar_v3.scope_partition import (
    ScopePartitionRefused,
    scope_membership,
)
from auditmanager.analysis.profiles.ar_v3.set_input import (
    V3SetInputRefused,
    parse_v3_set_input,
)
from auditmanager.analysis.text.textlayer import TextLayer


REQUEST_FORMAT_VERSION: Final[str] = "ar-v3-request-prep-v1"
SCOPED_REQUEST_FORMAT_VERSION: Final[str] = "ar-v3-scoped-request-prep-v1"


class V3RequestRefused(ValueError):
    """Supplied identities or material cannot form a v3 request candidate."""


@dataclass(frozen=True, slots=True)
class V3RequestCandidate:
    """Provider-facing material plus a local digest, without grounding corpus text.

    ``request_sha256`` fingerprints this draft and its supplied identities. It is
    neither a Run fingerprint nor evidence of reviewed prompt/profile authority.
    """

    version_uid: str
    norms_snapshot_id: str
    map_sha256: str
    set_sha256: str
    system_prompt: str
    user_prompt: str
    response_schema_json: str
    selected_label_count: int
    request_sha256: str
    scope_id: str | None = None
    composition_sha256: str | None = None
    item_ids: tuple[str, ...] = ()


def _canonical(value: dict[str, object]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def prepare_v3_request_candidate(
    text_layer: TextLayer,
    set_bytes: bytes,
    *,
    expected_version_uid: str,
    expected_set_sha256: str,
    expected_snapshot_id: str,
    expected_map_sha256: str,
    recognised_context: tuple[RecognisedContext, ...] = (),
    scope_id: str | None = None,
    expected_composition_sha256: str | None = None,
) -> V3RequestCandidate:
    """Bind an exact PDF version and supplied set bytes to draft request material.

    Only the selected prompt part crosses into ``user_prompt``. Full rebinding
    paragraphs remain in the supplied set and must be parsed again by the later
    local grounding gate; they are deliberately absent from this return value.
    """
    if (not isinstance(text_layer, TextLayer)
            or not isinstance(expected_version_uid, str)
            or not expected_version_uid
            or text_layer.version_uid != expected_version_uid):
        raise V3RequestRefused("version_uid_mismatch")
    if (scope_id is None) != (expected_composition_sha256 is None):
        raise V3RequestRefused("scope_identity_incomplete")
    try:
        set_input = parse_v3_set_input(
            set_bytes, expected_sha256=expected_set_sha256,
            expected_snapshot_id=expected_snapshot_id,
            expected_map_sha256=expected_map_sha256,
        )
        membership = scope_membership(scope_id) if scope_id is not None else None
        if membership is not None and (
            expected_composition_sha256 != membership.composition_sha256
            or set_input.selected_item_ids != membership.item_ids
        ):
            raise V3RequestRefused("scope_set_item_mismatch")
        prompt = prepare_v3_prompt(
            text_layer, set_input, recognised_context=recognised_context,
        )
    except (V3SetInputRefused, V3PromptRefused, ScopePartitionRefused) as exc:
        raise V3RequestRefused(str(exc)) from exc

    schema_json = _canonical(response_schema()).decode("utf-8")
    selected_label_count = len(set_input.label_bindings)
    digest_input = {
        "format_version": (
            SCOPED_REQUEST_FORMAT_VERSION if membership is not None
            else REQUEST_FORMAT_VERSION
        ),
        "version_uid": expected_version_uid,
        "norms_snapshot_id": expected_snapshot_id,
        "map_sha256": expected_map_sha256,
        "set_sha256": expected_set_sha256,
        "system_prompt": prompt.system,
        "user_prompt": prompt.user,
        "response_schema_json": schema_json,
        "selected_label_count": selected_label_count,
    }
    if membership is not None:
        digest_input.update({
            "scope_id": membership.scope_id,
            "composition_sha256": membership.composition_sha256,
            "item_ids": membership.item_ids,
        })
    return V3RequestCandidate(
        version_uid=expected_version_uid,
        norms_snapshot_id=expected_snapshot_id,
        map_sha256=expected_map_sha256,
        set_sha256=expected_set_sha256,
        system_prompt=prompt.system,
        user_prompt=prompt.user,
        response_schema_json=schema_json,
        selected_label_count=selected_label_count,
        request_sha256=hashlib.sha256(_canonical(digest_input)).hexdigest(),
        scope_id=membership.scope_id if membership is not None else None,
        composition_sha256=(
            membership.composition_sha256 if membership is not None else None
        ),
        item_ids=membership.item_ids if membership is not None else (),
    )


def prepare_v3_scoped_request_candidate(
    text_layer: TextLayer,
    set_bytes: bytes,
    *,
    expected_version_uid: str,
    expected_set_sha256: str,
    expected_snapshot_id: str,
    expected_map_sha256: str,
    scope_id: str,
    expected_composition_sha256: str,
    recognised_context: tuple[RecognisedContext, ...] = (),
) -> V3RequestCandidate:
    """Require an exact scope and set-prompt item sequence before prompt material.

    The caller must prove the expected set/map identities came from a pinned,
    custody-checked source; this pure candidate cannot grant that authority.
    """
    return prepare_v3_request_candidate(
        text_layer, set_bytes,
        expected_version_uid=expected_version_uid,
        expected_set_sha256=expected_set_sha256,
        expected_snapshot_id=expected_snapshot_id,
        expected_map_sha256=expected_map_sha256,
        recognised_context=recognised_context,
        scope_id=scope_id,
        expected_composition_sha256=expected_composition_sha256,
    )


__all__ = [
    "REQUEST_FORMAT_VERSION", "SCOPED_REQUEST_FORMAT_VERSION",
    "V3RequestCandidate", "V3RequestRefused", "prepare_v3_request_candidate",
    "prepare_v3_scoped_request_candidate",
]
