# Task W48-FREEZE-01 — freeze the W48 code base and publish its dispatch tip to `origin/dev`

## Outcome

W48 has one exact fully gated code base, one docs-only dispatch tip on `origin/dev`, a measured
unchanged contract set and executable task files for the three disjoint Stage-A lanes.

## Depends on

- `W48-PLAN-01` — completed at `7b6a458` after rebase onto the accepted main line
- `MAIN-AUTODEPLOY-02` — completed by run `36873558201`, attempt 2, exact SHA `608632a`
- `ALPHA-MANUAL-01` — completed at `a20d890`; fixture package and checksums are committed
- `MAIN-REF-POLICY-01` — completed at `6118e66`; development publication targets `origin/dev`

## Frozen inputs

- frozen code base: `6118e66033380661bb747244e0f7a222fb9a87b4`
- `origin/main` at freeze start: `608632a52940cbff70a1e8361f241901f48182aa`
- `origin/dev` at freeze start: `acc6463fccd83f8af75b1d405ddf7d3ca888fa8e`
- domain contract: `1.0.0-draft.1`, candidate revision 8, 27 opaque identities
- API contract: 17 paths / 20 operations / 61 schemas, SHA-256
  `f043eb6c3a5bbba3cb95fff59039fff42582c79ae0dc8ff2ba261e2cb4583585`
- error catalog: 22 codes
- analysis/comparison/event contract: PC-01 synthetic AR oracle and four-way comparison,
  unchanged
- migration head: `0013_norm_embeddings`
- controlling ruling: `R-49`

## Allowed paths

- `docs/program/tasks/W48-FREEZE-01.md`
- `docs/program/W48-FREEZE-01.md`
- `docs/program/dispatch/W48-PLAN.md` — frozen YAML/status only
- `docs/program/tasks/W48-AUDIT.md`
- `docs/program/tasks/W48-PROSE.md`
- `docs/program/tasks/W48-GUARDS.md`
- one docs-only dispatch commit and one fast-forward update of `origin/dev`

## Forbidden hotspots

- `contracts/**`, generated clients and error catalog
- `db/migrations/**` and migration head
- root dependencies/locks, `Makefile`, composition roots and global styles
- runtime, frontend, deploy and workflow implementation
- `CURRENT_STATE.md`, `DEBT_REGISTER.md` and historical evidence
- `origin/main`, tags, deployment host and secrets

## Non-goals

- no Stage-A implementation or audit finding in the freeze task
- no W48 contract, migration, dependency or product change
- no deployment, public manual acceptance or `alpha-w48` tag
- no task file for Stage B before Stage A and its judge are completed

## Deliverables

- full-gate evidence for exact frozen code base `6118e66`
- contract/error/migration measurements matching the W48 plan
- exact W48 frozen YAML and freeze completion report
- executable `W48-AUDIT`, `W48-PROSE` and `W48-GUARDS` task files
- docs-only dispatch tip fast-forwarded to `origin/dev`

## Required tests

- clean isolated checkout of `6118e66`: `make gate` prints literal `GATE OK`
- `sha256sum contracts/api/v1/openapi.json` equals the frozen API digest
- live API path/operation/schema counts equal 17/20/61; error catalog equals 22; domain opaque
  identity count equals 27; migration head equals `0013_norm_embeddings`
- `.venv/bin/python -m pytest tests/contract/api_v1/test_doc_prose_facts.py
  tests/contract/api_v1/test_surface_counts_in_prose.py -q` — green on the dispatch tree
- `git diff --check` and clean status before the ref update
- fetched `origin/dev` equals the pushed docs-only dispatch tip; `origin/main` remains `608632a`

## Integration contract

- `frozen_code_base` identifies every runtime, contract, migration, dependency and test byte
  entering W48.
- The dispatch commit may change only the six documentation paths in `Allowed paths`; therefore
  Stage-A lanes branch from its exact `origin/dev` tip while inheriting frozen code bytes.
- Stage-A tasks own disjoint paths and may not infer Stage-B or ref authority.
- This task owns the initial W48 `origin/dev` update only and has no `origin/main` authority.

## Failure/idempotency/security cases

- a moved `origin/main`/`origin/dev`, non-fast-forward relation, dirty base, red gate or changed
  contract measurement stops dispatch
- a docs-only change outside `Allowed paths` voids the dispatch commit
- rerunning the measurements is read-only; repeating the exact dev push is a no-op
- no workflow/host/provider credential enters task files, logs or commands

## Rollback / feature flag

Documentation/ref bookkeeping only. Do not rewind `origin/dev`; correct a bad dispatch record by
a reviewed forward documentation commit. No runtime feature flag or data rollback applies.

## Handoff

- changed files: recorded in `docs/program/W48-FREEZE-01.md`
- commands/results: recorded after the exact-base gate and measurements
- known limits: D-70 remains a release/tag blocker, not a Stage-A code blocker
- integration notes: Stage A starts from the exact dispatch tip published to `origin/dev`;
  `origin/main` is untouched
