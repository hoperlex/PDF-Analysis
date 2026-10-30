# Task BETA-PDF-PRECHECK-1030 — bounded background PDF interpretation before analysis

## Outcome
Every ordinary-section and AR v3 Run fully interprets the stored PDF in a bounded child during durable source preparation before any model call. Page progress is committed to the existing execution journal; parser/resource failure is explicit and cancellation stops the child.

## Depends on
- RUN-ROBUSTNESS-01
- CMP-INT-CODE-1030

## Frozen inputs
- owner decision 2026-10-30: full PDF check in the background before analysis, progress and explicit errors; no long upload request
- D-160 parser gap and existing source-preparation/text normalization contracts
- API `1.13.0` (254 operations), migration `0043_stage_ai_generations`; no schema/API change
- base `8a437cbe15c47b1655e3ef7268bd1c60a657fdd2`
- root grants `analysis/public.py` wrapper export and `jobs/events.py` progress scalar allowlist; cost agent owns commands/preflight/bootstrap and supplies the approved-cost policy consumed only in executor

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: D-160 fast upload reader decodes streams but does not interpret page operators; source preparation is the shared ordinary/AR v3 worker stage before their provider branches.

### P-01 — existing background boundary
- captured_at: 2026-10-30
- command: `git rev-parse HEAD; rg -n 'source_preparation|if v3_exact:' src/auditmanager/runs/executor.py`
- captured_output:
  ```text
  8a437cbe15c47b1655e3ef7268bd1c60a657fdd2
  1030: source_preparation
  1082: if v3_exact:
  ```
- interpretation: reuse the existing durable Job/Attempt and source stage instead of introducing a queue or API-side full parse.

## Historical evidence
- correction_mode: addendum
- source_record: D-160 / RUN-ROBUSTNESS-01
- addendum_path: `BETA-PDF-PRECHECK-1030.md`

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/analysis/stages/source_preparation.py`
- `src/auditmanager/analysis/stages/pdf_precheck.py`
- `src/auditmanager/analysis/stages/pdf_precheck_child.py`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/runs/executor.py`
- `src/auditmanager/jobs/events.py`
- `tests/unit/analysis/test_pdf_precheck.py`
- `tests/unit/runs/test_pdf_precheck_executor.py`
- `tests/integration/runs/test_pdf_precheck.py`
- `docs/program/tasks/BETA-PDF-PRECHECK-1030.md`
- `docs/program/BETA-PDF-PRECHECK-1030.md`

## Lane resources
No service is started by this lane. Root explicitly grants serial use of its existing test PostgreSQL/S3 stack on ports 58060/62060 with this worktree's ignored copied `.env`; the slot is released at handoff. Root owns the frontend progress files and all bootstrap wiring. Cost-policy provider commit `29c9c870` is integrated by root in `24caa634` and its existing exports are preserved.

## Forbidden hotspots
- commands/preflight/bootstrap/cost-agent paths, claims/lease machinery, frontend (root owns progress UI), contracts, migration head, root locks, remote refs

## Non-goals
- no full parse in upload request, live model call, large corpus, full gate/build, new queue or in-memory canonical job state
- no raw PDF text/path/exception payload in progress or logs; no fallback to unchecked input

## Deliverables
- bounded full page interpreter/extractor child and validated receipt; preserve existing normalized source artifacts
- source-stage public callback wrapper and durable lease-fenced executor progress/cancellation before both provider branches
- exact event schema/wiring handoff for root UI and focused tests/report

## Required tests
- focused parser/protocol/cancellation/source-stage tests and small executor integration cases only
- compile/lint/diff checks; optional shared test DB 58060 only after coordination with root

## Integration contract
`analysis.public` exposes a source-preparation handler accepting progress and checkpoint callbacks. Executor persists `stage.pdf_precheck` events with stage_id `source_preparation`, phase started/checking/completed/failed, completed_pages and total_pages; failures add fixed error_code/reason. Root UI reads existing execution journal; cancellation uses RunStatus and fences loser events. Root retains bootstrap ownership.

## Failure/idempotency/security cases
- child memory/CPU/wall/page/output bounds; startup/protocol failures are explicit
- every page is fully interpreted; counts/normalization/line geometry are checked; no partial document is accepted
- authority is checked during pages and fenced before progress commits; child is killed/reaped on cancel/loss/error
- last page and terminal phase always persist; intermediate events are throttled
- full source parsing and validation finish before any ordinary/AR v3 provider effect

## Rollback / feature flag
No bypass flag: unchecked input cannot silently proceed. Reverting restores the prior source-preparation implementation; no schema/data rollback is needed.

## Handoff
- implementation/report: `docs/program/BETA-PDF-PRECHECK-1030.md`
- checks: 13 focused unit + 4 DB/S3 integration + 3 existing source-preparation regressions passed; targeted compilation and diff whitespace checks passed
- limits: child 1536 MiB AS / 1200 s CPU / 1800 s wall / 180 s page / 45 s startup; receipt 32 MiB line / 256 MiB total; 500 pages and existing character bounds
- contracts/migrations: none
- integration: root UI `49b4018e` consumes the exact event schema; cost-policy provider `29c9c870` is already merged by root; PDF bootstrap changes unnecessary; local commit only
- limitations: Linux descriptor/resource primitives; heavy maximum-corpus/browser/full-gate acceptance deferred; AR v3 failure test injects reviewed-pack selection/binding and claims only the before-model refusal path
- forbidden-hotspot evidence: final commit path list is limited to the exact allowlist; no ingest/upload, commands, bootstrap, contracts, migration, root lock, frontend, tag or remote ref is changed by this task
