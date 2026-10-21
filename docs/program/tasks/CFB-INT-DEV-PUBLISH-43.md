# Task CFB-INT-DEV-PUBLISH-43 — publish deployment verification repair to dev

task_id: CFB-INT-DEV-PUBLISH-43

## Outcome

Fast-forward `origin/dev` to a clean candidate carrying the checked
`deploy-auto` stdin-continuation repair. The release ref `origin/main` and
`v0.6.0` remain on the deployed W55b SHA.

## Depends on

- `CFB-INT-DEV-PUBLISH-42`, completed at `f812014588010f408e0594d56f1d9f41d1379227`.
- `W55B-INT-DEPLOY-VERIFY-FIX-01`, completed at `babab5b5ba30f35dde8be058e143ad5a2f286943`.

## Frozen inputs

- base commit: `f812014588010f408e0594d56f1d9f41d1379227`
- source repair commit: `babab5b5ba30f35dde8be058e143ad5a2f286943`;
- deployed release: `origin/main` / `v0.6.0` = `37393a979a430e490843d7f410e9eca9491a4ea1`;
- workflow run `38897018419` did not execute `verify-deployed.sh` in its log;
- owner's direct host verification of the deployed tree is recorded in `W55B-INT-MAIN-VERIFY-ADDENDUM-01.md`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the local repair source changes only workflow and its behavioral regression, plus its own records.

### P-01 — exact paths on the current dev candidate

- captured_at: 2026-10-16
- command: `git diff f812014588010f408e0594d56f1d9f41d1379227..HEAD --name-only`
- captured_output:
  ```text
  .github/workflows/deploy-auto.yml
  docs/program/W55B-INT-DEPLOY-VERIFY-FIX-01.md
  docs/program/tasks/W55B-INT-DEPLOY-VERIFY-FIX-01.md
  tests/contract/test_deploy_auto_workflow.py
  ```
- interpretation: this is a scoped dev repair; no main publication or host deployment follows from it.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `.github/workflows/deploy-auto.yml`
- `tests/contract/test_deploy_auto_workflow.py`
- `docs/program/tasks/W55B-INT-DEPLOY-VERIFY-FIX-01.md`
- `docs/program/W55B-INT-DEPLOY-VERIFY-FIX-01.md`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-43.md`
- `docs/program/CFB-INT-DEV-PUBLISH-43.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, deploy scripts, application/API/UI code, original release
evidence, production DB/S3, host state, `origin/main` and tags.

## Non-goals

No main push, new deployment, retagging, assertion that the old workflow
verified the host, beta acceptance or normative corpus publication.

## Deliverables

One source cherry-pick, this task/report, workflow behavioral and governance
checks, exact-path handoff, dev fast-forward and remote readback.

## Required tests

- `tests/contract/test_deploy_auto_workflow.py` and programme governance:
  pass, including both stdin-draining regression subcases.
- Clean tree, exact paths, `git diff --check`, handoff with explicit check argv.
- Fresh remote dev/main/tag read, fast-forward proof, exact-SHA dev push and
  readback. A full `make gate` on the isolated source repair candidate is
  running separately; this dev publication is not main-release certification.

## Integration contract

The workflow repair is present in `dev` for review. Its remote script now
passes `/dev/null` to deploy and verify children so Bash retains the rest
of its stdin script. Any later main publication requires a new exact-SHA
owner instruction, full same-SHA gate and the policy's deployment proof.

## Failure/idempotency/security cases

Stop on moved dev, dirty candidate, failed checks or path expansion. No
force push or credential/log copy. Publishing the exact already-present
dev SHA again is a no-op.

## Rollback / feature flag

No product runtime flag. Correct a future workflow issue by a reviewed
forward commit; never rewrite main or the release tag.

## Handoff

- changed files: six exact allowed paths;
- contracts: no product contract change; workflow execution guarantee;
- tests/limits: 24 tests and 2 subtests, full source gate pending;
- forbidden hotspots untouched.
