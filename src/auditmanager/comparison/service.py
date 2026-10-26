"""The served comparison of two versions of one document set (`W59-VERSION-COMPARE-01`).

One read, in the caller's session, composes the prepared W59 modules:

1. :func:`~auditmanager.comparison.version_reader.read_ordered_version_pair` proves
   that both versions are published versions of the named set in the named
   project, ordered source-before-target;
2. :func:`~auditmanager.comparison.version_section_pair.prepare_same_section_version_pair`
   requires the same explicit ``P``/``R`` stage and the same confirmed section on
   both, read from persisted classifications through :class:`VersionClassificationReader`
   (``mode=version``); with ``mode=stage``,
   :func:`~auditmanager.comparison.version_section_pair.prepare_stage_section_version_pair`
   requires a ``P`` source, an ``R`` target and the same section instead (the W62 П/Р
   slice) -- the rest of the comparison is identical;
3. each side's newest ``published`` run (or the run the caller names) supplies the
   saved page text and the published findings through :class:`VersionAnalysisReader`;
4. :func:`~auditmanager.comparison.sheet_match_suggestions.suggest_sheet_pairs`
   proposes sheet pairs, :func:`~auditmanager.comparison.raw_text.diff_page_lines`
   diffs them and
   :func:`~auditmanager.comparison.finding_match_suggestions.suggest_finding_matches_on_sheet_suggestions`
   proposes finding matches across them.

5. when the service was built with an approved-link reader (the composition root always does,
   `COMPARE-PERSISTED-SUMMARY-01`), the stored approvals of the pair are read in the same session
   and :func:`~auditmanager.comparison.approved_evidence.project_approved_pairs` recomputes, for
   the approved pairs only, their deterministic differences and the seal that binds them. The
   proposals above are never promoted to an approval by this read.

A failed precondition is an explicit :class:`~auditmanager.comparison.read_model.ComparisonRefusal`
in the result, never a relabelled pair and never a fallback to another version,
stage, section or run. A stored fact that contradicts its own constraints is a
:class:`ComparisonIntegrityError`. Nothing is written: no SheetLink, no finding
match, no decision and no AI artifact. The ports are this context's own
protocols; the composition root adapts the documents, runs, analysis, storage
and findings contexts to them.

**Bounds for 500-page versions.** The sheet list is at most one row per page of
both versions (1,000 rows). Line diffs are served a page at a time: at most
``MAX_DIFF_LIMIT`` sheets and ``MAX_DIFF_PAGE_CHARACTERS`` changed characters per
response (the first sheet of a page is always served; one sheet is bounded by the
raw-text page ceilings of 200,000 characters and 1,000 lines per side, above which
it is marked ``too_large`` rather than truncated). Equal spans are sent as line
ranges without their text. Finding proposals cover at most
``MAX_FINDINGS_PER_RUN`` findings per side; a larger run is reported
``findings_over_limit``, not cut.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Final, Protocol, runtime_checkable

from sqlalchemy.orm import Session

from auditmanager.comparison.finding_match_suggestions import (
    MAX_EVIDENCE_PER_FINDING,
    MAX_FINDINGS_PER_RUN,
    FindingForMatch,
    FindingMatchSuggestionRefused,
    FindingQuote,
    SuggestedSheetPair,
    suggest_finding_matches_on_sheet_suggestions,
)
from auditmanager.comparison.approved_evidence import project_approved_pairs
from auditmanager.comparison.raw_text import RawTextDiffRefused, diff_page_lines
from auditmanager.comparison.read_model import (
    BASIS_EVIDENCE_OVER_LIMIT,
    BASIS_EXACT_MATCH,
    BASIS_NO_SOURCE_MATCH,
    BASIS_QUOTE_PRESENT,
    BASIS_QUOTES_ABSENT,
    BASIS_SHEET_UNPAIRED,
    DIFF_COMPUTED,
    DIFF_TOO_LARGE,
    FINDINGS_COMPARED,
    FINDINGS_OVER_LIMIT,
    FINDINGS_UNAVAILABLE,
    MODE_STAGE,
    MODE_VERSION,
    MODES,
    OUTCOME_COMPARED,
    OUTCOME_REFUSED,
    PAIRING_EXACT_TEXT,
    PAIRING_SIMILAR_TEXT,
    PROPOSAL_KINDS,
    PROPOSAL_NEW,
    PROPOSAL_PROBABLY_FIXED,
    PROPOSAL_UNCHANGED,
    PROPOSAL_UNDETERMINED,
    SHEET_ADDED,
    SHEET_CHANGED,
    SHEET_REMOVED,
    SHEET_UNCHANGED,
    SIDE_SOURCE,
    SIDE_TARGET,
    ComparedVersion,
    ComparisonRefusal,
    DiffHunk,
    FindingComparison,
    FindingProposal,
    FindingRef,
    SheetDiff,
    SheetDiffPage,
    SheetPairing,
    VersionComparison,
)
from auditmanager.comparison.sheet_links import ApprovedLinkReader
from auditmanager.comparison.sheet_match_suggestions import (
    EXACT_PAIR_ALGORITHM,
    SheetMatchSuggestionRefused,
    SheetPairSuggestion,
    suggest_sheet_pairs,
)
from auditmanager.comparison.version_reader import (
    OrderedVersionPair,
    VersionFacts,
    VersionPairRefused,
    read_ordered_version_pair,
)
from auditmanager.comparison.version_section_pair import (
    SuppliedVersionClassification,
    VersionSectionPairRefused,
    prepare_same_section_version_pair,
    prepare_stage_section_version_pair,
)
from auditmanager.shared.identity import (
    FindingObservationId,
    FindingUid,
    IdentityError,
    RunId,
)

COMPARISON_ALGORITHM: Final[str] = "served-version-comparison-v1"
SHEET_DIFF_ALGORITHM: Final[str] = "suggested-sheet-lines-v1"
#: The success terminal of ``audit_run`` (there is no ``succeeded`` run state).
RUN_STATE_PUBLISHED: Final[str] = "published"
DEFAULT_DIFF_LIMIT: Final[int] = 10
MAX_DIFF_LIMIT: Final[int] = 25
MAX_DIFF_PAGE_CHARACTERS: Final[int] = 500_000
_PROJECT_STAGES: Final[frozenset[str]] = frozenset({"P", "R"})


class ComparisonRequestInvalid(ValueError):
    """A request value the API boundary should already have refused."""


class ComparisonIntegrityError(RuntimeError):
    """A stored fact or port answer contradicts its own constraints."""


@dataclass(frozen=True, slots=True)
class RunCandidate:
    run_id: str
    state: str


@dataclass(frozen=True, slots=True)
class SavedPageText:
    """The verified ``prepared.text_layer`` of one run, as page number to text."""

    run_id: str
    text_layer_sha256: str
    pages: Mapping[int, str]


@dataclass(frozen=True, slots=True)
class FindingEvidenceSnapshot:
    page_number: int
    quote: str


@dataclass(frozen=True, slots=True)
class FindingSnapshot:
    """One published finding's canonical observation and its evidence quotes."""

    finding_uid: str
    finding_observation_id: str
    category: str
    finding_text: str
    evidence: tuple[FindingEvidenceSnapshot, ...]


@runtime_checkable
class VersionClassificationReader(Protocol):
    """The persisted, expert-confirmed stage and section of one version."""

    def read_classification(
        self, session: Session, *, version_uid: str
    ) -> SuppliedVersionClassification | None:
        """The stored row, or ``None`` for an unclassified version. Never inferred."""


@runtime_checkable
class VersionAnalysisReader(Protocol):
    """Runs, saved page text and published findings of one version."""

    def runs_newest_first(self, session: Session, *, version_uid: str) -> Sequence[RunCandidate]:
        """Every run of the version, newest first."""

    def saved_page_text(
        self, session: Session, *, run_id: str, version: VersionFacts
    ) -> SavedPageText | None:
        """The run's verified text layer for every page, or ``None`` when it has none.

        A layer that exists but fails its recorded digest or shape must raise,
        never answer ``None``.
        """

    def published_findings(self, session: Session, *, run_id: str) -> Sequence[FindingSnapshot]:
        """The run's published findings. An ungrounded observation is never one."""


@dataclass(frozen=True, slots=True)
class CurrentFindingProposals:
    """A comparison recomputed for a command, and each compared finding's observation.

    ``observations`` maps ``source`` and ``target`` to ``finding_uid`` ->
    ``finding_observation_id`` of that side's run; both are empty for a refusal.
    """

    comparison: VersionComparison
    observations: Mapping[str, Mapping[str, str]]


@dataclass(frozen=True, slots=True)
class CurrentComparison:
    """A comparison recomputed for the pairing commands: the proposals and the texts behind them.

    ``comparison`` carries the sheet proposals (no diff page, no finding proposals, no approved
    pairs). ``pair``, ``suggestions`` and both page maps are those the proposals were built from,
    so a command can prove that the pair an expert confirmed is still the one proposed and can
    seal the approved set over exactly this text. For a refusal ``pair`` is ``None`` and the rest
    is empty.
    """

    comparison: VersionComparison
    pair: OrderedVersionPair | None
    suggestions: tuple[SheetPairSuggestion, ...]
    source_pages: Mapping[int, str]
    target_pages: Mapping[int, str]


@dataclass(frozen=True, slots=True)
class ComparisonRequest:
    project_uid: str
    document_uid: str
    source_version_uid: str
    target_version_uid: str
    source_run_id: str | None = None
    target_run_id: str | None = None
    diff_offset: int = 0
    diff_limit: int = DEFAULT_DIFF_LIMIT
    mode: str = MODE_VERSION


_VERSION_REFUSALS: Final[Mapping[str, str]] = {
    "same_version": "same_version",
    "version_pair_incomplete": "version_not_found",
    "version_set_mismatch": "different_set",
    "version_project_mismatch": "foreign_project",
    "version_not_published": "version_not_published",
    "version_order_invalid": "version_order_invalid",
}
_REQUEST_IDENTITY_REFUSALS: Final[frozenset[str]] = frozenset({
    "project_uid_invalid", "document_uid_invalid",
    "source_version_uid_invalid", "target_version_uid_invalid",
})
_SECTION_REFUSALS: Final[Mapping[str, tuple[str, str | None]]] = {
    "source_stage_unclassified": ("stage_unclassified", SIDE_SOURCE),
    "target_stage_unclassified": ("stage_unclassified", SIDE_TARGET),
    "source_section_unconfirmed": ("section_unconfirmed", SIDE_SOURCE),
    "target_section_unconfirmed": ("section_unconfirmed", SIDE_TARGET),
    "project_stage_mismatch": ("project_stage_mismatch", None),
    "confirmed_section_mismatch": ("confirmed_section_mismatch", None),
    "stage_pair_invalid": ("stage_pair_invalid", None),
}


class _Refused(Exception):
    """Internal control flow: one precondition failed with an explicit reason."""

    def __init__(self, reason: str, side: str | None = None) -> None:
        super().__init__(reason)
        self.refusal = ComparisonRefusal(reason, side)


@dataclass(frozen=True, slots=True)
class _Side:
    facts: VersionFacts
    run_id: str
    text: SavedPageText
    findings: tuple[FindingSnapshot, ...]


@dataclass(frozen=True, slots=True)
class _Prepared:
    """Both sides of a pair that passed every precondition, and its sheet suggestions."""

    pair: OrderedVersionPair
    progress: dict[str, ComparedVersion]
    source: _Side
    target: _Side
    suggestions: tuple[SheetPairSuggestion, ...]


def _assemble(
    request: ComparisonRequest, prepared: _Prepared, *, with_diff_page: bool,
) -> VersionComparison:
    pair, progress, suggestions = prepared.pair, prepared.progress, prepared.suggestions
    source, target = prepared.source, prepared.target
    sheets = _sheet_rows(suggestions, source, target)
    return VersionComparison(
        pair.project_uid, pair.document_uid,
        source.facts.version_uid, target.facts.version_uid,
        request.mode, OUTCOME_COMPARED, None,
        progress[SIDE_SOURCE], progress[SIDE_TARGET],
        _comparison_sha256(pair, request.mode, progress, suggestions),
        sheets,
        (
            _diff_page(pair, sheets, source, target, request.diff_offset, request.diff_limit)
            if with_diff_page else None
        ),
        _finding_comparison(pair, suggestions, source, target),
    )


class VersionComparisonService:
    """Compare two explicitly named versions of one set, read-only."""

    def __init__(
        self,
        *,
        classifications: VersionClassificationReader,
        analyses: VersionAnalysisReader,
        section_codes: frozenset[str],
        links: ApprovedLinkReader | None = None,
    ) -> None:
        if not isinstance(section_codes, frozenset) or not section_codes:
            raise ValueError("section_codes must be the sealed, non-empty catalogue")
        self._classifications = classifications
        self._analyses = analyses
        self._section_codes = section_codes
        self._links = links

    def compare(self, session: Session, request: ComparisonRequest) -> VersionComparison:
        """The comparison of ``request``'s pair, or its explicit refusal.

        Every read happens in ``session``; the caller owns the transaction and
        should keep one snapshot across the call.
        """
        _check_request(request)
        prepared = self._prepare(session, request)
        if isinstance(prepared, VersionComparison):
            return prepared
        assembled = _assemble(request, prepared, with_diff_page=True)
        if self._links is None:
            return assembled
        state = self._links.state(
            session,
            source_version_uid=prepared.pair.source.version_uid,
            target_version_uid=prepared.pair.target.version_uid,
        )
        return replace(assembled, approved_pairs=project_approved_pairs(
            pair=prepared.pair, state=state,
            source_pages=prepared.source.text.pages, target_pages=prepared.target.text.pages,
        ))

    def current_comparison(self, session: Session, request: ComparisonRequest) -> CurrentComparison:
        """The sheet proposals and the texts behind them, recomputed now, for a pairing command.

        The same preconditions as :meth:`compare` (a refusal is the same refusal); nothing is
        written and no finding is compared.
        """
        _check_request(request)
        prepared = self._prepare(session, request)
        if isinstance(prepared, VersionComparison):
            return CurrentComparison(prepared, None, (), {}, {})
        pair, source, target = prepared.pair, prepared.source, prepared.target
        return CurrentComparison(
            VersionComparison(
                pair.project_uid, pair.document_uid,
                source.facts.version_uid, target.facts.version_uid,
                request.mode, OUTCOME_COMPARED, None,
                prepared.progress[SIDE_SOURCE], prepared.progress[SIDE_TARGET],
                _comparison_sha256(pair, request.mode, prepared.progress, prepared.suggestions),
                _sheet_rows(prepared.suggestions, source, target), None, None,
            ),
            pair, prepared.suggestions, source.text.pages, target.text.pages,
        )

    def current_finding_proposals(
        self, session: Session, request: ComparisonRequest,
    ) -> CurrentFindingProposals:
        """The same comparison recomputed now, without its diff page, for a command.

        ``comparison`` is exactly what :meth:`compare` answers for ``request`` except
        that ``sheet_diffs`` is ``None`` (the diff page is display, not a precondition);
        a refusal is the same refusal. ``observations`` names each compared finding's
        observation per side, which a decision about that finding must cite. Nothing is
        written.
        """
        _check_request(request)
        prepared = self._prepare(session, request)
        if isinstance(prepared, VersionComparison):
            return CurrentFindingProposals(prepared, {SIDE_SOURCE: {}, SIDE_TARGET: {}})
        return CurrentFindingProposals(
            _assemble(request, prepared, with_diff_page=False),
            {
                label: {item.finding_uid: item.finding_observation_id for item in side.findings}
                for label, side in ((SIDE_SOURCE, prepared.source), (SIDE_TARGET, prepared.target))
            },
        )

    def _prepare(self, session: Session, request: ComparisonRequest) -> VersionComparison | _Prepared:
        """Every precondition and both sides, or the refused comparison itself."""
        progress: dict[str, ComparedVersion] = {}
        try:
            pair = self._version_pair(session, request)
            progress = {
                SIDE_SOURCE: _compared(pair.source),
                SIDE_TARGET: _compared(pair.target),
            }
            stages, section = self._classification(session, pair, request.mode)
            for label in (SIDE_SOURCE, SIDE_TARGET):
                progress[label] = replace(
                    progress[label], project_stage=stages[label], section_code=section,
                )
            run_ids = {
                SIDE_SOURCE: self._run(session, pair.source, request.source_run_id, SIDE_SOURCE),
                SIDE_TARGET: self._run(session, pair.target, request.target_run_id, SIDE_TARGET),
            }
            for label, run_id in run_ids.items():
                progress[label] = replace(progress[label], run_id=run_id)
            texts = {
                label: self._text(session, facts, run_ids[label], label)
                for label, facts in ((SIDE_SOURCE, pair.source), (SIDE_TARGET, pair.target))
            }
            for label, text in texts.items():
                progress[label] = replace(
                    progress[label], text_layer_sha256=text.text_layer_sha256,
                )
            sides = {
                label: _Side(
                    facts, run_ids[label], texts[label],
                    tuple(self._analyses.published_findings(session, run_id=run_ids[label])),
                )
                for label, facts in ((SIDE_SOURCE, pair.source), (SIDE_TARGET, pair.target))
            }
            suggestions = _sheet_suggestions(pair, sides[SIDE_SOURCE], sides[SIDE_TARGET])
        except _Refused as refused:
            return VersionComparison(
                request.project_uid, request.document_uid,
                request.source_version_uid, request.target_version_uid,
                request.mode, OUTCOME_REFUSED, refused.refusal,
                progress.get(SIDE_SOURCE), progress.get(SIDE_TARGET),
                None, (), None, None,
            )
        return _Prepared(pair, progress, sides[SIDE_SOURCE], sides[SIDE_TARGET], suggestions)

    # -- preconditions ---------------------------------------------------------

    @staticmethod
    def _version_pair(session: Session, request: ComparisonRequest) -> OrderedVersionPair:
        try:
            return read_ordered_version_pair(
                session,
                project_uid=request.project_uid,
                document_uid=request.document_uid,
                source_version_uid=request.source_version_uid,
                target_version_uid=request.target_version_uid,
            )
        except VersionPairRefused as refusal:
            reason = str(refusal)
            if reason in _REQUEST_IDENTITY_REFUSALS:
                raise ComparisonRequestInvalid(reason) from None
            if reason in _VERSION_REFUSALS:
                raise _Refused(_VERSION_REFUSALS[reason]) from None
            raise ComparisonIntegrityError(reason) from None

    def _classification(
        self, session: Session, pair: OrderedVersionPair, mode: str,
    ) -> tuple[dict[str, str], str]:
        """Each side's stage and the one shared section, under ``mode``'s stage rule."""
        supplied = {
            label: self._stored_classification(session, facts.version_uid)
            for label, facts in ((SIDE_SOURCE, pair.source), (SIDE_TARGET, pair.target))
        }
        try:
            if mode == MODE_STAGE:
                staged = prepare_stage_section_version_pair(
                    version_pair=pair, source=supplied[SIDE_SOURCE], target=supplied[SIDE_TARGET],
                )
                stages = {SIDE_SOURCE: staged.source_stage, SIDE_TARGET: staged.target_stage}
                return stages, staged.confirmed_section_code
            same = prepare_same_section_version_pair(
                version_pair=pair, source=supplied[SIDE_SOURCE], target=supplied[SIDE_TARGET],
            )
        except VersionSectionPairRefused as refusal:
            reason = str(refusal)
            if reason in _SECTION_REFUSALS:
                raise _Refused(*_SECTION_REFUSALS[reason]) from None
            raise ComparisonIntegrityError(reason) from None
        stages = {SIDE_SOURCE: same.project_stage, SIDE_TARGET: same.project_stage}
        return stages, same.confirmed_section_code

    def _stored_classification(self, session: Session, version_uid: str) -> SuppliedVersionClassification:
        stored = self._classifications.read_classification(session, version_uid=version_uid)
        if stored is None:
            return SuppliedVersionClassification(version_uid, None, None)
        if (
            not isinstance(stored, SuppliedVersionClassification)
            or stored.version_uid != version_uid
            or (stored.project_stage is None) != (stored.confirmed_section_code is None)
            or (stored.project_stage is not None and stored.project_stage not in _PROJECT_STAGES)
            or (
                stored.confirmed_section_code is not None
                and stored.confirmed_section_code not in self._section_codes
            )
        ):
            raise ComparisonIntegrityError("stored_classification_invalid")
        return stored

    def _run(
        self, session: Session, facts: VersionFacts, requested: str | None, side: str,
    ) -> str:
        runs = tuple(self._analyses.runs_newest_first(session, version_uid=facts.version_uid))
        for run in runs:
            if not isinstance(run, RunCandidate) or not isinstance(run.state, str):
                raise ComparisonIntegrityError("run_candidate_invalid")
            try:
                RunId.parse(run.run_id)
            except (IdentityError, TypeError):
                raise ComparisonIntegrityError("run_candidate_invalid") from None
        if requested is not None:
            chosen = next((run for run in runs if run.run_id == requested), None)
            if chosen is None:
                raise _Refused("run_not_of_version", side)
            if chosen.state != RUN_STATE_PUBLISHED:
                raise _Refused("run_not_published", side)
            return chosen.run_id
        newest = next((run for run in runs if run.state == RUN_STATE_PUBLISHED), None)
        if newest is None:
            raise _Refused("analysis_missing", side)
        return newest.run_id

    def _text(self, session: Session, facts: VersionFacts, run_id: str, side: str) -> SavedPageText:
        text = self._analyses.saved_page_text(session, run_id=run_id, version=facts)
        if text is None:
            raise _Refused("text_unavailable", side)
        pages = text.pages if isinstance(text, SavedPageText) else None
        if (
            pages is None
            or text.run_id != run_id
            or not _is_sha256(text.text_layer_sha256)
            or not isinstance(pages, Mapping)
            or set(pages) != set(range(1, facts.page_count + 1))
            or any(not isinstance(value, str) for value in pages.values())
        ):
            raise ComparisonIntegrityError("saved_page_text_invalid")
        return text


# -- request ---------------------------------------------------------------------


def _check_request(request: ComparisonRequest) -> None:
    if not isinstance(request, ComparisonRequest):
        raise ComparisonRequestInvalid("request_invalid")
    if request.mode not in MODES:
        raise ComparisonRequestInvalid("mode_invalid")
    for field, value in (
        ("source_run_id", request.source_run_id), ("target_run_id", request.target_run_id),
    ):
        if value is not None:
            try:
                RunId.parse(value)
            except (IdentityError, TypeError):
                raise ComparisonRequestInvalid(f"{field}_invalid") from None
    if type(request.diff_offset) is not int or request.diff_offset < 0:
        raise ComparisonRequestInvalid("diff_offset_invalid")
    if type(request.diff_limit) is not int or not 1 <= request.diff_limit <= MAX_DIFF_LIMIT:
        raise ComparisonRequestInvalid("diff_limit_invalid")


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str) and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _compared(facts: VersionFacts) -> ComparedVersion:
    return ComparedVersion(
        facts.version_uid, facts.version_ordinal, facts.page_count, facts.sha256,
        None, None, None, None,
    )


def _digest(body: object) -> str:
    return hashlib.sha256(json.dumps(
        body, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


# -- sheets ----------------------------------------------------------------------


def _sheet_suggestions(
    pair: OrderedVersionPair, source: _Side, target: _Side,
) -> tuple[SheetPairSuggestion, ...]:
    try:
        return suggest_sheet_pairs(
            version_pair=pair, source_pages=source.text.pages, target_pages=target.text.pages,
        )
    except SheetMatchSuggestionRefused as refusal:
        reason = str(refusal)
        for side in (SIDE_SOURCE, SIDE_TARGET):
            if reason in (f"{side}_page_too_large", f"{side}_pages_too_large"):
                raise _Refused("text_too_large", side) from None
        raise ComparisonIntegrityError(reason) from None


def _is_textless(text: str) -> bool:
    return not text.strip()


def _sheet_rows(
    suggestions: tuple[SheetPairSuggestion, ...], source: _Side, target: _Side,
) -> tuple[SheetPairing, ...]:
    """Every page of both versions once, in target order with removals in place.

    A removed source page follows the furthest target page reached by any
    paired source page before it, so the list reads like the newer set.
    """
    by_target = {item.target_page_number: item for item in suggestions}
    paired_source = {item.source_page_number: item.target_page_number for item in suggestions}
    keyed: list[tuple[tuple[int, int, int], SheetPairing]] = []
    for number in range(1, target.facts.page_count + 1):
        item = by_target.get(number)
        if item is None:
            keyed.append(((number, 0, 0), SheetPairing(
                SHEET_ADDED, None, number, None, None, None, None,
                _is_textless(target.text.pages[number]),
            )))
            continue
        exact = item.algorithm == EXACT_PAIR_ALGORITHM
        keyed.append(((number, 0, item.source_page_number), SheetPairing(
            SHEET_UNCHANGED if exact else SHEET_CHANGED,
            item.source_page_number, number,
            PAIRING_EXACT_TEXT if exact else PAIRING_SIMILAR_TEXT,
            item.similarity_permille, item.shared_line_count, item.suggestion_sha256, False,
        )))
    anchor = 0
    for number in range(1, source.facts.page_count + 1):
        if number in paired_source:
            anchor = max(anchor, paired_source[number])
            continue
        keyed.append(((anchor, 1, number), SheetPairing(
            SHEET_REMOVED, number, None, None, None, None, None,
            _is_textless(source.text.pages[number]),
        )))
    keyed.sort(key=lambda entry: entry[0])
    return tuple(row for _, row in keyed)


def _diffable(sheet: SheetPairing) -> bool:
    return sheet.status == SHEET_CHANGED or (
        sheet.status in (SHEET_ADDED, SHEET_REMOVED) and not sheet.textless
    )


def _sheet_diff(
    pair: OrderedVersionPair, sheet: SheetPairing, source: _Side, target: _Side,
) -> SheetDiff:
    source_text = (
        "" if sheet.source_page_number is None else source.text.pages[sheet.source_page_number]
    )
    target_text = (
        "" if sheet.target_page_number is None else target.text.pages[sheet.target_page_number]
    )
    try:
        page = diff_page_lines(source_text, target_text)
    except RawTextDiffRefused as refusal:
        return SheetDiff(
            sheet.status, sheet.source_page_number, sheet.target_page_number,
            DIFF_TOO_LARGE, str(refusal), None, None, None, None, (), None,
        )
    added = sum(c.target_end - c.target_start for c in page.changes if c.tag in ("insert", "replace"))
    removed = sum(c.source_end - c.source_start for c in page.changes if c.tag in ("delete", "replace"))
    evidence = _digest({
        "algorithm": SHEET_DIFF_ALGORITHM,
        "project_uid": pair.project_uid,
        "document_uid": pair.document_uid,
        "source_version_uid": pair.source.version_uid,
        "target_version_uid": pair.target.version_uid,
        "source_page_number": sheet.source_page_number,
        "target_page_number": sheet.target_page_number,
        "pairing_suggestion_sha256": sheet.suggestion_sha256,
        "source_sha256": page.source_sha256,
        "target_sha256": page.target_sha256,
        "changes": [
            [c.tag, c.source_start, c.source_end, c.target_start, c.target_end,
             list(c.source_lines), list(c.target_lines)]
            for c in page.changes
        ],
    })
    hunks = tuple(
        DiffHunk(
            c.tag, c.source_start, c.source_end, c.target_start, c.target_end,
            () if c.tag == "equal" else c.source_lines,
            () if c.tag == "equal" else c.target_lines,
        )
        for c in page.changes
    )
    return SheetDiff(
        sheet.status, sheet.source_page_number, sheet.target_page_number,
        DIFF_COMPUTED, None, page.source_line_count, page.target_line_count,
        added, removed, hunks, evidence,
    )


def _changed_characters(diff: SheetDiff) -> int:
    return sum(
        sum(map(len, hunk.source_lines)) + sum(map(len, hunk.target_lines))
        for hunk in diff.hunks
    )


def _diff_page(
    pair: OrderedVersionPair,
    sheets: tuple[SheetPairing, ...],
    source: _Side,
    target: _Side,
    offset: int,
    limit: int,
) -> SheetDiffPage:
    diffable = [sheet for sheet in sheets if _diffable(sheet)]
    items: list[SheetDiff] = []
    characters = 0
    position = offset
    while position < len(diffable) and len(items) < limit:
        diff = _sheet_diff(pair, diffable[position], source, target)
        size = _changed_characters(diff)
        if items and characters + size > MAX_DIFF_PAGE_CHARACTERS:
            break
        items.append(diff)
        characters += size
        position += 1
    return SheetDiffPage(
        offset, limit, len(diffable),
        position if position < len(diffable) else None,
        tuple(items),
    )


def _comparison_sha256(
    pair: OrderedVersionPair,
    mode: str,
    progress: Mapping[str, ComparedVersion],
    suggestions: tuple[SheetPairSuggestion, ...],
) -> str:
    def side(value: ComparedVersion) -> dict[str, object]:
        return {
            "version_uid": value.version_uid,
            "sha256": value.sha256,
            "project_stage": value.project_stage,
            "section_code": value.section_code,
            "run_id": value.run_id,
            "text_layer_sha256": value.text_layer_sha256,
        }

    return _digest({
        "algorithm": COMPARISON_ALGORITHM,
        "mode": mode,
        "project_uid": pair.project_uid,
        "document_uid": pair.document_uid,
        "source": side(progress[SIDE_SOURCE]),
        "target": side(progress[SIDE_TARGET]),
        "sheet_suggestion_sha256s": [item.suggestion_sha256 for item in suggestions],
    })


# -- findings --------------------------------------------------------------------


def _normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).split())


def _for_match(side: _Side, finding: FindingSnapshot) -> FindingForMatch | None:
    """The matcher's input, or ``None`` when the evidence exceeds its per-finding cap.

    Quotes repeated on one page are one coordinate for matching, so they are
    merged before the cap applies; the snapshot itself is not changed.
    """
    if not isinstance(finding, FindingSnapshot) or not isinstance(finding.evidence, tuple):
        raise ComparisonIntegrityError("finding_snapshot_invalid")
    try:
        FindingUid.parse(finding.finding_uid)
        FindingObservationId.parse(finding.finding_observation_id)
    except (IdentityError, TypeError):
        raise ComparisonIntegrityError("finding_snapshot_invalid") from None
    quotes: list[FindingQuote] = []
    seen: set[tuple[int, str]] = set()
    for item in finding.evidence:
        if (
            not isinstance(item, FindingEvidenceSnapshot)
            or type(item.page_number) is not int
            or not 1 <= item.page_number <= side.facts.page_count
            or not isinstance(item.quote, str)
        ):
            raise ComparisonIntegrityError("finding_evidence_invalid")
        key = (item.page_number, _normalized(item.quote))
        if key not in seen:
            seen.add(key)
            quotes.append(FindingQuote(item.page_number, item.quote))
    if not quotes:
        raise ComparisonIntegrityError("finding_evidence_invalid")
    if len(quotes) > MAX_EVIDENCE_PER_FINDING:
        return None
    return FindingForMatch(
        finding.finding_uid, finding.finding_observation_id, side.run_id,
        side.facts.version_uid, finding.category, finding.finding_text, tuple(quotes),
    )


def _ref(finding: FindingSnapshot) -> FindingRef:
    return FindingRef(
        finding.finding_uid, finding.category, finding.finding_text,
        tuple(sorted({item.page_number for item in finding.evidence})),
    )


def _source_only_label(
    finding: FindingSnapshot,
    page_map: Mapping[int, int],
    target: _Side,
    normalized_pages: dict[int, str],
) -> tuple[str, str]:
    unpaired = False
    for item in finding.evidence:
        target_page = page_map.get(item.page_number)
        if target_page is None:
            unpaired = True
            continue
        if target_page not in normalized_pages:
            normalized_pages[target_page] = _normalized(target.text.pages[target_page])
        if _normalized(item.quote) in normalized_pages[target_page]:
            return PROPOSAL_UNDETERMINED, BASIS_QUOTE_PRESENT
    if unpaired:
        return PROPOSAL_UNDETERMINED, BASIS_SHEET_UNPAIRED
    return PROPOSAL_PROBABLY_FIXED, BASIS_QUOTES_ABSENT


def _finding_comparison(
    pair: OrderedVersionPair,
    suggestions: tuple[SheetPairSuggestion, ...],
    source: _Side,
    target: _Side,
) -> FindingComparison:
    if len(source.findings) > MAX_FINDINGS_PER_RUN or len(target.findings) > MAX_FINDINGS_PER_RUN:
        return FindingComparison(
            FINDINGS_UNAVAILABLE, FINDINGS_OVER_LIMIT,
            len(source.findings), len(target.findings), (),
        )
    older = {item.finding_uid: (item, _for_match(source, item)) for item in source.findings}
    newer = {item.finding_uid: (item, _for_match(target, item)) for item in target.findings}
    if len(older) != len(source.findings) or len(newer) != len(target.findings):
        raise ComparisonIntegrityError("finding_duplicate")
    try:
        matches = suggest_finding_matches_on_sheet_suggestions(
            version_pair=pair,
            sheet_suggestions=tuple(
                SuggestedSheetPair(
                    item.source_page_number, item.target_page_number, item.suggestion_sha256,
                )
                for item in suggestions
            ),
            source_run_id=source.run_id,
            target_run_id=target.run_id,
            source_findings=tuple(m for _, m in older.values() if m is not None),
            target_findings=tuple(m for _, m in newer.values() if m is not None),
        )
    except FindingMatchSuggestionRefused as refusal:
        raise ComparisonIntegrityError(str(refusal)) from None

    proposals: list[FindingProposal] = [
        FindingProposal(
            PROPOSAL_UNCHANGED, BASIS_EXACT_MATCH,
            _ref(older[match.source_finding_uid][0]), _ref(newer[match.target_finding_uid][0]),
            match.proposal_sha256,
        )
        for match in matches
    ]
    matched_source = {match.source_finding_uid for match in matches}
    matched_target = {match.target_finding_uid for match in matches}
    page_map = {item.source_page_number: item.target_page_number for item in suggestions}
    normalized_pages: dict[int, str] = {}
    for uid, (snapshot, matchable) in older.items():
        if uid in matched_source:
            continue
        if matchable is None:
            kind, basis = PROPOSAL_UNDETERMINED, BASIS_EVIDENCE_OVER_LIMIT
        else:
            kind, basis = _source_only_label(snapshot, page_map, target, normalized_pages)
        proposals.append(FindingProposal(kind, basis, _ref(snapshot), None, None))
    for uid, (snapshot, matchable) in newer.items():
        if uid in matched_target:
            continue
        if matchable is None:
            kind, basis = PROPOSAL_UNDETERMINED, BASIS_EVIDENCE_OVER_LIMIT
        else:
            kind, basis = PROPOSAL_NEW, BASIS_NO_SOURCE_MATCH
        proposals.append(FindingProposal(kind, basis, None, _ref(snapshot), None))

    order = {kind: position for position, kind in enumerate(PROPOSAL_KINDS)}
    proposals.sort(key=lambda item: (
        order[item.kind],
        item.source_finding.finding_uid if item.source_finding else "",
        item.target_finding.finding_uid if item.target_finding else "",
    ))
    return FindingComparison(
        FINDINGS_COMPARED, None, len(source.findings), len(target.findings), tuple(proposals),
    )


__all__ = [
    "COMPARISON_ALGORITHM", "ComparisonIntegrityError", "ComparisonRequest",
    "ComparisonRequestInvalid", "CurrentComparison", "CurrentFindingProposals", "DEFAULT_DIFF_LIMIT",
    "FindingEvidenceSnapshot",
    "FindingSnapshot", "MAX_DIFF_LIMIT", "MAX_DIFF_PAGE_CHARACTERS", "RUN_STATE_PUBLISHED",
    "RunCandidate", "SHEET_DIFF_ALGORITHM", "SavedPageText", "VersionAnalysisReader",
    "VersionClassificationReader", "VersionComparisonService",
]
