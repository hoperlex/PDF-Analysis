"""The installation settings of the decision memory (`D-390`, `Q3c`).

Two values, kept as an append-only journal (``decision_memory_setting_event``, migration ``0061``) in the shape of the schedule's
settings: ``data_class`` says what the cases captured *now* are (``test`` or ``real``) and ``training_use`` whether the training export
may run (``off`` or ``on``). **Nothing journalled means the safe value**: ``test`` and ``off``. The capture reads ``data_class`` at every
decision; a case already captured keeps the class it was captured with (the column is immutable), so the setting is not a
reclassification of history. The application never writes a setting: the operator tool ``scripts/recovery/memory_setting.py`` does, as the
owner, naming an admin account; ``training_use = on`` names the owner's permission.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

SETTING_DATA_CLASS: Final[str] = "data_class"
SETTING_TRAINING_USE: Final[str] = "training_use"
SETTING_NAMES: Final[tuple[str, ...]] = (SETTING_DATA_CLASS, SETTING_TRAINING_USE)

#: The values each setting admits (mirrors ``ck_decision_memory_setting_event_value_for_name``) and the value in force when nothing is
#: journalled.
SETTING_VALUES: Final[dict[str, tuple[str, ...]]] = {
    SETTING_DATA_CLASS: ("test", "real"),
    SETTING_TRAINING_USE: ("off", "on"),
}
SETTING_DEFAULTS: Final[dict[str, str]] = {SETTING_DATA_CLASS: "test", SETTING_TRAINING_USE: "off"}


@dataclass(frozen=True, slots=True)
class MemorySettings:
    """The settings in force, with the revision each came from (``0``: nothing journalled, the default applies)."""

    data_class: str
    training_use: str
    data_class_revision: int = 0
    training_use_revision: int = 0

    @property
    def training_enabled(self) -> bool:
        return self.training_use == "on"
