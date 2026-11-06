# HOTFIX-RUN-PARTIAL-1106 — partial section analysis and response delivery

task_id: HOTFIX-RUN-PARTIAL-1106

## Outcome and ownership

The release integrator for this task owns publication of the exact buildable hotfix to
`origin/dev`, then fast-forward promotion to `origin/main`, and deployment observation.
The owner's direct instruction of 2026-11-06 authorizes this hotfix and explicitly limits
verification to deployment buildability; no test batteries, standalone lint/typecheck or
full gate are requested. This instruction overrides broader repository check defaults for
this release. The automatically triggered deployment still must finish and verify its tree.

## Inputs and completed dependencies

- Initial base: `0f0f15f8a50db0af42727b35539a132604b68fb0`; integrated dev base
  `ce08af3d20e2efdc6ee21d35317b097f7fdfb35d` before the build.
- Observed main: `5e95269fa89886e1f4242aae8fef745c96a9ee59`.
- Contract 1.32.0; migration `0055_work_schedule`; no migration is planned.
- Completed diagnosis: run `run_01M6R2EEQDFWJYK3113SMVX29A` has an invalid parameter
  quotation and a failed comprehensive batch followed by unknown-outcome skips. The local
  Codex wrapper also has an independent fixed 510-second deadline and response byte cap.
- depends_on: none (the owner's request and supplied run evidence define this repair).

## Allowed paths and lanes

- Integrator: `src/auditmanager/runs/extended_review.py`, relevant analysis response-delivery
  and executor server adapters, proportional release/task records, release-note revision pin and binding `RUNNER_API.md`.
- Parameter lane: `src/auditmanager/analysis/extended/project_parameters.py`,
  `src/auditmanager/runs/project_parameters.py`.
- Runner lane: `tools/executor-runner/{agent.py,codex_answer.py,runner_client.py,agent.codex-ssh.example.toml,README.md}`.
- Web lane: run/start/extended-review presentation and shared cost approval, excluding
  generated clients and global styles; group-start output-length copy is included.
- Integrator alone owns any necessary response-constraint contract reseal and generated
  consumers: contract 1.33.0 removes the existing answer-text ceiling, with all three
  globally sealed families and their constant consumers updated together.

## Non-goals and forbidden hotspots

No source/expert evidence rewriting, fuzzy quotation acceptance, blind retries after an
unknown provider outcome, new model calls, rerun of the owner's document, migration,
dependency/lock change, global styles, composition-root change, release tag or force-push.
Other sessions' worktrees and uncommitted changes are not part of this task.

## Deliverables and integration

Retain valid parameter facts and per-record refusal evidence while continuing independent
batches; preserve completed visual windows during posttext failure; report successful
versus stopped windows accurately; remove application response-size caps and UI response
length promises; remove the runner's hidden 510-second deadline within the server budget.
Install the repository-owned runner repair on this machine without changing credentials,
and restart only its idle service when needed. The deployment and local agent are separate
deliverables: publishing the API image does not replace `/opt` on this machine.

## Verification and rollback

Run deployment-equivalent web production build and backend/package buildability checks,
plus `git diff --check`. Record actual commands and limitations in the release handoff.
Recheck remote refs and require a clean fast-forward candidate before both pushes. Follow
the triggered workflow through its exact-tree verifier and public smoke checks. Rollback
is a forward revert of this task; old run artifacts remain immutable. No new flag is needed.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none

## Publication authority

- development_target: origin/main
- origin_main_authority: delegated release integrator HOTFIX-RUN-PARTIAL-1106
