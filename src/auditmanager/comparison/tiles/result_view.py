"""What the tile reads of a stored result's ``jsonb`` (wave brief C1 section 4 item 3).

`CMP-VIEWER-01`. ``{"format": 1, "canvas": {"width_pt", "height_pt"}, "how_compared": {"dpi", "transform": [a, b, c, d,
e, f], ...}, "aligned_blocks": [...], "mask": {"format": 1, "dpi", "width_px", "height_px"} | null, ...}``. An absent
member is absent (``None``): a result that was never registered has no transform, and the overlay of such a pair does
not exist. A member that is present and wrong is :class:`ResultInvalid` -- the engine validates a result before it
writes it, so a wrong one is damaged data, not a case to guess a way round.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from auditmanager.comparison.tiles.aligned import AlignedBlock, AlignedBlocksInvalid, parse_aligned_blocks
from auditmanager.comparison.tiles.grid import Affine, TransformInvalid

__all__ = ["ResultInvalid", "ResultView", "view_of"]


class ResultInvalid(ValueError):
    def __init__(self, member: str) -> None:
        super().__init__(member)
        self.member = member


@dataclass(frozen=True, slots=True)
class ResultView:
    canvas: tuple[float, float] | None
    dpi: int | None
    transform: Affine | None
    blocks: tuple[AlignedBlock, ...]
    mask_dpi: int | None
    mask_size: tuple[int, int] | None

    @property
    def grid_dpi(self) -> int | None:
        """The dpi of the mask's grid: the mask's own when it says, else the comparison's."""
        return self.mask_dpi or self.dpi


def _positive_int(value: object, member: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ResultInvalid(member)
    return value


def _positive_number(value: object, member: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ResultInvalid(member)
    return float(value)


def view_of(result: Mapping[str, Any]) -> ResultView:
    canvas = None
    raw_canvas = result.get("canvas")
    if raw_canvas is not None:
        if not isinstance(raw_canvas, Mapping):
            raise ResultInvalid("canvas")
        canvas = (_positive_number(raw_canvas.get("width_pt"), "canvas"), _positive_number(raw_canvas.get("height_pt"), "canvas"))
    dpi, transform = None, None
    how = result.get("how_compared")
    if how is not None:
        if not isinstance(how, Mapping):
            raise ResultInvalid("how_compared")
        dpi = _positive_int(how.get("dpi"), "how_compared.dpi")
        if how.get("transform") is not None:
            try:
                transform = Affine.from_sequence(how["transform"])
            except TransformInvalid:
                raise ResultInvalid("how_compared.transform") from None
    try:
        blocks = parse_aligned_blocks(result.get("aligned_blocks"))
    except AlignedBlocksInvalid:
        raise ResultInvalid("aligned_blocks") from None
    mask_dpi, mask_size = None, None
    mask = result.get("mask")
    if mask is not None:
        if not isinstance(mask, Mapping):
            raise ResultInvalid("mask")
        mask_dpi = _positive_int(mask.get("dpi"), "mask.dpi")
        mask_size = (_positive_int(mask.get("width_px"), "mask.width_px"), _positive_int(mask.get("height_px"), "mask.height_px"))
    return ResultView(canvas, dpi, transform, blocks, mask_dpi, mask_size)
