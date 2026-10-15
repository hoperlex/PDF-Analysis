# CODE-FIRST-INT-01 — плановый вход в кодовую серию

## Результат

Интеграционный кандидат собран от `origin/dev=6d63802ab465a0317839c9b57abd5e90f3d91769`:
включены plan `ca44d074` и подготовка W56a `191fbb36`, записаны R-135/R-136.
План `dispatch/CODE-FIRST-TO-BETA.md` задаёт W56a–W63 как кодовую очередь и
переносит полный gate после её завершения. `W56A-FREEZE-01` остаётся
остановленным историческим preflight; R-136 разрешает новый recorded-only
freeze с отдельным владельцем `P02_LOCK.json`.

## Изменённые файлы

- Точные документационные файлы двух исходных веток перечисляются командой
  `git diff --name-only 6d63802a..45eb9756` и закреплены merge-коммитами
  `d66abc75`, `45eb9756`.
- Этот интеграционный слот дополнительно меняет `AGENTS.md`,
  `docs/program/CURRENT_STATE.md`,
  `docs/program/OWNER_RULINGS_2026-09-17.md`,
  `docs/program/dispatch/W56-PLAN.md`,
  `docs/program/tasks/CODE-FIRST-BETA-01.md`,
  `docs/program/tasks/CODE-FIRST-INT-01.md` и этот отчёт.

## Проверки

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q
  -p no:cacheprovider tests/contract/api_v1/test_doc_prose_facts.py
  tests/contract/api_v1/test_surface_counts_in_prose.py
  tests/contract/program/test_wave_governance.py` — **93 passed**.
- `git diff --check` — exit 0; после коммита проверить весь diff от W55b.
- `git ls-remote origin refs/heads/dev` перед публикацией —
  `6d63802ab465a0317839c9b57abd5e90f3d91769`. После коммита
  повторить проверку и push с точным lease, затем read-back remote ref.
- Полный локальный `make gate`, стендовая приёмка, live model call и
  `origin/main` не запускались по R-135.

## Contracts и ограничения

API, domain, analysis contracts, migration head, root dependencies/locks,
composition roots, global styles и runtime/UI/test code не меняются этим
кандидатом. W56a gateway по-прежнему возвращает неподтверждённую модель;
`W56A-PROBE-01` остаётся FAIL, а `R-133` действует. W58–W63 ещё требуют
собственных freeze и task-файлов; этот план не является их write grant.

## Передача интегратору

После read-back `origin/dev` открыть `W56A-DEV-FREEZE-01` на точном новом
SHA, назначить SEAL и GENERATOR непересекающиеся пути. Для последующих
волн создавать task-файлы от закрытых предшественников, без преждевременного
полного gate. Публикация в `origin/main` не разрешена этим слотом.

## Доказательство forbidden hotspots

`git diff --name-only 6d63802a..HEAD` на закрытом кандидате содержит
только перечисленные документационные пути и `AGENTS.md`. Контрактные,
миграционные, кодовые, lock/deploy пути и `origin/main` не затронуты.
