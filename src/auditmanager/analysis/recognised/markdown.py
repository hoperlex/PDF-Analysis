"""The portal's ``_results.md``, read into one body per TEXT or IMAGE block.

`W55B-RECOGNISED-01` (plan section B3.6). The stored member ``source.markdown`` is the
portal's rendering of its own recognition, page by page::

    ## Page 3

    ### BLOCK #4 [IMAGE]: blk_91bef18c38cab738e6446aaa100fbd33

    > **Created:** 2026-07-07 07:36:38 UTC
    > **Crop:** [Crop](<a capability URL, never fetched>)
    > **Stamp:** Code: ... | Sheet: 3 | ...

    **[IMAGE]** | Type: План | ...

A STAMP block has no header here; it lives in the block list alone.

What a body is
--------------
The same definition ``auditmanager.ingest`` counts ``recognised_character_count`` by (that
module is another bounded context, so it is restated here rather than imported, and
``tests/integration/analysis/recognised`` holds the two equal over every committed bundle):
the lines after a block's header up to the next block header or ``## Page N`` heading,
each without a trailing carriage return; the blank lines at the start, then the
``> **Key:** value`` quote lines that follow them, then the blank lines at either end are
left out; what remains is joined with ``"\\n"``. Nothing else is touched: the body is the
portal's markdown, kept as text, and it is never rendered here.

The quote lines carry the portal's metadata and its capability URLs. They are skipped and
never read for anything else.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

#: ``### BLOCK #12 [TEXT]: blk_...`` -- the grammar ``auditmanager.ingest`` matches headers
#: by, so the two contexts agree on which lines are headers. The identifier is captured as
#: written; whether it names a block of the list is :mod:`.portal`'s question.
HEADER: Final[re.Pattern[str]] = re.compile(r"^### BLOCK #(\d+) \[([A-Za-z]+)\]: (\S+)[ \t\r]*$")
#: ``## Page 3`` -- ends the body before it, and starts no block.
PAGE_HEADING: Final[re.Pattern[str]] = re.compile(r"^## Page \d+[ \t\r]*$")
#: ``> **Created:** ...``, ``> **Crop:** ...``, ``> **Stamp:** ...``: a block's metadata.
QUOTE_FIELD: Final[re.Pattern[str]] = re.compile(r"^> \*\*[^*\n]+:\*\*")


@dataclass(frozen=True, slots=True)
class MarkdownBlock:
    """One block header of the markdown and the body under it.

    ``position`` is the header's place among the headers of the file, from 0: the order the
    portal wrote the blocks in, which is the second key of the artifact's entry order.
    ``label`` is the bracketed type as written, lower-cased (``text``, ``image``, or anything
    else a malformed file holds).
    """

    position: int
    portal_block_id: str
    label: str
    body: str


def body_of(lines: list[str]) -> str:
    """The body of one block, from the lines under its header (see the module docstring)."""
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    while start < len(lines) and QUOTE_FIELD.match(lines[start]):
        start += 1
    end = len(lines)
    while end > start and not lines[end - 1].strip():
        end -= 1
    while start < end and not lines[start].strip():
        start += 1
    return "\n".join(lines[start:end])


def read_blocks(text: str) -> tuple[MarkdownBlock, ...]:
    """Every block header of ``text`` with its body, in the order of the file.

    One pass over the lines; a file of five hundred pages and sixteen mebibytes is read in a
    fraction of a second. A header repeated for one identifier yields two blocks: refusing
    that is the agreement check's job, not the reader's.
    """
    blocks: list[MarkdownBlock] = []
    current: tuple[str, str] | None = None
    lines: list[str] = []

    def flush() -> None:
        if current is not None:
            blocks.append(
                MarkdownBlock(
                    position=len(blocks),
                    portal_block_id=current[0],
                    label=current[1],
                    body=body_of(lines),
                )
            )

    for line in text.split("\n"):
        header = HEADER.match(line)
        if header is not None:
            flush()
            current, lines = (header.group(3), header.group(2).lower()), []
            continue
        if PAGE_HEADING.match(line):
            flush()
            current, lines = None, []
            continue
        if current is not None:
            lines.append(line.rstrip("\r"))
    flush()
    return tuple(blocks)


__all__ = ["HEADER", "PAGE_HEADING", "QUOTE_FIELD", "MarkdownBlock", "body_of", "read_blocks"]
