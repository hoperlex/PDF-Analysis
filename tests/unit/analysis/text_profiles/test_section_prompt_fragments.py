"""SECTION-PROMPT-SENTENCE-GUARD-01 (D-224 residual): the sentences of the section prompts are read.

The 14 ``system_prompt.md`` files under ``src/auditmanager/analysis/text/profiles/`` are edited by
hand. A sentence deleted from one of them, with the section's recording rebuilt consistently,
passes every other test: the recording key follows the prompt, the token guard reads designations
and not sentences, and the expectations line does not read the prompt at all. The measured
residual (``SECTION-WIDEN-G1-01`` M5, ``-G2-``, ``-G3-``): 322 of 322 cases stay green.

This suite reads the sentences. ``section_prompt_fragments.json`` lists, per section:

* ``present`` -- a sentence that must stand: the ``adds`` fragments of the 25 narrowing decisions of
  ``SECTION-REVIEW-LEDGER-01`` and every fragment of the machine-readable tables of
  ``SECTION-WIDEN-G1-01``, ``-G2-`` and ``-G3-``, and the omission paragraph of five sections in
  ``SECTION-CATEGORY-OCR-01``;
* ``absent`` -- a sentence that must stay gone: the ledger's ``removes`` fragments (a class
  designation, a mark or a symbol that no pinned legacy source contains) and, from
  ``SECTION-CATEGORY-OCR-01``, the category name ``documentation`` in the nine prompts that do not declare it;
* ``superseded`` -- a ledger sentence that a later lane replaced (``ITP`` question ITP-1, replaced
  by ``SECTION-WIDEN-G3-01``): it is kept in the table, must not stand any more (the new unit rule
  contradicts it) and names the fragments that took its place, which must stand.

The table is generated from those documents by ``build_section_prompt_fragments.py`` and is
compared with them here, so neither side can drift. A fragment matches when it occurs in the prompt
after every run of whitespace, line breaks included, is replaced by one space on both sides;
nothing else is tolerated (one altered character is a miss).

Container-free. Every guard below has a case that makes it fail: a fragment deleted from a copy
of its prompt, an absent one added, a character changed, a line re-wrapped (which must stay green).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PROFILES = ROOT / "src/auditmanager/analysis/text/profiles"
TABLE = HERE / "section_prompt_fragments.json"
BUILDER = HERE / "build_section_prompt_fragments.py"

SECTIONS = ("AI", "PS", "POS", "TX", "KJ", "KM", "OV", "VK", "PT", "EOM", "SS", "ITP", "GP", "PB")
#: The sections the three widen lanes changed. ``PB`` has nothing reinstatable (no lane).
WIDENED = ("PS", "POS", "TX", "KJ", "KM", "OV", "VK", "PT", "EOM", "SS", "ITP", "GP")
FORMAT = "section-prompt-fragments/1"
MIN_TEXT = 7  # characters; the shortest entry is the removed class designation «(Г1–Г4)» (7)


def _load_builder() -> Any:
    spec = importlib.util.spec_from_file_location("section_prompt_fragments_builder", BUILDER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalise(text: str) -> str:
    return " ".join(text.split())


def _raw_prompts() -> dict[str, str]:
    found: dict[str, str] = {}
    for directory in sorted(path for path in PROFILES.iterdir() if path.is_dir()):
        manifest = json.loads((directory / "profile.json").read_text("utf-8"))
        found[manifest["section_code"]] = (directory / "system_prompt.md").read_text("utf-8")
    return found


RAW = _raw_prompts()
TABLE_DOCUMENT: dict[str, Any] = json.loads(TABLE.read_text("utf-8"))
ENTRIES: list[dict[str, Any]] = TABLE_DOCUMENT["fragments"]
BY_ID = {entry["id"]: entry for entry in ENTRIES}
PRESENT = [entry for entry in ENTRIES if entry["kind"] == "present"]
ABSENT = [entry for entry in ENTRIES if entry["kind"] == "absent"]
SUPERSEDED = [entry for entry in ENTRIES if entry["kind"] == "superseded"]


def stands(prompt: str, text: str) -> bool:
    return text in normalise(prompt)


def violations(entries: list[dict[str, Any]], prompts: dict[str, str]) -> list[tuple[str, str, str]]:
    """``(id, section, what is wrong)`` for every entry and section whose prompt disagrees."""
    wrong: list[tuple[str, str, str]] = []
    for entry in entries:
        for code in entry["sections"]:
            there = stands(prompts[code], entry["text"])
            if entry["kind"] == "present" and not there:
                wrong.append((entry["id"], code, "missing: the sentence no longer stands"))
            if entry["kind"] in ("absent", "superseded") and there:
                wrong.append((entry["id"], code, "back: a sentence that must stay gone stands again"))
    return wrong


def supersession_problems(entries: list[dict[str, Any]]) -> list[str]:
    """A superseded entry must name present entries that cover the same section."""
    by_id = {entry["id"]: entry for entry in entries}
    problems: list[str] = []
    for entry in entries:
        if entry["kind"] != "superseded":
            continue
        if not entry.get("superseded_by") or not entry.get("superseded_in"):
            problems.append(f"{entry['id']}: superseded without superseded_by / superseded_in")
            continue
        for other_id in entry["superseded_by"]:
            other = by_id.get(other_id)
            if other is None or other["kind"] != "present":
                problems.append(f"{entry['id']}: {other_id} is not a present entry of the table")
            elif not set(entry["sections"]) <= set(other["sections"]):
                problems.append(f"{entry['id']}: {other_id} does not cover {entry['sections']}")
    return problems


# --- the table: its shape, its coverage, its agreement with the documents -----------------------


def test_the_table_has_its_format_and_names_its_sources() -> None:
    assert TABLE_DOCUMENT["format"] == FORMAT
    assert set(TABLE_DOCUMENT) == {"format", "about", "normalisation", "sources", "fragments"}
    assert sorted(TABLE_DOCUMENT["sources"]) == [
        "SECTION-CATEGORY-OCR-01",
        "SECTION-REVIEW-LEDGER-01",
        "SECTION-WIDEN-G1-01",
        "SECTION-WIDEN-G2-01",
        "SECTION-WIDEN-G3-01",
    ]
    for relative in TABLE_DOCUMENT["sources"].values():
        assert (ROOT / relative).is_file(), relative


def test_every_entry_is_well_formed() -> None:
    assert len({entry["id"] for entry in ENTRIES}) == len(ENTRIES), "an id occurs twice"
    for entry in ENTRIES:
        required = {"id", "source", "kind", "sections", "role", "text"}
        if entry["kind"] == "superseded":
            required |= {"superseded_in", "superseded_by"}
        assert set(entry) == required, entry["id"]
        assert entry["kind"] in ("present", "absent", "superseded"), entry["id"]
        assert entry["source"] in TABLE_DOCUMENT["sources"], entry["id"]
        assert entry["sections"] and set(entry["sections"]) <= set(SECTIONS), entry["id"]
        assert len(set(entry["sections"])) == len(entry["sections"]), entry["id"]
        assert entry["text"] == normalise(entry["text"]), f"{entry['id']}: not whitespace-normalised"
        assert len(entry["text"]) >= MIN_TEXT, f"{entry['id']}: too short to mean anything"


def test_every_section_is_read_and_the_widened_ones_by_their_lane() -> None:
    assert sorted(RAW) == sorted(SECTIONS), "a package was added or removed: extend the table"
    ledger = {code for entry in ENTRIES if entry["source"] == "SECTION-REVIEW-LEDGER-01" for code in entry["sections"]}
    assert ledger == set(SECTIONS), "the ledger names a change in every one of the 14 sections"
    widened = {code for entry in ENTRIES if entry["source"].startswith("SECTION-WIDEN") for code in entry["sections"]}
    assert widened == set(WIDENED)
    for group, codes in {
        "SECTION-WIDEN-G1-01": ("PS", "POS", "TX", "KJ"),
        "SECTION-WIDEN-G2-01": ("KM", "OV", "VK", "PT"),
        "SECTION-WIDEN-G3-01": ("EOM", "SS", "ITP", "GP"),
    }.items():
        covered = {code for entry in ENTRIES if entry["source"] == group for code in entry["sections"]}
        assert covered == set(codes), group
    # `SECTION-CATEGORY-OCR-01` (`R-146ao`): the omission paragraph stands in exactly five prompts and the nine
    # others are held free of the new category's name.
    omission = [entry for entry in ENTRIES if entry["source"] == "SECTION-CATEGORY-OCR-01"]
    stands_in = {code for entry in omission if entry["kind"] == "present" for code in entry["sections"]}
    kept_out = {code for entry in omission if entry["kind"] == "absent" for code in entry["sections"]}
    assert stands_in == {"AI", "TX", "EOM", "SS", "ITP"}
    assert kept_out == set(SECTIONS) - stands_in and len(kept_out) == 9


def test_the_counts_are_the_ones_the_documents_state() -> None:
    """The reports state their own counts; the ledger totals 25 narrowing decisions."""
    expected = {
        "SECTION-WIDEN-G1-01": (20, 56),
        "SECTION-WIDEN-G2-01": (31, 40),
        "SECTION-WIDEN-G3-01": (23, 59),
        # `SECTION-CATEGORY-OCR-01`: 11 sentences in the five prompts (6 shared, 5 scopes) and one `absent` entry for the nine others.
        "SECTION-CATEGORY-OCR-01": (12, 44),
    }
    for source, (fragments, pairs) in expected.items():
        mine = [entry for entry in ENTRIES if entry["source"] == source]
        assert (len(mine), sum(len(entry["sections"]) for entry in mine)) == (fragments, pairs), source
    ledger = [entry for entry in ENTRIES if entry["source"] == "SECTION-REVIEW-LEDGER-01"]
    changes = {tuple(entry["id"].split(":")[1:3]) for entry in ledger}
    assert len(changes) == 25, "the ledger lists 25 prompt changes (one per narrowing decision group)"
    per_section = {code: sum(1 for c in changes if c[0] == code) for code in SECTIONS}
    assert per_section == {
        "AI": 2, "PS": 1, "POS": 3, "TX": 1, "KJ": 3, "KM": 1, "OV": 3,
        "VK": 2, "PT": 1, "EOM": 1, "SS": 2, "ITP": 2, "GP": 2, "PB": 1,
    }
    kinds = {kind: sum(1 for entry in ledger if entry["kind"] == kind) for kind in ("present", "absent", "superseded")}
    assert kinds == {"present": 29, "absent": 8, "superseded": 1}


def test_the_table_is_what_the_documents_say() -> None:
    """Generated, not retyped: the same builder re-reads the ledger and the three reports."""
    builder = _load_builder()
    rebuilt = builder.build(ROOT)
    assert rebuilt == TABLE_DOCUMENT, "section_prompt_fragments.json differs from its documents; run the builder with --write"
    assert builder.render(rebuilt) == TABLE.read_text("utf-8"), "the file is not the builder's output byte for byte"


# --- the prompts: every sentence stands or stays gone ---------------------------------------


def test_the_prompts_agree_with_the_whole_table() -> None:
    assert violations(ENTRIES, RAW) == []


@pytest.mark.parametrize("entry", PRESENT, ids=[entry["id"] for entry in PRESENT])
def test_each_present_fragment_stands_in_every_section_it_names(entry: dict[str, Any]) -> None:
    for code in entry["sections"]:
        assert stands(RAW[code], entry["text"]), f"{entry['id']} is gone from the {code} prompt: {entry['text'][:100]}"


@pytest.mark.parametrize("entry", ABSENT, ids=[entry["id"] for entry in ABSENT])
def test_each_removed_fragment_stays_gone(entry: dict[str, Any]) -> None:
    for code in entry["sections"]:
        assert not stands(RAW[code], entry["text"]), f"{entry['id']} is back in the {code} prompt: {entry['text']}"


def test_a_superseded_ledger_sentence_is_gone_and_its_replacement_stands() -> None:
    """``ITP`` question ITP-1: ``SECTION-WIDEN-G3-01`` replaced the ban on comparing units by the unit rule."""
    assert [entry["id"] for entry in SUPERSEDED] == ["LEDGER:ITP:1:adds:1"]
    assert SUPERSEDED[0]["superseded_in"] == "SECTION-WIDEN-G3-01"
    assert SUPERSEDED[0]["superseded_by"] == ["G3:W-UNITS-ITP-G3", "G3:W-UNITS-REF-ITP-G3"]
    assert supersession_problems(ENTRIES) == []
    old = SUPERSEDED[0]
    assert not stands(RAW["ITP"], old["text"]), "the old ban and the new rule would contradict each other"
    for other_id in old["superseded_by"]:
        assert stands(RAW["ITP"], BY_ID[other_id]["text"]), other_id


# --- the guard can fail: each case changes a copy of the prompts, never the files --------------


def _with(prompts: dict[str, str], code: str, text: str) -> dict[str, str]:
    return {**prompts, code: text}


@pytest.mark.parametrize("entry", PRESENT, ids=[entry["id"] for entry in PRESENT])
def test_deleting_a_fragment_from_its_prompt_turns_the_guard_red(entry: dict[str, Any]) -> None:
    for code in entry["sections"]:
        # Normalised text has the fragment verbatim; delete it where it stands, whatever the wrapping.
        shortened = normalise(RAW[code]).replace(entry["text"], "")
        assert shortened != normalise(RAW[code])
        assert (entry["id"], code, "missing: the sentence no longer stands") in violations(
            ENTRIES, _with(RAW, code, shortened)
        )


@pytest.mark.parametrize("entry", ABSENT + SUPERSEDED, ids=[entry["id"] for entry in ABSENT + SUPERSEDED])
def test_putting_a_removed_fragment_back_turns_the_guard_red(entry: dict[str, Any]) -> None:
    for code in entry["sections"]:
        restored = RAW[code].rstrip() + "\n\n" + entry["text"] + "\n"
        assert (entry["id"], code, "back: a sentence that must stay gone stands again") in violations(
            ENTRIES, _with(RAW, code, restored)
        )


@pytest.mark.parametrize("entry", PRESENT, ids=[entry["id"] for entry in PRESENT])
def test_one_changed_character_is_a_miss(entry: dict[str, Any]) -> None:
    middle = len(entry["text"]) // 2
    altered = entry["text"][:middle] + ("#" if entry["text"][middle] != "#" else "%") + entry["text"][middle + 1 :]
    for code in entry["sections"]:
        edited = normalise(RAW[code]).replace(entry["text"], altered)
        assert (entry["id"], code, "missing: the sentence no longer stands") in violations(
            ENTRIES, _with(RAW, code, edited)
        )


def test_rewrapping_a_prompt_does_not_turn_the_guard_red() -> None:
    """Whitespace is not content: a fragment broken over lines or padded still matches."""
    separators = ("\n", "  ", "\t", " \n  ")

    def rewrap(text: str) -> str:
        words = text.split()
        return "".join(word + separators[index % len(separators)] for index, word in enumerate(words))

    rewrapped = {code: rewrap(text) for code, text in RAW.items()}
    assert rewrapped != RAW
    assert violations(ENTRIES, rewrapped) == []


def test_a_section_missing_from_the_prompts_is_an_error_not_a_pass() -> None:
    incomplete = {code: text for code, text in RAW.items() if code != "PB"}
    with pytest.raises(KeyError):
        violations(ENTRIES, incomplete)


def test_a_superseded_entry_without_its_replacement_is_reported() -> None:
    broken = [
        {**entry, "superseded_by": ["G3:W-NO-SUCH-FRAGMENT"]} if entry["kind"] == "superseded" else entry
        for entry in ENTRIES
    ]
    assert supersession_problems(broken) == [
        "LEDGER:ITP:1:adds:1: G3:W-NO-SUCH-FRAGMENT is not a present entry of the table"
    ]
    dropped = [{k: v for k, v in entry.items() if k != "superseded_by"} if entry["kind"] == "superseded" else entry for entry in ENTRIES]
    assert supersession_problems(dropped) == ["LEDGER:ITP:1:adds:1: superseded without superseded_by / superseded_in"]
    wrong_section = [
        {**entry, "sections": ["PS"]} if entry["kind"] == "superseded" else entry for entry in ENTRIES
    ]
    assert len(supersession_problems(wrong_section)) == 2
