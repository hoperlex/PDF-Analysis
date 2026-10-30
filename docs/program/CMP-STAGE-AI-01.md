# CMP-STAGE-AI-01 — durable Stage AI runtime

Task: [`CMP-STAGE-AI-01`](tasks/CMP-STAGE-AI-01.md). C4 API `1.13.0`, migration `0042`, root-owned progress fix consumed at base `682d38b6`. This lane changes no shared contract, migration, registry or remote ref.

## Implemented

`StageAiRuntime` has a lazy constructor accepting sessions, optional blob store, shared routes and provider mode. `estimate(revision_id,user_uid)` reads current profile archives without model execution. `prepare(session,run_id,user_uid,consent)` and `resume(session,...)` use shared job commands in the caller transaction, with no separate connection reading an uncommitted run and no independent AI work items. A zero-text source retains profile/model/content pins and produces explicit not-checked counts without an AI verdict or job.

`advance(item,run_id,phase)` returns counts, `Yielded` or `Failed` for review/classify/synthesize. It checks lease, project, current effective revision, exact version pins and the durable work/job link. Connected sheet-link groups feed existing raw difference IDs into review; accepted interpretation overlays feed classifier and synthesis without changing raw rows. Every response uses shared routing, `ComparisonModelCaller`, consent and spend reservation/journal. One proven-safe technical retry is allowed; unknown or already-paid missing responses are never silently resent.

Immutable unit `payload` stores source request documents. Mutable `progress` saves per-plan responses, call IDs, technical retries and generation history. Whole-group review publishes only after all bounded chunks validate. Immutable answers are keyed by source/model/prompt content; saved answers replay without calls. A pause after a completed call keeps its response for resume. The shared job completes after synthesis while excluding the caller's current running full-chain work item. Invalid prerequisites fail the shared job even before a unit is allocated.

## Public integration

Import `StageAiRuntime` from `auditmanager.comparison.stage_ai`. Construct `StageAiRuntime(session_factory, blob_store=store, routes=dependencies.routes, provider_mode=mode)`. Root inserts the run, calls `prepare` in that session, links the returned optional job ID to run and full-chain work using shared `enqueue(comparison_ai_job_id=...)`, then orchestrates phases at steps4/5/6. Step5 deterministic repair and step7 expert cards remain root/review responsibilities. Full work with no job omits its job payload key. Successful phase results are dictionaries, never `Completed`.

Classification card `evidence_ids` are original `stage_text_difference_id` values. `stage_ai_unit.payload.sources[].atomic_evidence` retains their accepted interpretation, original fragment references and source keys; review payloads retain source fragments/items. Expert card carry-over must use its canonical raw-evidence digest rather than classifier grouping or class.

## Focused verification

- `.venv/bin/pytest -q --tb=short tests/unit/comparison/stage_ai`: **36 passed**. Includes core validation, replay, two-chunk atomicity, paid-response loss, pause retention, missing-prerequisite failure and lazy construction.
- Assigned PostgreSQL58050, `tests/integration/comparison/stage_ai/test_runtime.py`: **2 passed**. Actual C4 tables/shared job/spend/queue exercise caller-owned prepare rollback, three phases/three recorded calls, immutable answers, raw retention, completed shared job, replay without calls, zero-text source pins and explicit graphical not-checked status. Profile archive data is injected; no live provider or S3 crop claim is made.
- Package compile and whitespace checks passed. Full gate/heavy windows remain deferred under the owner's direct 2026-10-30 instruction.

## Remaining functional work

This first runnable candidate does not yet implement D-3 model context requests or the unparsed-record follow-up pass; parent assigned these as the immediate next owned follow-up. It explicitly records unavailable graphical bridge/crops as not checked; root owns the real bridge and its forthcoming seam. Resume after a consent pause needs a LEFT estimate bound to the run; the follow-up will expose that estimate. These limitations are functional gaps, not acceptance claims.

Root remains sole integrator and publisher to dev. The changed-path proof compares this lane with `682d38b6`, after parent-owned provider merges. No forbidden hotspot was authored by this lane, and no main publication or full validation is asserted.
