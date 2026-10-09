"""Crash the local executor on both sides of its two external-effect boundaries.

These tests use ordinary engine-bound sessions rather than the suite's rollback fixture:
closing the crashing session and observing from a new one is the property under test.
Every command key and aggregate identity is fresh, so the committed evidence is safe to
leave in the disposable integration database.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.text import ProviderConfig, ProviderMode
from auditmanager.ingest.reconciliation import Reconciler
from auditmanager.jobs import JobRepository
from auditmanager.runs import (
    execute_run,
    reconcile,
    reconcile_interrupted_runs,
    start_audit_run,
)
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey
from auditmanager.storage import BlobNotFoundError, parse_blob_id


class ProcessExit(BaseException):
    """A process loss: executor ``except Exception`` handlers cannot turn it into state."""


class InjectedFailure(RuntimeError):
    """A raised boundary fault for which the store still performs temporary cleanup."""


class CountingLiveAdapter:
    """The real recorded response shape presented through an explicit live test seam."""

    provider_mode = ProviderMode.LIVE

    def __init__(self, response_source) -> None:
        self._response_source = response_source
        self.calls = 0

    def complete(self, request):
        self.calls += 1
        return self._response_source.complete(request)


class FailingLiveAdapter:
    provider_mode = ProviderMode.LIVE

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, request):
        self.calls += 1
        raise DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            dependency="anthropic",
        )


class ExitAfterLiveResponse:
    """Lose the process after the provider returns but before response journalling."""

    provider_mode = ProviderMode.LIVE

    def __init__(self, response_source) -> None:
        self._response_source = response_source
        self.calls = 0

    def complete(self, request):
        self.calls += 1
        self._response_source.complete(request)
        raise ProcessExit("provider_returned_before_response_checkpoint")


class MissingOneObject:
    """Point-inspection view of a missing object; no bucket list or delete operation."""

    def __init__(self, inner, missing_blob_id: str) -> None:
        self._inner = inner
        self._missing_blob_id = missing_blob_id

    def inspect(self, blob_id):
        if str(blob_id) == self._missing_blob_id:
            raise BlobNotFoundError(blob_id=self._missing_blob_id)
        return self._inner.inspect(blob_id)

    def __getattr__(self, name):
        return getattr(self._inner, name)


class ExitAfterVerification:
    """Keep the exact temporary handle, then model process loss before DB verify state."""

    def __init__(self, inner) -> None:
        self._inner = inner
        self.temporary = None

    def stage_temporary(self, *args, **kwargs):
        self.temporary = self._inner.stage_temporary(*args, **kwargs)
        return self.temporary

    def verify_temporary(self, temporary):
        self._inner.verify_temporary(temporary)
        raise ProcessExit("artifact_verified_before_checkpoint")

    def __getattr__(self, name):
        return getattr(self._inner, name)


def _factory(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _key(label: str) -> IdempotencyKey:
    return IdempotencyKey(f"w48-{label}-{uuid4().hex}")


def _start(session: Session, helpers, blob_store, *, provider_mode: str):
    seeded = helpers.seed_version(session, blob_store)
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode=provider_mode,
        idempotency_key=_key(provider_mode),
    )
    return seeded, started


def _live_config() -> ProviderConfig:
    return ProviderConfig(
        mode=ProviderMode.LIVE,
        model_id="claude-opus-5",
        run_cost_ceiling_usd=1.0,
        api_key=None,
        ceiling_is_explicit=True,
    )


def _authority_for(session: Session, started, jobs: JobRepository):
    runs = RunRepository()
    runs.advance(session, run_id=started.run_id, from_state="created", to_state="queued")
    runs.advance(session, run_id=started.run_id, from_state="queued", to_state="running")
    return jobs.start_execution(session, run_id=started.run_id)


def _expire_and_reclaim(factory, run_id: str) -> None:
    """Model a dead owner after its lease expires, without waiting sixty seconds."""
    with factory() as controller:
        controller.execute(text(
            "UPDATE lease SET expires_at = statement_timestamp() - interval '1 second' "
            "WHERE attempt_id = (SELECT current_attempt_id FROM job WHERE run_id = :run_id)"
        ), {"run_id": run_id})
        controller.commit()
    with factory() as controller:
        assert JobRepository().reclaim_expired(controller) >= 1
        controller.commit()


def _terminate_without_settling(factory, run_id: str) -> None:
    """Make the owners terminal while retaining an effect for the bounded sweep."""
    with factory() as controller:
        controller.execute(text(
            "SELECT state FROM audit_run WHERE run_id = :run_id FOR UPDATE"
        ), {"run_id": run_id}).scalar_one()
        JobRepository().fail_for_run(controller, run_id=run_id)
        RunRepository().terminate(
            controller, run_id=run_id, from_state="running", to_state="failed",
            terminal_reason=ErrorCode.ANALYSIS_FAILED.value,
            interrupted_reason="test_terminal_owner_before_effect_settlement",
        )
        controller.commit()


def test_provider_checkpoints_refuse_a_foreign_current_authority(
    session,
    blob_store,
    helpers,
) -> None:
    jobs = JobRepository()
    _seeded_a, started_a = _start(
        session, helpers, blob_store, provider_mode="recorded"
    )
    _seeded_b, started_b = _start(
        session, helpers, blob_store, provider_mode="recorded"
    )
    authority_a = _authority_for(session, started_a, jobs)
    authority_b = _authority_for(session, started_b, jobs)
    session.commit()

    response_effect = jobs.prepare_provider_call(
        session,
        authority_a,
        provider="anthropic",
        model_identity="claude-opus-5",
        provider_mode="recorded",
        parameters={},
        request_sha256="1" * 64,
    )
    unknown_effect = jobs.prepare_provider_call(
        session,
        authority_a,
        provider="anthropic",
        model_identity="claude-opus-5",
        provider_mode="recorded",
        parameters={},
        request_sha256="2" * 64,
    )
    completion_effect = jobs.prepare_provider_call(
        session,
        authority_a,
        provider="anthropic",
        model_identity="claude-opus-5",
        provider_mode="recorded",
        parameters={},
        request_sha256="3" * 64,
    )
    jobs.record_provider_response(
        session,
        authority_a,
        model_call_id=completion_effect,
        response_sha256="4" * 64,
        input_tokens=10,
        output_tokens=20,
        latency_ms=30,
    )
    session.commit()

    with pytest.raises(DomainError) as response_refused:
        jobs.record_provider_response(
            session,
            authority_b,
            model_call_id=response_effect,
            response_sha256="5" * 64,
            input_tokens=1,
            output_tokens=2,
            latency_ms=3,
        )
    with pytest.raises(DomainError) as unknown_refused:
        jobs.record_provider_unknown(
            session,
            authority_b,
            model_call_id=unknown_effect,
            error_code=ErrorCode.DEPENDENCY_UNAVAILABLE.value,
        )
    with pytest.raises(DomainError) as completion_refused:
        jobs.complete_provider_call(
            session,
            authority_b,
            call={
                "model_call_id": str(completion_effect),
                "provider": "anthropic",
                "model_id": "claude-opus-5",
                "provider_mode": "recorded",
                "parameters": {},
                "request_sha256": "3" * 64,
                "response_sha256": "4" * 64,
                "input_tokens": 10,
                "output_tokens": 20,
                "latency_ms": 30,
                "cost_usd": 0.0,
                "cost_basis": "estimated",
                "status": "succeeded",
            },
        )

    assert {
        response_refused.value.code,
        unknown_refused.value.code,
        completion_refused.value.code,
    } == {ErrorCode.STATE_TRANSITION_NOT_ALLOWED}
    states = dict(
        session.execute(
            text(
                "SELECT model_call_id, state FROM provider_call_effect "
                "WHERE model_call_id = ANY(:ids)"
            ),
            {
                "ids": [
                    str(response_effect),
                    str(unknown_effect),
                    str(completion_effect),
                ]
            },
        ).all()
    )
    assert states == {
        str(response_effect): "prepared",
        str(unknown_effect): "prepared",
        str(completion_effect): "response_received",
    }
    assert session.execute(
        text("SELECT count(*) FROM model_call WHERE model_call_id = :model_call_id"),
        {"model_call_id": str(completion_effect)},
    ).scalar_one() == 0
    rendered = "".join(
        str(error.value) + repr(error.value.detail_fields)
        for error in (response_refused, unknown_refused, completion_refused)
    )
    assert authority_a.execution_token not in rendered
    assert authority_b.execution_token not in rendered


@pytest.mark.parametrize(
    ("boundary", "expected_state", "provider_calls"),
    [
        ("provider_intent_committed", "prepared", 0),
        ("provider_response_committed", "response_received", 1),
    ],
)
def test_provider_crash_boundaries_are_visible_from_a_new_transaction(
    engine,
    blob_store,
    recorded_adapter,
    helpers,
    boundary: str,
    expected_state: str,
    provider_calls: int,
) -> None:
    factory = _factory(engine)
    adapter = CountingLiveAdapter(recorded_adapter)
    session = factory()
    try:
        _seeded, started = _start(
            session, helpers, blob_store, provider_mode="live"
        )

        def crash_after(committed: str) -> None:
            if committed == boundary:
                raise ProcessExit(committed)

        with pytest.raises(ProcessExit, match=boundary):
            execute_run(
                session,
                started.run_id,
                blob_store=blob_store,
                adapter=adapter,
                provider_config=_live_config(),
                effect_checkpoint=crash_after,
            )
    finally:
        session.close()

    with factory() as observer:
        effect = observer.execute(
            text(
                "SELECT model_call_id, request_sha256, state, response_sha256 "
                "FROM provider_call_effect WHERE run_id = :run_id"
            ),
            {"run_id": started.run_id},
        ).mappings().one()
        model_call_count = observer.execute(
            text("SELECT count(*) FROM model_call WHERE run_id = :run_id"),
            {"run_id": started.run_id},
        ).scalar_one()

    assert effect["state"] == expected_state
    assert effect["model_call_id"].startswith("mc_")
    assert len(effect["request_sha256"]) == 64
    assert (effect["response_sha256"] is not None) is (
        expected_state == "response_received"
    )
    assert model_call_count == 0
    assert adapter.calls == provider_calls

    _terminate_without_settling(factory, started.run_id)

    with factory() as observer:
        report = reconcile(observer, older_than="0 seconds")
        assert started.run_id not in {item.run_id for item in report.unresolved_provider_effects}
        settled = {
            item.model_call_id: item for item in report.settled_provider_effects
        }
        assert settled[effect["model_call_id"]].previous_state == expected_state
        assert settled[effect["model_call_id"]].state == "abandoned"
        observer.commit()

    with factory() as observer:
        state, error_code = observer.execute(
            text(
                "SELECT state, error_code FROM provider_call_effect "
                "WHERE model_call_id = :model_call_id"
            ),
            {"model_call_id": effect["model_call_id"]},
        ).one()
        second = reconcile(observer, older_than="0 seconds")
    assert (state, error_code) == ("abandoned", ErrorCode.ANALYSIS_FAILED.value)
    assert second.settled_provider_effects == ()
    assert started.run_id not in {item.run_id for item in second.unresolved_provider_effects}


def test_live_response_lost_before_checkpoint_is_diagnosable_and_never_replayed(
    engine,
    blob_store,
    recorded_adapter,
    helpers,
) -> None:
    factory = _factory(engine)
    adapter = ExitAfterLiveResponse(recorded_adapter)
    session = factory()
    try:
        _seeded, started = _start(
            session, helpers, blob_store, provider_mode="live"
        )
        with pytest.raises(
            ProcessExit, match="provider_returned_before_response_checkpoint"
        ):
            execute_run(
                session,
                started.run_id,
                blob_store=blob_store,
                adapter=adapter,
                provider_config=_live_config(),
            )
    finally:
        session.close()

    with factory() as observer:
        before = observer.execute(
            text(
                "SELECT model_call_id, state, response_sha256 FROM provider_call_effect "
                "WHERE run_id = :run_id"
            ),
            {"run_id": started.run_id},
        ).mappings().one()
        assert dict(before) == {
            "model_call_id": before["model_call_id"],
            "state": "prepared",
            "response_sha256": None,
        }
        assert observer.execute(
            text("SELECT count(*) FROM model_call WHERE run_id = :run_id"),
            {"run_id": started.run_id},
        ).scalar_one() == 0

    _terminate_without_settling(factory, started.run_id)
    with factory() as observer:
        report = reconcile(observer, older_than="0 seconds")
        observer.commit()

    assert adapter.calls == 1
    assert started.run_id not in {item.run_id for item in report.unresolved_provider_effects}
    settled = {
        item.model_call_id: item for item in report.settled_provider_effects
    }
    assert settled[before["model_call_id"]].previous_state == "prepared"
    assert settled[before["model_call_id"]].state == "abandoned"

    with factory() as observer:
        assert observer.execute(
            text(
                "SELECT state FROM provider_call_effect "
                "WHERE model_call_id = :model_call_id"
            ),
            {"model_call_id": before["model_call_id"]},
        ).scalar_one() == "abandoned"
    assert adapter.calls == 1


def test_provider_effect_settlement_is_bounded_and_resumable(
    engine,
    blob_store,
    recorded_adapter,
    helpers,
) -> None:
    factory = _factory(engine)
    call_ids: set[str] = set()
    for _index in range(2):
        session = factory()
        try:
            _seeded, started = _start(
                session, helpers, blob_store, provider_mode="live"
            )

            def stop_after_intent(boundary: str) -> None:
                if boundary == "provider_intent_committed":
                    raise ProcessExit(boundary)

            with pytest.raises(ProcessExit, match="provider_intent_committed"):
                execute_run(
                    session,
                    started.run_id,
                    blob_store=blob_store,
                    adapter=CountingLiveAdapter(recorded_adapter),
                    provider_config=_live_config(),
                    effect_checkpoint=stop_after_intent,
                )
        finally:
            session.close()
        with factory() as observer:
            call_ids.add(
                str(
                    observer.execute(
                        text(
                            "SELECT model_call_id FROM provider_call_effect "
                            "WHERE run_id = :run_id"
                        ),
                        {"run_id": started.run_id},
                    ).scalar_one()
                )
            )

        _terminate_without_settling(factory, started.run_id)

    with factory() as observer:
        first = reconcile(
            observer,
            older_than="0 seconds",
            provider_effect_batch_size=1,
        )
        observer.commit()
    assert len(first.settled_provider_effects) == 1
    assert {item.model_call_id for item in first.unresolved_provider_effects} == (
        call_ids - {first.settled_provider_effects[0].model_call_id}
    )

    with factory() as observer:
        second = reconcile(
            observer,
            older_than="0 seconds",
            provider_effect_batch_size=1,
        )
        observer.commit()
    assert len(second.settled_provider_effects) == 1
    assert not (call_ids & {item.model_call_id for item in second.unresolved_provider_effects})


def test_an_ambiguous_live_failure_is_journalled_once_and_not_retried(
    engine, blob_store, helpers
) -> None:
    factory = _factory(engine)
    adapter = FailingLiveAdapter()
    with factory() as session:
        _seeded, started = _start(
            session, helpers, blob_store, provider_mode="live"
        )
        result = execute_run(
            session,
            started.run_id,
            blob_store=blob_store,
            adapter=adapter,
            provider_config=_live_config(),
            sleep=lambda _seconds: None,
        )
        session.commit()

    with factory() as observer:
        state, error_code = observer.execute(
            text(
                "SELECT state, error_code FROM provider_call_effect "
                "WHERE run_id = :run_id"
            ),
            {"run_id": started.run_id},
        ).one()

    assert adapter.calls == 1
    assert result.attempts == 1
    assert state == "outcome_unknown"
    assert error_code == ErrorCode.DEPENDENCY_UNAVAILABLE.value


@pytest.mark.parametrize(
    (
        "boundary",
        "blob_state_expected",
        "object_exists",
        "temporary_exists",
    ),
    [
        (
            "source_preparation:artifact_upload_intent_committed",
            "temporary",
            False,
            False,
        ),
        (
            "source_preparation:artifact_intent_committed",
            "verifying",
            False,
            False,
        ),
        (
            "source_preparation:artifact_published",
            "verifying",
            True,
            False,
        ),
    ],
)
def test_artifact_crash_boundaries_leave_enumerable_breadcrumbs(
    engine,
    blob_store,
    recorded_adapter,
    provider_config,
    helpers,
    boundary: str,
    blob_state_expected: str,
    object_exists: bool,
    temporary_exists: bool,
) -> None:
    factory = _factory(engine)
    session = factory()
    try:
        _seeded, started = _start(
            session, helpers, blob_store, provider_mode="recorded"
        )

        def crash_after(committed: str) -> None:
            if committed == boundary:
                raise InjectedFailure(committed)

        with pytest.raises(InjectedFailure, match=boundary):
            execute_run(
                session,
                started.run_id,
                blob_store=blob_store,
                adapter=recorded_adapter,
                provider_config=provider_config,
                effect_checkpoint=crash_after,
            )
    finally:
        session.close()

    with factory() as observer:
        publication = observer.execute(
            text(
                "SELECT blob_id, state FROM analysis_artifact_publication "
                "WHERE run_id = :run_id ORDER BY created_at LIMIT 1"
            ),
            {"run_id": started.run_id},
        ).mappings().one()
        blob_state = observer.execute(
            text("SELECT state FROM blob WHERE blob_id = :blob_id"),
            {"blob_id": publication["blob_id"]},
        ).scalar_one()

    assert publication["state"] == "prepared"
    assert blob_state == blob_state_expected
    try:
        blob_store.inspect(parse_blob_id(publication["blob_id"]))
        observed_exists = True
    except BlobNotFoundError:
        observed_exists = False
    assert observed_exists is object_exists

    report = Reconciler(blob_store, session_factory=factory).report()
    assert publication["blob_id"] not in {
        str(item.blob_id)
        for item in report.unattributed_blobs
    }
    unbound = [
        item
        for item in report.unbound_analysis_artifacts
        if item.run_id == started.run_id and str(item.blob_id) == publication["blob_id"]
    ]
    assert len(unbound) == 1
    assert unbound[0].stage_id == "source_preparation"
    assert unbound[0].attempt_state == "running"
    assert unbound[0].is_stale is False
    assert unbound[0].rejection_eligible is False
    assert unbound[0].object_present is object_exists
    assert unbound[0].temporary_present is temporary_exists


def test_process_loss_after_temporary_verification_keeps_a_pre_upload_breadcrumb(
    engine,
    blob_store,
    recorded_adapter,
    provider_config,
    helpers,
) -> None:
    factory = _factory(engine)
    killing_store = ExitAfterVerification(blob_store)
    session = factory()
    try:
        _seeded, started = _start(
            session, helpers, blob_store, provider_mode="recorded"
        )
        with pytest.raises(ProcessExit, match="artifact_verified_before_checkpoint"):
            execute_run(
                session,
                started.run_id,
                blob_store=killing_store,
                adapter=recorded_adapter,
                provider_config=provider_config,
            )
    finally:
        session.close()

    assert killing_store.temporary is not None
    try:
        # A second exact read proves the external temporary bytes survived the modeled
        # process loss; it neither lists the bucket nor publishes the object.
        verified = blob_store.verify_temporary(killing_store.temporary)
        with factory() as observer:
            publication = observer.execute(
                text(
                    "SELECT blob_id, state, stage_id FROM analysis_artifact_publication "
                    "WHERE run_id = :run_id ORDER BY created_at LIMIT 1"
                ),
                {"run_id": started.run_id},
            ).mappings().one()
            blob_state = observer.execute(
                text("SELECT state FROM blob WHERE blob_id = :blob_id"),
                {"blob_id": publication["blob_id"]},
            ).scalar_one()

        assert publication["blob_id"] == str(verified.blob_id)
        assert publication["state"] == "prepared"
        assert publication["stage_id"] == "source_preparation"
        assert blob_state == "temporary"

        report = Reconciler(blob_store, session_factory=factory).report()
        assert publication["blob_id"] not in {
            str(item.blob_id)
            for item in report.unattributed_blobs
        }
        unbound = [
            item
            for item in report.unbound_analysis_artifacts
            if item.run_id == started.run_id
            and str(item.blob_id) == publication["blob_id"]
        ]
        assert len(unbound) == 1
        assert unbound[0].attempt_state == "running"
        assert unbound[0].is_stale is False
        assert unbound[0].rejection_eligible is False
        assert unbound[0].object_present is False
        assert unbound[0].temporary_present is True
        assert not hasattr(unbound[0], "upload_token")

        reconciler = Reconciler(blob_store, session_factory=factory)
        with pytest.raises(DomainError) as refusal:
            reconciler.reject_unpublished(
                parse_blob_id(publication["blob_id"]), older_than="0 seconds"
            )
        assert refusal.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
        with factory() as observer:
            blob_state_after = observer.execute(
                text("SELECT state FROM blob WHERE blob_id = :blob_id"),
                {"blob_id": publication["blob_id"]},
            ).scalar_one()
            attempt_state_after = observer.execute(
                text(
                    "SELECT state FROM attempt WHERE attempt_id = "
                    "(SELECT attempt_id FROM analysis_artifact_publication "
                    " WHERE blob_id = :blob_id LIMIT 1)"
                ),
                {"blob_id": publication["blob_id"]},
            ).scalar_one()
        assert (blob_state_after, attempt_state_after) == ("temporary", "running")
    finally:
        blob_store.discard_temporary(killing_store.temporary)


def test_only_stale_terminal_analysis_publication_without_bytes_can_be_rejected(
    engine,
    blob_store,
    recorded_adapter,
    provider_config,
    helpers,
) -> None:
    factory = _factory(engine)
    killing_store = ExitAfterVerification(blob_store)
    session = factory()
    try:
        _seeded, started = _start(
            session, helpers, blob_store, provider_mode="recorded"
        )
        with pytest.raises(ProcessExit, match="artifact_verified_before_checkpoint"):
            execute_run(
                session,
                started.run_id,
                blob_store=killing_store,
                adapter=recorded_adapter,
                provider_config=provider_config,
            )
    finally:
        session.close()

    assert killing_store.temporary is not None
    verified = blob_store.verify_temporary(killing_store.temporary)
    blob_store.discard_temporary(killing_store.temporary)

    _expire_and_reclaim(factory, started.run_id)

    reconciler = Reconciler(blob_store, session_factory=factory)
    report = reconciler.report(unbound_artifact_age="0 seconds")
    item = next(
        entry
        for entry in report.unbound_analysis_artifacts
        if entry.run_id == started.run_id and entry.blob_id == verified.blob_id
    )
    assert item.attempt_state == "lost"
    assert item.is_stale is True
    assert item.object_present is False
    assert item.temporary_present is False
    assert item.rejection_eligible is True

    reconciler.reject_unpublished(verified.blob_id, older_than="0 seconds")
    with factory() as observer:
        state = observer.execute(
            text("SELECT state FROM blob WHERE blob_id = :blob_id"),
            {"blob_id": str(verified.blob_id)},
        ).scalar_one()
    assert state == "rejected"


def test_a_wrong_execution_token_and_a_superseded_attempt_fail_closed(
    engine, blob_store, recorded_adapter, provider_config, helpers
) -> None:
    factory = _factory(engine)
    with factory() as session:
        _seeded, started = _start(
            session, helpers, blob_store, provider_mode="recorded"
        )
        runs = RunRepository()
        runs.advance(
            session, run_id=started.run_id, from_state="created", to_state="queued"
        )
        runs.advance(
            session, run_id=started.run_id, from_state="queued", to_state="running"
        )
        jobs = JobRepository()
        authority = jobs.start_execution(session, run_id=started.run_id)
        session.commit()

        supplied = "wrong-token-value"
        with pytest.raises(DomainError) as invalid:
            jobs.require_current(
                session, replace(authority, execution_token=supplied)
            )
        assert invalid.value.code is ErrorCode.EXECUTION_TOKEN_INVALID
        rendered = repr(authority) + str(invalid.value) + repr(invalid.value.detail_fields)
        assert authority.execution_token not in rendered
        assert supplied not in rendered

        session.execute(
            text(
                "UPDATE attempt SET state = 'superseded', terminal_at = now(), "
                "updated_at = now() WHERE attempt_id = :attempt_id"
            ),
            {"attempt_id": authority.attempt_id},
        )
        session.commit()
        with pytest.raises(DomainError) as stale:
            jobs.prepare_provider_call(
                session,
                authority,
                provider="anthropic",
                model_identity="claude-opus-5",
                provider_mode="recorded",
                parameters={},
                request_sha256="0" * 64,
            )
        assert stale.value.code is ErrorCode.STALE_ATTEMPT


def test_supersession_before_the_first_effect_publishes_nothing(
    engine, blob_store, recorded_adapter, provider_config, helpers
) -> None:
    factory = _factory(engine)
    session = factory()
    try:
        _seeded, started = _start(
            session, helpers, blob_store, provider_mode="recorded"
        )

        def supersede_current_attempt() -> None:
            with factory() as controller:
                controller.execute(
                    text(
                        "UPDATE attempt a SET state = 'superseded', terminal_at = now(), "
                        "updated_at = now() FROM job j "
                        "WHERE j.run_id = :run_id "
                        "AND a.attempt_id = j.current_attempt_id"
                    ),
                    {"run_id": started.run_id},
                )
                controller.commit()

        with pytest.raises(DomainError) as refused:
            execute_run(
                session,
                started.run_id,
                blob_store=blob_store,
                adapter=recorded_adapter,
                provider_config=provider_config,
                checkpoint=supersede_current_attempt,
            )
        assert refused.value.code is ErrorCode.STALE_ATTEMPT
    finally:
        session.close()

    with factory() as observer:
        counts = observer.execute(
            text(
                "SELECT "
                "(SELECT count(*) FROM stage_result WHERE run_id = :run_id), "
                "(SELECT count(*) FROM provider_call_effect WHERE run_id = :run_id), "
                "(SELECT count(*) FROM analysis_artifact_publication WHERE run_id = :run_id), "
                "(SELECT count(*) FROM model_call WHERE run_id = :run_id)"
            ),
            {"run_id": started.run_id},
        ).one()
    assert tuple(counts) == (0, 0, 0, 0)


def test_bound_analysis_artifacts_are_not_detached_and_missing_bytes_are_named(
    engine, blob_store, recorded_adapter, provider_config, helpers
) -> None:
    factory = _factory(engine)
    with factory() as session:
        _seeded, started = _start(
            session, helpers, blob_store, provider_mode="recorded"
        )
        result = execute_run(
            session,
            started.run_id,
            blob_store=blob_store,
            adapter=recorded_adapter,
            provider_config=provider_config,
        )
        session.commit()
        assert result.terminal_state == "published"

    with factory() as observer:
        rows = observer.execute(
            text(
                "SELECT blob_id, stage_id, artifact_role "
                "FROM analysis_artifact_publication "
                "WHERE run_id = :run_id AND state = 'bound' ORDER BY stage_id, blob_id"
            ),
            {"run_id": started.run_id},
        ).all()
    assert rows
    bound_ids = {str(row.blob_id) for row in rows}

    healthy = Reconciler(blob_store, session_factory=factory).report()
    assert not (bound_ids & {str(item.blob_id) for item in healthy.unattributed_blobs})
    assert not {
        item.blob_id for item in healthy.missing_analysis_artifacts
    } & {parse_blob_id(blob_id) for blob_id in bound_ids}
    assert started.run_id not in {
        item.run_id for item in healthy.unbound_analysis_artifacts
    }

    missing_blob_id, missing_stage, missing_role = map(str, rows[0])
    hidden = MissingOneObject(blob_store, missing_blob_id)
    missing = Reconciler(hidden, session_factory=factory).report()
    named = [
        item
        for item in missing.missing_analysis_artifacts
        if str(item.blob_id) == missing_blob_id
    ]
    assert len(named) == 1
    assert named[0].run_id == started.run_id
    assert named[0].stage_id == missing_stage
    assert named[0].role == missing_role


# --- W48-FIX-C: regressions for W48-JUDGE-Z findings F-8 and F-9 -----------------------
#
# Each refusal below already existed and behaved correctly; what was missing was a test
# that fails when the refusal is removed. The existing tests assert only the error code,
# and every refusal of ``reject_unpublished`` shares one code, so a removed check was
# masked by the next one. These assert the refusal's own reason.


def _rejection_reason(refusal: pytest.ExceptionInfo[DomainError]) -> object:
    assert refusal.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    return refusal.value.detail_fields.get("current_state")


def _interrupted_publication(factory, helpers, blob_store, recorded_adapter, provider_config):
    """A verified, never-published analysis blob whose temporary bytes are gone."""
    killing_store = ExitAfterVerification(blob_store)
    session = factory()
    try:
        _seeded, started = _start(
            session, helpers, blob_store, provider_mode="recorded"
        )
        with pytest.raises(ProcessExit, match="artifact_verified_before_checkpoint"):
            execute_run(
                session,
                started.run_id,
                blob_store=killing_store,
                adapter=recorded_adapter,
                provider_config=provider_config,
            )
    finally:
        session.close()
    assert killing_store.temporary is not None
    verified = blob_store.verify_temporary(killing_store.temporary)
    blob_store.discard_temporary(killing_store.temporary)
    return started, verified


def _blob_state(factory, blob_id) -> str:
    with factory() as observer:
        return str(
            observer.execute(
                text("SELECT state FROM blob WHERE blob_id = :blob_id"),
                {"blob_id": str(blob_id)},
            ).scalar_one()
        )


def test_a_live_attempts_blob_is_refused_as_attempt_not_terminal_even_without_bytes(
    engine,
    blob_store,
    recorded_adapter,
    provider_config,
    helpers,
) -> None:
    """F-8, first half: the producing Attempt is still ``running``.

    The bytes are gone and the age threshold is zero, so every later check would let the
    rejection through: only ``attempt_not_terminal`` stands between a live Attempt and a
    permanently burned content identity.
    """
    factory = _factory(engine)
    _started, verified = _interrupted_publication(
        factory, helpers, blob_store, recorded_adapter, provider_config
    )
    reconciler = Reconciler(blob_store, session_factory=factory)
    with pytest.raises(DomainError) as refusal:
        reconciler.reject_unpublished(verified.blob_id, older_than="0 seconds")
    assert _rejection_reason(refusal) == "attempt_not_terminal"
    assert _blob_state(factory, verified.blob_id) == "temporary"


def test_a_fresh_terminal_publication_is_refused_as_publication_not_stale(
    engine,
    blob_store,
    recorded_adapter,
    provider_config,
    helpers,
) -> None:
    """F-8, second half: the Attempt is terminal, but the publication is younger than asked.

    Bytes are gone and the Attempt is ``lost``, so only ``publication_not_stale`` refuses;
    the same blob is then rejectable once the threshold admits it.
    """
    factory = _factory(engine)
    _started, verified = _interrupted_publication(
        factory, helpers, blob_store, recorded_adapter, provider_config
    )
    _expire_and_reclaim(factory, _started.run_id)
    reconciler = Reconciler(blob_store, session_factory=factory)
    with pytest.raises(DomainError) as refusal:
        reconciler.reject_unpublished(verified.blob_id, older_than="1 hour")
    assert _rejection_reason(refusal) == "publication_not_stale"
    assert _blob_state(factory, verified.blob_id) == "temporary"

    reconciler.reject_unpublished(verified.blob_id, older_than="0 seconds")
    assert _blob_state(factory, verified.blob_id) == "rejected"


def _prepared_provider_effect(factory, helpers, blob_store, recorded_adapter):
    """A live run stopped right after its provider intent was committed."""
    session = factory()
    try:
        _seeded, started = _start(session, helpers, blob_store, provider_mode="live")

        def stop_after_intent(boundary: str) -> None:
            if boundary == "provider_intent_committed":
                raise ProcessExit(boundary)

        with pytest.raises(ProcessExit, match="provider_intent_committed"):
            execute_run(
                session,
                started.run_id,
                blob_store=blob_store,
                adapter=CountingLiveAdapter(recorded_adapter),
                provider_config=_live_config(),
                effect_checkpoint=stop_after_intent,
            )
    finally:
        session.close()
    return started


def _effect_state(factory, run_id: str) -> str:
    with factory() as observer:
        return str(
            observer.execute(
                text("SELECT state FROM provider_call_effect WHERE run_id = :run_id"),
                {"run_id": run_id},
            ).scalar_one()
        )


def test_the_sweep_leaves_a_live_attempts_provider_effect_alone(
    engine,
    blob_store,
    recorded_adapter,
    helpers,
) -> None:
    """F-9, first half: Run, Job and Attempt are all still executing.

    With the age threshold at zero, only the terminal-owner conditions keep the sweep from
    marking a call that may still be in flight as ``abandoned``.
    """
    factory = _factory(engine)
    started = _prepared_provider_effect(factory, helpers, blob_store, recorded_adapter)
    with factory() as controller:
        settled = JobRepository().settle_terminal_provider_effects(
            controller, older_than="0 seconds"
        )
        controller.commit()
    assert started.run_id not in {item.run_id for item in settled}
    assert _effect_state(factory, started.run_id) == "prepared"


def test_the_sweep_leaves_a_terminal_effect_younger_than_its_threshold(
    engine,
    blob_store,
    recorded_adapter,
    helpers,
) -> None:
    """F-9, second half: the owners are terminal, but the effect is younger than asked.

    The run is terminated without settling its effects, so only the age condition refuses;
    the same effect is then settled once the threshold admits it.
    """
    factory = _factory(engine)
    started = _prepared_provider_effect(factory, helpers, blob_store, recorded_adapter)
    _terminate_without_settling(factory, started.run_id)
    with factory() as controller:
        young = JobRepository().settle_terminal_provider_effects(
            controller, older_than="1 hour"
        )
        controller.commit()
    assert started.run_id not in {item.run_id for item in young}
    assert _effect_state(factory, started.run_id) == "prepared"

    with factory() as controller:
        old = JobRepository().settle_terminal_provider_effects(
            controller, older_than="0 seconds"
        )
        controller.commit()
    assert started.run_id in {item.run_id for item in old}
    assert _effect_state(factory, started.run_id) == "abandoned"
