"""The sheet pairs of each adjacent transition, read from the effective matrix: what ``CMP-SERIES-01`` compares.

`CMP-MATRIX-01`. A series compares every pair of *adjacent* versions in the confirmed order; for one transition the
sheet pairs are the rows of the effective matrix read at two neighbouring columns. A pair is the older page and the
newer page of one row (either may be absent), with how they were linked and what the matrix knows about them:

``relation``
    ``matched`` -- both cells hold a page; ``added`` -- only the newer holds one and the older is ``absent``;
    ``removed`` -- only the older holds one and the newer is ``absent``; ``unmatched`` -- one holds a page and the
    other is an ``unmatched`` cell (needs an expert; ``candidates`` are the matrix's, for information). A row with
    nothing at both columns gives no pair. The order of pairs is the order of the rows.
``confidence``
    the newer cell's (the link between a version and the one before it is stored on the later cell): ``high``,
    ``medium``, ``group``, ``manual`` or ``ai``; ``None`` for a pair with only one page.
``ai_dependent``
    either cell is an accepted AI link: the series marks such a transition's verdict (ADR-0025 decision 3).
``split``
    set when the older page is a sheet split across the two versions, or the newer is one of its parts: the kind
    (``floors`` or ``split``), the role of the newer page, the older sheet, its parts and the percentage of the
    older sheet's text the parts cover together. The area coverage of a registered pair is the series' own; this
    is the figure the profiles give.

A duplicate copy of a page inside a version never makes a pair of its own: it stands in the cell of its primary.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from auditmanager.comparison.matrix.effective import EffectiveMatrix
from auditmanager.comparison.matrix.model import BuildRecord, PageRef

__all__ = [
    "AdjacentSheetPairs",
    "SheetPairSpec",
    "SplitSpec",
    "TransitionPairs",
    "adjacent_pairs",
]

_FLAG_ORDER = ("split", "duplicate", "scan", "bridge")


@dataclass(frozen=True, slots=True)
class SplitSpec:
    kind: str
    role: str
    source: PageRef
    parts: tuple[PageRef, ...]
    covered_percent: float


@dataclass(frozen=True, slots=True)
class SheetPairSpec:
    row_id: str
    page_a: PageRef | None
    page_b: PageRef | None
    relation: str
    confidence: str | None
    flags: tuple[str, ...]
    ai_dependent: bool
    edit_ids: tuple[str, ...]
    ai_link_ids: tuple[str, ...]
    candidates: tuple[PageRef, ...]
    split: SplitSpec | None


@dataclass(frozen=True, slots=True)
class TransitionPairs:
    source_version_uid: str
    target_version_uid: str
    pairs: tuple[SheetPairSpec, ...]


@dataclass(frozen=True, slots=True)
class AdjacentSheetPairs:
    """The pairs of every adjacent transition of one revision of the effective matrix."""

    matrix_id: str
    edit_no: int
    order_id: str | None
    order: tuple[str, ...]
    transitions: tuple[TransitionPairs, ...]


def _ref(raw: dict[str, Any]) -> PageRef:
    return PageRef(raw["version_uid"], raw["page_number"], raw.get("page_profile_id"))


def _splits(build: BuildRecord) -> dict[tuple[str, str], list[dict[str, Any]]]:
    out: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in build.summary.get("splits", ()):
        out.setdefault((item["a_version_uid"], item["b_version_uid"]), []).append(item)
    return out


def adjacent_pairs(
    build: BuildRecord, effective: EffectiveMatrix, *, edit_no: int, order: Sequence[str] | None = None
) -> AdjacentSheetPairs:
    """The sheet pairs of each adjacent transition of ``effective``, in the order of the build."""
    columns = list(order) if order is not None else [c["version_uid"] for c in effective.columns]
    splits = _splits(build)
    transitions: list[TransitionPairs] = []
    for a_version, b_version in zip(columns, columns[1:]):
        by_source: dict[tuple[str, int], dict[str, Any]] = {}
        by_part: dict[tuple[str, int], dict[str, Any]] = {}
        for item in splits.get((a_version, b_version), ()):
            by_source[(item["a"]["version_uid"], item["a"]["page_number"])] = item
            for part in item["parts"]:
                by_part[(part["version_uid"], part["page_number"])] = item
        pairs: list[SheetPairSpec] = []
        for row in effective.rows:
            cells = {c["version_uid"]: c for c in row["cells"]}
            a, b = cells.get(a_version), cells.get(b_version)
            if a is None or b is None:
                continue
            a_matched, b_matched = a["state"] == "matched", b["state"] == "matched"
            if not a_matched and not b_matched:
                continue
            if a_matched and b_matched:
                relation = "matched"
            elif a_matched:
                relation = "removed" if b["state"] == "absent" else "unmatched"
            else:
                relation = "added" if a["state"] == "absent" else "unmatched"
            page_a = _ref(a["page"]) if a_matched else None
            page_b = _ref(b["page"]) if b_matched else None
            held = [c for c in (a, b) if c["state"] == "matched"]
            flags = {f for c in held for f in c.get("flags", ())}
            ai_links = tuple(c["ai_link_id"] for c in held if c.get("ai_link_id"))
            edit_ids = tuple(c["edit_id"] for c in (a, b) if c.get("edit_id"))
            hole = b if not b_matched else a if not a_matched else None
            candidates = tuple(_ref(c["page"]) for c in (hole or {}).get("candidates", ()))
            item = None
            if page_a is not None and page_a.key in by_source:
                item = by_source[page_a.key]
            elif page_b is not None and page_b.key in by_part:
                item = by_part[page_b.key]
            split = None
            if item is not None:
                split = SplitSpec(
                    kind=item["kind"],
                    role=item["role"],
                    source=_ref(item["a"]),
                    parts=tuple(_ref(p) for p in item["parts"]),
                    covered_percent=float(item["covered_percent"]),
                )
                flags.add("split")
            pairs.append(
                SheetPairSpec(
                    row_id=row["row_id"],
                    page_a=page_a,
                    page_b=page_b,
                    relation=relation,
                    confidence=b.get("confidence") if relation == "matched" else None,
                    flags=tuple(f for f in _FLAG_ORDER if f in flags),
                    ai_dependent=bool(ai_links),
                    edit_ids=edit_ids,
                    ai_link_ids=ai_links,
                    candidates=candidates,
                    split=split,
                )
            )
        transitions.append(TransitionPairs(a_version, b_version, tuple(pairs)))
    return AdjacentSheetPairs(
        matrix_id=build.matrix_id,
        edit_no=edit_no,
        order_id=build.order_id,
        order=tuple(columns),
        transitions=tuple(transitions),
    )
