"""`CMP-VC-AIPAIR-01`: the prompt, the strict validator of the answer and the content key, container-free."""

from __future__ import annotations

import json

import pytest

from auditmanager.comparison.ai_pairs.model import (
    KIND_NO_PAIR,
    MAX_OUTPUT_TOKENS,
    PROMPT_VERSION,
    PageFacts,
    Question,
    QuestionPage,
)
from auditmanager.comparison.ai_pairs.plans import PlanContext, content_key, forward_plan, reverse_plan
from auditmanager.comparison.ai_pairs.prompt import ANSWER_SCHEMA, build_prompt, build_request, crop_ids, validate_answer

A, B = "ver_A", "ver_B"


def facts(version: str, number: int, *, sheet: str = "", title: str = "", sha: str | None = None, key: str | None = None) -> PageFacts:
    return PageFacts(
        page_profile_id=f"cpr_{version}_{number}", version_uid=version, page_number=number, content_key=key or f"key-{version}-{number}",
        sheet_number=sheet, title=title, preview_blob_id=f"blob_{version}_{number}", preview_sha256=sha or f"{number:02d}" * 32,
        preview_size=1000,
    )


def context(**over: object) -> PlanContext:
    pages = {(v, n): facts(v, n, sheet=str(n), title=f"План {n}") for v in (A, B) for n in range(1, 8)}
    base: dict[str, object] = dict(
        project_uid="prj_P", model_identity="claude-opus-5", provider_mode="live", order=(A, B), page_counts={A: 7, B: 7},
        facts=pages, document_title="133/23-ГК-ЭО",
    )
    return PlanContext(**{**base, **over})  # type: ignore[arg-type]


def question() -> Question:
    return Question(
        kind=KIND_NO_PAIR, a=QuestionPage(A, 2, "cpr_ver_A_2"), b_version_uid=B,
        candidates=(QuestionPage(B, 2, "cpr_ver_B_2"), QuestionPage(B, 3, "cpr_ver_B_3")), back={3: (1, 4)},
    )


# -- the prompt (a port of ``sheet_match.py:171-202``) ---------------------------------------------------------------------


def test_the_prompt_lists_the_sheet_and_every_candidate_as_the_original_does() -> None:
    text = build_prompt(
        code="133/23-ГК-ЭО", a_label="№1", a_facts=facts(A, 2, sheet="2", title="План этажа"), a_page_count=7, b_label="№2",
        candidates=[facts(B, 2, sheet="2"), facts(B, 3, title="План кровли")], b_page_count=7, back=False,
    )
    assert "Ты сверяешь две версии одного комплекта рабочей документации (шифр 133/23-ГК-ЭО)." in text
    assert "Изображение 1 — лист A: версия «№1», стр. 2 из 7, номер листа в штампе «2», название в штампе «План этажа»." in text
    assert "Изображение 2 — кандидат 1: версия «№2», стр. 2 из 7, номер листа в штампе «2»." in text
    assert "Изображение 3 — кандидат 2: версия «№2», стр. 3 из 7, название в штампе «План кровли»." in text
    assert "какой из кандидатов следующей версии — ЭТО ЖЕ лист" in text and "ПРЕДЫДУЩЕЙ" not in text
    assert "Если ни один кандидат не является тем же листом — ответ 0." in text
    assert "choice — номер кандидата (1…2) или 0" in text and "не длиннее 300 знаков" in text


def test_the_reverse_prompt_asks_for_the_previous_version() -> None:
    text = build_prompt(
        code="", a_label="№2", a_facts=facts(B, 3), a_page_count=7, b_label="№1", candidates=[facts(A, 2)], b_page_count=7, back=True,
    )
    assert "ПРЕДЫДУЩЕЙ версии" in text and "(шифр" not in text, "no cipher, no empty parenthesis"


def test_the_pictures_are_named_by_their_order_not_by_a_caption_this_port_does_not_print() -> None:
    text = build_prompt(
        code="", a_label="№1", a_facts=facts(A, 2), a_page_count=7, b_label="№2", candidates=[facts(B, 2)], b_page_count=7, back=False,
    )
    assert "Над каждой картинкой крупно впечатано" not in text
    assert "изображение 1 — лист A, изображение n+1 — кандидат n" in text
    assert crop_ids(3) == ("sheet-a", "cand-1", "cand-2", "cand-3")


def test_the_request_is_the_shape_every_text_stage_builds_and_pins_the_schema() -> None:
    request = build_request(model_id="claude-opus-5", prompt="p")
    assert request.body["model"] == "claude-opus-5" and request.body["max_tokens"] == MAX_OUTPUT_TOKENS
    assert request.body["messages"] == [{"role": "user", "content": "p"}] and isinstance(request.body["system"], str)
    assert request.body["output_config"]["format"] == {"type": "json_schema", "schema": dict(ANSWER_SCHEMA)}
    assert request.request_sha256 == build_request(model_id="claude-opus-5", prompt="p").request_sha256
    assert request.request_sha256 != build_request(model_id="claude-opus-5", prompt="q").request_sha256
    assert set(ANSWER_SCHEMA["required"]) == {"choice", "page", "confidence", "reason"}  # type: ignore[arg-type]
    assert ANSWER_SCHEMA["properties"]["confidence"]["enum"] == ["high", "medium", "low"]  # type: ignore[index]


# -- the strict validator --------------------------------------------------------------------------------------------------


def reply(**over: object) -> str:
    return json.dumps({**{"choice": 2, "page": 3, "confidence": "high", "reason": "тот же план"}, **over}, ensure_ascii=False)


def test_a_reply_that_is_exactly_the_schema_is_an_answer() -> None:
    answer = validate_answer(reply(), (2, 3))
    assert answer.ok and (answer.choice, answer.page, answer.confidence, answer.reason, answer.cands) == (2, 3, "high", "тот же план", (2, 3))


@pytest.mark.parametrize("text", [
    "not json", "[]", "null", json.dumps({"choice": 1}), reply(extra=1), reply(choice="2"), reply(choice=True), reply(page=2.5),
    reply(confidence="certain"), reply(reason=7), reply(choice=3), reply(choice=-1), reply(page=-1),
])
def test_anything_else_is_no_answer(text: str) -> None:
    assert not validate_answer(text, (2, 3)).ok


def test_a_number_and_a_page_that_disagree_are_kept_for_the_rule_to_drop() -> None:
    """It is an answer (a wrong one); dropping it here would make the next run ask again and pay again."""
    assert validate_answer(reply(choice=1, page=3), (2, 3)).ok


def test_the_reason_is_trimmed_and_cut_to_the_contracts_300_characters() -> None:
    answer = validate_answer(reply(reason="  слово   " + "я" * 400), (2, 3))
    assert answer.reason.startswith("слово я") and len(answer.reason) == 300


# -- the content key ------------------------------------------------------------------------------------------------------


def test_the_same_question_has_the_same_key_and_every_input_moves_it() -> None:
    base = forward_plan(question(), context())
    assert base.key == forward_plan(question(), context()).key
    assert base.images == 3 and base.cands == (2, 3) and base.image_bytes == 3000
    assert forward_plan(question(), context(project_uid="prj_Q")).key != base.key, "the key includes the project"
    assert forward_plan(question(), context(model_identity="claude-sonnet-5")).key != base.key, "and the model"
    assert forward_plan(question(), context(provider_mode="recorded")).key != base.key, "a recorded answer is not a live one"
    pages = dict(context().facts)
    pages[(B, 3)] = facts(B, 3, sheet="3", title="План 3", key="changed content")
    assert forward_plan(question(), context(facts=pages)).key != base.key, "the content of a candidate"
    pages = dict(context().facts)
    pages[(A, 2)] = facts(A, 2, sheet="2", title="План 2", sha="ab" * 32)
    assert forward_plan(question(), context(facts=pages)).key != base.key, "the stored preview of the sheet"
    pages = dict(context().facts)
    pages[(B, 3)] = facts(B, 3, sheet="3", title="Другое название")
    assert forward_plan(question(), context(facts=pages)).key != base.key, "the text of the prompt"


def test_a_new_prompt_version_is_a_new_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from auditmanager.comparison.ai_pairs import plans

    kwargs = dict(project_uid="prj_P", model_identity="m", provider_mode="live", kind="no_pair", prompt="t", pages=[facts(A, 1)])
    key = content_key(**kwargs)  # type: ignore[arg-type]
    monkeypatch.setattr(plans, "PROMPT_VERSION", PROMPT_VERSION + "-next")
    assert content_key(**kwargs) != key  # type: ignore[arg-type]


def test_the_reverse_question_has_a_key_of_its_own_and_its_candidates() -> None:
    plan = reverse_plan(question(), 3, context())
    assert plan is not None and plan.kind == "reverse_check"
    assert plan.cands == (1, 2, 4), "B's own candidates (1, 4) and sheet A (2)"
    assert plan.pages[0].page_number == 3 and plan.pages[0].version_uid == B
    assert plan.key != forward_plan(question(), context()).key
    assert plan.images == 4


def test_a_reverse_question_that_cannot_be_asked_is_none() -> None:
    pages = dict(context().facts)
    pages[(B, 3)] = PageFacts(page_profile_id="cpr_x", version_uid=B, page_number=3, content_key="k")  # no stored preview
    assert reverse_plan(question(), 3, context(facts=pages)) is None
    spec = dict(context().facts)
    spec[(B, 3)] = facts(B, 3, title="Спецификация оборудования")
    assert reverse_plan(question(), 3, context(facts=spec)) is None, "a specification sheet is compared whole"
