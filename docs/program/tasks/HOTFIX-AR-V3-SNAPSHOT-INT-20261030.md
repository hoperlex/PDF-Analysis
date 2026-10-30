# Task HOTFIX-AR-V3-SNAPSHOT-INT-20261030 — preserve the current AR v3 solution

## Outcome

The exact current `origin/dev` candidate is preserved as the independent remote branch `origin/ready/ar-v3-20261030` before changing АР on `dev`.

## Depends on

- `HOTFIX-SECTION-LIMITS-INT-20261030` (completed and published to `origin/dev`).

## Frozen inputs

- Domain/API/analysis/events contract: `1.12.0`.
- Migration head: `0039_comparison_core`.
- Base commit and saved branch tip: `99b337fb6e632ebd585f53134eb4425131cfe0b7`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: fetched `origin/dev` and the clean `hotfix/ui-ai-limits` worktree both resolved to `99b337fb6e632ebd585f53134eb4425131cfe0b7` before the branch was made; the proposed remote ref did not yet exist.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/ready/ar-v3-20261030`, by the owner's direct request to save the current АР v3 on a separate branch.
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/HOTFIX-AR-V3-SNAPSHOT-INT-20261030.md`

## Forbidden hotspots

- All runtime, contract, migration, dependency, composition and style files.
- `origin/dev`, `origin/main`, tags and checkpoints during the snapshot step.

## Non-goals

- Changing АР behavior or calling a model in the saved branch.
- A release or deployment claim.

## Deliverables

- Branch `ready/ar-v3-20261030` at the exact SHA above, locally and on `origin`.

## Required tests

- `git ls-remote origin refs/heads/ready/ar-v3-20261030`: the exact saved SHA.
- `git status --porcelain=v1` in the source worktree: empty before branch creation.

## Integration contract

Later `dev` work may change АР while the saved branch continues to identify the pre-rewrite solution. The branch contains the whole repository tree because Git branches identify commits, not individual modules.

## Failure/idempotency/security cases

- A pre-existing remote branch with a different SHA must not be overwritten. No force push.

## Rollback / feature flag

Keep the branch as the requested fallback. No runtime flag is changed by this task.

## Handoff

- Changed file in the `dev` working tree: this record only. The saved branch itself points to the pre-record commit and has no file changes.
- Checks: remote ref verified at `99b337fb6e632ebd585f53134eb4425131cfe0b7`; no gate requested.
- Contracts: unchanged. Risks: the branch is a code snapshot, not evidence of a completed deployment or live provider test.
- Integrator: preserve the branch while rewriting АР on a separate `dev` candidate; leave `origin/main` untouched.
