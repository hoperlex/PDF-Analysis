"""Match published findings to PC-02 ground truth, mechanically and by content.

The rule is ``docs/program/validation/PC-02_PROTOCOL.md`` section 11, implemented
literally and fixed before any result was looked at:

  A published finding **matches a seeded issue** when it cites the same document,
  carries the same ``category``, and at least one of its evidence quotations is on a
  page the seeded issue declares and either contains or is contained by the seeded
  quotation on that page.

  A published finding **matches a declared control** by the same rule against the
  control's quotation and pages.

``finding_uid`` is never used: PC-01 allocates fresh ones per run and implements no
cross-run matching, so identity across runs does not exist and matching is by content.

A control carries no ``category`` -- the manifest gives controls a ``quotation``, a
``pages`` list and an ``archetype``, and no category -- so the category clause of the
rule has nothing to bind to for controls and drops out. Only document, page and
quotation containment apply there. This is the reading the protocol's own wording
forces ("by the same rule against the control's quotation and pages"), and it is
recorded here because a reader should not have to infer it.

**Whitespace.** The primary comparison is on the exact strings as published and as
declared. ``pdfplumber``'s ``extract_text`` collapses runs of spaces while the corpus
writer's extractor does not, so a whitespace-only difference could in principle sink a
true match. Rather than relax the rule after seeing results -- which would measure the
relaxation -- the literal rule is the reported one, and a whitespace-normalised pass is
computed alongside it purely as a disclosed diagnostic. Both numbers are emitted. This
decision was taken before the corpus results were read.

**Vacuity.** ``self_proofs()`` exercises the matcher three ways: a finding that must
match, a finding that must not, and an empty finding set that must not report success.
A matcher that matches nothing reports perfect precision, so the proofs run every time
this module scores and their results are written into the output.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
MANIFEST = ROOT / "fixtures" / "validation" / "PC-02" / "corpus_manifest.json"
RUNS = HERE / "runs"

_WS = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Collapse every run of whitespace to one space and strip. Diagnostic use only."""
    return _WS.sub(" ", text).strip()


def overlaps(published: str, declared: str, *, normalised: bool) -> bool:
    """'either contains or is contained by', the protocol's containment test."""
    left, right = (normalise(published), normalise(declared)) if normalised else (
        published, declared
    )
    if not left or not right:
        return False
    return declared_in_published(left, right)


def declared_in_published(left: str, right: str) -> bool:
    return right in left or left in right


def evidence_of(finding: dict) -> list[dict]:
    return (finding.get("observation") or {}).get("evidence") or []


def matches_seed(finding: dict, seed: dict, *, normalised: bool) -> list[dict]:
    """Every (evidence, seed-anchor) pair that satisfies the rule. Empty means no match.

    The pairs are returned rather than a bool so the report can quote *which* quotation
    matched which anchor; a bare bool would make a wrong match indistinguishable from a
    right one.
    """
    if finding.get("category") != seed.get("category"):
        return []
    declared_pages = set(seed.get("pages") or [])
    hits: list[dict] = []
    for item in evidence_of(finding):
        for anchor in seed.get("evidence") or []:
            page = anchor.get("page")
            if page not in declared_pages:
                continue
            if item.get("page_number") != page:
                continue
            if overlaps(item.get("quote", ""), anchor.get("quotation", ""),
                        normalised=normalised):
                hits.append({
                    "page": page,
                    "published_quote": item.get("quote"),
                    "declared_quotation": anchor.get("quotation"),
                    "evidence_ordinal": item.get("evidence_ordinal"),
                })
    return hits


def matches_control(finding: dict, control: dict, *, normalised: bool) -> list[dict]:
    """The same rule against the control's ``quotation`` and ``pages``."""
    declared_pages = set(control.get("pages") or [])
    quotation = control.get("quotation", "")
    hits: list[dict] = []
    for item in evidence_of(finding):
        page = item.get("page_number")
        if page not in declared_pages:
            continue
        if overlaps(item.get("quote", ""), quotation, normalised=normalised):
            hits.append({
                "page": page,
                "published_quote": item.get("quote"),
                "declared_quotation": quotation,
                "evidence_ordinal": item.get("evidence_ordinal"),
            })
    return hits


def classify(findings: Iterable[dict], document: dict, *, normalised: bool) -> dict:
    """Split one document's findings into the protocol's three groups."""
    seeds = document.get("seeded_issues") or []
    controls = document.get("controls") or []

    classified: list[dict] = []
    seeds_hit: dict[str, list[int]] = {s["id"]: [] for s in seeds}
    controls_hit: dict[str, list[int]] = {c["id"]: [] for c in controls}

    for index, finding in enumerate(findings):
        seed_matches = []
        for seed in seeds:
            hits = matches_seed(finding, seed, normalised=normalised)
            if hits:
                seed_matches.append({"seed_id": seed["id"], "category": seed["category"],
                                     "hits": hits})
                seeds_hit[seed["id"]].append(index)
        control_matches = []
        for control in controls:
            hits = matches_control(finding, control, normalised=normalised)
            if hits:
                control_matches.append({"control_id": control["id"],
                                        "archetype": control["archetype"],
                                        "would_be_false_positive_as":
                                            control["would_be_false_positive_as"],
                                        "hits": hits})
                controls_hit[control["id"]].append(index)

        if seed_matches:
            group = "seeded_issue"
        elif control_matches:
            group = "declared_control"
        else:
            group = "neither"

        observation = finding.get("observation") or {}
        classified.append({
            "index": index,
            "group": group,
            "finding_uid": finding.get("finding_uid"),
            "category": finding.get("category"),
            "finding_text": observation.get("finding_text"),
            "recommendation_text": observation.get("recommendation_text"),
            "evidence": [
                {"page_number": e.get("page_number"), "quote": e.get("quote"),
                 "char_start": e.get("char_start"), "char_end": e.get("char_end")}
                for e in evidence_of(finding)
            ],
            "seed_matches": seed_matches,
            "control_matches": control_matches,
            "matched_both": bool(seed_matches and control_matches),
        })

    return {
        "findings": classified,
        "seeds_hit": {k: v for k, v in seeds_hit.items()},
        "controls_hit": {k: v for k, v in controls_hit.items()},
    }


def score(run_records: dict[str, dict], manifest: dict, *, normalised: bool) -> dict:
    """The whole corpus. Denominators count measurable documents only."""
    documents = {d["label"]: d for d in manifest["documents"]}
    per_document: dict[str, Any] = {}
    seed_status: dict[str, dict] = {}
    control_status: dict[str, dict] = {}

    for label, document in documents.items():
        record = run_records.get(label)
        findings = (record or {}).get("findings") or []
        result = classify(findings, document, normalised=normalised)
        per_document[label] = {
            "role": document["role"],
            "state": (record or {}).get("state"),
            "findings_returned": len(findings),
            **result,
        }
        for seed in document.get("seeded_issues") or []:
            seed_status[seed["id"]] = {
                "document": label,
                "category": seed["category"],
                "pages": seed["pages"],
                "attribute_ru": seed.get("attribute_ru"),
                "summary_ru": seed.get("summary_ru"),
                "quotations": [a["quotation"] for a in seed.get("evidence") or []],
                "found": bool(result["seeds_hit"].get(seed["id"])),
            }
        for control in document.get("controls") or []:
            control_status[control["id"]] = {
                "document": label,
                "archetype": control["archetype"],
                "pages": control["pages"],
                "quotation": control["quotation"],
                "would_be_false_positive_as": control["would_be_false_positive_as"],
                "why_not_an_issue_ru": control.get("why_not_an_issue_ru"),
                "flagged": bool(result["controls_hit"].get(control["id"])),
            }

    group_counts = {"seeded_issue": 0, "declared_control": 0, "neither": 0}
    third_group: list[dict] = []
    for label, entry in per_document.items():
        for finding in entry["findings"]:
            group_counts[finding["group"]] += 1
            if finding["group"] == "neither":
                third_group.append({"document": label, **finding})

    found = [k for k, v in seed_status.items() if v["found"]]
    missed = [k for k, v in seed_status.items() if not v["found"]]
    flagged = [k for k, v in control_status.items() if v["flagged"]]

    by_archetype: dict[str, dict] = {}
    for control_id, entry in control_status.items():
        bucket = by_archetype.setdefault(entry["archetype"], {"total": 0, "flagged": 0,
                                                             "flagged_ids": []})
        bucket["total"] += 1
        if entry["flagged"]:
            bucket["flagged"] += 1
            bucket["flagged_ids"].append(control_id)

    total_findings = sum(group_counts.values())
    return {
        "matching_rule": "PC-02_PROTOCOL.md section 11, literal containment"
                         if not normalised else
                         "PC-02_PROTOCOL.md section 11, whitespace-normalised (diagnostic)",
        "whitespace_normalised": normalised,
        "denominator_note": "measurable documents only; the four negative-envelope "
                            "documents are excluded from every finding denominator",
        "seeded_issues_total": len(seed_status),
        "seeded_issues_found": len(found),
        "seeded_issues_found_ids": sorted(found),
        "seeded_issues_missed_ids": sorted(missed),
        "recall": round(len(found) / len(seed_status), 4) if seed_status else None,
        "control_statements_total": len(control_status),
        "control_statements_flagged": len(flagged),
        "control_statements_flagged_ids": sorted(flagged),
        "controls_by_archetype": by_archetype,
        "findings_total": total_findings,
        "group_counts": group_counts,
        "third_group": third_group,
        "seed_status": seed_status,
        "control_status": control_status,
        "per_document": per_document,
    }


# ----------------------------------------------------------------------------------
# Anti-vacuity. A matcher that matches nothing reports perfect precision.
# ----------------------------------------------------------------------------------

def _finding(category: str, evidence: list[tuple[int, str]]) -> dict:
    return {
        "finding_uid": "fnd_probe",
        "category": category,
        "observation": {
            "category": category,
            "finding_text": "probe",
            "evidence": [
                {"evidence_ordinal": i + 1, "page_number": p, "quote": q,
                 "char_start": 0, "char_end": len(q)}
                for i, (p, q) in enumerate(evidence)
            ],
        },
    }


def self_proofs(manifest: dict) -> dict:
    """Three proofs that this matcher can fail, run every time it scores.

    1. A finding built from a seeded issue's own declared evidence must match it.
    2. Findings that must not match do not -- one per way the rule can refuse: wrong
       category, wrong page, wrong document, unrelated text, and a control quotation
       that is deliberately *not* the seeded issue.
    3. An empty finding set must not report success: recall must be 0 and no seed may
       be reported found.
    """
    documents = {d["label"]: d for d in manifest["documents"]}
    subject = documents["PC02-S01"]
    seed = subject["seeded_issues"][0]          # internal_contradiction, pages 2 and 5
    placeholder = subject["seeded_issues"][1]   # explicit_placeholder, page 7
    control = subject["controls"][0]            # other_object, page 3

    proofs: dict[str, Any] = {}

    # -- Proof 1: a finding that must match -----------------------------------------
    positive = _finding(seed["category"],
                        [(a["page"], a["quotation"]) for a in seed["evidence"]])
    hits = matches_seed(positive, seed, normalised=False)
    result = classify([positive], subject, normalised=False)
    proofs["positive_matches"] = {
        "description": "a finding carrying the seeded category and both declared "
                       "quotations on their declared pages",
        "seed_id": seed["id"],
        "hit_count": len(hits),
        "group": result["findings"][0]["group"],
        "passed": bool(hits) and result["findings"][0]["group"] == "seeded_issue",
    }

    # A containment variant: the published quote wrapped in a longer sentence must
    # still match, because the rule is containment in either direction.
    wrapped = _finding(seed["category"],
                       [(seed["evidence"][0]["page"],
                         "В разделе сказано: " + seed["evidence"][0]["quotation"] + " Далее.")])
    proofs["positive_containment_either_direction"] = {
        "description": "the declared quotation contained inside a longer published quote",
        "hit_count": len(matches_seed(wrapped, seed, normalised=False)),
        "passed": bool(matches_seed(wrapped, seed, normalised=False)),
    }

    # -- Proof 2: findings that must not match ---------------------------------------
    negatives = {
        "wrong_category": _finding(
            "explicit_placeholder",
            [(a["page"], a["quotation"]) for a in seed["evidence"]]),
        "wrong_page": _finding(
            seed["category"],
            [(4, seed["evidence"][0]["quotation"])]),
        "unrelated_text": _finding(
            seed["category"],
            [(seed["evidence"][0]["page"], "Совершенно посторонняя строка без отношения к делу.")]),
        "control_quotation_is_not_the_seed": _finding(
            seed["category"],
            [(control["pages"][0], control["quotation"])]),
        "other_document_quotation": _finding(
            seed["category"],
            [(seed["evidence"][0]["page"],
              documents["PC02-C01"]["controls"][0]["quotation"])]),
        "empty_quote": _finding(seed["category"], [(seed["evidence"][0]["page"], "")]),
    }
    negative_results = {}
    for name, probe in negatives.items():
        hits = matches_seed(probe, seed, normalised=False)
        negative_results[name] = {"hit_count": len(hits), "passed": not hits}
    proofs["negatives_do_not_match"] = {
        "description": "one probe per way the rule can refuse a match",
        "probes": negative_results,
        "passed": all(v["passed"] for v in negative_results.values()),
    }

    # The control probe must, however, match the CONTROL -- otherwise 'does not match'
    # would be indistinguishable from 'the matcher matches nothing'.
    control_probe_hits = matches_control(
        negatives["control_quotation_is_not_the_seed"], control, normalised=False)
    proofs["control_rule_matches_its_control"] = {
        "description": "the probe that must not match the seed must still match the "
                       "control it quotes; otherwise the negative proof is vacuous",
        "control_id": control["id"],
        "hit_count": len(control_probe_hits),
        "passed": bool(control_probe_hits),
    }

    # -- Proof 3: an empty finding set must not report success -------------------------
    empty = score({}, manifest, normalised=False)
    proofs["empty_finding_set_is_not_success"] = {
        "description": "scoring with no findings at all",
        "recall": empty["recall"],
        "seeded_issues_found": empty["seeded_issues_found"],
        "control_statements_flagged": empty["control_statements_flagged"],
        "findings_total": empty["findings_total"],
        "passed": (empty["seeded_issues_found"] == 0 and empty["recall"] == 0.0
                   and empty["findings_total"] == 0),
        "note": "zero flagged controls here is NOT precision: with no findings there is "
                "nothing to be precise about, which is exactly the vacuity this proves "
                "against. Precision is only meaningful beside a non-zero findings_total.",
    }

    proofs["all_passed"] = all(
        v["passed"] for k, v in proofs.items() if isinstance(v, dict) and "passed" in v
    )
    return proofs


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records: dict[str, dict] = {}
    for path in sorted(RUNS.glob("PC02-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if "findings" in record or record.get("role") in {"seeded", "control"}:
            records[record["label"]] = record

    proofs = self_proofs(manifest)
    literal = score(records, manifest, normalised=False)
    diagnostic = score(records, manifest, normalised=True)

    out = {
        "matcher_self_proofs": proofs,
        "primary": literal,
        "whitespace_normalised_diagnostic": {
            "seeded_issues_found": diagnostic["seeded_issues_found"],
            "seeded_issues_found_ids": diagnostic["seeded_issues_found_ids"],
            "control_statements_flagged": diagnostic["control_statements_flagged"],
            "control_statements_flagged_ids": diagnostic["control_statements_flagged_ids"],
            "group_counts": diagnostic["group_counts"],
            "differs_from_primary": (
                diagnostic["seeded_issues_found_ids"] != literal["seeded_issues_found_ids"]
                or diagnostic["control_statements_flagged_ids"]
                != literal["control_statements_flagged_ids"]
            ),
        },
    }
    (HERE / "matching.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not proofs["all_passed"]:
        print("MATCHER SELF-PROOFS FAILED", file=sys.stderr)
        print(json.dumps(proofs, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3

    print(f"self-proofs: all passed")
    print(f"recall: {literal['seeded_issues_found']}/{literal['seeded_issues_total']}")
    print(f"missed: {literal['seeded_issues_missed_ids']}")
    print(f"controls flagged: {literal['control_statements_flagged']}"
          f"/{literal['control_statements_total']} "
          f"{literal['control_statements_flagged_ids']}")
    print(f"groups: {literal['group_counts']}")
    print(f"whitespace diagnostic differs: "
          f"{out['whitespace_normalised_diagnostic']['differs_from_primary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
