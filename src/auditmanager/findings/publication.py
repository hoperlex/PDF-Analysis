"""Publication — turning a gate verdict into rows, and identity allocation.

What reaches the database is decided entirely by :mod:`auditmanager.findings.grounding`:

* a **grounded** observation gets a fresh ``finding_uid``, an immutable
  ``finding_observation_id`` bound to this one run, and one ``finding_evidence`` row per
  declared anchor;
* an **ungrounded** observation gets a ``finding_observation`` row carrying
  ``grounded = false``, its ``ungrounded_reason`` and **no** ``finding_uid`` — and no
  evidence rows, because an evidence row is the record of an anchor that resolved.

``finding_uid`` is fresh per published observation, per run (§5.2). PC-01 does no
cross-run matching and no decision carryover, so two runs over the same document produce
two disjoint sets. That is not a limitation this module works around: allocating a
carried-over identity would silently attach one document's expert history to another
run's text.

`F8-PUBLISH` (ADR-0029 decision 7, plan-v5 section 4): for a run whose ``publication_mode`` is ``one_list`` the module also holds
:func:`publish_candidate_groups`, the publisher of the extended-review candidates. N observations of one group become **one** finding: the
first member that passes gate v2 is the canonical observation, a group has one category (a mixed group is ``cross_source``), and the
evidence of a member is its blocks (``finding_block_evidence``, boxes taken from the run's verified geometry, never from the candidate).
The text gate's admission stays unchanged. In one-list runs its observations can carry a linked candidate reference and a severity
proposal; a ``text_only`` run publishes exactly as before.

The pairing ``grounded = (finding_uid IS NOT NULL)`` and
``grounded = (ungrounded_reason IS NULL)`` is a CHECK constraint in the migration. This
module writes rows that satisfy it and does **not** re-assert it in Python: a second
copy of a rule is a second place for it to be wrong, and the constraint is the one a
future caller cannot bypass.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final, Mapping

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.findings.artifacts import (
    MAX_EXTENDED_OBSERVATION_REF_CHARS,
    BlockEvidenceItem,
    BlockGateInputs,
    BlockObservation,
    ObservationSet,
)
from auditmanager.findings.grounding import GateResult, ObservationVerdict, run_block_gate
from auditmanager.shared.db import SQLSTATE_TO_CATALOG_CODE, nested_transaction
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import FindingObservationId, FindingUid

_INSERT_FINDING = text(
    """
    INSERT INTO finding (finding_uid, project_uid, version_uid, allocated_by_run_id, category, publication_policy)
    VALUES (:finding_uid, :project_uid, :version_uid, :run_id, :category, :publication_policy)
    """
)

_INSERT_OBSERVATION = text(
    """
    INSERT INTO finding_observation (
        finding_observation_id, run_id, finding_uid, stage_id, category,
        finding_text, recommendation_text, grounded, ungrounded_reason,
        analysis_profile_id, prompt_bundle_id, model_call_id, provider_mode, proposed_severity, extended_observation_ref, grounding_kind
    ) VALUES (
        :finding_observation_id, :run_id, :finding_uid, :stage_id, :category,
        :finding_text, :recommendation_text, :grounded, :ungrounded_reason,
        :analysis_profile_id, :prompt_bundle_id, :model_call_id, :provider_mode, :proposed_severity, :extended_observation_ref, :grounding_kind
    )
    """
)

_INSERT_EVIDENCE = text(
    """
    INSERT INTO finding_evidence (
        finding_observation_id, evidence_ordinal, page_number, quote,
        char_start, char_end, block_id
    ) VALUES (
        :finding_observation_id, :evidence_ordinal, :page_number, :quote,
        :char_start, :char_end, :block_id
    )
    """
)


@dataclass(frozen=True, slots=True)
class PublishedFinding:
    """One observation that survived the gate, with the identities allocated for it."""

    finding_uid: str
    finding_observation_id: str
    observation_ordinal: int
    category: str
    evidence_count: int


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One observation the gate rejected. Counted as a finding nowhere."""

    finding_observation_id: str
    observation_ordinal: int
    ungrounded_reason: str


@dataclass(frozen=True, slots=True)
class PublicationResult:
    """What one publication wrote, in terms a caller can assert on.

    ``candidates`` (`F8-PUBLISH`) is what the publisher of groups wrote for a ``one_list`` run, ``None`` for every other run. The counts
    and ``finding_uids`` cover the findings of both paths, so a caller that counts findings counts the candidates' too; ``published`` and
    ``diagnostics`` stay the text path's own.
    """

    run_id: str
    published: tuple[PublishedFinding, ...] = field(default_factory=tuple)
    diagnostics: tuple[Diagnostic, ...] = field(default_factory=tuple)
    candidates: "CandidatePublicationResult | None" = None

    @property
    def published_count(self) -> int:
        return len(self.finding_uids)

    @property
    def diagnostic_count(self) -> int:
        return len(self.diagnostics) + (0 if self.candidates is None else self.candidates.diagnostic_count)

    @property
    def finding_uids(self) -> tuple[str, ...]:
        text_uids = tuple(entry.finding_uid for entry in self.published)
        return tuple(dict.fromkeys(text_uids if self.candidates is None else text_uids + self.candidates.finding_uids))


def _translate(exc: DBAPIError) -> DomainError:
    """Map a database refusal on **SQLSTATE**, never on message text.

    A message is a diagnostic string that a server upgrade or a locale may reword; the
    SQLSTATE is the contract. ``SQLSTATE_TO_CATALOG_CODE`` is the shared kernel's map
    and this module adds no second one.
    """
    sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None) or getattr(
        exc, "code", None
    )
    mapped = SQLSTATE_TO_CATALOG_CODE.get(str(sqlstate)) if sqlstate else None
    if mapped is not None:
        return DomainError(ErrorCode(mapped), message=f"the database refused the write ({sqlstate})")
    return DomainError(ErrorCode.INTERNAL_ERROR, message="the database refused the write")


def publish_gate_result(
    session: Session,
    *,
    gate_result: GateResult,
    observation_set: ObservationSet,
    run_id: str,
    project_uid: str,
    version_uid: str,
    model_call_ids: Mapping[int, str] | None = None,
    proposed_severities: Mapping[int, str] | None = None,
    extended_observation_refs: Mapping[int, str] | None = None,
    reviewable: bool = False,
) -> PublicationResult:
    """Write the gate's decision, in one savepoint inside the caller's unit of work.

    The caller owns the transaction — this module opens no engine, commits nothing and
    writes no rollback of its own. The savepoint means a publication that violates a
    constraint discards only the publication, leaving the run's own bookkeeping for the
    caller to finish or abandon.

    ``model_call_ids`` maps ``observation_ordinal`` to the ``model_call_id`` that
    produced it, for the provenance §5 requires. An observation with no entry is written
    with a NULL ``model_call_id`` rather than a fabricated one.
    Optional proposal/reference maps annotate new one-list text observations, never expert decisions.
    """
    calls = dict(model_call_ids or {})
    proposals = dict(proposed_severities or {})
    extended_refs = dict(extended_observation_refs or {})
    if any(not isinstance(value, str) or value not in _PROPOSED_SEVERITIES for value in proposals.values()):
        raise _invalid_candidate("unknown proposed severity")
    if any(not isinstance(value, str) or not 1 <= len(value) <= 128 for value in extended_refs.values()):
        raise _invalid_candidate("unknown extended observation reference")
    published: list[PublishedFinding] = []
    diagnostics: list[Diagnostic] = []

    try:
        with nested_transaction(session):
            if reviewable:
                session.execute(text("SELECT run_id FROM audit_run WHERE run_id = :run_id FOR UPDATE"), {"run_id": run_id})
            for verdict in gate_result.verdicts:
                observation = verdict.observation
                candidate_ref = extended_refs.get(observation.observation_ordinal)
                if reviewable:
                    candidate_ref = candidate_ref or f"primary_text_{observation.observation_ordinal}"
                    existing = session.execute(text(
                        "SELECT o.finding_uid, o.finding_observation_id, o.finding_text, o.recommendation_text, "
                        "(SELECT count(*) FROM finding_evidence e WHERE e.finding_observation_id = o.finding_observation_id) AS n "
                        "FROM finding_observation o WHERE o.run_id = :run_id AND o.extended_observation_ref = :ref "
                        "AND o.finding_uid IS NOT NULL"
                    ), {"run_id": run_id, "ref": candidate_ref}).mappings().one_or_none()
                    if existing is not None:
                        if (existing["finding_text"], existing["recommendation_text"]) != (observation.finding_text, observation.recommendation_text):
                            raise _invalid_candidate("a published source reference changed its content")
                        published.append(PublishedFinding(existing["finding_uid"], existing["finding_observation_id"],
                                                          observation.observation_ordinal, observation.category, existing["n"]))
                        continue
                observation_id = FindingObservationId.new().value
                model_call_id = calls.get(observation.observation_ordinal) or (
                    observation.model_call_id
                )

                if verdict.grounded or reviewable:
                    # Fresh identity, this run only. §5.2.
                    finding_uid: str | None = FindingUid.new().value
                    session.execute(
                        _INSERT_FINDING,
                        {
                            "finding_uid": finding_uid,
                            "project_uid": project_uid,
                            "version_uid": version_uid,
                            "run_id": run_id,
                            "category": observation.category,
                            "publication_policy": "reviewable-v1" if reviewable else None,
                        },
                    )
                    reason: str | None = None if verdict.grounded else verdict.reason.value
                else:
                    finding_uid = None
                    failing = verdict.reason
                    assert failing is not None  # an ungrounded verdict always carries one
                    reason = failing.value

                session.execute(
                    _INSERT_OBSERVATION,
                    {
                        "finding_observation_id": observation_id,
                        "run_id": run_id,
                        "finding_uid": finding_uid,
                        "stage_id": observation_set.stage_id,
                        "category": observation.category,
                        "finding_text": observation.finding_text,
                        "recommendation_text": observation.recommendation_text,
                        "grounded": verdict.grounded,
                        "grounding_kind": "unverified" if reviewable and not verdict.grounded else "text_span",
                        "ungrounded_reason": reason,
                        "analysis_profile_id": observation_set.analysis_profile_id,
                        "prompt_bundle_id": observation_set.prompt_bundle_id,
                        "model_call_id": model_call_id,
                        "provider_mode": observation_set.provider_mode,
                        "proposed_severity": proposals.get(observation.observation_ordinal),
                        "extended_observation_ref": candidate_ref,
                    },
                )

                if verdict.grounded:
                    for item in observation.evidence:
                        session.execute(
                            _INSERT_EVIDENCE,
                            {
                                "finding_observation_id": observation_id,
                                "evidence_ordinal": item.evidence_ordinal,
                                "page_number": item.page_number,
                                "quote": item.quote,
                                "char_start": item.char_start,
                                "char_end": item.char_end,
                                "block_id": item.block_id,
                            },
                        )
                if finding_uid is not None:
                    if reviewable:
                        session.execute(_SET_CANONICAL, {"canonical_observation_id": observation_id, "finding_uid": finding_uid})
                    published.append(
                        PublishedFinding(
                            finding_uid=finding_uid,
                            finding_observation_id=observation_id,
                            observation_ordinal=observation.observation_ordinal,
                            category=observation.category,
                            evidence_count=len(observation.evidence) if verdict.grounded else 0,
                        )
                    )
                else:
                    assert reason is not None
                    diagnostics.append(
                        Diagnostic(
                            finding_observation_id=observation_id,
                            observation_ordinal=observation.observation_ordinal,
                            ungrounded_reason=reason,
                        )
                    )
    except DBAPIError as exc:
        raise _translate(exc) from exc

    return PublicationResult(
        run_id=run_id,
        published=tuple(published),
        diagnostics=tuple(diagnostics),
    )


# ---------------------------------------------------------------------------------------------
# One list: the publisher of candidate groups (`F8-PUBLISH`, ADR-0029 decision 7, plan-v5 section 4)
# ---------------------------------------------------------------------------------------------

#: The two categories a candidate group takes (migration 0064 adds them to ``FindingCategory``): a group of blocks only is a drawing
#: discrepancy; a group that also stands on a text or other source is ``cross_source``. A group has one category, so every observation of
#: it carries it (``findings.queries.group_published_findings`` refuses a group whose members differ).
CATEGORY_DRAWING_DISCREPANCY: Final[str] = "drawing_discrepancy"
CATEGORY_CROSS_SOURCE: Final[str] = "cross_source"
#: ``stage_id`` of a candidate finding: blocks of one window are ``block_analysis``; a mixed group, a cross-window group and a cross-check
#: are ``finding_merge``. ``STAGE_IDS`` does not change (``0002``).
STAGE_BLOCK_ANALYSIS: Final[str] = "block_analysis"
STAGE_FINDING_MERGE: Final[str] = "finding_merge"
#: The recommendation of a candidate the corrector did not refine. The expert checks the source; the machine states no remedy.
RECOMMENDATION_CHECK_THE_SOURCE: Final[str] = "Требуется проверка эксперта по источнику"

#: Why a group is not published as a finding. Neither is a defect: the first is the text path's work, the second has nothing the block gate
#: could verify.
SKIP_PRIMARY_TEXT_ONLY: Final[str] = "primary_text_only"
SKIP_NO_BLOCK_EVIDENCE: Final[str] = "no_block_evidence"

#: ``ck_finding_observation_text_length`` and the width of the contract's ``block_evidence`` (``Field(max_length=64)``).
MAX_TEXT_CHARS: Final[int] = 4000
MAX_BLOCK_EVIDENCE_ITEMS: Final[int] = 64
_PROPOSED_SEVERITIES = frozenset({"critical", "economic", "operational", "recommendation", "check_adjacent"})


def _invalid_candidate(detail: str) -> DomainError:
    return DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, message=detail)


@dataclass(frozen=True, slots=True)
class CandidateMember:
    """One extended-review candidate, as the publisher takes it: its words, what it stands on, and where it came from.

    ``block_evidence`` is the blocks the candidate stands on (empty for a candidate that stands on no block). Its other sources are only
    counted: ``primary_text_ordinals`` are the observation ordinals of the text findings it is a restatement of (the ``primary_text_<key>`` or
    ``text:<n>`` sources), ``primary_text_unlinked`` the primary texts whose text observation could not be named, and ``other_source_count``
    every source that is neither a block nor a primary text (a native page, a piece of a cross-window comparison).
    ``refined_recommendation`` is the corrector's refinement, if there is one.
    """

    extended_observation_ref: str
    finding_text: str
    block_evidence: tuple[BlockEvidenceItem, ...] = ()
    refined_recommendation: str | None = None
    primary_text_ordinals: tuple[int, ...] = ()
    primary_text_unlinked: int = 0
    other_source_count: int = 0
    window_id: str | None = None
    cross_window: bool = False
    proposed_severity: str | None = None
    proposed_recommendation: str | None = None
    native_sources: tuple[tuple[int, str], ...] = ()

    def __post_init__(self) -> None:
        ref = self.extended_observation_ref
        if not isinstance(ref, str) or not 1 <= len(ref) <= MAX_EXTENDED_OBSERVATION_REF_CHARS:
            raise _invalid_candidate("a candidate's reference is not 1 to 128 characters")
        if not isinstance(self.finding_text, str) or not self.finding_text.strip() or len(self.finding_text) > MAX_TEXT_CHARS:
            raise _invalid_candidate("a candidate's text is not 1 to 4000 characters")
        refined = self.refined_recommendation
        if refined is not None and (not isinstance(refined, str) or not refined.strip() or len(refined) > MAX_TEXT_CHARS):
            raise _invalid_candidate("a candidate's refinement is neither absent nor 1 to 4000 characters")
        if self.proposed_severity is not None and (not isinstance(self.proposed_severity, str) or self.proposed_severity not in _PROPOSED_SEVERITIES):
            raise _invalid_candidate("unknown proposed severity")
        proposed = self.proposed_recommendation
        if proposed is not None and (not isinstance(proposed, str) or not proposed.strip() or len(proposed) > MAX_TEXT_CHARS):
            raise _invalid_candidate("a candidate's recommendation is neither absent nor 1 to 4000 characters")
        if len(self.block_evidence) > MAX_BLOCK_EVIDENCE_ITEMS:
            raise _invalid_candidate(f"a candidate stands on at most {MAX_BLOCK_EVIDENCE_ITEMS} blocks")
        if (
            self.other_source_count < 0
            or self.primary_text_unlinked < 0
            or any(type(n) is not int for n in self.primary_text_ordinals)
        ):
            raise _invalid_candidate("a candidate's source counts are not counts")
        if any(type(number) is not int or number < 1 or not isinstance(quote, str) or not quote
               for number, quote in self.native_sources):
            raise _invalid_candidate("a native source is a page and its literal quote")

    @property
    def recommendation_text(self) -> str:
        if self.proposed_recommendation is not None:
            return self.proposed_recommendation
        return self.refined_recommendation if self.refined_recommendation is not None else RECOMMENDATION_CHECK_THE_SOURCE


@dataclass(frozen=True, slots=True)
class CandidateGroup:
    """One group of the strict consolidation: the candidates of identical wording that share a source, in their saved order.

    The first member that passes the block gate is the canonical observation (the consolidation's own rule: the first occurrence is the
    stable representative). A member need not stand on a block: a group of a block candidate and a primary text candidate is a mixed group,
    and its text member only says so (it is already published by the text path).
    """

    group_id: str
    members: tuple[CandidateMember, ...]

    def __post_init__(self) -> None:
        if not self.group_id or not self.members:
            raise _invalid_candidate("a candidate group has an identity and at least one member")


@dataclass(frozen=True, slots=True)
class GroupClassification:
    """What a group is, decided from the facts of its members and from nothing else."""

    publishable: bool
    skip_reason: str | None
    mixed: bool
    category: str
    stage_id: str


def classify_group(group: CandidateGroup) -> GroupClassification:
    """The rule of plan-v5 section 4 items 1 and 2, as one pure function.

    * no member stands on a block: **not published**. When the group also stands on nothing but primary texts it is the text path's own
      finding (``primary_text_only``: never published twice); otherwise there is no block the gate could prove (``no_block_evidence``);
    * a group that stands on blocks **and** on a primary text or another source is mixed: category ``cross_source``, stage ``finding_merge``;
    * a group of blocks only is ``drawing_discrepancy``; it is ``finding_merge`` when it was merged across windows (or comes from the
      cross-window pass), ``block_analysis`` otherwise.
    """
    members = group.members
    has_block = any(member.block_evidence for member in members)
    has_primary = any(member.primary_text_ordinals or member.primary_text_unlinked for member in members)
    has_other = any(member.other_source_count for member in members)
    mixed = has_block and (has_primary or has_other)
    windows = {member.window_id for member in members if member.window_id is not None}
    merged_across_windows = len(windows) > 1 or any(member.cross_window for member in members)
    category = CATEGORY_CROSS_SOURCE if mixed else CATEGORY_DRAWING_DISCREPANCY
    stage_id = STAGE_FINDING_MERGE if mixed or merged_across_windows else STAGE_BLOCK_ANALYSIS
    if has_block:
        return GroupClassification(True, None, mixed, category, stage_id)
    reason = SKIP_PRIMARY_TEXT_ONLY if has_primary and not has_other else SKIP_NO_BLOCK_EVIDENCE
    return GroupClassification(False, reason, mixed, category, stage_id)


@dataclass(frozen=True, slots=True)
class PublishedCandidateFinding:
    """One finding the publisher of groups wrote: its identity, its canonical observation and every observation it holds."""

    finding_uid: str
    group_id: str
    category: str
    stage_id: str
    canonical_observation_id: str
    observation_ids: tuple[str, ...]
    related_finding_uid: str | None
    block_evidence_count: int


@dataclass(frozen=True, slots=True)
class SkippedGroup:
    group_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class CandidatePublicationResult:
    """What the publisher of groups wrote, in terms a caller can assert on.

    ``diagnostics`` are the members gate v2 refused (written as ungrounded observations with no ``finding_uid``, like the text path's);
    ``skipped`` are the groups that are not published as findings and why.
    """

    run_id: str
    published: tuple[PublishedCandidateFinding, ...] = field(default_factory=tuple)
    diagnostics: tuple[Diagnostic, ...] = field(default_factory=tuple)
    skipped: tuple[SkippedGroup, ...] = field(default_factory=tuple)
    #: Why the saved candidates could not be read as groups at all (for example ``consolidation_unavailable``): said, never hidden.
    unread: tuple[str, ...] = field(default_factory=tuple)

    @property
    def published_count(self) -> int:
        return len(self.published)

    @property
    def diagnostic_count(self) -> int:
        return len(self.diagnostics)

    @property
    def observation_count(self) -> int:
        return sum(len(entry.observation_ids) for entry in self.published)

    @property
    def finding_uids(self) -> tuple[str, ...]:
        return tuple(entry.finding_uid for entry in self.published)


_INSERT_CANDIDATE_OBSERVATION = text(
    """
    INSERT INTO finding_observation (
        finding_observation_id, run_id, finding_uid, stage_id, category,
        finding_text, recommendation_text, grounded, ungrounded_reason,
        analysis_profile_id, prompt_bundle_id, model_call_id, provider_mode,
        grounding_kind, extended_observation_ref, related_finding_uid, proposed_severity
    ) VALUES (
        :finding_observation_id, :run_id, :finding_uid, :stage_id, :category,
        :finding_text, :recommendation_text, :grounded, :ungrounded_reason,
        :analysis_profile_id, :prompt_bundle_id, NULL, :provider_mode,
        :grounding_kind, :extended_observation_ref, :related_finding_uid, :proposed_severity
    )
    """
)

_INSERT_BLOCK_EVIDENCE = text(
    """
    INSERT INTO finding_block_evidence (
        finding_observation_id, ordinal, page_number, portal_block_id,
        bbox_x0, bbox_y0, bbox_x1, bbox_y1, crop_sha256, recognised_quote
    ) VALUES (
        :finding_observation_id, :ordinal, :page_number, :portal_block_id,
        :bbox_x0, :bbox_y0, :bbox_x1, :bbox_y1, :crop_sha256, :recognised_quote
    )
    """
)

_SET_CANONICAL = text(
    "UPDATE finding SET canonical_observation_id = :canonical_observation_id "
    "WHERE finding_uid = :finding_uid AND canonical_observation_id IS NULL"
)


def _candidate_ref(verdict: ObservationVerdict) -> str | None:
    """The reference the candidate carried into the gate: the verdict's own observation is the ``BlockObservation`` the publisher built."""
    observation = verdict.observation
    assert isinstance(observation, BlockObservation)
    return observation.extended_observation_ref


def publish_candidate_groups(
    session: Session,
    *,
    groups: Sequence[CandidateGroup],
    gate_inputs: BlockGateInputs | None,
    run_id: str,
    project_uid: str,
    version_uid: str,
    analysis_profile_id: str,
    prompt_bundle_id: str,
    provider_mode: str,
    primary_findings: Mapping[int, str] | None = None,
    unread: Sequence[str] = (),
    reviewable: bool = False,
    text_layer=None,
) -> CandidatePublicationResult:
    """Publish the candidate groups of a ``one_list`` run, in one savepoint inside the caller's unit of work.

    For each group: classify it (:func:`classify_group`); judge every member that stands on blocks with gate v2 (``run_block_gate`` over
    ``gate_inputs`` -- ``None`` refuses every block, so a run that has no verified geometry publishes nothing); the **members that pass** are
    the observations of one new finding, the first of them canonical, and the members the gate refused are written as ungrounded
    observations beside it (no ``finding_uid``, the reason, ``grounding_kind = portal_block``). A group none of whose members passes writes
    only those diagnostics. The gate decides per observation, so a group is split here, never published whole on one member's evidence.

    ``primary_findings`` maps the observation ordinal of a text finding the text path published to its ``finding_uid``. A group that
    stands on a primary text names the first one it finds there as ``related_finding_uid`` on each of its observations (a bare identity;
    the number of a finding is only for display). The box written for a block is the geometry's own (``place().bbox_norm``), never one the
    candidate declared.

    A refusal of the database propagates as a ``DomainError`` and the savepoint discards everything this call wrote. Nothing is committed.
    """
    if reviewable:
        from auditmanager.findings.review_publication import publish_reviewable_groups
        try:
            return publish_reviewable_groups(session, groups=groups, gate_inputs=gate_inputs, run_id=run_id,
                project_uid=project_uid, version_uid=version_uid, analysis_profile_id=analysis_profile_id,
                prompt_bundle_id=prompt_bundle_id, provider_mode=provider_mode, primary_findings=primary_findings, unread=unread,
                text_layer=text_layer)
        except DBAPIError as exc:
            raise _translate(exc) from exc
    linked = dict(primary_findings or {})
    published: list[PublishedCandidateFinding] = []
    diagnostics: list[Diagnostic] = []
    skipped: list[SkippedGroup] = []
    ordinal = 0

    try:
        with nested_transaction(session):
            for group in groups:
                kind = classify_group(group)
                if not kind.publishable:
                    assert kind.skip_reason is not None
                    skipped.append(SkippedGroup(group.group_id, kind.skip_reason))
                    continue

                standing = [member for member in group.members if member.block_evidence]
                observations = [
                    BlockObservation(
                        observation_ordinal=ordinal + position,
                        evidence=member.block_evidence,
                        extended_observation_ref=member.extended_observation_ref,
                    )
                    for position, member in enumerate(standing)
                ]
                ordinal += len(observations)
                verdicts = run_block_gate(observations, gate_inputs).verdicts
                passing = [(member, verdict) for member, verdict in zip(standing, verdicts) if verdict.grounded]
                refused = [(member, verdict) for member, verdict in zip(standing, verdicts) if not verdict.grounded]

                related = next(
                    (
                        linked[number]
                        for member in group.members
                        for number in member.primary_text_ordinals
                        if number in linked
                    ),
                    None,
                )
                finding_uid: str | None = None
                observation_ids: list[str] = []
                evidence_count = 0
                if passing:
                    finding_uid = FindingUid.new().value
                    session.execute(
                        _INSERT_FINDING,
                        {
                            "finding_uid": finding_uid,
                            "project_uid": project_uid,
                            "version_uid": version_uid,
                            "run_id": run_id,
                            "category": kind.category,
                            "publication_policy": None,
                        },
                    )

                base = {
                    "run_id": run_id,
                    "stage_id": kind.stage_id,
                    "category": kind.category,
                    "analysis_profile_id": analysis_profile_id,
                    "prompt_bundle_id": prompt_bundle_id,
                    "provider_mode": provider_mode,
                }
                for member, verdict in passing:
                    observation_id = FindingObservationId.new().value
                    observation_ids.append(observation_id)
                    session.execute(
                        _INSERT_CANDIDATE_OBSERVATION,
                        {
                            **base,
                            "finding_observation_id": observation_id,
                            "finding_uid": finding_uid,
                            "finding_text": member.finding_text,
                            "recommendation_text": member.recommendation_text,
                            "grounded": True,
                            "ungrounded_reason": None,
                            # how it was grounded and which candidate it came from are the verdict's and the observation's own
                            "grounding_kind": verdict.grounding_kind,
                            "extended_observation_ref": _candidate_ref(verdict),
                            "related_finding_uid": related,
                            "proposed_severity": member.proposed_severity,
                        },
                    )
                    for item in member.block_evidence:
                        place = None if gate_inputs is None else gate_inputs.geometry.place(item.portal_block_id)
                        if place is None:  # the gate passed it, so it is there; a missing place is a bug, never a default box
                            raise DomainError(
                                ErrorCode.STORAGE_INTEGRITY_ERROR,
                                message="a block that passed the gate has no place in the run's geometry",
                            )
                        x0, y0, x1, y1 = place.bbox_norm
                        session.execute(
                            _INSERT_BLOCK_EVIDENCE,
                            {
                                "finding_observation_id": observation_id,
                                "ordinal": item.evidence_ordinal,
                                "page_number": place.page_number,
                                "portal_block_id": item.portal_block_id,
                                "bbox_x0": x0,
                                "bbox_y0": y0,
                                "bbox_x1": x1,
                                "bbox_y1": y1,
                                "crop_sha256": item.crop_sha256,
                                "recognised_quote": item.recognised_quote,
                            },
                        )
                        evidence_count += 1

                for member, verdict in refused:
                    observation_id = FindingObservationId.new().value
                    failing = verdict.reason
                    assert failing is not None  # an ungrounded verdict always carries one
                    session.execute(
                        _INSERT_CANDIDATE_OBSERVATION,
                        {
                            **base,
                            "finding_observation_id": observation_id,
                            "finding_uid": None,
                            "finding_text": member.finding_text,
                            "recommendation_text": member.recommendation_text,
                            "grounded": False,
                            "ungrounded_reason": failing.value,
                            "grounding_kind": verdict.grounding_kind,
                            "extended_observation_ref": _candidate_ref(verdict),
                            "related_finding_uid": None,
                            "proposed_severity": member.proposed_severity,
                        },
                    )
                    diagnostics.append(
                        Diagnostic(
                            finding_observation_id=observation_id,
                            observation_ordinal=verdict.observation.observation_ordinal,
                            ungrounded_reason=failing.value,
                        )
                    )

                if finding_uid is not None:
                    result = session.execute(
                        _SET_CANONICAL,
                        {"canonical_observation_id": observation_ids[0], "finding_uid": finding_uid},
                    )
                    if result.rowcount != 1:
                        raise DomainError(
                            ErrorCode.STORAGE_INTEGRITY_ERROR,
                            message="the canonical observation of a candidate finding could not be set",
                        )
                    published.append(
                        PublishedCandidateFinding(
                            finding_uid=finding_uid,
                            group_id=group.group_id,
                            category=kind.category,
                            stage_id=kind.stage_id,
                            canonical_observation_id=observation_ids[0],
                            observation_ids=tuple(observation_ids),
                            related_finding_uid=related,
                            block_evidence_count=evidence_count,
                        )
                    )
    except DBAPIError as exc:
        raise _translate(exc) from exc

    return CandidatePublicationResult(
        run_id=run_id,
        published=tuple(published),
        diagnostics=tuple(diagnostics),
        skipped=tuple(skipped),
        unread=tuple(unread),
    )
