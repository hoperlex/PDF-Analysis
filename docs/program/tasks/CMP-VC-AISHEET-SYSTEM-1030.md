# Task CMP-VC-AISHEET-SYSTEM-1030 — запуск ИИ-описания листа через SSH и pull

## Outcome
Запросы «Описать этот лист…» для парных и односторонних листов проходят проверку формата SSH и pull исполнителей.

## Depends on
- CMP-VC-AISHEET-01

## Frozen inputs
- domain contract: `contracts/domain/v1/**`, без изменений
- API contract: `contracts/api/v1/openapi.json` 1.14.0, без изменений
- comparison contract: `CMP-VC-AISHEET-01`, модельный запрос и его content key
- migration head: `0043_stage_ai_generations`, без изменений
- base commit: `10099a4e`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: `ai_sheets.describe.build_request` не задаёт `system`; `executors.ssh_adapter._task` и `executors.pull._task_payload` требуют его и отвергают запрос до вызова модели. Независимое воспроизведение выполнено на base commit.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/ai_sheets/describe.py`
- `src/auditmanager/comparison/ai_sheets/method.py`
- `src/auditmanager/comparison/ai_sheets/schema.py`
- `tests/unit/comparison/ai_sheets/test_packet.py`
- `tests/unit/comparison/ai_sheets/test_schema_keys_and_material.py`
- `tests/integration/comparison/ai_sheets/test_reads_and_steering.py`
- `tests/integration/comparison/ai_sheets/test_series_run.py`
- `docs/program/tasks/CMP-VC-AISHEET-SYSTEM-1030.md`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, `src/auditmanager/bootstrap/**`, `src/auditmanager/executors/**`
- root dependency and lock files, global styles, `web/**`, `origin/main`

## Non-goals
- смена маршрута исполнителя или конфигурации сервера; исправление остальных видов сравнительного ИИ

## Deliverables
- Непустой постоянный `system` в запросе листа и в расчёте стоимости; новая версия и digest подсказки, чтобы не переиспользовать старый content key.
- Проверка формата запроса для обеих схем через SSH и pull адаптеры.

## Required tests
- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/comparison/ai_sheets/test_packet.py tests/unit/comparison/ai_sheets/test_schema_keys_and_material.py`
- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/comparison/ai_sheets`
- `PYTHONPATH=src .venv/bin/python -m compileall -q src/auditmanager/comparison/ai_sheets`

## Integration contract
Формат ответа и API не меняются. Начатое ранее задание сохраняет старый frozen prompt; новый запуск получает `sheet-changes/2` или `sheet-single/2` и новый digest.

## Failure/idempotency/security cases
- Ошибка обязательного `system` исчезает до отправки. Неизвестный результат вызова по-прежнему не повторяется автоматически.

## Rollback / feature flag
Откат dev коммита возвращает прежнее поведение. Модульный флаг `AUDITMANAGER_COMPARISON_MODULES` сохраняется.

## Handoff
- changed files: этот task и семь разрешённых файлов кода и тестов.
- commands/results: 24 focused and 104 module unit tests passed; `compileall` and `git diff --check` passed. Integration tests require a running test database and were not run for this hotfix.
- known limits: фактический live вызов модели зависит от настройки стенда; этот тест проверяет формат до передачи модели.
- integration notes: публиковать только в `origin/dev`; `origin/main` требует отдельного указания владельца.
