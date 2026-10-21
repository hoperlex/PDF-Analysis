# W55B-INT-DEPLOY-VERIFY-FIX-01 — remote verification continuation repair

## Finding

The W55b `origin/main` workflow run `38897018419` was reported successful, but the authenticated step log ended after `infra/deploy/deploy.sh` output and contained neither `=== verify deployed tree ===` nor `DEPLOY OK`. Therefore that run does not prove `infra/deploy/verify-deployed.sh` executed. The host's deployed revision is not established by this task.

The remote script is passed to `bash -s` on stdin. Without redirection, a child command can consume the remaining script. A new regression extracted the actual workflow heredoc and executed it with a deploy stub that drains stdin. On the base commit's workflow, both subcases ended before verification; the success subcase returned `0`, reproducing the false green mechanism.

## Change

`deploy-auto.yml` now runs both `infra/deploy/deploy.sh` and `infra/deploy/verify-deployed.sh` with stdin from `/dev/null`. The remote shell keeps the unread script, proceeds to verification and prints `DEPLOY OK` only after the verify command succeeds and the exact SHA/clean-tree checks pass. A nonzero verification result stops the script before that marker.

`tests/contract/test_deploy_auto_workflow.py` adds a behavioral regression using the actual remote heredoc, a stdin-draining deploy stub, a stdin-draining verification stub, and both successful and failing verification. The test does not require SSH, Docker, credentials or access to the deployment host.

## Verification

- Before the workflow edit, the new test failed in both verification subcases: output stopped at `DEPLOY STUB CALLED` and lacked `=== verify deployed tree ===`.
- After the edit, `python3 -m unittest tests.contract.test_deploy_auto_workflow -v` passed **8/8** tests, including both new subcases.
- The W55b candidate's virtualenv Python ran `pytest -q tests/contract/test_deploy_auto_workflow.py`: **8 tests, 2 subtests** passed.
- The same Python ran `pytest -q tests/contract/program/test_wave_governance.py`: **16 tests** passed.
- `git diff --cached --check` passed. The staged diff lists exactly the four allowed paths below; the commit-to-base path check follows commit creation.

## Frozen boundary and handoff

Base: `37393a979a430e490843d7f410e9eca9491a4ea1` (`0.6.0`, API 47/54/123, 24 errors, migration `0021_portal_bundles`). No API/domain contract, migration, dependency lock, composition root, global style, deploy script, product code or historical evidence is changed. There is no remote push, tag or host action from this lane.

The integrator must treat run `38897018419` as incomplete verification evidence, run a complete gate on a clean repair candidate, obtain the separate exact-SHA main publication authority, and then verify the new workflow run and deployment host on that same SHA under `MAIN_AUTODEPLOY_POLICY.md`. This local regression proves the stdin continuation behavior, not the live host result.

## Final handoff

- changed files: `.github/workflows/deploy-auto.yml`, `tests/contract/test_deploy_auto_workflow.py`, this report and `tasks/W55B-INT-DEPLOY-VERIFY-FIX-01.md`.
- checks: pre-fix red; post-fix 8/8 workflow contract tests plus 2 subtests; programme governance 16/16; `git diff --check` passed.
- new/changed contracts: workflow execution guarantee only; no product-facing contract.
- known limits: full gate and live same-SHA host verification remain integration work.
- integration instruction: cherry-pick the exact local repair commit onto the W55b main lineage and repeat full release preflight; do not infer deployment success from the earlier green run.
