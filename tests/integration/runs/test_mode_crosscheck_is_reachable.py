"""The executor's run/adapter mode cross-check, exercised where it can actually be reached.

`W6-CERT` named this in passing: removing the cross-check at ``runs/executor.py`` leaves the
whole criterion-4 suite green, because on the API path the refusal fires earlier — in
``bootstrap/adapters.py``, when a client asks for a mode the deployment is not configured to
provide. The twelve operations therefore cannot reach the executor's check at all, and a
guard that cannot be reached is not a guard.

It is still worth keeping, and it is reachable: ``execute_run`` is a public function, and it
is the only place that holds **both** the persisted run row and the adapter that will answer
for it. `adapters.py` compares a *request* against a *deployment*; this compares a *row*
against the *object about to write under it*. A composition that wired the wrong adapter, or
a caller reaching past the API, is refused here and nowhere else.

So these tests use the library surface rather than the twelve operations. That is not a
workaround: it is where the check lives, and pretending otherwise is what left it unguarded.

`PROTOTYPE_PROFILE.md` §8 criterion 4 requires live and recorded outcomes to be
distinguishable, and §4 forbids presenting a recorded result as a live one.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.analysis.text import ProviderMode
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.shared.identity import IdempotencyKey


class _AdapterClaiming:
    """A recorded adapter that reports whatever mode it is told to report.

    Only ``provider_mode`` matters: the executor reads it and refuses before any stage
    runs, so ``complete`` is never called on the refusing path. It raises rather than
    returning, so a test that somehow got past the refusal fails loudly instead of
    quietly producing a run.
    """

    def __init__(self, inner, mode: ProviderMode) -> None:
        self._inner = inner
        self.provider_mode = mode

    def complete(self, request):  # pragma: no cover - reached only if the guard is gone
        raise AssertionError(
            "the executor ran a stage although the adapter's mode disagreed with the run "
            "row; nothing may be written under a mode the adapter does not provide"
        )


def _start(session: Session, seeded, label: str) -> str:
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=IdempotencyKey(f"w8-mode-{label}-{uuid.uuid4()}"),
    )
    return started.run_id


def _run_state(session: Session, run_id: str) -> str:
    return session.execute(
        text("SELECT state FROM audit_run WHERE run_id = :r"), {"r": run_id}
    ).scalar_one()


def test_the_case_really_does_discriminate(
    session: Session, seeded, blob_store, recorded_adapter, provider_config
):
    """The precondition: the same call succeeds when the two modes agree.

    Without this, the refusal below could be caused by anything at all in the fixture —
    a missing recording, a bad profile — and would still look like the guard working.
    """
    agreeing = _AdapterClaiming(recorded_adapter, ProviderMode.RECORDED)
    agreeing.complete = recorded_adapter.complete  # type: ignore[method-assign]
    run_id = _start(session, seeded, "agreeing")

    result = execute_run(
        session,
        run_id,
        blob_store=blob_store,
        adapter=agreeing,
        provider_config=provider_config,
    )

    assert result.terminal_state == "published", result.terminal_state


def test_an_adapter_claiming_live_is_refused_under_a_recorded_run(
    session: Session, seeded, blob_store, recorded_adapter, provider_config
):
    """The claim. A recorded run must never be answered by something reporting `live`."""
    lying = _AdapterClaiming(recorded_adapter, ProviderMode.LIVE)
    run_id = _start(session, seeded, "claims-live")

    with pytest.raises(DomainError) as raised:
        execute_run(
            session,
            run_id,
            blob_store=blob_store,
            adapter=lying,
            provider_config=provider_config,
        )

    assert raised.value.code is ErrorCode.ANALYSIS_INPUT_INVALID, raised.value.code


def test_nothing_is_written_under_the_mode_the_adapter_does_not_provide(
    session: Session, seeded, blob_store, recorded_adapter, provider_config
):
    """The refusal is worth having only if it happens *before* anything is recorded.

    A check that fired after the stages ran would leave a half-written run whose rows
    claim a provenance nothing produced — which is the failure §4 forbids, arrived at by
    a different route.
    """
    lying = _AdapterClaiming(recorded_adapter, ProviderMode.LIVE)
    run_id = _start(session, seeded, "writes-nothing")

    with pytest.raises(DomainError):
        execute_run(
            session,
            run_id,
            blob_store=blob_store,
            adapter=lying,
            provider_config=provider_config,
        )

    assert _run_state(session, run_id) == "created", (
        "the run left its initial state although the adapter was refused"
    )
    # The three tables that carry `run_id`, read from information_schema rather than
    # guessed: `finding` is reached through `finding_observation`, so it has no run_id
    # column of its own and naming it here was a schema assumption, not a check.
    for table in ("model_call", "stage_result", "finding_observation"):
        count = session.execute(
            text(f"SELECT count(*) FROM {table} WHERE run_id = :r"), {"r": run_id}
        ).scalar_one()
        assert count == 0, f"{table} carries {count} row(s) for a run that never ran"
