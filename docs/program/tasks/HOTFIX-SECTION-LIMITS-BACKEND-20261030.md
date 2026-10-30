# Task HOTFIX-SECTION-LIMITS-BACKEND-20261030 — section Run limit policy

## Outcome

Every non-AR section `startRun` accepts an optional raised-limit choice. An accepted choice survives worker restart, requests at most 64,000 output tokens under a distinct immutable profile/bundle identity, and removes the application cost halt while still recording actual spend. The operational 12-window document-size bound remains.

## Depends on

- `HOTFIX-UI-INT-20261030` (completed at base `06b94745`)

## Frozen inputs

- domain/API/analysis/events shared contract: `1.11.0`, resealed together as `1.12.0` by this task's sole contract slot;
- API: 131 paths / 148 operations / 432 schemas, unchanged after optional field;
- migration head: `0039_comparison_core`, unchanged;
- base commit: `06b947459fa7535f340af75b625f40af88d2f18f` (`origin/dev` at task start).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

### P-01 — section analysis routes through a distinct `startRun`

- captured_at: 2026-10-30
- command: `rg -n 'class StartRunRequest|def start_audit_run|MAX_ANALYSIS_WINDOWS' src/auditmanager/api/schemas/models.py src/auditmanager/runs/commands.py src/auditmanager/analysis/text/budget.py`
- captured_output:
  ```text
  src/auditmanager/api/schemas/models.py:1201:class StartRunRequest(_Object):
  src/auditmanager/runs/commands.py:528:def start_audit_run(
  src/auditmanager/analysis/text/budget.py:191:MAX_ANALYSIS_WINDOWS: Final[int] = 12
  ```
- interpretation: the ordinary start and its operational window bound are separate from the already shipped AR v3 group.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev (integrator only, after focused checks)
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/HOTFIX-SECTION-LIMITS-BACKEND-20261030.md`
- `contracts/api/v1/**`
- `contracts/analysis/**`
- `contracts/domain/v1/**`
- `contracts/events/v1/**`
- `src/auditmanager/analysis/engine/result.py`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/analysis/text/cost.py`
- `src/auditmanager/analysis/text/profile_registry.py`
- `src/auditmanager/analysis/text/stage.py`
- `src/auditmanager/analysis/text/windowed.py`
- `src/auditmanager/analysis/text/windows.py`
- `src/auditmanager/api/routers/__init__.py`
- `src/auditmanager/api/routers/ports.py`
- `src/auditmanager/api/routers/runs.py`
- `src/auditmanager/api/schemas/models.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/providers.py`
- `src/auditmanager/runs/commands.py`
- `src/auditmanager/runs/executor.py`
- `src/auditmanager/runs/provider.py`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/proxy/tls-server.conf`
- `web/FRONTEND_LOCK.json`
- `web/openapi/openapi.json`
- `web/src/shared/api/**`
- `tests/support/expected_facts.json`
- `tests/contract/api_v1/test_contract_seal.py`
- `tests/integration/composition/test_comparison_stub_operations.py`
- `tests/unit/analysis/test_text_profile_registry.py`
- `tests/unit/runs/test_section_relaxed_limits.py`

## Forbidden hotspots

- migrations, root dependency/lock files and composition root;
- global styles and frontend start control owned by `HOTFIX-SECTION-LIMITS-WEB-20261030`;
- AR v3 group command/worker behavior and comparison evidence.

## Non-goals

- changing the provider's own context/output limit;
- lifting the 12-window operational bound, watchdog or job lease policy;
- changing `reauditRun`, whose separate request has no raised-limit control;
- publishing to `origin/main` or claiming deployment.

## Deliverables

- strict optional API boolean, coherent 1.12.0 contract family, generated client and frontend lock;
- durable command flag/fingerprint and exact registered profile variants for 14 sections;
- execution cost policy and window sizing with focused tests.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest tests/unit/analysis/test_text_profile_registry.py tests/unit/runs/test_section_relaxed_limits.py tests/contract/api_v1/test_contract_seal.py -q`: pass;
- `npm --prefix web run api:verify`: pass;
- `npm --prefix web run typecheck`: pass after frontend integration.

## Integration contract

`StartRunRequest.relaxed_limits` is optional strict boolean. Missing/false preserves the old fingerprint, profile pair, 16k request and cost ceiling. True is fingerprinted, persisted in the successful command outcome, routed to a new stable `ap_`/`pb_` pair per section, and executed with a 64k output request and no application cost halt. Cost records and provider refusals remain visible. Existing Runs resolve their old pair and default-off policy. The 12-window bound is checked before command claim using a versioned, fixed $1 sizing calibration independent of the configured cost ceiling; the same sizing rule is used after worker restart, so window custody keys stay stable when the ceiling changes.

## Failure/idempotency/security cases

- Reusing a key with a different boolean raises `idempotency_key_reuse` in either direction; old successful commands replay with the unchanged default fingerprint.
- A malformed or mismatched durable command/bundle policy fails before model effects.
- Provider output/context refusals and recorded-mode request-digest misses are explicit failures; no silent fallback or truncation is added.

## Rollback / feature flag

The UI switch defaults off. If hidden, new Runs use old limits; keep backend support until queued raised-limit Runs are terminal so accepted work does not silently change policy.

## Handoff

- changed files: `contracts/api/v1/**`, `contracts/analysis/**`, `contracts/domain/v1/**`, `contracts/events/v1/**`; `src/auditmanager/analysis/{engine/result.py,public.py,text/{cost.py,profile_registry.py,stage.py,windowed.py,windows.py}}`; `src/auditmanager/api/{routers/{__init__.py,ports.py,runs.py},schemas/models.py}`; `src/auditmanager/bootstrap/{adapters.py,providers.py}`; `src/auditmanager/runs/{commands.py,executor.py,provider.py}`; `infra/deploy/proxy/{nginx.conf,tls-server.conf}`; generated `web/src/shared/api/**`, `web/openapi/openapi.json`, `web/FRONTEND_LOCK.json`; `tests/{unit/runs/test_section_relaxed_limits.py,contract/api_v1/test_contract_seal.py,integration/composition/test_comparison_stub_operations.py,support/expected_facts.json}`; this task file.
- commands/results: targeted Python unit and contract suite 207 passed; `npm --prefix web run api:verify` OK (148 operations, SHA `c643581bd1e1c061d81e296cf577e2ab174fdb789e90a877286f0bb43d3229cc`); `npm --prefix web run typecheck` OK; `git diff --check` OK; frontend lock and OpenAPI snapshot hashes match.
- new/changed contracts: optional strict `StartRunRequest.relaxed_limits` and shared family `1.12.0`, 131 paths / 148 operations / 432 schemas; no new domain identity, error code, state machine or migration.
- known limits: the 12-window operational bound remains; the provider may reject 64k or its combined context, and recorded mode requires a matching 64k request recording. Re-audit has no raised-limit control.
- integration notes: combine this backend and the separately owned start-control UI, update `CURRENT_STATE.md` in the integration lane, then publish one fast-forward commit to `origin/dev`. The new profile pairs and command policy must stay deployed until accepted raised-limit Runs finish.
- forbidden hotspots: no migration, root dependency/lock file, `bootstrap/composition.py`, global style, AR v3 command/worker or comparison evidence changed by this lane.
