# Task CMP-C2-FIX-01 — integration repair of the C2 candidate

## Outcome
The C2 candidate passes its frozen contract check for the bundled report font, and its four AI worker methods bind the job's routed, pinned executor connection in the worker process. The remaining C2 findings are either verified against the merged code or recorded with an exact follow-up owner before publication.

## Depends on
- CMP-SEAL-C2
- CMP-AI-JOBS-01
- CMP-VC-SPEC-01
- CMP-VC-AIPAIR-01
- CMP-VC-AISHEET-01
- CMP-VC-REPORT-01
- CMP-VC-QUEUE-01
- CMP-VC-UI-02

## Frozen inputs
- API contract `1.11.0`, 176 paths / 198 operations / 517 schemas
- migration head `0040_comparison_ai_reports`
- ADR-0025, `docs/program/dispatch/CMP-WAVE-C2.md`, the six completed lane reports
- base commit `8fcdda42` on `integration/compare-modules`

## Captured premise evidence
- premise: P-01

### P-01 — frozen API, migration and base
- captured_at: 2026-10-29
- command: `python3 -c 'import json;d=json.load(open("contracts/api/v1/openapi.json"));print(d["info"]["version"],len(d["paths"]),sum(k in {"get","post","put","patch","delete","head","options","trace"} for p in d["paths"].values() for k in p),len(d["components"]["schemas"]))' && git rev-parse --short HEAD && ls db/migrations/versions/*0040*`
- captured_output:
  ```text
  1.11.0 176 198 517
  8fcdda42
  db/migrations/versions/20261029_0040_comparison_ai_reports.py
  ```
- interpretation: the C2 seal is unchanged at the start of FIX.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: `make gate-static`

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `tests/contract/api_v1/test_surface_counts_in_prose.py` (font data exclusion only)
- `src/auditmanager/bootstrap/composition.py` (comparison worker builder and call site only; integration slot)
- `src/auditmanager/executors/public.py` (exports of existing image validators to the integration seam only)
- `src/auditmanager/bootstrap/adapters.py` (AISHEET class docstring only)
- `src/auditmanager/comparison/work/model.py` (additive route seam only; integration slot)
- `src/auditmanager/comparison/spend/model.py`, `src/auditmanager/comparison/spend/caller.py` (additive attempt context seam and its binding before dispatch; integration slot)
- `src/auditmanager/comparison/spend/pull_images.py` (new pull crop publisher adapter)
- `src/auditmanager/comparison/ai_pairs/handler.py` (factory seam and route refusal handling only)
- `src/auditmanager/comparison/ai_sheets/handler.py` (factory seam only)
- `src/auditmanager/comparison/ai_sheets/service.py` (module docstring only)
- `src/auditmanager/comparison/ai_jobs/service.py` (estimate read for a paused live job; integration slot)
- `src/auditmanager/comparison/specification/method.py` (factory seam and route refusal handling only)
- `src/auditmanager/comparison/report/handler.py` (factory seam only)
- `src/auditmanager/comparison/queue/handler.py` (lazy factory construction and stable series binding for AI queue entries)
- `src/auditmanager/comparison/queue/repository.py` (fenced series attachment on a waiting entry only)
- `tests/unit/comparison/work/**`, `tests/unit/comparison/spend/**`, `tests/unit/comparison/ai_pairs/**`, `tests/unit/comparison/ai_sheets/**`, `tests/unit/comparison/specification/**`, `tests/unit/comparison/report/**`
- `tests/integration/comparison/work/**`, `tests/integration/comparison/queue/**`, `tests/integration/comparison/ai_jobs/**`, `tests/integration/composition/**`
- `docs/program/tasks/CMP-C2-FIX-01.md`, `docs/program/CMP-C2-FIX-01.md`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, root dependency and lock files, global styles, `web/**`, `infra/**`
- jobs, executors, analysis, ingest and other bounded-context internals
- other composition-root branches outside the comparison worker builder

## Non-goals
- no C3 contract fields or new API operation (`needs_consent` renewal, report pause, overview AI states, spec reason)
- no real model call in tests, no change to the deterministic comparison evidence
- no external ref update or deployment

## Deliverables
- exact font exclusion in the contract surface guard
- worker-only binding of the job's frozen executor revision and pinned model to the four AI handler factories
- durable series ID on AI sheet-change and report entries before their consent estimate, reused at execution
- estimate GET selects the remaining work of a paused `overrun` or `route_changed` job for renewed consent
- pull routes carry the comparison attempt and call ID, and publish image bytes under their verified blob descriptors before a runner task is written
- tests for correct revision/pin, missing route or key, and all four factory seams; `docs/program/CMP-C2-FIX-01.md`

## Required tests
- `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/api_v1/test_surface_counts_in_prose.py --basetemp=/tmp/pytest-cmp-c2-fix-01/contract`
- `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/comparison --basetemp=/tmp/pytest-cmp-c2-fix-01/unit`
- after `set -a; . ./.env; set +a`, `tests/integration/comparison` in one pytest process and `tests/integration/composition`
- final integration task runs full `make gate` on its exact clean candidate

## Integration contract
The worker uses the `comparison_ai_job.connection_revision_id` and `pinned_model` saved at start, opens the connection secret only through `executors.runtime.bind_connection` under the worker's private ring and destination policy, and hands a `CallRoute` to each handler. The route's attempt context is populated by the spend wrapper after its prepared row exists, before dispatch. A pull route publishes checked images through the durable blob publisher before creating a task; the task names the comparison attempt and call. An unavailable route or secret remains a typed refusal. Neither API nor a test process receives the private ring. The four factories still build without I/O for handler-register enumeration.

## Failure/idempotency/security cases
- missing revision, pin mismatch, secret unreadable or unsupported kind: fail closed; no fallback to an environment provider
- a recorded answer in tests is never a live model call
- model calls remain inside the spend journal and the module gate

## Rollback / feature flag
`AUDITMANAGER_COMPARISON_MODULES=none` prevents the comparison worker from claiming these items. Reverting this FIX restores named binder refusals and the previous contract guard result; it does not roll back data.

## Handoff
- changed files: contract prose guard; comparison worker composition, work and spend route seams, pull image publisher, two executor image-validator exports, four AI handler factories and two route refusals; AI estimate read; launch queue handler/repository; relevant tests; this task and `docs/program/CMP-C2-FIX-01.md`.
- checks/results: see the report; comparison integration 867 passed before final edits, AI integration 196 passed, queue integration 5 passed, spend/work integration 147 passed, pull DB 1 passed, pull unit 76 passed, focused 106 passed, full unit comparison 1661 passed before pull edits. The final-code broad rerun is the integration task's `make gate`.
- contracts: none changed; API `1.11.0`, 176/198/517 and migration `0040` stay frozen.
- risks: pull crop blobs need a retention or cleanup decision in the recovery audit; the API has no renewal command for a queue entry in `needs_consent`.
- integration notes: exact-candidate `make gate` reruns all broad suites before the C2 integration task publishes `origin/dev`; `origin/main` is out of scope.
- forbidden hotspots: `git diff --name-only 8fcdda42 -- contracts db/migrations web infra pyproject.toml uv.lock Makefile` prints nothing; the only composition hunk is the allowed comparison worker builder and call site.
