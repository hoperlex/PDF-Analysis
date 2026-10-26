# EXEC-CROSSCHECK — one task answered by several explicitly chosen executors

Planning record, written 2026-10-26 on `f6ee66ee` (`origin/main`). Documentation only: no
slice below is started, frozen or dispatched, and nothing here changes a contract, a migration
or a ruling.

## What the owner asked for

The owner asked for «параллельное распознавание на разных исполнителях явно». By direct poll
(2026-10-26) he chose the reading «сверка: одно и то же»: one and the same fragment is answered
at once by several **explicitly chosen** executor connections; every answer is kept on its own;
the answers are compared and the differences are visible to the expert.

Not chosen: splitting different parts of one job across executors for speed, and image
recognition (the crop stage is not active; `EXECUTOR-CONNECTIONS-PLAN.md` §2.2).

## Facts of the tree on `f6ee66ee`

Each line was read in the code; none comes from a report.

| Fact | Where |
| --- | --- |
| A `text_analysis` stage makes **one** model call: «one document, one call, one artifact». | `analysis/text/stage.py:1`, call at `:377` |
| The AR v3 provider stage has its own single call site. | `runs/v3_provider_call.py:240` |
| The route is one primary plus an optional standby, for the single work kind `text_analysis`. | `executors/model.py:61`; `executor_route_event` check, migration `0030:360` |
| A run freezes its connection revision at start and binds it per Attempt. | `executors/resolver.py:103`, `:126` |
| The worker has one slot (`R-146j`) and an Attempt is cut off at 900 s. | `workers/service.py:200`; `jobs/lease.py:21` |
| A pull or SSH answer waits inside the Attempt, bounded by `effective_timeout`. | `executors/http_adapter.py:83` |
| `model_call` has no uniqueness beyond its primary key, so a second call for a stage does not collide. | `20260910_0002_pc01_schema.py`, table `model_call` |
| Model calls are written by `ModelCallJournal.prepare` / `.complete`. | `runs/executor.py:359`, `:393` |
| No code compares two model answers; the repository treats LLM output as non-canonical. | searched `analysis/`, `runs/`, `comparison/` |
| The route editor takes one primary and one standby. | `web/src/widgets/executor-routes/ui/executor-routes.tsx` |
| Route operations are `listExecutorRoutes` and `setExecutorRoute`. | `contracts/api/v1/openapi.json` |

One consequence shapes everything below: because a stage is **one** call, a cross-check does not
need a second slot or a second run. It is the same request sent to N adapters inside one
Attempt.

## Three shapes

| | A. Fan-out inside the Attempt | B. N separate runs, compared afterwards | C. A cross-check group of N runs |
| --- | --- | --- | --- |
| Real parallelism | yes: N threads inside one worker slot | no: one slot runs them one after another (`R-146j`) | no, for the same reason |
| Canonical result | the primary's answer stays the run's answer | each run is canonical on its own | each run is canonical on its own |
| New state | N answer rows per stage, a comparison record, a route with several members | a comparison between runs | a group record on the model of the AR v3 group |
| Contract and migration | route operations and one migration | one new read operation | a group, its operations and a migration |
| Watchdog | every call must fit the same 900 s Attempt | none new | none new |
| Main risk | the slowest executor sets the pace of the stage | the owner's «параллельное» is not met | same as B |

**Recommendation: A.** It is the only shape that is parallel without changing `R-146j`, and it
keeps one canonical answer (the primary's), so the pipeline downstream does not change.

## Design of shape A

1. **A route with a cross-check set.** Besides the primary and the standby, an administrator names
   up to `K` secondary connections for `text_analysis`, explicitly, in «Назначения». The set is
   part of the route event, so it is journalled and frozen at run start with the primary. A
   secondary is never promoted silently and never replaces a failed primary: the standby rule is
   unchanged (no silent fallback).
2. **Concurrent calls, bounded.** The stage sends the same `ModelRequest` to the primary and each
   secondary on its own thread. Every call takes its own `effective_timeout` against the same
   remaining watchdog; a call that does not finish by the stage's deadline is recorded as
   `timed_out`, not waited for. The primary's failure fails the stage as it does today; a
   secondary's failure never does.
3. **Answers are stored, not merged.** Each call gets its own `model_call` row and its own
   artifact reference, tagged with `connection_revision_id` and `identity_basis`. Nothing is
   written into the primary's artifact.
4. **A deterministic comparison, never an LLM.** The comparison is computed from the stored
   answers by code (equal / different fields of the structured answer, per finding). It is a
   separate, non-canonical record that cites the answers by identifier. It does not alter the
   deterministic comparison evidence and it is not a decision of the expert.
5. **The expert sees the difference.** The run review shows, per secondary, which fields differ
   from the primary. The expert's decision stays the only canonical one.
6. **Cost.** Each secondary is metered on its own `CostMeter` line; the run's ceiling counts all
   of them, so a cross-check cannot exceed the ceiling the owner set.

## Slices

One owner per shared slot (`AGENTS.md` §3). Order, each after the one before:

1. `EXEC-CROSS-ADR-01`: the decision record (route shape, canonical answer, comparison rule).
   Documentation only.
2. `EXEC-CROSS-ROUTE-01`: the route with a secondary set. **Owns the contract slot and migration
   `0033`.** Backend and the route operations; nothing calls a secondary yet.
3. `EXEC-CROSS-CALL-01`: the concurrent calls and the answer rows, behind a feature flag that
   defaults off. Composition root slot (`bootstrap/providers.py`).
4. `EXEC-CROSS-COMPARE-01`: the deterministic comparison record and its read operation.
5. `EXEC-CROSS-V3-01`: the same fan-out at the AR v3 provider stage (see "AR v3" below). It
   follows `EXEC-CROSS-CALL-01` and reuses its answer rows and comparison; it adds no table.
6. `EXEC-CROSS-WEB-01`: the multi-select in «Назначения» and the difference view in the review,
   for both kinds of run.

Each slice's checks include a mutation proof that its guard can fail, and the real-executor
journey (two connections on one stand) is an operator check, not a unit test.

## Owner answers (poll, 2026-10-26)

- **Who is canonical?** The primary's answer. Secondary answers are stored beside it and their
  differences are shown to the expert; a disagreement does not block the stage and the pipeline
  downstream does not change.
- **Which runs?** `text_analysis` **and** the six checks of AR v3.

## AR v3 (scope chosen above)

The six checks run as an atomic group of six Runs with their own identity and immutable pins
(`runs/v3_group.py`), and the provider stage has its own call site (`runs/v3_provider_call.py:240`).
Four constraints follow, to be checked in `EXEC-CROSS-ADR-01` before `EXEC-CROSS-V3-01` is frozen:

1. **The pinned model is the run's identity.** A secondary may answer on a different pinned model
   (`claude-opus-5`, `claude-sonnet-5`, `gpt-6-sol` are the pins today), but its answer is a
   non-canonical record and never the model identity the group's pins name.
2. **Six runs, K secondaries each.** Up to `6 x (K + 1)` calls per group; the cost ceiling and the
   one-slot worker (`R-146j`) bound it, so the group's wall time grows with the slowest executor.
3. **Review-only stays review-only.** The comparison is shown beside the provisional citations; it
   adds no numerical conclusion and nothing the expert must act on.
4. **The lease is released during the provider call** in the current code, so concurrent calls
   there must not hold a lease lock. This is the main reason it is its own slice.

## Still open for the owner

- **How many executors?** `K` secondaries per route; the plan proposes 3.
- **Always on, or per run?** The plan proposes per route (on while the set is non-empty), with the
  feature flag as the rollback.

## Non-goals

No image recognition, no split of one job across executors, no LLM judge of the answers, no
change to `R-146j` (one worker slot), no change to the standby rule.
