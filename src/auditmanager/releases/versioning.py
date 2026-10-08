"""Canonical SemVer 2.0 precedence for release metadata.

The encoded key is intended for a PostgreSQL text column with ``COLLATE "C"``.
Locale-aware collation does not promise ASCII byte order and must not be used
for this key. No build metadata is admitted, so equal precedence has one
canonical spelling.
"""

from __future__ import annotations

import re
from typing import Final

_CORE: Final[str] = r"(0|[1-9][0-9]*)"
_CANONICAL: Final[re.Pattern[str]] = re.compile(
    rf"{_CORE}\.{_CORE}\.{_CORE}(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
)


def _ordered_number(digits: str) -> str:
    """Encode an arbitrary-length nonnegative integer for ASCII lexical order."""
    return "1" * len(digits) + "0" + digits


def canonical_semver_sort_key(version: str) -> str:
    """Return a C-collated key for one canonical SemVer without build metadata.

    A release sorts above all prereleases of its core version. Numeric
    prerelease identifiers sort below alphanumeric identifiers; a shorter
    prerelease list sorts below a longer list with the same prefix. ``!`` is
    below every character allowed in an identifier, so it terminates an
    identifier and the list without reversing prefix order.
    """
    match = _CANONICAL.fullmatch(version)
    if match is None:
        raise ValueError(f"noncanonical SemVer: {version!r}")

    major, minor, patch, prerelease = match.groups()
    core = "!".join(_ordered_number(part) for part in (major, minor, patch)) + "!"
    if prerelease is None:
        return core + "1"

    encoded: list[str] = []
    for identifier in prerelease.split("."):
        if identifier.isascii() and identifier.isdigit():
            if len(identifier) > 1 and identifier.startswith("0"):
                raise ValueError(f"noncanonical SemVer: {version!r}")
            encoded.append("0" + _ordered_number(identifier) + "!")
        else:
            encoded.append("1" + identifier + "!")
    return core + "0" + "".join(encoded) + "!"
