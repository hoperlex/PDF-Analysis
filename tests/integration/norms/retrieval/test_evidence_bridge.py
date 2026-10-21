from __future__ import annotations

import hashlib
from array import array
from dataclasses import replace

import pytest

from auditmanager.norms.embedding.profile import DIMENSIONS
from auditmanager.norms.retrieval.artifact import (
    SetIdentity,
    build_retrieval_set,
    canonical_json_bytes,
)
from auditmanager.norms.retrieval.catalogue import CatalogueDocument, build_catalogue
from auditmanager.norms.retrieval.evidence_bridge import (
    EvidenceBridgeRefused,
    ReviewedDesignation,
    project_snapshot_evidence,
)
from auditmanager.norms.retrieval.ranking import RetrievalItem, TargetSpan, select_prompt_part
from auditmanager.norms.retrieval.source_reader import (
    CanonicalParagraphEvidence,
    SnapshotEvidence,
    SnapshotFacts,
)


SNAPSHOT = "ns_" + "0" * 26
DOC_A = "ndoc_" + "1" * 26
DOC_B = "ndoc_" + "2" * 26
PAR_A0 = "npar_" + "3" * 26
PAR_A1 = "npar_" + "4" * 26
BUILD = "bge-m3-dense-v1:characters-v2:1200"


def _sha(data: bytes | str) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def _fixture():
    mapping = {
        "reviewed_content_key": "reviewed-key",
        "norms_snapshot_id": SNAPSHOT,
        "embedding_build": BUILD,
        "mapped_document_ids": [DOC_A],
        "items": [{"id": "item-1"}],
    }
    map_bytes = canonical_json_bytes(mapping)
    identity = SetIdentity(_sha(map_bytes), SNAPSHOT, "reviewed-key", BUILD)
    evidence = SnapshotEvidence(
        snapshot=SnapshotFacts(SNAPSHOT, "reviewed-key", "a" * 64, 2, 1),
        catalogue_documents=(
            CatalogueDocument(DOC_A, "СП_1.2020", ("сп", "1", "2020"), "Первый документ", "sp"),
            CatalogueDocument(DOC_B, "ГОСТ_2", ("гост", "2"), "Второй документ", "gost"),
        ),
        mapped_paragraphs=(
            CanonicalParagraphEvidence(
                DOC_A, PAR_A0, 0, 4, "body", "1.1", "Достоверный текст", "reliable",
                _sha("Достоверный текст"),
            ),
            CanonicalParagraphEvidence(
                DOC_A, PAR_A1, 1, 5, "heading", None, "Ненадёжный текст", "unreliable",
                _sha("Ненадёжный текст"),
            ),
        ),
    )
    labels = (ReviewedDesignation(DOC_A, "СП_1.2020", "СП 1.2020"),)
    return evidence, identity, map_bytes, labels


def _project(parts):
    evidence, identity, map_bytes, labels = parts
    return project_snapshot_evidence(
        evidence, identity=identity, map_bytes=map_bytes, reviewed_designations=labels,
    )


def test_projects_exact_rows_into_existing_pure_builders() -> None:
    parts = _fixture()
    projected = _project(parts)
    assert projected.snapshot.embedding_build == BUILD
    assert projected.snapshot.document_count == 2
    assert tuple(p.paragraph.reliable for p in projected.source_paragraphs) == (True, False)
    assert tuple(p.reliable for p in projected.target_paragraphs) == (True, False)
    assert tuple(p.paragraph.page_label for p in projected.source_paragraphs) == ("4", "5")
    assert projected.source_paragraphs[0].paragraph.designation == "СП 1.2020"
    assert projected.source_paragraphs[0].paragraph.title == "Первый документ"
    assert projected == _project(_fixture())

    vector = array("f", [0.0]) * DIMENSIONS
    vector[0] = 1.0
    selection = select_prompt_part(
        (RetrievalItem("item-1", vector, (TargetSpan(DOC_A, 0, 0),)),),
        tuple(row.paragraph for row in projected.source_paragraphs),
        (),
    )
    set_blob = build_retrieval_set(
        identity=parts[1], map_bytes=parts[2], snapshot=projected.snapshot,
        selection=selection, paragraphs=projected.source_paragraphs,
    )
    catalogue_blob = build_catalogue(
        snapshot=projected.snapshot, documents=parts[0].catalogue_documents,
    )
    assert set_blob.sha256 == _sha(set_blob.data)
    assert catalogue_blob.sha256 == _sha(catalogue_blob.data)
    assert "Ненадёжный текст" not in set_blob.data.decode("utf-8")


def test_map_digest_and_identity_refuse() -> None:
    evidence, identity, map_bytes, labels = _fixture()
    with pytest.raises(EvidenceBridgeRefused, match="map digest mismatch"):
        _project((evidence, replace(identity, map_sha256="b" * 64), map_bytes, labels))
    with pytest.raises(EvidenceBridgeRefused, match="map identity mismatch"):
        _project((evidence, replace(identity, embedding_build="other-build"), map_bytes, labels))
    with pytest.raises(EvidenceBridgeRefused, match="builder version"):
        _project((evidence, replace(identity, builder_version="other-version"), map_bytes, labels))
    with pytest.raises(EvidenceBridgeRefused, match="snapshot differs"):
        changed_snapshot = replace(evidence.snapshot, content_key="other")
        _project((replace(evidence, snapshot=changed_snapshot), identity, map_bytes, labels))
    mapping = {
        "reviewed_content_key": "reviewed-key", "norms_snapshot_id": SNAPSHOT,
        "embedding_build": BUILD, "mapped_document_ids": [DOC_B], "items": [{"id": "item-1"}],
    }
    changed = canonical_json_bytes(mapping)
    with pytest.raises(EvidenceBridgeRefused, match="reviewed designation document mismatch"):
        _project((evidence, replace(identity, map_sha256=_sha(changed)), changed, labels))


def test_reviewed_label_must_match_exact_snapshot_document() -> None:
    evidence, identity, map_bytes, labels = _fixture()
    with pytest.raises(EvidenceBridgeRefused, match="slug mismatch"):
        _project((evidence, identity, map_bytes, (replace(labels[0], slug="other"),)))
    with pytest.raises(EvidenceBridgeRefused, match="cover mapped"):
        _project((evidence, identity, map_bytes, ()))
    with pytest.raises(EvidenceBridgeRefused, match="nonempty NFC"):
        _project((evidence, identity, map_bytes, (replace(labels[0], designation="A\u0301"),)))


def test_catalogue_and_paragraph_drift_refuse() -> None:
    evidence, identity, map_bytes, labels = _fixture()
    with pytest.raises(EvidenceBridgeRefused, match="catalogue count mismatch"):
        truncated = replace(evidence, catalogue_documents=evidence.catalogue_documents[:1])
        _project((truncated, identity, map_bytes, labels))
    with pytest.raises(EvidenceBridgeRefused, match="absent from catalogue"):
        changed_docs = (
            replace(evidence.catalogue_documents[0], document_id="ndoc_" + "5" * 26),
            evidence.catalogue_documents[1],
        )
        _project((replace(evidence, catalogue_documents=changed_docs), identity, map_bytes, labels))
    changed = replace(evidence.mapped_paragraphs[1], ordinal=2)
    with pytest.raises(EvidenceBridgeRefused, match="ordinal mismatch"):
        shifted = replace(evidence, mapped_paragraphs=(evidence.mapped_paragraphs[0], changed))
        _project((shifted, identity, map_bytes, labels))
    changed = replace(evidence.mapped_paragraphs[0], text_sha256="b" * 64)
    with pytest.raises(EvidenceBridgeRefused, match="digest mismatch"):
        changed_evidence = replace(
            evidence, mapped_paragraphs=(changed, evidence.mapped_paragraphs[1]),
        )
        _project((changed_evidence, identity, map_bytes, labels))
    changed = replace(evidence.mapped_paragraphs[0], text_reliability="reviewed")
    with pytest.raises(EvidenceBridgeRefused, match="unknown paragraph"):
        changed_evidence = replace(
            evidence, mapped_paragraphs=(changed, evidence.mapped_paragraphs[1]),
        )
        _project((changed_evidence, identity, map_bytes, labels))


def test_unrepaired_block_count_is_not_paragraph_count() -> None:
    evidence, identity, map_bytes, labels = _fixture()
    rows = tuple(replace(row, text_reliability="unreliable") for row in evidence.mapped_paragraphs)
    projected = _project((replace(evidence, mapped_paragraphs=rows), identity, map_bytes, labels))
    assert evidence.snapshot.unreliable_count == 1
    assert all(not row.paragraph.reliable for row in projected.source_paragraphs)
