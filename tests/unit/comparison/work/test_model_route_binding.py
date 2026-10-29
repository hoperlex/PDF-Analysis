"""The C2 worker binds each job to its frozen executor revision for all AI methods."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from auditmanager.bootstrap.composition import _ComparisonRoutes
from auditmanager.comparison.ai_pairs.handler import pair_check_handler
from auditmanager.comparison.ai_sheets.handler import sheet_changes_handler
from auditmanager.comparison.report.handler import report_handler
from auditmanager.comparison.spend.pull_images import PublishedPullAdapter
from auditmanager.comparison.specification.method import spec_handler
from auditmanager.comparison.work.model import WorkDependencies
from auditmanager.executors import runtime
from auditmanager.executors.public import SecretUnreadableError, pinned_models
from auditmanager.shared.errors import DomainError, ErrorCode


def _job_and_bound(*, bound_pin: str | None = None, bound_revision: str = "ecr_frozen"):
    pin = pinned_models()[0]
    job = SimpleNamespace(connection_revision_id="ecr_frozen", pinned_model=pin.model_id, provider_mode="live")
    adapter = object()
    bound = SimpleNamespace(
        adapter=adapter,
        revision=SimpleNamespace(
            revision_id=bound_revision,
            settings=SimpleNamespace(pin_id=bound_pin or pin.model_id, gateway_model="gateway-model",
                                     billing="not_metered"),
        ),
    )
    return job, bound, adapter


def test_frozen_revision_and_pin_are_the_only_route(monkeypatch: pytest.MonkeyPatch) -> None:
    job, bound, adapter = _job_and_bound()
    called = []
    ring, policy, worker_runtime, session = object(), object(), SimpleNamespace(session_factory=object()), object()

    def bind(given_session, revision, **options):
        called.append((given_session, revision, options))
        return bound

    monkeypatch.setattr(runtime, "bind_connection", bind)
    routes = _ComparisonRoutes(ring=ring, policy=policy, runtime=worker_runtime)
    route = routes.route(session, job)
    assert route.adapter is adapter and route.model_identity == job.pinned_model
    assert route.connection_revision_id == job.connection_revision_id
    assert route.expected_model == "gateway-model" and route.unmetered is True
    assert route.pin.model_id == job.pinned_model
    assert called == [(session, "ecr_frozen", {"ring": ring, "policy": policy, "context": route.call_context,
                                           "runtime": worker_runtime})]
    assert routes.route_for(session, job).model_identity == job.pinned_model


@pytest.mark.parametrize("mismatch", ["pin", "revision"])
def test_a_changed_pin_or_revision_has_no_fallback(monkeypatch: pytest.MonkeyPatch, mismatch: str) -> None:
    job, bound, _adapter = _job_and_bound(
        bound_pin="another-model" if mismatch == "pin" else None,
        bound_revision="ecr_changed" if mismatch == "revision" else "ecr_frozen",
    )
    monkeypatch.setattr(runtime, "bind_connection", lambda *_args, **_kwargs: bound)
    with pytest.raises(DomainError) as refused:
        _ComparisonRoutes(ring=object(), policy=object(), runtime=SimpleNamespace(session_factory=object())).route(object(), job)
    assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert refused.value.detail_fields["dependency"] == "executor_route_missing"


def test_an_unreadable_secret_remains_a_typed_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    job, _bound, _adapter = _job_and_bound()

    def unreadable(*_args, **_kwargs):
        raise SecretUnreadableError()

    monkeypatch.setattr(runtime, "bind_connection", unreadable)
    with pytest.raises(DomainError) as refused:
        _ComparisonRoutes(ring=object(), policy=object(), runtime=SimpleNamespace(session_factory=object())).route(object(), job)
    assert refused.value.code is ErrorCode.DEPENDENCY_CREDENTIAL_REFUSED


def test_a_recorded_job_never_opens_a_live_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    job, _bound, _adapter = _job_and_bound()
    job.provider_mode = "recorded"

    def forbidden(*_args, **_kwargs):
        raise AssertionError("a recorded job reached a live binder")

    monkeypatch.setattr(runtime, "bind_connection", forbidden)
    with pytest.raises(DomainError) as refused:
        _ComparisonRoutes(ring=object(), policy=object(), runtime=SimpleNamespace(session_factory=object())).route(object(), job)
    assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE


def test_a_pull_route_gets_the_attempt_context_and_crop_publisher(monkeypatch: pytest.MonkeyPatch) -> None:
    job, bound, _adapter = _job_and_bound()
    bound.connection = SimpleNamespace(kind="pull")
    monkeypatch.setattr(runtime, "bind_connection", lambda *_args, **_kwargs: bound)
    routes = _ComparisonRoutes(
        ring=object(), policy=object(), runtime=SimpleNamespace(session_factory=object()), blob_store=object(),
    )
    route = routes.route(object(), job)
    assert isinstance(route.adapter, PublishedPullAdapter)
    assert route.call_context is not None


def test_all_four_factories_receive_the_worker_route_source_without_io() -> None:
    routes = _ComparisonRoutes(ring=object(), policy=object(), runtime=object())
    dependencies = WorkDependencies(None, None, None, None, routes)  # type: ignore[arg-type]
    assert pair_check_handler(dependencies)._binder.__self__ is routes
    assert sheet_changes_handler(dependencies)._routes is routes
    assert spec_handler(dependencies)._binder.__self__ is routes
    assert report_handler(dependencies)._given[0] is routes
