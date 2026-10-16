"""The synthetic builder prepares only a private, locally verifiable copy."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from auditmanager.storage.public import BlobId, canonical_object_key_for_recovery, derive_blob_id
from scripts.recovery.offline_restore_preflight import verify_offline_restore_inputs
from scripts.recovery.synthetic_drill_fixture import SyntheticFixtureRefused, prepare_synthetic_copy

STAMP = "20261016T120000Z"
INSTANCE = "auditmanager-w58-synthetic-source-01"
TREE = "a" * 40
PAYLOAD = b"one positive synthetic Blob"
LINE = f"blob|1|{'b' * 64}\n"


def _private(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    path.chmod(0o600)
    return path


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    return (
        _private(tmp_path / "input.dump", b"PGDMP\x00synthetic-header-only"),
        _private(tmp_path / "fingerprint.lines", LINE.encode("ascii")),
        _private(tmp_path / "payload.bin", PAYLOAD),
    )


def _prepare(tmp_path: Path, *, dump: Path | None = None,
             lines: Path | None = None, payload: Path | None = None):
    actual_dump, actual_lines, actual_payload = _inputs(tmp_path)
    return prepare_synthetic_copy(
        dump_path=dump or actual_dump,
        fingerprint_lines_path=lines or actual_lines,
        payload_path=payload or actual_payload,
        output_root=tmp_path / "synthetic-copy", stamp=STAMP,
        instance=INSTANCE, tree_sha=TREE,
    )


def test_builds_one_positive_blob_and_canonical_private_copy(tmp_path: Path) -> None:
    copy_dir, mirror, blob_id = _prepare(tmp_path)
    verify_offline_restore_inputs(copy_dir, mirror)
    digest = hashlib.sha256(PAYLOAD).hexdigest()
    expected_id = str(derive_blob_id(sha256=digest, size=len(PAYLOAD)))
    key = canonical_object_key_for_recovery(BlobId(expected_id))
    assert blob_id == expected_id
    assert (mirror / key).read_bytes() == PAYLOAD
    assert (copy_dir / "inventory.tsv").read_bytes() == (
        f"{key}\t{len(PAYLOAD)}\tsynthetic-local-{digest[:16]}\n".encode("ascii")
    )
    record = json.loads((copy_dir / "record.json").read_bytes())
    assert record["instance"] == INSTANCE and record["real_data_marker"] is False
    assert record["fingerprint"]["tables"]["blob"]["rows"] == 1
    assert record["fingerprint"]["sha256"] == hashlib.sha256(LINE.encode("ascii")).hexdigest()
    assert all((path.stat().st_mode & 0o077) == 0 for path in (
        copy_dir, mirror, mirror / "blobs", mirror / key, copy_dir / "db.dump",
    ))


@pytest.mark.parametrize("bad_lines", (
    b"blob|1|" + b"b" * 64,  # no final LF
    b"blob|1|" + b"b" * 64 + b"\nblob|1|" + b"b" * 64 + b"\n",
    b"z|0|" + b"b" * 64 + b"\na|0|" + b"b" * 64 + b"\n",
))
def test_malformed_fingerprint_refuses_without_output(tmp_path: Path, bad_lines: bytes) -> None:
    dump, lines, payload = _inputs(tmp_path)
    _private(lines, bad_lines)
    with pytest.raises(SyntheticFixtureRefused, match="fingerprint"):
        prepare_synthetic_copy(
            dump_path=dump, fingerprint_lines_path=lines, payload_path=payload,
            output_root=tmp_path / "synthetic-copy", stamp=STAMP,
            instance=INSTANCE, tree_sha=TREE,
        )
    assert not (tmp_path / "synthetic-copy").exists()


def test_public_or_linked_input_refuses_without_output(tmp_path: Path) -> None:
    dump, lines, payload = _inputs(tmp_path)
    payload.chmod(0o644)
    with pytest.raises(SyntheticFixtureRefused, match="Blob payload"):
        prepare_synthetic_copy(
            dump_path=dump, fingerprint_lines_path=lines, payload_path=payload,
            output_root=tmp_path / "synthetic-copy", stamp=STAMP,
            instance=INSTANCE, tree_sha=TREE,
        )
    payload.chmod(0o600)
    alias = tmp_path / "payload-link"
    alias.symlink_to(payload)
    with pytest.raises(SyntheticFixtureRefused, match="Blob payload"):
        prepare_synthetic_copy(
            dump_path=dump, fingerprint_lines_path=lines, payload_path=alias,
            output_root=tmp_path / "synthetic-copy", stamp=STAMP,
            instance=INSTANCE, tree_sha=TREE,
        )
    assert not (tmp_path / "synthetic-copy").exists()


def test_existing_output_and_wrong_dump_header_refuse(tmp_path: Path) -> None:
    dump, lines, payload = _inputs(tmp_path)
    root = tmp_path / "synthetic-copy"
    root.mkdir()
    with pytest.raises(SyntheticFixtureRefused, match="output root"):
        prepare_synthetic_copy(
            dump_path=dump, fingerprint_lines_path=lines, payload_path=payload,
            output_root=root, stamp=STAMP, instance=INSTANCE, tree_sha=TREE,
        )
    root.rmdir()
    _private(dump, b"not-a-PG-dump")
    with pytest.raises(SyntheticFixtureRefused, match="custom-format"):
        prepare_synthetic_copy(
            dump_path=dump, fingerprint_lines_path=lines, payload_path=payload,
            output_root=root, stamp=STAMP, instance=INSTANCE, tree_sha=TREE,
        )
