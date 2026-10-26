# Task EXEC-PAR-WEB-01 — choose the executor of a run in the UI, and see it

task_id: EXEC-PAR-WEB-01

## Outcome

The person who starts a run sees an «Исполнитель» selector in the start control: «По умолчанию
(маршрут)» and the connections that can serve a run now. The choice is sent as
`executor_connection_id` (omitted for the default). The run list and the run page name the
executor of every run that has one. A queued run says which executor it is waiting for. A refused
start says that the chosen executor cannot serve now and offers no other executor and no default.

## Depends on

- `EXEC-PAR-START-01` — merged on this base (the generated client carries
  `StartRunRequest.executor_connection_id` and `RunStatus.executor`).
- `EXEC-PAR-QUEUE-01` — merged on this base (no UI dependency; the waiting state is only worded here).

## Frozen inputs

- base commit: the tip of branch `integration/exec-par-1026` (both slices merged, `CURRENT_STATE.md` updated);
- shared contract `1.6.0`, API 92 paths / 104 operations / 301 schemas; the web client is generated
  and **must not be edited by hand**;
- `docs/program/EXEC-PAR-DECISION-01.md`, `docs/program/dispatch/EXEC-PARALLEL-RUNS-PLAN.md`,
  `docs/program/EXEC-PAR-START-01.md` (the refusal shape and the `executor` field).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the generated client already carries the choice and the executor of a run
- captured_at: 2026-10-26
- command: `grep -n -e "export type RunExecutor" -e "executor_connection_id" web/src/shared/api/generated/types.gen.ts`
- captured_output:
  ```text
  2577:export type RunExecutor = {
  3178:  executor_connection_id?: ExecutorConnectionId;
  ```
- interpretation: the UI work needs no contract change; `RunExecutor` is
  `{ connection_id, display_name, pin_id }` and `RunStatus.executor` is optional and nullable.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

The lane commits to its own branch only. It does not merge, push or tag.

## Allowed paths

Derive the exact set from the tree; record every path beyond these, with its reason, in the report.

- `web/src/features/start-run/**`
- `web/src/entities/audit-run/**`
- `web/src/entities/execution/**` (the label of the event `audit_run.executor_chosen`)
- `web/src/entities/executor-connection/**` (reuse the readiness logic; add only what the selector needs)
- `web/src/widgets/run-list/**`, `web/src/widgets/run-progress/**`
- `web/tests/unit/**` and `web/tests/guards/**` files that cover those paths or pin their texts
- `docs/program/tasks/EXEC-PAR-WEB-01.md`, `docs/program/EXEC-PAR-WEB-01.md`

## Forbidden hotspots

- `contracts/**`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`, `web/package.json`,
  `web/package-lock.json`, global styles, the composition root, `db/migrations/**`, `src/**`;
- `web/src/features/start-ar-v3-group/**` (the AR v3 group is not in this release);
- `docs/program/CURRENT_STATE.md`, refs, tags, the stand.

## Non-goals

No choice for the AR v3 group, no «Повторить прогон» selector (a repeat keeps the executor and the
page may say so), no administration of connections, no new route or screen, no polling of its own
(the no-second-polling-loop guard stands), no UI library: own module CSS with the `--am-*` tokens
and the repository's CSS census rules. No English or code identifiers in rendered text.

## Work

1. **Selector.** In the start control add a labelled select. Options: «По умолчанию (маршрут)», then
   each connection that can serve a run now, by the repository's own readiness logic in
   `entities/executor-connection` (served kind, current revision probed ok, not archived) — do not
   invent a second definition. Show kind, the pinned model and the last probe state beside the name.
   A connection that cannot serve is listed disabled with its reason in Russian, or not listed; say
   which and why in the report. Read the list with the existing hook; reads are open to every role.
2. **Intent key.** The start's idempotency key must change with the choice (same version, another
   executor, is another intent), as the contract treats the choice as part of the request.
3. **Refusal.** A `dependency_unavailable` whose `dependency` is `executor_connection`, and a
   `validation_failed` on `executor_connection_id`, are rendered as themselves in Russian
   («Выбранный исполнитель сейчас не может выполнить прогон…»), with a retry under the same key and
   **no** offer of another executor or of the default route.
4. **Run list and run page.** Show `RunStatus.executor.display_name` and its pinned model where the
   run has one; show nothing invented where it is absent. A run in the queue states «Ждёт исполнителя
   «…»». The journal label for `audit_run.executor_chosen` is «Выбран исполнитель».
5. **Texts.** Russian, in the repository's rendered-language style (the gender-agreement and
   rendered-language guards apply).

## Deliverables

The selector, the labels, the tests, and the report `docs/program/EXEC-PAR-WEB-01.md` (changed files
with reasons, commands and results, the mutation table, what was not run, the integrator's note).

## Required tests

- Setup: `web/node_modules` is a symlink to `/root/projects/PDF-Analysis/.local/worktrees/gate-night/web/node_modules`
  (the same lockfile; created for you). **Do not run `npm ci` or `npm install`**, and do not write
  through that link.
- command: `npm --prefix web run typecheck`; expected: exit 0.
- command: `npm --prefix web test -- --run` on the test files you add or change, plus every file in
  `web/tests/guards/`; expected: pass. If the whole battery is feasible within the host's limits, run it
  once and report the number; if not, say so.
- command: `npm --prefix web run lint` if the repository has it, on the changed paths; expected: pass.
- component tests that fail when the selector is removed, when the choice is not sent, when the
  intent key ignores the choice, and when the refusal offers a fallback.
- command: `git diff --check`; expected: exit 0.

## Integration contract

The UI sends `executor_connection_id` only when a connection is chosen, never the default. It never
renders a key, an address or a token. It reads connections through the existing hook and adds no
request of its own for the waiting state.

## Failure/idempotency/security cases

- the connection list fails to load: the selector says so and the default start still works;
- the chosen connection becomes unusable between choosing and starting: the start is refused, the
  page keeps the choice visible and offers a retry, nothing else;
- a run with no `executor` (the environment source): no label, no placeholder claiming one.

## Rollback / feature flag

Omit the selector's value: the request is today's. Revert the lane's commits to remove the UI.

## Handoff

changed files with reasons; commands and results; the mutation table; what was not run (the browser
journey — the frontend battery cannot see it; say so); the instruction to the integrator; proof the
forbidden hotspots are untouched.

## Result (recorded by the lane)

Done on branch `agent/exec-par-web-01`; report: [`../EXEC-PAR-WEB-01.md`](../EXEC-PAR-WEB-01.md). Every path the
lane touched is inside the allowed list above; the report names each with its reason. Two judgement calls differ
from the wording of this file and are stated there: a connection that cannot serve is listed disabled with its
reason (archived ones are not listed), and a retry is drawn exactly when the envelope says the failure is
retryable, so a rejected identifier (`validation_failed`) carries none.
