"""The W54 copy record and W58 mirror seal must name one exact inventory."""

from __future__ import annotations

import hashlib
import json

import pytest

from scripts.recovery.copy_record_binding import CopyRecordBindingRefused, verify_copy_record_binding
from scripts.recovery.object_copy import manifest_bytes


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fixture() -> tuple[dict[str, object], bytes, dict[str, object]]:
    inventory = b"a/one\t1\tetag-a\nb/two\t2\tetag-b\n"
    record: dict[str, object] = {
        "record_version": 1,
        "kind": "copy",
        "stamp": "20261015T120000Z",
        "state": "open",
        "purpose": "import",
        "target_sha": None,
        "instance": "auditmanager-alpha",
        "deployed_tree": "a" * 40,
        "migration_head": "0022_findings_v2",
        "opened_at": "2026-10-15T12:00:00Z",
        "quiesced_at": "2026-10-15T12:00:01Z",
        "writers_present": ["api", "worker"],
        "writers_stopped": ["api", "worker"],
        "dump": {"file": "db.dump", "size_bytes": 20, "sha256": "b" * 64},
        "fingerprint": {
            "algorithm": "stand-fingerprint-v1", "sha256": "c" * 64,
            "tables": {"project": {"rows": 1, "sha256": "d" * 64}},
        },
        "rejected_blob_count": 0,
        "inventory": {"file": "inventory.tsv", "count": 2, "bytes": 3, "sha256": _sha(inventory)},
        "attestation": {
            "dump_sha256": "b" * 64,
            "restore_report_sha256": "e" * 64,
            "attested_at": "2026-10-15T12:01:00Z",
        },
        "waiver": None,
        "real_data_marker": True,
        "restored_at": None,
        "closed_at": None,
    }
    seal: dict[str, object] = {
        "format": "offline-object-copy-v1",
        "inventory_sha256": _sha(inventory),
        "count": 2,
        "bytes": 3,
        "objects": [
            {"key": "a/one", "size_bytes": 1, "etag": "etag-a", "sha256": _sha(b"1")},
            {"key": "b/two", "size_bytes": 2, "etag": "etag-b", "sha256": _sha(b"22")},
        ],
    }
    return record, inventory, seal


def _record_bytes(record: dict[str, object]) -> bytes:
    fields = [
        f'  "{key}": {json.dumps(value, ensure_ascii=True, separators=(", ", ": "))}'
        for key, value in record.items()
    ]
    return ("{\n" + ",\n".join(fields) + "\n}\n").encode("ascii")


def _verify(record: dict[str, object], inventory: bytes, seal: dict[str, object]) -> None:
    verify_copy_record_binding(_record_bytes(record), inventory, manifest_bytes(seal))


def test_accepts_exact_copy_record_and_object_seal() -> None:
    record, inventory, seal = _fixture()
    _verify(record, inventory, seal)
    _verify(record, inventory, seal)


def test_rejects_record_inventory_digest_even_when_seal_matches_actual_inventory() -> None:
    record, inventory, seal = _fixture()
    record["inventory"]["sha256"] = "0" * 64
    with pytest.raises(CopyRecordBindingRefused, match="does not match W54 record"):
        _verify(record, inventory, seal)


@pytest.mark.parametrize("field,value", [("count", 3), ("bytes", 4), ("file", "other.tsv")])
def test_rejects_record_inventory_metadata_drift(field: str, value: object) -> None:
    record, inventory, seal = _fixture()
    record["inventory"][field] = value
    with pytest.raises(CopyRecordBindingRefused):
        _verify(record, inventory, seal)


def test_rejects_seal_entry_changed_or_reordered() -> None:
    record, inventory, seal = _fixture()
    seal["objects"].reverse()
    with pytest.raises(CopyRecordBindingRefused, match="differs from inventory row"):
        _verify(record, inventory, seal)


def test_rejects_malformed_object_hash() -> None:
    record, inventory, seal = _fixture()
    seal["objects"][0]["sha256"] = "etag-is-not-sha256"
    with pytest.raises(CopyRecordBindingRefused, match="sealed object SHA-256"):
        _verify(record, inventory, seal)


def test_rejects_duplicate_json_key_in_seal() -> None:
    record, inventory, seal = _fixture()
    duplicate = manifest_bytes(seal).replace(b'"count":2,', b'"count":2,"count":2,')
    with pytest.raises(CopyRecordBindingRefused, match="duplicate JSON key"):
        verify_copy_record_binding(_record_bytes(record), inventory, duplicate)


def test_rejects_unknown_or_missing_record_field() -> None:
    record, inventory, seal = _fixture()
    record["surprise"] = "field"
    with pytest.raises(CopyRecordBindingRefused, match="unknown or missing fields"):
        _verify(record, inventory, seal)
    del record["surprise"]
    del record["fingerprint"]
    with pytest.raises(CopyRecordBindingRefused, match="unknown or missing fields"):
        _verify(record, inventory, seal)


def test_rejects_waiver_and_unrestored_attestation() -> None:
    record, inventory, seal = _fixture()
    record["kind"] = "test_data_waiver"
    with pytest.raises(CopyRecordBindingRefused, match="not a W54 v1 copy"):
        _verify(record, inventory, seal)
    record["kind"] = "copy"
    record["attestation"]["dump_sha256"] = "f" * 64
    with pytest.raises(CopyRecordBindingRefused, match="another dump"):
        _verify(record, inventory, seal)


def test_rejects_noncanonical_record_and_seal_bytes() -> None:
    record, inventory, seal = _fixture()
    with pytest.raises(CopyRecordBindingRefused, match="canonical layout"):
        verify_copy_record_binding(json.dumps(record).encode(), inventory, manifest_bytes(seal))
    with pytest.raises(CopyRecordBindingRefused, match="canonical W58 format"):
        verify_copy_record_binding(_record_bytes(record), inventory, json.dumps(seal).encode())


def test_rejects_boolean_totals_and_extra_seal_field() -> None:
    record, inventory, seal = _fixture()
    seal["count"] = True
    with pytest.raises(CopyRecordBindingRefused, match="seal totals"):
        _verify(record, inventory, seal)
    seal["count"] = 2
    seal["source"] = "unapproved"
    with pytest.raises(CopyRecordBindingRefused, match="unknown or missing fields"):
        _verify(record, inventory, seal)
