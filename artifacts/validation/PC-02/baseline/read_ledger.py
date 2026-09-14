"""Read the measured cost and latency of this session's runs out of ``model_call``.

Read-only, and deliberately direct: ``tools/validation/ledger_report.py`` reports
``cost_basis`` by comparing the stored cost against a rate table rather than by reading
the ``cost_basis`` column that migration ``0004_cost_basis`` added, so its answer for a
proxy run is ``indeterminate`` whatever the column says. The column is what
``P4-BHV-01`` and ``P4-INT-01`` will cite, so it is read here as stored.

Nothing here is part of the pipeline: the runs were driven entirely through the router.
This is the ledger being read back afterwards.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_baseline import load_env_files  # noqa: E402

QUERY = """
SELECT mc.run_id,
       count(*)                          AS call_count,
       sum(mc.cost_micros)               AS cost_micros,
       sum(mc.latency_ms)                AS latency_ms,
       sum(mc.input_tokens)              AS input_tokens,
       sum(mc.output_tokens)             AS output_tokens,
       array_agg(DISTINCT mc.cost_basis) AS cost_basis,
       array_agg(DISTINCT mc.status)     AS statuses,
       array_agg(DISTINCT mc.model_identity) AS model_identity,
       array_agg(DISTINCT mc.provider_mode)  AS provider_mode
  FROM model_call mc
 WHERE mc.run_id = ANY(:run_ids)
 GROUP BY mc.run_id
"""


def main() -> int:
    load_env_files()
    from sqlalchemy import create_engine, text

    runs_dir = Path(__file__).resolve().parent / "runs"
    by_run: dict[str, str] = {}
    for path in sorted(runs_dir.glob("PC02-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("run_id"):
            by_run[record["run_id"]] = record["label"]

    # The attempts that failed on a transient provider outage are read too. They are
    # expected to carry no `model_call` row at all -- the stage fails before a call is
    # recorded -- and that absence is itself the thing worth reporting: whatever those
    # attempts cost upstream is invisible to this ledger.
    failed: dict[str, str] = {}
    for path in sorted((runs_dir / "attempts").glob("PC02-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("run_id"):
            failed[record["run_id"]] = f"{record['label']}#attempt{record.get('attempt', '1')}"
    if not by_run:
        print("no run ids recorded yet", file=sys.stderr)
        return 1

    url = os.environ["DATABASE_URL"]
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    rows: dict[str, dict] = {}
    failed_rows: dict[str, Any] = {}
    with engine.connect() as conn:
        for run_id, name in failed.items():
            found = list(conn.execute(text(QUERY), {"run_ids": [run_id]}).mappings())
            failed_rows[name] = {
                "run_id": run_id,
                "model_call_rows": len(found),
                "cost_micros": sum(int(r["cost_micros"] or 0) for r in found),
            }
        for row in conn.execute(text(QUERY), {"run_ids": list(by_run)}).mappings():
            entry = dict(row)
            entry["label"] = by_run[entry["run_id"]]
            # sum() over a bigint column comes back as Decimal; cost is carried in
            # integer micros precisely so money is never a float in storage, and is
            # converted to USD only here, at the reporting edge.
            entry["cost_micros"] = int(entry["cost_micros"] or 0)
            entry["latency_ms"] = int(entry["latency_ms"] or 0)
            entry["input_tokens"] = int(entry["input_tokens"] or 0)
            entry["output_tokens"] = int(entry["output_tokens"] or 0)
            entry["call_count"] = int(entry["call_count"])
            entry["cost_usd"] = entry["cost_micros"] / 1_000_000
            rows[entry["label"]] = entry

    out = {
        "source": "model_call, read directly; cost_micros are integer millionths of USD",
        "documents": {label: rows.get(label) for label in sorted(by_run.values())},
        "total_cost_usd": round(sum(r["cost_usd"] for r in rows.values()), 6),
        "total_calls": sum(r["call_count"] for r in rows.values()),
        "cost_basis_values": sorted(
            {b for r in rows.values() for b in (r["cost_basis"] or [])}
        ),
        "failed_attempts": failed_rows,
        "failed_attempt_note":
            "A run whose text_analysis stage failed with dependency_unavailable records "
            "no model_call row, so it contributes nothing to measured spend and any "
            "upstream tokens it consumed are not visible to this ledger.",
    }
    target = Path(__file__).resolve().parent / "ledger.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str) + "\n",
                      encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
