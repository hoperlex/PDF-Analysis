"""The overview equals what the matrix read and the series read answer, set by set (`CMP-VC-OVERVIEW-01`).

``ComparisonMatrixService.get_matrix`` and ``ComparisonSeriesService.list_series`` read one document set each; the overview
reads the whole project at once. For every state a set can be in, the overview's step 2, 3 and 5 must be what those two
services say, mapped by the table the contract and the brief give. The expected values below are written here in words, not
read back from the overview's own rules.
"""

from __future__ import annotations

from typing import Any

from .conftest import Doc, Lab


def steps(view: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["step"]: s for s in view["steps"]}


def row_of(overview: dict[str, Any], doc: Doc) -> dict[str, Any]:
    (row,) = [s for s in overview["sets"] if s["document_uid"] == doc.document_uid]
    return row


# -- the independent reading of the two services ---------------------------------------------------------------------


def expected_matrix_step(matrix: dict[str, Any], *, building_by_build_item: str | None = None) -> tuple[str, dict[str, int] | None]:
    """Step 3 from ``getComparisonMatrix`` (brief: absent, building, stale, failed, ready; ``counts.unmatched`` → attention)."""
    counts = matrix.get("counts")
    shown = None if counts is None else {"rows": counts["rows"], "unmatched": counts["unmatched"], "manual_edits": counts["manual"]}
    state = matrix["state"]
    if state == "ready":
        return ("attention" if counts["unmatched"] else "done"), shown
    if state == "failed":
        return "failed", shown
    if state == "stale":
        return "stale", shown
    if state == "building":
        if building_by_build_item:
            return building_by_build_item, shown
        return ("stale" if counts is not None else "not_started"), shown
    return "not_started", shown


def expected_series_step(page: Any, versions: int) -> tuple[str, dict[str, int] | None]:
    """Step 5 from ``listComparisonSeries`` (newest first): none → not started; completed with stale reasons → stale."""
    if not page.items:
        return "not_started", {"total": versions - 1, "done": 0}
    latest = page.items[0]
    mapping = {"queued": "queued", "running": "running", "paused": "paused", "completed": "done", "failed": "failed",
               "cancelled": "interrupted"}
    state = mapping[latest["state"]]
    if latest["state"] == "completed" and latest.get("stale_reasons"):
        state = "stale"
    return state, {"total": latest["transitions_total"], "done": latest["transitions_done"]}


def check_against_services(lab: Lab, service: Any, matrix_service: Any, series_service: Any, doc: Doc, **flags: Any) -> dict[str, Any]:
    overview = service.get_overview(project_uid=doc.project_uid)
    row = row_of(overview, doc)
    matrix = matrix_service.get_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)
    page = series_service.list_series(project_uid=doc.project_uid, document_uid=doc.document_uid, after=None, limit=1)
    by = steps(row)
    if len(doc.versions) >= 2:
        state, counts = expected_matrix_step(matrix, **flags)
        assert by["matrix"]["state"] == state, ("matrix", matrix["state"], by["matrix"])
        assert by["matrix"].get("counts") == counts
        state, counts = expected_series_step(page, len(doc.versions))
        assert by["series"]["state"] == state, ("series", page.items[:1], by["series"])
        got = by["series"].get("counts", {})
        assert {k: got.get(k) for k in ("total", "done")} == counts
    progress = matrix["progress"]
    got = by["profile"].get("counts", {})
    assert {k: got.get(k) for k in ("total", "ready", "failed")} == progress
    return row


# -- scenarios ---------------------------------------------------------------------------------------------------------


def test_a_set_nothing_was_done_to(lab: Lab, service, matrix_service, series_service) -> None:
    doc = lab.document(lab.project(), profiles="none")
    row = check_against_services(lab, service, matrix_service, series_service, doc)
    by = steps(row)
    assert by["upload"]["state"] == "done" and by["profile"]["state"] == "not_started"
    assert by["matrix"]["state"] == "not_started" and by["series"]["state"] == "not_started"
    assert row["next_step"] == "profile" and row["version_count"] == 3


def test_a_profiled_set_without_a_matrix(lab: Lab, service, matrix_service, series_service) -> None:
    doc = lab.document(lab.project())
    row = check_against_services(lab, service, matrix_service, series_service, doc)
    assert steps(row)["profile"] == {"step": "profile", "state": "done", "counts": {"total": 6, "ready": 6, "failed": 0}}
    assert row["next_step"] == "matrix"


def test_a_set_with_some_pages_profiled_is_partial(lab: Lab, service, matrix_service, series_service) -> None:
    doc = lab.document(lab.project(), profiles="some")
    row = check_against_services(lab, service, matrix_service, series_service, doc)
    assert steps(row)["profile"]["state"] == "partial" and row["next_step"] == "profile"


def test_a_set_with_pages_that_ended_without_a_result_is_failed_and_proposes_the_profile(lab, service, matrix_service, series_service) -> None:
    doc = lab.document(lab.project(), failed=1)
    row = check_against_services(lab, service, matrix_service, series_service, doc)
    assert steps(row)["profile"]["state"] == "failed"
    assert steps(row)["profile"]["counts"] == {"total": 6, "ready": 3, "failed": 3}
    assert row["next_step"] == "profile"


def test_a_ready_matrix_with_unmatched_sheets(lab: Lab, service, matrix_service, series_service) -> None:
    doc = lab.document(lab.project())
    lab.build(doc, lab.aligned_rows(doc, unmatched=1))
    row = check_against_services(lab, service, matrix_service, series_service, doc)
    assert steps(row)["matrix"] == {"step": "matrix", "state": "attention", "counts": {"rows": 2, "unmatched": 1, "manual_edits": 0}}
    assert row["next_step"] == "series"  # the series first (OV:323), the unmatched sheets after it


def test_a_ready_matrix_without_unmatched_sheets_is_done(lab: Lab, service, matrix_service, series_service) -> None:
    doc = lab.document(lab.project())
    lab.build(doc, lab.aligned_rows(doc))
    row = check_against_services(lab, service, matrix_service, series_service, doc)
    assert steps(row)["matrix"]["state"] == "done" and steps(row)["matrix"]["counts"]["unmatched"] == 0


def test_manual_edits_are_counted_as_the_matrix_counts_them(lab: Lab, service, matrix_service, series_service, expert_uid) -> None:
    doc = lab.document(lab.project())
    rows = lab.aligned_rows(doc, unmatched=1)
    last = doc.versions[2]
    # page 2 of the last version is a sheet of its own, which an expert links to the row whose cell in that version is a hole
    rows.append({"cells": [
        {"version_uid": doc.versions[0], "state": "absent", "reason": "no_candidates"},
        {"version_uid": doc.versions[1], "state": "absent", "reason": "no_candidates"},
        {"version_uid": last, "state": "matched", "page_number": 2, "page_profile_id": doc.pages[last][1],
         "confidence": "high", "flags": []},
    ]})
    lab.build(doc, rows)
    from auditmanager.comparison.public import MatrixEditInput, MatrixPageRef

    before = matrix_service.get_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)
    matrix_service.apply_edits(
        project_uid=doc.project_uid, document_uid=doc.document_uid, base_matrix_id=before["revision"]["matrix_id"],
        base_edit_no=before["revision"]["edit_no"],
        edits=[MatrixEditInput(kind="link", page=MatrixPageRef(doc.versions[0], 2), other_page=MatrixPageRef(doc.versions[2], 2))],
        user_uid=expert_uid, actor_label="Т", actor_roles=frozenset({"expert"}), idempotency_key=f"ov-{doc.document_uid[-12:]}",
    )
    row = check_against_services(lab, service, matrix_service, series_service, doc)
    counts = steps(row)["matrix"]["counts"]
    assert counts["manual_edits"] >= 1, counts
    after = matrix_service.get_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)
    assert counts == {"rows": after["counts"]["rows"], "unmatched": after["counts"]["unmatched"], "manual_edits": after["counts"]["manual"]}


def test_a_matrix_whose_profiles_changed_is_stale(lab: Lab, service, matrix_service, series_service) -> None:
    doc = lab.document(lab.project(), profiles="some")
    lab.build(doc, [])
    lab.profile_page(doc, doc.versions[0], 2)  # a profile stored after the build: the digest of the profiles moved
    row = check_against_services(lab, service, matrix_service, series_service, doc)
    assert steps(row)["matrix"]["state"] == "stale" and row["next_step"] == "profile"


def test_a_matrix_whose_order_changed_is_stale(lab: Lab, service, matrix_service, series_service) -> None:
    doc = lab.document(lab.project())
    lab.build(doc, lab.aligned_rows(doc))
    lab.reorder(doc, [doc.versions[1], doc.versions[0], doc.versions[2]])
    row = check_against_services(lab, service, matrix_service, series_service, doc)
    assert steps(row)["matrix"]["state"] == "stale"


def test_a_live_build_item_makes_the_matrix_step_running(lab: Lab, service, matrix_service, series_service) -> None:
    doc = lab.document(lab.project())
    lab.work(doc.project_uid, "matrix_build", "queued", key=f"matrix_build:{doc.document_uid}", payload={"document_uid": doc.document_uid})
    row = check_against_services(lab, service, matrix_service, series_service, doc, building_by_build_item="queued")
    assert steps(row)["matrix"]["state"] == "queued"
    assert row["next_step"] == "matrix"


def test_a_build_item_that_failed_after_the_build_is_a_failed_matrix(lab: Lab, service, matrix_service, series_service) -> None:
    doc = lab.document(lab.project())
    lab.work(doc.project_uid, "matrix_build", "failed", key=f"matrix_build:{doc.document_uid}", payload={"document_uid": doc.document_uid})
    row = check_against_services(lab, service, matrix_service, series_service, doc)
    assert steps(row)["matrix"]["state"] == "failed" and row["next_step"] == "matrix"


def test_a_live_page_profile_item_makes_the_profile_step_queued_and_the_matrix_wait(lab, service, matrix_service, series_service) -> None:
    doc = lab.document(lab.project(), profiles="none")
    lab.work(doc.project_uid, "page_profile", "queued", key=f"page_profile:{doc.versions[0]}", payload={"version_uid": doc.versions[0]})
    row = check_against_services(lab, service, matrix_service, series_service, doc)
    assert steps(row)["profile"]["state"] == "queued" and steps(row)["matrix"]["state"] == "not_started"
    assert row["next_step"] == "profile"
    lab.work(doc.project_uid, "page_profile", "running", key=f"page_profile:{doc.versions[1]}:retry_failed", payload={"version_uid": doc.versions[1]})
    assert steps(row_of(service.get_overview(project_uid=doc.project_uid), doc))["profile"]["state"] == "running"


# -- the series --------------------------------------------------------------------------------------------------------


def _ready(lab: Lab, **kwargs: Any) -> tuple[Doc, Any]:
    doc = lab.document(lab.project(), **kwargs)
    return doc, lab.build(doc, lab.aligned_rows(doc))


def test_a_completed_series_that_matches_its_inputs_is_done_and_counts_the_changed_transitions(lab, service, matrix_service, series_service) -> None:
    doc, build = _ready(lab)
    lab.series(doc, build, "completed", summaries=[{"different": 1}, {}])
    row = check_against_services(lab, service, matrix_service, series_service, doc)
    assert steps(row)["series"] == {"step": "series", "state": "done", "counts": {"total": 2, "done": 2, "with_changes": 1}}
    assert "next_step" not in row  # nothing is left: «Готово»


def test_a_completed_series_for_another_order_reads_stale(lab, service, matrix_service, series_service) -> None:
    doc, build = _ready(lab)
    lab.series(doc, build, "completed", stale=True)
    row = check_against_services(lab, service, matrix_service, series_service, doc)
    assert steps(row)["series"]["state"] == "stale" and row["next_step"] == "series"
    assert series_service.list_series(project_uid=doc.project_uid, document_uid=doc.document_uid, after=None, limit=1).items[0]["stale_reasons"]


def test_a_series_whose_version_was_added_after_it_reads_stale_with_the_same_reason_the_series_gives(lab, service, matrix_service, series_service) -> None:
    doc, build = _ready(lab)
    lab.series(doc, build, "completed")
    lab.add_version(doc)
    row = check_against_services(lab, service, matrix_service, series_service, doc)
    assert steps(row)["series"]["state"] == "stale"


def test_a_manual_edit_after_the_series_makes_it_stale(lab, service, matrix_service, series_service, expert_uid) -> None:
    """The series is bound to the number of manual edit events; an applied edit moves it (``matrix_changed``)."""
    from auditmanager.comparison.public import MatrixEditInput, MatrixPageRef

    doc = lab.document(lab.project())
    rows = lab.aligned_rows(doc, unmatched=1)
    last = doc.versions[2]
    rows.append({"cells": [
        {"version_uid": doc.versions[0], "state": "absent", "reason": "no_candidates"},
        {"version_uid": doc.versions[1], "state": "absent", "reason": "no_candidates"},
        {"version_uid": last, "state": "matched", "page_number": 2, "page_profile_id": doc.pages[last][1],
         "confidence": "high", "flags": []},
    ]})
    build = lab.build(doc, rows)
    lab.series(doc, build, "completed")
    assert steps(row_of(service.get_overview(project_uid=doc.project_uid), doc))["series"]["state"] == "done"
    matrix_service.apply_edits(
        project_uid=doc.project_uid, document_uid=doc.document_uid, base_matrix_id=build.matrix_id, base_edit_no=0,
        edits=[MatrixEditInput(kind="link", page=MatrixPageRef(doc.versions[0], 2), other_page=MatrixPageRef(last, 2))],
        user_uid=expert_uid, actor_label="Т", actor_roles=frozenset({"expert"}), idempotency_key=f"ov-s-{doc.document_uid[-12:]}",
    )
    row = check_against_services(lab, service, matrix_service, series_service, doc)
    assert steps(row)["series"]["state"] == "stale"
    assert series_service.list_series(project_uid=doc.project_uid, document_uid=doc.document_uid, after=None, limit=1).items[0]["stale_reasons"] == ["matrix_changed"]


def test_each_series_state(lab, service, matrix_service, series_service) -> None:
    for state, completed in (("queued", 0), ("running", 1), ("paused", 1), ("failed", 1), ("cancelled", 0)):
        doc, build = _ready(lab)
        lab.series(doc, build, state, completed=completed)
        row = check_against_services(lab, service, matrix_service, series_service, doc)
        assert steps(row)["series"]["state"] == {"queued": "queued", "running": "running", "paused": "paused",
                                                 "failed": "failed", "cancelled": "interrupted"}[state], state


def test_only_the_newest_series_decides(lab, service, matrix_service, series_service) -> None:
    doc, build = _ready(lab)
    lab.series(doc, build, "failed", completed=1)
    lab.series(doc, build, "completed")
    row = check_against_services(lab, service, matrix_service, series_service, doc)
    assert steps(row)["series"]["state"] == "done"


def test_a_follow_up_that_waits_makes_the_series_queued_before_it_exists(lab, service, matrix_service, series_service) -> None:
    doc, _build = _ready(lab)
    upload = lab.upload(doc.project_uid, "processing")
    lab.work(doc.project_uid, "series_after_preparation", "queued", key=f"series_after_preparation:cus_{doc.document_uid[-20:]}",
             payload={"document_uid": doc.document_uid, "set_id": "cus_x", "actor_label": "Э"}, upload=upload)
    row = steps(row_of(service.get_overview(project_uid=doc.project_uid), doc))
    assert row["series"]["state"] == "queued" and row["series"]["counts"] == {"total": 2, "done": 0}


# -- one version, the steps of wave C2 ------------------------------------------------------------------------------------


def test_a_set_of_one_version_has_nothing_to_compare_and_nothing_left(lab, service) -> None:
    doc = lab.document(lab.project(), pages=(3,))
    row = row_of(service.get_overview(project_uid=doc.project_uid), doc)
    by = steps(row)
    assert by["upload"]["state"] == "done" and by["profile"]["state"] == "done"
    assert by["matrix"]["state"] == "not_applicable" and by["series"]["state"] == "not_applicable"
    assert "next_step" not in row and row["version_count"] == 1


def test_the_steps_come_in_the_contracts_order_and_wave_c2_answers_not_applicable(lab, service) -> None:
    doc = lab.document(lab.project())
    row = row_of(service.get_overview(project_uid=doc.project_uid), doc)
    assert [s["step"] for s in row["steps"]] == ["upload", "profile", "matrix", "ai_pairs", "series", "ai_changes", "report"]
    for name in ("ai_pairs", "ai_changes", "report"):
        assert steps(row)[name] == {"step": name, "state": "not_applicable"}
