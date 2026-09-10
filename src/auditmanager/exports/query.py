"""The one read the CSV is built from: one row per evidence item, in the frozen order.

The grounding rule, preserved exactly
-------------------------------------
``finding_observation`` is reached through an **inner join on ``finding``**. That is the
whole safety argument and it is copied verbatim from
:mod:`auditmanager.findings.queries`, for the reason that module states: an ungrounded
observation carries ``finding_uid IS NULL``, so the join drops it. There is no
``WHERE grounded = true`` here, because a ``WHERE`` clause is something a later edit has
to remember and a join through the identity table is not. ``B4`` enforces the pairing at
the database level and **this query does not defeat it** — P02 §5.1 requires that an
ungrounded observation appear in no CSV row, and the join is how that is true by
construction.

``tests/integration/exports`` cross-checks the count this query produces against
``findings.queries.published_finding_count`` for the same run, so a future edit that
loosened the join would redden rather than quietly widen the export.

Why this module contains SQL at all
-----------------------------------
Seven of the seventeen frozen columns are not projected by any existing public query.
``findings.queries.published_findings`` returns neither ``finding.project_uid``,
``finding.version_uid``, ``finding.allocated_by_run_id`` nor ``finding.category``, and
nothing anywhere projects ``document_version.document_uid``, ``audit_run.state`` or
``audit_run.provider_mode`` alongside a finding. Sourcing those four ``finding`` columns
from ``audit_run`` instead — where PC-01 happens to hold equal values — would silently
substitute a different source for columns P02 §6 pins to ``finding``. This gap is
reported to the seam owner rather than papered over; the query below is written to match
``findings.queries``' join shape exactly so that the two cannot disagree about what
"published" means.

Determinism
-----------
The sort key is ``(finding_uid, finding_observation_id, evidence_ordinal)`` ascending on
the opaque identifiers, and the text columns are ordered ``COLLATE "C"``. The collation
is explicit because the database's default collation is an environment property, and
"two exports of an unchanged run are byte-identical" must not depend on one. ULID bodies
are drawn from a fixed uppercase alphabet, so ``C`` ordering is also the natural one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

_RUN_HEADER = text(
    """
    SELECT state, provider_mode
    FROM audit_run
    WHERE run_id = :run_id
    """
)

_EXPORT_ROWS = text(
    """
    SELECT
        f.project_uid                AS project_uid,
        dv.document_uid              AS document_uid,
        f.version_uid                AS version_uid,
        f.allocated_by_run_id        AS run_id,
        r.state                      AS run_state,
        r.provider_mode              AS provider_mode,
        f.finding_uid                AS finding_uid,
        o.finding_observation_id     AS finding_observation_id,
        f.category                   AS category,
        o.finding_text               AS finding_text,
        o.recommendation_text        AS recommendation_text,
        e.page_number                AS evidence_page,
        e.quote                      AS evidence_quote,
        cv.current_verdict           AS current_verdict,
        cv.latest_comment            AS latest_comment,
        cv.latest_decision_id        AS latest_decision_id,
        cv.decision_recorded_at      AS decision_recorded_at,
        e.evidence_ordinal           AS evidence_ordinal
    FROM finding_observation o
    JOIN finding f
      ON f.finding_uid = o.finding_uid
    JOIN finding_evidence e
      ON e.finding_observation_id = o.finding_observation_id
    JOIN document_version dv
      ON dv.version_uid = f.version_uid
    JOIN audit_run r
      ON r.run_id = o.run_id
    LEFT JOIN finding_current_verdict cv
      ON cv.finding_uid = f.finding_uid
    WHERE o.run_id = :run_id
    ORDER BY
        f.finding_uid COLLATE "C" ASC,
        o.finding_observation_id COLLATE "C" ASC,
        e.evidence_ordinal ASC
    """
)


@dataclass(frozen=True, slots=True)
class RunHeader:
    """The two run-level values the CSV carries, and the policy discriminator's input."""

    state: str
    provider_mode: str


@dataclass(frozen=True, slots=True)
class ExportRow:
    """One evidence item, with everything the seventeen columns need.

    ``evidence_ordinal`` is carried but is **not** a column: P02 §6 uses it to order the
    rows of one observation and nothing else.
    """

    project_uid: str
    document_uid: str
    version_uid: str
    run_id: str
    run_state: str
    provider_mode: str
    finding_uid: str
    finding_observation_id: str
    category: str
    finding_text: str
    recommendation_text: str | None
    evidence_page: int
    evidence_quote: str
    current_verdict: str | None
    latest_comment: str | None
    latest_decision_id: str | None
    decision_recorded_at: datetime | None
    evidence_ordinal: int


def run_header(session: Session, run_id: str) -> RunHeader | None:
    """The run's state and provider mode, or ``None`` when no such run exists."""
    row = session.execute(_RUN_HEADER, {"run_id": run_id}).mappings().first()
    if row is None:
        return None
    return RunHeader(state=row["state"], provider_mode=row["provider_mode"])


def export_rows(session: Session, run_id: str) -> tuple[ExportRow, ...]:
    """Every CSV row of one run, already in the frozen sort order."""
    rows = session.execute(_EXPORT_ROWS, {"run_id": run_id}).mappings().all()
    return tuple(
        ExportRow(
            project_uid=row["project_uid"],
            document_uid=row["document_uid"],
            version_uid=row["version_uid"],
            run_id=row["run_id"],
            run_state=row["run_state"],
            provider_mode=row["provider_mode"],
            finding_uid=row["finding_uid"],
            finding_observation_id=row["finding_observation_id"],
            category=row["category"],
            finding_text=row["finding_text"],
            recommendation_text=row["recommendation_text"],
            evidence_page=int(row["evidence_page"]),
            evidence_quote=row["evidence_quote"],
            current_verdict=row["current_verdict"],
            latest_comment=row["latest_comment"],
            latest_decision_id=row["latest_decision_id"],
            decision_recorded_at=row["decision_recorded_at"],
            evidence_ordinal=int(row["evidence_ordinal"]),
        )
        for row in rows
    )


__all__ = ["ExportRow", "RunHeader", "export_rows", "run_header"]
