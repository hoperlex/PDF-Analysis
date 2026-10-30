# Task BETA-COST-PREFLIGHT-1030 — priced consent before analysis starts

## Outcome
Before ordinary section analysis or the six-check AR v3 group starts, the application estimates the selected model's cost, asks the expert to approve a sufficient explicit ceiling and persists that approval before any provider spend. Source/route/model/preset changes invalidate stale consent; unmetered execution is explicit.

## Depends on
- HOTFIX-SECTION-LIMITS-INT-20261030

## Frozen inputs
- domain contract: owner's2026-10-30 decision to price large documents before start and request consent to a sufficient limit
- API contract: current1.13.0,228paths/254operations/614schemas; this lane holds the sole additive API seal through handoff
- migration head:0043_stage_ai_generations; existing command outcomes retain approval, no new DDL planned
- prior behavior: both raised-limit controls remain default off; accepted historical choices retain their semantics
- base commit: `8a437cbe15c47b1655e3ef7268bd1c60a657fdd2`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json`
- enumerator_owner: BETA-COST-PREFLIGHT-1030
- totality_query: focused contract operation/schema inventory and generated-client verification

## Captured premise evidence
- premise: parent assigned the full vertical slice and sole contracts/API/bootstrap slot; PDF precheck owner retains executor/source-preparation implementation.

### P-01 — frozen clean owner-hotfix base
- captured_at:2026-10-30
- command: `git status --short; git rev-parse HEAD`
- captured_output:
  ```text
  8a437cbe15c47b1655e3ef7268bd1c60a657fdd2
  ```
- interpretation: owner hotfixes are integrated; no pending files belong to another lane here.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/runs/commands.py`
- `src/auditmanager/runs/provider.py`
- `src/auditmanager/runs/preflight.py`
- `src/auditmanager/runs/cost_policy.py`
- `src/auditmanager/runs/v3_group.py`
- `src/auditmanager/runs/v3_worker.py`
- `src/auditmanager/runs/v3_provider_call.py`
- `src/auditmanager/runs/public.py`
- `src/auditmanager/analysis/text/cost.py`
- `src/auditmanager/analysis/text/config.py`
- `src/auditmanager/analysis/text/windows.py`
- `src/auditmanager/analysis/text/windowed.py`
- `src/auditmanager/analysis/text/profile_registry.py`
- `src/auditmanager/analysis/text/stage.py`
- `src/auditmanager/analysis/text/budget.py`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/api/schemas/**`
- `src/auditmanager/api/routers/runs.py`
- `src/auditmanager/api/routers/execution.py`
- `src/auditmanager/api/routers/ar_v3_groups.py`
- `src/auditmanager/api/routers/ports.py`
- `src/auditmanager/api/security.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/bootstrap/providers.py`
- `contracts/**`
- `web/openapi/**`
- `web/src/shared/api/generated/**`
- `web/src/shared/api/authorization.ts`
- `web/FRONTEND_LOCK.json`
- `web/src/features/start-run/**`
- `web/src/features/start-ar-v3-group/**`
- `web/tests/unit/start-run/**`
- `web/tests/unit/analysis-settings/**`
- `web/tests/unit/api/**`
- `tests/unit/runs/**`
- `tests/unit/analysis_text/**`
- `tests/integration/runs/**`
- `tests/integration/composition/**`
- `tests/contract/api_v1/**`
- `tests/support/expected_facts.json`
- `docs/program/tasks/BETA-COST-PREFLIGHT-1030.md`
- `docs/program/BETA-COST-PREFLIGHT-1030.md`
- `.venv`
- `.env`

## Lane resources
- foundation_instance: `auditmanager-cmp-stage-ai-01`
- postgres_port: `58050`
- s3_api_port: `62050`
- s3_console_port: `62051`
- postgres_db: `auditmanager_cmp_stage_ai_01`
- s3_bucket: `auditmanager-cmp-stage-ai-01`

## Forbidden hotspots
- runs/executor.py and PDF/source-preparation paths reserved to BETA-PDF-PRECHECK-1030
- root dependency/lock files, global styles, migration head without root serial grant
- UI implementation transferred to sibling BETA-COST-WEB-1030; this lane supplies backend/API/generated provider only
- optimisation implementation owned by root; only its v1/v2 transport literal widening is included in this seal
- remote refs, release tags and deployment

## Non-goals
- no changing supplier/model rate cards, hiding measured spend, silent input truncation or provider fallback
- no removal of the owner raised-limit controls and no retroactive rewrite of accepted commands
- no full gates/heavy batteries or live provider window

## Deliverables
- read-only cost preflight for ordinary profiles and trusted AR v3 six-group, with exact source/route/model/rate digest
- explicit approved ceiling persisted in accepted command and enforced by worker before further spend
- API/router/auth/bootstrap and visible estimate/confirmation flow in existing start controls
- additive generated transport/client seal, preserving optimisation match algorithm v1 and adding v2
- focused recorded tests, report and exact-SHA handoff

## Required tests
- short cost arithmetic/digest/consent unit cases and recorded start/worker SQL cases
- generated API/client verification and focused start-control tests/type checks
- compile/whitespace; no complete gate or whole-suite execution

## Integration contract
Parent followup grant after working start SHA3621092d: reaudit is also a new paid start, so POST `/runs/cost-estimate` with optional reaudit_of_run_id derives the current source/route on the server and POST reaudit requires fresh cost consent for a new command. Historical accepted replay is preserved. No preset is reapplied on reaudit; original explicitly named executor is retained as before.

Estimate and start share immutable route/source/profile/preset inputs. Start validates confirmed fresh consent before enqueue, then records approval in the durable command outcome. PDF executor owner consumes the public persisted cost-policy seam. Explicit approved caps apply to new starts while raised mode retains its token/window choice; historical commands without approval keep prior semantics. Parent alone integrates/publishes.

## Failure/idempotency/security cases
- changed document/classification/profile/preset/model/route or digest refuses stale consent before a job/call exists
- missing/unconfirmed/insufficient ceiling refuses; unmetered is labelled and never reported as measured money
- replay of an accepted command retains its original consent and frozen model authority
- approved cap checks do not silently omit document pages; every model call keeps existing spend/effect fencing

## Rollback / feature flag
Keep workers capable of reading accepted approvals until those Runs are terminal. UI controls can be hidden first; historical commands and owner relaxed-limit flags retain their prior meanings.

## Handoff
- changed files: exact committed inventory in `docs/program/BETA-COST-PREFLIGHT-1030.md`; backend/API/generated transport only, feature UI belongs to sibling lanes
- commands/results:71 focused unit/DTO/contract cases PASS;4 SQL acceptance/replay cases PASS; served/authored semantic conformance PASS; generated-client verification PASS; compile/whitespace PASS. Inherited wider prose/C4-stub drift reported to root for its final metadata pass.
- known limits: estimates use pinned rates and conservative token/output bounds, not a promise of measured spend
- integration notes: root sole integrator, serial API slot released only on handoff
