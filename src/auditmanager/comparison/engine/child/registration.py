"""Registration of the page of B onto the page of A (port of ``registration.py`` of the original, plan section 5 step 3).

`CMP-ENGINE-01`. Only a similarity: scale, rotation, shift, no local deformation.

1. **Anchors**: words that are unique on both pages and lie outside the service zones, ``cv2.estimateAffinePartial2D``
   with RANSAC over their centres (``registration.py:62-83``).
2. **Fallback**: phase correlation of the 36 dpi ink masks, a shift only (``:86-99``).
3. **Check**: how well the masks agree after the registration (Dice, ``:102-119``).

The work is done on the **downsampled raster** of the profile (the 36 dpi ink mask, 1/5.6 of the 200 dpi canvas),
never on the full-resolution render. The matrix goes from points of B (the frame of the displayed page) to points of A.
Line numbers are those of the original at ``23f379fd``.
"""

from __future__ import annotations

import math
import unicodedata
from collections import Counter
from collections.abc import Sequence
from typing import Any

import cv2
import numpy

from . import settings
from .geometry import identity

__all__ = ["by_anchors", "by_phase", "dice", "normalize_token", "register"]


def normalize_token(text: str) -> str:
    """Normalisation for matching words (``pdfio.py:46``), not for showing differences."""
    import re

    text = unicodedata.normalize("NFKC", text or "").strip().lower()
    return re.sub(r"\s+", " ", text)


def _inside_any(cx: float, cy: float, rects: Sequence[Sequence[float]]) -> bool:
    return any(r[0] <= cx <= r[2] and r[1] <= cy <= r[3] for r in rects)


def _anchors(words: Sequence[Sequence[Any]], zones: Sequence[Sequence[float]]) -> dict[str, tuple[float, float]]:
    texts: Counter[str] = Counter()
    keep: list[tuple[str, float, float]] = []
    for w in words:
        token = normalize_token(str(w[4]))
        if len(token) < 3 or not any(ch.isalnum() for ch in token):
            continue
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        if _inside_any(cx, cy, zones):
            continue
        texts[token] += 1
        keep.append((token, cx, cy))
    return {t: (cx, cy) for t, cx, cy in keep if texts[t] == 1}


def _decompose(m: Any) -> dict[str, float]:
    return {
        "scale": math.hypot(m[0, 0], m[1, 0]),
        "rot_deg": math.degrees(math.atan2(m[1, 0], m[0, 0])),
        "dx": float(m[0, 2]),
        "dy": float(m[1, 2]),
    }


def _snap(m: Any) -> tuple[Any, bool]:
    """A matrix that is the identity (to a tenth of a point) or a pure shift is made exactly that (``:53-59``)."""
    d = _decompose(m)
    if abs(d["scale"] - 1) < 1e-3 and abs(d["rot_deg"]) < 0.05 and abs(d["dx"]) < 0.5 and abs(d["dy"]) < 0.5:
        return identity(), True
    if abs(d["scale"] - 1) < 1e-3 and abs(d["rot_deg"]) < 0.05:
        return numpy.array([[1.0, 0.0, d["dx"]], [0.0, 1.0, d["dy"]]]), False
    return m, False


def similarity_ransac(src: Any, dst: Any, threshold: float, iterations: int = 3000) -> tuple[Any, Any]:
    """A similarity (scale, rotation, shift) from ``src`` points onto ``dst`` points by RANSAC over pairs of points,
    refined on its inliers by least squares: what ``cv2.estimateAffinePartial2D(..., method=cv2.RANSAC)`` returns.

    The OpenCV call reserves 136 MiB of address space the first time it runs, which is a sixth of the ceiling, so the
    few lines it stands for are written out here. A point is ``x + iy``; a similarity is ``z -> a z + b``."""
    n = len(src)
    zs, zd = src[:, 0] + 1j * src[:, 1], dst[:, 0] + 1j * dst[:, 1]
    if n > 3000:
        keep = numpy.random.default_rng(1).choice(n, 3000, replace=False)
        zs, zd = zs[keep], zd[keep]
        n = 3000
    rng = numpy.random.default_rng(0)
    best_count, best = 0, None
    for _ in range(0, iterations, 250):
        i, j = rng.integers(0, n, 250), rng.integers(0, n, 250)
        dz = zs[j] - zs[i]
        ok = (i != j) & (numpy.abs(dz) > 1e-6)
        i, j, dz = i[ok], j[ok], dz[ok]
        if not len(i):
            continue
        a = (zd[j] - zd[i]) / dz
        b = zd[i] - a * zs[i]
        counts = (numpy.abs(a[:, None] * zs[None, :] + b[:, None] - zd[None, :]) <= threshold).sum(axis=1)
        k = int(numpy.argmax(counts))
        if counts[k] > best_count:
            best_count, best = int(counts[k]), (a[k], b[k])
    if best is None or best_count < 3:
        return None, None
    a, b = best
    for _ in range(3):  # refit on the inliers, twice more with the improved transform
        inliers = numpy.abs(a * zs + b - zd) <= threshold
        if int(inliers.sum()) < 3:
            return None, None
        ms, md = zs[inliers].mean(), zd[inliers].mean()
        ds = zs[inliers] - ms
        denominator = float((numpy.abs(ds) ** 2).sum())
        if denominator < 1e-9:
            return None, None
        a = (numpy.conj(ds) * (zd[inliers] - md)).sum() / denominator
        b = md - a * ms
    matrix = numpy.array([[a.real, -a.imag, b.real], [a.imag, a.real, b.imag]])
    full = (src[:, 0] + 1j * src[:, 1])
    inliers = numpy.abs(a * full + b - (dst[:, 0] + 1j * dst[:, 1])) <= threshold
    return matrix, inliers.astype(numpy.uint8).reshape(-1, 1)


def by_anchors(words_a: Any, words_b: Any, zones_a: Any, zones_b: Any) -> dict[str, Any]:
    aa, bb = _anchors(words_a, zones_a), _anchors(words_b, zones_b)
    common = [t for t in aa if t in bb]
    if len(common) < 3:
        return {"method": "anchors", "accepted": False, "anchors": len(common), "reason": "few common words"}
    src = numpy.array([bb[t] for t in common], dtype=numpy.float64)
    dst = numpy.array([aa[t] for t in common], dtype=numpy.float64)
    m, inl = similarity_ransac(src, dst, settings.ANCHOR_RANSAC_PT)
    if m is None or inl is None:
        return {"method": "anchors", "accepted": False, "anchors": len(common), "reason": "RANSAC did not converge"}
    inl = inl.ravel().astype(bool)
    proj = src @ m[:, :2].T + m[:, 2]
    res = numpy.hypot(*(proj - dst).T)
    inliers = int(inl.sum())
    median = float(numpy.median(res[inl])) if inliers else 1e9
    need = max(settings.ANCHOR_MIN_INLIERS, int(math.ceil(settings.ANCHOR_MIN_RATIO * len(common))))
    accepted = inliers >= need and median <= settings.ANCHOR_MAX_MEDIAN_RESIDUAL_PT
    snapped, is_identity = _snap(m)
    return {
        "method": "anchors", "accepted": bool(accepted), "anchors": len(common), "inliers": inliers,
        "median_residual_pt": round(median, 3), "matrix": snapped.tolist(), "identity": is_identity,
    }


def _pool(mask: Any, factor: int) -> Any:
    """The mask reduced by an integer factor, a pixel is ink if any pixel of its block is (so thin lines stay)."""
    if factor == 1:
        return mask
    pad_h, pad_w = (-mask.shape[0]) % factor, (-mask.shape[1]) % factor
    if pad_h or pad_w:
        mask = numpy.pad(mask, ((0, pad_h), (0, pad_w)))
    h, w = mask.shape
    return mask.reshape(h // factor, factor, w // factor, factor).max(axis=(1, 3))


def by_phase(mask_a: Any, mask_b: Any, dpi: int) -> dict[str, Any]:
    """The shift of B onto A by phase correlation. A mask over ``PHASE_MAX_PIXELS`` is reduced first (a transform of a
    4 Mpx mask needs 180 MiB of address space, which the ceiling of 768 MiB cannot spare); the shift is then
    known to a point or two, which the vector lines refine (:func:`refine_by_lines`)."""
    h = max(mask_a.shape[0], mask_b.shape[0])
    w = max(mask_a.shape[1], mask_b.shape[1])
    factor = 1
    while (h // factor) * (w // factor) > settings.PHASE_MAX_PIXELS:
        factor += 1
    if factor > 1:
        mask_a, mask_b = _pool(mask_a, factor), _pool(mask_b, factor)
        h, w = max(mask_a.shape[0], mask_b.shape[0]), max(mask_a.shape[1], mask_b.shape[1])
    a = numpy.zeros((h, w), numpy.float32)
    b = numpy.zeros((h, w), numpy.float32)
    a[: mask_a.shape[0], : mask_a.shape[1]] = mask_a
    b[: mask_b.shape[0], : mask_b.shape[1]] = mask_b
    win = cv2.createHanningWindow((w, h), cv2.CV_32F)
    (dx, dy), response = cv2.phaseCorrelate(b * win, a * win)
    del win, a, b
    dx, dy = dx * factor, dy * factor
    k = 72.0 / dpi
    snapped, is_identity = _snap(numpy.array([[1.0, 0.0, dx * k], [0.0, 1.0, dy * k]]))
    return {"method": "phase", "accepted": bool(response > 0.05), "response": round(float(response), 4),
            "matrix": snapped.tolist(), "identity": is_identity}


def _corners(lines: Any) -> Any:
    """The two corners of the box of each line, ``(2n, 2)``: a line of the page is the same line on the other page
    whatever its direction, and its corners move with it."""
    lines = numpy.asarray(lines, dtype=numpy.float64).reshape(-1, 4)
    return numpy.concatenate([lines[:, [0, 1]], lines[:, [2, 3]]])


def refine_by_lines(lines_a: Any, lines_b: Any, matrix: Any) -> dict[str, Any] | None:
    """The shift that carries the vector lines of B onto those of A, to a tenth of a point, near ``matrix``.

    A drawing re-issued with its coordinates unchanged (or moved as a whole) has the same lines at the same distance
    from each other, so the corners of A's lines minus the corners of B's lines (B already carried by ``matrix``)
    agree on one vector, the true shift, in a clear majority of the pairs that lie within ``LINES_SEARCH_PT``; the
    pairs that do not belong to it spread over the plane. The vector is the most voted bin of a histogram, refined by
    the median of its members; it is accepted only with ``LINES_MIN_VOTES`` votes and ``LINES_MIN_SHARE`` of the
    points. The phase correlation of the masks is good to a point or two; this makes it exact on vector sheets.
    Only a pure shift is refined: the linear part of ``matrix`` must be the identity.
    """
    m = numpy.array(matrix, dtype=numpy.float64)
    if not numpy.allclose(m[:, :2], numpy.eye(2), atol=1e-6) or lines_a is None or lines_b is None:
        return None
    pa, pb = _corners(lines_a), _corners(lines_b)
    if len(pa) < settings.LINES_MIN_VOTES or len(pb) < settings.LINES_MIN_VOTES:
        return None
    rng = numpy.random.default_rng(0)
    if len(pa) > settings.LINES_MAX_POINTS:
        pa = pa[rng.choice(len(pa), settings.LINES_MAX_POINTS, replace=False)]
    if len(pb) > settings.LINES_MAX_POINTS * 2:
        pb = pb[rng.choice(len(pb), settings.LINES_MAX_POINTS * 2, replace=False)]
    pb = pb + m[:, 2]
    radius = settings.LINES_SEARCH_PT
    step = settings.LINES_BIN_PT
    side = int(math.ceil(2 * radius / step)) + 1
    cell = radius
    big = 1_000_003
    keys_b = numpy.floor(pb[:, 0] / cell).astype(numpy.int64) * big + numpy.floor(pb[:, 1] / cell).astype(numpy.int64)
    order = numpy.argsort(keys_b, kind="stable")
    sorted_keys = keys_b[order]
    cxa = numpy.floor(pa[:, 0] / cell).astype(numpy.int64)
    cya = numpy.floor(pa[:, 1] / cell).astype(numpy.int64)
    spans = []
    total = 0
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            target = (cxa + di) * big + (cya + dj)
            lo = numpy.searchsorted(sorted_keys, target, side="left")
            counts = numpy.searchsorted(sorted_keys, target, side="right") - lo
            total += int(counts.sum())
            if total > 1_500_000:
                return None  # a hatch: every point has a thousand neighbours and the vote means nothing
            spans.append((lo, counts))

    def displacements(lo: Any, counts: Any) -> Any:
        n = int(counts.sum())
        if not n:
            return numpy.empty((0, 2))
        ia = numpy.repeat(numpy.arange(len(pa)), counts)
        offsets = numpy.arange(n) - numpy.repeat(numpy.cumsum(counts) - counts, counts)
        d = pa[ia] - pb[order[numpy.repeat(lo, counts) + offsets]]
        return d[(numpy.abs(d[:, 0]) <= radius) & (numpy.abs(d[:, 1]) <= radius)]

    # First pass: a two-dimensional histogram of the displacements (side x side bins), no list of pairs is kept.
    histogram = numpy.zeros(side * side, dtype=numpy.int64)
    for lo, counts in spans:
        d = displacements(lo, counts)
        if len(d):
            bins = numpy.floor((d + radius) / step).astype(numpy.int64)
            histogram += numpy.bincount(bins[:, 0] * side + bins[:, 1], minlength=side * side)
    grid = histogram.reshape(side, side).astype(numpy.float32)
    window = cv2.blur(grid, (3, 3), borderType=cv2.BORDER_CONSTANT) * 9.0  # votes of a 3 x 3 window of bins
    peak = numpy.unravel_index(int(numpy.argmax(window)), window.shape)
    votes = int(round(float(window[peak])))
    if votes < max(settings.LINES_MIN_VOTES, int(settings.LINES_MIN_SHARE * min(len(pa), len(pb)))):
        return None
    # The peak must stand out: a periodic drawing (a hatch, a grid of equal cells) agrees with itself at many shifts, and
    # then no shift is the shift. Half a point around the peak is left out and the next highest bin must have at most half
    # of its votes.
    reach = int(round(0.5 / step))
    rest = window.copy()
    rest[max(0, peak[0] - reach) : peak[0] + reach + 1, max(0, peak[1] - reach) : peak[1] + reach + 1] = 0
    if votes < settings.LINES_PEAK_RATIO * float(rest.max()):
        return None
    # Second pass: the members of the peak, whose median is the shift.
    low = numpy.array([(peak[0] - 1) * step - radius, (peak[1] - 1) * step - radius])
    members = []
    for lo, counts in spans:
        d = displacements(lo, counts)
        if len(d):
            members.append(d[(d >= low).all(axis=1) & (d < low + 3 * step).all(axis=1)])
    d = numpy.concatenate(members)
    delta = numpy.median(d, axis=0)
    refined = m.copy()
    refined[:, 2] = m[:, 2] + delta
    return {"method": "lines", "accepted": True, "votes": votes, "points": int(min(len(pa), len(pb))),
            "matrix": refined.tolist(), "delta_pt": [round(float(delta[0]), 3), round(float(delta[1]), 3)]}


def dice(mask_a: Any, mask_b: Any, matrix: Any, dpi: int, zones_a: Sequence[Sequence[float]]) -> float:
    """How well the ink masks agree after B is carried onto A, with a tolerance of one pixel (``:102-119``)."""
    k = dpi / 72.0
    m = numpy.array(matrix, dtype=numpy.float64).copy()
    m[:, 2] *= k
    warped = cv2.warpAffine(mask_b, m, (mask_a.shape[1], mask_a.shape[0]), flags=cv2.INTER_NEAREST)
    a = mask_a.copy()
    for z in zones_a:
        a[int(z[1] * k) : int(z[3] * k) + 1, int(z[0] * k) : int(z[2] * k) + 1] = 0
        warped[int(z[1] * k) : int(z[3] * k) + 1, int(z[0] * k) : int(z[2] * k) + 1] = 0
    kernel = numpy.ones((3, 3), numpy.uint8)
    inter_a = int((a & cv2.dilate(warped, kernel)).sum())
    inter_b = int((warped & cv2.dilate(a, kernel)).sum())
    total = int(a.sum()) + int(warped.sum())
    if total == 0:
        return 1.0
    return (inter_a + inter_b) / total


def register(
    words_a: Any, words_b: Any, zones_a: Any, zones_b: Any, mask_a: Any, mask_b: Any, mask_dpi: int,
    lines_a: Any = None, lines_b: Any = None,
) -> dict[str, Any]:
    """The final transform of B onto A, with the method, its quality and the attempts (``:122-157``)."""
    anchor = by_anchors(words_a, words_b, zones_a, zones_b)
    chosen = anchor if anchor.get("accepted") else None
    tried: list[dict[str, Any]] = [anchor]
    if chosen is None and mask_a is not None and mask_b is not None:
        phase = by_phase(mask_a, mask_b, mask_dpi)
        tried.append(phase)
        if phase["accepted"]:
            chosen = phase
    if chosen is None:
        chosen = {"method": "identity", "accepted": False, "matrix": identity().tolist(), "identity": True}
    matrix = numpy.array(chosen["matrix"])
    if chosen["method"] == "phase" and not chosen.get("identity") and mask_a is not None and mask_b is not None:
        # The estimate of the correlation is good to half a pixel of the mask (a point at 36 dpi); the pages may be the
        # same: as is is kept when it agrees with the drawing as well as the estimate does.
        if dice(mask_a, mask_b, identity(), mask_dpi, zones_a) >= dice(mask_a, mask_b, matrix, mask_dpi, zones_a) - 0.005:
            chosen = {"method": "phase", "accepted": True, "matrix": identity().tolist(), "identity": True,
                      "response": chosen.get("response")}
            matrix = identity()
    if chosen["method"] in ("phase", "identity") and lines_a is not None and lines_b is not None:
        refined = refine_by_lines(lines_a, lines_b, matrix)
        if refined is not None:
            tried.append({k: v for k, v in refined.items() if k != "matrix"})
            exact = numpy.array(refined["matrix"])
            snapped, is_identity = (identity(), True) if numpy.hypot(*exact[:, 2]) < 0.05 else (exact, False)
            chosen = {"method": "lines", "accepted": True, "matrix": snapped.tolist(), "identity": is_identity}
            matrix = snapped
    quality = dice(mask_a, mask_b, matrix, mask_dpi, zones_a) if mask_a is not None and mask_b is not None else None
    if chosen["method"] == "anchors" and not chosen.get("identity") and quality is not None and quality < settings.ALIGN_MIN_DICE:
        # The anchors may have met on a part of the sheet that moved as a whole; "as is" is checked against the
        # drawing and taken when clearly better (``:136-147``).
        q_id = dice(mask_a, mask_b, identity(), mask_dpi, zones_a)
        tried.append({"method": "identity_check", "dice36": round(q_id, 4), "accepted": False})
        if q_id >= quality + settings.ALIGN_SWITCH_MARGIN:
            tried[-1]["accepted"] = True
            chosen = {"method": "identity", "accepted": True, "matrix": identity().tolist(), "identity": True,
                      "reason": "only part of the sheet agreed by the anchors; as is the drawing agrees better"}
            matrix, quality = identity(), q_id
    reliable = bool(chosen.get("accepted")) and (chosen["method"] == "anchors" or (quality or 0) >= settings.ALIGN_MIN_DICE)
    if chosen.get("reason"):
        reliable = True
    out: dict[str, Any] = {
        "method": chosen["method"], "matrix": matrix.tolist(), "identity": bool(chosen.get("identity")),
        "reliable": reliable, "dice36": None if quality is None else round(quality, 4),
        "attempts": [{k: v for k, v in t.items() if k != "matrix"} for t in tried if t],
    }
    out.update({k: round(v, 5) for k, v in _decompose(matrix).items()})
    if chosen["method"] == "anchors":
        out.update(anchors=chosen["anchors"], inliers=chosen["inliers"], median_residual_pt=chosen["median_residual_pt"])
    return out
