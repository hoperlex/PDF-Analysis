"""SECTION-JUDGE-FIXES-01: the omission check's judge findings, shown against the real stages and the executor.

``tests/unit/analysis/test_omission_judge_fixes.py`` holds the pure cases. Here the same guards are driven through
``run_text_analysis`` (one call), ``run_text_analysis_windows`` (windows) and the executor's text stage
(``_run_text_analysis_stage``, which hands the version's ``textless_pages`` and the recognised text to the stage),
with the registered AI profile and a scripted adapter. No container, no network.

* finding 1: the judge's reproduction (term named on page 1, heading on page 3, the schedule goes on on page 4
  with the term) is refused in one call and from the first of two windows; a clean continuation is published;
* finding 4: a range page the version stores as text-less, and the term in the recognised text of a searched
  page, refuse the pair; both reach the check from the executor;
* the sentence the stage appends names the pages that were searched.
"""

from __future__ import annotations

import json
import re
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
    publish_artifact,
)
from auditmanager.analysis.text import STATUS_SUCCEEDED, ProviderConfig, ProviderMode, run_text_analysis
from auditmanager.analysis.text.omission import OMISSION_REASONS, note_for
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.analysis.text.recognised_input import RecognisedPage, total_characters
from auditmanager.analysis.text.windowed import run_text_analysis_windows
from auditmanager.analysis.text.windows import WindowPolicy
from auditmanager.runs.executor import _run_text_analysis_stage, _StageOutputs
from auditmanager.runs.retry import RetryPolicy
from auditmanager.shared.identity import RunId
from auditmanager.storage.public import derive_blob_id

AI = load_text_profile_registry().entries["AI"].profile
VERSION = "ver_01M2545JSD15ETSNNV904X991J"
CONFIG = ProviderConfig(
    mode=ProviderMode.RECORDED, model_id="claude-opus-5", run_cost_ceiling_usd=5.0, api_key=None,
    ceiling_is_explicit=True,
)
BANNER = re.compile(r"=== Страница (\d+) ===")

PLAN = "План пола. Помещение 4 — санузел. Дверь Д-5 в санузел, ширина 800 мм. Отметка чистого пола 0,000."
GENERAL = "Общие данные: двери по проекту принимаются по ведомости; марки приведены ниже на листах."
HEADING = "Ведомость дверных заполнений"
SCHEDULE = f"{HEADING}\nМарка Д-1 Дверь входная, 2 шт.\nМарка Д-2 Дверь межкомнатная, 6 шт."
CONTINUATION = "Продолжение ведомости: марка Д-5 Дверь в санузел, 1 шт.; марка Д-6 Дверь в кухню, 1 шт."
CLEAN_CONTINUATION = "Продолжение ведомости: марка Д-6 Дверь в кухню, 1 шт.; марка Д-7 Дверь в коридор, 1 шт."
LONG_GENERAL = GENERAL + " Дополнительные указания к общим данным приведены в пояснительной записке. " * 3


def document(*pages: str) -> dict[str, Any]:
    out, start = [], 0
    for number, text in enumerate(pages, 1):
        out.append({"page_number": number, "char_start": start, "char_end": start + len(text), "text": text})
        start += len(text)
    return {
        "artifact_role": "prepared.text_layer", "artifact_version": "1.0.0", "version_uid": VERSION,
        "normalization": {"id": "nfc_v1", "description": "NFC"}, "total_char_count": start, "pages": out,
    }


def omission(*, first: int, last: int, heading_page: int, naming_page: int = 1) -> dict[str, Any]:
    return {
        "category": "documentation", "finding_text": "Марка Д-5 названа на плане и не найдена в ведомости.",
        "recommendation_text": "Сверить ведомость с планом.",
        "evidence": [{"page_number": naming_page, "quote": "Дверь Д-5 в санузел"}],
        "omission": {
            "term": "Д-5", "first_page": first, "last_page": last,
            "heading": {"page_number": heading_page, "quote": HEADING},
        },
    }


class Scripted:
    """Replies with ``answer(pages_of_this_call)``; keeps the requests."""

    provider_mode = ProviderMode.RECORDED

    def __init__(self, answer: Any) -> None:
        self._answer = answer
        self.requests: list[Any] = []

    def complete(self, request: Any) -> ModelResponse:
        self.requests.append(request)
        user = request.body["messages"][0]["content"]
        pages = [int(n) for n in BANNER.findall(user)]
        return ModelResponse(
            output_text=json.dumps({"observations": self._answer(pages)}, ensure_ascii=False),
            stop_reason="end_turn", input_tokens=100, output_tokens=10, latency_ms=5, reported_cost_usd=0.01,
        )


def one_call(pages: tuple[str, ...], reply: dict[str, Any], **extra: Any) -> Any:
    adapter = Scripted(lambda seen: [reply])
    outcome = run_text_analysis(
        run_id=RunId.new(), text_layer_document=document(*pages), adapter=adapter, profile=AI, config=CONFIG, **extra
    )
    assert outcome.status == STATUS_SUCCEEDED and len(adapter.requests) == 1
    return outcome


def windows(
    pages: tuple[str, ...], reply: dict[str, Any], first_window_pages: int, *, replies_on: int = 1,
    extra_weight: int = 0, **extra: Any
) -> Any:
    """Two windows: the first holds the first ``first_window_pages`` pages, the second the rest.

    The scripted model gives ``reply`` in the window that holds page ``replies_on`` and nothing in the other.
    ``extra_weight`` is what the recognised-text blocks and the notice add to the first window's weight.
    """
    ceiling = sum(len(text) for text in pages[:first_window_pages]) + extra_weight
    adapter = Scripted(lambda seen: [reply] if replies_on in seen else [])
    outcome = run_text_analysis_windows(
        run_id=RunId.new(), text_layer_document=document(*pages), adapter=adapter, profile=AI, config=CONFIG,
        policy=WindowPolicy(window_characters=ceiling, max_windows=12), **extra,
    )
    assert outcome.status == STATUS_SUCCEEDED
    assert [[int(n) for n in BANNER.findall(r.body["messages"][0]["content"])] for r in adapter.requests] == [
        list(range(1, first_window_pages + 1)), list(range(first_window_pages + 1, len(pages) + 1)),
    ], "the plan is the two windows this case describes"
    return outcome


JUDGE_PAGES = (PLAN, GENERAL, SCHEDULE, CONTINUATION)
JUDGE_REPLY = omission(first=3, last=3, heading_page=3)


def dropped(outcome: Any, reason: str) -> None:
    assert outcome.artifact["observations"] == []
    assert outcome.metrics["omissions_proposed"] == 1 and outcome.metrics["omissions_published"] == 0
    for each in OMISSION_REASONS:
        assert outcome.metrics[f"omissions_dropped_{each}"] == (1 if each == reason else 0), each


# --- finding 1 ---------------------------------------------------------------------------------------


def test_the_judges_reproduction_is_dropped_in_one_call() -> None:
    dropped(one_call(JUDGE_PAGES, JUDGE_REPLY), "term_on_other_visible_page")


def test_the_judges_reproduction_is_dropped_from_the_first_of_two_windows() -> None:
    """Pages 1 to 3 are a window that is not the last: a claim ending on page 3 says nothing of page 4."""
    dropped(windows(JUDGE_PAGES, JUDGE_REPLY, 3), "range_reaches_window_end")


def test_a_clean_continuation_is_published_and_the_sentence_names_every_page_searched() -> None:
    pages = (PLAN, GENERAL, SCHEDULE, CLEAN_CONTINUATION)
    outcome = one_call(pages, JUDGE_REPLY)
    (published,) = outcome.artifact["observations"]
    assert outcome.metrics["omissions_published"] == 1
    assert published["finding_text"].endswith(note_for("Д-5", 3, 3, others=(2, 4), naming_pages=(1,)))
    assert "на странице 3 и на остальных страницах 2, 4, которые видела модель" in published["finding_text"]
    assert [(item["page_number"], item["quote"]) for item in published["evidence"]] == [
        (1, "Дверь Д-5 в санузел"), (3, HEADING),
    ]


def test_a_claim_that_ends_before_the_window_end_is_published_over_the_pages_of_its_window() -> None:
    pages = (PLAN, GENERAL, SCHEDULE, CLEAN_CONTINUATION, CONTINUATION)  # window 1 = pages 1-4
    outcome = windows(pages, JUDGE_REPLY, 4)
    (published,) = outcome.artifact["observations"]
    assert published["finding_text"].endswith(note_for("Д-5", 3, 3, others=(2, 4), naming_pages=(1,))), (
        "the sentence names pages 2 and 4 and not page 5, which is in the other window"
    )


def test_the_last_window_may_end_on_its_last_page() -> None:
    """Pages 3-5 are the last window: naming on page 3, the schedule on 4-5, nothing after it."""
    pages = (LONG_GENERAL, LONG_GENERAL, PLAN, SCHEDULE, CLEAN_CONTINUATION)
    reply = omission(first=4, last=5, heading_page=4, naming_page=3)
    outcome = windows(pages, reply, 2, replies_on=3)
    (published,) = outcome.artifact["observations"]
    assert published["finding_text"].endswith(note_for("Д-5", 4, 5, others=(), naming_pages=(3,)))


# --- finding 4: the version's own list of text-less pages, and the recognised text ------------------------


def test_a_range_page_the_version_lists_as_text_less_refuses_the_pair_in_one_call_and_in_windows() -> None:
    pages = (PLAN, GENERAL, SCHEDULE, CLEAN_CONTINUATION)
    reply = omission(first=3, last=4, heading_page=3)
    assert one_call(pages, reply).metrics["omissions_published"] == 1
    dropped(one_call(pages, reply, textless_pages=(4,)), "range_page_textless")
    assert one_call(pages, reply, textless_pages=(2,)).metrics["omissions_published"] == 1, "page 2 is not in the range"
    # windows: pages 1-4 are the first window, 5 the second; the pair is judged inside the first
    longer = (*pages, CLEAN_CONTINUATION)
    inner = omission(first=3, last=3, heading_page=3)
    assert windows(longer, inner, 4).metrics["omissions_published"] == 1
    dropped(windows(longer, inner, 4, textless_pages=(3,)), "range_page_textless")


def test_the_term_in_the_recognised_text_of_a_searched_page_refuses_the_pair() -> None:
    pages = (PLAN, "", SCHEDULE, CLEAN_CONTINUATION)  # page 2 is a scan
    scan = RecognisedPage(2, "Распознано: на скане написано: дверь Д-5 в санузел.")
    reply = omission(first=3, last=3, heading_page=3)
    dropped(one_call(pages, reply, recognised_pages=(scan,)), "term_in_recognised_text")
    quiet = RecognisedPage(2, "Распознано: общие данные листа.")
    published = one_call(pages, reply, recognised_pages=(quiet,))
    assert published.metrics["omissions_published"] == 1
    assert "распознанный текст страницы 2 тоже проверен" in published.artifact["observations"][0]["finding_text"]


def test_the_term_in_the_recognised_text_refuses_the_pair_from_a_window_too() -> None:
    pages = (PLAN, "", SCHEDULE, CLEAN_CONTINUATION, CLEAN_CONTINUATION)
    scan = RecognisedPage(2, "Распознано: на скане написано: дверь Д-5 в санузел.")
    dropped(
        windows(pages, JUDGE_REPLY, 4, recognised_pages=(scan,), extra_weight=total_characters([scan])),
        "term_in_recognised_text",
    )


# --- the executor hands the version's list and the recognised text to the check ----------------------------


class Store:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_blob(self, payload: bytes, *, declared_sha256: str, declared_size: int, role: str, media_type: str) -> Any:
        blob_id = str(derive_blob_id(sha256=declared_sha256, size=declared_size))
        self.objects[blob_id] = payload
        return SimpleNamespace(blob_id=blob_id, sha256=declared_sha256, size=declared_size, media_type=media_type)

    def read(self, blob_id: Any, *, verify: bool) -> bytes:
        return self.objects[str(blob_id)]


def executor_world(pages: tuple[str, ...], scans: dict[int, str]) -> tuple[Store, _StageOutputs]:
    store, outputs = Store(), _StageOutputs()
    entries = [
        {
            "portal_block_id": f"blk_{number}", "page_number": number, "kind": "recognised_text",
            "quote_source": "recognised", "text": text, "flags": [],
        }
        for number, text in scans.items()
    ]
    for role, body in (
        (ROLE_TEXT_LAYER, document(*pages)),
        (ROLE_DOCUMENT_GRAPH, {"artifact_role": ROLE_DOCUMENT_GRAPH, "artifact_version": "1.0.0", "version_uid": VERSION}),
        (ROLE_RECOGNISED_TEXT, {
            "artifact_role": ROLE_RECOGNISED_TEXT, "artifact_version": "1.0.0", "version_uid": VERSION,
            "results_sha256": "a" * 64, "entries": entries,
        }),
    ):
        reference, _ = publish_artifact(store, role, body)
        outputs.refs[role] = reference
    return store, outputs


def executor_stage(pages: tuple[str, ...], scans: dict[int, str], reply: dict[str, Any], **extra: Any) -> Any:
    store, outputs = executor_world(pages, scans)
    adapter = Scripted(lambda seen: [reply])
    clock = lambda: datetime(2026, 10, 28, tzinfo=timezone.utc)  # noqa: E731
    result, artifact, _ = _run_text_analysis_stage(
        run_id="run_01M5YJZCQVQKMDFWT4MWCVEKQ7", version_uid=VERSION, outputs=outputs, blob_store=store,
        adapter=adapter, provider_config=CONFIG, cost_meter=CostMeter(ceiling_usd=5.0), policy=RetryPolicy(),
        sleep=lambda seconds: None, clock=clock, call_journal=None, profile=AI, **extra,
    )
    assert result.status.value == "succeeded" and artifact is not None
    return SimpleNamespace(artifact=artifact, metrics=result.metrics)


def test_the_executor_hands_the_versions_text_less_list_to_the_omission_check() -> None:
    pages = (PLAN, GENERAL, SCHEDULE, CLEAN_CONTINUATION)
    reply = omission(first=3, last=4, heading_page=3)
    assert executor_stage(pages, {}, reply, textless_pages=()).metrics["omissions_published"] == 1
    assert executor_stage(pages, {}, reply, textless_pages=None).metrics["omissions_published"] == 1
    dropped(executor_stage(pages, {}, reply, textless_pages=(4,)), "range_page_textless")


def test_the_executor_hands_the_recognised_text_to_the_omission_check() -> None:
    pages = (PLAN, "", SCHEDULE, CLEAN_CONTINUATION)
    reply = omission(first=3, last=3, heading_page=3)
    dropped(
        executor_stage(pages, {2: "Распознано: на скане написано: дверь Д-5 в санузел."}, reply, textless_pages=(2,)),
        "term_in_recognised_text",
    )
    quiet = executor_stage(pages, {2: "Распознано: общие данные листа."}, reply, textless_pages=(2,))
    assert quiet.metrics["omissions_published"] == 1
    assert "распознанный текст страницы 2 тоже проверен" in quiet.artifact["observations"][0]["finding_text"]


@pytest.mark.parametrize("reason", ["range_reaches_window_end", "term_on_other_visible_page", "range_page_textless",
                                    "term_in_recognised_text", "finding_text_overclaims"])
def test_every_new_reason_is_a_stage_metric(reason: str) -> None:
    outcome = one_call((PLAN, GENERAL, SCHEDULE, CLEAN_CONTINUATION), omission(first=3, last=4, heading_page=3))
    assert f"omissions_dropped_{reason}" in outcome.metrics and outcome.metrics[f"omissions_dropped_{reason}"] == 0
