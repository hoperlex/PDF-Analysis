# Task EXEC2-WEB-WIZARD-01 — «Добавить подключение»: remote Ubuntu agent (A or B) or API provider, one lifecycle, moving an agent

## Outcome
«Добавить подключение» offers two cards: «Удалённый Ubuntu-агент» or «API-провайдер». Choosing the agent shows two equally prominent cards, A «Установить по SSH» and B «Выполнить команду на Ubuntu». Both lead to one lifecycle: ожидает регистрации → агент в сети → CLI найден → вход действителен / нужен вход → проба пройдена → готово. Errors are in Russian. OpenRouter is a prefilled `http_api` form. «Перенести на другой сервер» issues a new enrollment for an existing agent connection.

## Depends on
- EXEC2-INT-1

## Frozen inputs
- domain contract: unchanged
- API contract: 1.15.0, frozen by `EXEC2-SEAL-1`
- analysis/comparison/event contract: unchanged
- migration head: `0046`, created by `EXEC2-SEAL-1`; this task adds no migration
- base commit: `integration/exec2` after `EXEC2-INT-1` is on `origin/dev`
- architecture: `docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md` decisions 4–9; plan `docs/program/dispatch/EXEC2-PLAN.md`; rulings `R-149a`…`R-149f`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the workers screen has three tabs and the connection form lives in its feature

### P-01 — the workers screen tabs
- captured_at: 2026-11-02
- command: `git grep -n 'WORKERS_TABS = ' origin/dev -- web/src/_pages/workers/model/tabs.ts`
- captured_output:
  ```text
  origin/dev:web/src/_pages/workers/model/tabs.ts:13:export const WORKERS_TABS = ['connections', 'processes', 'routes'] as const;
  exit=0
  ```
- interpretation: the wizard is a dialog in «Подключения», not a fourth tab.

The integrator re-runs every premise command on the actual base before dispatch (`EXEC2-PLAN.md` section 6) and corrects line numbers; a premise that no longer holds stops the dispatch.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `web/src/features/connect-remote-agent/**`
- `web/src/features/manage-executor-connection/**`
- `web/src/widgets/executor-connections/**`

## Forbidden hotspots
- `contracts/**`, generated models and client, the migration head, root dependency/lock files and global styles (owned by the stage's SEAL task)
- `src/auditmanager/shared/errors/**`: EXEC-2 adds no error code (ADR-0026 decision 18)
- paths another EXEC-2 task owns in the same stage (`EXEC2-PLAN.md` section 5)
- `web/src/_pages/workers/**` (stage 3)

## Non-goals
- no ChatGPT or Claude passwords requested
- no SSH internals outside an optional details panel

## Deliverables
- The wizard, the copyable command with a «Новая команда» action, the four distinct statuses of decision 8 with official CLI login guidance and «Проверить снова».
- The integration-authorisation mark (`R-149b`).
- The OpenRouter preset (base URL, `openai_chat`, pinned model, key).
- The «Перенести на другой сервер» flow.
- Component tests for B2 §11 items 6, 9 and 10.

## Required tests
- command: not run in EXEC-2 (`R-149d`); write the tests below and mark those that need PostgreSQL with the suite's existing database marker
- expected: B2 §11 tests 6, 9 and 10 exist as component tests

## Integration contract
- reads only the 1.15.0 generated client

## Failure/idempotency/security cases
- a shown secret is never re-displayed after the dialog closes
- an expired command shows «Команда устарела» and offers a new one

## Rollback / feature flag
UI only; revert the merge.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: generation commands run and their result; no test, build, typecheck, lint, database, browser or model run (`R-149d`)
- known limits: every acceptance test named above is unexecuted
- integration notes: what the next consumer of this task may rely on
