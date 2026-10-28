"""The life of a call on a real PostgreSQL (`CMP-SPEND-01`, ADR-0025 decision 5).

What these tests stand for, each with a mutation recorded in ``docs/program/CMP-SPEND-01.md``:

* **A provider call without a prior ``prepared`` row is impossible.** The adapter looks at the database from a
  connection of its own *at the instant it is called*; what it sees is what a crash there would leave.
* The row moves ``prepared -> sent -> completed | failed | unknown`` and the wrapper never sends twice.
* A reply from another model is refused (`R-133`); a recorded reply is journalled as recorded.
* A worker that lost its lease neither sends nor overwrites what the reclaim settled.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.analysis.public import ProviderMode, ProxyDispatchError
from auditmanager.comparison.public import CallFailed, CallLost, CallRefused, OutcomeUnknown, SPEND_SETTLERS
from auditmanager.shared.errors import ErrorCode


def _seen_by_another_connection(sessions: Any, work_id: str) -> list[dict[str, Any]]:
    with sessions() as session:
        return [dict(r) for r in session.execute(text(
            "SELECT state, request_sha256, estimate_micros, sent_at IS NOT NULL AS has_sent, provider_mode "
            "FROM comparison_model_call WHERE comparison_work_id = :w"), {"w": work_id}).mappings()]


def test_the_prepared_row_is_committed_and_visible_before_the_adapter_is_called(
    caller: Any, queue: Any, journal: Any, sessions: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    item = queue.claimed()
    seen: list[list[dict[str, Any]]] = []
    adapter = h.ScriptedAdapter(reply=h.reply(), on_call=lambda request: seen.append(
        _seen_by_another_connection(sessions, item.work_id)))
    result = h.make_call(caller, item, adapter, connection[1], label="one")
    # At the instant of the call, another connection saw exactly one row, ``sent``, for this very request.
    assert len(seen) == 1 and len(seen[0]) == 1
    row = seen[0][0]
    assert row["state"] == "sent" and row["has_sent"] is True
    assert row["request_sha256"] == h.request("one").request_sha256
    assert row["estimate_micros"] == 2_000_000 and row["provider_mode"] == "live"
    # Afterwards the same row is completed with the reply's cost, and nothing else was added.
    rows = journal.rows(item.work_id)
    assert len(rows) == 1 and rows[0]["state"] == "completed" and rows[0]["call_id"] == result.call_id
    assert (rows[0]["cost_basis"], rows[0]["cost_micros"]) == ("estimated", 1_000_000)
    assert rows[0]["input_tokens"] == 500_000 and rows[0]["output_tokens"] == 100_000
    assert rows[0]["has_terminal"] and rows[0]["error_code"] is None


def test_a_reported_cost_is_journalled_measured(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    item = queue.claimed()
    result = h.make_call(caller, item, h.ScriptedAdapter(reply=h.reply(cost=0.123456)), connection[1])
    assert (result.cost_basis, result.cost_micros) == ("measured", 123_456)
    assert journal.rows(item.work_id)[0]["cost_micros"] == 123_456


def test_the_journal_row_carries_the_pinned_model_the_revision_and_the_request_digest(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    item = queue.claimed()
    h.make_call(caller, item, h.ScriptedAdapter(reply=h.reply()), connection[1], label="digest-me")
    row = journal.rows(item.work_id)[0]
    assert row["model_identity"] == h.MODEL and row["connection_revision_id"] == connection[1]
    assert row["request_sha256"] == h.request("digest-me").request_sha256
    assert row["attempt_id"] == item.attempt_id


def test_a_recorded_reply_is_journalled_as_recorded_and_unmetered(
    caller: Any, queue: Any, journal: Any, h: Any,
) -> None:
    item = queue.claimed()
    adapter = h.ScriptedAdapter(mode=ProviderMode.RECORDED, reply=h.reply(model=None))
    result = h.make_call(caller, item, adapter, None, with_consent=False)
    row = journal.rows(item.work_id)[0]
    assert (row["provider_mode"], row["model_identity"], row["cost_basis"], row["cost_micros"]) == (
        "recorded", "recorded", "unmetered", 0)
    assert row["estimate_micros"] == 0 and result.cost_micros == 0 and result.pause is None


def test_a_not_metered_live_call_is_journalled_unmetered_with_an_estimate_of_zero(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any,
) -> None:
    item = queue.claimed()
    result = h.make_call(
        caller, item, h.ScriptedAdapter(reply=h.reply(cost=7.0)), connection[1],
        route_over={"unmetered": True, "pin": None},
    )
    row = journal.rows(item.work_id)[0]
    assert (row["cost_basis"], row["cost_micros"], row["estimate_micros"]) == ("unmetered", 0, 0)
    assert result.cost_basis == "unmetered"


# --- failures: what the transport proves decides the row --------------------------------------------------------


def _error(dispatch_class: str, **kw: Any) -> ProxyDispatchError:
    return ProxyDispatchError(
        kw.pop("code", ErrorCode.DEPENDENCY_UNAVAILABLE), dispatch_class=dispatch_class,
        retry_safe=kw.pop("retry_safe", False), **kw)


@pytest.mark.parametrize("dispatch_class", ["not_sent", "rate_limited", "proxy_unavailable", "definite_refusal"])
def test_an_error_proven_to_precede_processing_is_failed_without_a_cost(
    dispatch_class: str, caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    item = queue.claimed()
    adapter = h.ScriptedAdapter(error=_error(dispatch_class))
    with pytest.raises(CallFailed):
        h.make_call(caller, item, adapter, connection[1])
    row = journal.rows(item.work_id)[0]
    assert row["state"] == "failed" and row["error_code"] == "dependency_unavailable"
    assert row["cost_micros"] is None and row["cost_basis"] is None and row["has_terminal"]
    assert adapter.calls == 1


def test_an_unproven_outcome_is_unknown_and_the_adapter_is_called_once(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    item = queue.claimed()
    adapter = h.ScriptedAdapter(error=_error("outcome_unknown"))
    with pytest.raises(OutcomeUnknown):
        h.make_call(caller, item, adapter, connection[1])
    rows = journal.rows(item.work_id)
    assert [r["state"] for r in rows] == ["unknown"] and rows[0]["cost_micros"] is None
    assert adapter.calls == 1, "the wrapper must never send again by itself"


def test_an_unusable_answer_is_failed_with_the_cost_it_may_have_charged(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    from auditmanager.analysis.public import ProxyDispatchError as Dispatch
    from types import SimpleNamespace

    item = queue.claimed()
    received = SimpleNamespace(response_sha256="cd" * 32, input_tokens=1_000_000, output_tokens=0, latency_ms=700)
    adapter = h.ScriptedAdapter(error=Dispatch(
        ErrorCode.ANALYSIS_FAILED, dispatch_class="outcome_unknown", retry_safe=False, received=received))
    with pytest.raises(CallFailed):
        h.make_call(caller, item, adapter, connection[1])
    row = journal.rows(item.work_id)[0]
    assert row["state"] == "failed" and row["response_sha256"] == "cd" * 32
    assert (row["cost_basis"], row["cost_micros"]) == ("estimated", 1_000_000)


def test_an_unexpected_fault_of_the_adapter_is_unknown(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    item = queue.claimed()
    with pytest.raises(OutcomeUnknown):
        h.make_call(caller, item, h.ScriptedAdapter(error=RuntimeError("boom")), connection[1])
    assert journal.rows(item.work_id)[0]["state"] == "unknown"
    assert journal.rows(item.work_id)[0]["error_code"] == "adapter_fault"


def test_a_runner_that_refused_the_images_is_unknown_on_a_metered_route_and_failed_on_a_free_one(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    refusal = _error("outcome_unknown", details={"dependency": "executor_image_input_unsupported"})
    metered = queue.claimed()
    with pytest.raises(OutcomeUnknown):
        h.make_call(caller, metered, h.ScriptedAdapter(error=refusal), connection[1])
    assert journal.rows(metered.work_id)[0]["state"] == "unknown"
    assert journal.rows(metered.work_id)[0]["error_code"] == "executor_image_input_unsupported"
    free = queue.claimed()
    with pytest.raises(CallFailed) as failure:
        h.make_call(caller, free, h.ScriptedAdapter(error=refusal), connection[1],
                    route_over={"unmetered": True, "pin": None})
    assert failure.value.reason == "executor_image_input_unsupported"
    assert journal.rows(free.work_id)[0]["state"] == "failed"


def test_a_process_killed_mid_call_leaves_the_row_sent_and_nothing_else(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    class Killed(BaseException):
        pass

    item = queue.claimed()
    with pytest.raises(Killed):
        h.make_call(caller, item, h.ScriptedAdapter(error=Killed()), connection[1])
    rows = journal.rows(item.work_id)
    assert [r["state"] for r in rows] == ["sent"] and rows[0]["has_sent"] and not rows[0]["has_terminal"]


# --- R-133 -------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("reported", ["anthropic/claude-sonnet-5", None])
def test_a_reply_from_another_model_is_refused_and_its_cost_is_kept(
    reported: str | None, caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    item = queue.claimed()
    adapter = h.ScriptedAdapter(reply=h.reply(model=reported, cost=0.5))
    with pytest.raises(CallFailed) as failure:
        h.make_call(caller, item, adapter, connection[1])
    assert failure.value.reason == "model_identity_mismatch"
    row = journal.rows(item.work_id)[0]
    assert row["state"] == "failed" and row["error_code"] == "model_identity_mismatch"
    assert (row["cost_basis"], row["cost_micros"]) == ("measured", 500_000)
    assert row["response_sha256"] is not None


def test_a_reply_that_cannot_be_held_to_a_model_is_refused_before_any_row_exists(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any,
) -> None:
    item = queue.claimed()
    adapter = h.ScriptedAdapter(reply=h.reply())
    with pytest.raises(CallRefused) as refusal:
        h.make_call(caller, item, adapter, connection[1], route_over={"expected_model": "proxy"})
    assert refusal.value.reason == "model_not_selected"
    assert adapter.calls == 0 and journal.rows(item.work_id) == []


def test_a_consent_for_another_revision_pauses_before_any_row_exists(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any,
) -> None:
    item = queue.claimed()
    adapter = h.ScriptedAdapter(reply=h.reply())
    with pytest.raises(CallRefused) as refusal:
        h.make_call(caller, item, adapter, connection[1], consent_over={"connection_revision_id": "excr_OTHER"})
    assert refusal.value.reason == "consent_stale" and refusal.value.pauses_job
    assert adapter.calls == 0 and journal.rows(item.work_id) == []


def test_a_live_call_without_a_consent_makes_no_row_and_no_call(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any,
) -> None:
    item = queue.claimed()
    adapter = h.ScriptedAdapter(reply=h.reply())
    with pytest.raises(CallRefused) as refusal:
        h.make_call(caller, item, adapter, connection[1], with_consent=False)
    assert refusal.value.reason == "consent_required"
    assert adapter.calls == 0 and journal.rows(item.work_id) == []


# --- the lease ---------------------------------------------------------------------------------------------------


def test_a_worker_that_lost_its_lease_sends_nothing_and_makes_no_row(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any,
) -> None:
    item = queue.claimed()
    assert queue.expire_and_reclaim(item, settlers=SPEND_SETTLERS) == 1
    adapter = h.ScriptedAdapter(reply=h.reply())
    with pytest.raises(CallLost) as lost:
        h.make_call(caller, item, adapter, connection[1])
    assert lost.value.call_id is None and adapter.calls == 0 and journal.rows(item.work_id) == []


def test_a_lease_lost_between_the_two_commits_sends_nothing(
    sessions: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    from auditmanager.comparison.public import ComparisonModelCaller

    item = queue.claimed()

    class Racing(ComparisonModelCaller):
        def _prepare(self, *args: Any, **kwargs: Any) -> str:
            call_id = super()._prepare(*args, **kwargs)
            queue.expire_and_reclaim(item, settlers=SPEND_SETTLERS)       # the reclaim runs after the prepare commit
            return call_id

    adapter = h.ScriptedAdapter(reply=h.reply())
    with pytest.raises(CallLost):
        h.make_call(Racing(sessions), item, adapter, connection[1])
    assert adapter.calls == 0
    row = journal.rows(item.work_id)[0]
    # The reclaim made the open row unknown (it cannot know nothing was sent); the wrapper does not overwrite it.
    assert row["state"] == "unknown" and not row["has_sent"]
    assert queue.work_state(item.work_id) == "spend_unknown"


def test_a_lease_lost_between_the_two_commits_sends_nothing_even_when_no_settler_ended_the_row(
    sessions: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    """The fence of the send is the attempt's authority, not the row's state: here the reclaim ran with no settler,
    so the row is still ``prepared`` and only ``require_current`` stands between the lost lease and the provider."""
    from auditmanager.comparison.public import ComparisonModelCaller

    item = queue.claimed()

    class Racing(ComparisonModelCaller):
        def _prepare(self, *args: Any, **kwargs: Any) -> str:
            call_id = super()._prepare(*args, **kwargs)
            queue.expire_and_reclaim(item, settlers=())
            return call_id

    adapter = h.ScriptedAdapter(reply=h.reply())
    with pytest.raises(CallLost):
        h.make_call(Racing(sessions), item, adapter, connection[1])
    assert adapter.calls == 0
    row = journal.rows(item.work_id)[0]
    # Nothing was sent, and the wrapper knows it: the row is failed, not left open, and was never marked sent.
    assert row["state"] == "failed" and row["error_code"] == "lease_lost" and not row["has_sent"]


def test_a_reply_that_arrives_after_the_reclaim_settled_the_row_is_lost_not_published(
    caller: Any, queue: Any, journal: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    item = queue.claimed()

    def reclaim_while_in_flight(request: Any) -> None:
        queue.expire_and_reclaim(item, settlers=SPEND_SETTLERS)

    adapter = h.ScriptedAdapter(reply=h.reply(), on_call=reclaim_while_in_flight)
    with pytest.raises(CallLost) as lost:
        h.make_call(caller, item, adapter, connection[1])
    assert lost.value.call_id is not None
    rows = journal.rows(item.work_id)
    assert [r["state"] for r in rows] == ["unknown"], "the settled row is not overwritten by a late reply"
    assert rows[0]["cost_micros"] is None and rows[0]["response_sha256"] is None


# --- the database's own guards behind the wrapper -----------------------------------------------------------------


def test_the_database_refuses_a_row_inserted_in_any_state_but_prepared(
    queue: Any, sessions: Any, connection: tuple[str, str],
) -> None:
    """The structural half of "a call without a prior prepared row is impossible": no row can be born ``sent``."""
    from sqlalchemy.exc import DBAPIError

    item = queue.claimed()
    with pytest.raises(DBAPIError) as refused, sessions() as session:
        session.execute(text(
            "INSERT INTO comparison_model_call (comparison_model_call_id, comparison_work_id, "
            "comparison_work_attempt_id, work_kind, state, provider_mode, model_identity, request_sha256, "
            "estimate_micros, sent_at) VALUES ('cmc_01J00000000000000000000000', :w, :a, 'x_kind', 'sent', "
            "'live', 'm', :sha, 0, clock_timestamp())"),
            {"w": item.work_id, "a": item.attempt_id, "sha": "ab" * 32})
    assert "inserted prepared" in str(refused.value)


def test_a_settled_row_never_moves_again(
    caller: Any, queue: Any, sessions: Any, repository: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    item = queue.claimed()
    result = h.make_call(caller, item, h.ScriptedAdapter(reply=h.reply()), connection[1])
    with sessions() as session:
        assert repository.mark_unknown(session, result.call_id, error_code="late_word") is False
        assert repository.fail(session, result.call_id, error_code="late_word") is False
        assert repository.complete(
            session, result.call_id, response_sha256="ab" * 32, input_tokens=1, output_tokens=1, latency_ms=1,
            cost_basis="measured", cost_micros=1) is False
        session.rollback()


def test_the_pull_task_can_be_linked_to_its_journal_row_once(
    caller: Any, queue: Any, sessions: Any, repository: Any, connection: tuple[str, str], h: Any, clean_day: None,
) -> None:
    from auditmanager.executors.runner_repository import RunnerRepository

    item = queue.claimed()

    def link(request: Any) -> None:
        with sessions() as session:
            call = repository.calls_of_work(session, item.work_id)[0]
            task = RunnerRepository().insert_task(
                session, connection_id=connection[0], revision_id=connection[1], origin="comparison_call",
                run_id=None, attempt_id=None, model_call_id=None, probe_id=None, expected_model=h.GATEWAY,
                payload={}, deadline_seconds=60, comparison_attempt_id=item.attempt_id)
            assert repository.attach_task(session, call.call_id, task.task_id) is True
            assert repository.attach_task(session, call.call_id, task.task_id) is False
            session.commit()

    h.make_call(caller, item, h.ScriptedAdapter(reply=h.reply(), on_call=link), connection[1])
    with sessions() as session:
        call = repository.calls_of_work(session, item.work_id)[0]
    assert call.executor_task_id is not None and call.state == "completed"
