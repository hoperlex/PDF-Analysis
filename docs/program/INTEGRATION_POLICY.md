# Integration policy

## Working refs and worktrees

- `dev` is the shared development line; `main` is the auto-deploy release line.
- A single owner can make a small, isolated change on the appropriate development
  checkout. Create a short-lived branch/worktree when work is concurrent, the base must
  remain fixed, or isolation protects uncommitted work. Reuse it through the task; do
  not create a branch for each stage, review or small correction.
- Use one integration branch only when several concurrent changes need convergence.
  Prefer a small vertical change over a mandatory contract → provider → consumer → QA
  branch chain when one owner can safely edit it.
- After integration, remove clean, idle worktrees with `scripts/worktree_cleanup.py`.
  Delete a local branch only after confirming its work landed by content (`git cherry`
  when history was rewritten) and that no task, review or handoff still uses its name
  as a reference. Prefer immutable commit SHAs in new records. Never infer safe
  deletion from age or branch name alone.

## Ownership

One writer at a time for a shared contract, migration head, root lockfile,
composition root or global style surface. A change in those paths needs an identified
owner and affected-consumer checks, but it does not automatically need multiple task
files or a full gate on the development server. Generated OpenAPI client changes are
made from the owned contract, not hand-edited.

## Acceptance and publication

Use `AGENTS.md` §8's risk-based checks on the changed behavior. A merge into `dev`
may carry an explicitly labelled unverified candidate; its known gaps travel with it.
Do not describe it as accepted or deployable until the relevant checks pass. Do not
repeat the full suite after each merge when the next merge changes the candidate.

The delegated release integrator decides and records the exact release candidate and
checks under `MAIN_AUTODEPLOY_POLICY.md`, then fast-forwards `main` and verifies the
workflow and host. The owner need not perform a GitHub merge for every release.

Reject or pause integration for an unowned contract change, secret exposure, silent
failure path, unresolved data-integrity/retry behavior, or a failed relevant check.
Record a resource-blocked check as unverified rather than treating it as green.
