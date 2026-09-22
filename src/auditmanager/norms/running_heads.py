"""What is discarded before a paragraph becomes retrievable text.

Two families, and they are different kinds of claim.

**Publisher noise** is a closed list of phrases the ConsultantPlus export stamps onto every
page. The owner confirmed at `R-16` that it is noise. The list is matched as substrings
because the export bolds some of them — `**КонсультантПлюс**` — and a match on the enum-ish
spelling alone would miss the bolded one (`OPERATING_CONSTRAINTS.md` §12).

**Repeated offcuts** are the document's own title, truncated with an ellipsis and reprinted at
the top of every page. There is no phrase to match: the text differs per document. What
identifies it is that it *repeats* — that is what a running head is — so the rule is
structural: a paragraph ending in an ellipsis that occurs more than once in the same document.

The repetition test is load-bearing and not decoration. Measured over all 674 documents, 110
ellipsis-terminated paragraphs occur exactly once in their document, and they are body text —
`"Рисунок Л.6 - Схема расположения колонн, ригелей и балок перекрытия на отм. ..."`. A rule
that discarded every ellipsis paragraph would delete them.
"""

from __future__ import annotations

import collections
import re
from collections.abc import Iterable

#: Phrases the ConsultantPlus export stamps on every page. Substrings, not whole lines: the
#: export writes `Документ предоставлен **КонсультантПлюс**` and `**КонсультантПлюс**` alike.
PUBLISHER_NOISE_SUBSTRINGS: tuple[str, ...] = (
    "КонсультантПлюс",
    "consultant.ru",
    "Дата сохранения",
    "надежная правовая поддержка",
)

#: `Страница 2 из 14`. Anchored, because `Страница ` on its own is body text elsewhere in the
#: corpus: `ГОСТ_Р_72509-2026` — which carries no ConsultantPlus marker at all — prints
#: `Страница документа - https://GostExpert.ru/gost/...` 49 times, and an unanchored match
#: would discard all 49 as though they were ConsultantPlus footers.
_PAGE_OF_PAGES = re.compile(r"^Страница\s+\d+\s+из\s+\d+$")

#: Both the three-dot ASCII form the export uses and the single ellipsis character, because
#: the corpus contains both and a rule that knows one spelling is a §12 shape.
_ELLIPSIS_ENDINGS: tuple[str, ...] = ("...", "…")

_EMPHASIS = "*_ \t"


def is_publisher_noise_line(line: str) -> bool:
    """One line of a paragraph is a ConsultantPlus stamp."""
    stripped = line.strip().strip(_EMPHASIS).strip()
    if not stripped:
        return False
    if _PAGE_OF_PAGES.match(stripped):
        return True
    return any(phrase in line for phrase in PUBLISHER_NOISE_SUBSTRINGS)


def is_publisher_noise(paragraph: str) -> bool:
    """A paragraph is noise when *every* non-blank line of it is.

    A paragraph mixing a stamp with body text is kept whole. It happens — the export puts
    `Документ предоставлен **КонсультантПлюс**` immediately above the first clause of a page
    with no blank line between — and dropping the paragraph would lose the clause with it.
    """
    lines = [line for line in paragraph.split("\n") if line.strip()]
    if not lines:
        return True
    return all(is_publisher_noise_line(line) for line in lines)


def ends_with_ellipsis(paragraph: str) -> bool:
    return paragraph.rstrip().endswith(_ELLIPSIS_ENDINGS)


def repeated_offcuts(paragraphs: Iterable[str]) -> frozenset[str]:
    """The ellipsis-terminated paragraph texts that occur more than once in one document.

    Returned as a set for membership only. Nothing downstream iterates it, so no output order
    depends on set ordering.
    """
    counts: collections.Counter[str] = collections.Counter(
        paragraph for paragraph in paragraphs if ends_with_ellipsis(paragraph)
    )
    return frozenset(text for text, seen in counts.items() if seen > 1)
