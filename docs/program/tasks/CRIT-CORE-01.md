# Task CRIT-CORE-01 — the precedents core: votes, independence, marks, veto, stop-words, hints and the budget

## Outcome
A pure module in the new context `precedents` implements `ADR-0029` decisions 4 and 5: who votes, independence, similarity classes, the marks, `cancel_suggested` with the critic condition, the veto, stop-words by stems, the hints P1, P4 and P5, and the selection under a character budget. It calls no model and no database.

Owner: the core lane.

## Depends on
- CRIT-ADR-29

Dispatch the lane only when every task above is merged into the base it works from.

## Frozen inputs
- domain contract: 1.49.0, unchanged until the seal
- API contract: 1.49.0, unchanged until the seal
- analysis/comparison/event contract: 1.49.0, unchanged until the seal
- migration head: `0062_hosts_stage_models`, unchanged until the seal
- the seal: 1.50.0 / `0063`, or the next free numbers if the AR v3 removal wave merges first
- base commit: `47c90e1ec6adf160f788e69279819c0e9c048e8e`
- ADR: `ADR-0029` decisions 1, 4, 5 and 14; plan section 2 (the rules); the hints P2 and P3 are not built (`R-154a`)
- the context imports only the `public` module of any other context (`AGENTS.md` section 4)
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
- no persistence, no operation, no wiring: the consumer lands in `PREC-PASS`
- no model call
- no hint P2 or P3

## Deliverables
- functions that take votes, comments and critic records as data and return marks, queue membership, hints and a budgeted selection
- the label table: `often_rejected`, `cancel_suggested` (a part of it), `likely_accepted`, `mixed`, `few`/`none`; unanimous refusals never give `mixed`
- a finding the critic did not review gets only the neutral line «Прецедентов: N (критик не разбирал)» and never `cancel_suggested`
- `src/auditmanager/precedents/` and `tests/unit/precedents/` are new directories

## Required tests
- command: .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <the test files named above>
- expected: pass; each check below can fail, and a lane shows the test that proves it can
- unanimous refusals do not give `mixed`
- fewer than 5 independent votes give no `cancel_suggested`
- a vote cast under a shown refusal mark is not independent
- `carried` does not vote and an imported decision does
- a finding the critic did not review gets no `cancel_suggested`
- a veto from any linked candidate hides `cancel_suggested`
- a stop-word in another grammatical case still matches
- the selection under 12 000 characters returns the line «не уместилось: N»

## Integration contract
`PREC-PASS` and `CTX-STAND` call the module; its input and output shapes are the contract between the lanes and change only with this task's owner.

## Failure/idempotency/security cases
- a case without a section never votes
- at most two votes from one version of a document
- no vector means no vote, never a fallback

## Rollback / feature flag
No consumer exists until wave 4; remove the directory.

## Handoff
- changed files: `git diff --stat <base>..HEAD` and a proof that the forbidden hotspots are untouched
- commands/results: each check with its exact command, the tree SHA and the counts; «not run» with the reason
- known limits: stated, with `path:line` evidence for any departure from the plan
- integration notes: what the integrator must do next
