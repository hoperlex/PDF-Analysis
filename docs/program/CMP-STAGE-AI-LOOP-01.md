# CMP-STAGE-AI-LOOP-01 — bounded durable follow-up and control edges

Task: [`CMP-STAGE-AI-LOOP-01`](tasks/CMP-STAGE-AI-LOOP-01.md). Runtime input `13b17880`; root-owned cancel/dispatch provider consumed at base `a9be8659`. No contract, migration, shared service or remote ref is authored by this lane.

## Behavior

Each reviewer chunk, classifier group and synthesis plan can perform its main call, one model context-request pass and one unparsed-record coverage pass. All use the original immutable group/source digest and evidence IDs, the pinned shared route and the shared pre-call spend journal. Follow-ups have distinct deterministic request keys derived from source, prior answer and resolved context. The entire group still publishes only after every final chunk passes the core validator.

The optional `context_requests` field permits at most six mark/row/fragment lookups in the run's loaded canonical fragments. Results carry source IDs, profile IDs, content keys, box anchors and bounded text excerpts with offsets. Paths, URLs, SQL and arbitrary tools are never executed. Context cannot add canonical evidence IDs or relax lexical/source validation. Duplicate requests, foreign kinds, source mismatch, oversized data, repeated context/coverage and invalid final responses fail explicitly.

Mutable progress stores every successful intermediate answer, its request SHA/content key, call ID, context receipt and step history. A saved answer is never resent after pause/replay. One transport-proven technical retry is shared across a plan's main/context/coverage calls. Proven 429 failures use persisted 20/60/120/300/600-second not-before waits without sleeping in the worker; after five waits another failure ends the unit. Unknown or paid lost responses remain non-retryable.

Quota/auth failures pause both shared job and full run with their typed reason. Explicit `resume` may authorize a retry only when a saved refusal was transport-proven not processed (`definite_refusal` or retry-safe) and the latest journal row is that exact failed call. It cannot authorize an unknown/completed call. Each pause instance has its own command identity. `estimate_resume(*,run_id,user_uid)` returns the shared LEFT estimate including job spend; renewed consent still passes the shared service's route/model/digest checks.

`cancel(session,run_id,user_uid)` uses root's new shared caller-owned cancellation seam. Advancement checks both run state and the durable work cancellation flag before provider execution. Constructor and existing phase API remain compatible; successful phase results remain counts dictionaries.

## Focused evidence

- Stage AI unit suite: **48 passed**. Bounded context+coverage, retained history, no resend, repeated-pass refusal, anchored source lookup, one shared technical retry, durable 429 schedule and typed auth pause are covered alongside core validation.
- Isolated PostgreSQL58050 recorded suite: **5 passed**. It covers ordinary three-call execution, five-call context/coverage execution, exact LEFT consent renewal, actual shared auth refusal/manual resume, caller-owned prepare/cancel rollback, durable work cancellation, zero-text pins, immutable answers/raw retention and replay without provider calls. No live endpoint is used; profile archive data is injected.
- Compile and whitespace checks passed. Full gate/heavy suites remain deferred under the owner's direct instruction.

## Integration and limits

Root consumes this commit after its shared `e045736f` seam. Wire the existing paused estimate endpoint to `estimate_resume` and full-run stop to `cancel` in the same transaction. Root retains ownership of chain steps, deterministic repair, expert cards and transport.

This resolves the first runtime report's D-3 TEXT context/coverage and LEFT-estimate gaps. Real graphical source/crop attachment and graphic-only preflight groups are separate pending bridge integration; unavailable graphics remain explicitly not checked. Bounded text context provides interpretation support, not engineering acceptance or new canonical evidence. All changes are inside the task allowlist after root's provider merge; forbidden hotspots are untouched by this lane.
