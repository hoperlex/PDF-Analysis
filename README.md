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

До завершения `S00` production-код предметной области не пишется. До `CP-01` допустим только bootstrap/tooling-код.

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
