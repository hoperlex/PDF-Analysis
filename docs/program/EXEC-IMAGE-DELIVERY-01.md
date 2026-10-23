# EXEC-IMAGE-DELIVERY-01 — доставка одного PNG pull-исполнителю

## Результат

Pull-задание может содержать одну ссылку на сохранённый PNG-кроп: Blob ID,
`portal_block_id`, SHA-256, размер и `image/png`. По `getExecutorTaskImage`
байты получает только токен, который держит текущий claim задания. Сервер
проверяет актуальность Attempt, срок claim и deadline до чтения и после него,
а также размер, SHA-256 и тип объекта. Агент повторяет проверку байтов,
создаёт временный файл с закрытыми правами и передаёт его Codex CLI через
`--image`; файл удаляется после завершения команды. Текстовый MCP-клиент и
агент без `[command].accept_images = true` отвечают явным отказом.

Это транспорт для **отдельного будущего задания по изображениям**. Текущая
стадия «Анализ текста» не создаёт такие задания. W56b должен добавить
производителя после утверждения промпта, бюджета и правил доказательств.

## Контракты

- API, domain, analysis и events: `contract_version` `1.1.0` после
  добавления опционального поля и операции. Domain `supersedes` указывает
  на `1.0.0`; словарь из 27 кодов и ревизия 19 не изменены.
- OpenAPI: 88 путей, 100 операций, 286 схем; новая операция
  `getExecutorTaskImage` и опциональное `ClaimedExecutorTask.images`.
- Клиент `web/src/shared/api/generated/` пересобран из того же OpenAPI;
  `web/FRONTEND_LOCK.json` содержит его хеши.
- Миграции, root lockfile и глобальные стили не менялись. Право на
  `contracts/**` и `bootstrap/composition.py` закреплено в
  [task-файле](tasks/EXEC-IMAGE-DELIVERY-01.md).

## Проверки

- Python: `tests/contract/api_v1` — 328 passed;
  `tests/contract/domain_p02` — 149 passed;
  `tests/contract/test_proxy_rate_limits.py` — 57 passed;
  `tests/unit/executor_runner` — 122 passed (локальный HTTP-макет);
  `tests/unit/executors/test_pull_images.py` — 9 passed.
- Web: `api:verify`, `typecheck` — OK; `test:contract` — 185 passed.
  Guard-набор: 282 passed в обычной песочнице; шесть проверок потребовали
  запуска дочерних `tsc` и `eslint` и затем прошли отдельно (20 passed) с
  разрешёнными локальными процессами.
- `git diff --check` и Python compile — OK. Полный `make gate` не запускался;
  `tests/integration/executors/test_runner_channel.py` требует `DATABASE_URL`,
  которого нет в рабочей среде этого среза.

## Интеграция и откат

Производитель W56b передаёт ссылку только после проверки сохранённого кропа
через current run/Attempt и digest портала. Текстовое описание блока остаётся
в `user_text`, картинка — в `images`. Для команды Codex включить
`[command].accept_images = true` после запуска новой версии агента. Пока
производителя нет, поле отсутствует и текущие текстовые задачи работают по
старому пути. Откатить этот срез до включения W56b можно без изменения БД.

## Известные границы

Здесь нет нового промпта, модельного вызова или опубликованного заключения
по кропу; продакшен-проверка изображения требует отдельного тестового задания
после интеграции W56b. Полный `make gate` не запускался для промежуточного
среза по `R-135`.
