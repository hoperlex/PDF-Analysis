"""Stage two of the matching: contested pairs are decided by evidence, not by lowering a threshold.

`CMP-MATRIX-01`, a port of ``resolve.py`` of the original at ``23f379fd`` (rules ``resolve``, ``package``,
``permit``, ``pageno`` and ``group`` of the set ``v1.2``; ``direct`` is :func:`strong_pairs`). After the main
assignment (the page score and the margin to the nearest competitor) some pages are still undecided: look-alike
sheets, a supplier's questionnaire pages, repeated sections of a specification. A pair is accepted here only on
positive evidence:

* *distinctive words*: the winner must outweigh **every** competitor on the words that exactly one of the two has,
  counted on the words of page A only. A word weighs its rarity over the pages of the transition times its kind
  (mark or position, letters and digits, 1.0; a word of three letters or more, 0.5; a number, size or date, 0.15
  -- values change between versions);
* *tables* (specifications, journals) must also cover each other's marks, otherwise their rows moved between sheets
  and the relation is a *block*, not one-to-one;
* pages with no distinguishing text (twins, sheets with no text layer): the image area in which the candidates
  differ decides which of them A matches;
* a *mutual check*: from B's side the same rule must point at the same A page, over all candidates at or above the
  floor, linked ones included (a pointer at a page that is already linked refuses the pair);
* the pair's score must reach ``MATCH_MEDIUM`` (the threshold is not lowered);
* *package*: A's and B's designations must not contradict the designation correspondence the confident pairs of the
  transition establish.

The order of the pages is not used. An undecided page gets a reason code (``reasons``). Line numbers cited are the
original's (``backend/app/services/version_comparison/resolve.py``).
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any, Final

import cv2
import numpy as np

from auditmanager.comparison.matrix import settings
from auditmanager.comparison.matrix.features import PageFeatures
from auditmanager.comparison.matrix.scoring import mask_iou
from auditmanager.comparison.matrix.settings import MATCH_CANDIDATE_FLOOR, MATCH_MEDIUM

__all__ = [
    "REASON_CODES",
    "TABLE_KINDS",
    "footer_counts",
    "is_permit",
    "package_conflict",
    "package_map",
    "permit_conflict",
    "resolve",
    "same_drawing",
    "strong_pairs",
    "token_class",
    "weights",
]

_DIM: Final[re.Pattern[str]] = re.compile(r"^\d+([.,]\d+)?([xх×*]\d+([.,]\d+)?)+$")
# A code of digits with two or more separators ("1.13.3", "0986-04-24_2") is a designation, not a value; dates are not codes.
_CODE: Final[re.Pattern[str]] = re.compile(r"^\d+([./\-_]\d+){2,}$")
_DATE: Final[re.Pattern[str]] = re.compile(r"^((19|20)\d\d[-.]\d\d[-.]\d\d|\d\d[-.]\d\d[-.](19|20)?\d\d)$")
TABLE_KINDS: Final[tuple[str, ...]] = ("spec", "text")  # resolve.py:42

#: The reason codes of an undecided page (``REASON_LABELS``, resolve.py:44-58), as codes; the words are the client's.
REASON_CODES: Final[tuple[str, ...]] = (
    "twin",
    "twin_sheet",
    "block",
    "weak",
    "taken",
    "not_mutual",
    "below_pair",
    "package",
    "no_evidence",
    "title_conflict",
    "title_only",
    "page_no_conflict",
    "permit",
)

Link = tuple[int, float, dict[str, Any]]


def token_class(token: str) -> float:
    """resolve.py:61-70: the kind weight of a word."""
    has_digit = any(ch.isdigit() for ch in token)
    has_alpha = any(ch.isalpha() for ch in token)
    if has_digit and has_alpha and not _DIM.match(token):
        return settings.RESOLVE_W_MARK
    if has_alpha and not has_digit:
        return settings.RESOLVE_W_WORD if len(token) >= 3 else 0.0
    if _CODE.match(token) and not _DATE.match(token):
        return settings.RESOLVE_W_MARK
    return settings.RESOLVE_W_NUMBER


def weights(pages: list[PageFeatures]) -> dict[str, float]:
    """resolve.py:73-76: rarity over the pages of the transition times the kind weight."""
    frequency = Counter(t for f in pages for t in set(f.tokens))
    count = len(pages)
    return {t: math.log(count / d) * token_class(t) for t, d in frequency.items()}


def _contest(
    words_a: set[str], first: set[str], other: set[str], w: dict[str, float]
) -> tuple[float, float, int, int]:
    """resolve.py:79-84: the words of A that exactly one of the two candidates has: weight and count for each."""
    different = (first ^ other) & words_a
    for_first = {t for t in different & first if w.get(t, 0.0) > 0}
    for_other = {t for t in different - first if w.get(t, 0.0) > 0}
    # fsum: the sum of a set must not depend on the process's string hashing, or two runs could disagree at a threshold.
    return math.fsum(w[t] for t in for_first), math.fsum(w[t] for t in for_other), len(for_first), len(for_other)


def _decisive(pro: float, con: float, n_pro: int, n_con: int) -> bool:
    """resolve.py:87-96: the lead is proven by weight share and absolute lead, or, when one or two rare words
    against spoil the share, by an overwhelming majority of the distinctive words."""
    if pro - con < settings.RESOLVE_MIN_W:
        return False
    fraction = pro / (pro + con)
    if fraction >= settings.RESOLVE_FRAC:
        return True
    return (
        fraction >= settings.RESOLVE_FRAC_ROBUST
        and n_con <= settings.RESOLVE_MAX_AGAINST
        and n_pro / (n_pro + n_con) >= settings.RESOLVE_COUNT_FRAC
    )


_ONES: Final[np.ndarray] = np.ones((3, 3), np.uint8)


def _image_contest(a: PageFeatures, first: PageFeatures, other: PageFeatures) -> tuple[int, int] | None:
    """resolve.py:104-119: in the region where the two candidates differ (ink in one only, away from the ink they
    share) at 36 dpi, how many lines of A agree with the first and with the second. ``None``: no masks, or formats
    differ. A line missing from A is no argument (a revision table or signature may have been added)."""
    masks = [x.full_mask() for x in (a, first, other)]
    if any(m is None for m in masks) or not (masks[0].shape == masks[1].shape == masks[2].shape):  # type: ignore[union-attr]
        return None
    m1, mk = masks[1], masks[2]
    d1, dk = first.dilated_full(), other.dilated_full()
    assert m1 is not None and mk is not None and d1 is not None and dk is not None
    region = (m1 ^ mk) & ~(d1 & dk)
    area = int(region.sum())
    if area == 0:
        return 0, 0
    near_a = a.dilated_full()
    assert near_a is not None
    return int((region & m1 & near_a).sum()), int((region & mk & near_a).sum())


def _title_key(f: PageFeatures) -> str:
    """resolve.py:122-124: the stamp title if substantial."""
    return f.title if len(f.title) >= settings.RESOLVE_TITLE_MIN_LEN else ""


def footer_counts(pages: list[PageFeatures]) -> Counter[tuple[frozenset[str], str]]:
    """resolve.py:127-129: (template, footer number) -> sheets of the version that have it."""
    return Counter((f.template, f.footer_no) for f in pages if f.footer_no)


def _by_page_no(
    x: PageFeatures,
    candidates: list[PageFeatures],
    indices: list[int],
    footers: tuple[Counter[tuple[frozenset[str], str]], Counter[tuple[frozenset[str], str]]],
) -> int | None:
    """resolve.py:132-147 (rule ``pageno``): the candidate with the same footer page number, when that number is
    the only one among the sheets of the same template in both versions and the templates agree."""
    number = x.footer_no
    if not number or footers[0].get((x.template, number), 0) != 1:
        return None
    hit = [k for k in indices if candidates[k].footer_no == number]
    if len(hit) != 1:
        return None
    c = candidates[hit[0]]
    if footers[1].get((c.template, number), 0) != 1:
        return None
    union = len(x.template | c.template)
    if not union or len(x.template & c.template) / union < settings.RESOLVE_TEMPLATE_SIM:
        return None
    return hit[0]


def _sheet(f: PageFeatures) -> str:
    return (f.sheet_no or "").strip()


def _mask_score(a: PageFeatures, b: PageFeatures) -> float:
    """resolve.py:270-277."""
    if not a.has_mask or not b.has_mask or a.mask_shape() != b.mask_shape():
        return 0.0
    return mask_iou(a, b)


def _nearest(x: PageFeatures, candidates: list[PageFeatures], expect: tuple[int, int] | None = None) -> int | None:
    """resolve.py:236-250: the candidate nearest by relative position, among those between the neighbours' accepted
    pairs; a tie is ``None``."""
    pool = list(enumerate(candidates))
    if expect is not None:
        pool = [(q, c) for q, c in pool if expect[0] < c.page < expect[1]]
        if len(pool) == 1:
            return pool[0][0]
    if not pool:
        return None
    distances = sorted((abs(c.rel - x.rel), q) for q, c in pool)
    if len(distances) > 1 and distances[1][0] - distances[0][0] < 1e-9:
        return None
    return distances[0][1]


def _winner_content(
    x: PageFeatures,
    candidates: list[PageFeatures],
    w: dict[str, float],
    footers: tuple[Counter[tuple[frozenset[str], str]], Counter[tuple[frozenset[str], str]]] | None = None,
    expect: tuple[int, int] | None = None,
) -> tuple[int | None, str]:
    """resolve.py:169-229."""
    if len(candidates) == 1:
        return 0, "single"
    words_x = set(x.tokens)
    sets = [set(c.tokens) for c in candidates]
    text_ok = x.has_text and all(c.has_text for c in candidates)
    if text_ok:
        best = max(range(len(candidates)), key=lambda k: math.fsum(w.get(t, 0.0) for t in words_x & sets[k]))
        twin: list[int] = []
        thin: list[int] = []
        for k in range(len(candidates)):
            if k == best:
                continue
            pro, con, n_pro, n_con = _contest(words_x, sets[best], sets[k], w)
            if pro + con <= 0:
                twin.append(k)  # no difference by text: the footer page number or the image decides
                continue
            if _decisive(pro, con, n_pro, n_con):
                continue
            if pro + con < settings.RESOLVE_MIN_W:
                thin.append(k)  # they differ only by numbers and dates: text decides for nobody
                continue
            return None, "weak"
        if not twin and not thin:
            return best, "text"
        if footers is not None:
            k = _by_page_no(x, candidates, [best] + twin + thin, footers)
            if k is not None:
                return k, "page_no"
        if thin:
            return None, "weak"
        chosen = [k for k in range(len(candidates)) if not (sets[k] ^ sets[best]) & words_x] + [best]
        indices = sorted(set(chosen))
    else:
        indices = list(range(len(candidates)))
    # Image: among the candidates text cannot tell apart (or with no text), the one with the best shared mask must
    # agree with A in the region where it differs from each of the others.
    best_image = max(indices, key=lambda k: _mask_score(x, candidates[k]))
    for k in indices:
        if k == best_image:
            continue
        contest = _image_contest(x, candidates[best_image], candidates[k])
        if contest is None:
            return None, "no_evidence"
        pro, con = contest
        if pro + con < settings.RESOLVE_MIN_IMAGE_AREA or pro / (pro + con) < settings.RESOLVE_IMAGE_FRAC:
            if not text_ok:
                return None, "no_evidence"
            # Twins: neither text nor image tells them apart; the nearest by position wins (decision of 17.10).
            group = [candidates[q] for q in indices]
            numbers = {_sheet(c) for c in group} - {""}
            if len(numbers) > 1:
                # The stamp does tell the twins apart: only the same sheet number decides, nearness does not.
                same_number = [q for q, c in zip(indices, group) if _sheet(x) and _sheet(c) == _sheet(x)]
                return (same_number[0], "twin_sheet") if len(same_number) == 1 else (None, "twin_sheet")
            near = _nearest(x, group, expect)
            return (indices[near], "twin_nearest") if near is not None else (None, "twin")
    return best_image, "image"


def _winner(
    x: PageFeatures,
    candidates: list[PageFeatures],
    w: dict[str, float],
    titles: tuple[Counter[str], Counter[str]] | None = None,
    footers: tuple[Counter[tuple[frozenset[str], str]], Counter[tuple[frozenset[str], str]]] | None = None,
    expect: tuple[int, int] | None = None,
) -> tuple[int | None, str]:
    """resolve.py:150-166: the candidate that outweighs every other, and the kind of evidence; or ``(None, reason)``."""
    if not candidates:
        return None, "no_evidence"
    title = _title_key(x)
    same = [k for k, c in enumerate(candidates) if title and _title_key(c) == title]
    if titles is not None and title and titles[0][title] == 1 and titles[1][title] == 1 and len(same) == 1:
        # A reliably read sheet title, unique in both versions, decides.
        return same[0], "title"
    k, how = _winner_content(x, candidates, w, footers, expect)
    if k is not None and same and k not in same and _title_key(candidates[k]):
        return None, "title_conflict"  # the content points at a differently titled sheet while the same-titled one exists
    return k, how


def same_drawing(a: PageFeatures, b: PageFeatures) -> bool:
    """resolve.py:253-261: the drawing is the same at 36 dpi: fewer than ``RESOLVE_MIN_IMAGE_AREA`` ink pixels belong
    to one page only (away from the ink they share). A signature and a stamp against a table of changes is no twin."""
    ma, mb = a.full_mask(), b.full_mask()
    if ma is None or mb is None or ma.shape != mb.shape:
        return False
    da, db = a.dilated_full(), b.dilated_full()
    assert da is not None and db is not None
    only = (ma ^ mb) & ~(da & db)
    return int(only.sum()) < settings.RESOLVE_MIN_IMAGE_AREA


def _content_supports(parts: dict[str, Any]) -> bool:
    """resolve.py:264-267: the content confirms the pair by itself (without title or sheet number)."""
    return bool(
        parts.get("text", 0) >= 0.15
        or parts.get("layout", 0) >= 0.15
        or parts.get("image", 0) >= 0.4
        or parts.get("containment", 0) >= 0.25
    )


def is_permit(f: PageFeatures) -> bool:
    return f.kind == "permit" or bool(f.permit_no)


def permit_conflict(a: PageFeatures, b: PageFeatures) -> bool:
    """resolve.py:283-287 (rule ``permit``): a permit to make changes is a document of its own: sheets of different
    permits (different numbers) and a permit against an ordinary sheet are never linked."""
    return bool(a.permit_no and b.permit_no and a.permit_no != b.permit_no) or is_permit(a) != is_permit(b)


def _expected(
    prev: list[PageFeatures], cur: list[PageFeatures], links: dict[int, Link]
) -> tuple[dict[int, tuple[int, int]], dict[int, tuple[int, int]]]:
    """resolve.py:290-304: the gap of the other version's pages between the nearest accepted pairs left and right of a
    page (within ``RESOLVE_NEIGHBOR_SPAN`` pages), for twins; a neighbour on one side only is not enough."""
    pairs = [(prev[i].page, cur[j].page) for i, (j, _s, _p) in links.items()]

    def near(pages: list[PageFeatures], own: list[tuple[int, int]]) -> dict[int, tuple[int, int]]:
        out: dict[int, tuple[int, int]] = {}
        for k, f in enumerate(pages):
            left = max(((a, b) for a, b in own if 0 < f.page - a <= settings.RESOLVE_NEIGHBOR_SPAN), default=None)
            right = min(((a, b) for a, b in own if 0 < a - f.page <= settings.RESOLVE_NEIGHBOR_SPAN), default=None)
            if left and right and left[1] < right[1]:
                out[k] = (left[1], right[1])
        return out

    return near(prev, pairs), near(cur, [(b, a) for a, b in pairs])


def _mark_cover(words_a: set[str], words_b: set[str], w: dict[str, float]) -> float:
    """resolve.py:332-335: the share of A's mark weight that B also has."""
    marks = {t for t in words_a if token_class(t) == settings.RESOLVE_W_MARK}
    total = math.fsum(w.get(t, 0.0) for t in marks)
    return math.fsum(w.get(t, 0.0) for t in marks & words_b) / total if total else 1.0


def strong_pairs(prev: list[PageFeatures], cur: list[PageFeatures], similarity: np.ndarray, links: dict[int, Link]) -> set[int]:
    """resolve.py:307-329 (rule ``direct``): the pairs confirmed by decisive evidence from both sides, the same checks
    as for contested pairs: for a direct comparison of non-adjacent versions the overall score alone is no proof."""
    w = weights(prev + cur)
    titles_prev = Counter(_title_key(f) for f in prev if _title_key(f))
    titles_cur = Counter(_title_key(f) for f in cur if _title_key(f))
    footers_prev, footers_cur = footer_counts(prev), footer_counts(cur)
    floor = similarity >= MATCH_CANDIDATE_FLOOR
    expect_a, expect_b = _expected(prev, cur, links)
    out: set[int] = set()
    for i, (j, _s, _p) in links.items():
        row_candidates = [jj for jj in range(len(cur)) if floor[i, jj]]
        column_candidates = [ii for ii in range(len(prev)) if floor[ii, j]]
        best_i, how = _winner(
            prev[i], [cur[jj] for jj in row_candidates], w, (titles_prev, titles_cur), (footers_prev, footers_cur),
            expect_a.get(i),
        )
        best_j, how_b = _winner(
            cur[j], [prev[ii] for ii in column_candidates], w, (titles_cur, titles_prev), (footers_cur, footers_prev),
            expect_b.get(j),
        )
        if best_i is None or best_j is None or row_candidates[best_i] != j or column_candidates[best_j] != i:
            continue
        if how == how_b == "single":
            continue
        if (prev[i].kind in TABLE_KINDS or cur[j].kind in TABLE_KINDS) and min(
            _mark_cover(set(prev[i].tokens), set(cur[j].tokens), w),
            _mark_cover(set(cur[j].tokens), set(prev[i].tokens), w),
        ) < settings.RESOLVE_TABLE_COVER:
            continue
        out.add(i)
    return out


def _blocks(
    prev: list[PageFeatures],
    cur: list[PageFeatures],
    similarity: np.ndarray,
    links: dict[int, Link],
    used: set[int],
    w: dict[str, float],
) -> list[tuple[list[int], list[int], list[int], list[int]]]:
    """resolve.py:351-394: a table block. Table sheets of A and of B whose rows moved over several sheets: two sheets
    are related if a noticeable share of one's marks is on the other; a block is a connected group where at least one
    side has more than one sheet and the group's marks cover each other almost entirely. The group is built from
    **all** table sheets of the transition (an accepted pair does not cut the chain of moved rows); only the
    unresolved sheets of the group are marked."""
    table_a = [i for i in range(len(prev)) if prev[i].kind in TABLE_KINDS]
    table_b = [j for j in range(len(cur)) if cur[j].kind in TABLE_KINDS]
    if not any(i not in links for i in table_a) and not any(j not in used for j in table_b):
        return []
    sets_a = {i: set(prev[i].tokens) for i in table_a}
    sets_b = {j: set(cur[j].tokens) for j in table_b}
    adjacency: dict[tuple[str, int], set[tuple[str, int]]] = defaultdict(set)
    for i in table_a:
        for j in table_b:
            if similarity[i, j] < MATCH_CANDIDATE_FLOOR:
                continue
            if max(_mark_cover(sets_a[i], sets_b[j], w), _mark_cover(sets_b[j], sets_a[i], w)) >= settings.RESOLVE_BLOCK_EDGE:
                adjacency[("a", i)].add(("b", j))
                adjacency[("b", j)].add(("a", i))
    out: list[tuple[list[int], list[int], list[int], list[int]]] = []
    seen: set[tuple[str, int]] = set()
    for node in list(adjacency):
        if node in seen:
            continue
        component: set[tuple[str, int]] = set()
        stack = [node]
        while stack:
            x = stack.pop()
            if x in component:
                continue
            component.add(x)
            stack.extend(adjacency[x] - component)
        seen |= component
        ia = sorted(i for side, i in component if side == "a")
        jb = sorted(j for side, j in component if side == "b")
        if len(ia) < 2 and len(jb) < 2:
            continue
        union_a = set().union(*(sets_a[i] for i in ia))
        union_b = set().union(*(sets_b[j] for j in jb))
        if min(_mark_cover(union_a, union_b, w), _mark_cover(union_b, union_a, w)) >= settings.RESOLVE_BLOCK_COVER:
            open_a = [i for i in ia if i not in links]
            open_b = [j for j in jb if j not in used]
            if open_a or open_b:
                out.append((open_a, open_b, ia, jb))
    return out


def _sheet_key(f: PageFeatures) -> tuple[int, ...] | None:
    numbers = re.findall(r"\d+", f.sheet_no or "")
    return tuple(int(n) for n in numbers) if numbers else None


def _group_order(pages: list[PageFeatures], indices: list[int]) -> dict[int, int]:
    """resolve.py:402-410: the place of a sheet in its group: by the stamp's sheet number if every sheet of the group
    has one (specification sheets can be out of order in the PDF), otherwise by page number."""
    keys = {i: _sheet_key(pages[i]) for i in indices}
    if all(keys.values()):
        ordered = sorted(indices, key=lambda i: (keys[i], pages[i].page))  # type: ignore[arg-type,return-value]
    else:
        ordered = sorted(indices, key=lambda i: pages[i].page)
    return {i: k for k, i in enumerate(ordered)}


def _increasing(pairs: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """resolve.py:413-428: the longest subsequence of pairs increasing in both (the pairs are ordered by the first)."""
    if not pairs:
        return []
    best = [1] * len(pairs)
    back = [-1] * len(pairs)
    for k in range(len(pairs)):
        for q in range(k):
            if pairs[q][1] < pairs[k][1] and pairs[q][0] < pairs[k][0] and best[q] + 1 > best[k]:
                best[k], back[k] = best[q] + 1, q
    k = max(range(len(pairs)), key=lambda x: best[x])
    out: list[tuple[int, int]] = []
    while k >= 0:
        out.append(pairs[k])
        k = back[k]
    return out[::-1]


def _group_pairs(
    open_a: list[int],
    open_b: list[int],
    ia: list[int],
    jb: list[int],
    links: dict[int, Link],
    floor: np.ndarray,
    order_a: dict[int, int] | None = None,
    order_b: dict[int, int] | None = None,
) -> dict[int, int]:
    """resolve.py:431-449 (rule ``group``): the unresolved sheets of a group are linked in order between the accepted
    pairs of the group (the anchors: the longest accepted chain that runs in order; a pair found by content across the
    order stays as it is and does not break the group). Surplus sheets at the end of a segment get no pair."""
    oa = order_a or {i: i for i in ia}
    ob = order_b or {j: j for j in jb}
    anchors = _increasing(sorted((oa[i], ob[links[i][0]]) for i in ia if i in links and links[i][0] in jb))
    bounds = [(-1, -1)] + anchors + [(10**9, 10**9)]
    out: dict[int, int] = {}
    for (la, lb), (ra, rb) in zip(bounds, bounds[1:]):
        segment_a = sorted((i for i in open_a if la < oa[i] < ra), key=oa.get)  # type: ignore[arg-type]
        segment_b = sorted((j for j in open_b if lb < ob[j] < rb), key=ob.get)  # type: ignore[arg-type]
        for i, j in zip(segment_a, segment_b):
            if floor[i, j]:
                out[i] = j
    return out


def package_map(
    prev: list[PageFeatures], cur: list[PageFeatures], links: dict[int, Link]
) -> tuple[dict[str, str], dict[str, str]]:
    """resolve.py:452-471: the designation correspondence of the confident pairs: A's designation -> B's, when at least
    ``RESOLVE_PACKAGE_MIN`` pairs and ``RESOLVE_PACKAGE_SHARE`` of that designation's pairs say so."""
    forward: dict[str, Counter[str]] = defaultdict(Counter)
    for i, (j, _s, _p) in links.items():
        da, db = prev[i].designation, cur[j].designation
        if da and db:
            forward[da][db] += 1
    mapping: dict[str, str] = {}
    reverse: dict[str, str] = {}
    for da, counter in forward.items():
        db, n = counter.most_common(1)[0]
        if n >= settings.RESOLVE_PACKAGE_MIN and n / sum(counter.values()) >= settings.RESOLVE_PACKAGE_SHARE:
            mapping[da] = db
    back: dict[str, Counter[str]] = defaultdict(Counter)
    for da, db in mapping.items():
        back[db][da] += forward[da][db]
    for db, counter in back.items():
        if len(counter) == 1:
            reverse[db] = next(iter(counter))
    return mapping, reverse


def package_conflict(a: PageFeatures, b: PageFeatures, pmap: tuple[dict[str, str], dict[str, str]]) -> bool:
    """resolve.py:474-481 (rule ``package``): contradiction on both sides: A's designation steadily becomes another
    designation of B, and B's designation steadily comes from another designation of A."""
    mapping, reverse = pmap
    if not a.designation or not b.designation:
        return False
    return (a.designation in mapping and mapping[a.designation] != b.designation) and (
        b.designation in reverse and reverse[b.designation] != a.designation
    )


def resolve(
    prev: list[PageFeatures],
    cur: list[PageFeatures],
    similarity: np.ndarray,
    parts_all: dict[tuple[int, int], dict[str, Any]],
    links: dict[int, Link],
    rules: frozenset[str],
) -> tuple[dict[int, Link], dict[tuple[str, int], Any]]:
    """resolve.py:484-573: add the proven pairs to those of the main assignment. Returns ``(links, reasons)`` where
    reasons maps (side ``a``/``b``, index) to a reason code (``block`` also carries a detail, dropped by the caller)."""
    n, m = len(prev), len(cur)
    w = weights(prev + cur)
    titles_prev = Counter(_title_key(f) for f in prev if _title_key(f))
    titles_cur = Counter(_title_key(f) for f in cur if _title_key(f))
    foot = (footer_counts(prev), footer_counts(cur)) if "pageno" in rules else None
    floor = similarity >= MATCH_CANDIDATE_FLOOR
    pmap = package_map(prev, cur, links) if "package" in rules else ({}, {})
    taken_columns = {j for j, _s, _p in links.values()}
    expect_a, expect_b = _expected(prev, cur, links)
    reasons: dict[tuple[str, int], Any] = {}
    out = dict(links)
    # Sheets of different permits are not linked, also not by the main assignment.
    for i, (j, _s, _p) in list(out.items()):
        if "permit" in rules and permit_conflict(prev[i], cur[j]):
            del out[i]
            taken_columns.discard(j)
            reasons[("a", i)] = reasons[("b", j)] = "permit"
    # A pair already accepted is not withdrawn by the package check: designations in real stamps are unstable.
    decided: dict[int, tuple[int, str]] = {}
    for i in range(n):
        if i in out:
            continue
        candidates = [j for j in range(m) if floor[i, j]]
        if not candidates:
            continue
        best_i, how = _winner(prev[i], [cur[j] for j in candidates], w, (titles_prev, titles_cur), foot, expect_a.get(i))
        if best_i is None:
            reasons[("a", i)] = how
            continue
        j = candidates[best_i]
        if j in taken_columns:
            reasons[("a", i)] = "taken"
            continue
        if similarity[i, j] < MATCH_MEDIUM:
            reasons[("a", i)] = "below_pair"
            continue
        column_candidates = [ii for ii in range(n) if floor[ii, j]]
        best_j, how_b = _winner(
            cur[j], [prev[ii] for ii in column_candidates], w, (titles_cur, titles_prev), foot[::-1] if foot else None,
            expect_b.get(j),
        )
        if best_j is None or column_candidates[best_j] != i:
            reasons[("a", i)] = "not_mutual"
            continue
        if "permit" in rules and permit_conflict(prev[i], cur[j]):
            reasons[("a", i)] = "permit"
            continue
        if "title" in (how, how_b) and not _content_supports(parts_all[(i, j)]):
            reasons[("a", i)] = "title_only"
            continue
        if how == how_b == "single":
            reasons[("a", i)] = "weak"
            continue
        if (prev[i].kind in TABLE_KINDS or cur[j].kind in TABLE_KINDS) and min(
            _mark_cover(set(prev[i].tokens), set(cur[j].tokens), w),
            _mark_cover(set(cur[j].tokens), set(prev[i].tokens), w),
        ) < settings.RESOLVE_TABLE_COVER:
            reasons[("a", i)] = "block"
            continue
        if "package" in rules and package_conflict(prev[i], cur[j], pmap):
            reasons[("a", i)] = "package"
            continue
        decided[i] = (j, how if how != "single" else how_b)
    for i, (j, how) in decided.items():
        out[i] = (j, float(similarity[i, j]), parts_all[(i, j)] | {"resolved": how})
        reasons.pop(("a", i), None)
    used = {j for j, _s, _p in out.values()}
    for open_a, open_b, ia, jb in _blocks(prev, cur, similarity, out, used, w):
        paired = (
            _group_pairs(open_a, open_b, ia, jb, out, floor, _group_order(prev, ia), _group_order(cur, jb))
            if "group" in rules
            else {}
        )
        for i, j in paired.items():
            # Membership of a group of table sheets, not a "sheet for sheet" pair: the comparison is by positions.
            out[i] = (j, float(similarity[i, j]), parts_all[(i, j)] | {"resolved": "group"})
            used.add(j)
            reasons.pop(("a", i), None)
        for i in open_a:
            if i not in paired:
                reasons[("a", i)] = "block"
        for j in open_b:
            if j not in used:
                reasons[("b", j)] = "block"
    for j in range(m):
        if j not in used and ("b", j) not in reasons and floor[:, j].any():
            # The B side takes the reason of the A page its best candidate points at.
            i = int(np.argmax(similarity[:, j]))
            reasons[("b", j)] = reasons.get(("a", i), "weak")
    return out, reasons
