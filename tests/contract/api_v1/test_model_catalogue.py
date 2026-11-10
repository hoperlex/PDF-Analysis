"""`HOSTS-SEAL-1`: ``contracts/analysis/v1/model-catalogue.json`` against the provider lock and the original's prohibitions.

The catalogue is what the stage layout may name. It covers pins of ``docs/program/P02_LOCK.json`` and nothing else, never offers a Haiku, an
effort above ``high`` or ``low`` for Opus, and its ``accepted_reported`` strings are exact: they are what the three places that compare an
answer's model (``extended_review.py``, ``executors/runner.py``, ``analysis/text/stage.py``) will accept.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CATALOGUE = json.loads((ROOT / "contracts/analysis/v1/model-catalogue.json").read_text(encoding="utf-8"))
LOCK = json.loads((ROOT / "docs/program/P02_LOCK.json").read_text(encoding="utf-8"))

OFFERED = {"claude-opus-5-5", "claude-sonnet-5-5", "gpt-6.1-sol", "gpt-6-sol", "gpt-6-astra"}
CLAUDE = {"claude-opus-5-5", "claude-sonnet-5-5"}
CODEX = {"gpt-6.1-sol", "gpt-6-sol", "gpt-6-astra"}
PROVIDERS = {"claude_code", "codex", "anthropic_api", "openai_api", "openrouter_api"}
EFFORTS = {
    "claude-opus-5-5": ["medium", "high"],
    "claude-sonnet-5-5": ["low", "medium", "high"],
    "gpt-6.1-sol": ["low", "medium", "high"],
    "gpt-6-sol": ["low", "medium", "high"],
    "gpt-6-astra": ["low", "medium", "high"],
}


def _entries(provider: str | None = None) -> list[dict]:
    return [entry for entry in CATALOGUE["entries"] if provider is None or entry["provider"] == provider]


def test_the_catalogue_is_the_version_of_the_contract_it_was_sealed_with() -> None:
    assert CATALOGUE["contract"] == "auditmanager.analysis.model-catalogue"
    assert CATALOGUE["contract_version"] == "1.47.0"
    assert CATALOGUE["lock_file"] == "docs/program/P02_LOCK.json"


def test_every_model_it_offers_is_a_pin_of_the_lock_and_only_those_are_offered() -> None:
    pinned = {entry["model_id"] for entry in LOCK["models"].values() if isinstance(entry, dict) and "model_id" in entry}
    offered = {entry["model_id"] for entry in _entries()}
    assert offered == OFFERED
    assert offered <= pinned, f"offered but not pinned: {sorted(offered - pinned)}"


def test_the_older_claude_pins_stay_in_the_lock_and_are_never_offered() -> None:
    pinned = {entry["model_id"] for entry in LOCK["models"].values() if isinstance(entry, dict) and "model_id" in entry}
    assert {"claude-opus-5", "claude-sonnet-5"} <= pinned
    assert not {"claude-opus-5", "claude-sonnet-5"} & {entry["model_id"] for entry in _entries()}


def test_no_haiku_and_no_effort_above_high_and_no_low_for_opus_is_ever_offered() -> None:
    for entry in _entries():
        assert "haiku" not in entry["model_id"].lower(), entry
        assert set(entry["efforts"]) <= {"low", "medium", "high"}, entry
        assert entry["efforts"] == EFFORTS[entry["model_id"]], entry
    assert CATALOGUE["efforts_vocabulary"] == ["low", "medium", "high"]
    for entry in _entries():
        if "opus" in entry["model_id"]:
            assert "low" not in entry["efforts"], entry


def test_the_cli_providers_cover_the_five_models_with_their_exact_reported_strings() -> None:
    claude = {entry["model_id"]: entry for entry in _entries("claude_code")}
    codex = {entry["model_id"]: entry for entry in _entries("codex")}
    assert set(claude) == CLAUDE and set(codex) == CODEX
    for model, entry in claude.items():
        assert entry["accepted_reported"] == [model, f"{model}[1m]"], entry  # the long-context spelling is a different string
    for model, entry in codex.items():
        assert entry["accepted_reported"] == [model], entry  # the model id only
    for entry in (*claude.values(), *codex.values()):
        assert entry["access"] == ["subscription", "api"], entry  # the CLI is logged in with an account or with a key


def test_the_direct_api_providers_serve_the_same_model_ids_with_access_api_only() -> None:
    assert {entry["model_id"] for entry in _entries("anthropic_api")} == CLAUDE
    assert {entry["model_id"] for entry in _entries("openai_api")} == CODEX
    assert {entry["model_id"] for entry in _entries("openrouter_api")} == OFFERED
    for provider in ("anthropic_api", "openai_api", "openrouter_api"):
        for entry in _entries(provider):
            assert entry["access"] == ["api"], entry
            assert entry["model_id"] in entry["accepted_reported"], entry


def test_the_shape_of_every_entry_is_closed() -> None:
    seen: set[tuple[str, str]] = set()
    for entry in _entries():
        assert set(entry) == {"provider", "model_id", "access", "efforts", "accepted_reported"}, entry
        assert entry["provider"] in PROVIDERS, entry
        assert (entry["provider"], entry["model_id"]) not in seen, f"repeated: {entry}"
        seen.add((entry["provider"], entry["model_id"]))
        assert entry["access"] and set(entry["access"]) <= {"subscription", "api"}, entry
        assert len(entry["accepted_reported"]) == len(set(entry["accepted_reported"])), entry
        assert all(isinstance(value, str) and 1 <= len(value) <= 200 for value in entry["accepted_reported"]), entry
    assert CATALOGUE["provider_vocabulary"] == sorted(PROVIDERS, key=CATALOGUE["provider_vocabulary"].index)
    assert set(CATALOGUE["provider_vocabulary"]) == PROVIDERS


@pytest.mark.parametrize("mutation", ["xhigh", "max"])
def test_an_effort_above_high_would_be_caught_by_the_guard_above(mutation: str) -> None:
    """The guard can fail: the same assertion over a catalogue with the forbidden effort added is false."""
    entry = dict(_entries("claude_code")[0], efforts=["medium", "high", mutation])
    assert not (set(entry["efforts"]) <= {"low", "medium", "high"})
