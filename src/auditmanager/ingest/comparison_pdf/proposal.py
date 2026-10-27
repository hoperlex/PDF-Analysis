"""The grouping proposal: which files are versions of one drawing set, in what order, with which labels.

Pure rules, no database and no PDF (`ORIGINAL-VERSION-COMPARISON-INVENTORY.md` section 3.2 items 3 to 5, and
ADR-0025 decisions 10 and 16). Everything this module returns is a **proposal**: the user confirms the
membership, the order, the labels, the stage and the section of every set
(:func:`~auditmanager.ingest.comparison_pdf.service.confirm_set`), and nothing becomes a version before that.

**Grouping.** Files are grouped by the designation their stamps carry (the «шифр»: metadata, never an identity);
a file whose stamps carry none is grouped by what its name hints at (its folder, else its base name:
:mod:`.names`), and its set says so (``no_stamp_found``). A name never *overrides* a designation: two files with
the same designation are one set whatever they are called, and two files with different designations are two
sets whatever they are called.

**Order.** Ascending by the file's highest «Изм.», then its latest release date, then the number in its file
name, then the name itself (the original's ``store.proposal``); a file with no «Изм.» sorts before one with
«Изм.0». The file identity is the last tie-break, so the proposal is a function of its input.

**Warnings** (a closed vocabulary, the contract's ``ComparisonProposalWarning``): ``designations_differ`` (a
file's own sheets carry two designations), ``order_disagrees_with_file_numbers`` (the proposed order is not the
order of the numbers in the names, when at least two files have one), ``duplicate_revision_number`` (two files
state the same «Изм.»), ``no_stamp_found`` (the set is grouped by name: no file states a designation) and
``scan_without_text`` (a file has pages with no text layer and is compared as an image only).

**Labels** are the original's suggestion (``V{n} Изм.{N} {date}``); the user edits them.
"""

from __future__ import annotations

import unicodedata
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Final

from .names import NameHint, group_key
from .stamp import FileStamp

__all__ = [
    "FileEntry",
    "ProposedFile",
    "SetProposal",
    "WARNINGS",
    "fold_designation",
    "grouping_key",
    "propose_set",
    "suggest_label",
]

#: The contract's ``ComparisonProposalWarning`` values, in the order a proposal lists them.
WARNINGS: Final[tuple[str, ...]] = (
    "designations_differ",
    "order_disagrees_with_file_numbers",
    "duplicate_revision_number",
    "no_stamp_found",
    "scan_without_text",
)
MAX_LABEL: Final[int] = 80


@dataclass(frozen=True, slots=True)
class FileEntry:
    """One verified file as the proposal reads it."""

    file_id: str
    display_name: str
    stamp: FileStamp
    hint: NameHint


@dataclass(frozen=True, slots=True)
class ProposedFile:
    file_id: str
    position: int
    version_label: str


@dataclass(frozen=True, slots=True)
class SetProposal:
    """The proposal for one set: the files in order, and what the reader noticed."""

    designation: str | None
    project_stage: str | None
    section_code: str | None
    files: tuple[ProposedFile, ...]
    warnings: tuple[str, ...]


def fold_designation(designation: str) -> str:
    """The comparison form of a designation or a title: NFKC, upper case, single spaces."""
    return " ".join(unicodedata.normalize("NFKC", designation).upper().split())


_folded = fold_designation


def grouping_key(stamp: FileStamp, hint: NameHint) -> str:
    """The key files share when they are one set: the designation, else what the name hints at.

    The two kinds are prefixed, so a designation can never collide with a base name.
    """
    if stamp.designation:
        return f"designation:{_folded(stamp.designation)}"
    return group_key(hint)


def _order_key(entry: FileEntry) -> tuple[int, date, int, str, str]:
    stamp, hint = entry.stamp, entry.hint
    return (
        -1 if stamp.revision_number is None else stamp.revision_number,
        stamp.release_date or date.min,
        -1 if hint.file_number is None else hint.file_number,
        hint.file_name.casefold(),
        entry.file_id,
    )


def suggest_label(position: int, stamp: FileStamp) -> str:
    """``V{position} Изм.{N} {дд.мм.гггг}``, each part only when the stamps state it."""
    parts = [f"V{position}"]
    if stamp.revision_number is not None:
        parts.append(f"Изм.{stamp.revision_number}")
    if stamp.release_date is not None:
        parts.append(stamp.release_date.strftime("%d.%m.%Y"))
    return " ".join(parts)[:MAX_LABEL]


def _most_common(values: Sequence[str]) -> str | None:
    """The single most common value; ``None`` for no value or a tie for first place."""
    counts = Counter(value for value in values if value)
    if not counts:
        return None
    (top, top_count), *rest = counts.most_common()
    return top if not rest or rest[0][1] < top_count else None


def propose_set(entries: Sequence[FileEntry]) -> SetProposal:
    """The proposal for the files of one set. ``entries`` is every verified file of it, in any order."""
    if not entries:
        raise ValueError("a set has at least one file")
    ordered = sorted(entries, key=_order_key)
    designations = [entry.stamp.designation for entry in ordered if entry.stamp.designation]
    designation = _most_common([_folded(item) for item in designations])
    if designation is not None:
        # Show the spelling the files carry, not the folded key.
        designation = next(item for item in designations if _folded(item) == designation)
    stage = _most_common([entry.stamp.project_stage or "" for entry in ordered])
    section = _most_common([entry.stamp.section_code or "" for entry in ordered])

    warnings: set[str] = set()
    if any(entry.stamp.designations_differ for entry in ordered):
        warnings.add("designations_differ")
    numbered = [entry for entry in ordered if entry.hint.file_number is not None]
    if len(numbered) >= 2 and [entry.file_id for entry in numbered] != [
        entry.file_id for entry in sorted(numbered, key=lambda item: (item.hint.file_number, item.file_id))
    ]:
        warnings.add("order_disagrees_with_file_numbers")
    revisions = [entry.stamp.revision_number for entry in ordered if entry.stamp.revision_number is not None]
    if len(revisions) != len(set(revisions)):
        warnings.add("duplicate_revision_number")
    if designation is None:
        warnings.add("no_stamp_found")
    if any(entry.stamp.textless_pages for entry in ordered):
        warnings.add("scan_without_text")

    return SetProposal(
        designation=designation,
        project_stage=stage,
        section_code=section,
        files=tuple(
            ProposedFile(entry.file_id, position, suggest_label(position, entry.stamp))
            for position, entry in enumerate(ordered, start=1)
        ),
        warnings=tuple(name for name in WARNINGS if name in warnings),
    )
