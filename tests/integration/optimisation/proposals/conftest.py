"""Fixtures for the proposals suite: real PostgreSQL and MinIO, the parent suite's cast.

The project, the document set, its version and Blob, the expert's classification, the
price-list revision and the vendor lists are real rows written through their owning
boundaries (``storage``, ``documents``, ``sections``, ``optimisation``). The published run is
one ``audit_run`` row inserted directly -- the runs context has no seeding boundary and the
pass only needs the row to exist for its foreign key -- and its state and saved text come
through the specification read's own port, as the composition root will supply them.

Each command runs in its own unit of work (``session_scope``), as the composition root runs
it: committed on success, rolled back on any refusal.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.public import AccountRepository
from auditmanager.documents.public import DocumentRepository, ManifestEntry
from auditmanager.optimisation.project_match import RunCandidate, SavedPageText
from auditmanager.optimisation.public import (
    PriceListUploads,
    set_global_vendor_list,
    set_project_vendor_list,
)
from auditmanager.sections.public import classify_document_version
from auditmanager.shared.db.session import session_scope
from auditmanager.shared.identity import AnalysisProfileId, ProjectUid, PromptBundleId, RunId
from auditmanager.storage import S3BlobStore, sha256_of
from auditmanager.storage.blob_repository import BlobMetadataRepository
from auditmanager.storage.models import VerifiedBlob, parse_blob_role

accounts = AccountRepository()
documents = DocumentRepository()

LAYER_SHA256 = "e" * 64

#: One Form-7 specification page (the matcher's own fixture, `W60-OPT-MATCH-01`).
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
PAGES = {1: FORM7_PAGE}

#: The vendor whose name a spreadsheet would read as a formula, on the list and in the prices.
HOSTILE_VENDOR = '=HYPERLINK("http://example.invalid")'

PRICE_LIST = (
    "Код;Наименование;Марка;Ед. изм.;Цена;Валюта;Поставщик\n"
    ";Дверь противопожарная;ДПМ-01/60;шт;25000;RUB;ООО «Промет»\n"
    ";Дверь противопожарная;ДПМ-02/60;шт;21000;RUB;Кнауф Гипс\n"
    ";Дверь противопожарная металлическая;;шт;19500;RUB;Неизвестный завод\n"
    ";Окно ПВХ двухкамерное ОП В2 1460х1460;;шт;18500,5;RUB;Промет\n"
    ";Окно ПВХ двухкамерное ОП В2 1460х1460 эконом;;шт;16000;RUB;Кнауф Гипс\n"
    ";Окно ПВХ двухкамерное ОП В2 1460х1460 евро;;шт;15000;EUR;Кнауф Гипс\n"
    ";Анкер химический;HIT-HY 200;шт;12,75;EUR;Промет\n"
    f";Анкер химический;HIT-HY 170;шт;9,5;EUR;\"{HOSTILE_VENDOR.replace(chr(34), chr(34) * 2)}\"\n"
    ";Профиль направляющий ПН 50х40;;м;95;RUB;Промет\n"
    ";Профиль направляющий ПН 50х40 эконом;;м;60;RUB;Кнауф Гипс\n"
    ";Пена монтажная;;шт;700;RUB;Промет\n"
    ";Пена монтажная;;шт;710;RUB;Промет\n"
    ";Пена монтажная бытовая;;шт;300;RUB;Кнауф Гипс\n"
    ";Монтажная лента;;компл;450;RUB;Промет\n"
    ";Монтажная лента армированная;;компл;300;RUB;Кнауф Гипс\n"
).encode("utf-8")
#: A later revision in which the door analog is cheaper still.
NEWER_PRICE_LIST = PRICE_LIST.replace(b";21000;", b";20000;")

GLOBAL_VENDORS = ({"vendor": "Кнауф Гипс"}, {"vendor": HOSTILE_VENDOR}, {"vendor": "Промет"})


class Reader:
    """The runs-and-text port, answering from memory and recording every question."""

    def __init__(
        self,
        runs: Sequence[RunCandidate] = (),
        texts: Mapping[str, SavedPageText | None] | None = None,
        *,
        by_version: Mapping[str, Sequence[RunCandidate]] | None = None,
    ) -> None:
        self.runs = tuple(runs)
        self.by_version = {key: tuple(value) for key, value in (by_version or {}).items()}
        self.texts = dict(texts or {})
        self.asked_texts: list[str] = []

    def runs_newest_first(self, session: Session, *, version_uid: str) -> Sequence[RunCandidate]:
        return self.by_version.get(version_uid, self.runs)

    def saved_page_text(
        self, session: Session, *, run_id: str, version_uid: str, page_count: int
    ) -> SavedPageText | None:
        self.asked_texts.append(run_id)
        return self.texts.get(run_id)


@dataclass(frozen=True, slots=True)
class World:
    project: str
    document: str
    version: str
    run: str
    foreign_document: str
    other_document: str
    other_version: str
    other_run: str


def _publish_version(
    session: Session, store: S3BlobStore, project_uid: str, title: str
) -> tuple[str, str]:
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


def _run_row(session: Session, project_uid: str, version_uid: str) -> str:
    run_id = str(RunId.new())
    session.execute(
        text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, "
            "prompt_bundle_id, provider_mode, frozen_input_digest) "
            "VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :s)"
        ),
        {
            "r": run_id,
            "p": project_uid,
            "v": version_uid,
            "ap": str(AnalysisProfileId.new()),
            "pb": str(PromptBundleId.new()),
            "s": hashlib.sha256(run_id.encode()).hexdigest(),
        },
    )
    return run_id


@pytest.fixture
def world(session: Session, store: S3BlobStore, cast: Any) -> World:
    document, version = _publish_version(session, store, cast.project, "13АВ-РД-АР-ТП1")
    other_document, other_version = _publish_version(session, store, cast.project, "АР-2")
    foreign_document, _ = _publish_version(session, store, cast.other_project, "Чужой АР")
    built = World(
        project=cast.project,
        document=document,
        version=version,
        run=_run_row(session, cast.project, version),
        foreign_document=foreign_document,
        other_document=other_document,
        other_version=other_version,
        other_run=_run_row(session, cast.project, other_version),
    )
    session.commit()
    return built


def published_reader(world: World, *, pages: Mapping[int, str] = PAGES) -> Reader:
    return Reader(
        by_version={
            world.version: (RunCandidate(world.run, "published"),),
            world.other_version: (RunCandidate(world.other_run, "published"),),
        },
        texts={
            world.run: SavedPageText(world.run, LAYER_SHA256, dict(pages)),
            world.other_run: SavedPageText(world.other_run, LAYER_SHA256, dict(pages)),
        },
    )


@pytest.fixture
def unit(factory: sessionmaker[Session]) -> Callable[..., Any]:
    """Run one callable in its own unit of work: commit on success, roll back on refusal."""

    def run(call: Callable[..., Any], /, **arguments: Any) -> Any:
        with session_scope(factory) as session:
            if "actor_uid" in arguments and "actor_roles" not in arguments:
                arguments["actor_roles"] = accounts.roles_of(session, arguments["actor_uid"])
            return call(session, **arguments)

    return run


def classify(unit: Callable[..., Any], cast: Any, world: World, section: str = "AR",
             *, document: str | None = None, version: str | None = None) -> None:
    unit(
        classify_document_version,
        project_uid=world.project,
        document_uid=document or world.document,
        version_uid=version or world.version,
        project_stage="R",
        section_code=section,
        actor_uid=cast.expert,
    )


def upload(store: S3BlobStore, factory: sessionmaker[Session], cast: Any, content: bytes, key: str):
    return PriceListUploads(store, session_factory=factory).upload(
        project_uid=cast.project,
        content=content,
        source_filename=f"{key}.csv",
        idempotency_key=key,
        actor_uid=cast.expert,
    )


def global_vendors(unit: Callable[..., Any], cast: Any, entries=GLOBAL_VENDORS, section: str = "AR"):
    return unit(
        set_global_vendor_list, section_code=section, entries=list(entries), actor_uid=cast.admin
    ).revision


def project_vendors(unit: Callable[..., Any], cast: Any, mode: str, entries=()):
    return unit(
        set_project_vendor_list,
        project_uid=cast.project,
        section_code="AR",
        mode=mode,
        entries=list(entries),
        actor_uid=cast.expert,
    ).revision


@pytest.fixture
def ready(unit, store, factory, cast, world) -> Iterator[World]:
    """An AR-classified version, a price list and a global AR vendor list."""
    classify(unit, cast, world)
    upload(store, factory, cast, PRICE_LIST, "prices-1")
    global_vendors(unit, cast)
    yield world
