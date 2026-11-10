# Task CRIT-REPLAY-01 — the history replay tool and the per-section threshold report

## Outcome
A product tool replays the stored decisions over time and reports, per section, whether refusal marks may be switched on: base refusal rate, gain, precision of «снять» and harm (`ADR-0029` decision 6).

Owner: the replay lane.

## Depends on
- CRIT-CORE-01

Dispatch the lane only when every task above is merged into the base it works from.

## Frozen inputs
- domain contract: 1.49.0, unchanged until the seal
- API contract: 1.49.0, unchanged until the seal
- analysis/comparison/event contract: 1.49.0, unchanged until the seal
- migration head: `0062_hosts_stage_models`, unchanged until the seal
- the seal: 1.50.0 / `0063`, or the next free numbers if the AR v3 removal wave merges first
- base commit: `47c90e1ec6adf160f788e69279819c0e9c048e8e`
- ADR: `ADR-0029` decision 6; plan section 2.6
- the tool is a product tool, not a measurement; synthetic data proves only that it works
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
- `src/auditmanager/precedents/**`
- `tests/unit/precedents/**`

## Forbidden hotspots
- `contracts/**` and `db/migrations/**`, unless the lane owns them below
- `src/auditmanager/bootstrap/composition.py` and `src/auditmanager/bootstrap/adapters.py`, unless the lane owns them below
- `pyproject.toml`, `uv.lock`, `web/package-lock.json`, `web/src/app/globals.css`
- `VERSION` and `release-notes/**`, unless the lane owns them below
- the historical records `docs/program/tasks/**` (except the new task files of `CRIT-ADR-29`) and `docs/manual-tests/**`
- any path outside `Allowed paths`; a path a lane needs and lacks is named in its report, not taken

## Non-goals
- no switch is turned on by this lane
- no measurement of real data

## Deliverables
- the cut: for each case the end time of its run, or the earliest decision on it if the run was erased; votes from the same run are left out
- tuning on the early 70 % of decisions and a check on the late 30 %
- decisions under a shown refusal mark are left out of the «снять» check and reported apart
- the report: base refusal rate, gain, precision, harm; the section passes at precision at least 0,90 on at least 30 cases, gain at least 0,15, harm at most 2 % and zero on protected findings

## Required tests
- command: .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <the test files named above>
- expected: pass; each check below can fail, and a lane shows the test that proves it can
- a replay slice contains no decision from the future
- decisions under a mark are excluded from precision
- the split is by time, 70/30

## Integration contract
`PREC-PASS` reads the report to let an administrator switch a section on; the journal row carries the report's digest.

## Failure/idempotency/security cases
- an empty or tiny history yields «not enough cases», never a pass

## Rollback / feature flag
A tool: remove it.

## Handoff
- changed files: `git diff --stat <base>..HEAD` and a proof that the forbidden hotspots are untouched
- commands/results: each check with its exact command, the tree SHA and the counts; «not run» with the reason
- known limits: stated, with `path:line` evidence for any departure from the plan
- integration notes: what the integrator must do next
