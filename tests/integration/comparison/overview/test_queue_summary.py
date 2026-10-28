"""The comparison queue summary (`CMP-VC-OVERVIEW-01`; ADR-0025 decisions 6 and 23): the whole installation's queue by state
and by module and kind, the module set, the pause, the age of the oldest queued item."""

from __future__ import annotations

from typing import Any

from .conftest import Lab

STATES = ("queued", "leased", "running", "retry_wait", "paused", "spend_unknown", "succeeded", "failed", "cancelled")


def kind_counts(summary: dict[str, Any], module: str, kind: str) -> dict[str, int]:
    found = [k for k in summary["kinds"] if k["module"] == module and k["kind"] == kind]
    return found[0]["counts"] if found else dict.fromkeys(STATES, 0)


def test_the_summary_counts_what_was_added_by_state_module_and_kind(lab: Lab, service) -> None:
    before = service.get_queue_summary(modules="versions")
    project = lab.project()
    for state in ("queued", "queued", "running", "paused", "succeeded", "failed", "cancelled"):
        lab.work(project, "page_profile", state)
    lab.work(project, "matrix_build", "leased")
    lab.work(project, "pair_result", "queued", module="stages")
    after = service.get_queue_summary(modules="versions")

    def delta(table_before: dict[str, int], table_after: dict[str, int]) -> dict[str, int]:
        return {s: table_after[s] - table_before[s] for s in STATES if table_after[s] != table_before[s]}

    assert delta(before["counts"], after["counts"]) == {"queued": 3, "leased": 1, "running": 1, "paused": 1,
                                                        "succeeded": 1, "failed": 1, "cancelled": 1}
    assert delta(kind_counts(before, "versions", "page_profile"), kind_counts(after, "versions", "page_profile")) == {
        "queued": 2, "running": 1, "paused": 1, "succeeded": 1, "failed": 1, "cancelled": 1}
    assert delta(kind_counts(before, "versions", "matrix_build"), kind_counts(after, "versions", "matrix_build")) == {"leased": 1}
    assert delta(kind_counts(before, "stages", "pair_result"), kind_counts(after, "stages", "pair_result")) == {"queued": 1}


def test_the_total_is_the_sum_of_the_kinds_and_every_state_is_present(lab: Lab, service) -> None:
    lab.work(lab.project(), "page_profile", "queued")
    summary = service.get_queue_summary(modules="versions")
    assert set(summary["counts"]) == set(STATES)
    for state in STATES:
        assert summary["counts"][state] == sum(k["counts"][state] for k in summary["kinds"])
    keys = [(k["module"], k["kind"]) for k in summary["kinds"]]
    assert keys == sorted(keys) and len(keys) == len(set(keys))
    for kind in summary["kinds"]:
        assert set(kind["counts"]) == set(STATES)


def test_the_module_set_is_reported_as_it_is_given(service) -> None:
    for modules in ("none", "versions", "versions,stages"):
        assert service.get_queue_summary(modules=modules)["modules"] == modules


def test_the_oldest_queued_item_is_the_oldest_with_state_queued(lab: Lab, service) -> None:
    project = lab.project()
    first = lab.work(project, "page_profile", "queued")
    lab.work(project, "page_profile", "queued")
    summary = service.get_queue_summary(modules="versions")
    created = lab.rows("SELECT min(created_at) AS t FROM comparison_work WHERE state = 'queued'")[0]["t"]
    assert summary["oldest_queued_at"] == created
    assert first  # created before the second
    only_running = {k for k in summary if k == "oldest_queued_at"}
    assert only_running == {"oldest_queued_at"}


def test_the_pause_is_the_installations_execution_pause(sessions, service) -> None:
    from auditmanager.jobs.public import set_execution_paused
    from auditmanager.shared.db import session_scope
    from auditmanager.shared.identity import new_ulid

    def pause(paused: bool) -> None:
        with session_scope(sessions) as session:
            set_execution_paused(session, paused=paused, roles=frozenset({"admin"}), idempotency_key=f"ov-pause-{new_ulid()}",
                                 actor_uid="usr_01ARZ3NDEKTSV4RRFFQ69G5FAV")

    pause(False)  # a run that was cut short may have left the installation paused
    try:
        assert service.get_queue_summary(modules="versions")["paused"] is False
        pause(True)
        assert service.get_queue_summary(modules="versions")["paused"] is True
    finally:
        pause(False)
    assert service.get_queue_summary(modules="versions")["paused"] is False
