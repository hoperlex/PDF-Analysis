"""`SECTION-READ-MODEL-01`: the dashboard's section breakdown counts a document in the section
its **current version** is confirmed in, on real PostgreSQL rows.

The unit of count is the set (``document``) that has a published current version -- the same
one ``documents_by_project`` counts -- placed by its current version's own
``document_version_classification`` row. A set whose current version is unclassified goes to
the unclassified bucket whatever the legacy ``document.section`` label, or an older
version, says. The response shape is the one `R-44` froze: every one of the fifteen
sections present even at zero, the unclassified bucket last and always present.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from auditmanager.dashboard.repository import PROJECT_SECTIONS, DashboardRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.db.conftest import (  # type: ignore[import-not-found]  # noqa: F401
    configured_settings,
    maintenance_engine,
    migrated_database,
    migrated_database_factory,
    migrated_engine,
    migrated_template,
)
from tests.integration.documents.seeding import Seeder

dashboard = DashboardRepository()


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    with Session(migrated_engine) as opened:
        yield opened


def _breakdown(session: Session) -> dict[str | None, int]:
    rows = dashboard.summary(session).section_breakdown
    return {row.section: row.document_count for row in rows}


def test_an_empty_deployment_has_every_section_at_zero_and_the_bucket_last(session: Session) -> None:
    rows = dashboard.summary(session).section_breakdown
    assert [row.section for row in rows] == [*PROJECT_SECTIONS, None]
    assert {row.document_count for row in rows} == {0}
    assert len(PROJECT_SECTIONS) == 15 and "PS" in PROJECT_SECTIONS


def test_a_set_is_counted_in_the_section_its_current_version_is_confirmed_in(session: Session) -> None:
    seed = Seeder(session)
    school = seed.project("Школа")
    clinic = seed.project("Поликлиника")
    for number in range(3):
        seed.version(seed.document(school, f"АР-{number}"), classified=("R", "AR"))
    seed.version(seed.document(clinic, "АР-П"), classified=("P", "AR"))
    seed.version(seed.document(clinic, "ПЗ"), classified=("P", "PS"))
    seed.version(seed.document(clinic, "КЖ"), classified=("R", "KJ"))
    session.commit()
    counted = _breakdown(session)
    assert counted["AR"] == 4 and counted["PS"] == 1 and counted["KJ"] == 1
    assert counted[None] == 0
    assert sum(counted.values()) == 6
    assert {code: count for code, count in counted.items() if code not in ("AR", "PS", "KJ")} == {
        code: 0 for code in (*PROJECT_SECTIONS, None) if code not in ("AR", "PS", "KJ")
    }


def test_unclassified_current_versions_go_to_the_bucket_whatever_else_says(session: Session) -> None:
    seed = Seeder(session)
    project = seed.project("Школа")
    # Never classified, no legacy label.
    seed.version(seed.document(project, "Комплект"))
    # The legacy document label says AR; nothing is confirmed.
    seed.version(seed.document(project, "АР по ярлыку", legacy_section="AR"))
    # An older version was confirmed EOM; the current one is not.
    older = seed.document(project, "ЭОМ, потом без раздела")
    seed.version(older, classified=("R", "EOM"))
    seed.version(older)
    session.commit()
    counted = _breakdown(session)
    assert counted[None] == 3
    assert counted["AR"] == 0 and counted["EOM"] == 0
    assert sum(counted.values()) == 3


def test_the_current_version_decides_not_the_legacy_label_and_not_an_older_version(
    session: Session,
) -> None:
    seed = Seeder(session)
    project = seed.project("Школа")
    # Legacy label AR, confirmed KJ: KJ.
    seed.version(seed.document(project, "КЖ", legacy_section="AR"), classified=("R", "KJ"))
    # Confirmed OV on the first version, AR on the head: AR.
    moved = seed.document(project, "Сменился")
    seed.version(moved, classified=("R", "OV"))
    seed.version(moved, classified=("P", "AR"))
    session.commit()
    counted = _breakdown(session)
    assert (counted["KJ"], counted["AR"], counted["OV"], counted[None]) == (1, 1, 0, 0)


def test_the_head_moving_moves_the_count(session: Session) -> None:
    seed = Seeder(session)
    project = seed.project("Школа")
    moving = seed.document(project, "Двигается")
    first = seed.version(moving, classified=("R", "OV"))
    second = seed.version(moving, classified=("P", "AR"))
    session.commit()
    assert (_breakdown(session)["AR"], _breakdown(session)["OV"]) == (1, 0)
    seed.point_at(moving, first)
    session.commit()
    assert (_breakdown(session)["AR"], _breakdown(session)["OV"]) == (0, 1)
    seed.point_at(moving, second)
    session.commit()
    assert (_breakdown(session)["AR"], _breakdown(session)["OV"]) == (1, 0)


def test_a_set_without_a_published_head_is_counted_nowhere(session: Session) -> None:
    seed = Seeder(session)
    project = seed.project("Школа")
    seed.version(seed.document(project, "Без головы"), classified=("R", "AR"), current=False)
    seed.document(project, "Совсем пустой")
    session.commit()
    assert set(_breakdown(session).values()) == {0}


def test_the_breakdown_adds_up_to_the_documents_the_project_panel_counts(session: Session) -> None:
    seed = Seeder(session)
    one = seed.project("Первый")
    two = seed.project("Второй")
    seed.version(seed.document(one, "а"), classified=("R", "AR"))
    seed.version(seed.document(one, "б"))
    seed.version(seed.document(two, "в"), classified=("P", "PS"))
    seed.version(seed.document(two, "г"), classified=("R", "AR"), current=False)
    session.commit()
    summary = dashboard.summary(session)
    assert sum(row.document_count for row in summary.section_breakdown) == sum(
        project.document_count for project in summary.documents_by_project
    ) == 3


# --- a code the vocabulary does not list ------------------------------------------------------


class _Result:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[Any, ...]]:
        return self._rows

    def one(self) -> tuple[Any, ...]:
        return self._rows[0]


class _Session:
    """Answers each statement of ``summary`` by its text; the section rows are the subject."""

    def __init__(self, sections: list[tuple[Any, ...]]) -> None:
        self.sections = sections

    def execute(self, statement: Any, parameters: Any = None) -> _Result:
        sql = str(statement)
        if "version_classification_current" in sql:  # the breakdown reads the current revision
            return _Result(self.sections)
        if "FROM model_call" in sql:
            return _Result([(0, 0, 0)])
        if "FROM project p" in sql:
            return _Result([])
        return _Result([])


def test_a_confirmed_code_missing_from_the_vocabulary_is_refused_not_dropped() -> None:
    known = _Session([("AR", 2), (None, 1)])
    assert [
        (row.section, row.document_count)
        for row in dashboard.summary(known).section_breakdown  # type: ignore[arg-type]
        if row.document_count
    ] == [("AR", 2), (None, 1)]
    unknown = _Session([("AR", 2), ("ZZ", 5)])
    with pytest.raises(DomainError) as caught:
        dashboard.summary(unknown)  # type: ignore[arg-type]
    assert caught.value.code is ErrorCode.INTERNAL_ERROR
