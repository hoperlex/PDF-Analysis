"""W58 evidence collection rehashes locally before any restored-DB read."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from auditmanager.storage.public import canonical_object_key_for_recovery, derive_blob_id
from scripts.recovery import offline_restore_audit as coordinator
from scripts.recovery.blob_reference_audit import BlobFact, BlobReferenceAudit
from scripts.recovery.object_copy import build_manifest, manifest_bytes
from scripts.recovery.offline_restore_preflight import RecoveryPreflightRefused

_STAMP = "20261015T120000Z"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _record_bytes(record: dict[str, object]) -> bytes:
    fields = [
        f'  "{key}": {json.dumps(value, ensure_ascii=True, separators=(", ", ": "))}'
        for key, value in record.items()
    ]
    return ("{\n" + ",\n".join(fields) + "\n}\n").encode("ascii")


def _copy(tmp_path: Path) -> tuple[Path, Path, BlobReferenceAudit]:
    copy_dir = tmp_path / _STAMP
    mirror = tmp_path / "mirror"
    copy_dir.mkdir(mode=0o700)
    mirror.mkdir(mode=0o700)
    payload = b"canonical payload"
    sha = _sha(payload)
    blob_id = str(derive_blob_id(sha256=sha, size=len(payload)))
    key = canonical_object_key_for_recovery(blob_id)
    object_path = mirror / key
    object_path.parent.mkdir(parents=True)
    object_path.write_bytes(payload)
    inventory = f"{key}\t{len(payload)}\tetag-not-a-digest\n".encode("ascii")
    dump = b"PGDMP\x00isolated fake"
    record: dict[str, object] = {
        "record_version": 1, "kind": "copy", "stamp": _STAMP, "state": "open",
        "purpose": "import", "target_sha": None, "instance": "auditmanager-alpha",
        "deployed_tree": "a" * 40, "migration_head": "0022_findings_v2",
        "opened_at": "2026-10-15T12:00:00Z", "quiesced_at": "2026-10-15T12:00:01Z",
        "writers_present": ["api", "worker"], "writers_stopped": ["api", "worker"],
        "dump": {"file": "db.dump", "size_bytes": len(dump), "sha256": _sha(dump)},
        "fingerprint": {"algorithm": "stand-fingerprint-v1", "sha256": "c" * 64,
                        "tables": {"project": {"rows": 1, "sha256": "d" * 64}}},
        "rejected_blob_count": 0,
        "inventory": {"file": "inventory.tsv", "count": 1, "bytes": len(payload),
                      "sha256": _sha(inventory)},
        "attestation": None, "waiver": None, "real_data_marker": False,
        "restored_at": None, "closed_at": None,
    }
    (copy_dir / "record.json").write_bytes(_record_bytes(record))
    (copy_dir / "db.dump").write_bytes(dump)
    (copy_dir / "inventory.tsv").write_bytes(inventory)
    (copy_dir / "objects.json").write_bytes(manifest_bytes(build_manifest(inventory, mirror)))
    audit = BlobReferenceAudit((("input_manifest_entry", 1),),
                               (BlobFact(blob_id, sha, len(payload), "application/pdf"),))
    return copy_dir, mirror, audit


def test_collects_facts_after_local_rehash_and_before_return_rehash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    copy_dir, mirror, expected_audit = _copy(tmp_path)
    before = {p.name: p.read_bytes() for p in copy_dir.iterdir()}
    events: list[str] = []
    original_preflight = coordinator.verify_offline_restore_inputs
    original_bind = coordinator.bind_available_blob_objects

    def preflight(copy: Path, objects: Path) -> None:
        events.append("preflight")
        original_preflight(copy, objects)

    def audit(session: object) -> BlobReferenceAudit:
        assert events == ["preflight"]
        events.append("db_select")
        return expected_audit

    def bind(*args: object, **kwargs: object) -> tuple[coordinator.BoundBlobObject, ...]:
        events.append("bind")
        return original_bind(*args, **kwargs)

    monkeypatch.setattr(coordinator, "verify_offline_restore_inputs", preflight)
    monkeypatch.setattr(coordinator, "audit_blob_references", audit)
    monkeypatch.setattr(coordinator, "bind_available_blob_objects", bind)
    evidence = coordinator.collect_offline_restore_evidence(object(), copy_dir, mirror)  # type: ignore[arg-type]
    assert events == ["preflight", "db_select", "bind", "preflight"]
    assert evidence.blob_references == expected_audit
    assert [(row.blob_id, row.sha256, row.size_bytes) for row in evidence.bound_objects] == [
        (fact.blob_id, fact.sha256, fact.size_bytes)
        for fact in expected_audit.available_blobs
    ]
    assert {p.name: p.read_bytes() for p in copy_dir.iterdir()} == before


def test_failed_local_preflight_prevents_restored_db_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    copy_dir, mirror, audit_facts = _copy(tmp_path)
    object_path = mirror / canonical_object_key_for_recovery(audit_facts.available_blobs[0].blob_id)
    object_path.write_bytes(b"changed payload")
    monkeypatch.setattr(coordinator, "audit_blob_references",
                        lambda _: pytest.fail("DB read started before preflight"))
    with pytest.raises(RecoveryPreflightRefused):
        coordinator.collect_offline_restore_evidence(object(), copy_dir, mirror)  # type: ignore[arg-type]


def test_symlinked_metadata_after_preflight_refuses_before_db_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    copy_dir, mirror, _ = _copy(tmp_path)
    original = coordinator.verify_offline_restore_inputs

    def preflight_and_replace(copy: Path, objects: Path) -> None:
        original(copy, objects)
        record = copy / "record.json"
        record.rename(copy / "record.actual")
        record.symlink_to(copy / "record.actual")

    monkeypatch.setattr(coordinator, "verify_offline_restore_inputs", preflight_and_replace)
    monkeypatch.setattr(coordinator, "audit_blob_references",
                        lambda _: pytest.fail("DB read started after metadata substitution"))
    with pytest.raises(coordinator.RecoveryEvidenceRefused):
        coordinator.collect_offline_restore_evidence(object(), copy_dir, mirror)  # type: ignore[arg-type]


@pytest.mark.parametrize("change", ("mirror", "metadata"))
def test_post_audit_drift_prevents_evidence_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    copy_dir, mirror, expected_audit = _copy(tmp_path)
    monkeypatch.setattr(coordinator, "audit_blob_references", lambda _: expected_audit)
    original_bind = coordinator.bind_available_blob_objects

    def bind_then_change(*args: object, **kwargs: object) -> tuple[coordinator.BoundBlobObject, ...]:
        bound = original_bind(*args, **kwargs)
        if change == "mirror":
            (mirror / bound[0].key).write_bytes(b"changed payload")
        else:
            record = copy_dir / "record.json"
            record.write_bytes(record.read_bytes().replace(b'"state": "open"', b'"state": "closed"'))
        return bound

    monkeypatch.setattr(coordinator, "bind_available_blob_objects", bind_then_change)
    expected = RecoveryPreflightRefused if change == "mirror" else coordinator.RecoveryEvidenceRefused
    with pytest.raises(expected):
        coordinator.collect_offline_restore_evidence(object(), copy_dir, mirror)  # type: ignore[arg-type]
