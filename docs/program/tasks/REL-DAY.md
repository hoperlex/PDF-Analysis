# Task REL-DAY — the release day: VERSION and the release note

## Outcome
On the day of the deployment, `VERSION` and a release note say that the number of findings will grow, that for runs with «один список» «проверено» and «ждут решения» count differently, and that the v3 queue is re-consented.

Owner: the release integrator.

## Depends on
- F8-COUNT-XLSX
- F8-WEB
- CTX-CRITIC

Dispatch the lane only when every task above is merged into the base it works from.

## Frozen inputs
- domain contract: 1.49.0, unchanged until the seal
- API contract: 1.49.0, unchanged until the seal
- analysis/comparison/event contract: 1.49.0, unchanged until the seal
- migration head: `0062_hosts_stage_models`, unchanged until the seal
- the seal: 1.50.0 / `0063`, or the next free numbers if the AR v3 removal wave merges first
- base commit: `47c90e1ec6adf160f788e69279819c0e9c048e8e`
- ADR: `ADR-0029` consequences; `AGENTS.md` section 6.1 (a user-visible change carries its version note)
- plan: the «Прецеденты» plan (version 5, with the R-154 correction) is the integrator's working copy `.local/evidence/lane-common-prec/plan-v5.md` and is not in git; the decisions it carries are in `ADR-0029`
- rules: the common rules of the programme (`.local/evidence/lane-common-prec-2026-11-10.md`, git-ignored): minimal checks only, tests under the host lock, no push, merge or tag
- the plan read the code at `5342b7178`, which has the same code as the base; every `path:line` the lane relies on is checked in its own worktree before use

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the files that pin the product version

### P-01 — the files that pin the product version
- captured_at: 2026-11-10
- command: `git grep -l "0\.23\.1" -- . ':!docs/program/tasks' ':!docs/manual-tests' ':!release-notes'`
- captured_output:
  ```text
  VERSION
  docs/program/CURRENT_STATE.md
  tests/contract/release_notes/test_release_notes_form.py
  tests/integration/releases/test_release_loader.py
  ```
- interpretation: at the base the version literal is pinned in these four files; moving `VERSION` moves the other three in the same commit (`AGENTS.md` section 6.1), so they are allowed paths of this lane. The plan's own allowed list named only `VERSION` and `release-notes/**`.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `VERSION`
- `release-notes/**`
- `tests/contract/release_notes/test_release_notes_form.py`
- `tests/integration/releases/test_release_loader.py`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots
- `contracts/**` and `db/migrations/**`, unless the lane owns them below
- `src/auditmanager/bootstrap/composition.py` and `src/auditmanager/bootstrap/adapters.py`, unless the lane owns them below
- `pyproject.toml`, `uv.lock`, `web/package-lock.json`, `web/src/app/globals.css`
- `VERSION` and `release-notes/**`, unless the lane owns them below
- the historical records `docs/program/tasks/**` (except the new task files of `CRIT-ADR-29`) and `docs/manual-tests/**`
- any path outside `Allowed paths`; a path a lane needs and lacks is named in its report, not taken
- moving `VERSION` moves its pins in the same commit (the release-note form test, the release loader test, the «Product `VERSION` is» line); those paths belong to the release integrator under `AGENTS.md` section 6.1

## Non-goals
- no code

## Deliverables
- the note and the version, one version per deploy day

## Required tests
- command: .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <the test files named above>
- expected: pass; each check below can fail, and a lane shows the test that proves it can
- the release-note form test

## Integration contract
Published to `origin/dev`; `origin/main` only by the release integrator under the autodeploy policy.

## Failure/idempotency/security cases
- a note over seven items opens a patch version

## Rollback / feature flag
Revert the note and the version.

## Handoff
- changed files: `git diff --stat <base>..HEAD` and a proof that the forbidden hotspots are untouched
- commands/results: each check with its exact command, the tree SHA and the counts; «not run» with the reason
- known limits: stated, with `path:line` evidence for any departure from the plan
- integration notes: what the integrator must do next
