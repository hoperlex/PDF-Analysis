"""The stored profile of a page: one ZIP archive holding the profile document, the ink mask and the
tile levels the worker keeps.

`CMP-PROFILE-01`. ``comparison_page_profile`` has three blob columns, all audited and write-once:
``profile_blob_id``, ``preview_blob_id`` and ``thumbnail_blob_id``. The preview and the thumbnail are
PNGs that are served as they are; everything else a page keeps -- the words and lines, the annotations,
the ink mask and the tile levels 2 and up of ADR-0025's addendum -- is one archive in the first column, so
that **every byte the lane stores is reachable from an audited reference** and none of it is an orphan
that a reconciliation report would have to explain. The archive is deterministic (sorted names, a fixed
timestamp, stored PNG members and deflated JSON), so equal profiles are equal blobs.

Members
-------
``profile.json``
    the document: ``schema``, ``algo_version``, ``page``, the size, ``words`` as
    ``[x0, top, x1, bottom, text]``, ``lines`` as ``[x0, top, x1, bottom, linewidth, colour]``,
    ``images`` as boxes, ``annotations``, ``stamp``, ``extract`` (``null`` when the extraction failed);
``mask.bin``
    the ink mask: rows padded to whole bytes, most significant bit first, 1 is ink;
``tiles/<level>/<column>_<row>.png``
    the tiles of the levels the worker stores.

The reader opens members by name and never extracts to a path.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from collections.abc import Iterable, Mapping
from typing import Any, Final

__all__ = [
    "MASK_MEMBER",
    "PACK_MEDIA_TYPE",
    "PROFILE_MEMBER",
    "PackReader",
    "PackUnreadable",
    "build_pack",
    "canonical_json",
    "tile_member",
]

PACK_MEDIA_TYPE: Final[str] = "application/zip"
PROFILE_MEMBER: Final[str] = "profile.json"
MASK_MEMBER: Final[str] = "mask.bin"
_TIMESTAMP: Final[tuple[int, int, int, int, int, int]] = (1980, 1, 1, 0, 0, 0)
_MEMBER_NAME = re.compile(r"^(profile\.json|mask\.bin|tiles/\d{1,2}/\d{1,4}_\d{1,4}\.png)$")
#: A profile document larger than this once inflated is refused: a defence in depth, the worker wrote it.
MAX_PROFILE_BYTES: Final[int] = 512 * 1024 * 1024


class PackUnreadable(ValueError):
    """The archive is not one this lane wrote."""


def canonical_json(value: Any) -> bytes:
    """Compact JSON with sorted object keys: the same value is always the same bytes."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def tile_member(level: int, column: int, row: int) -> str:
    return f"tiles/{level}/{column}_{row}.png"


def _member(name: str, compress: int) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=_TIMESTAMP)
    info.compress_type = compress
    info.external_attr = 0o600 << 16
    return info


def build_pack(
    document: Mapping[str, Any],
    *,
    mask: bytes | None,
    tiles: Iterable[tuple[int, int, int, bytes]],
) -> bytes:
    """The archive of one page: ``tiles`` is ``(level, column, row, png bytes)``."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", allowZip64=False) as archive:
        archive.writestr(_member(PROFILE_MEMBER, zipfile.ZIP_DEFLATED), canonical_json(document))
        if mask is not None:
            archive.writestr(_member(MASK_MEMBER, zipfile.ZIP_DEFLATED), mask)
        for level, column, row, data in sorted(tiles, key=lambda item: item[:3]):
            archive.writestr(_member(tile_member(level, column, row), zipfile.ZIP_STORED), data)
    return buffer.getvalue()


class PackReader:
    """Read members of a stored archive by name."""

    def __init__(self, data: bytes) -> None:
        try:
            self._archive = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as failure:
            raise PackUnreadable("not an archive") from failure
        self._names = {info.filename: info for info in self._archive.infolist()}
        if PROFILE_MEMBER not in self._names or not all(_MEMBER_NAME.fullmatch(n) for n in self._names):
            raise PackUnreadable("unexpected members")

    def document(self) -> dict[str, Any]:
        info = self._names[PROFILE_MEMBER]
        if info.file_size > MAX_PROFILE_BYTES:
            raise PackUnreadable("profile document too large")
        value = json.loads(self._archive.read(info))
        if not isinstance(value, dict):
            raise PackUnreadable("profile document is not an object")
        return value

    def mask(self) -> bytes | None:
        info = self._names.get(MASK_MEMBER)
        return None if info is None else self._archive.read(info)

    def tile(self, level: int, column: int, row: int) -> bytes | None:
        info = self._names.get(tile_member(level, column, row))
        return None if info is None else self._archive.read(info)

    def tile_names(self) -> list[str]:
        return sorted(name for name in self._names if name.startswith("tiles/"))
