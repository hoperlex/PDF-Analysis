# System architecture

## Context

```text
Browser
  │
  ▼
Next.js UI ───── generated API client ─────► Control Plane
                                                │
                   ┌────────────────────────────┼─────────────────────────┐
                   ▼                            ▼                         ▼
              PostgreSQL                  private S3              Analysis Port
        metadata/jobs/outbox/audit        blobs/artifacts              │
                                                                        ▼
                                                               Execution Engine
                                                               local or worker
                                                                        │
                                              ┌─────────────────────────┼─────────┐
                                              ▼                         ▼         ▼
                                      deterministic stages          LLM APIs   norms
```

## Control plane

Владеет identity/access, projects/documents/versions, storage metadata, jobs/runs, findings/reviews, decisions/KB, comparison state, export, worker control и durable audit.

Он **не обязан** выполнять тяжёлый анализ в API process.

## Execution engine

Получает immutable/versioned `JobPackage`; выполняет stage DAG/registry; возвращает `ResultPackage`. Engine:

- не меняет current document version;
- не пишет напрямую canonical PostgreSQL aggregates;
- не решает, какой result publish;
- не владеет expert decisions;
- может работать локально или на remote worker при одинаковом package contract.

## Publication boundary

```text
JobPackage → attempt → stage results → ResultPackage
                                      │
                                      ▼
                           schema + checksum validation
                                      │
                            valid? ───┴─── no → failed/quarantine
                              │ yes
                              ▼
                       transactional publish
                       metadata + outbox
```

## Long operation rule

Оркестрация длинных операций — explicit orchestration saga/state machine. Choreography допустима только для простых informational events.

## Deployment evolution

Начало:

```text
web + api + local engine process + PostgreSQL + S3
```

Позже:

```text
web + api/control-plane + engine workers + PostgreSQL + S3
```

Выделение нового microservice требует ADR; bounded context сам по себе не является microservice.
