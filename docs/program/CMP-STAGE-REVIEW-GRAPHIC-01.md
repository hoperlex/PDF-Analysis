# CMP-STAGE-REVIEW-GRAPHIC-01 — stable graphic verdict source

Completed 2026-10-30 as the root-authorized serial followup after GRAPHIC provider `76a1db92`. No public API, schema, migration, root wiring or graphic provider change.

`StageReviewService` now reads the referenced engine row's immutable content key, verifies each region's registration source/result/key/reliability, and binds GRAPHIC evidence to that engine key, sorted region keys and actual source profiles. A run-local sge ID/content key remains the card's atomic reference and idempotency identity; it no longer masquerades as stable raw graphic content in the verdict digest.

Every region contributes left/right source parts with exact `x0/top/x1/bottom` anchors, document/page/side context and content-bound region keys. Invalid or inconsistent proof and nonfinite/empty native boxes refuse materialization. Unchecked/unreliable graphics remain status records. No raw engine row, existing card or expert act is rewritten.

Focused evidence:

- Three-run actual-0042 DB test **passed in 2.35 s**: accepted GRAPHIC card, second run with another sge receipt over identical engine evidence gets equal digest and a new carried verdict with original lineage, third run with changed raw region gets a different digest/stale label and no accepted verdict. All source-side box anchors are populated.
- Existing pure review/export suite **9 passed**.
- `git diff --check` clean.

The test uses real engine-result FK rows and the GRAPHIC projection; the underlying real PDF engine/profile/crop path was separately proven by `CMP-STAGE-GRAPHIC-01`. Previously materialized cards retain their historical digests; this task does not reinterpret their accepted evidence. Full gate/build/browser/live-model/deployment/remote-ref actions remain deferred/unperformed.

Authored files: `comparison/stage_review/service.py`, `tests/integration/comparison/stage_review/test_graphic_carryover.py`, this report and its task. Root can merge this local followup after `76a1db92`; StageReviewService method signatures and frozen transport DTOs are unchanged. Forbidden hotspots are untouched.
