"""`SECTION-CATEGORY-OCR-01` (`R-146aq`): the section run path reads the recognised text of the text-less pages only.

Two layers, no container. The loader (`runs/section_recognised_input.py`) is driven over a real
``prepared.recognised_text`` document in an in-memory blob store: it returns the recognised text of the
version's stored text-less pages and of no other page, merges the blocks of one page, and refuses an
inconsistent artifact instead of substituting an empty context. The executor's text stage
(`_run_text_analysis_stage`) is then driven over the same store with a scripted adapter: the model's request
carries the block of a text-less page and none for a page that has text, an unreadable pair fails the stage
before any call, and the window decision is handed the blocks' characters.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.public import (
    ROLE_DOCUMENT_GRAPH,
    ROLE_RECOGNISED_TEXT,
    ROLE_TEXT_LAYER,
    CostMeter,
    ModelResponse,
    ProviderConfig,
    ProviderMode,
    publish_artifact,
    recognised_total_characters,
)
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.analysis.text.recognised_input import RecognisedPage
from auditmanager.runs import executor as executor_module
from auditmanager.runs.executor import _run_text_analysis_stage, _StageOutputs
from auditmanager.runs.retry import RetryPolicy
from auditmanager.runs.section_recognised_input import load_section_recognised_pages
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import derive_blob_id

VERSION = "ver_01M2545JSD15ETSNNV904X991J"
TEXT_PAGE = "Страница с текстовым слоем: высота помещения 3,0 м, площадь 24,5 м2, этаж 2, секция А."
CONFIG = ProviderConfig(
    mode=ProviderMode.RECORDED, model_id="claude-opus-5", run_cost_ceiling_usd=5.0, api_key=None,
    ceiling_is_explicit=True,
)
PROFILE = load_text_profile_registry().entries["PS"].profile


class Store:
    """The blob store of the artifacts, in memory: ``put_blob`` and ``read`` as the stages use them."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.unreadable: set[str] = set()

    def put_blob(self, payload: bytes, *, declared_sha256: str, declared_size: int, role: str, media_type: str) -> Any:
        blob_id = str(derive_blob_id(sha256=declared_sha256, size=declared_size))
        self.objects[blob_id] = payload
        return SimpleNamespace(
            blob_id=blob_id, sha256=declared_sha256, size=declared_size, media_type=media_type
        )

    def read(self, blob_id: Any, *, verify: bool) -> bytes:
        assert verify is True
        if str(blob_id) in self.unreadable:
            raise OSError("store down")
        return self.objects[str(blob_id)]


def entry(block: str, page: int, kind: str, text: str, flags: list[str] | None = None) -> dict[str, Any]:
    if kind == "portal_description":
        return {"portal_block_id": block, "page_number": page, "kind": kind, "text": text}
    return {
        "portal_block_id": block, "page_number": page, "kind": kind, "quote_source": "recognised",
        "text": text, "flags": flags or [],
    }


def recognised_document(entries: list[dict[str, Any]], version: str = VERSION) -> dict[str, Any]:
    return {
        "artifact_role": ROLE_RECOGNISED_TEXT, "artifact_version": "1.0.0", "version_uid": version,
        "results_sha256": "a" * 64, "entries": entries,
    }


def world(entries: list[dict[str, Any]], *, version: str = VERSION, pages: tuple[str, ...] | None = None) -> tuple[Store, _StageOutputs]:
    texts = pages if pages is not None else (TEXT_PAGE, "", TEXT_PAGE)
    layer_pages, start = [], 0
    for number, text in enumerate(texts, 1):
        layer_pages.append({"page_number": number, "char_start": start, "char_end": start + len(text), "text": text})
        start += len(text)
    store = Store()
    outputs = _StageOutputs()
    for role, document in (
        (ROLE_TEXT_LAYER, {
            "artifact_role": ROLE_TEXT_LAYER, "artifact_version": "1.0.0", "version_uid": VERSION,
            "normalization": {"id": "nfc_v1", "description": "NFC"}, "total_char_count": start, "pages": layer_pages,
        }),
        (ROLE_DOCUMENT_GRAPH, {"artifact_role": ROLE_DOCUMENT_GRAPH, "artifact_version": "1.0.0", "version_uid": VERSION}),
        (ROLE_RECOGNISED_TEXT, recognised_document(entries, version)),
    ):
        reference, _ = publish_artifact(store, role, document)
        outputs.refs[role] = reference
    return store, outputs


# --- the loader --------------------------------------------------------------------------------------


def test_only_the_text_less_pages_are_read_and_a_page_with_text_is_never_in_the_context() -> None:
    store, outputs = world(
        [
            entry("blk_1", 1, "recognised_text", "Распознано на странице с текстом: не должно попасть."),
            entry("blk_2", 2, "recognised_text", "Первый блок скана", ["mixed_script"]),
            entry("blk_3", 2, "portal_description", "Описание изображения портала"),
            entry("blk_4", 2, "recognised_text", "Второй блок скана", ["mixed_script", "homoglyph"]),
            entry("blk_5", 3, "recognised_text", "Ещё одно распознавание страницы с текстом."),
        ]
    )
    pages = load_section_recognised_pages(
        blob_store=store, refs=outputs.refs, version_uid=VERSION, textless_pages=(2,)
    )
    assert pages == (
        RecognisedPage(page_number=2, text="Первый блок скана\nВторой блок скана", flags=("mixed_script", "homoglyph")),
    )
    joined = " ".join(page.text for page in pages)
    assert "не должно попасть" not in joined and "Описание изображения" not in joined


def test_no_text_less_page_means_no_context_and_the_artifact_is_not_read() -> None:
    store, outputs = world([entry("blk_1", 1, "recognised_text", "x")])
    store.unreadable.update(store.objects)  # any read would fail
    for textless in (None, ()):
        assert load_section_recognised_pages(
            blob_store=store, refs=outputs.refs, version_uid=VERSION, textless_pages=textless
        ) == ()


def test_a_blank_recognised_page_is_left_out() -> None:
    store, outputs = world([entry("blk_1", 2, "recognised_text", "  \n ", ["empty_text"])])
    assert load_section_recognised_pages(
        blob_store=store, refs=outputs.refs, version_uid=VERSION, textless_pages=(2,)
    ) == ()


@pytest.mark.parametrize(
    "case",
    ["missing_artifact", "other_version", "malformed_entry", "unordered_pages"],
)
def test_an_inconsistent_artifact_fails_explicitly_not_as_an_empty_context(case: str) -> None:
    entries = [entry("blk_1", 2, "recognised_text", "скан")]
    if case == "malformed_entry":
        entries = [{"portal_block_id": "blk_1", "page_number": 2, "kind": "recognised_text", "text": "скан"}]
    if case == "unordered_pages":
        entries = [entry("blk_1", 3, "recognised_text", "b"), entry("blk_2", 2, "recognised_text", "a")]
    store, outputs = world(entries, version="ver_01M2545JSD15ETSNNV904X991K" if case == "other_version" else VERSION)
    refs = {role: ref for role, ref in outputs.refs.items() if role != ROLE_RECOGNISED_TEXT or case != "missing_artifact"}
    with pytest.raises(DomainError) as raised:
        load_section_recognised_pages(blob_store=store, refs=refs, version_uid=VERSION, textless_pages=(2,))
    assert raised.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert raised.value.detail_fields["reason"] == "recognised_input_invalid"


def test_an_unreadable_store_is_the_readers_own_refusal() -> None:
    store, outputs = world([entry("blk_1", 2, "recognised_text", "скан")])
    store.unreadable.add(outputs.refs[ROLE_RECOGNISED_TEXT].blob_id)
    with pytest.raises(DomainError) as raised:
        load_section_recognised_pages(blob_store=store, refs=outputs.refs, version_uid=VERSION, textless_pages=(2,))
    assert raised.value.code is ErrorCode.ANALYSIS_INPUT_INVALID


# --- the executor's text stage -----------------------------------------------------------------------


class Adapter:
    provider_mode = ProviderMode.RECORDED

    def __init__(self) -> None:
        self.requests: list[Any] = []

    def complete(self, request: Any) -> ModelResponse:
        self.requests.append(request)
        return ModelResponse(
            output_text=json.dumps({"observations": []}), stop_reason="end_turn",
            input_tokens=10, output_tokens=2, latency_ms=3, reported_cost_usd=0.01,
        )


def stage(store: Store, outputs: _StageOutputs, adapter: Adapter, **extra: Any) -> Any:
    clock = lambda: datetime(2026, 10, 27, tzinfo=timezone.utc)  # noqa: E731
    return _run_text_analysis_stage(
        run_id="run_01M5YJZCQVQKMDFWT4MWCVEKQ7", version_uid=VERSION, outputs=outputs, blob_store=store,
        adapter=adapter, provider_config=CONFIG, cost_meter=CostMeter(ceiling_usd=5.0), policy=RetryPolicy(),
        sleep=lambda seconds: None, clock=clock, call_journal=None, profile=PROFILE, **extra,
    )


def test_the_text_stage_sends_the_block_of_a_text_less_page_and_none_for_a_page_with_text() -> None:
    store, outputs = world(
        [
            entry("blk_1", 1, "recognised_text", "Распознавание страницы, у которой есть текстовый слой"),
            entry("blk_2", 2, "recognised_text", "Скан: степень огнестойкости III"),
        ]
    )
    adapter = Adapter()
    result, document, _ = stage(store, outputs, adapter, textless_pages=(2,))
    assert result.status.value == "succeeded" and document is not None
    (request,) = adapter.requests
    user = request.body["messages"][0]["content"]
    assert "Распознанный текст страницы 2 (не из текстового слоя)" in user
    assert "Скан: степень огнестойкости III" in user
    assert "Распознанный текст страницы 1" not in user and "Распознавание страницы, у которой" not in user
    assert result.metrics["recognised_pages"] == 1


def test_a_version_without_text_less_pages_sends_no_block() -> None:
    store, outputs = world([entry("blk_1", 1, "recognised_text", "x")])
    adapter = Adapter()
    result, _, _ = stage(store, outputs, adapter, textless_pages=())
    assert "Распознанный текст" not in adapter.requests[0].body["messages"][0]["content"]
    assert "recognised_pages" not in result.metrics
    none_result, _, _ = stage(store, outputs, Adapter(), textless_pages=None)
    assert "recognised_pages" not in none_result.metrics


def test_an_inconsistent_pair_fails_the_stage_before_any_call() -> None:
    store, outputs = world([entry("blk_1", 2, "recognised_text", "скан")], version="ver_01M2545JSD15ETSNNV904X991K")
    adapter = Adapter()
    result, document, attempts = stage(store, outputs, adapter, textless_pages=(2,))
    assert adapter.requests == [] and document is None
    assert result.status.value == "failed"
    assert result.error is not None and result.error.code == ErrorCode.ANALYSIS_INPUT_INVALID.value
    assert attempts.attempts == 0 if hasattr(attempts, "attempts") else True


def test_the_window_decision_is_handed_the_characters_the_blocks_add(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict[str, Any]] = []
    original = executor_module.text_window_policy

    def spy(**kwargs: Any) -> Any:
        seen.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(executor_module, "text_window_policy", spy)
    store, outputs = world([entry("blk_1", 2, "recognised_text", "Скан: степень огнестойкости III")])
    stage(store, outputs, Adapter(), textless_pages=(2,), text_character_count=300)
    (kwargs,) = seen
    expected = recognised_total_characters(
        load_section_recognised_pages(blob_store=store, refs=outputs.refs, version_uid=VERSION, textless_pages=(2,))
    )
    assert expected > 0 and kwargs["recognised_characters"] == expected and kwargs["text_character_count"] == 300
    seen.clear()
    stage(store, outputs, Adapter(), textless_pages=None, text_character_count=300)
    assert seen[0]["recognised_characters"] == 0
