"""The money rules of a comparison call (`CMP-SPEND-01`, ADR-0025 decision 19), pure: each guard is a refusal
that must fire. Container-free."""

from __future__ import annotations

import pytest

from auditmanager.comparison.spend import ceilings, errors, model

DIGEST = "cd" * 32
ZERO = model.Spend(0, 0)


def _consent(*, estimate_usd: float = 5.0, ceiling_usd: float = 10.0) -> model.Consent:
    return model.Consent(
        estimate_digest=DIGEST, estimate_usd=estimate_usd, ceiling_usd=ceiling_usd,
        connection_revision_id="excr_X", pinned_model="claude-opus-5",
    )


def _usd(amount: float) -> int:
    return model.estimate_micros_of(amount)


def _refused(**kwargs: object) -> errors.CallRefused:
    with pytest.raises(errors.CallRefused) as info:
        ceilings.check_before_call(**kwargs)  # type: ignore[arg-type]
    return info.value


def test_a_call_that_fits_every_ceiling_is_allowed() -> None:
    ceilings.check_before_call(
        estimate_micros=_usd(1), consent=_consent(), job=model.Spend(_usd(2), _usd(1)), day=model.Spend(_usd(20), 0),
    )


def test_the_job_ceiling_refuses_a_call_that_would_cross_it_not_one_that_reaches_it() -> None:
    consent = _consent(estimate_usd=9.0)
    ceilings.check_before_call(estimate_micros=_usd(1), consent=consent, job=model.Spend(_usd(8), _usd(1)), day=ZERO)
    refusal = _refused(estimate_micros=_usd(1) + 1, consent=consent, job=model.Spend(_usd(8), _usd(1)), day=ZERO)
    assert refusal.reason == errors.REASON_JOB_CEILING and refusal.pauses_job is True


def test_the_job_ceiling_counts_what_may_be_in_flight_not_only_what_is_known() -> None:
    """An open or unknown call is money that may be spent: it is reserved against the ceiling."""
    refusal = _refused(
        estimate_micros=_usd(2), consent=_consent(estimate_usd=9.0), job=model.Spend(_usd(5), _usd(4)), day=ZERO,
    )
    assert refusal.reason == errors.REASON_JOB_CEILING


def test_the_consent_may_lower_the_job_ceiling_and_never_raise_it() -> None:
    consent = _consent(estimate_usd=1.0, ceiling_usd=2.0)
    assert ceilings.job_ceiling_micros(consent) == _usd(2)
    assert _refused(estimate_micros=_usd(1), consent=consent, job=model.Spend(_usd(1), _usd(0.5)), day=ZERO).reason == (
        errors.REASON_JOB_CEILING)
    assert ceilings.job_ceiling_micros(_consent(ceiling_usd=10.0)) == model.JOB_CEILING_MICROS


def test_the_day_ceiling_refuses_a_call_that_would_cross_it() -> None:
    consent = _consent()
    ceilings.check_before_call(estimate_micros=_usd(1), consent=consent, job=ZERO, day=model.Spend(_usd(40), _usd(9)))
    refusal = _refused(estimate_micros=_usd(1) + 1, consent=consent, job=ZERO, day=model.Spend(_usd(40), _usd(9)))
    assert refusal.reason == errors.REASON_DAY_CEILING and refusal.pauses_job is True


def test_the_day_ceiling_counts_reservations_too() -> None:
    assert _refused(
        estimate_micros=_usd(2), consent=_consent(), job=ZERO, day=model.Spend(_usd(30), _usd(19)),
    ).reason == errors.REASON_DAY_CEILING


def test_a_job_that_has_already_overrun_makes_no_further_call() -> None:
    consent = _consent(estimate_usd=5.0)
    over = model.Spend(_usd(6) + 1, 0)       # above 1.2 x 5.00
    assert _refused(estimate_micros=1, consent=consent, job=over, day=ZERO).reason == errors.REASON_OVERRUN
    ceilings.check_before_call(estimate_micros=1, consent=consent, job=model.Spend(_usd(6), 0), day=ZERO)


def test_the_overrun_is_judged_on_the_known_cost_not_on_reservations() -> None:
    """Reserved money is an estimate, not an actual spend: it can fill a ceiling but not overrun."""
    ceilings.check_before_call(
        estimate_micros=1, consent=_consent(estimate_usd=5.0), job=model.Spend(0, _usd(9)), day=ZERO,
    )


def test_after_a_call_an_actual_spend_above_one_point_two_times_the_estimate_pauses_the_job() -> None:
    consent = _consent(estimate_usd=5.0)
    assert ceilings.check_after_call(consent=consent, job=model.Spend(_usd(6), 0)) is None
    pause = ceilings.check_after_call(consent=consent, job=model.Spend(_usd(6) + 1, 0))
    assert pause is not None and pause.reason == errors.REASON_OVERRUN


def test_after_a_call_an_actual_spend_above_the_job_ceiling_pauses_the_job() -> None:
    consent = _consent(estimate_usd=9.5, ceiling_usd=3.0)       # 1.2 x 9.5 is not the edge here
    pause = ceilings.check_after_call(consent=consent, job=model.Spend(_usd(3) + 1, 0))
    assert pause is not None and pause.reason == errors.REASON_JOB_CEILING
    assert ceilings.check_after_call(consent=consent, job=model.Spend(_usd(3), 0)) is None
