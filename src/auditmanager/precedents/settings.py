"""The read of the switches of the «Прецеденты» programme (``precedent_setting_event``, migration ``0064``; plan-v5 section 3.6).

The journal is append-only: a setting's value in force is the row with the highest ``revision`` of that name, and **nothing journalled means
the switch is off**. This module only reads. The write (the administrator's switch) belongs to a later lane; nothing here inserts a row, and a
reader that finds a value it does not understand reads it as off, never as on.

The one switch the run's start reads is ``one_list``: its value is ``{"enabled": bool}`` (``ck_precedent_setting_event_switch`` keeps the
flag a boolean). A run reads it once, when it is created, and freezes the answer as ``audit_run.publication_mode``; a later change of the
switch acts on new runs only.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

#: The name of the «один список» switch in ``precedent_setting_event.setting_name``.
SETTING_ONE_LIST: Final[str] = "one_list"

_LATEST = text(
    "SELECT value FROM precedent_setting_event WHERE setting_name = :name ORDER BY revision DESC LIMIT 1"
)


def latest_setting_value(session: Session, setting_name: str) -> Mapping[str, Any] | None:
    """The value of the latest journal row of ``setting_name``, or ``None`` when nothing is journalled under that name."""
    value = session.execute(_LATEST, {"name": setting_name}).scalar_one_or_none()
    return value if isinstance(value, Mapping) else None


def one_list_enabled(session: Session) -> bool:
    """Is the «один список» switch on right now? Absent, or a flag that is not exactly ``true``, is off."""
    value = latest_setting_value(session, SETTING_ONE_LIST)
    return value is not None and value.get("enabled") is True
