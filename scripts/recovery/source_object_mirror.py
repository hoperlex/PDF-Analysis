"""Prepare a private mirror of every object in one W54 S3 inventory.

The injected reader supplies GetObject bytes; this module has no credentials,
endpoint configuration or stand-copy entrypoint. It cannot prove that source
writers stayed stopped. A later W58 transport owner must hold that boundary
across the entire transfer before using this mirror for recovery.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol

from scripts.recovery.object_copy import (
    ObjectCopyRefused,
    build_manifest,
    manifest_bytes,
    parse_inventory,
    verify_manifest,
)

_CHUNK = 1024 * 1024
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW
_WRITE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
_ETAG = re.compile(r"[A-Za-z0-9._~-]+\Z")


class SourceObjectMirrorRefused(ValueError):
    """A source stream or private mirror cannot prove the inventory's bytes."""


class GetObjectReader(Protocol):
    def get_object(self, *, Bucket: str, Key: str, IfMatch: str) -> Mapping[str, object]: ...


@dataclass(frozen=True, slots=True)
class SourceObjectMirror:
    count: int
    size_bytes: int
    inventory_sha256: str
    manifest: bytes


def _private(fd: int, *, directory: bool) -> None:
    info = os.fstat(fd)
    if (not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            or info.st_uid != os.getuid() or info.st_mode & 0o077
            or (not directory and info.st_nlink != 1)):
        raise SourceObjectMirrorRefused("mirror path is not owner-private")


def _leaf_directory(root_fd: int, key: str) -> tuple[int, str]:
    parts = key.split("/")
    directory_fd = os.dup(root_fd)
    try:
        for segment in parts[:-1]:
            try:
                os.mkdir(segment, mode=0o700, dir_fd=directory_fd)
                os.fsync(directory_fd)
            except FileExistsError:
                pass
            child_fd = os.open(segment, _DIR_FLAGS, dir_fd=directory_fd)
            try:
                _private(child_fd, directory=True)
            except BaseException:
                os.close(child_fd)
                raise
            os.close(directory_fd)
            directory_fd = child_fd
        return directory_fd, parts[-1]
    except BaseException:
        os.close(directory_fd)
        raise


def _existing_digest(directory_fd: int, name: str) -> tuple[int, str]:
    fd = os.open(name, _READ_FLAGS, dir_fd=directory_fd)
    try:
        _private(fd, directory=False)
        before = os.fstat(fd)
        digest = hashlib.sha256()
        size = 0
        while chunk := os.read(fd, _CHUNK):
            digest.update(chunk)
            size += len(chunk)
        after = os.fstat(fd)
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_size, after.st_mtime_ns, after.st_ctime_ns
        ) or size != after.st_size:
            raise SourceObjectMirrorRefused("existing mirror object changed during read")
        return size, digest.hexdigest()
    finally:
        os.close(fd)


def _etag_value(value: object) -> str:
    if not isinstance(value, str):
        raise SourceObjectMirrorRefused("source ETag is invalid")
    unquoted = value[1:-1] if len(value) >= 2 and value[0] == value[-1] == '"' else value
    if _ETAG.fullmatch(unquoted) is None:
        raise SourceObjectMirrorRefused("source ETag is invalid")
    return unquoted


def _copy_one(
    reader: GetObjectReader,
    bucket: str,
    key: str,
    expected_size: int,
    inventory_etag: str,
    directory_fd: int,
    name: str,
) -> None:
    etag = _etag_value(inventory_etag)
    try:
        response = reader.get_object(Bucket=bucket, Key=key, IfMatch=f'"{etag}"')
    except Exception:
        raise SourceObjectMirrorRefused("source GetObject failed") from None
    if not isinstance(response, Mapping):
        raise SourceObjectMirrorRefused("source GetObject response is invalid")
    body = response.get("Body")
    if not callable(getattr(body, "read", None)) or not callable(getattr(body, "close", None)):
        raise SourceObjectMirrorRefused("source body is not a closable stream")

    temporary = f".source-object-{secrets.token_hex(16)}"
    temporary_created = False
    try:
        if _etag_value(response.get("ETag")) != etag:
            raise SourceObjectMirrorRefused("source ETag differs from inventory")
        declared = response.get("ContentLength")
        if type(declared) is not int or declared != expected_size:
            raise SourceObjectMirrorRefused("source ContentLength differs from inventory")
        fd = os.open(temporary, _WRITE_FLAGS, 0o600, dir_fd=directory_fd)
        temporary_created = True
        digest = hashlib.sha256()
        size = 0
        try:
            while True:
                try:
                    chunk = body.read(_CHUNK)
                except Exception:
                    raise SourceObjectMirrorRefused("source body read failed") from None
                if chunk == b"":
                    break
                if type(chunk) is not bytes or not chunk:
                    raise SourceObjectMirrorRefused("source body returned a non-byte chunk")
                size += len(chunk)
                if size > expected_size:
                    raise SourceObjectMirrorRefused("source body exceeds inventory size")
                digest.update(chunk)
                remaining = memoryview(chunk)
                while remaining:
                    written = os.write(fd, remaining)
                    if written < 1:
                        raise SourceObjectMirrorRefused("mirror write made no progress")
                    remaining = remaining[written:]
            if size != expected_size:
                raise SourceObjectMirrorRefused("source body is shorter than inventory size")
            os.fsync(fd)
        finally:
            os.close(fd)
        try:
            os.link(
                temporary, name,
                src_dir_fd=directory_fd, dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
            os.fsync(directory_fd)
        except FileExistsError:
            try:
                existing_size, existing_sha256 = _existing_digest(directory_fd, name)
            except OSError:
                raise SourceObjectMirrorRefused("existing mirror object is unsafe") from None
            if (existing_size, existing_sha256) != (size, digest.hexdigest()):
                raise SourceObjectMirrorRefused("existing mirror object differs from source")
    finally:
        try:
            body.close()
        except Exception:
            raise SourceObjectMirrorRefused("source body close failed") from None
        finally:
            if temporary_created:
                os.unlink(temporary, dir_fd=directory_fd)


def mirror_source_objects(
    *,
    inventory_data: bytes,
    objects_root: Path,
    bucket: str,
    reader: GetObjectReader,
) -> SourceObjectMirror:
    """Read all inventory keys, then rehash the complete private mirror.

    Partial success leaves at most verified object files and never returns a
    manifest. Retrying fetches the source again and refuses differing existing
    bytes instead of replacing them. ETag is a conditional-read token only;
    the SHA-256 values are computed from bytes received and read back locally.
    """
    if not isinstance(bucket, str) or not bucket:
        raise SourceObjectMirrorRefused("source bucket is missing")
    try:
        expected = parse_inventory(inventory_data)
    except (ObjectCopyRefused, TypeError):
        raise SourceObjectMirrorRefused("source inventory is invalid") from None
    try:
        root_fd = os.open(objects_root, _DIR_FLAGS)
    except OSError:
        raise SourceObjectMirrorRefused("objects root is unavailable or unsafe") from None
    try:
        _private(root_fd, directory=True)
        for key, size, etag in expected:
            try:
                directory_fd, name = _leaf_directory(root_fd, key)
                try:
                    _copy_one(reader, bucket, key, size, etag, directory_fd, name)
                finally:
                    os.close(directory_fd)
            except OSError:
                raise SourceObjectMirrorRefused("mirror path or write failed") from None
    finally:
        os.close(root_fd)
    try:
        sealed = manifest_bytes(build_manifest(inventory_data, objects_root))
        verify_manifest(inventory_data, objects_root, sealed)
    except ObjectCopyRefused:
        raise SourceObjectMirrorRefused("complete mirror differs from inventory") from None
    return SourceObjectMirror(
        len(expected), sum(size for _, size, _ in expected),
        hashlib.sha256(inventory_data).hexdigest(), sealed,
    )


__all__ = [
    "GetObjectReader", "SourceObjectMirror", "SourceObjectMirrorRefused",
    "mirror_source_objects",
]
