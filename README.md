# AuditManager Greenfield — bootstrap package

Этот репозиторий — **стартовый набор для разработки нового приложения с нуля**. Он не является копией legacy-кода и не предполагает runtime-зависимости от старого приложения.

Legacy `PDF-proverka-main` используется только как:

1. behavioral oracle — источник фактического пользовательского поведения;
2. источник characterization/golden fixtures;
3. каталог edge cases и бизнес-инвариантов;
4. эталон для semantic parity там, где бизнес-смысл должен сохраниться.

Архитектура нового приложения задаётся `docs/architecture/ARCHITECTURE_BIBLE.md`, принятыми ADR и замороженными контрактами в `contracts/`.

## С чего начать

Новый репозиторий должен создаваться **из содержимого этого пакета**, после чего работа идёт в следующем порядке:

```text
README
  → docs/PRODUCT_SYNOPSIS.md
  → docs/architecture/ARCHITECTURE_BIBLE.md
  → docs/architecture/ADR_INDEX.md
  → docs/program/ROADMAP.md
  → docs/program/WAVE_EXECUTION_GUIDE.md
  → docs/stages/S00_...
```

`FF-01 ACCEPTED` записан 2026-09-09. На текущей planning-линии разрешён только
foundation provider code из P01 (`infra/local/**`, `db/migrations/**`,
`src/auditmanager/shared/db/**`, `src/auditmanager/storage/**`) в пределах task-specific
`allowed_paths`. Production-код предметной области остаётся запрещён до отдельной
приёмки детального P02–P05 плана и выполнения его зависимостей.

## Команды foundation (P01)

Корневой task runner — `make`. Эти девять команд заморожены FF-01 и являются
единственной командной поверхностью foundation; их владелец — `P1-INT-00`.
Провайдерные ленты заполняют только свои зарезервированные пути и вызывают эти
цели, не редактируя `Makefile` и не создавая приватных алиасов.

| Команда | Что делает | Кто реализует |
|---|---|---|
| `make bootstrap` | воспроизводит обе locked-среды: `.venv/bootstrap` (валидаторы) и `.venv` (runtime/тесты) | `P1-INT-00` |
| `make up` | поднимает PostgreSQL и S3-совместимый сервис | `P1-INF-01` |
| `make down` | останавливает их, не удаляя данные | `P1-INF-01` |
| `make check-services` | health сервисов и идемпотентная инициализация приватного бакета | `P1-INF-01` |
| `make migrate` | применяет migration head | `P1-DB-01` |
| `make check-db` | связность БД и текущее состояние миграций | `P1-DB-01` |
| `make check-storage` | доступ BlobStore к приватному бакету | `P1-STO-01` |
| `make test-foundation` | только принятый foundation-набор тестов | `P1-QA-00` |
| `make foundation` | вся последовательность подряд | композиция |

Цель, реализация которой ещё не пришла, — стабильный forwarder: она **падает явно**,
называя зарезервированный путь и задачу-владельца. Подмены реализации, тихого
пропуска и fallback нет ни в одной цели.

Код возврата сам по себе не является доказательством. `check-services`, `check-db` и
`check-storage` обязаны печатать `FOUNDATION-CHECK OK <цель>` **последней фактической
строкой вывода** — после того как их проверки прошли. `make` отклоняет: нулевой код
возврата без этой строки, любой видимый вывод после неё и зарезервированный файл
нулевого размера. ANSI-цвет, CR и окружающие пробелы нормализуются, пустые строки
после sentinel допустимы. Checker запускается с `PYTHONUNBUFFERED=1`, иначе порядок
в захваченном выводе отражал бы буферизацию stdout, а не порядок записи. Граница
гарантии: проверяется, что после заявления об успехе checker ничего больше не
**напечатал**; работу без вывода (фоновый процесс, вывод в `/dev/null`) выводом
проверить нельзя.

Образы нельзя переопределить с места вызова. Фактическая ссылка читается во время
выполнения из строк `override FOUNDATION_*_IMAGE :=` самого `Makefile`, поэтому её не
меняют ни `make up FOUNDATION_POSTGRES_IMAGE=...`, ни `make -e`, ни target-scoped
присваивание через `--eval` (в том числе переданное через `MAKEFLAGS`/`GNUMAKEFLAGS`),
ни второй `-f` makefile: make-переменную можно перекрыть, байты файла — нет. Значение
без `@sha256:` отвергается. Другой образ — это запрос на новый пин к `P1-INT-00`, а не
решение ленты.

`.env` — это данные, а не код. Файл разбирается построчно как `NAME=VALUE` и никогда
не исполняется: sourcing позволял бы `.env` подменить функцию `compose()`, подменить
`PATH` или сделать `exit 0` и отрапортовать успех, ничего не выполнив.

Имена — строгий allowlist ровно из 15 замороженных FF-01 имён, а не чёрный список.
Любое другое имя отвергается: `PYTEST_ADDOPTS`, `PYTHONPATH`, `DOCKER_HOST`, `AWS_*`,
`PATH`, `MAKEFLAGS`, имя образа — всё одинаково. Чёрный список закрывал бы только те
имена, о которых кто-то вспомнил. Каждое из 15 имён обязано встретиться ровно один раз:
пропуск и повтор — явные ошибки, повтор никогда не разрешается молча в пользу одного из
двух значений.

Подстановки переменных внутри значений нет. Кавычки допускаются только как одна парная
обёртка всего значения, внутри которой нет кавычки того же вида; экранирования нет.
Незакрытая кавычка (`X="abc`), кавычка, не оборачивающая значение (`X=abc"`), и кавычка
внутри закавыченного значения (`X="a"b"`) — отвергаются, а не сохраняются как
неоднозначный литерал.

Зарезервированные пути провайдеров (`infra/local/docker-compose.yml`,
`infra/local/check_services.py`, `db/migrations/alembic.ini`,
`src/auditmanager/shared/db/check.py`, `src/auditmanager/storage/check.py`,
`tests/integration/foundation`) и интерпретаторы читаются во время выполнения из байтов
того makefile, который make действительно разобрал (`$(abspath $(lastword
$(MAKEFILE_LIST)))`), как и пины образов. Якорь именно такой, потому что `awk` по голому
`Makefile` читает `./Makefile`: запуск `make -f /настоящий/Makefile` из каталога с
подложной копией брал бы подложную. Поэтому ни `make up INF_COMPOSE=...`, ни
`make -e`, ни target-scoped `--eval` (в том числе через `MAKEFLAGS`/`GNUMAKEFLAGS`), ни
второй `-f` makefile не подменяют путь, к которому обращается forwarder. Это же
закрывает `make test-foundation RUNTIME_PY=/bin/true`, который иначе завершился бы с
кодом 0, не выполнив ни одного теста.

`make test-foundation` запускается герметично: вычищаются все `PYTEST_*`, меняющие
интерпретацию `PYTHON*` и загрузчиковые (`LD_AUDIT`, `LD_PRELOAD`, `OPENSSL_CONF`,
`GLIBC_TUNABLES`) переменные, выставляется `PYTHONNOUSERSITE=1`, конфиг pytest
закрепляется через `-c pyproject.toml --rootdir=.`, а код возврата pytest `5` («не
собрано ни одного теста») трактуется как ошибка. Вычистка делается `unset` в подоболочке,
а не через `env`: экспортированная bash-функция `env` перекрыла бы бинарник. Кроме того
`make` больше не передаёт в recipe-оболочку `BASH_ENV`, `ENV`, `SHELLOPTS` и `BASHOPTS`, а
`make -t` отвергается на этапе разбора.

Что этим **не** закрыто и заявлено прямо: `MAKEFLAGS=-n` — это dry-run, recipe не
выполняется вовсе, поэтому никакой guard внутри recipe сработать не может (`make -n`
остаётся обязательной проверкой, а сухой прогон не печатает ни `bootstrap OK`, ни отчёта
pytest, так что перепутать его с доказательством нельзя); `conftest.py` внутри самого
набора и плагин из runtime-лока — это deliverable `P1-QA-00`, они ревьюятся там; файл
`.pth` в `.venv/lib/python3.12/site-packages` исполняется при старте интерпретатора, уже
после вычистки.

`make bootstrap` приводит governance-окружение `.venv/bootstrap` в точное соответствие
`requirements/validation.lock`: лишние дистрибутивы удаляются, после чего проверяется,
что установлено ровно то, что залочено (плюс seeded `pip`).

Импорт foundation-кода из `src/` обеспечивают два root-owned механизма:
`PYTHONPATH=src` в вызовах модулей и `pythonpath = ["src"]` в
`[tool.pytest.ini_options]`. Благодаря второму буквальные команды лент работают
без правки окружения:

```bash
.venv/bin/pytest tests/integration/db
.venv/bin/pytest tests/integration/storage
```

Добавлять `sys.path`-манипуляции в conftest ленте не нужно и не разрешено.

### Требования к хосту

- CPython строго версии из `.python-version` (сейчас `3.12.3`). Если `python3.12` не в
  `PATH` или это интерпретатор активного virtualenv, bootstrap откажется работать —
  передайте базовый интерпретатор: `make bootstrap FOUNDATION_PYTHON=/path/to/python3.12`.
- Docker с плагином `compose` — для `up`/`down` и сервисных проверок.
- Сеть до PyPI и container registry при первом `make bootstrap` / `make up`.

Кэши закреплены внутри репозитория (в `.gitignore`): uv — в `.local/uv-cache`, pip —
в `.local/pip-cache`. Поэтому `make bootstrap` без каких-либо переменных не пишет в
домашний каталог — ни в `~/.cache/uv`, ни в `~/.cache/pip` — и не требует задавать
`UV_CACHE_DIR`.

`make bootstrap` идемпотентен и никогда не генерирует lock: отсутствующий `uv.lock`
или `requirements/validation.lock` — это явная ошибка, а не повод пересобрать пины.
Все версии зависимостей, точные образы (тег + digest) и точные строки вызова
записаны в `docs/program/FOUNDATION_LOCK.json`.

### Локальное окружение

```bash
cp .env.example .env
```

`.env` игнорируется git и никогда не коммитится; в `.env.example` лежат только
одноразовые локальные примеры. Перед `make up` дайте своей ленте уникальные
`FOUNDATION_INSTANCE`, `POSTGRES_PORT`, `S3_API_PORT`, `S3_CONSOLE_PORT`,
`POSTGRES_DB` и `S3_BUCKET`: FF-01 запрещает двум лентам делить одно живое
состояние сервисов. Перед любой сервисной командой `make` проверяет, что все
замороженные имена заданы и что service-сторона (`POSTGRES_*`, `MINIO_ROOT_*`)
согласована с application-стороной (`DATABASE_URL`, `S3_*`).

### Если что-то не так

- `.env is missing` — выполните `cp .env.example .env` и задайте значения ленты.
- `is an active virtualenv interpreter` — вы в активированном venv; откройте чистую
  оболочку или передайте `FOUNDATION_PYTHON`.
- `Python version mismatch` — пин точный; поставьте нужную версию или укажите путь.
- `uv.lock is missing` — lock создаёт только владелец пинов отдельной задачей.
- `a foundation provider implementation is not present yet` — соответствующая лента
  ещё не поставила свой файл; задача-владелец названа в тексте ошибки.

## Целевой стек

- backend/control plane: Python + FastAPI/ASGI, модульный монолит;
- metadata/durable workflow state: PostgreSQL;
- files/artifacts: private S3-compatible object storage;
- frontend: Next.js + React + TypeScript strict, App Router, FSD/vertical slices;
- contracts: OpenAPI + JSON Schema + SQL migrations;
- heavy analysis: отдельный execution process/worker, общающийся с control plane только через versioned packages/ports;
- local development: containers для PostgreSQL и S3-compatible storage; точные версии инструментов фиксируются в `CP-01`.

## Контрольные версии

| Checkpoint | Tag | Основной результат |
|---|---|---|
| CP-00 | `v0.0.0-architecture` | business/architecture/contracts frozen enough to code |
| CP-01 | `v0.1.0-foundation` | reproducible repo/toolchain/local stack |
| CP-02 | `v0.2.0-walking-skeleton` | upload → fake run → finding end-to-end |
| CP-03 | `v0.3.0-audit-alpha` | первый реальный audit stage + evidence |
| CP-04 | `v0.4.0-audit-beta` | основной audit pipeline |
| CP-05 | `v0.5.0-expert` | expert decisions + KB/review workflow |
| CP-06 | `v0.6.0-comparison-core` | deterministic comparison core |
| CP-07 | `v0.7.0-comparison-advanced` | AI/graphic comparison layers |
| CP-08 | `v0.8.0-distributed` | remote workers with fencing/recovery |
| CP-09 | `v0.9.0-hardening` | security/retention/restore/load/cost gates |
| CP-10 | `v1.0.0` | release acceptance |

Каждый checkpoint создаётся только после автоматических gates, ручного локального runbook и заполненного checkpoint report.

## Что в пакете намеренно отсутствует

- production business implementation;
- secrets и реальные production payloads;
- точные TTL/retention для пользовательских данных — это owner/legal decision;
- точные cloud/vendor choices и provider credentials;
- импорт legacy-модулей «для ускорения» без отдельной contract/characterization task.

Это не пробелы: они перечислены как явные решения/гейты в roadmap и ADR.
