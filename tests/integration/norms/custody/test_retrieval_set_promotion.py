"""A synthetic two-object promotion through real 0023 PostgreSQL and S3 custody.

This test proves persistence mechanics only. Its one-document snapshot is not a
reviewed or qualified normative corpus.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest
from sqlalchemy import text

from auditmanager.norms.custody import (
    CustodyDispatcher, CustodySlot, DeclaredContent, ManifestIndex,
    NORM_CATALOGUE, NORM_RETRIEVAL_SET,
)
from auditmanager.norms.embedding.profile import EMBEDDING_PROFILE
from auditmanager.norms.retrieval import promotion as promotion_module
from auditmanager.norms.retrieval.artifact import CanonicalBlob, SetIdentity, canonical_json_bytes
from auditmanager.norms.retrieval.candidate import RetrievalCandidate
from auditmanager.norms.retrieval.promotion import (
    PreparedPromotion, PromotionRefused, PromotionRequest, admit_matched,
    finalize_matched, record_rejection, select_verified_retrieval_set,
)
from auditmanager.norms.retrieval.qualification_decision import DigestComparison
from auditmanager.norms.retrieval.ranking import PromptSelection
from auditmanager.shared.db import session_scope
from auditmanager.shared.identity import (
    NormDocumentId, NormParagraphId, NormRetrievalSetId, NormsSnapshotId,
)

from .conftest import CustodyKit


CHUNKING = "reliable-v1-1200"
TEXT = "Synthetic normative paragraph for persistence testing only."


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _seed_complete_build(kit: CustodyKit, snapshot: str, key: str) -> str:
    """One source, chunk and vector window: exactly the 0023 trigger's minimum."""
    document = str(NormDocumentId.new())
    with session_scope(kit.session_factory) as session:
        session.execute(text(
            "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, "
            "content_digest, undated_documents, document_count, segmentation_profile) "
            "VALUES (:snapshot, :key, :key, :digest, 0, 1, 'markdown-v1')"
        ), {"snapshot": snapshot, "key": key, "digest": "a" * 64})
        document_pk = session.execute(text(
            "INSERT INTO norm_document (norm_document_id, norms_snapshot_id, "
            "source_document_ref, slug, title, doc_type, source_attribution, "
            "pdf_page_count, block_count, page_heading_count, recognised_characters, "
            "paragraph_count) VALUES (:document, :snapshot, 'synthetic-source', "
            "'synthetic_slug', 'Synthetic document', 'СП', 'unattributed', "
            "1, 1, 0, :length, 1) RETURNING norm_document_pk"
        ), {"document": document, "snapshot": snapshot, "length": len(TEXT)}).scalar_one()
        session.execute(text(
            "INSERT INTO norm_paragraph (norm_paragraph_id, norms_snapshot_id, "
            "norm_document_pk, ordinal, page_label, block_ref, char_offset, char_length, "
            "kind, text) VALUES (:paragraph, :snapshot, :document_pk, 0, 1, 'block-1', "
            "0, :length, 'body', :body)"
        ), {"paragraph": str(NormParagraphId.new()), "snapshot": snapshot,
            "document_pk": document_pk, "length": len(TEXT), "body": TEXT})
        session.execute(text(
            "INSERT INTO norm_chunk_build (norms_snapshot_id, chunking_profile, "
            "target_characters, chunk_count) VALUES (:snapshot, :chunking, 1200, 1)"
        ), {"snapshot": snapshot, "chunking": CHUNKING})
        chunk_pk = session.execute(text(
            "INSERT INTO norm_chunk (norms_snapshot_id, norm_document_pk, "
            "chunking_profile, ordinal, page_first, page_last, char_offset, char_length, "
            "paragraph_ordinal_first, paragraph_ordinal_last, paragraph_count, "
            "contains_clause, text, content_sha256) VALUES (:snapshot, :document_pk, "
            ":chunking, 0, 1, 1, 0, :length, 0, 0, 1, false, :body, :sha) "
            "RETURNING norm_chunk_pk"
        ), {"snapshot": snapshot, "document_pk": document_pk, "chunking": CHUNKING,
            "length": len(TEXT), "body": TEXT, "sha": _sha(TEXT.encode())}).scalar_one()
        session.execute(text(
            "INSERT INTO norm_embedding_build (norms_snapshot_id, chunking_profile, "
            "embedding_profile, chunk_count, window_count, embedding_set_sha256) "
            "VALUES (:snapshot, :chunking, :embedding, 1, 1, :sha)"
        ), {"snapshot": snapshot, "chunking": CHUNKING,
            "embedding": EMBEDDING_PROFILE, "sha": "b" * 64})
        session.execute(text(
            "INSERT INTO norm_embedding (norms_snapshot_id, norm_chunk_pk, "
            "chunking_profile, embedding_profile, window_ordinal, token_count, "
            "char_offset, char_length, paragraph_ordinal_first, paragraph_ordinal_last, "
            "input_sha256, embedding_sha256, embedding) VALUES (:snapshot, :chunk, "
            ":chunking, :embedding, 0, 10, 0, :length, 0, 0, :input_sha, :embedding_sha, "
            "('[1,' || repeat('0,', 1022) || '0]')::vector)"
        ), {"snapshot": snapshot, "chunk": chunk_pk, "chunking": CHUNKING,
            "embedding": EMBEDDING_PROFILE, "length": len(TEXT),
            "input_sha": "c" * 64, "embedding_sha": "d" * 64})
    return document


def _synthetic_prepared(
    snapshot: str, key: str, document: str, *, set_id: str,
) -> PreparedPromotion:
    mapping = canonical_json_bytes({"mapped_document_ids": [document]})
    set_bytes = canonical_json_bytes({"synthetic_set": TEXT})
    catalogue_bytes = canonical_json_bytes({"synthetic_catalogue": TEXT})
    identity = SetIdentity(_sha(mapping), snapshot, key, f"{EMBEDDING_PROFILE}:{CHUNKING}")
    request = PromotionRequest(
        set_id=set_id, identity=identity, map_bytes=mapping,
        reviewed_designations=(), items=(), chunking_profile=CHUNKING,
        independently_checked_source_digest="a" * 64,
        independently_checked_embedding_digest="b" * 64,
        expected_set_sha256=_sha(set_bytes), expected_catalogue_sha256=_sha(catalogue_bytes),
    )
    candidate = RetrievalCandidate(
        retrieval_set=CanonicalBlob(set_bytes, _sha(set_bytes)),
        catalogue=CanonicalBlob(catalogue_bytes, _sha(catalogue_bytes)),
        selection=PromptSelection((), "synthetic prompt", 0, False),
        embedding_set_sha256="b" * 64,
    )
    comparison = DigestComparison(
        status="matched", expected_set_sha256=_sha(set_bytes),
        observed_set_sha256=_sha(set_bytes),
        expected_catalogue_sha256=_sha(catalogue_bytes),
        observed_catalogue_sha256=_sha(catalogue_bytes), different_artifacts=(),
    )
    return PreparedPromotion(request, candidate, comparison)


@pytest.mark.usefixtures("clean_tables")
def test_two_saved_blobs_are_bound_to_one_verified_set_and_replay(
    custody: CustodyKit, monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = str(NormsSnapshotId.new())
    set_id = str(NormRetrievalSetId.new())
    key = f"synthetic-promotion-{snapshot[-12:].lower()}"
    document = _seed_complete_build(custody, snapshot, key)
    prepared = _synthetic_prepared(snapshot, key, document, set_id=set_id)
    rejected = replace(
        prepared,
        request=replace(prepared.request, set_id=str(NormRetrievalSetId.new()),
                        expected_set_sha256="f" * 64),
        comparison=replace(prepared.comparison, status="rejected",
                           expected_set_sha256="f" * 64,
                           different_artifacts=("retrieval_set",)),
    )
    # This acceptance isolates 0023 persistence/custody. The real read-only W57
    # preparation boundary is separately checked by the offline promotion suite.
    monkeypatch.setattr(promotion_module, "prepare_promotion", lambda _session, request: (
        rejected if request == rejected.request else prepared
    ))
    with session_scope(custody.session_factory) as session:
        assert record_rejection(session, rejected).state == "rejected"
    assert custody.bucket_keys() == []
    declarations: dict[CustodySlot, DeclaredContent] = {}
    for role, anchor, data, sha in (
        (NORM_RETRIEVAL_SET, "retrieval-set.json", prepared.candidate.retrieval_set.data,
         prepared.comparison.observed_set_sha256),
        (NORM_CATALOGUE, "catalogue.json", prepared.candidate.catalogue.data,
         prepared.comparison.observed_catalogue_sha256),
    ):
        declarations[CustodySlot(role, "norm_retrieval_set", set_id, "artifact", anchor)] = (
            DeclaredContent(sha, len(data), "application/json")
        )
        custody.source.files[anchor] = data
    manifest = ManifestIndex(declarations)
    with session_scope(custody.session_factory) as session:
        admissions = admit_matched(session, prepared, manifest=manifest)
        assert len(set(admissions)) == 2
        assert admit_matched(session, prepared, manifest=manifest) == admissions
    report = CustodyDispatcher(
        custody.store, source=custody.source, session_factory=custody.session_factory,
    ).dispatch()
    assert len(report.steps) == 2
    assert report.pending == 0 and report.poisoned == 0
    with session_scope(custody.session_factory) as session:
        outcome = finalize_matched(session, prepared, blob_store=custody.store)
        assert outcome.state == "verified" and not outcome.replayed
    with session_scope(custody.session_factory) as session:
        assert finalize_matched(session, prepared, blob_store=custody.store).replayed
        selected = select_verified_retrieval_set(
            session, identity=prepared.request.identity, chunking_profile=CHUNKING,
        )
        assert selected.set_id == set_id
        assert selected.set_sha256 == prepared.comparison.observed_set_sha256
        assert session.execute(text(
            "SELECT count(*) FROM norm_custody_binding WHERE target_id = :set_id"
        ), {"set_id": set_id}).scalar_one() == 2
        with pytest.raises(PromotionRefused, match="unavailable"):
            select_verified_retrieval_set(
                session, identity=SetIdentity("c" * 64, snapshot, key,
                                              f"{EMBEDDING_PROFILE}:{CHUNKING}"),
                chunking_profile=CHUNKING,
            )
