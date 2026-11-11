# Task PREC-PASS — the precedents pass: marks, queue, revisions and the per-section switch

## Outcome
The pass computes marks and the queue after the night window, keeps their revisions and lets an administrator switch refusal marks on by section from the replay report (`ADR-0029` decisions 5 and 6).

Owner: the pass lane.

## Depends on
- EMBED-01
- F8-PUBLISH
- CRIT-CORE-01
- CRIT-REPLAY-01

Dispatch the lane only when every task above is merged into the base it works from.

## Frozen inputs
- domain contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- API contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- analysis/comparison/event contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- migration head: `0062_hosts_stage_models` at the base; `0063` once the AR v3 removal wave merges (`R-154h`)
- the seals: the first seal of this programme is 1.51.0 / `0064` (`R-154h`: the AR v3 removal wave takes 1.50.0 / `0063` first); the second is 1.52.0 / `0065` (`R-154h`)
- base commit: `47c90e1ec6adf160f788e69279819c0e9c048e8e`
- ADR: `ADR-0029` decisions 5, 6 and 14
- the pass state lives in «Разбор», not on a rail chip: `RunStageChip` is not extended
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
- `src/auditmanager/api/routers/**`
- `tests/unit/precedents/**`
- `tests/integration/decisions/**`

## Forbidden hotspots
- `contracts/**` and `db/migrations/**`, unless the lane owns them below
- `src/auditmanager/bootstrap/composition.py` and `src/auditmanager/bootstrap/adapters.py`, unless the lane owns them below
- `pyproject.toml`, `uv.lock`, `web/package-lock.json`, `web/src/app/globals.css`
- `VERSION` and `release-notes/**`, unless the lane owns them below
- the historical records `docs/program/tasks/**` (except the new task files of `CRIT-ADR-29`) and `docs/manual-tests/**`
- any path outside `Allowed paths`; a path a lane needs and lacks is named in its report, not taken
- `api/routers/**` only for the implementation of `getRunPrecedents` and `getFindingPrecedents`

## Non-goals
- no UI: `PREC-WEB`
- no change of the core's rules: mapping the deterministic critic of plan v2 (`R-154f`) and the AI critic's records of plan v3 into the inputs «critic in plan» and «reviewed» is this lane's job

## Deliverables
- marks, queue and hints from the core over the memory read through `decision_memory.public`
- the nightly recomputation for fresh runs and revisions
- the per-section switch from the replay report, with the journal row carrying the report's digest

## Required tests
- command: .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <the test files named above>
- expected: pass; each check below can fail, and a lane shows the test that proves it can
- a withdrawn case leaves the marks at read time
- a finding outside the AI critic's window does not enter the queue
- a finding no critic reviewed does not enter the queue, in plan v2 and in plan v3
- a finding reviewed by the plan v2 deterministic critic without a veto can enter the queue
- a switched-off section shows no refusal marks
- the viewer role gets `permission_denied`

## Integration contract
`PREC-WEB` reads the two operations; the pass runs from the maintenance loop, registered by the last part of `CRIT-CAPTURE-01`, which the integrator takes right after this lane. The v2 critic's output comes from the lane `V2-ORIGINAL-REVIEW-01` of the AR v3 removal wave (`R-154f`); until it lands, the pass treats a v2 finding as not reviewed, so v2 gets no «снять».

## Failure/idempotency/security cases
- no vector gives «Недоступно», never a fallback search

## Rollback / feature flag
The switch `section_labels`.

## Handoff
- changed files: `git diff --stat <base>..HEAD` and a proof that the forbidden hotspots are untouched
- commands/results: each check with its exact command, the tree SHA and the counts; «not run» with the reason
- known limits: stated, with `path:line` evidence for any departure from the plan
- integration notes: what the integrator must do next
