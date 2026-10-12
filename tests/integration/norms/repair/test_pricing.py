"""The rate card and the bound an unknown outcome is charged at (`W54-PLAN.md` §3.3)."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from auditmanager.norms.repair_journal import (
    RATE_CARD,
    ModelNotPriced,
    rate_for,
    unknown_outcome_bound,
)
from tests.integration.norms.repair.support import REPOSITORY_ROOT

A4_AT_150_DPI = 1241 * 1754


def test_the_rate_card_is_the_lock_files() -> None:
    lock = json.loads((REPOSITORY_ROOT / "docs/program/P02_LOCK.json").read_text(encoding="utf-8"))
    locked = {
        entry["model_id"]: (
            Decimal(str(entry["input_per_mtok_usd"])),
            Decimal(str(entry["output_per_mtok_usd"])),
        )
        for entry in (lock["models"]["primary"], lock["models"]["cheaper_tier"])
    }
    assert {
        name: (rate.input_per_mtok_usd, rate.output_per_mtok_usd) for name, rate in RATE_CARD.items()
    } == locked


@pytest.mark.parametrize(
    ("model", "low", "high"),
    [("claude-opus-5", Decimal("0.20"), Decimal("0.23")),
     ("claude-sonnet-5", Decimal("0.08"), Decimal("0.09"))],
)
def test_the_bound_is_the_plans_figure(model: str, low: Decimal, high: Decimal) -> None:
    """≈ $0.20 on opus-5 and ≈ $0.08 on sonnet-5: 8000 output tokens plus the pixels."""
    bound = unknown_outcome_bound(model, pixels=A4_AT_150_DPI)
    assert low <= bound <= high


def test_more_pixels_never_lower_the_bound() -> None:
    assert unknown_outcome_bound("claude-opus-5", pixels=4 * A4_AT_150_DPI) > unknown_outcome_bound(
        "claude-opus-5", pixels=A4_AT_150_DPI
    )


@pytest.mark.parametrize("model", ["", "proxy", "default", "auto", "gpt-5", "stub/w37cert4"])
def test_a_stub_or_an_unpriced_model_is_refused(model: str) -> None:
    with pytest.raises(ModelNotPriced):
        rate_for(model)


def test_a_vendor_prefixed_gateway_name_takes_the_bare_models_rate() -> None:
    assert rate_for("anthropic/claude-opus-5") == RATE_CARD["claude-opus-5"]
