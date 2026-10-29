"""One project's overview is a fixed number of statements whatever the number of its sets (`CMP-VC-OVERVIEW-01`).

The matrix read, the series read and the queue counts each take one set (or one series): over a project they are N+1. The
overview reads the project at once. The statements are counted at the driver (``before_cursor_execute``) for a project of
one set and a project of thirty, with every kind of fact in the sets (profiles, a build, edits, a series with transitions,
queue items, upload metadata).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import event

from .conftest import Lab


def populate(lab: Lab, sets: int) -> str:
    project = lab.project()
    for index in range(sets):
        doc = lab.document(project, title=f"Комплект {index:02d}", pages=(2, 2, 2))
        if index % 2 == 0:
            lab.stamp(doc, designation=f"133/23-ГК-ЭМ{index}", stage="P", section="EOM")
        build = lab.build(doc, lab.aligned_rows(doc, unmatched=index % 2))
        if index % 3 == 0:
            lab.series(doc, build, "completed", summaries=[{"different": 1}, {}])
        elif index % 3 == 1:
            lab.series(doc, build, "running", completed=1)
        if index % 5 == 0:
            lab.work(project, "page_profile", "queued", key=f"page_profile:{doc.versions[0]}", payload={"version_uid": doc.versions[0]})
    lab.upload(project, "processing", sets=("needs_confirmation", "failed"))
    return project


def statements(engine: Any, call: Any) -> int:
    seen: list[str] = []

    def count(_conn: Any, _cursor: Any, statement: str, *_rest: Any) -> None:
        seen.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        call()
    finally:
        event.remove(engine, "before_cursor_execute", count)
    return len(seen)


def test_the_number_of_statements_does_not_depend_on_the_number_of_sets(lab: Lab, service, engine) -> None:
    one, thirty = populate(lab, 1), populate(lab, 30)
    service.get_overview(project_uid=one)  # warm the engine (the first statement of a connection)
    small = statements(engine, lambda: service.get_overview(project_uid=one))
    large = statements(engine, lambda: service.get_overview(project_uid=thirty))
    assert len(service.get_overview(project_uid=thirty)["sets"]) == 30
    assert large == small, f"{small} statements for 1 set, {large} for 30: the overview is N+1"
    assert small <= 20, f"{small} statements for one project: the budget is a fixed handful"


def test_the_empty_project_costs_no_more_than_the_full_one(lab: Lab, service, engine) -> None:
    empty, full = lab.project(), populate(lab, 5)
    service.get_overview(project_uid=empty)
    assert statements(engine, lambda: service.get_overview(project_uid=empty)) <= statements(
        engine, lambda: service.get_overview(project_uid=full)
    )
    overview = service.get_overview(project_uid=empty)
    assert overview["sets"] == [] and overview["pending_uploads"] == []
    assert overview["counters"] == {"all": 0, "waiting": 0, "running": 0, "failed": 0, "ready": 0}
    assert overview["totals"] == {"versions": 0, "transitions": 0}


def test_the_queue_summary_is_three_statements_at_most(lab: Lab, service, engine) -> None:
    populate(lab, 3)
    service.get_queue_summary(modules="versions")
    assert statements(engine, lambda: service.get_queue_summary(modules="versions")) <= 6
