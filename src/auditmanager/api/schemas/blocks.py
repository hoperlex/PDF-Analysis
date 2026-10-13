"""``VersionBlockIndex`` and ``BlockGeometry``, the ``W45-BLOCKS`` reseal.

The producer is :mod:`auditmanager.analysis.stages.page_geometry_extraction`, which
carries no model and no provider reference (``contracts/analysis/v1/stage-registry.json``
declares ``execution.model_routed: false``), so what it publishes is a deterministic
property of the version rather than of any one run of it -- see
``docs/program/W45-BLOCKS.md``.

**Absent is not empty.** :attr:`VersionBlockIndexView.status` is the field a caller reads
to tell "no run of this version has produced this artifact yet" from "it was produced and
the version genuinely has no blocks" -- both answer ``blocks=()``, and only ``status``
differs between them. See ``P02_SEAMS.md`` and `OPERATING_CONSTRAINTS.md` section 12 on
never letting the length of a collection carry a distinction it cannot carry alone.

Carries no crops. ``page_geometry_extraction`` also publishes ``ROLE_PAGE_CROPS``: ``crops: []``
under ``crop_policy: none`` for a version without a portal bundle, one crop per IMAGE block
under ``portal_image_blocks`` for a bundle (`W55B-GEOMETRY-01`). It is a separate artifact this
view does not restate, rather than a field shipped here that a version could leave empty and
unexplained; the portal crops are served by :class:`PortalBlockView`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

__all__ = [
    "STATUS_NOT_PRODUCED",
    "STATUS_PRODUCED",
    "BlockGeometryView",
    "PortalBlockIndexView",
    "PortalBlockView",
    "PortalCropContent",
    "PortalCropView",
    "PortalRecognisedTextView",
    "VersionBlockIndexView",
    "block_geometry_body",
    "portal_block_body",
    "portal_block_page_body",
    "version_block_index_body",
]

#: The frozen ``VersionBlockIndex.status`` enum, spelled once so the adapter and this
#: module cannot disagree on the two literal strings the wire carries.
STATUS_PRODUCED = "produced"
STATUS_NOT_PRODUCED = "not_produced"


@dataclass(frozen=True, slots=True)
class BlockGeometryView:
    """Exactly the frozen ``BlockGeometry``. ``bbox`` is the four points, verbatim."""

    block_id: str
    page_number: int
    block_ordinal: int
    bbox: Mapping[str, float]
    bbox_unit: str
    bbox_origin: str
    char_start: int
    char_end: int


@dataclass(frozen=True, slots=True)
class VersionBlockIndexView:
    """Exactly the frozen ``VersionBlockIndex``.

    ``produced_by_run_id`` and ``text_layer_sha256`` are ``None`` exactly when ``status``
    is :data:`STATUS_NOT_PRODUCED` -- never independently.
    """

    version_uid: str
    status: str
    produced_by_run_id: str | None
    text_layer_sha256: str | None
    block_count: int
    blocks: tuple[BlockGeometryView, ...] = ()


def block_geometry_body(view: BlockGeometryView) -> dict[str, Any]:
    return {
        "block_id": view.block_id,
        "page_number": view.page_number,
        "block_ordinal": view.block_ordinal,
        "bbox": dict(view.bbox),
        "bbox_unit": view.bbox_unit,
        "bbox_origin": view.bbox_origin,
        "char_start": view.char_start,
        "char_end": view.char_end,
    }


def version_block_index_body(view: VersionBlockIndexView) -> dict[str, Any]:
    return {
        "version_uid": view.version_uid,
        "status": view.status,
        "produced_by_run_id": view.produced_by_run_id,
        "text_layer_sha256": view.text_layer_sha256,
        "block_count": view.block_count,
        "blocks": [block_geometry_body(b) for b in view.blocks],
    }


# ---------------------------------------------------------------------------------------
# portal blocks (`W55B-SEAL-01`, `W55-PLAN.md` sections B3.6 and B3.7)
# ---------------------------------------------------------------------------------------
#
# A bundle's block list, normalised by ``page_geometry_extraction`` into
# ``geometry.portal_blocks``, with the recognised text and the portal's descriptions joined
# on by ``portal_block_id``. Keyed by the version for the reason ``getVersionBlocks`` is: it
# is a property of the version's bundle, identical across every run that reaches the stage.
# The ``not_produced`` / ``produced`` distinction is the same one, for the same reason.


@dataclass(frozen=True, slots=True)
class PortalCropView:
    """A crop this product cut itself. Never the portal's ``crop_url``."""

    media_type: str
    width_px: int
    height_px: int
    sha256: str


@dataclass(frozen=True, slots=True)
class PortalRecognisedTextView:
    """The portal's OCR text of a TEXT block, marked ``recognised`` on the wire."""

    text: str
    flags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PortalBlockView:
    """Exactly the frozen ``PortalBlock``."""

    portal_block_id: str
    page_number: int
    page_label: int
    ordinal: int | None
    block_type: str
    status: str
    bbox_norm: tuple[float, float, float, float]
    geometry: str
    polygon_points: tuple[tuple[float, float], ...] | None = None
    crop: PortalCropView | None = None
    recognised_text: PortalRecognisedTextView | None = None
    portal_description: str | None = None


@dataclass(frozen=True, slots=True)
class PortalBlockIndexView:
    """A version's portal blocks, **already in order**: page, ordinal (null last), id.

    ``produced_by_run_id`` is ``None`` exactly when ``status`` is
    :data:`STATUS_NOT_PRODUCED` -- never independently. The router pages ``blocks`` and never
    re-sorts them, for the reason ``list_documents`` gives.
    """

    version_uid: str
    status: str
    produced_by_run_id: str | None
    blocks: tuple[PortalBlockView, ...] = ()


@dataclass(frozen=True, slots=True)
class PortalCropContent:
    """One crop's PNG bytes, as ``streamVersionPortalBlockCrop`` answers them."""

    media_type: str
    sha256: str
    content: bytes


def portal_block_body(view: PortalBlockView) -> dict[str, Any]:
    """The block's wire shape. An absent optional member is left out, never ``null``."""
    body: dict[str, Any] = {
        "portal_block_id": view.portal_block_id,
        "page_number": view.page_number,
        "page_label": view.page_label,
        "ordinal": view.ordinal,
        "block_type": view.block_type,
        "status": view.status,
        "bbox_norm": list(view.bbox_norm),
    }
    if view.polygon_points is not None:
        body["polygon_points"] = [list(point) for point in view.polygon_points]
    body["geometry"] = view.geometry
    if view.crop is not None:
        body["crop"] = {
            "media_type": view.crop.media_type,
            "width_px": view.crop.width_px,
            "height_px": view.crop.height_px,
            "sha256": view.crop.sha256,
        }
    if view.recognised_text is not None:
        body["recognised_text"] = {
            "quote_source": "recognised",
            "text": view.recognised_text.text,
            "flags": list(view.recognised_text.flags),
        }
    if view.portal_description is not None:
        body["portal_description"] = view.portal_description
    return body


def portal_block_page_body(
    index: PortalBlockIndexView,
    items: Sequence[PortalBlockView],
    next_cursor: str | None,
) -> dict[str, Any]:
    return {
        "version_uid": index.version_uid,
        "status": index.status,
        "produced_by_run_id": index.produced_by_run_id,
        "block_count": len(index.blocks),
        "items": [portal_block_body(view) for view in items],
        "page": {"next_cursor": next_cursor},
    }
