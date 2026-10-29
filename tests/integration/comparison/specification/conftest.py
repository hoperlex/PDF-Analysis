"""PostgreSQL and object-store fixtures of the specification integration tests (`CMP-VC-SPEC-01`), after the series lane's.

The lane's own services are required, never skipped. The tests **commit**, and ``document_version`` refuses DELETE by trigger, so
every test works in documents of its own with fresh identities and the shared database is never cleaned.

The expensive part, profiling the versions V3, V4 and V5 of VS-1 through the real page children, is done once per database for a
*template* document; a test's document is a clone of it (new project, document and versions, the template's profile rows copied
under the new versions -- a profile is a function of the page's bytes). The synthetic corpus' answer key is the oracle.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.profile.builder import build_version_page_profiles
from auditmanager.comparison.profile.publish import ProfileBlobPublisher
from auditmanager.documents.public import MANIFEST_ROLE_SOURCE_DOCUMENT
from auditmanager.shared.db import session_scope
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.session import create_session_factory
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid, new_ulid
from auditmanager.storage.public import S3BlobStore, S3StorageSettings, StorageError

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures" / "comparison"
_NAMES = (
    "DATABASE_URL", "S3_ENDPOINT_URL", "S3_API_PORT", "S3_REGION", "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY", "S3_BUCKET",
)
SECRET = "comparison-specification-suite"
TEMPLATE_PROJECT = "Спецификации: образец"
#: The versions of the template, oldest first: the corpus' V3, V4 and V5 (the specification sheet is page 6, 6 and 7).
TEMPLATE_FILES = ("vs1/v3.pdf", "vs1/v4.pdf", "vs1/v5.pdf")
SPEC_PAGE = {"vs1/v3.pdf": 6, "vs1/v4.pdf": 6, "vs1/v5.pdf": 7}


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
        for table in ("comparison_matrix", "comparison_series", "comparison_page_profile", "comparison_spec_extraction", "comparison_spec_comparison"):
            if connection.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}).scalar_one_or_none() is None:
                pytest.fail(f"the database has no {table} table: run `make migrate` (head 0040)")
    yield built
    built.dispose()


@pytest.fixture(scope="session")
def sessions(engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(engine)


@pytest.fixture(scope="session")
def blob_store() -> S3BlobStore:
    _load_dotenv()
    try:
        store = S3BlobStore(S3StorageSettings.from_env())
        store.check_access()
    except StorageError as failure:
        pytest.fail(f"the lane's private bucket is not reachable: {failure}")
    return store


@pytest.fixture(scope="session")
def vs1_key() -> dict[str, Any]:
    return json.loads((FIXTURES / "vs1" / "answer_key.json").read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class Doc:
    project_uid: str
    document_uid: str
    versions: tuple[str, ...]  # oldest first: V3, V4, V5
    page_counts: dict[str, int]


class Lab:
    """The committed reads and writes the tests make beside the code under test."""

    def __init__(self, sessions: sessionmaker[Session], engine: Engine, blob_store: S3BlobStore, template: Doc) -> None:
        self.sessions, self.engine, self.blob_store, self.template = sessions, engine, blob_store, template

    def clone(self) -> Doc:
        project, document = str(ProjectUid.new()), str(DocumentUid.new())
        made: list[str] = []
        with session_scope(self.sessions) as session:
            session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'Спецификации')"), {"p": project})
            session.execute(
                text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'Комплект')"),
                {"d": document, "p": project},
            )
            for ordinal, source in enumerate(self.template.versions, start=1):
                version = str(VersionUid.new())
                made.append(version)
                session.execute(
                    text(
                        "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, "
                        "byte_size, sha256, page_count) SELECT :v, :d, :o, media_type, byte_size, sha256, page_count "
                        "FROM document_version WHERE version_uid = :s"
                    ),
                    {"v": version, "d": document, "o": ordinal, "s": source},
                )
                session.execute(
                    text(
                        "INSERT INTO input_manifest_entry (version_uid, role, blob_id, sha256, size_bytes, media_type) "
                        "SELECT :v, role, blob_id, sha256, size_bytes, media_type FROM input_manifest_entry WHERE version_uid = :s"
                    ),
                    {"v": version, "s": source},
                )
                session.execute(
                    text(
                        "INSERT INTO comparison_page_profile (comparison_page_profile_id, version_uid, page_number, "
                        "content_key, algo_version, status, reason, profile, profile_blob_id, preview_blob_id, "
                        "thumbnail_blob_id) SELECT 'cpr_' || :ulid_prefix || lpad(page_number::text, 6, '0'), :v, "
                        "page_number, content_key, algo_version, status, reason, profile, profile_blob_id, "
                        "preview_blob_id, thumbnail_blob_id FROM comparison_page_profile WHERE version_uid = :s"
                    ),
                    {"v": version, "s": source, "ulid_prefix": new_ulid()[:20]},
                )
        return Doc(project, document, tuple(made), {v: self.template.page_counts[s] for v, s in zip(made, self.template.versions, strict=True)})

    def rows(self, sql: str, **params: Any) -> list[dict[str, Any]]:
        with self.sessions() as session:
            return [dict(r) for r in session.execute(text(sql), params).mappings()]

    def profile_id(self, doc: Doc, version_index: int, page: int) -> str:
        found = self.rows(
            "SELECT comparison_page_profile_id AS id FROM comparison_page_profile WHERE version_uid = :v AND page_number = :n "
            "ORDER BY created_at DESC LIMIT 1", v=doc.versions[version_index], n=page)
        return str(found[0]["id"])


@pytest.fixture(scope="session")
def template(sessions: sessionmaker[Session], blob_store: S3BlobStore, vs1_key: dict[str, Any]) -> Doc:
    """V3, V4 and V5 of VS-1 as a published document with every page profiled by the real children (built once per database)."""
    with sessions() as session:
        found = session.execute(text(
            "SELECT d.document_uid, p.project_uid FROM document d JOIN project p ON p.project_uid = d.project_uid "
            "WHERE p.name = :n ORDER BY p.created_at DESC LIMIT 1"), {"n": TEMPLATE_PROJECT}).first()
        if found is not None:
            rows = session.execute(text(
                "SELECT v.version_uid, v.page_count, count(cp.comparison_page_profile_id) AS profiled "
                "FROM document_version v LEFT JOIN comparison_page_profile cp ON cp.version_uid = v.version_uid "
                "WHERE v.document_uid = :d GROUP BY v.version_uid, v.page_count, v.version_ordinal "
                "ORDER BY v.version_ordinal"), {"d": found[0]}).all()
            if len(rows) == len(TEMPLATE_FILES) and all(r[1] == r[2] for r in rows):
                return Doc(found[1], found[0], tuple(r[0] for r in rows), {r[0]: int(r[1]) for r in rows})
    project, document = str(ProjectUid.new()), str(DocumentUid.new())
    versions: list[str] = []
    counts: dict[str, int] = {}
    with session_scope(sessions) as session:
        session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, :n)"), {"p": project, "n": TEMPLATE_PROJECT})
        session.execute(
            text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'Образец')"),
            {"d": document, "p": project},
        )
    page_counts = {v["file"]: v["page_count"] for v in vs1_key["versions"]}
    for ordinal, name in enumerate(TEMPLATE_FILES, start=1):
        data = (FIXTURES / name).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        version = str(VersionUid.new())
        blob_id = ProfileBlobPublisher(sessions, blob_store).publish(data, role="source_document", media_type="application/pdf")
        with session_scope(sessions) as session:
            session.execute(
                text(
                    "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, "
                    "sha256, page_count) VALUES (:v, :d, :o, 'application/pdf', :n, :s, :c)"
                ),
                {"v": version, "d": document, "o": ordinal, "n": len(data), "s": digest, "c": page_counts[name]},
            )
            session.execute(
                text(
                    "INSERT INTO input_manifest_entry (version_uid, role, blob_id, sha256, size_bytes, media_type) "
                    "VALUES (:v, :r, :b, :s, :n, 'application/pdf')"
                ),
                {"v": version, "r": MANIFEST_ROLE_SOURCE_DOCUMENT, "b": blob_id, "s": digest, "n": len(data)},
            )
        report = build_version_page_profiles(sessions, blob_store, version)
        assert report.complete, name
        versions.append(version)
        counts[version] = page_counts[name]
    return Doc(project, document, tuple(versions), counts)


@pytest.fixture
def lab(sessions: sessionmaker[Session], engine: Engine, blob_store: S3BlobStore, template: Doc) -> Lab:
    return Lab(sessions, engine, blob_store, template)


@pytest.fixture(scope="session")
def expert_uid(sessions: sessionmaker[Session]) -> str:
    return _account(sessions, "spec-expert", ("expert",))[0]


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
            accounts.complete_profile(session, user_uid=str(created.user_uid), email=None, last_name=SUITE_NAMES[0], first_name=SUITE_NAMES[1])
            for role in roles:
                accounts.grant_role(session, user_uid=str(created.user_uid), role=role, granted_by=None)
            record = users.find_by_login(session, suite_login(label))
            session.commit()
        return str(record.user_uid), record.login


@pytest.fixture
def matrix_service(sessions: sessionmaker[Session], blob_store: S3BlobStore):
    from auditmanager.comparison.public import ComparisonMatrixService

    return ComparisonMatrixService(session_factory=sessions, blob_store=blob_store)


@pytest.fixture
def series_service(sessions: sessionmaker[Session], blob_store: S3BlobStore):
    from auditmanager.comparison.public import ComparisonSeriesService

    return ComparisonSeriesService(session_factory=sessions, blob_store=blob_store)


@pytest.fixture
def started(lab: Lab, matrix_service, series_service, expert_uid: str):
    """A series over the clone of the template: its transitions and sheet pairs exist (queued, not compared): the rows the reads
    of part A are addressed by. Nothing is compared and no worker runs."""

    def start() -> tuple[Doc, dict[str, Any]]:
        doc = lab.clone()
        built = matrix_service.build_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)
        assert built.outcome in ("built", "existing"), built
        series = series_service.start_series(
            project_uid=doc.project_uid, document_uid=doc.document_uid, restart=False, base_order_revision_no=None,
            user_uid=expert_uid, actor_label="Эксперт Т.", actor_roles=frozenset({"expert"}), idempotency_key=f"spec-{new_ulid()}")
        return doc, series

    return start


@pytest.fixture(autouse=True)
def _leave_no_live_item_behind(sessions: sessionmaker[Session]):
    """A test of this directory starts a series, which queues its items; at the end of every test the live items of this directory's
    projects are cancelled, so no other directory of ``tests/integration/comparison`` meets them."""
    yield
    mine = "FROM project p WHERE p.project_uid = w.project_uid AND p.name = 'Спецификации' AND w.terminal_at IS NULL"
    with sessions() as session:
        session.execute(text(
            "UPDATE comparison_work w SET state = 'cancelled', terminal_at = clock_timestamp() " + mine +
            " AND w.state IN ('queued', 'paused', 'retry_wait')"))
        session.commit()


# -- part B: a job row of the transition, and the model a careful reader of the text would be ---------------------------------

import json  # noqa: E402

from auditmanager.comparison.specification import check  # noqa: E402

ACTOR = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SHA = "a" * 64


def faithful_answer(source: dict[str, Any]) -> dict[str, Any]:
    """The answer a careful model gives for a packet: every pipe row a position (its whole line as evidence, its cells as the
    fields), the header and separator lines ignored as such, a plain line a section title."""
    blocks = []
    section = ""
    for block in source["blocks"]:
        rows, ignored = [], []
        header: dict[int, str] | None = None
        for line in block["lines"]:
            cells = check._pipe_cells(line["text"])
            if cells is None:
                text_line = line["text"].strip()
                if text_line.lower().startswith("примечание"):  # a substantive note is a position of its own, with the field note
                    fields = {name: "" for name in check.FIELDS}
                    fields["note"] = text_line
                    rows.append({"section": section, "parent": "", "fields": fields, "evidence": [{"line": line["line"], "quote": line["text"]}]})
                    continue
                section = text_line
                ignored.append({"line": line["line"], "reason": "section"})
                continue
            recognized = check._table_header(cells)
            if recognized is not None:
                header = recognized
                ignored.append({"line": line["line"], "reason": "header"})
                continue
            if check._separator_row(cells):
                ignored.append({"line": line["line"], "reason": "separator"})
                continue
            fields = {name: "" for name in check.FIELDS}
            for index, field in (header or {}).items():
                fields[field] = cells[index]
            rows.append({"section": section, "parent": "", "fields": fields, "evidence": [{"line": line["line"], "quote": line["text"]}]})
        blocks.append({"block_id": block["block_id"], "rows": rows, "ignored": ignored, "issues": []})
    return {"blocks": blocks}


@pytest.fixture
def job_for(sessions: sessionmaker[Session]):
    """``job_for(scope)``: a ``spec`` job of the transition with the connection revision it needs; the AI-job core is the writer of
    this table in the product, the tests write the row they need."""

    def make(scope: Any) -> str:
        connection, revision, command, job = (f"{p}_{new_ulid()}" for p in ("exc", "excr", "cmd", "cai"))
        with session_scope(sessions) as session:
            session.execute(text("INSERT INTO executor_connection (connection_id, kind, display_name, created_by) VALUES (:id, 'http_api', 'test', :a)"),
                            {"id": connection, "a": ACTOR})
            session.execute(text(
                "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, created_by, pin_id, gateway_model, billing, "
                "allow_client_documents, timeout_seconds, api_flavour, base_url, transport) VALUES (:r, :c, 1, :a, 'claude-opus-5', "
                "'anthropic/claude-opus-5', 'metered', false, 60, 'openai_chat', 'https://proxy.test', 'direct')"),
                {"r": revision, "c": connection, "a": ACTOR})
            session.execute(text("INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) VALUES (:c, 'start_comparison_spec', :k, :f)"),
                            {"c": command, "k": command[:20], "f": SHA})
            session.execute(text(
                "INSERT INTO comparison_ai_job (comparison_ai_job_id, project_uid, document_uid, method, "
                "comparison_transition_id, connection_revision_id, pinned_model, provider_mode, estimate, estimate_digest, estimate_micros, "
                "ceiling_micros, consented_by_user_uid, command_id) VALUES (:j, :p, :d, 'spec', :t, :rev, 'claude-opus-5', 'recorded', "
                "CAST(:est AS jsonb), :dig, 0, 0, :a, :c)"),
                {"j": job, "p": scope.project_uid, "d": scope.document_uid, "t": scope.transition_id, "rev": revision,
                 "est": json.dumps({"estimate_digest": SHA, "units": 2}), "dig": SHA, "a": ACTOR, "c": command})
        return job

    return make


# -- part B on the AI-job core: a route, a service, a runner of the lane's handler --------------------------------------------

@pytest.fixture
def route(sessions: sessionmaker[Session]) -> dict[str, str]:
    """An executor connection with a current revision, **routed** to the work kind ``comparison_spec`` in «Назначения» (the append-only
    route event is written; the latest wins). Nothing here can reach a provider."""
    connection, revision, event = (f"{p}_{new_ulid()}" for p in ("exc", "excr", "ert"))
    with session_scope(sessions) as session:
        session.execute(text("INSERT INTO executor_connection (connection_id, kind, display_name, created_by) VALUES (:id, 'http_api', 'recorded', :a)"),
                        {"id": connection, "a": ACTOR})
        session.execute(text(
            "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, created_by, pin_id, gateway_model, billing, "
            "allow_client_documents, timeout_seconds, api_flavour, base_url, transport) VALUES (:r, :c, 1, :a, 'claude-opus-5', "
            "'anthropic/claude-opus-5', 'metered', false, 60, 'openai_chat', 'https://recorded.test', 'direct')"),
            {"r": revision, "c": connection, "a": ACTOR})
        session.execute(text(
            "INSERT INTO executor_route_event (route_event_id, work_kind, route_no, primary_connection_id, set_by) "
            "SELECT :e, 'comparison_spec', COALESCE(MAX(route_no), 0) + 1, :c, :a FROM executor_route_event WHERE work_kind = 'comparison_spec'"),
            {"e": event, "c": connection, "a": ACTOR})
    return {"connection": connection, "revision": revision}


@pytest.fixture
def jobs(sessions: sessionmaker[Session], blob_store: Any):
    """The core's service with the lane's method, in a recorded process."""
    from auditmanager.comparison.public import ComparisonAiJobService, SpecMethod

    return ComparisonAiJobService(
        sessions, methods=[SpecMethod(sessions, blob_store)], comparison_modules="versions", provider_mode="recorded")


@pytest.fixture(scope="session")
def worker_id(sessions: sessionmaker[Session]) -> str:
    from auditmanager.workers.public import WorkerRegistry

    with sessions() as session:
        registered = WorkerRegistry().register(session, version="cmp-vc-spec-01-test", slots=1)
        session.commit()
    return str(registered)


@pytest.fixture
def runner_of(sessions: sessionmaker[Session], engine: Engine, blob_store: Any):
    """``runner_of(binder)``: the comparison runner with the lane's handler (and no other) bound to ``binder``; the Run-priority gate reads
    nothing, so a claim sees comparison work only."""
    from auditmanager.comparison.public import ClaimGates, ComparisonWorkRepository, ComparisonWorkRunner, HandlerRegistry, WorkDependencies, default_gates
    from auditmanager.comparison.specification.method import SpecHandler

    def make(binder: Any) -> Any:
        work = ComparisonWorkRepository()
        registry = HandlerRegistry.build(
            (lambda deps: SpecHandler(deps, binder=binder),), WorkDependencies(engine=engine, session_factory=sessions, blob_store=blob_store, work=work))
        gates = ClaimGates(paused=default_gates().paused, run_claimable=lambda session: False)
        return ComparisonWorkRunner(sessions, registry=registry, modules=frozenset({"versions"}), repository=work, gates=gates)

    return make


def run_items(runner: Any, worker: str, engine: Engine, project: str, *, limit: int = 10) -> list[tuple[str, str | None]]:
    """Claim and execute the project's items until none is claimable (other projects' items are fenced off)."""
    ran: list[tuple[str, str | None]] = []
    for _ in range(limit):
        with engine.connect() as fence:
            fence.execute(text(
                "SELECT comparison_work_id FROM comparison_work WHERE state = 'queued' AND project_uid <> :p "
                "ORDER BY comparison_work_id FOR UPDATE SKIP LOCKED"), {"p": project})
            try:
                item = runner.claim(worker)
            finally:
                fence.rollback()
        if item is None:
            break
        ran.append((item.kind, runner.execute(item)))
    return ran
