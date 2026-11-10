"""The night window of the vectors: when it is open, in which state it stands and what a run that waits for it is told (`ADR-0029` decision 8).

Pure: a clock and a setting go in, a span or a sentence comes out. Nothing here reads a database or a file.

**The setting** is ``vector_window`` of the journal ``precedent_setting_event``: ``{"start": "HH:MM", "end": "HH:MM", "tz": "<IANA zone>"}``,
read in the zone, so a stand in Yekaterinburg (+05) keeps 01:00-06:00 by the wall clock whatever the server's own zone is. Nothing journalled
means :data:`DEFAULT_WINDOW`. A window may cross midnight (``22:00`` to ``03:00``); ``start == end`` is refused (it would be no window or all
of the day, and the setting never says which).

**The states** are those of ``vector_control.window_state`` (contract 1.51.0, ``VectorWindowState``): ``closed``; ``draining`` (no new run is
issued, the running ones finish); ``encoding`` (the encoder runs); ``skipped`` (the window did not take place, with a reason code). The
transitions and who makes them are in :mod:`~auditmanager.precedents.vectors.window_pass`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any, Final
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

__all__ = [
    "DEFAULT_WINDOW", "SETTING_NAME", "STATE_CLOSED", "STATE_DRAINING", "STATE_ENCODING", "STATE_SKIPPED", "STATES", "OPEN_STATES",
    "SKIP_REASONS", "WindowSetting", "WindowSpan", "current_span", "parse_setting", "wait_text",
]

SETTING_NAME: Final[str] = "vector_window"

STATE_CLOSED: Final[str] = "closed"
STATE_DRAINING: Final[str] = "draining"
STATE_ENCODING: Final[str] = "encoding"
STATE_SKIPPED: Final[str] = "skipped"
STATES: Final[tuple[str, ...]] = (STATE_CLOSED, STATE_DRAINING, STATE_ENCODING, STATE_SKIPPED)
#: The two states in which the stand issues no new run (`jobs/repository.py`, the same query as the analysis pause).
OPEN_STATES: Final[tuple[str, ...]] = (STATE_DRAINING, STATE_ENCODING)

#: Why a window was skipped. Each is a code of ``vector_control.window_reason`` (``^[a-z][a-z0-9_]{0,63}$``): the administrator reads it in the
#: pause menu, and a skipped window is never silent (AGENTS section 4).
SKIP_REASONS: Final[frozenset[str]] = frozenset({
    "runs_did_not_finish",            # work was still running when the window ended: the encoder never started
    "window_ended_before_start",      # the window ended before the drain finished and nothing was running: the worker was away
    "host_timer_silent",              # the host's timer did not report in time: nothing would have started the encoder
    "window_ended_while_encoding",    # the encoder did not finish before the window ended; it was stopped
    "encoder_failed",                 # the container ended with an error (the exit status is in the log)
    "encoder_out_of_memory",          # the container was killed at its memory limit (exit status 137)
    "encoder_timed_out",              # the host stopped the container at the window's deadline (exit status 124)
    "encoder_image_missing",          # the host has no image to run
    "export_failed",                  # the file for the encoder could not be written
    "import_refused",                 # the encoder's answer was not one this stand accepts
    "pass_failed",                    # the worker's pass failed on several looks in a row: the stand is given back rather than held by a broken pass
})

#: ``HH:MM`` as the contract writes it (``VectorWindow``).
_CLOCK_LENGTH: Final[int] = 5


@dataclass(frozen=True, slots=True)
class WindowSetting:
    """The configured window: local ``start`` and ``end`` in the zone ``tz``."""

    start: time
    end: time
    tz: str

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.tz)

    def as_value(self) -> dict[str, str]:
        """The shape the setting and ``VectorWindow`` carry."""
        return {"start": _clock(self.start), "end": _clock(self.end), "tz": self.tz}


#: 01:00-06:00 at Yekaterinburg (+05), the owner's default (`R-153ap`, plan-v5 section 5).
DEFAULT_WINDOW: Final[WindowSetting] = WindowSetting(time(1, 0), time(6, 0), "Asia/Yekaterinburg")


def _clock(value: time) -> str:
    return f"{value.hour:02d}:{value.minute:02d}"


def _parse_clock(raw: Any, name: str) -> time:
    if not isinstance(raw, str) or len(raw) != _CLOCK_LENGTH or raw[2] != ":":
        raise ValueError(f"vector_window {name} must be HH:MM, got {raw!r}")
    hours, minutes = raw[:2], raw[3:]
    if not (hours.isdigit() and minutes.isdigit()) or int(hours) > 23 or int(minutes) > 59:
        raise ValueError(f"vector_window {name} must be HH:MM between 00:00 and 23:59, got {raw!r}")
    return time(int(hours), int(minutes))


def parse_setting(value: Mapping[str, Any]) -> WindowSetting:
    """The window a ``vector_window`` revision names. A value that is not the shape of the setting is refused, never read as the default: a
    window nobody asked for would stop the stand's runs at an hour nobody chose."""
    if set(value) != {"start", "end", "tz"}:
        raise ValueError(f"vector_window holds start, end and tz, got {sorted(value)}")
    start, end = _parse_clock(value["start"], "start"), _parse_clock(value["end"], "end")
    if start == end:
        raise ValueError("vector_window start and end are the same minute")
    zone = value["tz"]
    if not isinstance(zone, str) or not zone or len(zone) > 64:
        raise ValueError(f"vector_window tz must be an IANA zone name, got {zone!r}")
    try:
        ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        raise ValueError(f"vector_window tz {zone!r} is not a zone this stand knows") from exc
    return WindowSetting(start, end, zone)


@dataclass(frozen=True, slots=True)
class WindowSpan:
    """One occurrence of the window: ``opens_at <= moment < closes_at``, both aware."""

    opens_at: datetime
    closes_at: datetime

    def contains(self, moment: datetime) -> bool:
        return self.opens_at <= moment < self.closes_at

    def closing_clock(self, setting: WindowSetting) -> str:
        """``HH:MM`` at which it closes, on the wall clock of the window's own zone."""
        return _clock(self.closes_at.astimezone(setting.zone).time())


def _occurrence(day: datetime, setting: WindowSetting) -> WindowSpan:
    """The occurrence of the window that opens on the local date of ``day``."""
    zone = setting.zone
    opens = datetime.combine(day.date(), setting.start, tzinfo=zone)
    closes_date = day.date() if setting.end > setting.start else day.date() + timedelta(days=1)
    closes = datetime.combine(closes_date, setting.end, tzinfo=zone)
    return WindowSpan(opens, closes)


def current_span(moment: datetime, setting: WindowSetting) -> WindowSpan | None:
    """The occurrence of the window that contains ``moment``, or ``None`` when it is outside every occurrence.

    The local date is read in the window's zone; the occurrence that opened yesterday is looked at too, because a window that crosses midnight
    is still open after the date turned over. An unaware ``moment`` is refused: a guess would move the window by the server's own zone."""
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise ValueError("the moment must be timezone-aware")
    local = moment.astimezone(setting.zone)
    for offset in (0, -1):
        span = _occurrence(local + timedelta(days=offset), setting)
        if span.contains(moment):
            return span
    return None


def wait_text(span: WindowSpan, setting: WindowSetting) -> str:
    """What a run that waits for the window is told (plan-v5 section 5): «ночное окно векторов, до HH:MM»."""
    return f"ночное окно векторов, до {span.closing_clock(setting)}"
