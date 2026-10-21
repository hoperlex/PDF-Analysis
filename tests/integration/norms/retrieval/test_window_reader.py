from __future__ import annotations

import pytest

from auditmanager.norms.embedding import vectors
from auditmanager.norms.embedding.digest import EmbeddingSetDigest
from auditmanager.norms.embedding.profile import DIMENSIONS
from auditmanager.norms.retrieval import window_reader
from auditmanager.norms.retrieval.window_reader import WindowReadRefused, read_retrieval_windows


SNAPSHOT = "ns_" + "0" * 26
DOC_A = "ndoc_" + "1" * 26
DOC_B = "ndoc_" + "2" * 26
EMBEDDING = "bge-m3-dense-v1"
CHUNKING = "characters-v2:1200"
BUILD = EMBEDDING + ":" + CHUNKING
PACKED = vectors.pack((1.0, *([0.0] * (DIMENSIONS - 1))))


class _Rows:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def mappings(self):
        return self

    def one_or_none(self):
        assert len(self.rows) <= 1
        return self.rows[0] if self.rows else None

    def __iter__(self):
        return iter(self.rows)


class _Session:
    def __init__(self) -> None:
        self.metadata = [
            {
                "norm_document_id": DOC_A, "source_document_ref": "source/a",
                "chunk_ordinal": 0, "window_ordinal": 0, "token_count": 12,
                "char_offset": 0, "char_length": 20,
                "paragraph_ordinal_first": 0, "paragraph_ordinal_last": 0,
                "input_sha256": "a" * 64, "embedding_sha256": vectors.sha256(PACKED),
            },
            {
                "norm_document_id": DOC_B, "source_document_ref": "source/b",
                "chunk_ordinal": 0, "window_ordinal": 0, "token_count": 15,
                "char_offset": 0, "char_length": 25,
                "paragraph_ordinal_first": 0, "paragraph_ordinal_last": 1,
                "input_sha256": "b" * 64, "embedding_sha256": vectors.sha256(PACKED),
            },
        ]
        self.vectors = [
            {
                key: value for key, value in self.metadata[0].items()
                if key != "source_document_ref"
            } | {"embedding_text": vectors.pgvector_literal(PACKED)}
        ]
        self.build = [{
            "content_key": "reviewed-key",
            "canonical_chunk_count": 2,
            "stored_chunk_count": 2,
            "chunk_count": 2,
            "window_count": 2,
            "embedding_set_sha256": self.digest(),
        }]
        self.calls: list[tuple[str, dict, dict]] = []

    def digest(self) -> str:
        digest = EmbeddingSetDigest(
            content_key="reviewed-key", chunking_profile=CHUNKING,
            embedding_profile=EMBEDDING,
        )
        for row in self.metadata:
            digest.add_values(
                row["source_document_ref"], row["chunk_ordinal"],
                window_ordinal=row["window_ordinal"],
                token_count=row["token_count"], char_offset=row["char_offset"],
                char_length=row["char_length"],
                paragraph_ordinal_first=row["paragraph_ordinal_first"],
                paragraph_ordinal_last=row["paragraph_ordinal_last"],
                input_sha256=row["input_sha256"],
                embedding_sha256=row["embedding_sha256"],
            )
        return digest.hexdigest()

    def execute(self, statement, parameters, execution_options=None):
        sql = str(statement).strip()
        assert sql.startswith("SELECT ")
        assert parameters["snapshot_id"] == SNAPSHOT
        assert parameters["chunking_profile"] == CHUNKING
        assert parameters["embedding_profile"] == EMBEDDING
        self.calls.append((sql, parameters, execution_options or {}))
        if "FROM norms_snapshot s" in sql:
            return _Rows(self.build)
        if "embedding::text" in sql:
            assert parameters["mapped_ids"] == [DOC_A]
            return _Rows(self.vectors)
        assert "FROM norm_embedding e" in sql
        return _Rows(self.metadata)


def _read(session: _Session, **overrides):
    values = {
        "snapshot_id": SNAPSHOT,
        "expected_content_key": "reviewed-key",
        "embedding_build": BUILD,
        "expected_embedding_set_sha256": (
            session.build[0]["embedding_set_sha256"] if session.build else session.digest()
        ),
        "mapped_document_ids": (DOC_A,),
    }
    return read_retrieval_windows(session, **(values | overrides))


def test_reads_complete_build_and_exact_mapped_float32_vector() -> None:
    session = _Session()
    result = _read(session)
    assert result.build_chunk_count == 2
    assert result.build_window_count == 2
    assert result.embedding_set_sha256 == session.digest()
    assert len(result.windows) == 1
    window = result.windows[0]
    assert (window.document_id, window.chunk_ordinal, window.window_ordinal) == (DOC_A, 0, 0)
    assert (window.paragraph_ordinal_first, window.paragraph_ordinal_last) == (0, 0)
    assert window.vector.typecode == "f"
    assert len(window.vector) == DIMENSIONS
    assert tuple(window.vector[:2]) == (1.0, 0.0)
    assert len(session.calls) == 3
    assert session.calls[1][2] == {"stream_results": True, "yield_per": 2000}
    assert session.calls[2][2] == {"stream_results": True, "yield_per": 250}
    assert result == _read(_Session())


def test_missing_build_or_changed_snapshot_refuses_before_window_read() -> None:
    session = _Session()
    session.build.clear()
    with pytest.raises(WindowReadRefused, match="build is absent"):
        _read(session)
    assert len(session.calls) == 1
    session = _Session()
    session.build[0]["content_key"] = "other"
    with pytest.raises(WindowReadRefused, match="content key"):
        _read(session)
    assert len(session.calls) == 1


def test_counts_and_independent_digest_refuse() -> None:
    session = _Session()
    session.build[0]["stored_chunk_count"] = 1
    with pytest.raises(WindowReadRefused, match="count mismatch"):
        _read(session)
    session = _Session()
    with pytest.raises(WindowReadRefused, match="differs from expected"):
        _read(session, expected_embedding_set_sha256="0" * 64)
    session = _Session()
    session.metadata.pop()
    with pytest.raises(WindowReadRefused, match="rows differ"):
        _read(session)
    session = _Session()
    session.metadata[0]["input_sha256"] = "c" * 64
    with pytest.raises(WindowReadRefused, match="rows differ"):
        _read(session)


def test_sparse_window_ordinals_and_changed_metadata_refuse() -> None:
    session = _Session()
    session.metadata[0]["window_ordinal"] = 1
    with pytest.raises(WindowReadRefused, match="ordinals are incomplete"):
        _read(session)
    session = _Session()
    session.vectors[0]["char_length"] = 21
    with pytest.raises(WindowReadRefused, match="metadata differs"):
        _read(session)
    session = _Session()
    session.vectors.clear()
    with pytest.raises(WindowReadRefused, match="rows are incomplete"):
        _read(session)


def test_vector_hash_and_bounded_mapped_input_refuse(monkeypatch) -> None:
    session = _Session()
    session.vectors[0]["embedding_text"] = "[1,0]"
    with pytest.raises(WindowReadRefused, match="invalid stored vector"):
        _read(session)
    session = _Session()
    other = vectors.pack((0.0, 1.0, *([0.0] * (DIMENSIONS - 2))))
    session.vectors[0]["embedding_text"] = vectors.pgvector_literal(other)
    with pytest.raises(WindowReadRefused, match="stored vector digest mismatch"):
        _read(session)
    session = _Session()
    session.vectors[0]["embedding_sha256"] = "0" * 64
    with pytest.raises(WindowReadRefused, match="metadata differs"):
        _read(session)
    session = _Session()
    session.build[0]["window_count"] = 1_000_001
    with pytest.raises(WindowReadRefused, match="capacity exceeded"):
        _read(session)
    session = _Session()
    monkeypatch.setattr(window_reader, "MAX_CANDIDATE_WINDOWS", 0)
    with pytest.raises(WindowReadRefused, match="too many mapped"):
        _read(session)
    assert len(session.calls) == 2


def test_inputs_fail_before_sql() -> None:
    session = _Session()
    with pytest.raises(WindowReadRefused, match="duplicate mapped"):
        _read(session, mapped_document_ids=(DOC_A, DOC_A))
    with pytest.raises(WindowReadRefused, match="invalid mapped"):
        _read(session, mapped_document_ids=("file.pdf",))
    with pytest.raises(WindowReadRefused, match="unknown embedding build"):
        _read(session, embedding_build="other:characters-v2:1200")
    with pytest.raises(WindowReadRefused, match="invalid chunking"):
        _read(session, embedding_build="bge-m3-dense-v1:bad")
    assert not session.calls
