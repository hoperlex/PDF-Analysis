"""A step the queue launched and watched finish is ``done``; only an unnecessary step is ``skipped``."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from auditmanager.comparison.queue.handler import ComparisonLaunchHandler
from auditmanager.comparison.work.model import WorkDependencies

PROJECT = "prj_00000000000000000000000001"
DOCUMENT = "doc_00000000000000000000000001"


class _Overview:
    """Answers the matrix step's state from a script, one answer per read; the last one repeats."""

    def __init__(self, *states: str) -> None:
        self._states = list(states)
        self.reads = 0

    def get_overview(self, *, project_uid: str) -> dict[str, Any]:
        self.reads += 1
        state = self._states.pop(0) if len(self._states) > 1 else self._states[0]
        return {"sets": [{"document_uid": DOCUMENT, "steps": [{"step": "matrix", "state": state}]}]}


class _Matrix:
    def __init__(self) -> None:
        self.prepared: list[str] = []

    def prepare_matrix(self, **kwargs: Any) -> None:
        self.prepared.append(kwargs["idempotency_key"])


def _handler(*states: str) -> tuple[ComparisonLaunchHandler, _Overview, _Matrix]:
    handler = ComparisonLaunchHandler(WorkDependencies(None, None, None, None))  # type: ignore[arg-type]
    overview, matrix = _Overview(*states), _Matrix()
    handler._wired = True
    handler._overview, handler._matrix = overview, matrix  # type: ignore[assignment]
    handler._roles = lambda _user: frozenset({"expert"})  # type: ignore[method-assign]
    return handler, overview, matrix


def _entry(state: str, *, restart: bool = False) -> dict[str, Any]:
    return {"comparison_launch_entry_id": "cle_00000000000000000000000001", "project_uid": PROJECT,
            "document_uid": DOCUMENT, "step": "matrix", "state": state, "restart": restart,
            "comparison_series_id": None, "actor_user_uid": "usr_00000000000000000000000001",
            "actor_label": "Expert"}


def _item() -> Any:
    return SimpleNamespace()  # the matrix step never touches the work item


def test_a_step_that_finishes_after_its_first_poll_is_done_not_skipped() -> None:
    # Launch: the step is not started, the queue starts it, the step is still running when read back.
    handler, _overview, matrix = _handler("not_started", "running")
    assert handler._deterministic(_item(), _entry("waiting")) == "working"
    assert len(matrix.prepared) == 1
    # Poll: the entry is now ``running`` and the overview reports the launched step finished.
    handler, _overview, matrix = _handler("done")
    assert handler._deterministic(_item(), _entry("running")) == "done"
    handler, _overview, matrix = _handler("attention")
    assert handler._deterministic(_item(), _entry("running")) == "done"


def test_a_poll_that_still_sees_work_in_progress_keeps_waiting() -> None:
    handler, _overview, _matrix = _handler("running")
    assert handler._deterministic(_item(), _entry("running")) == "working"


def test_a_step_that_is_already_done_when_launched_is_skipped_unless_restarted() -> None:
    handler, _overview, matrix = _handler("done")
    assert handler._deterministic(_item(), _entry("waiting")) == "skipped"
    assert matrix.prepared == []
    handler, _overview, matrix = _handler("attention")
    assert handler._deterministic(_item(), _entry("waiting")) == "skipped"
    handler, _overview, matrix = _handler("done")
    assert handler._deterministic(_item(), _entry("waiting", restart=True)) == "done"
    assert len(matrix.prepared) == 1


def test_a_step_that_does_not_apply_is_skipped_at_launch_and_at_poll() -> None:
    for state in ("waiting", "running"):
        handler, _overview, matrix = _handler("not_applicable")
        assert handler._deterministic(_item(), _entry(state)) == "skipped"
        assert matrix.prepared == []
