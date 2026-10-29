"""Shared fixtures of the unit tests of the specification package (`CMP-VC-SPEC-01`).

Pages of a specification, drawn the way the page profile reports them: words ``[x0, top, x1, bottom, text]`` and vector lines
``[x0, top, x1, bottom]`` in points, origin at the top left (`CMP-VC-SPEC-01`). Used by the unit tests of the pure parser; the
corpus pages are profiled by the real children in the engine tests."""

from __future__ import annotations

from typing import Any

import pytest

PAGE_W, PAGE_H = 595.28, 841.89
#: pos | mark | name | quantity | mass | note
COLUMNS = [("pos", 56.7, 92.7), ("mark", 92.7, 222.7), ("name", 222.7, 422.7), ("quantity", 422.7, 458.7), ("mass", 458.7, 513.7),
           ("note", 513.7, 581.1)]
HEADER = {"pos": ["Поз."], "mark": ["Обозначение"], "name": ["Наименование", "и", "тех.", "характеристика"], "quantity": ["Кол."],
          "mass": ["Масса", "ед.,", "кг"], "note": ["Прим."]}
ROW_H = 22.0
HEADER_TOP, HEADER_RULE = 72.0, 98.0


def _words(text: str, x0: float, top: float, size: float = 8.0) -> list[list[Any]]:
    out, x = [], x0 + 3
    for token in text.split():
        width = 4.6 * len(token)
        out.append([x, top, x + width, top + size, token])
        x += width + 2.6
    return out


class Page:
    """A specification page: the header, the rules, and the rows added one by one."""

    def __init__(self, *, columns=COLUMNS, header=HEADER, numbered_row: bool = False, rules: bool = True, header_words: bool = True) -> None:
        self.columns = list(columns)
        self.words: list[list[Any]] = []
        self.lines: list[list[float]] = []
        self.y = HEADER_RULE
        x_first, x_last = self.columns[0][1], self.columns[-1][2]
        if header_words:
            for field, x0, _ in self.columns:
                self.words += _words(" ".join(header.get(field, [])), x0, 82.0)
        if rules:
            self.lines.append([x_first, HEADER_TOP, x_last, HEADER_TOP])
            self.lines.append([x_first, HEADER_RULE, x_last, HEADER_RULE])
        self._x_first, self._x_last, self._rules = x_first, x_last, rules
        if numbered_row:
            self.row({field: str(k + 1) for k, (field, _, _) in enumerate(self.columns)})

    def row(self, cells: dict[str, str], *, height: float = ROW_H, lines: int = 1) -> "Page":
        top = self.y
        for field, x0, x1 in self.columns:
            if cells.get(field):
                for k, chunk in enumerate(_chunks(cells[field], lines)):
                    self.words += _words(chunk, x0, top + 4 + 9 * k)
        self.y = top + height * lines if lines > 1 and height == ROW_H else top + height
        if self._rules:
            self.lines.append([self._x_first, self.y, self._x_last, self.y])
        return self

    def merged(self, text: str, *, height: float = ROW_H) -> "Page":
        """A section title across the whole table (a merged cell): contiguous words that cross the borders of the columns."""
        top = self.y
        x = self.columns[0][1] + 140  # starts in the second column and runs on into the third
        for token in text.split():
            width = 4.6 * len(token)
            self.words.append([x, top + 4, x + width, top + 12, token])
            x += width + 2.0
        self.y = top + height
        if self._rules:
            self.lines.append([self._x_first, self.y, self._x_last, self.y])
        return self

    def finish(self) -> "Page":
        """The vertical rules (the columns) from the top of the header to the last row rule."""
        borders = sorted({c[1] for c in self.columns} | {c[2] for c in self.columns})
        for x in borders:
            self.lines.append([x, HEADER_TOP, x, self.y])
        return self

    def parse(self, **kw: Any):
        from auditmanager.comparison.specification import table

        self.finish()
        return table.parse_page(self.words, self.lines, PAGE_W, PAGE_H, kw.get("stamp_zone"))


def _chunks(text: str, parts: int) -> list[str]:
    if parts <= 1:
        return [text]
    tokens = text.split()
    size = -(-len(tokens) // parts)
    return [" ".join(tokens[i : i + size]) for i in range(0, len(tokens), size)]


class Drawn:
    """What the tests get from the ``drawn`` fixture: the page builder and the sheet's size."""

    Page = Page
    PAGE_W = PAGE_W
    PAGE_H = PAGE_H
    COLUMNS = COLUMNS


@pytest.fixture(scope="session")
def drawn() -> type[Drawn]:
    return Drawn


# -- a model's answer, written the way a faithful model would, for the checks of part B ----------------------------------------

from auditmanager.comparison.specification import check, source as source_module  # noqa: E402


def faithful_answer(source: dict) -> dict:
    """The answer a careful model gives for a packet: every pipe row a position (its whole line as evidence, its cells as the
    fields), the header and separator lines ignored as such, a plain line a section title. The oracle of the checks."""
    blocks = []
    section = ""
    for block in source["blocks"]:
        rows, ignored = [], []
        header: dict[int, str] | None = None
        for line in block["lines"]:
            cells = check._pipe_cells(line["text"])
            if cells is None:
                section = line["text"].strip()
                ignored.append({"line": line["line"], "reason": "section"})
                continue
            recognized = check._table_header(cells)
            if recognized is not None:
                header = recognized
                ignored.append({"line": line["line"], "reason": "header"})
                continue
            if check._separator_row(cells):
                ignored.append({"line": line["line"], "reason": "separator"})
                continue
            assert header is not None
            fields = {name: "" for name in check.FIELDS}
            for index, field in header.items():
                fields[field] = cells[index]
            rows.append({"section": section, "parent": "", "fields": fields, "evidence": [{"line": line["line"], "quote": line["text"]}]})
        blocks.append({"block_id": block["block_id"], "rows": rows, "ignored": ignored, "issues": []})
    return {"blocks": blocks}


def source_of(*pages: "Page") -> dict:  # noqa: F821
    """The packet of one version from drawn pages (the parser's rows are the text)."""
    parsed = []
    for number, page in enumerate(pages, start=1):
        result = page.parse()
        assert result is not None and result["parsed"], result
        parsed.append({"page": number, "sheet": str(number), "name": "Спецификация", "columns": result["columns"], "rows": result["rows"]})
    return source_module.build_source(parsed)


class Whole:
    faithful_answer = staticmethod(faithful_answer)
    source_of = staticmethod(source_of)


@pytest.fixture(scope="session")
def whole() -> type[Whole]:
    return Whole
