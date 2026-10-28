"""SECTION-JUDGE-FIXES-01: what the independent judge J2 found in the omission check, one case per finding.

``decide`` used to prove an absence only for the page range the model chose, from the text layer alone.
The judge's reproduction: a term named on page 1, the schedule's heading on page 3, the schedule continuing on
page 4 with the term; the claim «pages 3 to 3», visible 1 to 3, was published as «не найдена на странице 3».
The findings, and the guard each case below makes fail:

* finding 1 (range): the term must not occur on any other page the model was shown (except the pages of the
  naming quote), and a claim that ends on the last page of a window that is not the last window is refused;
* finding 4 (scans): a range page the version stores as text-less, or the term in the recognised text of a
  searched page, refuses the pair;
* finding 6 (wording): a finding text that says the item is absent from the project or required is refused.

Pure unit cases over :func:`auditmanager.analysis.text.omission.decide`; the same guards against the real
stage (single call and windows) are in ``tests/integration/sections/test_section_omission_judge_fixes.py``.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from auditmanager.analysis.text.anchors import resolve_anchor
from auditmanager.analysis.text.omission import (
    OMISSION_REASONS,
    decide,
    note_for,
    quotes_of,
)
from auditmanager.analysis.text.prompt import CATEGORIES, OMISSION_CATEGORY
from auditmanager.analysis.text.recognised_input import RecognisedPage
from auditmanager.analysis.text.response import parse_response
from auditmanager.analysis.text.textlayer import load_text_layer

CATEGORIES3 = (*CATEGORIES, OMISSION_CATEGORY)
PLAN = "План. Помещение 4 — санузел. Дверь Д-5 в санузел, ширина 800 мм. Отметка чистого пола 0,000."
GENERAL = "Общие данные: двери по проекту принимаются по ведомости; марки приведены ниже на листах."
HEADING = "Ведомость дверных заполнений"
SCHEDULE = f"{HEADING}\nМарка Д-1 Дверь входная, 2 шт.\nМарка Д-2 Дверь межкомнатная, 6 шт."
CONTINUATION = "Продолжение ведомости: марка Д-5 Дверь в санузел, 1 шт.; марка Д-6 Дверь в кухню, 1 шт."
FILLER = "Продолжение ведомости: марка Д-1, марка Д-2, марка Д-3, марка Д-4, достаточно текста."


def layer(*pages: str) -> Any:
    out, start = [], 0
    for number, text in enumerate(pages, 1):
        out.append({"page_number": number, "char_start": start, "char_end": start + len(text), "text": text})
        start += len(text)
    return load_text_layer(
        {
            "artifact_role": "prepared.text_layer", "artifact_version": "1.0.0", "version_uid": "ver_x",
            "normalization": {"id": "nfc_v1", "description": "NFC"}, "total_char_count": start, "pages": out,
        }
    )


def reply(*, finding: str = "Марка Д-5 названа на плане и не найдена в ведомости.", **claim: Any) -> str:
    omission = {
        "term": "Д-5", "first_page": 2, "last_page": 2,
        "heading": {"page_number": 2, "quote": HEADING},
    }
    omission.update(claim)
    return json.dumps(
        {
            "observations": [
                {
                    "category": "documentation", "finding_text": finding, "recommendation_text": "Сверить.",
                    "evidence": [{"page_number": 1, "quote": "Дверь Д-5 в санузел"}], "omission": omission,
                }
            ]
        },
        ensure_ascii=False,
    )


def check(text_layer: Any, body: str, *, visible: tuple[int, int] | None = None, **extra: Any) -> Any:
    (proposal,) = parse_response(body, truncated=False, categories=CATEGORIES3).observations
    anchors = [
        resolve_anchor(text_layer, page_number=item.page_number, quote=item.quote) for item in quotes_of(proposal)
    ]
    return decide(text_layer, proposal, anchors, visible, **extra)


# --- finding 1: the range the model chose is not the whole schedule ------------------------------------------


def judge_layer() -> Any:
    """The judge's reproduction: the term on page 1, the heading on page 3, the schedule continues on page 4."""
    return layer(PLAN, GENERAL, SCHEDULE, CONTINUATION)


JUDGE_CLAIM = {"first_page": 3, "last_page": 3, "heading": {"page_number": 3, "quote": HEADING}}
TO_PAGE_4 = {**JUDGE_CLAIM, "last_page": 4}


def test_the_judges_reproduction_is_not_published_in_one_call() -> None:
    outcome = check(judge_layer(), reply(**JUDGE_CLAIM))
    assert outcome.reason == "term_on_other_visible_page", "the schedule continues on page 4 with the term"


def test_the_judges_reproduction_is_not_published_from_the_first_of_two_windows() -> None:
    """Pages 1 to 3 are a window that is not the last one: a claim that ends on page 3 says nothing of page 4."""
    outcome = check(judge_layer(), reply(**JUDGE_CLAIM), visible=(1, 3))
    assert outcome.reason == "range_reaches_window_end"


def test_a_claim_ending_on_the_last_page_of_the_last_window_is_judged_on_the_pages_it_saw() -> None:
    clean = layer(PLAN, GENERAL, SCHEDULE, FILLER)
    assert check(clean, reply(**TO_PAGE_4), visible=(1, 4)).published
    assert check(clean, reply(**TO_PAGE_4), visible=None).published
    assert check(judge_layer(), reply(**TO_PAGE_4), visible=(1, 4)).reason == "term_present_in_range"


def test_a_claim_that_ends_before_the_window_end_is_published_when_the_page_after_it_is_clean() -> None:
    """The page after the range is the sentinel: it is visible and does not hold the term."""
    clean = layer(PLAN, GENERAL, SCHEDULE, FILLER, FILLER)
    assert check(clean, reply(**JUDGE_CLAIM), visible=(1, 4)).published
    dirty = layer(PLAN, GENERAL, SCHEDULE, CONTINUATION, FILLER)
    assert check(dirty, reply(**JUDGE_CLAIM), visible=(1, 4)).reason == "term_on_other_visible_page"


@pytest.mark.parametrize("where", [0, 1, 3, 4])
def test_the_term_on_any_other_visible_page_refuses_the_pair(where: int) -> None:
    """A page before the range, between the naming page and the range, or after it: all count."""
    pages = [PLAN, GENERAL, SCHEDULE, FILLER, FILLER]
    pages[where] = pages[where] + " Ещё упоминание: Д-5."
    outcome = check(layer(*pages), reply(**JUDGE_CLAIM))
    if where == 0:
        assert outcome.published, "page 1 is the naming page: the term is there by definition"
    else:
        assert outcome.reason == "term_on_other_visible_page", where


def test_the_naming_page_is_the_only_page_exempt_and_only_the_pages_the_model_was_shown_count() -> None:
    text_layer = layer(PLAN, GENERAL, SCHEDULE, FILLER, CONTINUATION)  # the term on page 5, beyond the window
    assert check(text_layer, reply(**JUDGE_CLAIM), visible=(1, 4)).published
    assert check(text_layer, reply(**JUDGE_CLAIM), visible=(1, 5)).reason == "term_on_other_visible_page"
    # a term in the schedule's range is still the older reason
    assert check(layer(PLAN, GENERAL, SCHEDULE + "\nМарка Д-5", FILLER), reply(**JUDGE_CLAIM)).reason == (
        "term_present_in_range"
    )


def test_the_term_split_across_the_range_and_the_next_page_is_a_presence() -> None:
    split = layer(PLAN, GENERAL, SCHEDULE + "\nМарка Д-", "5 Дверь в санузел, 1 шт. и ещё достаточно текста.")
    assert check(split, reply(**JUDGE_CLAIM)).reason == "term_on_other_visible_page"


def test_the_sentence_names_the_pages_that_were_searched() -> None:
    assert note_for("Д-5", 3, 3, others=(2, 4, 5), naming_pages=(1,)) == (
        "Проверка программой: запись «Д-5» не найдена в текстовом слое на странице 3 и на остальных "
        "страницах 2, 4–5, которые видела модель (кроме страницы 1, где запись названа); "
        "сравнение без учёта регистра, тире, пробелов и сходных по начертанию букв; "
        "другие написания не проверялись."
    )
    assert "на остальных" not in note_for("Д-5", 2, 3, others=(), naming_pages=(1,))
    assert "распознанный текст страниц 3, 6 тоже проверен" in note_for(
        "Д-5", 2, 3, others=(6,), naming_pages=(1,), recognised_pages=(3, 6)
    )


def test_the_published_sentence_is_the_one_for_the_pages_decide_searched() -> None:
    text_layer = layer(PLAN, GENERAL, SCHEDULE, FILLER, FILLER)
    outcome = check(text_layer, reply(**JUDGE_CLAIM), visible=(1, 4))
    assert outcome.published
    assert outcome.finding_text.endswith(note_for("Д-5", 3, 3, others=(2, 4), naming_pages=(1,)))
    whole = check(text_layer, reply(**JUDGE_CLAIM))
    assert whole.finding_text.endswith(note_for("Д-5", 3, 3, others=(2, 4, 5), naming_pages=(1,)))


# --- finding 4: scans -------------------------------------------------------------------------------------


def test_a_range_page_the_version_stores_as_text_less_refuses_the_pair() -> None:
    text_layer = layer(PLAN, SCHEDULE, FILLER)
    claim = {"last_page": 3}
    assert check(text_layer, reply(**claim)).published
    assert check(text_layer, reply(**claim), textless_pages=(2,)).reason == "range_page_textless"
    assert check(text_layer, reply(**claim), textless_pages=(3,)).reason == "range_page_textless"
    assert check(text_layer, reply(**claim), textless_pages=(1,)).published, "page 1 is not in the range"
    assert check(text_layer, reply(**claim), textless_pages=()).published
    assert check(text_layer, reply(**claim), textless_pages=None).published


def test_the_term_in_the_recognised_text_of_a_range_page_refuses_the_pair() -> None:
    text_layer = layer(PLAN, SCHEDULE, FILLER)
    claim = {"last_page": 3}
    scan = RecognisedPage(3, "Марка Д-5 Дверь в санузел, 1 шт. (распознано)")
    assert check(text_layer, reply(**claim), recognised=(scan,)).reason == "term_in_recognised_text"
    other = RecognisedPage(3, "Марка Д-6 Дверь в кухню, 1 шт. (распознано)")
    assert check(text_layer, reply(**claim), recognised=(other,)).published
    # a spelling the text-layer check already folds is a presence in the recognised text as well
    dash = RecognisedPage(3, "марка д–5 дверь в санузел")
    assert check(text_layer, reply(**claim), recognised=(dash,)).reason == "term_in_recognised_text"


def test_recognised_text_of_another_searched_page_counts_and_of_an_unseen_page_does_not() -> None:
    text_layer = layer(PLAN, GENERAL, SCHEDULE, FILLER, FILLER)
    page_two = RecognisedPage(2, "Д-5 есть и здесь")
    page_five = RecognisedPage(5, "Д-5 есть и здесь")
    assert check(text_layer, reply(**JUDGE_CLAIM), recognised=(page_two,)).reason == "term_in_recognised_text"
    assert check(text_layer, reply(**JUDGE_CLAIM), visible=(1, 4), recognised=(page_five,)).published
    assert check(text_layer, reply(**JUDGE_CLAIM), visible=None, recognised=(page_five,)).reason == (
        "term_in_recognised_text"
    )
    # the naming page's own recognised text is the naming place, not a presence elsewhere
    assert check(text_layer, reply(**JUDGE_CLAIM), recognised=(RecognisedPage(1, "Д-5"),)).published


def test_the_published_sentence_says_which_recognised_pages_were_searched() -> None:
    text_layer = layer(PLAN, GENERAL, SCHEDULE, FILLER, FILLER)
    scan = RecognisedPage(4, "Марка Д-6 Дверь в кухню")
    outcome = check(text_layer, reply(**JUDGE_CLAIM), recognised=(scan,))
    assert outcome.published
    assert outcome.finding_text.endswith(
        note_for("Д-5", 3, 3, others=(2, 4, 5), naming_pages=(1,), recognised_pages=(4,))
    )
    assert "распознанный текст страницы 4 тоже проверен" in outcome.finding_text


# --- finding 6: the sentence of the model must not claim more than the check proved ---------------------------


@pytest.mark.parametrize(
    "finding",
    [
        "Марка Д-5 названа на плане, но её нет в проекте.",
        "Марка Д-5 в ведомости не предусмотрена.",
        "Такая марка обязательна в ведомости, а её там нет.",
        "МАРКА Д-5 НЕТ В ПРОЕКТЕ",
        "Марка Д-5 не предусмотрено вовсе.",
        "Нет в проекте: марка Д-5.",
    ],
)
def test_a_finding_text_that_claims_absence_from_the_project_or_a_requirement_is_refused(finding: str) -> None:
    outcome = check(layer(PLAN, SCHEDULE), reply(finding=finding))
    assert outcome.reason == "finding_text_overclaims", finding


def test_a_finding_text_that_names_two_places_is_published() -> None:
    finding = "Марка Д-5 названа на плане на странице 1 и не найдена в ведомости на странице 2."
    assert check(layer(PLAN, SCHEDULE), reply(finding=finding)).published


# --- the vocabulary -------------------------------------------------------------------------------------


def test_the_new_reasons_are_in_the_closed_vocabulary_in_the_order_the_checks_run() -> None:
    new = ("range_reaches_window_end", "finding_text_overclaims", "range_page_textless",
           "term_on_other_visible_page", "term_in_recognised_text")
    assert set(new) <= set(OMISSION_REASONS)
    order = {reason: index for index, reason in enumerate(OMISSION_REASONS)}
    assert order["range_outside_window"] < order["range_reaches_window_end"] < order["heading_outside_range"]
    assert order["term_not_in_naming_quote"] < order["finding_text_overclaims"] < order["range_page_textless"]
    assert order["range_page_textless"] < order["range_page_without_text"] < order["term_present_in_range"]
    assert order["term_present_in_range"] < order["term_on_other_visible_page"] < order["term_in_recognised_text"]
