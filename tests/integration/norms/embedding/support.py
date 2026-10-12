"""Fakes for the container-free embedder tests: a fast tokenizer, an encoder, chunk sets.

``FakeTokenizer`` has the three calls the windowing makes, with real character offsets. Its
``encode`` counts one extra token for every ``ё``/``Ё`` — a byte-fallback quirk — so that
re-encoding a window can exceed the offset count and the runner's shrink loop is exercised.
``FakeEncoder`` maps a text to a deterministic unit float32 vector and records every call.
"""

from __future__ import annotations

import hashlib
import importlib.util
import math
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from auditmanager.norms.chunking import JOIN
from auditmanager.norms.embedding import vectors
from auditmanager.norms.embedding.checkpoint import BuildIdentity
from auditmanager.norms.embedding.model import ChunkInput

ROOT = Path(__file__).resolve().parents[4]
RECORDINGS = Path(__file__).resolve().parent / "recordings"
SNAPSHOT_ID = "ns_" + "0" * 26
CONTENT_KEY = "2026-07-23..2026-08-20+17d+2r+1u.0123456789ab+seg-markdown-v2"
CHUNKING_PROFILE = "characters-v2:1200"

SYNTHETIC_SOURCE = (
    "synthetic: FakeTokenizer of tests/integration/norms/embedding/support.py (regex pieces of "
    "at most three word characters, one extra encode token per ё)"
)

_TOKEN = re.compile(r"\w{1,3}|[^\w\s]", re.UNICODE)


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUNNER = load_module(ROOT / "tools/norms/embedding_bakeoff.py", "embedding_bakeoff_runner")
RECORDING = load_module(ROOT / "infra/norms-worker/tokenizer_recording.py", "tokenizer_recording")


class FakeTokenizer:
    is_fast = True

    def __init__(self) -> None:
        self.calls = 0

    def _pieces(self, text: str) -> list[tuple[int, int]]:
        return [(match.start(), match.end()) for match in _TOKEN.finditer(text)]

    def __call__(
        self, text: str, *, add_special_tokens: bool, return_offsets_mapping: bool, truncation: bool
    ) -> dict[str, Any]:
        assert not add_special_tokens and return_offsets_mapping and not truncation
        self.calls += 1
        offsets = self._pieces(text)
        return {"input_ids": list(range(len(offsets))), "offset_mapping": offsets}

    def encode(self, text: str, *, add_special_tokens: bool, truncation: bool) -> list[int]:
        assert add_special_tokens and not truncation
        self.calls += 1
        quirk = text.count("ё") + text.count("Ё")
        return [0] * (len(self._pieces(text)) + quirk + 2)

    def num_special_tokens_to_add(self, pair: bool = False) -> int:
        return 2


def fake_vector(text: str) -> bytes:
    raw = hashlib.shake_256(text.encode("utf-8")).digest(1024)
    values = [(byte - 127.5) / 127.5 for byte in raw]
    norm = math.sqrt(math.fsum(value * value for value in values))
    return vectors.pack([value / norm for value in values])


class FakeEncoder:
    def __init__(self, tokenizer: Any | None = None) -> None:
        self.tokenizer = tokenizer or FakeTokenizer()
        self.calls: list[int] = []

    def encode(self, texts: Sequence[str]) -> list[bytes]:
        self.calls.append(len(texts))
        return [fake_vector(text) for text in texts]

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text, add_special_tokens=True, truncation=False))


_WORDS = (
    "Ширина", "дверного", "проёма", "в", "свету", "для", "маломобильных", "групп", "населения",
    "должна", "быть", "не", "менее", "0,9", "м;", "высота", "порога", "—", "не", "более",
    "0,014", "м.", "|", "REI", "45", "|", "п.", "5.2.3", "ГОСТ", "Ё-образный", "ёмкость",
)


def paragraph(seed: int, words: int) -> str:
    stream = hashlib.sha256(f"paragraph-{seed}".encode()).digest() * (words // 32 + 1)
    return " ".join(_WORDS[stream[index] % len(_WORDS)] for index in range(words))


def chunk(document_ref: str, ordinal: int, lengths: Sequence[int], *, first: int = 0, seed: int = 0) -> ChunkInput:
    """A chunk joining ``len(lengths)`` paragraphs of about ``lengths[i]`` words each."""
    texts = [paragraph(seed * 1000 + ordinal * 10 + index, words) for index, words in enumerate(lengths)]
    return ChunkInput(
        document_ref=document_ref,
        chunk_ordinal=ordinal,
        text=JOIN.join(texts),
        paragraph_ordinal_first=first,
        paragraph_ordinal_last=first + len(texts) - 1,
        paragraph_lengths=tuple(len(text) for text in texts),
    )


def chunk_set(count: int, *, seed: int = 0) -> list[ChunkInput]:
    """``count`` chunks over a few documents, in canonical order; every fifth needs windows."""
    chunks: list[ChunkInput] = []
    documents = ["doc-a", "doc-b", "doc-c", "doc-é"]
    per_document = max(1, math.ceil(count / len(documents)))
    first = {name: 0 for name in documents}
    for index in range(count):
        name = documents[min(index // per_document, len(documents) - 1)]
        ordinal = sum(1 for item in chunks if item.document_ref == name)
        lengths = (200, 260, 180) if index % 5 == 0 else (12, 30)
        built = chunk(name, ordinal, lengths, first=first[name], seed=seed + index)
        first[name] = built.paragraph_ordinal_last + 1
        chunks.append(built)
    return sorted(chunks, key=lambda item: item.key)


def identity() -> BuildIdentity:
    return BuildIdentity(
        norms_snapshot_id=SNAPSHOT_ID, content_key=CONTENT_KEY, chunking_profile=CHUNKING_PROFILE
    )
