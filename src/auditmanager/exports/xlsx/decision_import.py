"""Importing expert decisions from our own run workbook (`UI-PARITY-P0L`, ruling `R-151d`).

The original pdf-proverka reads «Решение эксперта» and «Причина отклонения» back from its own
Excel report by the finding's ID. Ours does the same by ``finding_uid``: the expert edits
«Решение эксперта» (принято / отклонено) and «Комментарий» in the workbook ``exportRunXlsx``
produced and loads it back for the same run (:mod:`.reader` refuses a foreign file whole). The
display number «№» is never a key.

Each row that changes something becomes an ordinary decision event authored by the importer,
appended through :func:`auditmanager.decisions.public.record_decision` exactly as
``appendDecision`` appends one: ``accept`` or ``reject`` carrying the row's comment when the
decision changes, a ``comment`` event when only the comment does. Nothing is ever revoked: the
ledger has no such event, so «не решено» or «нужен ручной разбор» over another decision is
refused. The severity columns are not read; a severity stays a decision taken on the screen.

Every row that names an ID or a decision is reported -- ``recorded``, ``unchanged``, or
``refused`` with one :data:`REFUSAL_REASONS` reason. A row with neither (a «также найдено»
row, a blank one) is not a row about a decision and is not reported.

One keyed command covers the whole import: the same key with the same file for the same run
and caller answers the stored report and appends nothing; another file under that key is
``409 idempotency_key_reuse``. The events are the history: each names its author.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.decisions.public import record_decision
from auditmanager.exports.xlsx.labels import VERDICT_LABELS
from auditmanager.exports.xlsx.reader import SheetRow, read_findings_sheet
from auditmanager.ingest.public import CommandReplay, CommandRepository, CommandStarted, payload_fingerprint
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey

__all__ = ["COMMAND_TYPE", "OUTCOMES", "REFUSAL_REASONS", "DecisionImport", "ImportedRow", "import_run_decisions"]

COMMAND_TYPE: Final[str] = "import_run_decisions"
OUTCOMES: Final[tuple[str, ...]] = ("recorded", "unchanged", "refused")
#: Why a row was refused, in the order the checks run.
REFUSAL_REASONS: Final[tuple[str, ...]] = (
    "no_finding_uid",  # a decision without an ID
    "duplicate_finding",  # the ID's second and later rows
    "unknown_finding",  # no published finding carries the ID
    "finding_not_in_run",  # another run's finding
    "unknown_decision",  # not one of the four labels
    "not_importable",  # «не решено» / «нужен ручной разбор» over another decision
)
#: The label a cell holds, case-folded, to the verdict: the labels the export writes.
_VERDICT_OF_LABEL: Final[Mapping[str, str]] = {label.casefold(): verdict for verdict, label in VERDICT_LABELS.items()}
_EVENT_OF_VERDICT: Final[Mapping[str, str]] = {"accepted": "accept", "rejected": "reject"}

_RUN = text("SELECT 1 FROM audit_run WHERE run_id = :run_id")
_FINDINGS = text(
    """
    SELECT f.finding_uid, f.allocated_by_run_id,
           COALESCE(f.canonical_observation_id, (
               SELECT min(o.finding_observation_id) FROM finding_observation o
                WHERE o.finding_uid = f.finding_uid HAVING count(*) = 1
           )) AS observation_id,
           cv.current_verdict, cv.latest_comment
      FROM finding f
      JOIN finding_current_verdict cv ON cv.finding_uid = f.finding_uid
     WHERE f.finding_uid = ANY(:finding_uids)
    """
)


@dataclass(frozen=True, slots=True)
class ImportedRow:
    row: int
    outcome: str
    finding_uid: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class DecisionImport:
    run_id: str
    rows: tuple[ImportedRow, ...]

    def count(self, outcome: str) -> int:
        return sum(1 for row in self.rows if row.outcome == outcome)


def _stored(report: DecisionImport) -> dict[str, Any]:
    return {
        "run_id": report.run_id,
        "rows": [
            {key: value for key, value in (("row", row.row), ("outcome", row.outcome),
                                           ("finding_uid", row.finding_uid), ("reason", row.reason))
             if value is not None}
            for row in report.rows
        ],
    }


def _replayed(outcome: Mapping[str, Any]) -> DecisionImport:
    return DecisionImport(
        run_id=str(outcome["run_id"]),
        rows=tuple(ImportedRow(row=int(item["row"]), outcome=str(item["outcome"]),
                               finding_uid=item.get("finding_uid"), reason=item.get("reason"))
                   for item in outcome["rows"]),
    )


def import_run_decisions(
    session: Session, *, run_id: str, content: bytes, idempotency_key: str, author_label: str,
    author_user_uid: str | None, commands: CommandRepository | None = None,
) -> DecisionImport:
    """Read the edited workbook and append the decisions it changes; one report row per decision row."""
    if session.execute(_RUN, {"run_id": run_id}).first() is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="AuditRun")
    ledger = commands or CommandRepository()
    claimed = ledger.begin(
        session, command_type=COMMAND_TYPE, idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint({
            "run_id": run_id, "sha256": hashlib.sha256(content).hexdigest(), "author_user_uid": author_user_uid,
        }),
    )
    if isinstance(claimed, CommandReplay):
        return _replayed(claimed.outcome)
    assert isinstance(claimed, CommandStarted)
    sheet = read_findings_sheet(content)
    report = DecisionImport(run_id=run_id, rows=tuple(_import(session, run_id, sheet, author_label, author_user_uid)))
    ledger.succeed(session, claimed.command_id, _stored(report))
    return report


def _refused(row: SheetRow, reason: str, *, known: bool = False) -> ImportedRow:
    """A refusal; the cell's ID is echoed only when it names a published finding."""
    return ImportedRow(row.row, "refused", finding_uid=row.finding_uid if known else None, reason=reason)


def _import(
    session: Session, run_id: str, sheet: Sequence[SheetRow], author_label: str, author_user_uid: str | None,
) -> list[ImportedRow]:
    named = sorted({row.finding_uid for row in sheet if row.finding_uid})
    known = {} if not named else {
        str(found["finding_uid"]): found for found in session.execute(_FINDINGS, {"finding_uids": named}).mappings()
    }
    seen: set[str] = set()
    report: list[ImportedRow] = []
    for row in sheet:
        if not row.finding_uid:
            if row.decision:
                report.append(_refused(row, "no_finding_uid"))
            continue
        uid = row.finding_uid
        if uid in seen:
            report.append(_refused(row, "duplicate_finding", known=uid in known))
            continue
        seen.add(uid)
        finding = known.get(uid)
        if finding is None or finding["observation_id"] is None:
            report.append(_refused(row, "unknown_finding"))
            continue
        if finding["allocated_by_run_id"] != run_id:
            report.append(_refused(row, "finding_not_in_run", known=True))
            continue
        current = str(finding["current_verdict"])
        target = _VERDICT_OF_LABEL.get(row.decision.casefold()) if row.decision else current
        if target is None:
            report.append(_refused(row, "unknown_decision", known=True))
            continue
        comment = row.comment or None
        if target == current:
            if comment is None or comment == (finding["latest_comment"] or "").strip():
                report.append(ImportedRow(row.row, "unchanged", finding_uid=uid))
                continue
            event = "comment"
        elif target in _EVENT_OF_VERDICT:
            event = _EVENT_OF_VERDICT[target]
        else:
            report.append(_refused(row, "not_importable", known=True))
            continue
        record_decision(
            session, finding_uid=uid, finding_observation_id=str(finding["observation_id"]), event_type=event,
            comment=comment, author_label=author_label, author_user_uid=author_user_uid, origin_kind="imported",
        )
        report.append(ImportedRow(row.row, "recorded", finding_uid=uid))
    return report
