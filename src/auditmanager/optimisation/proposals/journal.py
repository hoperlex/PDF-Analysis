"""The journal of expert decisions on optimisation proposals (`UI-PARITY-P0J`, ruling `R-151h`).

The original's knowledge base lists the expert's decisions on remarks and on optimisation proposals, with a «Тип»
filter. Ours lists the finding decisions through ``listDecisions``; this is the other half, ``listProposalDecisions``:
every appended ``optimisation_proposal_decision``, newest first, with where it belongs (project, document, version,
section) and what it decided about (the specification row, the proposed vendor). Optionally narrowed to one project,
which is a filter and not a parent: a project nothing was decided in yields nothing.

The decisions are read as appended: a later decision on the same proposal is another row, and the proposal's current
verdict is its latest one, as everywhere in the optimisation context.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

_JOURNAL = text(
    """
    SELECT
        d.proposal_decision_id, d.optimisation_proposal_id, d.verdict, d.comment, d.actor_user_uid, d.decided_at,
        p.optimisation_pass_id, p.row_text, p.proposed_vendor, p.unit,
        s.project_uid, pr.name AS project_name, s.document_uid, doc.display_title AS document_name, s.version_uid,
        c.section_code
    FROM optimisation_proposal_decision d
    JOIN optimisation_proposal p ON p.optimisation_proposal_id = d.optimisation_proposal_id
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
        )
        for row in rows
    )
