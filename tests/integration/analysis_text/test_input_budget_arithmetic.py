"""`W55B-BUDGET-01`: ``input_budget_characters`` is exact, monotone, non-negative and honest about its model.

Container-free. The budget is the number a run can afford to be given and still finish under
the per-run cost ceiling (``W55-PLAN.md`` section B3.3); these cases pin the arithmetic
against an **independent** computation that reads the lock's JSON directly, so a change to
the formula, to a rate lookup or to the way the output cap is priced turns one of them red.
"""

from __future__ import annotations

import ast
import json
from fractions import Fraction
from pathlib import Path

import pytest

from auditmanager.analysis import public
from auditmanager.analysis.text import budget as budget_module
from auditmanager.analysis.text.budget import (
    CHARACTERS_PER_TOKEN,
    PAGE_FRAMING_ALLOWANCE_CHARACTERS,
    REFERENCE_DOCUMENT_CHARACTERS,
    input_budget_characters,
)
from auditmanager.analysis.text.lock import load_provider_lock, provider_lock
from auditmanager.analysis.text.prompt import AR_TEXT_PROMPT_BUNDLE, canonical_json
from auditmanager.shared.errors import DomainError, ErrorCode

LOCK_PATH = Path(__file__).resolve().parents[3] / "docs/program/P02_LOCK.json"
PRIMARY = "claude-opus-5"
CHEAPER = "claude-sonnet-5"


def _lock_document() -> dict:
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


def _fixed_characters() -> int:
    bundle = AR_TEXT_PROMPT_BUNDLE
    return len(bundle.system_prompt) + len(canonical_json(bundle.response_schema))


def _expected(input_rate: str, output_rate: str, ceiling: str, reserved: int = 0) -> int:
    """The same figure, derived from decimal strings and the documented formula, in whole.

    Not a call into the module: a second derivation, so an arithmetic slip in the module is
    a disagreement and not a tautology. Decimal strings keep it exact.
    """
    output_usd = Fraction(AR_TEXT_PROMPT_BUNDLE.max_output_tokens) * Fraction(output_rate) / 1_000_000
    tokens = (Fraction(ceiling) - output_usd) * 1_000_000 / Fraction(input_rate)
    if tokens <= 0:
        return 0
    chars = (
        int(tokens * Fraction(7, 5))
        - _fixed_characters()
        - PAGE_FRAMING_ALLOWANCE_CHARACTERS
        - reserved
    )
    return max(0, chars)


class TestTheDefaultConfiguration:
    def test_the_figure_matches_an_independent_derivation(self) -> None:
        models = _lock_document()["models"]
        primary = models["primary"]
        ceiling = str(models["run_cost_ceiling_usd"])
        assert primary["model_id"] == PRIMARY
        assert input_budget_characters(PRIMARY, float(ceiling)) == _expected(
            str(primary["input_per_mtok_usd"]), str(primary["output_per_mtok_usd"]), ceiling
        )

    def test_the_cheaper_tier_is_priced_from_its_own_pin(self) -> None:
        models = _lock_document()["models"]
        cheaper = models["cheaper_tier"]
        assert cheaper["model_id"] == CHEAPER
        figure = input_budget_characters(CHEAPER, 1.0)
        assert figure == _expected(
            str(cheaper["input_per_mtok_usd"]), str(cheaper["output_per_mtok_usd"]), "1.0"
        )
        assert figure > input_budget_characters(PRIMARY, 1.0), (
            "the cheaper tier buys more input for the same dollar"
        )

    def test_the_default_is_roughly_fifty_pages_and_admits_the_ar_set_with_room(self) -> None:
        """§B3.3: "≈ 50 pages of text", the 30-page АР set (93 690 characters) well inside."""
        figure = input_budget_characters(PRIMARY, _lock_document()["models"]["run_cost_ceiling_usd"])
        assert 140_000 <= figure <= 160_000, figure
        assert figure >= 1.5 * REFERENCE_DOCUMENT_CHARACTERS, (
            "the default configuration must admit the 30-page АР set with margin (plan §C2 stop)"
        )

    def test_the_reference_document_is_the_one_the_ingest_report_measured(self) -> None:
        assert REFERENCE_DOCUMENT_CHARACTERS == 93_690


class TestTheArithmeticIsNotAGuess:
    def test_the_rates_come_from_the_lock_not_from_the_module(self, tmp_path: Path) -> None:
        """A variant lock with other rates moves the figure; a rate written into the module would not."""
        document = _lock_document()
        document["models"]["primary"]["input_per_mtok_usd"] = 3.0
        document["models"]["primary"]["output_per_mtok_usd"] = 15.0
        variant_path = tmp_path / "variant_lock.json"
        variant_path.write_text(json.dumps(document), encoding="utf-8")
        variant = load_provider_lock(variant_path)
        figure = input_budget_characters(PRIMARY, 1.0, lock=variant)
        assert figure == _expected("3.0", "15.0", "1.0")
        assert figure != input_budget_characters(PRIMARY, 1.0)

    def test_the_output_cap_is_priced_in_full_before_any_input_is_bought(self) -> None:
        """A ceiling the output cap alone exhausts buys no input at all."""
        pin = provider_lock().model(PRIMARY)
        cap_usd = AR_TEXT_PROMPT_BUNDLE.max_output_tokens * pin.output_per_mtok_usd / 1_000_000
        assert input_budget_characters(PRIMARY, cap_usd) == 0
        assert input_budget_characters(PRIMARY, cap_usd - 0.01) == 0
        assert input_budget_characters(PRIMARY, cap_usd + 1.0) > 0

    def test_the_prompts_own_text_is_taken_off_the_top(self) -> None:
        """One more character of system prompt is one fewer character of document.

        Shown by arithmetic rather than by editing the prompt: the module's figure plus the
        fixed characters and the framing allowance is exactly what the money buys.
        """
        pin = provider_lock().model(PRIMARY)
        buys = (
            (1.0 - AR_TEXT_PROMPT_BUNDLE.max_output_tokens * pin.output_per_mtok_usd / 1_000_000)
            * 1_000_000
            / pin.input_per_mtok_usd
            * float(CHARACTERS_PER_TOKEN)
        )
        figure = input_budget_characters(PRIMARY, 1.0)
        assert abs((figure + _fixed_characters() + PAGE_FRAMING_ALLOWANCE_CHARACTERS) - buys) < 1.0

    def test_the_module_names_no_model(self) -> None:
        """No model identifier in the source; the lock is the closed set of models."""
        tree = ast.parse(Path(budget_module.__file__).read_text(encoding="utf-8"))
        strings = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        # Docstrings and comments describe; only string *values* that could select a model count.
        selecting = [s for s in strings if "claude" in s.lower() and len(s) < 80]
        assert selecting == []

    def test_an_unpinned_model_is_refused_not_guessed(self) -> None:
        with pytest.raises(DomainError) as refused:
            input_budget_characters("claude-opus-4", 1.0)
        assert refused.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
        assert refused.value.detail_fields.get("reason") == "model_not_pinned"

    def test_an_empty_model_name_is_refused_too(self) -> None:
        with pytest.raises(DomainError):
            input_budget_characters("", 1.0)


class TestMonotoneAndNeverNegative:
    CEILINGS = [round(0.01 * step, 2) for step in range(0, 1001)]  # 0.00 .. 10.00

    @pytest.mark.parametrize("model", [PRIMARY, CHEAPER])
    def test_a_higher_ceiling_never_lowers_the_figure(self, model: str) -> None:
        figures = [input_budget_characters(model, ceiling) for ceiling in self.CEILINGS]
        assert all(later >= earlier for earlier, later in zip(figures, figures[1:]))
        assert figures[0] == 0 and figures[-1] > 0
        assert len(set(figures)) > 100, "the figure must actually respond to the ceiling"

    @pytest.mark.parametrize("model", [PRIMARY, CHEAPER])
    def test_the_figure_is_never_negative(self, model: str) -> None:
        for ceiling in (0.0, 1e-9, 0.01, 0.1, 0.16, 0.3999999, 0.4, 0.41):
            assert input_budget_characters(model, ceiling) >= 0

    @pytest.mark.parametrize("model", [PRIMARY, CHEAPER])
    def test_a_larger_reservation_never_raises_the_figure(self, model: str) -> None:
        figures = [
            input_budget_characters(model, 1.0, reserved) for reserved in range(0, 700_000, 997)
        ]
        assert all(later <= earlier for earlier, later in zip(figures, figures[1:]))
        assert figures[-1] == 0

    def test_a_ceiling_is_a_ceiling_even_to_the_dollar_cent(self) -> None:
        """Exact arithmetic: no float neighbour of a ceiling flips the figure by a character."""
        assert input_budget_characters(PRIMARY, 0.7) == _expected("5.0", "25.0", "0.7")
        assert input_budget_characters(PRIMARY, 1.1) == _expected("5.0", "25.0", "1.1")
        assert input_budget_characters(PRIMARY, 2.55) == _expected("5.0", "25.0", "2.55")


class TestReservedCharacters:
    def test_reserved_characters_are_subtracted_exactly(self) -> None:
        base = input_budget_characters(PRIMARY, 1.0)
        assert input_budget_characters(PRIMARY, 1.0, 0) == base
        assert input_budget_characters(PRIMARY, 1.0, 1) == base - 1
        assert input_budget_characters(PRIMARY, 1.0, 20_000) == base - 20_000
        assert input_budget_characters(PRIMARY, 1.0, reserved_characters=1234) == base - 1234

    def test_a_reservation_beyond_the_room_leaves_zero_not_a_negative(self) -> None:
        base = input_budget_characters(PRIMARY, 1.0)
        assert input_budget_characters(PRIMARY, 1.0, base) == 0
        assert input_budget_characters(PRIMARY, 1.0, base + 1) == 0
        assert input_budget_characters(PRIMARY, 1.0, 10 * base) == 0

    def test_a_negative_reservation_is_refused(self) -> None:
        with pytest.raises(ValueError):
            input_budget_characters(PRIMARY, 1.0, -1)


class TestArgumentsThatAreNotMoney:
    @pytest.mark.parametrize("ceiling", [float("nan"), float("inf"), float("-inf"), -0.01, -1.0])
    def test_a_ceiling_that_is_not_a_finite_non_negative_amount_is_refused(
        self, ceiling: float
    ) -> None:
        with pytest.raises(ValueError):
            input_budget_characters(PRIMARY, ceiling)


class TestTheExport:
    def test_the_public_surface_carries_the_budget(self) -> None:
        assert public.input_budget_characters is input_budget_characters
        assert "input_budget_characters" in public.__all__
        assert public.REFERENCE_DOCUMENT_CHARACTERS == REFERENCE_DOCUMENT_CHARACTERS
        assert "REFERENCE_DOCUMENT_CHARACTERS" in public.__all__
