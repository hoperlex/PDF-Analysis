"""The PNG of a norm page, made once and kept, for the AI critic's task (`M7-NORM-PNG`, plan-v5 section 3.4, ``DECISION-MEMORY-01`` section 6.3).

**What it is.** Custody holds every norm page as a one-page PDF (``norm_custody_binding``: role ``norm_source``, target the norm document, anchor
kind ``crop``, the anchor the drop's ``blk_...`` block id, which is also ``norm_paragraph.block_ref``). A task's ``images`` are PNGs
(``RunnerImage.media_type`` is the constant ``image/png``), so a page is rendered **once**, under ``PDFIUM_LOCK``, published as a Blob and
recorded in ``norm_crop_render`` -- one immutable row per (binding, render profile), migration ``0065``. Every later delivery of the page reuses it.
The identity the critic's task declares is ``crop_id: norm.<nbd_...>``: the custody binding, an opaque id that is never a path, a file name or a
display number.

**What it is not.** It decides nothing about *whether* a task carries images: that is the runtime's rule (``runs.extended_review``: only a run
that carries the reference policy, only a ``review:main`` member that serves images, never a Claude Code host). This module answers which pages of
the paragraphs it is given may be shown, and produces them.

**Which pages.** Only those of the paragraphs the caller passes -- the ``norm_context`` rows of the request the critic was given, which are the
candidates of this run's own norm search -- in their order (the paragraphs the critic's norm assessment cites come first), at most
:data:`MAX_IMAGES_PER_TASK` pages, one per page however many paragraphs sit on it, and never a page the paragraphs do not name.

**A page that cannot be produced** is listed with a fixed reason and the text still goes to the critic; nothing is dropped silently and nothing is
rendered smaller than asked (``page_too_large``). A source that cannot be read leaves no row, so the next delivery tries again; a row that exists
is never rewritten.

The renderer is the one the geometry stage uses (``analysis.public.PdfiumDocument``, ``render_page``), imported where it is used so that this
context stays importable without it. Pillow encodes the PNG. No new dependency.
"""

from __future__ import annotations

import hashlib
import io
import os
import secrets
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError
from auditmanager.storage.public import (
    BlobDeclaration,
    BlobMetadataRepository,
    DurablePublicationStore,
    StorageError,
    VerifiedBlob,
    parse_blob_id,
    parse_blob_role,
)

__all__ = [
    "CROP_ID_PREFIX",
    "MAX_IMAGES_PER_TASK",
    "MAX_PARAGRAPHS_EXAMINED",
    "NormPageImage",
    "NormPageImages",
    "NormPageRender",
    "PageImageSelection",
    "PageRenderRefused",
    "REASON_PAGE_NOT_IN_CUSTODY",
    "RENDER_DPI",
    "RENDER_PROFILE",
    "RenderedPage",
    "render_pdf_page",
]

#: How the page is rendered (the ``render_profile`` of the row). Another profile is another row, never an update of this one.
RENDER_PROFILE: Final[str] = "png-150dpi-v1"
RENDER_DPI: Final[int] = 150
#: A page that would need more pixels is refused, never rendered smaller (ADR-0025 decision 9 caps a full page at 40 Mpx; a norm page is A4-ish,
#: 2.2 Mpx at this profile, and the PNG has to fit the 16 MiB an image may take).
MAX_RENDER_PIXELS: Final[int] = 12_000_000
MAX_SOURCE_PDF_BYTES: Final[int] = 16 << 20
MAX_PNG_BYTES: Final[int] = 16 << 20
#: ``DECISION-MEMORY-01`` section 6.3 and ``ADR-0029`` decision 9: at most two norm page images in one task, inside the runner's eight.
MAX_IMAGES_PER_TASK: Final[int] = 2
#: The paragraphs of ``norm_context`` that are looked at (the consent's ``max_paragraphs`` is 12): the cost of choosing is bounded.
MAX_PARAGRAPHS_EXAMINED: Final[int] = 12
CROP_ID_PREFIX: Final[str] = "norm."
BLOB_ROLE: Final[str] = "norm_crop_render"
_PNG_MEDIA_TYPE: Final[str] = "image/png"
_PNG_SIGNATURE: Final[bytes] = b"\x89PNG\r\n\x1a\n"
#: At most this many page images stay in a service's memory; a run asks for a handful.
_CACHE_PAGES: Final[int] = 16

REASON_PAGE_NOT_IN_CUSTODY: Final[str] = "page_not_in_custody"
_REASON_STORAGE: Final[str] = "storage_unavailable"
_REASON_RENDER_UNREADABLE: Final[str] = "render_unreadable"
_REASON_RENDER_FAILED: Final[str] = "render_failed"


class PageRenderRefused(Exception):
    """A page that cannot be rendered. ``reason`` is a fixed word, never a value."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class RenderedPage:
    png: bytes = field(repr=False)
    width_px: int
    height_px: int


@dataclass(frozen=True, slots=True)
class NormPageRender:
    """One row of ``norm_crop_render``: the PNG Blob of a custody binding under a render profile."""

    norm_custody_binding_id: str
    render_profile: str
    blob_id: str
    sha256: str
    size_bytes: int
    media_type: str
    width_px: int
    height_px: int
    rendered_at: datetime | None = None

    @property
    def crop_id(self) -> str:
        return CROP_ID_PREFIX + self.norm_custody_binding_id


@dataclass(frozen=True, slots=True)
class NormPageImage:
    """A page ready to be declared: the row, the PNG bytes, and the paragraphs of the request that sit on it."""

    render: NormPageRender
    paragraph_ids: tuple[str, ...]
    data: bytes = field(repr=False)

    @property
    def crop_id(self) -> str:
        return self.render.crop_id


@dataclass(frozen=True, slots=True)
class PageImageSelection:
    """The pages chosen for one request, and the paragraphs whose page could not be produced (``(paragraph_id, reason)``)."""

    images: tuple[NormPageImage, ...] = ()
    unavailable: tuple[tuple[str, str], ...] = ()

    @property
    def paragraph_ids(self) -> frozenset[str]:
        return frozenset(paragraph for image in self.images for paragraph in image.paragraph_ids)


# --- the renderer -------------------------------------------------------------------------------------------------------------


def render_pdf_page(pdf: bytes, *, dpi: int = RENDER_DPI, max_pixels: int = MAX_RENDER_PIXELS) -> RenderedPage:
    """The one page of ``pdf`` as a PNG, drawn the way a viewer draws it (the geometry stage's renderer, under ``PDFIUM_LOCK``)."""
    from auditmanager.analysis.public import PdfiumDocument

    descriptor, name = tempfile.mkstemp(prefix="am-norm-page-", suffix=".pdf")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(pdf)
        try:
            with PdfiumDocument(name, stage_id="norm_page_render") as document:
                if document.page_count != 1:
                    raise PageRenderRefused("source_not_one_page")
                image = document.render_page(1, dpi=dpi, max_pixels=max_pixels)
        except DomainError as refusal:
            reason = refusal.detail_fields.get("reason")
            raise PageRenderRefused(
                "page_too_large" if reason == "page_pixel_cap" else "source_unreadable" if reason == "source_unreadable"
                else _REASON_RENDER_FAILED
            ) from None
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        width, height = image.size
    finally:
        Path(name).unlink(missing_ok=True)
    png = buffer.getvalue()
    if not png.startswith(_PNG_SIGNATURE):
        raise PageRenderRefused(_REASON_RENDER_FAILED)
    if len(png) > MAX_PNG_BYTES:
        raise PageRenderRefused("png_too_large")
    return RenderedPage(png=png, width_px=int(width), height_px=int(height))


# --- the rows -----------------------------------------------------------------------------------------------------------------

_COLUMNS = (
    "norm_custody_binding_id, render_profile, blob_id, sha256, size_bytes, media_type, width_px, height_px, rendered_at"
)
_PAGE_OF_PARAGRAPH = text(
    "SELECT b.norm_custody_binding_id, b.blob_id "
    "FROM norm_paragraph p "
    "JOIN norm_document d ON d.norms_snapshot_id = p.norms_snapshot_id AND d.norm_document_pk = p.norm_document_pk "
    "JOIN norm_custody_binding b ON b.role = 'norm_source' AND b.target_kind = 'norm_document' "
    "AND b.target_id = d.norm_document_id AND b.anchor_kind = 'crop' AND b.anchor = p.block_ref "
    "WHERE p.norms_snapshot_id = :snapshot AND d.norm_document_id = :document AND p.norm_paragraph_id = :paragraph"
)
_SELECT_RENDER = text(
    f"SELECT {_COLUMNS} FROM norm_crop_render WHERE norm_custody_binding_id = :binding AND render_profile = :profile"
)
_INSERT_RENDER = text(
    "INSERT INTO norm_crop_render (norm_custody_binding_id, render_profile, blob_id, sha256, size_bytes, media_type, width_px, height_px) "
    "VALUES (:binding, :profile, :blob, :sha256, :size, 'image/png', :width, :height) "
    "ON CONFLICT (norm_custody_binding_id, render_profile) DO NOTHING"
)


def _render_row(row: Any) -> NormPageRender:
    return NormPageRender(
        norm_custody_binding_id=str(row["norm_custody_binding_id"]), render_profile=str(row["render_profile"]),
        blob_id=str(row["blob_id"]), sha256=str(row["sha256"]), size_bytes=int(row["size_bytes"]),
        media_type=str(row["media_type"]), width_px=int(row["width_px"]), height_px=int(row["height_px"]),
        rendered_at=row["rendered_at"])


def _identity(row: object) -> tuple[str, str, str] | None:
    """The three ids a ``norm_context`` row names its paragraph by, or ``None`` for a row that does not carry them."""
    if not isinstance(row, Mapping):
        return None
    found = tuple(row.get(key) for key in ("snapshot_id", "document_id", "paragraph_id"))
    return found if all(isinstance(value, str) and value for value in found) else None  # type: ignore[return-value]


class _Unavailable(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


# --- the service ----------------------------------------------------------------------------------------------------------------


class NormPageImages:
    """Chooses and produces the page images of the paragraphs of one request.

    ``store`` is the Blob store (the run's, or any ``BlobStore``); ``session_factory`` opens its own short transactions, so nothing here touches the
    caller's: a read, then the external effects with no transaction open, then one write. ``renderer`` is injected so that a test states the page
    instead of drawing it; production passes nothing.
    """

    __slots__ = ("_blobs", "_cache", "_factory", "_renderer", "_store")

    def __init__(
        self, *, store: Any, session_factory: sessionmaker[Session],
        renderer: Callable[[bytes], RenderedPage] = render_pdf_page,
    ) -> None:
        self._store = store
        self._factory = session_factory
        self._renderer = renderer
        self._blobs = BlobMetadataRepository()
        self._cache: dict[str, bytes] = {}

    # The choice

    def select(self, norm_context: Sequence[object], *, limit: int = MAX_IMAGES_PER_TASK) -> PageImageSelection:
        """At most ``limit`` pages of the paragraphs of ``norm_context``, in its order, each rendered once and read back.

        ``limit`` can lower the count and never raise it above :data:`MAX_IMAGES_PER_TASK`. A paragraph that names a page custody does not hold, or whose
        page cannot be produced, is listed in ``unavailable`` with the reason; the next page takes its place. Pages are told apart by the custody binding,
        so two paragraphs of one page are one image.
        """
        if type(limit) is not int or not 0 <= limit <= MAX_IMAGES_PER_TASK:
            raise ValueError("norm_page_image_limit_invalid")
        paragraphs: list[tuple[str, str | None, str | None]] = []  # (paragraph_id, binding_id, source blob id)
        seen: set[str] = set()
        with session_scope(self._factory) as session:
            for row in norm_context:
                if len(paragraphs) >= MAX_PARAGRAPHS_EXAMINED:
                    break
                identity = _identity(row)
                if identity is None or identity[2] in seen:
                    continue
                seen.add(identity[2])
                page = session.execute(
                    _PAGE_OF_PARAGRAPH, {"snapshot": identity[0], "document": identity[1], "paragraph": identity[2]}
                ).first()
                paragraphs.append((identity[2], None if page is None else str(page[0]), None if page is None else str(page[1])))
        chosen: dict[str, tuple[NormPageRender, bytes]] = {}
        failed: dict[str, str] = {}
        for _paragraph, binding, blob in paragraphs:
            if binding is None or binding in chosen or binding in failed:
                continue
            if len(chosen) >= limit:
                break
            assert blob is not None
            try:
                render = self._render_of(binding, blob)
                chosen[binding] = (render, self._bytes_of(render))
            except _Unavailable as refused:
                failed[binding] = refused.reason
        images = tuple(
            NormPageImage(render=render, data=data, paragraph_ids=tuple(
                paragraph for paragraph, binding, _ in paragraphs if binding == render.norm_custody_binding_id))
            for render, data in chosen.values())
        unavailable = tuple(
            (paragraph, REASON_PAGE_NOT_IN_CUSTODY if binding is None else failed[binding])
            for paragraph, binding, _ in paragraphs if binding is None or binding in failed)
        return PageImageSelection(images=images, unavailable=unavailable)

    # The render, once

    def render_of(self, binding_id: str, source_blob_id: str) -> NormPageRender:
        """The row for ``(binding, RENDER_PROFILE)``, rendered and kept now if it was not there. Raises ``PageRenderRefused`` for a page that
        cannot be produced and ``StorageError`` while the store is out of reach."""
        try:
            return self._render_of(binding_id, source_blob_id)
        except _Unavailable as refused:
            raise PageRenderRefused(refused.reason) from None

    def _render_of(self, binding: str, source_blob_id: str) -> NormPageRender:
        with session_scope(self._factory) as session:
            found = session.execute(_SELECT_RENDER, {"binding": binding, "profile": RENDER_PROFILE}).mappings().first()
        if found is not None:
            return _render_row(found)
        try:
            pdf = self._read_source(source_blob_id)
            rendered = self._renderer(pdf)
            blob_id = self._publish(rendered.png)
        except PageRenderRefused as refused:
            raise _Unavailable(refused.reason) from None
        except StorageError:
            raise _Unavailable(_REASON_STORAGE) from None
        digest = hashlib.sha256(rendered.png).hexdigest()
        with session_scope(self._factory) as session:
            self._blobs.mark_available(session, parse_blob_id(blob_id))
            session.execute(_INSERT_RENDER, {
                "binding": binding, "profile": RENDER_PROFILE, "blob": blob_id, "sha256": digest, "size": len(rendered.png),
                "width": rendered.width_px, "height": rendered.height_px})
            # The row is immutable and one per (binding, profile): a concurrent renderer that was first keeps its row, and this call returns it.
            row = session.execute(_SELECT_RENDER, {"binding": binding, "profile": RENDER_PROFILE}).mappings().one()
            return _render_row(row)

    def _read_source(self, blob_id: str) -> bytes:
        identity = parse_blob_id(blob_id)
        if self._store.inspect(identity).size > MAX_SOURCE_PDF_BYTES:
            raise PageRenderRefused("source_too_large")
        return self._store.read(identity, verify=True)

    def _publish(self, png: bytes) -> str:
        """The PNG as a Blob, with the journal every publisher keeps: declared before the first external write, verified, ``verifying`` before
        it is made canonical; ``available`` is marked in the transaction that records the row."""
        def before_stage(declaration: BlobDeclaration) -> str:
            with session_scope(self._factory) as session:
                self._blobs.record_declared(session, declaration)
            return secrets.token_hex(16)

        def before_publish(verified: VerifiedBlob) -> None:
            with session_scope(self._factory) as session:
                self._blobs.record_verified(session, verified)

        store = DurablePublicationStore(self._store, before_stage=before_stage, before_publish=before_publish)
        published = store.put_blob(
            png, declared_sha256=hashlib.sha256(png).hexdigest(), declared_size=len(png),
            role=parse_blob_role(BLOB_ROLE), media_type=_PNG_MEDIA_TYPE)
        return str(published.blob_id)

    def _bytes_of(self, render: NormPageRender) -> bytes:
        """The PNG of a row, checked against the row's own digest and size: a Blob that no longer matches is reported, never delivered."""
        data = self._cache.get(render.blob_id)
        if data is None:
            try:
                data = self._store.read(parse_blob_id(render.blob_id), verify=True)
            except StorageError:
                raise _Unavailable(_REASON_STORAGE) from None
            if (len(data) != render.size_bytes or hashlib.sha256(data).hexdigest() != render.sha256
                    or not data.startswith(_PNG_SIGNATURE)):
                raise _Unavailable(_REASON_RENDER_UNREADABLE)
            if len(self._cache) >= _CACHE_PAGES:
                self._cache.clear()
            self._cache[render.blob_id] = data
        return data
