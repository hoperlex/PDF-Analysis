"""Stop words matched by word stem (`plan-v5` 2.4), so a different Russian case of a word still matches.

The stemmer is a small, deterministic suffix stripper in the manner of the Snowball Russian algorithm: it removes a perfective-gerund,
reflexive, adjectival, verb or noun ending, then a derivational ending, inside the usual regions (RV, R2). It is written here, with no
dependency, and is not a claim of conformance with any library: the only contract is that the inflected forms of one word meet in one
stem, and that the same input gives the same stem on every host.

A word that is not wholly Cyrillic (a digit, a Latin designation) is left as it is, casefolded.

Known limit, shared with the Snowball rule it follows: only what lies after the word's first vowel is stripped, so a short word whose first
vowel is its last or last-but-one letter (шов, шва, швов) keeps its form and meets only itself. The owner lists such a word in the forms
that matter.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Final

_VOWELS: Final[frozenset[str]] = frozenset("аеиоуыэюя")
_CYRILLIC_WORD: Final[re.Pattern[str]] = re.compile(r"[а-я]+")
_TOKEN: Final[re.Pattern[str]] = re.compile(r"[^\W_]+")

_PERFECTIVE_GERUND_PLAIN: Final[tuple[str, ...]] = ("ившись", "ывшись", "ивши", "ывши", "ив", "ыв")
_PERFECTIVE_GERUND_AFTER_A_YA: Final[tuple[str, ...]] = ("вшись", "вши", "в")
_REFLEXIVE: Final[tuple[str, ...]] = ("ся", "сь")
_ADJECTIVE: Final[tuple[str, ...]] = (
    "ее", "ие", "ые", "ое", "ими", "ыми", "ей", "ий", "ый", "ой", "ем", "им", "ым", "ом",
    "его", "ого", "ему", "ому", "их", "ых", "ую", "юю", "ая", "яя", "ою", "ею",
)  # fmt: skip
_PARTICIPLE_PLAIN: Final[tuple[str, ...]] = ("ивш", "ывш", "ующ")
_PARTICIPLE_AFTER_A_YA: Final[tuple[str, ...]] = ("ем", "нн", "вш", "ющ", "щ")
_VERB_PLAIN: Final[tuple[str, ...]] = (
    "ила", "ыла", "ена", "ейте", "уйте", "ите", "или", "ыли", "ей", "уй", "ил", "ыл", "им", "ым", "ен",
    "ило", "ыло", "ено", "ят", "ует", "уют", "ит", "ыт", "ены", "ить", "ыть", "ишь", "ую", "ю",
)  # fmt: skip
_VERB_AFTER_A_YA: Final[tuple[str, ...]] = (
    "ла", "на", "ете", "йте", "ли", "й", "л", "ем", "н", "ло", "но", "ет", "ют", "ны", "ть", "ешь", "нно",
)  # fmt: skip
_NOUN: Final[tuple[str, ...]] = (
    "а", "ев", "ов", "ие", "ье", "е", "иями", "ями", "ами", "еи", "ии", "и", "ией", "ей", "ой", "ий", "й",
    "иям", "ям", "ием", "ем", "ам", "ом", "о", "у", "ах", "иях", "ях", "ы", "ь", "ию", "ью", "ю", "ия", "ья", "я",
)  # fmt: skip
_DERIVATIONAL: Final[tuple[str, ...]] = ("ость", "ост")
_SUPERLATIVE: Final[tuple[str, ...]] = ("ейше", "ейш")


def normalise(word: str) -> str:
    """Casefold and fold the letter ё into е, so that the two spellings meet."""
    return word.casefold().replace("ё", "е")


def tokens(text: str) -> tuple[str, ...]:
    """The words of a text, normalised, in order. A word is a run of letters and digits; the rest separates."""
    return tuple(normalise(match) for match in _TOKEN.findall(text))


def _first_vowel_end(word: str, start: int) -> int:
    for index in range(start, len(word)):
        if word[index] in _VOWELS:
            return index + 1
    return len(word)


def _region_after_consonant(word: str, start: int) -> int:
    """The index after the first non-vowel that follows a vowel, from ``start`` (the R1 / R2 rule)."""
    for index in range(start + 1, len(word)):
        if word[index] not in _VOWELS and word[index - 1] in _VOWELS:
            return index + 1
    return len(word)


def _longest(word: str, region_start: int, plain: Sequence[str] = (), after_a_ya: Sequence[str] = ()) -> str:
    """The longest ending that starts inside the region; an ending of the second list also needs а or я right before it, inside it."""
    best = ""
    for ending in plain:
        if len(ending) > len(best) and word.endswith(ending) and len(word) - len(ending) >= region_start:
            best = ending
    for ending in after_a_ya:
        if len(ending) <= len(best) or not word.endswith(ending):
            continue
        start = len(word) - len(ending)
        if start - 1 >= region_start and word[start - 1] in "ая":
            best = ending
    return best


def _step_one(word: str, rv: int) -> str:
    ending = _longest(word, rv, _PERFECTIVE_GERUND_PLAIN, _PERFECTIVE_GERUND_AFTER_A_YA)
    if ending:
        return word[: -len(ending)]
    ending = _longest(word, rv, _REFLEXIVE)
    if ending:
        word = word[: -len(ending)]
    ending = _longest(word, rv, _ADJECTIVE)
    if ending:
        word = word[: -len(ending)]
        participle = _longest(word, rv, _PARTICIPLE_PLAIN, _PARTICIPLE_AFTER_A_YA)
        return word[: -len(participle)] if participle else word
    ending = _longest(word, rv, _VERB_PLAIN, _VERB_AFTER_A_YA)
    if ending:
        return word[: -len(ending)]
    ending = _longest(word, rv, _NOUN)
    if ending:
        return word[: -len(ending)]
    return word


def stem(word: str) -> str:
    """The stem of one word: the same for the inflected forms of a Russian word; a non-Cyrillic word comes back casefolded."""
    folded = normalise(word)
    if not _CYRILLIC_WORD.fullmatch(folded):
        return folded
    rv = _first_vowel_end(folded, 0)
    if rv >= len(folded):
        return folded
    r1 = _region_after_consonant(folded, 0)
    r2 = _region_after_consonant(folded, r1) if r1 < len(folded) else len(folded)

    result = _step_one(folded, rv)
    if result.endswith("и") and len(result) - 1 >= rv:
        result = result[:-1]
    derivational = _longest(result, r2, _DERIVATIONAL)
    if derivational:
        result = result[: -len(derivational)]
    superlative = _longest(result, rv, _SUPERLATIVE)
    if superlative:
        result = result[: -len(superlative)]
    if result.endswith("нн") and len(result) - 1 >= rv:
        result = result[:-1]
    elif result.endswith("ь") and len(result) - 1 >= rv:
        result = result[:-1]
    return result


def stems(text: str) -> tuple[str, ...]:
    """The stems of the words of a text, in order."""
    return tuple(stem(token) for token in tokens(text))


@dataclass(frozen=True, slots=True)
class StopWordMatcher:
    """The owner's stop words compiled to stem sequences. A word or a phrase; a phrase matches as consecutive stems."""

    entries: tuple[tuple[str, tuple[str, ...]], ...] = ()

    def matches(self, *texts: str) -> tuple[str, ...]:
        """The stop words (as the owner wrote them, in the list's order) found in any of ``texts``; a phrase never spans two texts."""
        text_stems = [stems(text) for text in texts]
        found: list[str] = []
        for original, sequence in self.entries:
            width = len(sequence)
            for haystack in text_stems:
                if any(haystack[start : start + width] == sequence for start in range(len(haystack) - width + 1)):
                    found.append(original)
                    break
        return tuple(found)


def compile_stop_words(words: Iterable[str]) -> StopWordMatcher:
    """Compile the owner's list. A blank entry is refused, not skipped: a list that silently shrinks would show «снять» it should not."""
    entries: list[tuple[str, tuple[str, ...]]] = []
    seen: set[tuple[str, ...]] = set()
    for word in words:
        sequence = stems(word)
        if not sequence:
            raise ValueError(f"a stop word has no letters or digits: {word!r}")
        if sequence in seen:
            continue
        seen.add(sequence)
        entries.append((word.strip(), sequence))
    return StopWordMatcher(entries=tuple(entries))
