# Task AR-SET-PROMOTION-01 — promote a pinned normative retrieval set

task_id: AR-SET-PROMOTION-01

## Outcome

A caller with an independently reviewed map, source/build proofs and expected artifact digests can construct one canonical retrieval set for the named snapshot, refuse a mismatch before Blob dispatch, and complete the existing 0023 two-role custody transaction. An exact replay returns the same set identity. Run persistence can freeze the verified set ID at INSERT time, without activating a v3 runtime profile.

## Depends on

- `AR-ORIGINAL-CITATIONS-PLAN-01` — completed implementation map.
- `W57A-SEAL-01A` — completed 0023 set, Run pin and custody schema.
- `W57A-INT-SET-ARTIFACT-PREP-01` — completed canonical set and catalogue builders.
- `W57A-INT-RETRIEVAL-CANDIDATE-01` — completed pure candidate assembly.
- `W57A-INT-QUALIFICATION-READ-01` — completed stored snapshot/build fact reader.
- `W57A-INT-RETRIEVAL-WINDOW-READ-01` — completed complete embedding-window reader.

## Frozen inputs

- domain contract: sealed `1.0.0`; no reseal in this task.
- API contract: `1.0.0`, 87 paths / 99 operations / 284 schemas, 27 error codes.
- analysis/comparison/event contract: unchanged; v3 runtime remains unserved.
- migration head: `0031_executor_pull_channel`; reuse existing `0023_norm_citations` set/custody tables and Run column.
- base commit: `integration/beta-main` `2c6d863d9ccd3067be6319a819a4236bffcf6229`.
- governing inputs: `docs/program/AR-ORIGINAL-CITATIONS-PLAN-01.md`, `docs/program/dispatch/W57-PLAN.md` §A3.2, `R-135` code-first cadence.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: 0023 already declares immutable retrieval-set, two artifact custody roles and nullable Run pin, while W57 pure modules build but do not promote a set.

### P-01 — exact base and existing seams

- captured_at: 2026-10-22
- command: `git rev-parse HEAD; rg -n '^def (assemble_retrieval_candidate|compare_retrieval_candidate|read_snapshot_build_facts|read_snapshot_evidence|read_retrieval_windows|publish_bindings)|^        CREATE TABLE norm_retrieval_set' src/auditmanager/norms/retrieval/*.py src/auditmanager/norms/custody/service.py db/migrations/versions/20261016_0023_norm_citations.py`
- captured_output:
  ```text
  2c6d863d9ccd3067be6319a819a4236bffcf6229
  db/migrations/versions/20261016_0023_norm_citations.py:134:        CREATE TABLE norm_retrieval_set (
  src/auditmanager/norms/retrieval/candidate.py:126:def assemble_retrieval_candidate(
  src/auditmanager/norms/custody/service.py:516:def publish_bindings(
  src/auditmanager/norms/retrieval/window_reader.py:154:def read_retrieval_windows(
  src/auditmanager/norms/retrieval/source_reader.py:109:def read_snapshot_evidence(
  src/auditmanager/norms/retrieval/qualification_decision.py:64:def compare_retrieval_candidate(
  src/auditmanager/norms/retrieval/qualification_reader.py:115:def read_snapshot_build_facts(
  ```
- interpretation: the promotion service can reuse these exact modules and 0023 storage; this inventory alone does not prove a qualified corpus or an owner-reviewed map.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/retrieval/promotion.py`
- `src/auditmanager/norms/retrieval/promotion_repository.py`
- `src/auditmanager/norms/public.py`
- `src/auditmanager/runs/repository.py`
- `src/auditmanager/runs/commands.py`
- `tests/integration/norms/retrieval/test_promotion.py`
- `tests/integration/norms/custody/test_retrieval_set_promotion.py`
- `tests/integration/runs/test_retrieval_set_persistence.py`
- `docs/program/tasks/AR-SET-PROMOTION-01.md`
- `docs/program/AR-SET-PROMOTION-01.md`
- ignored `.env` in this worktree only, with the assigned disposable lane identity; remove after DB/Blob checks.
- ignored `.venv` symlink in this worktree only, pointing to existing `/root/projects/PDF-Analysis/.venv` so the pinned Makefile can find its interpreter; remove after DB/Blob checks without changing the shared environment.

## Lane resources

- foundation_instance: `auditmanager-ar-set-promotion-01`
- postgres_port: `57741`
- s3_api_port: `61542`
- s3_console_port: `61543`
- postgres_db: `auditmanager_ar_set_promotion_01`
- s3_bucket: `auditmanager-ar-set-promotion-01`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependency manifests/locks, `src/auditmanager/bootstrap/**`, `web/**`, global styles, shared test fixtures and conftest files.
- All other source and test paths, refs, tags and deployment stand.

## Non-goals

- No owner map authoring or claim of real normative qualification, live corpus import, v3 profile registration, executor dispatch, router/UI or model call.
- No assumption that one global map digest can produce six verified scope sets: 0023 UNIQUE identity is `(map_sha256, norms_snapshot_id, chunking_profile, embedding_profile, builder_version)`; scope-specific map digests or a future owned schema seal are required.
- No publication to `origin/dev` or `origin/main`; no migration or contract reseal.

## Deliverables

- A bounded promotion/custody workflow and exact replay/refusal checks using 0023; a cross-context read port in `norms/public.py`.
- Additive Run INSERT pin seam with default NULL, preserving v1/v2 behavior.
- Focused offline and, where capacity permits, real PostgreSQL/Blob tests; result report.

## Required tests

- Focused `pytest` for `test_promotion.py`, `test_retrieval_set_persistence.py` and real DB/Blob test when an isolated lane is available.
- `python -m compileall` for changed Python; `pytest tests/contract/program`; `git diff --check` and allowed-path audit.
- Complete `make gate` deferred to the integrator under `R-135`; no frontend battery or live journey in this unserved lane.

## Integration contract

The caller supplies reviewed map bytes and their independent SHA, independent source/embedding proof digests, and expected set/catalogue digests. Preparation reads one named snapshot/build, constructs and compares canonical bytes before an admission or external Blob effect. Each write/admission/finalization re-runs this read-only preparation and demands exact equality; a hand-built or stale prepared value cannot authorize a write. The caller must hold a consistent database read transaction for the named snapshot/build. A mismatch can only create an immutable rejected row; a matched candidate uses two custody admissions as the durable outbox, dispatches via the existing `CustodyDispatcher`, then inserts the verified row and publishes both bindings in one transaction. The public read port returns only a verified identity with matching confirmed custody. `RunRepository.create` may freeze that ID in its INSERT; a later owned runtime slice must select it for v3, add its digest to the frozen input and dispatch only after the transaction commits.

## Failure/idempotency/security cases

- Wrong snapshot/key/build/map/source/embedding evidence refuses before admission or Blob access; expected artifact SHA mismatch writes no admission and produces only a rejected row.
- Exact admission/finalization replays; a changed digest or set ID reuse refuses.
- Missing/poisoned custody, unavailable/mismatched Blob, or incomplete vector build cannot yield a verified set.
- All DB writes and Blob dispatch use the existing custody outbox/reconciliation boundary; no direct dual write.

## Rollback / feature flag

Revert the additive unserved code commit before runtime activation. Existing 0023 rows remain immutable and need no data rollback. The Run parameter defaults to NULL until a later integration task explicitly enables v3 selection.
The DB/Blob test lane uses minimal synthetic fixtures only; no 674-document import. Stop its containers after tests. Its volumes are disposable only after recording test evidence and only if they belong to `auditmanager-ar-set-promotion-01`; do not touch other lanes' volumes.
Do not start the lane while free space is below 6144 MiB or the integration gate is running. The assigned `.env` and `.venv` symlink are temporary and removed after lane checks; do not print its credentials into task reports.

## Handoff

- changed files: see `docs/program/AR-SET-PROMOTION-01.md`
- commands/results: see `docs/program/AR-SET-PROMOTION-01.md`
- known limits: no owner map or real qualified snapshot is asserted
- integration notes: no push or runtime activation in this lane
