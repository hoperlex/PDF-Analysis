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

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.precedents.similarity import Thresholds
from auditmanager.precedents.stemming import StopWordMatcher, compile_stop_words


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



# -- the three settings the «Прецеденты» pass reads (`PREC-PASS`): their shapes, their parsers and their reads ------------------------------

#: The constraints a refused value of these settings names (``validation_failed``, ``field: value``): the service's own words for them.
CONSTRAINT_SECTION_LABELS_SHAPE: Final[str] = "section_labels_shape"
CONSTRAINT_STOP_WORDS_SHAPE: Final[str] = "stop_words_shape"
CONSTRAINT_THRESHOLDS_SHAPE: Final[str] = "thresholds_shape"

_SECTION_CODE: Final[re.Pattern[str]] = re.compile(r"[A-Z][A-Z0-9_]{0,15}")
_SHA256: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}")
#: A stop word is a word or a short phrase; the list is the owner's, so it is small.
MAX_STOP_WORDS: Final[int] = 200
MAX_STOP_WORD_CHARS: Final[int] = 64


@dataclass(frozen=True, slots=True)
class SectionLabelSwitch:
    """One section's entry of ``section_labels``: the administrator turned the refusal labels on from the replay report whose digest this is.

    ``analogous`` is the cosine threshold the report chose for the section (``SectionReport.analogous_threshold``): the section was admitted at that
    threshold, so the pass uses it for that section and for no other -- a rule enabled from a report that tested another rule would be the
    wrong rule. ``None`` keeps the installation's own value (``thresholds``)."""

    section: str
    report_sha256: str
    analogous: float | None = None


def section_labels_value(entries: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """The journal value of ``section_labels`` for ``entries`` (``{section: {"enabled": bool, "report_sha256": hex64, "analogous": float?}}``).

    The value is one object, the whole state: every section named is listed, whatever its switch, because the latest revision replaces the
    one before it. Returned canonical, or ``ValueError`` saying which entry is not the shape: a section code (``[A-Z][A-Z0-9_]{0,15}``); ``enabled``
    a boolean; the digest of the replay report (64 lowercase hex) **required when enabled** -- a switch with no report to point at is not a switch the
    journal may hold -- and optional otherwise; ``analogous`` a number in [0, 1]. No other member."""
    if not isinstance(entries, Mapping):
        raise ValueError("section_labels is an object of sections")
    checked: dict[str, dict[str, Any]] = {}
    for section, entry in entries.items():
        if not isinstance(section, str) or not _SECTION_CODE.fullmatch(section):
            raise ValueError(f"{section!r} is not a section code")
        if not isinstance(entry, Mapping) or not set(entry) <= {"enabled", "report_sha256", "analogous"} or not isinstance(entry.get("enabled"), bool):
            raise ValueError(f"the entry of {section} is {{enabled, report_sha256, analogous?}}")
        digest, analogous = entry.get("report_sha256"), entry.get("analogous")
        if digest is not None and not (isinstance(digest, str) and _SHA256.fullmatch(digest)):
            raise ValueError(f"the report digest of {section} is 64 lowercase hex characters")
        if entry["enabled"] and digest is None:
            raise ValueError(f"{section} is switched on with no replay report")
        if analogous is not None and not (type(analogous) in (int, float) and 0.0 <= float(analogous) <= 1.0):
            raise ValueError(f"the analogous threshold of {section} is a number from 0 to 1")
        item: dict[str, Any] = {"enabled": entry["enabled"]}
        if digest is not None:
            item["report_sha256"] = digest
        if analogous is not None:
            item["analogous"] = float(analogous)
        checked[section] = item
    return checked


def parse_section_labels(value: Mapping[str, Any] | None) -> dict[str, SectionLabelSwitch]:
    """The sections whose refusal labels are on, from a journalled value. **A value this cannot read is read as off**, entry by entry: a malformed
    entry switches nothing on, and a good one beside it stays (the write refuses a bad value, so a bad one is old, edited or foreign)."""
    on: dict[str, SectionLabelSwitch] = {}
    if not isinstance(value, Mapping):
        return on
    for section, entry in value.items():
        try:
            (item,) = section_labels_value({section: entry}).values()
        except (ValueError, TypeError):
            continue
        if item["enabled"]:
            on[section] = SectionLabelSwitch(section, item["report_sha256"], item.get("analogous"))
    return on


def stop_words_value(value: Mapping[str, Any]) -> dict[str, list[str]]:
    """The journal value of ``stop_words``: ``{"words": [word or phrase, ...]}``, canonical (trimmed, in the given order), or ``ValueError``.

    At most :data:`MAX_STOP_WORDS` entries of at most :data:`MAX_STOP_WORD_CHARS` characters, each with at least one letter or digit (a list that
    silently shrinks would show «снять» it should not: the compiler refuses a blank entry, and so does this)."""
    if not isinstance(value, Mapping) or set(value) != {"words"} or not isinstance(value["words"], list):
        raise ValueError("stop_words is {words: [...]}")
    words = value["words"]
    if len(words) > MAX_STOP_WORDS or not all(isinstance(word, str) and 1 <= len(word.strip()) <= MAX_STOP_WORD_CHARS for word in words):
        raise ValueError(f"stop_words holds at most {MAX_STOP_WORDS} words of 1 to {MAX_STOP_WORD_CHARS} characters")
    compile_stop_words(words)       # a word with no letter or digit is refused here, as the pass would refuse it
    return {"words": [word.strip() for word in words]}


def thresholds_value(value: Mapping[str, Any]) -> dict[str, float]:
    """The journal value of ``thresholds``: ``{"analogous", "similar", "history"}``, all three numbers with ``similar <= analogous <= history``."""
    if not isinstance(value, Mapping) or set(value) != {"analogous", "similar", "history"}:
        raise ValueError("thresholds is {analogous, similar, history}")
    if not all(type(item) in (int, float) for item in value.values()):
        raise ValueError("the thresholds are numbers")
    thresholds = Thresholds(analogous=float(value["analogous"]), similar=float(value["similar"]), history=float(value["history"]))
    return {"analogous": thresholds.analogous, "similar": thresholds.similar, "history": thresholds.history}


def read_stop_words(session: Session) -> StopWordMatcher:
    """The owner's stop words in force. **Nothing journalled is no stop words.** A journalled value that is not the shape the write admits is
    *not* read as an empty list: ``ValueError``, so the pass that asked fails loudly and shows nothing. A list that silently shrank would show
    a «снять» the owner had forbidden."""
    value = latest_setting_value(session, SETTING_STOP_WORDS)
    if value is None:
        return StopWordMatcher()
    return compile_stop_words(stop_words_value(value)["words"])


def read_thresholds(session: Session) -> Thresholds:
    """The installation's thresholds in force; the starting values (0,85 / 0,75 / 0,92) while nothing is journalled. A journalled value that is not
    the shape the write admits is a ``ValueError`` (the pass fails loudly), never the starting values under another name."""
    value = latest_setting_value(session, SETTING_THRESHOLDS)
    if value is None:
        return Thresholds()
    return Thresholds(**thresholds_value(value))


def read_section_labels(session: Session) -> dict[str, SectionLabelSwitch]:
    """The sections whose refusal labels are on right now. Nothing journalled: none, which is the default (every switch is off)."""
    return parse_section_labels(latest_setting_value(session, SETTING_SECTION_LABELS))


def thresholds_for(base: Thresholds, switch: SectionLabelSwitch | None) -> Thresholds:
    """The thresholds a section's labels are computed at: the installation's, with the section's tuned ``analogous`` when the section is on and has one.

    A tuned value that cannot stand beside the installation's other two (``similar <= analogous <= history``) is a value the section was not admitted
    at, so it is not used and the section is **not on** for this call: the caller asks :func:`section_is_on` first and gets ``False`` for it."""
    if switch is None or switch.analogous is None:
        return base
    return Thresholds(analogous=switch.analogous, similar=base.similar, history=base.history)


def section_is_on(base: Thresholds, switch: SectionLabelSwitch | None) -> bool:
    """Is the section's switch on **and** usable: its tuned threshold, if any, stands beside the installation's other two."""
    if switch is None:
        return False
    try:
        thresholds_for(base, switch)
    except ValueError:
        return False
    return True
