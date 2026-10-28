"""The numbers of the comparison, each with the line of the original that sets it.

`CMP-ENGINE-01`. The original is PDF-proverka at commit ``23f379fd``, ``backend/app/services/version_comparison/``;
``settings.py:N`` below is that file's line N. A number that is the engine's own (it has no counterpart there) says
so. Changing any value here is a change of the algorithm: bump :data:`ALGO_VERSION`, which is part of the content key
of every stored result (ADR-0025 decision 15).
"""

from __future__ import annotations

from typing import Final

__all__ = ["ALGO_VERSION", "PARAMS"]

#: Names the algorithm that makes a result. The original's is ``vc1.13`` (``settings.py:11``); this one is the
#: engine's own and starts at 1.
ALGO_VERSION: Final[str] = "cmp-engine/1"

# -- the raster and the tolerance -------------------------------------------------------------
#: ``tolerance_pt()`` default, ``settings.py:37-38``: two lines closer than this are the same line.
TOLERANCE_PT: Final[float] = 0.5
#: ``settings.py:46-47``: a pixel darker than DARK is a line, darker than LIGHT is any ink.
DARK_THRESHOLD: Final[int] = 200
LIGHT_THRESHOLD: Final[int] = 250
#: ``settings.py:50-51``: the colour channel, a*b* distance on a common line and L inside it.
COLOR_DELTA: Final[int] = 25
LUMA_DELTA: Final[int] = 60
#: ``settings.py:53``: a component of at most this many pixels that touches a common line is anti-aliasing noise.
NOISE_MAX_PX: Final[int] = 2
#: ``settings.py:56``: a light element must be darker than the darkest pixel of the other version nearby by this much.
LIGHT_DELTA: Final[int] = 10
#: ``settings.py:60``: a light area wider than this is a fill, not a line.
STYLE_FILL_PX: Final[int] = 7
#: ``settings.py:63-64``: a colour change explained by the drawing order of crossing lines.
OVERDRAW_DELTA: Final[int] = 25
OVERDRAW_MIN_SHARE: Final[float] = 0.6

# -- moved blocks and shifted marks -----------------------------------------------------------
#: ``settings.py:68-71``.
BLOCK_MIN_WORDS: Final[int] = 5
BLOCK_TOL_PT: Final[float] = 1.0
BLOCK_MIN_SHIFT_PT: Final[float] = 3.0
BLOCK_MIN_IOU: Final[float] = 0.6
#: ``block_alignment.py:359-360``: only a block moved with at least this share explained is aligned in the viewer.
ALIGN_MIN_SHARE: Final[float] = 0.9
#: ``settings.py:77-79``.
GLYPH_MAX_ASPECT: Final[float] = 2.0
GLYPH_MAX_FILL: Final[float] = 0.85
GLYPH_STROKE_RATIO: Final[float] = 0.25
#: ``settings.py:81``, ``:83``, ``:85``, ``:87``.
SHIFT_EXPLAINED_SHARE: Final[float] = 0.9
SHIFT_NEAR_MM: Final[float] = 5.0
SHIFT_REFINE_PT: Final[float] = 6.0
REGION_CLOSE_MM: Final[float] = 1.5
#: ``settings.py:90``: the same text farther than the tolerance and nearer than this is a moved inscription.
WORD_MOVE_PT: Final[float] = 20.0

# -- registration -----------------------------------------------------------------------------
#: ``settings.py:196-199``: anchors by unique words (RANSAC).
ANCHOR_MIN_INLIERS: Final[int] = 8
ANCHOR_MIN_RATIO: Final[float] = 0.15
ANCHOR_MAX_MEDIAN_RESIDUAL_PT: Final[float] = 0.6
ANCHOR_RANSAC_PT: Final[float] = 2.0
#: ``settings.py:201``, ``:203``: the check of the registration by the 36 dpi ink masks.
ALIGN_MIN_DICE: Final[float] = 0.5
ALIGN_SWITCH_MARGIN: Final[float] = 0.1
#: ``settings.py:205``: not used here (see the report: the stream-level separation is not built).
WARNING_MIN_AREA_SHARE: Final[float] = 0.20

# -- the engine's own numbers (no counterpart in the original) --------------------------------
#: The phase correlation of the 36 dpi masks runs on a mask of at most this many pixels (a 2A0 sheet is 4 Mpx and the
#: transform needs 180 MiB of address space at that size): larger masks are reduced by an integer factor first.
PHASE_MAX_PIXELS: Final[int] = 1_000_000
#: Translation by the vector lines of the sheets: the search radius, the finest bin of the vote and the least votes.
LINES_SEARCH_PT: Final[float] = 3.5
LINES_BIN_PT: Final[float] = 0.1
LINES_MIN_VOTES: Final[int] = 8
LINES_MIN_SHARE: Final[float] = 0.05
LINES_MAX_POINTS: Final[int] = 12_000
#: The working band: rows are compared a band at a time so that a 40 Mpx page fits the ceiling of 768 MiB
#: (ADR-0025 decision 8, "the engine tiles its full-resolution work to fit").
BAND_PIXELS: Final[int] = 1_000_000
#: How long the child spends on the expensive analysis of single regions before it classifies the rest by the
#: cheap rules alone (never as a shift, which would hide a difference) and says so (reason PARTIAL_COVERAGE).
REGION_ANALYSIS_SECONDS: Final[float] = 120.0
#: The page of B outside the canvas of A: ink farther out than this many points makes the pair PARTIAL_COVERAGE.
OUTSIDE_CANVAS_PT: Final[float] = 3.0
#: A mask pixel of the 36 dpi ink mask is a pixel of ink.
MASK_DPI: Final[int] = 36

#: What a stored result's key depends on besides the pages: every number above that decides a pixel or a class.
PARAMS: Final[dict[str, float | int]] = {
    "tol_pt": TOLERANCE_PT, "dark": DARK_THRESHOLD, "light": LIGHT_THRESHOLD, "color_delta": COLOR_DELTA,
    "luma_delta": LUMA_DELTA, "noise_px": NOISE_MAX_PX, "light_delta": LIGHT_DELTA, "style_fill_px": STYLE_FILL_PX,
    "overdraw_delta": OVERDRAW_DELTA, "overdraw_share": OVERDRAW_MIN_SHARE, "block_words": BLOCK_MIN_WORDS,
    "block_tol_pt": BLOCK_TOL_PT, "block_shift_pt": BLOCK_MIN_SHIFT_PT, "block_iou": BLOCK_MIN_IOU,
    "shift_share": SHIFT_EXPLAINED_SHARE, "shift_near_mm": SHIFT_NEAR_MM, "shift_refine_pt": SHIFT_REFINE_PT,
    "region_close_mm": REGION_CLOSE_MM, "word_move_pt": WORD_MOVE_PT, "anchor_inliers": ANCHOR_MIN_INLIERS,
    "anchor_ratio": ANCHOR_MIN_RATIO, "anchor_residual_pt": ANCHOR_MAX_MEDIAN_RESIDUAL_PT,
    "anchor_ransac_pt": ANCHOR_RANSAC_PT, "align_dice": ALIGN_MIN_DICE, "align_switch": ALIGN_SWITCH_MARGIN,
    "phase_max_px": PHASE_MAX_PIXELS, "lines_search_pt": LINES_SEARCH_PT, "lines_bin_pt": LINES_BIN_PT,
    "lines_min_votes": LINES_MIN_VOTES, "lines_min_share": LINES_MIN_SHARE,
    "pixel_cap": 40_000_000, "max_dpi": 200, "min_dpi": 72,
}
