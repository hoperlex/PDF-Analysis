"""``OD-10``'s two words, pinned as literals rather than compared to themselves.

``test_reconciliation_and_terminals.py`` proves the *shape* of reconciliation: a stale
``running`` run reaches a declared terminal, no ``interrupted`` state is invented, and both
clauses run independently. It does not pin the two values that reconciliation writes, and
each is unpinned in its own way — which are the two failure modes this programme has now
found twice each.

**The reason is compared to itself.** Line 297 of that file reads::

    assert row["interrupted_reason"] == INTERRUPTED_REASON

with ``INTERRUPTED_REASON`` imported from the module under test at the top of the file.
Both sides move together: ``W10-RUN`` changed the constant to ``"something_went_wrong"``
on a copy of ``src/`` and all 154 tests in ``tests/integration/runs`` and
``tests/integration/ingest`` passed. This is wave 9's mistake, still in the tree.

**The terminal reason is asserted as a field, not as a reason.** The next line reads
``assert row["terminal_reason"] is not None``. ``INTERRUPTED_TERMINAL_REASON`` was changed
from ``analysis_failed`` to ``internal_error`` and the same 154 tests passed. That is the
"field is not reason" shape: any of the frozen catalog's twenty codes would satisfy it,
including ones that would tell an operator something untrue.

What is pinned here, and against what
-------------------------------------
* ``executor_process_ended_before_terminal``, written out. The authority is ``OD-10``'s own
  requirement that the interruption be recorded as a *reason* and the module's statement
  that the reason "names what actually happened — the executing process ended without
  reaching a terminal — and is deliberately not a state name". Both halves of that are
  asserted: the exact string, and that the string is not a declared state.
* ``analysis_failed``, written out, and cross-checked against the **schema's own**
  authority rather than against the module: the value must be one the migration's
  ``ck_audit_run_terminal_reason`` CHECK admits, which is read out of
  ``contract_state_transition``-era reference data via the frozen error catalog. The test
  reads the catalog through ``ErrorCode`` membership, which is generated from
  ``contracts/domain/v1/error-codes.json`` and is not this module's to change.
* ``failed``, written out, as the terminal ``RECONCILIATION_TERMINAL`` names. That one
  *is* already guarded — changing it to ``cancelled`` reddens three tests in the file
  beside this — and is re-pinned here so all three of ``OD-10``'s values sit together.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.runs import RunRepository, reconcile_interrupted_runs, start_audit_run
from auditmanager.shared.errors import ErrorCode

#: The three ``OD-10`` values, written out. Nothing below imports them from the module.
PINNED_INTERRUPTED_REASON = "executor_process_ended_before_terminal"
PINNED_TERMINAL_REASON = "analysis_failed"
PINNED_TERMINAL_STATE = "failed"


def _start(session: Session, seeded, key):
    return start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=key,
    )


def _abandon_a_running_run(session: Session, seeded, key) -> str:
    """Leave a ``running`` run with nobody to finish it, aged past any threshold.

    Exactly what ``test_reconciliation_and_terminals.py`` does: advance through the
    declared edges and move the clock, touching no state column by hand.
    """
    started = _start(session, seeded, key)
    runs = RunRepository()
    runs.advance(session, run_id=started.run_id, from_state="created", to_state="queued")
    runs.advance(session, run_id=started.run_id, from_state="queued", to_state="running")
    session.execute(
        text(
            "UPDATE audit_run SET updated_at = now() - interval '2 hours' "
            "WHERE run_id = :run_id"
        ),
        {"run_id": started.run_id},
    )
    return started.run_id


def test_a_reconciled_run_carries_the_pinned_reason_spelled_out(
    session: Session, seeded, new_key
) -> None:
    """The reason is this exact string, and it is not a state name.

    An operator, a query and an export all read this column, and "some non-empty value was
    written" is not a thing any of them can act on. Writing the string out is what makes
    changing it a decision that has to edit a test stating the old one.
    """
    run_id = _abandon_a_running_run(session, seeded, new_key("pinned-reason"))

    reconciled = reconcile_interrupted_runs(session, older_than="1 hour")

    assert [entry.run_id for entry in reconciled] == [run_id]
    assert [entry.interrupted_reason for entry in reconciled] == [
        "executor_process_ended_before_terminal"
    ]
    assert [entry.to_state for entry in reconciled] == ["failed"]
    assert [entry.from_state for entry in reconciled] == ["running"]

    row = (
        session.execute(
            text(
                "SELECT state, interrupted_reason, terminal_reason, terminal_at "
                "FROM audit_run WHERE run_id = :run_id"
            ),
            {"run_id": run_id},
        )
        .mappings()
        .one()
    )

    assert row["state"] == "failed"
    assert row["interrupted_reason"] == "executor_process_ended_before_terminal", (
        "the reason is compared to a literal, not to the constant it came from; the "
        "assertion in test_reconciliation_and_terminals.py imports INTERRUPTED_REASON "
        "and so agrees with the module under every value"
    )
    assert row["terminal_at"] is not None

    # And it is a *reason*, not a state: no aggregate may be in a state by this name.
    declared_states = {
        value
        for row_ in session.execute(
            text(
                "SELECT DISTINCT to_state FROM contract_state_transition "
                "WHERE machine = 'audit_run'"
            )
        )
        for value in row_
    }
    assert "executor_process_ended_before_terminal" not in declared_states
    assert declared_states == {
        "created",
        "queued",
        "running",
        "validating",
        "published",
        "partial",
        "failed",
        "cancelled",
    }, "the declared audit_run vocabulary, written out; 'interrupted' is not in it"


def test_the_terminal_reason_is_analysis_failed_and_not_merely_present(
    session: Session, seeded, new_key
) -> None:
    """*Which* reason, not *that* there is one.

    ``terminal_reason is not None`` is satisfied by any of the catalog's codes.
    ``internal_error`` would satisfy it and would be a lie: an interrupted run did not
    fail internally, it produced no acceptable result, and an operator reading
    ``internal_error`` would go looking for a crash that never happened.

    The literal is cross-checked against the frozen error catalog rather than against the
    module that writes it, so a code that drifted out of the catalog fails here.
    """
    run_id = _abandon_a_running_run(session, seeded, new_key("pinned-terminal-reason"))

    reconcile_interrupted_runs(session, older_than="1 hour")

    terminal_reason = session.execute(
        text("SELECT terminal_reason FROM audit_run WHERE run_id = :run_id"),
        {"run_id": run_id},
    ).scalar_one()

    assert terminal_reason == "analysis_failed"
    # The independent authority: the string is a member of the frozen catalog, and the
    # one this module's docstring argues for — "an interrupted run produced no acceptable
    # result, which is what this code means".
    assert ErrorCode("analysis_failed") is ErrorCode.ANALYSIS_FAILED
    assert terminal_reason != ErrorCode.INTERNAL_ERROR.value
    assert terminal_reason != ErrorCode.DEPENDENCY_UNAVAILABLE.value


def test_the_three_pinned_values_are_the_ones_this_file_states(
    session: Session, seeded, new_key
) -> None:
    """One row, all three values at once, against the module-level literals.

    Kept separate from the two above so that a change to any one of them fails with the
    whole ``OD-10`` vocabulary in view rather than one field at a time.
    """
    run_id = _abandon_a_running_run(session, seeded, new_key("all-three"))

    reconcile_interrupted_runs(session, older_than="1 hour")

    state, interrupted_reason, terminal_reason = session.execute(
        text(
            "SELECT state, interrupted_reason, terminal_reason FROM audit_run "
            "WHERE run_id = :run_id"
        ),
        {"run_id": run_id},
    ).one()

    assert (state, interrupted_reason, terminal_reason) == (
        PINNED_TERMINAL_STATE,
        PINNED_INTERRUPTED_REASON,
        PINNED_TERMINAL_REASON,
    )
    assert (
        PINNED_TERMINAL_STATE,
        PINNED_INTERRUPTED_REASON,
        PINNED_TERMINAL_REASON,
    ) == ("failed", "executor_process_ended_before_terminal", "analysis_failed")


def test_a_run_that_is_not_stale_is_left_alone(
    session: Session, seeded, new_key
) -> None:
    """The mirror image: reconciliation writes these values only where it should.

    Without this, the three tests above would pass against a reconciler that stamped every
    run it could find, which would be a far worse bug than an unpinned string.
    """
    started = _start(session, seeded, new_key("still-running"))
    runs = RunRepository()
    runs.advance(session, run_id=started.run_id, from_state="created", to_state="queued")
    runs.advance(session, run_id=started.run_id, from_state="queued", to_state="running")
    # Not aged: this is a run whose executor is alive.

    assert reconcile_interrupted_runs(session, older_than="1 hour") == ()

    state, interrupted_reason = session.execute(
        text(
            "SELECT state, interrupted_reason FROM audit_run WHERE run_id = :run_id"
        ),
        {"run_id": started.run_id},
    ).one()
    assert state == "running"
    assert interrupted_reason is None
