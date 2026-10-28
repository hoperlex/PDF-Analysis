"""The money rules of a comparison call (ADR-0025 decision 19, `Q-CMP-7`), as pure functions.

The meter of the Run path (``analysis.text.cost.CostMeter``) checks twice and the two checks catch
different failures; so do these:

* **before** a call (:func:`check_before_call`): the job has not already overrun (actual spend above
  1.2 x the estimate it was consented to), and the call -- at its estimate, on top of everything the
  job and the day have spent or may have spent -- fits under the job ceiling and under the day
  ceiling. The meter refuses a run that is *at* its ceiling; this refuses a call that would *cross*
  it, because the ceilings here are hard and a call cannot be taken back;
* **after** a call (:func:`check_after_call`): on the measured cost, so a single call that turns out
  far more expensive than its estimate pauses the job rather than being noticed in a bill.

The job ceiling is the lower of the consent's ceiling and the hard USD 10. Nothing here is applied to
an unmetered call: the caller does not invoke it (``not_metered`` connections are not limited by
money, decision 19).
"""

from __future__ import annotations

from auditmanager.comparison.spend.errors import (
    REASON_DAY_CEILING,
    REASON_JOB_CEILING,
    REASON_OVERRUN,
    CallRefused,
)
from auditmanager.comparison.spend.model import (
    DAY_CEILING_MICROS,
    JOB_CEILING_MICROS,
    Consent,
    Spend,
    SpendPause,
    overruns,
)

__all__ = ["check_after_call", "check_before_call", "job_ceiling_micros"]


def job_ceiling_micros(consent: Consent) -> int:
    """The ceiling one job may not pass: the user's, and never above the hard USD 10."""
    return min(consent.ceiling_micros, JOB_CEILING_MICROS)


def check_before_call(*, estimate_micros: int, consent: Consent, job: Spend, day: Spend) -> None:
    """Refuse (``CallRefused``) unless the call may be made. Every refusal pauses the job."""
    if overruns(job.actual_micros, consent.estimate_micros):
        raise CallRefused(REASON_OVERRUN, pauses_job=True)
    if job.committed_micros + estimate_micros > job_ceiling_micros(consent):
        raise CallRefused(REASON_JOB_CEILING, pauses_job=True)
    if day.committed_micros + estimate_micros > DAY_CEILING_MICROS:
        raise CallRefused(REASON_DAY_CEILING, pauses_job=True)


def check_after_call(*, consent: Consent, job: Spend) -> SpendPause | None:
    """The pause a call that has just been paid for causes, if any: the job's actual spend is above
    1.2 x its estimate, or above its ceiling."""
    if overruns(job.actual_micros, consent.estimate_micros):
        return SpendPause(REASON_OVERRUN)
    if job.actual_micros > job_ceiling_micros(consent):
        return SpendPause(REASON_JOB_CEILING)
    return None
