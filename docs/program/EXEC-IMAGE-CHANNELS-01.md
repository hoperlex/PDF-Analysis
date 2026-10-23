# EXEC-IMAGE-CHANNELS-01 — графические кропы на действующих каналах исполнителя

## Результат

`ModelRequest` несёт один дескриптор кропа с SHA-256 и размером, а для прямого
HTTP-вызова — проверенные PNG-байты отдельно от журналируемого тела. До отправки
проверяются идентификатор Blob, `portal_block_id`, тип, размер, сигнатура и
SHA-256. OpenAI Chat получает `image_url` с data URL, Anthropic Messages —
блок `image` с base64. Это работает для `http_api` по `direct` и `vpn`.

Pull-команда с `local_images` и Codex `--image` была готова в
`EXEC-IMAGE-DELIVERY-01`. Теперь локальный OpenAI-совместимый endpoint может
получить PNG в сообщении пользователя при `[endpoint].accept_images = true`.
MCP-мост при `--accept-images` возвращает проверенные байты как image content
рядом с текстом задания. Без явного включения оба клиента сообщают
`image_input_unsupported`; при подмене байтов — `image_delivery_failed` до
модельного вызова. Инструкция изолированной Claude-сессии требует проверить,
что блок изображения реально виден, и сообщить отказ, если его нет.

| Подключение/клиент | Доставка PNG |
| --- | --- |
| `http_api` / `openai_chat`, direct или VPN | OpenAI Chat `image_url` |
| `http_api` / `anthropic_messages`, direct или VPN | Anthropic Messages `image` |
| `pull` / command | Проверенный временный PNG, `local_images` |
| `pull` / local endpoint | OpenAI Chat `image_url`, опция `accept_images` |
| `pull` / MCP Claude session | MCP image content, опция `--accept-images` |
| `ssh_command`, `http_api` / `ssh_tunnel` | В текущем коде не обслуживаются и не назначаются |

## Проверки

- HTTP, агент и MCP через локальные тестовые серверы: **81 passed**.
- Существующие pull-адаптер, доставка PNG и proxy: **117 passed**.
- MCP workspace и проверка дескриптора: **14 passed**.
- README и Codex answer command: **13 passed**.
- Python compile и `git diff --check`: OK.
- Полный `make gate` отложен для итогового beta-кандидата по `R-135`.

## Контракты и границы

OpenAPI `1.1.0`, 88 путей / 100 операций / 286 схем, stage registry,
crop manifest и migration head `0031_executor_pull_channel` не менялись.
Новых API-операций, миграций, зависимостей и назначений нет. Запросы без
изображения идут прежним путём. Никакая стадия прогона пока не создаёт
задание с кропом: W56b должен предоставить утверждённый промпт, бюджет,
правила доказательств и отдельный ключ назначения. Большой MCP image content
может упереться в лимит Claude Code на результат инструмента; для такого
кропа пригоден агент, а MCP-сессия требует ручной проверки перед включением.

## Интеграция и откат

Для будущей отдельной image-стадии взять ровно один PNG через
`load_saved_image_crop_item` под текущим Attempt, поместить дескриптор в
`ModelRequest.body.images`, а байты в `ModelRequest.image_bytes`. В pull-задании
используется тот же дескриптор, а клиент сам получает байты через
`getExecutorTaskImage`. В конфигурации локального endpoint включать
`accept_images` только для визуальной модели; для MCP добавить
`--accept-images` и проверить одно синтетическое задание в Claude-сессии.
Пока image-стадия не активирована, откат — revert этого среза; БД не меняется.

Запретные hotspots (`contracts/**`, миграции, composition root, root lockfiles,
глобальные стили) не затронуты. Публикация — только `origin/dev`; перенос
в `origin/main` остаётся действием владельца.
