# BETA-COST-PREFLIGHT-1030 — priced start consent

Completed backend/provider task: [`BETA-COST-PREFLIGHT-1030`](tasks/BETA-COST-PREFLIGHT-1030.md), base `8a437cbe`. This lane owns the serial API/bootstrap seal; sibling BETA-COST-WEB-1030 owns the existing start controls, and BETA-PDF-PRECHECK-1030 owns executor/source-preparation edits.

## Early API provider milestone

Contract1.13.0 is additively extended to230paths/256operations/618schemas. `estimateRunCost` posts to `/runs/cost-estimate`; `estimateArV3GroupCost` posts to `/ar-v3-beta/groups/cost-estimate`. Both are expert-only, create no jobs and return the frozen `RunCostEstimate` shape. Existing starts accept optional strict `cost_consent{estimate_digest,ceiling_micros,confirmed}`. Raised-limit defaults remain off. The transport also retains historical price-match-v1 and admits root's new price-match-v2 in the two requested schemas.

The early generated provider is for parallel UI work; cost arithmetic/start validation/worker enforcement are still being implemented in this active lane. Adapter estimate/start consent paths fail closed while no cost policy is wired. This milestone is not the completed vertical slice and must not be published alone.

Focused DTO/security/contract-seal tests and generated-client byte verification are recorded with the milestone commit. Full gates and live spend remain deferred under the owner's instruction.

## Worker policy provider milestone

`runs.public.read_run_cost_policy(session,run_id,default_ceiling_usd,runs=None)` reads accepted command authority without opening another transaction. Historical missing consent retains the prior normal/raised policy. New accepted consent supplies the approved cap, billing mode, stable window/max-window bounds and exact model/rate/connection pins. Explicit metered caps remain enforced when raised output limits are selected; declared unmetered execution has no monetary halt. Group members receive only their allocated share of the group ceiling.

ProviderConfig carries additive approved fields for the executor owner to preserve across database provider binding. Text execution refuses changed approved model/rate/connection pins before a provider call. Focused cost-policy and existing raised-limit tests:32passed; compile/whitespace passed. The estimate/start persistence backend continues next; this provider alone is not the completed vertical slice.

## Functional start backend milestone

`RunCostPreflight` now recomputes a source/classification/profile/preset/route/model/rate-bound estimate in the accepting transaction. New served ordinary and six-scope AR starts require explicit confirmed consent at or above the estimate; accepted command outcomes retain the approval and actor, per-member group shares, stable window size and sufficient window bound. Historical command replays keep their accepted result. Large ordinary sections can explicitly approve more than twelve windows without removing pages. New approved caps remain active with raised output limits; unmetered routes remain explicit. The complete next request and its full output allowance must fit the remaining approved cap before provider intent/dispatch.

Focused evidence at this milestone: thirteen pure preflight cases cover all fourteen section profiles, large inputs, arithmetic, stale source/classification/route/preset/rates, raised output choice, unmetered and pre-call cap. Three PostgreSQL cases on the assigned 58050 database pass: normal/raised large acceptance and durable replay, missing/low/stale consent creates no command/run/job/call. No model call or S3 write was performed. Reaudit's separate endpoint is the next explicitly assigned owner followup; this milestone does not claim the entire task closed.

## Reaudit preflight provider

The final transport uses the existing POST `/runs/cost-estimate` with optional `reaudit_of_run_id` and required matching `version_uid`; no extra GET operation was introduced. The server restores the original named connection or selects today's route, and uses today's section profile without a preset or raised-limit override. The source Run ID is part of the fresh consent digest. POST `/runs/{run_id}/reaudit` accepts an optional `ReauditRunRequest` body containing `cost_consent`; a new served command requires approval, while accepted historical keys still replay. Four focused PostgreSQL cases now pass, including refusal of the parent's paid approval and durable accepted rerun replay. Current additive API1.13.0 surface:230paths/256operations/619schemas; migration0043 unchanged.


## Final handoff

The backend/provider slice is complete. Root alone integrates the sibling start/reaudit UI and PDF-precheck executor, updates remaining integration metadata and publishes dev. The two optimisation algorithm properties retain v1 and admit v2 with no contradictory old const. Served/authored OpenAPI semantic comparison passes after this correction.

Validation:71 focused unit/DTO/contract cases PASS (cost source/rate/model/preset binding, all14 normal profiles, raised caps, all6 AR scope estimates and unmetered);4 SQL cases PASS on assigned PostgreSQL58050 (large normal/raised acceptance, refusal before writes, restart replay, fresh re-audit approval);1 served/authored semantic conformance PASS. Generated verification and compile/whitespace pass. No provider request, S3 write, full gate, whole battery or build ran.

An additional broad prose/C4-seal check reported5 inherited failures: obsolete253-operation/227-path expectations, a former C4 stub test now invoking a working adapter without sessions, and old current-count prose across integration-owned API/infra/BFF/P02 files. Root accepted the remaining metadata pass; these are not hidden as passing checks. The authored OpenAPI current description and this provider's lock/count metadata are corrected here.

Limitations: input tokens and money are estimates using the selected pinned rate card and conservative character/output allowances, not measured invoices. Every fresh provider request is checked against the remaining explicit cap; measured usage is retained and checked after a response. Unknown source counts fail closed. Historical command keys retain their accepted outcomes; new commands require new approval. AR v3 estimates still require the installed reviewed six-scope pack and verified normative inputs. UI behavior is delivered by BETA-COST-WEB-1030 and BETA-REAUDIT-COST-WEB-1030, and worker approval propagation by BETA-PDF-PRECHECK-1030.

Integration: merge the lane through the final seal metadata commit after content commits96c48977,29c9c870,3621092d and6ea9459f; preserve both additive analysis.public cost and PDF-precheck exports. Composition now sets require_cost_consent=True; do not expose it without the sibling UI. Contract1.13.0 is230paths/256operations/619schemas, migration0043 unchanged. No root dependencies, migration source, executor.py, source_preparation, global styles, feature UI, remote refs or tags were modified in this lane.

Changed files from the assigned base (plus this final seal and lock):

- `contracts/api/v1/README.md`
- `contracts/api/v1/openapi.json`
- `contracts/domain/v1/error-codes.json`
- `docs/program/BETA-COST-PREFLIGHT-1030.md`
- `docs/program/tasks/BETA-COST-PREFLIGHT-1030.md`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/analysis/text/config.py`
- `src/auditmanager/analysis/text/cost.py`
- `src/auditmanager/analysis/text/stage.py`
- `src/auditmanager/analysis/text/windowed.py`
- `src/auditmanager/analysis/text/windows.py`
- `src/auditmanager/api/routers/ar_v3_groups.py`
- `src/auditmanager/api/routers/execution.py`
- `src/auditmanager/api/routers/ports.py`
- `src/auditmanager/api/routers/runs.py`
- `src/auditmanager/api/schemas/models.py`
- `src/auditmanager/api/security.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/bootstrap/providers.py`
- `src/auditmanager/runs/commands.py`
- `src/auditmanager/runs/cost_policy.py`
- `src/auditmanager/runs/preflight.py`
- `src/auditmanager/runs/provider.py`
- `src/auditmanager/runs/public.py`
- `src/auditmanager/runs/v3_group.py`
- `src/auditmanager/runs/v3_provider_call.py`
- `src/auditmanager/runs/v3_worker.py`
- `tests/contract/api_v1/test_run_cost_preflight.py`
- `tests/integration/runs/test_cost_preflight.py`
- `tests/support/expected_facts.json`
- `tests/unit/runs/test_cost_policy.py`
- `tests/unit/runs/test_cost_preflight.py`
- `web/FRONTEND_LOCK.json`
- `web/openapi/openapi.json`
- `web/src/shared/api/authorization.ts`
- `web/src/shared/api/generated/client.gen.ts`
- `web/src/shared/api/generated/index.ts`
- `web/src/shared/api/generated/operations.gen.ts`
- `web/src/shared/api/generated/types.gen.ts`
