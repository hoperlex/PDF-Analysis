# Task CMP-STAGE-REVIEW-GRAPHIC-01 — stable graphic verdict evidence and region anchors

## Outcome
GRAPHIC cards bind their evidence digest to stable real engine content/regions and actual source profiles; exact unchanged graphics carry expert verdicts across runs, while changed regions do not. Every region has source-side box anchors.

## Depends on
- CMP-STAGE-REVIEW-01
- CMP-STAGE-GRAPHIC-01

## Frozen inputs
- domain: ADR-0025 A-9/A-10 exact evidence carryover, raw immutable GRAPHIC evidence
- API: 1.13.0; no schema change
- migration head: 0042_comparison_stage_review
- base commit: `76a1db92cb66e3744c2569e06e7fcc1b0404cc79`
- owner/root grant 2026-10-30: exact stage_review paths after graphic SHA; full gates/heavy windows tomorrow

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: old review GRAPHIC source uses run-bound stage receipt content key and empty per-profile boxes.

### P-01 — source projection
- captured_at: 2026-10-30
- command: `rg -n 'graphic_key|box_anchor.*\{\}|content_key.*row' src/auditmanager/comparison/stage_review/service.py`
- captured_output:
  ```text
  94:                                  "content_key": row[f"{side}_key"],
  107:                      "content_key": row["content_key"], "box_anchor": {}}
  112:                "graphic_key": row["content_key"],
  ```
- interpretation: run-local receipt identity cannot prove equal raw graphic evidence across runs; empty boxes cannot locate individual regions.

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
- `docs/program/tasks/CMP-STAGE-REVIEW-GRAPHIC-01.md`
- `docs/program/CMP-STAGE-REVIEW-GRAPHIC-01.md`

## Lane resources
- foundation_instance: `auditmanager-cmp-seal-c4`
- postgres_port: `58040`
- s3_api_port: `62040`
- s3_console_port: `62041`
- postgres_db: `auditmanager_cmp_seal_c4`
- s3_bucket: `auditmanager-cmp-seal-c4`

Same isolated stack sequentially reused after completed graphic smoke by explicit root grant.

## Forbidden hotspots
- graphic provider, shared wiring/public, contracts, migrations, locks/global styles, remote refs

## Non-goals
- no new AI call, UI/schema change, raw engine rewrite or looser acceptance predicate

## Deliverables
- stable GRAPHIC source projection, per-region side anchors, focused exact/changed carryover DB check, report/local commit

## Required tests
- focused review GRAPHIC PostgreSQL test and existing pure review tests; git diff --check
- expected: same engine evidence across two run-local sge IDs yields equal digest and carried lineage; changed raw region yields no accepted carryover

## Integration contract
Existing StageReviewService interface and DTOs remain unchanged; root merges this serial followup after the graphic provider. GRAPHIC evidence uses real engine key + sorted raw region keys + source profiles, not run-local receipt key.

## Failure/idempotency/security cases
- missing/inconsistent proof or invalid source box refuses instead of inventing a region
- unchanged raw evidence can carry a verdict only by the existing exact/unanimous digest predicate
- changed raw evidence may have stale/partial source-location labels but no inherited accepted decision

## Rollback / feature flag
Root controls stages module flag; immutable prior cards/verdicts remain historical. No migration is changed.

## Handoff
- status: completed
- changed files/checks/limits: `docs/program/CMP-STAGE-REVIEW-GRAPHIC-01.md`; three-run GRAPHIC DB test passed, existing 9 unit/export tests passed, whitespace clean; historical card digests remain immutable
- contracts: none
- integration: local commit only, root sole integrator
