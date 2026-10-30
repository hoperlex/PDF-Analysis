# CMP-STAGE-AI-GENERATIONS-SEAL-01

Migration `0043_stage_ai_generations` adds frozen nonnegative `stage_ai_unit.generation` with default0 and includes it in source uniqueness. The old source/group/request identity and immutable job pins remain unchanged. Downgrade refuses any generation above0.

`ComparisonAiJobService.start_in_session` adds `estimate_mode=AiMode.START` and `estimate_job=None`. LEFT is accepted only with queue_items=False, stage_review and a terminal previous job in the same run/project/document. The previous job is re-read. Its spend counts in consent validation. Default START fingerprints stay unchanged.

Focused evidence: isolated PostgreSQL0042→0043, empty-new-generation0043→0042→0043 PASS; compile/whitespace PASS. Recorded terminal-job recovery is owned by CMP-STAGE-AI-RECOVERY-01. No full gate or deployment. Expected-facts inventory now names the one expert action and schema added by the preceding root seal and the new migration head. Shared API remains1.13.0 at228/254/614.

Files: migration0043, shared AI job service, expected facts, task/report; no root dependencies, global styles, historical migration rewrite or remote publication. Root integrates the generation-aware runtime before dev. Rollback: stages flag off; migration downgrade only while generations are all0.
