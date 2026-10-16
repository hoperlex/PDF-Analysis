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

from auditmanager.analysis.profiles.ar_v2.recognised_context import RecognisedContext
from auditmanager.analysis.profiles.ar_v3.prompt_material import (
    V3PromptRefused,
    prepare_v3_prompt,
)
from auditmanager.analysis.profiles.ar_v3.response_schema import response_schema
from auditmanager.analysis.profiles.ar_v3.set_input import (
    V3SetInputRefused,
    parse_v3_set_input,
)
from auditmanager.analysis.text.textlayer import TextLayer


REQUEST_FORMAT_VERSION: Final[str] = "ar-v3-request-prep-v1"


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
    try:
        set_input = parse_v3_set_input(
            set_bytes, expected_sha256=expected_set_sha256,
            expected_snapshot_id=expected_snapshot_id,
            expected_map_sha256=expected_map_sha256,
        )
        prompt = prepare_v3_prompt(
            text_layer, set_input, recognised_context=recognised_context,
        )
    except (V3SetInputRefused, V3PromptRefused) as exc:
        raise V3RequestRefused(str(exc)) from exc

    schema_json = _canonical(response_schema()).decode("utf-8")
    selected_label_count = len(set_input.label_bindings)
    digest_input = {
        "format_version": REQUEST_FORMAT_VERSION,
        "version_uid": expected_version_uid,
        "norms_snapshot_id": expected_snapshot_id,
        "map_sha256": expected_map_sha256,
        "set_sha256": expected_set_sha256,
        "system_prompt": prompt.system,
        "user_prompt": prompt.user,
        "response_schema_json": schema_json,
        "selected_label_count": selected_label_count,
    }
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
    )


__all__ = [
    "REQUEST_FORMAT_VERSION", "V3RequestCandidate", "V3RequestRefused",
    "prepare_v3_request_candidate",
]
