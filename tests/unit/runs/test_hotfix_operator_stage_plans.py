"""`D-670` (`HOSTS-DEBTS-01`): the operator's re-audit takes the stage layout through the same reader the API's re-audit does.

``reaudit_unmetered`` builds the application, approves an unmetered estimate and calls ``reaudit_run``. With the layout on, the estimate it
approves (the cost preflight reads the layout itself) is the plan's, so a command that is not told where the layout is freezes a run **without**
the plan the consent was for: the legacy route, in silence. The command must be handed ``stage_plans=control.stage_plans`` -- the object
``ExecutionAdapter.reaudit_run`` hands it (``tests/unit/bootstrap/test_hosts_int_wiring.py``).

No database and no application: ``build_application`` and the repositories are fakes, ``reaudit_run`` records what it was called with.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.bootstrap import adapters, public as bootstrap_public
from auditmanager.runs import hotfix_operator as operator

RUN = "run_01M2545JSD15ETSNNV904X991K"
KEY = operator.TASK_KEY


class _Session:
    def __enter__(self) -> "_Session":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def begin(self) -> "_Session":
        return self


class _Estimate:
    estimate_digest = "d" * 64

    def as_dict(self) -> dict[str, Any]:
        return {"billing": "unmetered", "estimated_cost_micros": 0}

    def approve(self, consent: Any, *, actor_user_uid: Any) -> dict[str, Any]:
        return {}


class _Control:
    """The members of a ``RunAdapter`` that ``reaudit_unmetered`` reads."""

    input_budget_characters = 1000
    route_freezer = object()
    group_admitter = object()
    section_profiles = None

    def __init__(self, stage_plans: Any) -> None:
        self.stage_plans = stage_plans
        self.cost_preflight = SimpleNamespace(estimate_reaudit=lambda session, **kwargs: _Estimate())
        self.submitted: list[str] = []

    def current_configuration(self) -> tuple[Any, Any, str]:
        return "profile", "bundle", "live"

    def submit_existing(self, run_id: str) -> None:
        self.submitted.append(run_id)


@pytest.fixture
def seen(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    class Runs:
        def get(self, session: Any, run_id: str) -> Any:
            return SimpleNamespace(state="published")

    class Commands:
        def find(self, session: Any, **kwargs: Any) -> None:
            return None

    def reaudit_run(session: Any, **kwargs: Any) -> Any:
        calls.append(kwargs)
        return SimpleNamespace(run_id="run_NEW", replayed=False)

    monkeypatch.setattr(operator, "RunRepository", Runs)
    monkeypatch.setattr(operator, "CommandRepository", Commands)
    monkeypatch.setattr(operator, "reaudit_run", reaudit_run)
    return calls


def _application(monkeypatch: pytest.MonkeyPatch, control: Any) -> None:
    application = SimpleNamespace(run_control=control, session_factory=_Session)
    monkeypatch.setattr(bootstrap_public, "build_application", lambda environ=None, **kwargs: application)


def test_the_operators_reaudit_is_handed_the_layout_reader_of_the_run_adapter(monkeypatch: pytest.MonkeyPatch, seen: list[dict[str, Any]]) -> None:
    reader = object()
    control = _Control(reader)
    _application(monkeypatch, control)
    result = operator.reaudit_unmetered(RUN, KEY)
    (command,) = seen
    assert command["stage_plans"] is reader, "the layout is read by the object the API's re-audit reads it by"
    assert command["cost_preflight"] is control.cost_preflight and command["connection_route"] is control.route_freezer
    assert result["run_id"] == "run_NEW" and control.submitted == ["run_NEW"]


def test_a_layout_that_is_off_is_still_asked_not_assumed(monkeypatch: pytest.MonkeyPatch, seen: list[dict[str, Any]]) -> None:
    """The freezer answers ``None`` while the switch is off; the command must still be handed the freezer to ask."""
    def off(session: Any) -> None:
        return None

    _application(monkeypatch, _Control(off))
    operator.reaudit_unmetered(RUN, KEY)
    assert seen[0]["stage_plans"] is off


def test_a_control_without_the_seam_is_not_served_by_the_legacy_route_in_silence(monkeypatch: pytest.MonkeyPatch, seen: list[dict[str, Any]]) -> None:
    control = _Control(None)
    del control.stage_plans
    _application(monkeypatch, control)
    with pytest.raises(AttributeError):
        operator.reaudit_unmetered(RUN, KEY)
    assert seen == [], "no command was issued without the layout reader"


def test_the_run_adapter_the_operator_reads_has_the_member_it_asks_for() -> None:
    """``application.run_control`` is the ``RunAdapter``: its ``stage_plans`` is the member ``reaudit_unmetered`` reads."""
    assert isinstance(adapters.RunAdapter.stage_plans, property)
