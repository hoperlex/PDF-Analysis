# BETA-COST-PREFLIGHT-1030 — priced start consent

Active task: [`BETA-COST-PREFLIGHT-1030`](tasks/BETA-COST-PREFLIGHT-1030.md), base `8a437cbe`. This lane owns the serial API/bootstrap seal; sibling BETA-COST-WEB-1030 owns the existing start controls, and BETA-PDF-PRECHECK-1030 owns executor/source-preparation edits.

## Early API provider milestone

Contract1.13.0 is additively extended to230paths/256operations/618schemas. `estimateRunCost` posts to `/runs/cost-estimate`; `estimateArV3GroupCost` posts to `/ar-v3-beta/groups/cost-estimate`. Both are expert-only, create no jobs and return the frozen `RunCostEstimate` shape. Existing starts accept optional strict `cost_consent{estimate_digest,ceiling_micros,confirmed}`. Raised-limit defaults remain off. The transport also retains historical price-match-v1 and admits root's new price-match-v2 in the two requested schemas.

The early generated provider is for parallel UI work; cost arithmetic/start validation/worker enforcement are still being implemented in this active lane. Adapter estimate/start consent paths fail closed while no cost policy is wired. This milestone is not the completed vertical slice and must not be published alone.

Focused DTO/security/contract-seal tests and generated-client byte verification are recorded with the milestone commit. Full gates and live spend remain deferred under the owner's instruction.

## Worker policy provider milestone

`runs.public.read_run_cost_policy(session,run_id,default_ceiling_usd,runs=None)` reads accepted command authority without opening another transaction. Historical missing consent retains the prior normal/raised policy. New accepted consent supplies the approved cap, billing mode, stable window/max-window bounds and exact model/rate/connection pins. Explicit metered caps remain enforced when raised output limits are selected; declared unmetered execution has no monetary halt. Group members receive only their allocated share of the group ceiling.

ProviderConfig carries additive approved fields for the executor owner to preserve across database provider binding. Text execution refuses changed approved model/rate/connection pins before a provider call. Focused cost-policy and existing raised-limit tests:32passed; compile/whitespace passed. The estimate/start persistence backend continues next; this provider alone is not the completed vertical slice.
