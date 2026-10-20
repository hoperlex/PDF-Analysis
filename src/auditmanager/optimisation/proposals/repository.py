"""Statements over the three tables of migration ``0027_optimisation_proposals``. No rule here.

Writers serialise on transaction advisory locks -- one per document version for passes, one
per proposal for decisions -- so two concurrent starts of the same inputs never both insert
(the natural-key unique constraint is the backstop) and two concurrent decisions never take
the same ``seq`` (the unique pair is the backstop). The locks are released at commit or
rollback.

Proposals are written with one statement per chunk: the rows travel as one JSON array and
``jsonb_to_recordset`` expands them; every price, quantity and saving reaches ``numeric`` from
its exact decimal text, never through a float.

The current decision of a proposal is its highest ``seq``; it is read, never stored.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..matching import canonical_amount
from .generator import ProposalDraft
from .identity import OptimisationPassId, OptimisationProposalId, ProposalDecisionId
from .policy import DECISION_PENDING, VERDICTS

__all__ = [
    "OptimisationPassRecord",
    "OptimisationProposalRecord",
    "PositionSummary",
    "ProposalDecisionRecord",
    "ProposalRepository",
]

_PROPOSAL_CHUNK: Final[int] = 2000

_COUNTS = (
    "(SELECT jsonb_object_agg(k.verdict, k.n) FROM ("
    "  SELECT COALESCE(cur.verdict, 'pending') AS verdict, count(*) AS n "
    "  FROM optimisation_proposal q "
    "  LEFT JOIN LATERAL (SELECT d.verdict FROM optimisation_proposal_decision d "
    "    WHERE d.optimisation_proposal_id = q.optimisation_proposal_id "
    "    ORDER BY d.seq DESC LIMIT 1) cur ON TRUE "
    "  WHERE q.optimisation_pass_id = s.optimisation_pass_id "
    "  GROUP BY 1) k) AS decision_counts"
)
_PASS_COLUMNS = (
    "s.optimisation_pass_id, s.project_uid, s.document_uid, s.version_uid, s.run_id, "
    "s.text_layer_sha256, s.price_list_id, s.vendor_list_id, s.vendor_list_source, "
    "s.extraction_algorithm, s.match_algorithm, s.generator_version, "
    "s.specification_row_count, s.matched_row_count, s.proposed_row_count, s.proposal_count, "
    f"s.started_by_user_uid, s.started_at, {_COUNTS}"
)
_SELECT_PASS = text(
    f"SELECT {_PASS_COLUMNS} FROM optimisation_pass s WHERE s.optimisation_pass_id = :id"
)
_FIND_PASS = text(
    f"SELECT {_PASS_COLUMNS} FROM optimisation_pass s "
    "WHERE s.version_uid = :version AND s.run_id = :run AND s.price_list_id = :price_list "
    "AND s.vendor_list_id = :vendor_list AND s.extraction_algorithm = :extraction "
    "AND s.match_algorithm = :match AND s.generator_version = :generator"
)
_LIST_PASSES = text(
    f"SELECT {_PASS_COLUMNS} FROM optimisation_pass s "
    "WHERE s.project_uid = :project "
    "AND (CAST(:document AS text) IS NULL OR s.document_uid = CAST(:document AS text)) "
    "ORDER BY s.started_at DESC, s.optimisation_pass_id DESC LIMIT :limit"
)
_LOCK_VERSION = text(
    "SELECT pg_advisory_xact_lock(hashtextextended("
    "'auditmanager.optimisation_pass|' || :version, 0))"
)
_INSERT_PASS = text(
    "INSERT INTO optimisation_pass (optimisation_pass_id, project_uid, document_uid, "
    "version_uid, run_id, text_layer_sha256, price_list_id, vendor_list_id, "
    "vendor_list_source, extraction_algorithm, match_algorithm, generator_version, "
    "specification_row_count, matched_row_count, proposed_row_count, proposal_count, "
    "started_by_user_uid) VALUES (:optimisation_pass_id, :project_uid, :document_uid, "
    ":version_uid, :run_id, :text_layer_sha256, :price_list_id, :vendor_list_id, "
    ":vendor_list_source, :extraction_algorithm, :match_algorithm, :generator_version, "
    ":specification_row_count, :matched_row_count, :proposed_row_count, :proposal_count, "
    ":started_by_user_uid)"
)
_INSERT_PROPOSALS = text(
    "INSERT INTO optimisation_proposal (optimisation_proposal_id, optimisation_pass_id, "
    "ordinal, proposal_type, spec_row_key, page_number, sheet_label, line_start, line_end, "
    "table_ordinal, row_position, row_text, matched_position_id, matched_basis, "
    "proposed_position_id, analog_basis, name_similarity, proposed_vendor, unit, quantity, "
    "quantity_text, current_unit_price, proposed_unit_price, currency, saving, rationale) "
    "SELECT r.id, :pass_id, r.ordinal, r.proposal_type, r.spec_row_key, r.page_number, "
    "r.sheet_label, r.line_start, r.line_end, r.table_ordinal, r.row_position, r.row_text, "
    "r.matched_position_id, r.matched_basis, r.proposed_position_id, r.analog_basis, "
    "CAST(r.name_similarity AS numeric), r.proposed_vendor, r.unit, "
    "CAST(r.quantity AS numeric), r.quantity_text, CAST(r.current_unit_price AS numeric), "
    "CAST(r.proposed_unit_price AS numeric), r.currency, CAST(r.saving AS numeric), "
    "r.rationale "
    "FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS r(id text, ordinal integer, "
    "proposal_type text, spec_row_key text, page_number integer, sheet_label text, "
    "line_start integer, line_end integer, table_ordinal integer, row_position text, "
    "row_text text, matched_position_id text, matched_basis text, proposed_position_id text, "
    "analog_basis text, name_similarity text, proposed_vendor text, unit text, quantity text, "
    "quantity_text text, current_unit_price text, proposed_unit_price text, currency text, "
    "saving text, rationale text)"
)
_PROPOSAL_COLUMNS = (
    "q.optimisation_proposal_id, q.optimisation_pass_id, q.ordinal, q.proposal_type, "
    "q.spec_row_key, q.page_number, q.sheet_label, q.line_start, q.line_end, "
    "q.table_ordinal, q.row_position, q.row_text, q.matched_basis, q.analog_basis, "
    "q.name_similarity, q.proposed_vendor, q.unit, q.quantity, q.quantity_text, "
    "q.current_unit_price, q.proposed_unit_price, q.currency, q.saving, q.rationale, "
    "m.price_list_position_id, m.row_number, m.code, m.name, m.mark, m.vendor, "
    "p.price_list_position_id, p.row_number, p.code, p.name, p.mark, p.vendor, "
    "cur.proposal_decision_id, cur.seq, cur.verdict, cur.comment, cur.actor_user_uid, "
    "cur.decided_at"
)
_PROPOSAL_FROM = (
    "FROM optimisation_proposal q "
    "JOIN price_list_position m ON m.price_list_position_id = q.matched_position_id "
    "JOIN price_list_position p ON p.price_list_position_id = q.proposed_position_id "
    "LEFT JOIN LATERAL (SELECT d.proposal_decision_id, d.seq, d.verdict, d.comment, "
    "  d.actor_user_uid, d.decided_at FROM optimisation_proposal_decision d "
    "  WHERE d.optimisation_proposal_id = q.optimisation_proposal_id "
    "  ORDER BY d.seq DESC LIMIT 1) cur ON TRUE "
)
_PROPOSAL_FILTER = (
    "WHERE q.optimisation_pass_id = :pass_id "
    "AND (CAST(:decision AS text) IS NULL "
    "  OR COALESCE(cur.verdict, 'pending') = CAST(:decision AS text)) "
)
_PROPOSAL_PAGE = text(
    f"SELECT {_PROPOSAL_COLUMNS} {_PROPOSAL_FROM} {_PROPOSAL_FILTER} "
    "ORDER BY q.ordinal LIMIT :limit OFFSET :offset"
)
_PROPOSAL_TOTAL = text(f"SELECT count(*) {_PROPOSAL_FROM} {_PROPOSAL_FILTER}")
_SELECT_PROPOSAL = text(
    f"SELECT {_PROPOSAL_COLUMNS} {_PROPOSAL_FROM} WHERE q.optimisation_proposal_id = :id"
)
_LOCK_PROPOSAL = text(
    "SELECT pg_advisory_xact_lock(hashtextextended("
    "'auditmanager.optimisation_proposal|' || :proposal, 0))"
)
_NEXT_SEQ = text(
    "SELECT COALESCE(max(seq), 0) + 1 FROM optimisation_proposal_decision "
    "WHERE optimisation_proposal_id = :proposal"
)
_INSERT_DECISION = text(
    "INSERT INTO optimisation_proposal_decision (proposal_decision_id, "
    "optimisation_proposal_id, seq, verdict, comment, actor_user_uid, command_id) "
    "VALUES (:id, :proposal, :seq, :verdict, :comment, :actor, :command)"
)
_DECISION_COLUMNS = (
    "proposal_decision_id, optimisation_proposal_id, seq, verdict, comment, actor_user_uid, "
    "decided_at"
)
_DECISION_BY_ID = text(
    f"SELECT {_DECISION_COLUMNS} FROM optimisation_proposal_decision "
    "WHERE proposal_decision_id = :id"
)
_DECISION_BY_COMMAND = text(
    f"SELECT {_DECISION_COLUMNS} FROM optimisation_proposal_decision WHERE command_id = :command"
)
_DECISION_HISTORY = text(
    f"SELECT {_DECISION_COLUMNS} FROM optimisation_proposal_decision "
    "WHERE optimisation_proposal_id = :proposal ORDER BY seq"
)


@dataclass(frozen=True, slots=True)
class OptimisationPassRecord:
    """One stored pass. ``decision_counts`` covers every proposal: pending and each verdict."""

    optimisation_pass_id: str
    project_uid: str
    document_uid: str
    version_uid: str
    run_id: str
    text_layer_sha256: str
    price_list_id: str
    vendor_list_id: str
    vendor_list_source: str
    extraction_algorithm: str
    match_algorithm: str
    generator_version: str
    specification_row_count: int
    matched_row_count: int
    proposed_row_count: int
    proposal_count: int
    started_by_user_uid: str
    started_at: datetime
    decision_counts: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class PositionSummary:
    """The price-list position a proposal names, as the revision stores it."""

    price_list_position_id: str
    row_number: int
    code: str | None
    name: str
    mark: str | None
    vendor: str | None


@dataclass(frozen=True, slots=True)
class ProposalDecisionRecord:
    """One appended decision. ``seq`` orders a proposal's decisions; it is not an identity."""

    proposal_decision_id: str
    optimisation_proposal_id: str
    seq: int
    verdict: str
    comment: str | None
    actor_user_uid: str
    decided_at: datetime


@dataclass(frozen=True, slots=True)
class OptimisationProposalRecord:
    """One stored proposal with its two positions and its current decision (``None``: pending)."""

    optimisation_proposal_id: str
    optimisation_pass_id: str
    ordinal: int
    proposal_type: str
    spec_row_key: str
    page_number: int
    sheet_label: str | None
    line_start: int
    line_end: int
    table_ordinal: int
    row_position: str | None
    row_text: str
    matched_basis: str
    analog_basis: str
    name_similarity: Decimal
    proposed_vendor: str
    unit: str
    quantity: Decimal | None
    quantity_text: str | None
    current_unit_price: Decimal
    proposed_unit_price: Decimal
    currency: str
    saving: Decimal | None
    rationale: str
    matched_position: PositionSummary
    proposed_position: PositionSummary
    current_decision: ProposalDecisionRecord | None

    @property
    def current_verdict(self) -> str:
        return DECISION_PENDING if self.current_decision is None else self.current_decision.verdict


def _counts(raw: Any) -> dict[str, int]:
    if isinstance(raw, str):  # pragma: no cover - psycopg decodes jsonb
        raw = json.loads(raw)
    stored = {str(key): int(value) for key, value in dict(raw or {}).items()}
    return {key: stored.get(key, 0) for key in (DECISION_PENDING, *VERDICTS)}


def _pass(row: Any) -> OptimisationPassRecord:
    values = tuple(row)
    return OptimisationPassRecord(
        optimisation_pass_id=values[0],
        project_uid=values[1],
        document_uid=values[2],
        version_uid=values[3],
        run_id=values[4],
        text_layer_sha256=values[5],
        price_list_id=values[6],
        vendor_list_id=values[7],
        vendor_list_source=values[8],
        extraction_algorithm=values[9],
        match_algorithm=values[10],
        generator_version=values[11],
        specification_row_count=int(values[12]),
        matched_row_count=int(values[13]),
        proposed_row_count=int(values[14]),
        proposal_count=int(values[15]),
        started_by_user_uid=values[16],
        started_at=values[17],
        decision_counts=_counts(values[18]),
    )


def _decimal(value: Any) -> Decimal | None:
    return None if value is None else Decimal(value)


def _decision(values: Sequence[Any]) -> ProposalDecisionRecord:
    return ProposalDecisionRecord(
        proposal_decision_id=values[0],
        optimisation_proposal_id=values[1],
        seq=int(values[2]),
        verdict=values[3],
        comment=values[4],
        actor_user_uid=values[5],
        decided_at=values[6],
    )


def _proposal(row: Any) -> OptimisationProposalRecord:
    v = tuple(row)
    current = None
    if v[36] is not None:
        current = _decision((v[36], v[0], v[37], v[38], v[39], v[40], v[41]))
    return OptimisationProposalRecord(
        optimisation_proposal_id=v[0],
        optimisation_pass_id=v[1],
        ordinal=int(v[2]),
        proposal_type=v[3],
        spec_row_key=v[4],
        page_number=int(v[5]),
        sheet_label=v[6],
        line_start=int(v[7]),
        line_end=int(v[8]),
        table_ordinal=int(v[9]),
        row_position=v[10],
        row_text=v[11],
        matched_basis=v[12],
        analog_basis=v[13],
        name_similarity=Decimal(v[14]),
        proposed_vendor=v[15],
        unit=v[16],
        quantity=_decimal(v[17]),
        quantity_text=v[18],
        current_unit_price=Decimal(v[19]),
        proposed_unit_price=Decimal(v[20]),
        currency=v[21],
        saving=_decimal(v[22]),
        rationale=v[23],
        matched_position=PositionSummary(v[24], int(v[25]), v[26], v[27], v[28], v[29]),
        proposed_position=PositionSummary(v[30], int(v[31]), v[32], v[33], v[34], v[35]),
        current_decision=current,
    )


def _exact(value: Decimal | None) -> str | None:
    """A decimal as exact plain text for ``numeric``; never a float, never rounded."""
    return None if value is None else canonical_amount(value)


def _proposal_row(draft: ProposalDraft) -> dict[str, Any]:
    row = draft.row
    return {
        "id": str(OptimisationProposalId.new()),
        "ordinal": draft.ordinal,
        "proposal_type": draft.proposal_type,
        "spec_row_key": row.row_id,
        "page_number": row.page_number,
        "sheet_label": row.sheet_label,
        "line_start": row.line_start,
        "line_end": row.line_end,
        "table_ordinal": row.table_ordinal,
        "row_position": row.position,
        "row_text": row.name,
        "matched_position_id": draft.matched.price_list_position_id,
        "matched_basis": draft.matched_basis,
        "proposed_position_id": draft.proposed.price_list_position_id,
        "analog_basis": draft.analog_basis,
        "name_similarity": _exact(draft.similarity),
        "proposed_vendor": draft.proposed.vendor,
        "unit": draft.unit,
        "quantity": _exact(draft.quantity),
        "quantity_text": row.quantity_text,
        "current_unit_price": _exact(draft.current_unit_price),
        "proposed_unit_price": _exact(draft.proposed_unit_price),
        "currency": draft.currency,
        "saving": _exact(draft.saving),
        "rationale": draft.rationale,
    }


class ProposalRepository:
    """Write and read passes, proposals and proposal decisions."""

    __slots__ = ()

    # -- passes --------------------------------------------------------------

    def lock_version(self, session: Session, version_uid: str) -> None:
        session.execute(_LOCK_VERSION, {"version": version_uid})

    def find_pass(
        self,
        session: Session,
        *,
        version_uid: str,
        run_id: str,
        price_list_id: str,
        vendor_list_id: str,
        extraction_algorithm: str,
        match_algorithm: str,
        generator_version: str,
    ) -> OptimisationPassRecord | None:
        row = session.execute(
            _FIND_PASS,
            {
                "version": version_uid,
                "run": run_id,
                "price_list": price_list_id,
                "vendor_list": vendor_list_id,
                "extraction": extraction_algorithm,
                "match": match_algorithm,
                "generator": generator_version,
            },
        ).first()
        return None if row is None else _pass(row)

    def insert_pass(
        self,
        session: Session,
        *,
        pass_id: OptimisationPassId,
        project_uid: str,
        document_uid: str,
        version_uid: str,
        run_id: str,
        text_layer_sha256: str,
        price_list_id: str,
        vendor_list_id: str,
        vendor_list_source: str,
        extraction_algorithm: str,
        match_algorithm: str,
        generator_version: str,
        specification_row_count: int,
        matched_row_count: int,
        proposed_row_count: int,
        drafts: Sequence[ProposalDraft],
        started_by_user_uid: str,
    ) -> None:
        session.execute(
            _INSERT_PASS,
            {
                "optimisation_pass_id": str(pass_id),
                "project_uid": project_uid,
                "document_uid": document_uid,
                "version_uid": version_uid,
                "run_id": run_id,
                "text_layer_sha256": text_layer_sha256,
                "price_list_id": price_list_id,
                "vendor_list_id": vendor_list_id,
                "vendor_list_source": vendor_list_source,
                "extraction_algorithm": extraction_algorithm,
                "match_algorithm": match_algorithm,
                "generator_version": generator_version,
                "specification_row_count": specification_row_count,
                "matched_row_count": matched_row_count,
                "proposed_row_count": proposed_row_count,
                "proposal_count": len(drafts),
                "started_by_user_uid": started_by_user_uid,
            },
        )
        for start in range(0, len(drafts), _PROPOSAL_CHUNK):
            rows = [_proposal_row(draft) for draft in drafts[start : start + _PROPOSAL_CHUNK]]
            session.execute(
                _INSERT_PROPOSALS,
                {"pass_id": str(pass_id), "rows": json.dumps(rows, ensure_ascii=False)},
            )

    def get_pass(self, session: Session, pass_id: str) -> OptimisationPassRecord | None:
        row = session.execute(_SELECT_PASS, {"id": pass_id}).first()
        return None if row is None else _pass(row)

    def list_passes(
        self, session: Session, *, project_uid: str, document_uid: str | None, limit: int
    ) -> tuple[OptimisationPassRecord, ...]:
        rows = session.execute(
            _LIST_PASSES, {"project": project_uid, "document": document_uid, "limit": limit}
        ).all()
        return tuple(_pass(row) for row in rows)

    # -- proposals -----------------------------------------------------------

    def proposal_page(
        self,
        session: Session,
        *,
        pass_id: str,
        decision: str | None,
        offset: int,
        limit: int,
    ) -> tuple[tuple[OptimisationProposalRecord, ...], int]:
        parameters = {"pass_id": pass_id, "decision": decision}
        total = int(session.execute(_PROPOSAL_TOTAL, parameters).scalar_one())
        rows = session.execute(
            _PROPOSAL_PAGE, {**parameters, "offset": offset, "limit": limit}
        ).all()
        return tuple(_proposal(row) for row in rows), total

    def get_proposal(self, session: Session, proposal_id: str) -> OptimisationProposalRecord | None:
        row = session.execute(_SELECT_PROPOSAL, {"id": proposal_id}).first()
        return None if row is None else _proposal(row)

    # -- decisions -----------------------------------------------------------

    def lock_proposal(self, session: Session, proposal_id: str) -> None:
        session.execute(_LOCK_PROPOSAL, {"proposal": proposal_id})

    def next_seq(self, session: Session, proposal_id: str) -> int:
        return int(session.execute(_NEXT_SEQ, {"proposal": proposal_id}).scalar_one())

    def insert_decision(
        self,
        session: Session,
        *,
        decision_id: ProposalDecisionId,
        proposal_id: str,
        seq: int,
        verdict: str,
        comment: str | None,
        actor_user_uid: str,
        command_id: str,
    ) -> ProposalDecisionRecord:
        session.execute(
            _INSERT_DECISION,
            {
                "id": str(decision_id),
                "proposal": proposal_id,
                "seq": seq,
                "verdict": verdict,
                "comment": comment,
                "actor": actor_user_uid,
                "command": command_id,
            },
        )
        stored = self.get_decision(session, str(decision_id))
        if stored is None:  # pragma: no cover - inserted above in this transaction
            raise LookupError("the new decision is not readable")
        return stored

    def get_decision(self, session: Session, decision_id: str) -> ProposalDecisionRecord | None:
        row = session.execute(_DECISION_BY_ID, {"id": decision_id}).first()
        return None if row is None else _decision(tuple(row))

    def decision_by_command(self, session: Session, command_id: str) -> ProposalDecisionRecord | None:
        row = session.execute(_DECISION_BY_COMMAND, {"command": command_id}).first()
        return None if row is None else _decision(tuple(row))

    def decision_history(
        self, session: Session, proposal_id: str
    ) -> tuple[ProposalDecisionRecord, ...]:
        rows = session.execute(_DECISION_HISTORY, {"proposal": proposal_id}).all()
        return tuple(_decision(tuple(row)) for row in rows)
