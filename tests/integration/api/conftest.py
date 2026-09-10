"""Fixtures for the API-edge suite: real PostgreSQL, real MinIO, real refusals.

Three decisions shape this file.

**The services are real and the suite never skips.** A missing ``DATABASE_URL`` or an
unreachable bucket is a hard failure. Everything this suite exists to prove is service
behaviour -- the ``AM001``/``AM002``/``AM003`` triggers, the ``finding_current_verdict``
view, the immutability of a published version, the bytes coming back from object
storage -- and none of it has an in-memory equivalent worth asserting against. A skipped
integration suite reports success while proving nothing.

**Isolation is by rollback.** It has to be: ``expert_decision_event`` refuses ``DELETE``
with ``AM002`` and ``document_version`` refuses it with ``AM003``, which are the very
properties under test. A fixture that tore rows down afterwards would have to defeat
the guards it is meant to prove. Objects written to MinIO are *not* rolled back; they
are content-addressed and harmless, and an orphan object is exactly the state
``auditmanager.ingest``'s reconciler exists to adopt.

**The ports are wired to real modules wherever a public surface exists.**
``ProjectPort``, ``DocumentPort`` and ``DecisionPort`` run against ``B1``'s
``IngestService`` and ``B4``'s ledger and projection. ``FindingPort`` cannot be: three
fields the frozen ``Finding`` requires are not on ``B4``'s ``FindingRow`` projection,
so the adapter here reads them from the database directly. ``RunPort`` and
``CsvExportPort`` have no producer in this tree at all -- ``B5`` is building
``auditmanager.runs`` and ``auditmanager.exports`` in parallel -- so they are satisfied
here by adapters written against the same frozen declarations. All of this is recorded
in ``src/auditmanager/api/README.md`` and reported to the integrator; none of it is a
widening of another session's module.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.api.routers import Router, build_router
from auditmanager.api.schemas.decisions import DecisionEventView
from auditmanager.api.schemas.documents import DocumentVersionView, ManifestEntryView
from auditmanager.api.schemas.findings import (
    EvidenceView,
    FindingDetailView,
    FindingView,
    ObservationView,
    ProvenanceView,
)
from auditmanager.api.schemas.projects import ProjectView
from auditmanager.api.schemas.runs import RunStatusView, StageStateView
from auditmanager.decisions import current_verdict, decision_history, record_decision
from auditmanager.findings import (
    BlockIndex,
    ObservationSet,
    TextLayer,
    publish_gate_result,
    run_grounding_gate,
)
from auditmanager.ingest import IngestService
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    AnalysisProfileId,
    CommandId,
    DocumentUid,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)
from auditmanager.storage import S3BlobStore, S3StorageSettings, StorageError

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CORPUS_PDF = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar" / "ar_baseline.pdf"

#: The governance interpreter, the only one carrying `jsonschema`. Section-7 conformance
#: is checked with a real Draft 2020-12 implementation, driven exactly the way
#: `tests/contract/api_v1` drives it, because re-implementing 2020-12 evaluation in the
#: test would be asserting the belief under test.
GOVERNANCE_PYTHON = REPOSITORY_ROOT / ".venv" / "bootstrap" / "bin" / "python"
SCHEMA_CHECKER = (
    REPOSITORY_ROOT / "tests" / "contract" / "api_v1" / "schema_validation_check.py"
)
OPENAPI = REPOSITORY_ROOT / "contracts" / "api" / "v1" / "openapi.json"

_S3_VARS = (
    "S3_ENDPOINT_URL",
    "S3_REGION",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "S3_BUCKET",
)
_REQUIRED_VARS = ("DATABASE_URL", *_S3_VARS)

#: Two short Russian pages, so an offset counted in bytes rather than in code points
#: lands in the wrong place and is caught. Mirrors tests/integration/decisions.
PAGE_ONE = "Степень огнестойкости здания — II.\nВысота этажа 3,3 м.\n"
PAGE_TWO = "Степень огнестойкости здания — III.\nТип заполнения — уточнить.\n"


def _load_dotenv_if_needed() -> None:
    """Fill in missing frozen names from the repository-root ``.env``.

    Narrow on purpose: only the names this suite needs, never overriding an exported
    value, and no shell evaluation -- the file is data, as its own header says. Mirrors
    ``tests/integration/storage/conftest.py``; it must not grow into a general loader.
    """
    if all(os.environ.get(name) for name in _REQUIRED_VARS):
        return
    dotenv = REPOSITORY_ROOT / ".env"
    if not dotenv.is_file():
        return
    for raw in dotenv.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        name, sep, value = line.partition("=")
        if not sep:
            continue
        name = name.strip()
        if name not in _REQUIRED_VARS or os.environ.get(name):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ[name] = value


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    _load_dotenv_if_needed()
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail(
            "DATABASE_URL is not set. tests/integration/api runs against real "
            "PostgreSQL: the AM001/AM002/AM003 triggers this suite maps to the error "
            "envelope are database behaviour and have no in-memory equivalent. This "
            "suite never skips."
        )
    built = create_database_engine(DatabaseSettings(url=parse_database_url(raw)))
    try:
        with built.connect() as connection:
            present = connection.execute(
                text("SELECT to_regclass('public.finding_current_verdict')")
            ).scalar_one_or_none()
        if present is None:
            pytest.fail(
                "the configured database has no finding_current_verdict view. Run "
                "`make migrate` (or `make foundation`) for this lane first."
            )
        yield built
    finally:
        built.dispose()


@pytest.fixture(scope="session")
def store() -> S3BlobStore:
    _load_dotenv_if_needed()
    try:
        built = S3BlobStore(S3StorageSettings.from_env())
        built.check_access()
    except StorageError as exc:
        pytest.fail(
            "tests/integration/api needs a real private bucket: "
            f"streamDocumentVersionContent returns real bytes. {exc}"
        )
    return built


@pytest.fixture
def connection(engine: Engine) -> Iterator[Any]:
    """One connection with an outer transaction that is always rolled back."""
    opened = engine.connect()
    transaction = opened.begin()
    try:
        yield opened
    finally:
        transaction.rollback()
        opened.close()


@pytest.fixture
def session_factory(connection: Any) -> sessionmaker[Session]:
    """Sessions that join the outer transaction, so ``session_scope`` commits inside it.

    ``IngestService`` opens its own units of work and commits them. Bound to this
    connection, each of those commits releases a savepoint inside the enclosing
    transaction, and the fixture's rollback still undoes everything.
    """
    return sessionmaker(bind=connection, expire_on_commit=False, future=True)


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    opened = session_factory()
    try:
        yield opened
    finally:
        opened.close()


@pytest.fixture
def ingest(store: S3BlobStore, session_factory: sessionmaker[Session]) -> IngestService:
    return IngestService(store, session_factory=session_factory)


@pytest.fixture(scope="session")
def corpus_pdf() -> bytes:
    if not CORPUS_PDF.is_file():
        pytest.fail(f"the committed corpus fixture is missing at {CORPUS_PDF}")
    return CORPUS_PDF.read_bytes()


# ---------------------------------------------------------------------------
# Port adapters
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Uploaded:
    version: DocumentVersionView
    replayed: bool


@dataclass(frozen=True, slots=True)
class _Appended:
    event: DecisionEventView
    current_verdict: str


class IngestProjectAdapter:
    """``ProjectPort`` over ``B1``'s ``IngestService``.

    ``create_project`` takes no idempotency key: ``B1`` publishes no
    key-accepting project command. The key is required by the frozen document and is
    validated at the edge, and this adapter is where it stops. Reported, not worked
    around -- deriving a command record here would be the router re-deriving a key,
    which section 7 forbids in the same sentence that requires the header.
    """

    def __init__(self, ingest: IngestService) -> None:
        self._ingest = ingest

    def create_project(self, *, name: str, idempotency_key: str) -> ProjectView:
        record = self._ingest.create_project(name)
        return ProjectView(
            project_uid=str(record.project_uid),
            name=record.name,
            created_at=record.created_at,
        )

    def list_projects(self) -> Sequence[ProjectView]:
        # The frozen document says "newest first"; `B1`'s query is `ORDER BY created_at,
        # project_uid`, which is oldest first. Reversing here is the adapter's job, not
        # the router's, and the mismatch is reported.
        rows = self._ingest.list_projects()
        return tuple(
            ProjectView(
                project_uid=str(record.project_uid),
                name=record.name,
                created_at=record.created_at,
            )
            for record in reversed(rows)
        )


class IngestDocumentAdapter:
    """``DocumentPort`` over ``B1``'s ``IngestService``.

    ``version_ordinal`` is **required** by the frozen ``DocumentVersion`` and is not on
    ``B1``'s ``DocumentVersionRecord``, so this adapter reads that one column from the
    database. That is the gap, made explicit and reported; the alternative -- widening
    ``B1``'s projection -- is another session's tree.
    """

    def __init__(self, ingest: IngestService, session: Session) -> None:
        self._ingest = ingest
        self._session = session

    def _view(self, record: Any) -> DocumentVersionView:
        ordinal = self._session.execute(
            text(
                "SELECT version_ordinal FROM document_version WHERE version_uid = :v"
            ),
            {"v": str(record.version_uid)},
        ).scalar_one()
        return DocumentVersionView(
            version_uid=str(record.version_uid),
            document_uid=str(record.document_uid),
            project_uid=str(record.project_uid),
            version_ordinal=int(ordinal),
            byte_size=record.byte_size,
            sha256=record.sha256,
            page_count=record.page_count,
            published_at=record.published_at,
            media_type=record.media_type,
            input_manifest=tuple(
                ManifestEntryView(
                    role=entry.role,
                    sha256=entry.sha256,
                    size_bytes=entry.size_bytes,
                    media_type=entry.media_type,
                )
                for entry in record.manifest
            ),
        )

    def upload_document(
        self,
        *,
        project_uid: str,
        content: bytes,
        source_filename: str,
        display_title: str | None,
        idempotency_key: str,
    ) -> _Uploaded:
        outcome = self._ingest.upload_single_pdf(
            project_uid=ProjectUid(project_uid),
            content=content,
            source_filename=source_filename,
            display_title=display_title or source_filename,
            idempotency_key=idempotency_key,
        )
        return _Uploaded(version=self._view(outcome.version), replayed=outcome.replayed)

    def get_version(self, *, version_uid: str) -> DocumentVersionView:
        return self._view(self._ingest.get_version(VersionUid(version_uid)))

    def read_content(self, *, version_uid: str) -> bytes:
        return self._ingest.read_source_bytes(VersionUid(version_uid))


class DatabaseFindingAdapter:
    """``FindingPort``.

    ``B4``'s ``published_findings`` returns a ``FindingRow`` carrying neither
    ``project_uid`` nor ``version_uid`` nor ``run_id``, and the frozen ``Finding``
    requires all three; there is also no by-``finding_uid`` detail query at all. So this
    adapter reads the columns the document requires. It is a **test** adapter standing
    in for a projection ``B4`` does not publish, and the gap is reported rather than
    patched into ``B4``.
    """

    _FINDINGS = text(
        """
        SELECT f.finding_uid, f.project_uid, f.version_uid, f.allocated_by_run_id,
               f.category, o.finding_observation_id, o.run_id, o.finding_text,
               o.recommendation_text, o.stage_id, o.analysis_profile_id,
               o.prompt_bundle_id, o.model_call_id, o.provider_mode
        FROM finding f
        JOIN finding_observation o ON o.finding_uid = f.finding_uid
        WHERE (:run_id IS NULL OR o.run_id = :run_id)
          AND (:finding_uid IS NULL OR f.finding_uid = :finding_uid)
        ORDER BY f.finding_uid, o.finding_observation_id
        """
    )
    _EVIDENCE = text(
        """
        SELECT evidence_ordinal, page_number, quote, char_start, char_end, block_id
        FROM finding_evidence
        WHERE finding_observation_id = :observation_id
        ORDER BY evidence_ordinal
        """
    )

    def __init__(self, session: Session) -> None:
        self._session = session

    def _rows(self, *, run_id: str | None, finding_uid: str | None) -> list[FindingView]:
        found = (
            self._session.execute(
                self._FINDINGS, {"run_id": run_id, "finding_uid": finding_uid}
            )
            .mappings()
            .all()
        )
        views: list[FindingView] = []
        for row in found:
            evidence = (
                self._session.execute(
                    self._EVIDENCE,
                    {"observation_id": row["finding_observation_id"]},
                )
                .mappings()
                .all()
            )
            projection = current_verdict(self._session, row["finding_uid"])
            views.append(
                FindingView(
                    finding_uid=row["finding_uid"],
                    project_uid=row["project_uid"],
                    version_uid=row["version_uid"],
                    run_id=row["run_id"],
                    category=row["category"],
                    observation=ObservationView(
                        finding_observation_id=row["finding_observation_id"],
                        run_id=row["run_id"],
                        category=row["category"],
                        finding_text=row["finding_text"],
                        recommendation_text=row["recommendation_text"],
                        evidence=tuple(
                            EvidenceView(
                                evidence_ordinal=item["evidence_ordinal"],
                                page_number=item["page_number"],
                                quote=item["quote"],
                                char_start=item["char_start"],
                                char_end=item["char_end"],
                                block_id=item["block_id"],
                            )
                            for item in evidence
                        ),
                        provenance=ProvenanceView(
                            stage_id=row["stage_id"],
                            analysis_profile_id=row["analysis_profile_id"],
                            prompt_bundle_id=row["prompt_bundle_id"],
                            provider_mode=row["provider_mode"],
                            model_call_id=row["model_call_id"],
                        ),
                    ),
                    current_verdict=(
                        projection.current_verdict if projection else "pending"
                    ),
                    latest_decision_id=(
                        projection.latest_decision_id if projection else None
                    ),
                    decision_recorded_at=(
                        projection.decision_recorded_at if projection else None
                    ),
                )
            )
        return views

    def list_run_findings(
        self, *, run_id: str, category: str | None, verdict: str | None
    ) -> Sequence[FindingView]:
        views = self._rows(run_id=run_id, finding_uid=None)
        if category is not None:
            views = [view for view in views if view.category == category]
        if verdict is not None:
            views = [view for view in views if view.current_verdict == verdict]
        return tuple(views)

    def get_finding(self, *, finding_uid: str) -> FindingDetailView:
        views = self._rows(run_id=None, finding_uid=finding_uid)
        if not views:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Finding")
        projection = current_verdict(self._session, finding_uid)
        return FindingDetailView(
            finding=views[0],
            latest_comment=projection.latest_comment if projection else None,
            decision_event_count=projection.decision_event_count if projection else 0,
        )


class LedgerDecisionAdapter:
    """``DecisionPort`` over ``B4``'s append-only ledger and its projection.

    ``record_decision`` accepts a ``command_id`` and no idempotency key, and nothing in
    ``auditmanager.decisions`` claims a command record from one. The key is therefore
    mapped to a ``command_id`` **here**, in the adapter a composition root owns, and not
    in the router -- section 7 forbids the router deriving a key, and this is the
    boundary where the two meet. Reported.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._keys: dict[str, str] = {}

    def _command_id(self, key: str) -> str:
        allocated = self._keys.get(key)
        if allocated is None:
            allocated = str(CommandId.new())
            self._keys[key] = allocated
        return allocated

    @staticmethod
    def _view(event: Any) -> DecisionEventView:
        return DecisionEventView(
            decision_id=event.decision_id,
            finding_uid=event.finding_uid,
            finding_observation_id=event.finding_observation_id,
            event_type=event.event_type,
            author_label=event.author_label,
            recorded_at=event.recorded_at,
            verdict=event.verdict,
            comment=event.comment,
        )

    def append_decision(
        self,
        *,
        finding_uid: str,
        finding_observation_id: str,
        event_type: str,
        comment: str | None,
        idempotency_key: str,
    ) -> _Appended:
        event = record_decision(
            self._session,
            finding_uid=finding_uid,
            finding_observation_id=finding_observation_id,
            event_type=event_type,
            comment=comment,
            command_id=self._command_id(idempotency_key),
        )
        projection = current_verdict(self._session, finding_uid)
        return _Appended(
            event=self._view(event),
            current_verdict=projection.current_verdict if projection else "pending",
        )

    def decision_history(self, *, finding_uid: str) -> Sequence[DecisionEventView]:
        events = decision_history(self._session, finding_uid)
        # The declared client-visible order is `(recorded_at, decision_id)`; `B4`
        # returns `ORDER BY sequence_no`. Sorting here means the cursor never has to
        # know that the server has a sequence at all.
        return tuple(
            sorted(
                (self._view(event) for event in events),
                key=lambda view: (view.recorded_at, view.decision_id),
            )
        )


class SeamRunAdapter:
    """``RunPort`` written against the frozen ``RunStatus``, standing in for ``B5``.

    ``auditmanager.runs`` does not exist in this tree. This reads the ``audit_run`` row
    the migration head defines and renders the frozen shape. It implements no run
    behaviour: it starts nothing, schedules nothing and moves no state.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def _view(self, run_id: str) -> RunStatusView:
        row = (
            self._session.execute(
                text(
                    "SELECT run_id, project_uid, version_uid, state, provider_mode, "
                    "analysis_profile_id, prompt_bundle_id, created_at, terminal_at "
                    "FROM audit_run WHERE run_id = :r"
                ),
                {"r": run_id},
            )
            .mappings()
            .first()
        )
        if row is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="AuditRun")
        return RunStatusView(
            run_id=row["run_id"],
            project_uid=row["project_uid"],
            version_uid=row["version_uid"],
            state=row["state"],
            provider_mode=row["provider_mode"],
            created_at=row["created_at"],
            analysis_profile_id=row["analysis_profile_id"],
            prompt_bundle_id=row["prompt_bundle_id"],
            stages=(
                StageStateView(stage_id="source_preparation", status="succeeded"),
                StageStateView(
                    stage_id="text_analysis", status="partial", error_code="analysis_failed"
                ),
            ),
            terminal_at=row["terminal_at"],
        )

    def start_run(
        self, *, version_uid: str, provider_mode: str | None, idempotency_key: str
    ) -> RunStatusView:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="DocumentVersion")

    def get_run_status(self, *, run_id: str) -> RunStatusView:
        return self._view(run_id)


class SeamExportAdapter:
    """``CsvExportPort`` standing in for ``B5``'s use case.

    It renders no CSV. It answers with bytes for a run whose terminal publishes a
    result and refuses everything else with ``state_transition_not_allowed``, which is
    the only part of the export contract the router is responsible for observing.
    """

    #: `terminal_semantics.publishes_result` is true for exactly these two.
    EXPORTABLE = frozenset({"published", "partial"})

    def __init__(self, session: Session) -> None:
        self._session = session

    def export_run_csv(self, *, run_id: str) -> bytes:
        state = self._session.execute(
            text("SELECT state FROM audit_run WHERE run_id = :r"), {"r": run_id}
        ).scalar_one_or_none()
        if state is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="AuditRun")
        if state not in self.EXPORTABLE:
            raise DomainError(
                ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
                machine="audit_run",
                current_state=state,
                requested_state="exported",
            )
        # UTF-8 with a BOM and CRLF, per section 6. The column list is `B5`'s; this
        # stands in only far enough to prove the router adds nothing to the bytes.
        return ("﻿" + "project_uid,run_id\r\n").encode("utf-8")


@pytest.fixture
def router(ingest: IngestService, session: Session) -> Router:
    return build_router(
        projects=IngestProjectAdapter(ingest),
        documents=IngestDocumentAdapter(ingest, session),
        runs=SeamRunAdapter(session),
        findings=DatabaseFindingAdapter(session),
        decisions=LedgerDecisionAdapter(session),
        exports=SeamExportAdapter(session),
    )


# ---------------------------------------------------------------------------
# A really published run: through the gate, never a hand-written INSERT
# ---------------------------------------------------------------------------


def _text_layer_artifact() -> dict[str, Any]:
    pages = [PAGE_ONE, PAGE_TWO]
    entries = []
    cursor = 0
    for number, page in enumerate(pages, start=1):
        entries.append(
            {
                "page_number": number,
                "char_start": cursor,
                "char_end": cursor + len(page),
                "text": page,
            }
        )
        cursor += len(page)
    return {
        "artifact_role": "prepared.text_layer",
        "artifact_version": "1.0.0",
        "normalization": {"id": "nfc_v1", "description": "Unicode NFC."},
        "total_char_count": cursor,
        "pages": entries,
    }


class PublishedRun:
    """One run whose findings reached the database through the real grounding gate."""

    def __init__(self, session: Session, state: str = "created") -> None:
        self.session = session
        self.project_uid = str(ProjectUid.new())
        self.document_uid = str(DocumentUid.new())
        self.version_uid = str(VersionUid.new())
        self.run_id = str(RunId.new())
        self.analysis_profile_id = str(AnalysisProfileId.new())
        self.prompt_bundle_id = str(PromptBundleId.new())
        self.text_layer = TextLayer.from_artifact(_text_layer_artifact())
        self._seed(state)
        self.publication = self._publish()

    def _seed(self, state: str) -> None:
        digest = hashlib.sha256(self.run_id.encode("utf-8")).hexdigest()
        self.session.execute(
            text("INSERT INTO project (project_uid, name) VALUES (:p, 'Проект')"),
            {"p": self.project_uid},
        )
        self.session.execute(
            text(
                "INSERT INTO document (document_uid, project_uid, display_title) "
                "VALUES (:d, :p, 'АР')"
            ),
            {"d": self.document_uid, "p": self.project_uid},
        )
        self.session.execute(
            text(
                "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
                "media_type, byte_size, sha256, page_count) "
                "VALUES (:v, :d, 1, 'application/pdf', 1024, :s, 2)"
            ),
            {"v": self.version_uid, "d": self.document_uid, "s": digest},
        )
        self.session.execute(
            text(
                "INSERT INTO audit_run (run_id, project_uid, version_uid, state, "
                "analysis_profile_id, prompt_bundle_id, provider_mode, frozen_input_digest) "
                "VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :s)"
            ),
            {
                "r": self.run_id,
                "p": self.project_uid,
                "v": self.version_uid,
                "ap": self.analysis_profile_id,
                "pb": self.prompt_bundle_id,
                "s": digest,
            },
        )
        if state != "created":
            self._walk_to(state)

    def _walk_to(self, target: str) -> None:
        """Move the run along declared edges only.

        A test that needs a `published` run must walk `created -> queued -> running ->
        validating -> published`, because `AM001` refuses anything else. Reaching a
        terminal by writing it directly would be testing against a row the schema would
        not have allowed.
        """
        path = {
            "queued": ("queued",),
            "running": ("queued", "running"),
            "validating": ("queued", "running", "validating"),
            "published": ("queued", "running", "validating", "published"),
            "failed": ("queued", "running", "validating", "failed"),
        }[target]
        for step in path:
            terminal = step in {"published", "partial", "failed", "cancelled"}
            self.session.execute(
                text(
                    "UPDATE audit_run SET state = :s, "
                    "terminal_at = CASE WHEN :t THEN now() ELSE NULL END, "
                    "degradation_set = CASE WHEN :s = 'published' THEN '[]'::jsonb "
                    "ELSE degradation_set END "
                    "WHERE run_id = :r"
                ),
                {"s": step, "t": terminal, "r": self.run_id},
            )

    def _publish(self) -> Any:
        quote_one = "Степень огнестойкости здания — II."
        quote_two = "Степень огнестойкости здания — III."
        page_two = self.text_layer.page(2)
        assert page_two is not None
        payload = {
            "artifact_role": "analysis.text_observations",
            "artifact_version": "1.0.0",
            "run_id": self.run_id,
            "stage_id": "text_analysis",
            "analysis_profile_id": self.analysis_profile_id,
            "prompt_bundle_id": self.prompt_bundle_id,
            "provider_mode": "recorded",
            "pages_analysed": [1, 2],
            "observations": [
                {
                    "observation_ordinal": 0,
                    "category": "internal_contradiction",
                    "finding_text": "Степень огнестойкости указана по-разному.",
                    "recommendation_text": "Согласовать степень огнестойкости.",
                    "evidence": [
                        {
                            "evidence_ordinal": 0,
                            "page_number": 1,
                            "quote": quote_one,
                            "char_start": PAGE_ONE.index(quote_one),
                            "char_end": PAGE_ONE.index(quote_one) + len(quote_one),
                        },
                        {
                            "evidence_ordinal": 1,
                            "page_number": 2,
                            "quote": quote_two,
                            "char_start": page_two.char_start + PAGE_TWO.index(quote_two),
                            "char_end": page_two.char_start
                            + PAGE_TWO.index(quote_two)
                            + len(quote_two),
                        },
                    ],
                }
            ],
        }
        observations = ObservationSet.from_artifact(payload)
        gate = run_grounding_gate(
            observations=observations, text_layer=self.text_layer, block_index=None
        )
        return publish_gate_result(
            self.session,
            gate_result=gate,
            observation_set=observations,
            run_id=self.run_id,
            project_uid=self.project_uid,
            version_uid=self.version_uid,
        )

    @property
    def finding_uid(self) -> str:
        return self.publication.published[0].finding_uid

    @property
    def finding_observation_id(self) -> str:
        return self.publication.published[0].finding_observation_id


@pytest.fixture
def published_run(session: Session) -> PublishedRun:
    return PublishedRun(session)


@pytest.fixture(scope="session")
def openapi_document() -> dict[str, Any]:
    return json.loads(OPENAPI.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def validate_against_schema():
    """Evaluate a payload against one frozen schema with a real Draft 2020-12 validator.

    Drives ``tests/contract/api_v1/schema_validation_check.py`` through the governance
    interpreter -- the only one carrying ``jsonschema`` -- exactly as that suite does.
    The runtime lock has no validator and adding a root dependency is a single-owner
    task, not a lane decision.

    Fails closed: a missing governance interpreter is an error, never a skip.
    """
    if not GOVERNANCE_PYTHON.exists():
        raise AssertionError(
            f"the governance interpreter is missing at {GOVERNANCE_PYTHON}. "
            "Run: make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12"
        )

    def run(document: dict[str, Any], cases: list[dict[str, Any]]) -> dict[str, Any]:
        job = json.dumps({"document": document, "cases": cases})
        completed = subprocess.run(
            [str(GOVERNANCE_PYTHON), str(SCHEMA_CHECKER)],
            input=job,
            capture_output=True,
            text=True,
            cwd=REPOSITORY_ROOT,
        )
        if completed.returncode != 0:
            raise AssertionError(
                "the schema validation check could not be performed "
                f"(exit {completed.returncode}):\n{completed.stderr}"
            )
        return {
            result["name"]: result
            for result in json.loads(completed.stdout)["results"]
        }

    return run
