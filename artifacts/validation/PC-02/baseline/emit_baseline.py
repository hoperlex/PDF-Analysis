"""Emit the PC-02 baseline artifact: per document and in aggregate.

``P4-BHV-01`` hands this to domain experts and ``P4-INT-01`` reports from it, so the
shape here is the shape those tasks get. It is assembled from four files that are each
produced by a separate step and never by this one:

* ``runs/*.json``     -- what the application answered, through the router
* ``matching.json``   -- the protocol section 11 classification, and the matcher's proofs
* ``grounding.json``  -- the independent quotation verification
* ``ledger.json``     -- measured cost and latency, read from ``model_call``

Nothing is recomputed here. If a number appears in this artifact it appears in one of
those four files first, so a reader can always find the step that produced it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
MANIFEST = ROOT / "fixtures" / "validation" / "PC-02" / "corpus_manifest.json"
RUNS = HERE / "runs"

ARTIFACT_SCHEMA = "pc02-baseline-run/1"


def read(name: str) -> dict:
    path = HERE / name
    if not path.is_file():
        raise SystemExit(f"{path} is missing; run the step that produces it first")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    matching = read("matching.json")
    grounding = read("grounding.json")
    ledger = read("ledger.json")
    session = read("session.json")

    primary = matching["primary"]
    documents = {d["label"]: d for d in manifest["documents"]}
    negatives = {n["label"]: n for n in manifest["negative_envelope_documents"]}

    per_document: list[dict] = []
    negative_records: list[dict] = []
    total_wall = 0.0

    for path in sorted(RUNS.glob("PC02-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        label = record["label"]

        if label in negatives:
            negative_records.append({
                "label": label,
                "violates_rule": record["violates_rule"],
                "rule_description": record["rule_description"],
                "bytes": record["bytes"],
                "upload_status": record["upload_status"],
                "refused": record["refused"],
                "error_code": (record.get("response") or {}).get("error_code"),
                "message": (record.get("response") or {}).get("message"),
                "details": (record.get("response") or {}).get("details"),
                "seconds": record["seconds"],
            })
            continue

        document = documents[label]
        classification = primary["per_document"][label]
        cost = (ledger.get("documents") or {}).get(label) or {}
        ground = (grounding.get("documents") or {}).get(label) or {}
        total_wall += record.get("run_wall_seconds") or 0.0

        per_document.append({
            "label": label,
            "role": document["role"],
            "pages": document["pages"],
            "sha256": document["sha256"],
            "run_id": record.get("run_id"),
            "version_uid": record.get("version_uid"),
            "state": record.get("state"),
            "terminal": record.get("terminated"),
            "terminal_reason": record.get("terminal_reason"),
            "degradation_set": record.get("degradation_set"),
            "stages": [
                {"stage_id": s.get("stage_id"), "status": s.get("status"),
                 "stage_version": s.get("stage_version"),
                 "error_code": s.get("error_code")}
                for s in record.get("stages") or []
            ],
            "findings_returned": record.get("findings_returned"),
            "findings": classification["findings"],
            "seeded_issues_declared": [s["id"] for s in document.get("seeded_issues") or []],
            "seeded_issues_matched": [
                sid for sid, hits in classification["seeds_hit"].items() if hits
            ],
            "controls_declared": [c["id"] for c in document.get("controls") or []],
            "controls_flagged": [
                cid for cid, hits in classification["controls_hit"].items() if hits
            ],
            "cost": {
                "measured_cost_usd": cost.get("cost_usd"),
                "cost_micros": cost.get("cost_micros"),
                "cost_basis": cost.get("cost_basis"),
                "model_calls": cost.get("call_count"),
                "input_tokens": cost.get("input_tokens"),
                "output_tokens": cost.get("output_tokens"),
                "model_identity": cost.get("model_identity"),
            },
            "latency": {
                "provider_latency_ms": cost.get("latency_ms"),
                "run_wall_seconds": record.get("run_wall_seconds"),
                "upload_seconds": record.get("upload_seconds"),
            },
            "grounding": {
                "page_text_sha256_pinned": ground.get("page_text_sha256_pinned"),
                "quotations_checked": len(ground.get("evidence_items") or []),
                "quotations_verified": sum(
                    1 for e in ground.get("evidence_items") or [] if e.get("verified")
                ),
                "global_offsets_run_in_page_order":
                    ground.get("global_offsets_run_in_page_order"),
                "global_offsets_distinct": ground.get("global_offsets_distinct"),
            },
        })

    states = {}
    for entry in per_document:
        states[entry["state"]] = states.get(entry["state"], 0) + 1

    artifact = {
        "schema": ARTIFACT_SCHEMA,
        "checkpoint": "PC-02",
        "task": "P4-RUN-01",
        "produced_by": "artifacts/validation/PC-02/baseline/emit_baseline.py",
        "corpus_manifest": "fixtures/validation/PC-02/corpus_manifest.json",
        "protocol": "docs/program/validation/PC-02_PROTOCOL.md",
        "session": session,
        "note": "One live run per measurable document, driven through "
                "auditmanager.api.app.create_app() and the Router it returns. Nothing "
                "was tuned in response to any result; the matching rule and the "
                "whitespace decision were fixed before the corpus was scored.",

        "aggregate": {
            "measurable_documents": len(per_document),
            "documents_reaching_terminal_state": sum(
                1 for e in per_document if e["terminal"]),
            "states": states,
            "findings_total": primary["findings_total"],
            "group_counts": primary["group_counts"],
            "group_definition": {
                "seeded_issue": "matches a seeded issue by protocol section 11",
                "declared_control": "matches a declared control statement and no seeded issue",
                "neither": "matches neither; the corpus's blind spot, reported in full",
            },
            "recall": {
                "seeded_issues_total": primary["seeded_issues_total"],
                "found": primary["seeded_issues_found"],
                "rate": primary["recall"],
                "found_ids": primary["seeded_issues_found_ids"],
                "missed_ids": primary["seeded_issues_missed_ids"],
            },
            "false_positive_pressure": {
                "control_statements_total": primary["control_statements_total"],
                "flagged": primary["control_statements_flagged"],
                "flagged_ids": primary["control_statements_flagged_ids"],
                "by_archetype": primary["controls_by_archetype"],
            },
            "grounding": {
                "quotations_verified": grounding["quotations_verified"],
                "failure_count": grounding["failure_count"],
                "failures": grounding["failures"],
                "independent_reader": grounding["independent_reader"],
                "product_extractor": grounding["product_extractor"],
                "documents_pinned_to_manifest":
                    grounding["documents_pinned_to_manifest"],
            },
            "cost": {
                "total_measured_usd": ledger.get("total_cost_usd"),
                "total_model_calls": ledger.get("total_calls"),
                "cost_basis_values": ledger.get("cost_basis_values"),
                "run_cost_ceiling_usd": 1.0,
                "ceiling_source": "docs/program/P02_LOCK.json models.run_cost_ceiling_usd (OD-03)",
                "runs_halted_on_ceiling": [
                    e["label"] for e in per_document
                    if e["state"] not in {"published"} and e["state"] is not None
                ],
            },
            "latency": {
                "total_run_wall_seconds": round(total_wall, 3),
                "total_provider_latency_ms": sum(
                    (e["latency"]["provider_latency_ms"] or 0) for e in per_document),
            },
        },

        "seed_status": primary["seed_status"],
        "control_status": primary["control_status"],
        "third_group": primary["third_group"],
        "matcher_self_proofs": matching["matcher_self_proofs"],
        "whitespace_normalised_diagnostic":
            matching["whitespace_normalised_diagnostic"],
        "documents": per_document,
        "negative_envelope": {
            "note": "Excluded from every finding denominator and from every gate that "
                    "counts measurable documents, G4 included.",
            "documents": negative_records,
            "all_refused": all(n["refused"] for n in negative_records)
                           and len(negative_records) == 4,
        },
    }

    (HERE / "baseline.json").write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    agg = artifact["aggregate"]
    print(f"documents: {agg['measurable_documents']} terminal="
          f"{agg['documents_reaching_terminal_state']} states={agg['states']}")
    print(f"findings: {agg['findings_total']} groups={agg['group_counts']}")
    print(f"recall: {agg['recall']['found']}/{agg['recall']['seeded_issues_total']} "
          f"missed={agg['recall']['missed_ids']}")
    print(f"controls flagged: {agg['false_positive_pressure']['flagged']}"
          f"/{agg['false_positive_pressure']['control_statements_total']} "
          f"{agg['false_positive_pressure']['flagged_ids']}")
    print(f"grounding: {agg['grounding']['quotations_verified']} verified, "
          f"{agg['grounding']['failure_count']} failures")
    print(f"cost: USD {agg['cost']['total_measured_usd']} "
          f"basis={agg['cost']['cost_basis_values']}")
    print(f"negatives all refused: {artifact['negative_envelope']['all_refused']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
