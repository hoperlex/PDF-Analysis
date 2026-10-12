"""Values the embedder passes between its phases. No behaviour beyond derivation.

A chunk is named by its **computed key** ``(source_document_ref, ordinal)`` inside one
snapshot and chunking profile (`D-127`), never by the private ``norm_chunk_pk``: the same
corpus in another database has other private keys and the same computed keys.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkInput:
    """One stored chunk as the embedder reads it: its text and its paragraph layout.

    ``paragraph_lengths`` are the character lengths of the canonical paragraphs
    ``paragraph_ordinal_first … paragraph_ordinal_last``, whose texts the chunk joins with
    ``chunking.JOIN``; a window's paragraph span is derived from them.
    """

    document_ref: str
    chunk_ordinal: int
    text: str
    paragraph_ordinal_first: int
    paragraph_ordinal_last: int
    paragraph_lengths: tuple[int, ...]

    @property
    def key(self) -> tuple[str, int]:
        return (self.document_ref, self.chunk_ordinal)

    @property
    def content_sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class EmbeddedWindow:
    """One window of one chunk with its vector.

    ``vector`` is the 1024 float32 values packed big-endian (``struct`` ``"!1024f"``);
    ``embedding_sha256`` is SHA-256 over exactly those bytes, as ``norm_embedding`` stores it.
    ``token_count`` is the window's inference count, special tokens included (≤ 512).
    """

    window_ordinal: int
    char_offset: int
    char_length: int
    token_count: int
    paragraph_ordinal_first: int
    paragraph_ordinal_last: int
    input_sha256: str
    vector: bytes

    @property
    def embedding_sha256(self) -> str:
        return hashlib.sha256(self.vector).hexdigest()


@dataclass(frozen=True, slots=True)
class ChunkEmbedding:
    """Every window of one chunk, in window order."""

    document_ref: str
    chunk_ordinal: int
    windows: tuple[EmbeddedWindow, ...]

    @property
    def key(self) -> tuple[str, int]:
        return (self.document_ref, self.chunk_ordinal)
