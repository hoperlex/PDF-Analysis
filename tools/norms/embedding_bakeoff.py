#!/usr/bin/env python3
"""Reproducible local embedding bake-off over the canonical normative corpus.

The production project deliberately has no embedding dependency yet. Run this tool with the
isolated evaluation environment recorded in ``docs/program/NORM_EMBEDDING_BAKEOFF.md`` and
``PYTHONPATH=src``. It never writes the source corpus, database or object store.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import resource
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from auditmanager.norms.corpus_source import open_corpus_projection


WORD = re.compile(r"[0-9A-Za-zА-Яа-яЁё]+", re.UNICODE)
STOPWORDS = frozenset(
    {
        "какое",
        "какие",
        "каким",
        "какова",
        "какой",
        "когда",
        "можно",
        "должны",
        "должен",
        "должна",
        "следует",
        "требуется",
        "нужно",
        "норматив",
        "помещения",
        "помещении",
        "здания",
        "здании",
        "системы",
        "системой",
        "этого",
        "если",
        "который",
        "которые",
        "для",
        "при",
        "или",
        "над",
        "под",
        "без",
        "из",
        "на",
        "по",
        "от",
        "как",
        "что",
    }
)


@dataclass(frozen=True, slots=True)
class ParagraphRecord:
    key: str
    document_slug: str
    ordinal: int
    text: str


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be an object")
    return value


def _fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _terms(text: str) -> frozenset[str]:
    result: set[str] = set()
    for raw in WORD.findall(text.casefold()):
        if len(raw) < 4 or raw in STOPWORDS or raw.isdecimal():
            continue
        result.add(raw[:6] if len(raw) >= 8 else raw)
    return frozenset(result)


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def _load_corpus(corpus: Path, fixture: dict[str, Any]) -> tuple[list[ParagraphRecord], dict[str, int], list[str]]:
    projection = open_corpus_projection(corpus)
    if projection.snapshot.content_key != fixture["content_key"]:
        raise ValueError(
            "fixture content_key does not identify this corpus: "
            f"{fixture['content_key']!r} != {projection.snapshot.content_key!r}"
        )

    paragraphs: list[ParagraphRecord] = []
    anchors: dict[str, int] = {}
    chunk_texts: list[str] = []
    for document in projection.iter_documents():
        for paragraph in document.paragraphs:
            key = f"{paragraph.document_slug}:{paragraph.ordinal}"
            if key in anchors:
                raise ValueError(f"duplicate canonical paragraph anchor: {key}")
            anchors[key] = len(paragraphs)
            paragraphs.append(
                ParagraphRecord(
                    key=key,
                    document_slug=paragraph.document_slug,
                    ordinal=paragraph.ordinal,
                    text=paragraph.text,
                )
            )
        chunk_texts.extend(chunk.text for chunk in document.chunks)
    return paragraphs, anchors, chunk_texts


def _candidate_indices(
    paragraphs: list[ParagraphRecord],
    anchors: dict[str, int],
    fixture: dict[str, Any],
) -> tuple[list[int], dict[str, int], dict[str, int]]:
    queries = fixture["queries"]
    policy = fixture["candidate_policy"]
    hard_limit = int(policy["lexical_hard_negatives_per_query"])
    final_limit = int(policy["candidate_paragraphs"])

    query_terms = {query["id"]: _terms(query["query"]) for query in queries}
    vocabulary = frozenset().union(*query_terms.values())
    paragraph_terms: list[frozenset[str]] = []
    document_frequency: Counter[str] = Counter()
    for paragraph in paragraphs:
        present = _terms(paragraph.text) & vocabulary
        paragraph_terms.append(present)
        document_frequency.update(present)

    selected: set[int] = set()
    relevant_index: dict[str, int] = {}
    lexical_rank: dict[str, int] = {}
    corpus_size = len(paragraphs)
    for query in queries:
        anchor = query["relevant"]
        key = f"{anchor['document_slug']}:{anchor['paragraph_ordinal']}"
        if key not in anchors:
            raise ValueError(f"fixture anchor is absent from corpus: {query['id']} -> {key}")
        target = anchors[key]
        relevant_index[query["id"]] = target
        selected.add(target)

        terms = query_terms[query["id"]]
        scored: list[tuple[float, str, int]] = []
        for index, present in enumerate(paragraph_terms):
            overlap = terms & present
            if not overlap:
                continue
            score = sum(
                math.log((corpus_size + 1) / (document_frequency[term] + 1))
                for term in overlap
            )
            scored.append((-score, paragraphs[index].key, index))
        scored.sort()
        ranked = [index for _, _, index in scored]
        lexical_rank[query["id"]] = ranked.index(target) + 1 if target in ranked else 0
        selected.update(ranked[:hard_limit])

    if len(selected) > final_limit:
        raise ValueError(
            f"hard-negative union has {len(selected)} rows, over candidate limit {final_limit}"
        )
    distractors = sorted(
        (record.key, index)
        for index, record in enumerate(paragraphs)
        if index not in selected
    )
    distractors.sort(key=lambda item: hashlib.sha256(item[0].encode()).digest())
    selected.update(index for _, index in distractors[: final_limit - len(selected)])
    if any(rank == 0 for rank in lexical_rank.values()):
        raise ValueError("at least one relevant paragraph has no lexical candidate rank")

    ordered = sorted(selected, key=lambda index: paragraphs[index].key)
    if len(ordered) != final_limit:
        raise ValueError(f"candidate set has {len(ordered)} rows, expected {final_limit}")
    return ordered, relevant_index, lexical_rank


def _input_prefix(mode: str, *, query: bool) -> str:
    if mode == "e5_prefix":
        return "query: " if query else "passage: "
    if mode in {"plain", "prompt_name_query"}:
        return ""
    raise ValueError(f"unknown query_mode: {mode}")


def _windows(
    tokenizer,
    text: str,
    limit: int,
    overlap: int,
    *,
    prefix: str,
) -> tuple[list[str], int, int]:
    if not getattr(tokenizer, "is_fast", False):
        raise ValueError("offset-aware lossless windows require a fast tokenizer")
    encoded = tokenizer(
        text,
        add_special_tokens=False,
        return_offsets_mapping=True,
        truncation=False,
    )
    token_ids = encoded["input_ids"]
    offsets = encoded["offset_mapping"]
    if not token_ids:
        raise ValueError("canonical paragraph tokenized to zero tokens")
    if len(token_ids) != len(offsets) or any(end <= start for start, end in offsets):
        raise ValueError("tokenizer returned unusable character offsets")

    special_tokens = tokenizer.num_special_tokens_to_add(pair=False)
    inference_count = (
        len(tokenizer.encode(prefix + text, add_special_tokens=True, truncation=False))
        if prefix
        else len(token_ids) + special_tokens
    )
    if inference_count <= limit:
        return [text], len(token_ids), inference_count

    windows: list[str] = []
    start = 0
    while start < len(token_ids):
        end = min(len(token_ids), start + limit)
        while end > start:
            char_start = 0 if start == 0 else offsets[start][0]
            char_end = len(text) if end == len(token_ids) else offsets[end - 1][1]
            value = text[char_start:char_end]
            encoded_count = len(
                tokenizer.encode(
                    prefix + value,
                    add_special_tokens=True,
                    truncation=False,
                )
            )
            if encoded_count <= limit:
                break
            end -= max(1, encoded_count - limit)
        if end <= start or not value.strip():
            raise ValueError("cannot produce a non-empty token window within model limit")
        windows.append(value)
        if end == len(token_ids):
            break
        start = max(start + 1, end - overlap)

    if windows[0][0] != text[0] or windows[-1][-1] != text[-1]:
        raise ValueError("token windows do not cover the paragraph boundaries")
    return windows, len(token_ids), inference_count


def _token_stats(
    tokenizer,
    texts: list[str],
    limit: int,
    overlap: int,
    *,
    prefix: str,
) -> dict[str, Any]:
    content_counts: list[int] = []
    inference_counts: list[int] = []
    windows = 0
    over_limit = 0
    started = time.perf_counter()
    for text in texts:
        values, content_count, inference_count = _windows(
            tokenizer,
            text,
            limit,
            overlap,
            prefix=prefix,
        )
        content_counts.append(content_count)
        inference_counts.append(inference_count)
        over_limit += inference_count > limit
        windows += len(values)
    return {
        "rows": len(inference_counts),
        "total_tokens": sum(inference_counts),
        "total_content_tokens": sum(content_counts),
        "max_tokens": max(inference_counts, default=0),
        "max_content_tokens": max(content_counts, default=0),
        "p50_tokens": _percentile(inference_counts, 0.50),
        "p95_tokens": _percentile(inference_counts, 0.95),
        "p99_tokens": _percentile(inference_counts, 0.99),
        "over_limit": over_limit,
        "windowed_rows": windows,
        "seconds": round(time.perf_counter() - started, 3),
    }


def _encode(model, texts: list[str], *, mode: str, batch_size: int, query: bool):
    prefix = _input_prefix(mode, query=query)
    prepared = [prefix + text for text in texts] if prefix else texts
    arguments: dict[str, Any] = {
        "batch_size": batch_size,
        "show_progress_bar": True,
        "convert_to_numpy": True,
        "normalize_embeddings": True,
    }
    if mode == "prompt_name_query" and query:
        arguments["prompt_name"] = "query"
    return model.encode(prepared, **arguments)


def _metrics(scores, queries: list[dict[str, Any]], relevant_windows: dict[str, set[int]]) -> dict[str, Any]:
    reciprocal_ranks: list[float] = []
    recalls = {1: 0, 5: 0, 10: 0}
    ranks: dict[str, int] = {}
    for row, query in enumerate(queries):
        order = scores[row].argsort()[::-1]
        relevant = relevant_windows[query["id"]]
        rank = next(position for position, index in enumerate(order, start=1) if int(index) in relevant)
        ranks[query["id"]] = rank
        reciprocal_ranks.append(1.0 / rank)
        for cutoff in recalls:
            recalls[cutoff] += rank <= cutoff
    total = len(queries)
    return {
        "mrr": round(statistics.fmean(reciprocal_ranks), 6),
        "recall_at_1": round(recalls[1] / total, 6),
        "recall_at_5": round(recalls[5] / total, 6),
        "recall_at_10": round(recalls[10] / total, 6),
        "ranks": ranks,
    }


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    fixture_path = args.fixture.resolve()
    fixture = _load_json(fixture_path)
    models = {model["key"]: model for model in fixture["models"]}
    if args.model not in models:
        raise ValueError(f"model {args.model!r} not declared in fixture")
    model_spec = models[args.model]
    paragraphs, anchors, chunk_texts = _load_corpus(args.corpus.resolve(), fixture)
    candidate_indices, relevant_index, lexical_rank = _candidate_indices(
        paragraphs, anchors, fixture
    )

    from sentence_transformers import SentenceTransformer, __version__ as st_version
    from transformers import AutoTokenizer, __version__ as transformers_version
    import numpy as np
    import torch

    torch.set_num_threads(args.threads)
    tokenizer_started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(
        model_spec["repository"], revision=model_spec["revision"]
    )
    tokenizer_seconds = time.perf_counter() - tokenizer_started

    policy = fixture["candidate_policy"]
    limit = int(policy["model_token_limit"])
    overlap = int(policy["token_overlap"])
    passage_prefix = _input_prefix(model_spec["query_mode"], query=False)
    canonical_stats = _token_stats(
        tokenizer,
        [paragraph.text for paragraph in paragraphs],
        limit,
        overlap,
        prefix=passage_prefix,
    )
    chunk_stats = _token_stats(
        tokenizer,
        chunk_texts,
        limit,
        overlap,
        prefix=passage_prefix,
    )

    window_texts: list[str] = []
    relevant_windows: dict[str, set[int]] = {query["id"]: set() for query in fixture["queries"]}
    candidate_position = {index: position for position, index in enumerate(candidate_indices)}
    target_queries_by_candidate: dict[int, list[str]] = {}
    for query_id, index in relevant_index.items():
        target_queries_by_candidate.setdefault(candidate_position[index], []).append(query_id)

    candidate_token_counts: list[int] = []
    for position, paragraph_index in enumerate(candidate_indices):
        windows, _, inference_count = _windows(
            tokenizer,
            paragraphs[paragraph_index].text,
            limit,
            overlap,
            prefix=passage_prefix,
        )
        candidate_token_counts.append(inference_count)
        start = len(window_texts)
        window_texts.extend(windows)
        for query_id in target_queries_by_candidate.get(position, []):
            relevant_windows[query_id].update(range(start, len(window_texts)))

    load_started = time.perf_counter()
    model = SentenceTransformer(
        model_spec["repository"],
        revision=model_spec["revision"],
        device="cpu",
    )
    model.max_seq_length = limit
    load_seconds = time.perf_counter() - load_started

    query_texts = [query["query"] for query in fixture["queries"]]
    query_prefix = _input_prefix(model_spec["query_mode"], query=True)
    if model_spec["query_mode"] == "prompt_name_query":
        query_prefix = model.prompts.get("query", "")
        if not query_prefix:
            raise ValueError("query prompt is absent from the pinned model")
    if any(
        len(tokenizer.encode(query_prefix + value, add_special_tokens=True)) > limit
        for value in query_texts
    ):
        raise ValueError("a prepared query exceeds the frozen model token limit")
    query_started = time.perf_counter()
    query_vectors = _encode(
        model,
        query_texts,
        mode=model_spec["query_mode"],
        batch_size=int(model_spec["batch_size"]),
        query=True,
    )
    query_seconds = time.perf_counter() - query_started
    passage_started = time.perf_counter()
    passage_vectors = _encode(
        model,
        window_texts,
        mode=model_spec["query_mode"],
        batch_size=int(model_spec["batch_size"]),
        query=False,
    )
    passage_seconds = time.perf_counter() - passage_started
    scores = np.matmul(query_vectors, passage_vectors.T)
    measured = _metrics(scores, fixture["queries"], relevant_windows)

    dimension = int(passage_vectors.shape[1])
    maximum_rss_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    return {
        "schema_version": 1,
        "fixture_sha256": _fingerprint(fixture_path),
        "runner_sha256": _fingerprint(Path(__file__).resolve()),
        "content_key": fixture["content_key"],
        "model": model_spec,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "transformers": transformers_version,
            "sentence_transformers": st_version,
            "threads": args.threads,
            "platform": platform.platform(),
        },
        "corpus": {
            "canonical_paragraphs": len(paragraphs),
            "character_chunks": len(chunk_texts),
        },
        "tokenization": {
            "limit": limit,
            "overlap": overlap,
            "passage_prefix": passage_prefix,
            "special_tokens": tokenizer.num_special_tokens_to_add(pair=False),
            "canonical_paragraphs": canonical_stats,
            "character_chunks": chunk_stats,
            "tokenizer_load_seconds": round(tokenizer_seconds, 3),
        },
        "benchmark": {
            "queries": len(fixture["queries"]),
            "candidate_paragraphs": len(candidate_indices),
            "candidate_windows": len(window_texts),
            "candidate_max_tokens": max(candidate_token_counts),
            "lexical_baseline_rank": lexical_rank,
            **measured,
        },
        "inference": {
            "dimension": dimension,
            "normalization": "L2",
            "distance": "cosine/IP over normalized vectors",
            "model_load_seconds": round(load_seconds, 3),
            "query_seconds": round(query_seconds, 3),
            "passage_seconds": round(passage_seconds, 3),
            "passages_per_second": round(len(window_texts) / passage_seconds, 3),
            "max_rss_mib": round(maximum_rss_mib, 1),
            "float32_vector_mib_for_windowed_character_chunks": round(
                chunk_stats["windowed_rows"] * dimension * 4 / 1024 / 1024,
                2,
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=min(os.cpu_count() or 1, 8))
    args = parser.parse_args(argv)
    if args.threads <= 0:
        parser.error("--threads must be positive")
    result = evaluate(args)
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
