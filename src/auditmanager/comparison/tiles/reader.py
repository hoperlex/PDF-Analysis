"""``streamComparisonPairTile``: one PNG tile of a sheet pair, from what the worker stored.

`CMP-VIEWER-01`, ADR-0025 decision 9 and the addenda of 2026-10-27 and 2026-10-28. **The API never calls PDFium**: the
tiles of page A and page B are the page profile's (stored levels 2 and up from the archive, levels 0 and 1 rendered on
request in a ceilinged child by the page-profile reader), the mask is bytes that this process reads and reduces with
``numpy``, and nothing is written.

The three modes
---------------
``a``
    The page profile's tile of the pair's older page, as stored (no decode, no re-encode).
``b``
    The newer page **warped onto the older page's canvas** with ``how_compared.transform``, so a tile of ``a`` and a
    tile of ``b`` at one ``(level, column, row)`` cover the same canvas square (the original's ``sheet_tile``,
    ``version_comparison.py:419-444``). A pair that has no older page, or whose result has no transform, has no canvas
    to warp onto: its ``b`` is the newer page's own tile.
``overlay``
    Both pages on one canvas (the darker pixel of the two) with the selected mask layers painted over them in solid
    colour; with ``align_blocks`` page B carries its aligned blocks moved back and the layers are not painted on the old
    or the new place of a block. It needs a result with a transform: a pair that was never compared has no overlay
    (``404``). ``layers`` empty means no layer; a ``same`` result has no mask and nothing to draw.

The grid is the pyramid of page A's page profile (or of page B's, for a ``b`` that has no canvas). A level, column or row
outside it is ``404``.

What one request costs (measured in ``docs/program/CMP-VIEWER-01.md``): the pair and its result (one indexed query);
page A's tile (one decode); page B's source tiles (at most :data:`~.limits.MAX_SOURCE_TILES`, usually 1 to 4, each
read at most once from the archive cache or rendered once in a child); one warp of 512 x 512; per selected layer one
reduction over a window of the packed plane (the rows OR-ed as bytes first, so a 40 Mpx plane at the top of the
pyramid is a few megabytes of work); one PNG encode. At most :data:`~.limits.COMPOSE_SLOTS` requests compose at once.
"""

from __future__ import annotations

import math
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import numpy
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.profile.models import PageProfileRow
from auditmanager.comparison.profile.reader import PageProfileReader
from auditmanager.comparison.tiles import errors
from auditmanager.comparison.tiles.aligned import TooManyBlocks, block_pixels, warp_aligned
from auditmanager.comparison.tiles.compose import encode_png, min_composite, paint_layers
from auditmanager.comparison.tiles.grid import PageGrid
from auditmanager.comparison.tiles.limits import COMPOSE_SLOTS, COMPOSE_WAIT_SECONDS
from auditmanager.comparison.tiles.masks import MaskStore
from auditmanager.comparison.tiles.reduction import axis_starts, reduce_max
from auditmanager.comparison.tiles.repository import PairRow, PairTileRepository, ResultRow
from auditmanager.comparison.tiles.result_view import ResultInvalid, ResultView, view_of
from auditmanager.comparison.tiles.source import ProfileTiles
from auditmanager.comparison.tiles.warp import Region, SourceBudget, TooManySourceTiles, warp_region
from auditmanager.shared.db import session_scope

__all__ = ["MODE_A", "MODE_B", "MODE_OVERLAY", "PairTileReader"]

MODE_OVERLAY = "overlay"
MODE_A = "a"
MODE_B = "b"
#: A result with these statuses has a mask when it was compared; the others have none by construction (``same``) or
#: whether they have one is the engine's choice (``needs_review``).
_MASK_EXPECTED = frozenset({"different", "same_zones_changed"})
_FRAME_TOLERANCE_PT = 0.5
_MASK_TOLERANCE_PX = 1


@dataclass(frozen=True, slots=True)
class _Plan:
    kind: str  # "single" | "warped" | "overlay"
    row_a: PageProfileRow | None
    grid_a: PageGrid | None
    row_b: PageProfileRow | None
    grid_b: PageGrid | None
    view: ResultView | None
    result: ResultRow | None


class PairTileReader:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        blob_store: Any,
        *,
        profile_reader: PageProfileReader | None = None,
        tiles: ProfileTiles | None = None,
        masks: MaskStore | None = None,
        slots: int = COMPOSE_SLOTS,
        slot_wait_seconds: float = COMPOSE_WAIT_SECONDS,
    ) -> None:
        self._factory = session_factory
        self._repository = PairTileRepository()
        self._profiles = profile_reader or PageProfileReader(session_factory, blob_store)
        self._tiles = tiles or ProfileTiles(self._profiles, blob_store)
        self._masks = masks or MaskStore(blob_store)
        self._slots = threading.BoundedSemaphore(slots)
        self._wait = slot_wait_seconds

    @property
    def tiles(self) -> ProfileTiles:
        return self._tiles

    @property
    def masks(self) -> MaskStore:
        return self._masks

    # -- the request ---------------------------------------------------------------------------------------

    def read_tile(
        self,
        *,
        sheet_pair_id: str,
        mode: str,
        level: int,
        column: int,
        row: int,
        layers: Sequence[str] = (),
        align_blocks: bool = False,
    ) -> bytes:
        """The PNG of one tile; ``not_found`` for a pair, page, result, mask or tile that does not exist."""
        pair, result = self._load(sheet_pair_id)
        plan = self._plan(mode, pair, result, level, column, row)
        if plan.kind == "single":
            row_, grid = (plan.row_a, plan.grid_a) if mode == MODE_A else (plan.row_b, plan.grid_b)
            assert row_ is not None and grid is not None
            return self._tiles.png(row_, grid, level, column, row)
        with self._slot():
            return self._compose(plan, level, column, row, tuple(dict.fromkeys(layers)), align_blocks)

    # -- planning: which pages, which grid; nothing heavy ------------------------------------------------------

    def _load(self, pair_id: str) -> tuple[PairRow, ResultRow | None]:
        with session_scope(self._factory) as session:
            found = self._repository.get(session, pair_id)
        if found is None:
            raise errors.not_found("ComparisonSheetPair")
        return found

    def _view(self, result: ResultRow | None) -> ResultView | None:
        if result is None:
            return None
        try:
            return view_of(result.result)
        except ResultInvalid as invalid:
            raise errors.integrity(f"result {invalid.member} {result.result_id}") from None

    def _grid(self, page_profile_id: str) -> tuple[PageProfileRow, PageGrid]:
        row = self._tiles.profile(page_profile_id)
        grid = self._tiles.grid(row)
        if grid is None:
            raise errors.not_found("PageTile")  # a page that was refused or ended without a result has no pyramid
        return row, grid

    def _plan(self, mode: str, pair: PairRow, result: ResultRow | None, level: int, column: int, tile_row: int) -> _Plan:
        view = self._view(result)
        has_canvas = pair.page_a_profile_id is not None and view is not None and view.transform is not None
        if mode == MODE_A:
            if pair.page_a_profile_id is None:
                raise errors.not_found("ComparisonPage")
            row_a, grid_a = self._grid(pair.page_a_profile_id)
            self._inside(grid_a, level, column, tile_row)
            return _Plan("single", row_a, grid_a, None, None, view, result)
        if pair.page_b_profile_id is None:
            raise errors.not_found("ComparisonPage")
        if mode == MODE_B and not has_canvas:
            row_b, grid_b = self._grid(pair.page_b_profile_id)
            self._inside(grid_b, level, column, tile_row)
            return _Plan("single", None, None, row_b, grid_b, view, result)
        if mode != MODE_B:  # the overlay of a pair that was never compared, or never registered, does not exist
            if result is None:
                raise errors.not_found("ComparisonSheetPairResult")
            if pair.page_a_profile_id is None or view is None or view.transform is None:
                raise errors.not_found("ComparisonOverlay")
        assert pair.page_a_profile_id is not None and view is not None
        row_a, grid_a = self._grid(pair.page_a_profile_id)
        self._inside(grid_a, level, column, tile_row)
        row_b, grid_b = self._grid(pair.page_b_profile_id)
        if view.canvas is not None and (
            abs(view.canvas[0] - grid_a.width_pt) > _FRAME_TOLERANCE_PT
            or abs(view.canvas[1] - grid_a.height_pt) > _FRAME_TOLERANCE_PT
        ):
            raise errors.integrity(f"canvas {pair.sheet_pair_id}")
        return _Plan("warped" if mode == MODE_B else "overlay", row_a, grid_a, row_b, grid_b, view, result)

    @staticmethod
    def _inside(grid: PageGrid, level: int, column: int, tile_row: int) -> None:
        if grid.tile_box(level, column, tile_row) is None:
            raise errors.not_found("PairTile")

    # -- composing ---------------------------------------------------------------------------------------------

    @contextmanager
    def _slot(self) -> Iterator[None]:
        if not self._slots.acquire(timeout=self._wait):
            raise errors.unavailable("compose slots")
        try:
            yield
        finally:
            self._slots.release()

    def _compose(
        self, plan: _Plan, level: int, column: int, tile_row: int, layers: tuple[str, ...], align_blocks: bool
    ) -> bytes:
        grid_a, row_a, grid_b, row_b, view = plan.grid_a, plan.row_a, plan.grid_b, plan.row_b, plan.view
        assert grid_a and row_a and grid_b and row_b and view and view.transform
        left, top, right, bottom = grid_a.tile_box(level, column, tile_row)  # type: ignore[misc]
        origin, size = (left, top), (right - left, bottom - top)
        budget = SourceBudget()

        def fetch(source_level: int, source_column: int, source_row: int) -> "numpy.ndarray | None":
            return self._tiles.array(row_b, grid_b, source_level, source_column, source_row)

        aligned = align_blocks and bool(view.blocks)
        try:
            if aligned:
                page_b = warp_aligned(
                    fetch, budget, blocks=view.blocks, grid_a=grid_a, level_a=level, origin=origin, size=size,
                    grid_b=grid_b, to_a=view.transform,
                )
            else:
                page_b = warp_region(
                    fetch, budget, grid_a=grid_a, level_a=level, origin=origin, region=Region(0, 0, *size),
                    grid_b=grid_b, to_a=view.transform,
                )
            if plan.kind == "warped":
                return encode_png(page_b)
            image = min_composite(self._tiles.array(row_a, grid_a, level, column, tile_row), page_b)
            masks = self._layer_masks(plan, level, origin, size, layers)
            if aligned and masks:
                moved = block_pixels(view.blocks, grid_a, level, origin, size)
                for name in masks:
                    masks[name] = masks[name] & ~moved
        except (TooManySourceTiles, TooManyBlocks) as heavy:
            raise errors.unavailable(type(heavy).__name__) from None
        paint_layers(image, masks, origin)
        return encode_png(image)

    def _layer_masks(
        self, plan: _Plan, level: int, origin: tuple[int, int], size: tuple[int, int], layers: tuple[str, ...]
    ) -> "dict[str, numpy.ndarray]":
        """The chosen layers reduced to this tile (``bool`` arrays); empty when nothing is to be drawn."""
        result, view, grid_a = plan.result, plan.view, plan.grid_a
        assert result is not None and view is not None and grid_a is not None
        if not layers:
            return {}
        if result.mask_blob_id is None:
            if result.status in _MASK_EXPECTED:
                raise errors.not_found("ComparisonMask")
            return {}
        dpi = view.grid_dpi
        if dpi is None or view.mask_size is None:
            raise errors.integrity(f"mask description {result.result_id}", result.mask_blob_id)
        planes = self._masks.planes(result.mask_blob_id)
        if (planes.width_px, planes.height_px) != view.mask_size:
            raise errors.integrity(f"mask size {result.result_id}", result.mask_blob_id)
        if view.canvas is not None and (
            abs(planes.width_px - math.ceil(view.canvas[0] * dpi / 72.0)) > _MASK_TOLERANCE_PX
            or abs(planes.height_px - math.ceil(view.canvas[1] * dpi / 72.0)) > _MASK_TOLERANCE_PX
        ):
            raise errors.integrity(f"mask grid {result.result_id}", result.mask_blob_id)
        num, den = (1 << level) * dpi, grid_a.dpi
        if (origin[0] * num) // den >= planes.width_px or (origin[1] * num) // den >= planes.height_px:
            return {name: numpy.zeros((size[1], size[0]), dtype=bool) for name in layers}
        xs, x_end = axis_starts(origin[0], size[0], num, den, planes.width_px)
        ys, y_end = axis_starts(origin[1], size[1], num, den, planes.height_px)
        return {name: reduce_max(planes.plane(name), xs, x_end, ys, y_end) for name in layers}
