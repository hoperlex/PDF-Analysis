# Task W55B-INT-DEPLOY-VERIFY-FIX-01 — ensure deployment verification runs

## Outcome

The GitHub deployment job cannot report success before the remote checkout has executed `infra/deploy/verify-deployed.sh` and printed `DEPLOY OK` for its trigger SHA.

## Depends on

- `W55B-INT-CLOSE` — W55b development close, complete.
- `W55B-INT-MAIN-PREP-03` — exact release candidate and R-125 gate record, complete on the development line.

## Frozen inputs

- base commit: `37393a979a430e490843d7f410e9eca9491a4ea1`, already published to `origin/main` as the W55b deployment trigger.
- API: 47 paths, 54 operations, 123 schemas; error catalog: 24.
- migration head: `0021_portal_bundles`; product version: `0.6.0`.
- deployment contract: `docs/program/MAIN_AUTODEPLOY_POLICY.md` at the base commit.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the remote deploy child inherits Bash script stdin.

### P-01 — remote shell reads the deploy commands from stdin

- captured_at: 2026-10-16
- command: `rg -n 'bash -s|infra/deploy/(deploy|verify-deployed).sh|DEPLOY OK' .github/workflows/deploy-auto.yml`
- captured_output:

  ```text
  78:            bash -s -- "$DEPLOY_SHA" <<'REMOTE'
  110:          infra/deploy/deploy.sh
  113:          infra/deploy/verify-deployed.sh
  118:          echo "DEPLOY OK: $DEPLOY_SHA"
  ```

- interpretation: the remote shell receives its script on stdin and passes the same stdin to child commands. A child that drains it can cause Bash to reach EOF before executing verification. The integrator observed that run `38897018419` ended successfully after deploy output, without the verification heading or `DEPLOY OK`; this task tests the mechanism locally, not the host state.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none; this repair lane prepares a candidate for a separate integration decision and does not push.

## Allowed paths

- `.github/workflows/deploy-auto.yml`
- `tests/contract/test_deploy_auto_workflow.py`
- `docs/program/tasks/W55B-INT-DEPLOY-VERIFY-FIX-01.md`
- `docs/program/W55B-INT-DEPLOY-VERIFY-FIX-01.md`

## Forbidden hotspots

- `contracts/**`, migrations, dependency and lock files, composition root, global styles, product source and deployment scripts.
- `docs/program/MAIN_AUTODEPLOY_POLICY.md` and all historical W55b evidence.
- Remote refs, tags, deployment host state and the clean `w55b-main-candidate` worktree.

## Non-goals

- No change to deploy behavior, image contents, migrations or data.
- No assertion that the already-green workflow run verified the host.
- No push, tag, new deployment or host write by this lane.

## Deliverables

- The workflow gives deployment and verification commands independent stdin.
- A regression executes the extracted remote script with a stdin-draining child and checks that verification runs, including its failure exit.
- A report gives exact diff, tests, known limits and integrator handoff.

## Required tests

- `python3 -m unittest tests.contract.test_deploy_auto_workflow -v`: all pass.
- `git diff --check`: pass.
- `git diff --name-only <base>`: only the four allowed paths.

## Integration contract

The integrator may take the repair commit on the W55b main lineage, run the full same-SHA release gate and the `MAIN_AUTODEPLOY_POLICY.md` preflight, then seek the separate publication decision. A green prior workflow run with no verification output remains incomplete evidence.

## Failure, idempotency and security cases

- A deployment command may read all stdin yet remote verification still runs.
- If verification exits nonzero, `set -e` must fail the job before `DEPLOY OK`.
- The pinned SSH host key, read-only GitHub permissions, exact SHA selection and cleanup remain unchanged.

## Rollback / feature flag

- No feature flag. Rollback would be an explicitly gated new fast-forward release, as required by the main policy.

## Handoff

- changed files: workflow, focused contract test, this task and companion report.
- commands/results: the pre-fix stdin-drain regression failed in both subcases; the post-fix workflow suite passed 8/8. See companion report for exact checks.
- known limits: host verification and a full gate belong to the integrating release task.
- integration notes: no publication from this repair lane.
