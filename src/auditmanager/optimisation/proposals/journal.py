"""The journal of expert decisions on optimisation proposals (`UI-PARITY-P0J`, ruling `R-151h`).

The original's knowledge base lists the expert's decisions on remarks and on optimisation proposals, with a «Тип»
filter. Ours lists the finding decisions through ``listDecisions``; this is the other half, ``listProposalDecisions``:
every appended ``optimisation_proposal_decision``, newest first, with where it belongs (project, document, version,
section) and what it decided about (the specification row, the proposed vendor). Optionally narrowed to one project,
which is a filter and not a parent: a project nothing was decided in yields nothing.

The decisions are read as appended: a later decision on the same proposal is another row, and the proposal's current
verdict is its latest one, as everywhere in the optimisation context.

A decision an expert **carried over** from an earlier version's pass (`UI-B-14`) names its source (`D-335`, contract
1.43.0): the source decision, the pass and the version it was made in, and the version's display ordinal -- read by the
same join the accepted list uses, and ``None`` for a decision made directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from .repository import CarriedFromRecord

_JOURNAL = text(
    """
    SELECT
        d.proposal_decision_id, d.optimisation_proposal_id, d.verdict, d.comment, d.actor_user_uid, d.decided_at,
        p.optimisation_pass_id, p.row_text, p.proposed_vendor, p.unit,
        s.project_uid, pr.name AS project_name, s.document_uid, doc.display_title AS document_name, s.version_uid,
        c.section_code,
        cd.proposal_decision_id AS carried_decision_id, cq.optimisation_pass_id AS carried_pass_id,
        cp.version_uid AS carried_version_uid, cv.version_ordinal AS carried_version_ordinal
    FROM optimisation_proposal_decision d
    JOIN optimisation_proposal p ON p.optimisation_proposal_id = d.optimisation_proposal_id
    LEFT JOIN optimisation_proposal_decision cd ON cd.proposal_decision_id = d.carried_from_decision_id
    LEFT JOIN optimisation_proposal cq ON cq.optimisation_proposal_id = cd.optimisation_proposal_id
    LEFT JOIN optimisation_pass cp ON cp.optimisation_pass_id = cq.optimisation_pass_id
    LEFT JOIN document_version cv ON cv.version_uid = cp.version_uid
    JOIN optimisation_pass s ON s.optimisation_pass_id = p.optimisation_pass_id
    JOIN project pr ON pr.project_uid = s.project_uid
    JOIN document doc ON doc.document_uid = s.document_uid
    LEFT JOIN version_classification_current c ON c.version_uid = s.version_uid
    WHERE (CAST(:project_uid AS text) IS NULL OR s.project_uid = CAST(:project_uid AS text))
    ORDER BY d.decided_at DESC, d.proposal_decision_id COLLATE "C" DESC
    """
)


@dataclass(frozen=True, slots=True)
class ProposalJournalEntry:
    proposal_decision_id: str
    optimisation_proposal_id: str
    verdict: str
    comment: str | None
    actor_user_uid: str
    decided_at: datetime
    optimisation_pass_id: str
    row_text: str
    proposed_vendor: str
    unit: str
    project_uid: str
    project_name: str
    document_uid: str
    document_name: str
    version_uid: str
    section: str | None
    #: `D-335`: where a decision carried over from an earlier version's pass came from; ``None`` for one made directly.
    carried_from: CarriedFromRecord | None = None


def proposal_decision_journal(session: Session, *, project_uid: str | None = None) -> tuple[ProposalJournalEntry, ...]:
    """Every decision on an optimisation proposal, newest first, optionally of one project."""
    rows = session.execute(_JOURNAL, {"project_uid": project_uid}).mappings()
    return tuple(
        ProposalJournalEntry(
            proposal_decision_id=row["proposal_decision_id"],
            optimisation_proposal_id=row["optimisation_proposal_id"],
            verdict=row["verdict"],
            comment=row["comment"],
            actor_user_uid=row["actor_user_uid"],
            decided_at=row["decided_at"],
            optimisation_pass_id=row["optimisation_pass_id"],
            row_text=row["row_text"],
            proposed_vendor=row["proposed_vendor"],
            unit=row["unit"],
            project_uid=row["project_uid"],
            project_name=row["project_name"],
            document_uid=row["document_uid"],
            document_name=row["document_name"],
            version_uid=row["version_uid"],
            section=row["section_code"],
            carried_from=(
                None if row["carried_decision_id"] is None else CarriedFromRecord(
                    proposal_decision_id=row["carried_decision_id"], optimisation_pass_id=row["carried_pass_id"],
                    version_uid=row["carried_version_uid"], version_ordinal=int(row["carried_version_ordinal"]),
                )
            ),
        )
        for row in rows
    )
