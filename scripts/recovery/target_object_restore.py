"""Copy a sealed W58 object mirror into an operator-owned isolated S3 bucket.

The caller must keep the private mirror and target bucket frozen and prove the
bucket is disposable. This helper verifies bytes and exact key sets; it cannot
prove source-writer quiescence or that the endpoint is a production-safe target.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Mapping, Protocol

from scripts.recovery.object_copy import ObjectCopyRefused, parse_inventory, verify_manifest

_CHUNK = 1024 * 1024
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK


class TargetObjectRestoreRefused(ValueError):
    """The isolated target or local mirror cannot prove exact recovered bytes."""


class TargetObjectClient(Protocol):
    def list_objects_v2(self, **kwargs: object) -> Mapping[str, object]: ...

    def get_object(self, *, Bucket: str, Key: str) -> Mapping[str, object]: ...

    def put_object(
        self, *, Bucket: str, Key: str, Body: BinaryIO, ContentLength: int,
        IfNoneMatch: str,
    ) -> Mapping[str, object]: ...


@dataclass(frozen=True, slots=True)
class TargetObjectRestore:
    count: int
    bytes_read: int
    manifest_sha256: str


def _private(info: os.stat_result, *, directory: bool) -> None:
    kind = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if not kind or info.st_uid != os.getuid() or info.st_mode & 0o077 \
            or (not directory and info.st_nlink != 1):
        raise TargetObjectRestoreRefused("local mirror is not an owned private tree")


def _open_mirror_object(root_fd: int, key: str) -> int:
    directory_fd = os.dup(root_fd)
    try:
        parts = key.split("/")
        for part in parts[:-1]:
            next_fd = os.open(part, _DIR_FLAGS, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
            _private(os.fstat(directory_fd), directory=True)
        file_fd = os.open(parts[-1], _FILE_FLAGS, dir_fd=directory_fd)
        try:
            _private(os.fstat(file_fd), directory=False)
        except BaseException:
            os.close(file_fd)
            raise
        return file_fd
    except OSError as exc:
        raise TargetObjectRestoreRefused("local mirror object cannot be opened safely") from exc
    finally:
        os.close(directory_fd)


def _hash_file(fd: int, size: int, sha256: str) -> None:
    before = os.fstat(fd)
    os.lseek(fd, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    read = 0
    while chunk := os.read(fd, _CHUNK):
        read += len(chunk)
        if read > size:
            raise TargetObjectRestoreRefused("local mirror object exceeds its seal")
        digest.update(chunk)
    after = os.fstat(fd)
    if (read, digest.hexdigest()) != (size, sha256) or (
        before.st_dev, before.st_ino, before.st_mode, before.st_uid,
        before.st_nlink, before.st_size, before.st_mtime_ns, before.st_ctime_ns,
    ) != (
        after.st_dev, after.st_ino, after.st_mode, after.st_uid,
        after.st_nlink, after.st_size, after.st_mtime_ns, after.st_ctime_ns,
    ):
        raise TargetObjectRestoreRefused("local mirror object changed or differs from seal")


def _target_listing(client: TargetObjectClient, bucket: str) -> dict[str, int]:
    result: dict[str, int] = {}
    tokens: set[str] = set()
    token: str | None = None
    while True:
        arguments: dict[str, object] = {"Bucket": bucket}
        if token is not None:
            arguments["ContinuationToken"] = token
        try:
            page = client.list_objects_v2(**arguments)
        except Exception:
            raise TargetObjectRestoreRefused("target bucket listing failed") from None
        if not isinstance(page, Mapping) or type(page.get("IsTruncated")) is not bool:
            raise TargetObjectRestoreRefused("target bucket listing is malformed")
        rows = page.get("Contents", [])
        if type(rows) is not list:
            raise TargetObjectRestoreRefused("target bucket listing is malformed")
        for row in rows:
            if not isinstance(row, Mapping):
                raise TargetObjectRestoreRefused("target object listing is malformed")
            key, size = row.get("Key"), row.get("Size")
            if type(key) is not str or type(size) is not int or size < 0 or key in result:
                raise TargetObjectRestoreRefused("target key or size is invalid or repeated")
            result[key] = size
        if not page["IsTruncated"]:
            return result
        token = page.get("NextContinuationToken")
        if type(token) is not str or not token or token in tokens:
            raise TargetObjectRestoreRefused("target listing continuation is invalid")
        tokens.add(token)


def _read_target(client: TargetObjectClient, bucket: str, key: str, size: int, sha256: str) -> None:
    try:
        response = client.get_object(Bucket=bucket, Key=key)
    except Exception:
        raise TargetObjectRestoreRefused("target GetObject failed") from None
    if not isinstance(response, Mapping):
        raise TargetObjectRestoreRefused("target GetObject response is malformed")
    body = response.get("Body")
    if not callable(getattr(body, "read", None)) or not callable(getattr(body, "close", None)):
        raise TargetObjectRestoreRefused("target body is not a closable stream")
    try:
        if type(response.get("ContentLength")) is not int or response["ContentLength"] != size:
            raise TargetObjectRestoreRefused("target ContentLength differs from seal")
        digest = hashlib.sha256()
        read = 0
        while True:
            try:
                chunk = body.read(_CHUNK)
            except Exception:
                raise TargetObjectRestoreRefused("target body read failed") from None
            if chunk == b"":
                break
            if type(chunk) is not bytes or not chunk:
                raise TargetObjectRestoreRefused("target body returned non-byte data")
            read += len(chunk)
            if read > size:
                raise TargetObjectRestoreRefused("target object exceeds its seal")
            digest.update(chunk)
        if (read, digest.hexdigest()) != (size, sha256):
            raise TargetObjectRestoreRefused("target object bytes differ from seal")
    finally:
        try:
            body.close()
        except Exception:
            raise TargetObjectRestoreRefused("target body close failed") from None


def restore_sealed_objects(
    *, inventory_data: bytes, sealed_data: bytes, objects_root: Path,
    target_bucket: str, client: TargetObjectClient,
) -> TargetObjectRestore:
    """Upload only missing objects, then fully reread every sealed target key.

    A partial run may leave verified objects in the isolated bucket. A retry
    verifies those bytes before any new upload. A foreign key or changed byte
    refuses rather than overwrites. Successful return requires two exact
    target listings around the final byte readback.
    """
    if type(target_bucket) is not str or not target_bucket:
        raise TargetObjectRestoreRefused("isolated target bucket is missing")
    try:
        verify_manifest(inventory_data, objects_root, sealed_data)
        inventory = parse_inventory(inventory_data)
    except (ObjectCopyRefused, OSError, TypeError):
        raise TargetObjectRestoreRefused("local object mirror differs from seal") from None
    entries = json.loads(sealed_data)["objects"]  # canonical shape proven above
    expected = {item["key"]: (item["size_bytes"], item["sha256"]) for item in entries}
    if len(expected) != len(inventory):
        raise TargetObjectRestoreRefused("sealed object keys are repeated")
    try:
        root_fd = os.open(objects_root, _DIR_FLAGS)
    except OSError as exc:
        raise TargetObjectRestoreRefused("local mirror root cannot be opened safely") from exc
    try:
        _private(os.fstat(root_fd), directory=True)
        before = _target_listing(client, target_bucket)
        if set(before) - set(expected) or any(before[key] != expected[key][0] for key in before):
            raise TargetObjectRestoreRefused("target contains an extra or differently sized object")
        for key, _, _ in inventory:
            size, sha256 = expected[key]
            if key in before:
                _read_target(client, target_bucket, key, size, sha256)
                continue
            fd = _open_mirror_object(root_fd, key)
            try:
                _hash_file(fd, size, sha256)
                os.lseek(fd, 0, os.SEEK_SET)
                with os.fdopen(os.dup(fd), "rb", buffering=0) as stream:
                    try:
                        client.put_object(
                            Bucket=target_bucket, Key=key, Body=stream,
                            ContentLength=size, IfNoneMatch="*",
                        )
                    except Exception:
                        raise TargetObjectRestoreRefused("conditional target PutObject failed") from None
                    if stream.tell() != size:
                        raise TargetObjectRestoreRefused("target PutObject did not consume full mirror object")
                _hash_file(fd, size, sha256)
            finally:
                os.close(fd)
            _read_target(client, target_bucket, key, size, sha256)
    finally:
        os.close(root_fd)
    after = _target_listing(client, target_bucket)
    if after != {key: value[0] for key, value in expected.items()}:
        raise TargetObjectRestoreRefused("target key set or sizes changed after upload")
    for key, _, _ in inventory:
        size, sha256 = expected[key]
        _read_target(client, target_bucket, key, size, sha256)
    if _target_listing(client, target_bucket) != after:
        raise TargetObjectRestoreRefused("target key set changed during final readback")
    try:
        verify_manifest(inventory_data, objects_root, sealed_data)
    except (ObjectCopyRefused, OSError):
        raise TargetObjectRestoreRefused("local object mirror changed during target restore") from None
    return TargetObjectRestore(len(inventory), sum(size for _, size, _ in inventory),
                               hashlib.sha256(sealed_data).hexdigest())


__all__ = [
    "TargetObjectClient", "TargetObjectRestore", "TargetObjectRestoreRefused",
    "restore_sealed_objects",
]
