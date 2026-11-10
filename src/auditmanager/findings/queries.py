"""The public read surface over published findings. ``P2-API-01`` and ``P2-EXP-01``
read these; neither reimplements them, and neither reimplements the verdict projection.

Every query here reaches ``finding_observation`` through an **inner join on
``finding``**. That is deliberate and is the whole safety argument: an ungrounded
observation carries ``finding_uid IS NULL``, so the join drops it. There is no
``WHERE grounded = true`` anywhere in this module, because a ``WHERE`` clause is
something a later query has to remember and a join through the identity table is not.

The diagnostic read is a separate function with a separate name, so nothing can obtain
diagnostics and published findings from one call and confuse the two counts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.errors import DomainError, ErrorCode

_PUBLISHED_FINDINGS = text(
    """
    SELECT
        o.finding_uid,
        o.finding_observation_id,
        f.project_uid,
        f.version_uid,
        f.allocated_by_run_id,
        f.canonical_observation_id,
        o.category,
        o.finding_text,
        o.recommendation_text,
        o.stage_id,
        o.analysis_profile_id,
        o.prompt_bundle_id,
        o.model_call_id,
        o.provider_mode,
        o.proposed_severity,
        o.grounding_kind,
        o.extended_observation_ref,
        o.related_finding_uid,
        o.created_at
    FROM finding_observation o
    JOIN finding f ON f.finding_uid = o.finding_uid
    WHERE o.run_id = :run_id
    ORDER BY f.finding_uid COLLATE "C", o.finding_observation_id COLLATE "C"
    """
)

_FINDING_EVIDENCE = text(
    """
    SELECT
        e.finding_observation_id,
        e.evidence_ordinal,
        e.page_number,
        e.quote,
        e.char_start,
        e.char_end,
        e.block_id
    FROM finding_evidence e
    JOIN finding_observation o ON o.finding_observation_id = e.finding_observation_id
    JOIN finding f ON f.finding_uid = o.finding_uid
    WHERE o.run_id = :run_id
    ORDER BY f.finding_uid COLLATE "C", e.finding_observation_id COLLATE "C", e.evidence_ordinal
    """
)

_BLOCK_EVIDENCE = text(
    """
    SELECT
        b.finding_observation_id,
        b.ordinal,
        b.page_number,
        b.portal_block_id,
        b.bbox_x0,
        b.bbox_y0,
        b.bbox_x1,
        b.bbox_y1,
        b.crop_sha256,
        b.recognised_quote
    FROM finding_block_evidence b
    JOIN finding_observation o ON o.finding_observation_id = b.finding_observation_id
    JOIN finding f ON f.finding_uid = o.finding_uid
    WHERE o.run_id = :run_id
    ORDER BY f.finding_uid COLLATE "C", b.finding_observation_id COLLATE "C", b.ordinal
    """
)

_DIAGNOSTICS = text(
    """
    SELECT
        o.finding_observation_id,
        o.category,
        o.finding_text,
        o.ungrounded_reason,
        o.created_at
    FROM finding_observation o
    WHERE o.run_id = :run_id AND o.finding_uid IS NULL
    ORDER BY o.finding_observation_id
    """
)

_PUBLISHED_COUNT = text(
    """
    SELECT count(DISTINCT f.finding_uid)
    FROM finding_observation o
    JOIN finding f ON f.finding_uid = o.finding_uid
    WHERE o.run_id = :run_id
    """
)

_FIND_BY_UID = text(
    """
    SELECT o.finding_uid, o.finding_observation_id, o.run_id, o.category
    FROM finding_observation o
    JOIN finding f ON f.finding_uid = o.finding_uid
    WHERE o.finding_uid = :finding_uid
    """
)


@dataclass(frozen=True, slots=True)
class FindingRow:
    finding_uid: str
    finding_observation_id: str
    #: The three the frozen ``Finding`` schema requires. They live on ``finding``, which
    #: every query here already joins; until this widening the join selected nothing from
    #: it, so the API could not render a conformant body from this surface at all.
    project_uid: str
    version_uid: str
    run_id: str
    category: str
    finding_text: str
    recommendation_text: str
    stage_id: str
    analysis_profile_id: str
    prompt_bundle_id: str
    model_call_id: str | None
    provider_mode: str
    canonical_observation_id: str | None = None
    proposed_severity: str | None = None
    #: `F8-PUBLISH` (migration 0064): how the observation is grounded (``text_span`` for the text path, ``portal_block`` for a candidate
    #: of a ``one_list`` run), the extended-review candidate it was published from, and the finding it is related to (a bare identity).
    grounding_kind: str = "text_span"
    extended_observation_ref: str | None = None
    related_finding_uid: str | None = None


@dataclass(frozen=True, slots=True)
class FindingGroupRow:
    canonical: FindingRow
    merged: tuple[FindingRow, ...]


@dataclass(frozen=True, slots=True)
class EvidenceRow:
    finding_observation_id: str
    evidence_ordinal: int
    page_number: int
    quote: str
    char_start: int
    char_end: int
    block_id: str | None


@dataclass(frozen=True, slots=True)
class BlockEvidenceRow:
    """One block a candidate finding stands on (`F8-PUBLISH`): the portal block, its normalised box in the run's geometry and the crop on record."""

    finding_observation_id: str
    ordinal: int
    page_number: int
    portal_block_id: str
    bbox_norm: tuple[float, float, float, float]
    crop_sha256: str
    recognised_quote: str | None


@dataclass(frozen=True, slots=True)
class DiagnosticRow:
    finding_observation_id: str
    category: str
    finding_text: str
    ungrounded_reason: str


def published_findings(session: Session, run_id: str) -> tuple[FindingRow, ...]:
    """Every published finding of one run. An ungrounded observation cannot appear."""
    rows = session.execute(_PUBLISHED_FINDINGS, {"run_id": run_id}).mappings().all()
    return tuple(
        FindingRow(
            finding_uid=row["finding_uid"],
            finding_observation_id=row["finding_observation_id"],
            project_uid=row["project_uid"],
            version_uid=row["version_uid"],
            run_id=row["allocated_by_run_id"],
            category=row["category"],
            finding_text=row["finding_text"],
            recommendation_text=row["recommendation_text"],
            stage_id=row["stage_id"],
            analysis_profile_id=row["analysis_profile_id"],
            prompt_bundle_id=row["prompt_bundle_id"],
            model_call_id=row["model_call_id"],
            provider_mode=row["provider_mode"],
            canonical_observation_id=row["canonical_observation_id"],
            proposed_severity=row["proposed_severity"],
            grounding_kind=row["grounding_kind"],
            extended_observation_ref=row["extended_observation_ref"],
            related_finding_uid=row["related_finding_uid"],
        )
        for row in rows
    )


def group_published_findings(rows: Sequence[FindingRow]) -> tuple[FindingGroupRow, ...]:
    """Project persisted finding identity; never infer canonical status from row order."""
    by_uid: dict[str, list[FindingRow]] = {}
    for row in rows:
        by_uid.setdefault(row.finding_uid, []).append(row)
    groups: list[FindingGroupRow] = []
    for members in by_uid.values():
        head = members[0]
        ids = [member.finding_observation_id for member in members]
        stored_canonical_id = head.canonical_observation_id
        canonical_id = stored_canonical_id
        # The old v1 publisher still inserts one observation and leaves the
        # post-0022 canonical column null. That exact legacy shape is identifiable
        # by its single member and absent severity (the recorded v2 publisher is
        # removed, `PROD-11-AR-V1-V2-REMOVAL-01`; its rows always carried a severity
        # and a canonical member).
        if (canonical_id is None and len(members) == 1
                and head.proposed_severity is None):
            canonical_id = head.finding_observation_id
        if (canonical_id is None or ids.count(canonical_id) != 1
                or len(set(ids)) != len(ids)
                or any(
                    member.canonical_observation_id != stored_canonical_id
                    or member.project_uid != head.project_uid
                    or member.version_uid != head.version_uid
                    or member.run_id != head.run_id
                    or member.category != head.category
                    for member in members
                )):
            raise DomainError(
                ErrorCode.STORAGE_INTEGRITY_ERROR,
                message="published finding observation group is inconsistent",
            )
        canonical = next(member for member in members if member.finding_observation_id == canonical_id)
        groups.append(FindingGroupRow(
            canonical=canonical,
            merged=tuple(member for member in members if member.finding_observation_id != canonical_id),
        ))
    return tuple(groups)


def published_finding_evidence(session: Session, run_id: str) -> tuple[EvidenceRow, ...]:
    """Evidence rows of the published findings of one run, in a stable order."""
    rows = session.execute(_FINDING_EVIDENCE, {"run_id": run_id}).mappings().all()
    return tuple(
        EvidenceRow(
            finding_observation_id=row["finding_observation_id"],
            evidence_ordinal=row["evidence_ordinal"],
            page_number=row["page_number"],
            quote=row["quote"],
            char_start=row["char_start"],
            char_end=row["char_end"],
            block_id=row["block_id"],
        )
        for row in rows
    )


def published_finding_block_evidence(session: Session, run_id: str) -> tuple[BlockEvidenceRow, ...]:
    """The block evidence of the published findings of one run, in a stable order. Empty for a ``text_only`` run.

    Reached through the same inner join on ``finding`` as every read here, so a diagnostic (ungrounded) observation can have none to show.
    """
    rows = session.execute(_BLOCK_EVIDENCE, {"run_id": run_id}).mappings().all()
    return tuple(
        BlockEvidenceRow(
            finding_observation_id=row["finding_observation_id"],
            ordinal=row["ordinal"],
            page_number=row["page_number"],
            portal_block_id=row["portal_block_id"],
            bbox_norm=(float(row["bbox_x0"]), float(row["bbox_y0"]), float(row["bbox_x1"]), float(row["bbox_y1"])),
            crop_sha256=row["crop_sha256"],
            recognised_quote=row["recognised_quote"],
        )
        for row in rows
    )


def published_finding_count(session: Session, run_id: str) -> int:
    """Count persisted Finding identities, not merged observation members."""
    return int(session.execute(_PUBLISHED_COUNT, {"run_id": run_id}).scalar_one())


def diagnostics(session: Session, run_id: str) -> tuple[DiagnosticRow, ...]:
    """The rejected observations, retained as diagnostics and counted as findings
    nowhere. Named apart from the finding queries so the two counts cannot be mixed."""
    rows = session.execute(_DIAGNOSTICS, {"run_id": run_id}).mappings().all()
    return tuple(
        DiagnosticRow(
            finding_observation_id=row["finding_observation_id"],
            category=row["category"],
            finding_text=row["finding_text"],
            ungrounded_reason=row["ungrounded_reason"],
        )
        for row in rows
    )


def finding_exists(session: Session, finding_uid: str) -> bool:
    """Is this a published finding? The decision ledger asks before appending."""
    return session.execute(_FIND_BY_UID, {"finding_uid": finding_uid}).first() is not None


def observation_belongs_to_finding(
    session: Session, *, finding_uid: str, finding_observation_id: str
) -> bool:
    """Does this observation carry this finding identity?

    A decision references the observation the expert actually reviewed (§5.3), so the
    two must belong together; a mismatched pair is a caller fault, not a row to write.
    """
    row = session.execute(
        text(
            "SELECT 1 FROM finding_observation "
            "WHERE finding_observation_id = :observation_id AND finding_uid = :finding_uid"
        ),
        {"observation_id": finding_observation_id, "finding_uid": finding_uid},
    ).first()
    return row is not None


def evidence_resolves(
    session: Session, run_id: str, sequence: str, pages: Sequence[tuple[int, int, int]]
) -> tuple[EvidenceRow, ...]:
    """Every stored evidence row of a run whose anchor does **not** resolve.

    A published row that does not resolve would mean the gate let something through, so
    this exists to be asserted empty against a real database rather than trusted. It
    re-reads the stored anchors and compares them with the same exact equality the gate
    used; ``pages`` is ``(page_number, char_start, char_end)`` from the text layer.
    """
    intervals = {number: (start, end) for number, start, end in pages}
    offenders: list[EvidenceRow] = []
    for row in published_finding_evidence(session, run_id):
        interval = intervals.get(row.page_number)
        if interval is None or not (interval[0] <= row.char_start and row.char_end <= interval[1]):
            offenders.append(row)
            continue
        if sequence[row.char_start : row.char_end] != row.quote:
            offenders.append(row)
    return tuple(offenders)


_FINDING_BY_UID = text(
    """
    SELECT
        o.finding_uid,
        o.finding_observation_id,
        f.project_uid,
        f.version_uid,
        f.allocated_by_run_id,
        f.canonical_observation_id,
        o.category,
        o.finding_text,
        o.recommendation_text,
        o.stage_id,
        o.analysis_profile_id,
        o.prompt_bundle_id,
        o.model_call_id,
        o.provider_mode,
        o.proposed_severity,
        o.grounding_kind,
        o.extended_observation_ref,
        o.related_finding_uid,
        o.created_at
    FROM finding_observation o
    JOIN finding f ON f.finding_uid = o.finding_uid
    WHERE o.finding_uid = :finding_uid
      AND (o.finding_observation_id = f.canonical_observation_id
           OR (f.canonical_observation_id IS NULL
               AND o.proposed_severity IS NULL
               AND NOT EXISTS (
                   SELECT 1 FROM finding_observation sibling
                   WHERE sibling.finding_uid = f.finding_uid
                     AND sibling.finding_observation_id <> o.finding_observation_id
               )))
      AND o.grounded
    """
)


def finding_by_uid(session: Session, finding_uid: str) -> FindingRow | None:
    """The published finding behind one ``finding_uid``, or ``None``.

    ``getFinding`` had no read path at all until this existed; the module could list a
    run's findings and never fetch one. The ``grounded`` predicate is the same one
    :func:`published_findings` applies, so a diagnostic observation is unreachable here
    for the same reason it is unreachable there - by the column the database pairs with
    ``finding_uid``, not by a ``WHERE`` clause a later reader has to remember.

    V2 may link several observations to one finding. Select only the persisted
    canonical member; recency or lexical ordering cannot decide that identity.
    """
    row = session.execute(_FINDING_BY_UID, {"finding_uid": finding_uid}).mappings().first()
    if row is None:
        return None
    return FindingRow(
        finding_uid=row["finding_uid"],
        finding_observation_id=row["finding_observation_id"],
        project_uid=row["project_uid"],
        version_uid=row["version_uid"],
        run_id=row["allocated_by_run_id"],
        category=row["category"],
        finding_text=row["finding_text"],
        recommendation_text=row["recommendation_text"],
        stage_id=row["stage_id"],
        analysis_profile_id=row["analysis_profile_id"],
        prompt_bundle_id=row["prompt_bundle_id"],
        model_call_id=row["model_call_id"],
        provider_mode=row["provider_mode"],
        canonical_observation_id=row["canonical_observation_id"],
        proposed_severity=row["proposed_severity"],
        grounding_kind=row["grounding_kind"],
        extended_observation_ref=row["extended_observation_ref"],
        related_finding_uid=row["related_finding_uid"],
    )
