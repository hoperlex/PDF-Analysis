"""`W55B-BUDGET-01`: the served application always hands the analysis input budget to the commands.

``start_audit_run`` and ``reaudit_run`` take ``input_budget_characters: int | None = None`` so
the ~30 callers that predate the budget stay as they are, and ``None`` -- "no configuration" --
checks nothing. That default is only safe if the **served** application never takes it: an
adapter that forgot the keyword would silently admit a document of any size, which is the
very failure the budget exists to stop, and no behavioural test of the command would notice.

So this module proves it from the outside, three ways:

* by the **real composition**: ``build_application`` is run, the two adapters it really builds
  are caught, and the arguments each really passes to the real command entry points are read
  -- a positive ``int`` equal to what ``settings.load`` derived from the operator's model and
  ceiling (a ceiling the default would not produce, so a constant cannot pass);
* by **reading the source**: every call of either command in ``src/auditmanager`` outside
  ``runs/`` names the keyword, so an adapter added tomorrow is red before it is ever served;
* by **construction**: ``AppSettings`` cannot be built without the figure, and the start-up
  refusal reaches ``build_application`` and the worker, not only ``load``.

Container-free: ``build_application`` opens an engine lazily and these cases never run a
statement. It needs the lane's environment names only because the settings loader does.
"""

from __future__ import annotations

import ast
import dataclasses
import os
from pathlib import Path
from typing import Any

import pytest

from auditmanager.analysis.public import input_budget_characters
from auditmanager.api.composition import ConfigurationError, build_application
from auditmanager.bootstrap import adapters as adapters_module
from auditmanager.bootstrap import composition as composition_module
from auditmanager.bootstrap.composition import build_worker_runtime
from auditmanager.bootstrap.settings import (
    COST_CEILING_ENV,
    EXECUTION_ROLE_ENV,
    MODEL_ID_ENV,
    AppSettings,
)

SOURCE = Path(__file__).resolve().parents[3] / "src" / "auditmanager"
STATIC_TOKEN = "composition-suite-token"

#: A ceiling the default (1.00) does not produce, so the budget cannot be the default's by accident.
CEILING = "2.50"
MODEL = "claude-sonnet-5"


class _Captured(Exception):
    """Raised by a spy standing in for a command, carrying what the adapter passed it."""

    def __init__(self, kwargs: dict[str, Any]) -> None:
        super().__init__("captured")
        self.kwargs = kwargs


def _env() -> dict[str, str]:
    env = dict(os.environ)
    assert env.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    env["AUDITMANAGER_API_TOKEN"] = STATIC_TOKEN
    env[COST_CEILING_ENV] = CEILING
    env[MODEL_ID_ENV] = MODEL
    return env


@pytest.fixture
def served(monkeypatch: pytest.MonkeyPatch) -> Any:
    """The real application, with the two adapters it builds caught and both commands spied.

    Nothing about the wiring is replaced: the subclasses only remember themselves, and the
    spies stand where the adapters import the commands from, at call time.
    """
    import auditmanager.runs as runs_package
    import auditmanager.runs.commands as commands_module

    built: dict[str, Any] = {}

    class RunAdapterSpy(adapters_module.RunAdapter):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            built["runs"] = self

    class ExecutionAdapterSpy(adapters_module.ExecutionAdapter):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            built["execution"] = self

    def start_spy(session: Any, **kwargs: Any) -> Any:
        raise _Captured(kwargs)

    def reaudit_spy(session: Any, **kwargs: Any) -> Any:
        raise _Captured(kwargs)

    monkeypatch.setattr(composition_module, "RunAdapter", RunAdapterSpy)
    monkeypatch.setattr(composition_module, "ExecutionAdapter", ExecutionAdapterSpy)
    monkeypatch.setattr(runs_package, "start_audit_run", start_spy)
    monkeypatch.setattr(commands_module, "reaudit_run", reaudit_spy)
    # `_roles` is a database read; the spy is reached before the command, so give it a role.
    monkeypatch.setattr(
        adapters_module.ExecutionAdapter, "_roles", staticmethod(lambda _s, _u: frozenset({"expert"}))
    )
    app = build_application(environ=_env())
    assert set(built) == {"runs", "execution"}, "the composition root no longer builds both adapters"
    return app, built


def _expected_budget() -> int:
    return input_budget_characters(MODEL, float(CEILING))


class TestTheRealCompositionPassesTheDerivedBudget:
    def test_the_settings_carry_the_figure_derived_from_the_operators_model_and_ceiling(
        self, served: Any
    ) -> None:
        app, _ = served
        assert app.settings.model_id == MODEL
        assert app.settings.run_cost_ceiling_usd == float(CEILING)
        assert app.settings.input_budget_characters == _expected_budget()
        assert _expected_budget() != input_budget_characters("claude-opus-5", 1.0), (
            "the case would pass with the default's figure; choose a model and ceiling that differ"
        )

    def test_start_run_passes_a_positive_integer_budget(self, served: Any) -> None:
        app, built = served
        with pytest.raises(_Captured) as seen:
            built["runs"].start_run(
                version_uid="ver_00000000000000000000000000", idempotency_key="budget-probe-start"
            )
        assert "input_budget_characters" in seen.value.kwargs, "startRun forgot the budget"
        passed = seen.value.kwargs["input_budget_characters"]
        assert type(passed) is int and passed > 0
        assert passed == app.settings.input_budget_characters == _expected_budget()

    def test_reaudit_run_passes_a_positive_integer_budget(self, served: Any) -> None:
        app, built = served
        with pytest.raises(_Captured) as seen:
            built["execution"].reaudit_run(
                run_id="run_00000000000000000000000000",
                user_uid="usr_00000000000000000000000000",
                idempotency_key="budget-probe-reaudit",
            )
        assert "input_budget_characters" in seen.value.kwargs, "reauditRun forgot the budget"
        passed = seen.value.kwargs["input_budget_characters"]
        assert type(passed) is int and passed > 0
        assert passed == app.settings.input_budget_characters == _expected_budget()

    def test_a_reaudit_reads_the_budget_the_run_adapter_holds(self, served: Any) -> None:
        """One figure for both: the re-audit faces exactly the budget a start does (R-82)."""
        app, built = served
        assert built["runs"].input_budget_characters == app.settings.input_budget_characters
        assert built["execution"]._runs is built["runs"]


def _unbudgeted_calls(source: str) -> list[int]:
    """Line numbers of calls to either command that do not name ``input_budget_characters``.

    A call is the bare imported name or ``commands.<name>`` / ``runs.<name>``; a method that
    merely shares the name (the router's ``execution.reaudit_run``) is a different function.
    """
    flagged: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        name = (
            function.id
            if isinstance(function, ast.Name)
            else function.attr
            if isinstance(function, ast.Attribute)
            and isinstance(function.value, ast.Name)
            and function.value.id in {"commands", "runs"}
            else None
        )
        if name not in {"start_audit_run", "reaudit_run"}:
            continue
        if not any(keyword.arg == "input_budget_characters" for keyword in node.keywords):
            flagged.append(node.lineno)
    return flagged


class TestNoServedCodePathCanForgetTheBudget:
    def test_every_call_of_a_command_outside_the_runs_package_names_the_budget(self) -> None:
        offenders: list[str] = []
        inspected = 0
        for path in sorted(SOURCE.rglob("*.py")):
            if "runs" in path.relative_to(SOURCE).parts[:1]:
                continue
            source = path.read_text(encoding="utf-8")
            if "start_audit_run" not in source and "reaudit_run" not in source:
                continue
            inspected += 1
            offenders += [f"{path.relative_to(SOURCE)}:{line}" for line in _unbudgeted_calls(source)]
        assert inspected >= 1, "found no caller at all; the walk is not looking where the adapters are"
        assert offenders == [], f"a served path calls a command without the budget: {offenders}"

    def test_both_adapters_call_a_command_the_walk_can_see(self) -> None:
        """The walk is only worth anything if it reads the calls it is about."""
        source = (SOURCE / "bootstrap" / "adapters.py").read_text(encoding="utf-8")
        calls = [
            node.func.id
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"start_audit_run", "reaudit_run"}
        ]
        assert sorted(calls) == ["reaudit_run", "start_audit_run"]

    def test_the_walk_can_fail(self) -> None:
        """A guard nobody has watched fail may be silently disabled."""
        assert _unbudgeted_calls("start_audit_run(session, version_uid='v')") == [1]
        assert _unbudgeted_calls("commands.reaudit_run(session, source_run_id='r')") == [1]
        assert _unbudgeted_calls("start_audit_run(session, input_budget_characters=b)") == []
        assert _unbudgeted_calls("reaudit_run(session, **configuration)") == [1], (
            "a **kwargs spread cannot be shown to carry the budget"
        )
        assert _unbudgeted_calls("execution.reaudit_run(run_id=r)") == [], (
            "the router's port method shares the name and is not the command"
        )


class TestTheFigureIsPartOfTheSettingsAndTheStartUp:
    def test_app_settings_cannot_be_built_without_the_figure(self) -> None:
        field = next(f for f in dataclasses.fields(AppSettings) if f.name == "input_budget_characters")
        assert field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING
        assert field.type in (int, "int")

    def test_the_start_up_refusal_reaches_the_composition_root(self) -> None:
        with pytest.raises(ConfigurationError, match=COST_CEILING_ENV):
            build_application(environ=_env() | {COST_CEILING_ENV: "0.5", MODEL_ID_ENV: "claude-opus-5"})

    def test_the_worker_service_refuses_the_same_configuration(self) -> None:
        env = _env() | {EXECUTION_ROLE_ENV: "worker", COST_CEILING_ENV: "0.5", MODEL_ID_ENV: "claude-opus-5"}
        env.pop("AUDITMANAGER_API_TOKEN")
        with pytest.raises(ConfigurationError, match=COST_CEILING_ENV):
            build_worker_runtime(environ=env)
