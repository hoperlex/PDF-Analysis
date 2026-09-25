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

Carries no crops. ``page_geometry_extraction`` also publishes ``ROLE_PAGE_CROPS``, and this
pipeline renders no visual detection so that artifact is unconditionally ``crops: []`` --
it is a separate artifact this view does not restate, rather than a field shipped here
always empty and unexplained.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = [
    "STATUS_NOT_PRODUCED",
    "STATUS_PRODUCED",
    "BlockGeometryView",
    "VersionBlockIndexView",
    "block_geometry_body",
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
