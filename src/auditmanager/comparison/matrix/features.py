"""What the matrix reads of a page: its words, stamp, kind and ink mask, in the form the score and the rules use.

`CMP-MATRIX-01`. This is ``PageFeatures`` of the original (``lineage.py:71-172``) rebuilt over our page profile
(:class:`~auditmanager.comparison.profile.models.PageProfileData`). The identity of a page here is its version and
its profile (``version_uid`` and ``profile_id``), never its number alone (``AGENTS.md`` section 4).

**What the profile does not carry, and what replaces it** (each is a limit in the report):

* *kind* (``spec``, ``permit``, ``drawing``, ``title``, ``unknown``): the original takes it from its stamp parser's
  form (``stamp.py:196-211``). Our stamp reader gives fields, not a form, so ``drawing`` stands for a page with a
  recognised stamp (the original's ``drawing`` and ``text`` are compatible with one another in the score, so the
  distinction would change nothing), and ``spec``/``permit`` are decided by the original's own words rule.
* *service zones* (``profile.py:99-106``): the original's stamp zone comes from the position of the label row.
  Here it is the 185 x 55 mm block against the frame's bottom-right corner (190 x 60 mm against the page when no
  frame is found) -- the size of a GOST 21.101 title block, which the original's own default zone uses
  (``stamp.py:110``). The release-stamp zone and its QR code are not detected; the frame margin zones are.
* *hidden SHX text* (``lineage.py:48-69``): the profile has none, so a stamp is read from the text layer only.

The masks are kept compressed and unpacked through a bounded cache (:class:`MaskCache`): a document set of twelve
versions of a hundred A1 sheets must not hold a thousand uncompressed rasters.
"""

from __future__ import annotations

import re
import zlib
from collections import Counter, OrderedDict
from collections.abc import Callable, Iterable
from typing import Any, Final

import cv2
import numpy as np

from auditmanager.comparison.matrix import settings
from auditmanager.comparison.profile.models import PageProfileData

__all__ = [
    "MM",
    "MaskCache",
    "PageFeatures",
    "detect_frame",
    "norm",
]

MM: Final[float] = 72.0 / 25.4
#: The mask resolution of the page profile (``profile.limits.MASK_DPI``): the zone arithmetic uses ``k = dpi / 72``.
_MASK_DPI: Final[int] = 36
_TOKEN_STRIP: Final[re.Pattern[str]] = re.compile(r"^[\W_]+|[\W_]+$", re.U)
_DIGITS_1_4: Final[re.Pattern[str]] = re.compile(r"\d{1,4}")


def norm(text: str) -> str:
    """The token form of a word (``lineage.py:40-42``): trimmed, lower case, edge punctuation stripped."""
    return _TOKEN_STRIP.sub("", (text or "").strip().lower())


def detect_frame(
    page_w: float, page_h: float, segments: Iterable[tuple[float, float, float, float]]
) -> list[float] | None:
    """The GOST frame from long lines near the edges: about 20 mm on the left, 5 mm on the others.

    ``stamp.py:62-77``. ``None`` unless three of the four sides are found.
    """

    def near(values: list[float], lo: float, hi: float) -> float | None:
        hits = [v for v in values if lo <= v <= hi]
        return min(hits, key=lambda v: abs(v - (lo + hi) / 2)) if hits else None

    segment_list = list(segments)
    verticals = [x0 for x0, y0, x1, y1 in segment_list if abs(x0 - x1) < 0.8 and abs(y1 - y0) >= 0.4 * page_h]
    horizontals = [y0 for x0, y0, x1, y1 in segment_list if abs(y0 - y1) < 0.8 and abs(x1 - x0) >= 0.4 * page_w]
    left = near(verticals, 12 * MM, 28 * MM)
    right = near(verticals, page_w - 9 * MM, page_w - 2 * MM)
    top = near(horizontals, 2 * MM, 9 * MM)
    bottom = near(horizontals, page_h - 9 * MM, page_h - 2 * MM)
    if sum(v is not None for v in (left, right, top, bottom)) < 3:
        return None
    return [
        left if left is not None else 20 * MM,
        top if top is not None else 5 * MM,
        right if right is not None else page_w - 5 * MM,
        bottom if bottom is not None else page_h - 5 * MM,
    ]


class MaskCache:
    """A least-recently-used cache of unpacked rasters, bounded in bytes. The values are pure functions of the
    page, so what it holds can never change a result, only how long one takes."""

    def __init__(self, budget_bytes: int = 96 * 1024 * 1024) -> None:
        self._budget = budget_bytes
        self._used = 0
        self._items: OrderedDict[tuple[str, str], np.ndarray] = OrderedDict()

    def get(self, key: tuple[str, str], make: Callable[[], np.ndarray]) -> np.ndarray:
        found = self._items.get(key)
        if found is not None:
            self._items.move_to_end(key)
            return found
        value = make()
        self._items[key] = value
        self._used += value.nbytes
        while self._used > self._budget and len(self._items) > 1:
            _, dropped = self._items.popitem(last=False)
            self._used -= dropped.nbytes
        return value

    @property
    def used_bytes(self) -> int:
        return self._used


class _Packed:
    """A binary raster kept as zlib-compressed bits."""

    __slots__ = ("shape", "data")

    def __init__(self, array: np.ndarray) -> None:
        self.shape = (int(array.shape[0]), int(array.shape[1]))
        self.data = zlib.compress(np.packbits(array.astype(bool), axis=None).tobytes(), 3)

    def unpack(self) -> np.ndarray:
        bits = np.unpackbits(np.frombuffer(zlib.decompress(self.data), dtype=np.uint8))
        return bits[: self.shape[0] * self.shape[1]].reshape(self.shape).astype(np.uint8)


def _zone_cells(zone: list[float]) -> tuple[int, int, int, int]:
    k = _MASK_DPI / 72.0
    return max(0, int(zone[1] * k)), int(zone[3] * k) + 1, max(0, int(zone[0] * k)), int(zone[2] * k) + 1


class PageFeatures:
    """One page, read for matching. Built once, immutable after construction (the caches are not state)."""

    def __init__(self, data: PageProfileData, *, rules: frozenset[str], cache: MaskCache) -> None:
        row = data.row
        self.version_uid: str = row.version_uid
        self.page: int = row.page_number
        self.profile_id: str = row.page_profile_id
        self.status: str = row.status
        self.rules = rules
        self._cache = cache
        width, height = float(data.width_pt), float(data.height_pt)
        self.width, self.height = width, height
        self.size = (round(width), round(height))
        self.scan: bool = bool(data.scan)
        stamp = data.stamp
        designation = (stamp.designation or "").strip()
        self.designation: str = designation
        self.sheet_no: str = (stamp.sheet_number or "").strip()
        title_raw = " ".join((stamp.sheet_title or "").split())
        self.title_raw: str = title_raw
        self.title: str = norm(title_raw)
        recognised = bool(designation or self.sheet_no or title_raw)
        self.stamp_source: str = "text" if recognised else ""

        words = [(w.x0, w.top, w.x1, w.bottom, w.text) for w in data.words]
        segments = [(ln.x0, ln.top, ln.x1, ln.bottom) for ln in data.lines]
        frame = detect_frame(width, height, segments) if width > 0 and height > 0 else None
        self.frame: list[float] | None = frame
        zones: list[list[float]] = []
        if recognised or frame:
            right = frame[2] if frame else width
            bottom = frame[3] if frame else height
            if frame:
                zones.append([right - 185 * MM - 1.5 * MM, bottom - 55 * MM - 1.5 * MM, width, height])
            else:
                zones.append([width - 190 * MM, height - 60 * MM, width, height])
        if frame:
            fx0, fy0, fx1, fy1 = frame
            for rect in ([0, 0, fx0, height], [fx1, 0, width, height], [fx0, 0, fx1, fy0], [fx0, fy1, fx1, height]):
                if rect[2] - rect[0] > 0.5 and rect[3] - rect[1] > 0.5:
                    zones.append([float(v) for v in rect])
        self.zones = zones

        self.kind: str = self._kind(words, designation, recognised, frame, width, height)
        self.permit_no: str = self._permit_no(words, height) if (self.kind == "permit" or "resolve" in rules) else ""

        tokens: Counter[str] = Counter()
        pos: set[tuple[str, int, int]] = set()
        for x0, top, x1, bottom, text in words:
            cx, cy = (x0 + x1) / 2, (top + bottom) / 2
            if any(z[0] <= cx <= z[2] and z[1] <= cy <= z[3] for z in zones):
                continue
            token = norm(str(text))
            if not token:
                continue
            tokens[token] += 1
            pos.add((token, int(cx // 15), int(cy // 15)))
        self.tokens: Counter[str] = tokens
        self.token_total: int = sum(tokens.values())
        self.template: frozenset[str] = frozenset(t for t in tokens if not any(ch.isdigit() for ch in t))
        self.footer_no: str = ""
        if "pageno" in rules and not self.stamp_source:
            self.footer_no = self._footer_no(words, height)
        self.has_text: bool = self.token_total >= settings.MATCH_TEXT_MIN_TOKENS
        self.pos: set[tuple[str, int, int]] = pos
        #: The page's position among the pages of its version, 0..1 (set by the loader; ``lineage.py:331-332``).
        self.rel: float = 0.0

        self._full: _Packed | None = None
        self._half: _Packed | None = None
        #: Ink pixels of the half-resolution and of the full mask (the denominators of the overlap measures).
        self.half_ink: int = 0
        self.full_ink: int = 0
        if data.ink_mask is not None:
            mask = data.ink_mask.as_array().astype(np.uint8)
            for zone in zones:
                y0, y1, x0, x1 = _zone_cells(zone)
                mask[y0:y1, x0:x1] = 0
            self._full = _Packed(mask)
            self.full_ink = int((mask > 0).sum())
            half = cv2.resize(
                mask, (max(1, mask.shape[1] // 2), max(1, mask.shape[0] // 2)), interpolation=cv2.INTER_AREA
            )
            half_bits = (half > 0).astype(np.uint8)
            self._half = _Packed(half_bits)
            self.half_ink = int(half_bits.sum())
        self.has_mask: bool = self._half is not None

    # -- kind, permit number, footer number ------------------------------------------------------------------

    @staticmethod
    def _kind(
        words: list[tuple[float, float, float, float, str]],
        designation: str,
        recognised: bool,
        frame: list[float] | None,
        width: float,
        height: float,
    ) -> str:
        """``classify_kind`` (``stamp.py:196-211``) then the ``kind`` rule of ``PageFeatures`` (``lineage.py:101-106``)."""
        top = {w[4].strip().lower() for w in words if w[1] < height * 0.3}
        if designation.upper().endswith(".СО") or (
            "поз." in top
            and any(t.startswith("наименование") for t in top)
            and any(t.startswith("кол") for t in top)
        ):
            return "spec"
        first = [w[4].strip().lower() for w in sorted(words, key=lambda w: (w[1], w[0]))[:12]]
        if "разрешение" in first:
            return "permit"
        if recognised:
            return "drawing"
        joined = " " + norm(" ".join(str(w[4]) for w in words)) + " "
        return "title" if (frame is None and any(k in joined for k in settings.COVER_WORDS)) else "unknown"

    @staticmethod
    def _permit_no(words: list[tuple[float, float, float, float, str]], height: float) -> str:
        """The number under the word «Разрешение» in the top quarter of the sheet (``lineage.py:107-114``)."""
        label = next((w for w in words if norm(str(w[4])).startswith("разрешени") and w[1] < height * 0.25), None)
        if label is None:
            return ""
        below = [
            w
            for w in words
            if label[3] < w[1] < label[3] + 40 and abs((w[0] + w[2]) / 2 - (label[0] + label[2]) / 2) < 50
        ]
        return " ".join(str(w[4]) for w in sorted(below, key=lambda w: w[0])).strip()

    @staticmethod
    def _footer_no(words: list[tuple[float, float, float, float, str]], height: float) -> str:
        """The page number in the footer band of a page with no GOST stamp (``lineage.py:121-132``): the only
        1-4 digit number in the bottom (otherwise the top) strip."""
        band = settings.RESOLVE_FOOTER_BAND
        for inside in (lambda w: w[1] > height * band, lambda w: w[3] < height * (1 - band)):
            found = [str(w[4]).strip() for w in words if _DIGITS_1_4.fullmatch(str(w[4]).strip()) and inside(w)]
            if found:
                return found[0] if len(found) == 1 else ""
        return ""

    # -- the rasters ---------------------------------------------------------------------------------------

    @property
    def mask(self) -> np.ndarray | None:
        """The ink mask at half the profile's resolution with the service zones cleared (``lineage.py:151-158``)."""
        if self._half is None:
            return None
        half = self._half
        return self._cache.get((self.profile_id, "half"), half.unpack)

    def full_mask(self) -> np.ndarray | None:
        """The 36 dpi ink mask with the service zones cleared (``lineage.py:160-172``)."""
        if self._full is None:
            return None
        full = self._full
        return self._cache.get((self.profile_id, "full"), full.unpack)

    def dilated(self) -> np.ndarray | None:
        """``mask`` dilated by a 3 x 3 square, for the overlap measure."""
        mask = self.mask
        if mask is None:
            return None
        return self._cache.get((self.profile_id, "dil"), lambda: cv2.dilate(mask, np.ones((3, 3), np.uint8)))

    def dilated_full(self) -> np.ndarray | None:
        full = self.full_mask()
        if full is None:
            return None
        return self._cache.get((self.profile_id, "fdil"), lambda: cv2.dilate(full, np.ones((3, 3), np.uint8)))

    def mask_shape(self) -> tuple[int, int] | None:
        return None if self._half is None else self._half.shape

    def full_shape(self) -> tuple[int, int] | None:
        return None if self._full is None else self._full.shape

    def public_ref(self) -> dict[str, Any]:
        """The page as a stored reference: version, number and profile identity."""
        return {"version_uid": self.version_uid, "page_number": self.page, "page_profile_id": self.profile_id}
