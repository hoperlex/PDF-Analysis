"""The three similarity thresholds of `plan-v5` 2.2, applied to precomputed cosines.

There is no lexical path and no fallback: a finding with no vector gets the status "unavailable" from :mod:`auditmanager.precedents.advice`,
never a guess from words. The values are starting values, refined per section by the history replay (:mod:`auditmanager.precedents.replay`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

BAND_ANALOGOUS: Final[str] = "analogous"
BAND_SIMILAR: Final[str] = "similar"
BAND_BELOW: Final[str] = "below"

#: The profile every vector is read under (`norms/embedding/profile.py`); a vector of another profile is not comparable.
VECTOR_PROFILE: Final[str] = "bge-m3-dense-v1"


@dataclass(frozen=True, slots=True)
class Thresholds:
    """Cosine >= ``analogous``: the case votes. >= ``similar``: it may carry a comment. >= ``history`` and the same document: hint P5."""

    analogous: float = 0.85
    similar: float = 0.75
    history: float = 0.92

    def __post_init__(self) -> None:
        if not 0.0 <= self.similar <= self.analogous <= self.history <= 1.0:
            raise ValueError("thresholds must satisfy 0 <= similar <= analogous <= history <= 1")


def band(cosine: float, thresholds: Thresholds) -> str:
    """``analogous`` (votes), ``similar`` (comments only) or ``below``. Both edges are inclusive."""
    if cosine >= thresholds.analogous:
        return BAND_ANALOGOUS
    if cosine >= thresholds.similar:
        return BAND_SIMILAR
    return BAND_BELOW
