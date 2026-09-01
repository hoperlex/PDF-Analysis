# Contract catalog

## Rule

Any boundary between independently changing components has a versioned machine-checkable contract. Unknown major version is rejected explicitly.

## Contract families

| Family | Location | Owner | Consumers |
|---|---|---|---|
| Domain primitives | `contracts/domain/v1` | ARC/contract owner | all contexts |
| Public API | `contracts/api/v1` | API contract owner | web/external clients |
| Events | `contracts/events/v1` | integration owner | outbox/ops/projections |
| Analysis packages | `contracts/analysis/v1` | ENG contract owner | control plane/engine/workers |
| Comparison | `contracts/comparison/v1` | CMP contract owner | comparison backend/web/tests |
| DB schema | `db/migrations` | migration owner | backend/ops |

Владелец в таблице — роль, а не постоянное назначение. Конкретный владелец пути
фиксируется контрактом активной волны: в
[W0.2](../program/waves/W0.2_architecture_domain_contract.md) `contracts/domain/v1/**`
принадлежит DOM lane, `contracts/analysis/v1/**` — ENG/ANA lane, а ARC lane владеет
только `docs/architecture/**`. Лейн не пишет в чужой contract family даже для
исправления собственной сборки.

## Freeze manifest

Каждая волна создаёт contract manifest в checkpoint evidence (не обязательно отдельный постоянный формат до CP-01):

```yaml
wave: W3
contracts:
  domain: 1.0.0-draft.1
  api: 1.1.0-draft.0
  events: 1.0.0-draft.0
  analysis: 1.2.0-draft.0
  comparison: not-active
frozen_at_commit: <sha>
owner: W3-C-01
```

После freeze consumer не редактирует общий contract. Нужное изменение либо backward-compatible и принимается owner/integrator, либо переносится в следующую wave.

## Compatibility

- additive optional field in known major — allowed by policy only if provider/consumer tests pass;
- removed/renamed required field — breaking;
- semantic meaning change without schema change — breaking and requires version change/ADR if public;
- enum expansion requires consumer policy: tolerant or versioned;
- DB migration follows expand→backfill→switch→contract.

## Analysis package boundaries

Control plane → engine: `JobPackage`.  
Stage → orchestrator: `StageResult`.  
Engine → control plane: `ResultPackage`.

All artifact references use `blob_id` + checksum/size/media type/role; internal object key is not contract data.
