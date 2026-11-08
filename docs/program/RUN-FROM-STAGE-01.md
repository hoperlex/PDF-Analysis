# RUN-FROM-STAGE-01 — «Запустить с этапа» (UI-A-60, R-151i, D-301)

Design of 2026-11-09 (lane S2). The owner's ruling `R-151i` fixed the meaning: a **new run** that reuses the earlier run's
completed stage outputs before the chosen stage and computes the rest; the estimate and the consent cover the remaining
stages only; the earlier run is unchanged (runs are immutable history). The owner was unreachable for the two points the
ruling left to the task; both are decided here and recorded as lane decisions, open to the owner's ruling.

## What the PC-01 chain makes possible

A standard run has four stages in a chain: `source_preparation` → `page_geometry_extraction` → `document_context_build` →
`text_analysis`; the evidence gate and the publication of findings follow and are never "reused" (they run on every run).
Every model call is made by `text_analysis` (and the extended review inside it). The first three stages are deterministic
functions of the version's bytes and publish content-addressed artifacts; none of them reads the analysis profile, the
prompt bundle or the norms snapshot. So the chain splits cleanly: a start from stage *S* takes the outputs of the stages
before *S*, and computes *S* and everything after it. The stages that can be chosen are the three after the first;
`source_preparation` reuses nothing (that is a re-audit, `reauditRun`) and stages PC-01 does not schedule have nothing to
start. The nine-stage graph of the registry is not a line, but PC-01 schedules a chain, and only the chain is offered.

## Decision 1 — the reuse rule (which output may be taken)

Per reused stage, in order; the first failure is the typed refusal `analysis_input_invalid` with `stage_id` and `reason`
(no new error code, nothing recomputed in its place, nothing written):

| reason | the output is refused when |
| --- | --- |
| `source_stage_not_completed` | the source has no `stage_result` for the stage, or it is not `succeeded` |
| `source_stage_version_changed` | its `stage_version` is not the registry's today (an older algorithm's output is not what a fresh run produces) |
| `source_stage_output_incomplete` | its artifacts lack a role the registry requires of the stage |
| `source_artifact_unavailable` | an artifact's blob is not `available` |
| `source_artifact_changed` | an artifact's recorded sha256 or size is not the reference's |
| `source_stage_inputs_changed` | the one input beside the version's bytes differs: whether the accepted consent lets pages without a text layer through (`extended-review-v3`), which changes what `source_preparation` and `document_context_build` do |

Deliberately **not** compared: analysis profile, prompt bundle, norms snapshot. They are not inputs of the reused stages and
are inputs of `text_analysis`, which is always computed; the new run records **today's** configuration exactly as a re-audit
does (`R-82`, `W55A-PIN-01`), which is the use of the feature (re-run the analysis on a changed prompt without redoing the PDF
work). The version is the same by construction. The source must be terminal (any of the four terminal states: a failed run
keeps the outputs of the stages that succeeded, which is the original's «продолжить с этапа») and of the standard analysis
(a member of an AR v3 group is refused as for a re-audit). The rule is asked three times with the same function
(`runs.stage_reuse.plan_stage_reuse`): when the price is asked, when the start is accepted, and when the executor
materialises the reuse (the rows and blobs may have changed in between); the last one fails the run, it does not fall back.

## Decision 2 — the idempotency key

The command is `start_run_from_stage`, keyed by the caller's `Idempotency-Key` header like every run start. The fingerprint
is the request: source run, chosen stage, the source's stored `frozen_input_digest`, and the cost consent. The same key with
the same request replays the run it created (also after the source's or the configuration's change); the same key with
another stage is `idempotency_key_reuse`. Two different keys for the same source and stage are two decisions (and two
payments), but not two in flight: while a run from that source and stage has not ended, a second is `conflict`. No semantic
key (source+stage) is derived on the server: the owner may legitimately want the same start twice, a day apart.

## Data flow

1. **Price.** `POST /runs/cost-estimate` with `start_from_run_id` + `start_stage_id` (both, and nothing that chooses a route).
   The server prices the stages the new run computes — all model calls are `text_analysis`'s, so the figure is that stage's —
   and answers `reused_stage_ids` / `computed_stage_ids`. The digest is bound to the source and stage; a digest from a
   re-audit or another stage is `run_cost_estimate_stale`.
2. **Start.** `POST /runs/{run_id}/start-from-stage` `{stage_id, cost_consent}` (`expert`, `admin`; 202). One transaction:
   check the reuse, claim the key, create the run with `started_from_run_id` and `start_stage_id` (migration 0060, frozen
   columns; `reaudit_of_run_id` stays NULL), queue it, enqueue its Job.
3. **Execute.** The executor reads the two columns, re-asks the rule, and writes the new run's own `stage_result` rows for the
   reused stages: `succeeded`, the **same artifact references** (no copy of bytes, no change to the source), metrics of the
   source plus `reused_from_run_id`, both times = the moment of reuse. It then runs the remaining stages as always; terminal
   selection reads the four rows as it always does, so findings, the gate and the export are unchanged. A second Attempt after
   a lost lease reaches the same rows by the same upsert.
4. **Show.** `RunStatus` gains `started_from_run_id` and `start_stage_id`; the run page says «Запущен с этапа N из прогона …»
   with a link to the source, marks the reused stages «из прогона …», and offers «Запустить с этапа» beside «Повторить прогон»
   (dialog: choose a stage, see the reused and computed stages, the estimate for the computed ones, consent, start).

## Not done here (debt)

`D-410` the two decisions above are the lane's and stand until the owner rules; `D-411` only the PC-01 chain is startable (the
original's later stages are not scheduled by PC-01); `D-412` no browser walk of the dialog, and the details table still reads
«0 с» for a reused stage; `D-413` the reuse writes no journal line (the run's frozen columns and its reused rows are the record);
`D-414` (closed) migration `0060` is chained after lane M1's `0059`.
