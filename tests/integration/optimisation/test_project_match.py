"""`W60-OPT-MATCH-01` phase A: «Спецификация и цены» on real PostgreSQL and MinIO.

The project, the document set, its version and Blob, the expert's classification and the
price-list revisions are real rows written through their owning boundaries (``storage``,
``documents``, ``sections``, ``optimisation``). The runs and the saved text layer come through
the query's own port, as the composition root will supply them (the comparison's pattern);
the fake records what it was asked, so each state proves how far the query went.

Each precondition is an explicit state with the facts read so far; a total never contains an
unmatched, ambiguous, unit-mismatched or quantity-less row; nothing is written.
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
from auditmanager.optimisation import specification
from auditmanager.optimisation.project_match import (
    STATE_ANALYSIS_MISSING,
    STATE_PRICE_LIST_MISSING,
    STATE_READY,
    STATE_SECTION_NOT_AR,
    STATE_SPECIFICATION_TOO_LARGE,
    STATE_TEXT_UNAVAILABLE,
    STATE_VERSION_UNCLASSIFIED,
    RunCandidate,
    SavedPageText,
    SpecificationPrices,
    read_specification_prices,
)
from auditmanager.optimisation.public import PriceListUploads
from auditmanager.sections.public import classify_document_version
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, ProjectUid
from auditmanager.storage import S3BlobStore, sha256_of
from auditmanager.storage.blob_repository import BlobMetadataRepository
from auditmanager.storage.models import VerifiedBlob, parse_blob_role

accounts = AccountRepository()
documents = DocumentRepository()

RUN_OLD = "run_01M2545JSD15ETSNNV904XA001"
RUN_PUBLISHED = "run_01M2545JSD15ETSNNV904XA002"
RUN_FAILED = "run_01M2545JSD15ETSNNV904XA003"
LAYER_SHA256 = "e" * 64

#: Page 1: the real AR set's metal-products schedule (verbatim lines, sheet 10).
SCHEDULE_PAGE = (
    "Ведомость металлических изделий\n"
    "Поз. Наименование Кол-во, шт. Примечание\n"
    "1 Металлический щит МЩ-1 12\n"
    "План наотм. +0,400 2 Металлический щит МЩ-2 12\n"
    "3 Рифленая сталь 690х395 t=4 мм 7\n"
    "1. СпецификациюэлементовметаллическихщитовМЩ-1 иМЩ-2 см. л. 17 и18\n"
    "Изм. Кол.уч. Лист №док. Подпись Дата\n"
    "Стадия Лист Листов\n"
    "10\n"
)
#: Page 2: a Form-7 specification with a split header.
FORM7_PAGE = (
    "Поз. Наименование и техническая характеристика Тип, марка Код Завод- Ед. Кол. Масса Примечание\n"
    "изготовитель изм. 1 ед., кг\n"
    "1 Дверь противопожарная ДПМ-01/60 EI60 ООО «Промет» шт. 4 45,5\n"
    "2 Окно ПВХ двухкамерное ОП В2 1460х1460 шт 12\n"
    "3 Анкер химический HIT-HY 200 шт 200\n"
    "4 Профиль направляющий ПН 50х40 п. м 120\n"
    "5 Пена монтажная шт 3\n"
    "6 Монтажная лента компл. - по месту\n"
)
PAGES = {1: SCHEDULE_PAGE, 2: FORM7_PAGE}

PRICE_LIST = (
    "Код;Наименование;Марка;Ед. изм.;Цена;Валюта\n"
    ";Мет. щит МЩ-1;;шт.;15000;RUB\n"
    ";Рифлёная сталь 690x395 t=4 мм;;кг;120;RUB\n"
    ";Дверь противопожарная;ДПМ-01/60;шт;25000;RUB\n"
    ";Окно ПВХ двухкамерное ОП В2 1460х1460;;шт;18500,5;RUB\n"
    ";Анкер химический;HIT-HY 200;шт;12,75;EUR\n"
    ";Профиль направляющий ПН 50х40;;м;95;RUB\n"
    ";Пена монтажная;;шт;700;RUB\n"
    ";Пена монтажная;;шт;710;RUB\n"
    ";Монтажная лента;;компл;450;RUB\n"
).encode("utf-8")
OLDER_PRICE_LIST = "Наименование;Ед. изм.;Цена;Валюта\nМет. щит МЩ-1;шт;99999;RUB\n".encode()


class _Reader:
    """The runs-and-text port, answering from memory and recording every question."""

    def __init__(
        self,
        runs: Sequence[RunCandidate] = (),
        texts: Mapping[str, SavedPageText | None] | None = None,
    ) -> None:
        self.runs = tuple(runs)
        self.texts = dict(texts or {})
        self.asked_runs: list[str] = []
        self.asked_texts: list[tuple[str, str, int]] = []

    def runs_newest_first(self, session: Session, *, version_uid: str) -> Sequence[RunCandidate]:
        self.asked_runs.append(version_uid)
        return self.runs

    def saved_page_text(
        self, session: Session, *, run_id: str, version_uid: str, page_count: int
    ) -> SavedPageText | None:
        self.asked_texts.append((run_id, version_uid, page_count))
        return self.texts.get(run_id)


def _published_reader(pages: Mapping[int, str] = PAGES) -> _Reader:
    return _Reader(
        runs=(
            RunCandidate(RUN_FAILED, "failed"),
            RunCandidate(RUN_PUBLISHED, "published"),
            RunCandidate(RUN_OLD, "published"),
        ),
        texts={
            RUN_PUBLISHED: SavedPageText(RUN_PUBLISHED, LAYER_SHA256, dict(pages)),
            RUN_OLD: SavedPageText(RUN_OLD, "f" * 64, {1: "", 2: ""}),
        },
    )


def _publish_version(session: Session, store: S3BlobStore, project_uid: str, title: str) -> tuple[str, str]:
    payload = f"%PDF-1.7 synthetic {title}".encode()
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
            upload_token=f"seeded-{title}",
            sha256=published.sha256,
            size=published.size,
            role=published.role,
            media_type=published.media_type,
        ),
    )
    blobs.mark_available(session, published.blob_id)
    document_uid = documents.create_document(
        session, project_uid=ProjectUid.parse(project_uid), display_title=title
    )
    version_uid = documents.publish_version(
        session,
        document_uid=document_uid,
        media_type="application/pdf",
        byte_size=len(payload),
        sha256=digest,
        page_count=len(PAGES),
        source_filename=None,
        entries=(
            ManifestEntry(
                role="source_document",
                blob_id=published.blob_id,
                sha256=published.sha256,
                size_bytes=published.size,
                media_type=published.media_type,
            ),
        ),
    )
    return str(document_uid), str(version_uid)


@pytest.fixture
def world(session: Session, store: S3BlobStore, cast: Any) -> dict[str, str]:
    document, version = _publish_version(session, store, cast.project, "13АВ-РД-АР-ТП1")
    foreign_document, _ = _publish_version(session, store, cast.other_project, "Чужой АР")
    session.commit()
    return {"document": document, "version": version, "foreign_document": foreign_document}


def _classify(session: Session, cast: Any, world: Mapping[str, str], section: str) -> None:
    classify_document_version(
        session,
        project_uid=cast.project,
        document_uid=world["document"],
        version_uid=world["version"],
        project_stage="R",
        section_code=section,
        actor_uid=cast.expert,
        actor_roles=accounts.roles_of(session, cast.expert),
    )
    session.commit()


def _upload(store: S3BlobStore, factory: sessionmaker[Session], cast: Any, content: bytes, key: str):
    return PriceListUploads(store, session_factory=factory).upload(
        project_uid=cast.project,
        content=content,
        source_filename=f"{key}.csv",
        idempotency_key=key,
        actor_uid=cast.expert,
    )


def _read(session: Session, cast: Any, world: Mapping[str, str], reader: _Reader, **extra: Any) -> SpecificationPrices:
    arguments: dict[str, Any] = {
        "project_uid": cast.project,
        "document_uid": world["document"],
        "actor_roles": frozenset({"expert"}),
        "reader": reader,
    }
    arguments.update(extra)
    return read_specification_prices(session, **arguments)


def _refused(code: ErrorCode, call: Any, *args: Any, **kwargs: Any) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call(*args, **kwargs)
    assert caught.value.code is code, (caught.value.code, dict(caught.value.detail_fields))
    return caught.value


# -- explicit states, in the order they are checked ----------------------------------------


def test_an_unclassified_version_is_an_explicit_state_and_reads_nothing_further(
    session: Session, cast, world
) -> None:
    reader = _published_reader()
    result = _read(session, cast, world, reader)
    assert result.state == STATE_VERSION_UNCLASSIFIED
    assert (result.version_uid, result.page_count, result.version_ordinal) == (world["version"], 2, 1)
    assert (result.section_code, result.price_list, result.rows, result.totals) == (None, None, None, ())
    assert reader.asked_runs == [] and reader.asked_texts == []


def test_a_version_classified_in_another_section_goes_on_to_the_price_list(session: Session, cast, world) -> None:
    """Was ``section_not_ar``: the section is reported and no longer stops the read."""
    _classify(session, cast, world, "KJ")
    reader = _published_reader()
    result = _read(session, cast, world, reader)
    assert (result.state, result.project_stage, result.section_code) == (STATE_PRICE_LIST_MISSING, "R", "KJ")
    assert result.state != STATE_SECTION_NOT_AR
    assert result.rows is None and result.price_list is None and reader.asked_runs == []


def test_an_ar_version_without_a_price_list_says_so(session: Session, cast, world) -> None:
    _classify(session, cast, world, "AR")
    reader = _published_reader()
    result = _read(session, cast, world, reader)
    assert (result.state, result.section_code, result.price_list) == (STATE_PRICE_LIST_MISSING, "AR", None)
    assert reader.asked_runs == []


@pytest.mark.parametrize("section", ["PB", "OV", "KJ"])
def test_a_version_of_another_section_is_priced_exactly_like_an_ar_one_of_the_same_text(
    session: Session, store, factory, cast, world, section: str
) -> None:
    """The fake reader's Form-7 pages are the АР tests' own: a real run of this section is not measured."""
    _classify(session, cast, world, section)
    second_document, second_version = _publish_version(session, store, cast.project, "АР-2")
    session.commit()
    ar = {"document": second_document, "version": second_version}
    _classify(session, cast, ar, "AR")
    _upload(store, factory, cast, PRICE_LIST, "prices-1")

    other = _read(session, cast, world, _published_reader(), limit=200)
    reference = _read(session, cast, ar, _published_reader(), limit=200, document_uid=second_document)

    assert (other.state, other.section_code) == (STATE_READY, section)
    assert (reference.state, reference.section_code) == (STATE_READY, "AR")
    assert other.rows is not None and reference.rows is not None
    assert len(other.rows.items) == 8  # not vacuous: the whole specification was read

    def shape(result: SpecificationPrices) -> list[Any]:
        assert result.rows is not None
        return [
            (m.row.page_number, m.row.position, m.row.name, m.row.quantity, m.status, m.basis,
             m.reason, m.excluded_reason, m.amount)
            for m in result.rows.items
        ]

    assert shape(other) == shape(reference)
    assert [(t.currency, t.amount, t.row_count) for t in other.totals] == [
        (t.currency, t.amount, t.row_count) for t in reference.totals
    ]
    assert other.totals and dict(other.matching.excluded_by_reason) == dict(reference.matching.excluded_by_reason)


def test_no_published_run_is_analysis_missing_with_the_price_list_named(
    session: Session, store, factory, cast, world
) -> None:
    _classify(session, cast, world, "AR")
    uploaded = _upload(store, factory, cast, PRICE_LIST, "prices-1")
    reader = _Reader(runs=(RunCandidate(RUN_FAILED, "failed"),))
    result = _read(session, cast, world, reader)
    assert result.state == STATE_ANALYSIS_MISSING
    assert result.price_list is not None
    assert (result.price_list.price_list_id, result.position_count) == (uploaded.revision.price_list_id, 9)
    assert (result.run_id, reader.asked_texts) == (None, [])


def test_a_published_run_without_saved_text_is_text_unavailable(
    session: Session, store, factory, cast, world
) -> None:
    _classify(session, cast, world, "AR")
    _upload(store, factory, cast, PRICE_LIST, "prices-1")
    reader = _Reader(runs=(RunCandidate(RUN_PUBLISHED, "published"),), texts={RUN_PUBLISHED: None})
    result = _read(session, cast, world, reader)
    assert (result.state, result.run_id, result.text_layer_sha256) == (
        STATE_TEXT_UNAVAILABLE, RUN_PUBLISHED, None,
    )
    assert reader.asked_texts == [(RUN_PUBLISHED, world["version"], 2)]


# -- the priced specification ----------------------------------------------------------------


def test_the_current_ar_version_is_priced_from_the_current_price_list(
    session: Session, store, factory, cast, world
) -> None:
    _classify(session, cast, world, "AR")
    _upload(store, factory, cast, OLDER_PRICE_LIST, "prices-0")
    current = _upload(store, factory, cast, PRICE_LIST, "prices-1")
    reader = _published_reader()
    result = _read(session, cast, world, reader, limit=200)

    assert result.state == STATE_READY
    assert result.price_list is not None and result.price_list.price_list_id == current.revision.price_list_id
    assert result.price_list.revision_number == 2
    # The newest *published* run: the failed one above it is passed over, the older not read.
    assert (result.run_id, result.text_layer_sha256) == (RUN_PUBLISHED, LAYER_SHA256)
    assert [question[0] for question in reader.asked_texts] == [RUN_PUBLISHED]

    assert result.extraction is not None and result.matching is not None and result.rows is not None
    assert result.extraction.table_count == 2
    by_name = {match.row.name: match for match in result.rows.items}
    assert [(m.row.page_number, m.row.position) for m in result.rows.items] == [
        (1, "1"), (1, "3"), (2, "1"), (2, "2"), (2, "3"), (2, "4"), (2, "5"), (2, "6"),
    ]
    shield = by_name["Металлический щит МЩ-1"]
    assert (shield.status, shield.basis, shield.amount) == ("matched", "name", Decimal("180000"))
    assert shield.row.sheet_label == "10"
    assert by_name["Рифленая сталь 690х395 t=4 мм"].reason == "unit_mismatch"
    door = by_name["Дверь противопожарная ДПМ-01/60 EI60 ООО «Промет»"]
    assert (door.basis, door.amount) == ("mark", Decimal("100000"))
    anchor = by_name["Анкер химический HIT-HY 200"]
    assert (anchor.basis, anchor.position.currency, anchor.amount) == ("mark", "EUR", Decimal("2550.00"))
    assert by_name["Профиль направляющий ПН 50х40"].reason == "unit_mismatch"
    assert by_name["Пена монтажная"].status == "ambiguous"
    tape = by_name["Монтажная лента"]
    assert (tape.status, tape.amount, tape.excluded_reason) == ("matched", None, "quantity_not_numeric")

    totals = [(t.currency, t.amount, t.row_count) for t in result.totals]
    assert totals == [
        ("EUR", Decimal("2550.00"), 1),
        ("RUB", Decimal("180000") + Decimal("100000") + Decimal("222006.0"), 3),
    ]
    assert dict(result.matching.excluded_by_reason) == {
        "unit_mismatch": 2, "ambiguous": 1, "quantity_not_numeric": 1,
    }
    assert dict(result.extraction.skipped_by_reason) == {"position_missing": 1}


def test_rows_are_paged_while_counts_and_totals_cover_every_row(
    session: Session, store, factory, cast, world
) -> None:
    _classify(session, cast, world, "AR")
    _upload(store, factory, cast, PRICE_LIST, "prices-1")
    whole = _read(session, cast, world, _published_reader(), limit=200)
    first = _read(session, cast, world, _published_reader(), offset=0, limit=3)
    last = _read(session, cast, world, _published_reader(), offset=6, limit=3)
    assert first.rows is not None and last.rows is not None and whole.rows is not None
    assert (first.rows.total, len(first.rows.items), first.rows.next_offset) == (8, 3, 3)
    assert (last.rows.total, len(last.rows.items), last.rows.next_offset) == (8, 2, None)
    assert first.totals == last.totals == whole.totals
    assert [m.row.row_id for m in first.rows.items + last.rows.items] == [
        m.row.row_id for m in whole.rows.items[:3] + whole.rows.items[6:]
    ]


def test_a_specification_over_the_bound_is_too_large_not_cut(
    session: Session, store, factory, cast, world, monkeypatch
) -> None:
    _classify(session, cast, world, "AR")
    _upload(store, factory, cast, PRICE_LIST, "prices-1")
    monkeypatch.setattr(specification, "MAX_SPECIFICATION_ROWS", 4)
    result = _read(session, cast, world, _published_reader())
    assert result.state == STATE_SPECIFICATION_TOO_LARGE
    assert (result.matching, result.rows, result.totals) == (None, None, ())
    assert result.extraction is not None and result.extraction.over_limit


def test_the_read_writes_nothing(session: Session, store, factory, cast, world) -> None:
    _classify(session, cast, world, "AR")
    _upload(store, factory, cast, PRICE_LIST, "prices-1")
    tables = ("price_list_revision", "price_list_position", "command_record", "blob",
              "document_version", "document_version_classification")

    def counts() -> dict[str, int]:
        session.rollback()
        return {name: int(session.execute(text(f"SELECT count(*) FROM {name}")).scalar_one())
                for name in tables}

    before = counts()
    _read(session, cast, world, _published_reader())
    assert not session.new and not session.dirty and not session.deleted
    assert counts() == before


# -- scope, roles, requests, port integrity -------------------------------------------------


def test_scope_roles_and_request_values(session: Session, cast, world) -> None:
    reader = _published_reader()
    _refused(ErrorCode.NOT_FOUND, _read, session, cast, world, reader,
             document_uid=world["foreign_document"])
    _refused(ErrorCode.NOT_FOUND, _read, session, cast, world, reader,
             project_uid=str(ProjectUid.new()))
    _refused(ErrorCode.NOT_FOUND, _read, session, cast, world, reader,
             document_uid=str(DocumentUid.new()))
    denied = _refused(ErrorCode.PERMISSION_DENIED, _read, session, cast, world, reader,
                      actor_roles=frozenset())
    assert denied.detail_fields["required_capability"] == "role:admin|expert"
    assert _read(session, cast, world, reader, actor_roles=frozenset({"admin"})).state == (
        STATE_VERSION_UNCLASSIFIED
    )
    for field, value in (("project_uid", "prj_bad"), ("document_uid", "nonsense")):
        refused = _refused(ErrorCode.VALIDATION_FAILED, _read, session, cast, world, reader,
                           **{field: value})
        assert refused.detail_fields["field"] == field
    for field, value in (("offset", -1), ("limit", 0), ("limit", 201)):
        refused = _refused(ErrorCode.VALIDATION_FAILED, _read, session, cast, world, reader,
                           **{field: value})
        assert refused.detail_fields["field"] == field


def test_port_answers_that_contradict_their_constraints_are_internal_errors(
    session: Session, store, factory, cast, world
) -> None:
    _classify(session, cast, world, "AR")
    _upload(store, factory, cast, PRICE_LIST, "prices-1")
    malformed_run = _Reader(runs=(RunCandidate("not-a-run", "published"),))
    _refused(ErrorCode.INTERNAL_ERROR, _read, session, cast, world, malformed_run)
    missing_page = _Reader(
        runs=(RunCandidate(RUN_PUBLISHED, "published"),),
        texts={RUN_PUBLISHED: SavedPageText(RUN_PUBLISHED, LAYER_SHA256, {1: SCHEDULE_PAGE})},
    )
    _refused(ErrorCode.INTERNAL_ERROR, _read, session, cast, world, missing_page)
    other_run = _Reader(
        runs=(RunCandidate(RUN_PUBLISHED, "published"),),
        texts={RUN_PUBLISHED: SavedPageText(RUN_OLD, LAYER_SHA256, dict(PAGES))},
    )
    _refused(ErrorCode.INTERNAL_ERROR, _read, session, cast, world, other_run)
