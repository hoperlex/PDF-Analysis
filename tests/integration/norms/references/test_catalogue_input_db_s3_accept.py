"""Accept the unserved catalogue reader against real 0023 PostgreSQL and S3."""

from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import replace
from pathlib import Path

import boto3
import pytest
from botocore.client import Config
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.jobs.public import JobRepository
from auditmanager.norms.references.catalogue_input import load_verified_catalogue
from auditmanager.norms.references.catalogue_query import load_pinned_catalogue
from auditmanager.norms.references.tokens import sql_designation_tokens
from auditmanager.norms.retrieval.artifact import SnapshotBinding
from auditmanager.norms.retrieval.catalogue import CatalogueDocument, build_catalogue
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    AnalysisProfileId, AttemptId, DocumentUid, NormCustodyAdmissionId,
    NormCustodyBindingId, NormDocumentId, NormParagraphId, NormRetrievalSetId,
    NormsSnapshotId, ProjectUid, PromptBundleId, RunId, VersionUid,
)
from auditmanager.storage.public import (
    BlobMetadataRepository, S3BlobStore, S3StorageSettings, parse_blob_role,
)
from auditmanager.storage.models import VerifiedBlob


ROOT = Path(__file__).resolve().parents[4]
QUOTE = "Требуемая ширина пути эвакуации составляет 1,2 м."
CONTENT_DIGEST = "a" * 64


class _NoObjectRead:
    def open_stream(self, *args, **kwargs):
        raise AssertionError("stale authority reached S3")


def _load_lane_env() -> None:
    """Read literal, ignored lane settings without overriding exported values."""
    path = ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        name, separator, raw = line.strip().partition("=")
        if separator and name in {"DATABASE_URL", "S3_ENDPOINT_URL", "S3_REGION",
                                  "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_BUCKET"}:
            os.environ.setdefault(name, raw.strip().strip("\"'"))


def _publish(session: Session, store: S3BlobStore, payload: bytes, role: str) -> VerifiedBlob:
    sha = hashlib.sha256(payload).hexdigest()
    published = store.put_blob(
        payload, declared_sha256=sha, declared_size=len(payload),
        role=parse_blob_role(role), media_type="application/json",
    )
    verified = VerifiedBlob(
        blob_id=published.blob_id, upload_token=f"w57b-catalogue-{role}",
        sha256=published.sha256, size=published.size, role=published.role,
        media_type=published.media_type,
    )
    metadata = BlobMetadataRepository()
    metadata.record_verified(session, verified)
    metadata.mark_available(session, published.blob_id)
    return verified


def _seed_snapshot_and_build(session: Session, snapshot: str, document: str, key: str) -> None:
    session.execute(text(
        "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, "
        "content_digest, undated_documents, document_count, segmentation_profile) "
        "VALUES (:snapshot, :key, :key, :digest, 0, 1, 'markdown-v1')"
    ), {"snapshot": snapshot, "key": key, "digest": CONTENT_DIGEST})
    document_pk = session.execute(text(
        "INSERT INTO norm_document (norm_document_id, norms_snapshot_id, "
        "source_document_ref, slug, title, doc_type, source_attribution, "
        "pdf_page_count, block_count, page_heading_count, recognised_characters, "
        "paragraph_count) VALUES (:document, :snapshot, 'synthetic-source', "
        "'СП_54.13330.2022', 'Residential buildings', 'СП', 'unattributed', "
        "1, 1, 0, :length, 1) RETURNING norm_document_pk"
    ), {"document": document, "snapshot": snapshot, "length": len(QUOTE)}).scalar_one()
    session.execute(text(
        "INSERT INTO norm_paragraph (norm_paragraph_id, norms_snapshot_id, "
        "norm_document_pk, ordinal, page_label, block_ref, char_offset, char_length, "
        "kind, text) VALUES (:paragraph, :snapshot, :pk, 0, 1, 'block-1', "
        "0, :length, 'body', :quote)"
    ), {"paragraph": str(NormParagraphId.new()), "snapshot": snapshot,
        "pk": document_pk, "length": len(QUOTE), "quote": QUOTE})
    session.execute(text(
        "INSERT INTO norm_chunk_build (norms_snapshot_id, chunking_profile, "
        "target_characters, chunk_count) VALUES (:snapshot, 'reliable-v1-1200', 1200, 1)"
    ), {"snapshot": snapshot})
    chunk_pk = session.execute(text(
        "INSERT INTO norm_chunk (norms_snapshot_id, norm_document_pk, "
        "chunking_profile, ordinal, page_first, page_last, char_offset, char_length, "
        "paragraph_ordinal_first, paragraph_ordinal_last, paragraph_count, "
        "contains_clause, text, content_sha256) VALUES (:snapshot, :pk, "
        "'reliable-v1-1200', 0, 1, 1, 0, :length, 0, 0, 1, false, :quote, :sha) "
        "RETURNING norm_chunk_pk"
    ), {"snapshot": snapshot, "pk": document_pk, "length": len(QUOTE),
        "quote": QUOTE, "sha": "b" * 64}).scalar_one()
    session.execute(text(
        "INSERT INTO norm_embedding_build (norms_snapshot_id, chunking_profile, "
        "embedding_profile, chunk_count, window_count, embedding_set_sha256) "
        "VALUES (:snapshot, 'reliable-v1-1200', 'bge-m3-dense-v1', 1, 1, :sha)"
    ), {"snapshot": snapshot, "sha": "b" * 64})
    session.execute(text(
        "INSERT INTO norm_embedding (norms_snapshot_id, norm_chunk_pk, "
        "chunking_profile, embedding_profile, window_ordinal, token_count, "
        "char_offset, char_length, paragraph_ordinal_first, paragraph_ordinal_last, "
        "input_sha256, embedding_sha256, embedding) VALUES (:snapshot, :chunk, "
        "'reliable-v1-1200', 'bge-m3-dense-v1', 0, 10, 0, :length, 0, 0, "
        ":input_sha, :embedding_sha, ('[1,' || repeat('0,', 1022) || '0]')::vector)"
    ), {"snapshot": snapshot, "chunk": chunk_pk, "length": len(QUOTE),
        "input_sha": "c" * 64, "embedding_sha": "d" * 64})


def _bind(session: Session, set_id: str, role: str, blob: VerifiedBlob) -> None:
    admission = str(NormCustodyAdmissionId.new())
    session.execute(text(
        "INSERT INTO norm_custody_admission (norm_custody_admission_id, role, "
        "target_kind, target_id, anchor_kind, anchor, blob_id, "
        "declared_size_bytes, declared_sha256, media_type) VALUES "
        "(:admission, :role, 'norm_retrieval_set', :set_id, 'artifact', :role, "
        ":blob, :size, :sha, 'application/json')"
    ), {"admission": admission, "role": role, "set_id": set_id,
        "blob": str(blob.blob_id), "size": blob.size, "sha": blob.sha256})
    session.execute(text(
        "UPDATE norm_custody_admission SET state = 'confirmed', "
        "confirmed_at = clock_timestamp(), attempt_count = 1 "
        "WHERE norm_custody_admission_id = :admission"
    ), {"admission": admission})
    session.execute(text(
        "INSERT INTO norm_custody_binding (norm_custody_binding_id, "
        "norm_custody_admission_id, role, target_kind, target_id, anchor_kind, "
        "anchor, blob_id) VALUES (:binding, :admission, :role, "
        "'norm_retrieval_set', :set_id, 'artifact', :role, :blob)"
    ), {"binding": str(NormCustodyBindingId.new()), "admission": admission,
        "role": role, "set_id": set_id, "blob": str(blob.blob_id)})


def test_verified_catalogue_reads_exact_s3_bytes_for_current_attempt() -> None:
    _load_lane_env()
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail("DATABASE_URL is required for real PostgreSQL acceptance")
    settings = S3StorageSettings.from_env()
    engine = create_database_engine(DatabaseSettings(url=parse_database_url(raw)))
    s3 = boto3.client(
        "s3", endpoint_url=settings.endpoint_url, region_name=settings.region,
        aws_access_key_id=settings.access_key_id,
        aws_secret_access_key=settings.secret_access_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    bucket = f"{settings.bucket[:35]}-{secrets.token_hex(6)}"
    s3.create_bucket(Bucket=bucket)
    store = S3BlobStore(replace(settings, bucket=bucket))
    try:
        with engine.connect() as connection, connection.begin():
            assert connection.execute(text(
                "SELECT version_num FROM alembic_version"
            )).scalar_one() == "0023_norm_citations"
            session = Session(bind=connection)
            snapshot, document, set_id = (
                str(NormsSnapshotId.new()), str(NormDocumentId.new()),
                str(NormRetrievalSetId.new()),
            )
            key = f"synthetic-{snapshot}"
            _seed_snapshot_and_build(session, snapshot, document, key)
            catalogue = build_catalogue(
                snapshot=SnapshotBinding(snapshot, key, CONTENT_DIGEST, "bge-build", 1),
                documents=(CatalogueDocument(
                    document, "СП_54.13330.2022",
                    sql_designation_tokens("СП_54.13330.2022"),
                    "Residential buildings", "СП",
                ),),
            )
            set_blob = _publish(session, store, b'{"verified":true}', "norm_retrieval_set")
            cat_blob = _publish(session, store, catalogue.data, "norm_catalogue")
            session.execute(text(
                "INSERT INTO norm_retrieval_set (norm_retrieval_set_id, "
                "norms_snapshot_id, map_sha256, reviewed_content_key, "
                "chunking_profile, embedding_profile, builder_version, state, "
                "expected_set_sha256, observed_set_sha256, "
                "expected_catalogue_sha256, observed_catalogue_sha256, "
                "set_blob_id, set_size_bytes, catalogue_blob_id, "
                "catalogue_size_bytes, prompt_part_characters) VALUES "
                "(:set_id, :snapshot, :map, :key, 'reliable-v1-1200', "
                "'bge-m3-dense-v1', 'set-v1', 'verified', :set_sha, :set_sha, "
                ":cat_sha, :cat_sha, :set_blob, :set_size, :cat_blob, :cat_size, 100)"
            ), {"set_id": set_id, "snapshot": snapshot, "map": "e" * 64,
                "key": key, "set_sha": set_blob.sha256, "cat_sha": cat_blob.sha256,
                "set_blob": str(set_blob.blob_id), "set_size": set_blob.size,
                "cat_blob": str(cat_blob.blob_id), "cat_size": cat_blob.size})
            _bind(session, set_id, "norm_retrieval_set", set_blob)
            _bind(session, set_id, "norm_catalogue", cat_blob)
            session.execute(text("SET CONSTRAINTS trg_norm_retrieval_set_verified IMMEDIATE"))

            project, version, document_uid, run = (
                str(ProjectUid.new()), str(VersionUid.new()),
                str(DocumentUid.new()), str(RunId.new()),
            )
            session.execute(text("INSERT INTO project (project_uid, name) VALUES (:id, 'synthetic')"), {"id": project})
            session.execute(text(
                "INSERT INTO document (document_uid, project_uid, display_title) "
                "VALUES (:document, :project, 'synthetic')"
            ), {"document": document_uid, "project": project})
            session.execute(text(
                "INSERT INTO document_version (version_uid, document_uid, "
                "version_ordinal, media_type, byte_size, sha256, page_count) "
                "VALUES (:version, :document, 1, 'application/pdf', 1, :sha, 1)"
            ), {"version": version, "document": document_uid, "sha": "f" * 64})
            session.execute(text(
                "INSERT INTO audit_run (run_id, project_uid, version_uid, "
                "analysis_profile_id, prompt_bundle_id, provider_mode, "
                "frozen_input_digest, norms_snapshot_id, norm_retrieval_set_id) "
                "VALUES (:run, :project, :version, :profile, :bundle, "
                "'recorded', :digest, :snapshot, :set_id)"
            ), {"run": run, "project": project, "version": version,
                "profile": str(AnalysisProfileId.new()),
                "bundle": str(PromptBundleId.new()), "digest": "f" * 64,
                "snapshot": snapshot, "set_id": set_id})
            session.execute(text("UPDATE audit_run SET state = 'queued' WHERE run_id = :run"), {"run": run})
            jobs = JobRepository()
            authority = jobs.start_execution(session, run_id=run)
            session.execute(text("UPDATE audit_run SET state = 'running' WHERE run_id = :run"), {"run": run})

            saved = load_verified_catalogue(session, authority=authority, blob_store=store)
            assert saved.data == catalogue.data
            assert saved.catalogue_blob_id == str(cat_blob.blob_id)
            assert saved.norm_retrieval_set_id == set_id
            assert saved.expectation.catalogue_sha256 == hashlib.sha256(catalogue.data).hexdigest()
            assert saved.expectation.snapshot_id == snapshot
            checked = load_pinned_catalogue(
                blob=saved.data, expected=saved.expectation, listed_unparsed_slugs=(),
            )
            assert len(checked.documents) == 1
            with pytest.raises(DomainError) as refused:
                load_verified_catalogue(
                    session, authority=replace(authority, execution_token="forged-token"),
                    blob_store=_NoObjectRead(),
                )
            assert refused.value.code is ErrorCode.EXECUTION_TOKEN_INVALID
            with pytest.raises(DomainError) as stale:
                load_verified_catalogue(
                    session, authority=replace(authority, attempt_id=str(AttemptId.new())),
                    blob_store=_NoObjectRead(),
                )
            assert stale.value.code is ErrorCode.STALE_ATTEMPT
            session.close()
            connection.rollback()
    finally:
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket):
            for item in page.get("Contents", []):
                s3.delete_object(Bucket=bucket, Key=item["Key"])
        s3.delete_bucket(Bucket=bucket)
        engine.dispose()
