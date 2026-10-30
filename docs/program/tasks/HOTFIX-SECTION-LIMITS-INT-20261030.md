# Task HOTFIX-SECTION-LIMITS-INT-20261030 — publish raised limits for every section to dev

## Outcome

One reviewed commit extends the default-off AI limit switch from the AR v3 group to ordinary starts in all 14 text-profile sections and fast-forwards `origin/dev` to that commit.

## Depends on

- `HOTFIX-SECTION-LIMITS-BACKEND-20261030` (completed in the shared worktree).
- `HOTFIX-SECTION-LIMITS-WEB-20261030` (completed in the shared worktree).

## Frozen inputs

- Domain/API/analysis/events shared contract: `1.11.0` at base, resealed together as `1.12.0` by the backend task's sole contract slot.
- API surface: 131 paths / 148 operations / 432 schemas, unchanged in count.
- Migration head: `0039_comparison_core`, unchanged.
- Base commit: `06b947459fa7535f340af75b625f40af88d2f18f` (`origin/dev` at dispatch).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the backend and web task files above are completed integration inputs, and the review lane reported no remaining blockers.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`, by the owner's 2026-10-30 instruction to combine the independent fixes in one dev push; this follow-up completes the requested all-section scope.
- origin_main_authority: none

## Allowed paths

- `docs/program/CURRENT_STATE.md`
- `docs/program/tasks/HOTFIX-SECTION-LIMITS-INT-20261030.md`

The integration commit stages the two completed child tasks' owned files without editing their changes.

## Forbidden hotspots

- `db/migrations/**`, root dependencies and lock files, composition root, global styles, AR v3 worker and comparison evidence.
- `origin/main`, release tags and checkpoints.

## Non-goals

- Complete `make gate`, a live provider call, a deployment or a release tag; the owner requested basic checks and `dev` only.
- Changing the provider's own output or context limits or the 12-window operational bound.

## Deliverables

- One combined commit on the dev-based hotfix branch, one fast-forward push to `origin/dev`, and the updated current-state summary.
- Child task handoffs list their exact changed files, tests, contract effects and limits.

## Required tests

- Backend focused Python set: 207 passed; `npm --prefix web run api:verify`: pass.
- Web start-run focused tests: 52 passed; web TypeScript and ESLint: pass.
- `tests/contract/api_v1/test_doc_prose_facts.py`, `git diff --check`, and contract pin sweep: pass on the integrated tree.
- Verify `origin/dev` remains the base of the exact checked candidate before a fast-forward push; no force push.

## Integration contract

The optional strict `StartRunRequest.relaxed_limits` field defaults to the prior 16,000-token/cost-ceiling policy. True selects an immutable 64,000-token profile/bundle pair, persists the choice with the Run command and stops only the application cost halt while recording spend. Ordinary section input remains bounded by 12 operational windows whose raised-mode size is stable across cost-ceiling changes. The existing AR v3 switch, favicon and brand home link continue as shipped at base. There is no migration or main publication.

## Failure/idempotency/security cases

- Changing the switch mints a different client key; a reused key with a changed choice is refused by the server.
- A changed `origin/dev` requires reconciliation and renewed focused checks before publication.
- Provider output/context refusal and recorded-mode digest misses remain explicit failures.

## Rollback / feature flag

The switch defaults off and its optional field is omitted. To roll back after deployment, hide the UI choice first and retain worker support until accepted raised-limit Runs are terminal; then revert the contract and backend through a separately owned task.

## Handoff

- Integrator reports the commit SHA, remote ref, check results, unrun live verification, and any environment-only test limitation to the owner.
