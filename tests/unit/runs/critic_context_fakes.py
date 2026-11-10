"""A stand-in session for the estimate's one read of the journal of settings (`CTX-STAND`).

``RunCostPreflight.estimate_run`` reads the «контекст критику» switch from ``precedent_setting_event`` when it prices a run on the stage layout under
plan v3. The unit tests of the estimate have no database; this answers that one statement from a dict (setting name -> the value of its latest
row), and an empty dict is a journal with nothing in it, which is every switch off.
"""

from __future__ import annotations

from typing import Any


class _Scalar:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value


class SettingsSession:
    def __init__(self, values: dict[str, dict[str, Any]] | None = None) -> None:
        self.values = values or {}
        self.asked: list[str] = []

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _Scalar:
        assert params is not None and "name" in params and "precedent_setting_event" in str(statement), "only the settings' read is answered"
        self.asked.append(params["name"])
        return _Scalar(self.values.get(params["name"]))
