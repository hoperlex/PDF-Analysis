"""``document_context_build``: the document graph over stable block identities.

Section 4.6 of ``P02_SEAMS``.

``B3`` uses this to build the prompt neighbourhood. It is a **convenience for the
model, never evidence**: the grounding gate resolves against the text layer and the
block index only, so nothing here is allowed to become an anchor of record. That is
why every rule below is deterministic and cheap rather than clever - a better section
detector would not make the graph more trustworthy, because the graph is not what is
trusted.

The three declared rules
------------------------
**Heading.** A block is a heading when its text opens with a dotted decimal number
(``^\\d+(?:\\.\\d+)*\\.``) *and* its dominant font size is strictly greater than the
document's modal body size. Both conditions are needed: the numbering alone would
promote every numbered clause (``1.3. Степень огнестойкости...``) into a section, and
size alone would promote a title page's every line. ``level`` is the depth of the
numbering, so ``4.`` is level 1 and ``4.2.`` would be level 2.

**Front matter.** Blocks that precede the first heading belong to a synthetic section
titled from the first of them. It exists so that *every* block in the index belongs to
exactly one section - a total assignment is an invariant a test can assert, whereas a
graph that silently drops a title page is one nobody notices is lossy.

**References.** ``kind`` is drawn from the contract's four values.
``continuation`` marks a block whose predecessor ended mid-sentence and which does not
open a new numbered clause. ``cross_reference`` marks a block naming a section,
clause or table number whose leading component is an existing section.
``table_caption`` and ``figure_caption`` mark a block opening with ``Таблица N`` or
``Рисунок N``. Every emitted reference resolves to a section that exists; a reference
that would not resolve is not emitted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Final

from auditmanager.analysis.ports.artifacts import (
    ROLE_BLOCK_INDEX,
    ROLE_DOCUMENT_GRAPH,
    ROLE_TEXT_LAYER,
    envelope,
    publish_artifact,
    read_artifact,
)
from auditmanager.analysis.ports.stage import StageContext, StageProduction
from auditmanager.shared.errors import DomainError, ErrorCode

STAGE_ID = "document_context_build"

_NUMBERING: Final[re.Pattern[str]] = re.compile(r"^(\d+(?:\.\d+)*)\.\s+\S")
_CLAUSE_OPENER: Final[re.Pattern[str]] = re.compile(r"^\d+(?:\.\d+)*\.\s")
_SENTENCE_END: Final[re.Pattern[str]] = re.compile(r"[.!?:;»)]\s*$")
_TABLE_CAPTION: Final[re.Pattern[str]] = re.compile(r"^Таблиц[аы]\s+\d")
_FIGURE_CAPTION: Final[re.Pattern[str]] = re.compile(r"^(?:Рисунок|Рис\.)\s*\d")
_CROSS_REFERENCE: Final[re.Pattern[str]] = re.compile(
    r"(?:раздел\w*|пункт\w*|п\.|таблиц\w*|табл\.)\s*№?\s*(\d+)(?:\.\d+)*",
    re.IGNORECASE,
)

#: The title of the synthetic front-matter section is trimmed to this many code points.
_TITLE_LIMIT: Final[int] = 120

#: Share of cased letters that must be upper case for a numbered line to be a heading.
_UPPER_RATIO: Final[float] = 0.8


@dataclass(frozen=True, slots=True)
class _Block:
    block_id: str
    page_number: int
    text: str
    is_heading: bool
    level: int
    number: str


def run(context: StageContext) -> StageProduction:
    """Build and publish the document graph."""
    block_index, block_index_sha256 = read_artifact(
        context.blob_store,
        context.blob(ROLE_BLOCK_INDEX),
        expected_role=ROLE_BLOCK_INDEX,
    )
    text_layer, _ = read_artifact(
        context.blob_store,
        context.blob(ROLE_TEXT_LAYER),
        expected_role=ROLE_TEXT_LAYER,
    )

    blocks = _resolve_blocks(block_index, text_layer)
    sections, section_of = _build_sections(blocks)
    references = _build_references(blocks, sections, section_of)
    neighbourhood = _build_neighbourhood(blocks)

    graph = envelope(
        ROLE_DOCUMENT_GRAPH,
        context.version_uid,
        block_index_sha256=block_index_sha256,
        sections=sections,
        references=references,
        neighbourhood=neighbourhood,
    )
    _refuse_dangling(graph, {block.block_id for block in blocks})

    graph_ref, _ = publish_artifact(context.blob_store, ROLE_DOCUMENT_GRAPH, graph)

    return StageProduction(
        artifacts=(graph_ref,),
        metrics={
            "section_count": len(sections),
            "reference_count": len(references),
            "block_count": len(blocks),
        },
    )


def _resolve_blocks(
    block_index: dict[str, Any], text_layer: dict[str, Any]
) -> list[_Block]:
    """Read each block's text back out of the text layer by its own span.

    The block index carries no text - it carries offsets. Slicing the document-global
    sequence with those offsets is both how the text is obtained and a standing proof
    that the spans resolve: an anchor that does not resolve is refused here rather
    than shipped in a graph.
    """
    from auditmanager.analysis.stages.source_preparation import document_text

    whole = document_text(text_layer)
    total = text_layer.get("total_char_count")
    if total != len(whole):
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message=(
                "the text layer's declared total character count does not match its "
                "own concatenated pages"
            ),
            stage_id=STAGE_ID,
            reason="text_layer_length_mismatch",
        )

    raw = sorted(
        block_index.get("blocks", ()),
        key=lambda block: (block["page_number"], block["block_ordinal"]),
    )
    if not raw:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the block index declares no block",
            stage_id=STAGE_ID,
            reason="empty_block_index",
        )

    texts: list[tuple[dict[str, Any], str]] = []
    for block in raw:
        start, end = block["char_start"], block["char_end"]
        if not 0 <= start <= end <= len(whole):
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message=(
                    "a block span does not resolve against the text layer it is "
                    "bound to"
                ),
                stage_id=STAGE_ID,
                reason="block_span_unresolvable",
            )
        texts.append((block, whole[start:end]))

    resolved: list[_Block] = []
    for block, text in texts:
        match = _NUMBERING.match(text)
        resolved.append(
            _Block(
                block_id=block["block_id"],
                page_number=block["page_number"],
                text=text,
                is_heading=bool(match) and _is_upper_cased(text[match.end(1) :]),
                level=len(match.group(1).split(".")) if match else 0,
                number=match.group(1) if match else "",
            )
        )
    return resolved


def _is_upper_cased(text: str) -> bool:
    """Whether the cased letters of ``text`` are predominantly upper case.

    This is the second half of the heading rule, and it is computed from the text
    layer alone. Font size would discriminate better, but it is not in the block
    index and section 4.4 fixes that artifact's shape - so the graph is derived from
    exactly what a consumer holding the published artifacts can see, rather than from
    extractor internals it cannot reproduce.

    The declared limitation: a heading set in mixed case is not recognised, and its
    blocks fall to the preceding section. That costs the prompt neighbourhood some
    structure and costs the evidence path nothing, because the graph is never
    evidence.
    """
    cased = [character for character in text if character.isalpha()]
    if not cased:
        return False
    upper = sum(1 for character in cased if character.isupper())
    return upper / len(cased) >= _UPPER_RATIO


def _build_sections(
    blocks: list[_Block],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Sections in document order, and the section each block belongs to.

    Assignment is total: every block belongs to exactly one section, and a block
    preceding the first heading belongs to the synthetic front-matter section.
    """
    sections: list[dict[str, Any]] = []
    section_of: dict[str, str] = {}
    by_number: dict[str, str] = {}
    current: dict[str, Any] | None = None

    def open_section(title: str, level: int, page_number: int, number: str) -> None:
        nonlocal current
        section_id = f"s_{len(sections) + 1:04d}"
        parent = _parent_for(number, by_number) if number else None
        current = {
            "section_id": section_id,
            "title": title[:_TITLE_LIMIT],
            "level": level,
            "parent_section_id": parent,
            "page_number": page_number,
            "block_ids": [],
        }
        sections.append(current)
        if number:
            by_number[number] = section_id

    for block in blocks:
        if block.is_heading:
            open_section(block.text, block.level, block.page_number, block.number)
        elif current is None:
            open_section(block.text, 1, block.page_number, "")
        assert current is not None
        current["block_ids"].append(block.block_id)
        section_of[block.block_id] = current["section_id"]

    return sections, section_of


def _parent_for(number: str, by_number: dict[str, str]) -> str | None:
    """The section whose number is this one's prefix, if the document declared it."""
    parts = number.split(".")
    for depth in range(len(parts) - 1, 0, -1):
        candidate = ".".join(parts[:depth])
        if candidate in by_number:
            return by_number[candidate]
    return None


def _build_references(
    blocks: list[_Block],
    sections: list[dict[str, Any]],
    section_of: dict[str, str],
) -> list[dict[str, Any]]:
    """Every reference that resolves, in block order. Nothing that does not."""
    by_number = {
        section["title"].split(".")[0]: section["section_id"]
        for section in sections
        if section["title"][:1].isdigit()
    }
    references: list[dict[str, Any]] = []
    previous: _Block | None = None

    for block in blocks:
        owning = section_of[block.block_id]

        if _TABLE_CAPTION.match(block.text):
            references.append(_reference(block.block_id, owning, "table_caption"))
        elif _FIGURE_CAPTION.match(block.text):
            references.append(_reference(block.block_id, owning, "figure_caption"))
        elif (
            previous is not None
            and not previous.is_heading
            and not block.is_heading
            and not _CLAUSE_OPENER.match(block.text)
            and not _SENTENCE_END.search(previous.text)
        ):
            references.append(_reference(block.block_id, owning, "continuation"))

        for match in _CROSS_REFERENCE.finditer(block.text):
            target = by_number.get(match.group(1))
            if target is not None and target != owning:
                reference = _reference(block.block_id, target, "cross_reference")
                if reference not in references:
                    references.append(reference)

        previous = block

    return references


def _reference(from_block_id: str, to_section_id: str, kind: str) -> dict[str, Any]:
    return {
        "from_block_id": from_block_id,
        "to_section_id": to_section_id,
        "kind": kind,
    }


def _build_neighbourhood(blocks: list[_Block]) -> list[dict[str, Any]]:
    """Flat previous/next over the document-order block sequence."""
    entries: list[dict[str, Any]] = []
    for index, block in enumerate(blocks):
        entries.append(
            {
                "block_id": block.block_id,
                "previous_block_id": blocks[index - 1].block_id if index else None,
                "next_block_id": (
                    blocks[index + 1].block_id if index + 1 < len(blocks) else None
                ),
            }
        )
    return entries


def _refuse_dangling(graph: dict[str, Any], known_blocks: set[str]) -> None:
    """Section 4.6's referential rules, checked before anything is published."""
    section_ids = {section["section_id"] for section in graph["sections"]}

    for section in graph["sections"]:
        for block_id in section["block_ids"]:
            if block_id not in known_blocks:
                raise _dangling("a section names a block the block index does not hold")
        parent = section["parent_section_id"]
        if parent is not None and parent not in section_ids:
            raise _dangling("a section names a parent section that does not exist")

    for reference in graph["references"]:
        if reference["from_block_id"] not in known_blocks:
            raise _dangling("a reference names a block the block index does not hold")
        if reference["to_section_id"] not in section_ids:
            raise _dangling("a reference names a section that does not exist")

    for entry in graph["neighbourhood"]:
        for key in ("block_id", "previous_block_id", "next_block_id"):
            value = entry[key]
            if value is not None and value not in known_blocks:
                raise _dangling(
                    "a neighbourhood entry names a block the block index does not hold"
                )

    _refuse_cycle(graph["sections"])


def _refuse_cycle(sections: list[dict[str, Any]]) -> None:
    """The graph is a tree over ``parent_section_id`` with no cycle."""
    parents = {
        section["section_id"]: section["parent_section_id"] for section in sections
    }
    for section_id in parents:
        seen = {section_id}
        cursor = parents[section_id]
        while cursor is not None:
            if cursor in seen:
                raise _dangling("the section hierarchy contains a cycle")
            seen.add(cursor)
            cursor = parents.get(cursor)


def _dangling(message: str) -> DomainError:
    return DomainError(
        ErrorCode.ANALYSIS_FAILED,
        message=message,
        stage_id=STAGE_ID,
    )


__all__ = ["STAGE_ID", "run"]
