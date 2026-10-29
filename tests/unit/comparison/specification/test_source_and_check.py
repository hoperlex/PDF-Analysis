"""The packet a model reads and the program's check of what it answers (`CMP-VC-SPEC-01`, part B).

The checks port ``specification_source.validate_extraction`` of the original (PDF-proverka at ``23f379fd``): a value is confirmed only
by the exact quote of the line it came from, a line is accounted for or the side is incomplete, and one unconfirmed value makes the
whole side incomplete so that nothing of it is ever compared. The oracle is a faithful model written in the conftest; every check is
shown failing on an answer that breaks exactly it.
"""

from __future__ import annotations

import copy

from auditmanager.comparison.specification import check, prompt, source as source_module


def _two_pages(drawn):
    first = drawn.Page()
    first.merged("Раздел 1. Щиты")
    first.row({"pos": "1", "mark": "ЩО-1", "name": "Щит освещения", "quantity": "1", "mass": "45,0"})
    first.row({"pos": "2", "mark": "АВ-16", "name": "Выключатель 16 А", "quantity": "12", "mass": "0,15"})
    second = drawn.Page()
    second.row({"pos": "3", "mark": "КБ-3", "name": "Кабель", "quantity": "320", "mass": "0,12", "note": "по проекту"})
    return first, second


def test_the_packet_numbers_its_lines_across_the_pages_and_repeats_the_header(drawn, whole) -> None:
    source = whole.source_of(*_two_pages(drawn))
    assert source["complete"] is True and [b["page"] for b in source["blocks"]] == [1, 2]
    numbers = [ln["line"] for b in source["blocks"] for ln in b["lines"]]
    assert numbers == list(range(1, len(numbers) + 1))
    assert source["blocks"][0]["lines"][0]["text"].startswith("| Поз. | Тип, марка, обозначение | Наименование |")
    assert source["blocks"][1]["lines"][0]["text"] == source["blocks"][0]["lines"][0]["text"]  # a repeated header is on every page
    assert "Раздел 1. Щиты" in [ln["text"] for ln in source["blocks"][0]["lines"]]  # a title across the table is a plain line


def test_the_packet_carries_nothing_the_user_typed_so_the_same_text_has_the_same_key(drawn, whole) -> None:
    a = whole.source_of(*_two_pages(drawn))
    b = whole.source_of(*_two_pages(drawn))
    assert a["source_sha256"] == b["source_sha256"] and prompt.prompt_for(a) == prompt.prompt_for(b)
    assert prompt.content_key("prj_A", a["source_sha256"]) == prompt.content_key("prj_A", b["source_sha256"])
    assert prompt.content_key("prj_A", a["source_sha256"]) != prompt.content_key("prj_B", a["source_sha256"])
    assert prompt.content_key("prj_A", a["source_sha256"]) != prompt.content_key("prj_A", a["source_sha256"], "cmp-whole-spec/2")


def test_a_packet_over_the_cap_is_not_cut_and_not_split_it_is_incomplete(drawn, monkeypatch) -> None:
    monkeypatch.setattr(source_module, "MAX_SOURCE_CHARS", 100)
    page = drawn.Page()
    page.row({"pos": "1", "mark": "М-1", "name": "Щит", "quantity": "1"})
    parsed = page.parse()
    source = source_module.build_source([{"page": 1, "sheet": "1", "name": "", "columns": parsed["columns"], "rows": parsed["rows"]}])
    assert source["complete"] is False and "larger than one request holds" in source["issues"][-1]
    result = check.check_extraction(source, {"blocks": []})
    assert result["complete"] is False and result["rows"] == [] and result["reason"] == check.REASON_SOURCE


def test_a_faithful_answer_is_confirmed_and_every_value_is_the_text_of_the_sheet(drawn, whole) -> None:
    source = whole.source_of(*_two_pages(drawn))
    result = check.check_extraction(source, whole.faithful_answer(source))
    assert result["issues"] == [] and result["complete"] is True and result["reason"] is None
    assert [r["fields"]["pos"] for r in result["rows"]] == ["1", "2", "3"]
    assert result["rows"][0]["section"] == "Раздел 1. Щиты" and result["rows"][2]["fields"]["note"] == "по проекту"
    assert result["coverage"] == {"blocks_total": 2, "blocks_covered": 2, "rows_total": 3, "rows_unresolved": 0}
    assert all(s["page"] in (1, 2) and s["quote"] for r in result["rows"] for s in r["sources"])


def _broken(drawn, whole, edit):
    source = whole.source_of(*_two_pages(drawn))
    answer = copy.deepcopy(whole.faithful_answer(source))
    edit(answer)
    return check.check_extraction(source, answer)


def _refused(result, fragment: str) -> None:
    assert result["complete"] is False and result["rows"] == [] and result["reason"] == check.REASON_ANSWER
    assert any(fragment in issue for issue in result["issues"]), result["issues"]


def test_a_quote_that_is_not_in_the_line_is_never_confirmed(drawn, whole) -> None:
    """The mutation proof of the rule: a position whose quote the text does not contain is not a row, and the side that holds it
    yields no row at all, so no change can be built on it."""
    def edit(answer):
        answer["blocks"][0]["rows"][0]["evidence"][0]["quote"] = "| 1 | ЩО-1 | Щит освещения | 2 | 45,0 | |"

    _refused(_broken(drawn, whole, edit), "not an exact source substring")


def test_a_value_the_quotes_do_not_contain_is_fabricated(drawn, whole) -> None:
    def edit(answer):
        answer["blocks"][0]["rows"][1]["fields"]["quantity"] = "17"

    _refused(_broken(drawn, whole, edit), "Fabricated or ungrounded quantity")


def test_a_number_is_not_confirmed_by_a_longer_number_that_contains_it(drawn, whole) -> None:
    def edit(answer):
        answer["blocks"][0]["rows"][1]["fields"]["quantity"] = "1"  # the line says 12

    _refused(_broken(drawn, whole, edit), "Fabricated or ungrounded quantity")


def test_a_lost_row_makes_the_side_incomplete_and_the_coverage_says_which(drawn, whole) -> None:
    def edit(answer):
        answer["blocks"][0]["rows"].pop()

    result = _broken(drawn, whole, edit)
    _refused(result, "Markdown table data line is not extracted as a row")
    assert result["coverage"]["rows_unresolved"] == 1 and result["coverage"]["blocks_covered"] == 1
    assert any(b["unclassified_lines"] for b in result["source_coverage"])


def test_a_data_row_cannot_be_hidden_as_a_section_or_a_note(drawn, whole) -> None:
    def hide(answer):
        row = answer["blocks"][0]["rows"].pop()
        answer["blocks"][0]["ignored"].append({"line": row["evidence"][0]["line"], "reason": "section"})

    _refused(_broken(drawn, whole, hide), "Data-like line hidden as section")

    def discard(answer):
        row = answer["blocks"][0]["rows"].pop()
        answer["blocks"][0]["ignored"].append({"line": row["evidence"][0]["line"], "reason": "note"})

    _refused(_broken(drawn, whole, discard), "Substantive note may not be discarded")


def test_a_line_is_claimed_by_one_position_at_most(drawn, whole) -> None:
    def edit(answer):
        answer["blocks"][0]["rows"].append(copy.deepcopy(answer["blocks"][0]["rows"][0]))

    result = _broken(drawn, whole, edit)
    assert any("claimed by multiple rows" in i or "Duplicate extraction" in i for i in result["issues"]) and result["complete"] is False


def test_the_answer_has_exactly_the_assigned_blocks_in_the_closed_shape(drawn, whole) -> None:
    _refused(_broken(drawn, whole, lambda a: a["blocks"].pop()), "do not exactly match")
    _refused(_broken(drawn, whole, lambda a: a.update(extra=1)), "unexpected top-level keys")
    _refused(_broken(drawn, whole, lambda a: a["blocks"][0].update(extra=1)), "Malformed extraction block shape")
    _refused(_broken(drawn, whole, lambda a: a["blocks"][0]["rows"][0]["fields"].pop("note")), "Malformed fields")
    source = whole.source_of(*_two_pages(drawn))
    for payload in (None, [], {"blocks": "x"}, {}):
        assert check.check_extraction(source, payload)["complete"] is False


def test_a_section_the_text_does_not_name_is_ungrounded(drawn, whole) -> None:
    def edit(answer):
        answer["blocks"][0]["rows"][0]["section"] = "Раздел, которого нет в тексте"

    _refused(_broken(drawn, whole, edit), "Ungrounded section")


def test_a_position_may_continue_on_the_next_page_with_the_quotes_of_both(drawn, whole) -> None:
    first = drawn.Page()
    first.row({"pos": "1", "mark": "М-1", "name": "Светильник светодиодный", "quantity": "5"})
    second = drawn.Page()
    second.row({"name": "с аварийным питанием"})
    source = whole.source_of(first, second)
    answer = whole.faithful_answer(source)
    # the continuation row of page 2 is one position with the row of page 1: the model joins them
    row = answer["blocks"][0]["rows"][0]
    continued = answer["blocks"][1]["rows"].pop()
    row["fields"]["name"] = "Светильник светодиодный с аварийным питанием"
    row["evidence"].append(continued["evidence"][0])
    result = check.check_extraction(source, answer)
    assert result["issues"] == [] and len(result["rows"]) == 1
    assert [s["page"] for s in result["rows"][0]["sources"]] == [1, 2]
