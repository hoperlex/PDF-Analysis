"""`HOSTS-L1` (`D-660`, contract 1.48.0): a waiting planned run names the cells that wait, with the model, the access and the cause.

Container-free, in the manner of ``test_run_status_executor.py``: ``RunRepository`` and the findings reads are replaced, and the executors
context is asked through its public ``evaluate_wait``, replaced here by a recorder that answers a ``BindOutcome``. What is proved:

* a ``pending`` planned run that is ``queued`` and waits reports its stored ``wait_reason`` and ``waiting_since`` and **names the cells**
  ``evaluate_wait`` says wait, in the plan's order, in exactly the four members of ``RunWaitCell``; it has no ``planned`` and no ``binding``
  (a planned run holds no group of its own, and the group reading used to refuse it);
* the evaluation is asked of the run's own id and the cells of its frozen plan, once;
* a run whose cells could all be bound now names none and the body has no ``wait_cells`` key (never an empty list);
* a planned run that is not waiting (bound, or running), and a run that froze its executor at start, do not ask at all;
* the body validates against the contract's ``RunStatus``, and a cause that is not a ``RunWaitCause`` word does not (the guard can fail).
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

PROJECT = "prj_01M2545JSD15ETSNNV904X991F"
VERSION = "ver_01M2545JSD15ETSNNV904X991J"
PROFILE = "ap_01M2545JSD15ETSNNV904X991A"
BUNDLE = "pb_01M2545JSD15ETSNNV904X991P"
RUN = "run_01M2545JSD15ETSNNV904X993K"
SINCE = datetime(2026, 11, 10, 9, 30, tzinfo=timezone.utc)

PLAN = {
    "format": "stage-plan/1", "layout_revision_id": "slr_01M2545JSD15ETSNNV904X991A", "kit": "codex_only",
    "cells": [
        {"cell_key": "text:main", "model_id": "gpt-6-sol", "effort": "medium", "access": "subscription"},
        {"cell_key": "blocks:leg1", "model_id": "gpt-6-astra", "effort": "medium", "access": "subscription"},
        {"cell_key": "review:main", "model_id": "gpt-6-sol", "effort": "medium", "access": "api"},
    ],
}


def _outcome(*waits: tuple[str, str, str, str]) -> Any:
    from auditmanager.executors.public import BindOutcome, CellWait

    items = tuple(CellWait(*wait) for wait in waits)
    return BindOutcome(bound=None, reason="model_unavailable", waits=items) if items else BindOutcome(bound=(), reason=None)


def _view(monkeypatch: pytest.MonkeyPatch, outcome: Any, **over: Any) -> tuple[Any, list[tuple[str, list[str]]]]:
    import auditmanager.execution.eta as eta
    import auditmanager.executors.public as executors_public
    import auditmanager.findings as findings
    import auditmanager.runs as runs_package
    from auditmanager.bootstrap.adapters import _run_status_view

    fields: dict[str, Any] = dict(
        run_id=RUN, project_uid=PROJECT, version_uid=VERSION, state="queued", provider_mode="live",
        created_at=datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc), analysis_profile_id=PROFILE, prompt_bundle_id=BUNDLE,
        degradation_set=(), terminal_reason=None, terminal_detail=None, interrupted_reason=None, terminal_at=None,
        reaudit_of_run_id=None, norms_snapshot_id=None, connection_revision_id=None, preset_revision_id=None,
        binding_state="pending", executor_group_revision_id=None, routing_rule_revision_id=None,
        wait_reason="model_unavailable", waiting_since=SINCE, stage_plan=PLAN,
    )
    fields.update(over)
    row = SimpleNamespace(**fields)

    class _Repository:
        def get(self, session: Any, run_id: str) -> Any:
            return row

        def stage_results(self, session: Any, run_id: str) -> tuple[()]:
            return ()

        def cost(self, session: Any, run_id: str) -> None:
            return None

    asked: list[tuple[str, list[str]]] = []

    def evaluate_wait(session: Any, *, run_id: str, cells: Any, **_: Any) -> Any:
        asked.append((run_id, [cell.cell_key for cell in cells]))
        return outcome

    monkeypatch.setattr(runs_package, "RunRepository", _Repository)
    monkeypatch.setattr(eta, "run_estimated_finish", lambda session, run_id: None)
    monkeypatch.setattr(findings, "published_finding_count", lambda session, run_id: 0)
    monkeypatch.setattr(findings, "diagnostics", lambda session, run_id: ())
    monkeypatch.setattr(executors_public, "executor_of_revision", lambda session, revision_id: None)
    monkeypatch.setattr(executors_public, "run_queue_reason", lambda session, run_id: None)
    monkeypatch.setattr(executors_public, "evaluate_wait", evaluate_wait)
    return _run_status_view(None, RUN), asked  # type: ignore[arg-type]


def test_a_waiting_planned_run_names_the_cells_that_wait_in_the_plans_order_and_has_no_group_of_its_own(monkeypatch: pytest.MonkeyPatch) -> None:
    from auditmanager.api.schemas.runs import run_status_body

    view, asked = _view(monkeypatch, _outcome(
        ("text:main", "gpt-6-sol", "subscription", "not_on_any_server"),
        ("review:main", "gpt-6-sol", "api", "at_capacity"),
    ))
    assert asked == [(RUN, ["text:main", "blocks:leg1", "review:main"])], "one read, of the run's own id and every cell of its plan"
    assert view.binding_state == "pending" and view.wait_reason == "model_unavailable" and view.waiting_since == SINCE
    assert view.planned is None and view.binding is None, "a planned run holds no group and no connection revision"
    body = run_status_body(view)
    assert body["wait_cells"] == [
        {"cell_key": "text:main", "model_id": "gpt-6-sol", "access": "subscription", "cause": "not_on_any_server"},
        {"cell_key": "review:main", "model_id": "gpt-6-sol", "access": "api", "cause": "at_capacity"},
    ]
    assert body["binding_state"] == "pending" and body["wait_reason"] == "model_unavailable"
    assert "planned" not in body and "binding" not in body and "queue_reason" not in body


def test_the_body_is_a_valid_run_status_and_a_cause_outside_the_closed_set_is_not(monkeypatch: pytest.MonkeyPatch) -> None:
    from auditmanager.api.schemas import models
    from auditmanager.api.schemas.runs import run_status_body

    view, _ = _view(monkeypatch, _outcome(("blocks:leg1", "gpt-6-astra", "subscription", "login_required")))
    body = run_status_body(view)
    parsed = models.RunStatus.model_validate(body)
    assert [(cell.cell_key, cell.cause.value, cell.access.value) for cell in parsed.wait_cells] == [("blocks:leg1", "login_required", "subscription")]
    body["wait_cells"][0]["cause"] = "runner_offline"       # a RunQueueReason word is not a cause of a cell
    with pytest.raises(Exception):
        models.RunStatus.model_validate(body)
    body["wait_cells"][0]["cause"] = "at_capacity"
    body["wait_cells"][0]["cell_key"] = "blocks"            # not a cell key
    with pytest.raises(Exception):
        models.RunStatus.model_validate(body)


def test_a_run_whose_cells_could_all_be_bound_now_names_none_and_the_body_has_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from auditmanager.api.schemas.runs import run_status_body

    view, asked = _view(monkeypatch, _outcome())
    assert len(asked) == 1 and view.wait_cells is None
    body = run_status_body(view)
    assert "wait_cells" not in body and body["wait_reason"] == "model_unavailable", "the stored reason is the sweep's; the cells are the status's own reading"


@pytest.mark.parametrize("over", [
    {"binding_state": "bound", "state": "running", "wait_reason": None, "waiting_since": None},   # bound at dispatch: nothing waits
    {"state": "running"},                                                                         # a stale reason on a run that is not queued
    {"wait_reason": None, "waiting_since": None},                                                  # queued with no stored reason
    {"binding_state": "frozen_at_start", "stage_plan": None, "wait_reason": None, "waiting_since": None},   # the legacy route
])
def test_a_planned_run_that_is_not_waiting_and_a_legacy_run_do_not_ask(monkeypatch: pytest.MonkeyPatch, over: dict[str, Any]) -> None:
    from auditmanager.api.schemas.runs import run_status_body

    view, asked = _view(monkeypatch, _outcome(("text:main", "gpt-6-sol", "subscription", "not_on_any_server")), **over)
    assert asked == [] and view.wait_cells is None
    assert "wait_cells" not in run_status_body(view)
