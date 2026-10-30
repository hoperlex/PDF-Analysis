# Task SECTION-STATS-UNCAPPED-1030 — временный режим сбора статистики без прикладных лимитов разделов

## Outcome
Новый прогон раздела в режиме `relaxed_limits` не отклоняется из-за общего числа текстовых окон, визуальных источников, обзорных пакетов или денежного потолка; расход и полнота по-прежнему записываются. Прикладные квоты размера PDF, страниц, ZIP и загрузки временно подняты до пределов представления данных. Существующие принятые прогоны сохраняют свою политику.

## Depends on
- SECTION-REQUEST-AUDIT-1030 (завершена в `origin/dev`)
- BLOCK4-INT-1030 (завершена в `origin/dev`)

## Frozen inputs
- API/domain/analysis contracts: исходный API `1.14.0`, портал `contracts/analysis/v1/portal-blocks.schema.json`; разрешённое согласованное расширение числовых пределов для новых данных.
- Existing `relaxed_limits` и `cost_consent` поля запроса; новых полей API нет.
- Migration head: `0043_stage_ai_generations`; этот task владеет слотом следующей миграции для удаления `ck_document_version_page_count`.
- Base commit: `c0dc430be081c750545a34ae110b1f21b383d3a2`.
- Integration base after `origin/dev` advanced: `f4d722e5420699a0846b559d1410b7b7b683cdc7`.

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `db/migrations/versions/**`
- enumerator_owner: SECTION-STATS-UNCAPPED-1030
- totality_query: `ls db/migrations/versions/*_004*.py`

## Captured premise evidence
- `SECTION-REQUEST-AUDIT-1030` установила действующие ограничения: 12/500 текстовых окон, 1000 визуальных источников, 63 окна обзора, 30–154 дополнительных вызова на окно и подтверждаемый денежный потолок.
- Пользователь прямо поручил временно снять ограничения на запросы, объёмы и стоимость для сбора статистики и уточнил, что это относится также к PDF и загрузке.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/analysis/extended/**`
- `src/auditmanager/analysis/stages/pdf_precheck.py`
- `src/auditmanager/analysis/stages/pdf_precheck_child.py`
- `src/auditmanager/analysis/text/**`
- `src/auditmanager/ingest/envelope.py`
- `src/auditmanager/ingest/bundle_archive.py`
- `src/auditmanager/ingest/bundle_envelope.py`
- `src/auditmanager/ingest/comparison_pdf/limits.py`
- `src/auditmanager/ingest/comparison_pdf/envelope.py`
- `src/auditmanager/ingest/comparison_pdf/child.py`
- `src/auditmanager/ingest/comparison_pdf/zip_import.py`
- `src/auditmanager/ingest/comparison_zip/**`
- `src/auditmanager/api/routers/multipart.py`
- `src/auditmanager/api/routers/comparison_uploads.py`
- `src/auditmanager/api/routers/ports.py`
- `src/auditmanager/api/routers/__init__.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/comparison/stage/limits.py`
- `src/auditmanager/comparison/stage/intake.py`
- `src/auditmanager/comparison/stage/uploads.py`
- `src/auditmanager/api/routers/comparison_stage_uploads.py`
- `src/auditmanager/api/schemas/models.py`
- `contracts/domain/v1/error-codes.json`
- `db/migrations/versions/**`
- `contracts/api/v1/openapi.json`
- `contracts/analysis/v1/portal-blocks.schema.json`
- `infra/deploy/**`
- `web/src/entities/document-version/**`
- `web/src/entities/version-series/**`
- `web/src/widgets/comparison-upload/**`
- `web/src/_pages/stage-compare/ui/stage-upload-panel.tsx`
- `web/src/_pages/stage-compare/model/hash.ts`
- `web/src/shared/lib/sha256-file.ts`
- `web/src/shared/api/credentialed-forward.ts`
- `web/src/shared/api/generated/**`
- `web/openapi/openapi.json`
- `web/src/features/upload-document/**`
- `web/tests/**`
- `src/auditmanager/runs/**`
- `web/src/features/start-run/**`
- `web/src/shared/ui/cost-approval/cost-approval.tsx`
- `tests/unit/analysis/**`
- `tests/unit/ingest/**`
- `tests/unit/comparison/stage/test_intake.py`
- `tests/integration/composition/test_proxy_tls_path.py`
- `tests/unit/runs/**`
- `tests/integration/runs/test_window_reply_custody.py`
- `web/tests/unit/cost-approval/**`
- `docs/program/tasks/SECTION-STATS-UNCAPPED-1030.md`

## Forbidden hotspots
- Другие контракты, другие миграции, root dependencies/lockfiles, global styles, `origin/main`, другие подсистемы сравнения. Перечисленные выше contract/migration/integration slots и узкая строка ZIP-адаптера в composition root принадлежат только этой задаче.

## Non-goals
- Отмена проверки целостности PDF/портальных данных, разрешений, привязки модели и источника, повтор неизвестно оплаченного вызова, изменение результатов эксперта и исторических команд.

## Deliverables
- Явная временная политика для новых прогонов разделов; правильный UI; узкие проверки; список оставшихся внешних технических пределов и команда отката.

## Required tests
- Целевые Python и web unit tests, Python compile, frontend typecheck и production build.
- `git diff --check`.

## Integration contract
Неограниченный по деньгам режим ИИ активируется только новым запросом `relaxed_limits=true`, показывается в UI и фиксируется в принятой команде. Числовые квоты PDF и загрузки временно подняты для всех новых загрузок. Изменение не переписывает старые согласия. Вызовы сохраняют idempotency и measured cost; неизвестный оплаченный исход останавливает повтор. Увеличенные PDF принимаются только после миграции и согласованного API/портального контракта.

## Failure/idempotency/security cases
- Повреждённый или чужой источник и неверная классификация по-прежнему отказывают. Смена режима создаёт другой intent key. Расход записывается и выводится, даже когда приложение не останавливает прогон по денежному пределу.

## Rollback / feature flag
- Снять галочку `relaxed_limits` для нового прогона, чтобы вернуть денежное согласие. Для возврата прежних квот PDF и ZIP нужен обратный кодовый коммит; downgrade миграции проверяет отсутствие данных выше старых числовых границ и откажется, если такие данные уже сохранены. Старые принятые команды не меняются.

## Handoff
- changed files: исходный коммит `af581631` затронул 62 файла в указанных `allowed_paths`; последующие узкие фиксы снимают 2 ГиБ лимит публикации PDF-изображений и 1 МиБ лимит сохранения ответа текстового окна только для `relaxed_limits`, дополняют этот task и целевые тесты.
- commands/results: cost/preflight/coverage 36 passed; API/contract/proxy 38 passed; PDF/ZIP/stage 208 passed; web targeted 94 passed; `npm run api:verify`, `typecheck`, production `build`, Python compile and `alembic heads` passed. Existing extended-workflow suite has three failures also present in `origin/dev`: fixture lacks `run.version_uid`; 31 tests in that suite passed. No full gate or live provider/browser/DB migration run.
- contracts: расширены числовые границы API/портального блока, обновлено описание ошибок; версия API остаётся `1.14.0` для dev hotfix.
- known limits: внешний предел multipart-хранилища 10 000 частей по 16 МиБ (до 160 000 МиБ на файл), контекст и максимум ответа модели на один вызов, ресурсные пределы ОС/диска, 24-часовой сетевой таймаут. Длинный текст одной страницы всё ещё должен помещаться в окно модели; его разбиение требует отдельного правила ссылок на страницу. Слитые в `dev` после начала задачи дополнительные cross-window и project-parameters проходы имеют собственные замороженные лимиты выбора источников и 8 вызов; этот хотфикс их не пересматривает. Интеграционный тест публикации crops требует локальный S3 endpoint и здесь не выполняется.
- integration notes: только `origin/dev`; развёртывание остаётся отдельным действием владельца.
