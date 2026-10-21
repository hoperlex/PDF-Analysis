"""`W59-SECTION-SEAL-01`: the served application always routes run start by section.

``start_audit_run`` and ``reaudit_run`` still accept an explicit profile pair for in-process
callers, and ``execute_run`` still runs the v1 AR profile when it is handed no resolver. Both
are safe only if the **served** application never takes them -- an adapter that forgot the
section table would start every run on the configured AR pair, the AR fallback the decision
forbids, and no behavioural test of the command would notice. So this proves it from the
real composition:

* ``startRun`` and ``reauditRun`` pass ``section_profiles`` equal to the loaded registry's
  table and pass **no** profile or bundle of their own;
* the run adapter and the worker runtime hand ``execute_run`` the registry's resolver;
* the section port is wired, and its ``executable`` set is the registry's;
* a package the registry refuses stops ``build_application`` and the worker at start-up.

Container-free: ``build_application`` opens its engine lazily and nothing here runs a
statement. It needs the lane's environment names only because the settings loader does.
"""

from __future__ import annotations

import os
from typing import Any

import pytest

from auditmanager.analysis.text import profile_registry as registry_module
from auditmanager.analysis.text.profile_registry import (
    SECTION_CODES,
    TextProfileLoadError,
    TextProfileRegistry,
    load_text_profile_registry,
)
from auditmanager.api.composition import ConfigurationError, build_application
from auditmanager.bootstrap import adapters as adapters_module
from auditmanager.bootstrap import composition as composition_module
from auditmanager.bootstrap.composition import build_worker_runtime
from auditmanager.bootstrap.settings import EXECUTION_ROLE_ENV

STATIC_TOKEN = "composition-suite-token"


class _Captured(Exception):
    def __init__(self, kwargs: dict[str, Any]) -> None:
        super().__init__("captured")
        self.kwargs = kwargs


def _env(**extra: str) -> dict[str, str]:
    env = dict(os.environ)
    assert env.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    env["AUDITMANAGER_API_TOKEN"] = STATIC_TOKEN
    env.update(extra)
    return env


def _worker_env() -> dict[str, str]:
    """The API's environment without its secret, as ``compose.server.yml`` runs the worker."""
    env = _env(**{EXECUTION_ROLE_ENV: "worker"})
    env.pop("AUDITMANAGER_API_TOKEN")
    return env


@pytest.fixture
def served(monkeypatch: pytest.MonkeyPatch) -> Any:
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

    class SectionAdapterSpy(adapters_module.SectionAdapter):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            built["sections"] = self

    def spy(session: Any, **kwargs: Any) -> Any:
        raise _Captured(kwargs)

    monkeypatch.setattr(composition_module, "RunAdapter", RunAdapterSpy)
    monkeypatch.setattr(composition_module, "ExecutionAdapter", ExecutionAdapterSpy)
    monkeypatch.setattr(composition_module, "SectionAdapter", SectionAdapterSpy)
    monkeypatch.setattr(runs_package, "start_audit_run", spy)
    monkeypatch.setattr(commands_module, "reaudit_run", spy)
    monkeypatch.setattr(
        adapters_module.ExecutionAdapter, "_roles", staticmethod(lambda _s, _u: frozenset({"expert"}))
    )
    app = build_application(environ=_env())
    assert set(built) == {"runs", "execution", "sections"}
    return app, built


def _registry_table() -> dict[str, tuple[str, str]]:
    return dict(load_text_profile_registry().section_profiles())


def test_start_run_passes_the_section_table_and_no_profile(served: Any) -> None:
    _, built = served
    with pytest.raises(_Captured) as seen:
        built["runs"].start_run(
            version_uid="ver_00000000000000000000000000", idempotency_key="route-probe-start"
        )
    kwargs = seen.value.kwargs
    assert "analysis_profile_id" not in kwargs and "prompt_bundle_id" not in kwargs
    assert dict(kwargs["section_profiles"]) == _registry_table()
    # `PB-PROFILE-01`: fire safety has a draft profile of its own, so the table covers all fifteen
    # sections and PB's pair is its own, not another section's.
    assert set(kwargs["section_profiles"]) == SECTION_CODES
    pb_entry = load_text_profile_registry().entries["PB"]
    pb = tuple(kwargs["section_profiles"]["PB"])
    assert pb == (pb_entry.analysis_profile_id, pb_entry.prompt_bundle_id)
    assert all(
        tuple(pair) != pb for code, pair in kwargs["section_profiles"].items() if code != "PB"
    )


def test_reaudit_passes_the_section_table_and_no_profile(served: Any) -> None:
    _, built = served
    with pytest.raises(_Captured) as seen:
        built["execution"].reaudit_run(
            run_id="run_00000000000000000000000000",
            user_uid="usr_00000000000000000000000000",
            idempotency_key="route-probe-reaudit",
        )
    kwargs = seen.value.kwargs
    assert "analysis_profile_id" not in kwargs and "prompt_bundle_id" not in kwargs
    assert dict(kwargs["section_profiles"]) == _registry_table()


def test_the_executor_and_the_section_port_get_the_registry(served: Any) -> None:
    _, built = served
    resolve = built["runs"].text_profiles
    assert isinstance(getattr(resolve, "__self__", None), TextProfileRegistry)
    assert resolve.__func__ is TextProfileRegistry.resolve
    assert built["sections"]._executable == load_text_profile_registry().executable_sections()
    assert "PB" in built["sections"]._executable, "PB-PROFILE-01: fire safety is executable"


def test_the_worker_runs_claimed_runs_with_the_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def run_to_terminal_spy(*args: Any, **kwargs: Any) -> None:
        seen.update(kwargs)

    monkeypatch.setattr(composition_module, "run_to_terminal", run_to_terminal_spy)
    runtime = build_worker_runtime(environ=_worker_env())
    try:
        runtime.execute("run_00000000000000000000000000", "wrk_00000000000000000000000000")
    finally:
        runtime.engine.dispose()
    assert isinstance(getattr(seen.get("text_profiles"), "__self__", None), TextProfileRegistry)


def test_a_refused_package_stops_the_start(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: Any, **_kwargs: Any) -> Any:
        raise TextProfileLoadError("section_code_duplicate: KJ")

    monkeypatch.setattr(registry_module, "load_text_profile_registry", refuse)
    with pytest.raises(ConfigurationError, match="section_code_duplicate"):
        build_application(environ=_env())
    with pytest.raises(ConfigurationError, match="section_code_duplicate"):
        build_worker_runtime(environ=_worker_env())
