"""The source PDF of a version, in a private temporary file, for the length of a ``with`` block.

`CMP-PROFILE-01`. A page child opens the document by path, so the stored bytes are streamed out of the
object store (:meth:`BlobStore.open_stream`: a whole read that holds back its last chunk until the
SHA-256 equals the digest the version recorded, so a corrupted object never reaches a child) into a
file of a directory that only this process can enter (mode 0700). The file and the directory are
removed on the way out, whether the block returned or raised. The version's bytes are found through
its manifest (``documents.public``), never by a name or a path.

:class:`SourceFileCache` keeps a few such files for the API's on-request tiles, so that the twenty
tiles of one screen do not stream the same PDF twenty times; it is bounded in files and bytes, holds a
file only while a tile child may be reading it, and removes everything when the process exits.
"""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
import threading
from collections import OrderedDict
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy.orm import Session

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "MAX_CACHED_BYTES",
    "MAX_CACHED_FILES",
    "REASON_AMBIGUOUS",
    "REASON_UNREADABLE",
    "SourceFileCache",
    "SourceVersion",
    "load_source_version",
    "materialised_source",
]

MAX_CACHED_FILES: Final[int] = 3
MAX_CACHED_BYTES: Final[int] = 512 * 1024 * 1024
REASON_UNREADABLE: Final[str] = "source_unreadable"
#: A manifest that holds both source roles (a portal version's and a comparison version's): which of the two is the
#: version's bytes is not decided by this code.
REASON_AMBIGUOUS: Final[str] = "source_manifest_ambiguous"


@dataclass(frozen=True, slots=True)
class SourceVersion:
    """The facts of a published version a profile is built from."""

    version_uid: str
    project_uid: str
    page_count: int
    sha256: str
    size_bytes: int
    blob_id: str


def load_source_version(session: Session, version_uid: str) -> SourceVersion:
    """The version and the blob of its source PDF. An unknown version is ``not_found``.

    A version's bytes are bound under one of two manifest roles and no other: ``source.document`` for a version a portal
    bundle published, ``comparison.source_pdf`` for a plain PDF admitted for comparison (`CMP-INGEST-01`, ADR-0025 decision 11:
    a distinct role, so that a run refuses it). A version holds one of the two; a manifest that holds both is refused
    (:data:`REASON_AMBIGUOUS`) rather than answered with whichever comes first, and one that holds neither, or holds the
    role under another media type, is :data:`REASON_UNREADABLE`. The roles are the ``documents.public`` names.
    """
    from auditmanager.documents.public import (
        MANIFEST_ROLE_COMPARISON_PDF,
        MANIFEST_ROLE_SOURCE_DOCUMENT,
        DocumentRepository,
    )
    from auditmanager.shared.identity import VersionUid

    record = DocumentRepository().get_version(session, VersionUid(version_uid))
    roles = (MANIFEST_ROLE_SOURCE_DOCUMENT, MANIFEST_ROLE_COMPARISON_PDF)
    entries = [item for item in record.manifest if item.role in roles]
    if len(entries) > 1:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the version binds more than one source document",
            stage_id="comparison_page_profile",
            reason=REASON_AMBIGUOUS,
        )
    entry = entries[0] if entries else None
    if entry is None or entry.media_type != "application/pdf":
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the version has no source document the page profile can read",
            stage_id="comparison_page_profile",
            reason=REASON_UNREADABLE,
        )
    return SourceVersion(
        version_uid=str(record.version_uid),
        project_uid=str(record.project_uid),
        page_count=int(record.page_count),
        sha256=entry.sha256,
        size_bytes=int(entry.size_bytes),
        blob_id=str(entry.blob_id),
    )


def _stream_to(store: Any, source: SourceVersion, path: str) -> None:
    from auditmanager.storage.public import parse_blob_id

    try:
        with open(path, "wb") as handle:
            for chunk in store.open_stream(
                parse_blob_id(source.blob_id),
                expected_sha256=source.sha256,
                expected_size=source.size_bytes,
            ):
                handle.write(chunk)
    except DomainError:
        raise
    except Exception as failure:  # noqa: BLE001 - re-raised as a typed refusal
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the source document of the version is unreadable",
            stage_id="comparison_page_profile",
            reason=REASON_UNREADABLE,
        ) from failure


@contextmanager
def materialised_source(store: Any, source: SourceVersion) -> Iterator[str]:
    """The path of a private temporary file holding the version's exact bytes."""
    directory = tempfile.mkdtemp(prefix="cmp-source-")
    try:
        path = os.path.join(directory, "source.pdf")
        _stream_to(store, source, path)
        yield path
    finally:
        shutil.rmtree(directory, ignore_errors=True)


class SourceFileCache:
    """A small, bounded, thread-safe cache of materialised source files (for on-request tiles)."""

    def __init__(self, *, max_files: int = MAX_CACHED_FILES, max_bytes: int = MAX_CACHED_BYTES) -> None:
        self._max_files = max_files
        self._max_bytes = max_bytes
        self._lock = threading.Lock()
        #: One load at a time: a file is streamed once, and the others wait for it instead of
        #: streaming the same PDF again.
        self._load = threading.Lock()
        #: blob id -> [directory, path, size, in-use count]
        self._entries: OrderedDict[str, list[Any]] = OrderedDict()
        atexit.register(self.clear)

    @contextmanager
    def acquire(self, store: Any, source: SourceVersion) -> Iterator[str]:
        key = source.blob_id
        with self._load:
            with self._lock:
                entry = self._entries.get(key)
                if entry is not None:
                    entry[3] += 1
                    self._entries.move_to_end(key)
            if entry is None:
                directory = tempfile.mkdtemp(prefix="cmp-source-")
                path = os.path.join(directory, "source.pdf")
                try:
                    _stream_to(store, source, path)
                except BaseException:
                    shutil.rmtree(directory, ignore_errors=True)
                    raise
                with self._lock:
                    entry = [directory, path, source.size_bytes, 1]
                    self._entries[key] = entry
                    self._evict()
        try:
            yield entry[1]
        finally:
            with self._lock:
                entry[3] -= 1
                self._evict()

    def _evict(self) -> None:
        """Drop the least recently used files that no tile child is reading (caller holds the lock)."""
        def over() -> bool:
            return len(self._entries) > self._max_files or sum(e[2] for e in self._entries.values()) > self._max_bytes

        for key in list(self._entries):
            if not over():
                break
            entry = self._entries[key]
            if entry[3] == 0:
                shutil.rmtree(entry[0], ignore_errors=True)
                del self._entries[key]

    def clear(self) -> None:
        with self._lock:
            for entry in self._entries.values():
                shutil.rmtree(entry[0], ignore_errors=True)
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
