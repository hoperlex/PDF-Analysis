# Task CMP-JOB-HINT-01 — account for comparison calls in the Run dispatch hint

## Outcome
The Run dispatcher offers the next queued Run whose executor connection is free from both active Runs and active comparison model calls. The claim's existing locked check remains authoritative. D-260's wasted claim retries are prevented for a visible active comparison call.

## Depends on
- CMP-SPEND-01

## Frozen inputs
- domain contract: the C2 identifier catalog; unchanged
- API contract: `1.11.0`, 176 paths / 198 operations / 517 schemas; unchanged
- analysis/comparison/event contract: ADR-0025 decision 4 and `CMP-SPEND-01` active-call definition; unchanged
- migration head: `0040_comparison_ai_reports`; unchanged
- base commit: `8f23322df1ced8aaa253b2b495e76993104e41af`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: D-260 names a mismatch between the Run dispatch hint and its locked claim check.

### P-01 — frozen C2 tree and two SQL decisions
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; python3 -c 'import json; d=json.load(open("contracts/api/v1/openapi.json")); print(d["info"]["version"],len(d["paths"]),sum(k in {"get","post","put","patch","delete","head","options","trace"} for p in d["paths"].values() for k in p),len(d["components"]["schemas"]))'; rg -n '^revision: str' db/migrations/versions/20261029_0040_comparison_ai_reports.py; rg -n '^_NEXT_JOB =|^_CONNECTION_HAS_OTHER_ACTIVE_RUN =' src/auditmanager/jobs/repository.py`
- captured_output:
  ```text
  8f23322df1ced8aaa253b2b495e76993104e41af
  1.11.0 176 198 517
  69:revision: str = "0040_comparison_ai_reports"
  69:_CONNECTION_HAS_OTHER_ACTIVE_RUN = text(
  94:_NEXT_JOB = text(
  ```
- interpretation: the separate worktree is based on the exact C2 publication candidate. The locked claim already checks comparison calls; `_NEXT_JOB` only includes active Jobs and submitted Runs in `held`.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/jobs/repository.py`
- `tests/integration/comparison/spend/test_connection_single_user.py`
- `docs/program/tasks/CMP-JOB-HINT-01.md`
- `docs/program/CMP-JOB-HINT-01.md`
- `.venv`
- `.env`

## Lane resources
- foundation_instance: `auditmanager-cmp-job-hint-01`
- postgres_port: `58100`
- s3_api_port: `62100`
- s3_console_port: `62101`
- postgres_db: `auditmanager_cmp_job_hint_01`
- s3_bucket: `auditmanager-cmp-job-hint-01`

## Forbidden hotspots
- contracts, migrations, root dependency/lock files, composition root, global styles, and all other `jobs/**` files
- the locked `_CONNECTION_HAS_OTHER_ACTIVE_RUN` claim check and comparison spend writer
- remote refs, especially `origin/main`

## Non-goals
- no new connection policy, claim admission change, queue ordering change, or new schema
- no C2 publication change; the exact gated C2 SHA remains untouched

## Deliverables
1. Extend `_NEXT_JOB`'s `held` CTE with active `prepared`/`sent` comparison calls whose attempt is `created`/`leased`/`running`, mapped through the frozen connection revision.
2. A real PostgreSQL test that distinguishes active and terminal calls and proves the next free Run is offered without changing the claim's enforcement.
3. A short report with checks, integration and rollback notes.

## Required tests
- `git diff --check`
- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/comparison/spend/test_connection_single_user.py` on an isolated PostgreSQL test database at head `0040`
- the existing `tests/integration/jobs/test_connection_limit_claim.py` hint cases on that database
- SQL plan check that the new branch uses the partial `ix_comparison_model_call_open` index or measures why it does not

## Integration contract
Merge after C2 `origin/dev` publication into the next development candidate. `_NEXT_JOB` is an advisory read and may race a new call; the claim's transaction-scoped lock and check retain final authority. The query's held set must scan only open calls, not historical calls.

## Failure/idempotency/security cases
- terminal call or lost attempt frees the hint even if the historical call row remains; a call without a connection blocks nothing
- a submitted Run and an active Run still hold their connections as before; a Run without a connection remains eligible

## Rollback / feature flag
Reverting this hint branch restores the old advisory selection. The claim's locked protection is unchanged, and the default comparison module flag remains `none`.

## Handoff
- changed files: `src/auditmanager/jobs/repository.py`, `tests/integration/comparison/spend/test_connection_single_user.py`, this task and `docs/program/CMP-JOB-HINT-01.md`.
- commands/results: isolated `make up`, `make migrate`, the two integration files **31 passed**, SQL `EXPLAIN` uses `ix_comparison_model_call_open`, `py_compile` and `git diff --check` pass.
- contracts: API `1.11.0` and migration head `0040_comparison_ai_reports` unchanged.
- known limits: the dispatch hint is a snapshot and can race a new comparison call; the locked claim remains the final guard. No full gate is claimed for this separate branch.
- integration notes: merge after the exact C2 candidate is published to `origin/dev`; then update D-260 in the integrated debt register. No remote ref or forbidden hotspot is owned here.
