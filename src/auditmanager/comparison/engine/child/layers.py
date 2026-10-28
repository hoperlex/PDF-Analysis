"""The pixel layers of one band of rows: what only A draws, what only B draws, light elements, line style, colour,
tolerance and noise (port of ``engine.py:575-684``).

`CMP-ENGINE-01`. Every operation here looks at a pixel and its neighbours within a few pixels, so a band of rows with
a margin of ``2 r + 10`` rows around it gives, in its core rows, exactly what a whole-canvas computation would give;
:func:`compute_band` is handed the extended band and the caller keeps the core. The thresholds are those of the
original (:mod:`.settings`). Line numbers in the comments are the original's ``engine.py``.

Layers returned (all ``uint8`` zeros and ones, shape of the band):

``dark_a``, ``dark_b``  a line (grey below 200) in A, in B;
``any_a``, ``any_b``    any ink (grey below 250);
``a_only``, ``b_only``  a line in one version with none of the other within the tolerance (the difference of the
                        main layer, a drawing removed from A, added in B);
``style``               a line of one version where the other has only a light or a thin one: the same line drawn
                        otherwise (``:610-621``);
``light_a``, ``light_b``  light elements (fills, hatches) only in A, only in B;
``color``               places where the colour of a common line changed;
``noise``               components of one or two pixels that touch a common line: anti-aliasing;
``within_tol``          differences no larger than the tolerance (a sub-pixel shift, a thinner pen).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import cv2
import numpy

from . import settings

__all__ = ["compute_band", "disk"]

_ONES3 = numpy.ones((3, 3), numpy.uint8)
_WIDE = numpy.ones((settings.STYLE_FILL_PX, settings.STYLE_FILL_PX), numpy.uint8)


def disk(radius: int) -> Any:
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius + 1, 2 * radius + 1))


def _small_touching(layer: Any, near: Any, noise: Any) -> None:
    """Components of at most ``NOISE_MAX_PX`` pixels that touch ``near`` move from ``layer`` into ``noise``
    (``:625-637``): the smoothing at the end or the edge of a line. An isolated dot on an empty place is never noise."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(layer, connectivity=8)
    if n <= 1:
        return
    small = numpy.nonzero(stats[1:, 4] <= settings.NOISE_MAX_PX)[0] + 1
    if not len(small):
        return
    touch = numpy.bincount(labels[near > 0], minlength=n)
    ids = small[touch[small] > 0].astype(numpy.int32)
    if len(ids):
        selected = numpy.isin(labels, ids)
        noise[selected] = 1
        layer[selected] = 0


def compute_band(
    bgr_a: Any,
    bgr_b: Any,
    main_full: Any,
    part: Any,
    *,
    radius: int,
    core: tuple[int, int],
    zone_masks: Mapping[str, Any],
) -> dict[str, Any]:
    """The layers of the extended band, and the numbers of its core rows.

    ``main_full`` is 1 outside the service zones; ``part`` (or ``None``) is 1 inside the part of a split sheet that
    B occupies (``:588-602``): the main area compared is their intersection.
    ``zone_masks`` maps a zone type to its mask (the rectangles of A and of B carried onto A) for the zone statistics.
    """
    main = main_full if part is None else main_full & part
    kernel = disk(radius)
    gray_a = cv2.cvtColor(bgr_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(bgr_b, cv2.COLOR_BGR2GRAY)
    dark_a = (gray_a < settings.DARK_THRESHOLD).astype(numpy.uint8)
    dark_b = (gray_b < settings.DARK_THRESHOLD).astype(numpy.uint8)
    any_a = (gray_a < settings.LIGHT_THRESHOLD).astype(numpy.uint8)
    any_b = (gray_b < settings.LIGHT_THRESHOLD).astype(numpy.uint8)

    dil_dark_a, dil_dark_b = cv2.dilate(dark_a, kernel), cv2.dilate(dark_b, kernel)
    dil_any_a, dil_any_b = cv2.dilate(any_a, kernel), cv2.dilate(any_b, kernel)
    unc_a = dark_a & (1 - dil_dark_b) & main
    unc_b = dark_b & (1 - dil_dark_a) & main

    # The style of a line (``:610-621``): a dark line of one version where the other has only a light or a thin one.
    # A light area wider than STYLE_FILL_PX is a fill, not a line: a dark line over it stays removed or added.
    fill_a = cv2.dilate(cv2.morphologyEx(any_a & (1 - dark_a), cv2.MORPH_OPEN, _WIDE), kernel)
    fill_b = cv2.dilate(cv2.morphologyEx(any_b & (1 - dark_b), cv2.MORPH_OPEN, _WIDE), kernel)
    style_a = unc_a & dil_any_b & (1 - fill_b)
    style_b = unc_b & dil_any_a & (1 - fill_a)
    a_only = unc_a & (1 - style_a)
    b_only = unc_b & (1 - style_b)

    noise = numpy.zeros(gray_a.shape, numpy.uint8)
    common_near = cv2.dilate(dark_a & dark_b, _ONES3)
    for layer in (a_only, b_only, style_a, style_b):
        _small_touching(layer, common_near, noise)
    style = style_a | style_b

    # Light elements only in A / only in B, clearly darker than the darkest pixel of the other version nearby:
    # the flicker of smoothing at the threshold of 250 is not a difference (``:638-647``).
    ring = disk(radius + 1)
    min_a = cv2.erode(gray_a, kernel).astype(numpy.int16)
    min_b = cv2.erode(gray_b, kernel).astype(numpy.int16)
    light_a = (any_a & (1 - dil_any_b) & (1 - cv2.dilate(a_only | style_a, ring)) & main
               & ((min_b - gray_a) > settings.LIGHT_DELTA)).astype(numpy.uint8)
    light_b = (any_b & (1 - dil_any_a) & (1 - cv2.dilate(b_only | style_b, ring)) & main
               & ((min_a - gray_b) > settings.LIGHT_DELTA)).astype(numpy.uint8)
    del min_a, min_b, fill_a, fill_b, dil_any_a, dil_any_b
    ink_near = cv2.dilate(dark_a | dark_b, _ONES3)
    for layer in (light_a, light_b):
        _small_touching(layer, ink_near, noise)
    del ink_near

    strict = (dark_a ^ dark_b) & main
    within_tol = strict & (1 - a_only) & (1 - b_only) & (1 - style)
    common_dark = dark_a & dark_b & main

    # The colour channel (``:665-683``): the chroma a*b* on common lines and the lightness inside them.
    lab_a = cv2.cvtColor(bgr_a, cv2.COLOR_BGR2Lab).astype(numpy.int16)
    lab_b = cv2.cvtColor(bgr_b, cv2.COLOR_BGR2Lab).astype(numpy.int16)
    chroma = numpy.hypot(lab_a[:, :, 1] - lab_b[:, :, 1], lab_a[:, :, 2] - lab_b[:, :, 2])
    core_dark = cv2.erode(common_dark, _ONES3)
    luma = numpy.abs(lab_a[:, :, 0] - lab_b[:, :, 0])
    color = ((common_dark & (chroma > settings.COLOR_DELTA)) | (core_dark & (luma > settings.LUMA_DELTA))).astype(numpy.uint8)
    del lab_a, lab_b, chroma, luma, core_dark
    # One or two pixels of colour on a common line are the blending of smoothing, not a recolouring (``:675-683``).
    n, labels, stats, _ = cv2.connectedComponentsWithStats(color, connectivity=8)
    if n > 1:
        ids = (numpy.nonzero(stats[1:, 4] <= settings.NOISE_MAX_PX)[0] + 1).astype(numpy.int32)
        if len(ids):
            selected = numpy.isin(labels, ids)
            noise[selected] = 1
            color[selected] = 0
    del labels

    c0, c1 = core
    zone_stats: dict[str, tuple[int, int]] = {}
    for kind, mask in zone_masks.items():
        zone = mask[c0:c1]
        if not zone.any():
            zone_stats[kind] = (0, 0)
            continue
        differs = ((dark_a[c0:c1] & (1 - dil_dark_b[c0:c1])) | (dark_b[c0:c1] & (1 - dil_dark_a[c0:c1]))) & zone
        zone_stats[kind] = (int(differs.sum()), int(((dark_a[c0:c1] ^ dark_b[c0:c1]) & zone).sum()))

    within_components = int(cv2.connectedComponents(within_tol[c0:c1], connectivity=8)[0] - 1) if within_tol[c0:c1].any() else 0
    noise_components = int(cv2.connectedComponents(noise[c0:c1], connectivity=8)[0] - 1) if noise[c0:c1].any() else 0
    return {
        "dark_a": dark_a, "dark_b": dark_b, "any_a": any_a, "any_b": any_b,
        "a_only": a_only, "b_only": b_only, "style": style, "light_a": light_a, "light_b": light_b,
        "color": color, "noise": noise, "within_tol": within_tol,
        "zone_stats": zone_stats,
        "within_components": within_components, "noise_components": noise_components,
        "ink_a_main": int((dark_a[c0:c1] & main_full[c0:c1]).sum()),
        "ink_a_in_part": int((dark_a[c0:c1] & main[c0:c1]).sum()),
    }
