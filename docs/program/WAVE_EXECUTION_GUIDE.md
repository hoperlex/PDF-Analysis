# Main guide — waves, contract freezes and checkpoints

Это основной operational документ для AI-agent разработки.

## 1. Roles

Каждая активная wave назначает роли, даже если их выполняют AI agents:

| Role | Responsibility |
|---|---|
| Program integrator | единственный владелец integration branch/checkpoint evidence |
| Contract owner | shared schemas/semantics текущей wave |
| Lane owner | ограниченный bounded-context implementation |
| QA owner | independent contract/integration/evidence verification |
| Ops owner | reproducibility, telemetry, local runtime |
| Manual tester | выполняет checkpoint runbook не из author context |

Один agent может иметь несколько ролей последовательно, но contract owner и consumer implementation не должны менять contract «на ходу» без нового freeze.

## 2. Lane codes

`ARC`, `DOM`, `META`, `STO`, `JOB`, `ENG`, `AI`, `FND`, `DEC`, `CMP`, `WRK`, `API`, `WEB`, `QA`, `OPS`, `SEC`, `INT`, `BHV`.

Task ID:

```text
W<stage-or-wave>-<lane>-<NN>
examples: W2-C-01, W4-ENG-03, W8-WRK-02, W4-INT-01
```

## 3. Wave lifecycle

### A. Prepare
Integrator creates/updates a wave-plan from `docs/templates/WAVE_PLAN_TEMPLATE.md`:

- scope/non-goals;
- completed dependencies;
- current contract versions;
- hotspots/owners;
- candidate tasks;
- expected integration order;
- checkpoint impact.

### B. Contract task
One owner changes shared semantics/contracts. Consumers may create mocks/fixtures **against draft contract**, but do not merge production consumer code until freeze.

Contract task delivers:

- schema/API/state-machine changes;
- examples;
- compatibility statement;
- provider/consumer test skeleton;
- contract version;
- changelog/freeze marker.

### C. Freeze
Integrator records:

```yaml
wave_id: W4.2
contract_set:
  domain: 1.0.0
  api: 1.3.0
  analysis: 1.4.0
  events: 1.1.0
  comparison: null
migration_head: <revision>
frozen_commit: <sha>
frozen_by: <task_id>
```

After freeze, implementation tasks are immutable consumers of that set.

### D. Parallel implementation
Agents receive task files with disjoint `allowed_paths`. Safe examples after freeze:

- PostgreSQL adapter vs S3 adapter;
- API provider vs generated client/mocked frontend;
- engine stage vs independent contract tests;
- web viewer vs backend read model;
- telemetry/dashboard definitions vs business implementation.

### E. Integration slot
Only integrator may:

- resolve cross-lane contract mismatch;
- update composition root;
- advance migration head if collision exists;
- update root locks;
- merge generated client changes tied to OpenAPI;
- change frozen contract set.

If mismatch requires semantic contract change, integration stops and opens `W*-C-FIX-*`; consumers do not silently fork schemas.

### F. Evidence gate
Run, at minimum where applicable:

```text
bootstrap / build
lint + typecheck
unit/domain
contract
integration with real PostgreSQL/S3
migration fresh + upgrade/re-run
E2E critical route
replay/golden
security/static checks
```

Exact commands become stable at CP-01 and are documented in root command surface (`make ...` or selected equivalent).

### G. Manual checkpoint gate
Checkpoint candidate is locally started from a clean state using the matching `docs/manual-tests/CP-XX_*.md`. Tester records actual result, evidence IDs/screenshots/log references and deviations.

### H. Checkpoint
Integrator fills `CHECKPOINT_REPORT_TEMPLATE.md`, updates `CURRENT_STATE.md`, then creates annotated tag from the accepted integration commit.

## 4. Shared hotspots

Always single-owner per wave:

- root package/dependency manifests and lock files;
- `contracts/**` frozen schemas;
- migration head;
- `src/auditmanager/bootstrap/**` composition;
- generated OpenAPI client regeneration commit;
- frontend global theme/styles;
- checkpoint registry/current state.

## 5. Worktree model

Default:

```text
main
integration/W4.2
agent/W4.2-STO-01  (worktree A)
agent/W4.2-JOB-02  (worktree B)
agent/W4.2-WEB-01  (worktree C)
agent/W4.2-QA-01   (worktree D)
```

Task starts from frozen commit. Agent does not stack on another unmerged agent branch. Integration is the only convergence point.

## 6. Task size

Target: one bounded context and one measurable result, usually 0.5–3 engineering days equivalent. If one task modifies shared schema + backend + frontend + migration, split it into:

```text
contract task
  → backend provider
  → frontend consumer
  → independent tests
  → integration task
```

## 7. Stop conditions

Stop wave integration when:

- contract meaning is ambiguous;
- two authoritative writers appear;
- migration cannot be replayed from clean DB;
- idempotency/retry creates duplicates;
- raw evidence changes under AI processing;
- manual route works only with local dirty data;
- a production failure is hidden by fallback;
- checkpoint evidence cannot identify exact contract/migration/build versions.

Do not «fix forward in multiple agent branches». Reopen a single contract/integration task.
