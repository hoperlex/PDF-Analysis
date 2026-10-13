"""``source_preparation``: the page inventory, the text layer and the recognised text.

This stage establishes the document-global character sequence that every later offset
in the system indexes. ``P02_SEAMS`` section 4.1 governs it; sections 4.2, 4.3 and 4.8
give the three artifact shapes.

The concatenation is the contract. Page ``i``'s text starts where page ``i-1``'s text
ended, with **no separator between pages**, and ``total_char_count`` is the length of
the whole sequence in code points. :func:`_build_text_layer` computes the running
offset with ``len()`` on ``str`` values and never touches bytes, and
``tests/integration/analysis_engine`` asserts the resulting count is strictly smaller
than the UTF-8 byte length of the same text - a byte-offset implementation cannot pass
that assertion on a Russian corpus.

The source PDF is read from a temporary file
--------------------------------------------
`W55B-RECOGNISED-01` (plan section B3.3). The blob is streamed to a temporary file, with
its digest checked as it streams (:meth:`BlobStore.open_stream`, the whole read: the last
chunk is withheld unless the SHA-256 is the recorded one, which is what ``read(verify=True)``
checked), and the extractor opens the file by its path. The file is removed when the stage
leaves, whether it succeeded or not. A document of five hundred pages is therefore never
held whole in this process's memory as bytes.

A text layer, or a portal block -- "OCR is always marked"
---------------------------------------------------------
Section 4.2 (``R-116``). A page with no extractable embedded text is refused with
``validation_failed`` **unless** the version is a portal bundle whose block list holds at
least one block (of any type) on that page. Such a page is admitted with
``has_text_layer: false`` and ``char_count: 0``, and its text-layer entry is empty
(``char_start == char_end``): its text exists only in ``prepared.recognised_text``,
marked ``recognised``. A version without a bundle keeps the rule as it was.

The recognised text never reaches the text layer
------------------------------------------------
For a portal bundle (both ``source.markdown`` and ``source.structured_companion``
supplied) the stage also publishes ``prepared.recognised_text`` (section 4.8,
:mod:`auditmanager.analysis.recognised`). It is a separate artifact: nothing in it is
merged into ``prepared.text_layer``, it carries no offsets, and no analysis stage reads it
(``R-117``). A version without a bundle publishes no such artifact and the stage still
succeeds. One of the two members without the other is refused: a bundle always carries
both, and a stage that guessed which half to trust would be a silent fallback.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Final

from auditmanager.analysis.engine.result import ArtifactRef, MetricValue
from auditmanager.analysis.ports.artifacts import (
    ROLE_PAGE_INVENTORY,
    ROLE_RECOGNISED_TEXT,
    ROLE_SOURCE_DOCUMENT,
    ROLE_SOURCE_MARKDOWN,
    ROLE_SOURCE_STRUCTURED_COMPANION,
    ROLE_TEXT_LAYER,
    envelope,
    publish_artifact,
)
from auditmanager.analysis.ports.stage import StageContext, StageProduction
from auditmanager.analysis.recognised import (
    PortalRecognition,
    build_recognised_text,
    read_portal,
)
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
from auditmanager.storage.public import BlobId, BlobStore

STAGE_ID = "source_preparation"

#: The ``reason`` for a portal bundle whose two stored members are not both supplied.
REASON_PORTAL_INCOMPLETE: Final[str] = "portal_inputs_incomplete"
#: The ``reason`` for a markdown or block list the store could not hand back.
REASON_PORTAL_UNREADABLE: Final[str] = "portal_input_unreadable"


def run(context: StageContext) -> StageProduction:
    """Extract the source document and publish the prepared artifacts."""
    source_blob = context.blob(ROLE_SOURCE_DOCUMENT)

    with _source_file(context.blob_store, source_blob) as (path, source_sha256):
        document = extract_document(path)

    portal_members = _portal_members(context)
    portal = (
        None
        if portal_members is None
        else read_portal(
            portal_members[0],
            portal_members[1],
            page_count=document.page_count,
            stage_id=STAGE_ID,
        )
    )
    _refuse_pages_without_text(
        document, frozenset() if portal is None else portal.pages_with_block
    )

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
    artifacts: tuple[ArtifactRef, ...] = (inventory_ref, text_layer_ref)

    metrics: dict[str, MetricValue] = {
        "page_count": document.page_count,
        "total_char_count": text_layer["total_char_count"],
        "normalization_id": NORMALIZATION_ID,
        "extractor_name": EXTRACTOR_NAME,
        "extractor_version": extractor_version(),
    }
    if portal is not None and portal_members is not None:
        recognised = build_recognised_text(
            portal, version_uid=context.version_uid, markdown=portal_members[0]
        )
        recognised_ref, _ = publish_artifact(
            context.blob_store, ROLE_RECOGNISED_TEXT, recognised
        )
        artifacts = (*artifacts, recognised_ref)
        metrics.update(_recognised_metrics(document, recognised))

    return StageProduction(artifacts=artifacts, metrics=metrics)


@contextmanager
def _source_file(store: BlobStore, blob_id: BlobId) -> Iterator[tuple[str, str]]:
    """The source PDF in a temporary file, as ``(path, sha256)``; removed on the way out.

    The digest the stream is held to is the one the store recorded when the bytes were
    published -- the same comparison ``read(verify=True)`` made -- and the size is the
    recorded size. Anything the store refuses, and any mismatch, is the typed refusal the
    whole read used to raise.
    """
    descriptor, name = tempfile.mkstemp(prefix="am-source-", suffix=".pdf")
    try:
        try:
            recorded = store.inspect(blob_id)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = -1
                for chunk in store.open_stream(
                    blob_id,
                    expected_sha256=recorded.sha256,
                    expected_size=recorded.size,
                ):
                    handle.write(chunk)
        except DomainError:
            raise
        except Exception as exc:  # noqa: BLE001 - re-raised as a typed refusal
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message="the declared source document could not be read from storage",
                stage_id=STAGE_ID,
                reason="source_unreadable",
            ) from exc
        yield name, recorded.sha256
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        Path(name).unlink(missing_ok=True)


def _portal_members(context: StageContext) -> tuple[bytes, bytes] | None:
    """``(markdown, block list)`` of a portal bundle, or ``None`` for a version without one."""
    markdown_blob = context.inputs.get(ROLE_SOURCE_MARKDOWN)
    blocks_blob = context.inputs.get(ROLE_SOURCE_STRUCTURED_COMPANION)
    if markdown_blob is None and blocks_blob is None:
        return None
    if markdown_blob is None or blocks_blob is None:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message=(
                "a portal bundle's recognised-text markdown and block list are supplied "
                "together or not at all; one without the other is refused"
            ),
            stage_id=STAGE_ID,
            reason=REASON_PORTAL_INCOMPLETE,
        )
    return _read_member(context.blob_store, markdown_blob), _read_member(
        context.blob_store, blocks_blob
    )


def _read_member(store: BlobStore, blob_id: BlobId) -> bytes:
    """A small stored member (ingest bounds both at 16 MiB), read whole and verified."""
    try:
        return store.read(blob_id, verify=True)
    except DomainError:
        raise
    except Exception as exc:  # noqa: BLE001 - re-raised as a typed refusal
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="a stored member of the portal bundle could not be read from storage",
            stage_id=STAGE_ID,
            reason=REASON_PORTAL_UNREADABLE,
        ) from exc


def _refuse_pages_without_text(
    document: ExtractedDocument, pages_with_block: frozenset[int]
) -> None:
    """Section 4.2: a page needs embedded text, or a portal block (``R-116``)."""
    for page in document.pages:
        if page.char_count == 0 and page.page_number not in pages_with_block:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=(
                    "a page of the source document carries no extractable embedded "
                    "text and no portal block; the document is refused rather than "
                    "published with a page a consumer would have to degrade around"
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


def _recognised_metrics(
    document: ExtractedDocument, recognised: dict[str, Any]
) -> dict[str, MetricValue]:
    """The counts a bundle adds to the stage metrics; the existing names are unchanged."""
    entries = recognised["entries"]
    return {
        "recognised_entry_count": len(entries),
        "recognised_flagged_entry_count": sum(1 for entry in entries if entry.get("flags")),
        "pages_without_text_layer": sum(1 for page in document.pages if page.char_count == 0),
    }


def _build_page_inventory(
    document: ExtractedDocument,
    *,
    version_uid: str,
    source_blob_id: str,
    source_sha256: str,
) -> dict[str, Any]:
    """Section 4.2. ``page_number`` is 1-based and contiguous, and is the only
    page addressing in this system. ``has_text_layer`` is ``false`` only on a page
    :func:`_refuse_pages_without_text` admitted for its portal block."""
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
                "has_text_layer": page.char_count > 0,
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
