"""From the adjacent sheet pairs of the effective matrix to the rows a series writes (`CMP-SERIES-01`).

Pure: no database, no clock. The input is :class:`~auditmanager.comparison.matrix.pairs.AdjacentSheetPairs`, what the
matrix lane reads for the series; the output is a :class:`~.model.SeriesPlan`.

What the original does and where (``PROOVERKA`` = ``backend/app/services/version_comparison/`` at ``23f379fd``):

* **Only neighbours are compared.** A series is the list of adjacent pairs of the order (``series.py:94-95``:
  ``zip(order, order[1:])``); a pair of versions that are not neighbours is never a transition here. The plan refuses an
  input whose transitions are not exactly the neighbours of its order (:func:`assert_adjacent`).
* **A matched pair is compared** (``jobs.py:436-460``); a sheet only in one version is ``removed`` / ``added`` when the
  other version's cell is ``absent``, and ``unmatched`` when it is a hole that needs an expert (``jobs.py:461-468``): these
  three are reported at once, never compared.
* **The forcing link reasons** (``jobs.py:449-456``): a medium or bridged link is ``MATCH_LOW_CONFIDENCE``, a group
  ``TABLE_GROUP``, an accepted AI link ``AI_MATCH``, a duplicate ``DUPLICATE_SHEET``. ``CHAIN_ONLY`` (``jobs.py:437-448``)
  belongs to a non-adjacent pair and so never arises.
* **A sheet split across versions** (``jobs.py:532-562``, ``_with_parts``): the older sheet is compared with each of its
  parts, every part pair names the older sheet as its page A, and the older sheet's own «removed» row disappears.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from auditmanager.comparison.matrix.model import PageRef
from auditmanager.comparison.matrix.pairs import AdjacentSheetPairs, SheetPairSpec, SplitSpec
from auditmanager.comparison.series.model import (
    PartRecord,
    PlannedPair,
    PlannedTransition,
    SeriesPlan,
)

__all__ = ["MAX_PARTS_LISTED", "assert_adjacent", "link_reasons", "plan_series"]

#: ``ComparisonPartsCoverage.parts`` holds at most 64 pages.
MAX_PARTS_LISTED: Final[int] = 64

_STATUS_OF_RELATION: Final[dict[str, str]] = {"added": "added", "removed": "removed", "unmatched": "unmatched"}


def link_reasons(confidence: str | None, flags: Sequence[str]) -> tuple[str, ...]:
    """The forcing link reasons of a pair, from what is stored on its row (``jobs.py:449-456``).

    The same function decides at enqueue time and, after a restart, at the time the item runs: nothing about the link
    is kept anywhere but the pair's own columns."""
    reasons: list[str] = []
    if confidence == "medium" or "bridge" in flags:
        reasons.append("MATCH_LOW_CONFIDENCE")
    if confidence == "group":
        reasons.append("TABLE_GROUP")
    if confidence == "ai":
        reasons.append("AI_MATCH")
    if "duplicate" in flags:
        reasons.append("DUPLICATE_SHEET")
    return tuple(reasons)


def assert_adjacent(order: Sequence[str], transitions: Sequence[tuple[str, str]]) -> None:
    """Refuse a list of transitions that is not exactly the neighbours of ``order``, oldest first.

    This is the guard of «non-adjacent pairs are never compared»: whatever produced the transitions, a series writes
    nothing for a pair of versions with another version between them."""
    expected = list(zip(order, order[1:]))
    if list(transitions) != expected:
        raise ValueError("a series compares only the adjacent versions of the order")


def _profile(ref: PageRef | None) -> str | None:
    if ref is None:
        return None
    if ref.page_profile_id is None:
        raise ValueError("a cell of a built matrix names its page profile")
    return ref.page_profile_id


def _part_record(split: SplitSpec, own: PageRef | None) -> PartRecord:
    others = tuple(
        ref.wire() for ref in split.parts if own is None or ref.key != own.key
    )[:MAX_PARTS_LISTED]
    return PartRecord(
        kind=split.kind,
        role=split.role,
        source_profile_id=_profile(split.source) or "",
        text_percent=round(float(split.covered_percent), 2),
        parts=others,
    )


def _plan_transition(number: int, source: str, target: str, specs: Sequence[SheetPairSpec]) -> PlannedTransition:
    part_keys: set[tuple[str, int]] = set()
    sources_with_part: set[tuple[str, int]] = set()
    for spec in specs:
        if spec.split is not None and spec.page_b is not None and spec.page_b.key in {p.key for p in spec.split.parts}:
            part_keys.add(spec.page_b.key)
            sources_with_part.add(spec.split.source.key)
    planned: list[PlannedPair] = []
    for spec in specs:
        split = spec.split
        is_part = split is not None and spec.page_b is not None and spec.page_b.key in part_keys
        if is_part:
            assert split is not None and spec.page_b is not None
            planned.append(
                PlannedPair(
                    pair_no=len(planned) + 1,
                    page_a_profile_id=_profile(split.source),
                    page_b_profile_id=_profile(spec.page_b),
                    status=None,
                    confidence=spec.confidence,
                    flags=spec.flags,
                    ai_dependent=spec.ai_dependent,
                    part=_part_record(split, spec.page_b),
                )
            )
            continue
        if (
            split is not None
            and spec.relation == "removed"
            and spec.page_a is not None
            and spec.page_a.key in sources_with_part
        ):
            continue  # the older sheet is compared with its parts (``jobs.py:543-544``)
        if spec.relation == "matched":
            planned.append(
                PlannedPair(
                    pair_no=len(planned) + 1, page_a_profile_id=_profile(spec.page_a),
                    page_b_profile_id=_profile(spec.page_b), status=None, confidence=spec.confidence,
                    flags=spec.flags, ai_dependent=spec.ai_dependent,
                )
            )
            continue
        status = _STATUS_OF_RELATION.get(spec.relation)
        if status is None:  # pragma: no cover - the matrix lane has four relations
            raise ValueError(f"unknown relation {spec.relation!r}")
        planned.append(
            PlannedPair(
                pair_no=len(planned) + 1, page_a_profile_id=_profile(spec.page_a),
                page_b_profile_id=_profile(spec.page_b), status=status, confidence=None, flags=spec.flags,
                ai_dependent=spec.ai_dependent,
            )
        )
    return PlannedTransition(number, source, target, tuple(planned))


def plan_series(pairs: AdjacentSheetPairs) -> SeriesPlan:
    """The transitions and sheet pairs a series writes for one revision of the effective matrix."""
    assert_adjacent(pairs.order, [(t.source_version_uid, t.target_version_uid) for t in pairs.transitions])
    transitions = tuple(
        _plan_transition(number, t.source_version_uid, t.target_version_uid, t.pairs)
        for number, t in enumerate(pairs.transitions, start=1)
    )
    return SeriesPlan(
        matrix_id=pairs.matrix_id, edit_no=pairs.edit_no, order_id=pairs.order_id, order=tuple(pairs.order),
        transitions=transitions,
    )
