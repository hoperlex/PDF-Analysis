"""`W63-SECTION-FORM7-01` phase A: «Оптимизация разделов» on real PostgreSQL and MinIO.

Projects, document sets, versions and their Blobs, the experts' classifications and the
price-list revisions are real rows written through their owning boundaries (``storage``,
``documents``, ``sections``, ``optimisation``). The runs and the saved text layers come through
the query's port, as the composition root will supply them; the stand-in answers per version
and records what it was asked.

The world: two projects whose current versions are confirmed **AR** with the same sheet and
different price lists; one project confirmed **KJ**; one whose current version is
unclassified although its older version was confirmed AR; one AR project with no price list.
Rows are never merged across projects, each row is priced from its own project's list,
totals exist per project and currency only, nothing is written.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.public import AccountRepository
from auditmanager.documents.public import DocumentRepository, ManifestEntry
from auditmanager.optimisation import section_specification as module
from auditmanager.optimisation.project_match import RunCandidate, SavedPageText
from auditmanager.optimisation.public import PriceListUploads
from auditmanager.optimisation.section_specification import (
    EXCLUSION_VERSION_UNCLASSIFIED,
    LIMIT_SOURCES,
    PRICE_STATE_NOT_READ,
    PRICE_STATE_PRICE_LIST_MISSING,
    PRICE_STATE_PRICED,
    ROW_PRICE_LIST_MISSING,
    SECTION_STATE_READY,
    SECTION_STATE_TOO_LARGE,
    SOURCE_STATE_ANALYSIS_MISSING,
    SOURCE_STATE_NOT_READ,
    SOURCE_STATE_READY,
    SectionSpecification,
    read_section_specification,
)
from auditmanager.sections.public import classify_document_version
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, ProjectUid, RunId
from auditmanager.storage import S3BlobStore, sha256_of
from auditmanager.storage.blob_repository import BlobMetadataRepository
from auditmanager.storage.models import VerifiedBlob, parse_blob_role

accounts = AccountRepository()
documents = DocumentRepository()

LAYER_SHA256 = "e" * 64

#: One Form-7 sheet (sheet 7), the same in every AR project.
SHEET = (
    "Поз. Наименование и техническая характеристика Тип, марка Код Завод- Ед. Кол. Масса Примечание\n"
    "изготовитель изм. 1 ед., кг\n"
    "1 Дверь противопожарная ДПМ-01/60 EI60 ООО «Промет» шт. 4 45,5\n"
    "2 Окно ПВХ двухкамерное ОП В2 1460х1460 шт 12\n"
    "3 Анкер химический HIT-HY 200 шт 200\n"
    "Изм. Кол.уч. Лист №док. Подпись Дата\n"
    "Стадия Лист Листов\n"
    "Р 7 12\n"
)
COVER = "Общие данные\nВедомость рабочих чертежей\n"
PAGES = {1: COVER, 2: SHEET}
DOOR = "Дверь противопожарная ДПМ-01/60 EI60 ООО «Промет»"
WINDOW = "Окно ПВХ двухкамерное ОП В2 1460х1460"
ANCHOR = "Анкер химический HIT-HY 200"

SCHOOL_PRICES = (
    "Наименование;Марка;Ед. изм.;Цена;Валюта\n"
    "Дверь противопожарная;ДПМ-01/60;шт;25000;RUB\n"
    "Анкер химический;HIT-HY 200;шт;12,75;EUR\n"
).encode("utf-8")
KINDERGARTEN_PRICES = (
    "Наименование;Марка;Ед. изм.;Цена;Валюта\n"
    "Дверь противопожарная;ДПМ-01/60;шт;31000;RUB\n"
    "Окно ПВХ двухкамерное ОП В2 1460х1460;;шт;18500,5;RUB\n"
).encode("utf-8")
CLINIC_PRICES = "Наименование;Марка;Ед. изм.;Цена;Валюта\nДверь противопожарная;ДПМ-01/60;шт;1;RUB\n".encode()


class _Reader:
    """The runs-and-text port, answering per version from memory, recording every question."""

    def __init__(self) -> None:
        self.runs: dict[str, list[RunCandidate]] = {}
        self.texts: dict[str, SavedPageText | None] = {}
        self.asked_runs: list[str] = []
        self.asked_texts: list[tuple[str, str, int]] = []

    def publish(self, version_uid: str, pages: Mapping[int, str] | None = PAGES) -> None:
        run_id = str(RunId.new())
        self.runs[version_uid] = [RunCandidate(str(RunId.new()), "failed"), RunCandidate(run_id, "published")]
        self.texts[run_id] = None if pages is None else SavedPageText(run_id, LAYER_SHA256, dict(pages))

    def runs_newest_first(self, session: Session, *, version_uid: str) -> Sequence[RunCandidate]:
        self.asked_runs.append(version_uid)
        return tuple(self.runs.get(version_uid, ()))

    def saved_page_text(
        self, session: Session, *, run_id: str, version_uid: str, page_count: int
    ) -> SavedPageText | None:
        self.asked_texts.append((run_id, version_uid, page_count))
        return self.texts.get(run_id)


def _blob_entry(session: Session, store: S3BlobStore, label: str) -> ManifestEntry:
    payload = f"%PDF-1.7 synthetic {label}".encode()
    digest = sha256_of(payload)
    published = store.put_blob(
        payload,
        declared_sha256=digest,
        declared_size=len(payload),
        role=parse_blob_role("source_document"),
        media_type="application/pdf",
    )
    blobs = BlobMetadataRepository()
    blobs.record_verified(
        session,
        VerifiedBlob(
            blob_id=published.blob_id,
            upload_token=f"seeded-{label}",
            sha256=published.sha256,
            size=published.size,
            role=published.role,
            media_type=published.media_type,
        ),
    )
    blobs.mark_available(session, published.blob_id)
    return ManifestEntry(
        role="source_document",
        blob_id=published.blob_id,
        sha256=published.sha256,
        size_bytes=published.size,
        media_type=published.media_type,
    )


def _publish(session: Session, store: S3BlobStore, document_uid: DocumentUid, label: str) -> str:
    entry = _blob_entry(session, store, label)
    return str(
        documents.publish_version(
            session,
            document_uid=document_uid,
            media_type="application/pdf",
            byte_size=entry.size_bytes,
            sha256=entry.sha256,
            page_count=len(PAGES),
            source_filename=None,
            entries=(entry,),
        )
    )


class World:
    def __init__(self, session: Session, store: S3BlobStore, factory: sessionmaker[Session], cast: Any):
        self.session, self.store, self.factory, self.cast = session, store, factory, cast
        self.reader = _Reader()
        self.versions: dict[str, tuple[str, str, str]] = {}  # title -> (project, document, version)
        self.projects: dict[str, str] = {}
        self.current_warehouse = ""

    def set(self, project_uid: str, title: str, section: str | None, *, published: bool = True) -> str:
        document = documents.create_document(
            self.session, project_uid=ProjectUid.parse(project_uid), display_title=title
        )
        version = _publish(self.session, self.store, document, title)
        self.session.commit()
        self.versions[title] = (project_uid, str(document), version)
        if section is not None:
            self.classify(title, section)
        if published:
            self.reader.publish(version)
        return version

    def classify(self, title: str, section: str) -> None:
        project, document, version = self.versions[title]
        classify_document_version(
            self.session,
            project_uid=project,
            document_uid=document,
            version_uid=version,
            project_stage="R",
            section_code=section,
            actor_uid=self.cast.expert,
            actor_roles=accounts.roles_of(self.session, self.cast.expert),
        )
        self.session.commit()

    def prices(self, project_uid: str, content: bytes, key: str) -> str:
        outcome = PriceListUploads(self.store, session_factory=self.factory).upload(
            project_uid=project_uid,
            content=content,
            source_filename=f"{key}.csv",
            idempotency_key=key,
            actor_uid=self.cast.expert,
        )
        return outcome.revision.price_list_id

    def read(self, section: str = "AR", **extra: Any) -> SectionSpecification:
        arguments: dict[str, Any] = {
            "section_code": section,
            "actor_roles": frozenset({"expert"}),
            "reader": self.reader,
            "limit": 200,
        }
        arguments.update(extra)
        return read_section_specification(self.session, **arguments)


@pytest.fixture
def world(session: Session, store: S3BlobStore, factory: sessionmaker[Session], cast: Any) -> World:
    built = World(session, store, factory, cast)
    clinic = str(documents.create_project(session, "Поликлиника").project_uid)
    warehouse = str(documents.create_project(session, "Склад").project_uid)
    garage = str(documents.create_project(session, "Гараж").project_uid)
    session.commit()
    built.projects = {
        "school": cast.project, "kindergarten": cast.other_project,
        "clinic": clinic, "warehouse": warehouse, "garage": garage,
    }
    built.set(cast.project, "13АВ-РД-АР школа", "AR")
    built.set(cast.other_project, "07-РД-АР сад", "AR")
    built.set(clinic, "11-РД-КЖ поликлиника", "KJ")
    # The warehouse's set: version 1 confirmed AR, version 2 (now current) unclassified.
    built.set(warehouse, "05-РД-АР склад", "AR")
    _, warehouse_document, _ = built.versions["05-РД-АР склад"]
    built.current_warehouse = _publish(
        session, store, DocumentUid.parse(warehouse_document), "05-РД-АР склад v2"
    )
    session.commit()
    built.reader.publish(built.current_warehouse)
    built.set(garage, "09-РД-АР гараж", "AR")
    built.prices(cast.project, SCHOOL_PRICES, "school-1")
    built.prices(cast.other_project, KINDERGARTEN_PRICES, "kindergarten-1")
    built.prices(clinic, CLINIC_PRICES, "clinic-1")
    return built


def _refused(code: ErrorCode, call: Any, *args: Any, **kwargs: Any) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call(*args, **kwargs)
    assert caught.value.code is code, (caught.value.code, dict(caught.value.detail_fields))
    return caught.value


# -- two projects, one section; one in another section; one unclassified --------------------


def test_two_projects_in_one_section_keep_their_rows_apart_and_their_own_prices(world: World) -> None:
    answer = world.read()
    p = world.projects
    assert answer.state == SECTION_STATE_READY
    # «Гараж», «Детский сад», «Школа на 550 мест» -- by name; the clinic and warehouse absent.
    assert [project.project_uid for project in answer.projects] == [
        p["garage"], p["kindergarten"], p["school"],
    ]
    assert answer.source_count == 3 and answer.row_count == answer.rows.total == 9
    assert [row.project_uid for row in answer.rows.items] == (
        [p["garage"]] * 3 + [p["kindergarten"]] * 3 + [p["school"]] * 3
    )
    for project in answer.projects:
        (source,) = project.sources
        own = [row for row in answer.rows.items if row.project_uid == project.project_uid]
        assert source.state == SOURCE_STATE_READY and source.row_count == 3
        assert source.text_layer_sha256 == LAYER_SHA256 and source.table_count == 1
        assert source.version_uid == world.versions[source.display_title][2]
        assert {(row.document_uid, row.version_uid) for row in own} == {
            (source.document_uid, source.version_uid)
        }
        assert {(row.row.page_number, row.row.sheet_label) for row in own} == {(2, "7")}
        for row in own:
            if row.match is not None and row.match.position is not None:
                assert row.match.position.price_list_id == project.price_list.price_list_id

    doors = {row.project_uid: row for row in answer.rows.items if row.row.name == DOOR}
    assert len({row.row.row_id for row in doors.values()}) == 3
    assert doors[p["school"]].match.amount == Decimal("100000")
    assert doors[p["kindergarten"]].match.amount == Decimal("124000")
    assert doors[p["garage"]].match is None
    assert doors[p["garage"]].price_status == ROW_PRICE_LIST_MISSING


def test_totals_exist_per_project_and_currency_only(world: World) -> None:
    answer = world.read()
    garage, kindergarten, school = answer.projects
    assert [(t.currency, t.amount, t.row_count) for t in school.totals] == [
        ("EUR", Decimal("2550.00"), 1), ("RUB", Decimal("100000"), 1),
    ]
    assert [(t.currency, t.amount, t.row_count) for t in kindergarten.totals] == [
        ("RUB", Decimal("124000") + Decimal("222006.0"), 2),
    ]
    assert dict(kindergarten.excluded_by_reason) == {"no_position": 1}
    assert (school.price_state, kindergarten.price_state) == (PRICE_STATE_PRICED, PRICE_STATE_PRICED)
    assert (school.position_count, kindergarten.position_count) == (2, 2)
    assert (garage.price_state, garage.price_list, garage.totals) == (PRICE_STATE_PRICE_LIST_MISSING, None, ())
    assert not hasattr(answer, "totals")


def test_a_project_in_another_section_never_appears(world: World) -> None:
    p = world.projects
    answer = world.read()
    seen = (
        {project.project_uid for project in answer.projects}
        | {item.project_uid for item in answer.excluded}
        | {row.project_uid for row in answer.rows.items}
    )
    assert p["clinic"] not in seen
    clinic_version = world.versions["11-РД-КЖ поликлиника"][2]
    assert clinic_version not in world.reader.asked_runs
    kj = world.read("KJ")
    assert [project.project_uid for project in kj.projects] == [p["clinic"]]
    assert [row.match.amount for row in kj.rows.items if row.row.name == DOOR] == [Decimal("4")]


def test_an_unclassified_current_version_is_excluded_even_after_an_ar_older_version(world: World) -> None:
    p = world.projects
    answer = world.read()
    assert [(item.project_uid, item.version_uid, item.version_ordinal, item.reason)
            for item in answer.excluded] == [
        (p["warehouse"], world.current_warehouse, 2, EXCLUSION_VERSION_UNCLASSIFIED),
    ]
    older = world.versions["05-РД-АР склад"][2]
    assert older not in world.reader.asked_runs
    assert world.current_warehouse not in world.reader.asked_runs
    assert p["warehouse"] not in {row.project_uid for row in answer.rows.items}


def test_a_set_without_a_published_run_is_analysis_missing(world: World) -> None:
    school = world.projects["school"]
    world.set(school, "13АВ-РД-АР школа корпус Б", "AR", published=False)
    project = next(item for item in world.read().projects if item.project_uid == school)
    assert [(source.display_title, source.state) for source in project.sources] == [
        ("13АВ-РД-АР школа", SOURCE_STATE_READY),
        ("13АВ-РД-АР школа корпус Б", SOURCE_STATE_ANALYSIS_MISSING),
    ]
    assert project.row_count == 3


# -- filters, paging, bounds ---------------------------------------------------------------------


def test_project_filter_query_and_paging(world: World) -> None:
    p = world.projects
    whole = world.read()
    narrowed = world.read(project_uid=p["kindergarten"])
    assert [project.project_uid for project in narrowed.projects] == [p["kindergarten"]]
    assert narrowed.projects[0] == whole.projects[1]
    assert {row.project_uid for row in narrowed.rows.items} == {p["kindergarten"]}
    assert (narrowed.excluded, narrowed.row_count) == ((), 3)
    warehouse = world.read(project_uid=p["warehouse"])
    assert (warehouse.projects, warehouse.excluded_count) == ((), 1)

    searched = world.read(query="анкер ХИМИЧЕСКИЙ")
    assert [(row.project_uid, row.row.name) for row in searched.rows.items] == [
        (p["garage"], ANCHOR), (p["kindergarten"], ANCHOR), (p["school"], ANCHOR),
    ]
    assert searched.projects == whole.projects and searched.row_count == 9

    first = world.read(offset=0, limit=4)
    second = world.read(offset=4, limit=4)
    third = world.read(offset=8, limit=4)
    assert [page.rows.next_offset for page in (first, second, third)] == [4, 8, None]
    assert [row.row.row_id for page in (first, second, third) for row in page.rows.items] == [
        row.row.row_id for row in whole.rows.items
    ]
    _refused(ErrorCode.NOT_FOUND, world.read, project_uid=str(ProjectUid.new()))


def test_over_the_source_bound_the_membership_is_served_and_no_text_read(
    world: World, monkeypatch
) -> None:
    monkeypatch.setattr(module, "MAX_SECTION_SOURCES", 2)
    answer = world.read()
    assert (answer.state, answer.limit_reason, answer.rows) == (SECTION_STATE_TOO_LARGE, LIMIT_SOURCES, None)
    assert answer.source_count == 3 and len(answer.projects) == 3
    assert {project.price_state for project in answer.projects} == {PRICE_STATE_NOT_READ}
    assert {s.state for project in answer.projects for s in project.sources} == {SOURCE_STATE_NOT_READ}
    assert world.reader.asked_runs == []
    one = world.read(project_uid=world.projects["school"])
    assert one.state == SECTION_STATE_READY and one.rows.total == 3


# -- nothing written; roles ----------------------------------------------------------------------


def test_the_read_writes_nothing(world: World) -> None:
    session = world.session
    tables = ("price_list_revision", "price_list_position", "command_record", "blob",
              "document", "document_version", "document_version_classification")

    def counts() -> dict[str, int]:
        session.rollback()
        return {name: int(session.execute(text(f"SELECT count(*) FROM {name}")).scalar_one())
                for name in tables}

    before = counts()
    world.read()
    world.read(query="дверь", project_uid=world.projects["school"])
    assert not session.new and not session.dirty and not session.deleted
    assert counts() == before


def test_roles_and_request_values(world: World) -> None:
    denied = _refused(ErrorCode.PERMISSION_DENIED, world.read, actor_roles=frozenset())
    assert denied.detail_fields["required_capability"] == "role:admin|expert"
    assert world.read(actor_roles=frozenset({"admin"})).state == SECTION_STATE_READY
    for field, value in (("section_code", "АР"), ("project_uid", "prj_bad"), ("limit", 201)):
        refused = _refused(ErrorCode.VALIDATION_FAILED, world.read, **{field: value})
        assert refused.detail_fields["field"] == field
