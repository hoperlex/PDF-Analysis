#!/usr/bin/env python3
"""PC-02 measurement tooling: read-only extraction over the PC-01 persistence schema.

This is the complete tool interface every later PC-02 consumer invokes. ``P4-BHV-01``
runs it session by session; ``P4-INT-01`` runs it unmodified over the closed validation
period. Both are forbidden from editing it, so every mode below is exercised by the
task that builds it.

**It adds no runtime instrumentation.** It extracts what the schema at the accepted
``PC-01`` commit already records. Where a ``PROTOTYPE_PROFILE.md`` §9 metric has no
producer, that is a gap-register entry, not a licence to add one.

Read-only is structural, not a promise
--------------------------------------
Three independent mechanics, because "the tool does not write" asserted by the absence
of an error is the vacuous shape this programme keeps finding:

1. the connection is opened and held in a ``READ ONLY`` transaction, so PostgreSQL
   itself refuses a write;
2. every statement passes through :class:`StatementLog`, which classifies it and
   **raises** on anything that is not a read — the log is then the positive evidence,
   not the lack of a traceback;
3. :func:`table_row_counts` is captured before and after every invocation and compared,
   so a write that somehow evaded both would still be caught by the row census.

Measured cost versus estimated cost
-----------------------------------
``model_call.cost_micros`` holds **either** the proxy's reported spend **or** a
``P02_LOCK.json`` rate-table estimate, and the schema records no discriminator. See
:func:`classify_cost_basis`: the basis is derived, and every figure this tool emits
carries the basis beside it. A measurement and an estimate presented identically is how
a report becomes uncitable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TOOL_VERSION = "1.0.0"
TOOL_ID = "P4-OPS-01/ledger_report"

#: ``tools/validation/ledger_report.py`` -> repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_GUARD = 3
EXIT_BLOCKED = 4


# ---------------------------------------------------------------------------
# 1. Read-only access, with a statement log that refuses rather than records
# ---------------------------------------------------------------------------

#: Leading keywords this tool is permitted to issue. A strict allowlist, not a
#: denylist of write verbs: a denylist passes whatever nobody thought to forbid.
_READ_KEYWORDS = frozenset({"select", "with", "show"})

#: The only non-read statement permitted, and only in this exact shape.
_READ_ONLY_PRAGMA = "set transaction read only"


class WriteAttempted(RuntimeError):
    """A statement that is not a read reached the connection."""


@dataclass
class StatementLog:
    """Every statement the tool issues, classified at issue time.

    ``--dry-run`` asserts against this log. The log is written by the same call path
    that talks to the database, so it cannot report a statement the database did not
    see, nor miss one the database did.
    """

    entries: list[dict[str, str]] = field(default_factory=list)

    def record(self, sql: str) -> None:
        kind = classify_statement(sql)
        self.entries.append({"kind": kind, "sql": _collapse(sql)})
        if kind != "read":
            raise WriteAttempted(
                f"ledger_report issued a non-read statement ({kind}): {_collapse(sql)}"
            )

    @property
    def writes(self) -> list[dict[str, str]]:
        return [entry for entry in self.entries if entry["kind"] != "read"]

    def summary(self) -> dict[str, Any]:
        return {
            "statements_issued": len(self.entries),
            "read_statements": len(self.entries) - len(self.writes),
            "write_statements": len(self.writes),
            "writes": self.writes,
        }


def _collapse(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip()


def classify_statement(sql: str) -> str:
    """``read``, ``pragma`` or the offending leading keyword.

    Comments are stripped first: a write hidden behind a leading ``/* select */`` would
    otherwise classify as a read.
    """
    stripped = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    stripped = re.sub(r"--[^\n]*", " ", stripped)
    collapsed = _collapse(stripped).lower()
    if collapsed.startswith(_READ_ONLY_PRAGMA):
        return "read"
    head = collapsed.split("(")[0].split()
    if not head:
        return "empty"
    keyword = head[0]
    if keyword in _READ_KEYWORDS:
        return "read"
    return keyword


class ReadOnlyDatabase:
    """A psycopg connection pinned read-only, with every statement logged."""

    def __init__(self, dsn: str, log: StatementLog) -> None:
        import psycopg  # locked dependency; never added by this task

        self._log = log
        self._conn = psycopg.connect(dsn, autocommit=False)
        # PostgreSQL refuses the write itself. Mechanism 1 of 3.
        self.execute(_READ_ONLY_PRAGMA.upper())

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
        self._log.record(sql)
        with self._conn.cursor() as cur:
            cur.execute(sql, params)  # type: ignore[arg-type]
            if cur.description is None:
                return []
            columns = [c.name for c in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def close(self) -> None:
        self._conn.rollback()
        self._conn.close()

    def __enter__(self) -> "ReadOnlyDatabase":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def load_dsn(env_path: Path | None = None) -> str:
    """``DATABASE_URL`` from ``.env``, as a DSN psycopg accepts.

    ``.env`` is parsed as data, never sourced. The stored URL carries SQLAlchemy's
    ``+psycopg`` driver tag, which libpq does not understand.
    """
    path = env_path or (REPO_ROOT / ".env")
    if not path.is_file():
        raise SystemExit(
            f"{TOOL_ID}: {path} is missing. The foundation environment is required "
            "for a read-only extraction. Run: cp .env.example .env"
        )
    url = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip().removeprefix("export ").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name.strip() == "DATABASE_URL":
            url = value.strip().strip('"').strip("'")
    if not url:
        raise SystemExit(f"{TOOL_ID}: DATABASE_URL is not set in {path}.")
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


#: Every table the PC-01 schema creates. The row census compares all of them, so a
#: write to a table this tool never reads is still caught.
CENSUS_TABLES = (
    "alembic_version",
    "audit_event",
    "audit_run",
    "blob",
    "command_record",
    "contract_state_transition",
    "document",
    "document_version",
    "expert_decision_event",
    "finding",
    "finding_evidence",
    "finding_observation",
    "input_manifest_entry",
    "model_call",
    "project",
    "stage_result",
)


def table_row_counts(db: ReadOnlyDatabase) -> dict[str, int]:
    """A row census over every table. Mechanism 3 of 3."""
    counts: dict[str, int] = {}
    for table in CENSUS_TABLES:
        rows = db.execute(f"SELECT count(*) AS n FROM {table}")  # noqa: S608 - fixed literals
        counts[table] = int(rows[0]["n"])
    return counts


def probe_column(db: ReadOnlyDatabase, table: str, column: str) -> dict[str, Any]:
    """Does this column exist, and does any row actually carry a value?

    The gap register's classifications are computed from this, never asserted as
    literals. A register that reports "persisted" for a column the database does not
    have, or holds no value for, would be asserting a property of the source it was
    written against rather than of the database in front of it — which is the exact
    vacuous shape this programme keeps finding. Emptying the table must be able to
    change the verdict, and because of this function it does.
    """
    exists = db.execute(
        "SELECT count(*) AS n FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = %s AND column_name = %s",
        [table, column],
    )
    if not int(exists[0]["n"]):
        return {"column": f"{table}.{column}", "exists": False, "rows": 0, "populated": 0}
    counts = db.execute(
        f"SELECT count(*) AS rows, count({column}) AS populated FROM {table}"  # noqa: S608
    )
    return {
        "column": f"{table}.{column}",
        "exists": True,
        "rows": int(counts[0]["rows"]),
        "populated": int(counts[0]["populated"]),
    }


def state_from_probe(*probes: Mapping[str, Any]) -> tuple[str, str]:
    """``persisted`` only when every column exists and at least one row carries it."""
    missing = [p["column"] for p in probes if not p["exists"]]
    if missing:
        return "absent", f"column(s) absent from the schema: {missing}"
    unpopulated = [p["column"] for p in probes if p["populated"] == 0]
    if unpopulated:
        if all(p["rows"] == 0 for p in probes):
            return (
                "absent",
                "the column exists but the table holds no rows, so nothing demonstrates "
                "a producer populates it; the preflight cannot promise this metric",
            )
        return "absent", f"column(s) present but never populated: {unpopulated}"
    return "persisted", "the column exists and rows carry values"


# ---------------------------------------------------------------------------
# 2. Observation classes
# ---------------------------------------------------------------------------

#: The eight reporting buckets this task defines. They are **not** codes from the
#: twenty-code domain catalog; the catalog code is recorded separately on every row.
OBSERVATION_CLASSES = (
    "provider_unavailable",
    "provider_timeout",
    "malformed_provider_response",
    "ungrounded_item_rejected",
    "unsupported_input",
    "checksum_failure",
    "application_or_process_crash",
    "other",
)

#: Catalog code -> observation class. Codes absent here fall to ``other``.
_CLASS_BY_CODE = {
    "dependency_unavailable": "provider_unavailable",
    "analysis_failed": "malformed_provider_response",
    "analysis_input_invalid": "unsupported_input",
    "unsupported_contract_version": "unsupported_input",
    "validation_failed": "unsupported_input",
    "partial_result_not_publishable": "ungrounded_item_rejected",
    "storage_integrity_error": "checksum_failure",
    "internal_error": "application_or_process_crash",
}

#: ``provider_timeout`` has no persisted discriminator: ``proxy.py`` maps both an
#: unreachable proxy and a 504 deadline onto ``dependency_unavailable``, and
#: ``model_call`` stores only the code. The stage error *message* separates them, so
#: it is used as an explicitly-labelled secondary signal and never silently.
_TIMEOUT_MESSAGE_MARKERS = ("deadline", "timed out", "timeout")


def classify_observation(code: str | None, message: str | None) -> tuple[str, str]:
    """Return ``(observation_class, how_it_was_decided)``.

    The second element is why this function exists: a bucket assigned by a heuristic
    and a bucket assigned by a recorded code must not look the same in the output.
    """
    if not code:
        return "other", "no_catalog_code_recorded"
    base = _CLASS_BY_CODE.get(code)
    if base is None:
        return "other", f"catalog_code_not_mapped:{code}"
    if base == "provider_unavailable" and message:
        lowered = message.lower()
        if any(marker in lowered for marker in _TIMEOUT_MESSAGE_MARKERS):
            return "provider_timeout", "heuristic:stage_error_message"
    return base, "catalog_code"


# ---------------------------------------------------------------------------
# 3. Cost: measured, estimated, or honestly indeterminate
# ---------------------------------------------------------------------------


def load_rate_table() -> dict[str, dict[str, float]]:
    """The ``P02_LOCK.json`` rate card, the one source ``B3`` and this tool share."""
    lock = json.loads((REPO_ROOT / "docs/program/P02_LOCK.json").read_text(encoding="utf-8"))
    models = lock.get("models", {})
    table: dict[str, dict[str, float]] = {}
    for key, entry in models.items():
        if isinstance(entry, Mapping) and "model_id" in entry:
            table[str(entry["model_id"])] = {
                "input_per_mtok_usd": float(entry["input_per_mtok_usd"]),
                "output_per_mtok_usd": float(entry["output_per_mtok_usd"]),
                "tier": key,
            }
    return table


def run_cost_ceiling_usd() -> float:
    lock = json.loads((REPO_ROOT / "docs/program/P02_LOCK.json").read_text(encoding="utf-8"))
    return float(lock["models"]["run_cost_ceiling_usd"])


def rate_table_micros(
    rates: Mapping[str, Mapping[str, Any]],
    model_identity: str,
    input_tokens: int | None,
    output_tokens: int | None,
) -> int | None:
    pin = rates.get(model_identity)
    if pin is None or input_tokens is None or output_tokens is None:
        return None
    usd = (
        input_tokens * float(pin["input_per_mtok_usd"])
        + output_tokens * float(pin["output_per_mtok_usd"])
    ) / 1_000_000.0
    return int(round(usd * 1_000_000))


def classify_cost_basis(
    *,
    provider_mode: str,
    model_identity: str,
    input_tokens: int | None,
    output_tokens: int | None,
    cost_micros: int | None,
    rates: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str]:
    """Return ``(basis, why)`` for one call's cost.

    The schema has no column saying which of the two a figure is, so this derives it:

    * ``recorded`` mode is **always** an estimate, and structurally so.
      ``analysis/text/recorded.py`` builds its ``ModelResponse`` without
      ``reported_cost_usd``, so ``CostMeter.charge`` falls through to the rate table
      for every replayed call. This does not depend on any particular recording.
    * ``live`` mode is a measurement **when** the proxy returned ``usage.cost``, which
      is not persisted. When the stored figure equals the rate table to the micro, the
      two are indistinguishable and this says ``indeterminate`` rather than guessing.
    """
    if cost_micros is None:
        return "absent", "cost_micros is NULL"
    if provider_mode == "recorded":
        return "estimated", "recorded adapter supplies no reported cost; rate table applies"
    expected = rate_table_micros(rates, model_identity, input_tokens, output_tokens)
    if expected is None:
        return "measured", "live call whose model is not in the rate table; no estimate exists"
    if abs(expected - cost_micros) <= 1:
        return (
            "indeterminate",
            "live call whose stored cost equals the rate-table estimate to the micro; "
            "the schema records no measured-or-estimated discriminator",
        )
    return "measured", "live call whose stored cost differs from the rate-table estimate"


# ---------------------------------------------------------------------------
# 4. Extraction
# ---------------------------------------------------------------------------

#: ``model_call`` columns the report needs, with the type to substitute when one is
#: not in the schema. A telemetry column that has gone missing is exactly what this
#: tool exists to detect, so its disappearance must produce a GAP, not a traceback:
#: the extraction selects a typed NULL in its place and the gap register classifies
#: the metric ``absent``. A preflight that crashes on missing telemetry tells the
#: reader nothing, and would do it after the expert sessions were booked.
_OPTIONAL_CALL_COLUMNS = {
    "input_tokens": "integer",
    "output_tokens": "integer",
    "latency_ms": "integer",
    "cost_micros": "bigint",
    "error_code": "text",
}


def build_calls_sql(present: Iterable[str]) -> str:
    available = set(present)
    projected = []
    for column, sql_type in _OPTIONAL_CALL_COLUMNS.items():
        if column in available:
            projected.append(f"mc.{column}")
        else:
            projected.append(f"NULL::{sql_type} AS {column}")
    return f"""
SELECT
    mc.model_call_id, mc.run_id, mc.stage_id, mc.provider, mc.model_identity,
    mc.provider_mode, mc.request_sha256, mc.response_sha256,
    mc.status, mc.created_at,
    {", ".join(projected)},
    sr.status AS stage_status,
    sr.error ->> 'code'    AS stage_error_code,
    sr.error ->> 'message' AS stage_error_message
FROM model_call mc
LEFT JOIN stage_result sr ON sr.run_id = mc.run_id AND sr.stage_id = mc.stage_id
ORDER BY mc.created_at, mc.model_call_id
"""


def existing_columns(db: ReadOnlyDatabase, table: str) -> set[str]:
    rows = db.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = %s",
        [table],
    )
    return {str(row["column_name"]) for row in rows}

_RUNS_SQL = """
SELECT
    r.run_id, r.project_uid, r.version_uid, r.state, r.provider_mode,
    r.terminal_reason, r.interrupted_reason, r.degradation_set,
    r.analysis_profile_id, r.prompt_bundle_id, r.frozen_input_digest,
    r.created_at, r.terminal_at,
    dv.document_uid, dv.version_ordinal,
    EXTRACT(EPOCH FROM (r.terminal_at - r.created_at)) * 1000 AS run_duration_ms
FROM audit_run r
JOIN document_version dv ON dv.version_uid = r.version_uid
ORDER BY r.created_at, r.run_id
"""

_STAGES_SQL = """
SELECT
    run_id, stage_id, stage_version, status, metrics,
    error ->> 'code'      AS error_code,
    error ->> 'message'   AS error_message,
    error -> 'retryable'  AS error_retryable,
    started_at, finished_at,
    EXTRACT(EPOCH FROM (finished_at - started_at)) * 1000 AS stage_duration_ms
FROM stage_result
ORDER BY run_id, started_at NULLS LAST, stage_id
"""

_FINDINGS_SQL = """
SELECT
    f.finding_uid, f.allocated_by_run_id AS run_id, f.version_uid, f.category,
    dv.document_uid,
    v.current_verdict
FROM finding f
JOIN document_version dv ON dv.version_uid = f.version_uid
LEFT JOIN finding_current_verdict v ON v.finding_uid = f.finding_uid
ORDER BY f.finding_uid
"""

_OBSERVATIONS_SQL = """
SELECT
    run_id,
    count(*)                                      AS observations_total,
    count(*) FILTER (WHERE grounded)              AS observations_grounded,
    count(*) FILTER (WHERE NOT grounded)          AS observations_ungrounded,
    count(DISTINCT ungrounded_reason)             AS distinct_ungrounded_reasons
FROM finding_observation
GROUP BY run_id
ORDER BY run_id
"""


def _jsonable(value: Any) -> Any:
    """Dates to ISO-8601, Decimals to float, everything else untouched."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", "replace")
    if value.__class__.__name__ == "Decimal":
        return float(value)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _rows(db: ReadOnlyDatabase, sql: str) -> list[dict[str, Any]]:
    return [{k: _jsonable(v) for k, v in row.items()} for row in db.execute(sql)]


@dataclass
class Extraction:
    """Everything the tool read, in one place, already labelled."""

    calls: list[dict[str, Any]]
    runs: list[dict[str, Any]]
    stages: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    observations: list[dict[str, Any]]
    failures: list[dict[str, Any]]
    ceiling_usd: float


def extract(db: ReadOnlyDatabase) -> Extraction:
    rates = load_rate_table()
    calls = _rows(db, build_calls_sql(existing_columns(db, "model_call")))
    for call in calls:
        basis, why = classify_cost_basis(
            provider_mode=call["provider_mode"],
            model_identity=call["model_identity"],
            input_tokens=call["input_tokens"],
            output_tokens=call["output_tokens"],
            cost_micros=call["cost_micros"],
            rates=rates,
        )
        call["cost_basis"] = basis
        call["cost_basis_reason"] = why
        call["cost_usd"] = (
            None if call["cost_micros"] is None else call["cost_micros"] / 1_000_000.0
        )
        call["rate_table_estimate_micros"] = rate_table_micros(
            rates, call["model_identity"], call["input_tokens"], call["output_tokens"]
        )
        call["total_tokens"] = (
            None
            if call["input_tokens"] is None or call["output_tokens"] is None
            else call["input_tokens"] + call["output_tokens"]
        )
        call["latency_ms_present"] = call["latency_ms"] is not None

    runs = _rows(db, _RUNS_SQL)
    stages = _rows(db, _STAGES_SQL)
    findings = _rows(db, _FINDINGS_SQL)
    observations = _rows(db, _OBSERVATIONS_SQL)
    return Extraction(
        calls=calls,
        runs=runs,
        stages=stages,
        findings=findings,
        observations=observations,
        failures=collect_failures(calls, stages, runs),
        ceiling_usd=run_cost_ceiling_usd(),
    )


def collect_failures(
    calls: Sequence[Mapping[str, Any]],
    stages: Sequence[Mapping[str, Any]],
    runs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """The failure ledger, over all three places a failure is recorded.

    ``model_call`` alone is not enough and getting this wrong is easy: a provider that
    could not be reached produces **no ``model_call`` row at all** — the call never
    returned, so there was nothing to record. A ledger built only from ``model_call``
    would report zero provider failures for a run that plainly suffered one. The
    observed PC-01 failure case is exactly this shape.
    """
    ledger: list[dict[str, Any]] = []

    for call in calls:
        if call["status"] == "failed" or call["error_code"]:
            klass, decided = classify_observation(
                call["error_code"], call.get("stage_error_message")
            )
            ledger.append(
                {
                    "surface": "model_call",
                    "run_id": call["run_id"],
                    "stage_id": call["stage_id"],
                    "model_call_id": call["model_call_id"],
                    "observation_class": klass,
                    "class_decided_by": decided,
                    "catalog_code": call["error_code"],
                    "provider_mode": call["provider_mode"],
                    "message": call.get("stage_error_message"),
                }
            )

    seen_calls = {(c["run_id"], c["stage_id"]) for c in calls if c["error_code"]}
    for stage in stages:
        if not stage["error_code"]:
            continue
        if (stage["run_id"], stage["stage_id"]) in seen_calls:
            continue  # already counted at the call surface; do not double-count
        klass, decided = classify_observation(stage["error_code"], stage["error_message"])
        ledger.append(
            {
                "surface": "stage_result",
                "run_id": stage["run_id"],
                "stage_id": stage["stage_id"],
                "model_call_id": None,
                "observation_class": klass,
                "class_decided_by": decided,
                "catalog_code": stage["error_code"],
                "retryable": stage["error_retryable"],
                "message": stage["error_message"],
                "note": "no model_call row exists for this stage failure",
            }
        )

    stage_failures = {(s["run_id"], s["stage_id"]) for s in stages if s["error_code"]}
    for run in runs:
        if not run["terminal_reason"]:
            continue
        if any(run_id == run["run_id"] for run_id, _ in stage_failures):
            continue  # the stage surface already names it
        klass, decided = classify_observation(run["terminal_reason"], None)
        ledger.append(
            {
                "surface": "audit_run",
                "run_id": run["run_id"],
                "stage_id": None,
                "model_call_id": None,
                "observation_class": klass,
                "class_decided_by": decided,
                "catalog_code": run["terminal_reason"],
                "message": run["interrupted_reason"],
            }
        )
    return ledger


# ---------------------------------------------------------------------------
# 5. Cost roll-up
# ---------------------------------------------------------------------------


def _basis_of(bases: Iterable[str]) -> str:
    """The basis of a sum is the weakest basis among its terms."""
    present = set(bases)
    if not present:
        return "none"
    for weakest in ("absent", "indeterminate", "estimated"):
        if weakest in present:
            return weakest
    return "measured"


def cost_rollup(extraction: Extraction) -> dict[str, Any]:
    """Cost per run, per document, per published finding, and cumulatively.

    Every figure carries its basis. A per-finding figure is a run's spend divided over
    the findings that run published, which is an allocation and is labelled as one:
    the provider is not billed per finding and no row says otherwise.
    """
    per_run: dict[str, dict[str, Any]] = {}
    for run in extraction.runs:
        per_run[run["run_id"]] = {
            "run_id": run["run_id"],
            "document_uid": run["document_uid"],
            "version_uid": run["version_uid"],
            "state": run["state"],
            "provider_mode": run["provider_mode"],
            "cost_micros": 0,
            "bases": [],
            "call_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }
    for call in extraction.calls:
        bucket = per_run.setdefault(
            call["run_id"],
            {
                "run_id": call["run_id"],
                "document_uid": None,
                "version_uid": None,
                "state": None,
                "provider_mode": call["provider_mode"],
                "cost_micros": 0,
                "bases": [],
                "call_count": 0,
                "input_tokens": 0,
                "output_tokens": 0,
            },
        )
        bucket["call_count"] += 1
        bucket["cost_micros"] += call["cost_micros"] or 0
        bucket["bases"].append(call["cost_basis"])
        bucket["input_tokens"] += call["input_tokens"] or 0
        bucket["output_tokens"] += call["output_tokens"] or 0

    published_by_run: dict[str, int] = {}
    accepted_by_run: dict[str, int] = {}
    for finding in extraction.findings:
        published_by_run[finding["run_id"]] = published_by_run.get(finding["run_id"], 0) + 1
        if finding["current_verdict"] == "accepted":
            accepted_by_run[finding["run_id"]] = accepted_by_run.get(finding["run_id"], 0) + 1

    runs_out = []
    for run_id, bucket in sorted(per_run.items()):
        published = published_by_run.get(run_id, 0)
        accepted = accepted_by_run.get(run_id, 0)
        basis = _basis_of(bucket["bases"])
        usd = bucket["cost_micros"] / 1_000_000.0
        runs_out.append(
            {
                "run_id": run_id,
                "document_uid": bucket["document_uid"],
                "state": bucket["state"],
                "provider_mode": bucket["provider_mode"],
                "call_count": bucket["call_count"],
                "input_tokens": bucket["input_tokens"],
                "output_tokens": bucket["output_tokens"],
                "cost_micros": bucket["cost_micros"],
                "cost_usd": usd,
                "cost_basis": basis,
                "published_findings": published,
                "accepted_findings": accepted,
                "cost_usd_per_published_finding": (usd / published) if published else None,
                "cost_usd_per_accepted_finding": (usd / accepted) if accepted else None,
                "per_finding_figures_are": "an allocation of run spend, not a billed unit",
                "over_run_ceiling": usd > extraction.ceiling_usd,
            }
        )

    per_document: dict[str, dict[str, Any]] = {}
    for row in runs_out:
        key = row["document_uid"] or "<unknown>"
        doc = per_document.setdefault(
            key,
            {
                "document_uid": row["document_uid"],
                "run_count": 0,
                "cost_micros": 0,
                "bases": [],
                "published_findings": 0,
                "accepted_findings": 0,
            },
        )
        doc["run_count"] += 1
        doc["cost_micros"] += row["cost_micros"]
        doc["bases"].append(row["cost_basis"])
        doc["published_findings"] += row["published_findings"]
        doc["accepted_findings"] += row["accepted_findings"]

    docs_out = []
    for _key, doc in sorted(per_document.items()):
        usd = doc["cost_micros"] / 1_000_000.0
        docs_out.append(
            {
                "document_uid": doc["document_uid"],
                "run_count": doc["run_count"],
                "cost_micros": doc["cost_micros"],
                "cost_usd": usd,
                "cost_basis": _basis_of(doc["bases"]),
                "published_findings": doc["published_findings"],
                "accepted_findings": doc["accepted_findings"],
                "cost_usd_per_published_finding": (
                    usd / doc["published_findings"] if doc["published_findings"] else None
                ),
            }
        )

    total_micros = sum(row["cost_micros"] for row in runs_out)
    all_bases = [b for row in per_run.values() for b in row["bases"]]
    return {
        "per_run": runs_out,
        "per_document": docs_out,
        "cumulative": {
            "cost_micros": total_micros,
            "cost_usd": total_micros / 1_000_000.0,
            "cost_basis": _basis_of(all_bases),
            "run_cost_ceiling_usd": extraction.ceiling_usd,
            "ceiling_source": "docs/program/P02_LOCK.json models.run_cost_ceiling_usd (OD-03)",
            "runs_over_run_ceiling": [r["run_id"] for r in runs_out if r["over_run_ceiling"]],
            "campaign_ceiling_usd": None,
            "campaign_ceiling_note": (
                "OD-03 records a per-run ceiling only. No machine-readable campaign or "
                "cumulative ceiling exists in P02_LOCK.json, so cumulative spend is "
                "reported against no threshold and P4-BHV-01 must not infer one."
            ),
        },
    }


def latency_summary(calls: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    values = sorted(c["latency_ms"] for c in calls if c["latency_ms"] is not None)
    missing = sum(1 for c in calls if c["latency_ms"] is None)
    if not values:
        return {
            "calls_with_latency": 0,
            "calls_without_latency": missing,
            "note": "no call carries a latency figure",
        }

    def pct(p: float) -> int:
        if len(values) == 1:
            return values[0]
        idx = min(len(values) - 1, max(0, int(round((len(values) - 1) * p))))
        return values[idx]

    return {
        "calls_with_latency": len(values),
        "calls_without_latency": missing,
        "min_ms": values[0],
        "median_ms": pct(0.5),
        "p95_ms": pct(0.95),
        "max_ms": values[-1],
        "caveat": (
            "a recorded call replays the latency figure stored in its recording; it is "
            "not a measurement of this machine and must not be pooled with live latency"
        ),
        "by_mode": {
            mode: sorted(
                c["latency_ms"]
                for c in calls
                if c["provider_mode"] == mode and c["latency_ms"] is not None
            )
            for mode in ("live", "recorded")
        },
    }


def failure_distribution(failures: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_class = {name: 0 for name in OBSERVATION_CLASSES}
    by_code: dict[str, int] = {}
    heuristic = 0
    for row in failures:
        by_class[row["observation_class"]] = by_class.get(row["observation_class"], 0) + 1
        code = row["catalog_code"] or "<none>"
        by_code[code] = by_code.get(code, 0) + 1
        if str(row["class_decided_by"]).startswith("heuristic"):
            heuristic += 1
    return {
        "total": len(failures),
        "by_observation_class": by_class,
        "by_catalog_code": dict(sorted(by_code.items())),
        "classified_by_heuristic": heuristic,
        "note": (
            "observation classes are reporting buckets defined by P4-OPS-01; the "
            "catalog code is recorded beside every one of them"
        ),
    }


# ---------------------------------------------------------------------------
# 6. The §9 gap register
# ---------------------------------------------------------------------------


def build_gap_register(
    extraction: Extraction, nav: Mapping[str, Any], probes: Mapping[str, Any]
) -> dict[str, Any]:
    """Every ``PROTOTYPE_PROFILE.md`` §9 metric, classified against the live schema.

    Classifications are probed against the database that is actually in front of the
    tool, not asserted from the source. ``probe`` on each entry records what was
    counted or looked up to decide, so a reader can repeat the decision.
    """
    calls = extraction.calls
    stages = extraction.stages
    ungrounded_rows = sum(int(o["observations_ungrounded"] or 0) for o in extraction.observations)
    grounding_stages = [
        s
        for s in stages
        if isinstance(s.get("metrics"), Mapping)
        and "evidence_unresolved" in (s.get("metrics") or {})
    ]
    verdicts = {f["current_verdict"] for f in extraction.findings}
    latency_present = sum(1 for c in calls if c["latency_ms"] is not None)
    tokens_present = sum(
        1 for c in calls if c["input_tokens"] is not None and c["output_tokens"] is not None
    )
    cost_present = sum(1 for c in calls if c["cost_micros"] is not None)
    bases = {c["cost_basis"] for c in calls}

    # Computed, never asserted. Emptying model_call or dropping one of these columns
    # flips the classification and fires the dispatch precondition.
    latency_state, latency_why = state_from_probe(probes["latency_ms"])
    tokens_state, tokens_why = state_from_probe(
        probes["input_tokens"], probes["output_tokens"]
    )
    cost_state, cost_why = state_from_probe(probes["cost_micros"])
    failure_state, failure_why = state_from_probe(probes["status"])

    entries: list[dict[str, Any]] = [
        {
            "metric_id": "finding_label_distribution",
            "profile_bullet": "percentage of findings marked useful, incorrect and unclear",
            "state": "absent",
            "owner": "P4-BHV-01",
            "where_i_looked": [
                "db/migrations/versions/20260910_0002_pc01_schema.py VERDICTS + "
                "DECISION_EVENT_TYPES",
                "expert_decision_event.verdict, finding_current_verdict.current_verdict",
                "contracts/api/v1/openapi.json current_verdict description",
                "docs/program/P02_SEAMS.md §534",
            ],
            "finding": (
                "the persisted vocabulary is accepted/rejected/pending, a two-way "
                "verdict. §9's three-way useful/incorrect/unclear is not it. "
                "'unclear' would map to needs_manual_review, which the contract and "
                "P02_SEAMS both record as having NO PC-01 producer. The label is a "
                "session-side instrument per PROTOTYPE_EXECUTION_PLAN §6.1, not a "
                "database field."
            ),
            "what_persisting_it_would_take": (
                "a producer for needs_manual_review, or a distinct label column on "
                "expert_decision_event. Both are P02 schema changes and are out of "
                "scope for P04 by the profile's own no-foundation-change rule."
            ),
            "probe": {
                "verdicts_observed": sorted(v for v in verdicts if v is not None),
                "needs_manual_review_rows": sum(
                    1 for f in extraction.findings if f["current_verdict"] == "needs_manual_review"
                ),
            },
        },
        {
            "metric_id": "evidence_location_correctness",
            "profile_bullet": "evidence-location correctness",
            "state": "derivable",
            "owner": None,
            "where_i_looked": [
                "finding_observation.grounded / ungrounded_reason",
                "src/auditmanager/analysis/text/stage.py _ground() and its metrics block",
                "stage_result.metrics evidence_emitted / evidence_unresolved / "
                "observations_dropped_unresolved",
                "db/migrations/versions/20260911_0003_open_items.py item 3",
                "artifacts/checkpoints/PC-01/report.json limits.not_inducible",
            ],
            "finding": (
                "available as a PER-STAGE RATE, not as a per-quotation list. "
                "text_analysis resolves each quotation and DROPS what does not resolve "
                "before the grounding gate sees it, so no grounded=false row is ever "
                "written and ungrounded_reason has no producer (owner-accepted "
                "2026-09-11). What IS persisted is the count: stage_result.metrics "
                "carries evidence_emitted, evidence_unresolved, observations_proposed, "
                "observations_emitted and observations_dropped_unresolved. "
                "P4-INT-01 MUST NOT design a metric around a per-quotation list."
            ),
            "what_persisting_it_would_take": (
                "writing the dropped anchors as grounded=false rows instead of "
                "discarding them — a runtime change in src/auditmanager/analysis, "
                "forbidden to this task and already ruled on by the owner."
            ),
            "probe": {
                "ungrounded_observation_rows": ungrounded_rows,
                "stages_carrying_grounding_counts": len(grounding_stages),
                "grounding_counts_seen": [
                    {
                        "run_id": s["run_id"],
                        "evidence_emitted": (s["metrics"] or {}).get("evidence_emitted"),
                        "evidence_unresolved": (s["metrics"] or {}).get("evidence_unresolved"),
                        "observations_dropped_unresolved": (s["metrics"] or {}).get(
                            "observations_dropped_unresolved"
                        ),
                    }
                    for s in grounding_stages
                ],
            },
        },
        {
            "metric_id": "expert_review_time_and_navigation_friction",
            "profile_bullet": "expert review time and navigation friction",
            "state": "absent",
            "owner": "P4-BHV-01",
            "where_i_looked": [
                "every table in CENSUS_TABLES for a per-expert timing column",
                "expert_decision_event.recorded_at",
                "PROTOTYPE_EXECUTION_PLAN.md §6.1",
            ],
            "finding": (
                "no expert-time column exists. expert_decision_event.recorded_at is a "
                "server clock stamp on a decision, not seconds-on-finding, and PC-01 "
                "has no authentication so there is no subject to attribute time to "
                "(author_label authorizes nothing, OD-12). §6.1 makes seconds-on-"
                "finding a session instrument."
            ),
            "what_persisting_it_would_take": "a session-side instrument; P4-BHV-01 owns it",
            "probe": {"decision_event_rows": len(extraction.findings)},
        },
        {
            "metric_id": "provider_latency",
            "profile_bullet": "provider latency, cost and failure distribution (latency)",
            "state": latency_state,
            "state_reason": latency_why,
            "owner": None if latency_state == "persisted" else "P2-AI-01 (no producer)",
            "where_i_looked": ["model_call.latency_ms", "stage_result.metrics.latency_ms"],
            "finding": (
                "model_call.latency_ms is present on every call row. A recorded call "
                "replays the recording's stored figure, so live and recorded latency "
                "must be reported separately and never pooled."
            ),
            "probe": {
                "column": probes["latency_ms"],
                "calls_total": len(calls),
                "calls_with_latency_ms": latency_present,
                "modes": sorted({c["provider_mode"] for c in calls}),
            },
        },
        {
            "metric_id": "provider_cost",
            "profile_bullet": "provider latency, cost and failure distribution (cost)",
            "state": cost_state,
            "state_reason": cost_why,
            "owner": None if cost_state == "persisted" else "P2-AI-01 (no producer)",
            "where_i_looked": [
                "model_call.cost_micros and its COMMENT",
                "src/auditmanager/analysis/text/cost.py CostMeter.charge",
                "src/auditmanager/analysis/text/proxy.py _reported_cost",
                "src/auditmanager/analysis/text/recorded.py ModelResponse construction",
                "docs/program/P02_LOCK.json models",
            ],
            "finding": (
                "the figure is persisted, but WHICH KIND of figure it is, is not. "
                "cost_micros holds the proxy's reported spend when the proxy returned "
                "usage.cost, and a P02_LOCK rate-table estimate otherwise, with no "
                "column distinguishing them. The tool derives the basis (see "
                "classify_cost_basis) and labels every figure measured/estimated/"
                "indeterminate. Recorded mode is structurally always an estimate."
            ),
            "what_persisting_it_would_take": (
                "one cost_basis column on model_call. A P02 schema change; raised as a "
                "P02 defect for owner decision, not fixed here."
            ),
            "probe": {
                "column": probes["cost_micros"],
                "calls_with_cost_micros": cost_present,
                "bases_observed": sorted(bases),
                "discriminator_column_exists": False,
            },
        },
        {
            "metric_id": "provider_token_usage",
            "profile_bullet": "provider latency, cost and failure distribution (tokens)",
            "state": tokens_state,
            "state_reason": tokens_why,
            "owner": None if tokens_state == "persisted" else "P2-AI-01 (no producer)",
            "where_i_looked": ["model_call.input_tokens, model_call.output_tokens"],
            "finding": (
                "both columns present and non-null on every observed call. A recorded "
                "call replays authored token counts, which the recording itself says."
            ),
            "probe": {
                "columns": [probes["input_tokens"], probes["output_tokens"]],
                "calls_total": len(calls),
                "calls_with_both_token_counts": tokens_present,
            },
        },
        {
            "metric_id": "provider_failure_distribution",
            "profile_bullet": "provider latency, cost and failure distribution (failures)",
            "state": failure_state,
            "state_reason": failure_why,
            "owner": None if failure_state == "persisted" else "P2-AI-01 (no producer)",
            "where_i_looked": [
                "model_call.status / error_code",
                "stage_result.error jsonb",
                "audit_run.terminal_reason / interrupted_reason",
                "src/auditmanager/analysis/text/proxy.py _map_http_failure",
            ],
            "finding": (
                "persisted, but across THREE surfaces, and model_call alone is "
                "insufficient: a provider that could not be reached writes no "
                "model_call row at all. The failure ledger unions all three. "
                "Separately, provider_timeout has no persisted discriminator — "
                "proxy.py maps both a 504 deadline and an unreachable proxy onto "
                "dependency_unavailable, and model_call stores only the code — so that "
                "one bucket is filled from the stage error message and is flagged as "
                "heuristic wherever it is used."
            ),
            "what_persisting_it_would_take": (
                "a distinct catalog code for a provider deadline, or the error reason "
                "persisted on model_call. A P02 change; raised, not fixed."
            ),
            "probe": {
                "failures_found": len(extraction.failures),
                "surfaces": sorted({f["surface"] for f in extraction.failures}),
                "model_call_failure_rows": sum(
                    1 for c in calls if c["status"] == "failed" or c["error_code"]
                ),
            },
        },
        {
            "metric_id": "missing_stage_or_capability",
            "profile_bullet": "which missing stage or capability prevents real use",
            "state": "derivable",
            "owner": "P4-BHV-01",
            "where_i_looked": [
                "audit_run.degradation_set",
                "stage_result rows against the nine-stage registry",
                "contracts/analysis/v1/stage-registry.json",
            ],
            "finding": (
                "the mechanical half is persisted: degradation_set names degraded "
                "stages and the executed stage set is enumerable against the nine-stage "
                "registry, so 'which stages did not run' is derivable. 'Which missing "
                "capability PREVENTS REAL USE' is a judgement and comes from the "
                "post-session ranking in §6.1, not from any row."
            ),
            "probe": {
                "stages_executed": sorted({s["stage_id"] for s in stages}),
                "runs_with_degradation": [
                    r["run_id"] for r in extraction.runs if r["degradation_set"]
                ],
            },
        },
        {
            "metric_id": "audit_depth_vs_document_comparison",
            "profile_bullet": (
                "whether audit depth or document comparison is the next highest-value "
                "investment"
            ),
            "state": "absent",
            "owner": "P4-BHV-01",
            "where_i_looked": [
                "every table in CENSUS_TABLES",
                "PROTOTYPE_EXECUTION_PLAN.md §6.1 post-session items",
            ],
            "finding": (
                "a forced-choice answer from the post-session instrument. No comparison "
                "aggregate exists in PC-01 at all — the 0002 migration deliberately "
                "creates no comparison table — so there is nothing to derive it from."
            ),
            "probe": {"comparison_tables_present": False},
        },
        {
            "metric_id": "failures_requiring_retry_or_fencing",
            "profile_bullet": (
                "which failures actually require retry, Attempt fencing or remote execution"
            ),
            "state": "derivable",
            "owner": None,
            "where_i_looked": [
                "stage_result.error->'retryable'",
                "audit_run.interrupted_reason (OD-10)",
                "0002 migration comment on audit_run: no Job, no Attempt, no execution token",
            ],
            "finding": (
                "the retryable flag is persisted on every stage error, so the failure "
                "ledger can answer the retry question from evidence rather than from "
                "memory — which is exactly what P4-BHV-01 needs it for. Attempt fencing "
                "is NOT evaluable: PC-01 instantiates no Job and no Attempt, so no "
                "fencing evidence can exist. Remote execution likewise has no producer."
            ),
            "what_persisting_it_would_take": (
                "Attempt/Job aggregates, which PC-01 deliberately does not instantiate"
            ),
            "probe": {
                "stage_errors_with_retryable": sum(
                    1 for s in stages if s["error_retryable"] is not None
                ),
                "attempt_tables_present": False,
            },
        },
        {
            "metric_id": "run_state_timing",
            "profile_bullet": (
                "derived from §9 latency/friction: time-in-state for queued, running, "
                "validating"
            ),
            "state": "absent",
            "owner": "P3-INT-01 (accepted limit) / owner ruling OD-24",
            "where_i_looked": [
                "audit_run.state and the RUN_STATES enum",
                "artifacts/checkpoints/PC-01/report.json limits.intermediate_run_states",
                "0002 migration COMMENT ON TABLE audit_run",
            ],
            "finding": (
                "execution is synchronous inside startRun, so queued, running and "
                "validating never appear through the API and no row ever holds them. "
                "Any §9 metric about time-in-state is unavailable. Run WALL-CLOCK "
                "duration IS available as terminal_at - created_at."
            ),
            "probe": {
                "states_observed": sorted({r["state"] for r in extraction.runs}),
                "intermediate_states_observed": sorted(
                    {r["state"] for r in extraction.runs} & {"queued", "running", "validating"}
                ),
            },
        },
        {
            "metric_id": "agent_navigation_friction",
            "profile_bullet": (
                "agent navigation friction: the search and rework incidents tasks recorded"
            ),
            "state": "absent",
            "owner": "P1-NAV-01 (not accepted)",
            "where_i_looked": [
                "docs/navigation/incidents/ (directory does not exist)",
                "docs/navigation/entries/ (directory does not exist)",
                "docs/program/tasks/P1-NAV-01.md status line",
                "the handoff section of all 21 completed P02/P03 tasks",
            ],
            "finding": (
                "P1-NAV-01 is 'specified; not dispatchable' and docs/navigation/ does "
                "not exist, so the directory contract this metric reads has never been "
                "created. Under the PROTOTYPE_EXECUTION_PLAN §3.3 status-aware rule the "
                "metric is ABSENT, not zero: no in-scope task reported a status at all. "
                "An empty (here, missing) incident directory is evidence of neither "
                "friction nor its absence."
            ),
            "what_persisting_it_would_take": "P1-NAV-01 accepted and integrated",
            "probe": nav,
        },
    ]

    absent = [e["metric_id"] for e in entries if e["state"] == "absent"]
    unclassified = [e["metric_id"] for e in entries if e["state"] not in
                    ("persisted", "derivable", "absent")]
    missing_owner = [
        e["metric_id"] for e in entries if e["state"] == "absent" and not e.get("owner")
    ]
    return {
        "schema": "P4-OPS-01/gap-register/1",
        "tool_version": TOOL_VERSION,
        "source": "docs/program/PROTOTYPE_PROFILE.md §9",
        "classification_vocabulary": ["persisted", "derivable", "absent"],
        "entries": entries,
        "totals": {
            "metrics": len(entries),
            "persisted": sum(1 for e in entries if e["state"] == "persisted"),
            "derivable": sum(1 for e in entries if e["state"] == "derivable"),
            "absent": len(absent),
            "unclassified": unclassified,
            "absent_without_owner": missing_owner,
        },
        "dispatch_precondition": dispatch_precondition(entries),
    }


def dispatch_precondition(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """P4-BHV-01 does not start if per-call latency or token/cost is absent.

    The task spec makes this a halt, not a warning. It is evaluated over the three
    metrics it actually names, and nothing else.
    """
    gating = ("provider_latency", "provider_token_usage", "provider_cost")
    states = {
        e["metric_id"]: e["state"] for e in entries if e["metric_id"] in gating
    }
    blocked = sorted(m for m, state in states.items() if state == "absent")
    return {
        "gating_metrics": list(gating),
        "states": states,
        "blocked": bool(blocked),
        "blocked_on": blocked,
        "rule": (
            "if per-call latency or token/cost is absent, P4-OPS-01 halts with BLOCKED "
            "and its gap register; P4-BHV-01 does not start until the owner rules "
            "under OD-23"
        ),
    }


# ---------------------------------------------------------------------------
# 7. Navigation aggregation
# ---------------------------------------------------------------------------

#: The twenty-one P02/P03 tasks complete when this task runs. It aggregates no P04
#: task: P4-BHV-01 and P4-INT-01 have not run and this task cannot report on its own
#: wave. P4-INT-01 aggregates P04; P5-INT-01 aggregates P05.
IN_SCOPE_NAVIGATION_TASKS = (
    "P2-AI-01", "P2-API-01", "P2-BHV-01", "P2-DOM-01", "P2-ENG-01", "P2-EXP-01",
    "P2-FND-01", "P2-INT-00", "P2-INT-01", "P2-INT-02", "P2-META-01", "P2-QA-01",
    "P2-RUN-01",
    "P3-API-01", "P3-INT-01", "P3-QA-01", "P3-WEB-00", "P3-WEB-01", "P3-WEB-02",
    "P3-WEB-03", "P3-WEB-04",
)

_STATUS_VALUES = ("recorded", "none_observed", "practice_not_exercised")


def aggregate_navigation() -> dict[str, Any]:
    """The §3.3 status-aware rule, applied literally.

    ``zero`` only when every in-scope task returned ``recorded`` or ``none_observed``.
    Otherwise ``absent``, naming the tasks that did not report. An absent file is
    ambiguous and is never read as "no friction".
    """
    incidents_dir = REPO_ROOT / "docs/navigation/incidents"
    statuses: dict[str, str | None] = {}
    for task_id in IN_SCOPE_NAVIGATION_TASKS:
        statuses[task_id] = _reported_status(task_id)

    reported = {t: s for t, s in statuses.items() if s is not None}
    not_reporting = sorted(t for t, s in statuses.items() if s is None)
    practice_not_exercised = sorted(
        t for t, s in statuses.items() if s == "practice_not_exercised"
    )

    if not_reporting or practice_not_exercised:
        value: int | None = None
        state = "absent"
    else:
        value = sum(_incident_count(t) for t in IN_SCOPE_NAVIGATION_TASKS)
        state = "zero" if value == 0 else "measured"

    return {
        "rule": "PROTOTYPE_EXECUTION_PLAN.md §3.3",
        "scope": "the 21 P02/P03 tasks complete at P4-OPS-01 run time",
        "aggregated_tasks": list(IN_SCOPE_NAVIGATION_TASKS),
        "p04_or_p05_tasks_aggregated": [],
        "incidents_dir": str(incidents_dir.relative_to(REPO_ROOT)),
        "incidents_dir_exists": incidents_dir.is_dir(),
        "statuses": statuses,
        "tasks_reporting": sorted(reported),
        "tasks_not_reporting": not_reporting,
        "tasks_practice_not_exercised": practice_not_exercised,
        "state": state,
        "value": value,
        "why": (
            "an empty or missing incident directory is never itself evidence that "
            "navigation was frictionless"
        ),
    }


def _reported_status(task_id: str) -> str | None:
    """A status a task actually reported, as opposed to the handoff template asking for one.

    Every task doc contains the sentence "navigation incident status, one of `recorded`,
    `none_observed` or `practice_not_exercised`" as its handoff REQUIREMENT. Matching
    that sentence would report 21 tasks reporting when none has. The template line is
    removed before looking, which is the whole difficulty of this function.
    """
    path = REPO_ROOT / "docs/program/tasks" / f"{task_id}.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    # Drop the requirement boilerplate wherever it appears.
    text = re.sub(
        r"navigation incident status,\s*one of.*?(?:\n\s*\n|\Z)",
        " ",
        text,
        flags=re.S | re.I,
    )
    for value in _STATUS_VALUES:
        if re.search(rf"navigation[^.\n]{{0,80}}\b{value}\b", text, flags=re.I):
            return value
    return None


def _incident_count(task_id: str) -> int:
    path = REPO_ROOT / "docs/navigation/incidents" / f"{task_id.lower()}.jsonl"
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


# ---------------------------------------------------------------------------
# 8. Session dataset validation
# ---------------------------------------------------------------------------

#: Mandatory per-session fields, from PROTOTYPE_EXECUTION_PLAN.md §6.1. Frozen by this
#: task's acceptance because P4-BHV-01 writes against it and may not edit this file.
SESSION_REQUIRED_FIELDS = (
    "session_id",
    "expert_label",
    "expert_independent",
    "build_commit",
    "documents",
)
DOCUMENT_REQUIRED_FIELDS = (
    "document_uid",
    "run_id",
    "provider_mode",
    "terminal_state",
    "review_time_seconds",
    "findings",
)
FINDING_REQUIRED_FIELDS = (
    "finding_uid",
    "label",
    "seconds_on_finding",
    "moderator_quotation_verbatim",
)
FINDING_LABELS = ("useful", "incorrect", "unclear")


def validate_sessions(directory: Path) -> dict[str, Any]:
    """Assert a session dataset is complete before anything aggregates it."""
    problems: list[dict[str, Any]] = []
    files = sorted(directory.glob("*.json")) if directory.is_dir() else []
    if not directory.is_dir():
        problems.append({"file": str(directory), "problem": "not a directory"})
    elif not files:
        problems.append({"file": str(directory), "problem": "no session records found"})

    sessions: list[dict[str, Any]] = []
    for path in files:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            problems.append({"file": path.name, "problem": f"not valid JSON: {exc}"})
            continue
        if not isinstance(record, dict):
            problems.append({"file": path.name, "problem": "top level is not an object"})
            continue
        sessions.append(record)
        for field_name in SESSION_REQUIRED_FIELDS:
            if field_name not in record or record[field_name] in (None, ""):
                problems.append(
                    {
                        "file": path.name,
                        "problem": f"missing mandatory session field: {field_name}",
                    }
                )
        for index, document in enumerate(record.get("documents") or []):
            where = f"{path.name}:documents[{index}]"
            if not isinstance(document, dict):
                problems.append({"file": where, "problem": "document is not an object"})
                continue
            for field_name in DOCUMENT_REQUIRED_FIELDS:
                if field_name not in document or document[field_name] in (None, ""):
                    problems.append(
                        {"file": where, "problem": f"missing mandatory field: {field_name}"}
                    )
            for f_index, finding in enumerate(document.get("findings") or []):
                f_where = f"{where}:findings[{f_index}]"
                if not isinstance(finding, dict):
                    problems.append({"file": f_where, "problem": "finding is not an object"})
                    continue
                for field_name in FINDING_REQUIRED_FIELDS:
                    if field_name not in finding or finding[field_name] in (None, ""):
                        problems.append(
                            {
                                "file": f_where,
                                "problem": f"missing mandatory field: {field_name}",
                            }
                        )
                label = finding.get("label")
                if label is not None and label not in FINDING_LABELS:
                    problems.append(
                        {
                            "file": f_where,
                            "problem": (
                                f"label {label!r} is not one of {list(FINDING_LABELS)}"
                            ),
                        }
                    )

    build_commits = sorted({s.get("build_commit") for s in sessions if s.get("build_commit")})
    if len(build_commits) > 1:
        problems.append(
            {
                "file": str(directory),
                "problem": (
                    f"G8: the build commit must be frozen across all sessions; found "
                    f"{len(build_commits)}: {build_commits}"
                ),
            }
        )

    return {
        "schema": "P4-OPS-01/session-validation/1",
        "tool_version": TOOL_VERSION,
        "directory": str(directory),
        "session_files": [p.name for p in files],
        "sessions": len(sessions),
        "build_commits": build_commits,
        "complete": not problems,
        "problems": problems,
    }


# ---------------------------------------------------------------------------
# 9. Report assembly
# ---------------------------------------------------------------------------


def build_report(extraction: Extraction) -> dict[str, Any]:
    """The per-call and per-run report, the thing every consumer actually reads."""
    return {
        "schema": "P4-OPS-01/ledger/1",
        "tool_version": TOOL_VERSION,
        "calls": [
            {
                "model_call_id": c["model_call_id"],
                "run_id": c["run_id"],
                "stage_id": c["stage_id"],
                "provider": c["provider"],
                "model_identity": c["model_identity"],
                "provider_mode": c["provider_mode"],
                "latency_ms": c["latency_ms"],
                "input_tokens": c["input_tokens"],
                "output_tokens": c["output_tokens"],
                "total_tokens": c["total_tokens"],
                "cost_micros": c["cost_micros"],
                "cost_usd": c["cost_usd"],
                "cost_basis": c["cost_basis"],
                "cost_basis_reason": c["cost_basis_reason"],
                "rate_table_estimate_micros": c["rate_table_estimate_micros"],
                "status": c["status"],
                "catalog_error_code": c["error_code"],
                "created_at": c["created_at"],
            }
            for c in extraction.calls
        ],
        "runs": [
            {
                "run_id": r["run_id"],
                "document_uid": r["document_uid"],
                "version_uid": r["version_uid"],
                "terminal_state": r["state"],
                "provider_mode": r["provider_mode"],
                "run_duration_ms": r["run_duration_ms"],
                "terminal_reason": r["terminal_reason"],
                "interrupted_reason": r["interrupted_reason"],
                "degradation_set": r["degradation_set"],
                "stage_outcomes": [
                    {
                        "stage_id": s["stage_id"],
                        "status": s["status"],
                        "duration_ms": s["stage_duration_ms"],
                        "error_code": s["error_code"],
                        "retryable": s["error_retryable"],
                    }
                    for s in extraction.stages
                    if s["run_id"] == r["run_id"]
                ],
            }
            for r in extraction.runs
        ],
        "latency": latency_summary(extraction.calls),
        "failure_ledger": extraction.failures,
        "failure_distribution": failure_distribution(extraction.failures),
        "cost": cost_rollup(extraction),
        "mode_summary": {
            "runs_by_mode": _tally(r["provider_mode"] for r in extraction.runs),
            "calls_by_mode": _tally(c["provider_mode"] for c in extraction.calls),
        },
    }


def _tally(values: Iterable[Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        key = str(value)
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def digest(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 10. Modes
# ---------------------------------------------------------------------------


def _open(log: StatementLog) -> ReadOnlyDatabase:
    return ReadOnlyDatabase(load_dsn(), log)


#: The model_call columns the gap register's classifications are computed from.
GAP_PROBE_COLUMNS = ("latency_ms", "input_tokens", "output_tokens", "cost_micros", "status")


def _with_census(
    log: StatementLog,
) -> tuple[Extraction, dict[str, Any], dict[str, Any]]:
    """Extract, with a row census on both sides of the work."""
    with _open(log) as db:
        before = table_row_counts(db)
        extraction = extract(db)
        probes = {
            column: probe_column(db, "model_call", column) for column in GAP_PROBE_COLUMNS
        }
        after = table_row_counts(db)
    census = {
        "tables": len(CENSUS_TABLES),
        "before": before,
        "after": after,
        "identical": before == after,
        "changed": {t: [before[t], after[t]] for t in before if before[t] != after[t]},
    }
    return extraction, census, probes


def mode_self_check() -> int:
    """Reproduce the known shape of the PC-01 recorded-response fixture run.

    It asserts properties of the DATABASE the tool is pointed at, cross-checked against
    the recording file on disk. A self-check that only restated its own query result
    would be the vacuous shape this programme keeps finding, so every assertion below
    names an independent source for the value it expects.
    """
    log = StatementLog()
    extraction, census, probes = _with_census(log)
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: Any) -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    recorded_calls = [c for c in extraction.calls if c["provider_mode"] == "recorded"]
    check(
        "a recorded-response call is present",
        len(recorded_calls) >= 1,
        {"recorded_calls": len(recorded_calls)},
    )

    # Independent source: the recording file itself, not the row we just read.
    fixture_dir = REPO_ROOT / "fixtures/recorded/text_analysis"
    recordings = {}
    for path in sorted(fixture_dir.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        recordings[str(doc.get("request_sha256"))] = doc

    matched = 0
    for call in recorded_calls:
        doc = recordings.get(call["request_sha256"])
        if doc is None:
            continue
        matched += 1
        usage = doc.get("usage") or {}
        check(
            f"{call['model_call_id']}: latency matches its recording",
            call["latency_ms"] == doc.get("latency_ms"),
            {"row": call["latency_ms"], "recording": doc.get("latency_ms")},
        )
        check(
            f"{call['model_call_id']}: tokens match its recording",
            call["input_tokens"] == usage.get("input_tokens")
            and call["output_tokens"] == usage.get("output_tokens"),
            {
                "row": [call["input_tokens"], call["output_tokens"]],
                "recording": [usage.get("input_tokens"), usage.get("output_tokens")],
            },
        )
        check(
            f"{call['model_call_id']}: the recording carries no cost, so the "
            "row's cost must be an estimate",
            "cost" not in usage and call["cost_basis"] == "estimated",
            {
                "recording_has_cost_field": "cost" in usage,
                "derived_basis": call["cost_basis"],
            },
        )
        # Independent source: the P02_LOCK rate card, recomputed here.
        check(
            f"{call['model_call_id']}: cost equals the rate table recomputed from the lock",
            call["cost_micros"] == call["rate_table_estimate_micros"],
            {
                "stored_micros": call["cost_micros"],
                "recomputed_micros": call["rate_table_estimate_micros"],
            },
        )

    check(
        "every recorded call was matched to a recording on disk",
        matched == len(recorded_calls) and matched > 0,
        {"matched": matched, "recorded_calls": len(recorded_calls)},
    )
    check(
        "every call carries a latency figure",
        all(c["latency_ms"] is not None for c in extraction.calls) and extraction.calls != [],
        {
            "calls": len(extraction.calls),
            "with_latency": sum(1 for c in extraction.calls if c["latency_ms"] is not None),
        },
    )
    check(
        "every call declares a closed provider mode",
        all(c["provider_mode"] in ("live", "recorded") for c in extraction.calls),
        {"modes": sorted({c["provider_mode"] for c in extraction.calls})},
    )
    check(
        "no cost figure is presented without its basis",
        all(
            c["cost_basis"] in ("measured", "estimated", "indeterminate", "absent")
            for c in extraction.calls
        ),
        {"bases": sorted({c["cost_basis"] for c in extraction.calls})},
    )
    check("the tool issued no write statement", not log.writes, log.summary())
    check("the row census is unchanged", census["identical"], census["changed"])

    failed = [c for c in checks if not c["ok"]]
    payload = {
        "mode": "self-check",
        "tool_version": TOOL_VERSION,
        "checks": checks,
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "statement_log": log.summary(),
        "row_census": {"identical": census["identical"], "changed": census["changed"]},
    }
    print(canonical_json(payload), end="")
    return EXIT_OK if not failed else EXIT_GUARD


def mode_dry_run() -> int:
    """Every read the tool performs, and the proof that none of them wrote."""
    log = StatementLog()
    extraction, census, probes = _with_census(log)
    report = build_report(extraction)
    summary = log.summary()
    ok = summary["write_statements"] == 0 and census["identical"]
    payload = {
        "mode": "dry-run",
        "tool_version": TOOL_VERSION,
        "statement_log": summary,
        "row_census": census,
        "would_emit": {
            "calls": len(report["calls"]),
            "runs": len(report["runs"]),
            "failures": report["failure_distribution"]["total"],
            "cumulative_cost_usd": report["cost"]["cumulative"]["cost_usd"],
            "cumulative_cost_basis": report["cost"]["cumulative"]["cost_basis"],
        },
        "files_written": [],
        "read_only_proven_by": [
            "the connection is held in a READ ONLY transaction",
            "every statement is classified at issue time and a non-read raises",
            "a row census over all 16 tables before and after is identical",
        ],
        "ok": ok,
    }
    print(canonical_json(payload), end="")
    return EXIT_OK if ok else EXIT_GUARD


def mode_snapshot(out_dir: Path) -> int:
    """Write the pre-session baseline: the state the study starts from.

    The artifacts are deterministic by construction — they carry no wall-clock — so
    running this twice over the same database and tree produces byte-identical files.
    That is what makes the final ledger differenceable against them.
    """
    log = StatementLog()
    extraction, census, probes = _with_census(log)
    nav = aggregate_navigation()
    report = build_report(extraction)
    register = build_gap_register(extraction, nav, probes)

    snapshot = {
        "schema": "P4-OPS-01/pre-session-snapshot/1",
        "this_is": (
            "the PRE-SESSION baseline for PC-02. It records the state that existed "
            "BEFORE the first expert session. It is NOT validation-period data and must "
            "never be merged into, or presented as, the validation-period ledger that "
            "P4-INT-01 owns under artifacts/validation/PC-02/ledger/."
        ),
        "tool": {"id": TOOL_ID, "version": TOOL_VERSION},
        "pc01": _pc01_provenance(),
        "baseline_counts": {
            "runs": len(extraction.runs),
            "model_calls": len(extraction.calls),
            "stage_results": len(extraction.stages),
            "published_findings": len(extraction.findings),
            "failures": len(extraction.failures),
            "table_rows": census["after"],
        },
        "baseline_spend": report["cost"]["cumulative"],
        "baseline_runs": report["runs"],
        "baseline_calls": report["calls"],
        "baseline_latency": report["latency"],
        "baseline_failures": report["failure_distribution"],
        "baseline_cost_per_run": report["cost"]["per_run"],
        "baseline_cost_per_document": report["cost"]["per_document"],
        "mode_summary": report["mode_summary"],
        "navigation": nav,
        "read_only_evidence": {
            "statement_log": log.summary(),
            "row_census_identical": census["identical"],
        },
        "no_secrets": (
            "no connection string, credential, bucket name or object key appears in "
            "this artifact; blobs are referenced by identifier only"
        ),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, payload in (
        ("snapshot.json", snapshot),
        ("gap_register.json", register),
        ("navigation.json", nav),
    ):
        path = out_dir / name
        path.write_text(canonical_json(payload), encoding="utf-8")
        # The NAME, not the path: the manifest is then identical wherever the snapshot
        # is written, and the digest is what actually identifies the content.
        written.append({"name": name, "sha256": digest(payload)})

    manifest = {
        "schema": "P4-OPS-01/preflight-manifest/1",
        "tool": {"id": TOOL_ID, "version": TOOL_VERSION},
        "written_by": "the tool, not by hand",
        "reproducible": (
            "these artifacts carry no wall-clock; re-running --snapshot over the same "
            "database state and tree reproduces them byte for byte"
        ),
        "files": written,
        "gap_register_totals": register["totals"],
        "dispatch_precondition": register["dispatch_precondition"],
    }
    (out_dir / "MANIFEST.json").write_text(canonical_json(manifest), encoding="utf-8")

    blocked = register["dispatch_precondition"]["blocked"]
    unclassified = register["totals"]["unclassified"]
    missing_owner = register["totals"]["absent_without_owner"]

    print(canonical_json({
        "mode": "snapshot",
        "out_dir": str(out_dir),
        "files": [str(out_dir / w["name"]) for w in written]
        + [str(out_dir / "MANIFEST.json")],
        "gap_register_totals": register["totals"],
        "dispatch_precondition": register["dispatch_precondition"],
        "statement_log": log.summary(),
        "row_census_identical": census["identical"],
    }), end="")

    if unclassified or missing_owner:
        print(
            f"{TOOL_ID}: gap register incomplete: unclassified={unclassified} "
            f"absent_without_owner={missing_owner}",
            file=sys.stderr,
        )
        return EXIT_GUARD
    if blocked:
        print(
            f"{TOOL_ID}: BLOCKED — {register['dispatch_precondition']['blocked_on']} "
            "is absent. P4-BHV-01 does not start until the owner rules under OD-23.",
            file=sys.stderr,
        )
        return EXIT_BLOCKED
    return EXIT_OK


def _pc01_provenance() -> dict[str, Any]:
    path = REPO_ROOT / "artifacts/checkpoints/PC-01/report.json"
    if not path.is_file():
        return {"available": False}
    report = json.loads(path.read_text(encoding="utf-8"))
    return {
        "available": True,
        "checkpoint_id": report.get("checkpoint_id"),
        "status": report.get("status"),
        "accepted_commit": report.get("accepted_commit"),
        "accepted_on": report.get("accepted_on"),
        "known_limits": sorted((report.get("limits") or {}).keys()),
    }


def mode_validate_sessions(directory: Path) -> int:
    result = validate_sessions(directory)
    print(canonical_json(result), end="")
    return EXIT_OK if result["complete"] else EXIT_GUARD


def mode_period(sessions: Path, baseline: Path, out: Path) -> int:
    """Extract the closed validation period and difference it against the baseline.

    This is the mode ``P4-INT-01`` runs. It is exercised here against fixtures so that
    task invokes an interface this task has already proven. **This task never writes
    under artifacts/validation/PC-02/ledger/**; the destination is the caller's.
    """
    validation = validate_sessions(sessions)
    if not validation["complete"]:
        print(canonical_json({"mode": "period", "session_validation": validation}), end="")
        print(
            f"{TOOL_ID}: the session dataset is incomplete; nothing was aggregated.",
            file=sys.stderr,
        )
        return EXIT_GUARD

    baseline_path = baseline / "snapshot.json" if baseline.is_dir() else baseline
    baseline_bytes = baseline_path.read_bytes()
    baseline_doc = json.loads(baseline_bytes.decode("utf-8"))

    log = StatementLog()
    extraction, census, probes = _with_census(log)
    report = build_report(extraction)

    base_counts = baseline_doc.get("baseline_counts", {})
    now_counts = {
        "runs": len(extraction.runs),
        "model_calls": len(extraction.calls),
        "stage_results": len(extraction.stages),
        "published_findings": len(extraction.findings),
        "failures": len(extraction.failures),
    }
    baseline_run_ids = {r["run_id"] for r in baseline_doc.get("baseline_runs", [])}
    baseline_call_ids = {c["model_call_id"] for c in baseline_doc.get("baseline_calls", [])}
    period_runs = [r for r in report["runs"] if r["run_id"] not in baseline_run_ids]
    period_calls = [c for c in report["calls"] if c["model_call_id"] not in baseline_call_ids]

    base_spend = (baseline_doc.get("baseline_spend") or {}).get("cost_micros", 0)
    total_spend = report["cost"]["cumulative"]["cost_micros"]
    period_spend = total_spend - base_spend

    ledger = {
        "schema": "P4-OPS-01/validation-period-ledger/1",
        "tool": {"id": TOOL_ID, "version": TOOL_VERSION},
        "this_is": (
            "the VALIDATION-PERIOD ledger: activity attributable to the study, with "
            "pre-existing baseline activity differenced out."
        ),
        "session_validation": validation,
        "baseline": {
            "path": str(baseline_path),
            "sha256": hashlib.sha256(baseline_bytes).hexdigest(),
            "counts": base_counts,
            "read_only": "the baseline is read and never modified",
        },
        "totals_now": now_counts,
        "period": {
            "runs": period_runs,
            "calls": period_calls,
            "run_count": len(period_runs),
            "call_count": len(period_calls),
            "spend_micros": period_spend,
            "spend_usd": period_spend / 1_000_000.0,
            "spend_basis": report["cost"]["cumulative"]["cost_basis"],
        },
        "baseline_activity_excluded": {
            "run_count": len(baseline_run_ids),
            "call_count": len(baseline_call_ids),
            "spend_micros": base_spend,
        },
        "full_report": report,
        "read_only_evidence": {
            "statement_log": log.summary(),
            "row_census_identical": census["identical"],
        },
    }

    out.mkdir(parents=True, exist_ok=True)
    ledger_path = out / "ledger.json"
    ledger_path.write_text(canonical_json(ledger), encoding="utf-8")

    after = baseline_path.read_bytes()
    if after != baseline_bytes:
        print(f"{TOOL_ID}: the baseline changed during the run.", file=sys.stderr)
        return EXIT_GUARD

    print(canonical_json({
        "mode": "period",
        "out": str(ledger_path),
        "period_runs": len(period_runs),
        "period_calls": len(period_calls),
        "period_spend_usd": period_spend / 1_000_000.0,
        "baseline_unmodified": True,
        "baseline_sha256": hashlib.sha256(baseline_bytes).hexdigest(),
        "statement_log": log.summary(),
        "row_census_identical": census["identical"],
    }), end="")
    return EXIT_OK


def mode_report() -> int:
    log = StatementLog()
    extraction, census, probes = _with_census(log)
    report = build_report(extraction)
    report["read_only_evidence"] = {
        "statement_log": log.summary(),
        "row_census_identical": census["identical"],
    }
    print(canonical_json(report), end="")
    return EXIT_OK


# ---------------------------------------------------------------------------
# 11. The frozen command-line interface
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ledger_report.py",
        description=(
            "PC-02 measurement tooling, read-only over the PC-01 schema. This interface "
            "is frozen by P4-OPS-01's acceptance: P4-BHV-01 and P4-INT-01 both invoke it "
            "and neither may edit it."
        ),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-check", action="store_true",
                      help="reproduce the known shape of the PC-01 recorded fixture run")
    group.add_argument("--dry-run", action="store_true",
                      help="read everything, write nothing, and print the statement log")
    group.add_argument("--snapshot", metavar="DIR", type=Path,
                      help="write the pre-session baseline and gap register into DIR")
    group.add_argument("--validate-sessions", metavar="DIR", type=Path,
                      help="assert a session dataset is complete before aggregating it")
    group.add_argument("--period", metavar="SESSIONS", type=Path,
                      help="extract the closed validation period (needs --baseline, --out)")
    group.add_argument("--report", action="store_true",
                      help="print the per-call and per-run report to stdout")
    parser.add_argument("--baseline", metavar="DIR", type=Path,
                        help="the pre-session snapshot to difference against (--period)")
    parser.add_argument("--out", metavar="DIR", type=Path,
                        help="where the validation-period ledger is written (--period)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.self_check:
            return mode_self_check()
        if args.dry_run:
            return mode_dry_run()
        if args.report:
            return mode_report()
        if args.snapshot is not None:
            return mode_snapshot(args.snapshot)
        if args.validate_sessions is not None:
            return mode_validate_sessions(args.validate_sessions)
        if args.period is not None:
            if args.baseline is None or args.out is None:
                parser.error("--period requires both --baseline and --out")
            return mode_period(args.period, args.baseline, args.out)
    except WriteAttempted as exc:
        print(f"{TOOL_ID}: {exc}", file=sys.stderr)
        return EXIT_GUARD
    parser.error("no mode selected")
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
