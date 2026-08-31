# Technology baseline

## Accepted direction

| Layer | Baseline |
|---|---|
| Backend | Python, FastAPI/ASGI, typed application/domain code |
| DB | PostgreSQL |
| Object storage | private S3-compatible API |
| Frontend | Next.js, React, TypeScript strict, App Router |
| Frontend architecture | FSD/vertical slices with thin Next adapter |
| API contract | OpenAPI + generated TypeScript client |
| Internal/package contracts | JSON Schema; SQL migration for DB |
| Jobs | durable PostgreSQL Job/Attempt/lease/outbox initially |
| Analysis | separate engine process boundary, versioned packages |
| Testing | pytest + frontend unit/component + contract/integration/E2E/replay |
| Local infra | containerized PostgreSQL + S3-compatible storage |

## Greenfield tool choices to freeze in W1-INT-00

Следующие конкретные инструменты являются **bootstrap recommendation**, а не выводом из legacy/Bible. Интегратор CP-01 фиксирует версии и создаёт ADR, если выбирается альтернатива:

- Python environment/deps: `uv` или эквивалент с reproducible lock;
- JS package manager: `pnpm` или эквивалент с lockfile;
- Python quality: Ruff + type checker;
- frontend quality: ESLint + TypeScript compiler;
- local services: Docker Compose compatible runtime;
- browser E2E: Playwright;
- OpenAPI client generation: генератор, выбранный по ability to preserve schema/runtime validation needs.

Нельзя разрешать каждому агенту самостоятельно выбирать package manager, ORM, migration tool, query cache или UI state library.

## Version policy

Точные runtime/tool versions пинятся в CP-01. После freeze обновление major/minor, затрагивающее contracts/build output, идёт отдельной maintenance wave с evidence.
