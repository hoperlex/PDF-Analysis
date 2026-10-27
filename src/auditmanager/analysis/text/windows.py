"""Whole-page windows of a section run: when a run is windowed, the plan, the request, the journal key.

`SECTION-CHUNKED-ANALYSIS-01` (`G-11`, the gap report's gap 1). A volume whose recorded character count
is above the one-call budget (:func:`~auditmanager.analysis.text.budget.input_budget_characters`) used to be
refused. It is now analysed in whole-page windows, each one model call, all under the run's one cost ceiling
(:mod:`.windowed`). This module is the pure part:

* :func:`text_window_policy` decides **whether** a run is windowed. Its predicate is the old refusal's
  predicate, so a version with no recorded count, or a count not above the per-call budget, gets ``None``
  and goes the old way untouched (one call, the same request bytes, the same recordings);
* :func:`plan_text_windows` partitions the text layer the stage already loaded
  (:func:`~auditmanager.analysis.text.chunk_preflight.partition_text_layer`: whole pages, document-global
  offsets) and refuses, before any call, a plan above the window limit or a page larger than a window;
* :func:`build_window_request` renders one fragment with its **true page numbers** and a short preamble that
  tells the model it sees one fragment only; :func:`window_key` is the identity under which a finished
  window is journaled (it binds the text, the range, the profile and the request, so a changed input never
  replays an old reply);
* :class:`WindowCustody` is the seam the executor fills: it recovers a window an earlier call of this run
  finished, and preserves a fresh window's reply before the call is completed.

Nothing here touches the database, the blob store or a provider.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Final, Mapping, Protocol, Sequence

from auditmanager.analysis.text.adapter import ModelRequest, ModelResponse, build_request
from auditmanager.analysis.text.budget import MAX_ANALYSIS_WINDOWS, input_budget_characters
from auditmanager.analysis.text.chunk_preflight import (
    ChunkPreflightError,
    TextChunk,
    partition_text_layer,
)
from auditmanager.analysis.text.lock import STAGE_ID, ProviderLock
from auditmanager.analysis.text.prompt import PAGE_BANNER, PromptBundle, canonical_json
from auditmanager.analysis.text.recognised_input import (
    NOTICE,
    RecognisedPage,
    extra_by_page,
    notice_for,
    render_block,
    validate,
)
from auditmanager.analysis.text.textlayer import Page, TextLayer
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ModelCallId

#: The version of the key's recipe. A change of the recipe is a new key space, never a reinterpretation.
WINDOW_KEY_FORMAT: Final[str] = "text-window-key/1"

#: ``model_call.parameters`` keys a finished window carries. ``jobs.repository`` reads the same literals
#: (it may not import this context); ``tests/unit/analysis/test_text_windows.py`` pins the two together.
PARAM_KEY: Final[str] = "text_window_key"
PARAM_INDEX: Final[str] = "text_window_index"
PARAM_COUNT: Final[str] = "text_window_count"
PARAM_FIRST_PAGE: Final[str] = "text_window_first_page"
PARAM_LAST_PAGE: Final[str] = "text_window_last_page"
PARAM_REPLY_BLOB_ID: Final[str] = "text_window_reply_blob_id"
PARAM_REPLY_BLOB_SHA256: Final[str] = "text_window_reply_blob_sha256"
PARAM_REPLY_BLOB_SIZE: Final[str] = "text_window_reply_blob_size"

#: What the model is told about its fragment. It is model-facing Russian like the system prompt, it lives
#: here and not in the prompt bundle (a bundle's hash is every recording's key, and the section packages are
#: not this lane's), and it is used for a multi-window run only. The last sentence is the same rule as the
#: system prompt's fifth condition, said for the case this module creates: a disagreement with a page the
#: model cannot see is not a finding.
WINDOW_PREAMBLE: Final[str] = (
    "Текстовый слой документа, фрагмент {index} из {count}: страницы {first}–{last} из {total}. "
    "Номера страниц в заголовках — номера страниц всего документа. Проанализируй только этот "
    "фрагмент и ответь по схеме. Других страниц документа у тебя нет: расхождение со страницей, "
    "которой ты не видишь, находкой не является."
)

#: Stored on the text stage's metrics for a windowed run (scalars only, the contract's schema). The model is
#: told the same thing in :data:`WINDOW_PREAMBLE`.
WINDOWS_NOTE: Final[str] = (
    "Страницы разбиты на окна; каждое окно проверено отдельно, поэтому расхождение между "
    "страницами разных окон не выявляется."
)


@dataclass(frozen=True, slots=True)
class WindowPolicy:
    """A run that is windowed: the most characters one window carries and the most windows a run takes."""

    window_characters: int
    max_windows: int

    def __post_init__(self) -> None:
        if type(self.window_characters) is not int or self.window_characters < 0:
            raise ValueError("window_characters must be a non-negative whole number")
        if type(self.max_windows) is not int or self.max_windows < 2:
            raise ValueError("a windowed policy takes at least two windows")


def text_window_policy(
    *,
    text_character_count: int | None,
    model_id: str,
    ceiling_usd: float,
    lock: ProviderLock | None = None,
    max_windows: int = MAX_ANALYSIS_WINDOWS,
    recognised_characters: int = 0,
) -> WindowPolicy | None:
    """The policy for a run, or ``None`` when the run is analysed in one call exactly as before.

    ``None`` for a version with no recorded count (published before the bundle upload, never refused by
    the budget and never windowed), for a count not above the per-call budget (strictly above is the old
    refusal's predicate), and for ``max_windows == 1`` (the rollback). An unpinned ``model_id`` raises the
    same ``model_not_pinned`` the stage would raise at its own pin lookup.

    ``recognised_characters`` (`SECTION-CATEGORY-OCR-01`) is what the recognised-text blocks add to a one-call
    user message (:func:`~auditmanager.analysis.text.recognised_input.total_characters`); the version's
    recorded count does not include them, so a version just under the budget that its scans push over is
    windowed here rather than sent whole. Zero (the default) is every call that carries no block.
    """
    if text_character_count is None:
        return None
    if type(text_character_count) is not int or text_character_count < 0:
        raise ValueError("text_character_count must be a non-negative whole number or None")
    if type(max_windows) is not int or max_windows < 1:
        raise ValueError("max_windows must be a positive whole number")
    if type(recognised_characters) is not int or recognised_characters < 0:
        raise ValueError("recognised_characters must be a non-negative whole number")
    call_budget = input_budget_characters(model_id, ceiling_usd, lock=lock)
    if text_character_count + recognised_characters <= call_budget or max_windows == 1:
        return None
    return WindowPolicy(window_characters=call_budget, max_windows=max_windows)


def _refuse(reason: str, message: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID, message=message, stage_id=STAGE_ID, reason=reason
    )


@dataclass(frozen=True, slots=True)
class WindowPlan:
    """The layer, its windows in page order, and the digest of the text they partition.

    ``recognised`` (`SECTION-CATEGORY-OCR-01`) are the recognised-text blocks of the text-less pages; a
    window renders the blocks of its own pages, and the plan counted them when it packed the pages.
    """

    layer: TextLayer
    windows: tuple[TextChunk, ...]
    window_characters: int
    text_sha256: str
    recognised: tuple[RecognisedPage, ...] = ()

    def pages_of(self, window: TextChunk) -> tuple[Page, ...]:
        return self.layer.pages[window.first_page - 1 : window.last_page]


def plan_text_windows(
    layer: TextLayer, policy: WindowPolicy, recognised: Sequence[RecognisedPage] = ()
) -> WindowPlan:
    """Partition ``layer`` into whole-page windows, or refuse before any call is made.

    Refusals are ``analysis_input_invalid`` (the code a stage may store; ``analysis_input_budget_exceeded``
    is a pre-run answer and is never stored) with a ``reason``: ``window_plan_over_limit`` when the plan has
    more than ``policy.max_windows`` windows (both figures are in the message), ``window_page_exceeds_limit``
    when one page alone is larger than a window (splitting a page needs a separately reviewed citation rule),
    ``window_ceiling_unusable`` and ``window_text_layer_invalid`` for the two states the primitive refuses.

    ``recognised`` blocks weigh into the pages they stand under, and the one notice a window's preamble
    gains is reserved from the ceiling; a window therefore stays within ``policy.window_characters``
    *with* its recognised text.
    """
    validate(layer, recognised)  # a handed page the layer lacks is refused here, before any call
    ceiling = policy.window_characters - ((len(NOTICE) + 1) if recognised else 0)
    try:
        windows = partition_text_layer(
            layer, max_chunk_characters=ceiling, page_extra=extra_by_page(recognised)
        )
    except ChunkPreflightError as exc:
        if exc.reason == "page_exceeds_limit":
            raise _refuse(
                "window_page_exceeds_limit",
                f"page {exc.page_number} alone is larger than the {policy.window_characters}-character "
                "window; a page is never split",
            ) from exc
        if exc.reason == "invalid_max_chunk_characters":
            raise _refuse(
                "window_ceiling_unusable",
                "the per-call budget leaves no room for a window of text",
            ) from exc
        raise _refuse(
            "window_text_layer_invalid", "the text layer cannot be partitioned into windows"
        ) from exc
    if len(windows) > policy.max_windows:
        raise _refuse(
            "window_plan_over_limit",
            f"the text layer needs {len(windows)} windows of at most {policy.window_characters} "
            f"characters and a run takes at most {policy.max_windows}",
        )
    return WindowPlan(
        layer=layer,
        windows=windows,
        window_characters=policy.window_characters,
        text_sha256=hashlib.sha256(layer.document_text.encode("utf-8")).hexdigest(),
        recognised=tuple(recognised),
    )


def render_window(plan: WindowPlan, window: TextChunk) -> str:
    """One fragment as the model sees it: the preamble, then every page with its banner.

    The page loop is :func:`~auditmanager.analysis.text.prompt.render_document`'s, so a page reads the same in
    a window as in the whole; only the preamble differs, and the banners carry the document's own page numbers.
    A text-less page of the window carries its recognised-text block, and the preamble the one notice, exactly
    as in the whole; a window with no such page renders as it always did.
    """
    pages = plan.pages_of(window)
    blocks = {
        item.page_number: item
        for item in plan.recognised
        if window.first_page <= item.page_number <= window.last_page
    }
    parts = [
        WINDOW_PREAMBLE.format(
            index=window.index + 1,
            count=len(plan.windows),
            first=window.first_page,
            last=window.last_page,
            total=len(plan.layer.pages),
        )
        + notice_for(tuple(blocks.values())),
        "",
    ]
    for page in pages:
        parts.append(PAGE_BANNER.format(page_number=page.page_number))
        parts.append(page.text)
        block = blocks.get(page.page_number)
        if block is not None:
            parts.append(render_block(block))
        parts.append("")
    return "\n".join(parts)


def build_window_request(
    *,
    model_id: str,
    bundle: PromptBundle,
    plan: WindowPlan,
    window: TextChunk,
    idempotency_scope: str | None = None,
) -> ModelRequest:
    """The request for one window: the run's body with the fragment as the user message.

    Everything but the user message is :func:`~auditmanager.analysis.text.adapter.build_request`'s, so the
    system prompt, schema, thinking and output ceiling are the section's own and the checksum moves with
    the fragment, the model and the prompt.
    """
    return build_request(
        model_id=model_id,
        bundle=bundle,
        text_layer=plan.layer,
        idempotency_scope=idempotency_scope,
        user_content=render_window(plan, window),
    )


def window_key(
    *,
    plan: WindowPlan,
    window: TextChunk,
    profile_sha256: str,
    model_id: str,
    request_sha256: str,
) -> str:
    """The identity of a finished window: what a restart looks up.

    Binds the digest of the text layer, the window's index, count and page and character range, the
    profile (and with it the prompt bundle), the model and the request checksum. Any of them moving makes
    a different key, so a changed text, range, prompt or model never replays an old reply.
    """
    payload: dict[str, Any] = {
        "format": WINDOW_KEY_FORMAT,
        "text_layer_sha256": plan.text_sha256,
        "version_uid": plan.layer.version_uid,
        "normalization_id": plan.layer.normalization_id,
        "window_index": window.index,
        "window_count": len(plan.windows),
        "first_page": window.first_page,
        "last_page": window.last_page,
        "char_start": window.char_start,
        "char_end": window.char_end,
        "profile_sha256": profile_sha256,
        "model_id": model_id,
        "request_sha256": request_sha256,
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class WindowIdentity:
    """A window as the ``model_call`` row names it."""

    key: str
    index: int
    count: int
    first_page: int
    last_page: int

    def as_parameters(self) -> dict[str, Any]:
        return {
            PARAM_KEY: self.key,
            PARAM_INDEX: self.index,
            PARAM_COUNT: self.count,
            PARAM_FIRST_PAGE: self.first_page,
            PARAM_LAST_PAGE: self.last_page,
        }


@dataclass(frozen=True, slots=True)
class RecoveredWindow:
    """A window an earlier call of this run finished: its call and its saved, verified reply."""

    model_call_id: ModelCallId
    response: ModelResponse


class WindowCustody(Protocol):
    """What the executor supplies so that a finished window survives a restart.

    ``recover`` answers a window key with the saved reply of the finished call that carries it, or
    ``None``; it refuses (``DomainError``) a call whose evidence does not agree with itself, and never
    guesses. ``preserve`` writes a fresh window's reply durably, **after** the provider answer is journaled
    and **before** the call is completed, and returns the extra ``model_call.parameters`` that make the
    reply findable again.
    """

    def recover(self, key: str) -> RecoveredWindow | None: ...

    def preserve(
        self,
        *,
        model_call_id: ModelCallId,
        window: WindowIdentity,
        request: ModelRequest,
        response: ModelResponse,
    ) -> Mapping[str, Any]: ...


__all__ = [
    "PARAM_COUNT",
    "PARAM_FIRST_PAGE",
    "PARAM_INDEX",
    "PARAM_KEY",
    "PARAM_LAST_PAGE",
    "PARAM_REPLY_BLOB_ID",
    "PARAM_REPLY_BLOB_SHA256",
    "PARAM_REPLY_BLOB_SIZE",
    "RecoveredWindow",
    "WINDOWS_NOTE",
    "WINDOW_KEY_FORMAT",
    "WINDOW_PREAMBLE",
    "WindowCustody",
    "WindowIdentity",
    "WindowPlan",
    "WindowPolicy",
    "build_window_request",
    "plan_text_windows",
    "render_window",
    "text_window_policy",
    "window_key",
]
