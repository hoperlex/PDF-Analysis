"""The description of a series, end to end in recorded mode (`CMP-VC-AISHEET-01`): estimate, start, the worker's items, the reads."""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.api.schemas import models
from auditmanager.shared.errors import DomainError


def prepare_all(lab: Any) -> None:
    """File the answers for the pairs that are asked: two table sheets and the two one-sided ones."""
    lab.record("p1")
    lab.record("p6")
    lab.record_single("p4")
    lab.record_single("p5", {"sheet_kind": "схема", "summary": "Схема щита ЩО-3.", "objects": [{"name": "щит", "detail": "ЩР-7"}],
                             "marks": ["ЩР-7"], "limitation": ""})


def test_the_estimate_counts_what_would_be_sent_and_calls_no_model(lab: Any) -> None:
    estimate = lab.service.estimate_series(series_id=lab.world.series, only_failed=False)
    models.ComparisonAiEstimate.model_validate(estimate)
    # p1, p6 (tables) and p4, p5 (single sheets) are asked; p2 has no candidate, p3 did not change
    assert (estimate["method"], estimate["units"], estimate["reused"], estimate["calls"]) == ("sheet_changes", 5, 0, 4)
    assert estimate["sheets"] == 5 and estimate["transitions"] == 1 and estimate["images"] >= 4 + 4 + 2
    assert estimate["image_bytes"] > 0 and estimate["prompt_chars"] > 0 and estimate["output_tokens"] == 4 * 8192
    assert estimate["route"]["provider_mode"] == "recorded" and estimate["estimate_micros"] == 0  # not metered
    assert lab.answers.calls == 0 and lab.db.rows("SELECT 1 FROM comparison_ai_job") == []


def test_the_estimate_digest_follows_the_figures_and_stays_when_nothing_moves(lab: Any) -> None:
    first = lab.service.estimate_series(series_id=lab.world.series, only_failed=False)
    assert lab.service.estimate_series(series_id=lab.world.series, only_failed=False)["estimate_digest"] == first["estimate_digest"]
    estimate = lab.service.estimate_description(sheet_pair_id=lab.world["p1"].pair)
    assert estimate["estimate_digest"] != first["estimate_digest"] and estimate["calls"] == 1


def test_a_series_is_described_sheet_by_sheet_and_the_job_completes_once_every_sheet_is_over(lab: Any) -> None:
    prepare_all(lab)
    job = lab.start_series()
    models.ComparisonAiJob.model_validate(job)
    assert (job["state"], job["method"], job["counts"]["total"]) == ("queued", "sheet_changes", 5)
    assert lab.items(job["job_id"]) == {n: "queued" for n in ("p1", "p2", "p4", "p5", "p6")}

    ran = lab.drain()
    sheets = [name for name, _outcome in ran if name != "drain"]
    assert sorted(sheets) == sorted(lab.world[n].pair for n in ("p1", "p2", "p4", "p5", "p6")) and ran[-1][0] == "drain"
    assert lab.items(job["job_id"]) == {n: "done" for n in ("p1", "p2", "p4", "p5", "p6")}
    view = lab.jobs.view(job["job_id"])
    assert (view.record.state, view.progress.total, view.progress.done, view.progress.failed) == ("completed", 5, 5, 0)
    assert lab.job(job["job_id"])["state"] == "completed"
    assert lab.answers.calls == 4, "one call for each of the four sheets that were asked; the quiet one needed none"
    assert [c["provider_mode"] for c in lab.calls()] == ["recorded"] * 4 and {c["state"] for c in lab.calls()} == {"completed"}
    states = {d["state"] for d in lab.descriptions()}
    assert states <= {"done", "partial", "no_construction_changes", "needs_clarification"} and len(lab.descriptions()) == 5
    assert all(d["recorded"] for d in lab.descriptions() if d["calls"])


def test_the_reads_after_the_run_show_the_eleven_states_the_progress_and_the_description(lab: Any) -> None:
    prepare_all(lab)
    before = lab.service.get_series(series_id=lab.world.series)
    models.ComparisonAiSheetChanges.model_validate(before)
    assert "job" not in before and before["transitions"][0]["sheets"] == 5 and before["transitions"][0]["done"] == 0
    assert lab.service.get_description(sheet_pair_id=lab.world["p1"].pair)["state"] == "not_processed"
    assert lab.service.get_description(sheet_pair_id=lab.world["p3"].pair)["state"] == "engine_same"
    job = lab.start_series()
    assert lab.service.get_description(sheet_pair_id=lab.world["p1"].pair)["state"] == "queued"
    lab.drain()
    after = lab.service.get_series(series_id=lab.world.series)
    models.ComparisonAiSheetChanges.model_validate(after)
    progress = after["transitions"][0]
    assert (progress["sheets"], progress["done"], progress["errors"], progress["calls"]) == (5, 5, 0, 4)
    assert progress["changed"] == 2 and progress["input_tokens"] == 400 and progress["output_tokens"] == 200
    assert after["job"]["job_id"] == job["job_id"] and after["job"]["state"] == "completed"

    description = lab.service.get_description(sheet_pair_id=lab.world["p1"].pair)
    models.ComparisonSheetDescription.model_validate(description)
    assert description["state"] == "done" and description["recorded"] is True and description["history_count"] == 1
    change = description["changes"][0]
    assert (change["object_name"], change["was"], change["now"], change["was_tier"], change["now_tier"], change["certainty"]) == (
        "Люк Лк-1", "2", "3", "from_text", "from_text", "confirmed")
    assert description["declared"] == [{"text": "Изм. 3: замена люка Лк-1", "reference": "declared_and_found"}]
    assert description["coverage"] == {"candidates": 3, "in_changes": 1, "not_reviewed": 0}
    assert description["model"] == "recorded" and description["prompt_version"].startswith("sheet-changes/1+")
    quiet = lab.service.get_description(sheet_pair_id=lab.world["p2"].pair)
    assert quiet["state"] == "partial" or quiet["state"] == "no_construction_changes"
    assert quiet["changes"] == [] and quiet["coverage"]["candidates"] == 0


def test_a_sheet_that_is_in_one_version_only_is_described_by_what_is_on_it(lab: Any) -> None:
    prepare_all(lab)
    lab.start_series()
    lab.drain()
    added = lab.service.get_description(sheet_pair_id=lab.world["p4"].pair)
    removed = lab.service.get_description(sheet_pair_id=lab.world["p5"].pair)
    for view in (added, removed):
        models.ComparisonSheetDescription.model_validate(view)
        assert view["state"] == "done" and view["changes"] and view["unresolved"] == []
    assert {c["kind"] for c in added["changes"]} == {"added"} and "now" in added["changes"][0] and "was" not in added["changes"][0]
    assert {c["kind"] for c in removed["changes"]} == {"removed"} and "was" in removed["changes"][0]
    # a mark that is not on the sheet is dropped: ЩО-2 is on p4 ("Схема ЩО-2"), the answer named it; ЩР-1 too
    row = lab.db.rows("SELECT description FROM comparison_sheet_description WHERE page_profile_id = :p", p=lab.world["p4"].page_b)[0]
    assert row["description"]["single"]["marks"] == ["ЩР-1", "ЩО-2"]
