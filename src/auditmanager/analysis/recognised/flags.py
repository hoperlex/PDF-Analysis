"""Quality flags on the portal's recognised text: pure functions, no I/O.

`W55B-RECOGNISED-01` (plan section B3.6, ``P02_SEAMS`` section 4.8). A flag says *this
recognised text may be wrong in this way*; it never changes the text, which is stored as the
portal wrote it. Flags are lowercase snake_case, each at most once, in the order of
:data:`FLAG_ORDER`.

The vocabulary
--------------
``mixed_script``
    A word holding both Cyrillic and Latin letters: ``мелкоshтучных``. A word is a maximal
    run of letters and digits (``[^\\W_]+``), so ``A500C`` is one word and ``1.A`` is two.
``homoglyph``
    A Latin letter standing where a Cyrillic one belongs, or the reverse, judged by the
    letters that look alike (:data:`LATIN_LOOKALIKES`, :data:`CYRILLIC_LOOKALIKES`):

    * inside a word: the letters of the word's minority script are all look-alikes of the
      other script (``Уровeнь``, ``здaния``; and the reverse, ``Systеm`` with a Cyrillic
      ``е``);
    * a whole word: every letter of a Latin word is a look-alike and the nearest words on
      its line are Cyrillic (``c`` for the preposition ``с``; ``600x600`` with a Latin
      ``x``). Not the reverse: a Cyrillic look-alike word among Latin ones was measured on
      the owner's export and raised false flags only.
``cjk``
    A CJK ideograph, kana or hangul syllable anywhere in the text (``кажд梯й``). CJK
    punctuation alone does not raise it.
``doubled_list_marker``
    Two list markers of one kind at the start of a line: ``- -``, ``• •``, ``1. 1.``. A
    markdown thematic break (``- - -``, ``***``) is not one.
``degenerate_instruction_echo``, ``degenerate_first_person_plan``, ``degenerate_page_narration``, ``degenerate_serialised_payload``
    The norms context's degeneracy signals (``auditmanager.norms.public``), one flag per
    signal: the recognition model talking about the page instead of transcribing it.
``empty_text``
    The portal recognised nothing in a TEXT block: its body is empty.

Engineering designations are exempt from ``mixed_script`` and ``homoglyph`` by one pinned
pattern, :data:`DESIGNATION`; its docstring says what it matches and what it does not.

These functions read the text after Unicode NFC (so a decomposed ``й`` is one letter); the
text a caller stores is not normalised.
"""

from __future__ import annotations

import re
import unicodedata
from bisect import bisect_right
from dataclasses import dataclass
from typing import Final, Mapping

from auditmanager.norms.public import DegeneracySignal, inspect_degeneracy

MIXED_SCRIPT: Final[str] = "mixed_script"
HOMOGLYPH: Final[str] = "homoglyph"
CJK: Final[str] = "cjk"
DOUBLED_LIST_MARKER: Final[str] = "doubled_list_marker"
EMPTY_TEXT: Final[str] = "empty_text"
#: ``degenerate_`` + the value of each ``DegeneracySignal``, in the norms context's order.
#: Derived rather than restated, so a signal the norms context adds becomes a flag here
#: instead of a key this module cannot file it under; the test pins today's four.
DEGENERACY_FLAGS: Final[tuple[str, ...]] = tuple(
    f"degenerate_{signal.value}" for signal in DegeneracySignal
)
#: The vocabulary, in the order a flag list carries it.
FLAG_ORDER: Final[tuple[str, ...]] = (
    MIXED_SCRIPT,
    HOMOGLYPH,
    CJK,
    DOUBLED_LIST_MARKER,
    *DEGENERACY_FLAGS,
    EMPTY_TEXT,
)

#: Latin letters that look like Cyrillic ones (``a`` / ``а``, ``B`` / ``В`` ...).
LATIN_LOOKALIKES: Final[frozenset[str]] = frozenset("aceopxyABCEHKMOPTXY")
#: Cyrillic letters that look like Latin ones, the same pairs read the other way.
CYRILLIC_LOOKALIKES: Final[frozenset[str]] = frozenset("асеорхуАВСЕНКМОРТХУ")

_CYRILLIC: Final[re.Pattern[str]] = re.compile("[Ѐ-ԯ]")
_LATIN: Final[re.Pattern[str]] = re.compile(
    "[A-Za-zÀ-ÖØ-öø-ɏḀ-ỿ]"
)
_WORD: Final[re.Pattern[str]] = re.compile(r"[^\W_]+")
_LETTER: Final[re.Pattern[str]] = re.compile(r"[^\W\d_]")

#: CJK unified ideographs (with extension A, the compatibility block and the
#: supplementary planes), hiragana, katakana (with the phonetic extensions and the
#: half-width forms) and hangul (jamo and syllables).
_CJK: Final[re.Pattern[str]] = re.compile(
    "[ᄀ-ᇿ぀-ヿ㄰-㆏ㇰ-ㇿ㐀-䶿"
    "一-鿿가-힯豈-﫿ｦ-ﾟ\U00020000-\U0003134f]"
)

_UPPER: Final[str] = "A-ZА-ЯЁ"

#: **The engineering-designation exemption** (``P02_SEAMS`` section 4.8: "exempt by a pinned
#: pattern"). A span this pattern matches raises neither ``mixed_script`` nor ``homoglyph``;
#: its words still count as the neighbours of other words.
#:
#: It matches, each standing alone (no letter or digit touching it on either side):
#:
#: * a number, a dot and one to three capitals -- an axis or an index: ``1.A``, ``12.Б``,
#:   ``2.1.В``;
#: * two to four capitals, an optional space, no-break space or hyphen, a number (its
#:   parts joined by ``.``, ``,`` or ``/``) and an optional tail of capitals and digits
#:   after an optional hyphen: ``REI 150``, ``EI 60``, ``СП 7-АР``, ``DN100``, ``IP54``;
#: * one capital and a number of at least two digits, with the same optional parts and
#:   tail: ``B25``, ``A500C``, ``M200``;
#: * a number followed by one to three capitals: ``3А``, ``12B``.
#:
#: The capitals are Latin or Cyrillic, mixed or not: a code is written either way.
#:
#: It deliberately does **not** match, so these stay flaggable:
#:
#: * a word with a lower-case letter: ``Bход``, ``Уровeнь``, ``мелкоshтучных``;
#: * capitals with no number: ``ООО``, ``PVC``, ``CП`` (an acronym is a word);
#: * a code with a letter glued to it: ``1.Aрхитектура``, ``A500Cталь``;
#: * five or more capitals before the number: ``ПОЖАР 5`` is a word and a number;
#: * **one capital and one digit**: ``C0``, ``B1``, ``K0``. A class written with a Latin
#:   look-alike is the substitution ``homoglyph`` exists for. Measured on the owner's
#:   portal export (`W55B-RECOGNISED-01.md`, section 4): a pattern that admitted them
#:   hid sixteen words, none of which the PDF's own text layer holds, and nothing else.
DESIGNATION: Final[re.Pattern[str]] = re.compile(
    rf"""
    (?<![^\W_])
    (?:
        \d{{1,3}}(?:\.\d{{1,3}})*\.[{_UPPER}]{{1,3}}
      | [{_UPPER}]{{2,4}}[  -]?\d+(?:[.,/]\d+)*(?:-?[{_UPPER}0-9]{{1,6}})?
      | [{_UPPER}][  -]?\d{{2,}}(?:[.,/]\d+)*(?:-?[{_UPPER}0-9]{{1,6}})?
      | \d+[{_UPPER}]{{1,3}}
    )
    (?![^\W_])
    """,
    re.VERBOSE,
)

_BULLET: Final[str] = "[-*+•–—·▪●○◦]"
_NUMBER: Final[str] = r"\d{1,3}[.)]"
#: Two markers of one kind at a line's start, then a space or the end of the line.
_DOUBLED: Final[re.Pattern[str]] = re.compile(
    rf"^[ \t]*(?:{_BULLET}[ \t]+{_BULLET}|{_NUMBER}[ \t]+{_NUMBER})(?=[ \t]|$)"
)
#: ``- - -``, ``***``, ``_ _ _``: a markdown thematic break, not a list.
_THEMATIC_BREAK: Final[re.Pattern[str]] = re.compile(r"^[ \t]*([-*_])(?:[ \t]*\1){2,}[ \t]*$")


@dataclass(frozen=True, slots=True)
class FlagReport:
    """The flags of one text and, for each, the words or phrases that raised it.

    ``evidence`` is for tests and measurement; the artifact carries ``flags`` only.
    """

    flags: tuple[str, ...]
    evidence: Mapping[str, tuple[str, ...]]


def _script(word: str) -> str:
    cyrillic = _CYRILLIC.search(word) is not None
    latin = _LATIN.search(word) is not None
    if cyrillic and latin:
        return "mixed"
    if cyrillic:
        return "cyrillic"
    if latin:
        return "latin"
    return "other"


def _within_word_homoglyph(word: str) -> bool:
    """The minority script's letters are all look-alikes of the majority script."""
    latin = [ch for ch in word if _LATIN.match(ch)]
    cyrillic = [ch for ch in word if _CYRILLIC.match(ch)]
    if len(latin) <= len(cyrillic) and all(ch in LATIN_LOOKALIKES for ch in latin):
        return True
    return len(cyrillic) <= len(latin) and all(ch in CYRILLIC_LOOKALIKES for ch in cyrillic)


def _letters(word: str) -> list[str]:
    return _LETTER.findall(word)


def _script_words(line: str, mixed: list[str], homoglyphs: list[str]) -> None:
    """``mixed_script`` and ``homoglyph`` over one line, designations exempt."""
    spans = [match.span() for match in DESIGNATION.finditer(line)]
    starts = [start for start, _end in spans]

    def exempt(start: int, end: int) -> bool:
        index = bisect_right(starts, start) - 1
        return index >= 0 and spans[index][0] <= start and end <= spans[index][1]

    words = [
        (match.group(0), _script(match.group(0)), exempt(*match.span()))
        for match in _WORD.finditer(line)
        if _LETTER.search(match.group(0))
    ]
    for index, (word, script, is_exempt) in enumerate(words):
        if is_exempt:
            continue
        if script == "mixed":
            mixed.append(word)
            if _within_word_homoglyph(word):
                homoglyphs.append(word)
            continue
        # The whole-word rule reads one way only: a Latin word among Cyrillic ones. Its
        # mirror (a Cyrillic look-alike word among Latin ones) was measured on the owner's
        # export and raised seven flags, every one of them on a word the PDF's own text
        # layer holds verbatim, and nothing else; it is left out (`W55B-RECOGNISED-01.md`).
        if script != "latin" or not all(ch in LATIN_LOOKALIKES for ch in _letters(word)):
            continue
        neighbours = [words[i][1] for i in (index - 1, index + 1) if 0 <= i < len(words)]
        if neighbours and all(neighbour == "cyrillic" for neighbour in neighbours):
            homoglyphs.append(word)


def inspect_recognised(text: str) -> FlagReport:
    """Every flag ``text`` raises, with its evidence (see the module docstring)."""
    normalised = unicodedata.normalize("NFC", text)
    lines = [line.rstrip("\r") for line in normalised.split("\n")]
    evidence: dict[str, list[str]] = {flag: [] for flag in FLAG_ORDER}

    if not normalised.strip():
        evidence[EMPTY_TEXT].append("")
    if _CYRILLIC.search(normalised) is not None and _LATIN.search(normalised) is not None:
        for line in lines:
            _script_words(line, evidence[MIXED_SCRIPT], evidence[HOMOGLYPH])
    if _CJK.search(normalised) is not None:
        # Words only: a word is letters and digits, so the punctuation inside the kana block
        # (``・``, ``゠``) and the CJK symbols never raise the flag on their own.
        evidence[CJK].extend(
            word for word in _WORD.findall(normalised) if _CJK.search(word) is not None
        )
    for line in lines:
        if _THEMATIC_BREAK.match(line):
            continue
        marker = _DOUBLED.match(line)
        if marker is not None:
            evidence[DOUBLED_LIST_MARKER].append(marker.group(0).strip())
    verdict = inspect_degeneracy(normalised)
    for signal, phrase in zip(verdict.signals, verdict.evidence):
        evidence[f"degenerate_{signal.value}"].append(phrase)

    flags = tuple(flag for flag in FLAG_ORDER if evidence[flag])
    return FlagReport(
        flags=flags,
        evidence={flag: tuple(evidence[flag]) for flag in flags},
    )


def flags_for(text: str) -> tuple[str, ...]:
    """The flags of a recognised text, deduplicated, in :data:`FLAG_ORDER`."""
    return inspect_recognised(text).flags


__all__ = [
    "CJK",
    "CYRILLIC_LOOKALIKES",
    "DEGENERACY_FLAGS",
    "DESIGNATION",
    "DOUBLED_LIST_MARKER",
    "EMPTY_TEXT",
    "FLAG_ORDER",
    "HOMOGLYPH",
    "LATIN_LOOKALIKES",
    "MIXED_SCRIPT",
    "FlagReport",
    "flags_for",
    "inspect_recognised",
]
