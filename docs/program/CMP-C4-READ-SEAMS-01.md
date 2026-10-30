# CMP-C4-READ-SEAMS-01 — connected stage read seams

The assembly response now carries `member_revision_no`, calculated from every add/remove event. In a focused database case, active members ended at event 4 while the real revision was 6 after a removal; the new field returns 6 and is the next edit's `base_member_no`. The new C4 assembly GET uses the existing service and this readback.

The profile-text GET now reads the stored profile archive through `PageProfileReader`, returning original words and PDF-point boxes. Missing archives refuse explicitly, a scan with a real empty archive returns no words, and over-budget pages refuse rather than truncate. This enables per-panel search before a comparison run.

The chain estimate GET also accepts an optional `stage_chain_run_id` for a paused run's remaining-work estimate and passes the authenticated actor to the runtime. Counts remain 227 paths / 253 operations / 613 schemas at 1.13.0; the DTO field and estimate query are additive before dev publication.

Focused assembly/C4 contract checks: **9 passed**; generated client verify **253 operations OK** and web typecheck passed before the query addition. Full acceptance is deferred by the owner. Root's serial runtime wiring follows; the remaining C4 methods stay typed refusals until then.
