"""A local restore must consume one unchanged W54/W58 byte set."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.recovery.object_copy import build_manifest, manifest_bytes
from scripts.recovery.offline_restore_preflight import (
    RecoveryPreflightRefused,
    main,
    verify_offline_restore_inputs,
)

_STAMP = "20261015T120000Z"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _record_bytes(record: dict[str, object]) -> bytes:
    lines = [
        f'  "{key}": {json.dumps(value, ensure_ascii=True, separators=(", ", ": "))}'
        for key, value in record.items()
    ]
    return ("{\n" + ",\n".join(lines) + "\n}\n").encode("ascii")


def _copy(tmp_path: Path, *, dump: bytes = b"PGDMP\x00fake dump") -> tuple[Path, Path]:
    copy_dir = tmp_path / _STAMP
    mirror = tmp_path / "mirror"
    copy_dir.mkdir(mode=0o700)
    (mirror / "blobs/00").mkdir(parents=True)
    mirror.chmod(0o700)
    (mirror / "blobs/00/one").write_bytes(b"first payload")
    (mirror / "blobs/00/two").write_bytes(b"")
    inventory = b"blobs/00/one\t13\tfirst-etag\nblobs/00/two\t0\tsecond-etag\n"
    record: dict[str, object] = {
        "record_version": 1,
        "kind": "copy",
        "stamp": _STAMP,
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
        "dump": {"file": "db.dump", "size_bytes": len(dump), "sha256": _sha(dump)},
        "fingerprint": {
            "algorithm": "stand-fingerprint-v1", "sha256": "c" * 64,
            "tables": {"project": {"rows": 1, "sha256": "d" * 64}},
        },
        "rejected_blob_count": 0,
        "inventory": {"file": "inventory.tsv", "count": 2, "bytes": 13, "sha256": _sha(inventory)},
        "attestation": None,
        "waiver": None,
        "real_data_marker": False,
        "restored_at": None,
        "closed_at": None,
    }
    (copy_dir / "record.json").write_bytes(_record_bytes(record))
    (copy_dir / "db.dump").write_bytes(dump)
    (copy_dir / "inventory.tsv").write_bytes(inventory)
    (copy_dir / "objects.json").write_bytes(manifest_bytes(build_manifest(inventory, mirror)))
    return copy_dir, mirror


def test_complete_inputs_pass_repeatedly_without_writes(tmp_path: Path) -> None:
    copy_dir, mirror = _copy(tmp_path)
    before = {path.name: path.read_bytes() for path in copy_dir.iterdir()}
    verify_offline_restore_inputs(copy_dir, mirror)
    verify_offline_restore_inputs(copy_dir, mirror)
    assert main([str(copy_dir), str(mirror)]) == 0
    assert {path.name: path.read_bytes() for path in copy_dir.iterdir()} == before


@pytest.mark.parametrize("change", ("same_size_dump", "truncated_dump", "empty_dump"))
def test_dump_must_match_record_bytes(tmp_path: Path, change: str) -> None:
    copy_dir, mirror = _copy(tmp_path)
    replacement = {
        "same_size_dump": b"XGDMP\x00fake dump",
        "truncated_dump": b"PGDMP",
        "empty_dump": b"",
    }[change]
    (copy_dir / "db.dump").write_bytes(replacement)
    with pytest.raises(RecoveryPreflightRefused, match="db.dump size or SHA-256"):
        verify_offline_restore_inputs(copy_dir, mirror)


def test_large_dump_is_hashed_in_chunks(tmp_path: Path) -> None:
    copy_dir, mirror = _copy(tmp_path, dump=b"x" * (2 * 1024 * 1024 + 17))
    verify_offline_restore_inputs(copy_dir, mirror)


@pytest.mark.parametrize("change", ("inventory", "seal", "mirror"))
def test_copy_and_mirror_must_remain_bound(tmp_path: Path, change: str) -> None:
    copy_dir, mirror = _copy(tmp_path)
    if change == "inventory":
        (copy_dir / "inventory.tsv").write_bytes(b"blobs/00/one\t13\twrong-etag\n")
    elif change == "seal":
        (copy_dir / "objects.json").write_bytes(b"{}\n")
    else:
        (mirror / "blobs/00/one").write_bytes(b"other payload")
    with pytest.raises(RecoveryPreflightRefused):
        verify_offline_restore_inputs(copy_dir, mirror)


def test_rejects_symlinked_dump_and_mirror(tmp_path: Path) -> None:
    copy_dir, mirror = _copy(tmp_path)
    dump = copy_dir / "db.dump"
    dump.rename(copy_dir / "dump.actual")
    dump.symlink_to(copy_dir / "dump.actual")
    with pytest.raises(RecoveryPreflightRefused):
        verify_offline_restore_inputs(copy_dir, mirror)
    dump.unlink()
    (copy_dir / "dump.actual").rename(dump)
    alias = tmp_path / "mirror-alias"
    alias.symlink_to(mirror, target_is_directory=True)
    with pytest.raises(RecoveryPreflightRefused):
        verify_offline_restore_inputs(copy_dir, alias)


def test_refuses_public_directory_and_wrong_stamp(tmp_path: Path) -> None:
    copy_dir, mirror = _copy(tmp_path)
    copy_dir.chmod(0o755)
    with pytest.raises(RecoveryPreflightRefused, match="private directory"):
        verify_offline_restore_inputs(copy_dir, mirror)
    copy_dir.chmod(0o700)
    wrong = tmp_path / "wrong-stamp"
    copy_dir.rename(wrong)
    with pytest.raises(RecoveryPreflightRefused, match="record stamp"):
        verify_offline_restore_inputs(wrong, mirror)


def test_rejects_replaced_record_during_mirror_scan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    copy_dir, mirror = _copy(tmp_path)
    from scripts.recovery import offline_restore_preflight as preflight

    original_verify = preflight.verify_manifest

    def replace_after_verify(inventory: bytes, root: Path, sealed: bytes) -> None:
        original_verify(inventory, root, sealed)
        record = copy_dir / "record.json"
        replacement = copy_dir / "replacement"
        replacement.write_bytes(record.read_bytes())
        replacement.replace(record)

    monkeypatch.setattr(preflight, "verify_manifest", replace_after_verify)
    with pytest.raises(RecoveryPreflightRefused, match="record.json changed"):
        verify_offline_restore_inputs(copy_dir, mirror)
