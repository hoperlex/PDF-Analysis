"""Conservative sheet metadata from the stored, deterministic page-profile stamp.

Names and stamp text only propose links. A profile ID and version ID remain the
identities, and no guessed field can create an expert map revision by itself.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

__all__ = ["SheetPassport", "from_stamp"]

_TYPE = re.compile(r"\b(план|разрез|фасад|схема|узел|спецификация|ведомость)\b")
_BUILDING = re.compile(r"\bкорп(?:ус|\.)\s*(\d+[а-яa-z]?)\b")
_FLOOR = re.compile(
    r"(?:\bэтаж[а-я]*\s*([+-]?\d+)\b|"
    r"\b([+-]?\d+)\s*(?:[-–]?\s*(?:го|й|ый))?\s*этаж[а-я]*\b)"
)
_LEVEL = re.compile(r"\b(?:уровень|отм(?:етка|\.)?)\s*([+-]?\d+(?:[.,]\d+)?)\b")


def _plain(value: str | None) -> str | None:
    if value is None:
        return None
    clean = " ".join(unicodedata.normalize("NFKC", value).casefold().split())
    return clean or None


@dataclass(frozen=True, slots=True)
class SheetPassport:
    profile_id: str
    version_uid: str
    page_number: int
    side: str
    sheet_type: str | None = None
    building: str | None = None
    floor: str | None = None
    level: str | None = None
    sheet_number: str | None = None


def from_stamp(
    *, profile_id: str, version_uid: str, page_number: int, side: str,
    sheet_title: str | None, sheet_number: str | None,
) -> SheetPassport:
    """Parse only explicit title tokens; missing fields remain unknown."""
    title = _plain(sheet_title) or ""
    kind = _TYPE.search(title)
    building = _BUILDING.search(title)
    floor = _FLOOR.search(title)
    level = _LEVEL.search(title)
    roof = bool(re.search(r"\bкровл[яиею]\b", title))
    return SheetPassport(
        profile_id=profile_id, version_uid=version_uid,
        page_number=page_number, side=side,
        sheet_type=None if kind is None else kind.group(1),
        building=None if building is None else building.group(1),
        floor="кровля" if roof else None if floor is None else floor.group(1) or floor.group(2),
        level=None if level is None else level.group(1).replace(",", "."),
        sheet_number=_plain(sheet_number),
    )
