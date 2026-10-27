"""Analysis presets: the vocabulary, the rules and the records (`ANALYSIS-PRESETS-01`, `R-146av`).

Pure: no SQL, no I/O. A *preset* is a named, saved choice of how a run is started. The premise of the
lane is that a run start selects **one** setting per run -- the executor connection
(``startRun.executor_connection_id``). The cost ceiling is a process-wide environment setting that the
meter and the input budget read once at start-up, no threshold is an input of a start, and the provider
mode must equal the deployment's own. So a preset is **a name plus an executor connection**, and
nothing else is stored because nothing else is selectable. A field joins a preset only together with a
field of the start request it fills; ``tests/contract/api_v1/test_analysis_preset_surface.py`` holds
that equality, so a later per-run limit cannot be added to one and forgotten in the other.

**Identity.** A preset is identified by ``preset_id`` for its whole life; its name is a label and never
an identity (a rename is a new revision under the same id). Both ids are ``evt_<ULID>``
(:class:`~auditmanager.shared.identity.AuditEventId`): the registry of identifier prefixes lives in the
domain contract and in ``auditmanager.shared.identity``, which this lane does not own, and
``comparison_summary.summary_id`` already has this identity (migration ``0035``). **Every revision's id
is the id of the audit event that records it**, written in the same transaction, and a preset's id is
the id of its first revision. Nothing is derived from the name or the connection.

**Revisions.** Append-only (migration ``0037``). Changing a preset appends an ``active`` revision with
the full settings, never a patch; archiving appends an ``archived`` revision that repeats the previous
name and connection; nothing follows an archive. The *current* revision of a preset is its highest
``revision_no``. A run records the exact revision it started with.

**Who.** Writing a preset is the administrator's act, as every executor write (``api/security.py``);
reading is open to every role; choosing a preset at start needs only what ``startRun`` needs.

Refusals reuse the catalogue's existing codes and detail keys (``contracts/domain/v1/error-codes.json``):
``validation_failed`` carries ``field`` and ``constraint``, ``conflict`` carries ``conflict_reason`` and
``aggregate_type``, ``not_found`` carries ``aggregate_type``. A detail never contains a name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "AGGREGATE_TYPE",
    "MAX_NAME_LENGTH",
    "MAX_PRESETS",
    "STATES",
    "ChosenPreset",
    "PresetRecord",
    "RunPresetRecord",
    "clean_name",
    "name_key",
    "not_found",
    "preset_archived",
    "preset_conflict",
]

AGGREGATE_TYPE: Final[str] = "AnalysisPreset"
STATES: Final[tuple[str, ...]] = ("active", "archived")
#: The most presets that may exist, archived ones included (an archive is not a deletion). Restated
#: by migration ``0037``; ``tests/unit/executors/test_presets.py`` holds the two equal.
MAX_PRESETS: Final[int] = 100
MAX_NAME_LENGTH: Final[int] = 120

# Control characters, line and paragraph separators and surrogates have no place in a label.
_UNPRINTABLE = re.compile(r"[\x00-\x1f\x7f-\x9f  \ud800-\udfff]")


@dataclass(frozen=True, slots=True)
class PresetRecord:
    """The current (or a stated) revision of one preset."""

    preset_id: str
    revision_id: str
    revision_no: int
    state: str
    name: str
    executor_connection_id: str
    #: When revision 1 was written, i.e. when the preset was made.
    created_at: datetime
    #: When this revision was written, and by whom.
    revised_at: datetime
    revised_by: str


@dataclass(frozen=True, slots=True)
class ChosenPreset:
    """What a run start applies: the preset's current revision, resolved in the start's own
    transaction. ``executor_connection_id`` is the one setting a start can take."""

    preset_id: str
    revision_id: str
    revision_no: int
    executor_connection_id: str


@dataclass(frozen=True, slots=True)
class RunPresetRecord:
    """The preset revision a run recorded, with the name it had then."""

    preset_id: str
    revision_no: int
    name: str


def clean_name(raw: object) -> str:
    """The name as it is stored: trimmed, 1 to 120 characters, nothing unprintable.

    The refusals are ``validation_failed`` on ``name`` with the classification-correction
    vocabulary: ``type`` (not text), ``required`` (blank after trimming), ``max_length`` and
    ``printable``. The database holds the same three bounds as CHECKs.
    """
    if not isinstance(raw, str):
        raise _invalid("type")
    name = raw.strip(" \t\r\n")
    if not name:
        raise _invalid("required")
    if _UNPRINTABLE.search(name) is not None:
        raise _invalid("printable")
    if len(name) > MAX_NAME_LENGTH:
        raise _invalid("max_length")
    return name


def name_key(name: str) -> str:
    """Two names are one name when this is equal: case is not a difference between presets."""
    return name.casefold()


def _invalid(constraint: str) -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED, message="the preset name is not acceptable",
        field="name", constraint=constraint,
    )


def not_found() -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type=AGGREGATE_TYPE)


def preset_conflict(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.CONFLICT, message="the preset is not in a state that allows this",
        conflict_reason=reason, aggregate_type=AGGREGATE_TYPE,
    )


def preset_archived() -> DomainError:
    return preset_conflict("preset_archived")
