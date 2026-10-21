"""Stored W57a counts are facts, never an implicit qualification verdict."""

from __future__ import annotations

from copy import deepcopy

import pytest

from auditmanager.norms.embedding.profile import EMBEDDING_PROFILE
from auditmanager.norms.retrieval.qualification_reader import (
    QualificationReadRefused,
    read_snapshot_build_facts,
)


SNAPSHOT = "ns_" + "0" * 26
KEY = "2026-07-23..2026-08-20+17d.example"
PROFILE = "characters-v2:1200"


def _snapshot_row() -> dict[str, object]:
    return {
        "norms_snapshot_id": SNAPSHOT,
        "content_key": KEY,
        "content_digest": "a" * 64,
        "document_count": 674,
        "repair_count": 121,
        "stored_document_count": 674,
        "pdf_bound_document_count": 674,
    }


def _build_row() -> dict[str, object]:
    return {
        "target_characters": 1200,
        "declared_chunk_count": 55702,
        "stored_chunk_count": 55702,
        "embedded_chunk_count": 55702,
        "declared_window_count": 78000,
        "embedding_set_sha256": "b" * 64,
        "stored_window_count": 78000,
        "stored_embedded_chunk_count": 55702,
    }


class _Result:
    def __init__(self, row: dict[str, object] | None):
        self.row = row

    def mappings(self) -> _Result:
        return self

    def one_or_none(self) -> dict[str, object] | None:
        return self.row


class _Session:
    def __init__(self, snapshot: dict[str, object] | None, build: dict[str, object] | None):
        self.rows = (snapshot, build)
        self.calls: list[tuple[str, dict[str, object]]] = []

    def execute(self, statement: object, parameters: dict[str, object]) -> _Result:
        index = len(self.calls)
        self.calls.append((str(statement), parameters))
        return _Result(self.rows[index])


def _read(session: _Session, **changes: object):
    kwargs = {"snapshot_id": SNAPSHOT, "expected_content_key": KEY,
              "chunking_profile": PROFILE}
    kwargs.update(changes)
    return read_snapshot_build_facts(session, **kwargs)  # type: ignore[arg-type]


def test_reads_stored_facts_with_two_selects_and_exact_identities() -> None:
    session = _Session(_snapshot_row(), _build_row())
    facts = _read(session)
    assert (facts.snapshot_id, facts.content_key, facts.declared_document_count,
            facts.stored_document_count, facts.pdf_bound_document_count) == (
                SNAPSHOT, KEY, 674, 674, 674)
    assert facts.repair_count == 121
    assert facts.chunk is not None and facts.chunk.stored_chunk_count == 55702
    assert facts.chunk.embedding is not None
    assert facts.chunk.embedding.embedding_set_sha256 == "b" * 64
    assert facts.chunk.embedding.stored_window_count == 78000
    assert len(session.calls) == 2
    assert all(sql.strip().startswith("SELECT") for sql, _ in session.calls)
    assert "norm_custody_binding" in session.calls[0][0]
    assert "norm_embedding_build" in session.calls[1][0]
    assert session.calls[0][1] == {"snapshot_id": SNAPSHOT}
    assert session.calls[1][1] == {
        "snapshot_id": SNAPSHOT,
        "chunking_profile": PROFILE,
        "embedding_profile": EMBEDDING_PROFILE,
    }


def test_missing_build_rows_stay_explicit() -> None:
    facts = _read(_Session(_snapshot_row(), None))
    assert facts.chunk is None
    build = _build_row()
    for key in ("embedded_chunk_count", "declared_window_count", "embedding_set_sha256"):
        build[key] = None
    facts = _read(_Session(_snapshot_row(), build))
    assert facts.chunk is not None and facts.chunk.embedding is None


def test_count_drift_is_reported_as_fact_not_qualification() -> None:
    snapshot = _snapshot_row()
    build = _build_row()
    snapshot["stored_document_count"] = 673
    snapshot["pdf_bound_document_count"] = 670
    build["stored_chunk_count"] = 55701
    build["stored_window_count"] = 77999
    facts = _read(_Session(snapshot, build))
    assert facts.stored_document_count == 673
    assert facts.pdf_bound_document_count == 670
    assert facts.chunk is not None and facts.chunk.stored_chunk_count == 55701
    assert facts.chunk.embedding is not None and facts.chunk.embedding.stored_window_count == 77999


@pytest.mark.parametrize("changes", [
    {"snapshot_id": "source.pdf"},
    {"expected_content_key": ""},
    {"expected_content_key": "e\u0301"},
    {"chunking_profile": "characters-v1:1200"},
    {"chunking_profile": "paragraphs-v2"},
])
def test_bad_caller_input_refuses_before_sql(changes: dict[str, object]) -> None:
    session = _Session(_snapshot_row(), _build_row())
    with pytest.raises(QualificationReadRefused):
        _read(session, **changes)
    assert session.calls == []


def test_snapshot_absence_or_changed_key_refuses_before_build_read() -> None:
    session = _Session(None, _build_row())
    with pytest.raises(QualificationReadRefused, match="snapshot is absent"):
        _read(session)
    assert len(session.calls) == 1
    snapshot = _snapshot_row()
    snapshot["content_key"] = "different"
    session = _Session(snapshot, _build_row())
    with pytest.raises(QualificationReadRefused, match="content key differs"):
        _read(session)
    assert len(session.calls) == 1


@pytest.mark.parametrize("column,value,reason", [
    ("content_digest", "x" * 64, "snapshot content digest"),
    ("document_count", 0, "declared document count"),
    ("stored_document_count", -1, "stored document count"),
    ("pdf_bound_document_count", 675, "PDF-bound count"),
    ("repair_count", -1, "repair count"),
])
def test_malformed_snapshot_scalars_refuse(
    column: str, value: object, reason: str
) -> None:
    snapshot = deepcopy(_snapshot_row())
    snapshot[column] = value
    with pytest.raises(QualificationReadRefused, match=reason):
        _read(_Session(snapshot, _build_row()))


@pytest.mark.parametrize("column,value,reason", [
    ("target_characters", 1199, "target differs"),
    ("declared_chunk_count", -1, "chunk count"),
    ("embedded_chunk_count", -1, "embedding chunk count"),
    ("declared_window_count", -1, "embedding window count"),
    ("embedding_set_sha256", "x" * 64, "embedding set digest"),
    ("stored_window_count", -1, "stored window count"),
    ("stored_embedded_chunk_count", -1, "stored embedded chunk count"),
])
def test_malformed_build_scalars_refuse(
    column: str, value: object, reason: str
) -> None:
    build = deepcopy(_build_row())
    build[column] = value
    with pytest.raises(QualificationReadRefused, match=reason):
        _read(_Session(_snapshot_row(), build))


def test_partial_embedding_completion_refuses() -> None:
    build = _build_row()
    build["embedded_chunk_count"] = None
    with pytest.raises(QualificationReadRefused, match="partial embedding completion"):
        _read(_Session(_snapshot_row(), build))
