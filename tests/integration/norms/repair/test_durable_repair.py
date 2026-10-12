"""`R-106` end to end: the write order, reconciliation, `R-79`'s tries, the ceiling, the sample.

Every case runs twice: against the in-memory store (container-free) and against the real
``norm_repair_call`` table (``-k postgres``, the owner's window). The transport is scripted;
``kit.transport.dispatches`` counts the tries that left the process, which in the real
transport are the calls that may have been paid for — every no-re-pay assertion is made
against it.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from auditmanager.norms import RepairOutcome
from auditmanager.norms.repair_journal import (
    CallState,
    Failure,
    JournalRefused,
    LocalJournal,
    RunStopped,
    StopReason,
    build_ledger,
    unknown_outcome_bound,
)
from tests.integration.norms.repair.support import (
    BASE,
    CLEAN_PAGE,
    DEGENERATE_PAGE,
    MODEL,
    PIXELS,
    SUMS,
    Answer,
    AnswerThenFail,
    Fail,
    Killed,
    Kit,
    openai_body,
    page,
)

BOUND = unknown_outcome_bound(MODEL, pixels=PIXELS)


def _ledger(kit: Kit, pages):
    assert kit.journal is not None
    return build_ledger(
        kit.journal, pages, kit.transport, model=MODEL, base_snapshot_id=BASE,
        generated_at="2026-10-12T12:00:00+00:00",
    )


def _states(kit: Kit) -> list[str]:
    return [row.state.value for row in kit.store.all_calls()]


def _file_kinds(kit: Kit) -> list[str]:
    lines = (kit.directory / "journal.jsonl").read_bytes().splitlines()
    return [json.loads(line)["kind"] for line in lines]


# --- the happy path and the write order -----------------------------------------------------


def test_a_clean_answer_is_one_paid_call_charged_at_its_reported_cost(kit: Kit) -> None:
    kit.transport.script = [Answer(openai_body(CLEAN_PAGE, cost=0.031))]
    runner = kit.runner()
    runner.reconcile()
    summary = runner.run([page()])

    assert len(kit.transport.dispatches) == 1
    assert summary.outcomes == {"repaired": 1}
    assert kit.store.charged_total() == Decimal("0.031000")
    ledger = _ledger(kit, [page()])
    assert ledger.repairs[0].outcome is RepairOutcome.REPAIRED
    assert ledger.repairs[0].replacement == CLEAN_PAGE
    assert _file_kinds(kit) == ["header", "intent", "response", "settled"]


def test_the_intent_is_on_disk_and_the_row_committed_before_the_dispatch(kit: Kit) -> None:
    """`R-106`'s order: file intent, then the row, then the call; effects database-first."""
    observed: dict[str, object] = {}

    def at(point: str) -> None:
        kinds = _file_kinds(kit)
        states = _states(kit)
        observed[point] = (kinds, states)

    kit.transport.script = [Answer(openai_body(CLEAN_PAGE))]
    runner = kit.runner()
    runner.fault = at
    runner.run([page()])

    # Intent fsynced, no row yet.
    assert observed["intent_appended"] == (["header", "intent"], [])
    # Row committed `prepared` before the transport is called.
    assert observed["row_committed"] == (["header", "intent"], ["prepared"])
    # The body is on disk before the row moves; the row moves before the file says so.
    assert observed["response_written"] == (["header", "intent"], ["prepared"])
    assert observed["checkpoint_committed"] == (["header", "intent"], ["response_received"])
    assert observed["response_appended"] == (["header", "intent", "response"], ["response_received"])
    # The settlement commits to the database before the file records it.
    assert observed["settled_committed"] == (["header", "intent", "response"], ["completed"])
    assert observed["settled_appended"] == (
        ["header", "intent", "response", "settled"], ["completed"],
    )


def test_each_try_is_its_own_idempotency_scope(kit: Kit) -> None:
    kit.transport.script = [
        Fail(Failure.RATE_LIMITED, retry_safe=True),
        Answer(openai_body(CLEAN_PAGE)),
    ]
    runner = kit.runner()
    runner.run([page()])
    rows = kit.store.all_calls()
    assert [row.call_id for row in rows] == kit.transport.dispatches
    assert len(set(kit.transport.dispatches)) == 2
    assert all(call_id.startswith("nrc_") for call_id in kit.transport.dispatches)
    assert [row.attempt_number for row in rows] == [1, 2]


# --- kills: no call is ever paid twice --------------------------------------------------------


@pytest.mark.parametrize(
    ("point", "expected_outcome", "expected_charge"),
    [
        # Before the dispatch: the call may or may not have left, so it is unknown at its bound.
        ("intent_appended", RepairOutcome.CALL_FAILED, BOUND),
        ("row_committed", RepairOutcome.CALL_FAILED, BOUND),
        # After the body reached the disk: replayed, never re-paid.
        ("response_written", RepairOutcome.REPAIRED, Decimal("0.03")),
        ("checkpoint_committed", RepairOutcome.REPAIRED, Decimal("0.03")),
        ("response_appended", RepairOutcome.REPAIRED, Decimal("0.03")),
        ("dispatched", RepairOutcome.REPAIRED, Decimal("0.03")),
        ("settled_committed", RepairOutcome.REPAIRED, Decimal("0.03")),
        ("settled_appended", RepairOutcome.REPAIRED, Decimal("0.03")),
        # After acceptance and before the ledger is written.
        ("page_done", RepairOutcome.REPAIRED, Decimal("0.03")),
    ],
)
def test_a_kill_at_any_durable_step_never_pays_twice(
    kit: Kit, point: str, expected_outcome: RepairOutcome, expected_charge: Decimal
) -> None:
    kit.transport.script = [Answer(openai_body(CLEAN_PAGE, cost=0.03))]
    kit.kill_at = point
    runner = kit.runner()
    with pytest.raises(Killed):
        runner.run([page()])
    paid_before = len(kit.transport.dispatches)

    kit.kill_at = None
    restarted = kit.runner()
    restarted.reconcile()
    restarted.run([page()])

    assert len(kit.transport.dispatches) == paid_before, "a restart re-dispatched a call"
    assert kit.transport.script == [] or point in ("intent_appended", "row_committed")
    assert kit.store.charged_total() == expected_charge
    assert all(state in ("completed", "outcome_unknown") for state in _states(kit))
    ledger = _ledger(kit, [page()])
    assert ledger.repairs[0].outcome is expected_outcome
    if expected_outcome is RepairOutcome.REPAIRED:
        assert ledger.repairs[0].replacement == CLEAN_PAGE


def test_a_kill_between_the_two_reads_resumes_with_the_second_read_only(kit: Kit) -> None:
    kit.transport.script = [
        Answer(openai_body(DEGENERATE_PAGE)),
        Answer(openai_body(CLEAN_PAGE)),
    ]
    kit.kill_at = "settled_appended"
    with pytest.raises(Killed):
        kit.runner().run([page()])
    kit.kill_at = None
    restarted = kit.runner()
    restarted.reconcile()
    restarted.run([page()])

    assert len(kit.transport.dispatches) == 2
    ledger = _ledger(kit, [page()])
    assert ledger.repairs[0].outcome is RepairOutcome.REPAIRED
    assert [a.ordinal for a in ledger.repairs[0].attempts] == [1, 2]


def test_a_page_degenerate_twice_is_two_calls_and_unreliable(kit: Kit) -> None:
    kit.transport.script = [Answer(openai_body(DEGENERATE_PAGE)), Answer(openai_body(DEGENERATE_PAGE))]
    kit.runner().run([page()])
    ledger = _ledger(kit, [page()])
    assert ledger.repairs[0].outcome is RepairOutcome.STILL_DEGENERATE
    assert ledger.unreliable_count == 1
    assert len(kit.transport.dispatches) == 2


# --- reconciliation, both directions ---------------------------------------------------------


def test_an_intent_in_the_file_but_not_in_the_database_becomes_unknown_at_its_bound(kit: Kit) -> None:
    kit.transport.script = [Answer(openai_body(CLEAN_PAGE))]
    kit.kill_at = "intent_appended"
    with pytest.raises(Killed):
        kit.runner().run([page()])
    assert kit.store.all_calls() == []

    report = kit.runner().reconcile()
    assert report.restored_rows == 1 and report.reconciled_unknown == 1
    (row,) = kit.store.all_calls()
    assert row.state is CallState.OUTCOME_UNKNOWN
    assert row.settlement.charged_usd == BOUND
    assert row.settlement.failure == Failure.RECONCILED_UNKNOWN


def test_a_call_in_the_database_but_not_in_the_file_refuses_the_start(kit: Kit, tmp_path) -> None:
    kit.transport.script = [Answer(openai_body(CLEAN_PAGE))]
    kit.runner().run([page()])
    kit.close()

    # A second journal over the same database: it never wrote the intent the row holds.
    kit.directory = tmp_path / "another-journal"
    runner = kit.runner()
    with pytest.raises(JournalRefused, match="intent_missing_from_file"):
        runner.reconcile()
    assert len(kit.transport.dispatches) == 1


def test_a_lost_volume_is_carried_forward_from_the_file(kit: Kit) -> None:
    """The database is restored from the dump taken after the first page; the file knows more."""
    first, second = page(block="a"), page(block="b")
    kit.transport.script = [
        Answer(openai_body(CLEAN_PAGE, cost=0.02)),
        Fail(Failure.OUTCOME_UNKNOWN),
        Answer(openai_body(CLEAN_PAGE + " Ещё.", cost=0.04)),
    ]
    runner = kit.runner()
    runner.run([first])
    dump = kit.store.dump()
    runner.run([second, page(block="c")])
    charged = kit.store.charged_total()
    before = _ledger(kit, [first, second, page(block="c")]).as_document()

    kit.store.restore(dump)  # the volume is lost; the latest dump comes back
    report = kit.runner().reconcile()

    assert report.restored_rows == 2
    assert kit.store.charged_total() == charged
    assert len(kit.transport.dispatches) == 3
    assert _ledger(kit, [first, second, page(block="c")]).as_document() == before


def test_a_lost_volume_without_any_dump_is_rebuilt_from_the_file(kit: Kit) -> None:
    kit.transport.script = [Answer(openai_body(CLEAN_PAGE, cost=0.02))]
    kit.runner().run([page()])
    charged = kit.store.charged_total()

    kit.store.restore(None)
    report = kit.runner().reconcile()
    assert report.restored_rows == 1
    assert kit.store.charged_total() == charged
    assert [row.state for row in kit.store.all_calls()] == [CallState.COMPLETED]


def test_a_hand_edited_journal_line_refuses_the_start(kit: Kit) -> None:
    kit.transport.script = [Answer(openai_body(CLEAN_PAGE, cost=0.02))]
    kit.runner().run([page()])
    kit.close()
    path = kit.directory / "journal.jsonl"
    text = path.read_text(encoding="utf-8")
    assert '"charged_usd":"0.020000"' in text
    # A hand edit breaks the chain first; that is refused before any comparison.
    path.write_text(text.replace('"charged_usd":"0.020000"', '"charged_usd":"0.010000"'), encoding="utf-8")
    with pytest.raises(JournalRefused):
        kit.runner()


# --- R-79's tries and R-85's 503 ------------------------------------------------------------


def test_a_retry_safe_failure_is_tried_three_times_with_r79_delays(kit: Kit) -> None:
    kit.transport.script = [
        Fail(Failure.NOT_SENT, retry_safe=True),
        Fail(Failure.RATE_LIMITED, retry_safe=True),
        Answer(openai_body(CLEAN_PAGE)),
    ]
    kit.runner().run([page()])
    assert len(kit.transport.dispatches) == 3
    assert kit.slept == [2.0, 8.0]
    assert _ledger(kit, [page()]).repairs[0].outcome is RepairOutcome.REPAIRED


def test_retry_after_wins_over_the_delay_up_to_sixty_seconds(kit: Kit) -> None:
    kit.transport.script = [
        Fail(Failure.RATE_LIMITED, retry_safe=True, retry_after=30),
        Fail(Failure.RATE_LIMITED, retry_safe=True, retry_after=600),
        Answer(openai_body(CLEAN_PAGE)),
    ]
    kit.runner().run([page()])
    assert kit.slept == [30.0, 60.0]


def test_a_fourth_try_is_never_made(kit: Kit) -> None:
    kit.transport.script = [Fail(Failure.RATE_LIMITED, retry_safe=True)] * 3
    kit.runner().run([page()])
    assert len(kit.transport.dispatches) == 3
    assert kit.store.charged_total() == 0
    assert _ledger(kit, [page()]).repairs[0].outcome is RepairOutcome.CALL_FAILED
    # A restart does not grant a fourth.
    kit.runner().run([page()])
    assert len(kit.transport.dispatches) == 3


def test_a_503_is_outcome_unknown_at_its_bound_and_never_retried(kit: Kit) -> None:
    kit.transport.script = [Fail(Failure.OUTCOME_UNKNOWN, retry_safe=False)]
    kit.runner().run([page()])
    (row,) = kit.store.all_calls()
    assert row.state is CallState.OUTCOME_UNKNOWN
    assert row.settlement.charged_usd == BOUND
    assert len(kit.transport.dispatches) == 1
    kit.runner().run([page()])
    assert len(kit.transport.dispatches) == 1, "an outcome_unknown call was re-paid"
    assert _ledger(kit, [page()]).repairs[0].outcome is RepairOutcome.CALL_FAILED


@pytest.mark.parametrize("failure", [Failure.REQUEST_REFUSED, Failure.CREDENTIAL_REFUSED])
def test_a_definite_refusal_ends_the_call_unpaid_and_stops_the_run(kit: Kit, failure: str) -> None:
    kit.transport.script = [Fail(failure)]
    with pytest.raises(RunStopped) as stopped:
        kit.runner().run([page(block="a"), page(block="b")])
    assert stopped.value.reason == failure
    assert len(kit.transport.dispatches) == 1
    assert kit.store.charged_total() == 0
    assert _states(kit) == ["not_processed"]


def test_three_unknown_outcomes_in_a_row_stop_the_run(kit: Kit) -> None:
    kit.transport.script = [Fail(Failure.OUTCOME_UNKNOWN)] * 3
    pages = [page(block=b) for b in "abcd"]
    with pytest.raises(RunStopped) as stopped:
        kit.runner().run(pages)
    assert stopped.value.reason == StopReason.PROXY_UNAVAILABLE
    assert len(kit.transport.dispatches) == 3


# --- price and model ------------------------------------------------------------------------


def test_an_answer_from_another_model_is_charged_refused_and_stops_the_run(kit: Kit) -> None:
    kit.transport.script = [Answer(openai_body(CLEAN_PAGE, model="claude-sonnet-5", cost=0.01))]
    with pytest.raises(RunStopped) as stopped:
        kit.runner().run([page(block="a"), page(block="b")])
    assert stopped.value.reason == Failure.MODEL_MISMATCH
    (row,) = kit.store.all_calls()
    assert row.settlement.failure == Failure.MODEL_MISMATCH
    assert row.settlement.response_model == "claude-sonnet-5"
    assert kit.store.charged_total() == Decimal("0.01")
    ledger = _ledger(kit, [page(block="a"), page(block="b")])
    assert [r.outcome for r in ledger.repairs] == [RepairOutcome.UNUSABLE, RepairOutcome.NOT_ATTEMPTED]
    assert ledger.repairs[0].replacement is None


def test_an_unpriced_answer_is_charged_at_its_bound_and_stops_the_run(kit: Kit) -> None:
    kit.transport.script = [Answer(openai_body(CLEAN_PAGE, cost=None))]
    with pytest.raises(RunStopped) as stopped:
        kit.runner().run([page()])
    assert stopped.value.reason == Failure.UNPRICED
    assert kit.store.charged_total() == BOUND
    assert _ledger(kit, [page()]).repairs[0].outcome is RepairOutcome.UNUSABLE


def test_a_body_the_adapter_could_not_parse_is_still_checkpointed_and_charged(kit: Kit) -> None:
    raw = b'{"model": "claude-opus-5", "choices": "not a list", "usage": {"cost": 0.05}}'
    kit.transport.script = [AnswerThenFail(raw)]
    kit.runner().run([page()])
    (row,) = kit.store.all_calls()
    assert row.state is CallState.COMPLETED
    assert row.settlement.failure == Failure.UNREADABLE
    assert row.settlement.charged_usd == Decimal("0.05")
    assert (kit.directory / "responses" / f"{row.call_id}.body").read_bytes() == raw


# --- the cumulative ceiling and the sample stop ------------------------------------------------


def test_the_ceiling_is_cumulative_across_restarts(kit: Kit) -> None:
    kit.ceiling = Decimal("0.50")
    kit.transport.script = [Answer(openai_body(CLEAN_PAGE, cost=0.25))]
    kit.runner().run([page(block="a")])

    # A new process: 0.25 spent + this call's bound (~0.21) is under 0.50; the next is not.
    kit.transport.script = [Answer(openai_body(CLEAN_PAGE, cost=0.06))]
    pages = [page(block=b) for b in "abc"]
    with pytest.raises(RunStopped) as stopped:
        kit.runner().run(pages)
    assert stopped.value.reason == StopReason.CEILING
    assert len(kit.transport.dispatches) == 2
    ledger = _ledger(kit, pages)
    assert [r.outcome for r in ledger.repairs] == [
        RepairOutcome.REPAIRED, RepairOutcome.REPAIRED, RepairOutcome.NOT_ATTEMPTED,
    ]
    assert ledger.unreliable_count == 1


def test_the_pre_check_counts_the_bound_so_an_unknown_cannot_cross_the_ceiling(kit: Kit) -> None:
    kit.ceiling = BOUND - Decimal("0.000001")
    kit.transport.script = [Answer(openai_body(CLEAN_PAGE))]
    with pytest.raises(RunStopped) as stopped:
        kit.runner().run([page()])
    assert stopped.value.reason == StopReason.CEILING
    assert kit.transport.dispatches == []
    assert kit.store.all_calls() == []


def _areas(pages):
    order = {p.block_id: index for index, p in enumerate(pages)}
    return lambda p: float(10 + order[p.block_id])  # the later the page, the larger its crop


def test_a_sample_under_the_ceiling_proceeds_and_is_not_paid_again(kit: Kit) -> None:
    pages = [page(block=b) for b in "abcdef"]
    kit.transport.script = [Answer(openai_body(CLEAN_PAGE, cost=0.02))] * 6
    runner = kit.runner()
    verdict = runner.sample(pages, _areas(pages))
    assert verdict["decision"] == "proceed"
    assert verdict["sample_blocks"] == [pages[5].block_id, pages[4].block_id, pages[3].block_id]
    assert Decimal(verdict["projected_usd"]) == Decimal("0.02") * 6 * Decimal("1.25")
    assert len(kit.transport.dispatches) == 3

    kit.runner().full(pages)
    assert len(kit.transport.dispatches) == 6  # three new pages, the sample replayed
    assert _ledger(kit, pages).unreliable_count == 0


def test_a_sample_above_the_ceiling_stops_for_the_owner(kit: Kit) -> None:
    """`R-95` (K-8): mean x pages x 1.25 above $10 stops; the verdict is kept in the journal."""
    pages = [page(block=b) for b in "abcdefghijklmnopqrst"]  # 20 pages
    kit.transport.script = [Answer(openai_body(CLEAN_PAGE, cost=0.45))] * 3
    runner = kit.runner()
    with pytest.raises(RunStopped) as stopped:
        runner.sample(pages, _areas(pages))
    assert stopped.value.reason == StopReason.SAMPLE_ABOVE_CEILING
    verdict = kit.journal.sample_verdict
    assert verdict["decision"] == "stop_for_owner"
    assert Decimal(verdict["projected_usd"]) == Decimal("0.45") * 20 * Decimal("1.25")

    with pytest.raises(RunStopped) as refused:
        kit.runner().full(pages)
    assert refused.value.reason == StopReason.SAMPLE_ABOVE_CEILING
    assert len(kit.transport.dispatches) == 3


def test_an_owner_decision_lets_a_stopped_sample_proceed_under_the_hard_ceiling(kit: Kit) -> None:
    pages = [page(block=b) for b in "abcdefghijklmnopqrst"]  # 20 pages
    kit.transport.script = [Answer(openai_body(CLEAN_PAGE, cost=0.55))] * 3
    with pytest.raises(RunStopped):
        kit.runner().sample(pages, _areas(pages))  # 0.55 x 20 x 1.25 = 13.75 > 10
    runner = kit.runner()
    runner.journal.append_owner_decision({"ruling": "R-999", "projected_usd": "13.75"}, kit.clock())
    kit.transport.script = [Answer(openai_body(CLEAN_PAGE, cost=0.55))] * 17
    with pytest.raises(RunStopped) as stopped:
        runner.full(pages)
    # The $10 ceiling still holds: after 18 pages 9.90 is charged, and 9.90 + a bound > 10.
    assert stopped.value.reason == StopReason.CEILING
    assert len(kit.transport.dispatches) == 18
    assert kit.store.charged_total() == Decimal("9.90")
    assert _ledger(kit, pages).unreliable_count == 2


def test_the_full_run_needs_a_sample_verdict(kit: Kit) -> None:
    with pytest.raises(RunStopped) as stopped:
        kit.runner().full([page()])
    assert stopped.value.reason == StopReason.NO_SAMPLE_VERDICT
    assert kit.transport.dispatches == []


def test_the_full_run_refuses_a_page_set_other_than_the_sampled_one(kit: Kit) -> None:
    pages = [page(block=b) for b in "abc"]
    kit.transport.script = [Answer(openai_body(CLEAN_PAGE, cost=0.02))] * 3
    kit.runner().sample(pages, _areas(pages))
    with pytest.raises(JournalRefused, match="not the one sampled"):
        kit.runner().full(pages + [page(block="d")])


def test_a_journal_is_bound_to_its_model(kit: Kit) -> None:
    kit.runner()
    kit.close()
    with pytest.raises(JournalRefused, match="model"):
        LocalJournal(kit.directory).open(
            base_snapshot=BASE, model="claude-sonnet-5", ceiling_usd=kit.ceiling,
            drop_sums_sha256=SUMS, now="t",
        )
