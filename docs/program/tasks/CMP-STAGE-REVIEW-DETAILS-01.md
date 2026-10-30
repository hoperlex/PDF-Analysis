# Task CMP-STAGE-REVIEW-DETAILS-01 — actual classification detail labels and exact counts

## Outcome
Stage card/detail/journal projections expose immutable classifier materiality, importance and detail-increased fields; summary counts actual high labels and unknown labels rather than inventing importance.

## Depends on
- CMP-STAGE-ESCALATE-SEAL-01
- CMP-STAGE-REVIEW-01
- CMP-STAGE-ESCALATE-01

## Frozen inputs
- domain: roadmap §1.2 card sections, root metadata policy 2026-10-30
- API: optional materiality material/non_material/unknown, importance high/normal/unknown, detail_increased bool on StageClassificationCard/StageChangeCard (root seal 80b6b9e3)
- migration: 0042; existing immutable classification JSON, no new column
- base commit: `5dcb036201f672e3f93cb630a71cf64156cba8c9`
- AI lane owns genuine metadata prompt/policy, UI lane owns section grouping, root owns API/wiring and dev publication; heavy gates tomorrow

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: review currently projects no detail labels and reports high_importance=0 without an assessment source.

### P-01 — base
- captured_at: 2026-10-30
- command: `git rev-parse HEAD`
- captured_output:
  ```text
  5dcb036201f672e3f93cb630a71cf64156cba8c9
  ```
- interpretation: source JSON is already immutable and API metadata fields are sealed, so only review read projections need code.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/stage_review/**`
- `tests/unit/comparison/stage_review/**`
- `tests/integration/comparison/stage_review/**`
- `docs/program/tasks/CMP-STAGE-REVIEW-DETAILS-01.md`
- `docs/program/CMP-STAGE-REVIEW-DETAILS-01.md`

## Lane resources
- foundation_instance: `auditmanager-cmp-seal-c4`
- postgres_port: `58040`
- s3_api_port: `62040`
- s3_console_port: `62041`
- postgres_db: `auditmanager_cmp_seal_c4`
- s3_bucket: `auditmanager-cmp-seal-c4`

Sequential DB-only root-assigned stack.

## Forbidden hotspots
- API/contracts/generated, migrations, AI/graphic/UI source, root wiring/public/locks, remote refs

## Non-goals
- no category-based importance heuristic, no raw evidence/card rewrite, no model call or new metadata authority

## Deliverables
- source-keyed classification metadata projection with unknown/unknown/false defaults and exact high/unknown counts
- focused actual-source-versus-raw tests and local commit/report

## Required tests
- focused review PostgreSQL and pure review checks, whitespace clean
- expected: labels come only from matched source card JSON; raw/manual/old/malformed absent labels remain unknown, high count matches real immutable high labels

## Integration contract
StageReviewService method signatures remain unchanged. Internal classification ID is never exposed in StageChangeCard. Match original immutable classification card by card_key or exact atomic ID set/class for historical JSON without a key. counts adds importance_unknown and computes high_importance from genuine labels. Raw/manual defaults unknown/unknown/false.

## Failure/idempotency/security cases
- a foreign/other card in the same JSON answer cannot lend importance to this card
- invalid/missing metadata cannot become a synthetic high/material label
- source rows remain immutable; no new evidence digest or expert verdict semantics

## Rollback / feature flag
Optional API metadata is additive; root stages gate remains; no DDL/rewrite.

## Handoff
- status: completed
- changed files/checks/limits: `docs/program/CMP-STAGE-REVIEW-DETAILS-01.md`; 15 connected DB tests and 9 pure review/export tests passed; unassessed/invalid labels stay unknown
- contracts: none
- integration: local commit only
