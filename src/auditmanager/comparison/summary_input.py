"""Bounded input for a future version-comparison summary.

The raw differences are reverified before projection. Equal lines may be left
out of a proposed summary input, but every approved sheet and its raw evidence
digest remain visible. This value is not an AI result or an approved artifact.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Sequence

from auditmanager.comparison.raw_evidence_seal import (
    RawEvidenceSeal,
    RawEvidenceSealRefused,
    seal_raw_version_evidence,
)
from auditmanager.comparison.raw_text import RawTextDiff
from auditmanager.comparison.version_reader import OrderedVersionPair

ALGORITHM = "approved-sheet-summary-input-v1"
MAX_CHANGED_CHARACTERS = 100_000
MAX_CHANGED_LINES = 1_000
MAX_CHANGED_HUNKS = 256


class SummaryInputRefused(ValueError):
    """The supplied raw artifact cannot yield one complete bounded input."""


@dataclass(frozen=True, slots=True)
class SummaryChange:
    tag: str
    source_start: int
    source_end: int
    target_start: int
    target_end: int
    source_lines: tuple[str, ...]
    target_lines: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SummarySheet:
    sheet_link_id: str
    source_page_number: int
    target_page_number: int
    raw_evidence_sha256: str
    changes: tuple[SummaryChange, ...]


@dataclass(frozen=True, slots=True)
class VersionSummaryInput:
    algorithm: str
    comparison_id: str
    source_version_uid: str
    target_version_uid: str
    link_revision: int
    raw_seal_sha256: str
    sheets: tuple[SummarySheet, ...]
    input_sha256: str


def prepare_version_summary_input(
    *,
    version_pair: OrderedVersionPair,
    raw_diffs: Sequence[RawTextDiff],
    raw_seal: RawEvidenceSeal,
) -> VersionSummaryInput:
    """Project changed lines after rechecking the complete raw evidence seal.

    An empty ``changes`` tuple on a sheet means that its approved pages are
    identical. No input is shortened to fit the budget; an overrun refuses.
    """
    if not isinstance(raw_seal, RawEvidenceSeal):
        raise SummaryInputRefused("raw_seal_invalid")
    try:
        expected = seal_raw_version_evidence(
            version_pair=version_pair,
            comparison_id=raw_seal.comparison_id,
            link_revision=raw_seal.link_revision,
            raw_diffs=raw_diffs,
        )
    except RawEvidenceSealRefused as error:
        raise SummaryInputRefused(str(error)) from None
    if expected != raw_seal:
        raise SummaryInputRefused("raw_seal_mismatch")

    changed_characters = 0
    changed_lines = 0
    changed_hunks = 0
    sheets: list[SummarySheet] = []
    for diff in sorted(raw_diffs, key=lambda item: (item.source_page_number, item.sheet_link_id)):
        changes: list[SummaryChange] = []
        for change in diff.changes:
            if change.tag == "equal":
                continue
            changed_characters += sum(map(len, change.source_lines))
            changed_characters += sum(map(len, change.target_lines))
            changed_lines += len(change.source_lines) + len(change.target_lines)
            changed_hunks += 1
            if (
                changed_characters > MAX_CHANGED_CHARACTERS
                or changed_lines > MAX_CHANGED_LINES
                or changed_hunks > MAX_CHANGED_HUNKS
            ):
                raise SummaryInputRefused("changed_input_too_large")
            changes.append(SummaryChange(
                change.tag,
                change.source_start,
                change.source_end,
                change.target_start,
                change.target_end,
                change.source_lines,
                change.target_lines,
            ))
        sheets.append(SummarySheet(
            diff.sheet_link_id,
            diff.source_page_number,
            diff.target_page_number,
            diff.evidence_sha256,
            tuple(changes),
        ))

    body = {
        "algorithm": ALGORITHM,
        "comparison_id": expected.comparison_id,
        "source_version_uid": expected.source_version_uid,
        "target_version_uid": expected.target_version_uid,
        "link_revision": expected.link_revision,
        "raw_seal_sha256": expected.seal_sha256,
        "sheets": [
            {
                "sheet_link_id": sheet.sheet_link_id,
                "source_page_number": sheet.source_page_number,
                "target_page_number": sheet.target_page_number,
                "raw_evidence_sha256": sheet.raw_evidence_sha256,
                "changes": [
                    {
                        "tag": change.tag,
                        "source_start": change.source_start,
                        "source_end": change.source_end,
                        "target_start": change.target_start,
                        "target_end": change.target_end,
                        "source_lines": change.source_lines,
                        "target_lines": change.target_lines,
                    }
                    for change in sheet.changes
                ],
            }
            for sheet in sheets
        ],
    }
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return VersionSummaryInput(
        ALGORITHM,
        expected.comparison_id,
        expected.source_version_uid,
        expected.target_version_uid,
        expected.link_revision,
        expected.seal_sha256,
        tuple(sheets),
        digest,
    )


__all__ = [
    "SummaryChange",
    "SummaryInputRefused",
    "SummarySheet",
    "VersionSummaryInput",
    "prepare_version_summary_input",
]
