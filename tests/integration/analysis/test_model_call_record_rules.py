"""``analysis.text.provenance``: the three refusals `ModelCallRecord.__post_init__` makes.

`W10-ANL` mutation sweep, rows PV-01 to PV-05. Disabling the closed-status-vocabulary
refusal, disabling the answered-must-carry-a-response-checksum refusal, disabling the
negative-token refusal, dropping `truncated` out of `_STATUSES_THAT_ANSWERED` and widening
`CALL_STATUSES` with a fourth member were **all** green across
`tests/integration/analysis_engine`, `tests/integration/analysis_text` and `tests/replay`.

The module's own docstring says these three checks mirror `ck_model_call_status`,
`ck_model_call_truncated_has_response` and `ck_model_call_tokens`, and that duplicating them
at this layer is worth it because this is the only layer that can say *which* call was
malformed. Nothing tested that any of them fires.

The constraints are the authority and they are read out of `db/migrations/` here, so a
vocabulary that drifts away from what the database will accept reddens at this layer rather
than at an INSERT several frames later. `db/` is not this module's tree.

The dispatch names `truncated` as the status wave 2 made first-class and asks whether every
status is now mapped by something that would notice a changed mapping. For the *record*
layer the answer was no, and PV-04 is the sharp case: dropping `truncated` from the set of
statuses that answered lets a truncated call be recorded with no response checksum, which is
exactly the row `ck_model_call_truncated_has_response` was added in migration `0005` to
forbid.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from auditmanager.analysis.text.config import ProviderMode
from auditmanager.analysis.text.provenance import ModelCallRecord
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ModelCallId

REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS = REPO_ROOT / "db" / "migrations" / "versions"

#: Pinned as literals. Checked against the migration CHECK constraints below.
CALL_STATUSES = frozenset({"succeeded", "truncated", "failed"})
STATUSES_THAT_ANSWERED = frozenset({"succeeded", "truncated"})

_SHA256 = "a" * 64


def _record(**overrides: object) -> ModelCallRecord:
    """A well-formed record, with exactly the fields a test wants changed."""
    fields: dict[str, object] = {
        "model_call_id": ModelCallId.new(),
        "provider": "anthropic",
        "model_id": "claude-opus-5",
        "provider_mode": ProviderMode.RECORDED,
        "parameters": {"max_tokens": 8192},
        "request_sha256": _SHA256,
        "response_sha256": _SHA256,
        "input_tokens": 1000,
        "output_tokens": 200,
        "latency_ms": 1234,
        "status": "succeeded",
        "cost_usd": 0.01,
    }
    fields.update(overrides)
    return ModelCallRecord(**fields)  # type: ignore[arg-type]


# --- the authority ------------------------------------------------------------------


def test_the_status_vocabulary_matches_ck_model_call_status() -> None:
    """`0003_open_items` widened the CHECK to exactly these three values."""
    sql = (MIGRATIONS / "20260911_0003_open_items.py").read_text(encoding="utf-8")
    match = re.search(
        r"ADD CONSTRAINT ck_model_call_status\s*\n\s*CHECK \(status IN \((.*?)\)\)", sql, re.S
    )
    assert match is not None, "the migration no longer declares ck_model_call_status"
    from_db = frozenset(
        part.strip().strip("'") for part in match.group(1).split(",") if part.strip()
    )
    assert from_db == CALL_STATUSES


def test_truncated_must_carry_a_response_per_migration_0005() -> None:
    """The CHECK that makes `truncated` a status that answered."""
    sql = (MIGRATIONS / "20260915_0005_truncated_call_status.py").read_text(encoding="utf-8")
    assert "ck_model_call_truncated_has_response" in sql
    assert "CHECK (status <> 'truncated' OR response_sha256 IS NOT NULL)" in sql
    assert "truncated" in STATUSES_THAT_ANSWERED


def test_tokens_must_be_non_negative_per_migration_0002() -> None:
    sql = (MIGRATIONS / "20260910_0002_pc01_schema.py").read_text(encoding="utf-8")
    assert "ck_model_call_tokens" in sql
    assert "input_tokens IS NULL OR input_tokens >= 0" in sql
    assert "output_tokens IS NULL OR output_tokens >= 0" in sql


# --- the rules ----------------------------------------------------------------------


@pytest.mark.parametrize("status", sorted(CALL_STATUSES))
def test_each_status_the_database_admits_is_constructible(status: str) -> None:
    """The negative half. All three must be accepted, or the refusal is too wide."""
    assert _record(status=status).status == status


@pytest.mark.parametrize(
    "status", ["partial", "skipped", "SUCCEEDED", "", "cut_short", "unknown"]
)
def test_a_status_outside_the_closed_vocabulary_is_refused(status: str) -> None:
    """PV-01 and PV-05."""
    with pytest.raises(DomainError) as raised:
        _record(status=status)
    error = raised.value
    assert error.code is ErrorCode.ANALYSIS_FAILED
    # Assert the rule that refused, not that something did: this message is the
    # closed-vocabulary rule and no other check in __post_init__ produces it.
    assert "succeeded|truncated|failed" in str(error)


@pytest.mark.parametrize("status", sorted(STATUSES_THAT_ANSWERED))
def test_a_status_that_answered_must_carry_a_response_checksum(status: str) -> None:
    """PV-02 and PV-04. `truncated` answered, so it needs a checksum just as `succeeded` does."""
    with pytest.raises(DomainError) as raised:
        _record(status=status, response_sha256="")
    error = raised.value
    assert error.code is ErrorCode.ANALYSIS_FAILED
    assert "claims the provider answered but carries no" in str(error)


def test_a_failed_call_may_carry_no_response_checksum() -> None:
    """The negative half: `failed` is the status that did *not* answer."""
    assert _record(status="failed", response_sha256="").response_sha256 == ""


@pytest.mark.parametrize(
    ("input_tokens", "output_tokens"), [(-1, 200), (1000, -1), (-5, -5)]
)
def test_a_negative_token_count_is_refused(input_tokens: int, output_tokens: int) -> None:
    """PV-03."""
    with pytest.raises(DomainError) as raised:
        _record(input_tokens=input_tokens, output_tokens=output_tokens)
    error = raised.value
    assert error.code is ErrorCode.ANALYSIS_FAILED
    assert "negative token count" in str(error)


def test_zero_tokens_are_not_negative() -> None:
    record = _record(input_tokens=0, output_tokens=0)
    assert record.input_tokens == 0 and record.output_tokens == 0


def test_the_record_renders_cost_to_eight_decimal_places() -> None:
    """PV-08. Rounding to 2dp would erase a sub-cent call entirely.

    0.00000123 USD is a real figure at the pinned rates: 246 input tokens at 5.0 USD per
    million. At two decimal places it renders as 0.0 and the call looks free. Both the
    input and the expected output are literals.
    """
    assert _record(cost_usd=0.00000123).as_dict()["cost_usd"] == 0.00000123
    assert _record(cost_usd=0.012345678).as_dict()["cost_usd"] == 0.01234568
    assert _record(cost_usd=0.000000004).as_dict()["cost_usd"] == 0.0


def test_cost_basis_defaults_to_estimated_not_reported() -> None:
    """PV-09. A record that did not measure must not claim it did."""
    assert _record().cost_basis == "estimated"
    assert _record().as_dict()["cost_basis"] == "estimated"
    assert _record(cost_basis="measured").as_dict()["cost_basis"] == "measured"


def test_the_rendered_record_carries_the_status_verbatim() -> None:
    assert _record(status="truncated").as_dict()["status"] == "truncated"
