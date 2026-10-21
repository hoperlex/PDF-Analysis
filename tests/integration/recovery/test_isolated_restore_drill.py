"""The offline drill coordinates W58 helpers without starting DB or S3 services."""

from __future__ import annotations

import hashlib
import io
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

import pytest

from auditmanager.storage.public import BlobId, BlobNotFoundError, canonical_object_key_for_recovery, derive_blob_id
from scripts.recovery import isolated_restore_drill as drill
from scripts.recovery.blob_object_binding import BoundBlobObject
from scripts.recovery.blob_reference_audit import BlobFact, BlobReferenceAudit, BlobReferenceAuditRefused
from scripts.recovery.object_copy import build_manifest, manifest_bytes
from scripts.recovery.offline_restore_audit import OfflineRestoreEvidence
from scripts.recovery.offline_restore_preflight import RecoveryPreflightRefused
from scripts.recovery.schema_coverage import (
    FINGERPRINTED_TABLES,
    HEAD,
    RestoredSchemaAudit,
    RestoredSchemaRefused,
)

_STAMP = "20261016T120000Z"
_PAYLOADS = (b"retrieval set payload", b"catalogue payload")
_FINGERPRINT = "c" * 64
_SCHEMA = RestoredSchemaAudit(55, 4, 72, 31, ())


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _copy(tmp_path: Path, *, tables: frozenset[str] = FINGERPRINTED_TABLES,
          ) -> tuple[Path, Path, OfflineRestoreEvidence]:
    copy_dir, mirror = tmp_path / _STAMP, tmp_path / "mirror"
    copy_dir.mkdir(mode=0o700)
    mirror.mkdir(mode=0o700)
    entries: list[tuple[str, bytes, BlobFact]] = []
    for payload in _PAYLOADS:
        sha = _sha(payload)
        blob_id = str(derive_blob_id(sha256=sha, size=len(payload)))
        key = canonical_object_key_for_recovery(BlobId(blob_id))
        object_path = mirror / key
        object_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        for directory in object_path.parents:
            if directory == mirror:
                break
            directory.chmod(0o700)
        object_path.write_bytes(payload)
        object_path.chmod(0o600)
        entries.append((key, payload, BlobFact(blob_id, sha, len(payload), "application/pdf")))
    inventory = b"".join(
        f"{key}\t{len(payload)}\tetag-is-opaque\n".encode("ascii")
        for key, payload, _ in sorted(entries)
    )
    dump = b"PGDMP\x00isolated fake"
    record = {
        "record_version": 1, "kind": "copy", "stamp": _STAMP, "state": "open",
        "purpose": "import", "target_sha": None, "instance": "isolated-fixture",
        "deployed_tree": "a" * 40, "migration_head": HEAD,
        "opened_at": "2026-10-16T12:00:00Z", "quiesced_at": "2026-10-16T12:00:01Z",
        "writers_present": ["api", "worker"], "writers_stopped": ["api", "worker"],
        "dump": {"file": "db.dump", "size_bytes": len(dump), "sha256": _sha(dump)},
        "fingerprint": {"algorithm": "stand-fingerprint-v1", "sha256": _FINGERPRINT,
                        "tables": {name: {"rows": 1, "sha256": "d" * 64} for name in sorted(tables)}},
        "rejected_blob_count": 0,
        "inventory": {"file": "inventory.tsv", "count": 2, "bytes": sum(map(len, _PAYLOADS)),
                      "sha256": _sha(inventory)},
        "attestation": None, "waiver": None, "real_data_marker": False,
        "restored_at": None, "closed_at": None,
    }
    lines = [f'  "{name}": {json.dumps(value, ensure_ascii=True, separators=(", ", ": "))}'
             for name, value in record.items()]
    (copy_dir / "record.json").write_bytes(("{\n" + ",\n".join(lines) + "\n}\n").encode("ascii"))
    (copy_dir / "db.dump").write_bytes(dump)
    (copy_dir / "inventory.tsv").write_bytes(inventory)
    (copy_dir / "objects.json").write_bytes(manifest_bytes(build_manifest(inventory, mirror)))
    evidence = OfflineRestoreEvidence(
        BlobReferenceAudit((("norm_retrieval_set", 1),), tuple(entry[2] for entry in entries)),
        tuple(BoundBlobObject(fact.blob_id, key, fact.sha256, fact.size_bytes)
              for key, _, fact in entries),
    )
    return copy_dir, mirror, evidence


class _Objects:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.objects: dict[str, bytes] = {}
        self.metadata: dict[str, dict[str, str]] = {}
        self.puts = 0

    def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
        self.events.append("list")
        assert kwargs == {"Bucket": "isolated-bucket"}
        return {"IsTruncated": False, "Contents": [
            {"Key": key, "Size": len(value)} for key, value in sorted(self.objects.items())
        ]}

    def put_object(self, *, Bucket: str, Key: str, Body: io.BufferedIOBase,
                   ContentLength: int, IfNoneMatch: str,
                   Metadata: dict[str, str]) -> dict[str, object]:
        self.events.append("put")
        assert Bucket == "isolated-bucket" and IfNoneMatch == "*" and Key not in self.objects
        value = Body.read()
        assert len(value) == ContentLength
        assert Metadata == {"content-sha256": _sha(value)}
        self.objects[Key] = value
        self.metadata[Key] = dict(Metadata)
        self.puts += 1
        return {}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        self.events.append("get")
        assert Bucket == "isolated-bucket"
        value = self.objects[Key]
        return {"ContentLength": len(value), "Body": io.BytesIO(value),
                "Metadata": dict(self.metadata[Key])}


class _Blobs:
    def __init__(self, objects: _Objects, events: list[str], *, missing: str | None = None) -> None:
        self.objects = objects
        self.events = events
        self.missing = missing

    def open_stream(self, blob_id: BlobId, *, expected_sha256: str,
                    expected_size: int, window: object = None) -> Iterator[bytes]:
        self.events.append("blob_read")
        assert window is None
        key = canonical_object_key_for_recovery(blob_id)
        if self.missing == str(blob_id) or key not in self.objects.objects:
            raise BlobNotFoundError(blob_id=str(blob_id))
        yield self.objects.objects[key]


def _run(copy_dir: Path, mirror: Path, evidence: OfflineRestoreEvidence,
         monkeypatch: pytest.MonkeyPatch, *, fingerprint: str = _FINGERPRINT,
         missing_blob_index: int | None = None,
         collector: Callable[[object, Path, Path], OfflineRestoreEvidence] | None = None,
         schema_audit: Callable[[object], RestoredSchemaAudit] | None = None,
         object_client: _Objects | None = None,
         events_sink: list[str] | None = None,
         ) -> tuple[drill.IsolatedRestoreDrillEvidence, _Objects, list[str]]:
    events: list[str] = (object_client.events if object_client is not None
                         else events_sink if events_sink is not None else [])
    objects = object_client if object_client is not None else _Objects(events)
    session = object()

    @contextmanager
    def restore_database(dump: Path) -> Iterator[drill.RestoredDatabase]:
        events.append("db_restore")
        assert dump == copy_dir / "db.dump"
        try:
            yield drill.RestoredDatabase(session, fingerprint)  # type: ignore[arg-type]
        finally:
            events.append("db_close")

    def collect(actual_session: object, actual_copy: Path, actual_mirror: Path) -> OfflineRestoreEvidence:
        events.append("db_audit")
        assert actual_session is session and (actual_copy, actual_mirror) == (copy_dir, mirror)
        return evidence

    def audit_schema(actual_session: object) -> RestoredSchemaAudit:
        events.append("schema_audit")
        assert actual_session is session
        return _SCHEMA

    monkeypatch.setattr(drill, "collect_offline_restore_evidence", collector or collect)
    monkeypatch.setattr(drill, "audit_restored_schema", schema_audit or audit_schema)
    result = drill.run_isolated_restore_drill(
        copy_dir=copy_dir, objects_root=mirror, restore_database=restore_database,
        target_bucket="isolated-bucket", object_client=objects,
        target_blobs=_Blobs(
            objects, events,
            missing=(evidence.bound_objects[missing_blob_index].blob_id
                     if missing_blob_index is not None else None),
        ),  # type: ignore[arg-type]
    )
    return result, objects, events


def test_coordinator_restores_db_before_target_write_then_reads_all_target_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    copy_dir, mirror, evidence = _copy(tmp_path)
    result, objects, events = _run(copy_dir, mirror, evidence, monkeypatch)
    assert events.index("db_restore") < events.index("schema_audit") < events.index("db_audit")
    assert events.index("db_audit") < events.index("put")
    assert result.schema == _SCHEMA
    assert events.index("put") < events.index("blob_read") < events.index("db_close")
    assert result.dump_sha256 == _sha((copy_dir / "db.dump").read_bytes())
    assert result.target_objects.count == result.target_blobs.count == 2
    assert result.target_objects.bytes_read == result.target_blobs.bytes_read == sum(map(len, _PAYLOADS))
    assert result.source_counts == (("norm_retrieval_set", 1),)
    assert objects.puts == 2
    second, objects_again, _ = _run(copy_dir, mirror, evidence, monkeypatch, object_client=objects)
    assert second == result and objects_again.puts == 2


def test_bad_copy_stops_before_database_restore_or_target_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    copy_dir, mirror, evidence = _copy(tmp_path)
    (copy_dir / "db.dump").write_bytes(b"changed")
    events: list[str] = []
    with pytest.raises(RecoveryPreflightRefused):
        _run(copy_dir, mirror, evidence, monkeypatch,
             collector=lambda *_: pytest.fail("DB audit reached"), events_sink=events)
    assert events == []


def test_wrong_restored_fingerprint_stops_before_database_audit_or_target_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    copy_dir, mirror, evidence = _copy(tmp_path)
    events: list[str] = []
    with pytest.raises(drill.IsolatedRestoreDrillRefused, match="fingerprint"):
        _run(copy_dir, mirror, evidence, monkeypatch, fingerprint="0" * 64,
             collector=lambda *_: pytest.fail("DB audit reached"), events_sink=events)
    assert events == ["db_restore", "db_close"]


def test_db_audit_failure_prevents_target_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    copy_dir, mirror, evidence = _copy(tmp_path)
    def refuse(*_: object) -> OfflineRestoreEvidence:
        raise BlobReferenceAuditRefused("missing catalogue Blob")
    events: list[str] = []
    with pytest.raises(BlobReferenceAuditRefused, match="catalogue"):
        _run(copy_dir, mirror, evidence, monkeypatch, collector=refuse, events_sink=events)
    assert events == ["db_restore", "schema_audit", "db_close"]


@pytest.mark.parametrize("missing_index", (0, 1))
def test_target_missing_either_verified_set_blob_prevents_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing_index: int,
) -> None:
    copy_dir, mirror, evidence = _copy(tmp_path)
    with pytest.raises(BlobNotFoundError):
        _run(copy_dir, mirror, evidence, monkeypatch, missing_blob_index=missing_index)


def test_metadata_drift_after_db_read_prevents_target_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    copy_dir, mirror, evidence = _copy(tmp_path)
    def drift(*_: object) -> OfflineRestoreEvidence:
        record = copy_dir / "record.json"
        record.write_bytes(record.read_bytes().replace(b'"state": "open"', b'"state": "closed"'))
        return evidence
    events: list[str] = []
    with pytest.raises(drill.IsolatedRestoreDrillRefused, match="before target"):
        _run(copy_dir, mirror, evidence, monkeypatch, collector=drift, events_sink=events)
    assert events == ["db_restore", "schema_audit", "db_close"]


@pytest.mark.parametrize("tables", (
    FINGERPRINTED_TABLES - {"price_list_revision"},
    FINGERPRINTED_TABLES | {"price_list_revision_extra"},
), ids=("table-missing", "table-unknown"))
def test_a_record_with_another_table_set_stops_before_database_restore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tables: frozenset[str],
) -> None:
    """A copy whose fingerprint omits (or adds) a table was taken at another schema."""
    copy_dir, mirror, evidence = _copy(tmp_path, tables=frozenset(tables))
    events: list[str] = []
    with pytest.raises(drill.IsolatedRestoreDrillRefused, match="declared schema"):
        _run(copy_dir, mirror, evidence, monkeypatch, events_sink=events)
    assert events == []


def test_schema_audit_failure_prevents_blob_audit_and_target_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    copy_dir, mirror, evidence = _copy(tmp_path)

    def refuse(_: object) -> RestoredSchemaAudit:
        raise RestoredSchemaRefused("triggers differ")

    events: list[str] = []
    with pytest.raises(RestoredSchemaRefused, match="triggers"):
        _run(copy_dir, mirror, evidence, monkeypatch, schema_audit=refuse,
             collector=lambda *_: pytest.fail("Blob audit reached"), events_sink=events)
    assert events == ["db_restore", "db_close"]
