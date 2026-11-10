# Task F8-GATE — gate v2: block evidence admitted only when verified

## Outcome
The gate accepts a block as evidence only when its `blk_` is in this run's geometry, the crop's sha matches `page_crops`, and a quote, if present, is verbatim in that block's recognised text (`ADR-0029` decision 7).

Owner: the gate lane.

## Depends on
- CRIT-SEAL-50

Dispatch the lane only when every task above is merged into the base it works from.

## Frozen inputs
- domain contract: 1.49.0, unchanged until the seal
- API contract: 1.49.0, unchanged until the seal
- analysis/comparison/event contract: 1.49.0, unchanged until the seal
- migration head: `0062_hosts_stage_models`, unchanged until the seal
- the seal: 1.50.0 / `0063`, or the next free numbers if the AR v3 removal wave merges first
- base commit: `47c90e1ec6adf160f788e69279819c0e9c048e8e`
- ADR: `ADR-0029` decision 7 (block grounding proves a place, not a content; `quote_in_recognised_text` is cancelled for block evidence only)
- plan section 4 item 3; the gate inputs are read in `_read_gate_inputs` of `src/auditmanager/runs/executor.py`
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
- `src/auditmanager/findings/grounding.py`
- `src/auditmanager/findings/artifacts.py`
- `src/auditmanager/runs/executor.py`
- `tests/integration/findings/**`

## Forbidden hotspots
- `contracts/**` and `db/migrations/**`, unless the lane owns them below
- `src/auditmanager/bootstrap/composition.py` and `src/auditmanager/bootstrap/adapters.py`, unless the lane owns them below
- `pyproject.toml`, `uv.lock`, `web/package-lock.json`, `web/src/app/globals.css`
- `VERSION` and `release-notes/**`, unless the lane owns them below
- the historical records `docs/program/tasks/**` (except the new task files of `CRIT-ADR-29`) and `docs/manual-tests/**`
- any path outside `Allowed paths`; a path a lane needs and lacks is named in its report, not taken

## Non-goals
- no publication of groups: `F8-PUBLISH`
- no change to the text-evidence rules

## Deliverables
- the gate reads `geometry.portal_blocks`, `geometry.page_crops` and `prepared.recognised_text` in addition
- a block-evidence verdict with the reasons `block_not_in_run_geometry`, `block_crop_mismatch`, `block_quote_not_in_recognised`; no normalisation of the quote
- `grounding_kind` on the observation: `text_span` or `portal_block`

## Required tests
- command: .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <the test files named above>
- expected: pass; each check below can fail, and a lane shows the test that proves it can
- a foreign `blk_` (not in this run) is refused
- a crop whose sha differs is refused
- a quote absent from the recognised text is refused
- text evidence is checked as before, including `quote_in_recognised_text`

## Integration contract
`F8-PUBLISH` publishes only what this gate passed; a run in `text_only` mode never reaches the block branch.

## Failure/idempotency/security cases
- the gate fails closed: an unverifiable block is a refusal with a reason, never a pass

## Rollback / feature flag
The marker `text_only` keeps the old gate.

## Handoff
- changed files: `git diff --stat <base>..HEAD` and a proof that the forbidden hotspots are untouched
- commands/results: each check with its exact command, the tree SHA and the counts; «not run» with the reason
- known limits: stated, with `path:line` evidence for any departure from the plan
- integration notes: what the integrator must do next
