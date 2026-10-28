"""What a series was computed from, and how a later read tells that it no longer is (`CMP-SERIES-01`).

Pure: no database, no clock. ADR-0025 decision 21 and plan ``R3-32``: staleness markers compare stored input digests,
never timestamps. ``comparison_series.input_sha256`` is the digest of the inputs the series was started on; a read
recomputes the digest of the inputs as they are now and, when it differs, names why:

``order_changed``
    the versions of the document set, in the order a build would walk them today, are not the chain of the series
    (a reorder, or a version published after it). «Сохранённая сводка для прежнего порядка версий» (the original:
    ``seriesMatchesOrder``, ``version-comparison.js:808``).
``matrix_changed``
    the latest build of the matrix, or the number of manual edit events, is not the one the series is bound to
    (a rebuild, an applied edit, an undo).
``profiles_changed``
    the page profiles of the bound build's versions are not the ones it read, or the algorithm of the pair comparison is
    another (the contract has no reason of its own for the second: the matrix lane reports the same case the same way).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

__all__ = [
    "CurrentInputs",
    "STALE_MATRIX_CHANGED",
    "STALE_ORDER_CHANGED",
    "STALE_PROFILES_CHANGED",
    "SeriesInputs",
    "input_digest",
    "stale_reasons",
]

STALE_ORDER_CHANGED: Final[str] = "order_changed"
STALE_MATRIX_CHANGED: Final[str] = "matrix_changed"
STALE_PROFILES_CHANGED: Final[str] = "profiles_changed"


@dataclass(frozen=True, slots=True)
class SeriesInputs:
    """The inputs a series is bound to."""

    chain: tuple[str, ...]
    matrix_id: str
    edit_no: int
    profile_signature: str
    engine_algo: str


@dataclass(frozen=True, slots=True)
class CurrentInputs:
    """The same facts as they are now: the order a build would walk, the latest build and its edit count, the digest of
    the page profiles of the bound build's versions, the algorithm of the pair comparison."""

    order: tuple[str, ...]
    matrix_id: str | None
    edit_no: int
    profile_signature: str
    engine_algo: str


def input_digest(inputs: SeriesInputs) -> str:
    """The stored digest: canonical JSON of the five facts, hashed (sorted keys, no whitespace)."""
    body = json.dumps(
        {
            "chain": list(inputs.chain), "edit_no": inputs.edit_no, "engine_algo": inputs.engine_algo,
            "matrix_id": inputs.matrix_id, "profile_signature": inputs.profile_signature,
        },
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def stale_reasons(
    stored_digest: str, bound: SeriesInputs, current: CurrentInputs
) -> list[str]:
    """Why the series no longer matches the present inputs (empty: it does). The digests decide; the components say why."""
    now = SeriesInputs(
        chain=current.order, matrix_id=current.matrix_id or "", edit_no=current.edit_no,
        profile_signature=current.profile_signature, engine_algo=current.engine_algo,
    )
    if input_digest(now) == stored_digest:
        return []
    reasons: list[str] = []
    if tuple(bound.chain) != tuple(current.order):
        reasons.append(STALE_ORDER_CHANGED)
    if current.matrix_id != bound.matrix_id or current.edit_no != bound.edit_no:
        reasons.append(STALE_MATRIX_CHANGED)
    if current.profile_signature != bound.profile_signature or current.engine_algo != bound.engine_algo or not reasons:
        reasons.append(STALE_PROFILES_CHANGED)
    return reasons


def chain_of(transitions: Sequence[tuple[str, str]]) -> tuple[str, ...]:
    """The versions a series walked, from its transitions in order: ``[(a, b), (b, c)]`` -> ``(a, b, c)``."""
    if not transitions:
        return ()
    return (transitions[0][0], *(t[1] for t in transitions))


__all__.append("chain_of")
