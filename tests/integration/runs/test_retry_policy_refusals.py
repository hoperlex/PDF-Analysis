"""The four refusals :class:`RetryPolicy` makes that no test had ever asked it to make.

``tests/integration/runs/test_retry_policy.py`` drives the retry policy through
``execute_run`` against the real chain, and it is thorough about the *behaviour*: how many
times the provider was asked, what was waited, what the database now says. It also guards
the one construction-time refusal that has an external authority — the frozen error
catalog's ``retryable`` flag.

It does not guard the other four. ``W10-RUN`` mutated each of them away on a copy of
``src/`` and ran the whole of ``tests/integration/runs`` and ``tests/integration/ingest``
against it; all 123 tests passed every time:

* ``if self.attempt_budget < 1:`` → ``if False:`` — a policy that gives a stage **no**
  attempts constructs;
* ``if len(self.backoff_seconds) != self.attempt_budget - 1:`` → ``if False:`` — a budget
  and a ladder that disagree construct, leaving one attempt's wait undefined, which is the
  exact fault the production docstring says the check exists to prevent;
* ``if any(wait < 0 for wait in self.backoff_seconds):`` → ``if False:`` — a negative wait
  constructs;
* ``backoff_before_attempt``'s ``raise ValueError(...)`` → ``return 0.0`` — an attempt past
  the budget silently waits nothing instead of saying it is past the budget.

Each of those is reachable: ``RetryPolicy`` is public, exported from
:mod:`auditmanager.runs`, and every field is a constructor argument. ``execute_run`` takes
a ``retry_policy=`` argument, so a composition can supply any of them.

Why the values here are literals
--------------------------------
Every expected value below is **written out**, never imported from the module and never
recomputed from it. ``ATTEMPT_BUDGET`` is spelled ``3`` and ``BACKOFF_SECONDS`` is spelled
``(2.0, 8.0)``. Wave 9's five vacuous tests were vacuous because they built the expected
value out of the constant under test, so raising the constant moved both sides of the
comparison together. A test here that said ``len(BACKOFF_SECONDS) == ATTEMPT_BUDGET - 1``
would agree with the module under every mutation of either.

The independent authority for the *relationship* is the module's own stated contract —
"Exactly ``ATTEMPT_BUDGET - 1`` entries, checked at construction" — which is a claim about
what the constructor does, and that claim is what these tests make falsifiable. The
authority for ``ATTEMPT_BUDGET == 3`` and ``BACKOFF_SECONDS == (2.0, 8.0)`` is
``P4-RUN-01``'s measurement, already pinned as literals in ``test_retry_policy.py``; this
file re-pins them at the boundaries it probes so that a drift in either constant reddens
here too rather than only there.

No database, no object store and no provider: these are refusals a constructor makes, and
routing them through the chain would test the chain.
"""

from __future__ import annotations

import pytest

from auditmanager.runs import RetryPolicy
from auditmanager.runs.retry import not_attempted

# The pinned figures, written out. Spelled here and compared against the module's own
# defaults below, so this file also fails if either pin drifts.
PINNED_ATTEMPT_BUDGET = 3
PINNED_BACKOFF_SECONDS = (2.0, 8.0)


def test_the_defaults_this_file_probes_are_still_the_pinned_ones() -> None:
    """The precondition for every boundary below, stated as literals.

    Without this, ``backoff_before_attempt(4)`` being "past the budget" would be a claim
    about whatever the budget happens to be, and a budget raised to four would make the
    refusal test below pass by not refusing anything it was asked about.
    """
    policy = RetryPolicy()
    assert policy.attempt_budget == 3
    assert policy.backoff_seconds == (2.0, 8.0)
    assert (PINNED_ATTEMPT_BUDGET, PINNED_BACKOFF_SECONDS) == (3, (2.0, 8.0))


# --- the constructor's three arithmetic refusals ------------------------------


@pytest.mark.parametrize("budget", [0, -1])
def test_a_policy_that_gives_a_stage_no_attempts_does_not_construct(budget: int) -> None:
    """"A stage gets at least one attempt" is a refusal, not a docstring.

    A budget of zero is not a conservative setting: ``has_budget_for(1)`` would be
    ``False``, the executor's loop would run its first attempt anyway — it asks the
    provider before it asks about budget — and ``budget_exhausted`` would then report
    ``True`` for a stage that was never short of a try. Refusing at construction is what
    keeps that shape out of the tree.
    """
    with pytest.raises(ValueError) as refusal:
        RetryPolicy(attempt_budget=budget, backoff_seconds=())
    assert "at least one attempt" in str(refusal.value)


@pytest.mark.parametrize(
    ("budget", "ladder"),
    [
        # One wait short of the pinned budget: attempt 3 would have no wait defined.
        (3, (2.0,)),
        # One too many: a wait exists for an attempt the budget never reaches.
        (3, (2.0, 8.0, 32.0)),
        # The pinned ladder against a budget of two: the same disagreement, other way up.
        (2, (2.0, 8.0)),
        # A budget of one takes no waits at all; any ladder is one too many.
        (1, (2.0,)),
    ],
)
def test_a_budget_and_a_ladder_that_disagree_do_not_construct(
    budget: int, ladder: tuple[float, ...]
) -> None:
    """Exactly ``budget - 1`` waits, or the policy does not exist.

    The module says why: "a budget and a backoff ladder that disagree would leave one
    attempt's wait undefined". With the check removed, ``RetryPolicy(attempt_budget=3,
    backoff_seconds=(2.0,))`` constructs, and the third attempt's wait comes out of
    ``backoff_before_attempt``'s ``IndexError`` path instead of the ladder.

    The message is asserted for its **numbers**, not merely for raising: it must name the
    budget it was given and the count it needed, so a reader of the failure knows which
    half to change.
    """
    with pytest.raises(ValueError) as refusal:
        RetryPolicy(attempt_budget=budget, backoff_seconds=ladder)
    message = str(refusal.value)
    assert f"a budget of {budget} attempts needs" in message
    assert f"{budget - 1} backoff values" in message
    assert f"got {len(ladder)}" in message


def test_the_pinned_budget_and_the_pinned_ladder_do_agree() -> None:
    """The mirror image, so the four cases above cannot pass by refusing everything.

    Both sides written out: a budget of three and a two-step ladder. This is the one
    combination the pins describe, and it constructs.
    """
    policy = RetryPolicy(attempt_budget=3, backoff_seconds=(2.0, 8.0))
    assert policy.attempt_budget == 3
    assert policy.backoff_seconds == (2.0, 8.0)


@pytest.mark.parametrize("ladder", [(-1.0,), (2.0, -0.001)])
def test_a_negative_wait_does_not_construct(ladder: tuple[float, ...]) -> None:
    """A backoff is a wait. There is no such thing as waiting minus one second.

    Unrefused, a negative wait reaches ``sleep()``. ``time.sleep(-1.0)`` raises
    ``ValueError`` from inside the attempt loop, which would surface as an unclassified
    fault in the middle of a run rather than as a refusal to build the policy.
    """
    with pytest.raises(ValueError) as refusal:
        RetryPolicy(attempt_budget=len(ladder) + 1, backoff_seconds=ladder)
    assert "a backoff cannot be negative" in str(refusal.value)


def test_a_zero_wait_is_not_negative_and_does_construct() -> None:
    """The boundary is ``< 0``, not ``<= 0``. Zero is a legitimate ladder entry."""
    policy = RetryPolicy(attempt_budget=3, backoff_seconds=(0.0, 0.0))
    assert policy.backoff_seconds == (0.0, 0.0)


# --- the ladder read at its boundaries ----------------------------------------


def test_the_ladder_is_read_by_attempt_and_the_first_attempt_never_waits() -> None:
    """Every rung, written out, plus the zero the first attempt takes.

    ``test_retry_policy.py`` asserts the waits an execution actually took, which is the
    behaviour that matters; this asserts the mapping itself, so a ladder read off by one
    is a failure here with the two numbers in it rather than a sequence mismatch there.
    """
    policy = RetryPolicy()
    assert policy.backoff_before_attempt(1) == 0.0
    assert policy.backoff_before_attempt(2) == 2.0
    assert policy.backoff_before_attempt(3) == 8.0
    # Attempt 0 and below are not attempts; they are not an error either, and they wait
    # for nothing rather than indexing backwards into the ladder.
    assert policy.backoff_before_attempt(0) == 0.0
    assert policy.backoff_before_attempt(-5) == 0.0


@pytest.mark.parametrize("attempt", [4, 5, 99])
def test_an_attempt_past_the_budget_is_refused_and_not_silently_free(
    attempt: int,
) -> None:
    """Asking for the wait before an attempt the budget does not allow is an error.

    With the refusal replaced by ``return 0.0`` the whole of
    ``tests/integration/runs`` and ``tests/integration/ingest`` stays green, because the
    executor's loop never asks: it breaks on ``has_budget_for`` first. That makes this a
    guard on the *policy object's* contract rather than on the executor's use of it — and
    the policy object is public and takes a caller's own budget, so a composition that
    computed an attempt number wrongly would get a zero wait and no complaint.

    Four is the first refused attempt against the pinned budget of three, written out.
    """
    policy = RetryPolicy()
    with pytest.raises(ValueError) as refusal:
        policy.backoff_before_attempt(attempt)
    message = str(refusal.value)
    assert f"attempt {attempt} is past a budget of 3" == message


def test_the_last_allowed_attempt_is_not_past_the_budget() -> None:
    """The mirror image of the refusal, at the boundary it sits on.

    Three is allowed and four is not. Without this the test above would pass against a
    policy that refused every attempt.
    """
    policy = RetryPolicy()
    assert policy.has_budget_for(3) is True
    assert policy.has_budget_for(4) is False
    assert policy.backoff_before_attempt(3) == 8.0


# --- the stage that never reached the provider --------------------------------


def test_a_stage_that_never_ran_records_no_attempts_rather_than_one_failed_one() -> None:
    """``attempts: 0`` and ``attempts: 1`` are different claims about the same run.

    ``not_attempted`` is what the executor records for a chain that halted before the
    model stage, and for a stage whose required inputs were missing. Reporting ``1`` would
    say the provider was asked and refused, which it was not — and would make
    ``P4_CLOSURE.md`` §1's alternative headline, the count of documents that published
    without a retry, count runs that never reached a provider at all.

    Every number is written out. Mutating ``attempts=0`` to ``attempts=1`` in
    ``not_attempted`` left all 123 tests in ``runs`` and ``ingest`` green.
    """
    summary = not_attempted(RetryPolicy())

    assert summary.attempts == 0
    assert summary.attempt_budget == 3
    assert summary.retried_on_error_code is None
    assert summary.records == ()
    assert summary.retried is False
    assert summary.budget_exhausted is False, (
        "a stage that was never attempted did not run out of attempts; it never spent one"
    )
    assert summary.metrics() == {
        "attempts": 0,
        "attempt_budget": 3,
        "attempt_budget_exhausted": False,
        "retried_on_error_code": None,
        "retry_waited_seconds": 0.0,
    }


def test_the_recorded_wait_keeps_sub_second_precision() -> None:
    """``retry_waited_seconds`` is the wait that was taken, not the wait rounded to a second.

    The pinned ladder is ``(2.0, 8.0)``, so every total a production run can produce is a
    whole number and the rounding is invisible to every existing test — rounding to zero
    places left all 123 of them green. It stops being invisible the moment a composition
    supplies its own ladder, which ``execute_run(retry_policy=...)`` allows, and a field
    that reports ``0`` for a run that waited a quarter of a second is worse than no field.

    Both waits and the expected total are written out.
    """
    from auditmanager.runs.retry import AttemptLedger

    ledger = AttemptLedger(attempt_budget=3)
    ledger.record(status="failed", error=None, waited_seconds=0.0)
    ledger.record(status="failed", error=None, waited_seconds=0.25)
    ledger.record(status="succeeded", error=None, waited_seconds=0.125)

    summary = ledger.close()

    assert summary.attempts == 3
    assert summary.waited_seconds_total == 0.375
    assert summary.metrics()["retry_waited_seconds"] == 0.375
