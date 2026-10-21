"""The synthetic builder prepares only a private, locally verifiable copy."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest

from auditmanager.storage.public import BlobId, canonical_object_key_for_recovery, derive_blob_id
from scripts.recovery.offline_restore_preflight import verify_offline_restore_inputs
from scripts.recovery.schema_coverage import FINGERPRINTED_TABLES, HEAD
from scripts.recovery.synthetic_drill_fixture import (
    SyntheticFixtureRefused,
    prepare_copy_from_bucket,
    prepare_synthetic_copy,
)

STAMP = "20261016T120000Z"
INSTANCE = "auditmanager-w58-synthetic-source-01"
TREE = "a" * 40
PAYLOAD = b"one positive synthetic Blob"
SECOND = b"a second positive synthetic Blob, a crop"


def _lines(tables: frozenset[str] = FINGERPRINTED_TABLES) -> bytes:
    return "".join(f"{name}|1|{'b' * 64}\n" for name in sorted(tables)).encode("ascii")


LINE = _lines().decode("ascii")


def _private(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    path.chmod(0o600)
    return path


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    return (
        _private(tmp_path / "input.dump", b"PGDMP\x00synthetic-header-only"),
        _private(tmp_path / "fingerprint.lines", _lines()),
        _private(tmp_path / "payload.bin", PAYLOAD),
    )


def _prepare(tmp_path: Path, *, dump: Path | None = None,
             lines: Path | None = None, payloads: tuple[Path, ...] | None = None):
    actual_dump, actual_lines, actual_payload = _inputs(tmp_path)
    return prepare_synthetic_copy(
        dump_path=dump or actual_dump,
        fingerprint_lines_path=lines or actual_lines,
        payload_paths=payloads or (actual_payload,),
        output_root=tmp_path / "synthetic-copy", stamp=STAMP,
        instance=INSTANCE, tree_sha=TREE,
    )


def test_builds_one_positive_blob_and_canonical_private_copy(tmp_path: Path) -> None:
    copy_dir, mirror, blob_ids = _prepare(tmp_path)
    verify_offline_restore_inputs(copy_dir, mirror)
    digest = hashlib.sha256(PAYLOAD).hexdigest()
    expected_id = str(derive_blob_id(sha256=digest, size=len(PAYLOAD)))
    key = canonical_object_key_for_recovery(BlobId(expected_id))
    assert blob_ids == (expected_id,)
    assert (mirror / key).read_bytes() == PAYLOAD
    assert (copy_dir / "inventory.tsv").read_bytes() == (
        f"{key}\t{len(PAYLOAD)}\tsynthetic-local-{digest[:16]}\n".encode("ascii")
    )
    record = json.loads((copy_dir / "record.json").read_bytes())
    assert record["instance"] == INSTANCE and record["real_data_marker"] is False
    assert record["migration_head"] == HEAD
    assert set(record["fingerprint"]["tables"]) == FINGERPRINTED_TABLES
    assert record["fingerprint"]["sha256"] == hashlib.sha256(LINE.encode("ascii")).hexdigest()
    assert all((path.stat().st_mode & 0o077) == 0 for path in (
        copy_dir, mirror, mirror / "blobs", mirror / key, copy_dir / "db.dump",
    ))


def test_several_payloads_become_one_sorted_inventory_and_seal(tmp_path: Path) -> None:
    dump, lines, first = _inputs(tmp_path)
    second = _private(tmp_path / "second.bin", SECOND)
    copy_dir, mirror, blob_ids = _prepare(tmp_path, payloads=(first, second))
    verify_offline_restore_inputs(copy_dir, mirror)
    assert len(blob_ids) == 2 and blob_ids[0] != blob_ids[1]
    keys = [canonical_object_key_for_recovery(BlobId(blob_id)) for blob_id in blob_ids]
    inventory = (copy_dir / "inventory.tsv").read_bytes().decode("ascii").splitlines()
    assert [row.split("\t")[0] for row in inventory] == sorted(keys)
    record = json.loads((copy_dir / "record.json").read_bytes())
    assert record["inventory"]["count"] == 2
    assert record["inventory"]["bytes"] == len(PAYLOAD) + len(SECOND)
    assert json.loads((copy_dir / "objects.json").read_bytes())["count"] == 2


@pytest.mark.parametrize("repeat", (True, False), ids=("same-payload-twice", "no-payload"))
def test_the_same_payload_twice_and_no_payload_refuse_without_output(
    tmp_path: Path, repeat: bool,
) -> None:
    dump, lines, payload = _inputs(tmp_path)
    with pytest.raises(SyntheticFixtureRefused, match="payload"):
        prepare_synthetic_copy(
            dump_path=dump, fingerprint_lines_path=lines,
            payload_paths=(payload, payload) if repeat else (),
            output_root=tmp_path / "synthetic-copy", stamp=STAMP,
            instance=INSTANCE, tree_sha=TREE,
        )
    assert not (tmp_path / "synthetic-copy").exists()


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
            dump_path=dump, fingerprint_lines_path=lines, payload_paths=(payload,),
            output_root=tmp_path / "synthetic-copy", stamp=STAMP,
            instance=INSTANCE, tree_sha=TREE,
        )
    assert not (tmp_path / "synthetic-copy").exists()


@pytest.mark.parametrize("tables,message", (
    (FINGERPRINTED_TABLES - {"price_list_revision"}, "missing=.*price_list_revision"),
    (FINGERPRINTED_TABLES | {"zz_unknown"}, "unknown=.*zz_unknown"),
    (frozenset({"blob"}), "declared schema"),
), ids=("table-missing", "table-unknown", "head-0023-sized-subset"))
def test_fingerprint_lines_must_name_exactly_the_declared_tables(
    tmp_path: Path, tables: frozenset[str], message: str,
) -> None:
    dump, lines, payload = _inputs(tmp_path)
    _private(lines, _lines(frozenset(tables)))
    with pytest.raises(SyntheticFixtureRefused, match=message):
        prepare_synthetic_copy(
            dump_path=dump, fingerprint_lines_path=lines, payload_paths=(payload,),
            output_root=tmp_path / "synthetic-copy", stamp=STAMP,
            instance=INSTANCE, tree_sha=TREE,
        )
    assert not (tmp_path / "synthetic-copy").exists()


def test_public_or_linked_input_refuses_without_output(tmp_path: Path) -> None:
    dump, lines, payload = _inputs(tmp_path)
    payload.chmod(0o644)
    with pytest.raises(SyntheticFixtureRefused, match="Blob payload"):
        prepare_synthetic_copy(
            dump_path=dump, fingerprint_lines_path=lines, payload_paths=(payload,),
            output_root=tmp_path / "synthetic-copy", stamp=STAMP,
            instance=INSTANCE, tree_sha=TREE,
        )
    payload.chmod(0o600)
    alias = tmp_path / "payload-link"
    alias.symlink_to(payload)
    with pytest.raises(SyntheticFixtureRefused, match="Blob payload"):
        prepare_synthetic_copy(
            dump_path=dump, fingerprint_lines_path=lines, payload_paths=(alias,),
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
            dump_path=dump, fingerprint_lines_path=lines, payload_paths=(payload,),
            output_root=root, stamp=STAMP, instance=INSTANCE, tree_sha=TREE,
        )
    root.rmdir()
    _private(dump, b"not-a-PG-dump")
    with pytest.raises(SyntheticFixtureRefused, match="custom-format"):
        prepare_synthetic_copy(
            dump_path=dump, fingerprint_lines_path=lines, payload_paths=(payload,),
            output_root=root, stamp=STAMP, instance=INSTANCE, tree_sha=TREE,
        )


# --- the source bucket as the object source ------------------------------------------------------


class _Bucket:
    """A boto3-like source: paged listing with quoted ETags, conditional GetObject."""

    def __init__(self, objects: dict[str, bytes], *, page: int = 2) -> None:
        self.objects = objects
        self.page = page
        self.reads: list[str] = []

    @staticmethod
    def etag(data: bytes) -> str:
        return hashlib.md5(data, usedforsecurity=False).hexdigest()

    def list_objects_v2(self, *, Bucket: str, ContinuationToken: str | None = None) -> dict[str, object]:
        assert Bucket == "source-bucket"
        keys = sorted(self.objects)
        start = int(ContinuationToken or 0)
        chunk = keys[start:start + self.page]
        truncated = start + self.page < len(keys)
        return {
            "Contents": [{"Key": k, "Size": len(self.objects[k]), "ETag": f'"{self.etag(self.objects[k])}"'}
                         for k in chunk],
            "IsTruncated": truncated,
            **({"NextContinuationToken": str(start + self.page)} if truncated else {}),
        }

    def get_object(self, *, Bucket: str, Key: str, IfMatch: str) -> dict[str, object]:
        assert Bucket == "source-bucket"
        data = self.objects[Key]
        assert IfMatch == f'"{self.etag(data)}"'
        self.reads.append(Key)
        return {"Body": io.BytesIO(data), "ContentLength": len(data), "ETag": f'"{self.etag(data)}"'}


def _bucket_objects() -> dict[str, bytes]:
    objects = {}
    for payload in (PAYLOAD, SECOND, b"a third", b"a fourth, a text layer"):
        blob_id = str(derive_blob_id(sha256=hashlib.sha256(payload).hexdigest(), size=len(payload)))
        objects[canonical_object_key_for_recovery(BlobId(blob_id))] = payload
    return objects


def test_bucket_copy_lists_pages_pulls_every_object_and_keeps_the_real_etags(tmp_path: Path) -> None:
    dump, lines, _ = _inputs(tmp_path)
    bucket = _Bucket(_bucket_objects())
    copy_dir, mirror, count = prepare_copy_from_bucket(
        dump_path=dump, fingerprint_lines_path=lines, source_client=bucket,
        source_bucket="source-bucket", output_root=tmp_path / "bucket-copy", stamp=STAMP,
        instance=INSTANCE, tree_sha=TREE,
    )
    verify_offline_restore_inputs(copy_dir, mirror)
    assert count == 4 and sorted(bucket.reads) == sorted(bucket.objects)
    rows = [row.split("\t") for row in (copy_dir / "inventory.tsv").read_bytes().decode().splitlines()]
    assert rows == [[key, str(len(data)), _Bucket.etag(data)] for key, data in sorted(bucket.objects.items())]
    assert all((mirror / key).read_bytes() == data for key, data in bucket.objects.items())
    record = json.loads((copy_dir / "record.json").read_bytes())
    assert record["inventory"]["count"] == 4 and record["migration_head"] == HEAD


@pytest.mark.parametrize("change", ("empty", "foreign_key", "changed_after_listing"))
def test_bucket_copy_refuses_an_empty_foreign_or_changing_source(tmp_path: Path, change: str) -> None:
    dump, lines, _ = _inputs(tmp_path)
    objects = {} if change == "empty" else _bucket_objects()
    if change == "foreign_key":
        objects["notes/readme.txt"] = b"not a Blob"
    bucket = _Bucket(objects)
    if change == "changed_after_listing":
        original = bucket.list_objects_v2

        def list_then_change(**kwargs: object) -> dict[str, object]:
            page = original(**kwargs)  # type: ignore[arg-type]
            if not page["IsTruncated"]:
                bucket.objects[next(iter(sorted(bucket.objects)))] = b"overwritten after the listing"
            return page

        bucket.list_objects_v2 = list_then_change  # type: ignore[method-assign]
    with pytest.raises(SyntheticFixtureRefused):
        prepare_copy_from_bucket(
            dump_path=dump, fingerprint_lines_path=lines, source_client=bucket,
            source_bucket="source-bucket", output_root=tmp_path / "bucket-copy", stamp=STAMP,
            instance=INSTANCE, tree_sha=TREE,
        )
