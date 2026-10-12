"""The embedding-set digest, keyed by computed keys only (`D-127`).

Format ``norm-embedding-set/2``: SHA-256 over a version line, then one line per window, each a
compact JSON array::

    [content_key, source_document_ref, chunking_profile, chunk_ordinal, embedding_profile,
     window_ordinal, token_count, char_offset, char_length,
     paragraph_ordinal_first, paragraph_ordinal_last, input_sha256, embedding_sha256]

Windows come in ascending ``(source_document_ref, chunk_ordinal, window_ordinal)``, with
``source_document_ref`` compared in code-point order — PostgreSQL's ``COLLATE "C"``. No private
key and no opaque database id enters it: the same corpus content, chunked and embedded the same
way, has the same digest in any database. The checkpoint files and the repository feed the
same class, and a window out of order raises instead of hashing.
"""

from __future__ import annotations

import hashlib
import json

from .model import EmbeddedWindow

EMBEDDING_SET_DIGEST_VERSION = "norm-embedding-set/2"


class EmbeddingSetDigest:
    __slots__ = ("_chunking_profile", "_content_key", "_digest", "_embedding_profile", "_last", "windows")

    def __init__(self, *, content_key: str, chunking_profile: str, embedding_profile: str) -> None:
        self._content_key = content_key
        self._chunking_profile = chunking_profile
        self._embedding_profile = embedding_profile
        self._digest = hashlib.sha256()
        self._digest.update(f"{EMBEDDING_SET_DIGEST_VERSION}\n".encode("ascii"))
        self._last: tuple[str, int, int] | None = None
        self.windows = 0

    def add(self, document_ref: str, chunk_ordinal: int, window: EmbeddedWindow) -> None:
        self.add_values(
            document_ref,
            chunk_ordinal,
            window_ordinal=window.window_ordinal,
            token_count=window.token_count,
            char_offset=window.char_offset,
            char_length=window.char_length,
            paragraph_ordinal_first=window.paragraph_ordinal_first,
            paragraph_ordinal_last=window.paragraph_ordinal_last,
            input_sha256=window.input_sha256,
            embedding_sha256=window.embedding_sha256,
        )

    def add_values(
        self,
        document_ref: str,
        chunk_ordinal: int,
        *,
        window_ordinal: int,
        token_count: int,
        char_offset: int,
        char_length: int,
        paragraph_ordinal_first: int,
        paragraph_ordinal_last: int,
        input_sha256: str,
        embedding_sha256: str,
    ) -> None:
        key = (document_ref, chunk_ordinal, window_ordinal)
        if self._last is not None and not key > self._last:
            raise ValueError(f"window {key!r} is out of canonical order after {self._last!r}")
        self._last = key
        line = [
            self._content_key,
            document_ref,
            self._chunking_profile,
            chunk_ordinal,
            self._embedding_profile,
            window_ordinal,
            token_count,
            char_offset,
            char_length,
            paragraph_ordinal_first,
            paragraph_ordinal_last,
            input_sha256,
            embedding_sha256,
        ]
        self._digest.update(json.dumps(line, ensure_ascii=False, separators=(",", ":")).encode())
        self._digest.update(b"\n")
        self.windows += 1

    def hexdigest(self) -> str:
        return self._digest.hexdigest()
