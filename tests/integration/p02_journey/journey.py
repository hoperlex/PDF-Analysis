"""Journey harness for the ``B-III`` convergence suites.

This session authored none of the modules under test and may repair none of them, so
everything here drives the composition through the owning modules' **public** surfaces:
``auditmanager.ingest`` for project and upload, ``auditmanager.runs`` for start and
execute, ``auditmanager.findings`` for what the gate published, ``auditmanager.decisions``
for the ledger, ``auditmanager.exports`` for the CSV. Where a surface does not let the
journey be driven, that is recorded as a finding rather than worked around by reaching
into a module.

**Isolation is by committed, uniquely-named data, not by rollback.** Two of the eight
journey steps -- restart, and the same sequence repeated under the same idempotency keys --
are meaningless against a transaction that is discarded at the end of the test: a restart
proves nothing if the rows never left the session, and an idempotency replay cannot be
observed if the first attempt was rolled back. So this suite commits. Every run gets a
fresh project name and fresh keys, and nothing is torn down afterwards -- ``document_version``
and ``expert_decision_event`` refuse ``DELETE`` by design, and a fixture that defeated
those guards would be defeating the properties the programme most wants kept.

Loaded by explicit path with ``importlib.util.spec_from_file_location`` from both of this
session's conftests, which is the mechanism ``tests/integration/runs`` and
``tests/contract/api_v1`` already use. It adds nothing to ``sys.path``: the root
``pyproject.toml`` states that a lane adding ``sys.path`` juggling is working around the
import contract rather than extending it.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.text import (
    AR_TEXT_PROFILE,
    AR_TEXT_PROMPT_BUNDLE,
    ProviderConfig,
    ProviderMode,
    RecordedAdapter,
)
from auditmanager.decisions import current_verdict, decision_history, record_decision
from auditmanager.exports import export_run_csv
from auditmanager.findings import published_findings
from auditmanager.ingest import IngestService
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import IdempotencyKey
from auditmanager.storage import S3BlobStore, S3StorageSettings

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CORPUS = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar"
BASELINE_PDF = CORPUS / "ar_baseline.pdf"
NEGATIVE = CORPUS / "negative"
RECORDINGS = REPOSITORY_ROOT / "fixtures" / "recorded" / "text_analysis"

#: Every base table in the P02 head. Counted before and after a replayed journey, because
#: "idempotent" is a claim about the whole schema and not about the four tables a module
#: happens to remember. ``alembic_version`` is included deliberately: a journey that
#: migrated something would show up here and nowhere else.
P02_TABLES = (
    "alembic_version",
    "audit_event",
    "audit_run",
    "blob",
    "command_record",
    "contract_state_transition",
    "document",
    "document_version",
    "expert_decision_event",
    "finding",
    "finding_evidence",
    "finding_observation",
    "input_manifest_entry",
    "model_call",
    "project",
    "stage_result",
)


def load_env_file() -> None:
    """Put this worktree's ``.env`` into the environment if it is not already there.

    ``pytest`` does not read ``.env``; the ``make`` targets do. A suite that silently
    skipped on a missing ``DATABASE_URL`` would report success having proved nothing, so
    a malformed or absent file is a hard failure here.
    """
    if os.environ.get("DATABASE_URL") and os.environ.get("S3_ENDPOINT_URL"):
        return
    path = REPOSITORY_ROOT / ".env"
    if not path.is_file():  # pragma: no cover - environment defect, not a code path
        raise RuntimeError(
            f"{path} is missing. This suite runs against real services: "
            "copy .env.example and set this session's instance."
        )
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        os.environ.setdefault(name.strip(), value.strip())


@pytest.fixture(scope="session", autouse=True)
def _environment() -> None:
    load_env_file()


@pytest.fixture(scope="session")
def engine(_environment: None) -> Iterator[Engine]:
    built = create_database_engine(
        DatabaseSettings(url=parse_database_url(os.environ["DATABASE_URL"]))
    )
    try:
        yield built.engine
    finally:
        built.engine.dispose()


@pytest.fixture(scope="session")
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


@pytest.fixture()
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """A committing session. See the module docstring for why this is not rollback-scoped."""
    with session_factory() as active:
        yield active


@pytest.fixture(scope="session")
def blob_store(_environment: None) -> S3BlobStore:
    return S3BlobStore(
        S3StorageSettings(
            endpoint_url=os.environ["S3_ENDPOINT_URL"],
            region=os.environ["S3_REGION"],
            access_key_id=os.environ["S3_ACCESS_KEY_ID"],
            secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
            bucket=os.environ["S3_BUCKET"],
        )
    )


@pytest.fixture()
def ingest(blob_store: S3BlobStore, session_factory: sessionmaker[Session]) -> IngestService:
    return IngestService(blob_store, session_factory=session_factory)


@pytest.fixture(scope="session")
def recorded_adapter() -> RecordedAdapter:
    return RecordedAdapter(RECORDINGS)


@pytest.fixture(scope="session")
def provider_config() -> ProviderConfig:
    return ProviderConfig(
        mode=ProviderMode.RECORDED,
        model_id="claude-opus-5",
        run_cost_ceiling_usd=1.0,
        api_key=None,
        ceiling_is_explicit=False,
    )


@dataclass(frozen=True)
class JourneyRecord:
    """Every identity the journey allocated, so a later step can resolve back to it."""

    project_uid: str
    document_uid: str
    version_uid: str
    run_id: str
    command_id: str
    upload_key: str
    run_key: str
    replayed_upload: bool
    replayed_run: bool
    state: str
    degradation_set: Any
    published_finding_count: int
    diagnostic_count: int
    gate_ran: bool


def table_counts(session: Session) -> dict[str, int]:
    """Row count of every P02 table, read in one statement per table by name.

    The table list is a literal above rather than a catalogue query, so that a table
    added by a future migration and never counted here shows up as a mismatch against
    ``information_schema`` in :func:`assert_table_list_is_complete` instead of silently
    dropping out of the idempotency claim.
    """
    return {name: int(session.execute(text(f"SELECT count(*) FROM {name}")).scalar_one())
            for name in P02_TABLES}


def assert_table_list_is_complete(session: Session) -> None:
    live = {
        row for row in session.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
        ).scalars()
    }
    missing = live - set(P02_TABLES)
    assert not missing, (
        f"tables exist that this suite's idempotency claim does not count: {sorted(missing)}. "
        "Add them to P02_TABLES; an uncounted table is an uncovered claim."
    )


def new_key(label: str) -> IdempotencyKey:
    return IdempotencyKey(f"b3conv-{label}-{uuid.uuid4()}")


def drive_journey(
    session: Session,
    *,
    ingest: IngestService,
    blob_store: S3BlobStore,
    adapter: Any,
    provider_config: ProviderConfig,
    project_name: str,
    upload_key: IdempotencyKey,
    run_key: IdempotencyKey,
    provider_mode: str = "recorded",
    content: bytes | None = None,
    source_filename: str = "ar_baseline.pdf",
    project_uid: str | None = None,
) -> JourneyRecord:
    """Steps 1 and 2 of the journey: project, upload, start, execute.

    ``provider_mode`` is threaded through as the caller's declared string because that is
    exactly what ``start_audit_run`` accepts; the suite uses it to attack the claim that a
    recorded run can never present itself as live.
    """
    if project_uid is None:
        project = ingest.create_project(name=project_name)
        project_uid = str(project.project_uid)

    outcome = ingest.upload_single_pdf(
        project_uid=_project_uid(project_uid),
        content=BASELINE_PDF.read_bytes() if content is None else content,
        source_filename=source_filename,
        display_title="AR baseline",
        idempotency_key=upload_key,
    )
    version = outcome.version

    started = start_audit_run(
        session,
        version_uid=str(version.version_uid),
        analysis_profile_id=str(AR_TEXT_PROFILE.analysis_profile_id),
        prompt_bundle_id=str(AR_TEXT_PROMPT_BUNDLE.prompt_bundle_id),
        provider_mode=provider_mode,
        idempotency_key=run_key,
    )
    session.commit()

    result = execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=adapter,
        provider_config=provider_config,
    )
    session.commit()

    row = session.execute(
        text("SELECT state, degradation_set FROM audit_run WHERE run_id = :r"),
        {"r": str(started.run_id)},
    ).mappings().one()

    return JourneyRecord(
        project_uid=str(project_uid),
        document_uid=str(version.document_uid),
        version_uid=str(version.version_uid),
        run_id=str(started.run_id),
        command_id=str(started.command_id),
        upload_key=str(upload_key),
        run_key=str(run_key),
        replayed_upload=bool(outcome.replayed),
        replayed_run=bool(started.replayed),
        state=row["state"],
        degradation_set=row["degradation_set"],
        published_finding_count=int(result.published_finding_count),
        diagnostic_count=int(result.diagnostic_count),
        gate_ran=bool(result.gate_ran),
    )


def _project_uid(value: str) -> Any:
    from auditmanager.shared.identity import ProjectUid

    return ProjectUid(value)


def seed_version_with_contract_manifest(session: Session, blob_store: S3BlobStore, label: str) -> dict[str, str]:
    """Publish the corpus PDF and a version whose manifest carries the CONTRACT role.

    This exists only because ``IngestService`` cannot currently produce such a version:
    it writes ``source_document`` where the frozen stage registry declares
    ``source.document``, and ``input_manifest_entry`` is immutable, so the row cannot be
    corrected afterwards either. That defect has its own dedicated test in
    ``test_manifest_role_seam.py`` and is **not** hidden by this helper -- a test that
    seeds its input here is asserting some other property, and says so.

    Every row goes through the owning module's public surface: ``S3BlobStore`` for the
    bytes, ``BlobMetadataRepository`` for the blob lifecycle, ``DocumentRepository`` for
    project, document, version and manifest.
    """
    from auditmanager.documents import DocumentRepository, ManifestEntry
    from auditmanager.storage import parse_blob_role, sha256_of
    from auditmanager.storage.blob_repository import BlobMetadataRepository
    from auditmanager.storage.models import VerifiedBlob

    payload = BASELINE_PDF.read_bytes()
    digest = sha256_of(payload)
    published = blob_store.put_blob(
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
            upload_token=f"b3conv-{label}",
            sha256=published.sha256,
            size=published.size,
            role=published.role,
            media_type=published.media_type,
        ),
    )
    blobs.mark_available(session, published.blob_id)

    documents = DocumentRepository()
    project = documents.create_project(session, f"B-III {label}")
    document_uid = documents.create_document(
        session, project_uid=project.project_uid, display_title="СП-7-АР"
    )
    version_uid = documents.publish_version(
        session,
        document_uid=document_uid,
        media_type="application/pdf",
        byte_size=len(payload),
        sha256=digest,
        page_count=8,
        source_filename="ar_baseline.pdf",
        entries=(
            ManifestEntry(
                role="source.document",
                blob_id=published.blob_id,
                sha256=published.sha256,
                size_bytes=published.size,
                media_type=published.media_type,
            ),
        ),
    )
    session.commit()
    return {
        "project_uid": str(project.project_uid),
        "document_uid": str(document_uid),
        "version_uid": str(version_uid),
    }


def run_from_seed(
    session: Session,
    seed: Mapping[str, str],
    *,
    blob_store: S3BlobStore,
    adapter: Any,
    provider_config: ProviderConfig,
    declared_provider_mode: str,
    run_key: IdempotencyKey,
) -> str:
    """Start and execute a run over a seeded version; return the run id."""
    started = start_audit_run(
        session,
        version_uid=seed["version_uid"],
        analysis_profile_id=str(AR_TEXT_PROFILE.analysis_profile_id),
        prompt_bundle_id=str(AR_TEXT_PROMPT_BUNDLE.prompt_bundle_id),
        provider_mode=declared_provider_mode,
        idempotency_key=run_key,
    )
    session.commit()
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=adapter,
        provider_config=provider_config,
    )
    session.commit()
    return str(started.run_id)
