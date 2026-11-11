# Task F8-COUNT-XLSX — counters by the run marker and the Excel column «Источник»

## Outcome
Counters count by the publication marker; the Excel export has a column «Источник» (text, drawing, cross-check); the release note says what changes for runs with «один список».

Owner: the counters lane.

## Depends on
- F8-PUBLISH

Dispatch the lane only when every task above is merged into the base it works from.

## Frozen inputs
- domain contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- API contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- analysis/comparison/event contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- migration head: `0062_hosts_stage_models` at the base; `0063` once the AR v3 removal wave merges (`R-154h`)
- the seals: the first seal of this programme is 1.51.0 / `0064` (`R-154h`: the AR v3 removal wave takes 1.50.0 / `0063` first); the second is 1.52.0 / `0065` (`R-154h`)
- base commit: `47c90e1ec6adf160f788e69279819c0e9c048e8e`
- ADR: `ADR-0029` decision 7; plan section 4 items 6 and 7
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
- `src/auditmanager/dashboard/**`
- `src/auditmanager/exports/xlsx/**`
- `tests/unit/dashboard/**`
- `tests/integration/dashboard/**`
- `tests/unit/exports/**`
- `tests/integration/exports/**`

## Forbidden hotspots
- `contracts/**` and `db/migrations/**`, unless the lane owns them below
- `src/auditmanager/bootstrap/composition.py` and `src/auditmanager/bootstrap/adapters.py`, unless the lane owns them below
- `pyproject.toml`, `uv.lock`, `web/package-lock.json`, `web/src/app/globals.css`
- `VERSION` and `release-notes/**`, unless the lane owns them below
- the historical records `docs/program/tasks/**` (except the new task files of `CRIT-ADR-29`) and `docs/manual-tests/**`
- any path outside `Allowed paths`; a path a lane needs and lacks is named in its report, not taken

## Non-goals
- no change to the import by «ID замечания»

## Deliverables
- `dashboard/audit_state` counts by the marker; for `one_list` runs the meaning of `clean` and `awaiting_decision` changes and the release note says so
- the column «Источник» through the full finding reads, not by the projection alone

## Required tests
- command: .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <the test files named above>
- expected: pass; each check below can fail, and a lane shows the test that proves it can
- a `text_only` run counts as before
- a block finding appears in an Excel row

## Integration contract
Reads the marker and the findings written by `F8-PUBLISH`.

## Failure/idempotency/security cases
- a run without a marker is `text_only`

## Rollback / feature flag
The switch «один список».

## Handoff
- changed files: `git diff --stat <base>..HEAD` and a proof that the forbidden hotspots are untouched
- commands/results: each check with its exact command, the tree SHA and the counts; «not run» with the reason
- known limits: stated, with `path:line` evidence for any departure from the plan
- integration notes: what the integrator must do next
