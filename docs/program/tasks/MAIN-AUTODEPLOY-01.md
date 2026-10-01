# Task MAIN-AUTODEPLOY-01 — make `origin/main` an explicit deployment boundary

## Outcome

Every agent and integrator is told that a push or merge to `origin/main` can change the
externally reachable alpha stand, and has one fail-closed publication procedure to follow.

## Depends on

- `W47-INT-CLOSE`
- `NORM-VECTOR-01`

## Frozen inputs

- domain contract: candidate revision 8, 27 opaque identities;
- API contract: 17 paths / 20 operations / 61 schemas, 22 error codes;
- analysis/comparison/event contract: unchanged;
- migration head: `0013_norm_embeddings`;
- base commit: `3489378ab8e916876688045085b51618d19d20b8`;
- deployment evidence remains executable, not prose: `infra/deploy/verify-deployed.sh`.

## Allowed paths

- `AGENTS.md`
- `docs/program/MAIN_AUTODEPLOY_POLICY.md`
- `docs/program/tasks/MAIN-AUTODEPLOY-01.md`
- `docs/program/MAIN-AUTODEPLOY-01.md`

## Forbidden hotspots

- `.github/**` and the auto-deploy workflow itself;
- `contracts/**`, migrations and generated consumers;
- root dependencies and lock files;
- composition roots, deployment scripts and global styles;
- `docs/program/CURRENT_STATE.md`, owned by the concurrent `NORM-ADR-01` work.

## Non-goals

- Implement, enable or test the GitHub auto-deploy workflow.
- Push, merge, tag or deploy anything.
- Claim that a particular commit is deployed from a time-sensitive prose sentence.
- Put deployment or registry credentials in Git or documentation.

## Deliverables

- A normative `origin/main` auto-deploy policy.
- A mandatory pointer to that policy in `AGENTS.md`.
- A documentation-only handoff report.

## Required tests

- `.venv/bin/python -m pytest tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py -q`
- `git diff --check`
- `rg -n "MAIN_AUTODEPLOY_POLICY|origin/main" AGENTS.md docs/program/MAIN_AUTODEPLOY_POLICY.md`

## Integration contract

Once the owner enables the workflow, an integration task may treat a successful fast-forward of
one exact, gated SHA to `origin/main` as a request to deploy that SHA. It may not treat the push as
proof that deployment completed: workflow success and `verify-deployed.sh` are separate required
evidence.

## Failure/idempotency/security cases

- A failed or cancelled workflow is a failed deployment, never a successful push with a warning.
- A second main update must not race an in-progress deployment.
- Rollback never rewrites `main`; it is a new reviewed and gated revert commit.
- Secrets remain in GitHub Environment/host storage and never enter logs or committed env files.
- A temporary hostname is not identity for a deployed revision.

## Rollback / feature flag

Documentation-only. Revert this task if auto-deploy is abandoned. Removing the documentation
while the trigger remains active is not a valid rollback.

## Handoff

- changed files: the four paths in `Allowed paths`;
- commands/results: recorded in `docs/program/MAIN-AUTODEPLOY-01.md`;
- known limits: workflow implementation and first deployment proof remain owner work;
- integration notes: no ref, tag, workflow or external deployment is changed by this task.
