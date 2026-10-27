"""The USD ceilings, the 1.2 x overrun and `not_metered` on a real PostgreSQL (`CMP-SPEND-01`, decision 19).

The sums come from the journal itself (what the job has spent, what the installation has spent today, what is in
flight), so these tests fill the journal the only way the database allows and ask the wrapper for one more call.
The day ceiling reads the whole installation: every test that needs an empty day asks for ``clean_day``.

Mutations recorded in ``docs/program/CMP-SPEND-01.md``: a ceiling that is not checked before the call, the
overrun that does not pause, the installation lock that is not taken, a ``not_metered`` call that is limited, a
day that is not the UTC day.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from auditmanager.comparison.public import CallRefused, ComparisonModelCaller, ComparisonSpendRepository

USD = 1_000_000


def _fill(journal: Any, queue: Any, revision: str, **row: Any) -> str:
    """A call of another item of the same AI job, in the state the test needs."""
    other = queue.claimed(ai_job_id=row.pop("job", "job-A"))
    return journal.insert(other.work_id, other.attempt_id, connection_revision_id=revision, **row)


def _refused(reason: str, caller: Any, item: Any, adapter: Any, revision: str, h: Any, **kw: Any) -> None:
    with pytest.raises(CallRefused) as refusal:
        h.make_call(caller, item, adapter, revision, **kw)
    assert refusal.value.reason == reason and refusal.value.pauses_job is True
    assert adapter.calls == 0, "the call must be refused before it is made"


def test_the_job_ceiling_refuses_a_call_that_would_cross_it_before_the_adapter_is_called(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    _fill(journal, queue, connection[1], cost_micros=8 * USD + 500_000)        # 8.50 spent on the job
    item = queue.claimed(ai_job_id="job-A")
    adapter = h.ScriptedAdapter(reply=h.reply())
    # The next call is estimated at 2.00: 8.50 + 2.00 > 10 (the consent's estimate is high enough not to overrun).
    _refused("job_ceiling", caller, item, adapter, connection[1], h, consent_over={"estimate_usd": 9.0})
    assert journal.rows(item.work_id) == [], "a refused call leaves no row"


def test_a_call_exactly_at_the_job_ceiling_is_allowed(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    _fill(journal, queue, connection[1], cost_micros=8 * USD)                  # 8.00 + 2.00 == 10.00
    item = queue.claimed(ai_job_id="job-A")
    adapter = h.ScriptedAdapter(reply=h.reply(cost=0.1))
    h.make_call(caller, item, adapter, connection[1], consent_over={"estimate_usd": 9.0})
    assert adapter.calls == 1


def test_the_consent_may_lower_the_job_ceiling(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    _fill(journal, queue, connection[1], cost_micros=1 * USD)
    item = queue.claimed(ai_job_id="job-A")
    adapter = h.ScriptedAdapter(reply=h.reply())
    _refused("job_ceiling", caller, item, adapter, connection[1], h,
             consent_over={"ceiling_usd": 2.5, "estimate_usd": 2.0})


def test_a_job_is_the_items_that_name_it_and_nothing_else(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    """Money spent by another job does not count against this one (the day ceiling counts all of it)."""
    _fill(journal, queue, connection[1], cost_micros=9 * USD, job="job-OTHER")
    item = queue.claimed(ai_job_id="job-A")
    adapter = h.ScriptedAdapter(reply=h.reply(cost=0.1))
    h.make_call(caller, item, adapter, connection[1])
    assert adapter.calls == 1


def test_an_item_with_no_job_key_is_a_job_of_its_own(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    lonely = queue.claimed()
    journal.insert(lonely.work_id, lonely.attempt_id, cost_micros=9 * USD, connection_revision_id=connection[1])
    adapter = h.ScriptedAdapter(reply=h.reply())
    _refused("job_ceiling", caller, lonely, adapter, connection[1], h, consent_over={"estimate_usd": 9.0})
    other = queue.claimed()
    fresh = h.ScriptedAdapter(reply=h.reply(cost=0.1))
    h.make_call(caller, other, fresh, connection[1])
    assert fresh.calls == 1


@pytest.mark.parametrize("state", ["prepared", "sent", "unknown"])
def test_money_that_may_be_in_flight_counts_against_the_ceiling(
    state: str, caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    """An open call and an unknown one are reserved at their estimate: they may be spent."""
    # In flight on no connection (so that the connection's single user is not what refuses): money only.
    _fill(journal, queue, None, state=state, estimate_micros=9 * USD, job="job-A")
    item = queue.claimed(ai_job_id="job-A")
    adapter = h.ScriptedAdapter(reply=h.reply())
    _refused("job_ceiling", caller, item, adapter, connection[1], h, consent_over={"estimate_usd": 9.0})


def test_a_failed_call_without_a_cost_and_a_recorded_one_cost_nothing_against_a_ceiling(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    other = queue.claimed(ai_job_id="job-A")
    journal.insert(other.work_id, other.attempt_id, state="failed", cost_micros=0, estimate_micros=9 * USD,
                   connection_revision_id=connection[1])
    item = queue.claimed(ai_job_id="job-A")
    adapter = h.ScriptedAdapter(reply=h.reply(cost=0.1))
    h.make_call(caller, item, adapter, connection[1], consent_over={"estimate_usd": 9.0})
    assert adapter.calls == 1


# --- the day ---------------------------------------------------------------------------------------------------


def test_the_day_ceiling_refuses_a_call_that_would_cross_it(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    for number in range(5):                                         # 5 jobs of 9.80 = 49.00 today
        _fill(journal, queue, connection[1], cost_micros=9 * USD + 800_000, job=f"job-{number}")
    item = queue.claimed(ai_job_id="job-new")
    adapter = h.ScriptedAdapter(reply=h.reply())
    _refused("day_ceiling", caller, item, adapter, connection[1], h)               # 49.00 + 2.00 > 50
    assert journal.rows(item.work_id) == []


def test_a_call_exactly_at_the_day_ceiling_is_allowed(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    for number in range(5):                                         # 5 jobs of 9.60 = 48.00; 48.00 + 2.00 == 50.00
        _fill(journal, queue, connection[1], cost_micros=9 * USD + 600_000, job=f"job-{number}")
    item = queue.claimed(ai_job_id="job-new")
    adapter = h.ScriptedAdapter(reply=h.reply(cost=0.01))
    h.make_call(caller, item, adapter, connection[1])
    assert adapter.calls == 1


def test_only_todays_calls_count_against_the_day(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    for number in range(6):                                         # 6 jobs of 9.60 yesterday
        _fill(journal, queue, connection[1], cost_micros=9 * USD + 600_000, job=f"job-{number}", days_ago=2)
    item = queue.claimed(ai_job_id="job-new")
    adapter = h.ScriptedAdapter(reply=h.reply(cost=0.01))
    h.make_call(caller, item, adapter, connection[1])
    assert adapter.calls == 1


def test_the_day_counts_what_is_in_flight(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    for number in range(5):
        _fill(journal, queue, None, state="sent", estimate_micros=9 * USD + 900_000, job=f"job-{number}")
    item = queue.claimed(ai_job_id="job-new")
    adapter = h.ScriptedAdapter(reply=h.reply())
    _refused("day_ceiling", caller, item, adapter, connection[1], h)               # 49.50 + 2.00 > 50


def test_two_workers_cannot_both_fit_the_one_call_that_fits(
    sessions: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, helpers: Any, clean_day: None,
) -> None:
    """The installation lock: two calls decided at once, room for one. The second reads after the first commits."""
    for number in range(4):                                         # 4 x 10.00 = 40.00 spent today
        _fill(journal, queue, connection[1], cost_micros=10 * USD, job=f"job-{number}")
    other_connection = helpers.new_connection(sessions)
    items = [queue.claimed(ai_job_id="job-A"), queue.claimed(ai_job_id="job-B")]
    revisions = [connection[1], other_connection[1]]

    class Slow(ComparisonSpendRepository):
        """Reads the day, then dawdles: without the lock both read 40.00 before either inserts."""

        def day_spend(self, session: Any) -> Any:
            spend = super().day_spend(session)
            time.sleep(0.6)
            return spend

    slow = ComparisonModelCaller(sessions, repository=Slow())
    outcomes: list[str] = []
    adapters = [h.ScriptedAdapter(reply=h.reply(cost=0.01)) for _ in items]
    barrier = threading.Barrier(2)

    def run(index: int) -> None:
        barrier.wait()
        try:
            # Each call is estimated at 6.00: 40 + 6 fits, 40 + 6 + 6 does not.
            h.make_call(slow, items[index], adapters[index], revisions[index],
                        estimate=h.CallEstimate(1_000_000, 1_000_000), consent_over={"estimate_usd": 9.0})
            outcomes.append("sent")
        except CallRefused as refusal:
            outcomes.append(refusal.reason)

    threads = [threading.Thread(target=run, args=(i,)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ["day_ceiling", "sent"], outcomes
    assert sum(a.calls for a in adapters) == 1


# --- overrun ---------------------------------------------------------------------------------------------------


def test_a_job_that_has_overrun_makes_no_further_call(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    _fill(journal, queue, connection[1], cost_micros=6 * USD + 1, job="job-A")       # > 1.2 x 5.00
    item = queue.claimed(ai_job_id="job-A")
    adapter = h.ScriptedAdapter(reply=h.reply())
    _refused("overrun", caller, item, adapter, connection[1], h)


def test_a_job_exactly_at_one_point_two_times_its_estimate_may_go_on(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    _fill(journal, queue, connection[1], cost_micros=6 * USD, job="job-A")
    item = queue.claimed(ai_job_id="job-A")
    adapter = h.ScriptedAdapter(reply=h.reply(cost=0.01))
    h.make_call(caller, item, adapter, connection[1])
    assert adapter.calls == 1


def test_a_call_that_takes_the_job_past_one_point_two_times_its_estimate_returns_its_reply_and_a_pause(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    item = queue.claimed(ai_job_id="job-A")
    reply = h.reply(cost=6.5)                                                    # one call, 6.50 against 5.00
    result = h.make_call(caller, item, h.ScriptedAdapter(reply=reply), connection[1])
    assert result.response is reply and result.cost_micros == 6_500_000
    assert result.pause is not None and result.pause.reason == "overrun"
    # ...and the job's next call is refused for the same reason, whatever worker asks.
    second = queue.claimed(ai_job_id="job-A")
    adapter = h.ScriptedAdapter(reply=h.reply())
    _refused("overrun", caller, second, adapter, connection[1], h)


def test_a_call_inside_its_estimate_has_no_pause(
    caller: Any, queue: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    item = queue.claimed(ai_job_id="job-A")
    result = h.make_call(caller, item, h.ScriptedAdapter(reply=h.reply(cost=1.0)), connection[1])
    assert result.pause is None


# --- not_metered -------------------------------------------------------------------------------------------------


def test_a_not_metered_connection_is_not_limited_by_money(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    """Over the job ceiling, over the day ceiling, over the overrun: a subscription connection goes on."""
    for number in range(6):
        _fill(journal, queue, connection[1], cost_micros=9 * USD + 900_000, job=f"job-{number}")
    _fill(journal, queue, connection[1], cost_micros=9 * USD + 900_000, job="job-A")
    item = queue.claimed(ai_job_id="job-A")
    adapter = h.ScriptedAdapter(reply=h.reply(cost=100.0))
    result = h.make_call(caller, item, adapter, connection[1], route_over={"unmetered": True, "pin": None})
    assert adapter.calls == 1 and result.pause is None
    assert (result.cost_basis, result.cost_micros) == ("unmetered", 0)


def test_a_not_metered_call_adds_nothing_to_the_day_or_the_job(
    caller: Any, queue: Any, repository: Any, sessions: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    item = queue.claimed(ai_job_id="job-A")
    h.make_call(caller, item, h.ScriptedAdapter(reply=h.reply(cost=100.0)), connection[1],
                route_over={"unmetered": True, "pin": None})
    with sessions() as session:
        day = repository.day_spend(session)
        job = repository.job_spend(session, project_uid=item.project_uid, work_id=item.work_id, job_id="job-A")
    assert (day.actual_micros, day.reserved_micros, job.actual_micros, job.reserved_micros) == (0, 0, 0, 0)


def test_a_recorded_reply_is_not_limited_by_money_either(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    from auditmanager.analysis.public import ProviderMode

    for number in range(6):
        _fill(journal, queue, connection[1], cost_micros=9 * USD + 900_000, job=f"job-{number}")
    item = queue.claimed(ai_job_id="job-A")
    adapter = h.ScriptedAdapter(mode=ProviderMode.RECORDED, reply=h.reply(model=None))
    h.make_call(caller, item, adapter, None, with_consent=False)
    assert adapter.calls == 1
