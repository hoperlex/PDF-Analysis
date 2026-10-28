"""The rule: one leading apostrophe on a text cell a spreadsheet could read as a formula.

``ACCESS-COMPARE-JUDGE-FIXES-01`` (finding 3 of the independent judge of ``SMALL-HARDENING-02``,
`R-146ax`). The first rule looked at the first character only, so ``' =1+1'``, ``'\\n=1+1'``, a cell
that began with a no-break space, a byte-order mark or a zero-width character, and the fullwidth
``＝`` all reached the file untouched. A spreadsheet steps over blanks and invisible characters
before it reads the start of a cell, so the rule does too.

A text cell gets one leading apostrophe when

* it **starts** with a tab, a carriage return or a line feed (:data:`CONTROL_STARTERS`) -- such a
  cell is quoted in the file and some readers trim it before they look, or
* the first character that is **not** one of :data:`LEADING_SKIPPED` (a space, a no-break space,
  U+FEFF, U+200B to U+200D, U+2060, a tab, a carriage return, a line feed) is one of
  :data:`FORMULA_TRIGGERS`: ``=``, ``+``, ``-``, ``@`` and the fullwidth ``＝``, ``＋``, ``－``,
  ``＠``.

Every other text is returned as it came, byte for byte: the empty string, a cell of blanks only,
a cell that starts with a letter, with an apostrophe (never doubled), with another kind of space
(such as U+3000, which is not in the set above), and a cell with a trigger further in. A cell
that is not text (a number, a date) is not this function's business: the writer decides.
"""

from __future__ import annotations

from typing import Final

#: The first characters of a cell that make a spreadsheet read it as a formula: ASCII and fullwidth
#: (U+FF1D, U+FF0B, U+FF0D, U+FF20).
FORMULA_TRIGGERS: Final[frozenset[str]] = frozenset({
    "=", "+", "-", "@",
    "\uff1d", "\uff0b", "\uff0d", "\uff20",
})

#: A cell that begins with one of these gets the apostrophe whatever follows.
CONTROL_STARTERS: Final[frozenset[str]] = frozenset({"\t", "\r", "\n"})

#: Blanks and invisible characters stepped over before the first real character is read: space,
#: no-break space U+00A0, byte-order mark U+FEFF, zero-width space / non-joiner / joiner
#: U+200B..U+200D, word joiner U+2060, tab, carriage return, line feed.
LEADING_SKIPPED: Final[frozenset[str]] = frozenset({
    " ", "\u00a0", "\ufeff", "\u200b", "\u200c", "\u200d", "\u2060", "\t", "\r", "\n",
})

#: The one character put in front of such a cell.
FORMULA_NEUTRALISER: Final[str] = "'"


def neutralise_formula(text: str) -> str:
    """``text`` with one leading apostrophe when it could be read as a formula, else unchanged."""
    if not text:
        return text
    if text[0] in CONTROL_STARTERS:
        return FORMULA_NEUTRALISER + text
    for character in text:
        if character in LEADING_SKIPPED:
            continue
        if character in FORMULA_TRIGGERS:
            return FORMULA_NEUTRALISER + text
        break
    return text


__all__ = [
    "CONTROL_STARTERS",
    "FORMULA_NEUTRALISER",
    "FORMULA_TRIGGERS",
    "LEADING_SKIPPED",
    "neutralise_formula",
]
