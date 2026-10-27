"""Read stored page profiles: the five sealed operations and the typed profile for other lanes.

`CMP-PROFILE-01`. Everything here reads what the worker stored -- rows of ``comparison_page_profile`` and
the blobs they name -- and **never calls PDFium**: the preview, the thumbnail and the stored tile levels are
bytes; the two levels that are not stored are rendered by :class:`~auditmanager.comparison.profile.tiles.TileRenderer`
in a child process. Sessions are short: each method reads its rows and lets go of the connection before it
reads a blob or starts a child.

An unknown profile, a profile without the asked-for image, a tile outside the pyramid: ``not_found``.
An unknown version: ``not_found`` (never an empty page, which would read as «no pages»). A page whose
profile has not been computed is simply absent from the list, and the version's ``page_count`` says how
many there should be.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.profile import limits
from auditmanager.comparison.profile.models import (
    Annotation,
    InkMask,
    PageProfileData,
    PageProfileRow,
    StampFields,
    VectorLine,
    Word,
)
from auditmanager.comparison.profile.pack import PackReader
from auditmanager.comparison.profile.repository import PageProfileRepository
from auditmanager.comparison.profile.source import load_source_version
from auditmanager.comparison.profile.tiles import TileRenderer
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobNotFoundError, StorageError, parse_blob_id

__all__ = ["PageProfileReader"]


def _not_found(what: str = "PageProfile") -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type=what)


class PageProfileReader:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        blob_store: Any,
        *,
        tiles: TileRenderer | None = None,
    ) -> None:
        self._factory = session_factory
        self._store = blob_store
        self._tiles = tiles
        self._repository = PageProfileRepository()

    def _renderer(self) -> TileRenderer:
        if self._tiles is None:
            self._tiles = TileRenderer()
        return self._tiles

    # -- the rows ---------------------------------------------------------------------------

    def list_profiles(
        self, version_uid: str, *, after_page: int, limit: int
    ) -> tuple[list[PageProfileRow], bool]:
        """Up to ``limit`` profiles with a page number above ``after_page``, and whether more follow."""
        with session_scope(self._factory) as session:
            if not self._repository.version_exists(session, version_uid):
                raise _not_found("DocumentVersion")
            rows = self._repository.list_after(
                session, version_uid, limits.ALGO_VERSION, after_page=after_page, limit=limit + 1
            )
        return rows[:limit], len(rows) > limit

    def get_profile(self, page_profile_id: str) -> PageProfileRow:
        with session_scope(self._factory) as session:
            row = self._repository.get(session, page_profile_id)
        if row is None:
            raise _not_found()
        return row

    # -- the bytes --------------------------------------------------------------------------

    def _blob(self, blob_id: str) -> bytes:
        try:
            return self._store.read(parse_blob_id(blob_id), verify=True)
        except BlobNotFoundError:
            raise _not_found() from None
        except StorageError as failure:
            from auditmanager.ingest import domain_error_from_storage

            raise domain_error_from_storage(failure, blob_id=blob_id) from None

    def read_preview(self, page_profile_id: str) -> bytes:
        row = self.get_profile(page_profile_id)
        if row.preview_blob_id is None:
            raise _not_found()
        return self._blob(row.preview_blob_id)

    def read_thumbnail(self, page_profile_id: str) -> bytes:
        row = self.get_profile(page_profile_id)
        if row.thumbnail_blob_id is None:
            raise _not_found()
        return self._blob(row.thumbnail_blob_id)

    def read_tile(self, page_profile_id: str, *, level: int, column: int, row: int) -> bytes:
        """One tile of the page's pyramid: from the stored archive for levels 2 and up, rendered in
        a child for levels 0 and 1."""
        profile = self.get_profile(page_profile_id)
        pyramid = (profile.summary.get("tiles") or {}).get("levels") or []
        if level >= len(pyramid):
            raise _not_found("PageTile")
        entry = pyramid[level]
        if not (0 <= column < int(entry["columns"]) and 0 <= row < int(entry["rows"])):
            raise _not_found("PageTile")
        if entry.get("stored"):
            if profile.profile_blob_id is None:
                raise _not_found("PageTile")
            data = PackReader(self._blob(profile.profile_blob_id)).tile(level, column, row)
            if data is None:
                raise _not_found("PageTile")
            return data
        if level > limits.MAX_ON_REQUEST_TILE_LEVEL:
            raise _not_found("PageTile")
        with session_scope(self._factory) as session:
            source = load_source_version(session, profile.version_uid)
        return self._renderer().render(
            self._store, source, page_number=profile.page_number, level=level, column=column, row=row
        )

    # -- the typed profile for the matrix and the engine -----------------------------------

    def read_page_profile(self, page_profile_id: str) -> PageProfileData:
        """The profile with its archive opened. A page that was refused, or whose archive is missing,
        has no words or mask: its :attr:`PageProfileRow.status` says why."""
        row = self.get_profile(page_profile_id)
        return self.open_profile(row)

    def open_profile(self, row: PageProfileRow) -> PageProfileData:
        summary = row.summary
        base = {
            "row": row,
            "width_pt": float(summary.get("width_pt") or 0.0),
            "height_pt": float(summary.get("height_pt") or 0.0),
            "rotation": int(summary.get("rotation") or 0),
            "has_text_layer": bool(summary.get("text_layer", False)),
            "scan": bool(summary.get("scan", False)),
            "content_merkle": summary.get("content_merkle"),
        }
        if row.profile_blob_id is None:
            return PageProfileData(**base)
        archive = PackReader(self._blob(row.profile_blob_id))
        document = archive.document()
        mask_info, mask_bytes = document.get("mask"), archive.mask()
        mask = None
        if mask_info and mask_bytes is not None:
            mask = InkMask(
                dpi=int(mask_info["dpi"]),
                width_px=int(mask_info["width_px"]),
                height_px=int(mask_info["height_px"]),
                row_bytes=int(mask_info["row_bytes"]),
                data=mask_bytes,
            )
        raster = summary.get("raster")
        stamp = document.get("stamp") or {}
        return PageProfileData(
            **base,
            words=tuple(Word(w[0], w[1], w[2], w[3], w[4]) for w in document.get("words", ())),
            lines=tuple(
                VectorLine(v[0], v[1], v[2], v[3], v[4], None if v[5] is None else tuple(v[5]))
                for v in document.get("lines", ())
            ),
            image_boxes=tuple(tuple(b) for b in document.get("images", ())),  # type: ignore[arg-type]
            annotations=tuple(
                Annotation(a["subtype"], None if a["rect"] is None else tuple(a["rect"]), a["contents"], a["sha256"])
                for a in document.get("annotations", ())
            ),
            stamp=StampFields(
                designation=stamp.get("designation"),
                sheet_number=stamp.get("sheet_number"),
                sheet_title=stamp.get("sheet_name"),
                revision_number=stamp.get("revision_number"),
                release_date=stamp.get("release_date"),
            ),
            ink_mask=mask,
            raster=None if not raster else (int(raster["dpi"]), int(raster["width_px"]), int(raster["height_px"])),
        )

    def read_version_profiles(self, version_uid: str) -> list[PageProfileData]:
        """Every stored profile of a version, by page number, archives opened (for the lanes that
        compare whole versions). An unknown version is ``not_found``."""
        profiles: list[PageProfileData] = []
        after = 0
        while True:
            rows, more = self.list_profiles(version_uid, after_page=after, limit=100)
            profiles.extend(self.open_profile(row) for row in rows)
            if not more:
                return profiles
            after = rows[-1].page_number
