# Source traceability

## 1. Переданные источники

- `PDF-proverka-main (1).zip` — действующее приложение и его документация; источник фактического бизнес-поведения.
- `Новая сжатая ZIP-папка.zip` — набор ADR/roadmap-материалов начатого refactoring; источник инженерных решений, но не plan-of-record нового greenfield проекта.
- `ADR_BIBLE.md` — архитектурная конституция refactoring; большинство системных принципов адаптировано сюда.

## 2. Что перенесено как принцип

- PostgreSQL — каноника бизнес-метаданных;
- private S3 — каноника долговечных bytes/artifacts;
- immutable manifests;
- modular monolith control plane;
- execution engine отделён от владения metadata;
- contract-first boundaries;
- outbox, idempotency, explicit state machines;
- generated OpenAPI client;
- Next.js/React/TypeScript strict + FSD/vertical slices;
- LLM reproducibility via AnalysisProfile/PromptBundle/NormsSnapshot/ModelCallRecord;
- characterization/contract/integration/E2E/replay/restore evidence;
- parallel delivery only after contract freeze.

## 3. Что **не** перенесено буквально

### Strangler runtime migration
В refactoring Bible legacy остаётся production runtime и новый control plane постепенно перехватывает сценарии. В этом пакете репозиторий пустой, поэтому runtime Strangler не нужен. Legacy — read-only oracle/fixture source, не adapter по умолчанию.

### Legacy filesystem/SQLite pilot choices
Distributed-worker материалы содержат решения, оправданные пилотом legacy (filesystem packages, SQLite, отсутствие S3). Greenfield каноника уже PostgreSQL/S3, поэтому переносится семантика протокола и recovery-инварианты, но не pilot storage implementation.

### Точные retention TTL
Источник формулирует необходимость classification/retention, но конкретные юридические сроки не определяет. Они остаются blocking owner decision до production hardening.

## 4. Правило дальнейшего использования legacy

Любой перенос алгоритма из legacy оформляется задачей типа:

```text
characterize → define contract → isolate algorithm → port/rewrite → parity evidence
```

Копирование крупного service/router/pipeline manager целиком запрещено.
