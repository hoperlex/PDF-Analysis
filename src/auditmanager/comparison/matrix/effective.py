"""The effective matrix: the algorithm, then accepted AI links, then manual edits; a manual edit wins.

`CMP-MATRIX-01` (ADR-0025 decisions 3, 13, 14, 16; plan section 3.2 ``R3-10``). The stored build
(:class:`~auditmanager.comparison.matrix.model.BuildRecord`) is raw and immutable. This module is the read model
over it, a pure function of the build, the accepted AI links and the manual edit history -- no database, no clock,
no randomness -- so the same inputs are the same bytes (:func:`canonical_json`).

Layers, in this order:

1. **The algorithm**: the stored rows.
2. **Accepted AI links** (written by wave C2, empty before). A link binds the build it answered and the state of
   the cell it answered, ``unmatched`` or ``doubtful`` (ADR-0025 decision 14). It *applies* only while that cell is
   still in that state, otherwise it is *superseded* and shapes nothing. An applied link marks its cell ``ai`` and
   carries ``ai_link_id``: it is never shown as an expert's act.
3. **Manual edits**, replayed in ``edit_no`` order; an undone edit and the undo events themselves are skipped. A
   manual edit overwrites an AI cell, and an AI link whose cell a manual edit has since taken is *superseded*.

An edit whose cells no longer exist in the build (a page the build never held, a ``mark_absent`` for a version the
build does not have, an ``unlink`` of a page that no longer shares a row with another) is **orphaned**: it is
kept, listed in ``orphaned_edit_ids`` and its history row reads ``orphaned``; it is never applied silently and never
dropped.

Edit semantics (the original's ``move``, ``detach`` and ``absent`` of ``lineage.py:537-576``, over immutable page
coordinates instead of row anchors):

``link(page, other_page)``
    ``other_page`` joins the row of ``page`` at its own version's column; a different page that was there gets a row
    of its own. A page moved out leaves a hole (``unmatched`` / ``edited``) in its old row; a row left empty goes.
``unlink(page)``
    ``page`` leaves its row for a row of its own, placed after the old one.
``mark_absent(page, absent_version_uid)``
    the row of ``page`` has no sheet in that version. A page that stood there gets a row of its own.

What an edit cannot do here that the original's rebuild does: the original rebuilds the whole matrix with the
edit in place and so recomputes the candidates of every hole. Here the build is not repeated for an edit, so a
hole keeps the candidates of the build (minus those an edit has since taken into a row that already holds the
reference version's sheet); a hole an edit left in the old row has none (``unmatched`` / ``edited``), and a row an
edit created holds one page and reads ``absent`` / ``edited`` in the other versions.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any, Final

from auditmanager.comparison.matrix.model import AiLinkRecord, BuildRecord, EditRecord, PageRef

__all__ = [
    "page_index",
    "AI_APPLIED",
    "AI_SUPERSEDED",
    "EDIT_APPLIED",
    "EDIT_ORPHANED",
    "EDIT_UNDONE",
    "EffectiveMatrix",
    "REASON_EDITED",
    "REASON_MARKED_ABSENT",
    "canonical_json",
    "effective_matrix",
    "latest_applied_edit",
]

EDIT_APPLIED: Final[str] = "applied"
EDIT_UNDONE: Final[str] = "undone"
EDIT_ORPHANED: Final[str] = "orphaned"
AI_APPLIED: Final[str] = "applied"
AI_SUPERSEDED: Final[str] = "superseded"
#: The reason codes of a cell an edit decided (the algorithm's reasons are those of ``resolve`` and
#: ``candidates_left`` / ``no_candidates``).
REASON_MARKED_ABSENT: Final[str] = "marked_absent"
REASON_EDITED: Final[str] = "edited"
_FLAG_ORDER: Final[tuple[str, ...]] = ("split", "duplicate", "scan", "bridge")

Row = dict[str, Any]


@dataclass(slots=True)
class EffectiveMatrix:
    """The effective matrix in the shape of the contract's ``ComparisonMatrix`` members, plus the statuses."""

    columns: list[dict[str, Any]]
    rows: list[dict[str, Any]]
    unassigned_pages: list[dict[str, Any]]
    counts: dict[str, int]
    orphaned_edit_ids: list[str]
    edit_status: dict[str, str] = field(default_factory=dict)
    ai_status: dict[str, str] = field(default_factory=dict)


def page_index(build: BuildRecord) -> dict[tuple[str, int], str]:
    """``{(version_uid, page_number): page_profile_id}`` of every page the build held (cells, copies, candidates,
    unassigned): how an edit, which names a page by version and number, is shown with its profile identity."""
    index: dict[tuple[str, int], str] = {}
    for row in build.rows:
        for cell in row["cells"]:
            version = cell["version_uid"]
            if cell["state"] == "matched":
                index[(version, cell["page_number"])] = cell["page_profile_id"]
                for dup in cell.get("dups", ()):
                    index[(version, dup["page_number"])] = dup["page_profile_id"]
            for candidate in cell.get("candidates", ()):
                index[(version, candidate["page_number"])] = candidate["page_profile_id"]
    for ref in build.unassigned:
        index[(ref["version_uid"], ref["page_number"])] = ref["page_profile_id"]
    return index


def canonical_json(value: Any) -> bytes:
    """The bytes of a matrix value: sorted keys, no whitespace, no escaping of non-ASCII."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


# -- working rows ----------------------------------------------------------------------------------------------


def _working_rows(build: BuildRecord) -> list[Row]:
    """The stored rows as editable rows: ``cells`` (matched, by version), ``holes`` (unmatched/absent by version)."""
    rows: list[Row] = []
    for stored in copy.deepcopy(build.rows):
        cells: dict[str, dict[str, Any]] = {}
        holes: dict[str, dict[str, Any]] = {}
        for cell in stored["cells"]:
            if cell["state"] == "matched":
                cells[cell["version_uid"]] = cell
            else:
                holes[cell["version_uid"]] = cell
        rows.append({"cells": cells, "holes": holes, "absent": {}})
    return rows


def _locate(rows: Sequence[Row], version_uid: str, page_number: int) -> tuple[Row, bool] | None:
    """The row that holds a page, and whether the page is a duplicate copy inside the cell of its primary."""
    for row in rows:
        cell = row["cells"].get(version_uid)
        if cell is None:
            continue
        if cell["page_number"] == page_number:
            return row, False
        if any(d["page_number"] == page_number for d in cell.get("dups", ())):
            return row, True
    return None


def _take_page(row: Row, version_uid: str, page_number: int, is_duplicate: bool) -> dict[str, Any]:
    """Remove a page from its row and return it as a standalone cell (a primary leaves with its copies)."""
    cell = row["cells"][version_uid]
    if not is_duplicate:
        del row["cells"][version_uid]
        return cell
    entry = next(d for d in cell["dups"] if d["page_number"] == page_number)
    cell["dups"].remove(entry)
    if not cell["dups"]:
        del cell["dups"]
        cell["flags"] = [f for f in cell.get("flags", []) if f != "duplicate"]
    taken: dict[str, Any] = {
        "version_uid": version_uid,
        "state": "matched",
        "page_number": page_number,
        "page_profile_id": entry["page_profile_id"],
        "flags": [f for f in cell.get("flags", []) if f != "duplicate"],
    }
    for key in ("title", "sheet_number"):
        if key in cell:
            taken[key] = cell[key]
    return taken


def _manual(cell: dict[str, Any], edit_id: str) -> dict[str, Any]:
    """A cell an expert decided: confidence ``manual``, the algorithm's score and any AI mark gone."""
    cell["confidence"] = "manual"
    cell["edit_id"] = edit_id
    for key in ("score", "parts", "ai_link_id"):
        cell.pop(key, None)
    cell["flags"] = [f for f in cell.get("flags", []) if f != "bridge"]
    return cell


def _index_of(rows: Sequence[Row], row: Row) -> int:
    return next(i for i, r in enumerate(rows) if r is row)


def _hole(reason: str = REASON_EDITED) -> dict[str, Any]:
    return {"state": "unmatched", "candidates": [], "reason": reason}


# -- the edits -------------------------------------------------------------------------------------------------


def _apply_link(rows: list[Row], edit: EditRecord) -> bool:
    assert edit.page is not None and edit.other_page is not None
    p, q = edit.page, edit.other_page
    found_p = _locate(rows, p.version_uid, p.page_number)
    found_q = _locate(rows, q.version_uid, q.page_number)
    if found_p is None or found_q is None:
        return False
    row_p, _dup_p = found_p
    row_q, dup_q = found_q
    if row_p is row_q:
        if not dup_q:
            _manual(row_q["cells"][q.version_uid], edit.edit_id)  # already one row: the expert confirmed it
        return True
    cell_q = _manual(_take_page(row_q, q.version_uid, q.page_number, dup_q), edit.edit_id)
    displaced = row_p["cells"].get(q.version_uid)
    row_p["cells"][q.version_uid] = cell_q
    row_p["absent"].pop(q.version_uid, None)
    row_p["holes"].pop(q.version_uid, None)
    if displaced is not None:
        rows.insert(_index_of(rows, row_p) + 1, {"cells": {q.version_uid: _manual(displaced, edit.edit_id)}, "holes": {}, "absent": {}})
    if not row_q["cells"]:
        rows.remove(row_q)
    else:
        row_q["holes"][q.version_uid] = _hole()
    return True


def _apply_unlink(rows: list[Row], edit: EditRecord) -> bool:
    assert edit.page is not None
    p = edit.page
    found = _locate(rows, p.version_uid, p.page_number)
    if found is None:
        return False
    row, is_duplicate = found
    if not is_duplicate and len(row["cells"]) < 2:
        return False  # nothing to detach: the page already stands alone, what the expert corrected is gone
    cell = _manual(_take_page(row, p.version_uid, p.page_number, is_duplicate), edit.edit_id)
    if not is_duplicate:
        row["holes"][p.version_uid] = _hole()
    rows.insert(_index_of(rows, row) + 1, {"cells": {p.version_uid: cell}, "holes": {}, "absent": {}})
    return True


def _apply_mark_absent(rows: list[Row], edit: EditRecord, order: Sequence[str]) -> bool:
    assert edit.page is not None and edit.absent_version_uid is not None
    p, version = edit.page, edit.absent_version_uid
    if version not in order:
        return False
    found = _locate(rows, p.version_uid, p.page_number)
    if found is None:
        return False
    row, _is_duplicate = found
    present = row["cells"].pop(version, None)
    row["holes"].pop(version, None)
    row["absent"][version] = edit.edit_id
    if present is not None:
        rows.insert(_index_of(rows, row) + 1, {"cells": {version: _manual(present, edit.edit_id)}, "holes": {}, "absent": {}})
    return True


# -- the accepted AI links -------------------------------------------------------------------------------------


def _apply_ai(rows: list[Row], link: AiLinkRecord, build: BuildRecord) -> bool:
    """Apply one link if the cell it answered is still in the state it answered (``_ai_link``, lineage.py:519-534)."""
    if link.matrix_id != build.matrix_id:
        return False
    a, b = link.page, link.other_page
    found_a = _locate(rows, a.version_uid, a.page_number)
    found_b = _locate(rows, b.version_uid, b.page_number)
    if found_a is None or found_b is None:
        return False
    row_a, dup_a = found_a
    row_b, dup_b = found_b
    if row_a is row_b or dup_a or dup_b:
        return False
    cell_b = row_b["cells"][b.version_uid]
    if link.answered_state == "unmatched":
        hole = row_a["holes"].get(b.version_uid)
        if (
            hole is None
            or hole.get("state") != "unmatched"
            or b.version_uid in row_a["cells"]
            or set(row_a["cells"]) & set(row_b["cells"])
        ):
            return False
        for version, cell in row_b["cells"].items():
            row_a["cells"][version] = cell
            row_a["holes"].pop(version, None)
        row_a["cells"][b.version_uid] = _ai(cell_b, link.ai_link_id)
        rows.remove(row_b)
        return True
    # doubtful: the algorithm linked another page here at medium confidence and the model says it is ``b``
    current = row_a["cells"].get(b.version_uid)
    if current is None or current.get("confidence") != "medium" or current["page_number"] == b.page_number:
        return False
    _take_page(row_b, b.version_uid, b.page_number, False)
    row_a["cells"][b.version_uid] = _ai(cell_b, link.ai_link_id)
    displaced = {k: v for k, v in current.items() if k not in ("confidence", "score", "parts")}
    rows.insert(_index_of(rows, row_a) + 1, {"cells": {b.version_uid: displaced}, "holes": {}, "absent": {}})
    if not row_b["cells"]:
        rows.remove(row_b)
    else:
        row_b["holes"][b.version_uid] = _hole()
    return True


def _ai(cell: dict[str, Any], ai_link_id: str) -> dict[str, Any]:
    cell["confidence"] = "ai"
    cell["ai_link_id"] = ai_link_id
    for key in ("score", "parts", "edit_id"):
        cell.pop(key, None)
    return cell


# -- the effective matrix --------------------------------------------------------------------------------------


def latest_applied_edit(edits: Sequence[EditRecord]) -> EditRecord | None:
    """The newest edit that an undo may reverse: not an undo, not already undone (orphaned edits count -- they are
    applied history that an expert may take back)."""
    undone = {e.undoes_edit_id for e in edits if e.kind == "undo"}
    candidates = [e for e in edits if e.kind != "undo" and e.edit_id not in undone]
    return max(candidates, key=lambda e: e.edit_no, default=None)


def effective_matrix(
    build: BuildRecord,
    edits: Sequence[EditRecord],
    ai_links: Sequence[AiLinkRecord],
    *,
    page_counts: dict[str, int] | None = None,
    version_labels: dict[str, str] | None = None,
) -> EffectiveMatrix:
    """The effective matrix of ``build`` under ``edits`` and ``ai_links``."""
    order = build.order
    rows = _working_rows(build)

    # layer 2: accepted AI links, oldest first
    ai_applied: dict[str, bool] = {}
    for link in sorted(ai_links, key=lambda x: (x.created_at, x.ai_link_id)):
        ai_applied[link.ai_link_id] = _apply_ai(rows, link, build)

    # layer 3: manual edits, in order; an edit that is undone, and an undo event, are not replayed
    undone = {e.undoes_edit_id for e in edits if e.kind == "undo"}
    edit_status: dict[str, str] = {}
    orphaned: list[str] = []
    for edit in sorted(edits, key=lambda e: e.edit_no):
        if edit.kind == "undo":
            edit_status[edit.edit_id] = EDIT_APPLIED
            continue
        if edit.edit_id in undone:
            edit_status[edit.edit_id] = EDIT_UNDONE
            continue
        if edit.kind == "link":
            ok = _apply_link(rows, edit)
        elif edit.kind == "unlink":
            ok = _apply_unlink(rows, edit)
        else:
            ok = _apply_mark_absent(rows, edit, order)
        edit_status[edit.edit_id] = EDIT_APPLIED if ok else EDIT_ORPHANED
        if not ok:
            orphaned.append(edit.edit_id)

    # an AI link applies only if its cell still carries it after the manual layer
    ai_status: dict[str, str] = {}
    surviving = {
        cell.get("ai_link_id")
        for row in rows
        for cell in row["cells"].values()
        if cell.get("confidence") == "ai"
    }
    for link in ai_links:
        ai_status[link.ai_link_id] = (
            AI_APPLIED if ai_applied.get(link.ai_link_id) and link.ai_link_id in surviving else AI_SUPERSEDED
        )

    rows = [row for row in rows if row["cells"]]
    held = {
        (version, cell["page_number"]) for row in rows for version, cell in row["cells"].items()
    } | {
        (version, d["page_number"]) for row in rows for version, cell in row["cells"].items() for d in cell.get("dups", ())
    }
    where: dict[tuple[str, int], Row] = {}
    for row in rows:
        for version, cell in row["cells"].items():
            where[(version, cell["page_number"])] = row
            for d in cell.get("dups", ()):
                where[(version, d["page_number"])] = row

    wire_rows: list[dict[str, Any]] = []
    for row in rows:
        wire_cells = [_wire_cell(row, version, where) for version in order]
        anchor_version = next(v for v in order if v in row["cells"])
        wire_row: dict[str, Any] = {"row_id": row["cells"][anchor_version]["page_profile_id"], "cells": wire_cells}
        for version in sorted(row["cells"], key=order.index, reverse=True):
            cell = row["cells"][version]
            if "title" in cell:
                wire_row["title"] = cell["title"]
                break
        for version in sorted(row["cells"], key=order.index, reverse=True):
            cell = row["cells"][version]
            if "sheet_number" in cell:
                wire_row["sheet_number"] = cell["sheet_number"]
                break
        wire_rows.append(wire_row)

    unassigned = [
        {"version_uid": ref["version_uid"], "page_number": ref["page_number"], "page_profile_id": ref["page_profile_id"]}
        for ref in build.unassigned
        if (ref["version_uid"], ref["page_number"]) not in held
    ]
    columns: list[dict[str, Any]] = []
    for version in order:
        column: dict[str, Any] = {"version_uid": version, "page_count": (page_counts or {}).get(version, 0)}
        label = (version_labels or {}).get(version)
        if label:
            column["label"] = label
        columns.append(column)

    return EffectiveMatrix(
        columns=columns,
        rows=wire_rows,
        unassigned_pages=unassigned,
        counts=_counts(wire_rows),
        orphaned_edit_ids=orphaned,
        edit_status=edit_status,
        ai_status=ai_status,
    )


def _wire_cell(row: Row, version: str, where: dict[tuple[str, int], Row]) -> dict[str, Any]:
    cell = row["cells"].get(version)
    if cell is not None:
        out: dict[str, Any] = {
            "version_uid": version,
            "state": "matched",
            "page": {"version_uid": version, "page_number": cell["page_number"], "page_profile_id": cell["page_profile_id"]},
            "flags": [f for f in _FLAG_ORDER if f in set(cell.get("flags", ()))],
        }
        if "confidence" in cell:
            out["confidence"] = cell["confidence"]
        if cell.get("edit_id"):
            out["edit_id"] = cell["edit_id"]
        if cell.get("ai_link_id"):
            out["ai_link_id"] = cell["ai_link_id"]
        return out
    if version in row["absent"]:
        return {"version_uid": version, "state": "absent", "reason": REASON_MARKED_ABSENT, "edit_id": row["absent"][version]}
    # A row an edit created holds one page and no hole: the expert said this sheet stands alone, so the other
    # versions are ``absent`` for it; a hole an edit left behind in the old row is recorded as ``unmatched``.
    hole = row["holes"].get(version) or {"state": "absent", "reason": REASON_EDITED}
    if hole["state"] == "absent":
        return {"version_uid": version, "state": "absent", "reason": hole.get("reason", "no_candidates")}
    reference = hole.get("ref_version_uid")
    kept: list[dict[str, Any]] = []
    for candidate in hole.get("candidates", ()):
        located = where.get((version, candidate["page_number"]))
        if located is not None and reference is not None and reference in located["cells"]:
            continue  # an edit has since taken this page into a row that already holds the reference sheet
        kept.append(
            {
                "page": {"version_uid": version, "page_number": candidate["page_number"], "page_profile_id": candidate["page_profile_id"]},
                "score": candidate["score"],
            }
        )
    if hole.get("candidates") and not kept:
        return {"version_uid": version, "state": "absent", "reason": "no_candidates"}
    out = {"version_uid": version, "state": "unmatched", "reason": hole.get("reason", "candidates_left")}
    if kept:
        out["candidates"] = kept
    return out


def _counts(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    rows = list(rows)
    cells = [c for r in rows for c in r["cells"]]
    return {
        "rows": len(rows),
        "unmatched": sum(1 for c in cells if c["state"] == "unmatched"),
        "manual": sum(1 for c in cells if c.get("confidence") == "manual"),
        "ai": sum(1 for c in cells if c.get("confidence") == "ai"),
        "groups": sum(1 for c in cells if c.get("confidence") == "group"),
        "duplicates": sum(1 for c in cells if "duplicate" in c.get("flags", ())),
    }
