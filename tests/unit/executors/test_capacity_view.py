"""`EXEC2-CAP-01` (ADR-0026 decision 1): what the API says of a connection's capacity, in the frozen shapes of
contract 1.15.0 -- the revision's ``max_active_runs``, the connection's ``occupancy`` and the Run status's
``queue_reason``.

Container-free: the adapter's mapping functions are called on hand-built records and the result is validated by
the generated closed models, so a field the contract does not have, or a value outside its range, fails here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.api.schemas import models
from auditmanager.api.schemas.runs import RunStatusView, run_status_body
from auditmanager.bootstrap.adapters import _executor_connection_view, _executor_revision_view
from auditmanager.executors.model import ConnectionRecord, RevisionRecord, RevisionSettings
from auditmanager.executors.queries import Occupancy, OccupiedConnectionSummary

NOW = datetime(2026, 11, 2, tzinfo=timezone.utc)
CONNECTION_ID = f"exc_{'0' * 26}"
REVISION_ID = f"excr_{'0' * 26}"
ACTOR = f"usr_{'0' * 26}"


def _settings(capacity: int | None) -> RevisionSettings:
    return RevisionSettings(
        pin_id="claude-opus-5", gateway_model="anthropic/claude-opus-5", billing="metered",
        allow_client_documents=False, timeout_seconds=60, api_flavour="openai_chat",
        base_url="https://proxy.test/agent/v1", transport="direct", max_active_runs=capacity,
    )


def _revision(capacity: int | None) -> RevisionRecord:
    return RevisionRecord(revision_id=REVISION_ID, connection_id=CONNECTION_ID, revision_no=2, created_at=NOW,
                          created_by=ACTOR, settings=_settings(capacity))


def _summary(occupancy: Occupancy, *, revision: RevisionRecord | None) -> OccupiedConnectionSummary:
    return OccupiedConnectionSummary(
        connection=ConnectionRecord(connection_id=CONNECTION_ID, kind="http_api", display_name="proxy",
                                    created_at=NOW, created_by=ACTOR),
        current_revision=revision, occupancy=occupancy,
    )


def test_a_connection_with_a_current_revision_shows_its_occupancy_in_the_contracts_shape() -> None:
    view = _executor_connection_view(_summary(Occupancy(3, 2, 1), revision=_revision(3)))
    assert view["occupancy"] == {"capacity": 3, "active_runs": 2, "active_calls": 1}
    served = models.ExecutorConnection.model_validate(view)
    assert (served.occupancy.capacity, served.occupancy.active_runs, served.occupancy.active_calls) == (3, 2, 1)


def test_a_connection_with_no_revision_shows_no_occupancy() -> None:
    """The contract has `occupancy` once the connection has a current revision; a connection nobody configured
    has no capacity to show, and an absent property is never `null`."""
    view = _executor_connection_view(_summary(Occupancy(1, 0, 0), revision=None))
    assert "occupancy" not in view
    assert models.ExecutorConnection.model_validate(view).occupancy is None


def test_a_full_connection_and_an_over_full_one_after_a_lowered_capacity_are_both_expressible() -> None:
    """`active_runs` may exceed `capacity` for a while after a revision lowered it; the contract only bounds
    `capacity` to 1..16 and the counts from below, so the read model must not clip or refuse."""
    full = models.ExecutorConnection.model_validate(
        _executor_connection_view(_summary(Occupancy(1, 1, 0), revision=_revision(1))))
    over = models.ExecutorConnection.model_validate(
        _executor_connection_view(_summary(Occupancy(1, 3, 1), revision=_revision(1))))
    assert (full.occupancy.active_runs, over.occupancy.active_runs, over.occupancy.active_calls) == (1, 3, 1)


@pytest.mark.parametrize("capacity", [1, 3, 16])
def test_a_revision_shows_the_capacity_it_was_written_with(capacity: int) -> None:
    view = _executor_revision_view(_revision(capacity), None)
    assert view["max_active_runs"] == capacity
    assert models.ExecutorRevision.model_validate(view).max_active_runs == capacity


def test_a_revision_written_before_the_setting_shows_no_capacity_rather_than_null() -> None:
    view = _executor_revision_view(_revision(None), None)
    assert "max_active_runs" not in view
    assert models.ExecutorRevision.model_validate(view).max_active_runs is None


def test_the_request_model_takes_the_capacity_and_refuses_one_outside_the_range() -> None:
    body = {"pin_id": "claude-opus-5", "gateway_model": "anthropic/claude-opus-5", "billing": "metered",
            "allow_client_documents": False, "timeout_seconds": 60, "api_flavour": "openai_chat",
            "base_url": "https://proxy.test/agent/v1", "transport": "direct"}
    assert models.ReviseExecutorConnectionRequest.model_validate({**body, "max_active_runs": 16}).max_active_runs == 16
    for outside in (0, 17):
        with pytest.raises(ValueError):
            models.ReviseExecutorConnectionRequest.model_validate({**body, "max_active_runs": outside})


# --- the Run status's queue_reason ------------------------------------------------------------------------------------

RUN = "run_01M2545JSD15ETSNNV904X993K"
PROJECT = "prj_01M2545JSD15ETSNNV904X991F"
VERSION = "ver_01M2545JSD15ETSNNV904X991J"


def _status(reason: str | None) -> RunStatusView:
    return RunStatusView(
        run_id=RUN, project_uid=PROJECT, version_uid=VERSION, state="queued", provider_mode="live",
        created_at=datetime(2026, 11, 2, 12, tzinfo=timezone.utc), queue_reason=reason,
    )


@pytest.mark.parametrize("reason", ["executor_at_capacity", "runner_offline"])
def test_the_status_body_renders_a_queue_reason_the_contract_accepts(reason: str) -> None:
    body = run_status_body(_status(reason))
    assert body["queue_reason"] == reason
    assert models.RunStatus.model_validate(body).queue_reason.value == reason


def test_the_status_body_of_a_run_that_is_not_waiting_has_no_queue_reason_key() -> None:
    """Every body that existed before the field is byte for byte what it was: absent, never null."""
    body = run_status_body(_status(None))
    assert "queue_reason" not in body
    assert models.RunStatus.model_validate(body).queue_reason is None


def _view(monkeypatch: pytest.MonkeyPatch, *, state: str, revision: str | None, reason: str | None) -> tuple[Any, list[str]]:
    """``_run_status_view`` with the repositories replaced, in the manner of
    ``tests/unit/runs/test_run_status_executor.py``; ``run_queue_reason`` is a recorder."""
    import auditmanager.executors.public as executors_public
    import auditmanager.findings as findings
    import auditmanager.runs as runs_package
    from auditmanager.bootstrap.adapters import _run_status_view

    row = SimpleNamespace(
        run_id=RUN, project_uid=PROJECT, version_uid=VERSION, state=state, provider_mode="live",
        created_at=datetime(2026, 11, 2, tzinfo=timezone.utc), analysis_profile_id=None, prompt_bundle_id=None,
        degradation_set=(), terminal_reason=None, terminal_detail=None, interrupted_reason=None,
        terminal_at=None, reaudit_of_run_id=None, norms_snapshot_id=None, connection_revision_id=revision,
        preset_revision_id=None,
    )

    class _Repository:
        def get(self, session: Any, run_id: str) -> Any:
            return row

        def stage_results(self, session: Any, run_id: str) -> tuple[()]:
            return ()

        def cost(self, session: Any, run_id: str) -> None:
            return None

    asked: list[str] = []

    def run_queue_reason(session: Any, run_id: str) -> str | None:
        asked.append(run_id)
        return reason

    monkeypatch.setattr(runs_package, "RunRepository", _Repository)
    # Contract 1.40.0 (`UI-B-45`): the view reads an active run's estimated finish from the database; these cases stub
    # the session, so the estimate is stubbed too (its own cases are tests/unit/execution/test_eta.py).
    import auditmanager.execution.eta as eta
    monkeypatch.setattr(eta, "run_estimated_finish", lambda session, run_id: None)
    monkeypatch.setattr(findings, "published_finding_count", lambda session, run_id: 0)
    monkeypatch.setattr(findings, "diagnostics", lambda session, run_id: ())
    monkeypatch.setattr(executors_public, "executor_of_revision", lambda session, revision_id: None)
    monkeypatch.setattr(executors_public, "run_queue_reason", run_queue_reason)
    return _run_status_view(None, RUN), asked  # type: ignore[arg-type]


@pytest.mark.parametrize("state", ["queued", "running"])
def test_a_run_that_froze_a_revision_and_may_be_waiting_is_asked_why(monkeypatch: pytest.MonkeyPatch, state: str) -> None:
    view, asked = _view(monkeypatch, state=state, revision="exr_FROZEN", reason="executor_at_capacity")
    assert asked == [RUN] and view.queue_reason == "executor_at_capacity"
    assert run_status_body(view)["queue_reason"] == "executor_at_capacity"


def test_a_run_with_no_answer_has_no_queue_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    view, asked = _view(monkeypatch, state="queued", revision="exr_FROZEN", reason=None)
    assert asked == [RUN] and view.queue_reason is None and "queue_reason" not in run_status_body(view)


@pytest.mark.parametrize(("state", "revision"), [
    ("queued", None),                    # the `environment` source froze no connection to wait for
    ("published", "exr_FROZEN"), ("failed", "exr_FROZEN"), ("cancelled", "exr_FROZEN"),
])
def test_a_run_that_cannot_be_waiting_costs_no_query_and_has_no_queue_reason(
    monkeypatch: pytest.MonkeyPatch, state: str, revision: str | None,
) -> None:
    view, asked = _view(monkeypatch, state=state, revision=revision, reason="executor_at_capacity")
    assert asked == [] and view.queue_reason is None
