"""XLSX preflight binds CSV's export state policy to verified version labels."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError

import pytest

from auditmanager.exports.xlsx.preflight import read_xlsx_run_source_preflight
from auditmanager.shared.errors import DomainError, ErrorCode


RUN_ID = "run_01M2545JSD15ETSNNV904X991J"
VERSION_UID = "ver_01M2545JSD15ETSNNV904X991J"


def _raw_labels() -> bytes:
    return json.dumps({
        "schema_version": 1,
        "coordinate_space": "normalized_page_top_left",
        "pages": [{"page_index": 0}, {"page_index": 1}],
        "blocks": [
            {"block_id": f"blk_{number:032x}", "page_index": index,
             "page_label": label}
            for number, (index, label) in enumerate(((0, 17), (1, 29)), start=1)
        ],
    }).encode("utf-8")


def _source_row(raw: bytes) -> dict[str, object]:
    digest = hashlib.sha256(raw).hexdigest()
    return {
        "version_uid": VERSION_UID, "page_count": 2,
        "manifest_version_uid": VERSION_UID,
        "manifest_role": "source.structured_companion",
        "blob_id": "blob_source", "manifest_sha256": digest,
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
    def __init__(self, *, state="published", run_row=None, source_row=None):
        self.run_row = (
            {"run_id": RUN_ID, "state": state, "version_uid": VERSION_UID}
            if run_row is None else run_row
        )
        self.source_row = source_row
        self.statements = []

    def execute(self, statement, parameters):
        sql = str(statement)
        assert sql.lstrip().upper().startswith("SELECT")
        self.statements.append(sql)
        if "FROM audit_run" in sql:
            assert parameters == {"run_id": RUN_ID}
            return _Result(self.run_row)
        assert "FROM document_version" in sql
        assert parameters == {
            "version_uid": VERSION_UID, "role": "source.structured_companion",
        }
        return _Result(self.source_row)


def _read(session, raw):
    blob_reads = []

    def read_blob(blob_id):
        blob_reads.append(blob_id)
        return raw

    return read_xlsx_run_source_preflight(
        session, RUN_ID, read_blob=read_blob,
    ), blob_reads


@pytest.mark.parametrize("state", ["published", "partial"])
def test_exportable_run_has_exact_version_and_verified_labels(state) -> None:
    raw = _raw_labels()
    session = _Session(state=state, source_row=_source_row(raw))
    result, blob_reads = _read(session, raw)
    assert len(session.statements) == 2
    assert blob_reads == ["blob_source"]
    assert (result.run_id, result.version_uid, result.state) == (
        RUN_ID, VERSION_UID, state,
    )
    assert result.page_labels.version_uid == VERSION_UID
    assert dict(result.page_labels.page_labels) == {1: "17", 2: "29"}
    assert result.page_labels.source_ref == (
        f"{VERSION_UID}:blob_source:{hashlib.sha256(raw).hexdigest()}"
    )
    with pytest.raises(FrozenInstanceError):
        result.state = "failed"
    assert _read(_Session(state=state, source_row=_source_row(raw)), raw)[0] == result


@pytest.mark.parametrize("state", ["failed", "queued"])
def test_nonpublishing_run_refuses_before_source_or_blob_read(state) -> None:
    session = _Session(state=state)
    blob_reads = []
    with pytest.raises(DomainError) as raised:
        read_xlsx_run_source_preflight(
            session, RUN_ID, read_blob=blob_reads.append,
        )
    assert raised.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    assert len(session.statements) == 1
    assert blob_reads == []


def test_missing_run_uses_csv_not_found_and_does_not_read_source() -> None:
    session = _Session()
    session.run_row = None
    blob_reads = []
    with pytest.raises(DomainError) as raised:
        read_xlsx_run_source_preflight(
            session, RUN_ID, read_blob=blob_reads.append,
        )
    assert raised.value.code is ErrorCode.NOT_FOUND
    assert len(session.statements) == 1 and blob_reads == []


@pytest.mark.parametrize("run_row", [
    {"run_id": "run_01M2545JSD15ETSNNV904X991K", "state": "published",
     "version_uid": VERSION_UID},
    {"run_id": RUN_ID, "state": "published", "version_uid": "ver_bad"},
])
def test_run_identity_or_version_mismatch_refuses_before_source(run_row) -> None:
    session = _Session(run_row=run_row)
    with pytest.raises(ValueError):
        _read(session, _raw_labels())
    assert len(session.statements) == 1


def test_absent_or_wrong_version_source_refuses_without_fallback() -> None:
    raw = _raw_labels()
    with pytest.raises(ValueError, match="xlsx_run_page_source_missing"):
        _read(_Session(source_row=None), raw)
    row = _source_row(raw)
    row["manifest_version_uid"] = "ver_01M2545JSD15ETSNNV904X991K"
    with pytest.raises(ValueError, match="xlsx_page_source_binding_invalid"):
        _read(_Session(source_row=row), raw)


def test_changed_blob_or_missing_page_label_refuses() -> None:
    raw = _raw_labels()
    with pytest.raises(ValueError, match="xlsx_page_source_bytes_invalid"):
        _read(_Session(source_row=_source_row(raw)), raw + b" ")
    missing_label = json.loads(raw)
    missing_label["blocks"].pop()
    changed = json.dumps(missing_label).encode("utf-8")
    with pytest.raises(ValueError, match="xlsx_page_source_label_missing"):
        _read(_Session(source_row=_source_row(changed)), changed)


def test_invalid_inputs_refuse_before_sql() -> None:
    session = _Session()
    with pytest.raises(ValueError):
        read_xlsx_run_source_preflight(session, "run_bad", read_blob=lambda _: b"")
    with pytest.raises(ValueError, match="xlsx_run_blob_reader_invalid"):
        read_xlsx_run_source_preflight(session, RUN_ID, read_blob=None)
    assert session.statements == []
