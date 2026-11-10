"""The switches and settings of the «Прецеденты» programme (``precedent_setting_event``, migration ``0064``; plan-v5 sections 3.1 and 3.6).

The journal is append-only: a setting's value in force is the row with the highest ``revision`` of that name, and **nothing journalled means
the switch is off**. This module names the settings, holds the one guard on the switch the run's start reads (:data:`ONE_LIST_READY`) and reads
the journal; it inserts nothing. The write, and the check of a value's shape that comes before it, is
``setting_journal.service.PrecedentSettingService``. A reader that finds a value it does not understand reads it as off, never as on.

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
SETTING_CRITIC_CONTEXT: Final[str] = "critic_context"
SETTING_SECTION_LABELS: Final[str] = "section_labels"
SETTING_STOP_WORDS: Final[str] = "stop_words"
SETTING_THRESHOLDS: Final[str] = "thresholds"
#: The night window's setting; ``vectors.window.SETTING_NAME`` is the same word (a test holds the two equal).
SETTING_VECTOR_WINDOW: Final[str] = "vector_window"

#: The six names ``ck_precedent_setting_event_setting_name`` admits, in the contract's order (``PrecedentSettingName``).
SETTING_NAMES: Final[tuple[str, ...]] = (
    SETTING_ONE_LIST, SETTING_CRITIC_CONTEXT, SETTING_SECTION_LABELS, SETTING_STOP_WORDS, SETTING_VECTOR_WINDOW, SETTING_THRESHOLDS,
)
#: The two names whose value is ``{"enabled": bool}`` (``ck_precedent_setting_event_switch``).
SWITCH_NAMES: Final[tuple[str, ...]] = (SETTING_ONE_LIST, SETTING_CRITIC_CONTEXT)
#: ``ck_precedent_setting_event_value``: an object of at most this many octets in its ``jsonb`` text.
VALUE_MAX_OCTETS: Final[int] = 16384

#: **«Один список» may not be switched on yet** (`D-683`). While the block findings of a one-list run break the 1.51.0 evidence contract, a
#: switch that sends runs down that path would publish findings the contract cannot carry; ``appendPrecedentSetting`` therefore refuses
#: ``one_list`` with ``{"enabled": true}`` (``validation_failed``, ``constraint: one_list_not_ready``). Switching it off is always allowed. The lane
#: that closes `D-683` flips this one line.
ONE_LIST_READY: bool = False

#: The ``constraint`` of the refusal of ``one_list`` with ``{"enabled": true}`` while :data:`ONE_LIST_READY` is false.
CONSTRAINT_ONE_LIST_NOT_READY: Final[str] = "one_list_not_ready"

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

