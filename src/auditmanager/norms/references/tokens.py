"""Python twin of migration 0020's `norm_designation_tokens(text)`.

The SQL function calls `translate(split_part(value, '__', 1), FROM, TO)`,
then splits on `[ ._-]+` and removes empty tokens. The fixed tables here are
checked against the migration by a focused test. No locale case operation is
used; Unicode separator cleanup applies only to project text, not SQL twin.
"""

from __future__ import annotations

import re
import unicodedata


_CYRILLIC_UPPER = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
_CYRILLIC_LOWER = "абвгдеежзийклмнопрстуфхцчшщъыьэюя"
_LATIN_REST_UPPER = "DFGIJLNQRSUVWZ"
_HOMOGLYPHS = (
    ("A", "а"), ("a", "а"), ("B", "в"), ("b", "в"),
    ("C", "с"), ("c", "с"), ("E", "е"), ("e", "е"),
    ("H", "н"), ("h", "н"), ("K", "к"), ("k", "к"),
    ("M", "м"), ("m", "м"), ("O", "о"), ("o", "о"),
    ("P", "р"), ("p", "р"), ("T", "т"), ("t", "т"),
    ("X", "х"), ("x", "х"), ("Y", "у"), ("y", "у"),
)


def _tables() -> tuple[str, str]:
    source = _CYRILLIC_UPPER + "ё" + _LATIN_REST_UPPER
    target = _CYRILLIC_LOWER + "е" + _LATIN_REST_UPPER.lower()
    for latin, cyrillic in _HOMOGLYPHS:
        source += latin
        target += cyrillic
    if len(source) != len(target) or len(set(source)) != len(source):
        raise RuntimeError("invalid designation fold tables")
    return source, target


FOLD_FROM, FOLD_TO = _tables()
_TRANSLATE = str.maketrans(FOLD_FROM, FOLD_TO)
_DASHES = {code: "-" for code in range(0x2010, 0x2016)}


def fold(value: str) -> str:
    return value.translate(_TRANSLATE)


def sql_designation_tokens(value: str) -> tuple[str, ...]:
    """Exact SQL twin, including its narrow ASCII-only separator class."""
    head = value.split("__", 1)[0]
    return tuple(token for token in re.split(r"[ ._-]+", fold(head)) if token)


def normalize_text_separators(value: str) -> str:
    """One-code-point replacement keeps extraction offsets aligned to raw text."""
    return "".join(
        " " if character.isspace() or unicodedata.category(character) == "Zs"
        else _DASHES.get(ord(character), character)
        for character in value
    )


def text_designation_tokens(value: str) -> tuple[str, ...]:
    """Project-side tokens after Unicode space/dash cleanup for matching."""
    return sql_designation_tokens(normalize_text_separators(value))
