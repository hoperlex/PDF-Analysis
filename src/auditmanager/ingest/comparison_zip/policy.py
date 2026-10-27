"""The set policy: what a ZIP of many PDFs may hold.

`CMP-INGEST-ZIP-01` (ADR-0025 decision 12, plan `R3-17`, `Q-CMP-10`). The original's «ZIP-комплект»
(``docs/program/compare/ORIGINAL-STAGE-COMPARISON-INVENTORY.md`` §3.1) is one archive holding the
PDFs of a stage, optionally with ZIPs of projects inside it. It refused an unsafe path, a
corrupt archive and an archive over its size guards; this policy refuses the same and more,
with the shared reader's mechanics under it.

The figures
-----------
=========================== ================ =====================================================
bound                       value            basis
=========================== ================ =====================================================
entries (``N``)             1 000            the batch holds at most 10 000 files and 100 sets
                                             (ADR-0025 decision 9): a set of whole stages averages
                                             100 files, so one archive may hold ten times that;
                                             and a PDF is read in a child process of its own, so
                                             the number of entries is a bound on time. **Decided
                                             by this slice**; the ADR left it to the slice
total uncompressed          2 GiB            ADR-0025 decision 12; the original's archive guard
one member                  250 MiB          the existing envelope's PDF bound (``MAX_BYTES``)
ratio                       100              the portal reader's (``MAX_RATIO``)
central directory           4 MiB            1 000 entries of 4 KiB each; the reader's own bound
                                             (``entries x 196 KiB``) would let 1 000 entries
                                             make the API read 196 MiB
nesting                     one level        an archive inside the archive, none inside that
=========================== ================ =====================================================

**The entry count and the total are counted over every level together**: the entries of a
nested archive take from the budget the first level left, and so do its bytes -- the nested
archive's own bytes included, because they are unpacked to disk before they are read. So the
disk a set can use is the total, at the moment of the largest nesting, and no nesting makes
the budget larger.

What a member is
----------------
A file member is a PDF (a name ending ``.pdf``, any case) or, at the first level, a ZIP (a name
ending ``.zip``). Anything else is refused (``comparison_zip_member_kind``) -- a document of
another format, a ``__MACOSX/`` file, a ``.pdf.exe``. A directory entry (a name ending ``/``,
no bytes) is structure: it is judged for its name and counted, and nothing is unpacked from it.
A name decides nothing but a member's kind: the content is judged by the PDF envelope, so a ZIP
named ``.pdf`` is a PDF that fails it.

The name rules are the portal reader's (:func:`~auditmanager.ingest.bundle_archive.is_unsafe_name`:
absolute, drive-letter, backslash, ``..``) applied to the raw bytes **and to the name a reader
would show**, which an Info-ZIP Unicode Path field can set to anything; a name is also unique
after case folding and NFC (:func:`~auditmanager.ingest.bundle_archive.duplicate_key`). Two members
of different folders may share a base name: a name is never an identity.
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
SET_MAX_ENTRIES: Final[int] = 1_000
#: ADR-0025 decision 12: the uncompressed bytes of a set over all its levels.
SET_TOTAL_BYTES: Final[int] = 2 * GiB
#: One member: the existing envelope's bound for a PDF.
SET_MEMBER_BYTES: Final[int] = MAX_BYTES
#: The ratio of a member and of an archive: the portal reader's.
SET_MAX_RATIO: Final[int] = MAX_RATIO
#: The central directory the reader will load, whatever its entries claim.
SET_DIRECTORY_BYTES: Final[int] = 4 * MiB
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

    __slots__ = ("archives_allowed", "files_required", "entries_seen")

    def __init__(self, *, archives_allowed: bool, files_required: bool) -> None:
        self.archives_allowed = archives_allowed
        self.files_required = files_required
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
            # it is held to the same rule, so a hint can never be a traversal.
            shown = decode_display_name(name, entry.flags, entry.extra)
            if is_unsafe_name(shown.encode("utf-8")):
                raise refuse_set("comparison_zip_member_name")
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
        if self.files_required and not chosen:
            raise refuse_set("comparison_zip_empty")
        return chosen
