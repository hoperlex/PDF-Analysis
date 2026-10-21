"""Designation families and editions used by the pure W57b rule.

This identifies labels in project text and catalogue slugs. It does not decide
whether a norm applies, whether a document is legally in force, or whether a
snapshot is qualified.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from auditmanager.norms.references.tokens import fold, normalize_text_separators


_AMENDMENT = re.compile(r"^изменени[ея][ _]*(?:n|№)[ _]*(\d+)[ _]*к[ _]*(.+)$")
# Migration 0020 folds visually similar Latin characters into Cyrillic. For
# example IEC becomes ``iес`` (Latin i, Cyrillic е/с). Construct the literal
# spellings through the same fold so catalogue slugs and project text agree.
_GOST_SUBSERIES = "|".join(re.escape(fold(label)) for label in ("IEC", "ISO", "ИСО", "МЭК"))
STANDARD_FAMILY_PATTERN = rf"(?:гост(?:[ _]+р)?(?:[ _]+(?:{_GOST_SUBSERIES}))?|сп|снип|санпин|всн)"
_STANDARD = re.compile(rf"^({STANDARD_FAMILY_PATTERN})[ _]+(\d+(?:[._-]\d+)*)")
_LAW_NUMBER = re.compile(r"(?<![а-яёa-z0-9])(\d+)[ _-]*фз(?![а-яёa-z0-9])")
_LAW_REVERSE = re.compile(r"(?<![а-яёa-z0-9])фз[ _-]*(\d+)(?![а-яёa-z0-9])")
_ACT_SHORT = re.compile(r"^пп[ _]+рф[ _]*(?:№|n)[ _]*(\d+)(?!\d)")
_ACT_LONG = re.compile(
    r"^постановление[ _]+правительства[ _]+рф(?:[ _]+от[ _\d.]+)?[ _]*(?:№|n)[ _]*(\d+)(?!\d)"
)


@dataclass(frozen=True, slots=True)
class Designation:
    family: str
    base: tuple[str, ...]
    edition: int | None
    amendment_number: int | None
    display: str

    @property
    def family_base(self) -> tuple[str, tuple[str, ...]]:
        return self.family, self.base

    @property
    def cited_key(self) -> tuple[str, tuple[str, ...], int | None, int | None]:
        return self.family, self.base, self.edition, self.amendment_number


def _year(value: str) -> int | None:
    if len(value) == 4 and 1800 <= int(value) <= 2199:
        return int(value)
    if len(value) == 2:
        number = int(value)
        return 2000 + number if number < 50 else 1900 + number
    return None


def parse_designation(text: str) -> Designation | None:
    """Parse a cited designation or a catalogue slug head.

    A numbered amendment retains its base's edition and is marked separately,
    so it cannot compete as a later edition of that base.
    """
    if not isinstance(text, str) or not text:
        return None
    head = text.split("__", 1)[0]
    shadow = fold(normalize_text_separators(head)).strip(" ,;:()[]")
    amendment = _AMENDMENT.match(shadow)
    if amendment is not None:
        base = parse_designation(amendment.group(2))
        if base is None or base.amendment_number is not None:
            return None
        return replace(base, amendment_number=int(amendment.group(1)), display=head.replace("_", " "))

    act = _ACT_SHORT.match(shadow) or _ACT_LONG.match(shadow)
    if act is not None:
        return Designation("пп рф", (str(int(act.group(1))),), None, None, head.replace("_", " "))
    law = _LAW_NUMBER.search(shadow) or _LAW_REVERSE.search(shadow)
    if law is not None:
        return Designation("фз", (str(int(law.group(1))),), None, None, head.replace("_", " "))

    standard = _STANDARD.match(shadow)
    if standard is None:
        return None
    family = standard.group(1).replace("_", " ").replace("  ", " ")
    parts = re.split(r"[._-]", standard.group(2))
    if (family == "сп" and len(parts) < 3) or len(parts) < 2:
        return None
    edition = _year(parts[-1])
    if edition is None:
        return None
    if any(not part for part in parts[:-1]):
        return None
    return Designation(family, tuple(parts[:-1]), edition, None, head.replace("_", " "))


def detection_shadow(text: str) -> str:
    """One-code-point fold/normalization for raw-offset extraction."""
    return fold(normalize_text_separators(text))
