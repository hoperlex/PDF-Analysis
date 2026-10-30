# CMP-STAGE-AI-RECOVERY-01 — terminal generation recovery

Task: [`CMP-STAGE-AI-RECOVERY-01`](tasks/CMP-STAGE-AI-RECOVERY-01.md). Owned input `686fea0f`; root's shared generation/LEFT provider consumed at `d8027328`, migration `0043`. Parent explicitly authorized terminal recovery and persisting run/step failure before shared job cancellation.

## Fixed behavior

The root audit at `36b0ae8d` found that repair undo, cancellation or a safely failed AI run could not resume: the shared resume edge accepts a paused job, while those jobs are terminal. `StageAiRuntime.resume` now validates a fresh LEFT estimate on the current source and creates a new shared job generation in the caller's transaction through the public start seam. The internal command key binds prior job, source signature and accepted digest. The run's job pointer changes atomically; root rereads it and rebinds durable work.

Generation is storage identity only. Group IDs, source digests and request fingerprints stay unchanged. Frozen old unit job/source pins, old answers and old spend rows remain intact. New units inherit saved matching responses and exact request pins without resending them. Published answer metadata includes each actual call's original job/model/connection identity, so accepting an older saved response never attributes its provider execution to the new job.

A run-wide request fence checks every generation. Unknown/open calls and completed calls without saved replies block a repeat before a recovery job is allocated and again before execution. Only the exact failed journal row plus saved transport proof of non-processing allows the same request under new consent. Current LEFT counts bind the `/2` metadata prompts/schema bundle; old-version completed progress cannot silently reduce the estimate. New effective graphical sources with no bridge receipt yet still reserve their first potential window.

When no AI work remains, the terminal job can be reused for cached/deterministic continuation without a new provider action or impossible zero-call consent. Cached phase advancement is permitted only when every required immutable answer is already present. This permits retrying expert-card materialization after AI has completed.

Fatal AI failures now persist the full run and active AI step as failed before `jobs.fail` requests work cancellation. A worker observing that cancellation cannot leave the run falsely running. Unit allocation failures also mark the correct phase step.

## Focused verification

- **75 owned unit tests passed**, including pre-unit failure phase persistence; package compile and whitespace checks passed.
- **13 recorded PostgreSQL tests passed**, including six new recovery cases: cancel after a saved reply with no resend; completed AI plus a changed effective source; completed AI plus remaining deterministic work; safely refused failed request; unknown outcome rejection; completed reply-loss rejection. The cases verify frozen generations, original call identity, no additional job on unsafe recovery, retained old journal/answers and terminal run/step failure.
- Assigned PostgreSQL58050 migrated successfully to root's0043. No full gate, whole-suite window, live model or external publication ran.

## Integration and scope

Root consumes this local commit after `0ae3d34b`. Its orchestration rereads `run.comparison_ai_job_id` after resume and cancels/requeues work with the new durable DB/payload job pin; root separately owns the audited work/run lock ordering fix. This lane edits only Stage AI, scoped tests and this task/report. Shared services, migration, contracts, composition/registry, dependency locks, raw deterministic evidence and remote refs are untouched by this lane.

Unknown and lost paid replies remain intentional typed stops; recovery never converts consent into permission to repeat an ambiguous request. Model hints and saved interpretations remain provisional, without expert verdict authority.
