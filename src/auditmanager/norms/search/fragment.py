"""A hit's fragment: plain text and the matched spans as offsets (`NORM-Q01`).

`W55A-SEARCH-01`. ``ts_headline`` marks what matched by wrapping it in ``StartSel`` and
``StopSel``. The contract wants plain text with offsets rather than markup, so the
database is asked to mark with two private-use characters that the canonical text cannot
carry (they are removed from the text before the headline is computed), and this module
turns the marked string into the text and its spans. Offsets are code points of the
returned text -- what a client indexing a string by character reads.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

__all__ = [
    "FRAGMENT_MAX_CHARACTERS",
    "Fragment",
    "HEADLINE_OPTIONS",
    "MARKERS",
    "START",
    "STOP",
    "UNRANKED_FRAGMENT_CHARACTERS",
    "fragment_from_headline",
    "plain_fragment",
]

START: Final[str] = ""
STOP: Final[str] = ""
#: Removed from the canonical text before ``ts_headline`` sees it.
MARKERS: Final[str] = START + STOP

#: ``ts_headline``'s options: our markers, a short excerpt, up to two fragments.
HEADLINE_OPTIONS: Final[str] = (
    f'StartSel="{START}", StopSel="{STOP}", MaxWords=35, MinWords=12, ShortWord=2, '
    'MaxFragments=2, FragmentDelimiter=" … "'
)

#: ``NormFragment.text`` is 1..4000 characters.
FRAGMENT_MAX_CHARACTERS: Final[int] = 4000

#: A designation or clause query has no words to excerpt around: the paragraph's opening.
UNRANKED_FRAGMENT_CHARACTERS: Final[int] = 300


@dataclass(frozen=True, slots=True)
class Fragment:
    text: str
    #: ``(char_start, char_end)``, half-open, non-empty, ordered and disjoint.
    highlights: tuple[tuple[int, int], ...]


def fragment_from_headline(marked: str, *, fallback: str) -> Fragment:
    """The plain text and spans of one ``ts_headline`` answer.

    An unbalanced marker (never produced by ``ts_headline``, but not trusted either) ends
    the span at the end of the text. A headline that leaves no text falls back to the
    paragraph's opening, unmarked.
    """
    text: list[str] = []
    spans: list[tuple[int, int]] = []
    start: int | None = None
    length = 0
    for character in marked:
        if character == START:
            if start is None:
                start = length
            continue
        if character == STOP:
            if start is not None and length > start:
                spans.append((start, length))
            start = None
            continue
        text.append(character)
        length += 1
    if start is not None and length > start:
        spans.append((start, length))
    plain = "".join(text)
    if not plain.strip():
        return plain_fragment(fallback)
    if len(plain) > FRAGMENT_MAX_CHARACTERS:
        plain = plain[:FRAGMENT_MAX_CHARACTERS]
        spans = [
            (first, min(last, FRAGMENT_MAX_CHARACTERS))
            for first, last in spans
            if first < FRAGMENT_MAX_CHARACTERS
        ]
    return Fragment(plain, tuple(spans))


def plain_fragment(text: str) -> Fragment:
    """The paragraph's opening, unmarked, for a hit no words selected."""
    cleaned = text.translate({ord(START): None, ord(STOP): None})
    excerpt = cleaned[:UNRANKED_FRAGMENT_CHARACTERS]
    if not excerpt.strip():
        excerpt = cleaned.strip()[:UNRANKED_FRAGMENT_CHARACTERS] or "…"
    return Fragment(excerpt, ())
