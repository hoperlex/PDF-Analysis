# EXEC-PAR-WEB-01 — choose the executor of a run in the UI, and see it

Lane branch `agent/exec-par-web-01`, based on `4c5bd6cd`. Task: [`tasks/EXEC-PAR-WEB-01.md`](tasks/EXEC-PAR-WEB-01.md).
Decisions: [`EXEC-PAR-DECISION-01.md`](EXEC-PAR-DECISION-01.md). Backend it consumes:
[`EXEC-PAR-START-01.md`](EXEC-PAR-START-01.md). The lane committed to its own branch only; nothing was
merged, pushed or tagged. Web only: no contract, no generated client, no lock, no package file, no
CSS (every class used already exists in `globals.css`), no Python.

The start-run control gets an «Исполнитель» select. The choice is sent as `executor_connection_id` (the
field is absent for «По умолчанию (маршрут)», never `null`) and is part of the start's idempotency intent.
The run list and the run page name the executor and its pinned model; a queued run says «Ждёт исполнителя
«…»»; the journal calls `audit_run.executor_chosen` «Выбран исполнитель». A refused choice is shown as
itself with no offer of another executor or of the default route.

## Judgement calls the integrator should read

1. **A connection that cannot serve is listed disabled, with its reason; an archived one is not listed.**
   The reason is the sentence «Назначения» already uses (`ROUTE_BLOCKER_SENTENCES`), because the select asks
   the repository's one readiness rule, `routeBlocker`, and does not restate it. Why listed: a person who
   looks for an executor and does not find it cannot tell a missing connection from one whose key needs
   checking. Why archived is hidden: it is retired, and «Назначения» hides it the same way. An archived
   connection that is the current choice stays listed (disabled, with «подключение в архиве»); a choice that
   has left the list altogether stays selected as «Выбранный исполнитель больше не в списке». The select never
   moves the choice by itself.
2. **The reason word of a refusal is read from the stand's English message, narrowly.**
   `dependency_unavailable` declares only `dependency` as a safe key (`EXEC-PAR-START-01`, call 1), so the stand
   writes `… cannot serve a run now (archived)` (`executors/resolver.py:128`; the message passes `screen_message`
   unchanged). `entities/audit-run/model/executor-refusal.ts` reads the last parenthesised word only when it is
   one of `archived`, `kind_not_served`, `not_probed`, `no_revision`, picks a Russian sentence from a closed
   `Map`, and never shows the message. Any other message leaves the reason out. If the catalog gains a detail
   key for the reason, that file is the one place to change.
3. **A retry is drawn when the envelope says the failure is retryable, as everywhere else.** The catalog
   pins `dependency_unavailable` retryable and `validation_failed` not. So an executor that cannot serve now
   gets «Повторить с тем же ключом»; a `validation_failed` on `executor_connection_id` (unknown, malformed or
   `kind_not_routable` identifier) is `unsupported` with no retry, because the same request is refused again.
   The task text reads as if both carry a retry; I followed the catalog rather than draw a button that cannot
   help. Say so if the owner wants the button on both.
4. **«Ждёт исполнителя «…»» is drawn for the state `queued`, and claims no more.** The queue also holds a run
   back for a free worker slot, and the reading does not say which; the sentence names the executor the run
   will run on. A run with no `executor` (every run on the environment source) draws no line and no placeholder.
5. **After a refusal the choice stays, and changing it clears the old refusal** (`mutation.reset()`), because
   the refusal was about the old choice. The select is disabled only while a start is in flight. The refusal
   block itself holds no link, no select and no second button; the select beside it is the control's own and is
   the person's act, not an offer.
6. **Reads.** The select uses the existing hooks (`useExecutorConnections`, `useExecutorConnectionDetails`),
   which `ExecutorRoutes` already uses; that is one list read and one detail read per non-archived connection
   (needed for the pinned model, the last probe and the readiness rule). The only polling is the hook's own,
   bounded probe poll, in the one file the no-second-polling-loop guard names. The lane adds no interval, no
   timer, and no request for the waiting state. Reads are open to every role.
7. **The intent key.** `startRunIntent(versionUid, chosen)` returns the signature and a builder of the command
   from one argument pair, so the key and the request cannot disagree. The signature of a start with no choice
   is the one it always had (`start-run:<version>`), so an unchanged page keeps its key; a chosen connection
   appends `:executor:<id>`.

## Changed files and why

All paths are inside the task's allowed list. Commits: `dd0c7f29` (entities, run list and run page),
`44d99f12` (select, intent, refusal, guards), `9d7764dc` (two harnesses), plus the docs commit with this note.

| Path | Reason |
|---|---|
| `web/src/entities/executor-connection/model/start-choice.ts` (+ `index.ts`) | the choices, their blockers and the option label, built on `routeBlocker` |
| `web/src/entities/audit-run/model/executor-refusal.ts` (+ `run-failure.ts`, `index.ts`) | the Russian wording of a refused executor choice; `classifyRunFailure` returns it before the generic provider sentence |
| `web/src/entities/audit-run/model/run-executor.ts`, `ui/run-row.tsx` | the executor of a run in words; the run list row |
| `web/src/widgets/run-progress/ui/run-progress.tsx` | the «Исполнитель» row and the waiting line on the run page |
| `web/src/entities/execution/model/presentation.ts` | the journal label |
| `web/src/features/start-run/model/start-run-intent.ts`, `model/use-start-run.ts` | the request and intent; the mutation sends the body built from the command |
| `web/src/features/start-run/ui/executor-select.tsx`, `ui/start-run-failure.tsx`, `ui/start-run-control.tsx`, `index.ts` | the select (presentational view + the control that holds the choice); the failure block moved out so a settled refusal is renderable by the static instruments |
| `web/tests/unit/start-run/*` (3 files), `tests/unit/run/run-executor.test.ts`, `tests/unit/execution/journal-executor-chosen.test.ts` | new tests (64) |
| `web/tests/guards/rendered-language.guard.test.ts` | renders the control and the refusals in every cache state; seeds an executor on every run and an `executor_chosen` journal entry |
| `web/tests/guards/gender-agreement.guard.test.ts` | judges the 18 refusal sentences (a cold route render never reaches them) |
| `web/tests/unit/screens/forms-and-pages.test.ts` | the claim «no provider-mode selector» now reads «exactly one select, the executor's, naming no mode» |
| `web/tests/unit/run/input-budget.test.ts`, `tests/unit/sections/run-refusal.test.ts` | they rendered the control without a `QueryClient`; the control now reads the connection list, so they provide one. Assertions unchanged |
| `web/tests/unit/analysis-settings/live-render.ts` | the shared minimal DOM had no `select.options`, which React reads when it sets a select's value; it now answers with the direct `<option>` children. Found by the full battery, not by the files I had run |

Not touched (measured below): `contracts/**`, `web/src/shared/**`, `web/FRONTEND_LOCK.json`, `web/package*.json`,
`web/src/app/**`, `web/src/_app/**`, `src/**`, `db/**`, `infra/**`, `web/src/features/start-ar-v3-group/**`,
`docs/program/CURRENT_STATE.md`, any `.css`.

## Commands and results

All from the worktree, `nice -n 19`, one at a time, no edit while one ran. `df -h /`: 2.6 GiB free at start,
2.5 GiB at the end (floor 1.5 GiB never approached). `node_modules` is the shared read-only link; no install.

| Command | Result |
|---|---|
| `npm --prefix web run typecheck` | exit 0, no output beyond the banner |
| `npm --prefix web run lint -- --quiet` | exit 0, no output |
| `npx vitest run` in `web/` (whole battery, final code tree `9d7764dc`) | **199 files, 3017 tests passed, 0 failed**, 207 s. Base figure in `CURRENT_STATE.md`: 2952 in 194 files; this lane adds 5 files and 65 tests |
| `npx vitest run tests/guards` (before the last two commits) | 21 files green except the one finding the loading label unreached, then fixed; the final battery above runs all guards |
| `node web/scripts/generate-api-client.mjs --check` | OK, 104 operations, sha256 `664a9069…a25af` (client untouched) |
| `git diff --check 4c5bd6cd..HEAD` | exit 0 |
| `git diff --stat 4c5bd6cd..HEAD -- contracts src web/src/shared web/FRONTEND_LOCK.json web/package.json web/package-lock.json web/src/app web/src/_app web/src/features/start-ar-v3-group docs/program/CURRENT_STATE.md db infra` | empty |

The guards that apply (`rendered-language`, `gender-agreement`, `lazy-boundary`, `eslint-boundary`,
`frontend-lock`, `server-credential`, `dashboard-invalidation`, the no-second-polling-loop block of
`tests/unit/run/polling.test.ts`, the CSS census in `tests/unit/styles`) are in the battery and pass without
being edited to pass; the two guard files that were extended only add states and sentences to render.

## Mutation table

Each row: one change to the named file, the named test files run, the result, then `git checkout -- <file>`;
`git status --short` and `git diff --stat` were empty after every row (the runner printed them).

| Guard | One mutation | Red |
|---|---|---|
| selector exists | remove `<ExecutorSelectView>` from the control | 10 tests in 3 files (`executor-select`, `executor-refusal`, `forms-and-pages`) |
| no provider-mode choice | add `<option value="live">` to the select | 1 (`forms-and-pages`) |
| choice is sent | `startRunBody` returns only `version_uid` | 2 |
| choice is sent | the command drops `executorConnectionId` | 2 |
| default is absence, not `null` | the default body gains `executor_connection_id: null` | 2 |
| key follows the choice | signature ignores the executor | 2 |
| control uses that signature | `useIntentKey(\`start-run:${versionUid}\`)` | 2 |
| control sends that command | `mutate({ versionUid, idempotencyKey })` | 1 |
| control never moves the choice | `onError: () => setChosen(null)` | 1 |
| refusal offers nothing | a link «Запустить на исполнителе по умолчанию» in the failure block | 1 |
| refusal offers nothing | the wording says «Запустите прогон на исполнителе по умолчанию» | 2 |
| refusal is its own state | `classifyRunFailure` skips `executorRefusal` | 8 |
| only the executor's dependency | every `dependency_unavailable` read as the executor's | 1 |
| only the executor's field | every `validation_failed` read as the executor's | 1 |
| rejected identifier has no retry | `presentation: 'error'` for it | 1 |
| no reason it was not told | a reason sentence when none was named | 1 |
| one readiness rule | choices ignore `routeBlocker` | 5 |
| archived not listed | every connection listed | 1 |
| chosen choice stays visible | the «больше не в списке» option dropped | 1 |
| list failure is said | the failed branch removed | 1 |
| loading is said | the loading state removed | 1 |
| select held while in flight | `disabled` removed | 1 |
| journal label | `audit_run.executor_chosen` removed | 2 |
| run row names the executor | the row's line removed | 3 |
| run page names the executor | the `<dt>/<dd>` removed | 1 |
| run page waits | the waiting line removed | 1 |
| queued waits | `waiting: false` | 4 |
| nothing invented | placeholder «не указан» for a run with none | 4 |
| language guard sees the new text | label `Executor` and an English refusal title | 2 (`rendered-language`) |
| gender guard sees the refusals | «Такой исполнителя» | 1 (`gender-agreement`) |

## Not run, with the reason

- **The browser journey** (`npm --prefix web run e2e:pc01`) and any stand: not run. The frontend battery renders
  static markup and one minimal DOM; it cannot see a click on a real select, a layout, or the choice surviving a
  real refusal. The select's `onChange`, the retry button's behaviour and the visual result are therefore
  **unproven in a browser**. The wiring of `onChange` → `setChosen` → `mutation.reset()` and of the key and
  command to one intent is pinned by reading the control's source, not by pressing anything.
- `next build`, `make gate`, database and container suites: not run (host disk; the task asks for none).
- No real refusal from a running backend was read: the wording rests on `executors/resolver.py:128` and the
  `EXEC-PAR-START-01` note, and on envelopes built by hand in the tests.
- The visual spacing of the new `am-form` wrapper was not looked at.

## Risks and known limits

- **Environment source.** A stand on the environment source has no freezer; a named connection is refused
  there (`EXEC-PAR-START-01`, call 4), without a reason word. The select still lists connections, because the
  UI cannot know the source, so a choice on such a stand ends in the refusal sentence without a cause. The
  queue slice's note already says a named executor needs `AUDITMANAGER_PROVIDER_SOURCE=database`.
- The re-audit of a named run can be refused for the same reason from the queue's command; that path
  (`entities/execution/model/failure.ts`) still prints the generic `dependency_unavailable` sentence. Out of
  scope here (the task owns the start), and cheap to add with `executorRefusal` if wanted.
- `RunExecutor.display_name` is the connection's current name, so a renamed connection shows its new name on
  old runs (`EXEC-PAR-START-01`, risks).
- N+1 reads: each page that draws the control reads the list and one detail per live connection.
- The select shows what was read when the page was last focused; a connection that became unusable since is
  refused by the server, which is the case the refusal block is for.
- A pre-existing React warning (`Cannot update a component (VersionRunList) while rendering … StartRunControl`)
  appears once in `run-list-ar-v3-live.test.ts`; measured the same with the base control, so it is not this lane's.

## Integration note

1. Merge `agent/exec-par-web-01` after `integration/exec-par-1026` (it needs `StartRunRequest.executor_connection_id`
   and `RunStatus.executor` from the regenerated client); `docs/program/CURRENT_STATE.md` is the integrator's and
   still says the selector is not built.
2. Nothing to regenerate, no lock, no dependency, no CSS. Expect the added tests only: `web` battery 199 files /
   3017 tests on `9d7764dc`.
3. Operator check on a stand with `AUDITMANAGER_PROVIDER_SOURCE=database`, `AUDITMANAGER_WORKER_SLOTS=4`, two
   probed connections and two documents: choose a different executor for each, start both, see both runs name
   their executor and the second for a busy executor say «Ждёт исполнителя «…»»; archive a connection after
   choosing it and press start to see the refusal.
4. Rollback: leave the select on «По умолчанию (маршрут)» (the request is today's) or revert the lane's commits.
