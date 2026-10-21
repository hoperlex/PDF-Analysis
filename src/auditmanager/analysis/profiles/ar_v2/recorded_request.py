"""Pure, recorded-only AR v2 request construction.

The registered descriptor binds reviewed prompt material, but it does not pin a
live model or generation settings. Those are explicit fixture inputs here.
This module cannot select a provider or read the v1 provider lock.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from auditmanager.analysis.profiles.ar_v2 import prompt_material, registered
from auditmanager.analysis.profiles.ar_v2.recognised_context import RecognisedContext
from auditmanager.analysis.recognised.flags import FLAG_ORDER
from auditmanager.analysis.text.adapter import ModelRequest
from auditmanager.analysis.text.textlayer import Page, TextLayer
from auditmanager.shared.identity import AnalysisProfileId, PromptBundleId


class RecordedRequestError(ValueError):
    """The fixture model, generation settings or supplied text are unsuitable."""


_FIXTURE_MODEL = re.compile(r"fixture/[a-z0-9][a-z0-9._-]{0,127}\Z")
_EFFORTS = frozenset({"low", "medium", "high", "max"})


@dataclass(frozen=True, slots=True)
class RecordedGenerationSettings:
    """Explicit fixture settings; no v1 bundle or provider defaults apply."""

    max_output_tokens: int
    effort: str
    thinking: Mapping[str, Any]

    def __post_init__(self) -> None:
        if type(self.max_output_tokens) is not int or self.max_output_tokens < 1:
            raise RecordedRequestError("invalid_max_output_tokens")
        if not isinstance(self.effort, str) or self.effort not in _EFFORTS:
            raise RecordedRequestError("invalid_effort")
        if not isinstance(self.thinking, Mapping) or self.thinking != {"type": "adaptive"}:
            raise RecordedRequestError("invalid_thinking")


def _validate_text_layer(text_layer: TextLayer) -> None:
    if (
        not isinstance(text_layer, TextLayer)
        or not isinstance(text_layer.version_uid, str)
        or not text_layer.version_uid
        or not isinstance(text_layer.normalization_id, str)
        or not text_layer.normalization_id
        or not isinstance(text_layer.pages, tuple)
        or not text_layer.pages
        or not isinstance(text_layer.document_text, str)
    ):
        raise RecordedRequestError("invalid_text_layer")
    position = 0
    previous_page = 0
    for page in text_layer.pages:
        if (
            not isinstance(page, Page)
            or not isinstance(page.text, str)
            or type(page.page_number) is not int
            or type(page.char_start) is not int
            or type(page.char_end) is not int
            or page.page_number != previous_page + 1
            or page.char_start != position
            or page.char_end - page.char_start != len(page.text)
        ):
            raise RecordedRequestError("invalid_text_layer")
        previous_page = page.page_number
        position = page.char_end
    if position != len(text_layer.document_text) or "".join(page.text for page in text_layer.pages) != text_layer.document_text:
        raise RecordedRequestError("invalid_text_layer")


def build_recorded_request(
    *,
    analysis_profile_id: AnalysisProfileId | str,
    prompt_bundle_id: PromptBundleId | str,
    fixture_model_id: str,
    settings: RecordedGenerationSettings,
    text_layer: TextLayer,
    recognised_context: tuple[RecognisedContext, ...] = (),
) -> ModelRequest:
    """Build one deterministic request after rechecking the recorded registration.

    The caller must pass OCR selected against the version's stored textless-page
    list. A recording is looked up separately by ``request_sha256``; this
    function never calls an adapter, writes a file or makes a model decision.
    """
    registered.resolve_recorded_profile(analysis_profile_id, prompt_bundle_id)
    if not isinstance(fixture_model_id, str) or not _FIXTURE_MODEL.fullmatch(fixture_model_id):
        raise RecordedRequestError("invalid_fixture_model_id")
    if not isinstance(settings, RecordedGenerationSettings):
        raise RecordedRequestError("invalid_generation_settings")
    RecordedGenerationSettings(
        settings.max_output_tokens, settings.effort, settings.thinking
    )
    _validate_text_layer(text_layer)
    if not isinstance(recognised_context, tuple):
        raise RecordedRequestError("invalid_recognised_context")
    previous_page = 0
    page_numbers = set(text_layer.page_numbers)
    for item in recognised_context:
        if (
            not isinstance(item, RecognisedContext)
            or type(item.page_number) is not int
            or item.page_number not in page_numbers
            or item.page_number <= previous_page
            or not isinstance(item.text, str)
            or not isinstance(item.flags, tuple)
            or any(not isinstance(flag, str) for flag in item.flags)
            or tuple(flag for flag in FLAG_ORDER if flag in item.flags) != item.flags
        ):
            raise RecordedRequestError("invalid_recognised_context")
        previous_page = item.page_number
    body: dict[str, Any] = {
        "model": fixture_model_id,
        "max_tokens": settings.max_output_tokens,
        "system": prompt_material.system_prompt(),
        "messages": [
            {"role": "user", "content": prompt_material.render_user_prompt(
                text_layer, recognised_context=recognised_context
            )},
        ],
        "thinking": dict(settings.thinking),
        "output_config": {
            "effort": settings.effort,
            "format": {"type": "json_schema", "schema": registered.response_schema()},
        },
    }
    return ModelRequest(model_id=fixture_model_id, body=body)
