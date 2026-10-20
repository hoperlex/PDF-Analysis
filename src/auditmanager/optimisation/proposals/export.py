"""The proposals CSV of one pass: computed on request, never stored, separate from findings.

The bytes follow the findings export's file conventions (``auditmanager.exports.serializer``)
-- UTF-8 with one byte-order mark, CRLF line endings, comma delimiter, RFC 4180 minimal
quoting, an empty cell for an absent value -- with one addition the findings file does not
make: **every cell is formula-escaped**. A cell whose text begins with ``=``, ``+``, ``-``,
``@``, a tab or a line break (after any leading spaces) gets a leading apostrophe, so a
spreadsheet shows the text instead of evaluating it. Row texts and names come from
uploaded drawings and price lists, which this system does not control; the numbers it
writes (prices, quantities, savings, similarity) are never negative, so no number is
altered by the rule.

One row per proposal in ordinal order, the pass's identities repeated on each row; the
header is written even for a pass with no proposals. A saving that is absent is an empty
cell -- never ``0``. Two exports of one pass with no new decision are byte-identical:
nothing here reads a clock, a locale or a random source.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Final

from sqlalchemy.orm import Session

from ..matching import canonical_amount
from .policy import AGGREGATE_OPTIMISATION_PROPOSAL, require_reader
from .queries import get_optimisation_pass
from .repository import OptimisationPassRecord, OptimisationProposalRecord, ProposalRepository

__all__ = [
    "BOM",
    "COLUMNS",
    "CONTENT_TYPE",
    "FORMULA_TRIGGERS",
    "ProposalsCsv",
    "escape_formula",
    "export_optimisation_proposals_csv",
    "render_proposals_csv",
]

COLUMNS: Final[tuple[str, ...]] = (
    "optimisation_pass_id",
    "project_uid",
    "document_uid",
    "version_uid",
    "run_id",
    "price_list_id",
    "vendor_list_id",
    "generator_version",
    "optimisation_proposal_id",
    "ordinal",
    "proposal_type",
    "page_number",
    "sheet_label",
    "line_start",
    "line_end",
    "row_position",
    "row_text",
    "matched_position_id",
    "matched_name",
    "matched_code",
    "matched_mark",
    "matched_vendor",
    "matched_basis",
    "proposed_position_id",
    "proposed_name",
    "proposed_code",
    "proposed_mark",
    "proposed_vendor",
    "analog_basis",
    "name_similarity",
    "unit",
    "quantity",
    "quantity_text",
    "current_unit_price",
    "proposed_unit_price",
    "currency",
    "saving",
    "rationale",
    "current_decision",
    "decision_comment",
    "decided_by_user_uid",
    "decided_at",
)

BOM: Final[bytes] = b"\xef\xbb\xbf"
CONTENT_TYPE: Final[str] = "text/csv; charset=utf-8"
FORMULA_TRIGGERS: Final[frozenset[str]] = frozenset({"=", "+", "-", "@", "\t", "\r", "\n"})

_PAGE: Final[int] = 200


@dataclass(frozen=True, slots=True)
class ProposalsCsv:
    """The rendered export. A value, not a record: nothing names or stores it."""

    optimisation_pass_id: str
    content: bytes
    content_type: str = CONTENT_TYPE


def escape_formula(text: str) -> str:
    """The text, with a leading apostrophe when a spreadsheet would read it as a formula."""
    stripped = text.lstrip(" ")
    if text and (text[0] in FORMULA_TRIGGERS or stripped[:1] in FORMULA_TRIGGERS):
        return "'" + text
    return text


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):  # pragma: no cover - no boolean column
        return "true" if value else "false"
    if isinstance(value, Decimal):
        return escape_formula(canonical_amount(value))
    if isinstance(value, datetime):
        moment = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return escape_formula(str(value))


def _row(header: OptimisationPassRecord, item: OptimisationProposalRecord) -> tuple[str, ...]:
    matched, proposed, decision = item.matched_position, item.proposed_position, item.current_decision
    values = (
        header.optimisation_pass_id,
        header.project_uid,
        header.document_uid,
        header.version_uid,
        header.run_id,
        header.price_list_id,
        header.vendor_list_id,
        header.generator_version,
        item.optimisation_proposal_id,
        item.ordinal,
        item.proposal_type,
        item.page_number,
        item.sheet_label,
        item.line_start,
        item.line_end,
        item.row_position,
        item.row_text,
        matched.price_list_position_id,
        matched.name,
        matched.code,
        matched.mark,
        matched.vendor,
        item.matched_basis,
        proposed.price_list_position_id,
        proposed.name,
        proposed.code,
        proposed.mark,
        item.proposed_vendor,
        item.analog_basis,
        item.name_similarity,
        item.unit,
        item.quantity,
        item.quantity_text,
        item.current_unit_price,
        item.proposed_unit_price,
        item.currency,
        item.saving,
        item.rationale,
        item.current_verdict,
        None if decision is None else decision.comment,
        None if decision is None else decision.actor_user_uid,
        None if decision is None else decision.decided_at,
    )
    return tuple(_cell(value) for value in values)


def render_proposals_csv(
    header: OptimisationPassRecord, items: tuple[OptimisationProposalRecord, ...]
) -> bytes:
    """The exact bytes: BOM, header row, one row per proposal in the order given."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(
        buffer, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n"
    )
    writer.writerow(COLUMNS)
    for item in items:
        writer.writerow(_row(header, item))
    return BOM + buffer.getvalue().encode("utf-8")


def export_optimisation_proposals_csv(
    session: Session,
    *,
    optimisation_pass_id: str,
    actor_roles: frozenset[str],
    repository: ProposalRepository | None = None,
) -> ProposalsCsv:
    """Every proposal of one pass as CSV. Reads only; the caller owns the transaction."""
    roles = frozenset(actor_roles)
    require_reader(roles, aggregate_type=AGGREGATE_OPTIMISATION_PROPOSAL)
    repository = repository or ProposalRepository()
    header = get_optimisation_pass(
        session, optimisation_pass_id=optimisation_pass_id, actor_roles=roles, repository=repository
    )
    items: list[OptimisationProposalRecord] = []
    while True:
        page, total = repository.proposal_page(
            session,
            pass_id=header.optimisation_pass_id,
            decision=None,
            offset=len(items),
            limit=_PAGE,
        )
        items.extend(page)
        if not page or len(items) >= total:
            break
    return ProposalsCsv(
        optimisation_pass_id=header.optimisation_pass_id,
        content=render_proposals_csv(header, tuple(items)),
    )
