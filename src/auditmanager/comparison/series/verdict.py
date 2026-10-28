"""The counts and the deterministic verdict of a transition (`CMP-SERIES-01`; ADR-0025 decision 3).

Pure: no database, no clock. The original's ``series.summary`` (``series.py:38-64`` at ``23f379fd``) builds the counts of
a transition from its run's items and a list of Russian sentences; here the sentences are the client's and the verdict is
a list of codes (:data:`~.model.VERDICT_ORDER`) beside the counts of ``summary``.

Mapping, with the original's line:

=========================  =====================================================  =================================
code                       original's sentence                                    rule
=========================  =====================================================  =================================
``incomplete``             «переход досчитан не полностью» (``series.py:51-52``)  some pair has no result (queued,
                                                                                  computing or failed)
``content_same``           «основное содержание совпадает» (``:53-54``)           nothing differs, needs a review,
                                                                                  was added or removed or failed
                                                                                  **and** the transition is complete
``zones_only``             «…, изменены только служебные зоны» (``:54``)          with ``content_same``, at least one
                                                                                  sheet changed only in its zones
``different``              «есть отличия на N л.» (``:55-56``)                    ``different`` > 0
``composition_changed``    «изменён состав (+A / −R л.)» (``:57-58``)             ``added`` or ``removed`` > 0
``needs_review``           «нужна проверка: N» (``:59-60``)                       ``needs_review`` (with the
                                                                                  unmatched) > 0
``calculation_failed``     «ошибка расчёта: N» (``:61-62``)                       ``failed`` > 0
=========================  =====================================================  =================================

The one rule that is stricter than the original's: ``content_same`` is **never** said while a pair has not finished or has
failed. The original counted a failed item and so withheld the sentence, but a pair still queued was counted nowhere and
the sentence stood; a transition that was only half compared must not read «Совпадает».
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from auditmanager.comparison.series.model import (
    PAIR_DONE,
    PAIR_FAILED,
    VERDICT_CALCULATION_FAILED,
    VERDICT_COMPOSITION_CHANGED,
    VERDICT_CONTENT_SAME,
    VERDICT_DIFFERENT,
    VERDICT_INCOMPLETE,
    VERDICT_NEEDS_REVIEW,
    VERDICT_ZONES_ONLY,
)

__all__ = ["PairFacts", "summarize", "transition_verdict", "verdict_codes"]


@dataclass(frozen=True, slots=True)
class PairFacts:
    """What the verdict reads of one sheet pair."""

    state: str
    status: str | None
    both_pages: bool
    ai_dependent: bool = False
    #: A ``different`` sheet whose only differences are line style (``series.py:48-49``).
    style_only: bool = False


def summarize(pairs: Iterable[PairFacts]) -> dict[str, int]:
    """The counts of ``ComparisonTransitionSummary`` (``ai_dependent`` included, always present)."""
    rows = list(pairs)
    done = [p for p in rows if p.state == PAIR_DONE]

    def count(status: str) -> int:
        return sum(1 for p in done if p.status == status)

    return {
        "sheets": len(rows),
        "compared": sum(1 for p in rows if p.both_pages),
        "same": count("same"),
        "zones_only": count("same_zones_changed"),
        "different": count("different"),
        "style_only": sum(1 for p in done if p.status == "different" and p.style_only),
        "needs_review": count("needs_review") + count("unmatched"),
        "added": count("added"),
        "removed": count("removed"),
        "failed": sum(1 for p in rows if p.state == PAIR_FAILED),
        "ai_dependent": sum(1 for p in rows if p.ai_dependent),
    }


def verdict_codes(summary: dict[str, Any], *, pairs_total: int, pairs_done: int) -> list[str]:
    """The verdict of a transition from its counts. ``pairs_done`` of ``pairs_total`` have a result."""
    incomplete = pairs_total == 0 or pairs_done < pairs_total
    different, review = summary["different"], summary["needs_review"]
    added, removed, failed = summary["added"], summary["removed"], summary["failed"]
    codes: list[str] = []
    if incomplete:
        codes.append(VERDICT_INCOMPLETE)
    if not incomplete and not (different or review or added or removed or failed):
        codes.append(VERDICT_CONTENT_SAME)
        if summary["zones_only"]:
            codes.append(VERDICT_ZONES_ONLY)
    if different:
        codes.append(VERDICT_DIFFERENT)
    if added or removed:
        codes.append(VERDICT_COMPOSITION_CHANGED)
    if review:
        codes.append(VERDICT_NEEDS_REVIEW)
    if failed:
        codes.append(VERDICT_CALCULATION_FAILED)
    return codes


def transition_verdict(pairs: Iterable[PairFacts]) -> tuple[dict[str, int], list[str]]:
    rows = list(pairs)
    summary = summarize(rows)
    done = sum(1 for p in rows if p.state == PAIR_DONE)
    return summary, verdict_codes(summary, pairs_total=len(rows), pairs_done=done)
