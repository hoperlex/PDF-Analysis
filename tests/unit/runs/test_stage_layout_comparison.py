"""`HOSTS-CMP-01`: the comparison cells of the stage layout -- the four kinds, the two sets' tables, the validation and what is stored.

The cells are pure data of the layout (ADR-0028 decision 19): one ``<kind>:main`` cell for each of the four kinds of comparison work that call a
model, in the same revision as the six rows and in no run's plan. No database.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from auditmanager.analysis.public import CellSettings, COMPARISON_TIMEOUT_SECONDS
from auditmanager.runs import stage_layout as layout
from auditmanager.runs import stage_layout_store as store
from auditmanager.runs.public import COMPARISON_KINDS, LayoutRevisionRow
from auditmanager.shared.errors import DomainError, ErrorCode

from .stage_layout_fakes import NOW, with_revision, MemoryStore

KINDS = ("comparison_pair_check", "comparison_sheet_changes", "comparison_spec", "comparison_report")


def refused(call, *args, **kwargs) -> dict:
    with pytest.raises(DomainError) as caught:
        call(*args, **kwargs)
    assert caught.value.code is ErrorCode.VALIDATION_FAILED
    return caught.value.detail_fields


def table(kit: str) -> dict[str, tuple[str, str, int]]:
    return {c.row: (c.model_id, c.effort, c.timeout_seconds) for c in layout.comparison_preset_cells(kit)}


def test_the_kinds_are_the_four_that_call_a_model_and_not_the_stage_review():
    assert layout.COMPARISON_KINDS == KINDS == COMPARISON_KINDS
    assert "comparison_stage_review" not in layout.COMPARISON_KINDS, "an enum value with no handler (CMP-SEAL-C4)"
    assert set(layout.COMPARISON_KINDS) <= {"comparison_pair_check", "comparison_sheet_changes", "comparison_spec", "comparison_report"}
    assert not set(layout.COMPARISON_KINDS) & set(layout.STAGE_ROWS), "a kind is never a row: a run's plan holds the rows only"


def test_each_set_has_the_table_of_the_task_with_the_originals_windows_and_no_answer_limit():
    assert table("codex_only") == {
        "comparison_pair_check": ("gpt-6-luna", "high", 900),
        "comparison_sheet_changes": ("gpt-6.1-sol", "high", 1_800),
        "comparison_spec": ("gpt-6-luna", "high", 900),
        "comparison_report": ("gpt-6.1-sol", "high", 2_400),
    }
    assert table("claude_only") == {
        kind: ("claude-sonnet-5-5", "high", seconds) for kind, seconds in (
            ("comparison_pair_check", 900), ("comparison_sheet_changes", 1_800), ("comparison_spec", 900), ("comparison_report", 2_400))
    }
    assert dict(COMPARISON_TIMEOUT_SECONDS) == {kind: seconds for kind, (_, _, seconds) in table("codex_only").items()}
    assert not any(hasattr(cell, "max_output_tokens") for cell in layout.comparison_preset_cells("codex_only"))
    assert [c.cell_key for c in layout.comparison_preset_cells("codex_only")] == [f"{kind}:main" for kind in KINDS]


def test_the_tables_are_what_the_catalogue_offers_and_the_sets_validate_as_they_are():
    for kit in ("claude_only", "codex_only"):
        cells = layout.comparison_preset_cells(kit)
        assert layout.validate_comparison_cells(cells) == cells
        assert layout.require_valid_comparison_cells(kit, cells) == cells


def test_only_the_two_sets_have_a_table():
    with pytest.raises(ValueError):
        layout.comparison_preset_cells("custom")


def test_the_cells_of_a_revision_are_what_it_stored_else_its_sets_table_else_none():
    stored = tuple(replace(cell, effort="medium") for cell in layout.comparison_preset_cells("codex_only"))
    assert layout.comparison_cells_in_force("codex_only", stored) == stored
    assert layout.comparison_cells_in_force("codex_only", None) == layout.comparison_preset_cells("codex_only")
    assert layout.comparison_cells_in_force("claude_only", ()) == layout.comparison_preset_cells("claude_only")
    # « Свой набор » has no table: the comparison kinds have no cell, and a comparison is refused rather than served by an unchosen model
    assert layout.comparison_cells_in_force("custom", None) is None
    assert layout.comparison_cells_in_force("custom", stored) == stored
    # whatever order the store keeps them in, they come back in the order of the kinds
    assert layout.comparison_cells_in_force("custom", tuple(reversed(stored))) == stored


def test_a_cell_of_every_kind_is_required_once_each():
    cells = list(layout.comparison_preset_cells("codex_only"))
    assert refused(layout.validate_comparison_cells, cells[:3]) == {"field": "comparison_cells", "constraint": "cell_missing"}
    assert refused(layout.validate_comparison_cells, [*cells, cells[0]])["constraint"] == "cell_repeated"
    assert refused(layout.validate_comparison_cells, [])["constraint"] == "cell_missing"


@pytest.mark.parametrize("key,constraint", [
    ("comparison_stage_review:main", "unknown_cell"),   # no handler, no call site: never offered
    ("text:main", "unknown_cell"),                      # a row of the analysis is not a comparison kind
    ("comparison_spec:judge", "role_not_offered"),      # a kind has one answer
    ("comparison_spec", "unknown_cell"),
])
def test_a_cell_that_is_not_a_kind_and_main_is_refused(key, constraint):
    cells = [*layout.comparison_preset_cells("codex_only"), CellSettings(key, "gpt-6-astra", "high")]
    assert refused(layout.validate_comparison_cells, cells)["constraint"] == constraint


@pytest.mark.parametrize("edit,constraint", [
    ({"model_id": "claude-haiku-5"}, "model_not_in_catalogue"),
    ({"model_id": "gpt-6-terra"}, "model_not_in_catalogue"),   # a model that is not a pin (the original's gpt-6-luna is one since R-153m / D-667)
    ({"effort": "xhigh"}, "effort_not_offered_for_model"),
    ({"effort": "max"}, "effort_not_offered_for_model"),
    ({"model_id": "claude-opus-5-5", "effort": "low"}, "effort_not_offered_for_model"),
])
def test_a_pair_the_catalogue_does_not_offer_is_refused(edit, constraint):
    cells = list(layout.comparison_preset_cells("codex_only"))
    cells[2] = replace(cells[2], **edit)
    assert refused(layout.validate_comparison_cells, cells) == {"field": "comparison_cells", "constraint": constraint}


def test_a_named_set_must_be_its_table_in_model_and_effort():
    claude = layout.comparison_preset_cells("claude_only")
    assert refused(layout.require_valid_comparison_cells, "codex_only", claude) == {
        "field": "kit", "constraint": "kit_does_not_match_cells"}
    assert layout.require_valid_comparison_cells("claude_only", claude) == claude
    assert layout.require_valid_comparison_cells("custom", claude) == claude, "« Свой набор » is whatever was saved"
    mixed = tuple(replace(cell, effort="medium") if cell.row == "comparison_spec" else cell for cell in claude)
    assert refused(layout.require_valid_comparison_cells, "claude_only", mixed)["constraint"] == "kit_does_not_match_cells"


def test_the_wire_names_the_kind_and_no_key():
    wire = layout.comparison_cells_to_wire(layout.comparison_preset_cells("codex_only"))
    assert [sorted(item) for item in wire] == [["effort", "model_id", "work_kind"]] * 4, "no answer limit and no timeout on the wire"
    assert [item["work_kind"] for item in wire] == list(KINDS)


# -- what is stored: one array, kept apart on the way out -----------------------------------------------------------------------


def stored(kit: str = "codex_only", *, comparison: bool = True) -> list[dict]:
    cells = [*layout.preset_cells(kit), *(layout.comparison_preset_cells(kit) if comparison else ())]
    return layout.cells_to_wire(cells)


def test_a_revision_stored_before_the_limits_left_is_read_and_its_numbers_are_not():
    """`R-153n`, `R-153o`: an old revision holds an answer limit and a timeout per cell. They are not read: the cells are the same cells,
    and their windows are the constants of their rows and kinds."""
    old = [{**item, "max_output_tokens": 77, "timeout_seconds": 5} for item in stored()]
    rows, comparison = store._cells_of(old)
    assert comparison == layout.comparison_preset_cells("codex_only") and rows == layout.preset_cells("codex_only")
    assert {c.row: c.timeout_seconds for c in comparison} == dict(COMPARISON_TIMEOUT_SECONDS), "never the 5 the old revision stored"
    assert {c.row: c.timeout_seconds for c in rows}["cross_check"] == 3600
    assert layout.cells_to_wire([*rows, *comparison]) == stored(), "and what is written again carries neither"


def test_a_stored_array_is_split_into_the_rows_and_the_comparison_cells():
    rows, comparison = store._cells_of(stored())
    assert [c.row for c in rows] == [c.row for c in layout.preset_cells("codex_only")]
    assert comparison == layout.comparison_preset_cells("codex_only")
    assert not {c.row for c in rows} & set(KINDS), "a reader of a run's plan never meets a kind"
    rows_only, none = store._cells_of(stored(comparison=False))
    assert rows_only == rows and none is None, "a revision made before the cells existed stores none"


def test_a_row_that_stores_a_kind_has_it_in_a_row_of_its_own_in_the_array():
    # the cell key pattern of migration 0062 admits <kind>:main and the array bound (32) holds six rows, the ensemble and four kinds
    document = stored("claude_only")
    assert len(document) <= 32
    assert {item["row"] for item in document if item["row"] in KINDS} == set(KINDS)
    assert all(item["role"] == "main" and item["cell_key"] == f"{item['row']}:main" for item in document if item["row"] in KINDS)


def test_a_revision_row_resolves_its_cells_and_the_plan_never_holds_a_kind():
    revision = store._revision({
        "layout_revision_id": "slr_01M2545JSD15ETSNNV904X991A", "revision_no": 3, "kit": "codex_only", "cells": stored(),
        "created_at": NOW, "created_by": "usr_x"})
    assert isinstance(revision, LayoutRevisionRow)
    assert revision.comparison_cell("comparison_report") == layout.comparison_preset_cells("codex_only")[3]
    assert revision.comparison_cell("comparison_stage_review") is None
    # the draft of a start reads ``revision.cells``: six rows, and every phase of the extended review finds its own
    assert {c.row for c in revision.cells} == set(layout.STAGE_ROWS)
    assert set(layout.rows_in_use({"enabled": True, "plan_version": "extended-review-v3"})) == set(layout.STAGE_ROWS)
    older = store._revision({**{
        "layout_revision_id": "slr_01M2545JSD15ETSNNV904X991A", "revision_no": 2, "kit": "claude_only", "cells": stored("claude_only", comparison=False),
        "created_at": NOW, "created_by": "usr_x"}})
    assert older.comparison_cells is None and older.comparison_cells_in_force == layout.comparison_preset_cells("claude_only")
    custom = store._revision({
        "layout_revision_id": "slr_01M2545JSD15ETSNNV904X991A", "revision_no": 1, "kit": "custom", "cells": stored("claude_only", comparison=False),
        "created_at": NOW, "created_by": "usr_x"})
    assert custom.comparison_cells_in_force is None and custom.comparison_cell("comparison_spec") is None


def test_an_appended_revision_keeps_the_rows_and_the_kinds_apart():
    memory = MemoryStore()
    row = with_revision(memory, layout.preset_cells("codex_only"), "codex_only")
    assert row.comparison_cells is None
    row = memory.append_revision(None, kit="codex_only", cells=layout.preset_cells("codex_only"), created_by="u",
                                 comparison_cells=layout.comparison_preset_cells("codex_only"))
    assert row.comparison_cells == layout.comparison_preset_cells("codex_only") and len(row.cells) == len(layout.preset_cells("codex_only"))
