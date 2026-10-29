"""Moved blocks (port of ``blocks.py`` of the original, plan section 5 step 3.4, stage 2).

`CMP-ENGINE-01`. After the common registration a part of a sheet can have moved as a whole (a table put in another
place). Without this step it looks like «removed + added». Here:

1. from the same words «only in A» / «only in B» (and the moved ones) groups of at least ``BLOCK_MIN_WORDS`` words that
   share a vector (within ``BLOCK_TOL_PT``, at least ``BLOCK_MIN_SHIFT_PT`` long) are found (:func:`find`, ``blocks.py:33-83``);
2. a group is confirmed by the raster: the pixels «only A» in the block, shifted by the vector, agree with the pixels
   «only B» (a share of at least ``BLOCK_MIN_IOU``, :func:`confirm`, ``blocks.py:112-184``);
3. the pixels the shift explains leave «only A/B» for the layer «moved»; the rest inside the block stays an ordinary
   difference (a change inside a moved block).

The main overlay is not deformed: the shift only decides the class of the pixels. The original works on whole-canvas
arrays; here every operation is on a **window** of the plane store around the block and its new place, so a block
costs the memory of its own window. A block whose window passes ``MAX_WINDOW_PIXELS`` is not confirmed: its pixels
stay ordinary differences, which can only report more, never less.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

import cv2
import numpy

from . import settings
from .geometry import Canvas
from .planes import PlaneStore
from .words import center

__all__ = ["MAX_WINDOW_PIXELS", "confirm", "find"]

MAX_WINDOW_PIXELS = 4_000_000
_EXTEND_WINDOW_PIXELS = 4_000_000
_K5 = numpy.ones((5, 5), numpy.uint8)


def find(words_cmp: dict[str, Any]) -> list[dict[str, Any]]:
    """Candidates for moved blocks from the words: ``[{vector, a_words, b_words}]`` (``blocks.py:33-83``)."""
    pairs: list[tuple[float, float, dict, dict]] = []
    by_text_a: dict[str, list[dict]] = defaultdict(list)
    by_text_b: dict[str, list[dict]] = defaultdict(list)
    for w in words_cmp["only_a"]:
        by_text_a[w["text"]].append(w)
    for w in words_cmp["only_b"]:
        by_text_b[w["text"]].append(w)
    for text, la in by_text_a.items():
        lb = by_text_b.get(text, [])
        if not lb or len(la) * len(lb) > 16:
            continue
        for wa in la:
            for wb in lb:
                (ax, ay), (bx, by) = center(wa["pt"]), center(wb["pt"])
                pairs.append((bx - ax, by - ay, wa, wb))
    for mv in words_cmp["moved"]:
        (ax, ay), (bx, by) = center(mv["a_pt"]), center(mv["b_in_a_pt"])
        pairs.append((bx - ax, by - ay, {"text": mv["text"], "pt": mv["a_pt"], "dir": mv.get("dir")},
                      {"text": mv["text"], "pt": mv["b_in_a_pt"], "dir": mv.get("dir")}))
    tol = settings.BLOCK_TOL_PT
    found: list[dict[str, Any]] = []
    used: set[int] = set()
    while True:
        votes = Counter((round(dx / tol), round(dy / tol)) for i, (dx, dy, _a, _b) in enumerate(pairs) if i not in used)
        if not votes:
            break
        (kx, ky), n = votes.most_common(1)[0]
        if n < settings.BLOCK_MIN_WORDS:
            break
        cx, cy = kx * tol, ky * tol
        members = [i for i, (dx, dy, _a, _b) in enumerate(pairs)
                   if i not in used and abs(dx - cx) <= tol and abs(dy - cy) <= tol]
        used.update(members)
        dx = float(numpy.median([pairs[i][0] for i in members]))
        dy = float(numpy.median([pairs[i][1] for i in members]))
        if (dx * dx + dy * dy) ** 0.5 < settings.BLOCK_MIN_SHIFT_PT:
            continue
        seen_a: set[int] = set()
        seen_b: set[int] = set()
        kept: list[int] = []
        for i in members:
            a, b = pairs[i][2], pairs[i][3]
            if id(a) in seen_a or id(b) in seen_b:
                continue
            seen_a.add(id(a))
            seen_b.add(id(b))
            kept.append(i)
        if len(kept) >= settings.BLOCK_MIN_WORDS:
            found.append({"vector": [dx, dy], "a_words": [pairs[i][2] for i in kept], "b_words": [pairs[i][3] for i in kept]})
    return found


def _union(rects: list[list[float]]) -> list[float]:
    return [min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects)]


def _touching_box(store: PlaneStore, name: str, rect: tuple[int, int, int, int]) -> list[int] | None:
    """The extent of the components of a plane that touch ``rect``, searched in a window around it (``blocks.py:90-104``)."""
    x0, y0, x1, y1 = rect
    bw, bh = x1 - x0, y1 - y0
    X0, Y0, X1, Y1 = max(0, x0 - bw), max(0, y0 - bh), min(store.width, x1 + bw), min(store.height, y1 + bh)
    if X1 <= X0 or Y1 <= Y0 or (X1 - X0) * (Y1 - Y0) > _EXTEND_WINDOW_PIXELS:
        return None
    window = store.window(name, X0, Y0, X1, Y1)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(window, connectivity=8)
    inner = labels[max(0, y0 - Y0) : max(0, y1 - Y0), max(0, x0 - X0) : max(0, x1 - X0)]
    ids = [int(v) for v in numpy.unique(inner) if v > 0]
    if not ids:
        return None
    return [X0 + min(int(stats[i][0]) for i in ids), Y0 + min(int(stats[i][1]) for i in ids),
            X0 + max(int(stats[i][0] + stats[i][2]) for i in ids), Y0 + max(int(stats[i][1] + stats[i][3]) for i in ids)]


def _shift(mask: Any, dx: int, dy: int) -> Any:
    """``mask`` moved by whole pixels, the vacated places zero (``warpAffine`` with nearest neighbour in the original)."""
    out = numpy.zeros_like(mask)
    h, w = mask.shape
    sx0, sx1 = max(0, -dx), min(w, w - dx)
    sy0, sy1 = max(0, -dy), min(h, h - dy)
    if sx1 > sx0 and sy1 > sy0:
        out[sy0 + dy : sy1 + dy, sx0 + dx : sx1 + dx] = mask[sy0:sy1, sx0:sx1]
    return out


def confirm(candidates: list[dict[str, Any]], store: PlaneStore, canvas: Canvas) -> list[dict[str, Any]]:
    """The raster check of the candidates; the plane store is changed in place (``blocks.py:112-184``).

    ``a_only`` and ``b_only`` lose the pixels the shift explains, ``moved`` gains them. A word moves at most once:
    the candidates come in the order of :func:`find` (more words first) and a word taken by a confirmed block is not
    offered to the next, or one line of A would move onto its own place and onto a new line of B at once (``blocks.py:123-127``).
    """
    out: list[dict[str, Any]] = []
    claimed_a: set[int] = set()
    claimed_b: set[int] = set()
    s = canvas.s
    pad_pt = 3.0 * 72.0 / 25.4
    for blk in candidates:
        keep = [i for i, (wa, wb) in enumerate(zip(blk["a_words"], blk["b_words"]))
                if id(wa) not in claimed_a and id(wb) not in claimed_b]
        if len(keep) < settings.BLOCK_MIN_WORDS:
            continue
        if len(keep) < len(blk["a_words"]):
            blk = blk | {"a_words": [blk["a_words"][i] for i in keep], "b_words": [blk["b_words"][i] for i in keep]}
        ra = _union([x["pt"] for x in blk["a_words"]])
        ra = [ra[0] - pad_pt, ra[1] - pad_pt, ra[2] + pad_pt, ra[3] + pad_pt]
        x0, y0, x1, y1 = canvas.px(ra)
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(store.width, x1), min(store.height, y1)
        if x1 <= x0 or y1 <= y0:
            continue
        dxp, dyp = int(round(blk["vector"][0] * s)), int(round(blk["vector"][1] * s))
        ext = [_touching_box(store, "a_only", (x0, y0, x1, y1)),
               _touching_box(store, "b_only", (x0 + dxp, y0 + dyp, x1 + dxp, y1 + dyp))]
        bx = [x0, y0, x1, y1]
        for k, eb in enumerate(ext):
            if eb is not None:
                sx, sy = (0, 0) if k == 0 else (dxp, dyp)
                bx = [min(bx[0], eb[0] - sx), min(bx[1], eb[1] - sy), max(bx[2], eb[2] - sx), max(bx[3], eb[3] - sy)]
        if (bx[2] - bx[0]) * (bx[3] - bx[1]) <= 4 * (x1 - x0) * (y1 - y0):
            x0, y0, x1, y1 = max(0, bx[0]), max(0, bx[1]), min(store.width, bx[2]), min(store.height, bx[3])
            ra = canvas.pt([x0, y0, x1, y1])
        # The window holds the block at its place in A and at its new place in B, with room for the 5 x 5 dilation.
        wx0, wy0 = max(0, min(x0, x0 + dxp) - 3), max(0, min(y0, y0 + dyp) - 3)
        wx1, wy1 = min(store.width, max(x1, x1 + dxp) + 3), min(store.height, max(y1, y1 + dyp) + 3)
        if wx1 <= wx0 or wy1 <= wy0 or (wx1 - wx0) * (wy1 - wy0) > MAX_WINDOW_PIXELS:
            continue
        win = {name: store.window(name, wx0, wy0, wx1, wy1) for name in ("a_only", "b_only", "dark_a", "dark_b")}
        region = numpy.zeros_like(win["a_only"])
        region[y0 - wy0 : y1 - wy0, x0 - wx0 : x1 - wx0] = 1
        a_blk = win["a_only"] & region
        region_b = _shift(region, dxp, dyp)
        b_blk = win["b_only"] & region_b
        expl_b = b_blk & cv2.dilate(_shift(win["dark_a"] & region, dxp, dyp), _K5)
        expl_a = a_blk & _shift(cv2.dilate(win["dark_b"] & region_b, _K5), -dxp, -dyp)
        total = int(a_blk.sum()) + int(b_blk.sum())
        share = (int(expl_a.sum()) + int(expl_b.sum())) / total if total else 0.0
        if share < settings.BLOCK_MIN_IOU:
            continue
        store.put_window("a_only", wx0, wy0, win["a_only"] & (1 - expl_a))
        store.put_window("b_only", wx0, wy0, win["b_only"] & (1 - expl_b))
        store.or_window("moved", wx0, wy0, expl_a | expl_b)
        vx, vy = blk["vector"]
        rb = [ra[0] + vx, ra[1] + vy, ra[2] + vx, ra[3] + vy]
        claimed_a.update(id(x) for x in blk["a_words"])
        claimed_b.update(id(x) for x in blk["b_words"])
        out.append(blk | {"bbox_a_pt": [round(v, 2) for v in ra], "bbox_b_in_a_pt": [round(v, 2) for v in rb],
                          "share": round(share, 3)})
    return out
