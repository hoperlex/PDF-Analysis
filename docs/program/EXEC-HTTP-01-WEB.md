STATUS: all pieces committed, R-144b checks green, report written (13:07 +05)

# EXEC-HTTP-01, web half: report (AGENTS.md section 5)

Branch `agent/exec-web-01`, based on `agent/exec-line-01` at `dfe5795a` (the EXEC-SEAL-01 contract with the
web client and `FRONTEND_LOCK.json` already regenerated, `7ab8ec15`). The lane touches `web/**` and this file only.
Acceptance is R-144b: lint, typecheck, vitest on the files added or changed plus `web/tests/guards` and
`web/tests/unit/workers`, `git diff --check`. No `next build`, no full suite, no live journey.

## What an administrator can do in «Исполнители» (/workers, no new route)

Three tabs, in the owner's order: «Подключения», «Процессы», «Назначения». The screen opens on «Процессы» (the
worker list, unchanged) unless the address says `?tab=`; the redirect from the key form says `connections`.

- **Подключения.** The list: kind, name, current settings, the key as a fact (last four characters, when, by whom;
  `secret_unreadable` is said in words), the latest probe as a Russian sentence, the state «готово к назначению» or
  the reason it is not. A notice of connection changes in the last seven days (creation, settings, keys, archive,
  routes), or a sentence saying there were none. An administrator also gets:
  - **Добавить подключение**: name, kind (HTTP API / команда по SSH / клиент забирает задания), and the first settings:
    address, request format, way of connecting (direct, VPN, SSH tunnel), model chosen from the pinned set (the rates
    are printed beside it) plus the gateway's own name for it, timeout, parallel calls, billing, documents of the
    client. Create then revise, each under its own idempotency key; a half-created connection (settings refused) is
    completed by the next press, never duplicated.
  - **Изменить настройки**: a new revision. The warning that a changed address, way of connecting or SSH endpoint
    leaves the key unreadable is shown while typing and after saving, with a link to the key form.
  - **Ввести ключ / Заменить ключ**: a link to `/workers?tab=connections&connection=<id>`; the route renders the key
    form on the server and the page places it above the list.
  - **Проверить**: records the probe; the card polls every 3 s while a probe is open and then names the outcome.
  - **Создать ключ** (SSH, also a tunnelled HTTP API): shows the public key and the `authorized_keys` line once with
    copy buttons; **Закрепить этот отпечаток** saves the host key a probe observed into a new revision.
  - **Архивировать** after a confirmation.
  An expert sees the list, the notice and the key facts, and no control.
- **Назначения.** The route for «Анализ текста»: primary, and a standby only if ticked or already configured. A
  connection is selectable only when its current settings have a finished `ok` probe on the current key; every other
  one is shown disabled with the reason beside it and again in a list below. The text says the standby is used only at
  run start and is never a retry. An expert sees the summary and no form.
- **Диспетчер.** «Исполнитель» became «ответственный» in the three rendered strings (assignment board column,
  assignment history line, the reassignment field).

## The secret form, and the new reserved BFF door

- `POST /bff/v1/executor-secret/<connection_id>` in `web/src/app/bff/v1/[...path]/route.ts` (`executorSecretDoor`,
  `setTheExecutorSecret`), shaped like `changeThePassword`: refuses a cross-site post (`isCrossSitePost`) before the
  session or the form is read; a post without a session goes to the sign-in screen and nothing is forwarded; reads the
  native form; fixes the purpose to `api_key`; forwards JSON to `setExecutorSecret` with the session's credential and
  the idempotency key the form carried; answers `303` to `/workers?tab=connections&connection=<id>&secret=<outcome>`
  with one of eight words (saved, validation, forbidden, not_found, conflict, unavailable, unconfigured, upstream).
  The key is in no header, body or address of the answer. A `401` ends the session.
- `features/set-executor-secret/ui/set-executor-secret-form.tsx` is a server component: no client directive, no
  handler, `type="password"`, `autoComplete="off"`, a hidden idempotency key minted when the page renders. Nothing under
  `web/src` calls `setExecutorSecret` and there is no hook for it (both asserted by test).
- Enumerator ownership: `grep -n "function .*Door\|_SEGMENT" 'web/src/app/bff/v1/[...path]/route.ts'` now also lists
  `EXECUTOR_SECRET_SEGMENT`, `executorSecretDoor`, `setTheExecutorSecret` and `reportSecret`. The slice report and the
  runbook should list the door (runbook edits are not this lane's).

## Changed files (reason)

- `web/src/app/bff/v1/[...path]/route.ts`: the door above.
- `web/src/app/workers/page.tsx`: renders the key form on the server and passes it, with the tab and connection read
  from a closed set of address parameters, to the page. **Not in the task file's allowed_paths list** (it names
  `_pages/workers` and `app/bff`), inside the caller's `web/**` grant; needed because only a route file receives
  `searchParams` and can hand a server-rendered element to a client page. The screen registry is untouched.
- `web/src/_pages/workers/**`: tabs (`model/tabs.ts`, `ui/workers-tabs.tsx`, `workers-page.module.css`); the page keeps its
  worker content inline so `intake-confirmation.test.ts`, which walks the returned tree, still passes unchanged.
- `web/src/entities/executor-connection/**`: reads (list, detail with polling while a probe is open, routes), the words
  (every enum value has a Russian label; every probe outcome a sentence), readiness (ok probe on the current key),
  destination hint, seven-day changes, refusal sentences from the safe detail keys.
- `web/src/features/manage-executor-connection/**`: commands (create, revise, archive, probe, SSH key, route), forms
  and controls, the pure settings reader, `useCommandKey` (one key per intent, held across an unknown outcome).
- `web/src/features/set-executor-secret/**`: the form and the closed outcome vocabulary.
- `web/src/widgets/executor-connections/**`, `web/src/widgets/executor-routes/**`: the two tabs.
- `web/src/entities/execution/model/presentation.ts`: `'connections'` joins the admin-only actions of `canExecute`.
- `web/src/shared/api/query-keys.ts`: `execution.connections/connection/routes`, under the existing root so one
  invalidation reaches them.
- `web/src/widgets/assignment-board/**`, `web/src/features/transition-assignment/**`: the wording.
- Tests: `web/tests/unit/workers/executor-{secret-door,connections,settings,commands,fixtures}.test.ts`,
  `workers-tabs.test.ts`; guards `rendered-language` (twelve Executor schemas translated with markers, eight Latin
  product names with reasons, new shapes) and `dashboard-invalidation` (two entries); `tests/unit/styles/screens.ts`
  (the new widgets reach the contrast census).

## Contracts

None changed. The generated client and `FRONTEND_LOCK.json` are as the contract commit left them.

## Checks run (all on the final tree)

See the end of this file for the commands and results.

## Guards shown failing under a mutation

Each applied to the tree, the named test run, the tree restored (`git status` clean after):

- form becomes `'use client'` -> `declares a client component` red; `type="password"` -> `text` -> red; `autoComplete="off"`
  -> `"on"` -> red.
- door without the cross-site refusal -> `refuses a post another site drove` red; door forwards `ssh_private_key` ->
  two tests red; door redirects with the key in the address -> five tests red.
- `canExecute` without `'connections'` -> three tests red (expert sees controls).
- readiness ignoring the secret the probe was taken on, and ignoring a key bound to the old address -> red.
- destination change not noticed -> two tests red; command hook with `retry: 3` -> red.
- default tab `connections` -> three of the existing page tests red.
- a probe outcome in English -> `rendered-language` two tests red; a mapped mutation hook un-mapped ->
  `dashboard-invalidation` red; an early `return` before `requireScreen` in the route -> `screen-guard` red.

## Risks and known limits

- **Journey manifest.** `tests/e2e/pc01/journey/manifest.json` and the conformance test are outside `web/**` and were not
  touched. «Исполнители» now reads `listExecutorConnections`, `getExecutorConnection` and `listExecutorRoutes` on its
  other two tabs and posts to the new door; the integrator must declare them (the default tab keeps the existing
  `listWorkers` step as it was).
- No `next build` was run: the hand-off of a server-rendered element to a client page and the `replaceState` that keeps
  the tab in the address are unproven in a browser. The key door, the form and the guards are proven by unit tests.
- The contract has no connection event list; the seven-day notice is rebuilt from creation, archive, secret and
  revision times and route times, and names the author by user id.
- `ssh_command` and `pull` can be created; a probe ends `kind_not_served` and the route editor lists them as not
  servable (non-goals of the task). Runner-token screens are not built.
- A probe polls every 3 s while open; a probe the server never closes would poll for as long as the tab is open (the
  server ends an untaken one at 120 s).
- Generated types make the generic JSON forward of `setExecutorSecret` reachable from any script; the UI never uses it
  and a test says so.

## Instruction to the integrator

Merge `agent/exec-web-01` after the contract lane. Declare the new operations on `/workers` in the journey manifest and
the new door in the slice report and runbook. Nothing here needs a migration or an environment change.

## Forbidden hotspots

`git diff --name-only dfe5795a..HEAD` lists only paths under `web/src`, `web/tests` and this file: no `contracts/**`, no
`db/migrations/**`, no dependency or lock file (`web/package*.json`, `web/FRONTEND_LOCK.json`), no `web/src/app/globals.css`,
no screen registry (`web/src/shared/config/screen-registry.ts`), no `norms/**`, `tools/**`, `CURRENT_STATE.md`.
