# Task AR-COST-PORTAL-STAMP-1030 — оценка АР при штампах портального пакета

## Outcome
Оценка стоимости обычного анализа АР принимает действительный `stamp` блок портального пакета и считает только `image` блоки.

## Depends on
- CMP-PDF-SECTION-RUN-1030

## Frozen inputs
- domain contract: `contracts/domain/v1/**`, без изменений
- API contract: `contracts/api/v1/openapi.json` 1.14.0, без изменений
- analysis contract: `analysis.recognised.portal.BLOCK_TYPES = {text, image, stamp}`
- migration head: `0043_stage_ai_generations`, без изменений
- base commit: `6e2eb23b684e60801df2bffa340ac42a21a28b12`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- Пользователь получил `POST /bff/v1/runs/cost-estimate` 422 `analysis_input_invalid`, `details.stage_id=text_analysis`, `details.reason=cost_blocks_source_invalid` для `ver_01M660VPAJW3GX6ZZPZPC67D2R`.
- `runs.preflight._image_block_count` принимал только `image` и `text`, хотя утверждённый контракт портала принимает также `stamp`. Сообщение каталога ошибок ошибочно приписывало любому `analysis_input_invalid` причину `comparison_only_version`.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/runs/preflight.py`
- `tests/unit/runs/test_cost_preflight.py`
- `web/src/shared/api/catalog-message.ts`
- `docs/program/tasks/AR-COST-PORTAL-STAMP-1030.md`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, `src/auditmanager/bootstrap/**`, root dependency/lock files, global styles, `origin/main`

## Non-goals
- Изменение байтов портального пакета, обход проверки размера/hash или структуры блоков, OCR и другие виды анализа.

## Deliverables
- Учёт `stamp` как допустимого блока без цены изображения; целевой тест; корректный общий текст ошибки без ложной причины.

## Required tests
- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runs/test_cost_preflight.py -k 'portal_stamps or comparison_zip_pdf'`
- `cd web && npm run typecheck && npm run build`
- `git diff --check`

## Integration contract
Форма API и хранилища не меняется. `stamp` не создаёт модельный image input и не увеличивает цену. Неверный тип блока и неверные сохранённые байты остаются отказом.

## Failure/idempotency/security cases
- Оценка остаётся read-only; согласие и запуск не меняются. Ответ 422 для иных недействительных пакетов сохраняется.

## Rollback / feature flag
Откат dev коммита возвращает прежний отказ. Нового флага нет.

## Handoff
- changed files: перечисленные выше.
- commands/results: 2 целевых теста прошли; 16 тестов `test_cost_preflight.py` прошли с явным `AUDITMANAGER_EXTENDED_ANALYSIS_PLAN=v2`; целевой тест отдельно проверил v3. TypeScript typecheck, production web build, Python compile и `git diff --check` прошли. Общий запуск без явного режима нашёл старое ожидание `max_blocks="all"` при текущем v3 default; это не отказ новой проверки.
- contracts: без изменений.
- known limits: без доступа к blob версии на стенде нельзя доказать, что именно `stamp` был его единственной проблемой; после публикации повторить оценку на той же версии.
- integration notes: только `origin/dev`; main/развёртывание требуют отдельного указания.
