# Task CRIT-CAPTURE-01 — changes in the composition root: capture, the precedents pass and the vector import

## Outcome
Capture writes the mark in force and its revision with each decision, the comments and, with `F8-PUBLISH`, `dm-capture/2` with block evidence; the pass «Прецеденты» and the vector import are registered in the maintenance loop (`ADR-0029` decisions 4, 7, 8, 10).

Owner: the integrator (the composition root has one owner per wave).

## Depends on
- CRIT-SEAL-50

Dispatch the lane only when every task above is merged into the base it works from.

## Frozen inputs
- domain contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- API contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- analysis/comparison/event contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- migration head: `0062_hosts_stage_models` at the base; `0063` once the AR v3 removal wave merges (`R-154h`)
- the seals: the first seal of this programme is 1.51.0 / `0064` (`R-154h`: the AR v3 removal wave takes 1.50.0 / `0063` first); the second is 1.52.0 / `0065` (`R-154h`)
- base commit: `47c90e1ec6adf160f788e69279819c0e9c048e8e`
- ADR: `ADR-0029` decisions 4, 7, 8, 10; `ADR-0027` decision 4 (capture in the decision's transaction, loud)
- plan: the «Прецеденты» plan (version 5, with the R-154 correction) is the integrator's working copy `.local/evidence/lane-common-prec/plan-v5.md` and is not in git; the decisions it carries are in `ADR-0029`
- rules: the common rules of the programme (`.local/evidence/lane-common-prec-2026-11-10.md`, git-ignored): minimal checks only, tests under the host lock, no push, merge or tag
- the plan read the code at `5342b7178`, which has the same code as the base; every `path:line` the lane relies on is checked in its own worktree before use

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `tests/unit/bootstrap/**`
- `tests/integration/decisions/**`

## Forbidden hotspots
- `contracts/**` and `db/migrations/**`, unless the lane owns them below
- `src/auditmanager/bootstrap/composition.py` and `src/auditmanager/bootstrap/adapters.py`, unless the lane owns them below
- `pyproject.toml`, `uv.lock`, `web/package-lock.json`, `web/src/app/globals.css`
- `VERSION` and `release-notes/**`, unless the lane owns them below
- the historical records `docs/program/tasks/**` (except the new task files of `CRIT-ADR-29`) and `docs/manual-tests/**`
- any path outside `Allowed paths`; a path a lane needs and lacks is named in its report, not taken

## Non-goals
- no logic of its own: the assemblers call the contexts' public modules

## Deliverables
- capture writes `precedent_label_at_decision` and `precedent_revision`
- capture of comments, and of block evidence with the crop taken by block (together with `F8-PUBLISH`)
- registration of the pass «Прецеденты» and the vector import in the maintenance loop
- delivered in parts, each right after its lane: comments after `MEM-COMMENTS-01`, block evidence with `F8-PUBLISH` (the same release), the pass and the vector import after `PREC-PASS`

## Required tests
- command: .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <the test files named above>
- expected: pass; each check below can fail, and a lane shows the test that proves it can
- ✓ on a block finding writes a case with the block evidence and its crop
- the mark in force is recorded
- capture is not silent: an error cancels the decision

## Integration contract
One owner of the composition root per wave: the integrator takes the parts in the order of the lanes above.

## Failure/idempotency/security cases
- a capture error propagates and the decision fails

## Rollback / feature flag
Not applicable: this is the capture.

## Handoff
- changed files: `git diff --stat <base>..HEAD` and a proof that the forbidden hotspots are untouched
- commands/results: each check with its exact command, the tree SHA and the counts; «not run» with the reason
- known limits: stated, with `path:line` evidence for any departure from the plan
- integration notes: what the integrator must do next
