# CMP-STAGE-AI-GRAPHIC-01 — graphical AI and answer read seam

Task: [`CMP-STAGE-AI-GRAPHIC-01`](tasks/CMP-STAGE-AI-GRAPHIC-01.md). C4 `1.13.0`, base `db576e45`; root remains sole shared-slot owner and integrator.

## Initial read seam milestone

`StageAiRuntime.page(*,run_id,kind,after=None,limit=50)` returns `(tuple[dict],next_id|None)` for kinds `review`, `classify`, `synthesize`. It checks that the run exists, validates a same-run answer-ID cursor, uses ascending immutable answer IDs and bounds the page to100. Every dictionary matches its existing StageAiReview/Classification/Synthesis transport shape. The synthesis title bound is aligned with the sealed260-character transport limit.

Five focused recorded PostgreSQL tests pass, including exact generated-model validation of all three answer types, a terminal keyset page and foreign cursor refusal. No contract, migration, raw evidence or shared service changed. Graphical estimate/crop wiring continues under this same active task; this milestone does not claim its completion.

## Final graphical behavior

The constructor accepts `graphic_source=StageGraphicService(...)`. Root advances the actual graphical bridge before AI step4. Reliable one-to-one nonempty SGE receipts form separate image-only classifier groups; scans create no TEXT reviewer answer or SAME proof. Native left/right boxes, registered source content and real SGE IDs bind every plan. Up to four regions/eight PNGs are attached through the public executor image API. The runtime checks each crop's evidence/region/side/profile/box/digest/size, then persists the exact request SHA and crop receipts before the shared provider caller can run. A regenerated request that differs from its durable pin refuses rather than risking a second paid call.

Canonical sorted regions are partitioned completely, and each executed page is checked against the provider's explicit cursor. There is no silent remainder truncation. START estimates the first bounded window per potential one-to-one link, including image bytes/tokens and D-3 reserves. Before a further page, the unit records its remaining-region cursor and pauses with a consent requirement. The shared LEFT estimate prices the next window; only a higher consent generation unlocks it. `graphic_window_info` exposes the partial-window bounds and durable remaining count; root's consent UI explicitly explains the rolling estimate.

All page responses remain durable. One immutable SGE classification publishes after every page validates. Conflicting page interpretations conservatively aggregate to REVIEW. Synthesis uses that source-bound card and its existing guards, so image-only input cannot assert a text-based high-level proof. Missing crop material is stored as explicit not-checked progress with no AI answer or provider call; the expert-review materializer supplies its conservative raw-evidence fallback.

The runtime also persists a source-consent baseline in the caller's prepare transaction. A repaired effective revision creates a new source pin and pauses before any model request until fresh LEFT consent accepts that source. Group/source keys prevent reuse of earlier answers. Resume estimates and consent renewal use the job's provider mode; execution uses the job's routed adapter. The final read page bound is500, matching the frozen API limit (the earlier milestone's100 bound is superseded).

R3-02 was completed while integrating this source path: model SAME or MOVED touching any raw CHANGED/REMOVED/ADDED fragment becomes UNCERTAIN, with a typed policy reason. Raw rows and source DTOs remain unchanged.

## Final focused verification and handoff

- Owned Stage AI unit suite: **59 passed**. Includes graphical-only eight-plus-two image traversal, fresh-consent pause, complete-group publication/replay, cropped-source tampering, unavailable material, unreliable registration, dropped cursor refusal and all six SAME/MOVED raw-status guard combinations.
- Owned recorded PostgreSQL suite: **7 passed**. The two new scenarios use real C4 engine-result receipts, real StageGraphicService evidence/cursor/crop methods, shared AI job/consent/spend and injected PNG material. Five regions produce requests with8,2,0images; a repaired source requires its own fresh consent before the first call; no TEXT review is created. Existing text/context/auth/cancel/rollback/page tests still pass.
- Package compile and whitespace checks pass. No full gate, whole-suite window, live provider or actual renderer run is claimed by this lane. The provider owner's separate actual-profile/engine/crop smoke is recorded in its own report.
- Root consumes this local commit after its effective-map graphical provider. This lane edits only its task allowlist. No shared contract, migration, registry/composition, dependency lock, raw deterministic evidence or remote ref is authored here. Parent-owned provider merges are excluded from the final path proof.
