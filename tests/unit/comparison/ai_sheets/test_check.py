"""The program's check of the model's answer (`CMP-VC-AISHEET-01`; the port of ``validate.py`` and its additions).

The commitments proved here: a claim the raw evidence does not contain is never a confirmed change (``unverified`` / ``unclear``); the
answer is never changed by the check; a candidate in no list leaves the sheet «Частично»; «исправлен текст» needs its second
representation; a service phrase is cut, not the item; a foreign packet is refused.
"""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from typing import Any

from auditmanager.comparison.ai_sheets import packet as pk
from auditmanager.comparison.ai_sheets.check import check, norm, state_of


def _fx() -> Any:
    name = "cmp_ai_sheets_fixtures"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / "sheet_fixtures.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


fx = _fx()
NO_OTHER = {"what": "", "value_a": "", "value_b": "", "image_id": ""}


def packet() -> dict[str, Any]:
    a, b = fx.table_pages("cpr_a", "cpr_b", "ver_a", "ver_b")
    facts = pk.SheetFacts(
        sheet_pair_id="ctp_1", title="План", project_title="Объект", designation="ЭМ-12", label_a="версия №1", label_b="версия №2",
        page_a=1, page_b=1, sheet_number="7", status="different", reasons=(), page_profile_a="cpr_a", page_profile_b="cpr_b",
        version_a="ver_a", version_b="ver_b",
    )
    return pk.assemble(facts, fx.table_result(), fx.FakeMaterial({"cpr_a": a, "cpr_b": b}), render=True, xrefs=False).document


def field(name: str = "количество", before: str = "2", after: str = "3", source: str = "text", certainty: str = "confirmed") -> dict[str, str]:
    return {"name": name, "before": before, "after": after, "unit": "шт", "source": source, "certainty": certainty}


def change(**over: Any) -> dict[str, Any]:
    base = {
        "object": "Люк Лк-1", "place": "таблица люков", "kind": "quantity", "summary": "Лк-1 — количество 2 → 3.",
        "fields": [field()], "members": [], "mapping": "one_to_one", "candidate_ids": ["O1"], "image_ids": ["I2"],
        "other_representation": dict(NO_OTHER), "limitation": "",
    }
    return base | over


def answer(doc: dict[str, Any], changes: list[dict[str, Any]], **over: Any) -> dict[str, Any]:
    base = {
        "packet_id": doc["packet_id"], "part_id": "P1", "changes": changes, "unresolved": [], "excluded": [], "context_requests": [],
    }
    return base | over


def everything_else(ids: tuple[str, ...] = ("O2", "O3")) -> list[dict[str, Any]]:
    return [{"candidate_ids": [i], "reason": "formatting", "note": ""} for i in ids]


def test_a_value_found_in_the_text_of_its_side_is_from_text_and_the_item_is_confirmed() -> None:
    doc = packet()
    result = check(doc, answer(doc, [change()], excluded=everything_else()))
    assert result["ok"] and result["issues"] == []
    item = result["changes"][0]
    assert (item["tier_was"], item["tier_now"], item["confirmation"]) == ("from_text", "from_text", "from_text")
    assert item["unclear"] is False
    assert state_of(result, doc) == "done"


def test_a_value_the_raw_evidence_does_not_contain_is_unverified_and_never_confirmed() -> None:
    doc = packet()
    claim = change(fields=[field(before="2", after="97")], summary="Лк-1 — количество 2 → 97.")
    result = check(doc, answer(doc, [claim], excluded=everything_else()))
    item = result["changes"][0]
    assert item["tier_now"] == "unverified" and item["confirmation"] == "unverified"
    assert item["unclear"] is True
    assert any(i["code"] == "VALUE_UNVERIFIED" for i in result["issues"])


def test_a_value_read_from_the_picture_the_model_cited_is_from_image_not_refused() -> None:
    doc = packet()
    claim = change(fields=[field(before="2", after="97", source="image")], summary="Лк-1 — количество 2 → 97.")
    item = check(doc, answer(doc, [claim], excluded=everything_else()))["changes"][0]
    assert item["tier_now"] == "from_image"
    # a picture the model did not cite proves nothing
    uncited = check(doc, answer(doc, [change(fields=[field(before="2", after="97", source="image")], image_ids=[],
                                             summary="Лк-1 — количество 2 → 97.")], excluded=everything_else()))["changes"][0]
    assert uncited["tier_now"] == "unverified"


def test_a_picture_that_was_not_in_the_packet_is_dropped_from_the_item() -> None:
    doc = packet()
    result = check(doc, answer(doc, [change(image_ids=["I2", "I99"])], excluded=everything_else()))
    assert result["changes"][0]["image_ids"] == ["I2"]
    assert any(i["code"] == "UNKNOWN_IMAGE" for i in result["issues"])


def test_a_number_in_the_summary_that_no_evidence_holds_makes_the_item_unclear() -> None:
    doc = packet()
    claim = change(summary="Лк-1 — количество 2 → 3, ориентировочно на 7777 руб.")
    result = check(doc, answer(doc, [claim], excluded=everything_else()))
    item = result["changes"][0]
    assert item["unsupported"]["summary"] == ["7777"] and item["unclear"] is True
    assert any(i["code"] == "SUMMARY_UNSUPPORTED" for i in result["issues"])


def test_a_place_that_no_evidence_holds_makes_the_item_unclear() -> None:
    doc = packet()
    result = check(doc, answer(doc, [change(place="оси 17-18, помещение 304")], excluded=everything_else()))
    item = result["changes"][0]
    assert item["unsupported"]["place"] and item["unclear"] is True
    assert any(i["code"] == "PLACE_UNVERIFIED" for i in result["issues"])


def test_an_item_with_no_candidate_is_flagged_and_never_confirmed() -> None:
    doc = packet()
    result = check(doc, answer(doc, [change(candidate_ids=["O9"], image_ids=[])], excluded=everything_else(("O1", "O2", "O3"))))
    item = result["changes"][0]
    assert "no_candidate" in item["flags"] and item["unclear"] is True
    assert {"NO_CANDIDATE", "UNKNOWN_CANDIDATE"} <= {i["code"] for i in result["issues"]}


def test_the_model_calling_a_value_unclear_keeps_it_unclear() -> None:
    doc = packet()
    claim = change(fields=[field(certainty="unclear")], limitation="знак нечитаем")
    item = check(doc, answer(doc, [claim], excluded=everything_else()))["changes"][0]
    assert item["unclear"] is True and item["tier_now"] == "from_text"


def test_a_candidate_in_no_list_is_not_reviewed_and_the_sheet_is_partial() -> None:
    doc = packet()
    result = check(doc, answer(doc, [change()]))
    assert result["coverage"]["not_reviewed"] == ["O2", "O3"]
    assert any(i["code"] == "NOT_REVIEWED" for i in result["issues"])
    assert state_of(result, doc) == "partial"


def test_a_question_makes_the_sheet_need_clarification_and_an_empty_answer_with_notes_is_partial() -> None:
    doc = packet()
    question = {"object": "Щит", "place": "", "question": "что именно сдвинуто?", "candidate_ids": ["O3"], "image_ids": []}
    result = check(doc, answer(doc, [change()], unresolved=[question], excluded=everything_else(("O2",))))
    assert state_of(result, doc) == "needs_clarification"
    empty = check(doc, answer(doc, [], excluded=everything_else(("O1", "O2", "O3"))))
    assert state_of(empty, doc) == "no_construction_changes"
    noted = dict(doc, engine=dict(doc["engine"], notes=["нет текстового слоя"]))
    assert state_of(empty, noted) == "partial"


def test_a_text_correction_without_its_second_representation_goes_to_the_questions() -> None:
    doc = packet()
    result = check(doc, answer(doc, [change(kind="text_correction")], excluded=everything_else()))
    assert result["changes"] == [] and len(result["unresolved"]) == 1
    assert result["unresolved"][0]["source"] == "program"
    assert any(i["code"] == "TEXT_CORRECTION_UNCHECKED" for i in result["issues"])


def test_a_text_correction_with_the_same_value_in_the_other_representation_stays_an_item() -> None:
    doc = packet()
    other = {"what": "схема щита", "value_a": "3", "value_b": "3", "image_id": "I2"}
    result = check(doc, answer(doc, [change(kind="text_correction", other_representation=other)], excluded=everything_else()))
    assert len(result["changes"]) == 1 and result["changes"][0]["kind"] == "text_correction"


def test_a_service_phrase_is_cut_and_an_item_with_nothing_left_is_set_aside() -> None:
    doc = packet()
    mixed = change(summary="Лк-1 — количество 2 → 3. Изменена дата выпуска в штампе.")
    result = check(doc, answer(doc, [mixed], excluded=everything_else()))
    assert result["changes"][0]["summary"] == "Лк-1 — количество 2 → 3."
    assert any(i["code"] == "SERVICE_PART_REMOVED" for i in result["issues"])
    only_service = change(summary="Изменена дата выпуска в штампе.")
    result = check(doc, answer(doc, [only_service], excluded=everything_else()))
    assert result["changes"] == []
    assert result["excluded"][0]["source"] == "program" and result["excluded"][0]["reason"] == "revision_mark"


def test_a_reason_or_a_judgement_is_cut_out_of_the_summary() -> None:
    doc = packet()
    reasoned = change(summary="Лк-1 — количество 2 → 3. Это сделано из-за ошибки в расчёте.")
    result = check(doc, answer(doc, [reasoned], excluded=everything_else()))
    assert result["changes"][0]["summary"] == "Лк-1 — количество 2 → 3."
    assert any(i["code"] == "REASON_REMOVED" for i in result["issues"])


def test_the_packet_id_with_a_typo_is_a_remark_and_a_foreign_one_is_refused() -> None:
    doc = packet()
    typo = answer(doc, [], excluded=everything_else(("O1", "O2", "O3")), packet_id=doc["packet_id"][:-1] + "x")
    assert check(doc, typo)["ok"] and any(i["code"] == "PACKET_ID_TYPO" for i in check(doc, typo)["issues"])
    foreign = answer(doc, [], packet_id="0" * 16)
    refused = check(doc, foreign)
    assert refused["ok"] is False and refused["issues"][0]["code"] == "MIXED_INPUT"
    wrong_part = answer(doc, [], part_id="P2")
    assert check(doc, wrong_part)["ok"] is False


def test_an_answer_out_of_the_schema_is_refused_and_a_check_never_changes_the_answer() -> None:
    doc = packet()
    assert check(doc, {"packet_id": doc["packet_id"]})["ok"] is False
    stuffed = answer(doc, [change()], excluded=everything_else(), extra="x")
    assert check(doc, stuffed)["ok"] is False
    good = answer(doc, [change(summary="Лк-1 — количество 2 → 3. Изменена дата выпуска в штампе.")], excluded=everything_else())
    before = copy.deepcopy(good)
    check(doc, good)
    assert good == before


def test_the_evidence_of_an_item_is_the_programs_box_and_names_the_row() -> None:
    doc = packet()
    item = check(doc, answer(doc, [change()], excluded=everything_else()))["changes"][0]
    assert item["evidence"] and item["evidence"][0]["side"] in {"A", "B"}
    assert item["evidence"][0]["box"] == [50.0, 120.0, 360.0, 140.0]
    assert "Лк-1" in item["evidence"][0]["what"]


def test_the_homoglyphs_of_the_two_alphabets_are_one_letter() -> None:
    assert norm("ВВГнг-LS 3х2,5") == norm("BBГнг-LS 3x2.5")
