"""PostgreSQL fixtures and a laboratory of synthetic document sets for the overview tests (`CMP-VC-OVERVIEW-01`).

The overview reads rows; the tests write the rows a set in each state leaves (versions, page profiles, a matrix build, edits
through the matrix service, a series with its transitions, queue items, upload batches) **through the lanes' own
repositories where one exists** and by plain ``INSERT`` for the rest, so the states are the ones the real code writes. The
tests commit (the service opens its own sessions) and ``document_version`` refuses DELETE by trigger, so every test works in
projects of its own with fresh identities and the shared database is never cleaned.

The oracle of the overview is what ``ComparisonMatrixService.get_matrix`` and ``ComparisonSeriesService.list_series``
answer for the same set: those two read one set each (and are N+1 over a project), the overview reads the project at once,
and the two must agree.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.matrix import settings as matrix_settings
from auditmanager.comparison.matrix.inputs import profile_digest
from auditmanager.comparison.matrix.repository import MatrixRepository
from auditmanager.comparison.overview.repository import OverviewRepository
from auditmanager.comparison.profile.limits import ALGO_VERSION as PAGE_PROFILE_ALGO
from auditmanager.comparison.series.inputs import SeriesInputs, input_digest
from auditmanager.comparison.series.repository import SeriesRepository
from auditmanager.comparison.engine.limits import ALGO_VERSION as ENGINE_ALGO
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.shared.db import session_scope
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.session import create_session_factory
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid, new_ulid

ROOT = Path(__file__).resolve().parents[4]
SECRET = "comparison-overview-suite"
_NAMES = ("DATABASE_URL", "S3_ENDPOINT_URL", "S3_API_PORT", "S3_REGION", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_BUCKET")
#: Every table the overview reads, and the ones that a read must never change: the rows are counted before and after a call.
COUNTED_TABLES = (
    "project", "document", "document_version", "command_record", "audit_event",
    "comparison_upload", "comparison_upload_set", "comparison_upload_file", "comparison_upload_part",
    "comparison_version_order", "comparison_page_profile", "comparison_work", "comparison_work_attempt",
    "comparison_matrix", "comparison_matrix_edit", "comparison_ai_link",
    "comparison_series", "comparison_transition", "comparison_sheet_pair", "comparison_sheet_pair_result",
    "comparison_model_call",
)


def _load_dotenv() -> None:
    dotenv = ROOT / ".env"
    if not dotenv.is_file():
        return
    for raw in dotenv.read_text(encoding="utf-8").splitlines():
        name, separator, value = raw.strip().partition("=")
        if separator and name in _NAMES and not os.environ.get(name):
            os.environ[name] = value.strip().strip("\"'")


@pytest.fixture(scope="session")
def engine() -> Engine:
    _load_dotenv()
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail("DATABASE_URL is not set: run `make up` and `make migrate` for this lane. These tests never skip.")
    built = create_database_engine(DatabaseSettings(url=parse_database_url(raw)))
    with built.connect() as connection:
        for table in COUNTED_TABLES:
            if connection.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}).scalar_one_or_none() is None:
                pytest.fail(f"the database has no {table} table: run `make migrate` (head 0039)")
    yield built
    built.dispose()


@pytest.fixture(scope="session")
def sessions(engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(engine)


@dataclass(frozen=True, slots=True)
class Doc:
    project_uid: str
    document_uid: str
    versions: tuple[str, ...]  # oldest first (the document's own order)
    page_counts: dict[str, int]
    pages: dict[str, tuple[str, ...]] = field(default_factory=dict)  # version -> profile ids, page 1.. (when profiled)


def _hash(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def ulid_id(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


class Lab:
    """The committed writes the tests make beside the code under test."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self.sessions = sessions

    # -- project, document, versions, profiles -----------------------------------------------------------------

    def project(self, name: str = "Обзор") -> str:
        project = str(ProjectUid.new())
        with session_scope(self.sessions) as session:
            session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, :n)"), {"p": project, "n": name})
        return project

    def document(
        self, project: str, *, pages: tuple[int, ...] = (2, 2, 2), title: str = "Комплект", profiles: str = "all",
        failed: int = 0, published_at: datetime | None = None,
    ) -> Doc:
        """A document with ``len(pages)`` versions. ``profiles``: ``all`` (every page ready), ``none``, ``some`` (the first
        page of each version), and ``failed`` pages (from the end) stored as ``needs_review``."""
        document = str(DocumentUid.new())
        versions: list[str] = []
        profile_ids: dict[str, list[str]] = {}
        with session_scope(self.sessions) as session:
            session.execute(
                text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, :t)"),
                {"d": document, "p": project, "t": title},
            )
            for ordinal, count in enumerate(pages, start=1):
                version = str(VersionUid.new())
                versions.append(version)
                session.execute(
                    text(
                        "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, "
                        "sha256, page_count, published_at) VALUES (:v, :d, :o, 'application/pdf', 1, :h, :c, "
                        "coalesce(:at, now()))"
                    ),
                    {"v": version, "d": document, "o": ordinal, "h": _hash(version), "c": count, "at": published_at},
                )
                profile_ids[version] = []
                for number in range(1, count + 1):
                    if profiles == "none" or (profiles == "some" and number > 1):
                        continue
                    bad = number > count - failed
                    profile_id = ulid_id("cpr")
                    session.execute(
                        text(
                            "INSERT INTO comparison_page_profile (comparison_page_profile_id, version_uid, page_number, "
                            "content_key, algo_version, status, reason, profile) VALUES (:i, :v, :n, :k, :a, :s, :r, "
                            "'{}'::jsonb)"
                        ),
                        {
                            "i": profile_id, "v": version, "n": number, "k": _hash(version, str(number)), "a": PAGE_PROFILE_ALGO,
                            "s": "needs_review" if bad else "ready", "r": "RENDER_FAILED" if bad else None,
                        },
                    )
                    profile_ids[version].append(profile_id)
        return Doc(project, document, tuple(versions), dict(zip(versions, pages, strict=True)),
                   {v: tuple(ids) for v, ids in profile_ids.items()})

    def profile_page(self, doc: Doc, version: str, number: int) -> None:
        """A page profile stored after the others (a build made before it no longer matches the profiles)."""
        with session_scope(self.sessions) as session:
            session.execute(
                text(
                    "INSERT INTO comparison_page_profile (comparison_page_profile_id, version_uid, page_number, content_key, "
                    "algo_version, status, reason, profile) VALUES (:i, :v, :n, :k, :a, 'ready', NULL, '{}'::jsonb)"
                ),
                {"i": ulid_id("cpr"), "v": version, "n": number, "k": _hash(version, str(number)), "a": PAGE_PROFILE_ALGO},
            )

    def add_version(self, doc: Doc, *, pages: int = 2) -> str:
        """A version published after everything else (a later ``version_ordinal``)."""
        version = str(VersionUid.new())
        with session_scope(self.sessions) as session:
            ordinal = session.execute(
                text("SELECT max(version_ordinal) + 1 FROM document_version WHERE document_uid = :d"), {"d": doc.document_uid}
            ).scalar_one()
            session.execute(
                text(
                    "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, "
                    "page_count) VALUES (:v, :d, :o, 'application/pdf', 1, :h, :c)"
                ),
                {"v": version, "d": doc.document_uid, "o": ordinal, "h": _hash(version), "c": pages},
            )
        return version

    def reorder(self, doc: Doc, order: list[str]) -> str:
        """An expert's version-order revision, written the way ``CMP-INGEST-01`` writes it."""
        order_id = ulid_id("cvo")
        with session_scope(self.sessions) as session:
            command = self.command(session, "append_comparison_version_order")
            revision = session.execute(
                text("SELECT coalesce(max(revision_no), 0) + 1 FROM comparison_version_order WHERE document_uid = :d"),
                {"d": doc.document_uid},
            ).scalar_one()
            session.execute(
                text(
                    "INSERT INTO comparison_version_order (comparison_version_order_id, project_uid, document_uid, "
                    "revision_no, version_uids, source, actor_user_uid, actor_label, command_id) VALUES (:i, :p, :d, :r, "
                    "CAST(:v AS jsonb), 'expert', :u, 'Эксперт', :c)"
                ),
                {"i": order_id, "p": doc.project_uid, "d": doc.document_uid, "r": revision, "v": json.dumps(order),
                 "u": ulid_id("usr"), "c": command},
            )
        return order_id

    def command(self, session: Session, kind: str) -> str:
        command = ulid_id("cmd")
        session.execute(
            text(
                "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
                "VALUES (:c, :t, :k, :f)"
            ),
            {"c": command, "t": kind, "k": f"seed-{new_ulid()}", "f": _hash(command)},
        )
        return command

    def stamp(self, doc: Doc, *, designation: str | None, stage: str | None = None, section: str | None = None) -> None:
        """The upload set that admitted the document, with the metadata the overview shows (a ``done`` set)."""
        with session_scope(self.sessions) as session:
            upload = self.upload_row(session, doc.project_uid, "completed")
            set_id = ulid_id("cus")
            session.execute(
                text(
                    "INSERT INTO comparison_upload_set (comparison_upload_set_id, comparison_upload_id, designation, "
                    "project_stage, section_code) VALUES (:s, :u, :d, :st, :sc)"
                ),
                {"s": set_id, "u": upload, "d": designation, "st": stage, "sc": section},
            )
            for edge in ("reading", "needs_confirmation"):
                session.execute(text("UPDATE comparison_upload_set SET state = :s WHERE comparison_upload_set_id = :i"),
                                {"s": edge, "i": set_id})
            session.execute(
                text(
                    "UPDATE comparison_upload_set SET state = 'ready', confirmed_at = now(), confirmed_by_user_uid = :u "
                    "WHERE comparison_upload_set_id = :i"
                ),
                {"u": ulid_id("usr"), "i": set_id},
            )
            session.execute(text("UPDATE comparison_upload_set SET state = 'admitting' WHERE comparison_upload_set_id = :i"),
                            {"i": set_id})
            session.execute(
                text(
                    "UPDATE comparison_upload_set SET state = 'done', document_uid = :d, terminal_at = now() "
                    "WHERE comparison_upload_set_id = :i"
                ),
                {"d": doc.document_uid, "i": set_id},
            )

    # -- uploads -------------------------------------------------------------------------------------------

    def upload_row(self, session: Session, project: str, state: str = "uploading") -> str:
        upload = ulid_id("cbt")
        command = self.command(session, "create_comparison_upload")
        session.execute(
            text(
                "INSERT INTO comparison_upload (comparison_upload_id, project_uid, declared_files, declared_bytes, "
                "actor_user_uid, actor_label, command_id) VALUES (:i, :p, 2, 10, :u, 'Эксперт', :c)"
            ),
            {"i": upload, "p": project, "u": ulid_id("usr"), "c": command},
        )
        path = {"uploading": [], "proposed": ["proposed"], "processing": ["proposed", "processing"],
                "paused": ["proposed", "processing", "paused"], "completed": ["proposed", "completed"],
                "cancelled": ["cancelled"]}[state]
        for step in path:
            terminal = ", terminal_at = now()" if step in ("completed", "cancelled") else ""
            session.execute(text(f"UPDATE comparison_upload SET state = :s{terminal} WHERE comparison_upload_id = :i"),
                            {"s": step, "i": upload})
        return upload

    def upload(self, project: str, state: str, *, sets: tuple[str, ...] = ()) -> str:
        """A batch in ``state`` with sets in the given states (``uploading``, ``needs_confirmation``, ``failed``,
        ``excluded`` or ``done``; a done set needs a document, so it is written by :meth:`stamp`)."""
        with session_scope(self.sessions) as session:
            upload = self.upload_row(session, project, state)
            for wanted in sets:
                set_id = ulid_id("cus")
                session.execute(
                    text("INSERT INTO comparison_upload_set (comparison_upload_set_id, comparison_upload_id) VALUES (:s, :u)"),
                    {"s": set_id, "u": upload},
                )
                path = {"uploading": [], "needs_confirmation": ["reading", "needs_confirmation"],
                        "failed": ["failed"], "excluded": ["excluded"]}[wanted]
                for step in path:
                    extra = ""
                    if step == "failed":
                        extra = ", failure_reason = 'comparison_sets_limit'"
                    if step == "excluded":
                        extra = ", terminal_at = now()"
                    session.execute(
                        text(f"UPDATE comparison_upload_set SET state = :s{extra} WHERE comparison_upload_set_id = :i"),
                        {"s": step, "i": set_id},
                    )
        return upload

    # -- the matrix ----------------------------------------------------------------------------------------

    def build(self, doc: Doc, rows: list[dict[str, Any]], *, order: list[str] | None = None,
              order_id: str | None = None) -> Any:
        """A matrix build over the document's current profiles, in ``order`` (default: the document's own)."""
        chosen = list(order or doc.versions)
        with session_scope(self.sessions) as session:
            facts = OverviewRepository().profile_facts(session, chosen, PAGE_PROFILE_ALGO)
            record = MatrixRepository().insert_build(
                session, project_uid=doc.project_uid, document_uid=doc.document_uid, order_id=order_id,
                signature=profile_digest(facts), rules=matrix_settings.RULES_VERSION, algo=matrix_settings.ALGO_VERSION,
                rows=rows, unassigned=[], summary={"order": chosen, "page_counts": {v: doc.page_counts[v] for v in chosen}},
            )
        assert record is not None
        return record

    def aligned_rows(self, doc: Doc, *, unmatched: int = 0) -> list[dict[str, Any]]:
        """One row for each page number of the first version: every version holds that page; the last ``unmatched`` rows
        have a hole (an unmatched cell) in the last version instead."""
        count = min(doc.page_counts[v] for v in doc.versions)
        rows: list[dict[str, Any]] = []
        for number in range(1, count + 1):
            holed = number > count - unmatched
            cells: list[dict[str, Any]] = []
            for index, version in enumerate(doc.versions):
                if holed and index == len(doc.versions) - 1:
                    cells.append({"version_uid": version, "state": "unmatched", "reason": "candidates_left"})
                else:
                    cells.append({
                        "version_uid": version, "state": "matched", "page_number": number,
                        "page_profile_id": doc.pages[version][number - 1], "confidence": "high", "flags": [],
                    })
            rows.append({"cells": cells})
        return rows

    # -- the series ----------------------------------------------------------------------------------------

    def series(
        self, doc: Doc, build: Any, state: str, *, completed: int | None = None, edit_no: int = 0, stale: bool = False,
        summaries: list[dict[str, int]] | None = None, order: list[str] | None = None,
    ) -> str:
        """A series over the adjacent pairs of ``order`` bound to ``build``: its ``state`` and ``completed`` transitions
        (the first ones). ``stale`` stores a digest of other inputs, so the series reads ``stale_reasons``."""
        chain = list(order or doc.versions)
        digest = input_digest(SeriesInputs(
            chain=tuple(chain), matrix_id=build.matrix_id, edit_no=edit_no, profile_signature=build.profile_signature,
            engine_algo=ENGINE_ALGO,
        ))
        if stale:
            digest = _hash("another input set")
        repo = SeriesRepository()
        series_id = ulid_id("cser")
        done = len(chain) - 1 if completed is None and state == "completed" else (completed or 0)
        with session_scope(self.sessions) as session:
            command = self.command(session, "start_comparison_series")
            repo.insert_series(
                session, series_id=series_id, project_uid=doc.project_uid, document_uid=doc.document_uid, order_id=None,
                matrix_id=build.matrix_id, edit_no=edit_no, digest=digest, restarted_from=None,
                actor_user_uid=ulid_id("usr"), actor_label="Эксперт", command_id=command,
            )
            transitions = [
                repo.insert_transition(session, series_id=series_id, number=i, source=a, target=b)
                for i, (a, b) in enumerate(zip(chain, chain[1:], strict=False), start=1)
            ]
            for index, transition in enumerate(transitions):
                if index < done:
                    summary = (summaries or [{}] * len(transitions))[index]
                    full = {"sheets": 2, "compared": 2, "same": 2, "zones_only": 0, "different": 0, "style_only": 0,
                            "needs_review": 0, "added": 0, "removed": 0, "failed": 0} | summary
                    repo.set_transition_state(session, transition, from_states=["queued"], to_state="running")
                    repo.set_transition_state(session, transition, from_states=["running"], to_state="completed",
                                              summary=full, verdict=["content_same"])
                elif state == "running" and index == done:
                    repo.set_transition_state(session, transition, from_states=["queued"], to_state="running")
            path = {"queued": [], "running": ["running"], "paused": ["running", "paused"], "completed": ["running", "completed"],
                    "failed": ["running", "failed"], "cancelled": ["cancelled"]}[state]
            previous = "queued"
            for step in path:
                repo.set_series_state(session, series_id, from_states=[previous], to_state=step,
                                      reason="series_failed_for_the_test" if step == "failed" else None)
                previous = step
        return series_id

    # -- the queue -----------------------------------------------------------------------------------------

    def work(self, project: str, kind: str, state: str = "queued", *, key: str | None = None,
             payload: dict[str, Any] | None = None, module: str = "versions", upload: str | None = None) -> str:
        """A queue item brought to ``state`` through the edges the database allows."""
        with session_scope(self.sessions) as session:
            enqueued = ComparisonWorkRepository().enqueue(
                session, project_uid=project, module=module, kind=kind, payload=payload or {},
                dedupe_key=key or f"{kind}:{new_ulid()}", max_attempts=3, comparison_upload_id=upload,
                created_by_user_uid=None,
            )
            path = {"queued": [], "leased": ["leased"], "running": ["leased", "running"], "paused": ["paused"],
                    "succeeded": ["leased", "running", "succeeded"], "failed": ["leased", "failed"],
                    "cancelled": ["cancelled"]}[state]
            for step in path:
                terminal = ", terminal_at = now()" if step in ("succeeded", "failed", "cancelled") else ""
                reason = ", failure_reason = 'work_failed_for_the_test'" if step == "failed" else ""
                session.execute(
                    text(f"UPDATE comparison_work SET state = :s{terminal}{reason} WHERE comparison_work_id = :i"),
                    {"s": step, "i": enqueued.work_id},
                )
        return enqueued.work_id

    # -- reads ---------------------------------------------------------------------------------------------

    def counts(self) -> dict[str, int]:
        with self.sessions() as session:
            return {t: int(session.execute(text(f"SELECT count(*) FROM {t}")).scalar_one()) for t in COUNTED_TABLES}

    def rows(self, sql: str, **params: Any) -> list[dict[str, Any]]:
        with self.sessions() as session:
            return [dict(r) for r in session.execute(text(sql), params).mappings()]


@pytest.fixture(scope="session")
def lab(sessions: sessionmaker[Session]) -> Lab:
    return Lab(sessions)


@pytest.fixture
def service(sessions: sessionmaker[Session]):
    from auditmanager.comparison.public import ComparisonOverviewService

    return ComparisonOverviewService(session_factory=sessions)


@pytest.fixture
def matrix_service(sessions: sessionmaker[Session]):
    from auditmanager.comparison.public import ComparisonMatrixService

    return ComparisonMatrixService(session_factory=sessions)


@pytest.fixture
def series_service(sessions: sessionmaker[Session]):
    from auditmanager.comparison.public import ComparisonSeriesService

    return ComparisonSeriesService(session_factory=sessions)


def _account(sessions: sessionmaker[Session], label: str, roles: tuple[str, ...]) -> tuple[str, str]:
    from auditmanager.access.accounts import AccountRepository
    from auditmanager.access.repository import UserRepository
    from tests.support.accounts import SUITE_NAMES, SUITE_PASSWORD, suite_login

    users = UserRepository()
    with sessions() as session:
        record = users.find_by_login(session, suite_login(label))
        if record is None:
            created = users.create_user(session, suite_login(label), SUITE_PASSWORD)
            accounts = AccountRepository()
            accounts.complete_profile(session, user_uid=str(created.user_uid), email=None,
                                      last_name=SUITE_NAMES[0], first_name=SUITE_NAMES[1])
            for role in roles:
                accounts.grant_role(session, user_uid=str(created.user_uid), role=role, granted_by=None)
            record = users.find_by_login(session, suite_login(label))
            session.commit()
        return str(record.user_uid), record.login


@pytest.fixture(scope="session")
def expert_uid(sessions: sessionmaker[Session]) -> str:
    return _account(sessions, "overview-expert", ("expert",))[0]


def token_for(sessions: sessionmaker[Session], label: str, roles: tuple[str, ...]) -> dict[str, str]:
    from auditmanager.api.security import API_TOKEN_VARIABLE, Subject, build_signer
    from auditmanager.access.repository import UserRepository
    from tests.support.accounts import suite_login

    _account(sessions, label, roles)
    with sessions() as session:
        record = UserRepository().find_by_login(session, suite_login(label))
        signer = build_signer({API_TOKEN_VARIABLE: SECRET})
        token = signer.issue(
            Subject(user_uid=str(record.user_uid), login=record.login, token_epoch=record.token_epoch,
                    display_label=record.display_label),
            is_default_credential=False,
        ).token
    return {"Authorization": f"Bearer {token}"}
