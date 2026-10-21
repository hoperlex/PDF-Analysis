"""`XLSX-RU-LABELS-01`: the workbook's Russian labels are the screens' labels, held in lockstep.

``auditmanager.exports.xlsx.labels`` is the one Python source of the words the Excel export
prints for severity, finding category and decision verdict. The screens print the same enums
from three web tables. This test reads those three ``.ts``/``.tsx`` files **as text** (no
node, no build) and fails when the tables differ in any key or any character, so a relabel
on a screen without the same change in the export, or a value the contract adds without a
label, is a red test instead of a workbook that disagrees with the screen.

It also holds the Python tables to the sealed contract vocabulary (``contracts/api/v1/
openapi.json``), in the contract's order, so the export cannot carry a label for a value the
contract does not have or miss one it does.

The parser is small and tolerant of formatting (comments, quote style, trailing commas,
quoted keys, escapes) and strict about meaning: anything it cannot read as a flat
``key: 'literal'`` table (a concatenation, a template with ``${}``, a spread, a computed
key, a duplicate key) is an error, never a skipped entry. A guard that cannot read what it
guards would pass for the wrong reason.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from auditmanager.exports.xlsx.labels import (
    CATEGORY_LABELS,
    SEVERITY_LABELS,
    VERDICT_LABELS,
)

ROOT = Path(__file__).resolve().parents[3]
ENTITIES = ROOT / "web" / "src" / "entities"
OPENAPI = ROOT / "contracts" / "api" / "v1" / "openapi.json"

#: (python table, web source file, exported name there, contract schema)
LOCKSTEP = {
    "severity": (
        SEVERITY_LABELS,
        ENTITIES / "finding" / "model" / "severity-labels.ts",
        "SEVERITY_LABELS",
        "Severity",
    ),
    "category": (
        CATEGORY_LABELS,
        ENTITIES / "expert-decision" / "model" / "category-labels.ts",
        "CATEGORY_LABELS",
        "FindingCategory",
    ),
    "verdict": (
        VERDICT_LABELS,
        ENTITIES / "expert-decision" / "ui" / "verdict-badge.tsx",
        "VERDICT_LABELS",
        "Verdict",
    ),
}


class TsTableUnreadable(ValueError):
    """The source is not a flat table of string literals this parser can read exactly."""


_IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
_SIMPLE_ESCAPES = {
    "n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0",
    "\\": "\\", "'": "'", '"': '"', "`": "`", "/": "/",
}


def _skip(source: str, position: int) -> int:
    """Skip whitespace, ``// …`` and ``/* … */`` comments."""
    while position < len(source):
        if source[position].isspace():
            position += 1
        elif source.startswith("//", position):
            newline = source.find("\n", position)
            position = len(source) if newline < 0 else newline + 1
        elif source.startswith("/*", position):
            end = source.find("*/", position + 2)
            if end < 0:
                raise TsTableUnreadable("unterminated_block_comment")
            position = end + 2
        else:
            break
    return position


def _string(source: str, position: int) -> tuple[str, int]:
    """Read one string literal starting at ``position``; return (value, next position)."""
    quote = source[position]
    if quote not in "'\"`":
        raise TsTableUnreadable(f"string_literal_expected_at:{source[position:position + 24]!r}")
    result: list[str] = []
    position += 1
    while position < len(source):
        character = source[position]
        if character == quote:
            return "".join(result), position + 1
        if character == "\n" and quote != "`":
            raise TsTableUnreadable("unterminated_string")
        if quote == "`" and source.startswith("${", position):
            raise TsTableUnreadable("template_substitution_unsupported")
        if character != "\\":
            result.append(character)
            position += 1
            continue
        position += 1
        if position >= len(source):
            break
        escape = source[position]
        if escape in _SIMPLE_ESCAPES:
            result.append(_SIMPLE_ESCAPES[escape])
            position += 1
        elif escape == "u" and source[position + 1:position + 2] == "{":
            end = source.find("}", position)
            if end < 0:
                raise TsTableUnreadable("bad_unicode_escape")
            result.append(chr(int(source[position + 2:end], 16)))
            position = end + 1
        elif escape == "u" and re.fullmatch(r"[0-9A-Fa-f]{4}", source[position + 1:position + 5]):
            result.append(chr(int(source[position + 1:position + 5], 16)))
            position += 5
        elif escape == "x" and re.fullmatch(r"[0-9A-Fa-f]{2}", source[position + 1:position + 3]):
            result.append(chr(int(source[position + 1:position + 3], 16)))
            position += 3
        else:
            raise TsTableUnreadable(f"escape_unsupported:\\{escape}")
    raise TsTableUnreadable("unterminated_string")


def parse_label_table(source: str, name: str) -> dict[str, str]:
    """The ``export const <name> … = { key: 'literal', … }`` table, in source order."""
    declarations = list(re.finditer(rf"\bexport\s+const\s+{re.escape(name)}\b", source))
    if len(declarations) != 1:
        raise TsTableUnreadable(f"declaration_count:{len(declarations)}")
    opening = re.compile(r"=\s*\{").search(source, declarations[0].end())
    if opening is None or ";" in source[declarations[0].end():opening.start()]:
        raise TsTableUnreadable("object_literal_missing")
    position = opening.end()
    table: dict[str, str] = {}
    while True:
        position = _skip(source, position)
        if position >= len(source):
            raise TsTableUnreadable("table_not_closed")
        if source[position] == "}":
            return table
        if source[position] in "'\"":
            key, position = _string(source, position)
        else:
            match = _IDENTIFIER.match(source, position)
            if match is None:
                raise TsTableUnreadable(f"key_expected_at:{source[position:position + 24]!r}")
            key, position = match.group(0), match.end()
        position = _skip(source, position)
        if source[position:position + 1] != ":":
            raise TsTableUnreadable(f"colon_expected_after:{key}")
        position = _skip(source, position + 1)
        value, position = _string(source, position)
        position = _skip(source, position)
        if source[position:position + 1] == ",":
            position += 1
        elif source[position:position + 1] != "}":
            raise TsTableUnreadable(f"value_not_a_plain_literal:{key}")
        if key in table:
            raise TsTableUnreadable(f"duplicate_key:{key}")
        table[key] = value


def disagreements(export: dict[str, str], web: dict[str, str]) -> list[str]:
    """Every way the export table and the web table differ. Empty means lockstep."""
    problems = [f"web-only key {key!r}: {web[key]!r}" for key in web.keys() - export.keys()]
    problems += [
        f"export-only key {key!r}: {export[key]!r}" for key in export.keys() - web.keys()
    ]
    problems += [
        f"{key!r}: web {web[key]!r} != export {export[key]!r}"
        for key in web.keys() & export.keys()
        if web[key] != export[key]
    ]
    return sorted(problems)


def _web(kind: str) -> dict[str, str]:
    _, path, name, _ = LOCKSTEP[kind]
    return parse_label_table(path.read_text(encoding="utf-8"), name)


@pytest.mark.parametrize("kind", sorted(LOCKSTEP))
def test_the_export_labels_equal_the_screens_labels(kind: str) -> None:
    table, path, name, _ = LOCKSTEP[kind]
    web = _web(kind)
    assert web, f"{name} in {path.relative_to(ROOT)} parsed empty"
    assert disagreements(dict(table), web) == []


@pytest.mark.parametrize("kind", sorted(LOCKSTEP))
def test_the_export_tables_are_the_contract_vocabulary_in_the_contract_order(kind: str) -> None:
    table, _, _, schema = LOCKSTEP[kind]
    contract = json.loads(OPENAPI.read_text(encoding="utf-8"))["components"]["schemas"][schema]
    assert contract["enum"], schema
    assert tuple(table) == tuple(contract["enum"])


def test_every_label_is_a_distinct_nonblank_russian_word() -> None:
    for table, _, name, _ in LOCKSTEP.values():
        values = list(table.values())
        assert len(set(values)) == len(values), name  # two values never share a cell text
        for key, value in table.items():
            assert value == value.strip() and value, (name, key)
            assert re.search(r"[А-Яа-яЁё]", value), (name, key)
            assert value != key  # the raw contract value is what this module replaces


# --- the parser reads what the web files really contain -----------------------------------

SAMPLE = '''
import type { Severity } from '@/shared/api';
// a comment: not an entry, { nor } either
export const OTHER = { critical: 'wrong' };
export const T: Readonly<Record<Severity, string>> = {
  /* block */ critical: 'Критическое', // trailing
  'quoted-key': "Двойные \\"кавычки\\" и \\u0451 \\x41 \\\\",
  "also": `шаблон`,
  last: 'Последнее',
};
'''


def test_the_parser_reads_comments_quote_styles_escapes_and_trailing_commas() -> None:
    assert parse_label_table(SAMPLE, "T") == {
        "critical": "Критическое",
        "quoted-key": 'Двойные "кавычки" и ё A \\',
        "also": "шаблон",
        "last": "Последнее",
    }


@pytest.mark.parametrize(
    ("source", "problem"),
    [
        ("export const T = { a: 'x' + 'y' };", "value_not_a_plain_literal:a"),
        ("export const T = { a: `x${y}` };", "template_substitution_unsupported"),
        ("export const T = { ...OTHER, a: 'x' };", "key_expected_at"),
        ("export const T = { [KEY]: 'x' };", "key_expected_at"),
        ("export const T = { a: LABEL };", "string_literal_expected_at"),
        ("export const T = { a: 'x', a: 'y' };", "duplicate_key:a"),
        ("export const T = { a: 'x', ", "table_not_closed"),
        ("export const T = { a: 'x\\q' };", "escape_unsupported"),
        ("const T = { a: 'x' };", "declaration_count:0"),
        ("export const T = { a: 'x' }; export const T = { a: 'y' };", "declaration_count:2"),
        ("export const T: Foo;\nconst U = { a: 'x' };", "object_literal_missing"),
        ("export const T = { a 'x' };", "colon_expected_after:a"),
    ],
)
def test_the_parser_refuses_what_it_cannot_read_exactly(source: str, problem: str) -> None:
    with pytest.raises(TsTableUnreadable, match=re.escape(problem)):
        parse_label_table(source, "T")


# --- the comparison can fail ---------------------------------------------------------------


_EXPORT = dict(SEVERITY_LABELS)
_MUTATIONS = {
    "a screen relabels one value": (_EXPORT, {**_EXPORT, "critical": "Критичное"}),
    "a trailing space on the screen": (_EXPORT, {**_EXPORT, "economic": "Экономическое "}),
    "a Latin homoglyph on the screen": (
        _EXPORT, {**_EXPORT, "critical": _EXPORT["critical"].replace("е", "e")},
    ),
    "the contract adds a value the screen labels": (_EXPORT, {**_EXPORT, "urgent": "Срочное"}),
    "the screen drops a value": (
        _EXPORT, {key: value for key, value in _EXPORT.items() if key != "operational"},
    ),
    "the export relabels one value": ({**_EXPORT, "critical": "Критичное"}, _EXPORT),
    "the export adds a value": ({**_EXPORT, "urgent": "Срочное"}, _EXPORT),
}


@pytest.mark.parametrize("case", sorted(_MUTATIONS))
def test_the_comparison_reports_every_kind_of_disagreement(case: str) -> None:
    export, web = _MUTATIONS[case]
    assert disagreements(export, web), case
    assert disagreements(_EXPORT, _EXPORT) == []


def test_the_comparison_reads_a_changed_web_source_text() -> None:
    """The whole path from a screen's file text to a verdict: relabel in the text, go red."""
    path = LOCKSTEP["severity"][1]
    text = path.read_text(encoding="utf-8")
    assert "critical: 'Критическое'," in text
    relabelled = text.replace("critical: 'Критическое',", "critical: 'Критично',")
    assert disagreements(dict(SEVERITY_LABELS), parse_label_table(relabelled, "SEVERITY_LABELS"))
    added = text.replace("};", "  urgent: 'Срочное',\n};")
    assert disagreements(dict(SEVERITY_LABELS), parse_label_table(added, "SEVERITY_LABELS"))
