"""The catalogue's display name of a norm document, derived from its stored slug.

`W57B-NORMS-CATALOGUE-XLSX-01`. The corpus names a document only by its source file name:
``norm_document.slug`` is that name without ``.pdf`` and ``title`` is the name itself. The
exporter that wrote those names replaced every space, dot, slash and asterisk with ``_``,
wrote ``. `` as ``__`` and cut the name at about sixty characters, so
:func:`auditmanager.norms.search.designation_of` -- the slug before the first ``__``,
underscores as spaces -- shows ``Приказ МЧС России от 24 04 2013 N 288 (ред`` for
``Приказ_МЧС_России_от_24_04_2013_N_288_(ред__от_27_06_2023)``: the ``__`` that split it was
the abbreviation dot of ``ред.``, not a separator.

:func:`display_name` reads the slug again with four rules and nothing else:

1. **Split.** The designation ends at the first ``__`` outside parentheses; for an act with no
   such ``__`` (``… N 320 Об утверждении …``) it ends before the subject's first word
   ``Об``/``О`` after the act's number. The rest is the title.
2. **Abbreviation dots.** A ``__`` inside parentheses is ``. `` (``(ред__от`` is ``(ред. от``);
   in the title every ``__`` is ``. ``.
3. **Dates.** ``от_DD_MM_YYYY`` with a real day and month is ``от DD.MM.YYYY``.
4. **Designation numbers.** After a document-type word of
   :data:`auditmanager.norms.search.DESIGNATION_TYPES` (and up to four-letter words such as
   ``Р``, ``IEC``), the underscores *between* numeric tokens were dots:
   ``СП_54_13330_2022`` is ``СП 54.13330.2022``, ``ГОСТ_1759_5-87`` is ``ГОСТ 1759.5-87``.
   Text inside parentheses (``(EN_136_1998)``, where the lost character may have been a
   colon) is not touched.

A designation left with an unclosed parenthesis is repaired only when the parenthesis is an
edition note cut short: a complete ``(ред. от DD.MM.YYYY`` gets its ``)``, a shorter one
(``(ред``, ``(ред. от 2``) becomes ``(ред. …)``, and ``(с изм.`` likewise. Anything else is
**not derivable**, and the designation falls back to the stored projection verbatim
(:func:`auditmanager.norms.search.designation_of`), so a row is either fully derived or shown
exactly as the document page shows it. Nothing here reads a row, writes one or guesses a
character the slug does not carry; the same slug always gives the same name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from ..search import DESIGNATION_TYPES, designation_of, fold

__all__ = ["DisplayName", "display_name"]

#: The separator the exporter wrote for ``. ``.
_DOT_SPACE: Final[str] = "__"
_DATE: Final[re.Pattern[str]] = re.compile(
    r"(?<![^\W_])от_(0[1-9]|[12]\d|3[01])_(0[1-9]|1[0-2])_(\d{4})(?![^\W_])"
)
_NUMERIC_TOKEN: Final[re.Pattern[str]] = re.compile(r"^\d+(?:-\d+)*$")
_SHORT_LETTERS: Final[re.Pattern[str]] = re.compile(r"^[^\W\d_]{1,4}$")
#: An act's number token, then the first word of its subject.
_ACT_NUMBER: Final[re.Pattern[str]] = re.compile(r"_N_[^_]")
_SUBJECT: Final[re.Pattern[str]] = re.compile(r"_(?=(?:Об|О)_)")
_EDITION_COMPLETE: Final[re.Pattern[str]] = re.compile(
    r"^(ред|с изм)\. от \d{2}\.\d{2}\.\d{4}$"
)
_EDITION_CUT: Final[re.Pattern[str]] = re.compile(r"^(ред|с изм)(?![^\W_])")
_WHITESPACE: Final[re.Pattern[str]] = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class DisplayName:
    """What the catalogue shows for one document; never stored, never an identity."""

    designation: str
    #: The rest of the file name, or ``None`` when the name carries nothing after the
    #: designation.
    title: str | None
    #: Whether :attr:`designation` differs from the stored projection
    #: (:func:`auditmanager.norms.search.designation_of`).
    derived: bool


def display_name(slug: str) -> DisplayName:
    """The display designation and title of ``slug``; see the module docstring."""
    stored = designation_of(slug)
    head, rest = _split(slug)
    designation = _designation(head)
    if designation is None or not designation:
        designation = stored
    title = _title(rest)
    return DisplayName(
        designation=designation, title=title or None, derived=designation != stored
    )


# --- rule 1: where the designation ends ----------------------------------------------------


def _top_level_dot_space(slug: str) -> int | None:
    depth = 0
    index = 0
    while index < len(slug):
        character = slug[index]
        if character == "(":
            depth += 1
        elif character == ")":
            depth = max(depth - 1, 0)
        elif depth == 0 and slug.startswith(_DOT_SPACE, index):
            return index
        index += 1
    return None


def _split(slug: str) -> tuple[str, str]:
    boundary = _top_level_dot_space(slug)
    if boundary is not None:
        return slug[:boundary], slug[boundary + len(_DOT_SPACE):]
    number = _ACT_NUMBER.search(slug)
    if number is not None:
        for subject in _SUBJECT.finditer(slug, number.end()):
            if _depth_at(slug, subject.start()) == 0:
                return slug[: subject.start()], slug[subject.end():]
    return slug, ""


def _depth_at(text: str, position: int) -> int:
    depth = 0
    for character in text[:position]:
        if character == "(":
            depth += 1
        elif character == ")":
            depth = max(depth - 1, 0)
    return depth


# --- rules 2-4 and the edition note --------------------------------------------------------


def _designation(head: str) -> str | None:
    text = _nested_dot_spaces(head)
    text = _dates(text)
    text = _designation_numbers(text)
    text = _spaces(text)
    return _close_edition(text)


def _nested_dot_spaces(text: str) -> str:
    """``__`` inside parentheses is the abbreviation dot and its space."""
    parts: list[str] = []
    depth = 0
    index = 0
    while index < len(text):
        character = text[index]
        if character == "(":
            depth += 1
        elif character == ")":
            depth = max(depth - 1, 0)
        if depth > 0 and text.startswith(_DOT_SPACE, index):
            parts.append(". ")
            index += len(_DOT_SPACE)
            continue
        parts.append(character)
        index += 1
    return "".join(parts)


def _dates(text: str) -> str:
    return _DATE.sub(lambda match: f"от_{match[1]}.{match[2]}.{match[3]}", text)


def _designation_numbers(text: str) -> str:
    """Dots between the numeric tokens that follow a document-type word, outside
    parentheses."""
    tokens = text.split("_")
    result: list[str] = []
    depth = 0
    index = 0
    while index < len(tokens):
        token = tokens[index]
        result.append(token)
        opening = depth
        depth = max(depth + token.count("(") - token.count(")"), 0)
        index += 1
        if opening != 0 or depth != 0 or fold(token) not in DESIGNATION_TYPES:
            continue
        while index < len(tokens) and _SHORT_LETTERS.match(tokens[index]):
            result.append(tokens[index])
            index += 1
        run: list[str] = []
        while index < len(tokens) and _NUMERIC_TOKEN.match(tokens[index]):
            run.append(tokens[index])
            index += 1
        if run:
            result.append(".".join(run))
    return "_".join(result)


def _spaces(text: str) -> str:
    return _WHITESPACE.sub(" ", text.replace("_", " ")).strip()


def _close_edition(text: str) -> str | None:
    """Repair one cut-short edition note at the end, or ``None`` when an unclosed
    parenthesis is anything else."""
    opened = _unclosed(text)
    if opened is None:
        return text
    if opened != text.rfind("("):
        return None
    note = text[opened + 1:].strip()
    if _EDITION_COMPLETE.match(note):
        return f"{text.rstrip()})"
    match = _EDITION_CUT.match(note)
    if match is None:
        return None
    return f"{text[:opened].rstrip()} ({match[1]}. …)"


def _unclosed(text: str) -> int | None:
    stack: list[int] = []
    for position, character in enumerate(text):
        if character == "(":
            stack.append(position)
        elif character == ")":
            if not stack:
                return -1
            stack.pop()
    if not stack:
        return None
    return stack[0] if len(stack) == 1 else -1


# --- the title -----------------------------------------------------------------------------


def _title(rest: str) -> str:
    text = _dates(rest.strip("_"))
    return _spaces(text.replace(_DOT_SPACE, ". "))
