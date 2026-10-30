# Task CMP-C4-INT-FIX-01 — durable AI chunk progress

## Outcome
Stage AI groups keep their source payload immutable while recording durable chunk responses/retries in a separate mutable progress object.

## Depends on
- CMP-SEAL-C4

## Frozen inputs
- API `1.13.0` 227 paths / 253 operations / 613 schemas
- unpublished migration head `0042_comparison_stage_review`
- base commit `6e9cf6d1f024814c28c0e9d046a6f6cabdb113d6`
- runtime evidence: the first recorded shared-call DB replay reached the frozen `stage_ai_unit.payload` guard; source pins must stay frozen

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: `stage_ai_unit.payload` is the frozen source and no progress column exists

## Historical evidence
- correction_mode: addendum
- source_record: `docs/program/CMP-SEAL-C4.md`
- addendum_path: `docs/program/CMP-C4-INT-FIX-01.md`

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `db/migrations/versions/20261030_0042_comparison_stage_review.py`
- `docs/program/tasks/CMP-C4-INT-FIX-01.md`
- `docs/program/CMP-C4-INT-FIX-01.md`

## Forbidden hotspots
- OpenAPI, source payload pins, other migrations, root dependencies, shared runtime and remote refs

## Non-goals
- no relaxation of immutable evidence or full gate

## Deliverables
- additive `progress jsonb` private persistence column and focused migration/runtime evidence

## Required tests
- additive column on disposable 0042 runtime databases and recorded runtime replay
- full gates deferred by owner to tomorrow

## Integration contract
Root owns the serial unpublished migration slot. Source payload remains frozen; stage AI runtime owns progress updates under its work lease. Existing disposable lane databases receive the exact same additive ALTER before further tests. No production database is touched.

## Failure/idempotency/security cases
- retries resume saved responses; progress must retain paid-call history and never mutate source SHA

## Rollback / feature flag
Private additive column; stages module remains the runtime gate. No deployed migration is rewritten.

## Handoff
- changed files: task/report and one private migration column
- checks/results: runtime replay follows in CMP-STAGE-AI-01
- contracts: public API unchanged
- known limits: full acceptance deferred
- integration notes: root dev candidate only
