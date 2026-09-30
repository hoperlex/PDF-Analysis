"""Recorded bake-off evidence stays bound to the exact fixture and runner."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/evaluation/norms/retrieval_queries.v1.json"
RUNNER = ROOT / "tools/norms/embedding_bakeoff.py"
RESULTS = ROOT / "fixtures/evaluation/norms/results"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_recorded_results_are_bound_to_the_current_fixture_and_runner() -> None:
    expected = {
        "bge-m3.json": "bge-m3",
        "qwen3-embedding-0.6b.json": "qwen3-embedding-0.6b",
        "multilingual-e5-base.json": "multilingual-e5-base",
    }
    assert {path.name for path in RESULTS.glob("*.json")} == set(expected)

    fixture_sha = _sha256(FIXTURE)
    runner_sha = _sha256(RUNNER)
    for filename, model_key in expected.items():
        result = json.loads((RESULTS / filename).read_text(encoding="utf-8"))
        assert result["fixture_sha256"] == fixture_sha
        assert result["runner_sha256"] == runner_sha
        assert result["model"]["key"] == model_key
        assert result["content_key"] == (
            "2026-07-23..2026-08-20+17d.4b74348debf7"
        )
        assert result["tokenization"]["limit"] == 512
        assert result["tokenization"]["overlap"] == 64
        assert result["benchmark"]["queries"] == 24
        assert result["benchmark"]["candidate_paragraphs"] == 512
