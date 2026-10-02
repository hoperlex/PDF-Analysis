# Task W48-DURABLE-01 — make provider and analysis-blob effects crash-auditable

## Outcome

Release blockers `A-01` and `A-02` are closed by one durable-execution owner:

- every production run has committed `Job`, current `Attempt` and opaque equality-only
  `execution_token` authority before its first external effect;
- every provider request has a committed call intent and stable `model_call_id` before dispatch,
  and a crash can leave only an explicit unresolved outcome which is never retried as if nothing
  happened;
- every analysis artifact has committed blob metadata and a publication intent before object
  publication, then becomes consumer-visible only when its stage result, blob availability and
  current-attempt check commit together;
- reconciliation can enumerate provider outcomes and object publications interrupted at every
  crash boundary without listing the bucket or silently deleting evidence.

This is the separate contract/migration slot directly authorised by the repository owner on
2026-10-02 after both W48 judges upheld `A-01` and `A-02`. It supersedes W48's original
no-migration freeze only for the paths and invariants below. It grants no ref publication.

## Depends on

- `W48-AUDIT` — completed at `c11f1b6`
- `W48-JUDGE-X` — completed and cross-examined at `349e824`
- `W48-JUDGE-Y` — completed and cross-examined at `9a31264`
- `W48-FIX-B` — completed and integrated at `e3fedd0`
- owner instruction of 2026-10-02 — explicit separate contract/migration authority for `A-01`
  and `A-02`

## Frozen inputs

- base commit: `e3fedd0fdf2f2eda18e55c22867201f5663717a6`
- domain contract: `1.0.0-draft.1` revision 8; existing `Job`, `Attempt`, `Lease`,
  `execution_token`, `stale_attempt` and `execution_token_invalid` semantics are authoritative
- analysis contract: `1.0.0-draft.1`; existing `attempt_authority` tuple and RC-01 through RC-09
  creation rules are authoritative
- API: 17 paths / 20 operations / 61 schemas; no wire change
- error catalog: 22; no new or reinterpreted code
- incoming migration head: `0013_norm_embeddings`
- outgoing migration head owned by this task: `0014_durable_analysis_effects`

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `tests/integration/db/test_migration_lifecycle.py`
- enumerator_owner: `W48-DURABLE-01`
- totality_query: `find db/migrations/versions -maxdepth 1 -type f -name '*.py' -print`

## Captured premise evidence

- premise: the exact dispatch base and incoming migration head are fixed, and the two upheld
  external-effect orderings are present on that base

### P-01 — exact dispatch base

- captured_at: 2026-10-02
- command: `git rev-parse HEAD`
- captured_output:
  ```text
  e3fedd0fdf2f2eda18e55c22867201f5663717a6
  ```
- interpretation: implementation branches from the merged W48-FIX-B subject; it does not prove
  any remote ref names this commit.

### P-02 — incoming migration head

- captured_at: 2026-10-02
- command: `env PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -c 'from auditmanager.shared.db.migrations import head_revision; print(head_revision())'`
- captured_output:
  ```text
  0013_norm_embeddings
  ```
- interpretation: the new migration has one linear predecessor; it does not authorise modifying
  any earlier migration.

### P-03 — provider effect precedes identity and persistence

- captured_at: 2026-10-02
- command: `rg -n "adapter\\.complete\\(request\\)|ModelCallId\\.new\\(\\)|_record_model_calls\\(" src/auditmanager/analysis/text/stage.py src/auditmanager/runs/executor.py`
- captured_output:
  ```text
  src/auditmanager/runs/executor.py:256:def _record_model_calls(
  src/auditmanager/runs/executor.py:441:        _record_model_calls(
  src/auditmanager/analysis/text/stage.py:226:        response = adapter.complete(request)
  src/auditmanager/analysis/text/stage.py:240:    model_call_id = ModelCallId.new()
  ```
- interpretation: the call is made before a call identity exists, and persistence is downstream;
  static order establishes the crash interval but not whether a historical crash occurred.

### P-04 — analysis object publication precedes stage-result persistence

- captured_at: 2026-10-02
- command: `rg -n "blob_store\\.put_blob|_persist\\(session" src/auditmanager/analysis/ports/artifacts.py src/auditmanager/runs/executor.py`
- captured_output:
  ```text
  src/auditmanager/runs/executor.py:664:        _persist(session, run_repo, run_id, result)
  src/auditmanager/runs/executor.py:691:        _persist(session, run_repo, run_id, text_result)
  src/auditmanager/analysis/ports/artifacts.py:72:    published = blob_store.put_blob(
  ```
- interpretation: stage functions can publish canonical bytes before their consumer-visible DB
  row exists; it does not enumerate objects already stranded in any deployed bucket.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/reviews/W48-AUDIT.md`, `docs/program/reviews/W48-JUDGE-X.md`,
  `docs/program/reviews/W48-JUDGE-Y.md`
- addendum_path: not_applicable

The judge and audit reports remain immutable. This task records closure evidence in its own
completion report and never rewrites their verdicts.

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `db/migrations/versions/20261002_0014_durable_analysis_effects.py`
- `src/auditmanager/jobs/**`
- `src/auditmanager/runs/carrier.py`
- `src/auditmanager/runs/executor.py`
- `src/auditmanager/runs/reconciliation.py`
- `src/auditmanager/runs/retry.py`
- `src/auditmanager/runs/scope.py`
- `src/auditmanager/analysis/text/stage.py`
- `src/auditmanager/storage/__init__.py`
- `src/auditmanager/storage/durable_publication.py`
- `src/auditmanager/ingest/reconciliation.py`
- `tests/integration/db/test_migration_lifecycle.py`
- `tests/integration/db/test_schema_shape.py`
- `tests/integration/db/test_durable_analysis_effects.py`
- `tests/integration/runs/**`
- `tests/integration/ingest/test_reconciliation.py`
- `tests/integration/ingest/test_reconciliation_reads_the_bytes.py`
- `tests/integration/ingest/test_reconciliation_rules_with_no_guard.py`
- `tests/integration/analysis/**`
- `tests/integration/analysis_text/**`
- `tests/integration/p02_journey/**`
- `tests/integration/exports/**`
- `docs/program/W48-DURABLE-01.md`

## Forbidden hotspots

- `contracts/**`, generated clients, API schemas and the error catalog: this task implements the
  already-frozen target semantics and does not change their bytes
- every migration before `20261002_0014_durable_analysis_effects.py`
- root dependency/lock files, frontend dependency/lock files, `Makefile`, workflows and global
  styles
- API routers, authentication, deployment state, credentials, public-host data and object
  deletion
- task briefs other than this dispatch document; immutable judge/audit reports;
  `CURRENT_STATE.md` and `DEBT_REGISTER.md`
- tags, `origin/dev`, `origin/main` and every deployment action

## Non-goals

- no remote/distributed worker, queue service, multi-host lease scheduler or automatic resume
- no API representation of Job, Attempt, Lease, token, provider intent or artifact intent
- no provider claim of exactly-once execution: a crash after remote acceptance can only be
  recorded as an unresolved outcome unless the provider offers an idempotency guarantee
- no silent adoption or deletion of orphan bytes; reconciliation reports and a later explicit
  operator policy decides remediation
- no mechanical repair of `A-03` cross-context import debt
- no alpha tag, live-host acceptance, development publication or main auto-deploy

## Deliverables

- one reversible linear migration instantiating Job/Attempt/Lease authority plus provider-call
  and analysis-artifact effect journals, with database checks and indexes
- a single public jobs repository that creates the first current Attempt, generates an opaque
  token, and equality-checks it under a database lock inside every guarded publication
- provider call intent committed before `adapter.complete()`, response/final provenance
  checkpoints, and fail-closed suppression of an automatic live retry after an ambiguous outcome
- durable analysis artifact publisher using the existing `temporary -> verify -> publish` store
  sequence and `BlobMetadataRepository` breadcrumb before canonical object publication
- binding of stage result + artifact intent + blob availability in one fenced transaction
- reconciliation reports for unresolved provider calls, unbound artifact publications and
  missing bound artifacts
- fault-injection tests at before/after-provider and before/after-object publication boundaries
- completion report `docs/program/W48-DURABLE-01.md`

## Required tests

- migrate a fresh PostgreSQL database from empty to `0014_durable_analysis_effects`, assert exact
  new relations/constraints/triggers, rerun safely and downgrade/upgrade on a disposable database
- kill/raise after a provider has accepted a request but before final provenance: another
  transaction sees the stable call identity, request digest and unresolved state; no automatic
  live retry occurs
- supersede or corrupt an execution token before publication: stage/artifact/provider/result
  publication is refused with no token value in logs or error details
- fail after blob verification, after intent commit, after object publish and before binding:
  every state is enumerable as unpublished or orphan; a successful path commits binding and is
  not reported detached
- remove or hide a bound analysis object in a disposable store: reconciliation reports its exact
  run/stage/role without bucket listing
- existing recorded PC-01 chain, retry provenance, cost, grounding, export and storage
  reconciliation suites remain green
- `git diff --check`; allowed-path-only diff; complete `make gate` before judging

## Integration contract

Every accepted run owns exactly one Job and a first Attempt before execution. The Attempt's
`execution_token` is secret-class, opaque and compared only for equality. A guarded transaction
locks the Job, proves `(run_id, job_id, attempt_id, execution_token)` still names its current
running Attempt, and only then writes consumer-visible state. The token is never an API field,
identity, log value or error detail.

A provider call allocates `model_call_id` and commits a redacted request intent before dispatch.
If no terminal provenance can be established, the intent remains explicitly unresolved and a
live call is not automatically repeated. A complete response is still represented by the
existing immutable `model_call` row; raw prompt and response bodies remain unstored.

An analysis artifact commits verified blob metadata plus an attempt-scoped intent before object
publication. The stage-result transaction checks current authority, binds every returned
artifact intent and advances its blob to `available`. A rollback can therefore leave an inert,
enumerable intent/object pair but never unindexed bytes that look published to a consumer.

## Failure/idempotency/security cases

- duplicate run execution finds the existing Job and is refused; it never mints a second first
  Attempt behind the same accepted command
- stale/superseded Attempt publication fails closed inside the writing transaction
- identical artifact bytes remain content-idempotent while each attempted publication remains
  attributable to its run/Attempt/stage
- a provider transport exception after dispatch is outcome-ambiguous, not evidence that no paid
  effect happened
- no token, prompt, response body, credential, bucket or object key is stored in an envelope,
  emitted to a log or returned through the API
- reconciliation uses DB breadcrumbs and point inspection only; the BlobStore port gains no
  list/delete/fallback operation

## Rollback / feature flag

No feature flag: the old ordering is a data-integrity defect and is not an admissible fallback.
Before any consumer deployment, rollback is the migration downgrade plus a revert of this task.
After consumer data exists, rollback is restore/forward-repair only: downgrading drops durable
effect evidence and is prohibited outside an owned disposable database.

## Handoff

- changed files and exact migration shape: recorded in `docs/program/W48-DURABLE-01.md`
- commands/results and fault-injection outcomes: recorded in the completion report
- contracts: external contract bytes remain unchanged; the existing Job/Attempt contract becomes
  instantiated runtime behaviour
- known limits: no distributed scheduler, automatic resume, orphan deletion or exactly-once
  provider promise
- integration notes: an independent durable-effects judge must inspect the exact candidate and
  rerun fault injection plus the complete gate before any later `W48-INT-CLOSE` decision; no
  remote ref moves under this task
