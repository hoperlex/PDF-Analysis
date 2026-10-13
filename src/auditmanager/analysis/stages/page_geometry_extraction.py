"""``page_geometry_extraction``: the block index and the page-crop manifest.

Sections 4.4 and 4.5 of ``P02_SEAMS``.

The block index re-derives geometry from the source document, then binds itself to the
exact text layer it aligned against via ``text_layer_sha256``. A consumer holding a
different text layer fails closed rather than resolving spans against text that is not
the text those spans were computed from.

Block spans are document-global offsets per section 4.1: a block's ``char_start`` is
its owning page's ``char_start`` plus the block's offset within the page text, counted
in code points. The line separator ``"\\n"`` sits *between* blocks and belongs to none
of them, which is why the running offset advances by ``len(line.text) + 1`` while the
block's own span covers only ``len(line.text)``.

``bbox_origin`` is ``top_left`` with y increasing downwards, after rotation.
pdfplumber's ``top``/``bottom`` are already in that space, so nothing is flipped here;
stating it once in the artifact is cheaper than four consumers each guessing PDF's
bottom-left default.

The source PDF is read from a temporary file
--------------------------------------------
Plan section B3.3: the blob is streamed to a temporary file with its digest checked as it
streams, the extractor and the page renderer open the file by its path, and the file is
removed when the stage leaves, whether it succeeded or not
(:func:`auditmanager.analysis.geometry.source_file`).

The page-crop manifest and ``OD-04`` (flipped by `W55B-SEAL-01`, ``R-119``)
------------------------------------------------------------------------
The registry marks ``geometry.page_crops`` a required output of a stage that allows
neither ``partial`` nor ``skipped``; it is a manifest with a content schema
(``contracts/analysis/v1/crop-manifest.schema.json``) under one of two policies, echoed in
the metrics as ``crop_policy`` and ``crop_count``:

* ``none`` -- a version without a portal bundle (no ``source.structured_companion``
  supplied): ``crops: []`` and nothing else, exactly as before.
* ``portal_image_blocks`` -- a portal bundle (`W55B-GEOMETRY-01`, ``P02_SEAMS`` sections
  4.5, 4.9 and 4.10). The block list is normalised into ``geometry.portal_blocks``; each
  page's box is checked against the PDF (:mod:`auditmanager.analysis.geometry.maths`); every
  IMAGE block on a page that passed gets a crop, a clip render of the PDF page published as
  a content-addressed PNG blob of role ``geometry.crop_image``; the manifest lists them. A
  page that failed the check is ``geometry: geometry_mismatch`` in the artifact and cuts no
  crop, and the stage still succeeds: the mismatch is visible in the artifact, in the
  metrics and in «Блоки», never a silent fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from auditmanager.analysis.engine.result import ArtifactRef, MetricValue
from auditmanager.analysis.geometry import (
    GEOMETRY_MISMATCH,
    IMAGE,
    CropPublisher,
    DegenerateCrop,
    PdfiumDocument,
    base_scale,
    check_page,
    crop_record,
    encode_png,
    image_blocks_to_crop,
    plan_crop,
    portal_blocks_body,
    read_layout,
    renderer_name,
    source_file,
)
from auditmanager.analysis.ports.artifacts import (
    ROLE_BLOCK_INDEX,
    ROLE_PAGE_CROPS,
    ROLE_PAGE_INVENTORY,
    ROLE_PORTAL_BLOCKS,
    ROLE_SOURCE_DOCUMENT,
    ROLE_SOURCE_STRUCTURED_COMPANION,
    ROLE_TEXT_LAYER,
    envelope,
    publish_artifact,
    read_artifact,
)
from auditmanager.analysis.ports.stage import StageContext, StageProduction
from auditmanager.analysis.stages.extraction import ExtractedDocument, extract_document
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobStore

STAGE_ID = "page_geometry_extraction"

#: ``OD-04``: a version without a portal bundle. Declared in the artifact and echoed in the
#: stage metrics.
CROP_POLICY: Final[str] = "none"
#: ``OD-04`` flipped (``R-119``): a portal bundle, one crop per IMAGE block on a page that
#: passed the page-box check.
CROP_POLICY_PORTAL: Final[str] = "portal_image_blocks"

#: The ``reason`` for a block list the store could not hand back.
REASON_PORTAL_UNREADABLE: Final[str] = "portal_input_unreadable"
#: The ``reason`` for an IMAGE block too small to be cut (``maths.DegenerateCrop``).
REASON_BLOCK_DEGENERATE: Final[str] = "portal_block_degenerate"

BBOX_UNIT: Final[str] = "pt"
BBOX_ORIGIN: Final[str] = "top_left"


def run(context: StageContext) -> StageProduction:
    """Derive the block index and publish it with the crop manifest, and for a portal
    bundle the normalised block list and the crops."""
    text_layer, text_layer_sha256 = read_artifact(
        context.blob_store,
        context.blob(ROLE_TEXT_LAYER),
        expected_role=ROLE_TEXT_LAYER,
    )
    inventory, _ = read_artifact(
        context.blob_store,
        context.blob(ROLE_PAGE_INVENTORY),
        expected_role=ROLE_PAGE_INVENTORY,
    )

    source_blob = context.inputs.get(ROLE_SOURCE_DOCUMENT)
    if source_blob is None:
        # The registry does not declare source.document a required input of this
        # stage, so the inventory's own reference is the canonical way back to the
        # bytes the geometry must be re-derived from.
        source_blob = _source_blob_from(inventory)

    companion = _companion(context)

    with source_file(context.blob_store, source_blob, stage_id=STAGE_ID) as path:
        document = extract_document(path)
        _refuse_text_layer_mismatch(document, text_layer)
        blocks = _build_blocks(document, text_layer)
        portal = (
            None
            if companion is None
            else _portal_geometry(
                context.blob_store,
                path,
                companion,
                page_count=document.page_count,
                version_uid=context.version_uid,
            )
        )

    block_index = envelope(
        ROLE_BLOCK_INDEX,
        context.version_uid,
        text_layer_sha256=text_layer_sha256,
        blocks=blocks,
    )
    crops = envelope(
        ROLE_PAGE_CROPS,
        context.version_uid,
        crop_policy=CROP_POLICY if portal is None else CROP_POLICY_PORTAL,
        crops=[] if portal is None else portal.crops,
    )

    block_ref, _ = publish_artifact(context.blob_store, ROLE_BLOCK_INDEX, block_index)
    crops_ref, _ = publish_artifact(context.blob_store, ROLE_PAGE_CROPS, crops)

    metrics: dict[str, MetricValue] = {
        "block_count": len(blocks),
        "page_count": len(document.pages),
        "crop_policy": CROP_POLICY,
        "crop_count": 0,
    }
    if portal is None:
        return StageProduction(artifacts=(block_ref, crops_ref), metrics=metrics)

    portal_ref, _ = publish_artifact(context.blob_store, ROLE_PORTAL_BLOCKS, portal.document)
    metrics.update(portal.metrics)
    return StageProduction(
        artifacts=(block_ref, crops_ref, portal_ref, *portal.crop_images),
        metrics=metrics,
    )


@dataclass(frozen=True, slots=True)
class _PortalGeometry:
    """What a portal bundle adds: the normalised list, the crops and their blobs."""

    document: dict[str, Any]
    crops: list[dict[str, Any]]
    crop_images: tuple[ArtifactRef, ...]
    metrics: dict[str, MetricValue]


def _companion(context: StageContext) -> bytes | None:
    """The stored ``_blocks.json`` of a portal bundle, or ``None`` for a version without one.

    Only the block list is read: the markdown is ``source_preparation``'s. A member the store
    cannot hand back is refused, never treated as absent.
    """
    blob_id = context.inputs.get(ROLE_SOURCE_STRUCTURED_COMPANION)
    if blob_id is None:
        return None
    try:
        return context.blob_store.read(blob_id, verify=True)
    except DomainError:
        raise
    except Exception as exc:  # noqa: BLE001 - re-raised as a typed refusal
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the portal bundle's block list could not be read from storage",
            stage_id=STAGE_ID,
            reason=REASON_PORTAL_UNREADABLE,
        ) from exc


def _portal_geometry(
    store: BlobStore, path: str, companion: bytes, *, page_count: int, version_uid: str
) -> _PortalGeometry:
    """Normalise the block list, check every page's box, and cut the IMAGE blocks' crops.

    PDFium reads the same temporary file the extractor read. Each crop is published as soon
    as it is encoded, so one crop at a time is held in memory; equal crops share one blob.
    """
    layout = read_layout(companion, page_count=page_count, stage_id=STAGE_ID)
    renderer = renderer_name()
    publisher = CropPublisher(store)
    records: list[dict[str, Any]] = []
    with PdfiumDocument(path, stage_id=STAGE_ID) as pdf:
        if pdf.page_count != page_count:
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message=(
                    "the page renderer and the extractor disagree on the page count; the "
                    "stage refuses rather than choosing one"
                ),
                stage_id=STAGE_ID,
                reason="page_count_disagreement",
            )
        pages = {page.page_number: pdf.page_geometry(page.page_number) for page in layout.pages}
        verdicts = {
            page.page_number: check_page(
                portal_width_px=page.width_px,
                portal_height_px=page.height_px,
                portal_rotation=page.rotation_deg,
                page_width_pt=pages[page.page_number].width_pt,
                page_height_pt=pages[page.page_number].height_pt,
                page_rotation=pages[page.page_number].rotation_deg,
            )
            for page in layout.pages
        }
        for block in image_blocks_to_crop(layout, verdicts):
            page = pages[block.page_number]
            try:
                plan = plan_crop(
                    block.bbox_norm,
                    page.width_pt,
                    page.height_pt,
                    base_scale(layout.page(block.page_number).width_px, page.width_pt),
                )
            except DegenerateCrop as exc:
                raise DomainError(
                    ErrorCode.ANALYSIS_INPUT_INVALID,
                    message=(
                        "an IMAGE block of the portal block list is too small to be cut as a "
                        "crop; the stage refuses rather than leaving the block without one"
                    ),
                    stage_id=STAGE_ID,
                    reason=REASON_BLOCK_DEGENERATE,
                ) from exc
            image = pdf.render(block.page_number, plan)
            reference = publisher.publish(encode_png(image))
            records.append(crop_record(block, plan, reference, renderer))

    mismatched = {number for number, verdict in verdicts.items() if verdict == GEOMETRY_MISMATCH}
    images = [block for block in layout.blocks if block.block_type == IMAGE]
    document = envelope(ROLE_PORTAL_BLOCKS, version_uid, **portal_blocks_body(layout, verdicts))
    return _PortalGeometry(
        document=document,
        crops=records,
        crop_images=publisher.references,
        metrics={
            "crop_policy": CROP_POLICY_PORTAL,
            "crop_count": len(records),
            "crop_blob_count": len(publisher.references),
            "crop_skipped_for_mismatch_count": sum(
                1 for block in images if block.page_number in mismatched
            ),
            "portal_block_count": len(layout.blocks),
            "portal_image_block_count": len(images),
            "geometry_mismatch_page_count": len(mismatched),
        },
    )


def _source_blob_from(inventory: dict[str, Any]) -> Any:
    from auditmanager.storage.public import parse_blob_id

    reference = inventory.get("source_blob_id")
    if not isinstance(reference, str):
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the page inventory carries no source document reference",
            stage_id=STAGE_ID,
            reason="missing_source_reference",
        )
    try:
        return parse_blob_id(reference)
    except Exception as exc:  # noqa: BLE001 - re-raised as a typed refusal
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the page inventory's source document reference is malformed",
            stage_id=STAGE_ID,
            reason="malformed_source_reference",
        ) from exc


def _refuse_text_layer_mismatch(
    document: ExtractedDocument, text_layer: dict[str, Any]
) -> None:
    """Prove the re-extraction reproduced the published text layer, page by page.

    Without this the block index could be built over text that differs from the text
    its spans claim to index - the exact failure ``text_layer_sha256`` exists to make
    detectable downstream, caught here before anything is published.
    """
    pages = sorted(text_layer.get("pages", ()), key=lambda page: page["page_number"])
    if len(pages) != len(document.pages):
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message=(
                "the published text layer and the source document disagree on the "
                "page count"
            ),
            stage_id=STAGE_ID,
            reason="text_layer_page_count_mismatch",
        )
    for published, extracted in zip(pages, document.pages):
        if published["page_number"] != extracted.page_number:
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message="the published text layer is not contiguous in page order",
                stage_id=STAGE_ID,
                reason="text_layer_page_order_mismatch",
            )
        if published["text"] != extracted.text:
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message=(
                    "the source document does not re-extract to the published text "
                    "layer; block spans would not index it"
                ),
                stage_id=STAGE_ID,
                reason="text_layer_text_mismatch",
            )


def _build_blocks(
    document: ExtractedDocument, text_layer: dict[str, Any]
) -> list[dict[str, Any]]:
    """One block per extracted line, numbered across the whole document.

    ``block_id`` matches ``^b_[0-9]{6}$`` and is assigned deterministically in
    ``(page_number, block_ordinal)`` order starting at ``b_000001``. It is an anchor
    inside this artifact: never a foreign key, never a contract identifier.
    """
    starts = {
        page["page_number"]: page["char_start"] for page in text_layer.get("pages", ())
    }
    ends = {page["page_number"]: page["char_end"] for page in text_layer.get("pages", ())}

    blocks: list[dict[str, Any]] = []
    sequence = 0
    for page in document.pages:
        page_start = starts[page.page_number]
        page_end = ends[page.page_number]
        cursor = page_start
        for ordinal, line in enumerate(page.lines):
            sequence += 1
            char_start = cursor
            char_end = char_start + len(line.text)
            if char_end > page_end:
                raise DomainError(
                    ErrorCode.ANALYSIS_INPUT_INVALID,
                    message=(
                        "a derived block span leaves its owning page's interval; "
                        "the stage refuses rather than publishing an anchor that "
                        "does not resolve"
                    ),
                    stage_id=STAGE_ID,
                    reason="block_span_out_of_page",
                )
            blocks.append(
                {
                    "block_id": f"b_{sequence:06d}",
                    "page_number": page.page_number,
                    "block_ordinal": ordinal,
                    "bbox": {
                        "x0": round(line.x0, 2),
                        "y0": round(line.top, 2),
                        "x1": round(line.x1, 2),
                        "y1": round(line.bottom, 2),
                    },
                    "bbox_unit": BBOX_UNIT,
                    "bbox_origin": BBOX_ORIGIN,
                    "char_start": char_start,
                    "char_end": char_end,
                }
            )
            # The "\n" that joins two lines belongs to neither block.
            cursor = char_end + 1
    return blocks


__all__ = [
    "BBOX_ORIGIN",
    "BBOX_UNIT",
    "CROP_POLICY",
    "CROP_POLICY_PORTAL",
    "REASON_BLOCK_DEGENERATE",
    "REASON_PORTAL_UNREADABLE",
    "STAGE_ID",
    "run",
]
