"""``OD-10`` reconciliation, and the proof that the executor does not choose terminals.

``test_terminal_selection_is_delegated`` is named by ``P2-RUN-01``'s required-tests
section and is asserted two ways, because either alone would be weak:

* **behaviourally** — the gate is replaced with one that returns a different terminal,
  and the run ends in *that* terminal. An executor that decided for itself would ignore
  the substitution;
* **structurally** — the executor's source is parsed and every non-docstring string
  constant is inspected. The literal ``"published"`` appears nowhere in its code, so
  there is no branch that could select the success terminal even by accident.

The structural half matters because the behavioural half only proves the *happy* path
delegates. A stray ``if everything_looks_fine: state = "published"`` somewhere else would
survive it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.findings import TerminalSelection
from auditmanager.runs import (
    INTERRUPTED_REASON,
    RunRepository,
    execute_run,
    reconcile,
    reconcile_interrupted_runs,
    start_audit_run,
)

EXECUTOR_SOURCE = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "auditmanager"
    / "runs"
    / "executor.py"
)


def _start(session: Session, seeded, key):
    return start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=key,
    )


def _age_run(session: Session, run_id: str, interval: str = "2 hours") -> None:
    """Make a run look as old as one whose executor died. Touches no state column."""
    session.execute(
        text(
            f"UPDATE audit_run SET updated_at = now() - interval '{interval}' "
            "WHERE run_id = :run_id"
        ),
        {"run_id": run_id},
    )


# --- terminal selection is the gate's, never the executor's ------------------


def test_terminal_selection_is_delegated(
    session: Session,
    seeded,
    blob_store,
    recorded_adapter,
    provider_config,
    new_key,
    monkeypatch,
    helpers,
):
    """The executor records what the gate returns, and has no path that picks one."""
    # -- behavioural: substitute the gate, and the run follows it.
    calls: list[dict] = []

    def fake_select_terminal(
        stage_statuses,
        *,
        required_stages,
        gate_ran=True,
        stage_errors=None,
        # `D-46`. The fourth argument arrived with `terminal_detail`, and this substitute
        # is recorded here rather than given a `**kwargs` catch-all deliberately: the point
        # of this test is that the executor *delegates*, so what it passes is part of the
        # claim. A signature that swallowed a new argument would go on passing while the
        # executor started deciding something on its own.
        stage_details=None,
    ):
        calls.append(
            {
                "stage_statuses": dict(stage_statuses),
                "required_stages": tuple(required_stages),
                "gate_ran": gate_ran,
                "stage_errors": dict(stage_errors or {}),
                "stage_details": dict(stage_details or {}),
            }
        )
        # A terminal the run would never have reached on its own: every stage succeeded.
        return TerminalSelection(
            state="partial", degradation_set=("document_context_build",)
        )

    monkeypatch.setattr(
        "auditmanager.runs.executor.select_terminal", fake_select_terminal
    )

    started = _start(session, seeded, new_key("delegated"))
    result = execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )

    assert calls, "the executor reached a terminal without consulting the gate"
    assert set(calls[0]["stage_statuses"].values()) == {"succeeded"}, (
        "the substituted gate was handed a run whose stages all succeeded, so a "
        "self-deciding executor would have written `published`"
    )
    assert result.terminal_state == "partial"
    assert helpers.run_state_of(session, started.run_id) == "partial"
    assert result.degradation_set == ("document_context_build",)
    # The reason is the gate's business too: the executor hands over each stage's error
    # code and writes back whatever reason comes out, rather than naming a cause itself.
    assert set(calls[0]["stage_errors"]) == set(calls[0]["stage_statuses"]), (
        "the gate was handed statuses for stages whose error codes it never saw, so it "
        "could not name a cause even when one exists"
    )

    # -- structural: the literal never appears in the executor's code.
    tree = ast.parse(EXECUTOR_SOURCE.read_text(encoding="utf-8"))
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        )
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    }
    # Exact equality, not a substring: a state is written as the whole literal, so
    # `"published"` is a state and "...no artifact was published" is prose. Matching on
    # substrings would force the module's English to be contorted to satisfy a test.
    offenders = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
        and node.value == "published"
    ]
    assert offenders == [], (
        "the executor's code contains the state literal 'published' outside a "
        "docstring, so it has a path that could select the success terminal itself"
    )


def test_a_partial_stage_yields_a_partial_run_with_a_non_empty_degradation_set(
    session: Session, seeded, blob_store, variant_adapter, provider_config, new_key, helpers
):
    """A reply cut short at the output ceiling degrades the run, visibly.

    The database refuses ``partial`` with an empty degradation set and ``published``
    with a non-empty one, so a silent degradation cannot reach the success terminal even
    if selection were wrong. This asserts the pair actually written.
    """
    started = _start(session, seeded, new_key("truncated-variant"))
    result = execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=variant_adapter("truncated"),
        provider_config=provider_config,
    )

    assert result.terminal_state == "partial"
    assert helpers.run_state_of(session, started.run_id) == "partial"
    assert result.degradation_set == ("text_analysis",)
    assert result.stage_statuses["text_analysis"] == "partial"

    row = helpers.audit_run_row(session, started.run_id)
    assert row["degradation_set"] == ["text_analysis"]
    assert row["terminal_at"] is not None


def test_an_unresolvable_quotation_never_becomes_a_finding(
    session: Session, seeded, blob_store, variant_adapter, provider_config, new_key
):
    """The safety property: an invented quotation reaches no finding and no CSV row.

    This test also records a **composition finding**, which is why it asserts the
    diagnostic count is zero rather than positive.

    The ``ungrounded_quotation`` variant proposes two observations: one wholly invented,
    and one pairing a real quotation with an invented one. ``B3``'s ``_ground`` resolves
    every proposed anchor and emits only what resolved, dropping an observation left
    with no evidence — so ``analysis.text_observations`` never contains an unresolvable
    anchor. ``B4``'s gate therefore never sees one, and the ``grounded = false`` row
    that P02 §5.1 describes is **unreachable through the composed PC-01 chain**.

    Safety is intact: nothing ungrounded is published, which is the property that
    matters. What is lost is observability — the five-value ``ungrounded_reason``
    vocabulary records nothing, and *which* quotation the model invented survives only
    as a count in the stage metrics, asserted below. Reported, not repaired: ``B3``'s
    filtering and ``B4``'s diagnostic path are each correct alone, and reconciling them
    is a seam decision rather than this session's to make.
    """
    started = _start(session, seeded, new_key("ungrounded-variant"))
    result = execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=variant_adapter("ungrounded_quotation"),
        provider_config=provider_config,
    )

    # One observation survives: the one whose real quotation resolved.
    assert result.published_finding_count == 1
    assert result.diagnostic_count == 0, (
        "B3 filters unresolvable anchors upstream, so B4's diagnostic path records "
        "nothing; if this ever becomes positive the two modules have been reconciled "
        "and this test's premise needs revisiting"
    )
    assert (
        session.execute(
            text(
                "SELECT count(*) FROM finding_observation "
                "WHERE run_id = :run_id AND finding_uid IS NULL"
            ),
            {"run_id": started.run_id},
        ).scalar_one()
        == 0
    )

    # The invented quotation is in no evidence row at all.
    quotes = {
        row[0]
        for row in session.execute(
            text(
                "SELECT e.quote FROM finding_evidence e "
                "JOIN finding_observation o "
                "  ON o.finding_observation_id = e.finding_observation_id "
                "WHERE o.run_id = :run_id"
            ),
            {"run_id": started.run_id},
        )
    }
    assert "Класс энергетической эффективности здания — A++." not in quotes
    assert "Степень огнестойкости здания — IV." not in quotes

    # What was dropped survives only here, as a count in the persisted stage metrics.
    metrics = (
        session.execute(
            text(
                "SELECT metrics FROM stage_result "
                "WHERE run_id = :run_id AND stage_id = 'text_analysis'"
            ),
            {"run_id": started.run_id},
        )
        .mappings()
        .one()["metrics"]
    )
    assert metrics["observations_proposed"] == 2
    assert metrics["observations_emitted"] == 1
    assert metrics["observations_dropped_unresolved"] == 1
    assert metrics["evidence_unresolved"] >= 1


# --- OD-10 -------------------------------------------------------------------


def test_an_interrupted_running_run_reconciles_to_failed_with_a_reason(
    session: Session, seeded, new_key, helpers
):
    """A killed executor leaves a ``running`` row; reconciliation makes it explicit.

    The run is advanced to ``running`` and then abandoned — which is exactly the state a
    process that died mid-execution leaves behind — and aged so reconciliation regards
    it as stale. There is no lease and no heartbeat to consult; age is the only evidence
    PC-01 has.
    """
    started = _start(session, seeded, new_key("interrupted"))
    runs = RunRepository()
    runs.advance(session, run_id=started.run_id, from_state="created", to_state="queued")
    runs.advance(session, run_id=started.run_id, from_state="queued", to_state="running")
    assert helpers.run_state_of(session, started.run_id) == "running"
    _age_run(session, started.run_id)

    reconciled = reconcile_interrupted_runs(session, older_than="1 hour")

    assert [entry.run_id for entry in reconciled] == [started.run_id]
    assert helpers.run_state_of(session, started.run_id) == "failed"
    assert helpers.run_state_of(session, started.run_id) != "running"

    row = helpers.audit_run_row(session, started.run_id)
    assert row["interrupted_reason"] == INTERRUPTED_REASON
    assert row["terminal_reason"] is not None, "a failed run must record a terminal reason"
    assert row["terminal_at"] is not None, "a terminal state requires terminal_at"


def test_reconciliation_invents_no_interrupted_state(session: Session, seeded, new_key, helpers):
    """The reconciled run lands on a terminal the contract declares.

    ``interrupted`` is not one of the four ``audit_run`` terminals, so recording the
    interruption as a *state* would put the application and the ``AM001`` trigger into
    disagreement about what states exist. It is recorded as a reason instead.
    """
    started = _start(session, seeded, new_key("no-interrupted-state"))
    runs = RunRepository()
    runs.advance(session, run_id=started.run_id, from_state="created", to_state="queued")
    runs.advance(session, run_id=started.run_id, from_state="queued", to_state="running")
    _age_run(session, started.run_id)

    reconcile_interrupted_runs(session, older_than="1 hour")

    state = helpers.run_state_of(session, started.run_id)
    assert state in {"published", "partial", "failed", "cancelled"}
    assert state == "failed"

    declared = {
        row[0]
        for row in session.execute(
            text(
                "SELECT DISTINCT to_state FROM contract_state_transition "
                "WHERE machine = 'audit_run'"
            )
        )
    }
    assert "interrupted" not in declared


def test_a_fresh_running_run_is_left_alone(session: Session, seeded, new_key, helpers):
    """Reconciliation must not terminate a run that is legitimately in flight.

    Without this, the guard would 'pass' by terminating everything it saw, which is the
    failure mode that turns a reconciler into a saboteur.
    """
    started = _start(session, seeded, new_key("fresh-running"))
    runs = RunRepository()
    runs.advance(session, run_id=started.run_id, from_state="created", to_state="queued")
    runs.advance(session, run_id=started.run_id, from_state="queued", to_state="running")
    # Deliberately not aged.

    reconciled = reconcile_interrupted_runs(session, older_than="1 hour")

    assert reconciled == ()
    assert helpers.run_state_of(session, started.run_id) == "running"


def test_reconcile_handles_both_clauses(session: Session, seeded, new_key, helpers):
    """The startup entry point reconciles runs and command records together."""
    started = _start(session, seeded, new_key("both-clauses"))
    runs = RunRepository()
    runs.advance(session, run_id=started.run_id, from_state="created", to_state="queued")
    runs.advance(session, run_id=started.run_id, from_state="queued", to_state="running")
    _age_run(session, started.run_id)

    report = reconcile(session, older_than="1 hour")

    assert report.run_count == 1
    assert helpers.run_state_of(session, started.run_id) == "failed"
