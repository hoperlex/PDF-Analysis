# CMP-STAGE-AI-GRAPHIC-01 — graphical AI and answer read seam

Task: [`CMP-STAGE-AI-GRAPHIC-01`](tasks/CMP-STAGE-AI-GRAPHIC-01.md). C4 `1.13.0`, base `db576e45`; root remains sole shared-slot owner and integrator.

## Initial read seam milestone

`StageAiRuntime.page(*,run_id,kind,after=None,limit=50)` returns `(tuple[dict],next_id|None)` for kinds `review`, `classify`, `synthesize`. It checks that the run exists, validates a same-run answer-ID cursor, uses ascending immutable answer IDs and bounds the page to100. Every dictionary matches its existing StageAiReview/Classification/Synthesis transport shape. The synthesis title bound is aligned with the sealed260-character transport limit.

Five focused recorded PostgreSQL tests pass, including exact generated-model validation of all three answer types, a terminal keyset page and foreign cursor refusal. No contract, migration, raw evidence or shared service changed. Graphical estimate/crop wiring continues under this same active task; this milestone does not claim its completion.
