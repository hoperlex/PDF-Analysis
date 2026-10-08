# Task W52-INT-MAIN-01 — publish the checked development snapshot to main

task_id: W52-INT-MAIN-01

## Outcome

The exact development snapshot `fd78ad8c76f21e034d81c0b1af0e8c2d1d75b022` is
merged with the existing main hotfix, passes a complete gate and production web
build, and is deployed by the serialized `origin/main` workflow. The workflow
and deployment host must verify the same merge commit.

## Depends on

- `W51-INT-HOTFIX-01`, completed on `origin/main` at `1e9bb1308b7b97cd75eef28e206b23c569871b68`.
- `W52-INT-A2B-01`, completed on `origin/dev` at `fd78ad8c76f21e034d81c0b1af0e8c2d1d75b022`.

## Frozen inputs

- Remote `origin/main`: `1e9bb1308b7b97cd75eef28e206b23c569871b68`.
- Remote `origin/dev`: `fd78ad8c76f21e034d81c0b1af0e8c2d1d75b022`.
- Domain candidate revision 9 / 29 identities; API 27 paths / 34 operations /
  77 schemas; error catalog 23; migration head `0015_accounts_roles_registration`.
- `docs/program/MAIN_AUTODEPLOY_POLICY.md`; the owner's direct 2026-10-08
  instruction to bring this `origin/dev` version to `origin/main` and explicit
  clarification that this is main-publication authority.
- The W51 production hotfix is already backported on dev by
  `W52-INT-HOTFIX-BACKPORT-01`. Stage B `W52-SEAL-01` remains outside this
  frozen snapshot.

## Allowed paths

- The Git merge of the two exact frozen refs, with all inherited development
  files taking their exact `origin/dev` blobs.
- `web/tests/guards/rendered-language.guard.test.ts`: resolve the sole merge
  conflict to the already accepted dev blob, which retains the W51 correction
  and later D-128 F-1 coverage.
- `docs/program/tasks/W52-INT-MAIN-01.md`: this publication grant and record.
- One merge commit on `integration/w52-main-publication` and one fast-forward
  update of `origin/main` after all policy checks.

## Forbidden hotspots

No newly authored contract, migration, root dependency/lock, composition-root,
global-style or deployment-input change; no change to a development blob outside
the conflict resolution above. No `origin/dev` update, tag, force-push or post-gate
fix. The inherited changes were authored under their completed development tasks.

## Non-goals

No W52 Stage B/C implementation, release tag, new API or migration, and no
claim that the deferred D-137–D-140 QA or manual acceptance is complete.

## Deliverables

- A clean merge commit containing both parent histories and the exact dev
  content, with the main-only W51 hotfix task retained.
- Complete `make gate` with literal `GATE OK` on that commit; production web
  build and deployment-input review.
- Exact-SHA workflow, host verification and public-origin evidence in the
  integration report, without a second post-deployment commit.

## Required checks

- `git diff --check`; `git merge-base --is-ancestor origin/main HEAD` and
  `git merge-base --is-ancestor origin/dev HEAD`.
- `make gate` on a clean committed tree with literal `GATE OK`.
- `npm --prefix web run build` on the same tree; review the pinned deployment
  Dockerfiles, compose inputs and workflow.
- Re-read `origin/main` immediately before push and verify fast-forward of
  the exact gated SHA. Then verify workflow success, selected SHA, host
  `infra/deploy/verify-deployed.sh` result and public TLS/application probes.

## Integration contract

Only this task publishes its gated merge commit to `origin/main` under the
owner's direct instruction. Preserve both frozen parents, resolve the sole
overlap to dev's tested guard, and stop publication if a check or ref readback
differs. The GitHub workflow is serialized with `cancel-in-progress: false`.

## Rollback / feature flag

No feature flag applies to this publication. A rollback is a newly reviewed,
fully gated forward revert and another exact-SHA deployment; history rewrite is
forbidden.
