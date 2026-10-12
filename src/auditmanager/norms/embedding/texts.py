"""``embed-texts``: W57's batch entry point, a file in and a file out.

Request (``auditmanager-embed-texts-request/1``)::

    {"format": "auditmanager-embed-texts-request/1",
     "texts": [{"id": "<caller's key>", "text": "<plain text>"}, ...]}

Response (``auditmanager-embed-texts/1``), one entry per request entry, in request order::

    {"format": "auditmanager-embed-texts/1",
     "embedding_profile": "bge-m3-dense-v1",
     "model_repository": "BAAI/bge-m3",
     "model_revision": "5617a9f61b028005a4858fdac845db406aefb181",
     "dimensions": 1024, "dtype": "float32", "byte_order": "big",
     "vectors": [{"id": ..., "input_sha256": ..., "token_count": ...,
                  "vector_sha256": ..., "vector": "<base64 of 1024 big-endian float32>"}]}

``vector_sha256`` is SHA-256 over the decoded bytes — the value ``norm_embedding`` stores as
``embedding_sha256``. The response is rendered canonically (sorted keys, no insignificant
whitespace, one trailing newline), so equal requests give byte-equal responses.

Refused, with nothing written: a request in another format, no texts, an id that is not a
non-empty string or repeats, an empty text, and a text whose inference count exceeds 512
tokens. A text is never truncated and never windowed here — a caller with a long text asks
for windows, not for a silently shortened vector.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from . import vectors
from .checkpoint import write_atomically
from .profile import (
    DIMENSIONS,
    EMBEDDING_PROFILE,
    MAX_TOKENS,
    MODEL_REPOSITORY,
    MODEL_REVISION,
)
from .windowing import input_digest

REQUEST_FORMAT = "auditmanager-embed-texts-request/1"
RESPONSE_FORMAT = "auditmanager-embed-texts/1"


class EmbedTextsRefused(ValueError):
    """The request cannot be answered under the frozen profile."""


class TextEncoder(Protocol):
    def count_tokens(self, text: str) -> int: ...

    def encode(self, texts: Sequence[str]) -> Sequence[bytes]: ...


def parse_request(document: Any) -> list[tuple[str, str]]:
    if not isinstance(document, dict) or document.get("format") != REQUEST_FORMAT:
        raise EmbedTextsRefused(f"the request is not {REQUEST_FORMAT}")
    if set(document) != {"format", "texts"}:
        raise EmbedTextsRefused("the request holds keys other than format and texts")
    entries = document["texts"]
    if not isinstance(entries, list) or not entries:
        raise EmbedTextsRefused("the request holds no texts")
    seen: set[str] = set()
    result: list[tuple[str, str]] = []
    for position, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != {"id", "text"}:
            raise EmbedTextsRefused(f"entry {position} is not {{id, text}}")
        identifier, text = entry["id"], entry["text"]
        if not isinstance(identifier, str) or not identifier:
            raise EmbedTextsRefused(f"entry {position} id is not a non-empty string")
        if identifier in seen:
            raise EmbedTextsRefused(f"id {identifier!r} repeats")
        if not isinstance(text, str) or not text.strip():
            raise EmbedTextsRefused(f"text {identifier!r} is empty")
        seen.add(identifier)
        result.append((identifier, text))
    return result


def embed_texts(encoder: TextEncoder, request: Any) -> dict[str, Any]:
    entries = parse_request(request)
    counts = []
    for identifier, text in entries:
        count = encoder.count_tokens(text)
        if count > MAX_TOKENS:
            raise EmbedTextsRefused(
                f"text {identifier!r} is {count} inference tokens, over the profile's {MAX_TOKENS}; "
                "it is not truncated"
            )
        counts.append(count)
    packed = list(encoder.encode([text for _, text in entries]))
    if len(packed) != len(entries):
        raise EmbedTextsRefused(f"the encoder returned {len(packed)} vectors for {len(entries)} texts")
    for vector in packed:
        vectors.require_unit(vector)
    return {
        "format": RESPONSE_FORMAT,
        "embedding_profile": EMBEDDING_PROFILE,
        "model_repository": MODEL_REPOSITORY,
        "model_revision": MODEL_REVISION,
        "dimensions": DIMENSIONS,
        "dtype": "float32",
        "byte_order": "big",
        "vectors": [
            {
                "id": identifier,
                "input_sha256": input_digest(text),
                "token_count": count,
                "vector_sha256": vectors.sha256(vector),
                "vector": vectors.to_base64(vector),
            }
            for (identifier, text), count, vector in zip(entries, counts, packed, strict=True)
        ],
    }


def render(response: dict[str, Any]) -> bytes:
    return (
        json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def run(encoder: TextEncoder, request_path: Path, response_path: Path) -> dict[str, Any]:
    if response_path.exists():
        raise EmbedTextsRefused(f"{response_path} exists; embed-texts never overwrites a response")
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise EmbedTextsRefused(f"{request_path} is not JSON") from exc
    response = embed_texts(encoder, request)
    write_atomically(response_path, [render(response)])
    return response
