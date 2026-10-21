# Task W56A-INT-EVALUATION-BRIDGE-PREP-01 — offline AR v2 evaluation bridge

task_id: W56A-INT-EVALUATION-BRIDGE-PREP-01

## Outcome

The seeded evaluation bridge scores complete AR v2 merge-publication plans
against the pinned manifest, verifies an optional published-group projection,
retains rejected diagnostics, and refuses absent or false bundle provenance.
A focused mutation that removes one seeded issue lowers recall from 21/21 to
20/21 without a provider, database or baseline.

## Depends on

- `W56A-INT-GENERATOR-01` — completed synthetic corpus;
- `W56A-INT-MATCHER-CORE-01` — completed seeded matcher;
- `W56A-INT-MERGE-PUBLICATION-PLAN-PREP-01` — completed grounded plan;
- `W56A-INT-V2-PUBLICATION-PREP-01` — completed unconnected publisher result shape.

## Frozen inputs

- base and development predecessor `9e3ec73e3be2ba3326380ca2c8e77bda6ad1bb7d`;
- W56 plan §A3.6 SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- seeded manifest SHA-256 `95e07c2919d46a600cb9ffead41c883fd38d141699c6857a4700126d6dae6fb7`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis stage registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the exact base has a matcher and publication plan but no evaluation bridge.

### P-01 — additive bridge paths

- captured_at: 2026-10-15
- command: `git ls-tree -r --name-only HEAD tools/evaluation tests/contract/evaluation docs/program/tasks/W56A-INT-EVALUATION-BRIDGE-PREP-01.md docs/program/W56A-INT-EVALUATION-BRIDGE-PREP-01.md`
- captured_output:
  ```text
  tests/contract/evaluation/test_matcher_core.py
  tools/evaluation/__init__.py
  tools/evaluation/matcher.py
  ```
- interpretation: all four paths are additive; existing matcher, plans and records remain owned elsewhere.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tools/evaluation/bridge.py`
- `tests/contract/evaluation/test_bridge.py`
- `docs/program/tasks/W56A-INT-EVALUATION-BRIDGE-PREP-01.md`
- `docs/program/W56A-INT-EVALUATION-BRIDGE-PREP-01.md`

## Forbidden hotspots

Existing matcher, merge plan, publisher, source fixtures and manifests,
recordings, `baseline.json`, `contracts/**`, migrations, runtime executor,
API, root dependencies/locks, composition root, global styles,
`CURRENT_STATE.md`, Git refs and tags.

## Non-goals

No recorded harness, paid/live call, database read or write, quality
threshold, beta verdict, expert decision, or source-byte verification.

## Deliverables

Pure bridge, seeded mutation and provenance tests, this task and result report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/evaluation/test_bridge.py tests/contract/evaluation/test_matcher_core.py` — pass;
- Python compilation, direct task governance, `git diff --check` and exact owned-path proof — pass;
- full `make gate` deferred by R-135.

## Integration contract

Call `score_seeded_plans(manifest, runs)` with exactly one `SeededPlan` per
manifest bundle. The caller supplies the run ID and independently verified
PDF and portal-bundle digests. The bridge compares those digests to the
manifest, projects all plan members' PDF page/quote evidence to matcher
`PredictedGroup`, optionally checks `V2PublicationResult` group identities,
ordinals, canonical IDs and diagnostics against the plan, and returns a
`SeededScore` with `MatchReport` and per-bundle rejected diagnostics. Missing
bundle runs, duplicate run/bundle mapping and digest mismatch fail closed.
The harness must independently verify actual input bytes and construct plans
through the existing grounding and deterministic merge pipeline.

## Failure/idempotency/security cases

No bundle inference from file path or finding UID. No rejected proposal can
become a predicted group. Missing evidence, non-dense/duplicate ordinals,
publication mismatch and incomplete bundle coverage raise `ValueError`.
Repeated pure inputs return the same score. An optional publication result
does not provide quotes on its own; the grounded plan remains required.

## Rollback / feature flag

Revert four additive paths before harness wiring; no data rollback or flag.

## Handoff

- changed files/checks/limits: result report;
- contracts: none;
- next: integrator may wire a recorded evaluation harness in a separately owned task.
