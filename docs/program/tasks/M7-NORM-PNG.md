# Task M7-NORM-PNG — norm page crops for the critic and «Возможные нормы»

## Outcome
PNG crops of norm pages are rendered once and declared in the critic's task for models that accept images; «Возможные нормы» come from the same paragraphs (`ADR-0029` decision 9).

Owner: the norms lane.

## Depends on
- CRIT-SEAL-50
- CTX-CRITIC

Dispatch the lane only when every task above is merged into the base it works from.

## Frozen inputs
- domain contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- API contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- analysis/comparison/event contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- migration head: `0062_hosts_stage_models` at the base; `0063` once the AR v3 removal wave merges (`R-154h`)
- the seals: the first seal of this programme is 1.51.0 / `0064` (`R-154h`: the AR v3 removal wave takes 1.50.0 / `0063` first); the second is 1.52.0 / `0065` (`R-154h`)
- base commit: `47c90e1ec6adf160f788e69279819c0e9c048e8e`
- ADR: `ADR-0029` decision 9; `DECISION-MEMORY-01` section 6.3
- a Claude Code host takes no images
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
- `src/auditmanager/norms/**`
- `src/auditmanager/executors/image_input.py`
- `src/auditmanager/runs/extended_review.py`
- `tests/unit/norms/**`
- `tests/integration/norms/**`

## Forbidden hotspots
- `contracts/**` and `db/migrations/**`, unless the lane owns them below
- `src/auditmanager/bootstrap/composition.py` and `src/auditmanager/bootstrap/adapters.py`, unless the lane owns them below
- `pyproject.toml`, `uv.lock`, `web/package-lock.json`, `web/src/app/globals.css`
- `VERSION` and `release-notes/**`, unless the lane owns them below
- the historical records `docs/program/tasks/**` (except the new task files of `CRIT-ADR-29`) and `docs/manual-tests/**`
- any path outside `Allowed paths`; a path a lane needs and lacks is named in its report, not taken

## Non-goals
- no search over norms by the encoder: «Возможные нормы» do not depend on it

## Deliverables
- a PNG made once from a one-page PDF and kept in `norm_crop_render`
- `crop_id: norm.<nbd_…>` declared in the task's `images` at its creation, only from this run's norm-context paragraphs, only if the `review:main` cell's model declared images, at most 2 per task within the limit of 8
- «Возможные нормы» in the finding card from the same paragraphs

## Required tests
- command: .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <the test files named above>
- expected: pass; each check below can fail, and a lane shows the test that proves it can
- a task for a Claude Code cell gets no norm images
- at most 2 images
- only norms of this run's context

## Integration contract
`runs/extended_review.py` has one owner at a time: `F8-PUBLISH`, then `CTX-STAND`, then `CTX-CRITIC`, then this lane, which is why `CTX-CRITIC` is listed above.

## Failure/idempotency/security cases
- a crop that cannot be produced is listed as unavailable with a reason; the text is still delivered

## Rollback / feature flag
The switch «контекст критику».

## Handoff
- changed files: `git diff --stat <base>..HEAD` and a proof that the forbidden hotspots are untouched
- commands/results: each check with its exact command, the tree SHA and the counts; «not run» with the reason
- known limits: stated, with `path:line` evidence for any departure from the plan
- integration notes: what the integrator must do next
