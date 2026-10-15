# Task W56A-INT-MERGE-PUBLICATION-PLAN-PREP-01 — validate AR v2 merge for later publication

task_id: W56A-INT-MERGE-PUBLICATION-PLAN-PREP-01

## Outcome

A pure, typed AR v2 plan accepts only a total, disjoint, rule-consistent merge
partition of fully grounded proposals. It retains canonical and member data,
source proposal ordinals and rejected diagnostics for the later database
publisher. Focused tests refuse missing/duplicate members, wrong canonical
members and rejected-source leakage; v1 publication is untouched.

## Depends on

- `W56A-INT-MERGE-INPUT-PREP-01` — completed pure dense merge input;
- `W56A-INT-RESPONSE-PIPELINE-PREP-01` — completed typed v2 response finish.

## Frozen inputs

- base commit and `origin/dev`: `eca8597b4b59a06371cfaf709df7bee8509a604f`;
- W56 plan §A3.3 and `CURRENT_STATE.md` at the base;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: merge preparation exists, but no typed publication plan exists on the exact base.

### P-01 — base and absent planner

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/findings/merge_publication_plan.py tests/integration/findings/test_merge_publication_plan.py docs/program/tasks/W56A-INT-MERGE-PUBLICATION-PLAN-PREP-01.md docs/program/W56A-INT-MERGE-PUBLICATION-PLAN-PREP-01.md`
- captured_output:
  ```text
  eca8597b4b59a06371cfaf709df7bee8509a604f
  eca8597b4b59a06371cfaf709df7bee8509a604f
  ```
- interpretation: the four task-owned paths are additive; no existing publication path needs mutation.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/findings/merge_publication_plan.py`
- `tests/integration/findings/test_merge_publication_plan.py`
- `docs/program/tasks/W56A-INT-MERGE-PUBLICATION-PLAN-PREP-01.md`
- `docs/program/W56A-INT-MERGE-PUBLICATION-PLAN-PREP-01.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, existing merge and publication
modules, runtime executor, public API, root dependencies/locks, composition
root, global styles, `CURRENT_STATE.md`, Git refs, tags, `origin/dev` and
`origin/main`.

## Non-goals

No database write, finding identity allocation, provider call, active AR v2
stage, expert verdict, v1 behavior change, complete gate or beta acceptance.

## Deliverables

Pure typed plan, meaningful focused tests, task file and result report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/findings/test_merge_publication_plan.py tests/integration/findings/test_v2_merge_core.py tests/integration/analysis/test_ar_v2_merge_input.py` — pass;
- Python compilation, direct task governance, whitespace and exact owned-path proof — pass;
- complete `make gate` deferred under `R-135`.

## Integration contract

Call `plan_v2_merge_publication(grounding, merge)` after `prepare_merge`.
`MergePublicationPlan.groups` contains one `PlannedFinding` per distinct
finding. Each group carries all accepted members and its canonical member;
each member carries dense merge and original proposal ordinals, proposal
fields, proposed severity and complete PDF evidence. `rejected`,
`malformed_count` and `salvaged` preserve diagnostics. The later publisher
must allocate one finding UID per group, insert all members against it, and
set the canonical observation ID in the same savepoint. It must publish no
finding from `rejected`.

## Failure/idempotency/security cases

Wrong input type, source map, artifact role/version, missing/duplicate or
out-of-range group member, wrong canonical, mixed category and forged grouping
fail closed. Repeated valid input produces the same plan without I/O. No
model output becomes an expert decision.

## Rollback / feature flag

Revert these four additive paths before runtime wiring; no data rollback or
feature flag.

## Handoff

- changed files/checks/limits: result report;
- contracts: none;
- next: integrator can connect the plan only in a separately granted AR v2
  transaction/publication task.
