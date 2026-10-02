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
from auditmanager.runs import execute_run, reconcile, start_audit_run
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

    with factory() as observer:
        report = reconcile(observer, older_than="0 seconds")
        assert effect["model_call_id"] in {
            item.model_call_id for item in report.unresolved_provider_effects
        }
        observer.rollback()


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
        "report_field",
    ),
    [
        (
            "source_preparation:artifact_upload_intent_committed",
            "temporary",
            False,
            False,
            "unpublished_records",
        ),
        (
            "source_preparation:artifact_intent_committed",
            "verifying",
            False,
            False,
            "unpublished_records",
        ),
        (
            "source_preparation:artifact_published",
            "verifying",
            True,
            False,
            "orphan_objects",
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
    report_field: str,
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
    enumerated = getattr(report, report_field)
    assert publication["blob_id"] in {str(item.blob_id) for item in enumerated}
    unbound = [
        item
        for item in report.unbound_analysis_artifacts
        if item.run_id == started.run_id and str(item.blob_id) == publication["blob_id"]
    ]
    assert len(unbound) == 1
    assert unbound[0].stage_id == "source_preparation"
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
        assert publication["blob_id"] in {
            str(item.blob_id) for item in report.unpublished_records
        }
        unbound = [
            item
            for item in report.unbound_analysis_artifacts
            if item.run_id == started.run_id
            and str(item.blob_id) == publication["blob_id"]
        ]
        assert len(unbound) == 1
        assert unbound[0].object_present is False
        assert unbound[0].temporary_present is True
        assert not hasattr(unbound[0], "upload_token")
    finally:
        blob_store.discard_temporary(killing_store.temporary)


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
    assert not (bound_ids & {str(item.blob_id) for item in healthy.orphan_objects})
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
