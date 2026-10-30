"""The text of a version's whole specification, as the model is given it (pure Python; `CMP-VC-SPEC-01`, part B).

The original prepares an authoritative Markdown of the specification from the stored words and the vector grid of the tables and
**never re-reads the PDF or the raster** (``docs/whole_specification_comparison.md`` lines 18-21 and 229-237, PDF-proverka at
``23f379fd``): the text is authoritative, a hole in it is a hole in the answer and not an empty specification. This module does the
same from the rows that part A reads (:func:`~.table.parse_page`): one **block** per specification page, its lines numbered
**absolutely** across the whole packet (the evidence of a position names a line, and a position may continue on the next page), a
table header and separator per page (a repeated header is not a position, ``specification_run.py:49``), one pipe row per table row
and a plain line for a title that spans the table.

The packet carries nothing the user typed (no label, no file name): the same text gives the same bytes, and so the same content key
(`prompt.content_key`). Its size is capped at the original's 140 000 characters (``specification_run.py:24``); a larger one is not cut
and not split, the side is incomplete (``docs/whole_specification_comparison.md`` lines 121-123).

Imports the standard library only.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any, Final

__all__ = [
    "HEADER_LABELS",
    "MAX_SOURCE_CHARS",
    "SOURCE_SCHEMA",
    "build_source",
    "packet_chars",
    "page_lines",
    "source_sha256",
]

SOURCE_SCHEMA: Final[str] = "cmp-spec-source/1"
#: ``specification_run.py:24``.
MAX_SOURCE_CHARS: Final[int] = 140_000
#: The label a column of each field carries in the header line the model reads. They are spellings the validator's header test knows
#: (``specification_source.py:21-31``: «Поз.», «Наименование», «Тип, марка, обозначение», «Код», «Завод-изготовитель», «Ед. изм.»,
#: «Кол.», «Масса», «Примечание»).
HEADER_LABELS: Final[dict[str, str]] = {
    "pos": "Поз.", "name": "Наименование", "mark": "Тип, марка, обозначение", "code": "Код", "supplier": "Завод-изготовитель",
    "unit": "Ед. изм.", "quantity": "Кол.", "mass": "Масса", "note": "Примечание",
}
#: A pipe in a cell would end the cell; it is shown as a slash (the only change made to a value, and made in the text the model
#: reads, never in the stored positions).
_PIPE: Final[str] = "/"


def _cell(text: str) -> str:
    return " ".join(str(text).replace("|", _PIPE).split())


def _plain(row: dict[str, Any]) -> bool:
    """A title that spans the table (a merged cell), or a centred line with nothing but a name: not a table row."""
    cells = row["cells"]
    return bool(row.get("span")) or (bool(row.get("centered")) and set(cells) == {"name"})


def page_lines(columns: Sequence[str | None], rows: Sequence[dict[str, Any]]) -> list[str]:
    """The lines of one specification page: the header, the separator, then the rows (``spec.py:146-232`` rows)."""
    width = len(columns)
    lines = [
        "| " + " | ".join(HEADER_LABELS[c] if c else "" for c in columns) + " |",
        "| " + " | ".join("---" for _ in range(width)) + " |",
    ]
    for row in rows:
        if _plain(row):
            lines.append(_cell(row["cells"].get("name", "")))
            continue
        lines.append("| " + " | ".join(_cell(row["cells"].get(c, "")) if c else "" for c in columns) + " |")
    return lines


def build_source(pages: Sequence[dict[str, Any]], *, batched: bool = False) -> dict[str, Any]:
    """The packet of one version's specification.

    ``pages`` is, in the order of the version, ``{"page": number, "sheet": str, "name": str, "columns": [...], "rows": [...]}``
    (the columns and rows of :func:`~.table.parse_page`). A page with two columns of one field, or no page at all, is an
    ``issue`` and the packet is not ``complete``; so is a packet over :data:`MAX_SOURCE_CHARS`."""
    issues: list[str] = []
    blocks: list[dict[str, Any]] = []
    number = 0
    for page in pages:
        columns = list(page["columns"])
        mapped = [c for c in columns if c]
        if len(mapped) != len(set(mapped)):
            issues.append(f"Two columns of one field on page {page['page']}")
        lines = []
        for text in page_lines(columns, page["rows"]):
            number += 1
            lines.append({"line": number, "text": text})
        blocks.append({
            "block_id": f"p{page['page']}", "page": int(page["page"]), "kind": "table", "lines": lines,
            "sheet": str(page.get("sheet") or ""), "name": str(page.get("name") or ""),
        })
    if not blocks:
        issues.append("No specification page")
    source: dict[str, Any] = {
        "schema": SOURCE_SCHEMA, "label": "specification", "document": "specification", "scope": "all blocks",
        "selection": {"pages": [b["page"] for b in blocks], "block_ids": [b["block_id"] for b in blocks], "mode": "all_blocks"},
        "blocks": blocks, "issues": issues,
    }
    source["source_sha256"] = source_sha256(source)
    if not batched and packet_chars(source) > MAX_SOURCE_CHARS:
        issues.append("The specification is larger than one request holds")
    source["complete"] = not issues
    return source


def packet_chars(source: dict[str, Any]) -> int:
    """The characters of the lines the model reads (the size the cap of the original counts)."""
    return sum(len(line["text"]) + 1 for block in source["blocks"] for line in block["lines"])


def source_sha256(source: dict[str, Any]) -> str:
    """The digest of the text the model reads: the blocks, their pages, sheets and titles and their numbered lines."""
    document = [
        [b["block_id"], b["page"], b["kind"], b.get("sheet", ""), b.get("name", ""), [[ln["line"], ln["text"]] for ln in b["lines"]]]
        for b in source["blocks"]
    ]
    return hashlib.sha256(json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
