"""PROD-11A: what an AR v3 Run leaves behind for the readers that take a version's saved text.

``optimisation/project_match.py`` (``_newest_published``) and ``optimisation/section_specification.py``
(``_read_source``) take the saved page text of the **newest published** Run of a version
(``SavedRunTextReader.saved_page_text`` in the served composition) and answer ``analysis_missing`` /
``text_unavailable`` without one. After the removal of AR v1 and v2 an AR version can start only the
AR v3 beta group (six Runs). This module is a *measurement*, not a fix: it drives that group to its
terminal state through the production worker entry point (``run_to_terminal`` -> ``execute_run``,
the pack registry installed) and then asks the real readers what they see.

What is real, what is stood in
------------------------------
* Real: PostgreSQL (a throw-away database migrated to head, dropped at the end), the S3 bucket, the
  pinned PDF extractor, the executor's three deterministic stages, ``start_ar_v3_group``, the v3
  provider-call journal, the CITE stage, ``finish_v3_review_run`` and the served composition's
  ``_SpecificationTextReader`` (the ``SavedTextReader`` of the optimisation context).
* Stood in: the **reviewed pack**. It is installed by data (``D-204``) that no code can supply, so
  the six norm sets are synthetic canonical sets seeded here, with real bytes in the bucket and real
  custody rows. The **model answer** is a recorded reply (``{"observations": []}``) written on first
  sight into a temporary recording directory and replayed by the stock ``RecordedAdapter``; the
  adapter holds no client and no credential. The text layer does not depend on either: it is produced
  by ``source_preparation`` before the provider is asked anything.

A v1 Run over the same bytes is driven first as a **control**: the same readings must say "published
and answered" for the path that works today, otherwise the instrument, not the v3 path, is at fault.

Every fact asserted below is a measured fact (the report ``docs/program/PROD-11A-V3-TEXT-LAYER-PROBE-01.md``
carries the table). A later change to the v3 path that alters one of them turns this module red.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.profiles.ar_v3.scope_partition import scope_membership
from auditmanager.analysis.public import resolve_beta_v3_profile
from auditmanager.analysis.text import CallBinding, RecordedAdapter
from auditmanager.analysis.text.recorded import recording_document
from auditmanager.bootstrap import adapters
from auditmanager.bootstrap.providers import EnvironmentProviders
from auditmanager.documents import DocumentRepository, ManifestEntry
from auditmanager.documents.models import MANIFEST_ROLE_SOURCE_DOCUMENT
from auditmanager.norms.public import SetIdentity
from auditmanager.optimisation.project_match import _newest_published
from auditmanager.optimisation.section_specification import _read_source
from auditmanager.runs import RunRepository, run_to_terminal, start_audit_run
from auditmanager.runs.provider import ProviderBinding
from auditmanager.runs.v3_group import (
    ReviewedScope,
    SCOPES,
    TrustedPack,
    TrustedPackRegistry,
    get_ar_v3_group,
    start_ar_v3_group,
)
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AuditEventId,
    IdempotencyKey,
    NormCustodyAdmissionId,
    NormCustodyBindingId,
    NormDocumentId,
    NormParagraphId,
    NormRetrievalSetId,
    ProjectUid,
)
from auditmanager.shared.identity.ids import UserUid
from auditmanager.storage import sha256_of
from auditmanager.storage.blob_repository import BlobMetadataRepository
from auditmanager.storage.models import VerifiedBlob, derive_blob_id, parse_blob_role

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BASELINE_PDF = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar" / "ar_baseline.pdf"
V1_RECORDINGS = REPOSITORY_ROOT / "fixtures" / "recorded" / "text_analysis"

PROFILE_ID = "ap_01M5M28ZCDD8VPSP1BTAEW92YE"
BUNDLE_ID = "pb_01M5M28ZCDVCR37BX1884JGSPM"
CHUNKING = "characters-v2:1200"
CONTENT_KEY = "ar-v3-probe-synthetic"
QUOTE = "Test normative paragraph."
V3_REPLY = '{"observations":[]}'
LOOPBACK = {"127.0.0.1", "::1", "localhost"}


# --- a throw-away database ---------------------------------------------------------------


def _database_url() -> str:
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail("DATABASE_URL is not set; this probe needs the lane's PostgreSQL server")
    return raw


def _drop(maintenance: Engine, name: str) -> None:
    with maintenance.connect() as connection:
        connection.execute(
            text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                 "WHERE datname = :name AND pid <> pg_backend_pid()"),
            {"name": name},
        )
        connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))


@pytest.fixture(scope="module")
def probe_database() -> Iterator[str]:
    """A fresh database migrated to head by the literal migration command; dropped afterwards."""
    base = parse_database_url(_database_url())
    maintenance = create_database_engine(
        DatabaseSettings(url=base.set(database="postgres"))
    ).execution_options(isolation_level="AUTOCOMMIT")
    name = f"{PROBE_DATABASE_PREFIX}{secrets.token_hex(6)}"
    try:
        with maintenance.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        url = base.set(database=name).render_as_string(hide_password=False)
        migrated = subprocess.run(
            [sys.executable, "-m", "alembic", "--config", "db/migrations/alembic.ini",
             "upgrade", "head"],
            cwd=REPOSITORY_ROOT, env={**os.environ, "DATABASE_URL": url},
            capture_output=True, text=True, timeout=300,
        )
        assert migrated.returncode == 0, migrated.stdout + migrated.stderr
        yield url
    finally:
        _drop(maintenance, name)
        maintenance.dispose()


# --- seeding -----------------------------------------------------------------------------


def _blob_row(session: Session, sha: str, size: int, media_type: str) -> str:
    blob_id = str(derive_blob_id(sha256=sha, size=size))
    session.execute(text("INSERT INTO blob (blob_id) VALUES (:id)"), {"id": blob_id})
    session.execute(text("UPDATE blob SET state = 'verifying' WHERE blob_id = :id"), {"id": blob_id})
    session.execute(text("""
        UPDATE blob SET state = 'available', sha256 = :sha,
            size_bytes = :size, media_type = :media WHERE blob_id = :id
    """), {"id": blob_id, "sha": sha, "size": size, "media": media_type})
    return blob_id


def _custody(
    session: Session, *, role: str, target_kind: str, target_id: str, anchor_kind: str,
    anchor: str, blob_id: str, size: int, sha: str, media_type: str,
) -> None:
    admission = str(NormCustodyAdmissionId.new())
    session.execute(text("""
        INSERT INTO norm_custody_admission
            (norm_custody_admission_id, role, target_kind, target_id, anchor_kind,
             anchor, blob_id, declared_size_bytes, declared_sha256, media_type)
        VALUES (:id, :role, :kind, :target, :anchor_kind, :anchor, :blob,
                :size, :sha, :media)
    """), {"id": admission, "role": role, "kind": target_kind, "target": target_id,
           "anchor_kind": anchor_kind, "anchor": anchor, "blob": blob_id,
           "size": size, "sha": sha, "media": media_type})
    session.execute(text("""
        UPDATE norm_custody_admission SET state = 'confirmed',
            confirmed_at = clock_timestamp(), attempt_count = 1
        WHERE norm_custody_admission_id = :id
    """), {"id": admission})
    session.execute(text("""
        INSERT INTO norm_custody_binding
            (norm_custody_binding_id, norm_custody_admission_id, role, target_kind,
             target_id, anchor_kind, anchor, blob_id)
        VALUES (:id, :admission, :role, :kind, :target, :anchor_kind, :anchor, :blob)
    """), {"id": str(NormCustodyBindingId.new()), "admission": admission, "role": role,
           "kind": target_kind, "target": target_id, "anchor_kind": anchor_kind,
           "anchor": anchor, "blob": blob_id})


@dataclass(frozen=True, slots=True)
class Source:
    project_uid: str
    document_uid: str
    version_uid: str
    blob_id: str
    sha256: str
    size: int


def _publish_source(
    session: Session, store: Any, *, title: str, register_blob: bool, actor: str
) -> Source:
    """The harness's ``seed_version`` through the same public surfaces, plus the classification.

    ``register_blob`` is false for the second version over the same bytes: the blob row of a
    content-addressed object exists once per database.
    """
    payload = BASELINE_PDF.read_bytes()
    digest = sha256_of(payload)
    published = store.put_blob(
        payload, declared_sha256=digest, declared_size=len(payload),
        role=parse_blob_role("source_document"), media_type="application/pdf",
    )
    if register_blob:
        blobs = BlobMetadataRepository()
        blobs.record_verified(session, VerifiedBlob(
            blob_id=published.blob_id, upload_token="prod-11a-probe", sha256=published.sha256,
            size=published.size, role=published.role, media_type=published.media_type,
        ))
        blobs.mark_available(session, published.blob_id)
    documents = DocumentRepository()
    project = documents.create_project(session, title)
    document_uid = documents.create_document(
        session, project_uid=project.project_uid, display_title=title, section="AR"
    )
    version_uid = documents.publish_version(
        session, document_uid=document_uid, media_type="application/pdf",
        byte_size=len(payload), sha256=digest, page_count=8, source_filename="ar_baseline.pdf",
        entries=(ManifestEntry(
            role=MANIFEST_ROLE_SOURCE_DOCUMENT, blob_id=published.blob_id,
            sha256=published.sha256, size_bytes=published.size, media_type=published.media_type,
        ),),
    )
    session.execute(text("""
        INSERT INTO document_version_classification
            (version_uid, project_stage, section_code, confirmed_by_user_uid)
        VALUES (:version, 'R', 'AR', :actor)
    """), {"version": str(version_uid), "actor": actor})
    return Source(str(project.project_uid), str(document_uid), str(version_uid),
                  str(published.blob_id), digest, len(payload))


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _set_bytes(
    *, scope_id: str, map_sha: str, snapshot: str, snapshot_digest: str,
    document_id: str, paragraph_id: str,
) -> bytes:
    """A canonical retrieval set whose prompt part carries exactly this scope's items."""
    row = dict(
        norm_document_id=document_id, norm_paragraph_id=paragraph_id,
        designation="СП 54", title="Жилые здания", ordinal=0, clause_number="7.1.4",
        page_label="1", text=QUOTE, text_sha256=hashlib.sha256(QUOTE.encode()).hexdigest(),
    )
    prompt = _canonical({
        "builder_version": "norm-ranking-prep-v1",
        "paragraphs": [dict(row, item_id=item_id, label=f"N{index}")
                       for index, item_id in enumerate(scope_membership(scope_id).item_ids, 1)],
    }).decode("utf-8")
    return _canonical({
        "builder_version": "norm-retrieval-set-prep-v1",
        "identity": {"map_sha256": map_sha, "reviewed_content_key": CONTENT_KEY,
                     "norms_snapshot_id": snapshot, "embedding_build": "bge-m3-dense-v1"},
        "snapshot_content_digest": snapshot_digest,
        "ranking_version": "norm-ranking-prep-v1", "norm_quote_version": "norm-quote-v1",
        "norm_value_version": "norm-value-v1", "prompt_part": prompt,
        "prompt_part_characters": len(prompt), "windows_per_item": 0,
        "inside_target_windows_dropped": True, "rebinding_paragraphs": [row],
    })


def _seed_norms(session: Session, store: Any, source: Source, actor: str) -> TrustedPack:
    """The norms the group start and the six verified sets need, with real set bytes in the bucket."""
    profile = resolve_beta_v3_profile(PROFILE_ID, BUNDLE_ID)
    snapshot = profile.snapshot_id
    snapshot_digest = "b" * 64
    session.execute(text("""
        INSERT INTO norms_snapshot
            (norms_snapshot_id, content_key, base_content_key, content_digest,
             undated_documents, document_count, segmentation_profile)
        VALUES (:id, :key, :key, :sha, 0, 1, 'markdown-v1')
    """), {"id": snapshot, "key": CONTENT_KEY, "sha": snapshot_digest})
    document_id, paragraph_id = str(NormDocumentId.new()), str(NormParagraphId.new())
    norm_pk = session.execute(text("""
        INSERT INTO norm_document
            (norm_document_id, norms_snapshot_id, source_document_ref, slug, title,
             doc_type, source_attribution, pdf_page_count, block_count,
             page_heading_count, recognised_characters, paragraph_count)
        VALUES (:id, :snapshot, 'synthetic-source', 'synthetic-slug', 'Synthetic standard',
                'СП', 'unattributed', 1, 1, 0, :length, 1)
        RETURNING norm_document_pk
    """), {"id": document_id, "snapshot": snapshot, "length": len(QUOTE)}).scalar_one()
    _custody(session, role="norm_source", target_kind="norm_document", target_id=document_id,
             anchor_kind="pdf", anchor="synthetic-source", blob_id=source.blob_id,
             size=source.size, sha=source.sha256, media_type="application/pdf")
    session.execute(text("""
        INSERT INTO norm_paragraph
            (norm_paragraph_id, norms_snapshot_id, norm_document_pk, ordinal,
             page_label, block_ref, char_offset, char_length, kind, text)
        VALUES (:id, :snapshot, :document, 0, 1, 'synthetic-block', 0, :length, 'body', :quote)
    """), {"id": paragraph_id, "snapshot": snapshot, "document": norm_pk,
           "length": len(QUOTE), "quote": QUOTE})
    session.execute(text("""
        INSERT INTO norm_chunk_build (norms_snapshot_id, chunking_profile, target_characters, chunk_count)
        VALUES (:snapshot, :chunking, 1200, 1)
    """), {"snapshot": snapshot, "chunking": CHUNKING})
    chunk_pk = session.execute(text("""
        INSERT INTO norm_chunk
            (norms_snapshot_id, norm_document_pk, chunking_profile, ordinal,
             page_first, page_last, char_offset, char_length,
             paragraph_ordinal_first, paragraph_ordinal_last, paragraph_count,
             contains_clause, text, content_sha256)
        VALUES (:snapshot, :document, :chunking, 0, 1, 1, 0, :length, 0, 0, 1,
                false, :quote, :sha)
        RETURNING norm_chunk_pk
    """), {"snapshot": snapshot, "document": norm_pk, "chunking": CHUNKING,
           "length": len(QUOTE), "quote": QUOTE, "sha": "c" * 64}).scalar_one()
    session.execute(text("""
        INSERT INTO norm_embedding_build
            (norms_snapshot_id, chunking_profile, embedding_profile,
             chunk_count, window_count, embedding_set_sha256)
        VALUES (:snapshot, :chunking, 'bge-m3-dense-v1', 1, 1, :sha)
    """), {"snapshot": snapshot, "chunking": CHUNKING, "sha": "d" * 64})
    session.execute(text("""
        INSERT INTO norm_embedding
            (norms_snapshot_id, norm_chunk_pk, chunking_profile, embedding_profile,
             window_ordinal, token_count, char_offset, char_length,
             paragraph_ordinal_first, paragraph_ordinal_last, input_sha256,
             embedding_sha256, embedding)
        VALUES (:snapshot, :chunk, :chunking, 'bge-m3-dense-v1', 0, 10, 0, :length,
                0, 0, :input, :embedding_sha, ('[1,' || repeat('0,', 1022) || '0]')::vector)
    """), {"snapshot": snapshot, "chunk": chunk_pk, "chunking": CHUNKING,
           "length": len(QUOTE), "input": "e" * 64, "embedding_sha": "f" * 64})
    event = str(AuditEventId.new())
    session.execute(text("""
        INSERT INTO norm_current_snapshot_event (event_id, from_snapshot_id, to_snapshot_id, actor_user_uid)
        VALUES (:event, NULL, :snapshot, :actor)
    """), {"event": event, "snapshot": snapshot, "actor": actor})
    session.execute(text("""
        INSERT INTO norm_current_snapshot (norms_snapshot_id, event_id) VALUES (:snapshot, :event)
    """), {"snapshot": snapshot, "event": event})

    catalogue = _canonical({"probe": "synthetic catalogue"})
    catalogue_sha = hashlib.sha256(catalogue).hexdigest()
    published = store.put_blob(
        catalogue, declared_sha256=catalogue_sha, declared_size=len(catalogue),
        role=parse_blob_role("norm_catalogue"), media_type="application/json",
    )
    assert str(published.blob_id) == str(derive_blob_id(sha256=catalogue_sha, size=len(catalogue)))
    catalogue_blob = _blob_row(session, catalogue_sha, len(catalogue), "application/json")
    scopes = []
    for index, scope_id in enumerate(profile.scopes, 1):
        map_sha = f"{index:x}" * 64
        raw = _set_bytes(scope_id=scope_id, map_sha=map_sha, snapshot=snapshot,
                         snapshot_digest=snapshot_digest, document_id=document_id,
                         paragraph_id=paragraph_id)
        set_sha = hashlib.sha256(raw).hexdigest()
        stored = store.put_blob(
            raw, declared_sha256=set_sha, declared_size=len(raw),
            role=parse_blob_role("norm_retrieval_set"), media_type="application/json",
        )
        assert str(stored.blob_id) == str(derive_blob_id(sha256=set_sha, size=len(raw)))
        set_blob = _blob_row(session, set_sha, len(raw), "application/json")
        prompt_characters = json.loads(raw)["prompt_part_characters"]
        set_id = str(NormRetrievalSetId.new())
        session.execute(text("""
            INSERT INTO norm_retrieval_set
                (norm_retrieval_set_id, norms_snapshot_id, map_sha256,
                 reviewed_content_key, chunking_profile, embedding_profile,
                 builder_version, state, expected_set_sha256, observed_set_sha256,
                 expected_catalogue_sha256, observed_catalogue_sha256,
                 set_blob_id, set_size_bytes, catalogue_blob_id,
                 catalogue_size_bytes, prompt_part_characters)
            VALUES (:id, :snapshot, :map, :key, :chunking, 'bge-m3-dense-v1',
                    'norm-retrieval-set-prep-v1', 'verified', :set_sha, :set_sha,
                    :catalogue_sha, :catalogue_sha, :set_blob, :set_size,
                    :catalogue_blob, :catalogue_size, :prompt_characters)
        """), {"id": set_id, "snapshot": snapshot, "map": map_sha, "key": CONTENT_KEY,
               "chunking": CHUNKING, "set_sha": set_sha, "catalogue_sha": catalogue_sha,
               "set_blob": set_blob, "set_size": len(raw), "catalogue_blob": catalogue_blob,
               "catalogue_size": len(catalogue), "prompt_characters": prompt_characters})
        for role, blob, sha, size in (
            ("norm_retrieval_set", set_blob, set_sha, len(raw)),
            ("norm_catalogue", catalogue_blob, catalogue_sha, len(catalogue)),
        ):
            _custody(session, role=role, target_kind="norm_retrieval_set", target_id=set_id,
                     anchor_kind="artifact", anchor=role, blob_id=blob, size=size, sha=sha,
                     media_type="application/json")
        scopes.append(ReviewedScope(
            scope_id=scope_id,
            identity=SetIdentity(map_sha256=map_sha, snapshot_id=snapshot,
                                 reviewed_content_key=CONTENT_KEY,
                                 embedding_build=f"bge-m3-dense-v1:{CHUNKING}"),
            chunking_profile=CHUNKING, set_id=set_id, set_sha256=set_sha,
        ))
    return TrustedPack(str(profile.analysis_profile_id), str(profile.prompt_bundle_id), tuple(scopes))


# --- the recorded model, stood in for only by a reply written on first sight -------------


class _RecordOnFirstSight(RecordedAdapter):
    """The stock recorded replay over a temporary directory, filled with one reply per request key.

    ``RecordedAdapter.complete`` is untouched: the file is written *before* it is called, so the
    answer still goes through the keyed lookup, the version, key and model checks of the replay.
    """

    def __init__(self, directory: Path, output_text: str) -> None:
        super().__init__(directory)
        self._reply = output_text
        self.requests: list[str] = []

    def complete(self, request: Any) -> Any:
        path = self.path_for(request.request_sha256)
        if not path.is_file():
            path.write_text(json.dumps(recording_document(
                request=request, output_text=self._reply, stop_reason="end_turn",
                input_tokens=100, output_tokens=10, latency_ms=1,
                note="PROD-11A probe: synthetic empty reply, not a model answer",
            )), encoding="utf-8")
        self.requests.append(request.request_sha256)
        return super().complete(request)


# --- the readings ------------------------------------------------------------------------


@dataclass(slots=True)
class RunReading:
    label: str
    run_id: str
    scope_id: str | None
    state: str
    terminal_reason: str | None
    error: str | None
    stage_statuses: dict[str, str]
    bound_artifact_roles: dict[str, list[str]]
    text_layer_reference_sha256: str | None
    saved_page_text_answers: bool
    saved_page_text_sha256: str | None
    saved_page_text_pages: int | None
    saved_page_text_error: str | None


@dataclass(slots=True)
class VersionReading:
    label: str
    version_uid: str
    page_count: int
    newest_published: str | None
    source_state: str
    source_run_id: str | None
    source_text_layer_sha256: str | None
    source_row_count: int | None
    source_table_count: int | None


@dataclass(slots=True)
class GroupMeasurement:
    """One six-Run group on its own version, and the readers' answers about that version."""

    binding: str
    scopes: tuple[str, ...]
    runs: list[RunReading]
    version: VersionReading
    recorded_requests: int


@dataclass(slots=True)
class Measurement:
    groups: dict[str, GroupMeasurement] = field(default_factory=dict)
    v1_run: RunReading | None = None
    v1_version: VersionReading | None = None
    peers: list[str] = field(default_factory=list)
    stage_check_before: str = ""
    stage_check_after: str = ""


def _reading(session: Session, store: Any, reader: Any, version: Source, run_id: str, *,
             label: str, scope_id: str | None, error: str | None) -> RunReading:
    runs = RunRepository()
    row = runs.get(session, run_id)
    stages = runs.stage_results(session, run_id)
    references = [
        dict(a) for stage in stages if stage.stage_id == "source_preparation"
        for a in stage.artifacts if "text_layer" in str(a.get("role"))
    ]
    bound: dict[str, list[str]] = {}
    for stage_id, role in session.execute(text("""
        SELECT stage_id, artifact_role FROM analysis_artifact_publication
         WHERE run_id = :run AND state = 'bound' ORDER BY stage_id, artifact_role
    """), {"run": run_id}).all():
        bound.setdefault(stage_id, []).append(role)
    answers, sha, pages, failure = False, None, None, None
    try:
        saved = reader.saved_page_text(session, run_id=run_id, version_uid=version.version_uid,
                                       page_count=8)
        if saved is not None:
            answers, sha, pages = True, saved.text_layer_sha256, len(saved.pages)
    except Exception as exc:  # recorded as a reading, never swallowed: it is the measurement
        failure = f"{type(exc).__name__}: {exc}"
    return RunReading(
        label=label, run_id=run_id, scope_id=scope_id, state=row.state,
        terminal_reason=row.terminal_reason, error=error,
        stage_statuses={s.stage_id: s.status for s in stages},
        bound_artifact_roles=bound,
        text_layer_reference_sha256=(references[0].get("sha256") if references else None),
        saved_page_text_answers=answers, saved_page_text_sha256=sha,
        saved_page_text_pages=pages, saved_page_text_error=failure,
    )


def _version_reading(session: Session, reader: Any, source: Source, label: str) -> VersionReading:
    record = next(
        item for item in DocumentRepository().list_current_versions_in_section(
            session, section_code="AR", project_uid=ProjectUid.parse(source.project_uid))
        if str(item.version_uid) == source.version_uid
    )
    newest = _newest_published(reader, session, source.version_uid)
    section_source, rows, _ = _read_source(session, reader, record, None)
    return VersionReading(
        label=label, version_uid=source.version_uid, page_count=record.page_count,
        newest_published=newest, source_state=section_source.state,
        source_run_id=section_source.run_id,
        source_text_layer_sha256=section_source.text_layer_sha256,
        source_row_count=len(rows) if section_source.state == "ready" else None,
        source_table_count=getattr(section_source, "table_count", None),
    )




# --- the drive ---------------------------------------------------------------------------

SERVED_RECORDED = "served recorded composition"
UNMETERED_RECORDED = "recorded replay, call marked unmetered"
WHAT_IF = "what-if: unmetered replay, stage CHECK widened in the throw-away database"
CITE_STAGE = "ar_v3_citation_review"
STAGE_CHECK = "ck_stage_result_stage_id"
PROBE_DATABASE_PREFIX = "prod11a_probe_"


def _unmetered(adapter: Any, config: Any) -> Any:
    """A binding like the ``database`` source's ``billing = not_metered``: nothing is charged."""

    def resolve(session: Session, run: Any, context: Any) -> ProviderBinding:
        return ProviderBinding(adapter=adapter, config=config, call=CallBinding(unmetered=True))

    return resolve


def _stage_check(session: Session) -> str:
    return session.execute(text(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :name"
        " AND conrelid = 'stage_result'::regclass"
    ), {"name": STAGE_CHECK}).scalar_one()


def _widen_stage_check(session: Session) -> None:
    """What-if only: admit the tenth stage id in the *throw-away* database, then nothing else."""
    name = session.execute(text("SELECT current_database()")).scalar_one()
    _require_probe_database(name)
    admitted = re.findall(r"'([a-z0-9_]+)'::text", _stage_check(session))
    if CITE_STAGE in admitted:
        return  # a migration has since admitted it: fact 1 turns red, there is nothing to widen
    assert len(admitted) == 9, admitted
    listed = ", ".join(f"'{stage}'::text" for stage in (*admitted, CITE_STAGE))
    session.execute(text(f"ALTER TABLE stage_result DROP CONSTRAINT {STAGE_CHECK}"))
    session.execute(text(
        f"ALTER TABLE stage_result ADD CONSTRAINT {STAGE_CHECK} "
        f"CHECK (stage_id = ANY (ARRAY[{listed}]))"
    ))


def _require_probe_database(name: str) -> None:
    if not name.startswith(PROBE_DATABASE_PREFIX):
        raise AssertionError(f"refusing to alter {name!r}: not a throw-away probe database")


def _require_loopback(peers: list[str]) -> None:
    outside = sorted({peer for peer in peers if peer not in LOOPBACK})
    if outside:
        raise AssertionError(f"the probe contacted a non-loopback peer: {outside}")


def _drive_group(
    factory: Any, store: Any, config: Any, recordings: Path, source: Source, pack: TrustedPack,
    reader: Any, *, binding: str, key: str,
) -> GroupMeasurement:
    with factory() as session, session.begin():
        group = start_ar_v3_group(
            session, version_uid=source.version_uid, idempotency_key=key,
            provider_mode="recorded", pack=pack, input_budget_characters=1_000_000,
        ).group
    registry = TrustedPackRegistry("ar-v3-beta-reviewed-pack-registry/1", (pack,))
    adapter = _RecordOnFirstSight(recordings, V3_REPLY)
    # The served composition for ``provider_mode == "recorded"`` hands every run
    # ``EnvironmentProviders(RecordedAdapter(), config, call=None)`` (bootstrap/composition.py).
    providers = (EnvironmentProviders(adapter, config, None).resolve
                 if binding == SERVED_RECORDED else _unmetered(adapter, config))
    errors: dict[str, str | None] = {}
    for member in group.members:
        try:
            run_to_terminal(factory, member.run_id, blob_store=store, adapter=adapter,
                            provider_config=config, providers=providers,
                            ar_v3_pack_registry=registry)
            errors[member.run_id] = None
        except Exception as exc:  # a reading, not a swallowed fault
            errors[member.run_id] = f"{type(exc).__name__}: {exc} <- {exc.__cause__!r}"[:600]
    with factory() as session:
        runs = [
            _reading(session, store, reader, source, member.run_id,
                     label=f"{binding} / {member.scope_id}", scope_id=member.scope_id,
                     error=errors[member.run_id])
            for member in group.members
        ]
        version = _version_reading(session, reader, source, binding)
        assert get_ar_v3_group(session, group.group_id).members  # the group is still readable
    return GroupMeasurement(
        binding=binding, scopes=tuple(member.scope_id for member in group.members),
        runs=runs, version=version, recorded_requests=len(adapter.requests),
    )


def _drive(probe_database: str, store: Any, config: Any, recordings: Path) -> Measurement:
    out = Measurement()
    engine = create_database_engine(DatabaseSettings(url=parse_database_url(probe_database)))
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    patch = pytest.MonkeyPatch()
    real_connect = socket.socket.connect

    def spy(self: socket.socket, address: Any, *args: Any, **kwargs: Any) -> Any:
        out.peers.append(str(address[0]) if isinstance(address, tuple) else str(address))
        return real_connect(self, address, *args, **kwargs)

    patch.setattr(socket.socket, "connect", spy)
    try:
        actor = str(UserUid.new())
        with factory() as session, session.begin():
            session.execute(text("""
                INSERT INTO app_user (user_uid, login, password_algorithm,
                    password_iterations, password_salt, password_hash)
                VALUES (:id, :login, 'pbkdf2_sha256', 100000, :salt, :hash)
            """), {"id": actor, "login": actor.lower(), "salt": "0" * 32, "hash": "0" * 64})
            served = _publish_source(session, store, title="AR v3 served recorded",
                                     register_blob=True, actor=actor)
            unmetered = _publish_source(session, store, title="AR v3 unmetered recorded",
                                        register_blob=False, actor=actor)
            what_if = _publish_source(session, store, title="AR v3 what-if",
                                      register_blob=False, actor=actor)
            control = _publish_source(session, store, title="AR v1 control",
                                      register_blob=False, actor=actor)

        # Control: the v1 path that works today, over the same bytes, before any norm exists.
        with factory() as session, session.begin():
            started = start_audit_run(
                session, version_uid=control.version_uid,
                analysis_profile_id="ap_01M5M28ZCDD8VPSP1BTAEW92YF",
                prompt_bundle_id="pb_01M5M28ZCDVCR37BX1884JGSPN",
                provider_mode="recorded", idempotency_key=IdempotencyKey("prod11a-control-v1"),
            )
        v1_error = None
        try:
            run_to_terminal(factory, started.run_id, blob_store=store,
                            adapter=RecordedAdapter(V1_RECORDINGS), provider_config=config)
        except Exception as exc:  # a reading, not a swallowed fault
            v1_error = f"{type(exc).__name__}: {exc}"

        with factory() as session, session.begin():
            pack = _seed_norms(session, store, served, actor)
        reader = adapters._SpecificationTextReader(store)
        out.groups[SERVED_RECORDED] = _drive_group(
            factory, store, config, recordings, served, pack, reader,
            binding=SERVED_RECORDED, key="prod11a-probe-served")
        out.groups[UNMETERED_RECORDED] = _drive_group(
            factory, store, config, recordings, unmetered, pack, reader,
            binding=UNMETERED_RECORDED, key="prod11a-probe-unmetered")
        with factory() as session:
            out.stage_check_before = _stage_check(session)
        with factory() as session, session.begin():
            _widen_stage_check(session)
        with factory() as session:
            out.stage_check_after = _stage_check(session)
        out.groups[WHAT_IF] = _drive_group(
            factory, store, config, recordings, what_if, pack, reader,
            binding=WHAT_IF, key="prod11a-probe-what-if")
        with factory() as session:
            out.v1_run = _reading(session, store, reader, control, started.run_id,
                                  label="v1 control", scope_id=None, error=v1_error)
            out.v1_version = _version_reading(session, reader, control, "v1 control")
    finally:
        patch.undo()
        engine.dispose()
    return out


def _plain(item: Any) -> Any:
    if item is None or isinstance(item, (str, int, float, bool)):
        return item
    if isinstance(item, dict):
        return {key: _plain(value) for key, value in item.items()}
    if isinstance(item, (list, tuple)):
        return [_plain(value) for value in item]
    return {name: _plain(getattr(item, name)) for name in item.__slots__}


@pytest.fixture(scope="module")
def measured(probe_database: str, blob_store: Any, provider_config: Any,
             tmp_path_factory: pytest.TempPathFactory) -> Measurement:
    recordings = tmp_path_factory.mktemp("prod11a-recordings")
    result = _drive(probe_database, blob_store, provider_config, recordings)
    print("PROD11A-MEASUREMENT " + json.dumps(_plain(result), ensure_ascii=False, sort_keys=True))
    return result


# --- the measured facts ------------------------------------------------------------------

REAL_SCHEMA = (SERVED_RECORDED, UNMETERED_RECORDED)
TEXT_LAYER_ROLE = "prepared.text_layer"
DETERMINISTIC = {
    "source_preparation": "succeeded",
    "page_geometry_extraction": "succeeded",
    "document_context_build": "succeeded",
}


def test_the_migrated_schema_does_not_admit_the_cite_stage(measured: Measurement) -> None:
    """Fact 1. ``stage_result`` is checked against nine stage ids; ``ar_v3_citation_review`` is not one.

    The contract seal (``AR-V3-BETA-RUN-STAGE-SEAL-01``) added the tenth id to the API vocabulary and
    no migration widened ``ck_stage_result_stage_id`` (head ``0032_ar_v3_run_group``).
    """
    admitted = re.findall(r"'([a-z0-9_]+)'::text", measured.stage_check_before)
    assert len(admitted) == 9
    assert CITE_STAGE not in admitted
    # The instrument: the what-if step really changed the constraint and nothing else about it.
    widened = re.findall(r"'([a-z0-9_]+)'::text", measured.stage_check_after)
    assert widened == [*admitted, CITE_STAGE]


@pytest.mark.parametrize("binding", REAL_SCHEMA)
def test_every_provider_request_was_answered_before_the_run_failed(
    measured: Measurement, binding: str
) -> None:
    """Fact 2. The six Runs of each group reached the provider seam once each (replayed reply),
    so the failures below are not failures to start, to read the text or to build the request."""
    group = measured.groups[binding]
    assert group.scopes == SCOPES
    assert group.recorded_requests == 6
    assert [run.stage_statuses for run in group.runs] == [DETERMINISTIC] * 6


def test_the_served_recorded_composition_refuses_every_run_on_cost(measured: Measurement) -> None:
    """Fact 3. ``EnvironmentProviders(RecordedAdapter, config, call=None)``: a replayed reply carries
    no cost and the call is not marked unmetered, so ``_check_completed_cost`` refuses before CITE."""
    for run in measured.groups[SERVED_RECORDED].runs:
        assert (run.state, run.terminal_reason) == ("failed", "analysis_input_invalid")
        assert run.error is not None and "no verifiable cost amount" in run.error


def test_an_unmetered_call_is_refused_at_the_cite_stage_row(measured: Measurement) -> None:
    """Fact 4. With the cost seam satisfied (an unmetered binding) every Run fails writing its CITE
    ``stage_result`` row: ``ck_stage_result_stage_id`` refuses ``ar_v3_citation_review``."""
    for run in measured.groups[UNMETERED_RECORDED].runs:
        assert (run.state, run.terminal_reason) == ("failed", "internal_error")
        assert run.error is not None and STAGE_CHECK in run.error
        assert CITE_STAGE not in run.stage_statuses


def test_no_v3_run_is_published_on_the_migrated_schema(measured: Measurement) -> None:
    """Fact 5, the answer to the first question: on the schema at head no v3 Run is ``published``."""
    states = [run.state for binding in REAL_SCHEMA for run in measured.groups[binding].runs]
    assert states == ["failed"] * 12


@pytest.mark.parametrize("binding", [*REAL_SCHEMA, WHAT_IF])
def test_every_v3_run_leaves_the_saved_text_layer_whatever_its_terminal(
    measured: Measurement, binding: str
) -> None:
    """Fact 6, the answer to the second question: ``source_preparation`` is the executor's own
    deterministic stage, it runs before the v3 branch, and the reader that production uses
    (``_SpecificationTextReader``) returns the verified layer of every Run, failed ones included."""
    for run in measured.groups[binding].runs:
        assert run.stage_statuses["source_preparation"] == "succeeded"
        assert TEXT_LAYER_ROLE in run.bound_artifact_roles["source_preparation"]
        assert run.text_layer_reference_sha256 is not None
        assert run.saved_page_text_error is None
        assert run.saved_page_text_answers is True
        assert run.saved_page_text_pages == group_page_count(measured, binding)
        assert run.saved_page_text_sha256 == run.text_layer_reference_sha256


def group_page_count(measured: Measurement, binding: str) -> int:
    return measured.groups[binding].version.page_count


@pytest.mark.parametrize("binding", REAL_SCHEMA)
def test_the_readers_find_no_published_run_of_an_unpublished_v3_group(
    measured: Measurement, binding: str
) -> None:
    """Fact 7. Because no Run is published, ``_newest_published`` is ``None`` and ``_read_source``
    answers ``analysis_missing``, although the layer is saved (fact 6): the state, not the layer,
    is what is missing."""
    version = measured.groups[binding].version
    assert version.newest_published is None
    assert version.source_state == "analysis_missing"
    assert version.source_run_id is None
    assert version.source_text_layer_sha256 is None


def test_the_v1_control_is_published_and_the_same_readers_answer(measured: Measurement) -> None:
    """Fact 8, the instrument check: the path that works today, read the same way."""
    run, version = measured.v1_run, measured.v1_version
    assert run is not None and version is not None
    assert (run.state, run.terminal_reason, run.error) == ("published", None, None)
    assert version.newest_published == run.run_id == version.source_run_id
    assert version.source_state == "ready"
    assert version.source_text_layer_sha256 == run.saved_page_text_sha256
    assert run.saved_page_text_pages == version.page_count


def test_with_the_stage_check_widened_all_six_publish_and_the_readers_answer(
    measured: Measurement,
) -> None:
    """Fact 9, the what-if: in the throw-away database, with only the constraint widened, the same
    drive publishes all six Runs and the readers answer ``ready``. Nothing else blocks (in this
    setting); the widening itself is a migration this lane does not write."""
    group = measured.groups[WHAT_IF]
    assert [(run.state, run.terminal_reason, run.error) for run in group.runs] == [
        ("published", None, None)
    ] * 6
    assert [run.stage_statuses.get(CITE_STAGE) for run in group.runs] == ["succeeded"] * 6
    version = group.version
    published = {run.run_id: run for run in group.runs}
    assert version.newest_published in published
    assert version.source_run_id == version.newest_published
    assert version.source_state == "ready"
    assert version.source_text_layer_sha256 == published[version.newest_published].saved_page_text_sha256


def test_the_probe_stayed_on_the_loopback(measured: Measurement) -> None:
    """The recorded adapter has no client; the Python-level connections that were opened (the
    pooled bucket connection may be reused and so not appear) were loopback only."""
    _require_loopback(measured.peers)


def test_the_guards_of_the_probe_can_fail() -> None:
    with pytest.raises(AssertionError, match="throw-away"):
        _require_probe_database("auditmanager_ar_close")
    _require_probe_database(f"{PROBE_DATABASE_PREFIX}abc")
    with pytest.raises(AssertionError, match="non-loopback"):
        _require_loopback(["127.0.0.1", "203.0.113.7"])
    _require_loopback(["127.0.0.1", "::1"])
