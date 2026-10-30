# Task HOTFIX-SECTION-LIMITS-WEB-20261030 — raised AI limits on ordinary section starts

## Outcome

The ordinary «Запустить прогон» control offers a switch, off by default, for the raised AI-analysis limits. The user can see that the application cost budget is disabled when selected, output is requested at up to 64,000 tokens, the provider may allow less, and the technical input-text bound remains. Every section using `startRun` sends the choice with its own idempotency intent.

## Depends on

- `HOTFIX-UI-INT-20261030` (completed and published to `origin/dev`).

## Frozen inputs

- Domain contract: confirmed section and text-profile routing from the current development tree.
- API contract: `1.11.0` at base; the sibling API lane owns the optional `StartRunRequest.relaxed_limits` addition and the next minor reseal. This web lane consumes that addition and owns no contract edit.
- Analysis/comparison/event contract: single-Run start semantics and preset/executor idempotency intent remain as at base.
- Migration head: `0039_comparison_core`, unchanged.
- Base commit: `06b947459fa7535f340af75b625f40af88d2f18f` (`origin/dev` at dispatch).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `StartRunControl` is the ordinary start UI, and its command builds `StartRunRequest` through `startRunBody`. The six-check AR v3 start already has a separate switch. Verified in `web/src/features/start-run/**` and `web/src/features/start-ar-v3-group/**` at base.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none; the integrator owns the combined `origin/dev` publication requested by the owner.
- origin_main_authority: none

## Allowed paths

- `web/src/features/start-run/**`
- `web/tests/**`
- `docs/program/tasks/HOTFIX-SECTION-LIMITS-WEB-20261030.md`

The wider test allowlist is solely for resealing current `contract_version` fixtures after the sibling API contract advances from `1.11.0` to `1.12.0`. Historical contract-version scenarios retain their original literals and meaning.

## Forbidden hotspots

- `contracts/**`, `web/src/shared/api/generated/**`, backend and database files.
- Root dependency and lock files, composition roots, global styles, navigation and favicon files.
- `origin/main`, release tags and checkpoints.

## Non-goals

- Changing the six-check AR v3 control or provider behaviour.
- A full gate, deployment, live model call or publication by this lane.

## Deliverables

- An ordinary start switch and a request builder that sends `relaxed_limits: true` only when selected.
- Idempotency signatures that include the choice while preserving the prior signature and request when off.
- Focused tests of request, key, default UI and retry wiring.
- Current-version web test fixtures updated to `1.12.0` for the generated literal contract type.

## Required tests

- `npm --prefix web test -- tests/unit/start-run/start-run-intent.test.ts tests/unit/start-run/executor-select.test.ts`: pass.
- `npm --prefix web run typecheck`: pass after the sibling API lane generates the new request field.
- `npm --prefix web run lint -- --quiet`: pass on the integrated tree.
- `git diff --check`: pass.

## Integration contract

`startRunIntent(versionUid, executorConnectionId, presetId, relaxedLimits)` preserves the three-argument call shape and old signature when `relaxedLimits` is absent or false. When true, its signature changes and its command carries the choice. `startRunBody` adds `relaxed_limits: true` to the existing preset or executor request, but omits the field when off. The API sibling must provide optional `StartRunRequest.relaxed_limits` in the generated type before the integrator's typecheck.

## Failure/idempotency/security cases

- Changing the switch clears the old refusal and mints a new idempotency key. A retry of the same choice retains the key.
- The switch is disabled while the start request is pending.
- The UI does not claim that the provider will accept 64,000 output tokens.
- The UI discloses the remaining technical input-text bound imposed by the Run watchdog.

## Rollback / feature flag

The switch defaults off and the optional field is omitted. Reverting the web files removes the choice. The backend must retain handling for already accepted raised-limit Runs until they finish.

## Handoff

- changed files: `web/src/features/start-run/model/start-run-intent.ts`, `web/src/features/start-run/ui/start-run-control.tsx`, its CSS module, three updated start-run tests, and current-version fixtures under `web/tests/**`. The passthrough test in `web/tests/unit/api/credentialed-forward.test.ts` deliberately retains one older upstream envelope and now says why.
- commands/results: focused `web/tests/unit/start-run` tests 52/52 passed; `npm --prefix web run typecheck`, `npm --prefix web run lint -- --quiet`, and `git diff --check` passed after reseal. A broader five-file Vitest run had 97 passed and one 120-second timeout: the unrelated real-fetch upload test tried to bind `127.0.0.1`, which the sandbox rejected with `listen EPERM`. This is an environment restriction, not a failed product assertion.
- known limits: provider output cap remains external; the ordinary Run's technical input-text bound remains in force. The sandbox prevents the local-server test from passing here.
- integration notes: generated `StartRunRequest` now includes optional `relaxed_limits`; verify the combined tree and run the remaining focused checks in an environment that permits loopback listening if needed.
