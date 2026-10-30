# Task HOTFIX-UI-INT-20261030 — integrate three UI hotfixes on dev

## Outcome

One development commit carries the AR v3 limit switch, favicon and removal of the duplicate «Главная» menu link; `origin/dev` fast-forwards to that commit.

## Depends on

- `HOTFIX-AI-LIMITS-20261030` (completed in the shared worktree).
- `HOTFIX-FAVICON-20261030` (completed in the shared worktree).
- `HOTFIX-NAV-20261030` (completed in the shared worktree).

## Frozen inputs

- Base: `e8567a1981cbe35cf66bae4ce79b2877224df1be`, the fetched `origin/dev` at task start.
- Contract: `1.10.0` at base; AI task owns the sole additive minor reseal to `1.11.0`.
- API surface: 131 paths / 148 operations / 432 schemas, unchanged in count.
- Migration head: `0039_comparison_core`, unchanged.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the three independent task files and their focused check reports are the integration inputs.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`, by the owner's 2026-10-30 instruction to combine and make one dev push.
- origin_main_authority: none

## Allowed paths

- `docs/program/CURRENT_STATE.md`
- `docs/program/tasks/HOTFIX-UI-INT-20261030.md`

The integration commit also stages the completed child tasks' allowed paths without editing their owned changes.

## Forbidden hotspots

- `db/migrations/**`, root dependencies and lock files, composition root, and `web/src/app/globals.css`.
- `origin/main`, release tags and checkpoints.

## Non-goals

- A deployment or a release tag.
- A complete gate or a live provider call, as the owner requested focused checks only.

## Deliverables

- One combined commit on the dev-based hotfix branch and one fast-forward push to `origin/dev`.
- This integration record and the current-state summary.

## Required tests

- Child task focused tests and API/client version checks: pass.
- `tests/contract/api_v1/test_doc_prose_facts.py`: 44 passed after a line break in an older dated paragraph removed a false deployed-SHA match.
- `git diff --check`: pass.
- Verify the fetched `origin/dev` is the parent of the candidate immediately before push; refuse a non-fast-forward.

## Integration contract

The shared contract is `1.11.0`; the optional AR v3 request field defaults to the prior policy. The home route remains accessible through the brand. The favicon is served by Next.js from its app directory. No migration runs, no root dependency changes, and no main publication is part of this task.

## Failure/idempotency/security cases

- A changed `origin/dev` requires reconciliation and renewed focused checks before publication; no force push.
- The AR v3 choice is part of the group idempotency fingerprint and persists for all six child Runs.

## Rollback / feature flag

The AR v3 switch defaults off. A revert of the dev commit restores the old menu and removes the favicon. If raised-limit groups have already been queued on a deployed stand, keep worker support until they reach a terminal state before removing it.

## Handoff

- Integrator reports the final commit SHA, push result, focused checks and any unrun live verification to the owner.
