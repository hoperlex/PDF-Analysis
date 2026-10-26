"""Builds ``section_prompt_fragments.json`` from the documents that are its source.

``SECTION-PROMPT-SENTENCE-GUARD-01`` (``D-224`` residual). The 14 ``system_prompt.md`` files are
edited by hand, and a later edit that rebuilds the recording consistently passes every other test.
The sentences that matter are listed in four documents, and this builder reads them; nothing is
retyped:

* ``SECTION-REVIEW-LEDGER-01.md`` -- the table of the 14 sections, column «Prompt changes»: for
  every numbered change the quoted fragments after ``adds`` (the prompt must carry them) and
  after ``removes`` (the prompt must not carry them). A change the parser cannot read is an
  error, never a skip;
* ``SECTION-WIDEN-G1-01.md``, ``-G2-``, ``-G3-`` -- each report's machine-readable block between
  ``<!-- fragments:begin -->`` and ``<!-- fragments:end -->`` (the block the report's own check
  command reads), taken as it stands;
* ``SECTION-WIDEN-G3-01.md``, section «The ledger fragment this lane supersedes» -- the ledger
  sentence that lane replaced. It is recorded in the table as ``superseded``, not dropped.

Usage (from the repository root)::

    python tests/unit/analysis/text_profiles/build_section_prompt_fragments.py          # check
    python tests/unit/analysis/text_profiles/build_section_prompt_fragments.py --write  # rewrite

The check prints ``fragments match`` or what differs. The test
``test_section_prompt_fragments.py`` runs the same comparison, so the table cannot drift from the
documents unnoticed. This module imports nothing from ``auditmanager``.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
TABLE = Path(__file__).resolve().with_name("section_prompt_fragments.json")
FORMAT = "section-prompt-fragments/1"

LEDGER_NAME = "SECTION-REVIEW-LEDGER-01"
LEDGER = f"docs/program/{LEDGER_NAME}.md"
#: Short id prefix -> report name. The prefix qualifies every widen fragment id, because ``W-HEAD``
#: is a different sentence in G2 than in G1 and G3.
WIDEN = {
    "G1": "SECTION-WIDEN-G1-01",
    "G2": "SECTION-WIDEN-G2-01",
    "G3": "SECTION-WIDEN-G3-01",
}
#: The registry order of the 14 sections (the ledger's own order).
SECTION_ORDER = ("AI", "PS", "POS", "TX", "KJ", "KM", "OV", "VK", "PT", "EOM", "SS", "ITP", "GP", "PB")

KINDS = ("present", "absent", "superseded")
_FENCE = "`" * 3
_BLOCK = re.compile(
    "<!-- fragments:begin -->\\s*" + _FENCE + "json\n(.*?)\n" + _FENCE + "\\s*<!-- fragments:end -->",
    re.S,
)
_TOKEN = re.compile(r"(?P<op>\b(?:adds|removes)\b)|«(?P<quote>[^»]*)»")
_ITEM = re.compile(r"^(?P<number>\d+)\. (?P<body>.+)$", re.S)
_REPLACED_ID = re.compile(r"`(W-[A-Z0-9-]+)`")


class SourceError(Exception):
    """A source document that the builder cannot read: never skipped, always reported."""


def normalise(text: str) -> str:
    """Every run of whitespace, line breaks included, becomes one space (the reports' rule)."""
    return " ".join(text.split())


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8")


# --- the widen reports ---------------------------------------------------------------------


def widen_entries(group: str, report_text: str) -> list[dict[str, Any]]:
    match = _BLOCK.search(report_text)
    if match is None:
        raise SourceError(f"{WIDEN[group]}: no machine-readable fragment block")
    entries: list[dict[str, Any]] = []
    for fragment in json.loads(match.group(1)):
        if set(fragment) != {"id", "sections", "role", "text"}:
            raise SourceError(f"{WIDEN[group]}: fragment {fragment.get('id')!r} has keys {sorted(fragment)}")
        entries.append(
            {
                "id": f"{group}:{fragment['id']}",
                "source": WIDEN[group],
                "kind": "present",
                "sections": list(fragment["sections"]),
                "role": fragment["role"],
                "text": normalise(fragment["text"]),
            }
        )
    return entries


# --- the ledger ----------------------------------------------------------------------------


def ledger_entries(ledger_text: str) -> list[dict[str, Any]]:
    """One entry per quoted fragment of the «Prompt changes» column, in table order."""
    rows: dict[str, list[str]] = {}
    for line in ledger_text.splitlines():
        match = re.match(r"^\| ([A-Z]+) \| ", line)
        if match is None or match.group(1) == "Code":
            continue
        cells = line[1:-1].split(" | ")
        if len(cells) != 8:
            raise SourceError(f"{LEDGER_NAME}: the row of {match.group(1)} has {len(cells)} cells, not 8")
        rows[match.group(1)] = cells
    if set(rows) != set(SECTION_ORDER):
        raise SourceError(f"{LEDGER_NAME}: rows {sorted(rows)}, expected {sorted(SECTION_ORDER)}")

    entries: list[dict[str, Any]] = []
    for code in SECTION_ORDER:
        items = rows[code][5].split("<br>")
        if not items[0].startswith("Commit `"):
            raise SourceError(f"{LEDGER_NAME}: {code} «Prompt changes» does not open with its commit")
        for raw in items[1:]:
            item = _ITEM.match(raw.strip())
            if item is None:
                raise SourceError(f"{LEDGER_NAME}: {code} change is not numbered: {raw[:80]!r}")
            label, separator, rest = item.group("body").partition(": ")
            if not separator:
                raise SourceError(f"{LEDGER_NAME}: {code} change {item.group('number')} has no «label: text» shape")
            counters = {"adds": 0, "removes": 0}
            operation: str | None = None
            for token in _TOKEN.finditer(rest):
                if token.group("op"):
                    operation = token.group("op")
                    continue
                if operation is None:
                    raise SourceError(f"{LEDGER_NAME}: {code} change {item.group('number')} quotes before adds/removes")
                counters[operation] += 1
                entries.append(
                    {
                        "id": f"LEDGER:{code}:{item.group('number')}:{operation}:{counters[operation]}",
                        "source": LEDGER_NAME,
                        "kind": "present" if operation == "adds" else "absent",
                        "sections": [code],
                        "role": f"{label}: {operation}",
                        "text": normalise(token.group("quote")),
                    }
                )
            if not any(counters.values()):
                raise SourceError(f"{LEDGER_NAME}: {code} change {item.group('number')} holds no adds/removes fragment")
    return entries


# --- the supersession recorded by lane G3 --------------------------------------------------


def apply_supersessions(
    ledger: list[dict[str, Any]], widen: list[dict[str, Any]], g3_text: str
) -> list[dict[str, Any]]:
    """Mark the ledger fragments that ``SECTION-WIDEN-G3-01`` says it replaced."""
    start = g3_text.find("### The ledger fragment this lane supersedes")
    if start < 0:
        raise SourceError(f"{WIDEN['G3']}: no section «The ledger fragment this lane supersedes»")
    end = g3_text.find("\n## ", start)
    section = g3_text[start : end if end > 0 else len(g3_text)]
    replacement_ids = sorted(set(_REPLACED_ID.findall(section)))
    known = {entry["id"] for entry in widen}
    for fragment_id in replacement_ids:
        if f"G3:{fragment_id}" not in known:
            raise SourceError(f"{WIDEN['G3']}: the supersession names {fragment_id}, which its fragment block lacks")
    replaced = 0
    for line in section.splitlines():
        match = re.match(r"^\| ([A-Z]+)-\d+ \(N\) \| (.+?) \| ", line)
        if match is None:
            continue
        code, sentence = match.group(1), normalise(match.group(2)).rstrip(";").rstrip()
        hits = [
            entry
            for entry in ledger
            if entry["sections"] == [code] and entry["kind"] == "present" and entry["text"] == sentence
        ]
        if len(hits) != 1:
            raise SourceError(f"{WIDEN['G3']}: the superseded {code} sentence matches {len(hits)} ledger fragments")
        hits[0]["kind"] = "superseded"
        hits[0]["superseded_in"] = WIDEN["G3"]
        hits[0]["superseded_by"] = [f"G3:{fragment_id}" for fragment_id in replacement_ids]
        replaced += 1
    if not replaced:
        raise SourceError(f"{WIDEN['G3']}: the supersession table names no ledger row")
    return ledger


# --- the table -----------------------------------------------------------------------------


def build(root: Path = ROOT) -> dict[str, Any]:
    ledger = ledger_entries(_read(root, LEDGER))
    widen: list[dict[str, Any]] = []
    for group, name in WIDEN.items():
        widen.extend(widen_entries(group, _read(root, f"docs/program/{name}.md")))
    ledger = apply_supersessions(ledger, widen, _read(root, f"docs/program/{WIDEN['G3']}.md"))
    return {
        "format": FORMAT,
        "about": (
            "Sentences of the 14 section prompts that a test must see stand or stay gone "
            "(SECTION-PROMPT-SENTENCE-GUARD-01, D-224 residual). kind present: the whitespace-normalised "
            "text occurs in the prompt of every listed section. kind absent: it does not. kind superseded: "
            "a ledger sentence a later lane replaced; it must not occur and every id in superseded_by must "
            "be a present entry of the same section. Generated from the documents named in sources by "
            "tests/unit/analysis/text_profiles/build_section_prompt_fragments.py; do not edit by hand."
        ),
        "normalisation": "every run of whitespace, line breaks included, replaced by one space, on both sides",
        "sources": {
            LEDGER_NAME: LEDGER,
            **{name: f"docs/program/{name}.md" for name in WIDEN.values()},
        },
        "fragments": [*ledger, *widen],
    }


def render(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=1) + "\n"


def main(argv: list[str]) -> int:
    try:
        document = build()
    except SourceError as error:
        print(f"cannot read the sources: {error}")
        return 3
    text = render(document)
    if argv == ["--write"]:
        TABLE.write_text(text, encoding="utf-8")
        print(f"wrote {len(document['fragments'])} fragments to {TABLE.relative_to(ROOT)}")
        return 0
    if argv:
        print(__doc__)
        return 2
    if not TABLE.is_file() or TABLE.read_text(encoding="utf-8") != text:
        print("fragments differ from the documents; re-run with --write")
        return 1
    print("fragments match")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
