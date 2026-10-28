"""SECTION-JUDGE-FIXES-01 finding 5: the input budget reserves the prompt of the run being planned.

``input_budget_characters`` subtracted the АР v1 bundle's system prompt and schema (3 639 characters) from every
run's budget, while a section's own system prompt and schema run from 7 163 (ПБ) to over 12 000 (СС)
characters. The one-call figure was therefore too large by the difference, and a volume the figure admitted
in one call could come out over the per-run cost ceiling. The figure now takes the prompt bundle of the run
(``bundle=``); with no bundle it is the figure it always was (the start-up check of ``bootstrap/settings``
and the AR v3 path pass none).

Container-free. The figures are derived here a second time, from the prompt files on disk and the lock's
JSON, so an arithmetic slip in the module is a disagreement and not a tautology.
"""

from __future__ import annotations

import json
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest

from auditmanager.analysis.text.budget import (
    PAGE_FRAMING_ALLOWANCE_CHARACTERS,
    input_budget_characters,
)
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.analysis.text.prompt import AR_TEXT_PROMPT_BUNDLE
from auditmanager.analysis.text.windows import text_window_policy

ROOT = Path(__file__).resolve().parents[3]
PROFILES = ROOT / "src/auditmanager/analysis/text/profiles"
LOCK = json.loads((ROOT / "docs/program/P02_LOCK.json").read_text(encoding="utf-8"))["models"]["primary"]
MODEL = LOCK["model_id"]
CEILING = 1.0
REGISTRY = load_text_profile_registry()
SECTIONS = sorted(REGISTRY.entries)


def schema_characters(schema: object) -> int:
    """The length of the canonical JSON of a schema, derived without the module's own helper."""
    return len(json.dumps(schema, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def prompt_characters(code: str) -> int:
    """The length of the section's system prompt, read from the file (one trailing newline is the file's)."""
    text = (PROFILES / code.lower() / "system_prompt.md").read_text(encoding="utf-8")
    return len(text[:-1] if text.endswith("\n") else text)


def fixed_characters(code: str) -> int:
    return prompt_characters(code) + schema_characters(REGISTRY.entries[code].profile.prompt_bundle.response_schema)


AR_FIXED = len(AR_TEXT_PROMPT_BUNDLE.system_prompt) + schema_characters(AR_TEXT_PROMPT_BUNDLE.response_schema)
AR_BUDGET = input_budget_characters(MODEL, CEILING)


def expected_budget(fixed: int, max_output_tokens: int) -> int:
    """The documented formula, once more, from the lock's decimal figures."""
    output_usd = Fraction(max_output_tokens) * Fraction(str(LOCK["output_per_mtok_usd"])) / 1_000_000
    tokens = (Fraction(str(CEILING)) - output_usd) * 1_000_000 / Fraction(str(LOCK["input_per_mtok_usd"]))
    return max(0, int(tokens * Fraction(7, 5)) - fixed - PAGE_FRAMING_ALLOWANCE_CHARACTERS)


def test_the_ar_figure_is_what_it_always_was() -> None:
    assert AR_FIXED == 3_639
    assert input_budget_characters(MODEL, CEILING) == expected_budget(AR_FIXED, AR_TEXT_PROMPT_BUNDLE.max_output_tokens)
    assert input_budget_characters(MODEL, CEILING, bundle=AR_TEXT_PROMPT_BUNDLE) == AR_BUDGET


@pytest.mark.parametrize("code", SECTIONS)
def test_a_section_run_reserves_its_own_prompt_and_schema(code: str) -> None:
    bundle = REGISTRY.entries[code].profile.prompt_bundle
    assert len(bundle.system_prompt) == prompt_characters(code), "the registry serves the file, nothing else"
    assert fixed_characters(code) > AR_FIXED
    figure = input_budget_characters(MODEL, CEILING, bundle=bundle)
    assert figure == expected_budget(fixed_characters(code), bundle.max_output_tokens)
    assert figure == AR_BUDGET - (fixed_characters(code) - AR_FIXED)
    assert figure < AR_BUDGET


@pytest.mark.parametrize("code", SECTIONS)
def test_what_a_section_call_can_carry_in_all_is_what_the_ar_figure_was_calibrated_on(code: str) -> None:
    """The invariant behind the fix: prompt, schema and document together stay at the calibrated total."""
    figure = input_budget_characters(MODEL, CEILING, bundle=REGISTRY.entries[code].profile.prompt_bundle)
    assert fixed_characters(code) + figure == AR_FIXED + AR_BUDGET


def test_ss_the_largest_prompt_reserves_its_real_length() -> None:
    largest = max(SECTIONS, key=fixed_characters)
    assert largest == "SS"
    fixed = fixed_characters("SS")
    assert fixed - AR_FIXED > 8_000, "the judge measured SS at 8 193 characters over the АР bundle"
    figure = input_budget_characters(MODEL, CEILING, bundle=REGISTRY.entries["SS"].profile.prompt_bundle)
    assert AR_BUDGET - figure == fixed - AR_FIXED
    assert figure == min(input_budget_characters(MODEL, CEILING, bundle=e.profile.prompt_bundle) for e in REGISTRY.entries.values())


def test_a_bundle_with_another_output_cap_prices_its_own_cap() -> None:
    bundle = REGISTRY.entries["PB"].profile.prompt_bundle
    cheap = replace(bundle, max_output_tokens=4_000)
    assert input_budget_characters(MODEL, CEILING, bundle=cheap) == expected_budget(fixed_characters("PB"), 4_000)
    assert input_budget_characters(MODEL, CEILING, bundle=cheap) > input_budget_characters(MODEL, CEILING, bundle=bundle)


def test_a_reservation_still_comes_off_the_section_figure() -> None:
    bundle = REGISTRY.entries["SS"].profile.prompt_bundle
    whole = input_budget_characters(MODEL, CEILING, bundle=bundle)
    assert input_budget_characters(MODEL, CEILING, 1_000, bundle=bundle) == whole - 1_000
    assert input_budget_characters(MODEL, CEILING, 10**9, bundle=bundle) == 0


# --- the boundary between one call and windows ------------------------------------------------------------


def decision(count: int, code: str | None) -> object:
    bundle = None if code is None else REGISTRY.entries[code].profile.prompt_bundle
    return text_window_policy(text_character_count=count, model_id=MODEL, ceiling_usd=CEILING, bundle=bundle)


def test_without_a_bundle_the_boundary_is_the_ar_figure() -> None:
    assert decision(AR_BUDGET, None) is None
    assert decision(AR_BUDGET + 1, None).window_characters == AR_BUDGET  # type: ignore[union-attr]


def test_a_section_run_is_windowed_from_its_own_figure_and_the_boundary_moves_down_by_the_difference() -> None:
    """The one boundary that moves: a volume in (section figure, АР figure] was one call and is now windowed."""
    bundle = REGISTRY.entries["SS"].profile.prompt_bundle
    section = input_budget_characters(MODEL, CEILING, bundle=bundle)
    assert section < AR_BUDGET
    assert decision(section, "SS") is None, "exactly at the section's figure: still one call"
    over = decision(section + 1, "SS")
    assert over is not None and over.window_characters == section  # type: ignore[attr-defined]
    at_old_limit = decision(AR_BUDGET, "SS")
    assert at_old_limit is not None, "the old limit is no longer a one-call volume for SS"
    assert at_old_limit.window_characters == section  # type: ignore[attr-defined]
    assert decision(AR_BUDGET, None) is None, "the same volume without a bundle is still one call"


def test_the_recognised_text_is_counted_against_the_sections_figure() -> None:
    bundle = REGISTRY.entries["SS"].profile.prompt_bundle
    section = input_budget_characters(MODEL, CEILING, bundle=bundle)
    kept = text_window_policy(
        text_character_count=section - 100, model_id=MODEL, ceiling_usd=CEILING, recognised_characters=100, bundle=bundle
    )
    assert kept is None
    pushed = text_window_policy(
        text_character_count=section - 100, model_id=MODEL, ceiling_usd=CEILING, recognised_characters=101, bundle=bundle
    )
    assert pushed is not None and pushed.window_characters == section
