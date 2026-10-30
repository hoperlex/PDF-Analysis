# Task CMP-STAGE-REVIEW-01 — stage cards, expert verdicts and accepted journal

## Outcome
The full-chain step 7 materializes immutable evidence-bound cards; experts can page cards, save keyed optimistic verdicts, inspect history and download grouped accepted-change journals as XLSX/PDF/HTML.

## Depends on
- CMP-SEAL-C4
- CMP-STAGE-AI-CORE-01
- CMP-STAGE-TEXT-RECOMPUTE-01

## Frozen inputs
- domain: ADR-0025 §3,21,22 and COMPARE-MODULES-PLAN A-9/A-10, tab3/tab4
- API: 1.13.0, 227 paths /253 operations /613 schemas
- migration head: 0042_comparison_stage_review; no schema change
- base commit: `cbb69852d9da6c05c57a738702c6241c2323b220`
- source: immutable effective link revision raw text differences, graphic evidence and validated C4 classifications
- owner override 2026-10-30: functional code and dev today, full gates/heavy windows tomorrow

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: C4 tables and API shapes are sealed; step7 review backend is not implemented.

### P-01 — base
- captured_at: 2026-10-30
- command: `git rev-parse HEAD`
- captured_output:
  ```text
  cbb69852d9da6c05c57a738702c6241c2323b220
  ```
- interpretation: root owns integration/wiring; this lane owns review code only.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/stage_review/**`
- `tests/unit/comparison/stage_review/**`
- `tests/integration/comparison/stage_review/**`
- `docs/program/tasks/CMP-STAGE-REVIEW-01.md`
- `docs/program/CMP-STAGE-REVIEW-01.md`
- `.venv`
- `.env`

## Lane resources
- foundation_instance: `auditmanager-cmp-seal-c4`
- postgres_port: `58040`
- s3_api_port: `62040`
- s3_console_port: `62041`
- postgres_db: `auditmanager_cmp_seal_c4`
- s3_bucket: `auditmanager-cmp-seal-c4`

The prior seal lane is complete; root explicitly assigned its now-idle isolated foundation to this sequential successor.

## Forbidden hotspots
- contracts, migrations, shared wiring/public.py, generated client, root dependency/lock files, global styles, remote refs

## Non-goals
- no model call, AI classification rewrite, raw evidence mutation, generic exports abstraction, full gate or deployment

## Deliverables
- StageReviewService advance/page/get/apply_verdicts/verdicts/journal/export
- deterministic REVIEW fallback for unclassified raw evidence, evidence-bound carryover without invented project-change claims
- local deterministic XLSX/PDF/HTML writers and focused DB/export checks

## Required tests
- focused unit/DB checks, export ZIP/PDF/HTML validation, git diff --check
- full gates/heavy windows remain tomorrow's integration work by direct owner instruction

## Integration contract
Root maps plain dictionaries to frozen API models. advance(item,run_id) publishes in the caller work lease fence. Journal groups are exactly {key,label,rows:StageChangeCard[]} and contain accepted PROJECT_CHANGE/REVIEW cards; SERVICE_STRUCTURE remains a collapsed unvoted class. Effective revision supersedes the original only for current source reads, never by changing raw pins.

## Failure/idempotency/security cases
- foreign/stale work cannot publish; keyed replay returns the same verdict IDs
- optimistic revision/refused rejection reason rolls back the entire verdict batch
- carryover binds exact canonical evidence digest; changed digest is stale, partial overlap is labelled and never silently accepted
- a missing/unavailable AI classification leaves conservative REVIEW cards, and an AI SAME never deletes raw evidence

## Rollback / feature flag
Root retains the stages module gate; immutable rows are retained. No migration/deployment is owned here.

## Handoff
- status: completed
- changed files: review service/cards/local writers/package; focused unit/DB tests; task/report
- checks: 9 unit passed, 7 real-0042 DB passed; deterministic XLSX/PDF/HTML readers; git diff --check clean
- contracts: none
- known limits: explicit source/carryover/journal/export budgets; no importance assessment; high-level synthesis is a separate sealed read; broader windows deferred by owner
- integration: local commit only, root wires/merges/publishes; report `docs/program/CMP-STAGE-REVIEW-01.md`
