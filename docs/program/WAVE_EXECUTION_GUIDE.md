# Main guide — waves, contract freezes and checkpoints

This guide retains the original wave procedure. For new routine work, use the lighter
task, branch and check rules in `AGENTS.md` §§2, 7–8 and `INTEGRATION_POLICY.md`.
Historical wave and checkpoint evidence is unchanged.

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

Every dispatched task is created from `docs/templates/TASK_TEMPLATE.md` and records four pieces
of governance evidence even when their value is `none`: enumerator ownership, captured premise
evidence, historical-evidence mode and publication authority. A route/screen/error/migration task
is not dispatchable until the shared enumerator and its sole wave owner are named.

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
  api: 1.4.0
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

An exact premise is evidence only when the task carries the dated command **and its captured,
untruncated output**. A command somebody could run later is a recipe, not proof that the premise
was true at dispatch. Paths, line numbers and counts all follow this rule.

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

Corrections to a completed task log, review or checkpoint record are committed as a new addendum
that cites the immutable source. The source record is not rewritten to make the past cleaner.

Development publication and deployment publication are different integration outcomes:

- `origin/dev` is the default ref for a development candidate, with its verification
  status stated explicitly;
- `origin/main` is an auto-deploy action owned by the delegated release integrator under
  `MAIN_AUTODEPLOY_POLICY.md`. The owner does not need to merge each SHA in GitHub.

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

Use the existing development checkout for sequential, single-owner work. Add one
short-lived branch/worktree per concurrent change only when it needs isolation; reuse
it through implementation and review. An integration branch is useful when concurrent
changes converge, not a default for every task. Record the base SHA when it matters to
the result and clean up finished worktrees after their content is safely integrated.

## 6. Task size

Target one measurable result. Split a change only when owners must work concurrently,
a frozen contract needs independent approval, or the resulting diff cannot be reviewed
or verified as one unit. A small vertical change can include contract, backend,
frontend and tests under one owner with focused checks.

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
