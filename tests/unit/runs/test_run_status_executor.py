"""`EXEC-PAR-START-01`: a run's status says which executor it is on, and nothing else about it.

Container-free, in the manner of ``test_w55a_pin_offline.py::test_the_run_status_view_carries_the_pin``:
``RunRepository`` and the findings reads are replaced, and the executors context is asked through
its public ``executor_of_revision``, replaced here by a recorder. What is proved:

* a run that froze no connection reports no executor and the status body has **no** ``executor``
  key -- every body that existed before the field is byte-for-byte what it was;
* a run that froze a revision reports the connection's id, its display name and the pinned model
  of that revision, in exactly those three keys: no kind, no address, no key, no probe;
* the revision is the one the run froze (``run.connection_revision_id``), not the connection's
  current one;
* a revision the executors context no longer answers is no executor, not an error.
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
CONNECTION = "exc_01M2545JSD15ETSNNV904X991N"


def _view(monkeypatch: pytest.MonkeyPatch, revision: str | None, answers: dict[str, Any]) -> tuple[Any, list[str]]:
    import auditmanager.executors.public as executors_public
    import auditmanager.findings as findings
    import auditmanager.runs as runs_package
    from auditmanager.bootstrap.adapters import _run_status_view

    row = SimpleNamespace(
        run_id=RUN, project_uid=PROJECT, version_uid=VERSION, state="queued",
        provider_mode="live", created_at=datetime(2026, 10, 26, tzinfo=timezone.utc),
        analysis_profile_id=PROFILE, prompt_bundle_id=BUNDLE, degradation_set=(),
        terminal_reason=None, terminal_detail=None, interrupted_reason=None, terminal_at=None,
        reaudit_of_run_id=None, norms_snapshot_id=None, connection_revision_id=revision,
    )

    class _Repository:
        def get(self, session: Any, run_id: str) -> Any:
            return row

        def stage_results(self, session: Any, run_id: str) -> tuple[()]:
            return ()

        def cost(self, session: Any, run_id: str) -> None:
            return None

    asked: list[str] = []

    def executor_of_revision(session: Any, revision_id: str) -> Any:
        asked.append(revision_id)
        return answers.get(revision_id)

    monkeypatch.setattr(runs_package, "RunRepository", _Repository)
    monkeypatch.setattr(findings, "published_finding_count", lambda session, run_id: 0)
    monkeypatch.setattr(findings, "diagnostics", lambda session, run_id: ())
    monkeypatch.setattr(executors_public, "executor_of_revision", executor_of_revision)
    return _run_status_view(None, RUN), asked  # type: ignore[arg-type]


def _answer() -> Any:
    from auditmanager.executors.public import RunExecutor

    return RunExecutor(connection_id=CONNECTION, display_name="Сервер 1", pin_id="model-pin")


def test_a_run_that_froze_no_connection_has_no_executor_and_an_unchanged_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from auditmanager.api.schemas.runs import run_status_body

    view, asked = _view(monkeypatch, None, {})
    assert view.executor is None and asked == [], "no revision, nothing is asked"
    assert "executor" not in run_status_body(view)


def test_a_run_that_froze_a_revision_reports_its_connection_name_and_pin_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from auditmanager.api.schemas.runs import run_status_body

    view, asked = _view(monkeypatch, "exr_FROZEN", {"exr_FROZEN": _answer()})
    assert asked == ["exr_FROZEN"], "the run's own frozen revision, not the connection's current"
    assert run_status_body(view)["executor"] == {
        "connection_id": CONNECTION, "display_name": "Сервер 1", "pin_id": "model-pin",
    }


def test_a_revision_the_executors_context_cannot_answer_is_no_executor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from auditmanager.api.schemas.runs import run_status_body

    view, asked = _view(monkeypatch, "exr_GONE", {})
    assert asked == ["exr_GONE"] and view.executor is None
    assert "executor" not in run_status_body(view)
