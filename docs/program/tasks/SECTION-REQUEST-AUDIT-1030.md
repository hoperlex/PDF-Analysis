# Task SECTION-REQUEST-AUDIT-1030 — проверка форматов и лимитов анализа разделов

## Outcome
Все 15 разделов формируют локально валидные запросы; OpenAI-совместимый `strict` маршрут принимает схему шести профилей с `documentation`. Действующие лимиты перечислены явно.

## Depends on
- AR-COST-PORTAL-STAMP-1030 (завершена и включена в `origin/dev`)
- BLOCK4-INT-1030 (опубликована в `origin/dev`; новый лимит обзорных вызовов)

## Frozen inputs
- Domain/API contracts: без изменений; API `1.14.0`.
- Analysis contracts: текущие профили `text-profile/1` и `text-profile/2`, без изменения идентичностей и хэшей.
- Migration head: `0043_stage_ai_generations`, без изменений.
- Base commit: `0dd8132806086044b9815842ef0cbf20eef34acc`.

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- Локальный проход через registry загрузил 15 профилей. Проверка конвертации запросов для стандартного и повышенного режимов прошла 30/30; старый тест ожидал 14 профилей.
- В `text.prompt.response_schema_for` поле `omission` необязательно у шести профилей, а `text.proxy._to_openai_body` отправляет схему с `strict: true`. [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) требует все свойства объекта в `required` и предлагает `null` для необязательного значения.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/analysis/text/proxy.py`
- `src/auditmanager/analysis/text/response.py`
- `tests/unit/analysis/text/test_wire_schema_text_transports.py`
- `tests/unit/analysis/test_omission_check.py`
- `docs/program/tasks/SECTION-REQUEST-AUDIT-1030.md`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, composition root, root dependencies/lockfiles, global styles, `origin/main`.

## Non-goals
- Снятие ресурсных и денежных ограничений, смена провайдера, изменение замороженных профилей и уже принятых запросов.

## Deliverables
- Транспортная strict-схема, допустимый разбор `omission: null` для иных категорий, целевые тесты и перечень фактических лимитов в handoff.

## Required tests
- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/analysis/text/test_wire_schema_text_transports.py tests/unit/analysis/test_omission_check.py tests/unit/analysis/text_profiles/test_text_profile_packages.py`
- `git diff --check`

## Integration contract
- Канонический запрос, checksum, хэши профилей и API не меняются. В OpenAI-совместимом провайдере все поля strict-схемы обязательны; `omission: null` эквивалентно отсутствующему claim для недокументальных категорий. Для `documentation` нужен полный claim.

## Failure/idempotency/security cases
- Неизвестная категория, неполный claim и непустой claim вне `documentation` отклоняются локальным валидатором. Исправление не добавляет модельных вызовов и не увеличивает согласованную стоимость.

## Rollback / feature flag
- Откат dev-коммита возвращает прежнюю транспортную схему. Нового флага нет.

## Handoff
- changed files: перечисленные в Allowed paths.
- commands/results: 217 passed, 1 skipped в целевом наборе с `AUDITMANAGER_EXTENDED_ANALYSIS_PLAN=v2`; Python compile и `git diff --check` прошли. Однократная локальная проверка формы 15 профилей × 2 режима прошла 30/30; реальный провайдер не вызывался.
- contracts: без изменений.
- known limits: лимиты **не сняты**. Обычный запрос: 16 000 output tokens, повышенный: 64 000; провайдер может ограничить сильнее. На PDF: не более 500 страниц, 200 000 символов/страницу и 20 млн/документ. Без свежего согласия старый путь ограничен 12 текстовыми окнами; свежая оценка сохраняет `max_windows` вплоть до числа страниц. На расширенный обзор: до 1000 визуальных источников, 16 источников/окно, 63 окна, 900 КБ/request. Свежий `batched-v1` бронирует до 154 дополнительных вызовов/окно: 2 визуальных, до 128 обзорных по размеру текста, по 8 нормативных, критических и исправляющих; `batched-fixed-v1` оставляет прежние 30. Это потолки, не обещание полного покрытия. Транспорт SSH дополнительно ограничен 24 МиБ (48 МиБ с несколькими изображениями) на задание и 2 МиБ на ответ. Для оплачиваемого маршрута свежий запуск требует подтверждённый digest оценки и лимит стоимости не ниже оценки; цена каждого вызова проверяется до и после ответа. Исторические команды с `relaxed_limits` без нового согласия сохраняют прежнюю политику без денежной остановки; неизменные принятые команды не переписываются.
- integration notes: только `origin/dev`; проверка живого провайдера отдельно.
