# Roadmap — greenfield delivery

## Program objective

Доставить новый AuditManager как набор доказанных вертикальных capabilities, а не как технические слои, которые интегрируются в конце.

## Stage map

| Stage | Checkpoint | Goal | Exit evidence |
|---|---|---|---|
| S00 Architecture & behavior freeze | CP-00 | определить business oracle, contracts и архитектуру | ratified Bible/ADR + golden plan + draft machine contracts |
| S01 Repository foundation | CP-01 | воспроизводимый repo/local stack/toolchain | one-command bootstrap, lint/test, health/readiness, generated client path |
| S02 Walking skeleton | CP-02 | первый E2E data/job path | project→version→upload→fake run→finding→UI |
| S03 First real audit | CP-03 | реальный analysis stage + evidence | synthetic document → stage → FindingObservation + ledger |
| S04 Core audit engine | CP-04 | основной audit workflow | stage DAG, norms, retry/resume, export, parity evidence |
| S05 Expert intelligence | CP-05 | human decision/knowledge workflow | append-only decisions, KB projection, verifier/re-review |
| S06 Comparison core | CP-06 | deterministic compare | approved sheet links + exclusions/diff + viewer |
| S07 Comparison advanced | CP-07 | AI/graphic comparison | additive AI synthesis + graphic evidence + repair/undo |
| S08 Distributed execution | CP-08 | remote engines safely | worker protocol, fencing, offline recovery, validated result publish |
| S09 Production hardening | CP-09 | operational/security readiness | AuthZ, retention decisions, restore/load/cost/redaction drills |
| S10 Release acceptance | CP-10 | v1.0 release evidence | full golden journeys + clean deploy/restore + release report |

## Dependency spine

```text
S00 → S01 → S02 → S03 → S04 → S05
                       │
                       └────────────→ S06 → S07
                              S04 ─────────────→ S08
S05 + S07 + S08(optional product scope) ──────→ S09 → S10
```

S06 может начинать contract/design discovery после CP-03, но production integration не должна ломать core audit flow. S08 contract discovery можно вести после стабильного Analysis Package v1; remote runtime интегрируется после CP-04.

## Parallelism policy

Внутри stage работа организуется waves. Волна не равна stage: один stage может иметь несколько contract freezes. Каждая wave имеет один contract owner и один integration slot.

```text
inventory/design
   ↓
contract task
   ↓ FREEZE Cn
┌───────────── parallel lanes ─────────────┐
│ backend │ storage │ engine │ web │ QA │ ops │
└────────────────────┬──────────────────────┘
                     ↓
                 integration
                     ↓
        automated + manual evidence
                     ↓
               checkpoint/tag
```

## Capability ordering rationale

1. S02 доказывает architecture plumbing до AI complexity.
2. S03 вводит только один реальный analysis path, чтобы не маскировать contract bugs множеством stages.
3. S04 расширяет pipeline после стабильной provenance/identity model.
4. S05 добавляет expert knowledge только после stable finding identity.
5. Comparison использует уже зрелые Version/Storage/Viewer primitives.
6. Remote workers появляются после стабильного package contract; иначе distributed transport замораживает плохой pipeline API.
7. Security/retention/restore развиваются с начала, но CP-09 является full production gate, а не первым моментом их появления.
