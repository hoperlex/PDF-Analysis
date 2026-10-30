"""Translate the existing engine's raw regions, preserving registration and source frames."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Sequence

GRAPHIC_CLASSES = frozenset({"graphic_added", "graphic_removed", "graphic_changed", "color_change",
                             "light_fill", "line_style", "block_moved", "shifted"})
_UNRELIABLE = frozenset({"ALIGNMENT_UNRELIABLE", "ALIGNMENT_PARTIAL", "PARTIAL_COVERAGE",
                         "FRAME_MISMATCH", "MATCH_LOW_CONFIDENCE", "MATCH_AMBIGUOUS", "MATCH_UNRESOLVED"})
_NOT_CHECKED = frozenset({"RENDER_FAILED", "PAGE_TOO_LARGE"})


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def clipped(box: Sequence[float], width: float, height: float) -> tuple[float, float, float, float]:
    if (len(box) != 4 or any(type(v) not in {int, float} or not math.isfinite(v) for v in box)
            or not math.isfinite(width) or not math.isfinite(height) or min(width, height) <= 0):
        raise ValueError("stage_graphic_box_invalid")
    x0, y0, x1, y1 = box
    x0, x1 = max(0.0, float(x0)), min(float(width), float(x1))
    y0, y1 = max(0.0, float(y0)), min(float(height), float(y1))
    if x1 <= x0 or y1 <= y0:
        raise ValueError("stage_graphic_box_outside_profile")
    return x0, y0, x1, y1


def inverse_box(transform: Sequence[float], box: Sequence[float]) -> tuple[float, float, float, float]:
    """Engine PDF-order affine maps displayed B→A; crops need native displayed B points."""
    if len(transform) != 6 or any(type(v) not in {int, float} or not math.isfinite(v) for v in transform):
        raise ValueError("stage_graphic_transform_invalid")
    a, b, c, d, e, f = transform
    determinant = a * d - b * c
    if abs(determinant) < 1e-9:
        raise ValueError("stage_graphic_transform_singular")
    x0, y0, x1, y1 = box
    points = [((d * (x - e) - c * (y - f)) / determinant,
               (-b * (x - e) + a * (y - f)) / determinant)
              for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
    return (min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points))


def project_result(stored: Any, *, left_size: tuple[float, float], right_size: tuple[float, float]
                   ) -> tuple[str, str, list[dict[str, Any]]]:
    """No registration refusal can become graphic evidence, regardless of pair status."""
    reasons = set(stored.reasons)
    if reasons & _NOT_CHECKED:
        return "not_checked", "graphics_not_checked_render_failed", []
    geometry = stored.channels.get("geometry", {}).get("state")
    color = stored.channels.get("color", {}).get("state")
    if reasons & _UNRELIABLE or geometry != "checked" or color != "checked":
        return "unreliable", "graphics_not_checked_registration_unreliable", []
    result = stored.result
    how = result.get("how_compared") or {}
    transform = how.get("transform") or []
    proof = {"source": "comparison_sheet_pair_result", "result_id": stored.result_id,
             "algo_version": stored.algo_version, "content_key": stored.content_key,
             "result_left_profile_id": stored.page_a_profile_id,
             "result_right_profile_id": stored.page_b_profile_id,
             "transform": transform, "transform_direction": "right_to_left",
             "coordinate_frame": "displayed_page_points_top_left", "reliable": True,
             "reliability_basis": "engine_checked_geometry_color_no_alignment_or_coverage_refusal",
             "geometry": stored.channels["geometry"], "color": stored.channels["color"],
             "reasons": sorted(reasons), "dpi": how.get("dpi")}
    regions = []
    try:
        inverse_box(transform, (0, 0, 1, 1))  # even identical/empty results need valid registration
        for value in result.get("differences", []):
            if value.get("region_class") not in GRAPHIC_CLASSES:
                continue
            box = value["box"]
            native_left = (box["x"], box["y"], box["x"] + box["width"], box["y"] + box["height"])
            left = clipped(native_left, *left_size)
            native_right = inverse_box(transform, native_left)
            right = clipped(native_right, *right_size)
            region = {"region_class": value["region_class"], "layer": value["layer"],
                      "left_box": list(left), "right_box": list(right),
                      "left_box_clipped": tuple(native_left) != left,
                      "right_box_clipped": tuple(native_right) != right,
                      "registration": proof, "raw_difference": value}
            region["region_key"] = digest(region)
            regions.append(region)
    except (ValueError, KeyError, TypeError, OverflowError):
        return "unreliable", "graphics_not_checked_region_or_registration_invalid", []
    # A reliable empty list means graphics were compared and no non-text graphic
    # regions survived the deterministic engine. It never means an unrun comparison.
    return "reliable", "graphics_compared" if regions else "graphics_compared_no_regions", sorted(
        regions, key=lambda region: region["region_key"])
