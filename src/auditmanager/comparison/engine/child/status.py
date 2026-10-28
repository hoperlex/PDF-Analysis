"""The channels and the status of a pair (port of ``status.py`` of the original, plan section 6).

`CMP-ENGINE-01`. «Совпадает» (``same``) is given only if **every applicable channel is ``checked``**; a channel the
engine did not compute or could not compute is ``unchecked`` with its reason, never ``not_applicable``. The sets are
the original's (``status.py:216-224``) with one deliberate difference, below.

**The one difference from the original.** The original counts the ``annotations`` channel with the service channels
(``status.py:218``), so a sheet whose only change is a PDF annotation is «Совпадает, изменены служебные зоны». ADR-0025
decision 15 and plan R3-09 say that an annotation-only change gives ``different`` in ``annotations``, and the answer
key of the synthetic corpus (V1 to V2, sheet E05) says the same; so here ``annotations`` is a main channel.
"""

from __future__ import annotations

from typing import Any, Final

__all__ = [
    "CHANNELS",
    "FORCING_REASONS",
    "MAIN_CHANNELS",
    "ORIGINAL_FORCING_REASONS",
    "OWN_FORCING_REASONS",
    "SERVICE_CHANNELS",
    "STATUSES",
    "checked",
    "decide",
    "not_applicable",
    "unchecked",
]

#: ``status.py:216``: the eight channels, in the order the contract lists them.
CHANNELS: Final[tuple[str, ...]] = (
    "geometry", "color", "text", "text_coverage", "zones", "annotations", "warnings", "spec_positions",
)
#: ``status.py:217`` plus ``annotations`` (see the module note).
MAIN_CHANNELS: Final[tuple[str, ...]] = ("geometry", "color", "text", "annotations")
#: ``status.py:218`` without ``annotations``.
SERVICE_CHANNELS: Final[tuple[str, ...]] = ("zones", "warnings")

#: ``status.py:221-225``: reasons that make the result «Нужна проверка» whatever the number of differences.
ORIGINAL_FORCING_REASONS: Final[frozenset[str]] = frozenset({
    "MATCH_LOW_CONFIDENCE", "MATCH_AMBIGUOUS", "MATCH_UNRESOLVED", "ALIGNMENT_UNRELIABLE", "ALIGNMENT_PARTIAL",
    "PARTIAL_COVERAGE", "DUPLICATE_SHEET", "RENDER_FAILED", "NO_TEXT_LAYER", "TEXT_UNREADABLE_IN_DIFF_AREA",
    "STAMP_NOT_RECOGNIZED", "SPEC_NOT_PARSED",
})
#: What this product adds because it caps the raster (ADR-0025 decision 9) and checks the frame of a profile
#: (``CMP-PROFILE-01``): a page that could not be read is never compared as if it had been.
OWN_FORCING_REASONS: Final[frozenset[str]] = frozenset({"PAGE_TOO_LARGE", "FRAME_MISMATCH"})
FORCING_REASONS: Final[frozenset[str]] = ORIGINAL_FORCING_REASONS | OWN_FORCING_REASONS

#: The statuses a stored result may have (the CHECK of ``comparison_sheet_pair_result``); ``added``, ``removed`` and
#: ``unmatched`` belong to a sheet pair of a transition and have no result.
STATUSES: Final[tuple[str, ...]] = ("same", "same_zones_changed", "different", "needs_review")

_REASON_MAX: Final[int] = 128


def _clip(text: str) -> str:
    text = " ".join(str(text).split()) or "-"
    return text if len(text) <= _REASON_MAX else text[: _REASON_MAX - 1] + "…"


def checked(diffs: int = 0) -> dict[str, Any]:
    """The channel was looked at and found ``diffs`` differences (``status.py:238``)."""
    return {"state": "checked", "diffs": int(diffs)}


def unchecked(reason: str) -> dict[str, Any]:
    """The channel could not be looked at, and why (``status.py:242``)."""
    return {"state": "unchecked", "reason": _clip(reason)}


def not_applicable(reason: str) -> dict[str, Any]:
    """The channel has nothing to look at on this pair (``status.py:246``)."""
    return {"state": "not_applicable", "reason": _clip(reason)}


def decide(channels: dict[str, dict[str, Any]], reasons: list[str]) -> tuple[str, list[str]]:
    """The status and the reasons from the channels and the forcing reasons (``status.py:250-271``).

    A channel nobody computed is ``unchecked`` (a defence against a forgotten channel, ``:254``). The order of the
    rules is the original's: a forcing reason; a difference in a main channel; an unchecked channel; a difference in
    a service channel; else the same.
    """
    for name in CHANNELS:
        if name not in channels:
            channels[name] = unchecked("канал не вычислен")
    kept = list(dict.fromkeys(reasons))
    unchecked_names = [name for name in CHANNELS if channels[name]["state"] == "unchecked"]
    for name in unchecked_names:
        kept.append(f"UNCHECKED_CHANNEL:{name}")
    main_diffs = sum(int(channels[n].get("diffs", 0)) for n in MAIN_CHANNELS if channels[n]["state"] == "checked")
    service_diffs = sum(int(channels[n].get("diffs", 0)) for n in SERVICE_CHANNELS if channels[n]["state"] == "checked")
    if any(reason.split(":")[0] in FORCING_REASONS for reason in kept):
        return "needs_review", kept
    if main_diffs > 0:
        return "different", kept
    if unchecked_names:
        return "needs_review", kept
    if service_diffs > 0:
        return "same_zones_changed", kept
    return "same", kept
