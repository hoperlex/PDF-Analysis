"""`W54-BUNDLE-01`: the rows and the build as bundle files, read back strictly.

Container-free. The row files carry exactly the declared columns, so the row digest of
what is read back is the origin's; the build files carry each vector with its digest.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditmanager.norms.bundle.contents import (
    DOCUMENTS_FILE,
    PARAGRAPHS_FILE,
    SNAPSHOT_FILE,
    BuildWriter,
    iter_build,
    read_rows,
    write_rows,
)
from auditmanager.norms.bundle.errors import BundleRefused
from tests.integration.norms.bundle.support import synthetic_chunks, synthetic_rows


def test_rows_read_back_equal_with_the_same_row_digest(tmp_path: Path) -> None:
    rows = synthetic_rows()
    assert write_rows(tmp_path, rows) == (SNAPSHOT_FILE, DOCUMENTS_FILE, PARAGRAPHS_FILE)
    back = read_rows(tmp_path)
    assert back.row_digest == rows.row_digest
    assert sorted(back.paragraphs, key=lambda r: r.norm_paragraph_id) == sorted(
        rows.paragraphs, key=lambda r: r.norm_paragraph_id
    )
    assert "пункт" in (tmp_path / PARAGRAPHS_FILE).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "edit",
    [
        lambda row: {**row, "norm_document_pk": 7},
        lambda row: {key: value for key, value in row.items() if key != "text_reliability"},
        lambda row: {**row, "ordinal": "0"},
        lambda row: {**row, "text": None},
    ],
)
def test_a_row_with_another_shape_is_refused(tmp_path: Path, edit) -> None:
    write_rows(tmp_path, synthetic_rows())
    path = tmp_path / PARAGRAPHS_FILE
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[0] = json.dumps(edit(json.loads(lines[0])), ensure_ascii=False)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(BundleRefused, match="bundle_rows_invalid"):
        read_rows(tmp_path)


def test_the_build_reads_back_chunk_for_chunk_across_files(tmp_path: Path) -> None:
    chunks = synthetic_chunks(["doc-a", "doc-b", "doc-é"], per_document=3)
    paths = BuildWriter(tmp_path, chunks_per_file=4).write_all(chunks)
    assert len(paths) == 3
    assert list(iter_build(tmp_path, paths)) == chunks


def test_the_build_writer_refuses_chunks_out_of_canonical_order(tmp_path: Path) -> None:
    chunks = synthetic_chunks(["doc-a", "doc-b"])
    with pytest.raises(BundleRefused, match="build_order"):
        BuildWriter(tmp_path).write_all([chunks[1], chunks[0]])


@pytest.mark.parametrize(
    "edit",
    [
        lambda window: {**window, "embedding_sha256": "0" * 64},
        lambda window: {**window, "vector": window["vector"][:-8]},
        lambda window: {**window, "window_ordinal": "0"},
        lambda window: {**window, "extra": 1},
    ],
)
def test_a_build_window_that_is_not_its_own_vector_is_refused(tmp_path: Path, edit) -> None:
    paths = BuildWriter(tmp_path).write_all(synthetic_chunks(["doc-a"]))
    path = tmp_path / paths[0]
    lines = path.read_text().splitlines()
    chunk = json.loads(lines[0])
    chunk["windows"][0] = edit(chunk["windows"][0])
    lines[0] = json.dumps(chunk)
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(BundleRefused, match="bundle_build_invalid"):
        list(iter_build(tmp_path, paths))
