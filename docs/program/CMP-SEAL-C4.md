# CMP-SEAL-C4 — stage AI, repair, full runs and expert journal

Base: `9fa035029a3422b1c3e63d108fbe8c5fdde5dd8e`. Task: [CMP-SEAL-C4](tasks/CMP-SEAL-C4.md). The owner explicitly deferred full gates and heavy verification to tomorrow on 2026-10-30; this lane performs focused provider checks and has no remote publication authority.

## Frozen surface

API `1.13.0`: **227 paths / 253 operations / 613 schemas**, adding 23 operations to C3. Existing C3 paths and required members remain; the full-run request gains optional AI consent and `with_ai`, the run read gains optional effective revision, kind, AI-job/batch and pause/failure fields. Every new operation is authenticated, every write is keyed/expert-only, and new typed adapters refuse under `comparison_modules` when stages are off and `comparison_stage_c4` while its runtime lane is unwired.

| Lane | Operations |
| --- | --- |
| Assembly reload | `getStageAssembly` |
| Chain/queue | `estimateStageChainRun`, `resumeStageChainRun`, `startStageChainBatch`, `getStageChainBatch`, `pauseStageChainBatch`, `resumeStageChainBatch`, `cancelStageChainBatch` |
| AI | `listStageAiReviews`, `listStageClassifications`, `getStageSynthesis` |
| Graphics | `listStageGraphicEvidence` |
| Repair | `listStageLinkRepairs`, `undoStageLinkRepair` |
| Expert review | `listStageChangeCards`, `getStageChangeCard`, `applyStageCardVerdicts`, `listStageCardVerdicts` |
| Journal | `getStageChangeJournal`, `streamStageChangeJournalXlsx`, `streamStageChangeJournalPdf`, `streamStageChangeJournalHtml` |
| Profile viewer | `getStageProfileText` |

The closed system vocabulary is `unknown`, `architecture`, `structural`, `electrical`, `heating_ventilation`, `water_sewage`, `fire_protection`, `low_current`, `technology`, `site`, `other`. Categories are the original 18-key classifier set. Reviewer status is SAME/MOVED/CHANGED/REMOVED/ADDED/UNCERTAIN; persisted whole-group decisions may contain up to 800 rows, while the runtime validator retains the 40 preliminary-item limit per model chunk and accepts only complete groups. A card retains its raw atomic evidence IDs; AI output cannot edit raw differences.

## Migration/provider seam

`0042_comparison_stage_review` adds twelve project-reachable tables:

- `stage_ai_unit`: run/job, kind review/classify/synthesize, group/source digest, state, payload, failure and timestamps. The answer tables `stage_ai_review`, `stage_ai_classification`, `stage_ai_synthesis` bind unit/run, content key, group/source digest, their JSON result and model identity; answers are immutable.
- `stage_graphic_evidence`: run/link item, left/right profile, optional engine result, not_checked/unreliable/reliable, reason, regions and content key. A reliable result requires one-to-one link cardinality and both profiles/result; other cases expose why graphics were not checked.
- `stage_link_repair`: source run, before/after map revisions, proof and full before/after JSON snapshots; one repair per source run. `stage_link_repair_event` is append-only applied/undone/superseded history with actor, command, resulting revision and optional recomputation run. Its current state is a read model over events.
- `stage_change_card`: run/classification, content/evidence digests, class/category/title/system, atomic IDs and before/after text. `stage_card_evidence` keeps typed raw foreign keys, side/profile/box/absence proof. `stage_card_verdict` is append-only, keyed per card, revision-checked, requires a reason for rejection and binds the current evidence digest. SERVICE_STRUCTURE has no verdict.
- `stage_chain_batch` and `stage_chain_batch_item`: project/actor/key, ordered pair/revision selections and consent, states and nullable child run references.

The run adds `kind` (deterministic/full), immutable `with_ai` and optional batch pin, mutable nullable `comparison_ai_job_id`, same-pair `effective_link_revision_id`, `pause_reason`, and a 0-or-1 `repair_cycle_count`. Original revision/input pins remain immutable. C3 text hints gain `source_side` default left; their scope trigger now supports right-to-left recommendations without changing existing left-to-right rows.

Shared AI gains method `stage_review`, routed work kind `comparison_stage_review`, run FK/scope validation and one live job per run. `AiScope.stage_link_revision_id` binds a preflight estimate to immutable source; a future allocated run ID is excluded from that estimate document. Persisted jobs require `stage_chain_run_id`. `start_in_session(..., queue_items=False)` and `resume_in_session(..., queue_items=False)` allow the chain's run/job/consent/work to commit in one caller transaction. `ComparisonWorkRepository.enqueue(comparison_ai_job_id=...)` pins the DB link and payload identity together and checks project/module; old unlinked payload behavior remains compatible. `complete_if_drained(excluding_work_id=...)` may exclude only this job's current running item after the caller's lease fence.

New opaque identity prefixes: `saunit`, `sarev`, `sacls`, `sasyn`, `sge`, `crp`, `crpe`, `ccd`, `sce`, `cdv`, `scb`, `scbi`. Recovery/grant/purge inventories include all twelve tables; batch/unit nonterminal states block erase. The three new actor FKs are registered for account deletion. No direct new Blob reference is introduced: graphic rows refer to existing engine results. Journal exports are synchronous deterministic reads; no generic XLSX writer or export resource was added, as ADR-0025 §22/R3-34 requires.

## Focused evidence

- API/shared estimate and C3/C4 role/module guards: **57 passed**; opaque identifier catalogue: **32 passed**.
- Separate C4 foundation: `0041 → 0042`, empty downgrade to `0041` and re-upgrade passed. A transaction inserts into all twelve new tables using real C3 pair/map/raw evidence, exercises scope and verdict triggers, and rolls back: **PASS**.
- Generated client verification passes at 253 operations. Web typecheck passed; the C2 consent-start compatibility check passed **24 tests**.
- No full gate, build, whole-suite measurement, live model call, push, merge, tag or deployment occurred. Surface/table literal census tests outside the focused provider set remain tomorrow's integration work under the owner override.

## Integration instruction

Preserve the contract content commit named by `web/FRONTEND_LOCK.json`, merge this provider before C4 runtime, and serialize adapter/composition/public wiring. Runtime owns all C4 algorithms and must replace typed stubs explicitly. The run lane must use the effective revision after repair and publish under its comparison-work lease. The review lane owns its XLSX writer inside `comparison/stage_review`; raw evidence and original expert verdict history remain immutable. Root is the sole integrator and `origin/dev` writer; this seal grants no `origin/main` authority.
