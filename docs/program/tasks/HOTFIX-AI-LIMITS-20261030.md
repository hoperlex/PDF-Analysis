# Task HOTFIX-AI-LIMITS-20261030 — temporary AR v3 limit switch

## Outcome

An expert can choose raised limits before starting the six AR v3 checks. An absent or off switch preserves the current cost ceiling and 16,000-token output request. On, it removes the application cost halt and requests up to 64,000 output tokens for all six Runs. The actual provider may refuse a lower limit. A worker restart does not change the choice.

## Depends on

- `CMP-SEAL-C1` (completed in `origin/dev` at base)
- `AR-V3-LIVENESS-PIPE-01` (completed in `origin/dev` at base)

## Frozen inputs

- domain/analysis/events contract: `1.10.0` at `e8567a19`, resealed together as `1.11.0` by this task's sole contract slot;
- API: 131 paths / 148 operations / 432 schemas at base, same counts after the optional field;
- migration head: `0039_comparison_core`, unchanged;
- base commit: `e8567a1981cbe35cf66bae4ce79b2877224df1be` (`origin/dev` at task start).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

### P-01 — AR v3 has a separate six-check start and finite output setting

- captured_at: 2026-10-30
- command: `rg -n 'StartArV3BetaGroupRequest|V3_BETA_SETTINGS' src/auditmanager/api/schemas/models.py src/auditmanager/runs/v3_worker.py`
- captured_output:
  ```text
  src/auditmanager/api/schemas/models.py:1216:class StartArV3BetaGroupRequest(_Object):
  src/auditmanager/runs/v3_worker.py:28:V3_BETA_SETTINGS = V3GenerationSettings(16_000, "high", {"type": "adaptive"})
  ```
- interpretation: this is the AR v3 path addressed here; it does not establish a provider's own output maximum.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev (integrator only, after focused checks)
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/HOTFIX-AI-LIMITS-20261030.md`
- `contracts/api/v1/**`
- `contracts/analysis/**`
- `contracts/domain/v1/**`
- `contracts/events/v1/**`
- `src/auditmanager/analysis/engine/result.py`
- `src/auditmanager/analysis/profiles/ar_v3/request_delivery.py`
- `src/auditmanager/api/routers/ar_v3_groups.py`
- `src/auditmanager/api/routers/ports.py`
- `src/auditmanager/api/routers/__init__.py`
- `src/auditmanager/api/schemas/models.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/runs/v3_group.py`
- `src/auditmanager/runs/v3_worker.py`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/proxy/tls-server.conf`
- `web/FRONTEND_LOCK.json`
- `web/openapi/openapi.json`
- `web/src/shared/api/**`
- `web/src/features/start-ar-v3-group/**`
- `web/tests/**`
- `tests/support/expected_facts.json`
- `tests/contract/api_v1/test_contract_seal.py`
- `tests/integration/composition/test_comparison_stub_operations.py`
- `tests/integration/runs/test_v3_worker_pipeline.py`
- `tests/unit/runs/test_v3_beta_settings.py`
- `tests/unit/runs/test_v3_relaxed_limits.py`

## Forbidden hotspots

- migrations and root dependency/lock files;
- composition root and global styles;
- navigation and favicon files owned by the parallel hotfix tasks;
- deterministic comparison evidence.

## Non-goals

- The ordinary section-analysis `startRun` and its cost/window policies;
- the provider's hard context/output limits or a guarantee that a 64,000-token request is accepted;
- release to `origin/main` or deployment.

## Deliverables

- Optional API field and coherent `1.11.0` family reseal, generated web client and frontend lock;
- per-group durable limit choice in the command outcome and fingerprint;
- AR v3 UI switch and worker execution policy;
- focused tests.

## Required tests

- `/root/projects/PDF-Analysis/.venv/bin/python -m pytest tests/unit/runs/test_v3_relaxed_limits.py tests/unit/runs/test_v3_beta_settings.py tests/integration/runs/test_v3_worker_pipeline.py tests/contract/api_v1/test_contract_seal.py tests/contract/api_v1/test_openapi_conformance.py -q`: pass;
- `npm --prefix web run typecheck`: pass;
- focused Vitest for AR v3 start and frontend lock: pass;
- `npm --prefix web run api:verify`: pass.

## Integration contract

`StartArV3BetaGroupRequest.relaxed_limits` is optional and strict boolean. Absent/false keeps the old request and cost behavior; true is fingerprinted and saved in the group's `command_record.outcome`, which every child Run references. Workers read the saved choice, request 64,000 tokens and skip only the cost-derived preflight/halt. The model call still records cost and refuses an unknown metered cost.

## Failure/idempotency/security cases

- A reused key with a different choice raises `idempotency_key_reuse`; existing groups accepted before this field replay with the old fingerprint.
- A malformed persisted choice fails before a model effect; an old outcome without the key means standard limits.
- Provider limits remain visible refusals; no fallback to a recorded answer or truncated output is introduced.

## Rollback / feature flag

The switch defaults off and is the temporary feature flag. To stop new raised-limit groups, hide/disable the UI choice. Keep worker support until already queued raised-limit groups reach terminal states; otherwise a rollback would silently change their accepted policy.

## Handoff

- Integrator reviews the common contract reseal and includes the checksum-pinned `web/FRONTEND_LOCK.json` in one combined commit. Its `content_commit` identifies the preceding 1.10.0 seal; the new byte identity is the checksum in this task's lock update.
- Integrator performs one push to `origin/dev` after combining the three independent hotfixes; no `origin/main` authority is conveyed.
