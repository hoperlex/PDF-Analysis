"""What the packet reads from the two pages of a sheet pair: words, ruling lines, pictures, the same designation elsewhere
(`CMP-VC-AISHEET-01`).

:class:`SheetMaterial` is the seam. The packet and the run never open a page profile, a tile or a version themselves; the real
implementation (:class:`ProfileMaterial`) reads the stored page profiles of ``CMP-PROFILE-01`` and **never calls PDFium**: a crop is
cut from the stored tile pyramid (levels 0 and 1 are rendered on request by the profile reader in a ceilinged child), the overview is the
stored preview. A test supplies another implementation with the words and the pictures it chooses.

``find_marks`` is the original's ``context.xrefs`` (`23f379fd`, ``context.py:170-206``): a designation that the changed text names is looked
for on the **other pages of the same two versions** (never other versions or projects); a designation that occurs on more than
``MARK_MAX_COMMON`` pages is noise; at most ``limit`` pages are returned for a designation.
"""

from __future__ import annotations

import io
import math
from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Final, Protocol

from PIL import Image

from auditmanager.comparison.ai_sheets import geometry as geo
from auditmanager.comparison.ai_sheets import images as pix
from auditmanager.comparison.ai_sheets.candidates import norm_mark
from auditmanager.comparison.profile.models import PageProfileData

__all__ = ["MarkHit", "ProfileMaterial", "SheetMaterial", "crop_from_tiles", "row_text_near"]

MARK_MAX_COMMON: Final[int] = 25  # context.py:28
_ROW_HALF_WIDTH_PT: Final[float] = 420.0  # context.py:20
_MAX_TEXT: Final[int] = 700  # context.py:22
_PAGE_CACHE: Final[int] = 16
_VERSION_CACHE: Final[int] = 4


class MarkHit(dict):  # type: ignore[type-arg]
    """``{mark, side, page, bbox, text, page_label}`` -- a designation found on another page of one of the two versions."""


class SheetMaterial(Protocol):
    """The reads of the packet. ``page_profile_id`` names a page profile (``cpr_...``)."""

    def page(self, page_profile_id: str) -> PageProfileData:
        """The page's words, ruling lines and stamp."""

    def overview(self, page_profile_id: str) -> bytes | None:
        """The whole page as a PNG whose long side is at most ``IMAGE_MAX_PX``, or ``None`` when there is no picture."""

    def crop(self, page_profile_id: str, box: Sequence[float], *, long_side_px: int) -> bytes | None:
        """The part ``box`` (points of the displayed page) as a PNG whose long side is at most ``long_side_px`` -- never enlarged
        -- or ``None`` when the page has no picture."""

    def find_marks(
        self, versions: Mapping[str, str], marks: Sequence[str], *, skip_pages: Mapping[str, int | None], limit: int,
    ) -> list[MarkHit]:
        """The designations of ``marks`` on the other pages of the two versions (``versions`` maps ``A``/``B`` to a version)."""


def row_text_near(words: Sequence[Sequence[Any]], box: Sequence[float]) -> str:
    """The row of a word: the words in the band of its height, up to 420 pt either side, in reading order (``context.py:106-121``)."""
    from auditmanager.comparison.ai_sheets.tables import lines_text

    cy0, cy1 = box[1] - 0.3 * (box[3] - box[1]), box[3] + 0.3 * (box[3] - box[1])
    row = [
        w for w in words
        if cy0 <= (w[1] + w[3]) / 2 <= cy1 and box[0] - _ROW_HALF_WIDTH_PT <= (w[0] + w[2]) / 2 <= box[2] + _ROW_HALF_WIDTH_PT
    ]
    text = lines_text(row)
    return text if len(text) <= _MAX_TEXT else text[:_MAX_TEXT] + " …"


def crop_from_tiles(
    summary: Mapping[str, Any], width_pt: float, height_pt: float, read_tile: Callable[[int, int, int], bytes],
    box: Sequence[float], *, long_side_px: int,
) -> bytes | None:
    """A crop of the page cut from its tile pyramid.

    ``summary`` is the profile's ``tiles`` member (``tile_px`` and the ``levels`` with their size and grid). The level is the finest one
    whose crop is at most ``long_side_px`` on its long side (the coarsest if none is); the tiles that cover the box are pasted into
    one canvas, which is cut to the box. ``None`` when the page has no pyramid or the box is empty.
    """
    levels = summary.get("levels") or []
    tile_px = int(summary.get("tile_px") or 0)
    if not levels or tile_px <= 0 or width_pt <= 0 or height_pt <= 0:
        return None
    x0, y0, x1, y1 = geo.clip(box, width_pt, height_pt)
    if x1 - x0 < 1.0 or y1 - y0 < 1.0:
        return None
    chosen = levels[-1]
    for level in levels:
        scale = int(level["width_px"]) / width_pt
        if max(x1 - x0, y1 - y0) * scale <= long_side_px:
            chosen = level
            break
    sx, sy = int(chosen["width_px"]) / width_pt, int(chosen["height_px"]) / height_pt
    px0, py0 = max(0, math.floor(x0 * sx)), max(0, math.floor(y0 * sy))
    px1, py1 = min(int(chosen["width_px"]), math.ceil(x1 * sx)), min(int(chosen["height_px"]), math.ceil(y1 * sy))
    if px1 <= px0 or py1 <= py0:
        return None
    first_col, last_col = px0 // tile_px, (px1 - 1) // tile_px
    first_row, last_row = py0 // tile_px, (py1 - 1) // tile_px
    canvas = Image.new("RGB", ((last_col - first_col + 1) * tile_px, (last_row - first_row + 1) * tile_px), (255, 255, 255))
    for row in range(first_row, last_row + 1):
        for column in range(first_col, last_col + 1):
            tile = Image.open(io.BytesIO(read_tile(int(chosen["level"]), column, row))).convert("RGB")
            canvas.paste(tile, ((column - first_col) * tile_px, (row - first_row) * tile_px))
    left, top = px0 - first_col * tile_px, py0 - first_row * tile_px
    cut = canvas.crop((left, top, left + (px1 - px0), top + (py1 - py0)))
    return pix.encode_png(pix.fit_long_side(cut, long_side_px))


class ProfileMaterial:
    """The material of the stored page profiles (``PageProfileReader``). Holds two small caches (pages and the word index of a
    version); both are keyed by immutable rows, so a stale entry cannot be read."""

    def __init__(self, reader: Any) -> None:
        self._reader = reader
        self._pages: OrderedDict[str, PageProfileData] = OrderedDict()
        self._versions: OrderedDict[str, list[PageProfileData]] = OrderedDict()

    def page(self, page_profile_id: str) -> PageProfileData:
        known = self._pages.get(page_profile_id)
        if known is not None:
            self._pages.move_to_end(page_profile_id)
            return known
        data = self._reader.read_page_profile(page_profile_id)
        self._pages[page_profile_id] = data
        while len(self._pages) > _PAGE_CACHE:
            self._pages.popitem(last=False)
        return data

    def overview(self, page_profile_id: str) -> bytes | None:
        from auditmanager.shared.errors import DomainError, ErrorCode

        try:
            data = self._reader.read_preview(page_profile_id)
        except DomainError as error:
            if error.code is ErrorCode.NOT_FOUND:
                return None
            raise
        return pix.encode_png(pix.fit_long_side(pix.decode(data), 1950)) if data else None

    def crop(self, page_profile_id: str, box: Sequence[float], *, long_side_px: int) -> bytes | None:
        from auditmanager.shared.errors import DomainError, ErrorCode

        profile = self.page(page_profile_id)
        tiles = profile.row.summary.get("tiles") or {}

        def read(level: int, column: int, row: int) -> bytes:
            return self._reader.read_tile(page_profile_id, level=level, column=column, row=row)

        try:
            return crop_from_tiles(tiles, profile.width_pt, profile.height_pt, read, box, long_side_px=long_side_px)
        except DomainError as error:
            if error.code is ErrorCode.NOT_FOUND:
                return None
            raise

    def _version_pages(self, version_uid: str) -> list[PageProfileData]:
        known = self._versions.get(version_uid)
        if known is not None:
            self._versions.move_to_end(version_uid)
            return known
        pages = [p for p in self._reader.read_version_profiles(version_uid) if p.words]
        self._versions[version_uid] = pages
        while len(self._versions) > _VERSION_CACHE:
            self._versions.popitem(last=False)
        return pages

    def find_marks(
        self, versions: Mapping[str, str], marks: Sequence[str], *, skip_pages: Mapping[str, int | None], limit: int,
    ) -> list[MarkHit]:
        index: dict[str, dict[str, list[tuple[PageProfileData, Any]]]] = {}
        for side, version in versions.items():
            side_index: dict[str, list[tuple[PageProfileData, Any]]] = {}
            for page in self._version_pages(version):
                for word in page.words:
                    side_index.setdefault(norm_mark(word.text), []).append((page, word))
            index[side] = side_index
        return find_marks_in(index, marks, skip_pages=skip_pages, limit=limit)


def find_marks_in(
    index: Mapping[str, Mapping[str, Sequence[tuple[PageProfileData, Any]]]], marks: Sequence[str], *,
    skip_pages: Mapping[str, int | None], limit: int,
) -> list[MarkHit]:
    """``context.xrefs`` over a prepared index ``{side: {normalised word: [(page, word)]}}`` (``context.py:170-206``)."""
    hits: list[MarkHit] = []
    seen: set[tuple[str, str, int]] = set()
    for mark in marks:
        key = norm_mark(mark)
        found: list[MarkHit] = []
        for side in ("B", "A"):
            for page, word in index.get(side, {}).get(key, ()):
                if page.row.page_number == skip_pages.get(side):
                    continue
                found.append(MarkHit(
                    mark=mark, side=side, page=page.row.page_number, bbox=geo.rounded(list(word[:4])),
                    text=row_text_near(page.words, word[:4]),
                    page_label=", ".join(
                        part for part in (
                            f"лист {page.stamp.sheet_number}" if page.stamp.sheet_number else "", page.stamp.sheet_title or "",
                        ) if part
                    ),
                ))
        if not found or len(found) > MARK_MAX_COMMON:
            continue  # no match, or a designation that is on too many pages -- noise (context.py:195-196)
        found.sort(key=lambda h: (h["side"] != "B", h["page"]))
        for hit in found[:limit]:
            signature = (key, hit["side"], hit["page"])  # one page, one match per designation
            if signature in seen:
                continue
            seen.add(signature)
            hits.append(hit)
    for number, hit in enumerate(hits, 1):
        hit["id"] = f"X{number}"
    return hits
