"""``source_preparation``: the page inventory and the text layer.

This stage establishes the document-global character sequence that every later offset
in the system indexes. ``P02_SEAMS`` section 4.1 governs it; section 4.2 and 4.3 give
the two artifact shapes.

The concatenation is the contract. Page ``i``'s text starts where page ``i-1``'s text
ended, with **no separator between pages**, and ``total_char_count`` is the length of
the whole sequence in code points. :func:`_build_text_layer` computes the running
offset with ``len()`` on ``str`` values and never touches bytes, and
``tests/integration/analysis_engine`` asserts the resulting count is strictly smaller
than the UTF-8 byte length of the same text - a byte-offset implementation cannot pass
that assertion on a Russian corpus.

``has_text_layer`` must be ``true`` for every page (section 4.2). A page with no
extractable embedded text is refused with ``validation_failed``; the field exists so
the refusal is provable, not so a consumer can degrade.
"""

from __future__ import annotations

from typing import Any

from auditmanager.analysis.ports.artifacts import (
    ROLE_PAGE_INVENTORY,
    ROLE_SOURCE_DOCUMENT,
    ROLE_TEXT_LAYER,
    envelope,
    publish_artifact,
)
from auditmanager.analysis.ports.stage import StageContext, StageProduction
from auditmanager.analysis.stages.extraction import (
    EXTRACTOR_NAME,
    NORMALIZATION_DESCRIPTION,
    NORMALIZATION_ID,
    ExtractedDocument,
    extract_document,
    extractor_version,
    options_sha256,
)
from auditmanager.shared.errors import DomainError, ErrorCode

STAGE_ID = "source_preparation"


def run(context: StageContext) -> StageProduction:
    """Extract the source document and publish both prepared artifacts."""
    source_blob = context.blob(ROLE_SOURCE_DOCUMENT)

    try:
        payload = context.blob_store.read(source_blob, verify=True)
    except DomainError:
        raise
    except Exception as exc:  # noqa: BLE001 - re-raised as a typed refusal
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the declared source document could not be read from storage",
            stage_id=STAGE_ID,
            reason="source_unreadable",
        ) from exc

    source_sha256 = context.blob_store.inspect(source_blob).sha256
    document = extract_document(payload)
    _refuse_pages_without_text(document)

    inventory = _build_page_inventory(
        document,
        version_uid=context.version_uid,
        source_blob_id=str(source_blob),
        source_sha256=source_sha256,
    )
    text_layer = _build_text_layer(document, version_uid=context.version_uid)

    inventory_ref, _ = publish_artifact(
        context.blob_store, ROLE_PAGE_INVENTORY, inventory
    )
    text_layer_ref, _ = publish_artifact(context.blob_store, ROLE_TEXT_LAYER, text_layer)

    return StageProduction(
        artifacts=(inventory_ref, text_layer_ref),
        metrics={
            "page_count": document.page_count,
            "total_char_count": text_layer["total_char_count"],
            "normalization_id": NORMALIZATION_ID,
            "extractor_name": EXTRACTOR_NAME,
            "extractor_version": extractor_version(),
        },
    )


def _refuse_pages_without_text(document: ExtractedDocument) -> None:
    """Section 4.2: a page without extractable embedded text never reaches an artifact."""
    for page in document.pages:
        if page.char_count == 0:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=(
                    "a page of the source document carries no extractable embedded "
                    "text; the document is refused rather than published with a "
                    "page a consumer would have to degrade around"
                ),
                field="page_number",
                constraint="every page must carry extractable embedded text",
            )
    if document.page_count == 0:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="the source document declares no page",
            field="page_count",
            constraint="a source document has at least one page",
        )


def _build_page_inventory(
    document: ExtractedDocument,
    *,
    version_uid: str,
    source_blob_id: str,
    source_sha256: str,
) -> dict[str, Any]:
    """Section 4.2. ``page_number`` is 1-based and contiguous, and is the only
    page addressing in this system."""
    return envelope(
        ROLE_PAGE_INVENTORY,
        version_uid,
        source_blob_id=source_blob_id,
        source_sha256=source_sha256,
        page_count=document.page_count,
        pages=[
            {
                "page_number": page.page_number,
                "width_pt": page.width_pt,
                "height_pt": page.height_pt,
                "rotation_deg": page.rotation_deg,
                "has_text_layer": True,
                "char_count": page.char_count,
            }
            for page in document.pages
        ],
    )


def _build_text_layer(document: ExtractedDocument, *, version_uid: str) -> dict[str, Any]:
    """Section 4.3. The running offset is the whole point of this function.

    ``cursor`` counts code points. It advances by ``len(page.text)`` and by nothing
    else - in particular not by one for a separator, because there is no separator
    between pages.
    """
    pages: list[dict[str, Any]] = []
    cursor = 0
    for page in document.pages:
        char_start = cursor
        cursor += len(page.text)
        pages.append(
            {
                "page_number": page.page_number,
                "char_start": char_start,
                "char_end": cursor,
                "text": page.text,
            }
        )

    return envelope(
        ROLE_TEXT_LAYER,
        version_uid,
        extractor={
            "name": EXTRACTOR_NAME,
            "version": extractor_version(),
            "options_sha256": options_sha256(),
        },
        normalization={
            "id": NORMALIZATION_ID,
            "description": NORMALIZATION_DESCRIPTION,
        },
        total_char_count=cursor,
        pages=pages,
    )


def document_text(text_layer: dict[str, Any]) -> str:
    """Reassemble the document-global sequence from a published text layer.

    Concatenation in ascending page order with no separator, which is the definition
    every consumer's offsets index. It is here rather than in each consumer so there
    is one implementation of the rule to be right about.
    """
    return "".join(
        page["text"] for page in sorted(text_layer["pages"], key=lambda p: p["page_number"])
    )


__all__ = ["STAGE_ID", "document_text", "run"]
