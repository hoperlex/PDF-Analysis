"""A pass's proposals as a workbook, and the experts' decisions loaded back from it (`UI-B-15`, contract 1.35.0).

The original's optimisation screen has «Загрузить решения»: the expert edits the exported table and loads it back. Ours
does the same by **proposal identity**, never by the display number «№»: the first column of the sheet «Предложения» is
«ID предложения» (the ``opr_`` identity), and :func:`import_proposal_decisions` reads «Решение эксперта» and «Комментарий»
back for the pass the file was exported from.

The workbook is the pass's own and nobody else's (:mod:`.reader` refuses a file that has no such sheet whole). Every cell is
an inline string, so a spreadsheet shows text that begins with ``=`` as text; the numbers the sheet states (prices, the
quantity, the saving) are the exact decimal text of the stored rows, never a float.

**What a row does.** A row whose «Решение эксперта» names a verdict different from the proposal's decision in force appends
one ordinary decision event, authored by the importer, through ``decide_optimisation_proposal`` -- exactly as the screen's
button does, under a key derived from the import's key, the pass, the row and the proposal. The labels are those of the
screen: «принято», «отклонено», «на доработку» (a comment is required, as everywhere) and «не решено», which over a
decision in force is its **withdrawal** (a ``revoke`` event, `UI-B-12`) and over a proposal nobody decided is nothing. A
blank cell keeps the decision in force. The same verdict with a new comment is a new event carrying the comment; the same
verdict with the comment it already has, or none, is ``unchanged``.

Every row that names an ID or a decision is reported -- ``recorded``, ``unchanged``, or ``refused`` with one
:data:`REFUSAL_REASONS` reason; a row with neither is not about a decision and is not reported. One keyed command covers the
whole file: the same key with the same file for the same pass and caller answers the stored report and appends nothing;
another file under that key is ``409 idempotency_key_reuse``. A failure while recording a row rolls the whole import back.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy.orm import Session

from auditmanager.access.public import ROLE_EXPERT
from auditmanager.exports.xlsx.reader import DecisionSheetRow, read_decision_sheet
from auditmanager.exports.xlsx.writer import (
    CONTENT_TYPE,
    _Cells,
    _FIXED_ZIP_TIME,
    _row,
    _sheet,
    _static_parts,
)
from auditmanager.ingest.public import CommandReplay, CommandRepository, CommandStarted, payload_fingerprint
from auditmanager.optimisation.public import (
    MAX_COMMENT_LENGTH,
    OptimisationProposalRecord,
    decide_optimisation_proposal,
    get_optimisation_pass,
    list_optimisation_proposals,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey

__all__ = [
    "COMMAND_TYPE",
    "DECISION_LABELS",
    "OUTCOMES",
    "PROPOSAL_COLUMNS",
    "PROPOSALS_SHEET",
    "REFUSAL_REASONS",
    "ImportedProposalRow",
    "ProposalDecisionImport",
    "export_proposals_xlsx",
    "import_proposal_decisions",
    "render_proposals_xlsx",
]

PROPOSALS_SHEET: Final[str] = "Предложения"
ID_COLUMN: Final[str] = "ID предложения"
DECISION_COLUMN: Final[str] = "Решение эксперта"
COMMENT_COLUMN: Final[str] = "Комментарий"
#: The sheet's columns; the identity first, then what a reader needs to decide, then the two columns that come back.
PROPOSAL_COLUMNS: Final[tuple[str, ...]] = (
    ID_COLUMN,
    "№",
    "Страница",
    "Позиция спецификации",
    "Сейчас в прайс-листе",
    "Дешёвый аналог",
    "Поставщик аналога",
    "Ед. изм.",
    "Количество",
    "Цена сейчас",
    "Цена аналога",
    "Валюта",
    "Экономия",
    DECISION_COLUMN,
    COMMENT_COLUMN,
)
_WIDTHS: Final[tuple[int, ...]] = (32, 7, 10, 54, 40, 40, 28, 10, 14, 14, 14, 9, 16, 22, 48)

#: The decision states as the workbook says them: the words of the screen's chips, which a spreadsheet user edits.
DECISION_LABELS: Final[Mapping[str, str]] = {
    "pending": "не решено",
    "accept": "принято",
    "reject": "отклонено",
    "revise": "на доработку",
}
_VERDICT_OF_LABEL: Final[Mapping[str, str]] = {label.casefold(): verdict for verdict, label in DECISION_LABELS.items()}

COMMAND_TYPE: Final[str] = "import_optimisation_proposal_decisions"
OUTCOMES: Final[tuple[str, ...]] = ("recorded", "unchanged", "refused")
#: Why a row was refused, in the order the checks run.
REFUSAL_REASONS: Final[tuple[str, ...]] = (
    "no_proposal_id",  # a decision without an ID
    "duplicate_proposal",  # the ID's second and later rows
    "unknown_proposal",  # no proposal of this pass carries the ID
    "unknown_decision",  # not one of the four labels
    "comment_required",  # «на доработку» without a comment
    "comment_too_long",  # a comment over the stored bound
)
_PAGE: Final[int] = 200
_PARTS: Final[tuple[str, ...]] = (
    "[Content_Types].xml",
    "_rels/.rels",
    "xl/workbook.xml",
    "xl/_rels/workbook.xml.rels",
    "xl/styles.xml",
    "xl/worksheets/sheet1.xml",
)


# -- the workbook ----------------------------------------------------------------------------------------------------


def _single_sheet_parts(sheet: bytes) -> dict[str, bytes]:
    """The static parts of the findings workbook, cut down to one sheet."""
    parts = _static_parts()
    parts["[Content_Types].xml"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    ).encode("utf-8")
    parts["xl/workbook.xml"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{PROPOSALS_SHEET}" sheetId="1" r:id="rId1"/></sheets></workbook>'
    ).encode("utf-8")
    parts["xl/_rels/workbook.xml.rels"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        "</Relationships>"
    ).encode("utf-8")
    parts["xl/worksheets/sheet1.xml"] = sheet
    return parts


def _decimal(value: Any) -> str:
    from auditmanager.optimisation.public import canonical_amount

    return "" if value is None else canonical_amount(value)


def _values(item: OptimisationProposalRecord) -> tuple[str | int, ...]:
    decision = None if item.current_verdict == "pending" else item.current_decision
    quantity = _decimal(item.quantity) or (item.quantity_text or "")
    return (
        item.optimisation_proposal_id,
        item.ordinal,
        item.page_number,
        item.row_text,
        item.matched_position.name,
        item.proposed_position.name,
        item.proposed_vendor,
        item.unit,
        quantity,
        _decimal(item.current_unit_price),
        _decimal(item.proposed_unit_price),
        item.currency,
        _decimal(item.saving),
        DECISION_LABELS[item.current_verdict],
        "" if decision is None or decision.comment is None else decision.comment,
    )


def render_proposals_xlsx(items: Sequence[OptimisationProposalRecord]) -> bytes:
    """The workbook: a header row and one row per proposal in the order given; the same bytes for the same rows."""
    cells = _Cells()
    rows = [_row(1, PROPOSAL_COLUMNS, 1, cells)]
    rows.extend(_row(index, _values(item), 0, cells) for index, item in enumerate(items, start=2))
    parts = _single_sheet_parts(_sheet(rows, _WIDTHS))
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in _PARTS:
            info = zipfile.ZipInfo(name, _FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 0
            info.external_attr = 0
            archive.writestr(info, parts[name])
    return output.getvalue()


def _every_proposal(
    session: Session, optimisation_pass_id: str, actor_roles: frozenset[str]
) -> tuple[OptimisationProposalRecord, ...]:
    """Every proposal of the pass in ordinal order, read in bounded pages (the pass must exist)."""
    collected: list[OptimisationProposalRecord] = []
    while True:
        page = list_optimisation_proposals(
            session, optimisation_pass_id=optimisation_pass_id, actor_roles=actor_roles, offset=len(collected), limit=_PAGE
        )
        collected.extend(page.items)
        if not page.items or len(collected) >= page.total:
            return tuple(collected)


def export_proposals_xlsx(session: Session, *, optimisation_pass_id: str, actor_roles: frozenset[str]) -> bytes:
    """The pass's proposals as a workbook. Reads only; an unknown pass is ``not_found``, an account with no role reads nothing."""
    get_optimisation_pass(session, optimisation_pass_id=optimisation_pass_id, actor_roles=actor_roles)
    return render_proposals_xlsx(_every_proposal(session, optimisation_pass_id, actor_roles))


# -- the way back ----------------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ImportedProposalRow:
    row: int
    outcome: str
    optimisation_proposal_id: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ProposalDecisionImport:
    optimisation_pass_id: str
    rows: tuple[ImportedProposalRow, ...]

    def count(self, outcome: str) -> int:
        return sum(1 for row in self.rows if row.outcome == outcome)


def _stored(report: ProposalDecisionImport) -> dict[str, Any]:
    return {
        "optimisation_pass_id": report.optimisation_pass_id,
        "rows": [
            {key: value for key, value in (("row", row.row), ("outcome", row.outcome),
                                           ("optimisation_proposal_id", row.optimisation_proposal_id),
                                           ("reason", row.reason)) if value is not None}
            for row in report.rows
        ],
    }


def _replayed(outcome: Mapping[str, Any]) -> ProposalDecisionImport:
    return ProposalDecisionImport(
        optimisation_pass_id=str(outcome["optimisation_pass_id"]),
        rows=tuple(
            ImportedProposalRow(row=int(item["row"]), outcome=str(item["outcome"]),
                                optimisation_proposal_id=item.get("optimisation_proposal_id"), reason=item.get("reason"))
            for item in outcome["rows"]
        ),
    )


def _row_key(import_key: str, optimisation_pass_id: str, row: DecisionSheetRow) -> str:
    """The key one row's decision is claimed under: derived, so a row is decided once however the import is retried."""
    digest = hashlib.sha256(f"{import_key}|{optimisation_pass_id}|{row.row}|{row.key}".encode()).hexdigest()
    return f"imp-{digest[:48]}"


def import_proposal_decisions(
    session: Session,
    *,
    optimisation_pass_id: str,
    content: bytes,
    idempotency_key: str,
    actor_uid: str,
    actor_roles: frozenset[str],
    commands: CommandRepository | None = None,
) -> ProposalDecisionImport:
    """Read the edited workbook and append the decisions it changes; one report row per decision row."""
    roles = frozenset(actor_roles)
    if ROLE_EXPERT not in roles:
        raise DomainError(
            ErrorCode.PERMISSION_DENIED,
            message="only an expert can load decisions on optimisation proposals",
            aggregate_type="OptimisationPass",
            required_capability="role:expert",
        )
    get_optimisation_pass(session, optimisation_pass_id=optimisation_pass_id, actor_roles=roles)
    ledger = commands or CommandRepository()
    claimed = ledger.begin(
        session,
        command_type=COMMAND_TYPE,
        idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint(
            {
                "command": "import_optimisation_proposal_decisions.v1",
                "optimisation_pass_id": optimisation_pass_id,
                "sha256": hashlib.sha256(content).hexdigest(),
                "actor_uid": actor_uid,
            }
        ),
    )
    if isinstance(claimed, CommandReplay):
        return _replayed(claimed.outcome)
    assert isinstance(claimed, CommandStarted)
    sheet = read_decision_sheet(
        content, sheet=PROPOSALS_SHEET, id_column=ID_COLUMN, decision_column=DECISION_COLUMN, comment_column=COMMENT_COLUMN
    )
    proposals = {item.optimisation_proposal_id: item for item in _every_proposal(session, optimisation_pass_id, roles)}
    report = ProposalDecisionImport(
        optimisation_pass_id=optimisation_pass_id,
        rows=tuple(_import(session, sheet, proposals, idempotency_key, optimisation_pass_id, actor_uid, roles)),
    )
    ledger.succeed(session, claimed.command_id, _stored(report))
    return report


def _import(
    session: Session,
    sheet: Sequence[DecisionSheetRow],
    proposals: Mapping[str, OptimisationProposalRecord],
    import_key: str,
    optimisation_pass_id: str,
    actor_uid: str,
    roles: frozenset[str],
) -> list[ImportedProposalRow]:
    seen: set[str] = set()
    report: list[ImportedProposalRow] = []

    def refuse(row: DecisionSheetRow, reason: str, *, known: bool = False) -> None:
        report.append(ImportedProposalRow(row.row, "refused", row.key if known else None, reason))

    for row in sheet:
        if not row.key:
            if row.decision:
                refuse(row, "no_proposal_id")
            continue
        identity = row.key
        if identity in seen:
            refuse(row, "duplicate_proposal", known=identity in proposals)
            continue
        seen.add(identity)
        proposal = proposals.get(identity)
        if proposal is None:
            refuse(row, "unknown_proposal")
            continue
        current = proposal.current_verdict
        target = _VERDICT_OF_LABEL.get(row.decision.casefold()) if row.decision else current
        if target is None:
            refuse(row, "unknown_decision", known=True)
            continue
        comment = " ".join(row.comment.split()) or None
        if comment is not None and len(comment) > MAX_COMMENT_LENGTH:
            refuse(row, "comment_too_long", known=True)
            continue
        standing = None if current == "pending" or proposal.current_decision is None else proposal.current_decision.comment
        if target == current:
            if target == "pending" or comment is None or comment == (standing or ""):
                report.append(ImportedProposalRow(row.row, "unchanged", identity))
                continue
            verdict = target
        elif target == "pending":
            verdict = "revoke"  # «не решено» over a decision in force is its withdrawal
        else:
            verdict = target
        if verdict == "revise" and comment is None:
            refuse(row, "comment_required", known=True)
            continue
        decide_optimisation_proposal(
            session,
            proposal_id=identity,
            verdict=verdict,
            comment=comment,
            idempotency_key=_row_key(import_key, optimisation_pass_id, row),
            actor_uid=actor_uid,
            actor_roles=roles,
        )
        report.append(ImportedProposalRow(row.row, "recorded", identity))
    return report
