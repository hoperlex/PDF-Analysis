"""`W53C-EXEC-01`: the closure findings C-01, C-02, C-03, C-05 and C-06 on real PostgreSQL.

* C-01 -- a pause that lands between the dispatcher's hint and the claim must leave the
  run and its Job queued. It used to reach ``_record_crash``: Job queued -> cancelled,
  run queued -> failed, for a run this process never held.
* C-02 (`R-82`) -- a re-audit records the configuration it actually runs, never the
  source run's.
* C-03 -- the lineage is read from ``RunRow``, not by raw SQL in the composition root.
* C-05 -- a failed recorded replay is ``not_processed``, so a crash after it resumes.
* C-06 -- ``ABSENT_CAPABILITIES`` no longer claims there is no cancel command.
"""

from __future__ import annotations

from contextlib import nullcontext
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from auditmanager.analysis.text import ProviderMode
from auditmanager.bootstrap.adapters import ExecutionAdapter
from auditmanager.jobs.public import ExecutionNotClaimed, JobRepository
from auditmanager.runs import execute_run, run_to_terminal
from auditmanager.runs.commands import (
    cancel_audit_run,
    frozen_input_digest,
    reaudit_run,
)
from auditmanager.runs.repository import RunRepository
from auditmanager.runs.scope import ABSENT_CAPABILITIES, AGGREGATES_NOT_INSTANTIATED
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AnalysisProfileId, PromptBundleId, RunId
from tests.support.v1_reference_profile import resolve_reference_profile


def _key() -> str:
    return "w53c-exec-" + uuid4().hex


def _run(session, seeded, *, mode: str = "recorded", terminal: bool = False) -> str:
    run_id = str(RunId.new())
    runs = RunRepository()
    runs.create(
        session, run_id=run_id, project_uid=seeded.project_uid,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode=mode, frozen_input_digest="a" * 64, command_id=None,
    )
    runs.advance(session, run_id=run_id, from_state="created", to_state="queued")
    if terminal:
        runs.advance(session, run_id=run_id, from_state="queued", to_state="running")
        runs.terminate(
            session, run_id=run_id, from_state="running", to_state="failed",
            terminal_reason=ErrorCode.ANALYSIS_FAILED.value,
        )
    return run_id


# --- C-01 ----------------------------------------------------------------------


def test_a_pause_between_hint_and_claim_leaves_the_run_queued(
    engine, blob_store, helpers, recorded_adapter, provider_config
) -> None:
    jobs = JobRepository()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as seed:
        jobs.set_paused(seed, paused=False)
        seeded = helpers.seed_version(seed, blob_store)
        run_id = _run(seed, seeded)
        job_id = jobs.enqueue(seed, run_id=run_id)
        jobs.set_priority(seed, job_id=job_id, priority=100)
        seed.commit()
    try:
        # The dispatcher's hint reads an unpaused queue ...
        with sessions() as poller:
            assert jobs.next_queued_run(poller) is not None
        # ... and an administrator pauses before the worker claims.
        with sessions() as administrator:
            jobs.set_paused(administrator, paused=True)
            administrator.commit()

        with pytest.raises(ExecutionNotClaimed) as refusal:
            run_to_terminal(
                sessions, run_id, blob_store=blob_store, adapter=recorded_adapter,
                provider_config=provider_config,
                text_profiles=resolve_reference_profile,
            )
        assert refusal.value.code is ErrorCode.CONFLICT

        with sessions() as observer:
            row = observer.execute(text(
                "SELECT r.state, r.terminal_reason, r.interrupted_reason, j.state, "
                "j.current_attempt_id, (SELECT count(*) FROM attempt a "
                "WHERE a.job_id = j.job_id) FROM audit_run r "
                "JOIN job j ON j.run_id = r.run_id WHERE r.run_id = :run_id"
            ), {"run_id": run_id}).one()
        assert tuple(row) == ("queued", None, None, "queued", None, 0), (
            "a pause that raced the claim destroyed a queued run this process never held",
            tuple(row),
        )
    finally:
        with sessions() as administrator:
            jobs.set_paused(administrator, paused=False)
            administrator.commit()
        with sessions() as cleanup:
            cancel_audit_run(
                cleanup, run_id=run_id, roles=frozenset({"expert"}),
                idempotency_key=_key(),
            )
            cleanup.commit()


# --- C-02 and C-03 -----------------------------------------------------------------


def _current_configuration() -> tuple[str, str, str]:
    return AnalysisProfileId.new().value, PromptBundleId.new().value, "live"


def test_reaudit_records_the_current_configuration_not_the_source(
    session, blob_store, helpers
) -> None:
    seeded = helpers.seed_version(session, blob_store)
    source_id = _run(session, seeded, mode="recorded", terminal=True)
    profile, bundle, mode = _current_configuration()

    started = reaudit_run(
        session, source_run_id=source_id, roles=frozenset({"expert"}),
        idempotency_key=_key(), analysis_profile_id=profile,
        prompt_bundle_id=bundle, provider_mode=mode,
    )

    source = RunRepository().get(session, source_id)
    child = RunRepository().get(session, started.run_id)
    assert (child.analysis_profile_id, child.prompt_bundle_id, child.provider_mode) == (
        profile, bundle, mode,
    ), "the re-audit recorded the source run's configuration, not the one it runs"
    assert (source.analysis_profile_id, source.provider_mode) != (profile, mode)
    assert child.frozen_input_digest == frozen_input_digest(
        version_uid=seeded.version_uid,
        blob_ids={helpers.MANIFEST_ROLE_SOURCE: seeded.source_blob_id},
        analysis_profile_id=profile,
        prompt_bundle_id=bundle,
        # `W55A-PIN-01`: the re-audit pins whatever is current in this database.
        norms_snapshot_id=child.norms_snapshot_id,
    )
    assert child.frozen_input_digest != source.frozen_input_digest
    assert child.version_uid == source.version_uid
    assert child.reaudit_of_run_id == source_id
    assert source.reaudit_of_run_id is None


class _ConfiguredRuns:
    """The things ExecutionAdapter asks of RunAdapter.

    ``input_budget_characters`` is the third (`W55B-BUDGET-01`): ``None`` is "no
    configuration", which this stub, like any test-built adapter, may carry and the served
    application never does. The budget's own cases are ``test_input_budget*.py``.
    """

    input_budget_characters: int | None = None
    #: `W59-SECTION-SEAL-01`. No section table: this stub keeps the configured pair, as an
    #: unrouted test wiring may; the served application always routes
    #: (``test_the_served_application_routes_by_section.py``).
    section_profiles: None = None
    #: `EXEC-HTTP-01`. No route freezer: ``ExecutionAdapter.reaudit_run`` passes the adapter's
    #: freezer to the command, and ``None`` is a wiring without the ``database`` provider source.
    route_freezer: None = None

    def __init__(self, configuration: tuple[str, str, str]) -> None:
        self.configuration = configuration
        self.submitted: list[str] = []

    def current_configuration(self) -> tuple[str, str, str]:
        return self.configuration

    def submit_existing(self, run_id: str) -> None:
        self.submitted.append(run_id)


def test_the_reaudit_port_stamps_the_deployment_and_reports_lineage(
    session, blob_store, helpers, monkeypatch
) -> None:
    seeded = helpers.seed_version(session, blob_store)
    source_id = _run(session, seeded, mode="recorded", terminal=True)
    configuration = _current_configuration()
    runs = _ConfiguredRuns(configuration)
    monkeypatch.setattr(
        ExecutionAdapter, "_roles",
        staticmethod(lambda _session, _user: frozenset({"expert"})),
    )
    port = ExecutionAdapter(lambda: nullcontext(session), runs=runs)

    view = port.reaudit_run(
        run_id=source_id, user_uid="usr_" + str(RunId.new()).split("_", 1)[1],
        idempotency_key=_key(),
    )

    assert (view.analysis_profile_id, view.prompt_bundle_id, view.provider_mode) == (
        configuration
    )
    assert view.reaudit_of_run_id == source_id
    assert view.state == "queued"
    assert runs.submitted == [view.run_id]


# --- C-05 ----------------------------------------------------------------------


class _FailingReplay:
    """A recorded adapter whose replay fails, as a missing recording does."""

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.RECORDED

    def complete(self, request):
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID, message="no recording for this request"
        )


class _Crash(RuntimeError):
    pass


def test_a_crash_after_a_failed_replay_resumes_instead_of_failing(
    session, blob_store, helpers, provider_config
) -> None:
    seeded = helpers.seed_version(session, blob_store)
    run_id = _run(session, seeded, mode="recorded")
    JobRepository().enqueue(session, run_id=run_id)

    def crash_after_the_provider_journal(boundary: str) -> None:
        if boundary in {"provider_not_processed", "provider_outcome_unknown"}:
            raise _Crash(boundary)

    with pytest.raises(_Crash):
        execute_run(
            session, run_id, blob_store=blob_store, adapter=_FailingReplay(),
            provider_config=provider_config, sleep=lambda _seconds: None,
            effect_checkpoint=crash_after_the_provider_journal,
            text_profiles=resolve_reference_profile,
        )

    effect_state = session.execute(text(
        "SELECT state FROM provider_call_effect WHERE run_id = :run_id"
    ), {"run_id": run_id}).scalar_one()
    assert effect_state == "not_processed", (
        "a recorded replay was journalled as a possibly-paid provider effect"
    )

    session.execute(text(
        "UPDATE lease SET expires_at = statement_timestamp() - interval '1 second' "
        "WHERE released_at IS NULL AND job_id = "
        "(SELECT job_id FROM job WHERE run_id = :run_id)"
    ), {"run_id": run_id})
    assert JobRepository().reclaim_expired(session) >= 1

    row = session.execute(text(
        "SELECT r.state, j.state FROM audit_run r JOIN job j ON j.run_id = r.run_id "
        "WHERE r.run_id = :run_id"
    ), {"run_id": run_id}).one()
    assert tuple(row) == ("running", "queued"), (
        "a crashed recorded run was failed as if its replay might have been paid",
        tuple(row),
    )


# --- C-06 ----------------------------------------------------------------------


def test_the_scope_note_does_not_deny_a_command_that_exists() -> None:
    from auditmanager.runs import commands

    assert callable(commands.cancel_audit_run)
    assert not any("no cancel command" in entry for entry in ABSENT_CAPABILITIES)
    # What the note still claims absent must still be absent.
    cancellation = [e for e in ABSENT_CAPABILITIES if e.startswith("cancellation")]
    assert cancellation and "validating" not in commands._CANCELLABLE_RUN_STATES
    remote = [e for e in ABSENT_CAPABILITIES if e.startswith("remote execution")]
    # `W54-SEAL-01`: migration 0019 instantiates the `worker` registry table, so it left the
    # absent-aggregate list; the worker *process* is still absent until W54-WORKER-01, and
    # the remote-execution note keeps saying so.
    assert remote and "worker" not in AGGREGATES_NOT_INSTANTIATED
