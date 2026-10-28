"""The algorithmic matrix: rows of sheets across the versions, built version by version.

`CMP-MATRIX-01`, a port of ``lineage.py`` of the original at ``23f379fd`` (``build``, ``_assign``, ``_duplicates``,
``_finalize``, ``direct_pairs``) over our page features. The versions are walked in the order the user confirmed;
for each adjacent pair the primary pages of the next version are assigned to the previous version's pages by a
maximum-weight assignment over the page score, a pair being accepted at ``MATCH_MEDIUM`` (0.35) and shown with
confidence ``high`` from ``MATCH_HIGH`` (0.55); pages below ``MATCH_CANDIDATE_FLOOR`` (0.20) are not candidates.
Then, with the rule set ``v1.2``:

* a pair must beat its nearest competitor, by row and by column, by ``MATCH_MARGIN`` (rule ``margin``), otherwise it
  is left to the evidence of :mod:`.resolve` (rules ``resolve``, ``package``, ``permit``, ``pageno``, ``group``);
* copies of a page inside one version are *duplicates*: they stand in the cell of their primary, and when the
  copies diverge in the next version each gets a row of its own (lineage revision ``copies1``);
* a sheet that is missing from an intermediate version and returns is *bridged* to its row when the pair scores at
  least ``MATCH_HIGH``;
* a page with no link opens a new row after the row of the previous page of its version;
* a cell of a row with no page in a version is *unmatched* (up to three candidates, scored against the row's nearest
  page, ordered by score to hundredths and then by distance in file order) or *absent* (no candidate left).

**What this function does not do**: it applies no manual edit and no AI link. Those are layers over its result
(:mod:`.effective`), so the stored build is a pure function of the profiles and the order, the same bytes for the
same input. (The original applies edits inside the build and rebuilds on every edit; here an edit is a row of a
table and the build is not repeated for it.)

A page is its version and its number *within that immutable version*, plus the identity of its profile; the stored
rows name pages by (``version_uid``, ``page_number``, ``page_profile_id``).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

import numpy as np

from auditmanager.comparison.matrix import resolve as resolve_module
from auditmanager.comparison.matrix import settings
from auditmanager.comparison.matrix.assignment import maximum_weight_assignment
from auditmanager.comparison.matrix.features import PageFeatures
from auditmanager.comparison.matrix.scoring import has_content_evidence, mask_iou, score
from auditmanager.comparison.matrix.settings import (
    MATCH_CANDIDATE_FLOOR,
    MATCH_HIGH,
    MATCH_MEDIUM,
)

__all__ = [
    "assign",
    "build_rows",
    "direct_pairs",
    "find_duplicates",
    "find_splits",
]

Link = tuple[int, float, dict[str, Any]]

#: Stamp field labels the stamp reader sometimes takes for a sheet title (lineage.py:668-672).
_NOT_TITLES = re.compile(r"^(формат(\s+а\d.*)?|лист|листов|стадия|изм\.?|подп\.?|дата)$", re.I)
_FLAG_ORDER = ("split", "duplicate", "scan", "bridge")


def _shown_title(f: PageFeatures) -> str:
    title = (f.title_raw or "").strip()
    return "" if _NOT_TITLES.match(title) else title


def _round_parts(parts: dict[str, Any]) -> dict[str, Any]:
    return {k: (round(v, 3) if isinstance(v, (int, float)) and not isinstance(v, bool) else v) for k, v in parts.items()}


def find_duplicates(pages: Sequence[PageFeatures], rules: frozenset[str]) -> dict[int, int]:
    """Copies inside one version: page -> the primary copy's page (``lineage.py:290-317``)."""
    dup: dict[int, int] = {}
    if "resolve" in rules:
        # Stage two: pages with no stamp (questionnaires, covers) that are equal are a duplicate, not two equal
        # candidates: the same words, title and number (both may be empty) and almost the same drawing.
        seen: dict[tuple[Any, ...], PageFeatures] = {}
        for a in pages:
            if not a.has_text:
                continue
            key = (frozenset(a.tokens.items()), a.title, a.sheet_no, a.designation, a.size)
            b = seen.get(key)
            if b is None:
                seen[key] = a
            elif (
                a.has_mask
                and b.has_mask
                and a.mask_shape() == b.mask_shape()
                and mask_iou(a, b) >= settings.RESOLVE_DUP_IMAGE
                and resolve_module.same_drawing(a, b)
            ):
                dup[a.page] = b.page
    for i, a in enumerate(pages):
        if a.page in dup or not a.designation or not a.sheet_no:
            continue
        for b in pages[i + 1 :]:
            if b.page in dup or b.designation != a.designation or b.sheet_no != a.sheet_no:
                continue
            union = len(a.pos | b.pos)
            inter = sum((a.tokens & b.tokens).values())
            union_tokens = a.token_total + b.token_total - inter
            jaccard = inter / union_tokens if (a.tokens or b.tokens) and union_tokens else 0.0
            if jaccard >= 0.9 and union and len(a.pos & b.pos) / union >= 0.7:
                dup[b.page] = a.page
    return dup


def assign(
    prev: Sequence[PageFeatures],
    cur: Sequence[PageFeatures],
    rules: frozenset[str],
    reasons_out: dict[tuple[str, int], Any] | None = None,
) -> tuple[dict[int, Link], np.ndarray]:
    """The links of one transition: ``{index in prev: (index in cur, score, parts)}`` and the score matrix
    (``lineage.py:343-392``)."""
    n, m = len(prev), len(cur)
    matrix = np.zeros((n, m), dtype=np.float64)
    parts_all: dict[tuple[int, int], dict[str, Any]] = {}
    for i, a in enumerate(prev):
        for j, b in enumerate(cur):
            value, parts = score(a, b, i / max(1, n - 1), j / max(1, m - 1), rules)
            matrix[i, j] = value
            parts_all[(i, j)] = parts
    weights = [[float(v) if v >= MATCH_CANDIDATE_FLOOR else 0.0 for v in row] for row in matrix]
    links: dict[int, Link] = {}
    if not (n and m):
        return links, matrix
    proposed = [
        (i, j) for i, j in maximum_weight_assignment(weights) if i < n and j < m and matrix[i, j] >= MATCH_MEDIUM
    ]
    if "margin" not in rules:
        for i, j in proposed:
            links[i] = (j, float(matrix[i, j]), parts_all[(i, j)])
        return links, matrix
    # Equal candidates are not chosen arbitrarily: a pair must stand out from its nearest competitor by row and by
    # column; otherwise it is "needs review" with candidates.
    taken_rows = np.zeros(n, dtype=bool)
    taken_columns = np.zeros(m, dtype=bool)
    while True:
        accepted: list[tuple[int, int, float]] = []
        for i, j in proposed:
            if i in links:
                continue
            s = float(matrix[i, j])
            row = np.where(taken_columns, -np.inf, matrix[i])
            row[j] = -np.inf
            column = np.where(taken_rows, -np.inf, matrix[:, j])
            column[i] = -np.inf
            row_alt = max(float(row.max()) if m > 1 else 0.0, 0.0)
            column_alt = max(float(column.max()) if n > 1 else 0.0, 0.0)
            if s - row_alt >= settings.MATCH_MARGIN and s - column_alt >= settings.MATCH_MARGIN:
                accepted.append((i, j, round(min(s - row_alt, s - column_alt), 4)))
        for i, j, margin in accepted:
            links[i] = (j, float(matrix[i, j]), parts_all[(i, j)] | {"margin": margin})
            taken_rows[i] = taken_columns[j] = True
        if not accepted or "peel" not in rules:
            break
    if "resolve" in rules:
        resolved, reasons = resolve_module.resolve(list(prev), list(cur), matrix, parts_all, links, rules)
        links = resolved
        if reasons_out is not None:
            reasons_out.update(reasons)
    return links, matrix


def direct_pairs(
    pages_a: Sequence[PageFeatures], pages_b: Sequence[PageFeatures], rules: frozenset[str]
) -> dict[int, tuple[int, bool]]:
    """A direct check of two versions that are not adjacent: ``{page of A: (page of B, decisive evidence)}``
    (``lineage.py:501-508``, rule ``direct``). Copies inside B are no candidates, as in the matrix: the pair goes to the
    primary copy. The chain of adjacent links is only a hint for such a pair."""
    duplicates_b = find_duplicates(pages_b, rules)
    primaries = [p for p in pages_b if p.page not in duplicates_b]
    links, similarity = assign(pages_a, primaries, rules)
    strong = resolve_module.strong_pairs(list(pages_a), primaries, similarity, links)
    return {pages_a[i].page: (primaries[j].page, i in strong) for i, (j, _s, _parts) in links.items()}


# -- the structure ---------------------------------------------------------------------------------------------


def _cell(page: int, confidence: str, score_value: float | None, parts: dict[str, Any] | None = None) -> dict[str, Any]:
    cell: dict[str, Any] = {"page": page, "confidence": confidence, "score": score_value}
    if parts is not None:
        cell["parts"] = parts
    return cell


def build_rows(
    order: Sequence[str],
    features: dict[str, list[PageFeatures]],
    rules: frozenset[str] = settings.RULES,
) -> dict[str, Any]:
    """The algorithmic rows for the versions in ``order`` (version identities, oldest first in the user's order).

    Returns ``{"rows": [...], "unassigned": [...], "duplicates": {...}, "splits": [...]}`` in the stored form
    (:func:`_finalize`). Deterministic: it depends on the features and the order and on nothing else.
    """
    rows: list[dict[str, Any]] = []
    page_row: dict[tuple[str, int], int] = {}
    dups_by_version: dict[str, dict[int, int]] = {}
    review_reasons: dict[tuple[str, int, str], Any] = {}

    for k, vid in enumerate(order):
        pages = features[vid]
        dups = find_duplicates(pages, rules)
        dups_by_version[vid] = dups
        primaries = [p for p in pages if p.page not in dups]
        if k == 0:
            for p in primaries:
                rows.append({"cells": {vid: _cell(p.page, "origin", None)}})
                page_row[(vid, p.page)] = len(rows) - 1
        else:
            prev_vid = order[k - 1]
            prev_pages = [p for p in features[prev_vid] if (prev_vid, p.page) in page_row]
            reasons: dict[tuple[str, int], Any] = {}
            links, _matrix = assign(prev_pages, primaries, rules, reasons)
            for (side, idx), code in reasons.items():
                if side == "a":
                    review_reasons[(prev_vid, prev_pages[idx].page, vid)] = code
                else:
                    review_reasons[(vid, primaries[idx].page, prev_vid)] = code
            linked_cur: set[int] = set()
            prev_dups = dups_by_version.get(prev_vid, {})
            # Primary copies first: a duplicate linked to another page gets a row of its own.
            for i, (j, s, parts) in sorted(links.items(), key=lambda kv: prev_pages[kv[0]].page in prev_dups):
                ridx = page_row[(prev_vid, prev_pages[i].page)]
                if prev_pages[i].page in prev_dups and vid in rows[ridx]["cells"]:
                    # Copies that were equal in the previous version diverged: without a row of its own the pair
                    # would overwrite the primary's and a page would fall out of the matrix (lineage.py:437-446).
                    dup_page = prev_pages[i].page
                    rows[ridx]["cells"][prev_vid]["dups"].remove(dup_page)
                    ridx += 1
                    rows.insert(ridx, {"cells": {prev_vid: _cell(dup_page, "origin", None)}})
                    page_row = {key: (ri + 1 if ri >= ridx else ri) for key, ri in page_row.items()}
                    page_row[(prev_vid, dup_page)] = ridx
                confidence = "group" if parts.get("resolved") == "group" else "high" if s >= MATCH_HIGH else "medium"
                rows[ridx]["cells"][vid] = _cell(primaries[j].page, confidence, round(s, 4), _round_parts(parts))
                page_row[(vid, primaries[j].page)] = ridx
                linked_cur.add(j)
            # Equal copies of the previous version are not told apart by content: their new pages go by position.
            for dup_page, primary in prev_dups.items():
                rp, rd = page_row.get((prev_vid, primary)), page_row.get((prev_vid, dup_page))
                if rp is None or rd is None or rp == rd or vid not in rows[rp]["cells"] or vid not in rows[rd]["cells"]:
                    continue
                qp, qd = rows[rp]["cells"][vid]["page"], rows[rd]["cells"][vid]["page"]
                if abs(primary - qd) + abs(dup_page - qp) < abs(primary - qp) + abs(dup_page - qd):
                    rows[rp]["cells"][vid], rows[rd]["cells"][vid] = rows[rd]["cells"][vid], rows[rp]["cells"][vid]
                    page_row[(vid, qp)], page_row[(vid, qd)] = rd, rp
            # A bridge across a gap: a sheet that was there before, vanished in the intermediate version and came back.
            dangling = [ri for ri, r in enumerate(rows) if prev_vid not in r["cells"] and vid not in r["cells"]]
            rest = [j for j in range(len(primaries)) if j not in linked_cur]
            if dangling and rest:
                last_pages: list[PageFeatures] = []
                for ri in dangling:
                    last_vid = max(rows[ri]["cells"], key=order.index)
                    page_number = rows[ri]["cells"][last_vid]["page"]
                    last_pages.append(next(p for p in features[last_vid] if p.page == page_number))
                sub = [primaries[j] for j in rest]
                bridge, _ = assign(last_pages, sub, rules)
                for i, (jj, s, parts) in bridge.items():
                    if s < MATCH_HIGH:
                        continue
                    ridx = dangling[i]
                    cell = _cell(sub[jj].page, "high", round(s, 4), _round_parts(parts))
                    cell["bridged"] = True
                    rows[ridx]["cells"][vid] = cell
                    page_row[(vid, sub[jj].page)] = ridx
                    linked_cur.add(rest[jj])
            # New sheets of the version: a row after the row of the previous page of this version.
            for j, p in enumerate(primaries):
                if j in linked_cur:
                    continue
                insert_at = 0
                for q in reversed(primaries[:j]):
                    if (vid, q.page) in page_row:
                        insert_at = page_row[(vid, q.page)] + 1
                        break
                rows.insert(insert_at, {"cells": {vid: _cell(p.page, "origin", None)}})
                page_row = {key: (ri + 1 if ri >= insert_at else ri) for key, ri in page_row.items()}
                page_row[(vid, p.page)] = insert_at
        # Duplicates: into the cell of the primary copy's row.
        for dup_page, primary in dups.items():
            ri = page_row.get((vid, primary))
            if ri is not None:
                rows[ri]["cells"][vid].setdefault("dups", []).append(dup_page)
                page_row[(vid, dup_page)] = ri

    splits = _all_splits(order, features)
    return _finalize(rows, list(order), features, dups_by_version, rules, review_reasons, splits)


# -- splits (parts.py) -----------------------------------------------------------------------------------------

_FLOORS = re.compile(r"(\d+(?:\s*(?:[-–,]|и)\s*\d+)*)\s*(?:-?(?:го|й|м|х))?\s*этаж\w*", re.I)


def _norm_title(text: str) -> str:
    return " ".join(str(text or "").lower().replace("ё", "е").split()).strip(" .")


def _floors(title: str) -> tuple[str, frozenset[int]] | None:
    """parts.py:27-43: «План 2-4 этажей. Сети» -> ("план # этаж. сети", {2, 3, 4})."""
    t = _norm_title(title)
    found = _FLOORS.search(t)
    if not found:
        return None
    numbers: set[int] = set()
    for part in re.split(r"\s*(?:,|и)\s*", found.group(1)):
        span = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", part.strip())
        if span and 0 <= int(span.group(2)) - int(span.group(1)) <= 60:
            numbers.update(range(int(span.group(1)), int(span.group(2)) + 1))
        elif part.strip().isdigit():
            numbers.add(int(part.strip()))
    if not numbers:
        return None
    return (t[: found.start()] + "# этаж" + t[found.end() :]).strip(), frozenset(numbers)


def find_splits(
    pages_a: Sequence[PageFeatures], pages_b: Sequence[PageFeatures]
) -> list[dict[str, Any]]:
    """Sheets split across two versions, by the stamps (``parts.py:54-75``): ``floors`` (a typical sheet repeated per
    floor: every new page is the whole old sheet with its own flat numbers) and ``split`` (a sheet cut into parts:
    «Схема ВРУ-1» becomes «… Начало» and «… Окончание»). Text containment cannot tell these: floor plans have
    different flat numbers and a split diagram is often reworked as well. Returns
    ``[{"a_page", "b_page", "kind"}]`` ordered by the older page and then the newer."""
    titles_b = {_norm_title(p.title_raw) for p in pages_b if _norm_title(p.title_raw)}
    out: list[dict[str, Any]] = []

    def doc(page: PageFeatures) -> str:
        return re.sub(r"\s+", "", page.designation or "").upper()

    for pa in pages_a:
        ta = _norm_title(pa.title_raw)
        if len(ta) < 6 or ta in titles_b:
            continue  # the sheet goes on under the same title: not a split
        fa = _floors(ta)
        if fa and len(fa[1]) >= 2:
            for pb in pages_b:
                fb = _floors(_norm_title(pb.title_raw))
                if fb and fb[0] == fa[0] and fb[1] < fa[1] and doc(pb) == doc(pa):
                    out.append({"a_page": pa.page, "b_page": pb.page, "kind": "floors"})
        prefixed = [
            pb
            for pb in pages_b
            if _norm_title(pb.title_raw).startswith(ta)
            and len(_norm_title(pb.title_raw)) > len(ta) + 2
            and doc(pb) == doc(pa)
        ]
        if len(prefixed) >= 2:
            for pb in prefixed:
                out.append({"a_page": pa.page, "b_page": pb.page, "kind": "split"})
    return out


def _coverage(source: PageFeatures, parts: Sequence[PageFeatures]) -> float:
    """The share (percent, two decimals) of the older sheet's words that stand in at least one of the parts: a
    text coverage, computed from the profiles (the area coverage of a registered pair is the series' own)."""
    total = source.token_total
    if not total:
        return 0.0
    return round(100.0 * _covered_words(source, parts) / total, 2)


def _covered_words(source: PageFeatures, parts: Sequence[PageFeatures]) -> int:
    """Words of ``source`` (with multiplicity) that some part also has."""
    union: dict[str, int] = {}
    for part in parts:
        for token, count in part.tokens.items():
            if count > union.get(token, 0):
                union[token] = count
    return sum(min(count, union.get(token, 0)) for token, count in source.tokens.items())


def _all_splits(order: Sequence[str], features: dict[str, list[PageFeatures]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for a_vid, b_vid in zip(order, order[1:]):
        by_a: dict[int, list[PageFeatures]] = {}
        pages_b = {p.page: p for p in features[b_vid]}
        pages_a = {p.page: p for p in features[a_vid]}
        found = find_splits(features[a_vid], features[b_vid])
        for item in found:
            by_a.setdefault(item["a_page"], []).append(pages_b[item["b_page"]])
        kinds = {(item["a_page"], item["b_page"]): item["kind"] for item in found}
        for a_page in sorted(by_a):
            parts = sorted(by_a[a_page], key=lambda p: p.page)
            source = pages_a[a_page]
            kind = kinds[(a_page, parts[0].page)]
            out.append(
                {
                    "a_version_uid": a_vid,
                    "b_version_uid": b_vid,
                    "a": source.public_ref(),
                    "parts": [p.public_ref() for p in parts],
                    "kind": kind,
                    # ``floors``: every new page is the whole old sheet; ``split``: each is one part of it.
                    "role": "whole" if kind == "floors" else "part",
                    "covered_percent": _coverage(source, parts),
                }
            )
    return out


# -- the stored form -------------------------------------------------------------------------------------------


def _matched_cell(f: PageFeatures, c: dict[str, Any], dups: Sequence[PageFeatures]) -> dict[str, Any]:
    flags: set[str] = set()
    if f.scan:
        flags.add("scan")
    if dups:
        flags.add("duplicate")
    if c.get("bridged"):
        flags.add("bridge")
    cell: dict[str, Any] = {
        "version_uid": f.version_uid,
        "state": "matched",
        "page_number": f.page,
        "page_profile_id": f.profile_id,
        "flags": [flag for flag in _FLAG_ORDER if flag in flags],
    }
    if c["confidence"] != "origin":
        cell["confidence"] = c["confidence"]
        cell["score"] = c["score"]
        if c.get("parts") is not None:
            cell["parts"] = c["parts"]
    if dups:
        cell["dups"] = [{"page_number": d.page, "page_profile_id": d.profile_id} for d in dups]
    shown = _shown_title(f)
    if shown:
        cell["title"] = shown[:400]
    if f.sheet_no:
        cell["sheet_number"] = f.sheet_no[:64]
    return cell


def _finalize(
    rows: list[dict[str, Any]],
    order: list[str],
    features: dict[str, list[PageFeatures]],
    dups_by_version: dict[str, dict[int, int]],
    rules: frozenset[str],
    review_reasons: dict[tuple[str, int, str], Any],
    splits: list[dict[str, Any]],
) -> dict[str, Any]:
    """The stored rows (``lineage.py:578-659``): a cell for every version, candidates for the unmatched, the
    duplicates, the row's title; and the pages no row holds."""
    feat_by = {(vid, p.page): p for vid, pages in features.items() for p in pages}
    where: dict[tuple[str, int], int] = {}
    for ri, r in enumerate(rows):
        for vid, c in r["cells"].items():
            where[(vid, c["page"])] = ri
            for d in c.get("dups", []):
                where[(vid, d)] = ri

    def row_has_link(vid: str, page: int, neighbour: str) -> bool:
        ri = where.get((vid, page))
        return ri is not None and neighbour in rows[ri]["cells"]

    split_pages = {
        (ref["version_uid"], ref["page_number"])
        for item in splits
        for ref in [item["a"], *item["parts"]]
    }
    out_rows: list[dict[str, Any]] = []
    for r in rows:
        anchor_vid = min(r["cells"], key=order.index)
        anchor = feat_by[(anchor_vid, r["cells"][anchor_vid]["page"])]
        cells: list[dict[str, Any]] = []
        for k, vid in enumerate(order):
            c = r["cells"].get(vid)
            if c:
                f = feat_by[(vid, c["page"])]
                dup_features = [feat_by[(vid, d)] for d in c.get("dups", [])]
                cell = _matched_cell(f, c, dup_features)
                if (vid, f.page) in split_pages and "split" not in cell["flags"]:
                    cell["flags"] = [flag for flag in _FLAG_ORDER if flag in {*cell["flags"], "split"}]
                cells.append(cell)
                continue
            # The reference page is the nearest version in the order where the row has a sheet.
            present = sorted(r["cells"], key=lambda ov: (abs(order.index(ov) - k), order.index(ov)))
            candidates: list[dict[str, Any]] = []
            ref_vid = present[0]
            ref = feat_by[(ref_vid, r["cells"][ref_vid]["page"])]
            for p in features[vid]:
                if row_has_link(vid, p.page, ref_vid):
                    continue  # the page is already linked to the reference version in its own row
                if "permit" in rules and resolve_module.permit_conflict(ref, p):
                    continue  # a sheet of another permit is another document, not a candidate
                s, parts = score(ref, p, 0.5, 0.5, rules)
                if s >= MATCH_CANDIDATE_FLOOR and has_content_evidence(parts):
                    entry = {"page": p, "score": round(s, 4)}
                    if "order" in rules:
                        n_ref, n_p = len(features[ref_vid]), len(features[vid])
                        entry["order_distance"] = round(
                            abs((ref.page - 1) / max(1, n_ref - 1) - (p.page - 1) / max(1, n_p - 1)), 4
                        )
                    candidates.append(entry)
            if "order" in rules:
                # Order only sorts candidates whose scores agree to hundredths; it never accepts a pair.
                sort_key = lambda c: (-round(c["score"], 2), c.get("order_distance", 0.0), c["page"].page)  # noqa: E731
            else:
                sort_key = lambda c: (-c["score"], c["page"].page)  # noqa: E731
            unique = sorted({c["page"].page: c for c in candidates}.values(), key=sort_key)[: settings.MAX_CANDIDATES]
            if unique:
                reason = "candidates_left"
                code = review_reasons.get((ref_vid, ref.page, vid))
                if code:
                    reason = code[0] if isinstance(code, tuple) else code
                cells.append(
                    {
                        "version_uid": vid,
                        "state": "unmatched",
                        "candidates": [
                            {"page_number": c["page"].page, "page_profile_id": c["page"].profile_id, "score": c["score"]}
                            for c in unique
                        ],
                        "reason": reason,
                        "ref_version_uid": ref_vid,
                    }
                )
            else:
                cells.append({"version_uid": vid, "state": "absent", "reason": "no_candidates"})
        out_rows.append({"anchor": anchor.public_ref(), "cells": cells})

    held = set(where)
    unassigned = [
        p.public_ref() for vid in order for p in features[vid] if (vid, p.page) not in held
    ]
    duplicates = {vid: {str(k): v for k, v in sorted(d.items())} for vid, d in dups_by_version.items() if d}
    return {"rows": out_rows, "unassigned": unassigned, "duplicates": duplicates, "splits": splits}
