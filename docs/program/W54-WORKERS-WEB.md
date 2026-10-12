# W54-WORKERS-WEB — hand-back report

- Task: `docs/program/tasks/W54-WORKERS-WEB.md`; grant: `dispatch/W54-PLAN.md` §4 Stage B item 6,
  behaviour per §3.7. Checks per `R-102` (light, container-free).
- Branch `agent/w54-workers-web`, worktree `.local/worktrees/w54-workers-web`, base `80a157f`
  (`integration/w54`: SEAL's sealed `listWorkers`/`setWorkerIntake`, WORKER's real bodies).
  Implementation commit `2798896`; this report is the last commit.

## 0. What was built

| Plan item (§3.7) | Where |
|---|---|
| `/workers` graduates from the stub: the registry from `listWorkers`, online and stale first (server order kept), offline in a collapsed `<details>` with its count | `_pages/workers/ui/workers-page.tsx`, `widgets/worker-list/**`, `entities/execution/model/workers.ts` (`groupWorkers`) |
| Each row: state («На связи» / «Не отвечает» / «Отключён»), intake, slots, version, started, last heartbeat, current runs (linked to `/logs?run_id=`) | `widgets/worker-list/ui/worker-list.tsx` |
| «Не брать новые» / «Разрешить» for administrators only (`canExecute(roles, 'intake')`); pressing it opens a confirmation naming the worker; «Подтвердить» sends `setWorkerIntake` with a key minted once per intent; an unknown outcome offers «Повторить с тем же ключом»; «Отмена» sends nothing | `workers-page.tsx`, `features/set-worker-intake/**` (`retry: false`, invalidates `queryKeys.execution.all()`) |
| `R-80`: the registry row stays `any-role` (unchanged); rows render without waiting for `getMe`, and on a `getMe` failure without any switch and with «Исполнители показаны без команд: права не прочитаны.» | `workers-page.tsx` |
| Refresh: `staleTime: 0`, `refetchOnWindowFocus: 'always'`, invalidation after the command, «Обновить» | `entities/execution/api/use-execution.ts` (`workersQueryOptions`) |
| Honest states: empty registry («Исполнителей нет», says runs executed by the application itself are not listed), empty later page, no worker on line on this page, a state outside the sealed set refused («Неизвестное состояние исполнителя»), read failure «Исполнители не прочитаны» with correlation id, command refusal / failure / unknown outcome | `worker-list.tsx`, `workers-page.tsx` |
| Queue and run screens name the worker: the queue for `leased`/`running` Jobs, the run screen in `running`/`validating`; both read one first page of `listWorkers` (limit 200, the contract maximum) only in those states and match `current_run_ids`. Five honest outcomes: held (id linked to `/workers`), unheld (whole registry read, no worker names it), beyond (more pages exist), unreadable, pending | `entities/execution/ui/run-worker-line.tsx`, `runWorker`, `widgets/execution-queue`, `_pages/queue`, `widgets/run-progress` (`RunHolder`) |
| New query key `queryKeys.execution.workers(cursor, limit)` inside the `execution` namespace; `routes.workers()` | `shared/api/query-keys.ts`, `shared/lib/routes.ts` |
| Placeholder stub text: `RoutePlaceholder`'s doc no longer cites workers as the deferred section (props kept, no caller) | `shared/ui/route-placeholder.tsx` |
| Journey manifest: `/workers` expects `listWorkers` + `getMe`; `/queue` and the run row list `listWorkers` as optional with the condition | `tests/e2e/pc01/journey/manifest.json` |

## 1. Changed files (`git diff --name-only 80a157f..HEAD`)

```
docs/program/W54-WORKERS-WEB.md
tests/e2e/pc01/journey/manifest.json
web/src/_pages/queue/ui/queue-page.tsx
web/src/_pages/workers/ui/workers-page.tsx
web/src/entities/execution/api/use-execution.ts
web/src/entities/execution/index.ts
web/src/entities/execution/model/presentation.ts
web/src/entities/execution/model/workers.ts                (new)
web/src/entities/execution/ui/run-worker-line.tsx          (new)
web/src/features/set-worker-intake/index.ts                (new)
web/src/features/set-worker-intake/model/use-set-worker-intake.ts (new)
web/src/shared/api/query-keys.ts
web/src/shared/lib/routes.ts
web/src/shared/ui/route-placeholder.tsx
web/src/widgets/execution-queue/ui/execution-queue.tsx
web/src/widgets/run-progress/ui/run-progress.tsx
web/src/widgets/worker-list/index.ts                       (new)
web/src/widgets/worker-list/ui/worker-list.module.css      (new)
web/src/widgets/worker-list/ui/worker-list.tsx             (new)
web/tests/guards/dashboard-invalidation.guard.test.ts
web/tests/guards/prepared-sections.guard.test.ts
web/tests/guards/rendered-language.guard.test.ts
web/tests/unit/execution/execution-screens.test.ts
web/tests/unit/screens/routes.test.ts
web/tests/unit/screens/run-progress.test.ts
web/tests/unit/styles/screens.ts
web/tests/unit/workers/intake-command.test.ts              (new)
web/tests/unit/workers/intake-confirmation.test.ts         (new)
web/tests/unit/workers/workers.test.ts                     (new)
```

Guards and shared tests changed, each because this change required it:

- `prepared-sections.guard.test.ts` — `/workers` graduates out (as `/logs` and `/queue` did in
  W53): removed from `SECTIONS`; the R-18 "workers is the one exempt stub" block becomes "every
  prepared section says it is coming" (same can-fail case kept).
- `rendered-language.guard.test.ts` — `KEYS.workers` seeded in the loaded (one worker per state)
  and empty clients, so the refused state reaches the read-failure branch; four extra shapes
  (unknown state, empty later page, none on line, all five `RunWorkerLine` sentences);
  `workerOf` on the three `ExecutionQueue` shapes; one `UNREACHABLE_IN_ONE_PASS` entry,
  «Команда исполнителю отклонена» (mutation-settled refusal past the confirmation, the same
  reason as the queue's «Команда отклонена»).
- `dashboard-invalidation.guard.test.ts` — the new mutation hook mapped `false`.
- `tests/unit/styles/screens.ts` — contrast census gains `ExecutionQueue running, its worker named`
  and `WorkerList loaded` (the new module's `.row` border is reached); `workerOf` on the queue seed.
- `routes.test.ts` — `routes.workers()` in the `D-94` builder census and the literal check.
- `execution-screens.test.ts` — the queue helper passes `workerOf` (required prop).
- `run-progress.test.ts` — three new cases (named while running/validating, unheld, no read
  in other states).

Not changed: `shared/config/screen-registry.ts` (the `/workers` row was already `any-role`, in
the menu), `screen-registry`/`lazy-boundary` guards, `route-screens.ts`.

## 2. Checks (in the worktree, container-free; no Next server, browser or docker)

| Command | Result |
|---|---|
| `git diff --check` | clean |
| `npm --prefix web run lint` | exit 0 |
| `npm --prefix web run typecheck` | exit 0 |
| `cd web && npx vitest run tests/guards/{prepared-sections,dashboard-invalidation,rendered-language,lazy-boundary,screen-registry,screen-set,screen-claims-about-the-system,eslint-boundary,query-key-shape}.guard.test.ts tests/unit/screens tests/unit/execution tests/unit/styles` | 29 files, 498 passed (after the one `UNREACHABLE_IN_ONE_PASS` entry; before it, 1 red naming that branch) |
| `cd web && npx vitest run tests/unit/workers tests/unit/screens/run-progress.test.ts` | 4 files, 105 passed |
| `cd web && npx vitest run` (whole suite, final tree before the report commit) | **126 files, 1881 passed** |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/e2e/test_pc01_journey_conformance.py` | 82 passed (manifest operations exist in the contract) |

**Shown able to fail** (each mutation applied to the source, the workers and run-progress
tests run, the file restored from a scratch copy):

| Mutation | Red |
|---|---|
| `'intake'` removed from `canExecute`'s admin set | 3 (`workers.test.ts`: list, page, presentation) |
| `select` executes the command instead of opening the confirmation | 1 (`intake-confirmation`: "answers the switch with a confirmation, not a write") |
| run screen's `RunHolder` never rendered | 2 (`run-progress.test.ts`) |
| `staleTime: 0` dropped from `workersQueryOptions` | 2 (`workers.test.ts` reads) |
| offline not separated in `groupWorkers` | 4 (`workers.test.ts`) |

The confirmation's key reuse is read off a recording `fetch`: two presses of «Подтвердить» send
two identical `PUT /execution/workers/{id}/intake {"enabled":false}` with the seeded intent key.

## 3. Contracts

None changed: no OpenAPI, domain, event, error-catalog or migration edit; the generated client is
used as is. Web-internal surface only:

- `queryKeys.execution.workers(cursor?, limit?)` (namespace set unchanged);
  `routes.workers()`.
- `@/entities/execution`: `WORKER_PAGE_LIMIT` (50), `WORKER_LOOKUP_LIMIT` (200),
  `workersQueryOptions`, `useWorkers`, `useWorkerLookup`, `groupWorkers`,
  `hasUnknownWorkerState`, `jobHoldsLease`, `runHoldsLease`, `runWorker`, `workerIntakeLabel`,
  `workerStateLabel`, `RunWorkerLine`, types `RunWorker`, `WorkerGroups`;
  `ExecutionAction` gains `'intake'` (administrator only).
- `@/features/set-worker-intake`: `useSetWorkerIntake`. `@/widgets/worker-list`: `WorkerList`.
- `ExecutionQueueProps.workerOf` (required). `_pages/workers`: `intakeIntentLabel`,
  `noIntakeIntent`, type `IntakeIntent` (module exports for tests; the slice index still
  exports `WorkersPage` only).

## 4. Risks and known limitations

1. The queue and run screens read only the first 200 workers (newest start first). Workers that
   can hold a run heartbeat and were started recently, so they come first; past 200 rows the line
   says «Исполнитель не найден на первой странице списка исполнителей» rather than guessing. The
   registry has no retention (`W54-WORKER-01` limitation 3), so a long-lived stand accumulates
   offline rows; the «Исполнители» screen pages 50 at a time and groups per page.
2. A run executed by the API process itself (`EXECUTION_ROLE=all`, the rollback shape) holds a
   Lease with no `worker_id`; the screens then say no registered worker holds it, which is true
   of the registry.
3. The run screen's worker line is read when it mounts and on tab return, not on the 2–15 s run
   poll; a reclaim to another worker mid-run shows after a tab return or a reload.
4. A worker that stopped reads «На связи» for up to 90 s (server-derived state, `W54-WORKER-01`
   limitation 3); the page shows the server's word and the last heartbeat time beside it.
5. Pressing the switch, confirming and retrying are verified through the element tree and a
   recording `fetch` (no DOM), not in a browser; the live journey is the integrator's window step.
6. `RoutePlaceholder`'s `unavailability`/`headline` props now have no caller; kept, documented.

## 5. Integrator instructions

1. Merge `agent/w54-workers-web` after reading the diff and this report. No path overlaps a
   backend lane; likely textual neighbours only in `rendered-language.guard.test.ts` and
   `tests/unit/styles/screens.ts` if another web lane seeds states there.
2. Post-merge light acceptance: web lint, typecheck, full Vitest; the Python journey
   conformance (`tests/e2e/test_pc01_journey_conformance.py`).
3. Window step (live journey): `/workers` cold must call exactly `listWorkers` and `getMe`
   (plus the optional `listReleases`); `/queue` and the run screen call `listWorkers` only when a
   Job is `leased`/`running` or the run is `running`/`validating`. With the worker service up,
   check by hand that an administrator's «Не брать новые» → «Подтвердить» flips the row to «Не
   берёт новые прогоны» and that an expert sees no switch.

## 6. Containment

- `git diff --name-only 80a157f..HEAD` is the list in §1; every path is inside the grant
  (plan §4 Stage B item 6 plus this report): `_pages/{workers,queue}/**`,
  `widgets/{worker-list,execution-queue,run-progress}/**`, `features/set-worker-intake/**`,
  `entities/execution/**`, `shared/api/query-keys.ts` (inside `execution` only),
  `shared/lib/routes.ts`, `shared/ui/route-placeholder.tsx` (doc text), the named tests and
  guards, the journey manifest.
- Not touched: BFF (`web/src/app/**`), backend, `contracts/**`, migrations, lock files,
  `globals.css`, `shared/{api,config,ui}/index.ts`, `screen-registry.ts`, `DEBT_REGISTER.md`,
  `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, other worktrees, refs, tags, the stand.
- No container, server or browser started; no push, merge, tag, stash; no process killed.
  `git status --porcelain -uall` is empty after this commit.
