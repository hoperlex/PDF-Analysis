"""`SECTION-CATEGORY-OCR-01`: recognised text reaches a section call as marked context, and confirms nothing.

Driven through the real stages (`run_text_analysis`, `run_text_analysis_windows`) with scripted adapters and the
registered section profiles, no container. What is held:

* a version with a text-less page sends that page's recognised text in a delimited block under the page
  banner, with the notice in the preamble; the call's metrics say how many pages and characters;
* a quote that exists only in recognised text confirms nothing: an observation whose only evidence is such a
  quote is dropped, one with other quotes keeps the other quotes, an omission whose naming or heading quote is
  recognised-only is refused. The control shows the guard is the text layer: the same quote resolves the moment
  its text is in the layer, which is exactly what this lane never does;
* in a windowed run each window carries the blocks of its own pages and the notice only if it has one, the
  plan counts the blocks, and an omission is judged inside its window.
"""

from __future__ import annotations

import json
import re
from typing import Any

from auditmanager.analysis.text import STATUS_SUCCEEDED, ProviderConfig, ProviderMode, run_text_analysis
from auditmanager.analysis.text.adapter import ModelResponse
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.analysis.text.recognised_input import BLOCK_OPEN, NOTICE, RecognisedPage, total_characters
from auditmanager.analysis.text.windowed import run_text_analysis_windows
from auditmanager.analysis.text.windows import WindowPolicy
from auditmanager.shared.identity import RunId

REGISTRY = load_text_profile_registry()
KJ = REGISTRY.entries["KJ"].profile  # two categories
AI = REGISTRY.entries["AI"].profile  # three categories

TEXT_1 = "Страница 1. Схема. Щит ЩО-3 питает освещение этажа; степень огнестойкости здания II."
TEXT_3 = "Страница 3. Спецификация оборудования. Щит ЩР-1 в сборе, 1 шт.; степень огнестойкости здания II."
HEADING = "Спецификация оборудования"
OCR = "На скане записано: степень огнестойкости здания III; щит ЩО-3 в спецификации не указан."
SCAN = RecognisedPage(page_number=2, text=OCR, flags=("mixed_script",))
BANNER = re.compile(r"=== Страница (\d+) ===")


def layer(*pages: str) -> dict[str, Any]:
    out, start = [], 0
    for number, text in enumerate(pages, 1):
        out.append({"page_number": number, "char_start": start, "char_end": start + len(text), "text": text})
        start += len(text)
    return {
        "artifact_role": "prepared.text_layer", "artifact_version": "1.0.0", "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
        "normalization": {"id": "nfc_v1", "description": "NFC"}, "total_char_count": start, "pages": out,
    }


CONFIG = ProviderConfig(
    mode=ProviderMode.RECORDED, model_id="claude-opus-5", run_cost_ceiling_usd=5.0, api_key=None,
    ceiling_is_explicit=True,
)


class Scripted:
    """Answers each call with ``answer(user_content, call_index)`` and keeps the requests it was asked."""

    def __init__(self, answer: Any) -> None:
        self._answer = answer
        self.requests: list[Any] = []

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.RECORDED

    def complete(self, request: Any) -> ModelResponse:
        self.requests.append(request)
        observations = self._answer(request.body["messages"][0]["content"], len(self.requests) - 1)
        return ModelResponse(
            output_text=json.dumps({"observations": observations}, ensure_ascii=False),
            stop_reason="end_turn", input_tokens=100, output_tokens=10, latency_ms=5, reported_cost_usd=0.01,
        )

    def user(self, index: int = 0) -> str:
        return self.requests[index].body["messages"][0]["content"]


def contradiction(*items: tuple[int, str]) -> dict[str, Any]:
    return {
        "category": "internal_contradiction", "finding_text": "Степень огнестойкости указана по-разному.",
        "recommendation_text": "Привести к одному значению.",
        "evidence": [{"page_number": page, "quote": quote} for page, quote in items],
    }


def omission_reply(*, naming: tuple[int, str], heading: tuple[int, str], first: int, last: int, term: str = "ЩО-3") -> dict[str, Any]:
    return {
        "category": "documentation", "finding_text": "Щит назван на схеме и не найден в спецификации.",
        "recommendation_text": "Сверить спецификацию.",
        "evidence": [{"page_number": naming[0], "quote": naming[1]}],
        "omission": {
            "term": term, "first_page": first, "last_page": last,
            "heading": {"page_number": heading[0], "quote": heading[1]},
        },
    }


def run(profile: Any, document: dict[str, Any], adapter: Scripted, recognised: tuple[RecognisedPage, ...] = ()) -> Any:
    return run_text_analysis(
        run_id=RunId.new(), text_layer_document=document, adapter=adapter, profile=profile, config=CONFIG,
        recognised_pages=recognised,
    )


# --- the block is sent, marked, and counted -----------------------------------------------------------


def test_a_scanned_page_goes_to_the_model_as_a_marked_block_under_its_banner() -> None:
    adapter = Scripted(lambda user, index: [])
    outcome = run(KJ, layer(TEXT_1, "", TEXT_3), adapter, (SCAN,))
    assert outcome.status == STATUS_SUCCEEDED
    user = adapter.user()
    assert NOTICE in user.split("\n")[0]
    lines = user.split("\n")
    banner = lines.index("=== Страница 2 ===")
    assert lines[banner + 2] == BLOCK_OPEN.format(page_number=2)
    assert json.loads(lines[banner + 3]) == OCR
    metrics = outcome.metrics
    assert metrics["recognised_pages"] == 1 and metrics["recognised_characters"] == total_characters([SCAN])


def test_a_version_without_a_scanned_page_sends_no_block_and_its_metrics_do_not_move() -> None:
    adapter = Scripted(lambda user, index: [])
    outcome = run(KJ, layer(TEXT_1, TEXT_3), adapter)
    assert "Распознанный текст" not in adapter.user() and NOTICE not in adapter.user()
    assert not any(key.startswith("recognised_") for key in outcome.metrics)
    assert not any(key.startswith("omissions_") for key in outcome.metrics), "KJ declares no omission category"


# --- a quote found only in recognised text confirms nothing ---------------------------------------------


def test_an_observation_whose_only_quote_is_in_the_recognised_text_is_dropped() -> None:
    quote = "степень огнестойкости здания III"
    assert quote in OCR and quote not in TEXT_1 + TEXT_3
    adapter = Scripted(lambda user, index: [contradiction((2, quote))])
    outcome = run(KJ, layer(TEXT_1, "", TEXT_3), adapter, (SCAN,))
    assert outcome.status == STATUS_SUCCEEDED
    assert outcome.artifact["observations"] == []
    assert outcome.metrics["evidence_unresolved"] == 1 and outcome.metrics["observations_dropped_unresolved"] == 1
    assert outcome.metrics["evidence_emitted"] == 0


def test_an_observation_keeps_its_text_layer_quote_and_loses_the_recognised_one() -> None:
    adapter = Scripted(
        lambda user, index: [
            contradiction((1, "степень огнестойкости здания II"), (2, "степень огнестойкости здания III"))
        ]
    )
    outcome = run(KJ, layer(TEXT_1, "", TEXT_3), adapter, (SCAN,))
    (published,) = outcome.artifact["observations"]
    assert [(item["page_number"], item["quote"]) for item in published["evidence"]] == [
        (1, "степень огнестойкости здания II")
    ], "the recognised-only quote is not evidence"
    assert outcome.metrics["evidence_unresolved"] == 1 and outcome.metrics["evidence_emitted"] == 1


def test_the_guard_is_the_text_layer_the_same_quote_resolves_if_its_text_is_in_it() -> None:
    """The control that makes the two cases above mean something: the property is structural."""
    quote = "степень огнестойкости здания III"
    in_layer = layer(TEXT_1, OCR, TEXT_3)  # what this lane never does: recognised text standing as page text
    adapter = Scripted(lambda user, index: [contradiction((2, quote))])
    outcome = run(KJ, in_layer, adapter)
    assert len(outcome.artifact["observations"]) == 1 and outcome.metrics["evidence_unresolved"] == 0


def test_an_omission_whose_naming_or_heading_quote_is_recognised_only_is_refused() -> None:
    page2_heading = "щит ЩО-3 в спецификации не указан"
    document = layer(TEXT_1, "", TEXT_3)
    naming_in_scan = Scripted(
        lambda user, index: [omission_reply(naming=(2, page2_heading), heading=(3, HEADING), first=3, last=3)]
    )
    outcome = run(AI, document, naming_in_scan, (SCAN,))
    assert outcome.artifact["observations"] == []
    assert outcome.metrics["omissions_dropped_evidence_unresolved"] == 1 and outcome.metrics["omissions_published"] == 0
    heading_in_scan = Scripted(
        lambda user, index: [omission_reply(naming=(1, "Щит ЩО-3 питает освещение этажа"), heading=(2, "На скане записано"), first=2, last=3)]
    )
    outcome = run(AI, document, heading_in_scan, (SCAN,))
    assert outcome.artifact["observations"] == []
    assert outcome.metrics["omissions_dropped_evidence_unresolved"] == 1


def test_a_scanned_page_in_the_range_proves_nothing_about_absence() -> None:
    """Even a recognised text that does not mention the term cannot support an absence claim."""
    adapter = Scripted(
        lambda user, index: [
            omission_reply(naming=(1, "Щит ЩО-3 питает освещение этажа"), heading=(3, HEADING), first=2, last=3)
        ]
    )
    outcome = run(AI, layer(TEXT_1, "", TEXT_3), adapter, (RecognisedPage(2, "Распознано: щит ЩР-1."),))
    assert outcome.artifact["observations"] == []
    assert outcome.metrics["omissions_dropped_heading_outside_range"] + outcome.metrics[
        "omissions_dropped_range_page_without_text"
    ] == 1


def test_the_same_pair_is_published_once_its_range_is_text_layer_text() -> None:
    """Before `SECTION-JUDGE-FIXES-01` this ran with the scan of `SCAN`, whose text names the term («щит ЩО-3 в
    спецификации не указан»), and the pair was published: the scan lay outside the range. The term in the
    recognised text of any page the model saw now refuses the pair (second half); the control keeps its
    meaning with a scan that does not name the term."""
    adapter = Scripted(
        lambda user, index: [
            omission_reply(naming=(1, "Щит ЩО-3 питает освещение этажа"), heading=(3, HEADING), first=3, last=3)
        ]
    )
    quiet = RecognisedPage(page_number=2, text="На скане записано: степень огнестойкости здания III.")
    outcome = run(AI, layer(TEXT_1, "", TEXT_3), adapter, (quiet,))
    (published,) = outcome.artifact["observations"]
    assert published["category"] == "documentation" and len(published["evidence"]) == 2
    assert outcome.metrics["omissions_published"] == 1
    assert "распознанный текст страницы 2 тоже проверен" in published["finding_text"]

    named = run(AI, layer(TEXT_1, "", TEXT_3), adapter, (SCAN,))
    assert named.artifact["observations"] == []
    assert named.metrics["omissions_dropped_term_in_recognised_text"] == 1 and named.metrics["omissions_published"] == 0


# --- windows --------------------------------------------------------------------------------------------

FILLER = "Страница {n}. Текст страницы с описанием решений, достаточный для окна. Щит ЩР-{n} в сборе."


def windowed_layer() -> dict[str, Any]:
    return layer(
        "Страница 1. Схема. Щит ЩО-3 питает освещение этажа; вводной автомат и УЗО на группах.",
        "Страница 2. Спецификация оборудования. Щит ЩР-2 в сборе, 1 шт.; автомат, 2 шт.",
        "",  # page 3 is a scan
        FILLER.format(n=4),
        FILLER.format(n=5),
        FILLER.format(n=6),
    )


def banners(user: str) -> list[int]:
    return [int(n) for n in BANNER.findall(user)]


def test_each_window_carries_the_blocks_of_its_own_pages_and_the_notice_only_with_one() -> None:
    scan = RecognisedPage(page_number=3, text="Распознано: щит ЩР-3.")
    adapter = Scripted(lambda user, index: [])
    outcome = run_text_analysis_windows(
        run_id=RunId.new(), text_layer_document=windowed_layer(), adapter=adapter, profile=KJ, config=CONFIG,
        policy=WindowPolicy(window_characters=800, max_windows=12), recognised_pages=(scan,),
    )
    assert outcome.status == STATUS_SUCCEEDED
    assert len(adapter.requests) >= 2
    seen_blocks = 0
    for index, request in enumerate(adapter.requests):
        user = adapter.user(index)
        pages = banners(user)
        has_block = "Распознанный текст страницы 3" in user
        assert has_block == (3 in pages)
        assert (NOTICE in user) == has_block
        seen_blocks += has_block
    assert seen_blocks == 1
    assert outcome.metrics["recognised_pages"] == 1 and outcome.metrics["windows_total"] == len(adapter.requests)


def test_a_single_window_plan_is_the_single_call_with_the_blocks() -> None:
    scan = RecognisedPage(page_number=3, text="Распознано: щит ЩР-3.")
    adapter = Scripted(lambda user, index: [])
    outcome = run_text_analysis_windows(
        run_id=RunId.new(), text_layer_document=windowed_layer(), adapter=adapter, profile=KJ, config=CONFIG,
        policy=WindowPolicy(window_characters=100_000, max_windows=12), recognised_pages=(scan,),
    )
    assert len(adapter.requests) == 1 and "Распознанный текст страницы 3" in adapter.user()
    assert "windows_total" not in outcome.metrics


def test_an_omission_is_judged_inside_its_window() -> None:
    """Pages 1-4 are the first window and 5-6 the second (330 characters)."""
    policy = WindowPolicy(window_characters=330, max_windows=12)
    document = windowed_layer()

    def go(answer: Any) -> Any:
        adapter = Scripted(answer)
        outcome = run_text_analysis_windows(
            run_id=RunId.new(), text_layer_document=document, adapter=adapter, profile=AI, config=CONFIG, policy=policy,
        )
        assert [banners(adapter.user(i)) for i in range(len(adapter.requests))] == [[1, 2, 3, 4], [5, 6]]
        return outcome

    def first_window(first: int, last: int) -> Any:
        def answer(user: str, index: int) -> list[dict[str, Any]]:
            if 1 not in banners(user):
                return []
            return [
                omission_reply(
                    naming=(1, "Щит ЩО-3 питает освещение этажа"), heading=(2, "Спецификация оборудования"),
                    first=first, last=last,
                )
            ]

        return answer

    inside = go(first_window(2, 2))
    assert inside.metrics["omissions_published"] == 1, inside.metrics
    (published,) = inside.artifact["observations"]
    assert [item["page_number"] for item in published["evidence"]] == [1, 2]

    beyond = go(first_window(2, 5))  # the range reaches into a window the model did not see
    assert beyond.artifact["observations"] == []
    assert beyond.metrics["omissions_dropped_range_outside_window"] == 1

    def naming_in_another_window(user: str, index: int) -> list[dict[str, Any]]:
        if 5 not in banners(user):
            return []
        return [
            omission_reply(
                naming=(1, "Щит ЩО-3 питает освещение этажа"),  # page 1 is not in this window
                heading=(5, "Текст страницы с описанием решений"), first=5, last=6,
            )
        ]

    elsewhere = go(naming_in_another_window)
    assert elsewhere.artifact["observations"] == []
    assert elsewhere.metrics["omissions_dropped_evidence_unresolved"] == 1
    assert elsewhere.metrics["evidence_outside_window"] >= 1
