"""Available restored Blob facts bind to one sealed offline object inventory."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from auditmanager.storage.public import derive_blob_id
from scripts.recovery.blob_object_binding import (
    BlobObjectBindingRefused,
    BoundBlobObject,
    bind_available_blob_objects,
)
from scripts.recovery.blob_reference_audit import BlobFact, BlobReferenceAudit
from scripts.recovery.object_copy import manifest_bytes


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _record_bytes(record: dict[str, object]) -> bytes:
    fields = [
        f'  "{key}": {json.dumps(value, ensure_ascii=True, separators=(", ", ": "))}'
        for key, value in record.items()
    ]
    return ("{\n" + ",\n".join(fields) + "\n}\n").encode("ascii")


def _fixture() -> tuple[BlobReferenceAudit, bytes, bytes, bytes, dict[str, str]]:
    facts = tuple(
        BlobFact(str(derive_blob_id(sha256=_sha(payload), size=len(payload))),
                 _sha(payload), len(payload), "application/pdf")
        for payload in (b"first", b"second")
    )
    keys = {
        fact.blob_id: f"blobs/{fact.blob_id[5:7]}/{fact.blob_id[7:9]}/{fact.blob_id[5:]}"
        for fact in facts
    }
    entries = sorted(
        ({"key": keys[fact.blob_id], "size_bytes": fact.size_bytes,
          "etag": f"etag-{index}", "sha256": fact.sha256}
         for index, fact in enumerate(facts)),
        key=lambda entry: entry["key"],
    )
    inventory = "".join(
        f"{entry['key']}\t{entry['size_bytes']}\t{entry['etag']}\n" for entry in entries
    ).encode("ascii")
    seal = manifest_bytes({
        "format": "offline-object-copy-v1", "inventory_sha256": _sha(inventory),
        "count": len(entries), "bytes": sum(entry["size_bytes"] for entry in entries),
        "objects": entries,
    })
    record = {
        "record_version": 1, "kind": "copy", "stamp": "20261015T120000Z",
        "state": "open", "purpose": "import", "target_sha": None,
        "instance": "auditmanager-alpha", "deployed_tree": "a" * 40,
        "migration_head": "0022_findings_v2", "opened_at": "2026-10-15T12:00:00Z",
        "quiesced_at": "2026-10-15T12:00:01Z", "writers_present": ["api", "worker"],
        "writers_stopped": ["api", "worker"],
        "dump": {"file": "db.dump", "size_bytes": 20, "sha256": "b" * 64},
        "fingerprint": {
            "algorithm": "stand-fingerprint-v1", "sha256": "c" * 64,
            "tables": {"project": {"rows": 1, "sha256": "d" * 64}},
        },
        "rejected_blob_count": 0,
        "inventory": {"file": "inventory.tsv", "count": len(entries),
                      "bytes": sum(entry["size_bytes"] for entry in entries),
                      "sha256": _sha(inventory)},
        "attestation": {"dump_sha256": "b" * 64, "restore_report_sha256": "e" * 64,
                        "attested_at": "2026-10-15T12:01:00Z"},
        "waiver": None, "real_data_marker": True, "restored_at": None,
        "closed_at": None,
    }
    return BlobReferenceAudit((), facts), _record_bytes(record), inventory, seal, keys


def _bind(audit: BlobReferenceAudit, record: bytes, inventory: bytes, seal: bytes,
          keys: dict[str, str]) -> tuple[BoundBlobObject, ...]:
    return bind_available_blob_objects(
        audit, record, inventory, seal, canonical_key_for=keys.__getitem__
    )


def test_binds_every_available_blob_to_exact_sealed_key_and_facts() -> None:
    audit, record, inventory, seal, keys = _fixture()
    result = _bind(audit, record, inventory, seal, keys)
    assert result == tuple(sorted(
        (BoundBlobObject(fact.blob_id, keys[fact.blob_id], fact.sha256, fact.size_bytes)
         for fact in audit.available_blobs),
        key=lambda item: item.blob_id,
    ))
    assert _bind(audit, record, inventory, seal, keys) == result


def test_empty_available_set_needs_no_object_binding() -> None:
    audit, record, inventory, seal, keys = _fixture()
    assert _bind(replace(audit, available_blobs=()), record, inventory, seal, keys) == ()


def test_missing_canonical_object_refuses() -> None:
    audit, record, inventory, seal, keys = _fixture()
    keys[audit.available_blobs[0].blob_id] = "blobs/missing/object"
    with pytest.raises(BlobObjectBindingRefused, match="missing at its canonical key"):
        _bind(audit, record, inventory, seal, keys)


def test_sealed_digest_mismatch_refuses_even_with_valid_record_binding() -> None:
    audit, record, inventory, seal, keys = _fixture()
    data = json.loads(seal)
    data["objects"][0]["sha256"] = "0" * 64
    with pytest.raises(BlobObjectBindingRefused, match="object facts differ"):
        _bind(audit, record, inventory, manifest_bytes(data), keys)


def test_sealed_size_mismatch_refuses_even_with_valid_record_binding() -> None:
    audit, record, inventory, seal, keys = _fixture()
    data = json.loads(seal)
    data["objects"][0]["size_bytes"] += 1
    rows = [
        f"{entry['key']}\t{entry['size_bytes']}\t{entry['etag']}\n"
        for entry in data["objects"]
    ]
    inventory = "".join(rows).encode("ascii")
    data["inventory_sha256"] = _sha(inventory)
    data["bytes"] += 1
    copy_record = json.loads(record)
    copy_record["inventory"].update(sha256=_sha(inventory), bytes=data["bytes"])
    with pytest.raises(BlobObjectBindingRefused, match="object facts differ"):
        _bind(audit, _record_bytes(copy_record), inventory, manifest_bytes(data), keys)


def test_duplicate_available_identity_and_ambiguous_key_refuse() -> None:
    audit, record, inventory, seal, keys = _fixture()
    duplicate = replace(audit, available_blobs=audit.available_blobs + audit.available_blobs[:1])
    with pytest.raises(BlobObjectBindingRefused, match="identity is repeated"):
        _bind(duplicate, record, inventory, seal, keys)
    keys[audit.available_blobs[1].blob_id] = keys[audit.available_blobs[0].blob_id]
    with pytest.raises(BlobObjectBindingRefused, match="invalid or ambiguous"):
        _bind(audit, record, inventory, seal, keys)


def test_bad_resolver_and_malformed_fact_refuse() -> None:
    audit, record, inventory, seal, keys = _fixture()
    keys[audit.available_blobs[0].blob_id] = "temporary/not-canonical"
    with pytest.raises(BlobObjectBindingRefused, match="invalid or ambiguous"):
        _bind(audit, record, inventory, seal, keys)
    bad = replace(audit.available_blobs[0], sha256="0" * 64)
    with pytest.raises(BlobObjectBindingRefused, match="wrong identity"):
        _bind(replace(audit, available_blobs=(bad,)), record, inventory, seal, keys)


def test_changed_or_noncanonical_seal_refuses_before_matching() -> None:
    audit, record, inventory, seal, keys = _fixture()
    with pytest.raises(BlobObjectBindingRefused, match="record and W58 object seal differ"):
        _bind(audit, record, inventory, seal.replace(b'"count":2', b'"count":3'), keys)
    with pytest.raises(BlobObjectBindingRefused, match="record and W58 object seal differ"):
        _bind(audit, record, inventory, json.dumps(json.loads(seal)).encode(), keys)
