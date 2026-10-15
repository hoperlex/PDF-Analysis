from __future__ import annotations

import hashlib
import json
from array import array
from dataclasses import replace

import pytest

from auditmanager.norms.embedding.profile import DIMENSIONS
from auditmanager.norms.retrieval.artifact import SetIdentity, canonical_json_bytes
from auditmanager.norms.retrieval.candidate import CandidateRefused, assemble_retrieval_candidate
from auditmanager.norms.retrieval.catalogue import CatalogueDocument
from auditmanager.norms.retrieval.evidence_bridge import ReviewedDesignation
from auditmanager.norms.retrieval.ranking import RetrievalItem, RetrievalWindow, TargetSpan
from auditmanager.norms.retrieval.source_reader import (
    CanonicalParagraphEvidence,
    SnapshotEvidence,
    SnapshotFacts,
)
from auditmanager.norms.retrieval.window_reader import WindowEvidence


SNAPSHOT = "ns_" + "0" * 26
DOC_A = "ndoc_" + "1" * 26
DOC_B = "ndoc_" + "2" * 26
PAR_A0 = "npar_" + "3" * 26
PAR_A1 = "npar_" + "4" * 26
BUILD = "bge-m3-dense-v1:characters-v2:1200"


def _sha(value: bytes | str) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def _vector() -> array:
    result = array("f", [0.0]) * DIMENSIONS
    result[0] = 1.0
    return result


def _fixture():
    map_bytes = canonical_json_bytes({
        "norms_snapshot_id": SNAPSHOT,
        "reviewed_content_key": "reviewed-key",
        "embedding_build": BUILD,
        "mapped_document_ids": [DOC_A],
        "items": [{"id": "item-1"}],
    })
    identity = SetIdentity(_sha(map_bytes), SNAPSHOT, "reviewed-key", BUILD)
    evidence = SnapshotEvidence(
        snapshot=SnapshotFacts(SNAPSHOT, "reviewed-key", "a" * 64, 2, 0),
        catalogue_documents=(
            CatalogueDocument(DOC_A, "СП_1.2020", ("сп", "1", "2020"), "Первый", "sp"),
            CatalogueDocument(DOC_B, "ГОСТ_2", ("гост", "2"), "Второй", "gost"),
        ),
        mapped_paragraphs=(
            CanonicalParagraphEvidence(
                DOC_A, PAR_A0, 0, 1, "body", "1.1", "Первый достоверный пункт",
                "reliable", _sha("Первый достоверный пункт"),
            ),
            CanonicalParagraphEvidence(
                DOC_A, PAR_A1, 1, 2, "body", None, "Второй достоверный пункт",
                "reliable", _sha("Второй достоверный пункт"),
            ),
        ),
    )
    windows = WindowEvidence(
        snapshot_id=SNAPSHOT,
        embedding_build=BUILD,
        embedding_set_sha256="b" * 64,
        build_chunk_count=1,
        build_window_count=1,
        windows=(RetrievalWindow(DOC_A, 0, 0, 0, 1, _vector()),),
    )
    labels = (ReviewedDesignation(DOC_A, "СП_1.2020", "СП 1.2020"),)
    items = (RetrievalItem("item-1", _vector(), (TargetSpan(DOC_A, 0, 0),)),)
    return evidence, windows, identity, map_bytes, labels, items


def _assemble(parts):
    evidence, windows, identity, map_bytes, labels, items = parts
    return assemble_retrieval_candidate(
        evidence=evidence, windows=windows, identity=identity,
        map_bytes=map_bytes, reviewed_designations=labels, items=items,
    )


def test_assembles_stable_exact_set_and_catalogue_candidates() -> None:
    parts = _fixture()
    candidate = _assemble(parts)
    assert candidate == _assemble(_fixture())
    assert candidate.retrieval_set.sha256 == _sha(candidate.retrieval_set.data)
    assert candidate.catalogue.sha256 == _sha(candidate.catalogue.data)
    assert candidate.embedding_set_sha256 == "b" * 64
    assert [row.label for row in candidate.selection.rows] == ["N1", "N2"]
    set_payload = json.loads(candidate.retrieval_set.data)
    catalogue_payload = json.loads(candidate.catalogue.data)
    assert set_payload["identity"]["map_sha256"] == parts[2].map_sha256
    assert [row["norm_paragraph_id"] for row in set_payload["rebinding_paragraphs"]] == [
        PAR_A0, PAR_A1,
    ]
    assert [row["norm_document_id"] for row in catalogue_payload["documents"]] == [
        DOC_A, DOC_B,
    ]


def test_snapshot_and_embedding_build_must_match() -> None:
    evidence, windows, identity, map_bytes, labels, items = _fixture()
    with pytest.raises(CandidateRefused, match="window snapshot or embedding build"):
        _assemble((evidence, replace(windows, snapshot_id="ns_" + "5" * 26), identity,
                   map_bytes, labels, items))
    with pytest.raises(CandidateRefused, match="window snapshot or embedding build"):
        _assemble((evidence, replace(windows, embedding_build="other"), identity,
                   map_bytes, labels, items))
    changed = replace(evidence, snapshot=replace(evidence.snapshot, content_key="other"))
    with pytest.raises(CandidateRefused, match="snapshot differs"):
        _assemble((changed, windows, identity, map_bytes, labels, items))


def test_foreign_duplicate_and_missing_mapped_windows_refuse() -> None:
    evidence, windows, identity, map_bytes, labels, items = _fixture()
    foreign = replace(windows.windows[0], document_id=DOC_B)
    with pytest.raises(CandidateRefused, match="unmapped document"):
        _assemble((evidence, replace(windows, windows=(foreign,)), identity,
                   map_bytes, labels, items))
    with pytest.raises(CandidateRefused, match="duplicate mapped window"):
        duplicate = replace(windows, build_window_count=2, windows=windows.windows * 2)
        _assemble((evidence, duplicate, identity, map_bytes, labels, items))
    with pytest.raises(CandidateRefused, match="empty"):
        _assemble((evidence, replace(windows, windows=()), identity,
                   map_bytes, labels, items))


def test_query_item_ids_and_target_documents_are_exact() -> None:
    evidence, windows, identity, map_bytes, labels, items = _fixture()
    wrong_id = (replace(items[0], item_id="other"),)
    with pytest.raises(CandidateRefused, match="query items differ"):
        _assemble((evidence, windows, identity, map_bytes, labels, wrong_id))
    wrong_target = (replace(items[0], targets=(TargetSpan(DOC_B, 0, 0),)),)
    with pytest.raises(CandidateRefused, match="query target documents differ"):
        _assemble((evidence, windows, identity, map_bytes, labels, wrong_target))
    malformed = (replace(items[0], targets=("paragraph.pdf",)),)
    with pytest.raises(CandidateRefused, match="query target spans are invalid"):
        _assemble((evidence, windows, identity, map_bytes, labels, malformed))


def test_changed_source_hash_and_bad_vector_refuse() -> None:
    evidence, windows, identity, map_bytes, labels, items = _fixture()
    bad_row = replace(evidence.mapped_paragraphs[0], text_sha256="0" * 64)
    changed = replace(evidence, mapped_paragraphs=(bad_row, evidence.mapped_paragraphs[1]))
    with pytest.raises(CandidateRefused, match="paragraph text digest mismatch"):
        _assemble((changed, windows, identity, map_bytes, labels, items))
    short = replace(windows.windows[0], vector=array("f", [1.0]))
    with pytest.raises(CandidateRefused, match="complete float32"):
        _assemble((evidence, replace(windows, windows=(short,)), identity,
                   map_bytes, labels, items))
