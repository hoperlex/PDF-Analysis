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

The page-crop manifest and ``OD-04``
------------------------------------
The registry marks ``geometry.page_crops`` a required output of a stage that allows
neither ``partial`` nor ``skipped``, and ``PC-01`` does no visual detection. So the
role is present, schema-valid and explicitly empty under a declared
``crop_policy: none``, echoed in the metrics as ``crop_policy=none`` and
``crop_count=0``. Its only contract consumer, ``block_analysis``, is out of ``PC-01``
scope and would fail closed on an empty list rather than degrade.

**Flip condition, carried from OD-04:** if any task adds a content schema for the crop
manifest, this decision reopens.
"""

from __future__ import annotations

from typing import Any, Final

from auditmanager.analysis.ports.artifacts import (
    ROLE_BLOCK_INDEX,
    ROLE_PAGE_CROPS,
    ROLE_PAGE_INVENTORY,
    ROLE_SOURCE_DOCUMENT,
    ROLE_TEXT_LAYER,
    envelope,
    publish_artifact,
    read_artifact,
)
from auditmanager.analysis.ports.stage import StageContext, StageProduction
from auditmanager.analysis.stages.extraction import ExtractedDocument, extract_document
from auditmanager.shared.errors import DomainError, ErrorCode

STAGE_ID = "page_geometry_extraction"

#: ``OD-04``. Declared in the artifact and echoed in the stage metrics.
CROP_POLICY: Final[str] = "none"

BBOX_UNIT: Final[str] = "pt"
BBOX_ORIGIN: Final[str] = "top_left"


def run(context: StageContext) -> StageProduction:
    """Derive the block index and publish it with the declared empty crop manifest."""
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

    try:
        payload = context.blob_store.read(source_blob, verify=True)
    except DomainError:
        raise
    except Exception as exc:  # noqa: BLE001 - re-raised as a typed refusal
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the source document referenced by the page inventory is unreadable",
            stage_id=STAGE_ID,
            reason="source_unreadable",
        ) from exc

    document = extract_document(payload)
    _refuse_text_layer_mismatch(document, text_layer)

    blocks = _build_blocks(document, text_layer)
    block_index = envelope(
        ROLE_BLOCK_INDEX,
        context.version_uid,
        text_layer_sha256=text_layer_sha256,
        blocks=blocks,
    )
    crops = envelope(
        ROLE_PAGE_CROPS,
        context.version_uid,
        crop_policy=CROP_POLICY,
        crops=[],
    )

    block_ref, _ = publish_artifact(context.blob_store, ROLE_BLOCK_INDEX, block_index)
    crops_ref, _ = publish_artifact(context.blob_store, ROLE_PAGE_CROPS, crops)

    return StageProduction(
        artifacts=(block_ref, crops_ref),
        metrics={
            "block_count": len(blocks),
            "page_count": len(document.pages),
            "crop_policy": CROP_POLICY,
            "crop_count": 0,
        },
    )


def _source_blob_from(inventory: dict[str, Any]) -> Any:
    from auditmanager.storage.models import parse_blob_id

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


__all__ = ["BBOX_ORIGIN", "BBOX_UNIT", "CROP_POLICY", "STAGE_ID", "run"]
