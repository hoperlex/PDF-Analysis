"""Hand-made page profiles for the rule tests: a page is a list of words, a stamp and (optionally) a mask.

Nothing here renders anything; the point is to control exactly which words two pages share, where they stand and
what the stamp says, so that a rule's threshold or condition is crossed on purpose.
"""

from __future__ import annotations

from datetime import datetime, timezone

from auditmanager.comparison.matrix import settings
from auditmanager.comparison.matrix.features import MaskCache, PageFeatures
from auditmanager.comparison.profile.models import InkMask, PageProfileData, PageProfileRow, StampFields, Word

WIDTH, HEIGHT = 595.0, 842.0
_COUNTER = [0]


def words(tokens: list[str], *, x0: float = 100.0, y0: float = 100.0, per_row: int = 8) -> tuple[Word, ...]:
    """One word per token on a grid whose cells (15 pt) are all different."""
    return tuple(
        Word(x0 + 60.0 * (i % per_row), y0 + 24.0 * (i // per_row), x0 + 60.0 * (i % per_row) + 40.0, y0 + 24.0 * (i // per_row) + 12.0, t)
        for i, t in enumerate(tokens)
    )


def blank_mask(width: float = WIDTH, height: float = HEIGHT) -> InkMask:
    w, h = int(width * 36 / 72) + 1, int(height * 36 / 72) + 1
    row_bytes = (w + 7) // 8
    return InkMask(dpi=36, width_px=w, height_px=h, row_bytes=row_bytes, data=bytes(row_bytes * h))


def page(
    version: str, number: int, tokens: list[str] | None = None, *, designation: str | None = None,
    sheet_number: str | None = None, title: str | None = None, scan: bool = False, mask: bool = False,
    extra_words: tuple[Word, ...] = (), status: str = "ready", size: tuple[float, float] = (WIDTH, HEIGHT),
    y0: float = 100.0,
) -> PageProfileData:
    _COUNTER[0] += 1
    row = PageProfileRow(
        page_profile_id=f"cpr_{_COUNTER[0]:026d}".replace("0", "0"), version_uid=version, page_number=number,
        content_key=f"{version}:{number}:{_COUNTER[0]}".ljust(64, "0")[:64], algo_version="cmp-profile/1",
        status=status, reason=None, summary={}, profile_blob_id=None, preview_blob_id=None, thumbnail_blob_id=None,
        created_at=datetime(2026, 10, 28, tzinfo=timezone.utc),
    )
    return PageProfileData(
        row=row, width_pt=size[0], height_pt=size[1], rotation=0, has_text_layer=not scan, scan=scan,
        content_merkle=None, words=words(tokens or [], y0=y0) + extra_words,
        stamp=StampFields(designation=designation, sheet_number=sheet_number, sheet_title=title),
        ink_mask=blank_mask(*size) if mask else None,
    )


def features(pages: list[PageProfileData], cache: MaskCache | None = None) -> list[PageFeatures]:
    shared = cache or MaskCache()
    out = [PageFeatures(p, rules=settings.RULES, cache=shared) for p in pages]
    for position, f in enumerate(out):
        f.rel = position / max(1, len(out) - 1)
    return out


def versions_features(spec: dict[str, list[PageProfileData]]) -> dict[str, list[PageFeatures]]:
    cache = MaskCache()
    return {vid: features(pages, cache) for vid, pages in spec.items()}


def tokens(prefix: str, count: int) -> list[str]:
    """``count`` distinct words that no other prefix produces (letters only, so they are plain words)."""
    return [f"{prefix}{'abcdefghijklmnopqrstuvwxyz'[i % 26]}{'abcdefghijklmnopqrstuvwxyz'[i // 26]}слово" for i in range(count)]
