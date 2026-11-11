"""`D-684`: the comparison loop's pause read holds while the vectors' night window is open, as the analysis pause holds (`ADR-0029` decision 8).

``default_gates().paused`` is what ``ComparisonWorkRunner.claim`` asks first; the two reads behind it are replaced by recorded answers, so each
combination is shown on its own and the check can fail: a gate that read only the analysis pause (the defect) fails the two window rows, and one
that held on the window alone fails the pause row. The same rows against PostgreSQL, through the runner, are in
``tests/integration/comparison/work/test_claim_gates.py``.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from auditmanager.comparison.work.gates import default_gates


def _gates_with(monkeypatch: pytest.MonkeyPatch, *, analysis_paused: bool, window_is_open: bool) -> tuple[object, list[str]]:
    log: list[str] = []

    class FakeExecution:
        def dispatch_status(self, session: object) -> SimpleNamespace:
            log.append("analysis pause")
            return SimpleNamespace(paused=analysis_paused)

    def fake_window_open(session: object) -> bool:
        log.append("vector window")
        return window_is_open

    monkeypatch.setattr("auditmanager.execution.public.ExecutionRepository", FakeExecution)
    monkeypatch.setattr("auditmanager.precedents.public.window_open", fake_window_open)
    return default_gates(), log


@pytest.mark.parametrize(
    ("analysis_paused", "window_is_open", "expected"),
    [
        (False, False, False),   # nothing holds: the comparison loop claims as it did
        (True, False, True),     # the analysis pause, as before
        (False, True, True),     # the night window is open (draining or encoding): no new attempt
        (True, True, True),
    ],
)
def test_either_hold_stops_a_new_claim_and_neither_stops_nothing(
    monkeypatch: pytest.MonkeyPatch, analysis_paused: bool, window_is_open: bool, expected: bool
) -> None:
    gates, _log = _gates_with(monkeypatch, analysis_paused=analysis_paused, window_is_open=window_is_open)
    assert gates.paused(object()) is expected  # type: ignore[attr-defined]


def test_the_window_is_not_read_when_the_analysis_pause_already_holds(monkeypatch: pytest.MonkeyPatch) -> None:
    gates, log = _gates_with(monkeypatch, analysis_paused=True, window_is_open=False)
    assert gates.paused(object()) is True  # type: ignore[attr-defined]
    assert log == ["analysis pause"]
    gates, log = _gates_with(monkeypatch, analysis_paused=False, window_is_open=False)
    assert gates.paused(object()) is False  # type: ignore[attr-defined]
    assert log == ["analysis pause", "vector window"], "one read of each when nothing holds"
