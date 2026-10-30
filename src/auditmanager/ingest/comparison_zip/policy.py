"""ZIP set structure and temporary statistics intake ceilings.

Names, member kinds, encryption, symlinks, compression methods, duplicate
entries and one nesting level are still checked. Numeric counts and byte
ceilings are raised to representation limits for the temporary statistics
intake. ADR-0025 records the earlier production thresholds for rollback.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from auditmanager.ingest.bundle_archive import (
    ACCEPTED_METHODS,
    MAX_RATIO,
    ArchiveEntry,
    decode_display_name,
    duplicate_key,
    is_unsafe_name,
)
from auditmanager.ingest.envelope import MAX_BYTES

from .refusals import refuse_set

__all__ = [
    "DEFAULT_SET_POLICY",
    "KEY_PDF",
    "KEY_ZIP",
    "LevelJudge",
    "SET_DIRECTORY_BYTES",
    "SET_MAX_ENTRIES",
    "SET_MAX_NESTING",
    "SET_MAX_RATIO",
    "SET_MEMBER_BYTES",
    "SET_TOTAL_BYTES",
    "SetPolicy",
]

MiB: Final[int] = 1024 * 1024
GiB: Final[int] = 1024 * MiB

#: ``N``: the entries of a set over all its levels (see the module docstring).
SET_MAX_ENTRIES: Final[int] = 2**31 - 1
#: ADR-0025 decision 12: the uncompressed bytes of a set over all its levels.
SET_TOTAL_BYTES: Final[int] = 2**63 - 1
#: One member: the existing envelope's bound for a PDF.
SET_MEMBER_BYTES: Final[int] = MAX_BYTES
#: The ratio of a member and of an archive: the portal reader's.
SET_MAX_RATIO: Final[int] = MAX_RATIO
#: The central directory the reader will load, whatever its entries claim.
SET_DIRECTORY_BYTES: Final[int] = 2**63 - 1
#: Archives inside the archive: one, ADR-0025 decision 12.
SET_MAX_NESTING: Final[int] = 1

#: The key prefixes of the members a level hands the reader. The key names the member's
#: temporary file; the archive's own name for the member never does.
KEY_PDF: Final[str] = "pdf_"
KEY_ZIP: Final[str] = "zip_"


@dataclass(frozen=True, slots=True)
class SetPolicy:
    """The bounds one ZIP set is read under. The defaults are the production values.

    A test lowers them to cross a rule without writing gigabytes; the constants above are
    asserted separately, so a lowered figure here never stands in for the real one.
    ``nesting_levels`` may be lowered to ``0`` (no archive inside the archive) and may not be
    raised: one level is the ruling.
    """

    entries: int = SET_MAX_ENTRIES
    total_bytes: int = SET_TOTAL_BYTES
    member_bytes: int = SET_MEMBER_BYTES
    ratio: int = SET_MAX_RATIO
    directory_bytes: int = SET_DIRECTORY_BYTES
    nesting_levels: int = SET_MAX_NESTING

    def __post_init__(self) -> None:
        if min(self.entries, self.total_bytes, self.member_bytes, self.directory_bytes) < 0:
            raise ValueError("a bound of a ZIP set cannot be negative")
        if self.ratio < 1:
            raise ValueError("the ratio of a ZIP set is at least 1")
        if not 0 <= self.nesting_levels <= SET_MAX_NESTING:
            raise ValueError("a ZIP set nests at most one level")


DEFAULT_SET_POLICY: Final[SetPolicy] = SetPolicy()


def _kind_of(name: bytes) -> str | None:
    """``"pdf"``, ``"zip"`` or ``None`` for the raw name's suffix (ASCII case folded)."""
    lowered = name.lower()
    if lowered.endswith(b".pdf"):
        return "pdf"
    if lowered.endswith(b".zip"):
        return "zip"
    return None


class LevelJudge:
    """The rules about the entries of one archive of a set: the ``judge`` of its policy.

    One instance judges one archive and remembers how many entries it saw, because the next
    level's entry budget is what this one left. Rules, cheapest first and in the portal
    reader's order: the single entries (a name, a symbolic link, encryption, a method), then
    the names that repeat, then what each member is.
    """

    __slots__ = ("archives_allowed", "entries_seen")

    def __init__(self, *, archives_allowed: bool) -> None:
        self.archives_allowed = archives_allowed
        self.entries_seen = 0

    def __call__(self, entries: tuple[ArchiveEntry, ...]) -> dict[str, ArchiveEntry]:
        self.entries_seen = len(entries)
        files: list[ArchiveEntry] = []
        for entry in entries:
            name = entry.name
            if is_unsafe_name(name):
                raise refuse_set("comparison_zip_member_name")
            if entry.is_symlink:
                raise refuse_set("comparison_zip_symlink")
            if entry.is_encrypted:
                raise refuse_set("comparison_zip_encrypted_member")
            if entry.method not in ACCEPTED_METHODS:
                raise refuse_set("comparison_zip_compression_method")
            if name.startswith(b"__MACOSX/"):
                raise refuse_set("comparison_zip_member_kind")
            # The name a reader shows can differ from the header's (the Unicode Path field):
            # it is held to the same path and service-member rules.
            shown = decode_display_name(name, entry.flags, entry.extra)
            if is_unsafe_name(shown.encode("utf-8")):
                raise refuse_set("comparison_zip_member_name")
            if shown.startswith("__MACOSX/"):
                raise refuse_set("comparison_zip_member_kind")
            if name.endswith(b"/"):
                if entry.size != 0:
                    raise refuse_set("comparison_zip_member_kind")
                continue
            files.append(entry)

        seen: set[str] = set()
        for entry in entries:
            key = duplicate_key(entry)
            if key in seen:
                raise refuse_set("comparison_zip_duplicate_member")
            seen.add(key)

        chosen: dict[str, ArchiveEntry] = {}
        for entry in files:
            kind = _kind_of(entry.name)
            if kind == "pdf":
                chosen[f"{KEY_PDF}{entry.index:05d}"] = entry
            elif kind == "zip":
                if not self.archives_allowed:
                    raise refuse_set("comparison_zip_nested_depth")
                chosen[f"{KEY_ZIP}{entry.index:05d}"] = entry
            else:
                raise refuse_set("comparison_zip_member_kind")
        return chosen
