"""`SECTION-READ-MODEL-01`: the documents projection's «which sets' current versions are
confirmed in section X» query, on real PostgreSQL rows.

The subject is the join, not the Python around it: ``document.current_version_uid`` selects
the version and that version's own ``document_version_classification`` row is the
confirmation. The world is built so that each wrong join gives a different wrong answer --
an older version's confirmation, the legacy ``document.section``, a head that moved, a set
with no published head -- and every one of them has its own set.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.documents.public import MAX_PLACEMENT_PAGE, DocumentRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, ProjectUid
from tests.integration.db.conftest import (  # type: ignore[import-not-found]  # noqa: F401
    configured_settings,
    maintenance_engine,
    migrated_database,
    migrated_database_factory,
    migrated_engine,
    migrated_template,
)
from tests.integration.documents.seeding import Seeder

documents = DocumentRepository()


@dataclass(frozen=True, slots=True)
class World:
    school: str
    clinic: str
    #: ``name -> document_uid`` of every set, by what makes it interesting.
    sets: dict[str, str]
    versions: dict[str, str]


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    with Session(migrated_engine) as opened:
        yield opened


@pytest.fixture
def world(session: Session) -> World:
    seed = Seeder(session)
    school = seed.project("Школа на 550 мест")
    clinic = seed.project("Поликлиника")
    sets: dict[str, str] = {}
    versions: dict[str, str] = {}

    def make(key: str, project: str, title: str, *, legacy: str | None = None) -> str:
        sets[key] = seed.document(project, title, legacy_section=legacy)
        return sets[key]

    # One project, several sets across sections.
    versions["ar"] = seed.version(make("ar", school, "АР-1"), classified=("R", "AR"))
    # An older version confirmed AR; the current one is not classified.
    old = seed.version(make("older_ar", school, "АР-2"), classified=("R", "AR"))
    versions["older_ar_head"] = seed.version(sets["older_ar"])
    versions["older_ar_old"] = old
    # An older version unclassified; the current one is confirmed AR.
    seed.version(make("newer_ar", school, "АР-3"))
    versions["newer_ar"] = seed.version(sets["newer_ar"], classified=("P", "AR"))
    # The legacy document label says AR; nothing is confirmed.
    versions["legacy"] = seed.version(make("legacy_ar", school, "АР-4", legacy="AR"))
    # The legacy label says AR; the expert confirmed KJ.
    versions["kj"] = seed.version(make("kj", school, "КЖ-1", legacy="AR"), classified=("R", "KJ"))
    # The fifteenth code.
    versions["ps"] = seed.version(make("ps", school, "ПЗ-1"), classified=("P", "PS"))
    # A version published but never made the head: the set has nothing to show.
    versions["headless"] = seed.version(
        make("headless", school, "АР-5 без головы"), classified=("R", "AR"), current=False
    )
    # Another project.
    versions["clinic_ar"] = seed.version(make("clinic_ar", clinic, "АР-1 поликлиника"), classified=("R", "AR"))
    versions["clinic_loose"] = seed.version(make("clinic_loose", clinic, "Комплект без раздела"))
    # A head that can move between two confirmed versions.
    seed.version(make("moving", clinic, "ОВ-1"), classified=("R", "KJ"))
    versions["moving_first"] = _head(session, sets["moving"])
    versions["moving_second"] = seed.version(sets["moving"], classified=("P", "AR"))
    seed.commit()
    return World(school, clinic, sets, versions)


def _head(session: Session, document_uid: str) -> str:
    return str(
        session.execute(
            text("SELECT current_version_uid FROM document WHERE document_uid = :d"),
            {"d": document_uid},
        ).scalar_one()
    )


def _members(session: Session, section: str, **extra) -> list[str]:
    return [
        str(item.document_uid)
        for item in documents.list_current_versions_in_section(session, section_code=section, **extra)
    ]


def _titles(session: Session, section: str, **extra) -> list[str]:
    return sorted(
        item.display_title
        for item in documents.list_current_versions_in_section(session, section_code=section, **extra)
    )


def test_members_are_the_sets_whose_current_version_is_confirmed_in_the_section(
    session: Session, world: World
) -> None:
    # Moving's head is its second version (AR) -- see the head test below for the move.
    assert _titles(session, "AR") == ["АР-1", "АР-1 поликлиника", "АР-3", "ОВ-1"]
    assert _titles(session, "KJ") == ["КЖ-1"]
    assert _titles(session, "PS") == ["ПЗ-1"]
    assert _titles(session, "PB") == []
    assert _titles(session, "not-a-section") == []


def test_an_older_versions_confirmation_never_makes_a_set_a_member(
    session: Session, world: World
) -> None:
    older = world.sets["older_ar"]
    assert older not in _members(session, "AR")
    assert older in {str(item.document_uid) for item in documents.list_unclassified_current_versions(session)}


def test_the_legacy_document_section_is_not_a_confirmation(session: Session, world: World) -> None:
    assert world.sets["legacy_ar"] not in _members(session, "AR")
    # ... and a legacy label that disagrees with the confirmation yields to the confirmation.
    assert world.sets["kj"] in _members(session, "KJ")
    assert world.sets["kj"] not in _members(session, "AR")


def test_a_set_with_no_published_head_is_in_no_answer(session: Session, world: World) -> None:
    headless = world.sets["headless"]
    assert headless not in _members(session, "AR")
    assert headless not in {str(item.document_uid) for item in documents.list_unclassified_current_versions(session)}


def test_the_unclassified_sets_are_the_complement(session: Session, world: World) -> None:
    unclassified = documents.list_unclassified_current_versions(session)
    assert sorted(item.display_title for item in unclassified) == [
        "АР-2", "АР-4", "Комплект без раздела",
    ]
    for item in unclassified:
        assert (item.project_stage, item.section_code) == (None, None)
    # Every set that has a head is exactly one of: a member of some section, or unclassified.
    placed = {
        str(item.document_uid)
        for code in ("AR", "AI", "KM", "KJ", "OV", "EOM", "VK", "PT", "PB", "SS", "ITP", "GP", "TX", "POS", "PS")
        for item in documents.list_current_versions_in_section(session, section_code=code)
    }
    assert placed.isdisjoint({str(item.document_uid) for item in unclassified})
    assert len(placed) + len(unclassified) == len(world.sets) - 1  # the headless set


def test_a_record_carries_what_the_section_view_needs(session: Session, world: World) -> None:
    (record,) = [
        item
        for item in documents.list_current_versions_in_section(session, section_code="AR")
        if item.display_title == "АР-3"
    ]
    assert str(record.project_uid) == world.school
    assert record.project_name == "Школа на 550 мест"
    assert str(record.document_uid) == world.sets["newer_ar"]
    assert str(record.version_uid) == world.versions["newer_ar"]
    assert (record.version_ordinal, record.page_count) == (2, 3)
    assert (record.project_stage, record.section_code) == ("P", "AR")


def test_a_project_with_several_sets_across_sections_is_placed_set_by_set(
    session: Session, world: World
) -> None:
    school = ProjectUid.parse(world.school)
    assert _titles(session, "AR", project_uid=school) == ["АР-1", "АР-3"]
    assert _titles(session, "KJ", project_uid=school) == ["КЖ-1"]
    assert _titles(session, "PS", project_uid=school) == ["ПЗ-1"]
    unclassified = documents.list_unclassified_current_versions(session, project_uid=school)
    assert sorted(item.display_title for item in unclassified) == ["АР-2", "АР-4"]


def test_a_project_filter_narrows_both_queries_and_an_unknown_project_is_empty(
    session: Session, world: World
) -> None:
    clinic = ProjectUid.parse(world.clinic)
    assert _titles(session, "AR", project_uid=clinic) == ["АР-1 поликлиника", "ОВ-1"]
    assert [
        item.display_title
        for item in documents.list_unclassified_current_versions(session, project_uid=clinic)
    ] == ["Комплект без раздела"]
    unknown = ProjectUid.new()
    assert _members(session, "AR", project_uid=unknown) == []
    assert documents.list_unclassified_current_versions(session, project_uid=unknown) == ()


def test_the_head_selects_the_version_that_places_the_set(session: Session, world: World) -> None:
    moving = world.sets["moving"]
    assert moving in _members(session, "AR") and moving not in _members(session, "KJ")
    Seeder(session).point_at(moving, world.versions["moving_first"])
    session.commit()
    assert moving in _members(session, "KJ") and moving not in _members(session, "AR")
    # The older confirmation did not move when the head moved away from it and back.
    Seeder(session).point_at(moving, world.versions["moving_second"])
    session.commit()
    assert moving in _members(session, "AR")


def test_pages_are_keyset_ordered_complete_and_never_repeat(session: Session, world: World) -> None:
    whole = _members(session, "AR")
    assert whole == sorted(whole) and len(whole) == 4
    walked: list[str] = []
    after: DocumentUid | None = None
    pages = 0
    while True:
        page = documents.list_current_versions_in_section(
            session, section_code="AR", after=after, limit=3
        )
        if not page:
            break
        pages += 1
        assert len(page) <= 3 and pages <= 3, "the walk does not end"
        walked.extend(str(item.document_uid) for item in page)
        after = page[-1].document_uid
        if len(page) < 3:
            break
    assert walked == whole and pages == 2
    # The same walk over the unclassified complement.
    unclassified = [
        str(item.document_uid) for item in documents.list_unclassified_current_versions(session)
    ]
    one_by_one: list[str] = []
    after = None
    while True:
        page = documents.list_unclassified_current_versions(session, after=after, limit=1)
        if not page:
            break
        one_by_one.append(str(page[0].document_uid))
        assert len(one_by_one) <= len(unclassified), "the walk does not end"
        after = page[0].document_uid
    assert one_by_one == unclassified == sorted(unclassified)


@pytest.mark.parametrize("limit", [0, -1, MAX_PLACEMENT_PAGE + 1, True, "5", None])
def test_the_page_size_is_bounded(session: Session, world: World, limit) -> None:
    for call in (
        lambda: documents.list_current_versions_in_section(session, section_code="AR", limit=limit),
        lambda: documents.list_unclassified_current_versions(session, limit=limit),
    ):
        with pytest.raises(DomainError) as caught:
            call()
        assert caught.value.code is ErrorCode.VALIDATION_FAILED
        assert caught.value.detail_fields["field"] == "limit"
    assert len(documents.list_current_versions_in_section(session, section_code="AR", limit=MAX_PLACEMENT_PAGE)) == 4


def test_count_projects_counts_without_listing(session: Session, world: World) -> None:
    assert documents.count_projects(session) == 2
    Seeder(session).project("Третий")
    session.commit()
    assert documents.count_projects(session) == 3
