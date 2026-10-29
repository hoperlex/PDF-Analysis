"""The stored description, its contract shapes, the Markdown of a sheet and the eleven states (`CMP-VC-AISHEET-01`)."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from auditmanager.api.schemas import models
from auditmanager.comparison.ai_sheets import description as dsc
from auditmanager.comparison.ai_sheets import packet as pk
from auditmanager.comparison.ai_sheets import views
from auditmanager.comparison.ai_sheets.check import check, state_of
from auditmanager.comparison.ai_sheets.model import AI_STATES, STATE_LABELS
from auditmanager.comparison.ai_sheets.repository import PairState


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
HEADER = {"sheet_pair_id": "ctp_1", "title": "План", "page_a": 1, "page_b": 1, "label_a": "версия №1", "label_b": "версия №2"}


def packet_document() -> dict[str, Any]:
    a, b = fx.table_pages("cpr_a", "cpr_b", "ver_a", "ver_b")
    facts = pk.SheetFacts(
        sheet_pair_id="ctp_1", title="План", project_title="Объект", designation="ЭМ-12", label_a="версия №1", label_b="версия №2",
        page_a=1, page_b=1, sheet_number="7", status="different", reasons=("NO_TEXT_LAYER",), page_profile_a="cpr_a",
        page_profile_b="cpr_b", version_a="ver_a", version_b="ver_b",
    )
    return pk.assemble(facts, fx.table_result(), fx.FakeMaterial({"cpr_a": a, "cpr_b": b}), render=False, xrefs=False).document


def described(*, after: str = "3", source: str = "text", covered: bool = True) -> tuple[dict[str, Any], dict[str, Any]]:
    doc = packet_document()
    change = {
        "object": "Люк Лк-1", "place": "таблица люков", "kind": "quantity", "summary": f"Лк-1 — количество 2 → {after}.",
        "fields": [{"name": "количество", "before": "2", "after": after, "unit": "шт", "source": source, "certainty": "confirmed"}],
        "members": [], "mapping": "one_to_one", "candidate_ids": ["O1"], "image_ids": ["I2"], "other_representation": NO_OTHER, "limitation": "",
    }
    excluded = [{"candidate_ids": [c], "reason": "formatting", "note": "оформление"} for c in (("O2", "O3") if covered else ())]
    answer = {"packet_id": doc["packet_id"], "part_id": "P1", "changes": [change], "unresolved": [], "excluded": excluded, "context_requests": []}
    checked = check(doc, answer)
    state = state_of(checked, doc)
    return doc, dsc.build_description(doc, checked, state, calls=[{"launch": 1}], launches=1, recorded=True)


def test_the_description_says_in_its_data_that_no_engineer_confirmed_it_and_that_it_is_recorded() -> None:
    _doc, description = described()
    assert description["engineer_confirmed"] is False and description["recorded"] is True
    assert description["disclaimer"] == "Описание составлено ИИ по исходным листам двух версий и инженером не подтверждено."
    assert description["schema"] == dsc.DESCRIPTION_SCHEMA and description["kind"] == "pair"


def test_the_description_names_raw_evidence_by_reference_and_leaves_it_as_it_was() -> None:
    doc, description = described()
    before = copy.deepcopy(doc)
    description = dsc.build_description(doc, check(doc, {"packet_id": doc["packet_id"], "part_id": "P1", "changes": [], "unresolved": [],
                                                           "excluded": [], "context_requests": []}), "partial", calls=[], launches=0,
                                        recorded=False)
    assert doc == before
    assert {c["id"] for c in description["diagnostics"]["candidates"]} == {"O1", "O2", "O3"}
    assert description["diagnostics"]["excluded_by_program"] == {"revision_tag": 1, "whitespace": 1, "engine_noise": 1, "service": 1}


def test_every_contract_shape_of_a_description_is_accepted_by_the_generated_models() -> None:
    _doc, description = described()
    for item in dsc.contract_changes(description):
        models.ComparisonAiChange.model_validate(item)
    for item in dsc.contract_unresolved({"unresolved": [{"question": "что сдвинуто?", "evidence": []}]}):
        models.ComparisonAiUnresolved.model_validate(item)
    for item in dsc.contract_excluded(description):
        models.ComparisonAiExcluded.model_validate(item)
    models.ComparisonAiCoverage.model_validate(dsc.contract_coverage(description))
    models.ComparisonAiDiagnostics.model_validate(dsc.contract_diagnostics(description))
    change = dsc.contract_changes(description)[0]
    assert (change["was"], change["now"], change["was_tier"], change["now_tier"], change["certainty"]) == ("2", "3", "from_text", "from_text", "confirmed")
    assert change["side"] in {"a", "b"} and change["box"] == {"x": 50.0, "y": 120.0, "width": 310.0, "height": 20.0}


def test_an_unverified_value_is_an_unclear_change_with_its_tier_and_its_reason_in_the_data() -> None:
    _doc, description = described(after="97")
    change = dsc.contract_changes(description)[0]
    assert (change["now_tier"], change["certainty"]) == ("unverified", "unclear")
    models.ComparisonAiChange.model_validate(change)
    assert "VALUE_UNVERIFIED" in dsc.contract_diagnostics(description)["issues"]


def test_a_single_sheet_description_is_served_as_changes_added_or_removed() -> None:
    checked = dsc.check_single(
        {"sheet_kind": "план этажа", "summary": "План 2 этажа.", "objects": [{"name": "щит", "detail": "ЩР-1"}, {"name": "", "detail": "x"}],
         "marks": ["ЩР-1"], "limitation": ""}, "План 2 этажа ЩР-1 щит",
    )
    single = dsc.build_single_description("removed", checked, packet_id="p" * 16, side="A", page=4, calls=[], launches=1, recorded=False)
    items = dsc.contract_changes(single)
    assert [i["kind"] for i in items] == ["removed", "removed"] and "was" in items[0] and "now" not in items[0]
    for item in items:
        models.ComparisonAiChange.model_validate(item)
    assert single["coverage"]["not_reviewed"] == [] and dsc.contract_unresolved(single) == []


def test_the_markdown_of_a_sheet_has_the_same_bytes_for_the_same_description() -> None:
    _doc, description = described()
    first = dsc.sheet_markdown(HEADER, description)
    again = dsc.sheet_markdown(HEADER, json.loads(json.dumps(description)))
    assert first == again and first.encode("utf-8") == again.encode("utf-8")
    assert first.endswith("\n") and "\r" not in first
    assert "1. **Люк Лк-1** — Лк-1 — количество 2 → 3." in first
    assert "_Описание составлено ИИ" in first and "Записанный (тестовый) ответ" in first
    assert "Состояние: Готово." in first


def test_the_markdown_marks_the_tier_of_a_value_and_lists_the_declared_items() -> None:
    _doc, description = described(after="97")
    text = dsc.sheet_markdown(HEADER, description, declared=[{"text": "Изм. 3: замена люка Лк-1"}])
    assert "→ 97 (не подтверждено)" in text
    assert "Заявлено проектировщиком в разрешении: Изм. 3: замена люка Лк-1" in text
    other = dsc.sheet_markdown(HEADER, description, declared=[])
    assert other != text, "the declared line belongs to the pair, not to the description"


def test_the_markdown_changes_only_with_the_description_never_with_the_clock_or_the_order_of_keys() -> None:
    _doc, description = described()
    shuffled = dict(reversed(list(description.items())))
    assert dsc.sheet_markdown(HEADER, shuffled) == dsc.sheet_markdown(HEADER, description)


def test_why_a_partial_sheet_is_to_be_checked() -> None:
    _doc, description = described(covered=False)
    assert description["state"] == "partial"
    assert "не разобрано 2" in dsc.review_reason(description)
    _doc2, calm = described()
    assert dsc.review_reason(calm) is None, "a done sheet has nothing to check"
    noted = {"state": "partial", "coverage": {"not_reviewed": []}, "engine": {"notes": ["нет текстового слоя"]}}
    assert dsc.review_reason(noted).startswith("ИИ строительных изменений не нашёл, но алгоритм сравнения оставил по листу пометки")


# -- the states -----------------------------------------------------------------------------------------------------------------------

PROMPT = "sheet-changes/1+abc"
TRN = "ctn_" + "0" * 25 + "1"
CTP = "ctp_" + "0" * 25 + "1"
VER_A, VER_B = "ver_" + "0" * 25 + "A", "ver_" + "0" * 25 + "B"
CPR_A, CPR_B = "cpr_" + "0" * 25 + "A", "cpr_" + "0" * 25 + "B"


def pair_state(**over: Any) -> PairState:
    base: dict[str, Any] = dict(
        pair_id=CTP, transition_id=TRN, pair_no=1, status="different", pair_state="done", transition_state="completed",
        result_id="csp_1", description_id=None, description_state=None, description_prompt=None, description_at=None,
        changes_count=0, unresolved_count=0, item_state=None, item_failure=None, item_at=None, job_state=None, job_id=None, row={},
    )
    return PairState(**(base | over))


def stored(state: str = "done", prompt: str = PROMPT, **over: Any) -> dict[str, Any]:
    return dict(description_id="csd_1", description_state=state, description_prompt=prompt,
                description_at=datetime(2026, 10, 29, tzinfo=timezone.utc), **over)


@pytest.mark.parametrize("over,expected", [
    ({}, "not_processed"),
    ({"status": "same"}, "engine_same"),
    ({"status": "same_zones_changed"}, "engine_same"),
    ({"item_state": "queued", "job_state": "queued"}, "queued"),
    ({"item_state": "queued", "job_state": "paused"}, "queued"),
    ({"item_state": "running", "job_state": "running"}, "running"),
    ({"item_state": "running", "job_state": "paused"}, "queued"),
    (stored("done"), "done"),
    (stored("needs_clarification"), "needs_clarification"),
    (stored("partial"), "partial"),
    (stored("no_construction_changes"), "no_construction_changes"),
    (stored("done", prompt="sheet-changes/0+old"), "stale"),
    ({"item_state": "failed", "job_state": "completed"}, "failed"),
    ({"item_state": "queued", "job_state": "failed"}, "failed"),
    ({"item_state": "cancelled", "job_state": "cancelled"}, "cancelled"),
    ({"item_state": "queued", "job_state": "cancelled"}, "cancelled"),
    ({"item_state": "queued", "job_state": "completed"}, "cancelled"),
    ({**stored("done"), "item_state": "running", "job_state": "running"}, "running"),
    ({**stored("done"), "item_state": "failed", "job_state": "completed"}, "done"),
])
def test_the_state_of_a_pair_is_derived_not_stored(over: dict[str, Any], expected: str) -> None:
    assert views.derive_state(pair_state(**over), current_prompt=PROMPT) == expected


def test_the_eleven_states_are_all_reachable_and_labelled() -> None:
    assert len(AI_STATES) == 11 and set(AI_STATES) == set(STATE_LABELS)
    reached = {
        views.derive_state(pair_state(**over), current_prompt=PROMPT)
        for over in ({}, {"status": "same"}, {"item_state": "queued", "job_state": "queued"}, {"item_state": "running", "job_state": "running"},
                     stored("done"), stored("needs_clarification"), stored("partial"), stored("no_construction_changes"),
                     stored("done", prompt="old"), {"item_state": "failed", "job_state": "completed"},
                     {"item_state": "cancelled", "job_state": "cancelled"})
    }
    assert reached == set(AI_STATES)
    assert STATE_LABELS["not_processed"] == "Не обработано" and STATE_LABELS["engine_same"] == "По данным сравнения изменений нет"


def test_not_processed_is_not_the_same_as_no_changes() -> None:
    assert views.derive_state(pair_state(), current_prompt=PROMPT) != views.derive_state(
        pair_state(**stored("no_construction_changes")), current_prompt=PROMPT)


def test_the_progress_of_a_transition_counts_sheets_changes_questions_errors_and_the_ones_to_check() -> None:
    rows = [
        (pair_state(pair_id="ctp_" + "0" * 25 + "1", **stored("done"), changes_count=2), "done"),
        (pair_state(pair_id="ctp_" + "0" * 25 + "2", **stored("needs_clarification"), changes_count=1, unresolved_count=3), "needs_clarification"),
        (pair_state(pair_id="ctp_" + "0" * 25 + "3", **stored("partial")), "partial"),
        (pair_state(pair_id="ctp_" + "0" * 25 + "4"), "not_processed"),
        (pair_state(pair_id="ctp_" + "0" * 25 + "5", item_state="failed", job_state="completed"), "failed"),
    ]
    progress = views.transition_progress(TRN, rows, {"calls": 4, "input_tokens": 900, "output_tokens": 300, "elapsed_ms": 61_900})
    models.ComparisonAiTransitionProgress.model_validate(progress)
    assert progress == {
        "transition_id": TRN, "sheets": 5, "done": 3, "changed": 2, "questions": 3, "errors": 1, "to_review": 1, "calls": 4,
        "input_tokens": 900, "output_tokens": 300, "seconds": 61,
    }


def test_the_review_list_holds_the_partial_sheets_and_the_one_sided_ones_and_nothing_else() -> None:
    row = {"a_version": VER_A, "a_number": 1, "a_sheet": "7", "a_title": "План", "a_scan": False, "b_version": VER_B, "b_number": 2,
           "b_sheet": "7", "b_title": "План", "b_scan": False, "page_a_profile_id": CPR_A, "page_b_profile_id": CPR_B}
    partial = views.review_item(pair_state(row=row, **stored("partial")), "partial")
    assert partial is not None and partial["kind"] == "to_check"
    models.ComparisonReviewSheet.model_validate(partial)
    added = views.review_item(pair_state(status="added", row={**row, "page_a_profile_id": None}), "not_processed")
    assert added is not None and added["kind"] == "added" and "page_a" not in added
    models.ComparisonReviewSheet.model_validate(added)
    assert views.review_item(pair_state(row=row, **stored("done")), "done") is None
    assert views.review_item(pair_state(row=row), "failed") is None


def test_a_pair_is_described_only_when_the_engine_found_a_difference_or_could_not_decide_or_the_sheet_is_alone() -> None:
    assert views.state_eligible(pair_state()) and views.state_eligible(pair_state(status="needs_review"))
    assert views.state_eligible(pair_state(status="added", result_id=None))
    assert not views.state_eligible(pair_state(status="same")) and not views.state_eligible(pair_state(status="unmatched", result_id=None))
    assert not views.state_eligible(pair_state(pair_state="failed")) and not views.state_eligible(pair_state(result_id=None))
