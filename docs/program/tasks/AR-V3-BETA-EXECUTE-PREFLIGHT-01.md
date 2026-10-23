# Task AR-V3-BETA-EXECUTE-PREFLIGHT-01 — resolve one grouped Run under current Attempt

task_id: AR-V3-BETA-EXECUTE-PREFLIGHT-01
status: implementation in progress

## Outcome

Before any v3 provider effect, the executor can resolve one persisted six-Run member to its server-installed reviewed pack and exact scope/map/set pins under current Job/Attempt authority. A missing, replaced or ambiguous pack, foreign Run, mismatched immutable pin or stale Attempt refuses without a model call.

## Depends on

- `AR-V3-BETA-SIX-RUN-02` — completed durable group and trusted-pack registry.
- `AR-V3-BETA-EXECUTE-GUARD-01` — completed pre-effect refusal until full executor integration.
- `AR-V3-BETA-REQUEST-DELIVERY-01` — completed pure provider request bridge.

## Frozen inputs

- Base published `origin/dev`: `125efed23406f75b31e66c423e76d67fef381fd9`.
- Contract family/API `1.2.0`; migration head `0032_ar_v3_run_group`; `VERSION=0.8.0`.
- `ar_v3_run_group`/`ar_v3_run_group_member` immutable pins and `TrustedPackRegistry` are the only selection authorities; no request-supplied SHA is trusted.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: group membership is persisted, and JobRepository can validate a current Attempt, but no Run-side bridge combines the two.
- captured_at: 2026-10-23
- command: `rg -n -F -e 'INSERT INTO ar_v3_run_group_member' -e 'class TrustedPackRegistry' src/auditmanager/runs/v3_group.py; rg -n -F -e 'def require_current' src/auditmanager/jobs/repository.py`
- captured_output:
  ```text
  87:class TrustedPackRegistry:
  326:            INSERT INTO ar_v3_run_group_member
  746:    def require_current(self, session: Session, authority: AttemptAuthority) -> None:
  ```
- interpretation: the input authority can be resolved without a new contract or schema; the future executor still must check set Blob custody and build/deliver the request separately.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/runs/v3_execution_binding.py`
- `src/auditmanager/runs/public.py`
- `tests/integration/db/test_ar_v3_run_group.py`
- `docs/program/tasks/AR-V3-BETA-EXECUTE-PREFLIGHT-01.md`
- `docs/program/AR-V3-BETA-EXECUTE-PREFLIGHT-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots

Contracts, migration head, composition root, root dependency/lock files, global styles, original topics/norm maps/sets, provider transports, Run executor, CITE publication, `origin/main`, tags and deployment host.

## Non-goals

No retrieval-set Blob read, model call, StageResult, CITE artifact, finding, approved normative map, numeric verdict, pack activation or stand operation. This is a read-only authority preflight inside the full execution roadmap slice.

## Deliverables

- Typed Run execution binding resolved only from a current Attempt, persisted group membership and server registry.
- Full comparison of group/Run/project/version/profile/bundle/snapshot/provider/pack/scope/map/set/digest pins; one read-only database projection.
- Real PostgreSQL tests for successful six-scope resolution, missing/changed pack, foreign Run and fenced Attempt, with zero provider effect.
- Report and roadmap note preserving the open full-executor boundary.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/db/test_ar_v3_run_group.py -x --tb=short` on the isolated PostgreSQL lane.
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/runs/test_v3_execution_guard.py tests/integration/analysis/test_ar_v3_request_delivery.py -x --tb=short`.
- `git diff --check` and exact allowed-path inventory. Full `make gate` belongs to final beta acceptance under `R-135`.

## Integration contract

The future executor calls this preflight after committing its Job/Attempt, uses the returned immutable map/set/scope pins to load the custody-verified set, then calls `prepare_beta_v3_request` and `build_v3_model_request`. It rechecks current Attempt and set authority before dispatch and after response. The binding cannot be cached across Attempts or used as a substitute for Blob custody.

## Failure/idempotency/security cases

No installed pack, a pack with changed digest, a Run outside a six-Run group, a swapped set/scope or stale Attempt refuses. Repeated reads under one current Attempt return equal pins and make no write. Idempotent group creation remains unchanged.

## Rollback / feature flag

This preflight is unserved and read-only. Revert it before full executor integration or leave it unused; the existing v3 execution guard and empty production pack registry remain active.

## Handoff

- changed files: report
- commands/results: report
- known limits: no Blob custody or provider dispatch
- integration notes: future executor consumes this binding only within current Attempt
