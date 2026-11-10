# Task F8-WEB — «Разбор» as one list: source chip, critic's advice, block frame

## Outcome
«Разбор» shows the source chip, the critic's advice and refinement in the card, the block frame in the viewer and the run's caption (`ADR-0029` decision 7); +3 concepts on the screen, counted.

Owner: the web lane; ownership of the page is by agreement with the UI-parity programme before this lane starts.

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
- ADR: `ADR-0029` decision 7; plan section 6 (concepts per screen)
- no UI library: own `--am-*` tokens and the CSS module next to the component; text in Russian; dense layout
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
- `web/src/_pages/review/**`
- `web/src/widgets/finding-list/**`
- `web/src/widgets/extended-review/**`
- `web/src/entities/finding/**`
- `web/src/entities/finding-observation/**`
- `web/tests/unit/review/**`
- `web/tests/unit/analysis-extended/**`

## Forbidden hotspots
- `contracts/**` and `db/migrations/**`, unless the lane owns them below
- `src/auditmanager/bootstrap/composition.py` and `src/auditmanager/bootstrap/adapters.py`, unless the lane owns them below
- `pyproject.toml`, `uv.lock`, `web/package-lock.json`, `web/src/app/globals.css`
- `VERSION` and `release-notes/**`, unless the lane owns them below
- the historical records `docs/program/tasks/**` (except the new task files of `CRIT-ADR-29`) and `docs/manual-tests/**`
- any path outside `Allowed paths`; a path a lane needs and lacks is named in its report, not taken
- `web/src/app/globals.css`

## Non-goals
- no more than two controls in a finding row
- no mark «Недоступно» in a row

## Deliverables
- the chip «Источник» (text, drawing, cross-check); the critic's advice and refinement through `extended_observation_ref`; the block frame in the viewer; the caption «отдельные машинные наблюдения» removed for `one_list` runs
- a preview in light and dark at 1280 and 390 px with DOM facts, before any commit of visual changes (the owner's rule)

## Required tests
- command: from `web/`: `npx vitest run --maxWorkers=1 <files>`, `npx tsc --noEmit -p .` and `npx eslint <files>`
- expected: pass; each check below can fail, and a lane shows the test that proves it can
- a block finding without `char_start` is drawn
- ✓/✕ on it records a decision
- the preview exists in both themes

## Integration contract
Reads `Finding.block_evidence[]` and `FindingObservation.grounding_kind`; collides with `PREC-WEB` on the same page, so the two are ordered.

## Failure/idempotency/security cases
- a finding with no text span still opens its card

## Rollback / feature flag
The switch «один список».

## Handoff
- changed files: `git diff --stat <base>..HEAD` and a proof that the forbidden hotspots are untouched
- commands/results: each check with its exact command, the tree SHA and the counts; «not run» with the reason
- known limits: stated, with `path:line` evidence for any departure from the plan
- integration notes: what the integrator must do next
- visible change: a preview in light and dark at 1280 and 390 px with DOM facts under `.local/reports/<lane>-2026-11-10/`; the lane reports the paths and stops, and the commit of visual changes waits for the owner
