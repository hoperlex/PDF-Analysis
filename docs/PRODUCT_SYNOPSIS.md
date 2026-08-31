# Product synopsis

## 1. Назначение

AuditManager Greenfield — платформа автоматизированного аудита проектной документации. Она принимает версионированные комплекты PDF и сопутствующих структурированных данных, запускает воспроизводимый multi-stage анализ, формирует доказательные замечания, передаёт их эксперту на решение, сохраняет историю решений и поддерживает сравнение версий/стадий документации.

Продукт проектируется не как «PDF viewer + LLM», а как система управления **Audit Runs** и доказательствами.

## 2. Основной пользовательский путь

```text
Object / Project
  → Document
    → Version
      → Ingest files
        → Audit Run
          → Analysis Stages
            → Findings + Evidence
              → Expert Review / Decision
                → Export / Knowledge / Comparison
```

Критический первый полезный путь:

```text
создать проект
→ загрузить документ
→ создать immutable version
→ запустить аудит
→ видеть progress
→ открыть finding рядом с evidence
→ принять/отклонить finding
→ выгрузить результат
```

## 3. Основные capability-группы

### Audit workspace
- объекты, дисциплины, проекты, документы и версии;
- загрузка PDF/ZIP/structured companions;
- статус ingest и audit run;
- просмотр PDF и evidence;
- findings и фильтрация;
- retry/resume безопасных операций;
- export.

### Analysis platform
- versioned stage registry;
- text/geometry/block context;
- text analysis;
- visual/block analysis;
- merge/deduplication;
- grounding/evidence validation;
- normative verification;
- critic/corrector quality gates;
- replay and cost accounting.

### Expert intelligence
- append-only expert decision events;
- reason codes/comments/discussions;
- knowledge-base projection;
- evidence verifier;
- suggested re-review of rejected findings;
- quality analytics.

### Comparison
- document/version pair;
- sheet matching suggestions + user-approved links;
- deterministic text exclusions/diff;
- raw evidence artifacts;
- AI synthesis as additive layer;
- graphic/vector comparison;
- audit/undo of automatic repairs.

### Distributed execution
- worker enrollment/capabilities;
- Run/Job/Attempt separation;
- lease/heartbeat/fencing;
- package transfer and checksums;
- offline event outbox/recovery;
- stale attempt rejection;
- result publication only after validation.

## 4. Продуктовые non-goals v1

- универсальная ECM/DMS;
- редактирование исходных PDF;
- микросервисная декомпозиция ради команд;
- autonomous expert verdict без явной policy;
- хранение канонических бизнес-данных в JSON/directories;
- точное текстовое совпадение live LLM output при parity.
