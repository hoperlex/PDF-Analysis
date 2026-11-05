"""`EXEC2-FOLLOWUP-01` item 5 (ADR-0026 decision 17): ``python -m auditmanager.executors import-env`` while the routing mode is
``rules``.

Under ``rules`` ``setExecutorRoute`` is refused, and ``import-env`` used to create the connection and then fail on its route step.
It now imports the connection, skips the route step and says so -- in the report (``ImportReport.routing_mode``) and on stderr
(``RULES_NOTICE``) -- while ``legacy`` is unchanged.

No database: the commands, the probe runner and the routing-mode read are stand-ins that record what they were asked, so each
guard is an assertion that would fail without it:

* under ``rules`` the route is **never written** (the stand-in refuses to be called) and the connection is still made;
* under ``legacy`` the route is written once, to ``text_analysis``, and committed;
* a cut-over that lands between the read of the mode and the write of the route (the route's own refusal) is the same fact said the
  same way: the session is rolled back, nothing is re-raised -- and any *other* refusal still propagates;
* the command line prints the notice on stderr under ``rules`` and only then, and its exit code is ``0`` for a finished import and
  ``3`` for a probe that did not pass.

The same flows over real rows are ``tests/integration/executors/test_http_operations.py``.

Written and **not run** in EXEC-2 (`R-149d`).
"""

from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.executors import __main__ as cli
from auditmanager.executors import operations
from auditmanager.executors.groups import ModeState
from auditmanager.executors.operations import ImportReport
from auditmanager.shared.errors import DomainError, ErrorCode

ENVIRON = {
    "PROXY_LLM_BASE_URL": "https://gateway.example/v1", "PROXY_LLM_TOKEN": "sk-test-0000000000",
    "PROXY_LLM_MODEL": "anthropic/claude-opus-5",
}
NEW = "exc_01NEWCONNECTION"


class FakeSession:
    """The session of the route step: it records its own commits and rollbacks."""

    def __init__(self) -> None:
        self.log: list[str] = []

    def commit(self) -> None:
        self.log.append("commit")

    def rollback(self) -> None:
        self.log.append("rollback")


class Store:
    """An ``ExecutorRepository`` with no connections yet, whose probe has finished with ``outcome``."""

    def __init__(self, outcome: str) -> None:
        self.outcome = outcome

    def list_connections(self, session: Any) -> list[Any]:
        return []

    def current_routes(self, session: Any) -> list[Any]:
        return []

    def get_probe(self, session: Any, probe_id: str) -> Any:
        return SimpleNamespace(outcome=self.outcome)


class World:
    """The commands ``import_env`` calls, replaced by stand-ins; ``routes`` is every route that was written."""

    def __init__(
        self, monkeypatch: pytest.MonkeyPatch, *, mode: str, outcome: str = "ok", route_error: BaseException | None = None,
    ) -> None:
        self.session = FakeSession()
        self.store = Store(outcome)
        self.routes: list[dict[str, Any]] = []
        self.route_error = route_error
        monkeypatch.setattr(operations, "create_connection", lambda session, **kw: SimpleNamespace(connection_id=NEW))
        monkeypatch.setattr(operations, "revise_connection", lambda session, **kw: None)
        monkeypatch.setattr(operations, "set_secret", lambda session, **kw: None)
        monkeypatch.setattr(operations, "request_probe", lambda session, **kw: SimpleNamespace(probe_id="prb_01"))
        monkeypatch.setattr(operations, "routing_mode", lambda session, *a, **kw: ModeState(mode=mode))
        monkeypatch.setattr(operations, "set_route", self._set_route)
        monkeypatch.setattr(operations, "ProbeRunner", lambda *a, **kw: SimpleNamespace(run_pending=lambda: 1))

    def _set_route(self, session: Any, **kw: Any) -> None:
        self.routes.append(kw)
        if self.route_error is not None:
            raise self.route_error

    @property
    def route_log(self) -> list[str]:
        """What the route step did to the session. One ``FakeSession`` serves every block of ``import_env``, and the create block commits
        (``log[0]``), so the route step's own commits and rollbacks are what follows it."""
        assert self.session.log[:1] == ["commit"], "the create block commits before anything else"
        return self.session.log[1:]

    def run(self) -> ImportReport:
        ring = SimpleNamespace(public_ring=lambda: object())
        return operations.import_env(
            lambda: nullcontext(self.session), ENVIRON, ring=ring, policy=object(), repository=self.store,  # type: ignore[arg-type]
        )


def rules_refusal() -> DomainError:
    """What ``set_route`` raises when a cut-over has landed (``routing_mode.ensure_legacy_routing``)."""
    return DomainError(
        ErrorCode.CONFLICT, message="the routing mode is not in a state that allows this",
        conflict_reason="routing_mode_rules", aggregate_type="ExecutorRouteEvent",
    )


# --- import_env -----------------------------------------------------------------------------------------------------------------


def test_under_rules_the_connection_is_imported_and_no_route_is_written(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, mode="rules")
    report = world.run()
    assert (report.connection_id, report.created, report.probe_outcome) == (NEW, True, "ok")
    assert report.routed is False and report.routing_mode == "rules"
    assert world.routes == [], "the legacy routes are read-only under rules: the route step is skipped, not attempted"
    assert world.route_log == [], "and it touched the session not at all: the create block's commit is the last"


def test_under_rules_a_probe_that_did_not_pass_is_reported_with_the_mode_too(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, mode="rules", outcome="ip_refused")
    report = world.run()
    assert (report.created, report.probe_outcome, report.routed, report.routing_mode) == (True, "ip_refused", False, "rules")
    assert world.routes == []


def test_under_legacy_the_route_is_written_once_to_text_analysis_and_committed(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, mode="legacy")
    report = world.run()
    assert report.routed is True and report.routing_mode == "legacy"
    assert len(world.routes) == 1
    assert (world.routes[0]["work_kind"], world.routes[0]["primary_connection_id"]) == ("text_analysis", NEW)
    assert world.routes[0]["standby_connection_id"] is None
    assert world.route_log == ["commit"], "the route is committed by the route step, after the create block committed the connection"


def test_under_legacy_a_probe_that_did_not_pass_is_not_routed(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, mode="legacy", outcome="ip_refused")
    report = world.run()
    assert (report.created, report.probe_outcome, report.routed, report.routing_mode) == (True, "ip_refused", False, "legacy")
    assert world.routes == []


def test_a_cut_over_between_the_read_of_the_mode_and_the_route_is_reported_like_the_mode_and_does_not_end_the_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = World(monkeypatch, mode="legacy", route_error=rules_refusal())
    report = world.run()
    assert report.routed is False and report.routing_mode == "rules" and report.created is True
    assert len(world.routes) == 1, "the route was attempted once, and refused before it wrote anything"
    assert world.route_log == ["rollback"], "the refused route's transaction is released, and nothing is committed by the route step"


def test_any_other_refusal_of_the_route_still_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    other = DomainError(ErrorCode.NOT_FOUND, aggregate_type="ExecutorConnection")
    world = World(monkeypatch, mode="legacy", route_error=other)
    with pytest.raises(DomainError) as refused:
        world.run()
    assert refused.value is other and world.route_log == [], "the route step committed and released nothing"


def test_a_repeat_names_the_existing_connection_and_has_no_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(monkeypatch, mode="rules")
    existing = SimpleNamespace(connection_id="exc_01EXISTING", display_name=operations.IMPORT_DISPLAY_NAME, archived_at=None)
    world.store.list_connections = lambda session: [existing]  # type: ignore[method-assign]
    report = world.run()
    assert (report.connection_id, report.created, report.routing_mode) == ("exc_01EXISTING", False, None)
    assert world.routes == []


# --- the command line ----------------------------------------------------------------------------------------------------------


def command_line(monkeypatch: pytest.MonkeyPatch, report: ImportReport) -> int:
    monkeypatch.setattr(cli, "_session_factory", lambda environ: object())
    monkeypatch.setattr(cli, "_ring", lambda environ: object())
    monkeypatch.setattr(cli, "import_env", lambda *a, **kw: report)
    return cli.run(["import-env"], {})


def test_under_rules_the_command_says_on_stderr_that_the_mode_is_rules_no_route_was_set_and_a_group_and_rule_are_needed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    code = command_line(monkeypatch, ImportReport(NEW, True, "ok", False, "rules"))
    captured = capsys.readouterr()
    assert code == 0, "a finished import: the route step is skipped by design"
    assert captured.err.strip() == cli.RULES_NOTICE
    for word in ("routing mode is rules", "no route was set", "group", "rule"):
        assert word in cli.RULES_NOTICE, word
    assert "NOT routed" in captured.out and NEW in captured.out
    assert NEW not in captured.err, "the notice carries words only"


def test_under_rules_a_probe_that_did_not_pass_still_exits_three_with_the_notice(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    code = command_line(monkeypatch, ImportReport(NEW, True, "ip_refused", False, "rules"))
    assert code == 3 and capsys.readouterr().err.strip() == cli.RULES_NOTICE


def test_under_legacy_nothing_is_said_on_stderr_and_the_exit_codes_are_unchanged(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    assert command_line(monkeypatch, ImportReport(NEW, True, "ok", True, "legacy")) == 0
    first = capsys.readouterr()
    assert first.err == "" and "routed to text_analysis" in first.out
    assert command_line(monkeypatch, ImportReport(NEW, True, "ip_refused", False, "legacy")) == 3
    second = capsys.readouterr()
    assert second.err == "" and "NOT routed" in second.out


def test_a_repeat_prints_nothing_on_stderr_whatever_the_mode(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    code = command_line(monkeypatch, ImportReport(NEW, False, None, False))
    captured = capsys.readouterr()
    assert code == 0 and captured.err == "" and "nothing changed" in captured.out
