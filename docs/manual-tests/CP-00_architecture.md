# CP-00 — Architecture acceptance

## Preconditions

- Распакованный bootstrap package.
- Доступ к read-only Git tree канонического legacy commit из `docs/SOURCE_TRACEABILITY.md` и исходным ADR/Bible.
- Назначены architecture/domain owner и independent reviewer.

## Start record

Before testing record:

```text
candidate_commit:
contract_manifest:
migration_head:
backend_runtime:
frontend_runtime:
local_infra_versions:
tester:
started_at:
```

## Test cases

### MT00-01 — Documentation navigation

**Action**
Открыть README → Product synopsis → Bible → ADR index → Roadmap → S00. Проверить, что цепочка не содержит ссылки на отсутствующий обязательный документ.

**Expected**
Все plan-of-record документы доступны; bootstrap package самодостаточен.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT00-02 — Greenfield boundary

**Action**
Проследить основной user journey и убедиться, что ни один mandatory runtime шаг не требует запуска/import legacy.

**Expected**
Legacy упоминается только как oracle/fixture source.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT00-03 — Identity walk

**Action**
Взять legacy-сценарий с rerun finding. На бумаге/whiteboard провести его через `Finding`/`FindingObservation`/`ExpertDecision`.

**Expected**
`F-NNN` нигде не нужен как FK; решение эксперта переживает rerun только через stable identity policy.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT00-04 — Run/job/attempt walk

**Action**
Смоделировать provider timeout → retry → stale worker result.

**Expected**
Run/Job/Attempt не смешиваются; stale Attempt не имеет права publish.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT00-05 — Comparison ownership

**Action**
Смоделировать auto suggestion → user-approved sheet link → recompute → AI review.

**Expected**
Recompute не перетирает approved link; AI не меняет raw deterministic evidence.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT00-06 — Unresolved decisions

**Action**
Просмотреть proposed ADR и owner decisions.

**Expected**
Retention/tenant/IdP и другие неподтверждённые значения явно unresolved, а не придуманы.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

## Final acceptance checklist

- [ ] Нет hidden Strangler runtime dependency.
- [ ] Все ключевые bounded contexts имеют владельца данных.
- [ ] Shared contract freeze/process понятен reviewer без устного пояснения.

## Stop/cleanup

Stop the local stack using the documented command. Preserve only synthetic/anonymized evidence required by the checkpoint report. Remove temporary credentials/tokens and local fault-injection overrides.

## Result

A checkpoint cannot be tagged if any mandatory case is `FAIL` or unexplained `BLOCKED`. Open a blocking task; after fix, rerun affected case plus regression cases whose contracts/state were touched.
