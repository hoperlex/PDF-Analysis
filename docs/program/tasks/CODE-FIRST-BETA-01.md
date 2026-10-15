# Task CODE-FIRST-BETA-01 — зафиксировать кодовую очередь до beta

## Outcome

На свежем `origin/dev` существует один план, который перечисляет весь остаток
кода до beta, переносит полные гейты после последнего кодового блока и
исключает из текущей очереди приёмку, стендовые live-прогоны и `origin/main`.
Действующий roadmap и планы W56/W57 ведут к этому уточнению.

## Depends on

- нет; W55b уже закрыта на базовом `origin/dev`.

## Frozen inputs

- domain contract: candidate revision 12 на `6d63802a`;
- API contract: 47 paths / 54 operations / 123 schemas, 24 error codes;
- analysis/comparison/event contract: W55b, без изменений этой задачей;
- migration head: `0021_portal_bundles`;
- base commit: `6d63802ab465a0317839c9b57abd5e90f3d91769` (`origin/dev`);
- owner instruction: сначала обновить план, полный локальный gate не запускать;
  затем код до beta, потом полные гейты, приёмку и `origin/main` сейчас не
  выполнять.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

План перечисляет будущие блоки, не изменяя реестр операций, экранов, ошибок
или миграций в коде.

## Captured premise evidence

### P-01 — база планирования

- captured_at: 2026-10-15
- command: `git rev-parse HEAD`
- captured_output:
  ```text
  6d63802ab465a0317839c9b57abd5e90f3d91769
  ```
- interpretation: плановый worktree создан от закрытой линии W55b;
  строка не утверждает, что эта версия развёрнута.

### P-02 — W58–W63 остаются планом, а не dispatch

- captured_at: 2026-10-15
- command: `git show 6d63802ab465a0317839c9b57abd5e90f3d91769:docs/program/dispatch/ROADMAP-TO-BETA.md | rg -n 'neither reviewed nor adopted'`
- captured_output:
  ```text
  637:| K-4 | the uncommitted 2026-10-08 planning layer found in the `plan-roadmap-to-beta` worktree (author unknown) | **preserve it and use it as the base**. It is preserved verbatim in `97127ac` on `plan/corpus-chain`. It is used for W54–W57 only; its W58–W64 plans and the beta move to W63 are neither reviewed nor adopted by this revision. |
  ```
- interpretation: будущие кодовые task-файлы требуют собственного freeze и
  точного path ownership; эта задача не выдаёт им write grant.

### P-03 — W56a gateway stop

- captured_at: 2026-10-15
- source: `integration/w56a` `e8aba916`,
  `docs/program/W56A-FREEZE-01.md` и
  `docs/program/reviews/W56A-MODEL-REQUIREMENT-REVIEW-01.md`;
- interpretation: model identity probe провалился; review рекомендует
  recorded-only development freeze и отдельный `MODEL-PIN`. Это основание
  для безопасной очередности, не свидетельство исправленного gateway.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

Исторические планы и отчёты сохраняются; новые указатели устанавливают
приоритет нового порядка, не исправляют задним числом результаты проверок.

## Publication authority

- development_target: none
- origin_main_authority: none

Эта задача не публикует refs. Будущие кодовые integration tasks могут иметь
`origin/dev` как development target; `origin/main` не разрешён.

## Allowed paths

- `docs/program/tasks/CODE-FIRST-BETA-01.md`
- `docs/program/dispatch/CODE-FIRST-TO-BETA.md`
- `docs/program/dispatch/ROADMAP-TO-BETA.md` — только верхний указатель
- `docs/program/dispatch/W56-PLAN.md` — только верхний указатель
- `docs/program/dispatch/W57-PLAN.md` — только верхний указатель

## Forbidden hotspots

- `contracts/**`, domain/error catalogue and generated client;
- `db/migrations/**`, migration head;
- root dependencies/locks, composition roots and global styles;
- runtime, UI, tests, scripts, deployment, `CURRENT_STATE.md`,
  `DEBT_REGISTER.md`, refs and tags.

## Non-goals

- no implementation, full local gate, live/paid call or acceptance;
- no `origin/main` publication or beta tag;
- no weakening of B1–B12 or R-133 model identity requirement;
- no claim that W58–W63 are already frozen task grants.

## Deliverables

- code-first plan and three pointers in the current planning documents;
- this task definition with the frozen starting point and handoff.

## Required tests

- `git diff --check` — no whitespace errors;
- changed-path inspection — only the five allowed documentation files;
- inspect roadmap B1–B12, W56/W57 order and W55b state for internal
  consistency. No full `make gate` in this planning task.

## Integration contract

The integrator may use `CODE-FIRST-TO-BETA.md` to create new freeze and task
files on the then-current `origin/dev`. Every implementation task needs exact
`allowed_paths` and independent owners for contracts, migration head, locks,
composition root and global styles. No future block is dispatched by this
planning task alone.

## Failure/idempotency/security cases

- A stale base or conflicting newer owner instruction requires a new plan
  revision before implementation grants.
- A failed gateway probe cannot be converted into a model pin or a green gate.
- Reapplying the planning change must not rewrite historical test evidence.

## Rollback / feature flag

Documentation only; revert the five files. No feature flag or data rollback.

## Handoff

- changed files: the five paths in Allowed paths;
- commands/results: recorded in the planning completion response;
- known limits: W56a gateway remains blocked; W58–W63 need detailed freezes;
- integration notes: full gates occur after all beta code on a separate exact
  candidate; manual acceptance and `origin/main` are outside this task.
