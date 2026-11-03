# Task EXEC2-WEB-CAP-01 — capacity on the connection form and card, honest waiting reasons, the client-document notice

## Outcome
An administrator sets «Одновременных прогонов» on a connection and sees used/total units on its card. A queued Run says «в очереди: исполнитель занят» or «раннер не в сети» rather than a generic state. Connection screens say «допуск клиентских документов не проверяется» (`R-149a`).

## Depends on
- EXEC2-SEAL-1

## Frozen inputs
- domain contract: unchanged
- API contract: 1.15.0, frozen by `EXEC2-SEAL-1`
- analysis/comparison/event contract: unchanged
- migration head: `0046`, created by `EXEC2-SEAL-1`; this task adds no migration
- base commit: `integration/exec2` after the `EXEC2-SEAL-1` merge
- architecture: `docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md` decisions 1, 2, 19; plan `docs/program/dispatch/EXEC2-PLAN.md`; rulings `R-149a`…`R-149f`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the connection form and card live in one feature and one widget

### P-01 — the files of the connection form and card
- captured_at: 2026-11-02
- command: `git ls-tree -r --name-only origin/dev web/src/widgets/executor-connections web/src/features/manage-executor-connection`
- captured_output:
  ```text
  web/src/features/manage-executor-connection/index.ts
  web/src/features/manage-executor-connection/model/settings.ts
  web/src/features/manage-executor-connection/model/use-command-key.ts
  web/src/features/manage-executor-connection/model/use-manage-executor-connection.ts
  web/src/features/manage-executor-connection/model/use-set-executor-route.ts
  web/src/features/manage-executor-connection/ui/archive-control.tsx
  web/src/features/manage-executor-connection/ui/command-failure.tsx
  web/src/features/manage-executor-connection/ui/create-connection-form.tsx
  web/src/features/manage-executor-connection/ui/host-key-control.tsx
  web/src/features/manage-executor-connection/ui/probe-button.tsx
  web/src/features/manage-executor-connection/ui/revise-connection-form.tsx
  web/src/features/manage-executor-connection/ui/runner-token-panel.tsx
  web/src/features/manage-executor-connection/ui/settings-fields.tsx
  web/src/features/manage-executor-connection/ui/ssh-key-control.tsx
  web/src/widgets/executor-connections/index.ts
  web/src/widgets/executor-connections/ui/connection-card.tsx
  web/src/widgets/executor-connections/ui/executor-connections.module.css
  web/src/widgets/executor-connections/ui/executor-connections.tsx
  exit=0
  ```
- interpretation: the settings fields, the card and their styles are the touch points.

The integrator re-runs every premise command on the actual base before dispatch (`EXEC2-PLAN.md` section 6) and corrects line numbers; a premise that no longer holds stops the dispatch.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `web/src/features/manage-executor-connection/**`
- `web/src/widgets/executor-connections/**`
- `web/src/entities/executor-connection/**`
- `web/src/entities/audit-run/**`
- `web/tests/unit/**`

## Forbidden hotspots
- `contracts/**`, generated models and client, the migration head, root dependency/lock files and global styles (owned by the stage's SEAL task)
- `src/auditmanager/shared/errors/**`: EXEC-2 adds no error code (ADR-0026 decision 18)
- paths another EXEC-2 task owns in the same stage (`EXEC2-PLAN.md` section 5)
- in `src/auditmanager/bootstrap/adapters.py` and `src/auditmanager/api/routers/ports.py`, which three stage-1 lanes share: any function or class outside this task's own port; new code goes in a section headed with this task id, and the integrator merges the lanes one by one
- `web/src/_pages/workers/**` (stage 3)
- `web/src/features/start-run/**` (stage 3)

## Non-goals
- no group UI
- no wizard (stage 2)

## Deliverables
- The capacity field (1–16) with the coupled-limit hints of decision 2 and the server's refusals mapped to Russian messages.
- Occupancy on the card. The Run waiting reason wherever a queued Run is shown.
- The `R-149a` notice on the connection list.
- Component tests for B1 §6 item 13, as new files under `web/tests/unit/` (no existing test file is edited).

## Required tests
- command: not run in EXEC-2 (`R-149d`); write the tests below and mark those that need PostgreSQL with the suite's existing database marker
- expected: B1 §6 test 13 exists as component tests

## Integration contract
- reads only the 1.15.0 generated client

## Failure/idempotency/security cases
- no «свободно» while unresolved remote work holds a unit

## Rollback / feature flag
UI only; revert the merge.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: generation commands run and their result; no test, build, typecheck, lint, database, browser or model run (`R-149d`)
- known limits: every acceptance test named above is unexecuted
- integration notes: what the next consumer of this task may rely on
