"""A reclaim never re-sends a call that was prepared or sent (`CMP-SPEND-01`, ADR-0025 decision 5).

The mutation proof of the ADR, in these tests: *kill the process between send and commit, reclaim, and observe no
second send and exactly one ``unknown`` row.* "Kill" is a ``BaseException`` out of the adapter (nothing in the
wrapper catches it, so no row is settled -- what a dead process leaves); "reclaim" is the queue's own
``reclaim_expired`` with the settlers the worker's composition registers.

Mutations recorded in ``docs/program/CMP-SPEND-01.md``: the settler not registered, the settler returning
``False``, the settler not touching the ``prepared`` row, the wrapper's belt against an earlier attempt's open call.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.comparison.public import (
    CallRefused,
    ComparisonModelCaller,
    ComparisonWorkRepository,
    SPEND_SETTLERS,
)


class Killed(BaseException):
    """A process that dies: not an ``Exception``, so nothing records an outcome."""


def _killed_mid_call(caller: Any, item: Any, connection: tuple[str, str], h: Any) -> Any:
    adapter = h.ScriptedAdapter(error=Killed())
    with pytest.raises(Killed):
        h.make_call(caller, item, adapter, connection[1])
    return adapter


def test_a_reclaim_after_a_kill_between_send_and_commit_sends_nothing_again_and_leaves_one_unknown_row(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    item = queue.claimed()
    first = _killed_mid_call(caller, item, connection, h)
    assert [r["state"] for r in journal.rows(item.work_id)] == ["sent"]
    assert queue.expire_and_reclaim(item, settlers=SPEND_SETTLERS) == 1
    # The item is not back in the queue: it waits for an explicit retry.
    assert queue.work_state(item.work_id) == "spend_unknown"
    rows = journal.rows(item.work_id)
    assert [r["state"] for r in rows] == ["unknown"] and rows[0]["error_code"] == "attempt_lost"
    assert rows[0]["cost_micros"] is None and rows[0]["has_terminal"]
    # No worker can take it: nothing sends a second time.
    queue.make_due(item.work_id)
    assert queue.reclaim_item() is None
    assert first.calls == 1
    assert len(journal.rows(item.work_id)) == 1


def test_a_kill_between_the_prepared_commit_and_the_sent_commit_is_unknown_too(
    sessions: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    """The row is ``prepared`` and the adapter was never reached; the ADR still says ``unknown`` (it cannot be shown)."""
    item = queue.claimed()

    class DiesBeforeSent(ComparisonModelCaller):
        def _mark_sent(self, *args: Any, **kwargs: Any) -> None:
            raise Killed()

    adapter = h.ScriptedAdapter(reply=h.reply())
    with pytest.raises(Killed):
        h.make_call(DiesBeforeSent(sessions), item, adapter, connection[1])
    assert [r["state"] for r in journal.rows(item.work_id)] == ["prepared"]
    assert queue.expire_and_reclaim(item, settlers=SPEND_SETTLERS) == 1
    assert [r["state"] for r in journal.rows(item.work_id)] == ["unknown"]
    assert queue.work_state(item.work_id) == "spend_unknown" and adapter.calls == 0


def test_an_attempt_that_made_no_call_is_requeued_as_before(
    queue: Any, connection: tuple[str, str],
) -> None:
    """The settler answers ``False`` for an attempt with no open call: the item goes back to the queue."""
    item = queue.claimed()
    assert queue.expire_and_reclaim(item, settlers=SPEND_SETTLERS) == 1
    assert queue.work_state(item.work_id) == "queued"


def test_an_attempt_whose_calls_all_ended_is_requeued_as_before(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    item = queue.claimed()
    h.make_call(caller, item, h.ScriptedAdapter(reply=h.reply(cost=0.1)), connection[1])
    assert queue.expire_and_reclaim(item, settlers=SPEND_SETTLERS) == 1
    assert queue.work_state(item.work_id) == "queued"
    assert [r["state"] for r in journal.rows(item.work_id)] == ["completed"]


def test_the_settler_touches_only_the_lost_attempts_calls(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    lost, other = queue.claimed(), queue.claimed()
    _killed_mid_call(caller, lost, connection, h)
    journal.insert(other.work_id, other.attempt_id, state="sent", estimate_micros=1, connection_revision_id=None)
    queue.expire_and_reclaim(lost, settlers=SPEND_SETTLERS)
    assert [r["state"] for r in journal.rows(lost.work_id)] == ["unknown"]
    assert [r["state"] for r in journal.rows(other.work_id)] == ["sent"], "another attempt's call must stay open"


def test_the_workers_composition_hands_the_settler_to_the_queue_and_its_reclaim_pass_uses_it(
    sessions: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, caller: Any, clean_day: None,
    comparison_engine: Any,
) -> None:
    """End to end through the production wiring: ``build_comparison_work`` -> the runner's ``reclaim()``."""
    from auditmanager.bootstrap.composition import build_comparison_work

    item = queue.claimed()
    _killed_mid_call(caller, item, connection, h)
    with sessions() as session:
        session.execute(text(
            "UPDATE comparison_work_attempt SET lease_expires_at = statement_timestamp() - interval '1 second' "
            "WHERE comparison_work_attempt_id = :a"), {"a": item.attempt_id})
        session.commit()
    runner = build_comparison_work(
        sessions=sessions, engine=comparison_engine, blob_store=object(),
        environ={"AUDITMANAGER_COMPARISON_MODULES": "versions"},
    )
    assert runner.reclaim() >= 1
    assert queue.work_state(item.work_id) == "spend_unknown"
    assert [r["state"] for r in journal.rows(item.work_id)] == ["unknown"]


def test_an_explicit_retry_clears_spend_unknown_and_the_item_may_send_again(
    caller: Any, queue: Any, journal: Any, sessions: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    """Only «Повторить» sends again, and then as a new call under a new attempt: the unknown row stays as the trail."""
    item = queue.claimed()
    _killed_mid_call(caller, item, connection, h)
    queue.expire_and_reclaim(item, settlers=SPEND_SETTLERS)
    with sessions() as session:
        assert ComparisonWorkRepository().retry_spend_unknown(session, item.work_id) == "queued"
        session.commit()
    queue.make_due(item.work_id)
    again = queue.reclaim_item()
    assert again is not None and again.attempt_no == 2
    adapter = h.ScriptedAdapter(reply=h.reply(cost=0.1))
    h.make_call(caller, again, adapter, connection[1])
    assert adapter.calls == 1
    assert [r["state"] for r in journal.rows(item.work_id)] == ["unknown", "completed"]


# --- the belt: nothing is sent for an item whose earlier attempt left a call open --------------------------------------


def test_an_earlier_attempts_open_call_stops_the_next_attempt_from_sending_if_no_settler_ran(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    """The settler is the guard; this is the second one. The reclaim ran with *no* settler (the mutation), the item
    went back to the queue with attempt 1's call still ``sent``, and attempt 2 asks to send: it is refused."""
    item = queue.claimed()
    _killed_mid_call(caller, item, connection, h)
    # Attempt 1 ends ``lost`` without anyone settling its row: the state a missing settler would leave.
    queue.expire_and_reclaim(item, settlers=())
    assert queue.work_state(item.work_id) == "queued"
    queue.make_due(item.work_id)
    again = queue.reclaim_item()
    assert again is not None and again.attempt_no == 2
    adapter = h.ScriptedAdapter(reply=h.reply())
    with pytest.raises(CallRefused) as refusal:
        h.make_call(caller, again, adapter, connection[1])
    assert refusal.value.reason == "unsettled_call" and adapter.calls == 0
    assert [r["state"] for r in journal.rows(item.work_id)] == ["sent"]


def test_a_row_an_ended_attempt_left_open_is_settled_by_the_next_call_anywhere(
    caller: Any, queue: Any, journal: Any, sessions: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    """The queue settles only a *lost* attempt, and only through the settlers it is given (none here); a row left open
    by an attempt that is over is settled ``unknown`` the next time any call is prepared."""
    stale = queue.claimed()
    _killed_mid_call(caller, stale, connection, h)
    queue.expire_and_reclaim(stale, settlers=())                   # attempt lost, row still sent
    assert [r["state"] for r in journal.rows(stale.work_id)] == ["sent"]
    with sessions() as session:                                    # the requeued item is not the next one claimed
        ComparisonWorkRepository().cancel(session, stale.work_id)
        session.commit()
    fresh = queue.claimed()
    h.make_call(caller, fresh, h.ScriptedAdapter(reply=h.reply(cost=0.1)), connection[1])
    rows = journal.rows(stale.work_id)
    assert [r["state"] for r in rows] == ["unknown"] and rows[0]["error_code"] == "attempt_ended"


def test_a_cancel_that_arrives_with_a_lost_lease_is_settled_by_the_queues_reclaim_too(
    caller: Any, queue: Any, journal: Any, sessions: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    """``CMP-C0-FIX-01`` (the finding of ``CMP-SPEND-01``, report section 8 item 2): ``reclaim_expired`` used to end a
    cancelled item before it asked the settlers, so a call that was ``sent`` when the worker died stayed open until
    housekeeping. It now asks them first: the cancel still wins (the item is ``cancelled``, not ``spend_unknown``) and
    the call is ``unknown`` the moment the reclaim commits, with the reason a settled lost attempt carries."""
    item = queue.claimed()
    adapter = _killed_mid_call(caller, item, connection, h)
    with sessions() as session:
        ComparisonWorkRepository().cancel(session, item.work_id)           # a cancel is requested while it runs
        session.commit()
    assert [r["state"] for r in journal.rows(item.work_id)] == ["sent"]
    queue.expire_and_reclaim(item, settlers=SPEND_SETTLERS)
    assert queue.work_state(item.work_id) == "cancelled", "the cancel wins over the unknown outcome"
    rows = journal.rows(item.work_id)
    assert [r["state"] for r in rows] == ["unknown"], "no sent call may stay open behind a cancelled item"
    assert rows[0]["error_code"] == "attempt_lost" and rows[0]["has_terminal"] and rows[0]["cost_micros"] is None
    assert adapter.calls == 1
    # Nothing is left for housekeeping: the next call anywhere finds no open row of that item to settle.
    fresh = queue.claimed()
    h.make_call(caller, fresh, h.ScriptedAdapter(reply=h.reply(cost=0.1)), connection[1])
    assert [r["state"] for r in journal.rows(item.work_id)] == ["unknown"]
    assert journal.rows(item.work_id)[0]["error_code"] == "attempt_lost", "not re-settled as attempt_ended"
