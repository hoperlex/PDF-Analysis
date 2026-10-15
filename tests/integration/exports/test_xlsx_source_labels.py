"""XLSX labels are bound to immutable version input, not inferred page numbers."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest

from auditmanager.exports.xlsx.source_labels import read_verified_page_labels


def _document() -> dict:
    return {
        "schema_version": 1,
        "coordinate_space": "normalized_page_top_left",
        "pages": [
            {"page_index": i, "width_px": 100, "height_px": 100, "rotation": 0}
            for i in range(2)
        ],
        "blocks": [_block(0, 17, 1), _block(1, 29, 2)],
    }


def _block(page_index: int, label: int, suffix: int) -> dict:
    return {
        "block_id": f"blk_{suffix:032x}",
        "page_index": page_index,
        "page_label": label,
        "ordinal": 0,
        "block_type": "text",
        "status": "ok",
        "coords_norm": [0.1, 0.1, 0.5, 0.5],
    }


def _bytes(document: dict) -> bytes:
    return json.dumps(document, ensure_ascii=False).encode("utf-8")


def _row(raw: bytes) -> dict:
    digest = hashlib.sha256(raw).hexdigest()
    return {
        "version_uid": "ver_a", "page_count": 2,
        "manifest_version_uid": "ver_a",
        "manifest_role": "source.structured_companion",
        "blob_id": "blob_a", "manifest_sha256": digest,
        "manifest_size_bytes": len(raw), "manifest_media_type": "application/json",
        "blob_state": "available", "blob_sha256": digest,
        "blob_size_bytes": len(raw), "blob_media_type": "application/json",
    }


class _Result:
    def __init__(self, row):
        self.row = row

    def mappings(self):
        return self

    def first(self):
        return self.row


class _Session:
    def __init__(self, row):
        self.row = deepcopy(row)
        self.calls = []

    def execute(self, statement, parameters):
        sql = str(statement)
        assert sql.lstrip().upper().startswith("SELECT")
        assert "m.version_uid = v.version_uid" in sql
        assert "b.blob_id = m.blob_id" in sql
        assert parameters == {
            "version_uid": "ver_a", "role": "source.structured_companion",
        }
        self.calls.append(sql)
        return _Result(self.row)


def _read(session, raw):
    reads = []

    def read_blob(blob_id):
        reads.append(blob_id)
        return raw

    return read_verified_page_labels(session, "ver_a", read_blob=read_blob), reads


def test_verified_portal_labels_are_version_bound_and_immutable() -> None:
    raw = _bytes(_document())
    session = _Session(_row(raw))
    result, reads = _read(session, raw)
    assert len(session.calls) == 1
    assert reads == ["blob_a"]
    assert result.version_uid == "ver_a"
    assert dict(result.page_labels) == {1: "17", 2: "29"}
    assert result.source_ref == f"ver_a:blob_a:{hashlib.sha256(raw).hexdigest()}"
    with pytest.raises(TypeError):
        result.page_labels[1] = "1"
    assert _read(_Session(_row(raw)), raw)[0] == result


def test_missing_version_returns_none_without_storage_read() -> None:
    raw = _bytes(_document())
    result, reads = _read(_Session(None), raw)
    assert result is None and reads == []


@pytest.mark.parametrize("field,value", [
    ("manifest_version_uid", "ver_other"),
    ("manifest_role", None),
    ("blob_id", None),
    ("manifest_sha256", "0" * 64),
    ("manifest_size_bytes", 4 * 1024 * 1024 + 1),
    ("manifest_media_type", "text/plain"),
    ("blob_state", "temporary"),
    ("blob_sha256", "0" * 64),
    ("blob_size_bytes", 1),
    ("blob_media_type", "text/plain"),
    ("page_count", 0),
])
def test_unbound_manifest_and_blob_refuse_before_storage(field, value) -> None:
    raw = _bytes(_document())
    row = _row(raw)
    row[field] = value
    with pytest.raises(ValueError, match="xlsx_page_source_binding_invalid"):
        _read(_Session(row), raw)


def test_changed_or_unreadable_bytes_refuse() -> None:
    raw = _bytes(_document())
    for changed in (raw + b" ", b"", "not bytes"):
        with pytest.raises(ValueError, match="xlsx_page_source_bytes_invalid"):
            _read(_Session(_row(raw)), changed)
    with pytest.raises(ValueError, match="xlsx_page_source_unreadable"):
        read_verified_page_labels(
            _Session(_row(raw)), "ver_a",
            read_blob=lambda _: (_ for _ in ()).throw(OSError("missing")),
        )


def test_unlabelled_or_conflicting_page_refuses_without_number_fallback() -> None:
    document = _document()
    document["blocks"].pop()
    raw = _bytes(document)
    with pytest.raises(ValueError, match="xlsx_page_source_label_missing"):
        _read(_Session(_row(raw)), raw)

    document = _document()
    document["blocks"].append(_block(0, 18, 3))
    raw = _bytes(document)
    with pytest.raises(ValueError, match="xlsx_page_source_label_conflict"):
        _read(_Session(_row(raw)), raw)


def test_invalid_portal_shape_refuses_after_byte_verification() -> None:
    document = _document()
    document["blocks"][0]["page_label"] = 0
    raw = _bytes(document)
    with pytest.raises(ValueError, match="xlsx_page_source_layout_invalid"):
        _read(_Session(_row(raw)), raw)


def test_duplicate_json_key_and_page_index_refuse() -> None:
    document = _document()
    document["pages"][1]["page_index"] = 0
    raw = _bytes(document)
    with pytest.raises(ValueError, match="xlsx_page_source_layout_invalid"):
        _read(_Session(_row(raw)), raw)

    raw = _bytes(_document()).replace(b'"schema_version": 1,', b'"schema_version": 1, "schema_version": 1,')
    with pytest.raises(ValueError, match="xlsx_page_source_layout_invalid"):
        _read(_Session(_row(raw)), raw)
