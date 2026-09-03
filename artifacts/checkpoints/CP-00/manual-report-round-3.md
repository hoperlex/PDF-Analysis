# CP-00 manual acceptance — primary report, round 3

> **Status: superseded.** This report describes the tree as it stood at
> `candidate_digest` `a05fc308…` (commit `016670ad`). The candidate has changed since:
> `W0-QA-01` was reopened and the digest recipe was corrected. A round-4 report on the
> corrected tree is owed, and this one carries forward as history, not as evidence for
> ratification.

## Start record

```text
candidate_commit:      016670ad58f53b3b6438cfd4bb17d25f3bd96e74 (integration/W0.3)
candidate_digest:      a05fc3085a801f2df22c39531918831f9b0b430c31a9177ce14fb826ca2fab6d
tree:                  72620f11b451ee17680a5964e56a596f1283ffff
contract_manifest:     domain/analysis/events 1.0.0-draft.1; golden_selection_schema 1;
                       artifact_manifest_sha256 39721aac…, 100 files
migration_head:        none (db/migrations holds only README.md)
backend_runtime:       not applicable - architecture-only checkpoint
frontend_runtime:      not applicable - architecture-only checkpoint
local_infra_versions:  not applicable - architecture-only checkpoint
tester:                cp00_manual_tester, independent agent; authored none of the
                       reviewed artifacts, the QA tests or the QA report
started_at:            2026-09-02T16:31+05:00
finished_at:           2026-09-02T16:42+05:00
```

## Per-case results

| Case | Result | Evidence |
|---|---|---|
| MT00-01 Documentation navigation | PASS | Recipe at `manifest.json:67` run with no knowledge of the SHA reproduces `candidate_digest` over 211 files; discriminates against `4acad77a`, `718f90aa`, `92e13fa4`, `854a6820`. `artifact_manifest_sha256` reproduces over 100 files. README chain resolves; 0 broken links across 146 markdown files. `S00:63-68` carries all six task rows with SHAs matching `manifest.json:23-30`. |
| MT00-02 Greenfield boundary | PASS | `src/` holds one 97-byte `__init__.py`; no legacy import anywhere in `src/`, `scripts/`, `tests/`. 638 legacy references classified, all under provenance keys. `ADR-0001:10` forbids runtime Strangler dependency. |
| MT00-03 Identity walk | PASS | `identifiers.json:21` bars display ordinals such as `F-014` from identity or foreign key; `DOMAIN_MODEL.md:69` and `GLOSSARY.md:16` agree. GJ-03 separates legacy `EO-06`/`EO-07` from target `EO-09`/`EO-10`. Legacy behaviour read at `32b9d903…:backend/app/services/findings/decision_carryover_service.py:605-620`. |
| MT00-04 Run/job/attempt walk | PASS | Three distinct machines. Timeout→retry→stale walk: `state-machines.json:370,507,521,663` fire `stale_attempt`; `:363,656` fire `execution_token_invalid`; `:415,701` state a late result is stored as immutable evidence and never applied. `machines.job.retry` creates a new `attempt_id`, never a new `run_id` or `job_id`. |
| MT00-05 Comparison ownership | PASS | `ADR-0013` plus GJ-04 `EO-02` (saved links authoritative), `EO-03`/`EO-04` (signature governs staleness), `EO-10` (an AI stage may only add its own artifact and may never edit, delete or reinterpret the stored raw difference record). |
| MT00-06 Unresolved decisions | PASS | Open set exactly `U-04` (open), `U-01` (deferred with deadline), `OQ-02`, `OQ-04` (deferred), `E-05` (open escalation), `ADR-0014` (sole defer, `proposed`). Numeric sweep for TTL, retention, lease, heartbeat, grace, backoff and retry-budget across `contracts/` and `fixtures/` returns nothing. |

## Verdict at the time

PASS, 6 of 6.

## Findings the tester raised

1. `candidate_digest` excluded the manifest, so two candidates differing only in
   manifest prose shared one value — the counterexample was `f4b8882d` and `00ec6449`.
   Corrected since; that correction is one reason this report is superseded.
2. `CURRENT_STATE.md` still framed the rebuild as following the first acceptance round
   while two had failed.
3. Neither recipe fixed the digest encoding as raw bytes rather than hex text.

## Method limitation

The tester is an independent agent, not a person. For an architecture-only checkpoint
the six cases are reading and judgment over documents rather than exercise of a running
system, so an agent is the closest available analogue — not a substitute. Recorded so a
later reader weighs the evidence for what it is.
