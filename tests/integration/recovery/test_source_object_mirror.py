"""Fake-S3 refusal and retry evidence for the unactivated W58 source mirror."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from scripts.recovery.object_copy import verify_manifest
from scripts.recovery.source_object_mirror import (
    SourceObjectMirrorRefused,
    mirror_source_objects,
)

ONE = "blobs/00/one"
TWO = "blobs/00/two"
INVENTORY = b"blobs/00/one\t13\tfirst-etag\nblobs/00/two\t0\tsecond-etag\n"


class FakeBody:
    def __init__(self, payload: bytes, *, broken: bool = False, nonbytes: bool = False) -> None:
        self.payload = payload
        self.broken = broken
        self.nonbytes = nonbytes
        self.reads = 0
        self.closed = False

    def read(self, amount: int) -> bytes | str:
        self.reads += 1
        if self.broken:
            raise OSError("transport interrupted")
        if self.nonbytes:
            return "not bytes"
        value, self.payload = self.payload[:amount], self.payload[amount:]
        return value

    def close(self) -> None:
        self.closed = True


class FakeReader:
    def __init__(self) -> None:
        self.payloads = {ONE: b"first payload", TWO: b""}
        self.etags = {ONE: "first-etag", TWO: "second-etag"}
        self.declared: dict[str, int] = {}
        self.broken: set[str] = set()
        self.nonbytes: set[str] = set()
        self.fail_get: set[str] = set()
        self.bodies: list[FakeBody] = []
        self.calls: list[tuple[str, str, str]] = []

    def get_object(self, *, Bucket: str, Key: str, IfMatch: str):
        self.calls.append((Bucket, Key, IfMatch))
        if Key in self.fail_get:
            raise OSError("private endpoint name")
        body = FakeBody(
            self.payloads[Key], broken=Key in self.broken,
            nonbytes=Key in self.nonbytes,
        )
        self.bodies.append(body)
        return {
            "Body": body,
            "ETag": f'"{self.etags[Key]}"',
            "ContentLength": self.declared.get(Key, len(self.payloads[Key])),
        }


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "objects"
    root.mkdir(mode=0o700)
    return root


def _mirror(root: Path, reader: FakeReader, inventory: bytes = INVENTORY):
    return mirror_source_objects(
        inventory_data=inventory, objects_root=root,
        bucket="private-bucket", reader=reader,
    )


def test_every_source_payload_is_streamed_and_handed_to_full_manifest(tmp_path: Path) -> None:
    root, reader = _root(tmp_path), FakeReader()
    result = _mirror(root, reader)
    assert result.count == 2 and result.size_bytes == 13
    assert result.inventory_sha256 == hashlib.sha256(INVENTORY).hexdigest()
    assert reader.calls == [
        ("private-bucket", ONE, '"first-etag"'),
        ("private-bucket", TWO, '"second-etag"'),
    ]
    assert all(body.closed for body in reader.bodies)
    assert (root / ONE).read_bytes() == b"first payload"
    assert (root / TWO).read_bytes() == b""
    assert (root / ONE).stat().st_mode & 0o077 == 0
    assert (root / "blobs/00").stat().st_mode & 0o077 == 0
    verify_manifest(INVENTORY, root, result.manifest)
    assert b'"sha256":"' + hashlib.sha256(b"first payload").hexdigest().encode() in result.manifest
    assert list(root.rglob(".source-object-*")) == []
    assert _mirror(root, reader) == result  # repeated source read, no overwrite


def test_empty_inventory_has_an_empty_exact_manifest_and_no_source_calls(tmp_path: Path) -> None:
    root, reader = _root(tmp_path), FakeReader()
    result = _mirror(root, reader, b"")
    assert result.count == 0 and result.size_bytes == 0 and reader.calls == []
    verify_manifest(b"", root, result.manifest)


@pytest.mark.parametrize("inventory", (
    b"blobs/../escape\t1\tetag\n",
    b"blobs/00/one\t13\te\nblobs/00/one\t13\te\n",
    b"blobs/00/two\t0\te\nblobs/00/one\t13\te\n",
    b"blobs/00/one\t13\te",
    b"blobs/00/one\t13\t\n",  # no usable IfMatch token
))
def test_bad_inventory_never_yields_a_complete_mirror(tmp_path: Path, inventory: bytes) -> None:
    root, reader = _root(tmp_path), FakeReader()
    with pytest.raises(SourceObjectMirrorRefused):
        _mirror(root, reader, inventory)
    assert not (root / ONE).exists()


@pytest.mark.parametrize("fault, reason", (
    ("get", "source GetObject failed"),
    ("etag", "source ETag differs"),
    ("header_short", "source ContentLength differs"),
    ("header_long", "source ContentLength differs"),
    ("body_short", "source body is shorter"),
    ("body_long", "source body exceeds"),
    ("broken", "source body read failed"),
    ("nonbytes", "source body returned a non-byte"),
))
def test_bad_source_stream_refuses_and_removes_partial_temp(
    tmp_path: Path, fault: str, reason: str,
) -> None:
    root, reader = _root(tmp_path), FakeReader()
    if fault == "get":
        reader.fail_get.add(ONE)
    elif fault == "etag":
        reader.etags[ONE] = "different-etag"
    elif fault == "header_short":
        reader.declared[ONE] = 12
    elif fault == "header_long":
        reader.declared[ONE] = 14
    elif fault == "body_short":
        reader.payloads[ONE] = b"short"
        reader.declared[ONE] = 13
    elif fault == "body_long":
        reader.payloads[ONE] = b"payload longer than inventory"
        reader.declared[ONE] = 13
    elif fault == "broken":
        reader.broken.add(ONE)
    else:
        reader.nonbytes.add(ONE)
    with pytest.raises(SourceObjectMirrorRefused, match=reason):
        _mirror(root, reader)
    assert not (root / ONE).exists()
    assert list(root.rglob(".source-object-*")) == []
    assert all(body.closed for body in reader.bodies)


def test_interrupted_transfer_retries_without_overwriting_verified_prior_object(
    tmp_path: Path,
) -> None:
    root, reader = _root(tmp_path), FakeReader()
    reader.broken.add(TWO)
    with pytest.raises(SourceObjectMirrorRefused, match="source body read failed"):
        _mirror(root, reader)
    original = (root / ONE).read_bytes()
    assert not (root / TWO).exists()
    assert list(root.rglob(".source-object-*")) == []

    reader.broken.clear()
    result = _mirror(root, reader)
    verify_manifest(INVENTORY, root, result.manifest)
    assert (root / ONE).read_bytes() == original
    assert reader.calls.count(("private-bucket", ONE, '"first-etag"')) == 2

    reader.payloads[ONE] = b"other payload"  # same length and declared ETag
    with pytest.raises(SourceObjectMirrorRefused, match="existing mirror object differs"):
        _mirror(root, reader)
    assert (root / ONE).read_bytes() == original
    assert list(root.rglob(".source-object-*")) == []


def test_private_no_follow_paths_and_extra_objects_are_refused(tmp_path: Path) -> None:
    root, reader = _root(tmp_path), FakeReader()
    root.chmod(0o755)
    with pytest.raises(SourceObjectMirrorRefused, match="owner-private"):
        _mirror(root, reader)
    root.chmod(0o700)
    (root / "blobs").symlink_to(tmp_path)
    with pytest.raises(SourceObjectMirrorRefused, match="path or write failed"):
        _mirror(root, reader)
    (root / "blobs").unlink()
    (root / "unlisted").write_bytes(b"extra")
    with pytest.raises(SourceObjectMirrorRefused, match="complete mirror differs"):
        _mirror(root, reader)


def test_existing_symlink_and_hardlink_are_never_accepted_or_overwritten(tmp_path: Path) -> None:
    root, reader = _root(tmp_path), FakeReader()
    target = root / ONE
    target.parent.mkdir(parents=True, mode=0o700)
    (root / "blobs").chmod(0o700)
    target.symlink_to(tmp_path / "outside")
    with pytest.raises(SourceObjectMirrorRefused, match="existing mirror object is unsafe"):
        _mirror(root, reader)
    target.unlink()
    outside = tmp_path / "outside"
    outside.write_bytes(b"first payload")
    os.link(outside, target)
    with pytest.raises(SourceObjectMirrorRefused, match="owner-private"):
        _mirror(root, reader)
    assert outside.read_bytes() == b"first payload"
