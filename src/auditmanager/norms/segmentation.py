"""The `results.md` parse.

`R-16`: *segmentation is a markdown parse, not an ML task* — the recognised text already
carries the structure. `results.md` has exactly one shape across all 674 documents:

    # Document: <name>.pdf
    Path: ...
    Generated: ...
    ## Page 1
    ### BLOCK #1 [TEXT]: blk_<32 hex>
    > **Created:** ...
    > **Crop:** [Crop](<url>)
    <blank>
    <body, paragraphs separated by blank lines>

The scaffolding lines are not content and are not paragraph candidates. Everything after a
block's `> **Crop:**` line, up to the next `## Page` or `### BLOCK`, is that block's body.
"""

from __future__ import annotations

import re

from .model import BlockBody, Paragraph, ParagraphKind, SegmentationReport, SourceAttribution
from .running_heads import is_publisher_noise, repeated_offcuts

_PAGE = re.compile(r"^## Page (\d+)\s*$")
_BLOCK = re.compile(r"^### BLOCK #(\d+) \[([A-Z]+)\]: (\S+)\s*$")
_BLOCK_META = re.compile(r"^> \*\*(?:Created|Crop):\*\*")
_PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n")

#: `1.`, `4.5`, `А.2.1.` — a clause number opening a paragraph. Requires a separator after it
#: so that a bare table cell reading `2000` is not read as clause 2000.
_CLAUSE = re.compile(r"^(\d+(?:\.\d+)*)\.?[ \t ]+\S")

#: `Дата сохранения: 23.07.2026`, the only date the export states about the draw.
_DRAWN_ON = re.compile(r"Дата сохранения:\s*(\d{2})\.(\d{2})\.(\d{4})")

_TABLE_SEPARATOR = re.compile(r"^\|[\s|:-]+\|$")


class _Block:
    __slots__ = ("page_label", "block_id", "body")

    def __init__(self, page_label: int, block_id: str) -> None:
        self.page_label = page_label
        self.block_id = block_id
        self.body: list[str] = []


def _parse_blocks(markdown: str) -> tuple[list[_Block], int]:
    """Split a `results.md` into blocks, and count the `## Page` headings it carried.

    The count is of headings, not of PDF pages, and the two are different numbers. `results.md`
    prints a `## Page N` heading only where the page carries a block: across the corpus there
    are 28 249 headings and 28 249 blocks over 28 251 PDF pages, because `ГОСТ_Р_50030_2-2010`
    has two pages with no block and `results.md` does not mention them at all.

    The label is the true PDF page number and does not renumber over the gap — that document's
    headings run 1..225 with 22 and 210 absent — so `page_label` can be used to fetch the page
    crop. A field named `pages` here would have been a count of something the file cannot see.
    """
    blocks: list[_Block] = []
    pages = 0
    current: _Block | None = None
    page_label = 0
    for line in markdown.split("\n"):
        page_match = _PAGE.match(line)
        if page_match is not None:
            pages += 1
            page_label = int(page_match.group(1))
            current = None
            continue
        block_match = _BLOCK.match(line)
        if block_match is not None:
            current = _Block(page_label, block_match.group(3))
            blocks.append(current)
            continue
        if current is None or _BLOCK_META.match(line):
            continue
        current.body.append(line)
    return blocks, pages


def blocks(markdown: str) -> tuple[BlockBody, ...]:
    """Every recognition block, in block order, with its page label and its body.

    The public form of the parse that `recognised_text` and `segment` already run. It exists
    because `D-59` is a property of a **block** — 79 of 28 249 of them carry the recognition
    model's own reasoning — and asking that question through `segment` would ask it of
    paragraphs after the noise filter had already run, which is a different population.
    """
    parsed, _page_headings = _parse_blocks(markdown)
    return tuple(
        BlockBody(
            page_label=block.page_label,
            block_id=block.block_id,
            text="\n".join(block.body).strip("\n"),
        )
        for block in parsed
    )


def recognised_text(markdown: str) -> str:
    """The document's recognised text: block bodies in block order, joined by a blank line.

    This is the string `Paragraph.char_offset` indexes into. It is defined here, once, because
    an offset is worthless unless the text it indexes is reconstructible from the source by
    anyone who reads this function.
    """
    blocks, _page_headings = _parse_blocks(markdown)
    return "\n\n".join("\n".join(block.body).strip("\n") for block in blocks)


def _classify(paragraph: str) -> ParagraphKind:
    if paragraph.startswith("#"):
        return ParagraphKind.HEADING
    if paragraph.startswith("|"):
        return ParagraphKind.TABLE_ROW
    return ParagraphKind.BODY


def _clause_number(paragraph: str, kind: ParagraphKind) -> str | None:
    if kind is ParagraphKind.TABLE_ROW:
        return None
    probe = paragraph.lstrip("#").strip() if kind is ParagraphKind.HEADING else paragraph
    match = _CLAUSE.match(probe)
    return match.group(1) if match is not None else None


def drawn_on(markdown: str) -> str | None:
    """The `Дата сохранения` value as ISO-8601, or `None` where the export states none.

    The first occurrence decides. Measured across all 674 documents, no document states two
    different dates, so "the first" and "the only" are the same value here — but the code says
    which it takes, because that stops being true the day two drops are concatenated.
    """
    match = _DRAWN_ON.search(markdown)
    if match is None:
        return None
    day, month, year = match.groups()
    return f"{year}-{month}-{day}"


def attribution(markdown: str) -> SourceAttribution:
    if _DRAWN_ON.search(markdown) is not None or "КонсультантПлюс" in markdown:
        return SourceAttribution.CONSULTANT_PLUS
    return SourceAttribution.UNATTRIBUTED


def segment(document_slug: str, markdown: str) -> tuple[tuple[Paragraph, ...], SegmentationReport]:
    """Parse one `results.md` into substantive paragraphs plus the counts behind them."""
    blocks, page_headings = _parse_blocks(markdown)

    candidates: list[tuple[int, str, str]] = []  # (page_label, block_id, text)
    offset_by_index: list[int] = []
    cursor = 0
    for index, block in enumerate(blocks):
        body = "\n".join(block.body).strip("\n")
        if index:
            cursor += 2  # the "\n\n" recognised_text joins blocks with
        search_from = 0
        for raw in _PARAGRAPH_BREAK.split(body):
            text = raw.strip()
            if not text:
                continue
            # Search forward from the previous paragraph's end, never from zero: a block that
            # prints the same line twice would otherwise give both copies the same offset, and
            # two chunks anchored to one position is an anchor that cannot be checked.
            found = body.find(text, search_from)
            if found < 0:
                found = search_from
            search_from = found + len(text)
            offset_by_index.append(cursor + found)
            candidates.append((block.page_label, block.block_id, text))
        cursor += len(body)

    offcuts = repeated_offcuts(text for _page, _block, text in candidates)

    paragraphs: list[Paragraph] = []
    noise = offcut = clauses = headings = table_rows = substantive_characters = 0
    for index, (page_label, block_id, text) in enumerate(candidates):
        if is_publisher_noise(text):
            noise += 1
            continue
        if text in offcuts:
            offcut += 1
            continue
        if _TABLE_SEPARATOR.match(text):
            offcut += 1
            continue
        kind = _classify(text)
        clause = _clause_number(text, kind)
        if clause is not None:
            clauses += 1
        if kind is ParagraphKind.HEADING:
            headings += 1
        elif kind is ParagraphKind.TABLE_ROW:
            table_rows += 1
        substantive_characters += len(text)
        paragraphs.append(
            Paragraph(
                document_slug=document_slug,
                page_label=page_label,
                block_id=block_id,
                ordinal=len(paragraphs),
                char_offset=offset_by_index[index],
                char_length=len(text),
                kind=kind,
                clause_number=clause,
                text=text,
            )
        )

    report = SegmentationReport(
        document_slug=document_slug,
        page_headings=page_headings,
        blocks=len(blocks),
        recognised_characters=sum(len("\n".join(b.body).strip("\n")) for b in blocks)
        + max(len(blocks) - 1, 0) * 2,
        candidates=len(candidates),
        discarded_publisher_noise=noise,
        discarded_repeated_offcut=offcut,
        substantive=len(paragraphs),
        numbered_clauses=clauses,
        headings=headings,
        table_rows=table_rows,
        substantive_characters=substantive_characters,
        drawn_on=drawn_on(markdown),
        attribution=attribution(markdown),
    )
    return tuple(paragraphs), report
