"""W58 target object restore: complete bytes, retry and refusal semantics."""

from __future__ import annotations

import io
import hashlib
from pathlib import Path

import pytest

from auditmanager.storage.public import (
    BlobId, BlobMetadataInvalidError, BlobIntegrityError, S3BlobStore, S3StorageSettings,
    canonical_object_key_for_recovery, derive_blob_id,
)
from scripts.recovery.object_copy import build_manifest, manifest_bytes
from scripts.recovery.target_object_restore import (
    TargetObjectRestoreRefused,
    restore_sealed_objects,
)

ONE = "blobs/00/one"
TWO = "blobs/00/two"
INVENTORY = b"blobs/00/one\t5\tfirst-etag\nblobs/00/two\t0\tsecond-etag\n"


class FakeClient:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.metadata: dict[str, dict[str, str]] = {}
        self.puts: list[str] = []
        self.gets: list[str] = []
        self.list_calls = 0
        self.fail_put: set[str] = set()
        self.corrupt_get: set[str] = set()
        self.short_get: set[str] = set()
        self.nonbytes_get: set[str] = set()
        self.closed: list[str] = []

    def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
        assert kwargs["Bucket"] == "isolated-bucket"
        self.list_calls += 1
        keys = sorted(self.objects)
        start = int(kwargs.get("ContinuationToken", "0"))
        current = keys[start:start + 1]  # exercise pagination
        next_start = start + len(current)
        page: dict[str, object] = {
            "IsTruncated": next_start < len(keys),
            "Contents": [{"Key": key, "Size": len(self.objects[key])} for key in current],
        }
        if next_start < len(keys):
            page["NextContinuationToken"] = str(next_start)
        return page

    def put_object(self, *, Bucket: str, Key: str, Body: io.BufferedIOBase,
                   ContentLength: int, IfNoneMatch: str,
                   Metadata: dict[str, str] | None = None) -> dict[str, object]:
        assert Bucket == "isolated-bucket" and IfNoneMatch == "*"
        self.puts.append(Key)
        if Key in self.fail_put:
            raise OSError("private endpoint details")
        if Key in self.objects:
            raise OSError("precondition failed")
        payload = Body.read()
        assert len(payload) == ContentLength
        self.objects[Key] = payload
        self.metadata[Key] = dict(Metadata or {})
        return {"ETag": '"opaque-not-a-checksum"'}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        assert Bucket == "isolated-bucket"
        self.gets.append(Key)
        payload = self.objects[Key]
        if Key in self.corrupt_get:
            payload = b"X" + payload[1:]
        body = _Body(payload, self.closed, Key, nonbytes=Key in self.nonbytes_get)
        declared = len(payload) - 1 if Key in self.short_get else len(payload)
        return {"Body": body, "ContentLength": declared,
                "Metadata": self.metadata.get(Key, {})}


class _Body(io.BytesIO):
    def __init__(self, payload: bytes, closed: list[str], key: str, *, nonbytes: bool) -> None:
        super().__init__(payload)
        self.closed_keys = closed
        self.key = key
        self.nonbytes = nonbytes

    def read(self, amount: int = -1) -> bytes | str:
        if self.nonbytes:
            return "bad"
        return super().read(amount)

    def close(self) -> None:
        self.closed_keys.append(self.key)
        super().close()


def _inputs(tmp_path: Path, *, empty: bool = False) -> tuple[Path, bytes, bytes]:
    root = tmp_path / "objects"
    root.mkdir(mode=0o700)
    (root / "blobs").mkdir(mode=0o700)
    (root / "blobs/00").mkdir(mode=0o700)
    inventory = b"" if empty else INVENTORY
    if not empty:
        (root / ONE).write_bytes(b"first")
        (root / TWO).write_bytes(b"")
        (root / ONE).chmod(0o600)
        (root / TWO).chmod(0o600)
    return root, inventory, manifest_bytes(build_manifest(inventory, root))


def _restore(root: Path, inventory: bytes, seal: bytes, client: FakeClient):
    return restore_sealed_objects(
        inventory_data=inventory, sealed_data=seal, objects_root=root,
        target_bucket="isolated-bucket", client=client,
    )


def test_uploads_every_object_and_rereads_exact_target_bytes(tmp_path: Path) -> None:
    root, inventory, seal = _inputs(tmp_path)
    client = FakeClient()
    result = _restore(root, inventory, seal, client)
    assert (result.count, result.bytes_read) == (2, 5)
    assert client.objects == {ONE: b"first", TWO: b""}
    assert client.puts == [ONE, TWO]
    assert client.gets.count(ONE) == client.gets.count(TWO) == 2
    assert client.closed == client.gets
    assert client.list_calls >= 3
    assert _restore(root, inventory, seal, client) == result
    assert client.puts == [ONE, TWO]  # complete retry only reads


def test_restored_canonical_object_is_streamable_through_real_blobstore(tmp_path: Path) -> None:
    payload = b"W58 synthetic positive Blob"
    digest = hashlib.sha256(payload).hexdigest()
    blob_id = derive_blob_id(sha256=digest, size=len(payload))
    key = canonical_object_key_for_recovery(BlobId(str(blob_id)))
    root = tmp_path / "objects"
    root.mkdir(mode=0o700)
    object_path = root / key
    object_path.parent.mkdir(parents=True, mode=0o700)
    for parent in object_path.parents:
        if parent == root:
            break
        parent.chmod(0o700)
    object_path.write_bytes(payload)
    object_path.chmod(0o600)
    inventory = f"{key}\t{len(payload)}\tsynthetic-etag\n".encode("ascii")
    seal = manifest_bytes(build_manifest(inventory, root))
    client = FakeClient()

    _restore(root, inventory, seal, client)
    settings = S3StorageSettings(
        endpoint_url="http://127.0.0.1:61999", region="us-east-1",
        access_key_id="synthetic", secret_access_key="synthetic", bucket="isolated-bucket",
    )
    store = S3BlobStore(settings, client=client)
    assert b"".join(store.open_stream(
        blob_id, expected_sha256=digest, expected_size=len(payload),
    )) == payload
    assert client.metadata[key] == {"content-sha256": digest}

    client.metadata[key].clear()
    with pytest.raises(BlobMetadataInvalidError):
        store.open_stream(blob_id, expected_sha256=digest, expected_size=len(payload))
    client.metadata[key]["content-sha256"] = "0" * 64
    with pytest.raises(BlobIntegrityError):
        store.open_stream(blob_id, expected_sha256=digest, expected_size=len(payload))


def test_interrupted_upload_resumes_only_after_existing_bytes_match(tmp_path: Path) -> None:
    root, inventory, seal = _inputs(tmp_path)
    client = FakeClient()
    client.fail_put.add(TWO)
    with pytest.raises(TargetObjectRestoreRefused, match="PutObject failed"):
        _restore(root, inventory, seal, client)
    assert client.objects == {ONE: b"first"}
    client.fail_put.clear()
    _restore(root, inventory, seal, client)
    assert client.puts == [ONE, TWO, TWO]
    assert client.objects == {ONE: b"first", TWO: b""}


@pytest.mark.parametrize("metadata", ({}, {"content-sha256": "0" * 64}))
def test_existing_exact_bytes_require_sealed_digest_metadata_before_write(
    tmp_path: Path, metadata: dict[str, str],
) -> None:
    root, inventory, seal = _inputs(tmp_path)
    client = FakeClient()
    client.objects[ONE] = b"first"
    client.metadata[ONE] = metadata

    with pytest.raises(TargetObjectRestoreRefused, match="metadata"):
        _restore(root, inventory, seal, client)

    assert client.puts == []
    assert client.objects == {ONE: b"first"}
    assert client.closed == [ONE]


def test_existing_exact_bytes_and_digest_metadata_resume_without_overwrite(tmp_path: Path) -> None:
    root, inventory, seal = _inputs(tmp_path)
    client = FakeClient()
    client.objects[ONE] = b"first"
    client.metadata[ONE] = {"content-sha256": hashlib.sha256(b"first").hexdigest()}

    result = _restore(root, inventory, seal, client)

    assert result.count == 2
    assert client.puts == [TWO]
    assert client.metadata[TWO] == {"content-sha256": hashlib.sha256(b"").hexdigest()}


def test_metadata_change_during_final_readback_refuses(tmp_path: Path) -> None:
    root, inventory, seal = _inputs(tmp_path)

    class ChangingMetadataClient(FakeClient):
        def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
            response = super().get_object(Bucket=Bucket, Key=Key)
            if Key == ONE and self.gets.count(ONE) == 2:
                response["Metadata"] = {}
            return response

    client = ChangingMetadataClient()
    with pytest.raises(TargetObjectRestoreRefused, match="metadata"):
        _restore(root, inventory, seal, client)

    assert client.puts == [ONE, TWO]
    assert client.closed.count(ONE) == 2


@pytest.mark.parametrize("objects", (
    {"foreign/key": b"x"}, {ONE: b"wrong"}, {ONE: b"longer"},
))
def test_foreign_or_changed_existing_target_refuses_before_write(
    tmp_path: Path, objects: dict[str, bytes],
) -> None:
    root, inventory, seal = _inputs(tmp_path)
    client = FakeClient()
    client.objects.update(objects)
    if ONE in objects:
        client.metadata[ONE] = {"content-sha256": hashlib.sha256(b"first").hexdigest()}
    with pytest.raises(TargetObjectRestoreRefused):
        _restore(root, inventory, seal, client)
    assert client.puts == []


@pytest.mark.parametrize("fault", ("corrupt", "header", "nonbytes"))
def test_target_readback_failure_never_returns_success(tmp_path: Path, fault: str) -> None:
    root, inventory, seal = _inputs(tmp_path)
    client = FakeClient()
    client.objects = {ONE: b"first", TWO: b""}
    client.metadata = {
        ONE: {"content-sha256": hashlib.sha256(b"first").hexdigest()},
        TWO: {"content-sha256": hashlib.sha256(b"").hexdigest()},
    }
    if fault == "corrupt":
        client.corrupt_get.add(ONE)
    elif fault == "header":
        client.short_get.add(ONE)
    else:
        client.nonbytes_get.add(ONE)
    with pytest.raises(TargetObjectRestoreRefused):
        _restore(root, inventory, seal, client)
    assert client.puts == [] and client.closed == [ONE]


def test_bad_local_mirror_or_public_root_refuses_before_target_io(tmp_path: Path) -> None:
    root, inventory, seal = _inputs(tmp_path)
    client = FakeClient()
    (root / ONE).write_bytes(b"other")
    with pytest.raises(TargetObjectRestoreRefused, match="local object mirror"):
        _restore(root, inventory, seal, client)
    assert client.list_calls == 0
    (root / ONE).write_bytes(b"first")
    root.chmod(0o755)
    with pytest.raises(TargetObjectRestoreRefused, match="owned private"):
        _restore(root, inventory, seal, client)
    assert client.puts == [] and client.list_calls == 0


def test_empty_sealed_mirror_requires_empty_target(tmp_path: Path) -> None:
    root, inventory, seal = _inputs(tmp_path, empty=True)
    client = FakeClient()
    assert _restore(root, inventory, seal, client).count == 0
    client.objects["foreign/key"] = b"x"
    with pytest.raises(TargetObjectRestoreRefused, match="extra"):
        _restore(root, inventory, seal, client)


def test_cyclic_target_listing_refuses_before_upload(tmp_path: Path) -> None:
    root, inventory, seal = _inputs(tmp_path)

    class CyclicClient(FakeClient):
        def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
            self.list_calls += 1
            return {"IsTruncated": True, "Contents": [], "NextContinuationToken": "same"}

    client = CyclicClient()
    with pytest.raises(TargetObjectRestoreRefused, match="continuation"):
        _restore(root, inventory, seal, client)
    assert client.puts == []


def test_unique_empty_target_pages_refuse_with_seal_bound(tmp_path: Path) -> None:
    root, inventory, seal = _inputs(tmp_path)

    class EmptyPagesClient(FakeClient):
        def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
            self.list_calls += 1
            return {
                "IsTruncated": True, "Contents": [],
                "NextContinuationToken": str(self.list_calls),
            }

    client = EmptyPagesClient()
    with pytest.raises(TargetObjectRestoreRefused, match="listing exceeds seal bound"):
        _restore(root, inventory, seal, client)
    assert client.list_calls == 3
    assert client.puts == []


def test_target_page_larger_than_seal_refuses_before_upload(tmp_path: Path) -> None:
    root, inventory, seal = _inputs(tmp_path)

    class OversizedPageClient(FakeClient):
        def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
            self.list_calls += 1
            return {
                "IsTruncated": False,
                "Contents": [
                    {"Key": f"foreign/{number}", "Size": 1}
                    for number in range(3)
                ],
            }

    client = OversizedPageClient()
    with pytest.raises(TargetObjectRestoreRefused, match="target contains extra objects"):
        _restore(root, inventory, seal, client)
    assert client.list_calls == 1
    assert client.puts == []


def test_concurrent_key_creation_is_not_overwritten(tmp_path: Path) -> None:
    root, inventory, seal = _inputs(tmp_path)

    class RacingClient(FakeClient):
        def put_object(self, **kwargs: object) -> dict[str, object]:
            self.objects[str(kwargs["Key"])] = b"other"
            return super().put_object(**kwargs)  # type: ignore[arg-type]

    client = RacingClient()
    with pytest.raises(TargetObjectRestoreRefused, match="conditional target PutObject"):
        _restore(root, inventory, seal, client)
    assert client.objects == {ONE: b"other"}


def test_foreign_key_appearing_during_copy_refuses_final_inventory(tmp_path: Path) -> None:
    root, inventory, seal = _inputs(tmp_path)

    class RacingClient(FakeClient):
        def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
            if self.list_calls == 1:
                self.objects["foreign/key"] = b"x"
            return super().list_objects_v2(**kwargs)

    client = RacingClient()
    with pytest.raises(TargetObjectRestoreRefused, match="target (contains extra objects|key set or sizes changed)"):
        _restore(root, inventory, seal, client)
