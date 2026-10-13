"""The two stored members of a portal bundle ``source_preparation`` reads, judged together.

`W55B-RECOGNISED-01`. Ingest admitted the bundle only after holding ``_results.md`` and
``_blocks.json`` equal **both ways** (every TEXT and IMAGE block of the list has exactly
one header of its own type, and no header names anything else). The stage reads the stored
bytes again, so it checks again, cheaply: bytes that disagree now are a defect of storage or
of a version published some other way, and they are refused with a typed
``analysis_input_invalid`` and a ``reason`` -- never skipped, never repaired, never read
around.

Only the facts this stage needs are read from the block list: each block's identifier, its
type and its page. The rest of the list (boxes, polygons, statuses, the portal's labels) is
``page_geometry_extraction``'s to normalise.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Final

from auditmanager.analysis.recognised.markdown import MarkdownBlock, read_blocks
from auditmanager.shared.errors import DomainError, ErrorCode

#: The portal's block identifier, an external identifier (``identifiers.json``).
PORTAL_BLOCK_ID: Final[re.Pattern[str]] = re.compile(r"blk_[0-9a-f]{32}")
#: The block types of the list; the markdown holds the first two.
TEXT: Final[str] = "text"
IMAGE: Final[str] = "image"
STAMP: Final[str] = "stamp"
BLOCK_TYPES: Final[frozenset[str]] = frozenset({TEXT, IMAGE, STAMP})

#: The ``reason`` values this module refuses with (detail of ``analysis_input_invalid``).
REASON_BLOCKS_INVALID: Final[str] = "portal_blocks_invalid"
REASON_BLOCKS_PAGES: Final[str] = "portal_blocks_page_mismatch"
REASON_MARKDOWN_INVALID: Final[str] = "recognised_markdown_invalid"
REASON_MARKDOWN_MISMATCH: Final[str] = "recognised_markdown_mismatch"


@dataclass(frozen=True, slots=True)
class PortalBlock:
    """One block of the list: what this stage reads of it."""

    portal_block_id: str
    block_type: str
    #: ``page_index + 1``: the true 1-based PDF page (``P02_SEAMS`` section 4.9).
    page_number: int


@dataclass(frozen=True, slots=True)
class PortalRecognition:
    """The block list and the markdown, agreed. Built only by :func:`read_portal`."""

    blocks: tuple[PortalBlock, ...]
    #: The TEXT and IMAGE blocks of the markdown, in the order of the file.
    bodies: tuple[MarkdownBlock, ...]

    @property
    def pages_with_block(self) -> frozenset[int]:
        """The 1-based pages that hold at least one block of any type."""
        return frozenset(block.page_number for block in self.blocks)

    def block(self, portal_block_id: str) -> PortalBlock:
        for block in self.blocks:
            if block.portal_block_id == portal_block_id:
                return block
        raise KeyError(portal_block_id)


def _refuse(reason: str, message: str, stage_id: str | None) -> DomainError:
    details: dict[str, Any] = {"reason": reason}
    if stage_id is not None:
        details["stage_id"] = stage_id
    return DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, message=message, **details)


def _is_index(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def read_block_list(
    raw: bytes, *, page_count: int, stage_id: str | None = None
) -> tuple[PortalBlock, ...]:
    """The blocks of a stored ``_blocks.json``, each on a page of the PDF.

    Refuses ``portal_blocks_invalid`` for bytes that are not the list's shape (strict UTF-8
    JSON, a ``pages`` list and a ``blocks`` list of objects with a ``blk_`` identifier, a type
    of the three and an integer page index, identifiers unique) and
    ``portal_blocks_page_mismatch`` for a list that describes another number of pages than
    the PDF has, or puts a block on a page the PDF does not have.
    """
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise _refuse(
            REASON_BLOCKS_INVALID, "the stored portal block list is not JSON", stage_id
        ) from None
    if (
        not isinstance(document, dict)
        or not isinstance(document.get("pages"), list)
        or not isinstance(document.get("blocks"), list)
    ):
        raise _refuse(
            REASON_BLOCKS_INVALID,
            "the stored portal block list carries no pages and blocks lists",
            stage_id,
        )
    if len(document["pages"]) != page_count:
        raise _refuse(
            REASON_BLOCKS_PAGES,
            "the stored portal block list describes another number of pages than the "
            "source document has",
            stage_id,
        )

    blocks: list[PortalBlock] = []
    seen: set[str] = set()
    for item in document["blocks"]:
        if not isinstance(item, dict):
            raise _refuse(REASON_BLOCKS_INVALID, "a portal block is not an object", stage_id)
        identifier = item.get("block_id")
        block_type = item.get("block_type")
        page_index = item.get("page_index")
        if (
            not isinstance(identifier, str)
            or PORTAL_BLOCK_ID.fullmatch(identifier) is None
            or not isinstance(block_type, str)
            or block_type not in BLOCK_TYPES
            or not _is_index(page_index)
        ):
            raise _refuse(
                REASON_BLOCKS_INVALID,
                "a portal block lacks a well-formed identifier, type or page index",
                stage_id,
            )
        if identifier in seen:
            raise _refuse(
                REASON_BLOCKS_INVALID, "a portal block identifier is repeated", stage_id
            )
        if page_index >= page_count:
            raise _refuse(
                REASON_BLOCKS_PAGES,
                "a portal block names a page the source document does not have",
                stage_id,
            )
        seen.add(identifier)
        blocks.append(PortalBlock(identifier, block_type, page_index + 1))
    return tuple(blocks)


def read_portal(
    markdown: bytes, block_list: bytes, *, page_count: int, stage_id: str | None = None
) -> PortalRecognition:
    """The stored markdown and block list, read and held equal both ways."""
    blocks = read_block_list(block_list, page_count=page_count, stage_id=stage_id)
    try:
        text = markdown.decode("utf-8")
    except UnicodeDecodeError:
        raise _refuse(
            REASON_MARKDOWN_INVALID,
            "the stored recognised-text markdown is not UTF-8",
            stage_id,
        ) from None

    bodies = read_blocks(text)
    expected = {
        block.portal_block_id: block.block_type
        for block in blocks
        if block.block_type in (TEXT, IMAGE)
    }
    labels: dict[str, list[str]] = {}
    for body in bodies:
        labels.setdefault(body.portal_block_id, []).append(body.label)
    for identifier, block_type in expected.items():
        if labels.get(identifier) != [block_type]:
            raise _refuse(
                REASON_MARKDOWN_MISMATCH,
                "a TEXT or IMAGE block of the stored block list has no single header of "
                "its own type in the stored markdown",
                stage_id,
            )
    if set(labels) - set(expected):
        raise _refuse(
            REASON_MARKDOWN_MISMATCH,
            "the stored markdown holds a header for a block the stored block list does "
            "not hold as TEXT or IMAGE",
            stage_id,
        )
    return PortalRecognition(blocks=blocks, bodies=bodies)


__all__ = [
    "BLOCK_TYPES",
    "IMAGE",
    "PORTAL_BLOCK_ID",
    "REASON_BLOCKS_INVALID",
    "REASON_BLOCKS_PAGES",
    "REASON_MARKDOWN_INVALID",
    "REASON_MARKDOWN_MISMATCH",
    "STAMP",
    "TEXT",
    "PortalBlock",
    "PortalRecognition",
    "read_block_list",
    "read_portal",
]
