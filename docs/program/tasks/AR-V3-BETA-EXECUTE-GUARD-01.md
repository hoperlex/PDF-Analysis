# Task AR-V3-BETA-EXECUTE-GUARD-01 — refuse v3 Runs before an executor exists

task_id: AR-V3-BETA-EXECUTE-GUARD-01
status: implementation in progress

## Outcome

Executing a persisted AR v3 beta Run through any current executor entry point refuses before a Job, stage, Blob or provider effect. In particular, the in-process harness with no text-profile registry cannot substitute the AR v1 profile. Historical v1 and recorded v2 execution paths keep their existing behavior.

## Depends on

- `AR-V3-BETA-PROMPT-SEAL-01` — completed immutable v3 profile identity.
- `AR-V3-BETA-SIX-RUN-02` — completed durable six-Run group on `origin/dev`.

## Frozen inputs

- Base `origin/dev` commit: `1b605f9d4597927942a5a8951d3203ffa75bb191`.
- Domain/API/analysis/events contract `1.2.0`; migration head `0032_ar_v3_run_group`; product `VERSION=0.8.0`.
- Frozen v3 identity pair: `ap_01M5M28ZCDD8VPSP1BTAEW92YE` / `pb_01M5M28ZCDVCR37BX1884JGSPM`.
- Production trusted-pack registry remains empty; the complete v3 executor belongs to `AR-V3-BETA-EXECUTE-01` and is not provided by this guard.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the current executor chooses AR v1 when a caller omits `text_profiles`, and has only an explicit recorded-v2 branch.
- captured_at: 2026-10-23
- command: `rg -n -F -e 'if recorded_v2 or text_profiles is None' -e 'else _pinned_text_profile(run, text_profiles)' -e 'if recorded_v2:' src/auditmanager/runs/executor.py`
- captured_output:
  ```text
  867:    if recorded_v2:
  903:        if recorded_v2 or text_profiles is None
  904:        else _pinned_text_profile(run, text_profiles)
  1066:    if recorded_v2:
  ```
- interpretation: a v3 Run constructed by the six-Run group can enter the v1 branch in an in-process composition. The served profile registry currently refuses it, but that is not an executor-level guarantee.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/public.py`
- `src/auditmanager/runs/executor.py`
- `tests/integration/runs/test_v3_execution_guard.py`
- `docs/program/tasks/AR-V3-BETA-EXECUTE-GUARD-01.md`
- `docs/program/AR-V3-BETA-EXECUTE-GUARD-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots

Contracts, migration head, root dependency/lock files, composition root, global styles, original topics/norm maps/sets, provider adapters, CITE stage, other Run behavior, `origin/main`, tags and deployment host.

## Non-goals

No v3 provider dispatch, trusted-pack installation, approved map/set, numerical finding, CITE artifact or stand acceptance. This guard is a prerequisite within the roadmap's execution slice, not completion of `AR-V3-BETA-EXECUTE-01`.

## Deliverables

- Publicly exported immutable v3 identity pair for the Run boundary.
- Executor preflight that recognizes either v3 identity field and refuses before any effect, including a mismatched pair.
- Focused in-process tests proving v3 refusal with and without a profile resolver, zero effects, and historical v1/v2 discrimination.
- Report and queue note identifying this guard as completed while the full executor stays open.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/runs/test_v3_execution_guard.py tests/integration/runs/test_v2_recorded_executor_bridge.py -x --tb=short`.
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/analysis_packages tests/contract/api_v1/test_contract_seal.py -x --tb=short`.
- `git diff --check` and exact changed-path audit against this task's allowlist. Full `make gate` is deferred to the final beta candidate under `R-135`.

## Integration contract

Before any Job or stage, the current executor rejects a Run whose profile ID or bundle ID denotes the sealed v3 profile. The later full executor must replace this explicit stop with an equally early verified pack/set/Attempt path; it cannot route v3 through `AR_TEXT_PROFILE` or a text-profile registry fallback. Public v3 ID constants have the same bytes as the sealed resolver.

## Failure/idempotency/security cases

An exact v3 pair and either half of a mismatched v3 pair refuse without writes. A caller supplying a resolver that would return AR v1 cannot bypass the guard. No idempotency behavior changes.

## Rollback / feature flag

Revert this narrow guard before full v3 executor integration if needed. New production group starts are already disabled by the empty trusted-pack registry; removing this guard before a replacement executor is installed would reopen the in-process v1 fallback and is therefore not a safe production rollback.

## Handoff

- changed files: report
- commands/results: report
- known limits: complete v3 execution remains open
- integration notes: replace guard only with the verified v3 execution path
