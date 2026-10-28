"""The parts coverage of a sheet split across versions (`CMP-SERIES-01`; the original's ``_parts_phase``).

Pure: no database, no clock.

The original (``jobs.py:875-926`` at ``23f379fd``) groups the pairs of a transition by the older page, and for a ``split``
group takes the area of each part in the older sheet from its result (``part.area_a_pt``, only when the registration is
reliable, ``jobs.py:897-901``), marks the 36 dpi ink mask of the older sheet outside its service zones, and reports the
share of that ink that falls inside the union of the areas (``jobs.py:905-915``); an unreliable registration of any part
gives no coverage and a note (``jobs.py:902-904``).

Here the engine has already measured, for each part, the share of the older sheet's ink inside the part's area
(``coverage_a``, ``CMP-ENGINE-01`` report section 4.2 item 9) and the matrix gives the text coverage of the group
(``split.covered_percent``). The union of the ink shares is their sum when the areas do not overlap. When any part has no
reliable area, or two areas overlap (one registration is then wrong: the parts of one sheet do not overlap), the ink figure
does not exist and the text coverage stands alone, marked unreliable (the contract's number is required; the mark is the
series' own and says the number is the weaker one).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

__all__ = ["PartFact", "areas_overlap", "group_coverage"]

#: Two parts whose areas overlap by more than this share of the smaller one are overlapping (a hair of padding at a cut is not).
OVERLAP_SHARE: Final[float] = 0.02


@dataclass(frozen=True, slots=True)
class PartFact:
    """What the engine's result says of one part: ``area_a_pt`` is ``[x0, y0, x1, y1]`` in the older sheet's points."""

    area_a_pt: Sequence[float] | None
    coverage_a: float | None
    reliable: bool


def _area(rect: Sequence[float]) -> float:
    return max(0.0, rect[2] - rect[0]) * max(0.0, rect[3] - rect[1])


def areas_overlap(a: Sequence[float], b: Sequence[float]) -> bool:
    inter = _area([max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])])
    smaller = min(_area(a), _area(b))
    return smaller > 0 and inter > OVERLAP_SHARE * smaller


def group_coverage(text_percent: float, parts: Sequence[PartFact]) -> tuple[float, bool]:
    """``(covered_percent, reliable)`` of one split group.

    ``reliable`` is true when every part has a reliable registration and an area and a measured ink share; then the
    figure is the ink coverage (capped by the text coverage when two areas overlap). Otherwise it is the text coverage and
    ``reliable`` is false. The figure is a percentage with two decimals, never above 100."""
    text_percent = max(0.0, min(100.0, float(text_percent)))
    if not parts or any(not p.reliable or p.area_a_pt is None or p.coverage_a is None for p in parts):
        return round(text_percent, 2), False
    ink = 100.0 * sum(float(p.coverage_a) for p in parts if p.coverage_a is not None)
    rects = [p.area_a_pt for p in parts if p.area_a_pt is not None]
    if any(areas_overlap(rects[i], rects[j]) for i in range(len(rects)) for j in range(i + 1, len(rects))):
        # Parts of one sheet do not overlap: where two areas do, one registration is wrong (the sum would count the overlap
        # twice and the areas cannot be trusted), so the ink figure is not offered and the text coverage stands alone.
        return round(text_percent, 2), False
    return round(max(0.0, min(100.0, ink)), 2), True
