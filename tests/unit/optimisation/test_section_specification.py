"""`W63-SECTION-FORM7-01` phase A: the section's combined specification, container-free.

The composition rules are the subject, over in-memory stand-ins for the documents
projection, the price-list repository and the runs-and-text port: membership by the
**current** version's confirmed section only (another section never appears, an unclassified
version is listed as excluded), every row priced from **its own** project's current list,
rows never merged across projects, totals per project and currency only, explicit states and
documented bounds, filters that narrow rows but never a project's totals.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from auditmanager.documents.public import (
    DocumentVersionRecord,
    ProjectListingRecord,
    ProjectRecord,
    VersionClassificationRecord,
)
from auditmanager.optimisation import section_specification as module
from auditmanager.optimisation import specification
from auditmanager.optimisation.matching import STATUS_AMBIGUOUS, STATUS_MATCHED, STATUS_UNMATCHED
from auditmanager.optimisation.project_match import RunCandidate, SavedPageText
from auditmanager.optimisation.repository import PriceListPositionRecord, PriceListRevisionRecord
from auditmanager.optimisation.section_specification import (
    EXCLUSION_VERSION_UNCLASSIFIED,
    LIMIT_PROJECTS,
    LIMIT_ROWS,
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
    SOURCE_STATE_SPECIFICATION_TOO_LARGE,
    SOURCE_STATE_TEXT_UNAVAILABLE,
    SectionSpecification,
    read_section_specification,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid

STATUSES_MATCHED = (STATUS_MATCHED, STATUS_AMBIGUOUS, STATUS_UNMATCHED)
NOW = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
EXPERT = "usr_01M2545JSD15ETSNNV904XA0E1"
LAYER = "a" * 64

#: A Form-7 sheet: split header, four rows, the stamp with sheet 7.
FORM7_PAGE = (
    "Поз. Наименование и техническая характеристика Тип, марка Код Завод- Ед. Кол. Масса Примечание\n"
    "изготовитель изм. 1 ед., кг\n"
    "1 Дверь противопожарная ДПМ-01/60 EI60 ООО «Промет» шт. 4 45,5\n"
    "2 Окно ПВХ двухкамерное ОП В2 1460х1460 шт 12\n"
    "3 Анкер химический HIT-HY 200 шт 200\n"
    "4 Ёмкость   накопительная ЕН-200 шт 2\n"
    "Изм. Кол.уч. Лист №док. Подпись Дата\n"
    "Стадия Лист Листов\n"
    "Р 7 12\n"
)
DOOR = "Дверь противопожарная ДПМ-01/60 EI60 ООО «Промет»"
WINDOW = "Окно ПВХ двухкамерное ОП В2 1460х1460"
ANCHOR = "Анкер химический HIT-HY 200"
TANK = "Ёмкость накопительная ЕН-200"


# --- stand-ins --------------------------------------------------------------------------


@dataclass
class _Documents:
    """The documents projection: projects, and the current version of each set."""

    projects: dict[str, str] = field(default_factory=dict)
    current: dict[str, list[DocumentVersionRecord]] = field(default_factory=dict)
    listed: list[str] = field(default_factory=list)

    def get_project(self, session: Any, project_uid: ProjectUid) -> ProjectRecord:
        if str(project_uid) not in self.projects:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Project")
        return ProjectRecord(project_uid, self.projects[str(project_uid)], NOW)

    def list_projects(self, session: Any) -> tuple[ProjectListingRecord, ...]:
        return tuple(
            ProjectListingRecord(ProjectUid.parse(uid), name, NOW, len(self.current.get(uid, ())))
            for uid, name in self.projects.items()
        )

    def list_documents(self, session: Any, project_uid: ProjectUid) -> tuple[DocumentVersionRecord, ...]:
        self.listed.append(str(project_uid))
        return tuple(self.current.get(str(project_uid), ()))


@dataclass
class _Prices:
    """The price-list repository: revisions newest first, positions by revision."""

    revisions: dict[str, list[PriceListRevisionRecord]] = field(default_factory=dict)
    positions: dict[str, list[PriceListPositionRecord]] = field(default_factory=dict)
    asked: list[str] = field(default_factory=list)

    def list_price_lists(self, session: Any, project_uid: str) -> tuple[PriceListRevisionRecord, ...]:
        self.asked.append(project_uid)
        return tuple(self.revisions.get(project_uid, ()))

    def position_page(
        self, session: Any, price_list_id: str, *, offset: int, limit: int
    ) -> tuple[PriceListPositionRecord, ...]:
        return tuple(self.positions.get(price_list_id, ())[offset : offset + limit])


@dataclass
class _Reader:
    """The runs-and-text port: runs by version, text by run."""

    runs: dict[str, list[RunCandidate]] = field(default_factory=dict)
    texts: dict[str, SavedPageText | None] = field(default_factory=dict)
    asked: list[str] = field(default_factory=list)

    def runs_newest_first(self, session: Any, *, version_uid: str) -> Sequence[RunCandidate]:
        self.asked.append(version_uid)
        return tuple(self.runs.get(version_uid, ()))

    def saved_page_text(
        self, session: Any, *, run_id: str, version_uid: str, page_count: int
    ) -> SavedPageText | None:
        return self.texts.get(run_id)


@dataclass
class World:
    documents: _Documents = field(default_factory=_Documents)
    prices: _Prices = field(default_factory=_Prices)
    reader: _Reader = field(default_factory=_Reader)
    serial: int = 0

    def _next(self) -> int:
        self.serial += 1
        return self.serial

    def project(self, name: str) -> str:
        uid = str(ProjectUid.new())
        self.documents.projects[uid] = name
        return uid

    def version(
        self,
        project_uid: str,
        title: str,
        section: str | None,
        *,
        pages: Mapping[int, str] | None = None,
        published: bool = True,
        text: bool = True,
        stage: str = "R",
    ) -> DocumentVersionRecord:
        version_uid = VersionUid.new()
        classification = (
            None
            if section is None
            else VersionClassificationRecord(version_uid, stage, section, EXPERT, NOW)
        )
        pages = dict(pages or {1: FORM7_PAGE})
        record = DocumentVersionRecord(
            version_uid=version_uid,
            document_uid=DocumentUid.new(),
            project_uid=ProjectUid.parse(project_uid),
            version_ordinal=1,
            display_title=title,
            section=None,
            media_type="application/pdf",
            byte_size=100,
            sha256="b" * 64,
            page_count=len(pages),
            published_at=NOW,
            manifest=(),
            classification=classification,
        )
        self.documents.current.setdefault(project_uid, []).append(record)
        if published:
            run_id = f"run_01M2545JSD15ETSNNV904X{self._next():04d}"
            self.reader.runs[str(version_uid)] = [
                RunCandidate(f"run_01M2545JSD15ETSNNV904Y{self._next():04d}", "failed"),
                RunCandidate(run_id, "published"),
            ]
            self.reader.texts[run_id] = SavedPageText(run_id, LAYER, pages) if text else None
        return record

    def price_list(self, project_uid: str, *rows: tuple[str, str | None, str, str, str]) -> str:
        """Upload a revision: rows of (name, mark, unit, price, currency)."""
        number = len(self.prices.revisions.get(project_uid, ())) + 1
        price_list_id = f"prl_01M2545JSD15ETSNNV904X{self._next():04d}"
        revision = PriceListRevisionRecord(
            price_list_id=price_list_id,
            project_uid=project_uid,
            revision_number=number,
            uploaded_by_user_uid=EXPERT,
            uploaded_at=NOW,
            blob_id="blob_01M2545JSD15ETSNNV904XA001",
            sha256="c" * 64,
            size_bytes=10,
            media_type="text/csv",
            source_format="csv",
            source_filename="prices.csv",
            default_currency=None,
            parse_report={},
            data_row_count=len(rows),
            accepted_row_count=len(rows),
            skipped_row_count=0,
            is_current=True,
        )
        earlier = [replace(item, is_current=False) for item in self.prices.revisions.get(project_uid, [])]
        self.prices.revisions[project_uid] = [revision, *earlier]
        self.prices.positions[price_list_id] = [
            PriceListPositionRecord(
                price_list_position_id=f"prp_01M2545JSD15ETSNNV904X{self._next():04d}",
                price_list_id=price_list_id,
                row_number=index,
                code=None,
                name=name,
                mark=mark,
                unit=unit,
                unit_price=Decimal(price),
                currency=currency,
                vendor=None,
                section_code=None,
            )
            for index, (name, mark, unit, price, currency) in enumerate(rows, start=2)
        ]
        return price_list_id

    def read(self, section: str = "AR", **extra: Any) -> SectionSpecification:
        arguments: dict[str, Any] = {
            "section_code": section,
            "actor_roles": frozenset({"expert"}),
            "reader": self.reader,
            "documents": self.documents,
            "repository": self.prices,
            "limit": 200,
        }
        arguments.update(extra)
        return read_section_specification(None, **arguments)  # type: ignore[arg-type]


def _refused(code: ErrorCode, call: Any, *args: Any, **kwargs: Any) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call(*args, **kwargs)
    assert caught.value.code is code, (caught.value.code, dict(caught.value.detail_fields))
    return caught.value


@pytest.fixture
def world() -> World:
    """Two AR projects with different lists, a KJ project, an unclassified one, an AR one unpriced."""
    built = World()
    zarya = built.project("Корпус 2 «Заря»")
    alpha = built.project("корпус 1 «Альфа»")
    kj = built.project("Корпус 3 (КЖ)")
    loose = built.project("Корпус 4 без раздела")
    bare = built.project("Корпус 5 без прайса")
    built.version(alpha, "АР-1", "AR")
    built.version(zarya, "АР-2", "AR")
    built.version(kj, "КЖ-3", "KJ")
    built.version(loose, "Новый комплект", None)
    built.version(bare, "АР-5", "AR")
    built.price_list(
        alpha,
        ("Дверь противопожарная", "ДПМ-01/60", "шт", "25000", "RUB"),
        ("Анкер химический", "HIT-HY 200", "шт", "12,75".replace(",", "."), "EUR"),
    )
    built.price_list(
        zarya,
        ("Дверь противопожарная", "ДПМ-01/60", "шт", "30000", "RUB"),
        ("Окно ПВХ двухкамерное ОП В2 1460х1460", None, "шт", "18000", "RUB"),
        ("Окно ПВХ двухкамерное ОП В2 1460х1460", None, "шт", "18100", "RUB"),
    )
    built.price_list(kj, ("Дверь противопожарная", "ДПМ-01/60", "шт", "1", "RUB"))
    return built


def _uid(world: World, name: str) -> str:
    return next(uid for uid, label in world.documents.projects.items() if label == name)


# -- membership ----------------------------------------------------------------------------


def test_members_are_current_versions_confirmed_in_the_section_in_name_order(world: World) -> None:
    answer = world.read()
    assert answer.state == SECTION_STATE_READY and answer.limit_reason is None
    assert [project.project_name for project in answer.projects] == [
        "корпус 1 «Альфа»", "Корпус 2 «Заря»", "Корпус 5 без прайса",
    ]
    assert answer.source_count == 3
    for project in answer.projects:
        assert [source.state for source in project.sources] == [SOURCE_STATE_READY]
        assert project.sources[0].project_uid == project.project_uid
        assert project.sources[0].project_stage == "R"


def test_another_sections_project_never_appears_anywhere(world: World) -> None:
    kj = _uid(world, "Корпус 3 (КЖ)")
    answer = world.read()
    assert kj not in {project.project_uid for project in answer.projects}
    assert kj not in {item.project_uid for item in answer.excluded}
    assert kj not in {row.project_uid for row in answer.rows.items}
    # Its own price list was never even read for this section.
    assert kj not in world.prices.asked
    only_kj = world.read("KJ")
    assert [project.project_uid for project in only_kj.projects] == [kj]


def test_an_unclassified_current_version_is_listed_as_excluded_and_contributes_nothing(
    world: World,
) -> None:
    loose = _uid(world, "Корпус 4 без раздела")
    answer = world.read()
    assert [(item.project_uid, item.display_title, item.reason) for item in answer.excluded] == [
        (loose, "Новый комплект", EXCLUSION_VERSION_UNCLASSIFIED),
    ]
    assert answer.excluded_count == 1
    assert loose not in {project.project_uid for project in answer.projects}
    assert loose not in {row.project_uid for row in answer.rows.items}


def test_only_the_current_versions_classification_counts(world: World) -> None:
    """The stand-in lists current versions only, as ``listDocuments`` does: a set whose
    current version is unclassified is excluded whatever an older version said."""
    project = world.project("Корпус 6")
    world.version(project, "АР-6", None)
    answer = world.read()
    assert project not in {item.project_uid for item in answer.projects}
    assert project in {item.project_uid for item in answer.excluded}


def test_a_projects_several_member_sets_are_sources_in_title_order(world: World) -> None:
    alpha = _uid(world, "корпус 1 «Альфа»")
    world.version(alpha, "АР-0 паркинг", "AR", stage="P")
    world.version(alpha, "КЖ-1", "KJ")
    project = next(item for item in world.read().projects if item.project_uid == alpha)
    assert [(source.display_title, source.project_stage) for source in project.sources] == [
        ("АР-0 паркинг", "P"), ("АР-1", "R"),
    ]
    assert project.row_count == 8


# -- rows: provenance, own price list, never merged -----------------------------------------


def test_rows_carry_their_full_address_and_are_never_merged_across_projects(world: World) -> None:
    answer = world.read()
    alpha, zarya, bare = (project.project_uid for project in answer.projects)
    assert answer.row_count == answer.rows.total == 12
    assert [row.project_uid for row in answer.rows.items] == [alpha] * 4 + [zarya] * 4 + [bare] * 4
    doors = [row for row in answer.rows.items if row.row.name == DOOR]
    assert len(doors) == 3 and len({row.row.row_id for row in doors}) == 3
    for row, project in zip(answer.rows.items, [p for p in answer.projects for _ in range(4)]):
        source = project.sources[0]
        assert (row.document_uid, row.version_uid) == (source.document_uid, source.version_uid)
        assert (row.row.page_number, row.row.sheet_label) == (1, "7")
        assert row.row.line_start == row.row.line_end and row.row.line_start >= 3


def test_every_row_is_priced_from_its_own_projects_current_list(world: World) -> None:
    answer = world.read()
    alpha, zarya, bare = answer.projects
    by_project = {
        project.project_uid: {row.row.name: row for row in answer.rows.items
                              if row.project_uid == project.project_uid}
        for project in answer.projects
    }
    door_a = by_project[alpha.project_uid][DOOR]
    door_z = by_project[zarya.project_uid][DOOR]
    assert door_a.match.position.price_list_id == alpha.price_list.price_list_id
    assert door_z.match.position.price_list_id == zarya.price_list.price_list_id
    assert (door_a.match.amount, door_z.match.amount) == (Decimal("100000"), Decimal("120000"))
    # The anchor is in Alpha's list only; Zarya's own list has no position for it.
    assert by_project[alpha.project_uid][ANCHOR].match.amount == Decimal("2550.00")
    assert by_project[zarya.project_uid][ANCHOR].price_status == STATUS_UNMATCHED
    # Zarya lists the window twice: ambiguous there, absent from Alpha's list.
    assert by_project[zarya.project_uid][WINDOW].price_status == STATUS_AMBIGUOUS
    assert by_project[alpha.project_uid][WINDOW].match.reason == "no_position"
    # No price list: rows without any match, never a figure.
    assert bare.price_state == PRICE_STATE_PRICE_LIST_MISSING and bare.price_list is None
    assert {row.price_status for row in by_project[bare.project_uid].values()} == {
        ROW_PRICE_LIST_MISSING
    }
    assert all(row.match is None for row in by_project[bare.project_uid].values())


def test_totals_are_per_project_and_currency_and_there_is_no_section_total(world: World) -> None:
    answer = world.read()
    alpha, zarya, bare = answer.projects
    assert [(t.currency, t.amount, t.row_count) for t in alpha.totals] == [
        ("EUR", Decimal("2550.00"), 1), ("RUB", Decimal("100000"), 1),
    ]
    assert [(t.currency, t.amount, t.row_count) for t in zarya.totals] == [
        ("RUB", Decimal("120000"), 1),
    ]
    assert (bare.totals, dict(bare.status_counts), dict(bare.excluded_by_reason)) == ((), {}, {})
    assert alpha.price_state == zarya.price_state == PRICE_STATE_PRICED
    assert dict(alpha.status_counts) == {STATUS_MATCHED: 2, STATUS_AMBIGUOUS: 0, STATUS_UNMATCHED: 2}
    assert dict(zarya.excluded_by_reason) == {"no_position": 2, "ambiguous": 1}
    assert (alpha.position_count, zarya.position_count) == (2, 3)
    assert not hasattr(answer, "totals")


def test_totals_sum_a_projects_own_sources_only(world: World) -> None:
    alpha = _uid(world, "корпус 1 «Альфа»")
    world.version(alpha, "АР-1 корпус Б", "AR")
    project = next(item for item in world.read().projects if item.project_uid == alpha)
    assert [(t.currency, t.amount, t.row_count) for t in project.totals] == [
        ("EUR", Decimal("5100.00"), 2), ("RUB", Decimal("200000"), 2),
    ]


# -- explicit states --------------------------------------------------------------------------


def test_source_states_are_explicit_and_other_sources_still_read(world: World, monkeypatch) -> None:
    alpha = _uid(world, "корпус 1 «Альфа»")
    world.version(alpha, "АР-1a без анализа", "AR", published=False)
    world.version(alpha, "АР-1b без текста", "AR", text=False)
    big = "\n".join(["Поз. Наименование Кол. Примечание"] + [f"{n} Деталь {n} 5" for n in range(1, 8)])
    world.version(alpha, "АР-1c большой", "AR", pages={1: big})
    monkeypatch.setattr(specification, "MAX_SPECIFICATION_ROWS", 5)
    project = next(item for item in world.read().projects if item.project_uid == alpha)
    states = {source.display_title: source for source in project.sources}
    assert states["АР-1"].state == SOURCE_STATE_READY
    missing = states["АР-1a без анализа"]
    assert (missing.state, missing.run_id, missing.row_count) == (SOURCE_STATE_ANALYSIS_MISSING, None, None)
    unavailable = states["АР-1b без текста"]
    assert unavailable.state == SOURCE_STATE_TEXT_UNAVAILABLE and unavailable.run_id is not None
    assert unavailable.text_layer_sha256 is None
    large = states["АР-1c большой"]
    assert (large.state, large.row_count, large.text_layer_sha256) == (
        SOURCE_STATE_SPECIFICATION_TOO_LARGE, None, LAYER,
    )
    assert project.row_count == 4 and states["АР-1"].row_count == 4
    assert [(t.currency, t.row_count) for t in project.totals] == [("EUR", 1), ("RUB", 1)]


def test_an_empty_section_is_ready_and_empty(world: World) -> None:
    answer = world.read("PB")
    assert (answer.state, answer.projects, answer.source_count, answer.row_count) == (
        SECTION_STATE_READY, (), 0, 0,
    )
    assert answer.rows.items == () and answer.rows.next_offset is None
    assert answer.excluded_count == 1  # the unclassified set might belong here


# -- filters and paging ------------------------------------------------------------------------


def test_the_project_filter_narrows_projects_exclusions_and_rows(world: World) -> None:
    zarya = _uid(world, "Корпус 2 «Заря»")
    whole = world.read()
    answer = world.read(project_uid=zarya)
    assert answer.project_filter == zarya
    assert [project.project_uid for project in answer.projects] == [zarya]
    assert answer.excluded == () and answer.excluded_count == 0
    assert {row.project_uid for row in answer.rows.items} == {zarya}
    assert answer.projects[0] == whole.projects[1]
    loose = _uid(world, "Корпус 4 без раздела")
    narrowed = world.read(project_uid=loose)
    assert (narrowed.projects, narrowed.excluded_count, narrowed.row_count) == ((), 1, 0)
    kj = world.read(project_uid=_uid(world, "Корпус 3 (КЖ)"))
    assert (kj.projects, kj.excluded, kj.row_count) == ((), (), 0)
    _refused(ErrorCode.NOT_FOUND, world.read, project_uid=str(ProjectUid.new()))
    refused = _refused(ErrorCode.VALIDATION_FAILED, world.read, project_uid="prj_bad")
    assert refused.detail_fields["field"] == "project_uid"


def test_the_query_folds_case_yo_and_spaces_and_never_narrows_totals(world: World) -> None:
    whole = world.read()
    answer = world.read(query="  ДВЕРЬ   противопожарная ")
    assert answer.query == "ДВЕРЬ противопожарная"
    assert [row.row.name for row in answer.rows.items] == [DOOR] * 3
    assert len({row.project_uid for row in answer.rows.items}) == 3
    assert (answer.row_count, answer.rows.total) == (12, 3)
    assert answer.projects == whole.projects
    tank = world.read(query="емкость накопительная")
    assert [row.row.name for row in tank.rows.items] == [TANK] * 3
    assert world.read(query="ЁМКОСТЬ").rows.total == 3
    assert world.read(query="hit-hy 200").rows.total == 3
    assert world.read(query="нет такого").rows.total == 0
    assert world.read(query="   ").query is None


def test_rows_are_paged_while_counts_and_totals_cover_every_row(world: World) -> None:
    whole = world.read()
    first = world.read(offset=0, limit=5)
    last = world.read(offset=10, limit=5)
    assert (first.rows.total, len(first.rows.items), first.rows.next_offset) == (12, 5, 5)
    assert (last.rows.total, len(last.rows.items), last.rows.next_offset) == (12, 2, None)
    assert first.projects == last.projects == whole.projects
    assert [row.row.row_id for row in first.rows.items + last.rows.items] == [
        row.row.row_id for row in whole.rows.items[:5] + whole.rows.items[10:]
    ]
    beyond = world.read(offset=50, limit=5)
    assert (beyond.rows.items, beyond.rows.next_offset, beyond.rows.total) == ((), None, 12)


# -- bounds -------------------------------------------------------------------------------------


def test_too_many_projects_is_explicit_and_scans_nothing(world: World, monkeypatch) -> None:
    monkeypatch.setattr(module, "MAX_SCANNED_PROJECTS", 4)
    answer = world.read()
    assert (answer.state, answer.limit_reason) == (SECTION_STATE_TOO_LARGE, LIMIT_PROJECTS)
    assert (answer.projects, answer.excluded, answer.rows) == ((), (), None)
    assert world.documents.listed == [] and world.reader.asked == []
    # One project named: the bound on the scan does not apply.
    narrowed = world.read(project_uid=_uid(world, "Корпус 2 «Заря»"))
    assert narrowed.state == SECTION_STATE_READY and narrowed.rows.total == 4


def test_too_many_sources_serves_the_membership_and_reads_no_text(world: World, monkeypatch) -> None:
    monkeypatch.setattr(module, "MAX_SECTION_SOURCES", 2)
    answer = world.read()
    assert (answer.state, answer.limit_reason, answer.rows) == (SECTION_STATE_TOO_LARGE, LIMIT_SOURCES, None)
    assert answer.source_count == 3 and answer.row_count == 0
    assert [project.project_name for project in answer.projects] == [
        "корпус 1 «Альфа»", "Корпус 2 «Заря»", "Корпус 5 без прайса",
    ]
    for project in answer.projects:
        assert (project.price_state, project.totals, project.price_list) == (PRICE_STATE_NOT_READ, (), None)
        assert {source.state for source in project.sources} == {SOURCE_STATE_NOT_READ}
    assert answer.excluded_count == 1
    assert world.reader.asked == [] and world.prices.asked == []
    narrowed = world.read(project_uid=_uid(world, "Корпус 2 «Заря»"))
    assert narrowed.state == SECTION_STATE_READY and narrowed.rows.total == 4


def test_too_many_rows_serves_the_membership_only(world: World, monkeypatch) -> None:
    monkeypatch.setattr(module, "MAX_SECTION_ROWS", 7)
    answer = world.read()
    assert (answer.state, answer.limit_reason, answer.rows) == (SECTION_STATE_TOO_LARGE, LIMIT_ROWS, None)
    assert answer.row_count == 0
    assert all(project.totals == () and project.price_state == PRICE_STATE_NOT_READ
               for project in answer.projects)
    assert {s.state for p in answer.projects for s in p.sources} == {SOURCE_STATE_NOT_READ}
    assert world.read(project_uid=_uid(world, "Корпус 2 «Заря»")).state == SECTION_STATE_READY


def test_the_exclusion_listing_is_capped_and_its_count_complete(world: World, monkeypatch) -> None:
    loose = _uid(world, "Корпус 4 без раздела")
    for number in range(3):
        world.version(loose, f"Комплект {number}", None)
    monkeypatch.setattr(module, "MAX_LISTED_EXCLUDED", 2)
    answer = world.read()
    assert answer.excluded_count == 4 and len(answer.excluded) == 2
    assert [item.display_title for item in answer.excluded] == ["Комплект 0", "Комплект 1"]


# -- requests, roles, integrity ----------------------------------------------------------------


def test_roles_and_request_values(world: World) -> None:
    denied = _refused(ErrorCode.PERMISSION_DENIED, world.read, actor_roles=frozenset())
    assert denied.detail_fields["required_capability"] == "role:admin|expert"
    assert world.read(actor_roles=frozenset({"admin"})).state == SECTION_STATE_READY
    for field_name, value in (
        ("section_code", "XX"), ("section_code", "ar"), ("section_code", None),
        ("offset", -1), ("offset", True), ("limit", 0), ("limit", 201),
        ("query", 5), ("query", "д" * 201), ("project_uid", 7),
    ):
        refused = _refused(ErrorCode.VALIDATION_FAILED, world.read, **{field_name: value})
        assert refused.detail_fields["field"] == field_name
    assert world.read(query="д" * 200).rows.total == 0


def test_contradictory_answers_are_internal_errors(world: World) -> None:
    alpha = _uid(world, "корпус 1 «Альфа»")
    zarya = _uid(world, "Корпус 2 «Заря»")
    stray = world.documents.current[alpha][0]
    world.documents.current[zarya].append(stray)  # a version of Alpha listed under Zarya
    _refused(ErrorCode.INTERNAL_ERROR, world.read)
    world.documents.current[zarya].pop()

    version = world.documents.current[alpha][0]
    foreign = replace(version.classification, version_uid=VersionUid.new())
    world.documents.current[alpha][0] = replace(version, classification=foreign)
    _refused(ErrorCode.INTERNAL_ERROR, world.read)
    world.documents.current[alpha][0] = version

    stale = replace(world.prices.revisions[alpha][0], is_current=False)
    world.prices.revisions[alpha][0] = stale
    _refused(ErrorCode.INTERNAL_ERROR, world.read)
    world.prices.revisions[alpha][0] = replace(stale, is_current=True)

    run = world.reader.runs[str(version.version_uid)]
    world.reader.runs[str(version.version_uid)] = [RunCandidate("not-a-run", "published")]
    _refused(ErrorCode.INTERNAL_ERROR, world.read)
    world.reader.runs[str(version.version_uid)] = run

    published = run[1].run_id
    good = world.reader.texts[published]
    world.reader.texts[published] = SavedPageText(published, LAYER, {2: FORM7_PAGE})
    _refused(ErrorCode.INTERNAL_ERROR, world.read)
    world.reader.texts[published] = good
    assert world.read().state == SECTION_STATE_READY


def test_the_answer_is_deterministic(world: World) -> None:
    assert world.read() == world.read()


# -- the wire: the read model as the frozen ``SectionSpecification`` --------------------------


def _wire(answer: SectionSpecification) -> Any:
    """The composition root's mapping, validated by the frozen response model."""
    from auditmanager.api.schemas import models
    from auditmanager.bootstrap.adapters import _section_specification_view

    return models.SectionSpecification.model_validate(_section_specification_view(answer))


def test_the_wire_carries_every_row_with_its_address_and_its_own_match(world: World) -> None:
    wire = _wire(world.read())
    alpha, zarya, bare = wire.projects
    assert [p.price_state for p in wire.projects] == ["priced", "priced", "price_list_missing"]
    rows = wire.rows.items
    assert len(rows) == 12
    by_name = {(row.project_uid, row.name): row for row in rows}
    door_alpha = by_name[(alpha.project_uid, DOOR)]
    door_zarya = by_name[(zarya.project_uid, DOOR)]
    assert (door_alpha.price_status, door_alpha.amount, door_alpha.price_position.unit_price) == (
        "matched", "100000", "25000",
    )
    assert (door_zarya.amount, door_zarya.price_position.unit_price) == ("120000", "30000")
    assert door_alpha.row_id != door_zarya.row_id and door_alpha.version_uid != door_zarya.version_uid
    anchor = by_name[(alpha.project_uid, ANCHOR)]
    assert (anchor.amount, anchor.price_position.currency) == ("2550", "EUR")
    assert by_name[(zarya.project_uid, WINDOW)].price_status == "ambiguous"
    assert by_name[(zarya.project_uid, WINDOW)].candidate_count == 2
    unpriced = [row for row in rows if row.project_uid == bare.project_uid]
    assert {row.price_status for row in unpriced} == {"price_list_missing"}
    for row in unpriced:
        assert (row.reason, row.basis, row.price_position, row.amount, row.excluded_reason) == (
            None, None, None, None, None,
        )
        assert (row.candidate_position_ids, row.candidate_count) == ([], 0)


def test_the_wire_keeps_money_as_exact_text_and_totals_per_project(world: World) -> None:
    wire = _wire(world.read())
    alpha, zarya, bare = wire.projects
    assert [(t.currency, t.amount, t.row_count) for t in alpha.matching.totals] == [
        ("EUR", "2550", 1), ("RUB", "100000", 1),
    ]
    assert [(t.currency, t.amount) for t in zarya.matching.totals] == [("RUB", "120000")]
    assert bare.matching is None and bare.price_list is None
    assert dict(zarya.matching.excluded.model_dump()) == {
        "no_position": 2, "unit_mismatch": 0, "row_unit_missing": 0, "ambiguous": 1,
        "quantity_not_numeric": 0,
    }
    assert alpha.matching.counts.model_dump() == {"matched": 2, "ambiguous": 0, "unmatched": 2}
    assert alpha.price_list.position_count == 2 and alpha.price_list.revision_number == 1
    dumped = wire.model_dump(mode="json")
    assert "totals" not in dumped and "total" not in dumped
    assert isinstance(dumped["projects"][0]["matching"]["totals"][0]["amount"], str)


def test_the_wire_writes_every_skip_reason_for_a_read_source_and_none_for_an_unread_one(
    world: World,
) -> None:
    alpha = _uid(world, "корпус 1 «Альфа»")
    world.version(alpha, "АР-1a без анализа", "AR", published=False)
    wire = _wire(world.read())
    project = next(item for item in wire.projects if item.project_uid == alpha)
    read, missing = project.sources
    assert read.state == "ready" and set(read.skipped_by_reason.model_dump()) == set(
        specification.SKIP_REASONS
    )
    assert (missing.state, missing.skipped_by_reason, missing.row_count, missing.run_id) == (
        "analysis_missing", None, None, None,
    )


def test_the_wire_of_a_bound_lists_the_membership_and_no_rows(world: World, monkeypatch) -> None:
    monkeypatch.setattr(module, "MAX_SECTION_SOURCES", 2)
    wire = _wire(world.read())
    assert (wire.state, wire.limit_reason, wire.rows, wire.row_count) == ("section_too_large", "sources", None, 0)
    assert [p.price_state for p in wire.projects] == ["not_read"] * 3
    assert all(p.matching is None and p.price_list is None for p in wire.projects)
    assert {s.state for p in wire.projects for s in p.sources} == {"not_read"}


def test_the_wire_vocabularies_are_the_read_models(world: World) -> None:
    from typing import get_args

    from auditmanager.api.schemas import models

    fields = models.SectionSpecification.model_fields
    assert set(get_args(fields["state"].annotation)) == set(module.SECTION_STATES)
    (limit_literal,) = [arg for arg in get_args(fields["limit_reason"].annotation) if arg is not type(None)]
    assert set(get_args(limit_literal)) == set(module.LIMIT_REASONS)
    project = models.SectionSpecificationProject.model_fields["price_state"].annotation
    assert set(get_args(project)) == set(module.PRICE_STATES)
    source = models.SectionSpecificationSource.model_fields["state"].annotation
    assert set(get_args(source)) == set(module.SOURCE_STATES)
    row = models.SectionSpecificationRow.model_fields["price_status"].annotation
    assert set(get_args(row)) == {*STATUSES_MATCHED, module.ROW_PRICE_LIST_MISSING}
    excluded = models.SectionSpecificationExcludedVersion.model_fields["reason"].annotation
    assert set(get_args(excluded)) == {module.EXCLUSION_VERSION_UNCLASSIFIED}
