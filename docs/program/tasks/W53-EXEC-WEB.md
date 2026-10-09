# Task W53-EXEC-WEB — execution journal and queue screens

task_id: W53-EXEC-WEB

## Outcome

`/logs` shows the server execution journal and `/queue` shows durable Jobs,
priority and pause. Authorized users can cancel or re-audit a Run, and
administrators can change queued priority and pause dispatch. Every action
uses the six sealed operations; role refusals and command failures are typed
visible states. At 780 px, long Run identifiers and labels remain usable.

## Depends on

- `W53-FREEZE-01`, completed at `3c527d363ee5a196fbd44bf2f5b187d544615dd6`.
- `W53-SEAL-01`, accepted into this line at `3132fcb861edbc86bb8bc9130034e7125f4e5bb3`.

The EXEC code is present at the exact base below, but its own-proxy 503 and
`validating` cancellation stop records remain open. This WEB task depends on
the sealed API surface, not on a release verdict for EXEC.

## Frozen inputs

- Code input after EXEC integration: `e210c674b4c6db8904572f939619e20d95625be4`.
  The task-file dispatch commit and agent worktree base are
  `a72b7e9e588e4c19bf156f1090402a3af889173e`.
- API: 36 paths / 43 operations / 91 schemas; OpenAPI SHA-256
  `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`.
- Domain: candidate revision 9 / 29 identities; state-machine SHA-256
  `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`;
  23 API error codes; migration head `0017_execution_queue`; contract version
  `1.0.0-draft.1`.
- `docs/program/dispatch/W53-PLAN.md` §3.2–3.3 and Stage B; R-75…R-79.
- `W53-EXEC-STOP-01` and `W53-EXEC-STOP-02`: the UI must not promise an
  automatic own-503 retry or cancellation during `validating`.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `web/src/shared/config/screen-registry.ts`
- enumerator_owner: `W53-EXEC-WEB`
- totality_query: `git grep -n -E "address: '/(logs|queue)'" -- web/src/shared/config/screen-registry.ts`

The two existing screen entries graduate from prepared to built. Query-key
and route maps, guards, the journey manifest and the UI seam note must agree.

## Captured premise evidence

### P-01 — prepared page locations

- captured_at: 2026-10-09
- command: `find web/src/app web/src/_pages -maxdepth 4 -type f | grep -E '/(logs|queue)/'`
- captured_output:
  ```text
  web/src/app/logs/page.tsx
  web/src/app/queue/page.tsx
  web/src/_pages/logs/ui/logs-page.tsx
  web/src/_pages/logs/index.ts
  web/src/_pages/queue/ui/queue-page.tsx
  web/src/_pages/queue/index.ts
  ```
- interpretation: these are the current stubs and module seams, not an
  `execution-queue` page namespace.

### P-02 — sealed client operations

- captured_at: 2026-10-09
- command: `git grep -n -E '^export function (listExecutionQueue|listExecutionJournal|cancelRun|reauditRun|setJobPriority|setExecutionPaused)' -- web/src/shared/api/generated/client.gen.ts`
- captured_output:
  ```text
  web/src/shared/api/generated/client.gen.ts:151:export function cancelRun(
  web/src/shared/api/generated/client.gen.ts:343:export function listExecutionJournal(
  web/src/shared/api/generated/client.gen.ts:355:export function listExecutionQueue(
  web/src/shared/api/generated/client.gen.ts:487:export function reauditRun(
  web/src/shared/api/generated/client.gen.ts:535:export function setExecutionPaused(
  web/src/shared/api/generated/client.gen.ts:547:export function setJobPriority(
  ```
- interpretation: generated client already exposes all six operations; this
  task consumes it and does not reseal or edit generated code.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/src/app/{logs,queue}/**`.
- `web/src/_pages/{logs,queue,workers,run}/**` (`run` is the journal link only;
  `workers` corrects its now-stale no-Job wording only).
- `web/src/widgets/{execution-journal,execution-queue}/**` (new).
- `web/src/features/{cancel-run,reaudit-run,set-job-priority,pause-execution}/**` (new).
- `web/src/entities/execution/**` (new).
- `web/src/shared/lib/routes.ts`, `web/tests/unit/screens/routes.test.ts`.
- `web/src/shared/config/screen-registry.ts` (the two entries only).
- `web/src/shared/api/query-keys.ts` (`execution` namespace only).
- `web/docs/PC01_UI_SEAM.md` (§6 only).
- `web/tests/unit/api/configuration-and-cache-keys.test.ts`,
  `web/tests/contract/narrow-sets.contract.test.ts`,
  `web/tests/guards/{query-key-shape,prepared-sections,dashboard-invalidation,rendered-language}.guard.test.ts`,
  `web/tests/unit/styles/screens.ts`.
- `web/tests/unit/execution/**` (new) and `tests/e2e/pc01/journey/manifest.json`.
- `docs/program/W53-EXEC-WEB.md` (handback).

## Forbidden hotspots

All other paths, especially `contracts/**`, API backend, migrations, generated
client, root and web dependency/lock files, composition roots, global styles,
MinIO, backup, `VERSION`, release notes, release refs/tags and the working stand.
No expansion of a maintained screen or capability set without its declared
enumerator owner and totality check.

## Non-goals

No live push or polling timer, worker service, backup, MinIO upgrade, release
claim, 0.4.0 notes, feature-flag framework, backend implementation or contract
change. Refresh on focus, after an action and by an explicit «Обновить» control.

## Deliverables

The two working screens, Run journal link, corrected Workers copy, typed
read/action states, role-aware controls, accessible confirmations naming the
Run, invalidation of execution data after commands, focused UI tests, guard
updates, journey manifest and six-item `W53-EXEC-WEB.md` handback.

## Required tests

- `npm --prefix web run lint`, `npm --prefix web run typecheck`,
  `npm --prefix web test`, `npm --prefix web run api:verify`;
  `.venv/bin/pytest tests/e2e/test_pc01_journey_conformance.py` for the
  journey manifest.
- Tests for all role combinations and typed refusal states, command
  idempotency-key reuse per intent, cursor pagination, focus/explicit refresh,
  action invalidation, long identifiers at 780 px and no sensitive journal data.
- `git diff --check`, frozen hashes and exact changed-path audit. Check disk
  under `AGENTS.md` §8 before costly tests. Full `make gate` is the
  integrator's final clean-SHA gate.

## Integration contract

Work in isolated branch `agent/w53-exec-web` from the exact dispatch SHA
supplied by the integrator. Use the generated client and existing BFF/session
path. Preserve operation IDs and DTO shapes. The server may return
`state_transition_not_allowed` when a Run is `validating`; display it as a
typed refusal and keep the current state. The `gate-w53web` lane owns ports
56870, 60470/60471 (API 56970, Next 31470 if needed); measure them before
use. Stop only own disposable resources at handback.

## Failure/idempotency/security cases

Mint one idempotency key per user intent and reuse it for transport retry;
show unknown outcomes without silently repeating a command. Render only
sealed safe journal fields, never raw provider payload, path, key or secret.
Role-hidden actions still handle a server 403 as a typed refusal. A delayed
page response must not overwrite newer action state.

## Rollback / feature flag

Revert the WEB commit before a development deployment. The screens use the
existing routes and have no new independent flag; no stand is changed here.

## Handoff

Return branch and exact SHA, all six items of `AGENTS.md` §5, commands and
results, exact base-to-HEAD changed-path audit, frozen hashes, risks and
integration instructions. No ref publication, tag or working-stand operation.
