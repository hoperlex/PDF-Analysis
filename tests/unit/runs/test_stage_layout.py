"""`HOSTS-LAYOUT-01`: the six rows, the two sets cell by cell, the closed validation and the plan's digest and immutability."""

from __future__ import annotations

from dataclasses import replace

import pytest

from auditmanager.analysis.public import CellSettings, accepted_reported, model_catalogue
from auditmanager.runs import stage_layout as layout
from auditmanager.shared.errors import DomainError, ErrorCode

# The sets of ADR-0028 decision 12, cell by cell: row -> (role, model, effort) of each of its cells. The blocks row is an ensemble.
CLAUDE = {
    "text": [("main", "claude-sonnet-5-5", "medium")],
    "blocks": [("leg1", "claude-opus-5-5", "medium"), ("judge", "claude-sonnet-5-5", "medium")],
    "cross_check": [("main", "claude-sonnet-5-5", "medium")], "norms": [("main", "claude-sonnet-5-5", "medium")],
    "review": [("main", "claude-sonnet-5-5", "medium")], "correction": [("main", "claude-sonnet-5-5", "medium")],
}
CODEX = {
    "text": [("main", "gpt-6.1-sol", "medium")],
    "blocks": [("leg1", "gpt-6-astra", "medium"), ("leg2", "gpt-6-sol", "medium"), ("judge", "gpt-6.1-sol", "medium")],
    "cross_check": [("main", "gpt-6-sol", "medium")], "norms": [("main", "gpt-6-astra", "medium")],
    "review": [("main", "gpt-6-sol", "medium")], "correction": [("main", "gpt-6.1-sol", "medium")],
}


def _refused(constraint: str, call, *args, **kwargs) -> None:
    with pytest.raises(DomainError) as caught:
        call(*args, **kwargs)
    assert caught.value.code is ErrorCode.VALIDATION_FAILED
    assert caught.value.detail_fields.get("constraint") == constraint


def test_the_rows_are_the_six_in_order():
    assert layout.STAGE_ROWS == ("text", "blocks", "cross_check", "norms", "review", "correction")
    assert set(layout.ROW_LABELS) == set(layout.STAGE_ROWS)


@pytest.mark.parametrize("kit,table", [("claude_only", CLAUDE), ("codex_only", CODEX)])
def test_a_set_is_the_adr_table_cell_by_cell(kit, table):
    cells = layout.preset_cells(kit)
    assert [(c.cell_key, c.model_id, c.effort) for c in cells] == [
        (f"{row}:{role}", model, effort) for row in layout.STAGE_ROWS for role, model, effort in table[row]]
    assert layout.kit_of(cells) == kit
    layout.require_valid_layout(kit, cells)


def test_the_default_limits_are_the_code_constants():
    cells = {c.row: c for c in layout.preset_cells("claude_only")}
    assert {row: c.max_output_tokens for row, c in cells.items()} == {
        "text": 16000, "blocks": 6000, "cross_check": 6000, "norms": 12000, "review": 12000, "correction": 12000}
    assert {c.timeout_seconds for c in cells.values()} == {1800}


def test_the_claude_set_is_named_plainly_now_that_the_ensemble_has_landed():
    assert layout.BLOCKS_ENSEMBLE_LANDED is True
    assert layout.KIT_LABELS["claude_only"] == "Только Claude"
    assert layout.KIT_LABELS["codex_only"] == "Только Codex" and layout.KIT_LABELS["custom"] == "Свой набор"


def test_every_phase_has_one_row_and_one_label():
    assert layout.row_of_phase("block_analysis") == "blocks"
    assert layout.row_of_phase("norm_verification:3") == "norms"
    assert layout.row_of_phase("project_parameters") == layout.row_of_phase("comprehensive_analysis") == "cross_check"
    assert layout.row_of_phase("merge") is None and layout.row_of_phase("report") is None
    assert set(layout.PHASE_LABELS) == set(layout.PHASE_ROWS) | set(layout.MODELLESS_PHASES)
    assert {phase for phases in layout.ROW_PHASES.values() for phase in phases} == set(layout.PHASE_ROWS)


def _edited(kit, row, **changes):
    """The set with every cell of ``row`` changed (the blocks row of an ensemble has two or three)."""
    return tuple(replace(c, **changes) if c.row == row else c for c in layout.preset_cells(kit))


def _blocks_as(kit, *cells):
    """The set with its blocks cells replaced by ``cells`` (role, model, effort)."""
    others = tuple(c for c in layout.preset_cells(kit) if c.row != "blocks")
    return tuple(sorted(others + tuple(CellSettings(f"blocks:{role}", model, effort, 6000, 1800) for role, model, effort in cells),
                        key=layout._position))


@pytest.mark.parametrize("row,changes,constraint", [
    ("text", {"model_id": "claude-haiku-5"}, "model_not_in_catalogue"),
    ("text", {"model_id": "claude-sonnet-5"}, "model_not_in_catalogue"),      # an older pin, never offered
    ("text", {"effort": "xhigh"}, "effort_not_offered_for_model"),
    ("text", {"effort": "max"}, "effort_not_offered_for_model"),
    ("blocks", {"effort": "low"}, "effort_not_offered_for_model"),             # Opus low (the leg of the Claude ensemble)
    ("norms", {"effort": "ultra"}, "effort_not_offered_for_model"),
    ("text", {"max_output_tokens": 0}, "limit_out_of_range"),
    ("text", {"max_output_tokens": 65537}, "limit_out_of_range"),
    ("text", {"timeout_seconds": 7201}, "limit_out_of_range"),
])
def test_a_layout_outside_the_catalogue_is_refused(row, changes, constraint):
    _refused(constraint, layout.validate_cells, _edited("claude_only", row, **changes))


def test_opus_low_is_refused_but_sonnet_low_is_not():
    layout.validate_cells(_edited("claude_only", "norms", effort="low"))


def test_the_blocks_row_is_a_listed_scheme_only():
    # A single Claude on the blocks is never offered, even in a custom set; the Astra single is, as the original allows it.
    for model in ("claude-sonnet-5-5", "claude-opus-5-5"):
        _refused("block_scheme_not_listed", layout.validate_cells, _blocks_as("claude_only", ("main", model, "medium")))
    _refused("block_scheme_not_listed", layout.validate_cells, _blocks_as("claude_only", ("main", "gpt-6-sol", "medium")))
    assert [c.cell_key for c in layout.validate_cells(_blocks_as("claude_only", ("main", "gpt-6-astra", "medium")))] == [
        "text:main", "blocks:main", "cross_check:main", "norms:main", "review:main", "correction:main"]
    # the legs and the judge are not edited one by one: every scheme is whole, in its models and its efforts
    _refused("block_scheme_not_listed", layout.validate_cells, _edited("claude_only", "blocks", model_id="claude-sonnet-5-5"))
    _refused("block_scheme_not_listed", layout.validate_cells, _blocks_as(
        "claude_only", ("leg1", "claude-opus-5-5", "medium"), ("judge", "claude-sonnet-5-5", "high")))
    _refused("block_scheme_not_listed", layout.validate_cells, _blocks_as("claude_only", ("leg1", "claude-opus-5-5", "medium")))
    _refused("block_scheme_not_listed", layout.validate_cells, _blocks_as(
        "claude_only", ("leg1", "claude-opus-5-5", "medium"), ("leg2", "claude-opus-5-5", "medium"), ("judge", "claude-sonnet-5-5", "medium")))
    _refused("block_scheme_not_listed", layout.validate_cells, _blocks_as(
        "codex_only", ("leg1", "gpt-6-sol", "medium"), ("leg2", "gpt-6-astra", "medium"), ("judge", "gpt-6.1-sol", "medium")))   # legs swapped
    _refused("block_scheme_not_listed", layout.validate_cells, _blocks_as(
        "codex_only", ("main", "gpt-6-astra", "medium"), ("judge", "gpt-6.1-sol", "medium")))
    # the same cells given in another order are the same scheme
    shuffled = tuple(reversed(layout.preset_cells("codex_only")))
    assert [c.cell_key for c in layout.validate_cells(shuffled) if c.row == "blocks"] == ["blocks:leg1", "blocks:leg2", "blocks:judge"]
    assert layout.kit_of(shuffled) == "codex_only"
    for kit in ("claude_only", "codex_only"):        # both ensembles of the sets are on the list
        layout.require_valid_layout(kit, layout.preset_cells(kit))


def test_the_cells_are_the_main_cell_of_each_row_and_the_cells_of_one_blocks_scheme():
    cells = layout.preset_cells("claude_only")
    _refused("cell_missing", layout.validate_cells, tuple(c for c in cells if c.row != "norms"))
    _refused("cell_missing", layout.validate_cells, tuple(c for c in cells if c.row != "blocks"))
    _refused("cell_repeated", layout.validate_cells, cells + (cells[0],))
    _refused("cell_repeated", layout.validate_cells, cells + (cells[1],))
    _refused("unknown_cell", layout.validate_cells, cells + (CellSettings("nothing:main", "claude-sonnet-5-5", "low", 1, 1),))
    _refused("unknown_cell", layout.validate_cells, cells + (CellSettings("blocks:third", "claude-sonnet-5-5", "low", 1, 1),))
    # only the blocks row has legs and a judge; every other row is one `main` cell
    for role in ("judge", "leg1", "leg2"):
        _refused("role_not_offered", layout.validate_cells, cells + (CellSettings(f"text:{role}", "claude-sonnet-5-5", "medium", 6000, 1800),))
    _refused("block_scheme_not_listed", layout.validate_cells,
             cells + (CellSettings("blocks:main", "gpt-6-astra", "medium", 6000, 1800),))


def test_a_named_kit_must_match_its_table_and_anything_else_is_custom():
    edited = _edited("claude_only", "text", model_id="claude-opus-5-5")
    assert layout.kit_of(edited) == "custom"
    _refused("kit_does_not_match_cells", layout.require_valid_layout, "claude_only", edited)
    assert layout.require_valid_layout("custom", edited)
    _refused("unknown_kit", layout.require_valid_layout, "mine", edited)
    # a changed timeout alone keeps the set's models
    assert layout.kit_of(_edited("codex_only", "text", timeout_seconds=60)) == "codex_only"


def _plan(access="subscription", **kw):
    cells = tuple(replace(c, access=access) for c in layout.preset_cells("claude_only"))
    return layout.FrozenStagePlan("slr_01M2545JSD15ETSNNV904X991J", "claude_only", cells, **kw)


def test_the_plan_round_trips_and_its_digest_follows_every_cell():
    plan = _plan()
    assert layout.parse_plan(plan.to_json()) == plan
    assert plan.digest == layout.parse_plan(plan.to_json()).digest and len(plan.digest) == 64
    other = layout.FrozenStagePlan(plan.layout_revision_id, plan.kit, tuple(
        replace(c, effort="high") if c.row == "text" else c for c in plan.cells))
    assert other.digest != plan.digest
    assert plan.models == ("claude-sonnet-5-5", "claude-opus-5-5")        # the judge is Sonnet too: three cells' worth of models is two
    assert plan.access == "subscription"


def test_a_plan_is_immutable_and_a_layout_revision_does_not_move_it():
    plan = _plan()
    with pytest.raises(Exception):
        plan.kit = "custom"  # type: ignore[misc]
    frozen_json = plan.to_json()
    # an administrator revises the layout afterwards: the stored document of the run is not touched
    revised = layout.preset_cells("codex_only")
    assert layout.kit_of(revised) == "codex_only"
    assert layout.parse_plan(frozen_json) == plan


def test_a_plan_carries_one_access_per_model_and_every_cell_its_access():
    cells = list(_plan().cells)
    cells[0] = replace(cells[0], access="api")           # text is Sonnet; cross_check Sonnet stays subscription
    with pytest.raises(ValueError):
        layout.FrozenStagePlan("slr_01M2545JSD15ETSNNV904X991J", "claude_only", tuple(cells))
    with pytest.raises(ValueError):
        layout.FrozenStagePlan("slr_01M2545JSD15ETSNNV904X991J", "claude_only", layout.preset_cells("claude_only"))
    mixed = tuple(replace(c, access="api" if c.model_id == "claude-opus-5-5" else "subscription") for c in layout.preset_cells("claude_only"))
    assert layout.FrozenStagePlan("slr_01M2545JSD15ETSNNV904X991J", "claude_only", mixed).access == "mixed"


def test_a_plan_that_is_not_what_was_written_is_refused():
    document = _plan().to_json()
    document["cells"][0]["model_id"] = "claude-sonnet-5-5 "   # still parses; the digest check is what holds the shape
    bad = dict(document, format="stage-plan/9")
    for broken in (bad, {}, None, {**document, "cells": [{"cell_key": "text:main"}]}, {**document, "extra": 1}):
        with pytest.raises(DomainError) as caught:
            layout.parse_plan(broken)
        assert caught.value.code is ErrorCode.INTERNAL_ERROR


def test_a_run_binds_only_the_rows_it_will_call():
    assert layout.rows_in_use(None) == ("text",)
    assert layout.rows_in_use({"enabled": True, "plan_version": "extended-review-v3"}) == layout.STAGE_ROWS
    assert layout.rows_in_use({"enabled": True, "plan_version": "extended-review-v2"}) == ("text", "blocks", "cross_check", "norms")
    narrowed = _plan().restricted_to(layout.rows_in_use({"enabled": True, "plan_version": "extended-review-v2"}))
    assert narrowed.rows == ("text", "blocks", "cross_check", "norms") and not narrowed.has_cell("review:main")


def test_the_catalogue_is_the_only_source_of_the_pairs_and_of_the_reported_names():
    catalogue = model_catalogue()
    for kit in ("claude_only", "codex_only"):
        for cell in layout.preset_cells(kit):
            catalogue.require_pair(cell.model_id, cell.effort)
    assert accepted_reported("claude-opus-5-5", "claude-opus-5-5[1m]")
    for bad in ("claude-opus-5-5-20261001", "Claude-Opus-5-5", " claude-opus-5-5", "claude-opus-5", None, 5):
        assert not accepted_reported("claude-opus-5-5", bad)


def test_a_plan_cell_carries_exactly_the_keys_the_readers_take_and_the_stage_key_is_the_row():
    """`getRunStages` and the cell-binding trigger read the frozen plan: each cell is exactly these six keys, and a call's `stage_key` is
    the layout row (`text`, `blocks`, `cross_check`, `norms`, `review`, `correction`)."""
    from auditmanager.analysis.text.binding import CallBinding
    from auditmanager.runs.stage_facts import _plan_cells

    document = _plan("subscription").to_json()
    assert {tuple(sorted(cell)) for cell in document["cells"]} == {
        ("access", "cell_key", "effort", "max_output_tokens", "model_id", "timeout_seconds")}
    seen = _plan_cells(document)       # the reader of `getRunStages` accepts it and reads every field
    assert sorted(cell["cell_key"] for views in seen.values() for cell in views) == sorted(c.cell_key for c in layout.preset_cells("claude_only"))
    assert [cell["cell_key"] for cell in seen["blocks"]] == ["blocks:leg1", "blocks:judge"], "a chip lists its cells in role order"
    for views in seen.values():
        for view in views:
            assert {"model_id", "effort", "max_output_tokens", "timeout_seconds", "access"} <= set(view)
    for cell in layout.preset_cells("codex_only"):
        assert CallBinding(expected_model="m", check_identity=True, cell_key=cell.cell_key, access="api").stage_key == cell.row
