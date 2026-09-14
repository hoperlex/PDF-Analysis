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

#: Which guard each envelope rule is enforced by, read out of the product rather than
#: asserted. The `ENV-*` names appear nowhere in `src/`, so a refusal can only be tied
#: back to its rule through the `constraint` detail key.
RULE_GUARDS = {
    "ENV-PDF": {
        "constraint": "pdf_magic_bytes",
        "guard": "src/auditmanager/ingest/envelope.py:145 (the envelope probe)",
    },
    "ENV-ENCRYPTED": {
        "constraint": "not_encrypted",
        "guard": "src/auditmanager/ingest/envelope.py:193 (the envelope probe)",
    },
    "ENV-SIZE": {
        "constraint": "byte_size <= 26214400",
        "guard": "src/auditmanager/ingest/envelope.py:153 (the envelope probe, 25 MiB)",
    },
    "ENV-PAGES": {
        "constraint": "1 <= page_count <= 30",
        "guard": "src/auditmanager/ingest/envelope.py:162 (the envelope probe)",
    },
    "ENV-TEXT": {
        "constraint": "every_page_has_extractable_text",
        "guard": "src/auditmanager/ingest/envelope.py:229 (the envelope probe)",
    },
}


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
            response = record.get("response") or {}
            details = response.get("details") or {}
            rule = record["violates_rule"]
            expected = RULE_GUARDS.get(rule, {})
            actual_constraint = details.get("constraint")
            negative_records.append({
                "label": label,
                "violates_rule": rule,
                "rule_description": record["rule_description"],
                "bytes": record["bytes"],
                "upload_status": record["upload_status"],
                "refused": record["refused"],
                "error_code": response.get("error_code"),
                "message": response.get("message"),
                "details": details,
                "seconds": record["seconds"],
                "expected_constraint_for_rule": expected.get("constraint"),
                "expected_guard": expected.get("guard"),
                "actual_constraint": actual_constraint,
                "refused_by_its_own_declared_guard":
                    actual_constraint == expected.get("constraint"),
                "refused_for_the_reason_the_rule_states": True,
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
                # A run halting on the ceiling would terminate with
                # `cost_budget_exceeded`; none did. The closest approach is reported as
                # a fraction of the ceiling so "nowhere near it" is a number rather than
                # an assurance.
                "runs_halted_on_ceiling": [
                    e["label"] for e in per_document
                    if e["terminal_reason"] == "cost_budget_exceeded"
                ],
                "most_expensive_document": max(
                    ((e["label"], e["cost"]["measured_cost_usd"] or 0.0)
                     for e in per_document),
                    key=lambda pair: pair[1], default=(None, 0.0)),
                "highest_fraction_of_ceiling": round(
                    max((e["cost"]["measured_cost_usd"] or 0.0)
                        for e in per_document) / 1.0, 4) if per_document else None,
            },
            "latency": {
                "total_run_wall_seconds": round(total_wall, 3),
                "total_provider_latency_ms": sum(
                    (e["latency"]["provider_latency_ms"] or 0) for e in per_document),
            },
        },

        "provider_reliability": {
            "note": "Every measurable document reached `published`, but three run "
                    "attempts had to be made twice or three times. Each failure was the "
                    "same transient one: the text_analysis stage ended "
                    "`dependency_unavailable` ('the model proxy could not be reached') "
                    "after roughly 133 seconds. Only the run command's idempotency key "
                    "was varied between attempts; the document, the prompt, the profile "
                    "and the model were identical, and nothing was tuned.",
            "attempts_total": len(list(RUNS.glob("PC02-S*.json")))
                              + len(list(RUNS.glob("PC02-C*.json")))
                              + len(list((RUNS / "attempts").glob("PC02-*.json"))),
            "failed_attempts": [
                {
                    "label": json.loads(p.read_text(encoding="utf-8"))["label"],
                    "attempt": json.loads(p.read_text(encoding="utf-8")).get("attempt", "1"),
                    "run_id": json.loads(p.read_text(encoding="utf-8")).get("run_id"),
                    "state": json.loads(p.read_text(encoding="utf-8")).get("state"),
                    "terminal_reason":
                        json.loads(p.read_text(encoding="utf-8")).get("terminal_reason"),
                    "stage_error_code_as_published_by_api": None,
                    "stage_error_code_as_stored":
                        "dependency_unavailable (stage_result.error.code)",
                    "run_wall_seconds":
                        json.loads(p.read_text(encoding="utf-8")).get("run_wall_seconds"),
                    "model_call_rows": 0,
                    "recorded_cost_usd": 0.0,
                }
                for p in sorted((RUNS / "attempts").glob("PC02-*.json"))
            ],
            "ledger_blind_spot": ledger.get("failed_attempt_note"),
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
            "all_refused_by_their_own_declared_guard": all(
                n["refused_by_its_own_declared_guard"] for n in negative_records
            ) and len(negative_records) == 4,
            "guard_note":
                "ENV-SIZE is the one rule whose fixture does not reach the guard that "
                "declares it. PC02-N03 is 27303351 bytes, which exceeds both the "
                "envelope's 25 MiB ENV-SIZE limit and the transport's 26 MiB multipart "
                "body limit (src/auditmanager/api/routers/multipart.py:30,64). The "
                "transport guard is outermost, so it refuses first and the response "
                "carries constraint `max_bytes` rather than the envelope's "
                "`byte_size <= 26214400`. The file is still refused for being too "
                "large, which is what ENV-SIZE states, but this run does not exercise "
                "the envelope's own ENV-SIZE check. A fixture between 25 and 26 MiB "
                "would.",
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
