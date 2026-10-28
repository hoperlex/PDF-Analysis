"""The vocabulary of the comparison spend journal (`CMP-SPEND-01`): the constants of `Q-CMP-7`, the integer
money, the consent, the states the code names against the states the migration declares. Container-free."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from auditmanager.comparison.spend import model

ROOT = Path(__file__).resolve().parents[4]
MIGRATION = ROOT / "db/migrations/versions/20261028_0038_comparison_foundation.py"
DIGEST = "ab" * 32


def _migration():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("cmp_spend_01_migration_0038", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _consent(**over: object) -> model.Consent:
    values: dict[str, object] = {
        "estimate_digest": DIGEST, "estimate_usd": 4.0, "ceiling_usd": 6.0,
        "connection_revision_id": "excr_X", "pinned_model": "claude-opus-5",
    }
    values.update(over)
    return model.Consent(**values)  # type: ignore[arg-type]


def test_the_states_the_code_names_are_the_states_the_migration_declares() -> None:
    migration = _migration()
    assert model.CALL_STATES == migration.CALL_STATES
    assert model.TERMINAL_STATES == migration.CALL_TERMINAL
    assert model.OPEN_STATES == tuple(s for s in migration.CALL_STATES if s not in migration.CALL_TERMINAL)


def test_the_cost_bases_are_the_ones_the_migration_admits() -> None:
    migration = _migration()
    assert {model.COST_MEASURED, model.COST_ESTIMATED, model.COST_UNMETERED} == set(migration.COST_BASES)


def test_the_ceilings_are_the_ones_of_q_cmp_7() -> None:
    """USD 10 per job, USD 50 per day per installation, 1.2 x the estimate (ADR-0025 decision 19)."""
    assert model.JOB_CEILING_USD == 10 and model.JOB_CEILING_MICROS == 10_000_000
    assert model.DAY_CEILING_USD == 50 and model.DAY_CEILING_MICROS == 50_000_000
    assert (model.OVERRUN_NUMERATOR, model.OVERRUN_DENOMINATOR) == (6, 5)


@pytest.mark.parametrize(("usd", "micros"), [(0.0, 0), (1.0, 1_000_000), (0.0000001, 1), (2.5000004, 2_500_001)])
def test_an_estimate_rounds_up_so_a_ceiling_is_never_passed_by_rounding(usd: float, micros: int) -> None:
    assert model.estimate_micros_of(usd) == micros


@pytest.mark.parametrize(("usd", "micros"), [(0.0, 0), (1.2345674, 1_234_567), (1.2345676, 1_234_568)])
def test_a_measured_cost_rounds_to_the_nearest_micro(usd: float, micros: int) -> None:
    assert model.measured_micros_of(usd) == micros


@pytest.mark.parametrize("bad", [-1.0, float("nan"), float("inf")])
def test_money_refuses_a_negative_or_non_finite_amount(bad: float) -> None:
    with pytest.raises(ValueError):
        model.estimate_micros_of(bad)
    with pytest.raises(ValueError):
        model.measured_micros_of(bad)


def test_the_overrun_edge_is_exactly_one_point_two_times_the_estimate() -> None:
    assert model.overruns(1_200_000, 1_000_000) is False      # exactly 1.2 x: not above it
    assert model.overruns(1_200_001, 1_000_000) is True
    assert model.overruns(0, 0) is False                       # nothing spent against nothing estimated
    assert model.overruns(1, 0) is True


def test_a_consent_above_the_hard_job_ceiling_is_refused_not_lowered() -> None:
    assert _consent(ceiling_usd=10.0).ceiling_micros == 10_000_000
    with pytest.raises(ValueError):
        _consent(ceiling_usd=10.01)
    with pytest.raises(ValueError):
        _consent(ceiling_usd=0.0)


@pytest.mark.parametrize("field", ["estimate_digest", "connection_revision_id", "pinned_model"])
def test_a_consent_names_what_it_binds(field: str) -> None:
    with pytest.raises(ValueError):
        _consent(**{field: ""})


def test_the_estimate_digest_is_a_lower_case_sha256() -> None:
    for bad in ("AB" * 32, "ab" * 31, "zz" * 32):
        with pytest.raises(ValueError):
            _consent(estimate_digest=bad)


@pytest.mark.parametrize(
    "change",
    [{"estimate_digest": "cd" * 32}, {"ceiling_usd": 7.0}, {"connection_revision_id": "excr_Y"},
     {"pinned_model": "claude-sonnet-5"}],
)
def test_the_consent_digest_binds_the_four_things_decision_19_names(change: dict[str, object]) -> None:
    assert _consent(**change).binding_digest != _consent().binding_digest
    assert _consent().binding_digest == _consent().binding_digest


def test_the_consent_digest_does_not_move_with_the_usd_total_alone() -> None:
    """The estimate document is bound by its digest; the USD figure is read from it, not a fifth binding."""
    assert _consent(estimate_usd=5.0).binding_digest == _consent().binding_digest


@pytest.mark.parametrize("tokens", [(-1, 0), (0, -1), (1.5, 0), (True, 0)])
def test_a_call_estimate_is_two_non_negative_integers(tokens: tuple[object, object]) -> None:
    with pytest.raises(ValueError):
        model.CallEstimate(*tokens)  # type: ignore[arg-type]


def test_a_route_names_its_pinned_model() -> None:
    with pytest.raises(ValueError):
        model.CallRoute(adapter=object(), model_identity="")  # type: ignore[arg-type]


def test_the_spend_of_a_scope_is_committed_money_plus_reserved() -> None:
    spend = model.Spend(actual_micros=3, reserved_micros=4)
    assert spend.committed_micros == 7
