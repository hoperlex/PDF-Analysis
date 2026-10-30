# BETA-COST-PREFLIGHT-1030 — priced start consent

Active task: [`BETA-COST-PREFLIGHT-1030`](tasks/BETA-COST-PREFLIGHT-1030.md), base `8a437cbe`. This lane owns the serial API/bootstrap seal; sibling BETA-COST-WEB-1030 owns the existing start controls, and BETA-PDF-PRECHECK-1030 owns executor/source-preparation edits.

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
