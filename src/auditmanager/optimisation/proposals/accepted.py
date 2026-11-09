"""The accepted optimisation decisions of a section's projects (`UI-B-27`, «Принято»).

The original's section-optimisation screen has a tab of the experts' accepted optimisations -- its «библиотека
опыта». Ours lists the proposals whose **decision in force is an acceptance**: the latest event of the proposal is an
``accept`` (a ``reject``, a ``revise``, a withdrawal that followed it, or no decision at all is not an acceptance and
is not listed). Every pass is read, so a proposal accepted in an earlier pass stays in the library; each row names its
pass, version and project, and a proposal is identified by its own ``opr_`` identity, never by its position in a pass.

The two filters are filters and not parents: ``project_uid`` narrows to one project and ``section`` to the versions an
expert confirmed in that section (``version_classification_current``). Newest acceptance first, then the decision id,
so the order is total and a page can be resumed by a cursor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdentityError, ProjectUid

from .generator import saving_percent_for
from .policy import AGGREGATE_OPTIMISATION_PROPOSAL, VERDICT_ACCEPT, require_reader
from .repository import CarriedFromRecord

__all__ = ["AcceptedProposal", "list_accepted_proposals"]

_ACCEPTED = text(
    """
    SELECT
        q.optimisation_proposal_id, q.optimisation_pass_id, q.proposal_type, q.page_number, q.row_position, q.row_text,
        q.proposed_vendor, q.unit, q.quantity, q.current_unit_price, q.proposed_unit_price, q.currency, q.saving,
        m.name AS matched_name, p.name AS proposed_name,
        cur.proposal_decision_id, cur.comment, cur.actor_user_uid, cur.decided_at,
        cd.proposal_decision_id AS carried_decision_id, cq.optimisation_pass_id AS carried_pass_id,
        cp.version_uid AS carried_version_uid, cv.version_ordinal AS carried_version_ordinal,
        s.project_uid, pr.name AS project_name, s.document_uid, doc.display_title AS document_name, s.version_uid,
        c.section_code
    FROM optimisation_proposal q
    JOIN LATERAL (
        SELECT d.proposal_decision_id, d.verdict, d.comment, d.actor_user_uid, d.decided_at, d.carried_from_decision_id
        FROM optimisation_proposal_decision d
        WHERE d.optimisation_proposal_id = q.optimisation_proposal_id
        ORDER BY d.seq DESC LIMIT 1
    ) cur ON cur.verdict = :accept
    LEFT JOIN optimisation_proposal_decision cd ON cd.proposal_decision_id = cur.carried_from_decision_id
    LEFT JOIN optimisation_proposal cq ON cq.optimisation_proposal_id = cd.optimisation_proposal_id
    LEFT JOIN optimisation_pass cp ON cp.optimisation_pass_id = cq.optimisation_pass_id
    LEFT JOIN document_version cv ON cv.version_uid = cp.version_uid
    JOIN optimisation_pass s ON s.optimisation_pass_id = q.optimisation_pass_id
    JOIN price_list_position m ON m.price_list_position_id = q.matched_position_id
    JOIN price_list_position p ON p.price_list_position_id = q.proposed_position_id
    JOIN project pr ON pr.project_uid = s.project_uid
    JOIN document doc ON doc.document_uid = s.document_uid
    LEFT JOIN version_classification_current c ON c.version_uid = s.version_uid
    WHERE (CAST(:project_uid AS text) IS NULL OR s.project_uid = CAST(:project_uid AS text))
      AND (CAST(:section AS text) IS NULL OR c.section_code = CAST(:section AS text))
    ORDER BY cur.decided_at DESC, cur.proposal_decision_id COLLATE "C" DESC
    """
)


@dataclass(frozen=True, slots=True)
class AcceptedProposal:
    optimisation_proposal_id: str
    optimisation_pass_id: str
    proposal_decision_id: str
    proposal_type: str
    project_uid: str
    project_name: str
    document_uid: str
    document_name: str
    version_uid: str
    section: str | None
    page_number: int
    row_position: str | None
    row_text: str
    matched_name: str
    proposed_name: str
    proposed_vendor: str
    unit: str
    quantity: Decimal | None
    current_unit_price: Decimal
    proposed_unit_price: Decimal
    currency: str
    saving: Decimal | None
    comment: str | None
    actor_user_uid: str
    decided_at: datetime
    #: `D-335`: where an acceptance carried over from an earlier version's pass came from; ``None`` for one made directly.
    carried_from: CarriedFromRecord | None = None
    #: `D-346` (contract 1.43.0): the percent the proposed unit price is below the current one, the very figure the proposals
    #: read states (:func:`saving_percent_for` over the two stored prices); ``None`` only at a zero current price. It does not
    #: wait for a numeric quantity, so it is present where ``saving`` is ``None``.
    saving_percent: Decimal | None = None


def _decimal(value: Any) -> Decimal | None:
    return None if value is None else Decimal(value)


def list_accepted_proposals(
    session: Session,
    *,
    actor_roles: frozenset[str],
    project_uid: str | None = None,
    section: str | None = None,
) -> tuple[AcceptedProposal, ...]:
    """Every proposal whose decision in force is an acceptance, newest acceptance first.

    ``project_uid`` and ``section`` are filters: a project or a section nothing was accepted in yields nothing, not
    ``not_found``. A malformed project identity is ``validation_failed``; an account with no role reads nothing
    (``permission_denied``, `R-80`).
    """
    require_reader(frozenset(actor_roles), aggregate_type=AGGREGATE_OPTIMISATION_PROPOSAL)
    project: str | None = None
    if project_uid is not None:
        try:
            project = str(ProjectUid.parse(project_uid))
        except (IdentityError, TypeError):
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="project_uid", constraint="pattern") from None
    rows = session.execute(
        _ACCEPTED, {"accept": VERDICT_ACCEPT, "project_uid": project, "section": section}
    ).mappings()
    return tuple(
        AcceptedProposal(
            optimisation_proposal_id=row["optimisation_proposal_id"],
            optimisation_pass_id=row["optimisation_pass_id"],
            proposal_decision_id=row["proposal_decision_id"],
            proposal_type=row["proposal_type"],
            project_uid=row["project_uid"],
            project_name=row["project_name"],
            document_uid=row["document_uid"],
            document_name=row["document_name"],
            version_uid=row["version_uid"],
            section=row["section_code"],
            page_number=int(row["page_number"]),
            row_position=row["row_position"],
            row_text=row["row_text"],
            matched_name=row["matched_name"],
            proposed_name=row["proposed_name"],
            proposed_vendor=row["proposed_vendor"],
            unit=row["unit"],
            quantity=_decimal(row["quantity"]),
            current_unit_price=Decimal(row["current_unit_price"]),
            proposed_unit_price=Decimal(row["proposed_unit_price"]),
            currency=row["currency"],
            saving=_decimal(row["saving"]),
            saving_percent=saving_percent_for(
                current_unit_price=Decimal(row["current_unit_price"]), proposed_unit_price=Decimal(row["proposed_unit_price"]),
            ),
            comment=row["comment"],
            actor_user_uid=row["actor_user_uid"],
            decided_at=row["decided_at"],
            carried_from=(
                None if row["carried_decision_id"] is None else CarriedFromRecord(
                    proposal_decision_id=row["carried_decision_id"], optimisation_pass_id=row["carried_pass_id"],
                    version_uid=row["carried_version_uid"], version_ordinal=int(row["carried_version_ordinal"]),
                )
            ),
        )
        for row in rows
    )
