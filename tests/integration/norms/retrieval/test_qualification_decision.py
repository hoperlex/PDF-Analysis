"""A matching digest comparison is not a verified retrieval-set row."""

from __future__ import annotations

from dataclasses import replace

import pytest

from auditmanager.norms.embedding.profile import EMBEDDING_PROFILE
from auditmanager.norms.retrieval.artifact import (
    CanonicalBlob,
    SetIdentity,
    canonical_blob,
)
from auditmanager.norms.retrieval.candidate import RetrievalCandidate
from auditmanager.norms.retrieval.catalogue import CATALOGUE_VERSION
from auditmanager.norms.retrieval.qualification_decision import (
    QualificationDecisionRefused,
    compare_retrieval_candidate,
)
from auditmanager.norms.retrieval.qualification_reader import (
    ChunkBuildFacts,
    EmbeddingBuildFacts,
    SnapshotBuildFacts,
)
from auditmanager.norms.retrieval.ranking import PromptSelection


SNAPSHOT = "ns_" + "0" * 26
MAP_DIGEST = "1" * 64
SOURCE_DIGEST = "2" * 64
EMBEDDING_DIGEST = "3" * 64
CHUNKING = "characters-v2:1200"
BUILD = f"{EMBEDDING_PROFILE}:{CHUNKING}"


def _inputs():
    identity = SetIdentity(MAP_DIGEST, SNAPSHOT, "reviewed-key", BUILD)
    facts = SnapshotBuildFacts(
        snapshot_id=SNAPSHOT,
        content_key="reviewed-key",
        content_digest=SOURCE_DIGEST,
        declared_document_count=2,
        stored_document_count=2,
        pdf_bound_document_count=2,
        repair_count=1,
        chunking_profile=CHUNKING,
        embedding_profile=EMBEDDING_PROFILE,
        chunk=ChunkBuildFacts(
            target_characters=1200,
            declared_chunk_count=3,
            stored_chunk_count=3,
            embedding=EmbeddingBuildFacts(
                declared_chunk_count=3,
                declared_window_count=4,
                embedding_set_sha256=EMBEDDING_DIGEST,
                stored_window_count=4,
                stored_embedded_chunk_count=3,
            ),
        ),
    )
    retrieval_set = canonical_blob({
        "builder_version": identity.builder_version,
        "identity": {
            "map_sha256": MAP_DIGEST,
            "reviewed_content_key": "reviewed-key",
            "norms_snapshot_id": SNAPSHOT,
            "embedding_build": BUILD,
        },
        "snapshot_content_digest": SOURCE_DIGEST,
    })
    catalogue = canonical_blob({
        "catalogue_version": CATALOGUE_VERSION,
        "norms_snapshot_id": SNAPSHOT,
        "content_key": "reviewed-key",
        "snapshot_content_digest": SOURCE_DIGEST,
        "document_count": 2,
        "documents": [{"id": "a"}, {"id": "b"}],
    })
    candidate = RetrievalCandidate(
        retrieval_set=retrieval_set,
        catalogue=catalogue,
        selection=PromptSelection((), "", 0, False),
        embedding_set_sha256=EMBEDDING_DIGEST,
    )
    arguments = dict(
        facts=facts,
        identity=identity,
        candidate=candidate,
        independently_checked_source_digest=SOURCE_DIGEST,
        independently_checked_embedding_digest=EMBEDDING_DIGEST,
        expected_set_sha256=retrieval_set.sha256,
        expected_catalogue_sha256=catalogue.sha256,
    )
    return arguments


def test_complete_facts_and_independent_expectations_yield_only_match_record() -> None:
    args = _inputs()
    result = compare_retrieval_candidate(**args)
    assert result.status == "matched"
    assert result.different_artifacts == ()
    assert (result.observed_set_sha256, result.observed_catalogue_sha256) == (
        args["expected_set_sha256"], args["expected_catalogue_sha256"],
    )
    assert result == compare_retrieval_candidate(**_inputs())


@pytest.mark.parametrize("changed,expected", [
    ({"expected_set_sha256": "a" * 64}, ("retrieval_set",)),
    ({"expected_catalogue_sha256": "b" * 64}, ("catalogue",)),
    ({"expected_set_sha256": "a" * 64, "expected_catalogue_sha256": "b" * 64},
     ("retrieval_set", "catalogue")),
])
def test_mismatched_expected_digest_records_rejected_artifacts(changed, expected) -> None:
    args = _inputs() | changed
    result = compare_retrieval_candidate(**args)
    assert result.status == "rejected"
    assert result.different_artifacts == expected
    assert result.expected_set_sha256 == args["expected_set_sha256"]
    assert result.observed_set_sha256 == args["candidate"].retrieval_set.sha256


@pytest.mark.parametrize("field,value,reason", [
    ("stored_document_count", 1, "documents"),
    ("pdf_bound_document_count", 1, "PDF custody"),
    ("declared_document_count", 0, "documents"),
])
def test_incomplete_snapshot_or_source_custody_refuses(field, value, reason) -> None:
    args = _inputs()
    args["facts"] = replace(args["facts"], **{field: value})
    with pytest.raises(QualificationDecisionRefused, match=reason):
        compare_retrieval_candidate(**args)


def test_missing_or_partial_build_refuses() -> None:
    args = _inputs()
    args["facts"] = replace(args["facts"], chunk=None)
    with pytest.raises(QualificationDecisionRefused, match="chunk build incomplete"):
        compare_retrieval_candidate(**args)
    args = _inputs()
    args["facts"] = replace(args["facts"], chunk=replace(args["facts"].chunk, embedding=None))
    with pytest.raises(QualificationDecisionRefused, match="chunk build incomplete"):
        compare_retrieval_candidate(**args)
    args = _inputs()
    args["facts"] = replace(args["facts"], chunk=replace(args["facts"].chunk, stored_chunk_count=2))
    with pytest.raises(QualificationDecisionRefused, match="chunk build incomplete"):
        compare_retrieval_candidate(**args)


@pytest.mark.parametrize("field,value", [
    ("declared_chunk_count", 2),
    ("stored_embedded_chunk_count", 2),
    ("declared_window_count", 2),
    ("stored_window_count", 3),
])
def test_incomplete_embedding_counts_refuse(field, value) -> None:
    args = _inputs()
    chunk = args["facts"].chunk
    args["facts"] = replace(args["facts"], chunk=replace(
        chunk, embedding=replace(chunk.embedding, **{field: value})
    ))
    with pytest.raises(QualificationDecisionRefused, match="embedding build incomplete"):
        compare_retrieval_candidate(**args)


def test_proof_digests_must_match_stored_and_candidate_values() -> None:
    args = _inputs()
    args["independently_checked_source_digest"] = "a" * 64
    with pytest.raises(QualificationDecisionRefused, match="source digest"):
        compare_retrieval_candidate(**args)
    args = _inputs()
    args["independently_checked_embedding_digest"] = "a" * 64
    with pytest.raises(QualificationDecisionRefused, match="embedding digest"):
        compare_retrieval_candidate(**args)
    args = _inputs()
    args["candidate"] = replace(args["candidate"], embedding_set_sha256="a" * 64)
    with pytest.raises(QualificationDecisionRefused, match="embedding digest"):
        compare_retrieval_candidate(**args)


@pytest.mark.parametrize("field,value", [
    ("expected_set_sha256", "A" * 64),
    ("expected_catalogue_sha256", "bad"),
    ("independently_checked_source_digest", ""),
    ("independently_checked_embedding_digest", "?" * 64),
])
def test_noncanonical_digest_inputs_refuse(field, value) -> None:
    args = _inputs()
    args[field] = value
    with pytest.raises(QualificationDecisionRefused, match="digest"):
        compare_retrieval_candidate(**args)


def test_changed_identity_or_candidate_bytes_refuse_before_digest_decision() -> None:
    args = _inputs()
    args["identity"] = replace(args["identity"], map_sha256="a" * 64)
    with pytest.raises(QualificationDecisionRefused, match="artifact identity"):
        compare_retrieval_candidate(**args)
    args = _inputs()
    changed = CanonicalBlob(args["candidate"].retrieval_set.data + b" ",
                            args["candidate"].retrieval_set.sha256)
    args["candidate"] = replace(args["candidate"], retrieval_set=changed)
    with pytest.raises(QualificationDecisionRefused, match="bytes differ"):
        compare_retrieval_candidate(**args)
    args = _inputs()
    noncanonical = b'{"z":1, "a":2}'
    from hashlib import sha256
    args["candidate"] = replace(args["candidate"], retrieval_set=CanonicalBlob(
        noncanonical, sha256(noncanonical).hexdigest()
    ))
    with pytest.raises(QualificationDecisionRefused, match="canonical JSON"):
        compare_retrieval_candidate(**args)


def test_catalogue_snapshot_and_document_count_must_match_facts() -> None:
    args = _inputs()
    args["facts"] = replace(args["facts"], content_key="other")
    with pytest.raises(QualificationDecisionRefused, match="identity differs"):
        compare_retrieval_candidate(**args)
    args = _inputs()
    catalogue = canonical_blob({
        "catalogue_version": CATALOGUE_VERSION,
        "norms_snapshot_id": SNAPSHOT,
        "content_key": "reviewed-key",
        "snapshot_content_digest": SOURCE_DIGEST,
        "document_count": 2,
        "documents": [{"id": "a"}],
    })
    args["candidate"] = replace(args["candidate"], catalogue=catalogue)
    with pytest.raises(QualificationDecisionRefused, match="artifact identity"):
        compare_retrieval_candidate(**args)
