"""The outcome of one pair: channels, status, reasons and the versioned ``result`` of the wave brief section 4 item 3.

`CMP-ENGINE-01`. Pure Python (the worker's side imports it too). The outcome has five members:

``status``, ``reasons``, ``channels``  the columns of ``comparison_sheet_pair_result``;
``result``                             the ``jsonb`` of the brief: ``{"format": 1, "canvas", "differences",
                                       "text_changes", "service_notes", "how_compared", "aligned_blocks", "mask"}``
                                       (and, for a split sheet only, ``"part"``);
``counts``                             facts for the report, not stored.

Every member that has a schema of the contract keeps within its caps (2000 differences, 2000 text changes, 500 service
notes) and its string lengths; the worker validates each with the generated model before the row is written.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Final

from . import settings, status as status_module

__all__ = [
    "CAPS",
    "FORMAT",
    "REGION_CLASSES",
    "box_dict",
    "build_result",
    "difference",
    "failure_outcome",
    "identical_outcome",
    "text_change",
]

FORMAT: Final[int] = 1
CAPS: Final[dict[str, int]] = {"differences": 2000, "text_changes": 2000, "service_notes": 500}
#: The class of a region as the engine names it, to the contract's ``region_class`` and ``layer``.
REGION_CLASSES: Final[dict[str, tuple[str, str]]] = {
    "text": ("text", "main"),
    "text_moved": ("text_moved", "moved"),
    "added": ("graphic_added", "main"),
    "removed": ("graphic_removed", "main"),
    "changed": ("graphic_changed", "main"),
    "color": ("color_change", "color_change"),
    "light": ("light_fill", "light_elements"),
    "style": ("line_style", "line_style"),
    "block_moved": ("block_moved", "moved"),
    "shifted": ("shifted", "moved"),
}
_TEXT_MAX = 2000


def _clip(text: str, limit: int = _TEXT_MAX) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def box_dict(rect: Sequence[float]) -> dict[str, float]:
    """``ComparisonBox`` from ``[x0, y0, x1, y1]`` in points."""
    x0, y0, x1, y1 = (float(v) for v in rect)
    return {"x": round(x0, 2), "y": round(y0, 2), "width": round(max(0.0, x1 - x0), 2), "height": round(max(0.0, y1 - y0), 2)}


def difference(region: dict[str, Any]) -> dict[str, Any]:
    """``ComparisonDifference`` from a region of the engine."""
    region_class, layer = REGION_CLASSES[region["class"]]
    out: dict[str, Any] = {"region_class": region_class, "layer": layer, "box": box_dict(region["bbox_a_pt"])}
    before = _clip(" ".join(region.get("text_before") or ()))
    after = _clip(" ".join(region.get("text_after") or region.get("moved_text") or ()))
    if before:
        out["before_text"] = before
    if after:
        out["after_text"] = after
    return out


def text_change(change: dict[str, Any]) -> dict[str, Any]:
    """``ComparisonTextChange`` from a change of :mod:`.textdiff`. A normalisation (spaces, a letter of the other
    alphabet, the number format) is part of the kind: ``changed_spaces``, ``changed_symbol``, ``changed_number_format``."""
    kind = change["kind"]
    if change.get("norm"):
        kind = f"{kind}_{change['norm']}"
    out: dict[str, Any] = {"kind": kind}
    if change.get("before"):
        out["before"] = _clip(change["before"])
    if change.get("after"):
        out["after"] = _clip(change["after"])
    numbers = [
        {"before": n["before"][:64], "after": n["after"][:64]}
        for n in change.get("numbers") or ()
        if n.get("before") and n.get("after")
    ]
    if numbers:
        out["numbers"] = numbers
    rect = change.get("a_bbox") or change.get("b_in_a_bbox")
    if rect:
        out["box"] = box_dict(rect)
    return out


def _how_compared(dpi: int, matrix_pdf: Sequence[float], *, within: int, noise: int, separated: int, aligned: int) -> dict[str, Any]:
    return {
        "algo_version": settings.ALGO_VERSION,
        "dpi": int(dpi),
        "tolerance_pt": settings.TOLERANCE_PT,
        "transform": [round(float(v), 6) for v in matrix_pdf],
        "within_tolerance_count": int(within),
        "noise_count": int(noise),
        "separated_objects": int(separated),
        "aligned_blocks": int(aligned),
    }


def build_result(
    *,
    width_pt: float,
    height_pt: float,
    dpi: int,
    matrix_pdf: Sequence[float],
    differences: list[dict[str, Any]],
    text_changes: list[dict[str, Any]],
    service_notes: list[dict[str, Any]],
    aligned_blocks: list[dict[str, Any]],
    within: int = 0,
    noise: int = 0,
    separated: int = 0,
    mask: dict[str, int] | None = None,
    part: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "format": FORMAT,
        "canvas": {"width_pt": round(float(width_pt), 2), "height_pt": round(float(height_pt), 2)},
        "differences": differences[: CAPS["differences"]],
        "text_changes": text_changes[: CAPS["text_changes"]],
        "service_notes": service_notes[: CAPS["service_notes"]],
        "how_compared": _how_compared(dpi, matrix_pdf, within=within, noise=noise, separated=separated, aligned=len(aligned_blocks)),
        "aligned_blocks": aligned_blocks,
        "mask": mask,
    }
    if part is not None:
        result["part"] = part
    return result


def failure_outcome(
    reason: str, why: str, *, width_pt: float = 1.0, height_pt: float = 1.0, dpi: int = 72, extra_reasons: Sequence[str] = ()
) -> dict[str, Any]:
    """A pair the engine could not compare: ``needs_review`` for ``reason`` (``RENDER_FAILED``, ``PAGE_TOO_LARGE``),
    every channel ``unchecked`` with ``why``. Never ``same`` (ADR-0025 decision 8)."""
    channels = {name: status_module.unchecked(why) for name in status_module.CHANNELS}
    status, reasons = status_module.decide(channels, [reason, *extra_reasons])
    return {
        "status": status, "reasons": reasons, "channels": channels,
        "result": build_result(
            width_pt=width_pt, height_pt=height_pt, dpi=dpi, matrix_pdf=[1, 0, 0, 1, 0, 0],
            differences=[], text_changes=[], service_notes=[], aligned_blocks=[],
        ),
        "counts": {"differences": 0},
    }


def identical_outcome(
    *,
    width_pt: float,
    height_pt: float,
    dpi: int,
    reasons: Sequence[str],
    annotation_diffs: int,
    has_annotations: bool,
    service_notes: list[dict[str, Any]],
    is_spec: bool,
    part: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The pair whose pages have the same content (the same Merkle): the fast path of the original
    (``engine.py:505-527``). Every channel but ``annotations`` is ``checked`` with no difference, because the rendered
    pages are the same by construction; the annotations are compared on their own."""
    channels: dict[str, dict[str, Any]] = {}
    for name in ("geometry", "color", "text", "text_coverage", "zones", "warnings"):
        channels[name] = status_module.checked(0)
    channels["annotations"] = (
        status_module.checked(annotation_diffs) if has_annotations else status_module.not_applicable("аннотаций нет ни в A, ни в B")
    )
    channels["spec_positions"] = status_module.checked(0) if is_spec else status_module.not_applicable("не спецификация")
    status, kept = status_module.decide(channels, list(reasons))
    return {
        "status": status, "reasons": kept, "channels": channels,
        "result": build_result(
            width_pt=width_pt, height_pt=height_pt, dpi=dpi, matrix_pdf=[1, 0, 0, 1, 0, 0],
            differences=[], text_changes=[], service_notes=service_notes, aligned_blocks=[], part=part,
        ),
        "counts": {"differences": 0},
    }
