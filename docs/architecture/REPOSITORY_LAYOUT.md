# Repository layout

```text
/
├── README.md
├── AGENTS.md
├── contracts/                 # frozen/versioned machine contracts
│   ├── domain/v1/
│   ├── api/v1/
│   ├── events/v1/
│   ├── analysis/v1/
│   └── comparison/v1/
├── src/auditmanager/          # Python modular monolith
│   ├── shared/
│   ├── access/
│   ├── documents/
│   ├── ingest/
│   ├── storage/
│   ├── jobs/
│   ├── analysis/
│   ├── findings/
│   ├── decisions/
│   ├── comparison/
│   ├── export/
│   ├── workers/
│   ├── operations/
│   ├── api/
│   └── bootstrap/
├── web/                       # Next.js application
│   └── src/
│       ├── app/
│       ├── _app/
│       ├── _pages/
│       ├── widgets/
│       ├── features/
│       ├── entities/
│       └── shared/
├── db/migrations/
├── infra/
│   ├── local/
│   ├── observability/
│   └── runbooks/
├── fixtures/
│   ├── synthetic/
│   └── golden/
├── tests/
│   ├── characterization/
│   ├── contract/
│   ├── integration/
│   ├── e2e/
│   └── replay/
├── scripts/
└── docs/
```

## Backend module shape

Каждый bounded context постепенно получает только необходимые уровни:

```text
<module>/
  domain/
  application/
  ports/
  adapters/
  public.py          # разрешённый Python public application API, если нужен
```

Не создавайте пустые framework-like слои заранее. Skeleton содержит README boundary, а каталоги появляются с реальным use case.

## Shared

`shared/` — только действительно cross-cutting primitives: typed IDs/base protocols/time/checksum/errors/telemetry abstractions. Domain-specific helper не переносится в shared ради удобства.

## Contract ownership

`contracts/**` принадлежит contract owner/integrator текущей волны. Consumer не меняет schema, чтобы «починить свой код».

## Hotspots

Параллельно не редактируются:

- root dependency manifests/lockfiles;
- `contracts/**` frozen set;
- migration head;
- application composition/bootstrap;
- global frontend styles/theme;
- `docs/program/CURRENT_STATE.md` и checkpoint registry.
