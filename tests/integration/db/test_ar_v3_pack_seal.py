"""`AR-V3-BETA-PACK-INSTALL-01`: `v3_pack_cli seal` against real verified retrieval sets.

Real PostgreSQL acceptance. The unit cases (every refusal, the atomic write, the exit status) run
container-free in `tests/integration/runs/test_v3_pack_manifest.py` with an injected fake; this
module proves the one thing the fake cannot: that the CLI's own database step reads the exact
verified set the group start will later pin, inside one read-only transaction, and that the sealed
file is accepted by the server's loader.

The seed is the norm half of `test_ar_v3_run_group.py::_seed` (snapshot, one document, chunk and
embedding build, six verified sets with their two custody bindings each); the run-side rows
(account, project, version) are not needed to select a set and are not created.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.analysis.public import resolve_beta_v3_profile
from auditmanager.runs import v3_pack_cli
from auditmanager.runs.v3_pack_manifest import load_manifest, load_trusted_pack_registry
from auditmanager.shared.db.config import DatabaseSettings
from auditmanager.shared.identity import (
    NormCustodyAdmissionId, NormCustodyBindingId, NormDocumentId, NormParagraphId,
    NormRetrievalSetId,
)
from auditmanager.storage.models import derive_blob_id

SNAPSHOT = "ns_01M59N8QNBVN91ACA2HCE6VE74"
CHUNKING = "characters-v2:1200"
CONTENT_KEY = "ar-v3-beta-synthetic"
QUOTE = "Test normative paragraph."
SET_SHA = "1" * 64


def _blob(session: Session, sha: str, size: int, media_type: str) -> str:
    blob_id = str(derive_blob_id(sha256=sha, size=size))
    session.execute(text("INSERT INTO blob (blob_id) VALUES (:id)"), {"id": blob_id})
    session.execute(text("UPDATE blob SET state = 'verifying' WHERE blob_id = :id"), {"id": blob_id})
    session.execute(text("""
        UPDATE blob SET state = 'available', sha256 = :sha,
            size_bytes = :size, media_type = :media WHERE blob_id = :id
    """), {"id": blob_id, "sha": sha, "size": size, "media": media_type})
    return blob_id


def _binding(
    session: Session, *, role: str, target_kind: str, target_id: str,
    anchor_kind: str, anchor: str, blob_id: str, size: int, sha: str, media_type: str,
) -> None:
    admission = str(NormCustodyAdmissionId.new())
    session.execute(text("""
        INSERT INTO norm_custody_admission
            (norm_custody_admission_id, role, target_kind, target_id, anchor_kind,
             anchor, blob_id, declared_size_bytes, declared_sha256, media_type)
        VALUES (:id, :role, :kind, :target, :anchor_kind, :anchor, :blob,
                :size, :sha, :media)
    """), {
        "id": admission, "role": role, "kind": target_kind, "target": target_id,
        "anchor_kind": anchor_kind, "anchor": anchor, "blob": blob_id,
        "size": size, "sha": sha, "media": media_type,
    })
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
    """), {
        "id": str(NormCustodyBindingId.new()), "admission": admission,
        "role": role, "kind": target_kind, "target": target_id,
        "anchor_kind": anchor_kind, "anchor": anchor, "blob": blob_id,
    })


def _seed_six_verified_sets(session: Session) -> list[dict[str, str]]:
    """The snapshot of the pinned beta profile and one verified set per scope; returns the spec rows."""
    profile = resolve_beta_v3_profile(
        "ap_01M5M28ZCDD8VPSP1BTAEW92YE", "pb_01M5M28ZCDVCR37BX1884JGSPM",
    )
    pdf_blob = _blob(session, "a" * 64, 1024, "application/pdf")
    session.execute(text("""
        INSERT INTO norms_snapshot
            (norms_snapshot_id, content_key, base_content_key, content_digest,
             undated_documents, document_count, segmentation_profile)
        VALUES (:id, :key, :key, :sha, 0, 1, 'markdown-v1')
    """), {"id": SNAPSHOT, "key": CONTENT_KEY, "sha": "b" * 64})
    norm_document = str(NormDocumentId.new())
    norm_pk = session.execute(text("""
        INSERT INTO norm_document
            (norm_document_id, norms_snapshot_id, source_document_ref, slug, title,
             doc_type, source_attribution, pdf_page_count, block_count,
             page_heading_count, recognised_characters, paragraph_count)
        VALUES (:id, :snapshot, 'synthetic-source', 'synthetic-slug', 'Synthetic standard',
                'СП', 'unattributed', 1, 1, 0, :length, 1)
        RETURNING norm_document_pk
    """), {"id": norm_document, "snapshot": SNAPSHOT, "length": len(QUOTE)}).scalar_one()
    _binding(session, role="norm_source", target_kind="norm_document",
             target_id=norm_document, anchor_kind="pdf", anchor="synthetic-source",
             blob_id=pdf_blob, size=1024, sha="a" * 64, media_type="application/pdf")
    session.execute(text("""
        INSERT INTO norm_paragraph
            (norm_paragraph_id, norms_snapshot_id, norm_document_pk, ordinal,
             page_label, block_ref, char_offset, char_length, kind, text)
        VALUES (:id, :snapshot, :document, 0, 1, 'synthetic-block',
                0, :length, 'body', :quote)
    """), {"id": str(NormParagraphId.new()), "snapshot": SNAPSHOT,
           "document": norm_pk, "length": len(QUOTE), "quote": QUOTE})
    session.execute(text("""
        INSERT INTO norm_chunk_build
            (norms_snapshot_id, chunking_profile, target_characters, chunk_count)
        VALUES (:snapshot, :chunking, 1200, 1)
    """), {"snapshot": SNAPSHOT, "chunking": CHUNKING})
    chunk_pk = session.execute(text("""
        INSERT INTO norm_chunk
            (norms_snapshot_id, norm_document_pk, chunking_profile, ordinal,
             page_first, page_last, char_offset, char_length,
             paragraph_ordinal_first, paragraph_ordinal_last, paragraph_count,
             contains_clause, text, content_sha256)
        VALUES (:snapshot, :document, :chunking, 0, 1, 1, 0, :length,
                0, 0, 1, false, :quote, :sha)
        RETURNING norm_chunk_pk
    """), {"snapshot": SNAPSHOT, "document": norm_pk, "chunking": CHUNKING,
           "length": len(QUOTE), "quote": QUOTE, "sha": "c" * 64}).scalar_one()
    session.execute(text("""
        INSERT INTO norm_embedding_build
            (norms_snapshot_id, chunking_profile, embedding_profile,
             chunk_count, window_count, embedding_set_sha256)
        VALUES (:snapshot, :chunking, 'bge-m3-dense-v1', 1, 1, :sha)
    """), {"snapshot": SNAPSHOT, "chunking": CHUNKING, "sha": "d" * 64})
    session.execute(text("""
        INSERT INTO norm_embedding
            (norms_snapshot_id, norm_chunk_pk, chunking_profile, embedding_profile,
             window_ordinal, token_count, char_offset, char_length,
             paragraph_ordinal_first, paragraph_ordinal_last, input_sha256,
             embedding_sha256, embedding)
        VALUES (:snapshot, :chunk, :chunking, 'bge-m3-dense-v1', 0, 10, 0,
                :length, 0, 0, :input, :embedding_sha,
                ('[1,' || repeat('0,', 1022) || '0]')::vector)
    """), {"snapshot": SNAPSHOT, "chunk": chunk_pk, "chunking": CHUNKING,
           "length": len(QUOTE), "input": "e" * 64, "embedding_sha": "f" * 64})

    set_blob = _blob(session, SET_SHA, 10, "application/json")
    catalogue_blob = _blob(session, "2" * 64, 11, "application/json")
    rows: list[dict[str, str]] = []
    for index, scope_id in enumerate(profile.scopes, 1):
        set_id = str(NormRetrievalSetId.new())
        map_sha = f"{index:x}" * 64
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
                    :catalogue_sha, :catalogue_sha, :set_blob, 10,
                    :catalogue_blob, 11, 100)
        """), {"id": set_id, "snapshot": SNAPSHOT, "map": map_sha,
               "key": CONTENT_KEY, "chunking": CHUNKING,
               "set_sha": SET_SHA, "catalogue_sha": "2" * 64,
               "set_blob": set_blob, "catalogue_blob": catalogue_blob})
        for role, blob, sha, size in (
            ("norm_retrieval_set", set_blob, SET_SHA, 10),
            ("norm_catalogue", catalogue_blob, "2" * 64, 11),
        ):
            _binding(session, role=role, target_kind="norm_retrieval_set",
                     target_id=set_id, anchor_kind="artifact", anchor=role,
                     blob_id=blob, size=size, sha=sha, media_type="application/json")
        rows.append({
            "scope_id": scope_id, "map_sha256": map_sha, "snapshot_id": SNAPSHOT,
            "reviewed_content_key": CONTENT_KEY,
            "embedding_build": f"bge-m3-dense-v1:{CHUNKING}",
            "builder_version": "norm-retrieval-set-prep-v1",
            "chunking_profile": CHUNKING, "set_id": set_id,
        })
    return rows


def _argv(spec: Path, out: Path, url: str) -> list[str]:
    return [
        "seal", "--scopes", str(spec), "--reviewer", "DB Test Reviewer", "--capacity", "expert",
        "--reviewed-at", "2026-10-26", "--decision-ref", "DB-TEST-1",
        "--scope-statement", "six synthetic scopes, database test", "--out", str(out),
        "--database-url", url,
    ]


def _write_spec(path: Path, rows: list[dict[str, str]], **replacements: Any) -> Path:
    scopes = [{k: v for k, v in row.items() if k != "set_id"} for row in rows]
    path.write_text(json.dumps({
        "analysis_profile_id": "ap_01M5M28ZCDD8VPSP1BTAEW92YE",
        "prompt_bundle_id": "pb_01M5M28ZCDVCR37BX1884JGSPM",
        "scopes": scopes, **replacements,
    }), encoding="utf-8")
    return path


def test_seal_pins_the_verified_sets_and_the_server_loader_accepts_the_file(
    migrated_database: DatabaseSettings, migrated_engine: Engine, tmp_path: Path,
) -> None:
    with Session(migrated_engine) as session, session.begin():
        rows = _seed_six_verified_sets(session)
    url = migrated_database.url.render_as_string(hide_password=False)
    out = tmp_path / "manifest.json"
    stdout, stderr = io.StringIO(), io.StringIO()
    status = v3_pack_cli.main(
        _argv(_write_spec(tmp_path / "scopes.json", rows), out, url),
        environ={}, out=stdout, err=stderr,
    )
    assert (status, stderr.getvalue()) == (0, "")
    parsed = load_manifest(str(out))
    assert [s.scope_id for s in parsed.pack.scopes] == [r["scope_id"] for r in rows]
    assert [s.set_id for s in parsed.pack.scopes] == [r["set_id"] for r in rows]
    assert {s.set_sha256 for s in parsed.pack.scopes} == {SET_SHA}
    assert load_trusted_pack_registry(str(out)).select_beta() == parsed.pack
    assert (out.stat().st_mode & 0o777) == 0o600


def test_seal_refuses_a_scope_whose_map_has_no_verified_set(
    migrated_database: DatabaseSettings, migrated_engine: Engine, tmp_path: Path,
) -> None:
    with Session(migrated_engine) as session, session.begin():
        rows = _seed_six_verified_sets(session)
    rows[3] = {**rows[3], "map_sha256": "9" * 64}
    url = migrated_database.url.render_as_string(hide_password=False)
    stderr = io.StringIO()
    status = v3_pack_cli.main(
        _argv(_write_spec(tmp_path / "scopes.json", rows), tmp_path / "manifest.json", url),
        environ={}, out=io.StringIO(), err=stderr,
    )
    assert status == 2 and "scope_unverified" in stderr.getvalue() and "A2" in stderr.getvalue()
    assert not (tmp_path / "manifest.json").exists()


def test_seal_reads_in_one_read_only_transaction(
    migrated_database: DatabaseSettings, monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = migrated_database.url.render_as_string(hide_password=False)
    seen: dict[str, Any] = {}

    def probe(session: Session, **_kwargs: Any) -> Any:
        seen["read_only"] = session.execute(text("SHOW transaction_read_only")).scalar_one()
        with pytest.raises(DBAPIError) as refused:
            session.execute(text("CREATE TEMP TABLE pack_seal_must_not_write (x int)"))
        seen["write_refused"] = "read-only" in str(refused.value).lower()
        raise RuntimeError("probe done")

    monkeypatch.setattr(v3_pack_cli, "select_verified_retrieval_set", probe)
    with pytest.raises(RuntimeError, match="probe done"):
        with v3_pack_cli.open_database_selector(url) as select:
            select(object(), CHUNKING)  # type: ignore[arg-type]
    assert seen == {"read_only": "on", "write_refused": True}
