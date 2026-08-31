# Architecture Bible — AuditManager Greenfield

**Статус:** baseline для нового репозитория; утверждается на CP-00.  
**Область:** backend, frontend, PostgreSQL, S3, analysis pipeline, workers, contracts, security, testing, operations и AI-agent delivery.

## 1. Архитектурная позиция

Продукт создаётся с нуля. Старое приложение не является runtime dependency. Оно используется как behavioral oracle и источник golden evidence.

```text
Next.js / React / TypeScript
        │ generated OpenAPI client
        ▼
Control Plane — Python/FastAPI modular monolith
        │
        ├── Metadata modules ───────── PostgreSQL
        ├── Storage module ─────────── private S3
        ├── Durable jobs/outbox ────── PostgreSQL
        └── Analysis port ──────────── Execution Engine / workers
                                         │
                                         ├── deterministic stages
                                         ├── model providers
                                         └── versioned norms snapshots
```

## 2. Sources of truth

| Данные | Каноника | Не каноника |
|---|---|---|
| objects/projects/documents/versions/runs/findings/decisions | PostgreSQL через owning module | JSON, path, frontend state |
| bytes/artifacts | private S3 через Storage port | local workdir, external URL |
| input/result of a run | immutable versioned manifest | `latest`, folder name |
| background operation status | durable Job/Attempt state | WebSocket, process memory |
| current expert verdict | projection of append-only Decision events | mutable finding field |
| prompts | content-addressed PromptBundle | editable current prompt folder |
| norms | versioned NormsSnapshot + provenance/checksum | mutable norms JSON without run snapshot |
| analysis configuration | immutable AnalysisProfile | `.env` or current UI selection |
| LLM call evidence | ModelCallRecord + protected payload/artifact checksum | diagnostic logs |
| comparison raw evidence | immutable deterministic artifact | AI summary |
| approved sheet link | user-owned state/event | latest automatic suggestion |

Одна сущность — один authoritative writer. Read models/projections могут быть множественными и rebuildable.

## 3. Bounded contexts

- Identity & Access
- Objects / Projects / Documents
- Versions & Ingest
- Storage & Blobs
- Audit Jobs & Runs
- Analysis
- Findings & Reviews
- Expert Decisions & Knowledge
- Comparison
- Export
- Worker Control
- Operations & Audit Trail

Контекст не импортирует внутренние ORM/repository/model соседнего контекста. Взаимодействие — application port, contract event или явно разрешённый read model.

## 4. Mandatory principles

### P-01 — Opaque identity
System ID генерируется один раз, не содержит path/business attributes и не парсится для восстановления связей. Human numbers — display fields.

### P-02 — Path is not identity
Filename, S3 key, URL и folder — адрес/представление, не identity.

### P-03 — Immutable history, explicit mutable pointers
Input versions, completed runs, manifests, raw comparison evidence и decision events immutable. Исправление создаёт новую revision/run/event. Mutable current pointers имеют одного владельца и меняются транзакционно.

### P-04 — Contract before concurrency
Shared contract сначала проектируется и фиксируется version/freeze marker; только после этого параллельно реализуются provider/consumer/tests/ops.

### P-05 — Modular monolith by default
Control plane — один deployable backend с жёсткими module boundaries. Новый network service требует отдельного ADR и доказательства необходимости.

### P-06 — Side effects at edges
Domain не читает env/filesystem/HTTP/clock/random напрямую. Это ports. Adapter отвечает за I/O/retry/typed error mapping.

### P-07 — Transaction ends in outbox
DB mutation + intent for external side effect фиксируются атомарно. Direct dual-write DB→S3/event/provider запрещён без recovery journal.

### P-08 — Retry is normal
Commands/imports/jobs/callbacks имеют idempotency key/natural unique key. Повтор после timeout не создаёт duplicate version/run/decision.

### P-09 — State is a state machine
Conflicting booleans не заменяют состояние. Allowed transitions, terminal states, retry/compensation определены один раз и тестируются.

### P-10 — No silent fallback
Неизвестный contract/auth/norm/provider state даёт явную typed failure/partial policy. Compatibility fallback допустим только как именованный, наблюдаемый и временный режим.

### P-11 — Derived data is rebuildable
Index/cache/thumbnail/page tile/KB projection/progress/read model не являются единственной копией. Есть source + recipe/version + rebuild procedure.

### P-12 — Observability is contract
Command/job имеет correlation ID, structured event, result metric и trace context. Diagnostic logs, durable audit и metrics — разные каналы с разными гарантиями.

### P-13 — Security fail-closed
Object authorization server-side. S3 private. Presigned access short-lived. Secrets/PII не попадают в browser state, package manifests, metric labels или logs без allowlist.

### P-14 — Simplicity before framework
Абстракция вводится после двух независимых применений либо потому, что это обязательная boundary. `BaseService`, `GenericRepository`, global `utils` без семантики запрещены.

### P-15 — LLM reproducibility by artifacts
LLM не детерминирован. Published run фиксирует input versions, AnalysisProfile, PromptBundle, NormsSnapshot, provider/model/params, checksums, usage, latency и measured/estimated cost.

### P-16 — Cost is an operational budget
Измеряются cost/run и cost/accepted-finding. Budget regression может останавливать canary/release так же, как error/latency regression.

### P-17 — Evidence first, AI additive
Deterministic/raw evidence не мутируется AI-слоем. AI создаёт отдельный versioned derived artifact со ссылкой на source checksum.

### P-18 — Expert decision is an event
Expert decision append-only. Current verdict/KB are projections. AI может рекомендовать review, но не переписывает человеческое событие.

### P-19 — Legacy is a read-only oracle
Legacy не импортируется runtime-кодом нового control plane без отдельного accepted ADR. Параллельные golden/replay tests допустимы.

### P-20 — Checkpoint is an evidence bundle
Git tag без green gates, manual report и contract manifest не является checkpoint.

### P-21 — Manual acceptance is first-class
В каждый CP входит воспроизводимый local runbook с expected results и evidence capture. Manual test не заменяет automated tests и наоборот.

### P-22 — Agent parallelism follows ownership boundaries
Количество агентов не определяет параллелизм. Декомпозиция идёт по frozen contracts, file ownership и bounded contexts. Shared hotspots принадлежат интегратору волны.

## 5. Backend dependency rule

```text
api / consumer
   → application commands & queries
      → domain rules
         ← ports
            ← adapters (PostgreSQL, S3, providers, worker transport)
```

- use-case handler вместо fat router;
- typed value objects для IDs/checksum/version/money/limits;
- UoW на один business transition;
- repository только на aggregate boundary;
- optimistic concurrency/row lock где нужен lost-update protection;
- typed Result/Error + central HTTP mapping;
- DI на composition root; service locator запрещён.

## 6. PostgreSQL rules

- normalized write model: FK, UNIQUE, CHECK, NOT NULL;
- UTC timestamps + actor/source;
- forward migrations; unsafe `down` не считается recovery;
- expand→backfill→switch→contract для breaking data change;
- cursor pagination для растущих списков;
- JSONB только для versioned opaque payload/extensions;
- cascade delete пользовательской истории по умолчанию запрещён;
- outbox/audit/migration journal append-only.

## 7. S3/storage rules

- private bucket/deny public;
- business code знает `blob_id`, role, size, sha256, media type, но не object layout;
- adapter единолично строит object key;
- upload: temporary/multipart → checksum/metadata verify → publish;
- complete object/manifest immutable;
- range/read/materialize cache — read contract;
- workers получают scoped short-lived access/package URLs, не permanent credentials.

## 8. Jobs and execution

- durable job record before side effect;
- `run_id`, `job_id`, `attempt_id` различны;
- lease/heartbeat + fencing token;
- retry bounded and error-class aware;
- poison job → terminal/DLQ state;
- progress — projection, не source of truth;
- result publish только после schema/checksum/manifest validation;
- stage registry — single versioned source;
- stage читает contract inputs и пишет только собственные outputs.

## 9. API

- OpenAPI — frontend/backend contract;
- generated TypeScript client не редактируется вручную;
- write commands принимают idempotency key;
- stable `error_code`, safe message, correlation ID;
- breaking change → new major contract/versioned compatibility period;
- liveness проверяет process/event loop, readiness — required dependencies; readiness failure не является kill signal.

## 10. Frontend

- Next.js App Router, React, TypeScript strict;
- `app/` — thin Next adapter; FSD layers: `_app`, `_pages`, `widgets`, `features`, `entities`, `shared`;
- `page.tsx` связывает route с `_pages`, без domain logic;
- PDF viewer/live progress/tables — bounded client islands;
- server state в query/cache; UI state local/narrow feature store; global domain store запрещён;
- raw HTTP только generated transport в `shared/api`;
- imports only downward; slice public API; no deep/cross imports;
- loading/empty/error/retry/permission states обязательны.

## 11. Comparison rules

- automatic matching suggestions are projections;
- approved sheet links have explicit owner/revision and survive recomputation;
- text exclusions/diff/raw graphic evidence deterministic and immutable per comparison revision;
- AI review refers to raw artifact checksums and cannot overwrite them;
- automatic link/content repair emits proof + audit event + reversible operation;
- viewer receives short-lived/public-safe read representations, never internal S3 key.

## 12. Testing evidence

Required evidence types:

1. characterization/golden tests;
2. domain unit tests;
3. contract provider/consumer tests;
4. integration tests with real PostgreSQL + S3-compatible adapter;
5. migration/re-run tests;
6. E2E critical journeys;
7. deterministic replay tests;
8. live-quality policy tests for LLM;
9. restore/rollback drills;
10. manual checkpoint runbooks.

LLM parity is qualified:
- contour parity — identities/manifests/schema/links/artifacts;
- replay parity — same recorded provider responses, deterministic logic;
- live quality parity — labelled sample vs quality/cost/latency policy, not text equality.

## 13. Architectural Definition of Done

Change is done only when applicable items are true:

1. contract + data owner named;
2. invariants encoded as constraints/domain tests;
3. success/validation/conflict/retry/terminal failure tested;
4. API/schema compatible or migration exists;
5. diagnostic correlation possible;
6. security/redaction checked;
7. data migration has dry-run/recovery;
8. frontend has loading/empty/error/permission states;
9. docs/ADR updated if decision changed;
10. feature flag has owner/default/removal criterion;
11. local + CI verification reproducible;
12. no direct bypass of application/storage/metadata ports.

## 14. ADR rule

ADR required when changing source of truth/data owner, introducing service/database/queue/storage/provider, public major contract, identity/retention/security/consistency/RPO/RTO, cross-cutting framework, or exception to this Bible.

Accepted ADR is immutable history; replacement is new ADR with `supersedes`. Temporary exception requires owner, risk/control, expiry and removal task.
