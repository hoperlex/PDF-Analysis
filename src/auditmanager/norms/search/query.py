"""What a search text asks for: a designation, a clause and words (`W55-PLAN.md` section A3.4).

`W55A-SEARCH-01`. ``q`` is 1-200 characters, and three things may be in it, in any order:

* a **designation** -- ``СП 54``, ``ГОСТ Р 52085``, ``СНиП 2.01.07-85``, ``ГОСТ_10140-2003``:
  a document-type word from :data:`DESIGNATION_TYPES` followed by tokens up to the last one
  that carries a digit (letter tokens of at most four letters may sit between, as ``Р`` and
  ``ИСО`` do). The database matches it, not this module: the text is handed to
  ``norm_designation_tokens(text)`` -- the same ``IMMUTABLE`` function that generated
  ``norm_document.designation_tokens`` -- and a document matches when the query's tokens
  equal its **leading** tokens, so ``СП 54`` finds ``СП_54_13330_2022`` and never
  ``СП_542_1325800_2024``;
* a **clause** -- ``п. 7.1.4``, ``п.7.1``, ``пункт 5`` -- a dotted-segment prefix of
  ``norm_paragraph.clause_number``: ``7.1`` is ``7.1`` itself and ``7.1.*``, never ``7.10``;
* **words** -- everything else, handed to ``websearch_to_tsquery('russian', ...)``, so the
  Russian stemmer gives the morphology (``здания`` finds ``зданий``).

This module only decides where the parts begin and end. To decide that a word is a
document-type word it folds case and Latin/Cyrillic homoglyphs with :func:`fold`, which is
the character map of migration ``0020`` written out again (a ``src`` module cannot import a
migration); ``tests/integration/norms/search/test_query_parsing.py`` asserts the two maps
are the same map.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

__all__ = [
    "DESIGNATION_TYPES",
    "FOLD_FROM",
    "FOLD_TO",
    "MAX_QUERY_CHARACTERS",
    "ParsedQuery",
    "designation_of",
    "fold",
    "parse_query",
]

#: ``q``'s declared bounds (``searchNorms``); the router enforces them, this restates them.
MAX_QUERY_CHARACTERS: Final[int] = 200

# --- the fold: migration 0020's character map, written out again --------------------------

_CYRILLIC_UPPER: Final[str] = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
_CYRILLIC_LOWER: Final[str] = "абвгдеежзийклмнопрстуфхцчшщъыьэюя"
_CYRILLIC_YO: Final[tuple[str, str]] = ("ё", "е")
_HOMOGLYPHS: Final[tuple[tuple[str, str], ...]] = (
    ("A", "а"), ("a", "а"),
    ("B", "в"), ("b", "в"),
    ("C", "с"), ("c", "с"),
    ("E", "е"), ("e", "е"),
    ("H", "н"), ("h", "н"),
    ("K", "к"), ("k", "к"),
    ("M", "м"), ("m", "м"),
    ("O", "о"), ("o", "о"),
    ("P", "р"), ("p", "р"),
    ("T", "т"), ("t", "т"),
    ("X", "х"), ("x", "х"),
    ("Y", "у"), ("y", "у"),
)
_LATIN_REST_UPPER: Final[str] = "DFGIJLNQRSUVWZ"


def _fold_tables() -> tuple[str, str]:
    source = _CYRILLIC_UPPER + _CYRILLIC_YO[0] + _LATIN_REST_UPPER
    target = _CYRILLIC_LOWER + _CYRILLIC_YO[1] + _LATIN_REST_UPPER.lower()
    for latin, cyrillic in _HOMOGLYPHS:
        source += latin
        target += cyrillic
    if len(source) != len(target) or len(set(source)) != len(source):
        raise RuntimeError("the designation fold tables are not a one-to-one character map")
    return source, target


FOLD_FROM, FOLD_TO = _fold_tables()
_FOLD: Final[dict[int, int]] = str.maketrans(FOLD_FROM, FOLD_TO)


def fold(value: str) -> str:
    """``translate(value, FOLD_FROM, FOLD_TO)``, as the database computes it."""
    return value.translate(_FOLD)


#: Document-type words that open a designation, **folded** (so ``CП`` with a Latin ``C`` is
#: ``сп``). Read off the corpus's designations (``MANIFEST.json``: ГОСТ, СП, СНиП, ВСН, МДС,
#: РД, ПЭУ) and the Russian building-norm families an expert types beside them. A word
#: outside this set is a word: ``бетон 25`` searches the text, it does not look for a
#: document called ``бетон``.
DESIGNATION_TYPES: Final[frozenset[str]] = frozenset(
    fold(word)
    for word in (
        "ГОСТ", "СП", "СНиП", "СанПиН", "СН", "ВСН", "МДС", "РД", "ПУЭ", "ПЭУ", "НПБ",
        "ВСП", "ТСН", "МГСН", "ОДМ", "СТО", "ОСТ", "ТУ", "ГН", "МУ", "ПБ", "ППБ",
    )
)

#: A token of ``q``: a run of anything but the separators ``norm_designation_tokens`` splits
#: on (space, dot, underscore, hyphen).
_TOKEN: Final[re.Pattern[str]] = re.compile(r"[^\s._\-]+")
_DIGIT: Final[re.Pattern[str]] = re.compile(r"\d")
_LETTERS: Final[re.Pattern[str]] = re.compile(r"^[^\W\d_]{1,4}$")

#: ``п. 7.1.4``, ``п.7.1``, ``пп. 5.2``, ``пункт 3``, ``пункта 4.1.`` -- case-insensitive, not
#: inside a word, the number not followed by a letter or digit.
_CLAUSE: Final[re.Pattern[str]] = re.compile(
    r"(?<![\w])(?:пункт[а-яё]*|пп|п)\s*\.?\s*(\d+(?:\.\d+)*)\.?(?![\w])",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ParsedQuery:
    """The three parts of one search text; at least one is present for a non-blank ``q``."""

    designation: str | None
    clause: str | None
    words: str | None

    @property
    def ranked(self) -> bool:
        """Words are ranked by ``ts_rank_cd``; a designation or clause alone is ordered."""
        return self.words is not None


def parse_query(q: str) -> ParsedQuery:
    """Split ``q`` into its designation, clause and words.

    The clause is taken first, so ``СП 54 п. 7.1`` does not read ``п`` as part of the
    designation. Then the first designation run in what is left. Whatever remains, with its
    whitespace collapsed, is the words.
    """
    text = q
    clause: str | None = None
    match = _CLAUSE.search(text)
    if match is not None:
        clause = match.group(1)
        text = text[: match.start()] + " " + text[match.end():]

    designation: str | None = None
    span = _designation_span(text)
    if span is not None:
        designation = text[span[0]: span[1]]
        text = text[: span[0]] + " " + text[span[1]:]

    words = " ".join(text.split()) or None
    return ParsedQuery(designation=designation, clause=clause, words=words)


def _designation_span(text: str) -> tuple[int, int] | None:
    tokens = list(_TOKEN.finditer(text))
    for index, token in enumerate(tokens):
        if fold(token.group()) not in DESIGNATION_TYPES:
            continue
        end: int | None = None
        for following in tokens[index + 1:]:
            value = following.group()
            if _DIGIT.search(value):
                end = following.end()
                continue
            if _LETTERS.match(value) and end is None:
                # ``Р`` in ``ГОСТ Р 52085``, ``ИСО`` in ``ГОСТ Р ИСО 17637``: a short letter
                # token is part of the designation only before its first number.
                continue
            break
        if end is not None:
            return token.start(), end
    return None


def designation_of(slug: str) -> str:
    """The designation a reader sees: the slug before ``__``, underscores as spaces.

    ``СП_54_13330_2022__Свод_правил…`` is ``СП 54 13330 2022``. The slug lost the source's
    dots, so this is what the corpus can honestly say; the title carries the rest.
    """
    head = slug.split("__", 1)[0]
    return " ".join(head.replace("_", " ").split()) or slug
