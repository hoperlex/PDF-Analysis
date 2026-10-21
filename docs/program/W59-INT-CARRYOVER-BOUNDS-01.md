# W59-INT-CARRYOVER-BOUNDS-01 — bounded carryover batch addendum

Base: published dev64 `a09721a5895a0aff93d08f203fe1bedbbffffb8a`.

The unserved pure carryover planner now refuses more than 200 matches or
selected offer digests. The same 200-findings-per-Run limit already applies to
the upstream W59 finding matcher. Batch limits run before per-item match
validation, digest construction, selection hashing or current-offer rebuild.
Exactly 200 distinct current matches and selections remain deterministic;
the offer format and digest for valid inputs did not change.

## Changed files

- `src/auditmanager/comparison/decision_carryover.py` — 200-item caps for
  offered matches and selected digests;
- `tests/integration/comparison/test_decision_carryover.py` — over-limit
  refusals and exact-limit full batch regression;
- `docs/program/tasks/W59-INT-CARRYOVER-BOUNDS-01.md` — freeze and ownership;
- this addendum.

## Checks

- Before the source change, the new over-limit test failed: a 201-item match
  list produced `match_invalid` instead of the required `matches_too_large`.
  The exact-200 test passed unchanged.
- Focused carryover and finding matcher suite after the fix: **32 passed**.
- The full offline comparison suite passed: **103 passed**. Direct task
  governance and ALR-05 architecture checks passed: **18 passed** (pytest
  emitted five stale `/tmp` cleanup warnings unrelated to these tests).
- Python compilation, frozen SHA readback and `git diff --check` passed.
  Exact-path clean-tree handoff is recorded separately in local evidence.
- No Docker, DB/S3, network, provider or full beta gate under R-135.

## Contracts and limitations

No API contract, migration, error catalogue, stage registry, persisted decision,
route or feature flag changed. The source of matches and expert roles remains
caller supplied; the future comparison owner must read authoritative current
state and append only in an idempotent transaction. A 200-item cap limits work
in this pure function but does not establish live source custody or a served
comparison workflow.

## Integration instruction

Cherry-pick this four-path source commit after dev64. It is disjoint from the
current W56a/W56b/W58 source lanes. Preserve the unserved status. The rollback
is a source revert before runtime activation; no data rollback is needed.

Forbidden hotspots including `contracts/**`, `db/migrations/**`, other W59
modules, served API/UI, root locks, composition root, global styles,
`CURRENT_STATE.md`, refs and tags were not edited.
