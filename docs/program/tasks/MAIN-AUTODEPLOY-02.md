# Task MAIN-AUTODEPLOY-02 — deploy the exact `main` revision through GitHub Actions

## Outcome

A push to `origin/main`, or a manual dispatch on `main`, serially SSHes to the alpha host,
selects the exact triggering commit, runs the repository-owned deployment command and refuses
success until the deployed-tree verifier passes for the same clean checkout.

## Depends on

- `MAIN-AUTODEPLOY-01` — completed at `50505fc`; publication/deployment policy is mandatory
- `W47-INT-CLOSE` — completed; deployment and verification commands are accepted
- `NORM-ADR-01` — completed; current `origin/main` decision state is published

## Frozen inputs

- base commit: `50505fcad67b551f0a6a5391ee27fdf1d949239c`
- deployment checkout: `/srv/auditmanager`
- deployment command: `infra/deploy/deploy.sh`
- proof command: `infra/deploy/verify-deployed.sh`
- GitHub secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `VPS_KNOWN_HOSTS`
- trigger branch and publication authority: `origin/main`
- API/domain/migration contracts: unchanged; migration head `0013_norm_embeddings`

## Ownership

This is the sole integration/deployment slot for adding the workflow and making its first
fast-forward publication to `origin/main`. It owns no runtime, contract, migration, dependency,
composition, environment-secret or host-configuration path.

## Allowed paths

- `.github/workflows/deploy-auto.yml`
- `tests/contract/test_deploy_auto_workflow.py`
- `docs/program/tasks/MAIN-AUTODEPLOY-02.md`
- one linear integration commit and one fast-forward update of `origin/main`

## Forbidden hotspots

- `contracts/**`, `db/**`, root dependencies/locks and composition roots
- `infra/deploy/**`, runtime/application/UI code and global styles
- deployment env files, SSH material, GitHub secret values and host configuration
- unrelated manual-alpha files already present in the shared working tree
- tags, `origin/dev`, force-push, history rewriting and destructive host cleanup

## Non-goals

- No secret creation/rotation and no private value in source, logs or task reports.
- No database/data migration beyond what the existing deploy command performs.
- No automatic rollback, force-push or deletion of a dirty host tree.
- No claim that a successful Git push alone proves a successful deployment.
- No change to the public URL, TLS, reverse proxy or Docker composition.

## Deliverables

- dependency-free GitHub Actions workflow with exact-SHA, clean-tree and verified-host-key guards
- workflow contract test protecting its trigger, serialization and command ordering
- executor handoff with candidate SHA, gate result, workflow result and public-origin probes;
  this point-in-time evidence is not committed after the push because that commit would itself
  request another deployment

## Required tests

- `.venv/bin/python -m pytest tests/contract/test_deploy_auto_workflow.py -q`
- `git diff --check`
- full `make gate` with literal `GATE OK` on the exact candidate commit in a clean checkout
- after publication: GitHub workflow success and `infra/deploy/verify-deployed.sh` evidence for
  the same candidate SHA

## Integration contract

- only `push` to `main` and `workflow_dispatch` on `main` may enter the deploy job
- concurrency group `auditmanager-alpha-production` serializes runs and never cancels one in
  progress
- GitHub's triggering SHA is validated as a 40-character commit, passed as data to remote Bash,
  proven reachable from fetched `origin/main`, and checked out detached
- the host refuses before fetch/deploy if tracked or untracked changes exist; it never cleans,
  resets, stashes or overwrites them
- `deploy.sh` runs before `verify-deployed.sh`; both exact HEAD and cleanliness are rechecked
  before the workflow prints `DEPLOY OK`

## Failure/idempotency/security cases

- missing/empty key or known-host material stops before any SSH connection
- malformed user, host or SHA stops locally; strict host-key checking and one explicit identity
  are mandatory
- dirty host, missing commit, non-main commit, checkout failure, deploy failure, verifier failure
  or post-deploy dirt stops the job non-zero
- a later main push queues behind an in-progress deploy rather than cancelling or racing it
- retrying the same SHA is safe because the repository deployment command is idempotent

## Rollback / feature flag

Disable the workflow in GitHub for an emergency stop. Code rollback is a reviewed revert commit
that passes the full gate and deploys forward through `main`; never rewrite `main` or reset the
host. If the first run fails before deployment, keep the workflow failure visible and repair the
owned workflow in a newly gated commit.

## Handoff

- Changed files are the three repository paths in `Allowed paths`; the existing manual-alpha
  files in the shared working tree remain untracked and untouched.
- No API/domain/event/migration/environment contract changes; the new workflow consumes only the
  four owner-created GitHub secrets named above.
- The executor must return exact candidate SHA, full-gate sentinel, workflow run result and
  public-origin results after the one authorized `origin/main` fast-forward. That live evidence
  belongs in the task response rather than a self-triggering follow-up commit.
- Known limitation: the workflow proves the repository-owned deploy/verify path but has no
  automatic rollback. A failed run stays failed and requires a separately gated forward fix.
- Forbidden-hotspot proof is the final staged-path list: no contract, migration, dependency,
  composition, deploy script, runtime/UI, environment, secret or manual-alpha path is included.
