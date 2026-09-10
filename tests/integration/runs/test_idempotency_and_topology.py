"""Idempotency through the command record, and the declared ``audit_run`` topology.

Two things are proved here that a unit test could not.

**The refusals come from the database, not only from the guard.** Each terminal-reopening
case is asserted twice: once through :func:`assert_transition`, which refuses early with
the typed catalog code, and once through a raw ``UPDATE`` that bypasses the guard
entirely and must still be refused by the ``AM001`` trigger. A guard nobody has watched
the database back up is a guard that might be the only thing standing there.

**A refusal is read on SQLSTATE, never on message text.** P02 §3.2: the message is a
diagnostic string a server upgrade or a locale may reword; the SQLSTATE is the contract.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.ingest import CommandRepository
from auditmanager.runs import (
    COMMAND_TYPE_START_RUN,
    RunRepository,
    abandon_stale_commands,
    execute_run,
    frozen_input_digest,
    start_audit_run,
    start_run_fingerprint,
)
from auditmanager.shared.db import SQLSTATE_UNDECLARED_TRANSITION
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey

NON_INITIAL_STATES = ("queued", "running", "validating")


def _sqlstate_of(exc: DBAPIError) -> str | None:
    orig = getattr(exc, "orig", None)
    return getattr(orig, "sqlstate", None) or getattr(exc, "code", None)


def _start(session: Session, seeded, key, **overrides):
    payload = {
        "version_uid": seeded.version_uid,
        "analysis_profile_id": seeded.analysis_profile_id,
        "prompt_bundle_id": seeded.prompt_bundle_id,
        "provider_mode": "recorded",
    }
    payload.update(overrides)
    return start_audit_run(session, idempotency_key=key, **payload)


# --- idempotency -------------------------------------------------------------


def test_the_same_key_and_payload_returns_the_identical_run_and_inserts_no_row(
    session: Session, seeded, new_key, helpers
):
    key = new_key("repeat-same-payload")
    first = _start(session, seeded, key)
    before = helpers.count_runs(session)

    second = _start(session, seeded, key)

    assert second.run_id == first.run_id
    assert second.command_id == first.command_id
    assert second.replayed is True
    assert helpers.count_runs(session) == before, "a repeat inserted a second run row"


def test_a_repeat_returns_the_existing_run_even_after_it_reached_a_terminal(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key, helpers
):
    """"Including for a terminal run" is the clause this covers.

    A repeat is answered from the command record, so the run's own state is irrelevant
    to whether the key still resolves — which is what makes the answer uniform.
    """
    key = new_key("repeat-after-terminal")
    first = _start(session, seeded, key)
    execute_run(
        session,
        first.run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )
    assert helpers.run_state_of(session, first.run_id) == "published"
    before = helpers.count_runs(session)

    second = _start(session, seeded, key)

    assert second.run_id == first.run_id
    assert second.replayed is True
    assert helpers.count_runs(session) == before


def test_the_same_key_with_a_different_payload_is_idempotency_key_reuse(
    session: Session, seeded, new_key, helpers
):
    key = new_key("repeat-changed-payload")
    _start(session, seeded, key)
    before = helpers.count_runs(session)

    with pytest.raises(DomainError) as raised:
        # A different analysis profile is a different question about the same document.
        _start(
            session,
            seeded,
            key,
            analysis_profile_id="ap_01M2545JSD15ETSNNV904X991J",
        )

    assert raised.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
    assert helpers.count_runs(session) == before
    # The key itself is a forbidden envelope detail and must not travel in the error.
    assert str(key) not in str(raised.value)


def test_a_new_key_over_a_terminal_run_creates_a_new_run_and_leaves_the_old_row_intact(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key, helpers
):
    first = _start(session, seeded, new_key("rerun-first"))
    execute_run(
        session,
        first.run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )
    original = helpers.audit_run_row(session, first.run_id)

    second = _start(session, seeded, new_key("rerun-second"))

    assert second.run_id != first.run_id
    assert second.replayed is False
    assert helpers.audit_run_row(session, first.run_id) == original, (
        "creating a new run mutated the earlier run's row"
    )


def test_a_repeat_under_an_abandoned_key_is_idempotency_key_stale(
    session: Session, seeded, new_key
):
    """A command nobody can resolve must never be replayed as if it had succeeded.

    The record is claimed and deliberately never completed, which is what a process
    dying between claiming the key and inserting the run looks like. Reconciliation
    abandons it — a terminal state — so the key is permanently spent.
    """
    key = new_key("abandoned-key")
    digest = frozen_input_digest(
        version_uid=seeded.version_uid,
        blob_ids={"source.document": seeded.source_blob_id},
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
    )
    fingerprint = start_run_fingerprint(
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        frozen_input_digest_value=digest,
    )
    commands = CommandRepository()
    claimed = commands.begin(
        session,
        command_type=COMMAND_TYPE_START_RUN,
        idempotency_key=key,
        fingerprint=fingerprint,
    )
    # Age the claim so reconciliation regards it as unresolvable.
    session.execute(
        text(
            "UPDATE command_record SET updated_at = now() - interval '2 hours' "
            "WHERE command_id = :command_id"
        ),
        {"command_id": str(claimed.command_id)},
    )

    abandoned = abandon_stale_commands(session, older_than="1 hour")
    assert str(claimed.command_id) in abandoned

    with pytest.raises(DomainError) as raised:
        _start(session, seeded, key)
    assert raised.value.code is ErrorCode.IDEMPOTENCY_KEY_STALE


# --- the declared topology ---------------------------------------------------


@pytest.mark.parametrize("target", NON_INITIAL_STATES)
def test_a_terminal_run_cannot_be_moved_back_by_the_guard(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key, target
):
    """The application guard refuses reopening a terminal, with the typed code."""
    started = _start(session, seeded, new_key(f"reopen-guard-{target}"))
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )

    with pytest.raises(DomainError) as raised:
        RunRepository().advance(
            session, run_id=started.run_id, from_state="published", to_state=target
        )
    assert raised.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED


@pytest.mark.parametrize("target", NON_INITIAL_STATES)
def test_a_terminal_run_cannot_be_moved_back_by_the_database_either(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key, target
):
    """The same refusal from the trigger, with the guard bypassed entirely.

    The ``UPDATE`` is issued directly, so nothing in Python has a chance to refuse it
    first. The row is confirmed to exist and to be terminal before the attempt, so a
    zero-row update cannot masquerade as a refusal — that is exactly the vacuous test
    ``B4`` caught in the previous wave.
    """
    started = _start(session, seeded, new_key(f"reopen-db-{target}"))
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )
    assert (
        session.execute(
            text("SELECT count(*) FROM audit_run WHERE run_id = :r AND state = 'published'"),
            {"r": started.run_id},
        ).scalar_one()
        == 1
    ), "the row this test is about is not there to be refused"

    savepoint = session.begin_nested()
    try:
        with pytest.raises(DBAPIError) as raised:
            session.execute(
                text("UPDATE audit_run SET state = :s WHERE run_id = :r"),
                {"s": target, "r": started.run_id},
            )
        assert _sqlstate_of(raised.value) == SQLSTATE_UNDECLARED_TRANSITION
    finally:
        savepoint.rollback()


def test_an_audit_run_may_not_be_inserted_in_a_non_initial_state(
    session: Session, seeded
):
    """``AM001`` also fires on an INSERT that skips the declared initial state."""
    savepoint = session.begin_nested()
    try:
        with pytest.raises(DBAPIError) as raised:
            session.execute(
                text(
                    "INSERT INTO audit_run (run_id, project_uid, version_uid, state, "
                    "analysis_profile_id, prompt_bundle_id, provider_mode, "
                    "frozen_input_digest) VALUES "
                    "('run_01M2545JSD15ETSNNV904X991J', :prj, :ver, 'running', :ap, :pb, "
                    "'recorded', :digest)"
                ),
                {
                    "prj": seeded.project_uid,
                    "ver": seeded.version_uid,
                    "ap": seeded.analysis_profile_id,
                    "pb": seeded.prompt_bundle_id,
                    "digest": "0" * 64,
                },
            )
        assert _sqlstate_of(raised.value) == SQLSTATE_UNDECLARED_TRANSITION
    finally:
        savepoint.rollback()


def test_pc01_instantiates_none_of_the_durable_execution_aggregates(session: Session):
    """No ``job``, ``attempt``, ``lease``, ``worker`` or ``outbox`` table exists.

    Adding one would be a visible scope change rather than a quiet convenience, which
    is precisely why the absence is asserted rather than assumed.
    """
    from auditmanager.runs import AGGREGATES_NOT_INSTANTIATED

    present = [
        name
        for name in AGGREGATES_NOT_INSTANTIATED
        if session.execute(
            text("SELECT to_regclass(:qualified)"), {"qualified": f"public.{name}"}
        ).scalar_one_or_none()
        is not None
    ]
    assert present == [], f"PC-01 declares no such aggregate, but these tables exist: {present}"


# --- isolating the two guards the database would otherwise mask ---------------


def test_the_application_guard_refuses_before_any_sql_is_issued(session: Session, seeded):
    """``assert_transition`` must refuse an undeclared edge *without* asking the database.

    The trigger would refuse it too, and ``translate_refusal`` maps that back to the same
    typed code — which is why the terminal-reopening tests above pass whether or not the
    application guard is there at all. Mutation M11 removed the guard and those tests
    stayed green, so this exists to isolate it: the session is replaced with one that
    fails loudly if ``execute`` is reached, making "refused early" the only way to pass.
    """

    class RefusingSession:
        def execute(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError(
                "the guard issued SQL instead of refusing an undeclared edge itself"
            )

    runs = RunRepository()
    # Prime the cached topology from the real session, so the refusal below cannot be a
    # side effect of the topology being unavailable.
    runs.topology(session)

    with pytest.raises(DomainError) as raised:
        runs.advance(
            RefusingSession(),  # type: ignore[arg-type]
            run_id="run_01M2545JSD15ETSNNV904X991J",
            from_state="created",
            to_state="validating",  # created -> validating is not a declared edge
        )
    assert raised.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED


def test_a_compare_and_set_that_moved_no_row_is_a_refusal(
    session: Session, seeded, new_key, helpers
):
    """A zero-row UPDATE moved nothing, and reporting it as success is a lost update.

    The edge requested here *is* declared, so the application guard permits it; what
    fails is the ``WHERE state = :from_state`` predicate, because the run is still
    ``created``. Only the rowcount assertion stands between that and a silent no-op.
    """
    started = _start(session, seeded, new_key("compare-and-set"))
    assert helpers.run_state_of(session, started.run_id) == "created"

    with pytest.raises(DomainError) as raised:
        # queued -> running is declared, but this run is not in `queued`.
        RunRepository().advance(
            session, run_id=started.run_id, from_state="queued", to_state="running"
        )
    assert raised.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    assert helpers.run_state_of(session, started.run_id) == "created", (
        "the run moved despite the refusal"
    )
