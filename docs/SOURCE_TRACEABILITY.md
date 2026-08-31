# Source traceability

## 1. Переданные источники

- `PDF-proverka-main (1).zip` — действующее приложение и его документация; источник фактического бизнес-поведения.
- `Новая сжатая ZIP-папка.zip` — набор ADR/roadmap-материалов начатого refactoring; источник инженерных решений, но не plan-of-record нового greenfield проекта.
- `ADR_BIBLE.md` — архитектурная конституция refactoring; большинство системных принципов адаптировано сюда.

### 1.1. Канонический legacy snapshot для CP-00

В локальном workspace legacy обнаружен в `/root/projects/PDF-proverka/PDF-proverka`.
По решению владельца источником characterization/parity зафиксирован последний на
момент фиксации commit локального `refs/heads/main`:

```text
repository: PDF-proverka
resolved_ref: refs/heads/main
commit: 32b9d903792b30506048a1d42b0e6b2d07aee403
subject: Add high-confidence Stage 5 sheet-link repair
commit_date: 2026-08-22T10:37:15+03:00
recorded_at: 2026-08-31
```

Локальный путь является discovery path текущего workspace, а не runtime/config
контрактом нового приложения. Все новые legacy inventory, golden fixtures и parity
evidence должны ссылаться на полный commit SHA выше и читать immutable Git tree
этого commit (`git show`/`git archive`), а не текущий checkout или движущийся branch.
Продвижение legacy `main` не меняет baseline автоматически: новый snapshot требует
отдельного review и явного обновления traceability. Legacy `.env`, credentials,
неотслеживаемые working-tree файлы и production payloads в snapshot не входят.

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

Каждый извлечённый fixture/evidence дополнительно фиксирует
`legacy_source_commit: 32b9d903792b30506048a1d42b0e6b2d07aee403` либо SHA
явно утверждённого следующего snapshot.
