"""The read model of one served version comparison (`W59-VERSION-COMPARE-01`).

Everything here is computed on request from immutable inputs -- two published
versions, their persisted classifications and one published run of each. Every
pairing and every finding label is a *proposal*: it approves no SheetLink, matches
no finding and records no decision. The raw line differences are deterministic and
bound by digest; no AI layer produces or edits any value in this model.

The one stored layer beside it (`COMPARE-PERSISTED-SUMMARY-01`) is an expert's
approval of a sheet pairing: ``VersionComparison.approved_pairs`` lists the active
approvals of the pair and, for approved pairs only, their deterministic differences,
sealed by ``raw_evidence_seal``. It is read from ``comparison_sheet_link`` and never
produced by a proposal.

The vocabularies below are closed. The API boundary restates them as enums, so a
new value is a contract change rather than a string that slips through.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

#: ``version``: the same explicit stage and section on both versions (W59). ``stage``: a
#: ``P`` source and an ``R`` target of the same set and section (the W62 П/Р slice).
MODE_VERSION: Final[str] = "version"
MODE_STAGE: Final[str] = "stage"
MODES: Final[tuple[str, ...]] = (MODE_VERSION, MODE_STAGE)

OUTCOME_COMPARED: Final[str] = "compared"
OUTCOME_REFUSED: Final[str] = "refused"

SIDE_SOURCE: Final[str] = "source"
SIDE_TARGET: Final[str] = "target"

#: Why a pair is not compared. Version facts first, then classification, then the
#: published analysis each side needs.
REFUSAL_REASONS: Final[tuple[str, ...]] = (
    "same_version",
    "version_not_found",
    "different_set",
    "foreign_project",
    "version_not_published",
    "version_order_invalid",
    "stage_unclassified",
    "section_unconfirmed",
    "project_stage_mismatch",
    "confirmed_section_mismatch",
    "stage_pair_invalid",
    "analysis_missing",
    "run_not_of_version",
    "run_not_published",
    "text_unavailable",
    "text_too_large",
)

SHEET_UNCHANGED: Final[str] = "unchanged"
SHEET_CHANGED: Final[str] = "changed"
SHEET_REMOVED: Final[str] = "removed"
SHEET_ADDED: Final[str] = "added"
SHEET_STATUSES: Final[tuple[str, ...]] = (
    SHEET_UNCHANGED, SHEET_CHANGED, SHEET_REMOVED, SHEET_ADDED,
)

PAIRING_EXACT_TEXT: Final[str] = "exact_text"
PAIRING_SIMILAR_TEXT: Final[str] = "similar_text"

DIFF_COMPUTED: Final[str] = "computed"
DIFF_TOO_LARGE: Final[str] = "too_large"

FINDINGS_COMPARED: Final[str] = "compared"
FINDINGS_UNAVAILABLE: Final[str] = "unavailable"
FINDINGS_OVER_LIMIT: Final[str] = "findings_over_limit"

#: The state of the approved pairs' raw evidence (`COMPARE-PERSISTED-SUMMARY-01`). ``none``: no
#: active approval. ``sealed``: every approved page still has the digest the expert saw, the raw
#: differences were recomputed and their seal equals the stored one. ``text_changed``: a page's
#: text is no longer the approved one, so no difference is served for any pair. ``seal_changed``:
#: the texts are as approved but the recomputed seal differs from the stored one. ``too_large``: the
#: differences exceed the bounds of one response; none is truncated, none is served.
EVIDENCE_NONE: Final[str] = "none"
EVIDENCE_SEALED: Final[str] = "sealed"
EVIDENCE_TEXT_CHANGED: Final[str] = "text_changed"
EVIDENCE_SEAL_CHANGED: Final[str] = "seal_changed"
EVIDENCE_TOO_LARGE: Final[str] = "too_large"
EVIDENCE_STATES: Final[tuple[str, ...]] = (
    EVIDENCE_NONE, EVIDENCE_SEALED, EVIDENCE_TEXT_CHANGED, EVIDENCE_SEAL_CHANGED,
    EVIDENCE_TOO_LARGE,
)

LINK_VERIFIED: Final[str] = "verified"
LINK_TEXT_CHANGED: Final[str] = "text_changed"
LINK_STATES: Final[tuple[str, ...]] = (LINK_VERIFIED, LINK_TEXT_CHANGED)

PROPOSAL_UNCHANGED: Final[str] = "unchanged"
PROPOSAL_PROBABLY_FIXED: Final[str] = "probably_fixed"
PROPOSAL_UNDETERMINED: Final[str] = "undetermined"
PROPOSAL_NEW: Final[str] = "new"
PROPOSAL_KINDS: Final[tuple[str, ...]] = (
    PROPOSAL_UNCHANGED, PROPOSAL_PROBABLY_FIXED, PROPOSAL_UNDETERMINED, PROPOSAL_NEW,
)

#: What a finding proposal rests on.
BASIS_EXACT_MATCH: Final[str] = "exact_issue_and_quotes"
BASIS_QUOTES_ABSENT: Final[str] = "quotes_absent_from_paired_sheets"
BASIS_QUOTE_PRESENT: Final[str] = "quote_still_on_paired_sheet"
BASIS_SHEET_UNPAIRED: Final[str] = "evidence_sheet_unpaired"
BASIS_EVIDENCE_OVER_LIMIT: Final[str] = "evidence_over_limit"
BASIS_NO_SOURCE_MATCH: Final[str] = "no_exact_source_match"
PROPOSAL_BASES: Final[tuple[str, ...]] = (
    BASIS_EXACT_MATCH, BASIS_QUOTES_ABSENT, BASIS_QUOTE_PRESENT,
    BASIS_SHEET_UNPAIRED, BASIS_EVIDENCE_OVER_LIMIT, BASIS_NO_SOURCE_MATCH,
)


@dataclass(frozen=True, slots=True)
class ComparisonRefusal:
    reason: str
    #: ``source`` or ``target`` when the reason belongs to one side, else ``None``.
    side: str | None


@dataclass(frozen=True, slots=True)
class ComparedVersion:
    """One side's facts, as far as they were established before any refusal."""

    version_uid: str
    version_ordinal: int
    page_count: int
    sha256: str
    project_stage: str | None
    section_code: str | None
    run_id: str | None
    text_layer_sha256: str | None


@dataclass(frozen=True, slots=True)
class SheetPairing:
    """One sheet of either version and its proposed counterpart, if any.

    ``unchanged`` is an exact-text pair, ``changed`` a similar-text pair,
    ``removed`` a source page and ``added`` a target page with no candidate.
    ``textless`` marks a present page whose text is blank: it cannot be paired
    by text and needs an expert's eye, not a guess.
    """

    status: str
    source_page_number: int | None
    target_page_number: int | None
    pairing_basis: str | None
    similarity_permille: int | None
    shared_line_count: int | None
    suggestion_sha256: str | None
    textless: bool


@dataclass(frozen=True, slots=True)
class DiffHunk:
    """One span of the raw line diff. Line indices are 0-based, end exclusive.

    An ``equal`` span carries its ranges only; its lines are left out of the
    response, and ``SheetDiff.evidence_sha256`` still binds them.
    """

    tag: str
    source_start: int
    source_end: int
    target_start: int
    target_end: int
    source_lines: tuple[str, ...]
    target_lines: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SheetDiff:
    status: str
    source_page_number: int | None
    target_page_number: int | None
    outcome: str
    #: The per-page ceiling that was exceeded, when ``outcome`` is ``too_large``.
    too_large_reason: str | None
    source_line_count: int | None
    target_line_count: int | None
    added_line_count: int | None
    removed_line_count: int | None
    hunks: tuple[DiffHunk, ...]
    evidence_sha256: str | None


@dataclass(frozen=True, slots=True)
class SheetDiffPage:
    """One page of the differing sheets, in ``sheets`` order.

    ``next_offset`` is ``None`` on the last page. A page can hold fewer than
    ``limit`` items when the next sheet would cross the response's character
    budget; it then names the offset to continue from, it never truncates.
    """

    offset: int
    limit: int
    total: int
    next_offset: int | None
    items: tuple[SheetDiff, ...]


@dataclass(frozen=True, slots=True)
class FindingRef:
    finding_uid: str
    category: str
    finding_text: str
    page_numbers: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class FindingProposal:
    kind: str
    basis: str
    source_finding: FindingRef | None
    target_finding: FindingRef | None
    #: The digest of an exact match proposal; ``None`` for one-sided labels.
    proposal_sha256: str | None


@dataclass(frozen=True, slots=True)
class FindingComparison:
    status: str
    unavailable_reason: str | None
    source_finding_count: int
    target_finding_count: int
    proposals: tuple[FindingProposal, ...]


@dataclass(frozen=True, slots=True)
class ApprovedDiffHunk:
    """One span of an approved pair's raw line diff (0-based, end exclusive).

    A changed span carries ``hunk_id`` (``<sheet_link_id>:<n>``, ``n`` counting the sheet's
    non-equal spans from 0); an ``equal`` span carries its ranges only and no id.
    """

    tag: str
    source_start: int
    source_end: int
    target_start: int
    target_end: int
    source_lines: tuple[str, ...]
    target_lines: tuple[str, ...]
    hunk_id: str | None


@dataclass(frozen=True, slots=True)
class ApprovedSheetDiff:
    """The deterministic differences of one approved pair (``raw_text.diff_approved_pairs``)."""

    source_line_count: int
    target_line_count: int
    added_line_count: int
    removed_line_count: int
    hunks: tuple[ApprovedDiffHunk, ...]
    #: ``RawTextDiff.evidence_sha256``: binds the complete diff, equal lines included.
    evidence_sha256: str


@dataclass(frozen=True, slots=True)
class ApprovedSheetPair:
    """One active approval of a source page against a target page."""

    sheet_link_id: str
    source_page_number: int
    target_page_number: int
    state: str
    #: The proposal the expert confirmed (``SheetPairing.suggestion_sha256``).
    suggestion_sha256: str
    approved_by_label: str
    approved_at: datetime
    #: The link revision of the approval itself.
    link_revision: int
    #: Present only when the whole set is ``sealed``.
    diff: ApprovedSheetDiff | None


@dataclass(frozen=True, slots=True)
class ApprovedSheetPairs:
    """The approved pairs of the compared pair and their evidence, or why it is withheld."""

    #: The current link revision of the comparison; ``None`` when nothing was ever approved.
    link_revision: int | None
    evidence_state: str
    #: The recomputed ``raw_evidence_seal`` of the active set; ``None`` unless ``sealed``.
    raw_evidence_seal_sha256: str | None
    items: tuple[ApprovedSheetPair, ...]


@dataclass(frozen=True, slots=True)
class VersionComparison:
    project_uid: str
    document_uid: str
    source_version_uid: str
    target_version_uid: str
    mode: str
    outcome: str
    refusal: ComparisonRefusal | None
    source: ComparedVersion | None
    target: ComparedVersion | None
    #: Binds both versions, both runs, both text layers and every sheet suggestion.
    comparison_sha256: str | None
    sheets: tuple[SheetPairing, ...]
    sheet_diffs: SheetDiffPage | None
    findings: FindingComparison | None
    #: `COMPARE-PERSISTED-SUMMARY-01`. ``None`` for a refused comparison, and for a service built
    #: without the approved-link reader (the unit tests of the proposals).
    approved_pairs: ApprovedSheetPairs | None = None


__all__ = [
    "ApprovedDiffHunk", "ApprovedSheetDiff", "ApprovedSheetPair", "ApprovedSheetPairs",
    "EVIDENCE_NONE", "EVIDENCE_SEALED", "EVIDENCE_SEAL_CHANGED", "EVIDENCE_STATES",
    "EVIDENCE_TEXT_CHANGED", "EVIDENCE_TOO_LARGE", "LINK_STATES", "LINK_TEXT_CHANGED",
    "LINK_VERIFIED",
    "BASIS_EVIDENCE_OVER_LIMIT", "BASIS_EXACT_MATCH", "BASIS_NO_SOURCE_MATCH",
    "BASIS_QUOTES_ABSENT", "BASIS_QUOTE_PRESENT", "BASIS_SHEET_UNPAIRED",
    "ComparedVersion", "ComparisonRefusal", "DIFF_COMPUTED", "DIFF_TOO_LARGE",
    "DiffHunk", "FINDINGS_COMPARED", "FINDINGS_OVER_LIMIT", "FINDINGS_UNAVAILABLE",
    "FindingComparison", "FindingProposal", "FindingRef", "MODES", "MODE_STAGE",
    "MODE_VERSION", "OUTCOME_COMPARED",
    "OUTCOME_REFUSED", "PAIRING_EXACT_TEXT", "PAIRING_SIMILAR_TEXT",
    "PROPOSAL_BASES", "PROPOSAL_KINDS", "PROPOSAL_NEW", "PROPOSAL_PROBABLY_FIXED",
    "PROPOSAL_UNCHANGED", "PROPOSAL_UNDETERMINED", "REFUSAL_REASONS",
    "SHEET_ADDED", "SHEET_CHANGED", "SHEET_REMOVED", "SHEET_STATUSES",
    "SHEET_UNCHANGED", "SIDE_SOURCE", "SIDE_TARGET", "SheetDiff", "SheetDiffPage",
    "SheetPairing", "VersionComparison",
]
