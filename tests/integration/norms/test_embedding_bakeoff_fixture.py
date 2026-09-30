"""The embedding benchmark is anchored to real canonical paragraphs, not invented labels."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

from auditmanager.norms.corpus_source import open_corpus_projection


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/evaluation/norms/retrieval_queries.v1.json"
CORPUS = ROOT / ".local/norms/corpus"


class _CharacterTokenizer:
    is_fast = True

    def __call__(
        self,
        text: str,
        *,
        add_special_tokens: bool,
        return_offsets_mapping: bool,
        truncation: bool,
    ) -> dict[str, list[object]]:
        assert add_special_tokens is False
        assert return_offsets_mapping is True
        assert truncation is False
        return {
            "input_ids": list(range(len(text))),
            "offset_mapping": [(index, index + 1) for index in range(len(text))],
        }

    def encode(
        self,
        text: str,
        *,
        add_special_tokens: bool,
        truncation: bool = False,
    ) -> list[int]:
        assert truncation is False
        extra = 2 if add_special_tokens else 0
        return list(range(len(text) + extra))

    def num_special_tokens_to_add(self, *, pair: bool) -> int:
        assert pair is False
        return 2


def test_windows_reserve_prefix_and_special_tokens_without_losing_boundaries() -> None:
    module_path = ROOT / "tools/norms/embedding_bakeoff.py"
    spec = importlib.util.spec_from_file_location("norm_embedding_bakeoff", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    text = "".join(chr(0x400 + index) for index in range(700))
    windows, content_tokens, inference_tokens = module._windows(
        _CharacterTokenizer(),
        text,
        512,
        64,
        prefix="passage: ",
    )

    assert content_tokens == 700
    assert inference_tokens == 711
    assert len(windows) == 2
    assert windows[0] == text[:501]
    assert windows[1] == text[437:]
    assert windows[0][-64:] == windows[1][:64]
    assert all(len("passage: " + value) + 2 <= 512 for value in windows)


def test_the_fixture_is_closed_pinned_and_contains_no_verbatim_query_answer() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["schema_version"] == 1
    assert fixture["language"] == "ru"
    assert len(fixture["queries"]) == 24
    assert len({query["id"] for query in fixture["queries"]}) == 24
    assert fixture["candidate_policy"] == {
        "lexical_hard_negatives_per_query": 20,
        "candidate_paragraphs": 512,
        "model_token_limit": 512,
        "token_overlap": 64,
    }
    models = fixture["models"]
    assert {model["key"] for model in models} == {
        "qwen3-embedding-0.6b",
        "bge-m3",
        "multilingual-e5-base",
    }
    for model in models:
        assert len(model["revision"]) == 40
        assert model["license"] in {"apache-2.0", "mit"}
        assert model["batch_size"] > 0


def test_every_relevance_anchor_resolves_to_the_exact_real_corpus() -> None:
    assert CORPUS.is_dir(), "real corpus required; this test never substitutes a tiny fixture"
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    projection = open_corpus_projection(CORPUS)
    assert projection.snapshot.content_key == fixture["content_key"]

    required = {
        (query["relevant"]["document_slug"], query["relevant"]["paragraph_ordinal"]): query
        for query in fixture["queries"]
    }
    found: dict[tuple[str, int], str] = {}
    for document in projection.iter_documents():
        for paragraph in document.paragraphs:
            anchor = (paragraph.document_slug, paragraph.ordinal)
            if anchor in required:
                found[anchor] = paragraph.text

    assert set(found) == set(required)
    for anchor, text in found.items():
        query = required[anchor]["query"]
        assert query.casefold() not in text.casefold(), (
            f"{required[anchor]['id']} is a copied answer rather than a retrieval query"
        )
        assert len(text.strip()) >= 20
