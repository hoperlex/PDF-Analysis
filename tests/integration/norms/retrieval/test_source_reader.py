from __future__ import annotations

import hashlib
from copy import deepcopy

import pytest

from auditmanager.norms.retrieval.source_reader import (
    SnapshotEvidenceRefused,
    read_snapshot_evidence,
)


SNAPSHOT = "ns_" + "0" * 26
DOC_A = "ndoc_" + "1" * 26
DOC_B = "ndoc_" + "2" * 26
PAR_A0 = "npar_" + "3" * 26
PAR_A1 = "npar_" + "4" * 26


class _Rows:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def mappings(self) -> _Rows:
        return self

    def one_or_none(self) -> dict | None:
        assert len(self.rows) <= 1
        return self.rows[0] if self.rows else None

    def one(self) -> dict:
        assert len(self.rows) == 1
        return self.rows[0]

    def __iter__(self):
        return iter(self.rows)


class _Session:
    def __init__(self) -> None:
        self.snapshot = [{
            "norms_snapshot_id": SNAPSHOT,
            "content_key": "reviewed-key",
            "content_digest": "a" * 64,
            "document_count": 2,
            "unreliable_count": 1,
        }]
        self.documents = [
            {
                "norm_document_id": DOC_A,
                "slug": "СП_1.2020",
                "title": "Первый документ",
                "doc_type": "sp",
                "designation_tokens": ["сп", "1", "2020"],
                "paragraph_count": 2,
            },
            {
                "norm_document_id": DOC_B,
                "slug": "ГОСТ_2",
                "title": "Второй документ",
                "doc_type": "gost",
                "designation_tokens": ["гост", "2"],
                "paragraph_count": 1,
            },
        ]
        self.counts = [{
            "paragraph_count": 3,
            "unknown_reliability_count": 0,
        }]
        self.paragraphs = [
            {
                "norm_document_id": DOC_A,
                "norm_paragraph_id": PAR_A0,
                "ordinal": 0,
                "page_label": 1,
                "kind": "body",
                "clause_number": "1.1",
                "text": "Достоверный текст",
                "text_reliability": "reliable",
            },
            {
                "norm_document_id": DOC_A,
                "norm_paragraph_id": PAR_A1,
                "ordinal": 1,
                "page_label": 2,
                "kind": "heading",
                "clause_number": None,
                "text": "Ненадёжный текст",
                "text_reliability": "unreliable",
            },
        ]
        self.calls: list[tuple[str, dict, dict]] = []

    def execute(self, statement, parameters, execution_options=None):
        sql = str(statement).strip()
        assert sql.startswith("SELECT ")
        self.calls.append((sql, parameters, execution_options or {}))
        assert parameters["snapshot_id"] == SNAPSHOT
        if "FROM norms_snapshot" in sql:
            return _Rows(self.snapshot)
        if "FROM norm_document WHERE" in sql:
            return _Rows(self.documents)
        if "count(*) AS paragraph_count" in sql:
            return _Rows(self.counts)
        assert "FROM norm_paragraph p" in sql
        assert parameters["mapped_ids"] == [DOC_A]
        return _Rows(self.paragraphs)


def _read(session: _Session):
    return read_snapshot_evidence(
        session, snapshot_id=SNAPSHOT, expected_content_key="reviewed-key",
        mapped_document_ids=(DOC_A,),
    )


def test_reads_complete_catalogue_and_mapped_raw_reliability() -> None:
    session = _Session()
    evidence = _read(session)
    assert evidence.snapshot.document_count == 2
    assert [row.document_id for row in evidence.catalogue_documents] == [DOC_A, DOC_B]
    assert evidence.catalogue_documents[0].designation_tokens == ("сп", "1", "2020")
    assert [row.text_reliability for row in evidence.mapped_paragraphs] == [
        "reliable", "unreliable",
    ]
    assert evidence.mapped_paragraphs[0].text_sha256 == hashlib.sha256(
        "Достоверный текст".encode("utf-8")
    ).hexdigest()
    assert evidence.mapped_paragraphs[1].page_label == 2
    assert len(session.calls) == 4
    assert session.calls[-1][2] == {"stream_results": True, "yield_per": 2000}
    assert evidence == _read(_Session())


def test_snapshot_key_is_bound_before_other_reads() -> None:
    session = _Session()
    session.snapshot[0]["content_key"] = "other-key"
    with pytest.raises(SnapshotEvidenceRefused, match="content key"):
        _read(session)
    assert len(session.calls) == 1
    session = _Session()
    session.snapshot.clear()
    with pytest.raises(SnapshotEvidenceRefused, match="absent"):
        _read(session)


def test_mapped_ids_are_validated_before_sql() -> None:
    session = _Session()
    with pytest.raises(SnapshotEvidenceRefused, match="unique nonempty"):
        read_snapshot_evidence(
            session, snapshot_id=SNAPSHOT, expected_content_key="reviewed-key",
            mapped_document_ids=(DOC_A, DOC_A),
        )
    with pytest.raises(SnapshotEvidenceRefused, match="mapped document id"):
        read_snapshot_evidence(
            session, snapshot_id=SNAPSHOT, expected_content_key="reviewed-key",
            mapped_document_ids=("file.pdf",),
        )
    assert not session.calls


def test_document_totality_and_membership_are_required() -> None:
    session = _Session()
    session.documents.pop()
    with pytest.raises(SnapshotEvidenceRefused, match="document count"):
        _read(session)
    session = _Session()
    session.documents[0]["norm_document_id"] = "ndoc_" + "0" * 26
    with pytest.raises(SnapshotEvidenceRefused, match="mapped document is absent"):
        _read(session)
    session = _Session()
    session.documents.reverse()
    with pytest.raises(SnapshotEvidenceRefused, match="canonical order"):
        _read(session)


def test_global_paragraph_count_and_known_reliability_are_bound() -> None:
    session = _Session()
    session.counts[0]["paragraph_count"] = 2
    with pytest.raises(SnapshotEvidenceRefused, match="paragraph or reliability count"):
        _read(session)
    session = _Session()
    session.counts[0]["unknown_reliability_count"] = 1
    with pytest.raises(SnapshotEvidenceRefused, match="paragraph or reliability count"):
        _read(session)


def test_one_unrepaired_block_can_produce_two_unreliable_paragraphs() -> None:
    session = _Session()
    session.paragraphs[0]["text_reliability"] = "unreliable"
    evidence = _read(session)
    assert evidence.snapshot.unreliable_count == 1
    assert [row.text_reliability for row in evidence.mapped_paragraphs] == [
        "unreliable", "unreliable",
    ]


def test_mapped_paragraphs_must_be_complete_and_ordered() -> None:
    session = _Session()
    session.paragraphs = deepcopy(session.paragraphs[1:])
    with pytest.raises(SnapshotEvidenceRefused, match="order or identity"):
        _read(session)
    session = _Session()
    session.paragraphs.pop()
    with pytest.raises(SnapshotEvidenceRefused, match="incomplete"):
        _read(session)


def test_unknown_local_reliability_and_foreign_rows_refuse() -> None:
    session = _Session()
    session.paragraphs[1]["text_reliability"] = "reviewed"
    with pytest.raises(SnapshotEvidenceRefused, match="unknown paragraph"):
        _read(session)
    session = _Session()
    session.paragraphs[0]["norm_document_id"] = DOC_B
    with pytest.raises(SnapshotEvidenceRefused, match="foreign mapped paragraph"):
        _read(session)


def test_non_nfc_canonical_text_refuses() -> None:
    session = _Session()
    session.paragraphs[0]["text"] = "A\u0301"
    with pytest.raises(SnapshotEvidenceRefused, match="NFC"):
        _read(session)
