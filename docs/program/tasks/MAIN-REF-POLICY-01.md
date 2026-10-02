# Task MAIN-REF-POLICY-01 — publish development versions to `origin/dev` by default

## Outcome

Every integrated development candidate is published to `origin/dev`; no task, wave closeout or
green gate may update `origin/main` unless the repository owner gives a separate direct
instruction to publish that exact candidate to `main`.

## Depends on

- `MAIN-AUTODEPLOY-02` — completed by successful run `36873558201`, attempt 2, for
  `608632a52940cbff70a1e8361f241901f48182aa`
- `W48-PLAN-01` — completed; its publication sequence is the first consumer of this ruling

## Frozen inputs

- owner ruling: development versions go to `origin/dev`; `origin/main` only by direct instruction
- `origin/main` at task start: `608632a52940cbff70a1e8361f241901f48182aa`
- `origin/dev` at task start: `acc6463fccd83f8af75b1d405ddf7d3ca888fa8e`
- auto-deploy workflow: `.github/workflows/deploy-auto.yml`, successful run `36873558201`
- domain contract: `1.0.0-draft.1`, candidate revision 8, 27 opaque identities
- API contract: 17 paths / 20 operations / 61 schemas, SHA-256
  `f043eb6c3a5bbba3cb95fff59039fff42582c79ae0dc8ff2ba261e2cb4583585`
- error catalog: 22 codes
- migration head: `0013_norm_embeddings`
- base commit: `85597167ba1084be1ea64b30d3d69893f735569f`

## Allowed paths

- `AGENTS.md`
- `docs/program/MAIN_AUTODEPLOY_POLICY.md`
- `docs/program/VERSION_FIXATION.md`
- `docs/program/CURRENT_STATE.md` — active-development orientation only
- `docs/program/dispatch/W48-PLAN.md`
- `docs/program/dispatch/W49-PLAN.md`
- `docs/program/tasks/MAIN-AUTODEPLOY-02.md` — successful live-evidence handoff only
- `docs/program/tasks/MAIN-REF-POLICY-01.md`
- `docs/program/MAIN-REF-POLICY-01.md`

## Forbidden hotspots

- `.github/**`, deploy scripts/composition and host configuration
- `contracts/**`, generated clients and the error catalog
- `db/migrations/**` and migration head
- root dependency/lock files, `Makefile`, runtime/UI code and global styles
- historical reports and completed wave evidence outside the explicit live-orientation paths
- Git refs, tags, deployment host state and all secrets

## Non-goals

- no workflow, trigger or deployment implementation change
- no push to `origin/main`, `origin/dev` or any other ref in this documentation task
- no claim that a dev publication is deployed or accepted as an alpha release
- no weakening of the full gate, fast-forward or deployed-verification requirements

## Deliverables

- normative branch/publication rule in `AGENTS.md`, the auto-deploy policy and version fixation
- W48 and queued W49 sequences that publish the development candidate to `origin/dev` and stop
  before `origin/main` unless separately instructed
- completed `MAIN-AUTODEPLOY-02` evidence and this task's completion report

## Required tests

- `.venv/bin/python -m pytest tests/contract/api_v1/test_doc_prose_facts.py
  tests/contract/api_v1/test_surface_counts_in_prose.py -q` — green
- `rg -n "direct instruction|прям.*указан|origin/dev|origin/main"
  AGENTS.md docs/program/MAIN_AUTODEPLOY_POLICY.md docs/program/VERSION_FIXATION.md
  docs/program/dispatch/W48-PLAN.md docs/program/dispatch/W49-PLAN.md` — the default and
  exceptional paths are explicit
- `git diff --check` — empty output

## Integration contract

- `origin/dev` is the default publication ref for a clean, gated integration candidate.
- Updating `origin/main` is a separate external deployment action. Authority exists only when
  the owner directly instructs publication of the exact candidate; a wave plan, integration
  role, green gate, tag target or prior permission is not a substitute.
- Once directly instructed, the assigned integration task must still follow
  `MAIN_AUTODEPLOY_POLICY.md` completely and prove workflow/deployed SHA equality.
- Without that instruction, a wave may become code-complete on `origin/dev`, but it remains
  undeployed and untagged if its tag requires deployed/manual evidence.

## Failure/idempotency/security cases

- ambiguous phrases such as “close the wave”, “publish the version” or “continue” do not grant
  `origin/main` authority
- a moved remote ref, dirty tree, missing full gate or non-fast-forward stops either publication
- pushing `origin/dev` never claims deployment and never substitutes for public acceptance
- no credential, workflow log body or host configuration enters repository documentation

## Rollback / feature flag

Documentation-only. A later owner ruling may supersede this policy in a new task; historical
evidence is not rewritten. No runtime flag or data rollback applies.

## Handoff

- changed files: recorded in `docs/program/MAIN-REF-POLICY-01.md`
- commands/results: recorded after validation
- known limits: the GitHub workflow still triggers only from `main`; dev publication is not a
  deployment
- integration notes: `W48-FREEZE-01` is next and may update only `origin/dev`
