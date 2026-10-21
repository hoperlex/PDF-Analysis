# Task W61-DISPATCHER-01 — «Диспетчер»: assign work to experts, statuses, «Мои задачи»

task_id: W61-DISPATCHER-01

## Outcome

An administrator assigns a project or one document set of a project to an expert
with an optional note; the expert sees the assignment in «Мои задачи» on the home
screen and moves it through `assigned → in_progress → done` (or returns it with a
reason); the administrator sees every assignment with its status and history on the
«Диспетчер» screen and may reassign or cancel it. Every change is an append-only
event with actor and time; the current state is derived, never held only in memory.

## Depends on

- `W59-SECTION-SEAL-01`, `W59-SECTION-UI-01` — completed (project/document screens).

## Frozen inputs

- base commit: `68868d8300440166cc5bc96b5fd872cf6e62066f` (`origin/dev`);
- API at base: 50 paths / 57 operations / 137 schemas; migration head
  `0024_version_classification` — this task alone takes `0025`;
- roadmap Q-2 (`ROADMAP-TO-BETA.md` §10.5): Диспетчер in beta, График работ after 1.0;
  placement in this window by `R-139` (the W61/W62 placement question is moot for the
  code); rulings `R-60` (roles are a set; admin without expert reads, does not decide),
  `R-135`.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/support/expected_facts.json
- enumerator_owner: W61-DISPATCHER-01 (migration head in phase A; API surface in phase B after the integrator hands over the contract slot)
- totality_query: `python3 -c "import json;d=json.load(open('tests/support/expected_facts.json'));print(d['path_count'],len(d['operations']),len(d['schema_names']),d['migration_head'])"`

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `db/migrations/versions/**`
- `src/auditmanager/dispatch/**`
- `src/auditmanager/access/references.py`
- `tests/integration/dispatch/**`
- `tests/integration/db/**`
- `tests/unit/dispatch/**`
- `tests/support/expected_facts.json`
- `contracts/api/v1/**`
- `contracts/domain/v1/**`
- `src/auditmanager/api/**`
- `src/auditmanager/bootstrap/**`
- `tests/support/**`
- `tests/contract/**`
- `tests/integration/api/**`
- `tests/integration/composition/**`
- `web/openapi/**`
- `web/FRONTEND_LOCK.json`
- `web/src/shared/api/**`
- `web/src/shared/config/screen-registry.ts`
- `web/src/entities/**`
- `web/src/features/**`
- `web/src/widgets/**`
- `web/src/_pages/dispatcher/**`
- `web/src/_pages/home/**`
- `web/src/app/dispatcher/**`
- `web/src/app/bff/v1/[...path]/route.ts`
- `web/tests/**`
- `web/docs/**`
- `tests/e2e/pc01/**`
- `docs/program/CONTRACT_PIN_REGISTRY.md`
- `docs/program/P02_SEAMS.md`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/manual-tests/**`
- `infra/deploy/README.md`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/serve.py`
- `docs/program/W61-DISPATCHER-01.md`
- `docs/program/tasks/W61-DISPATCHER-01.md`

**Phasing (binding):** phase A may touch only the first seven paths (migration,
`dispatch/**`, `access/references.py`, dispatch/db tests, `expected_facts.json` for the
migration head only) and the two docs files. Every other path opens only after the
integrator's message that hands over the contract slot, from the commit it names.

## Lane resources

- foundation_instance: `auditmanager-w61-dispatcher`
- postgres_port: `57530`
- s3_api_port: `61130`
- s3_console_port: `61131`
- postgres_db: `auditmanager_w61_dispatcher`
- s3_bucket: `auditmanager-w61-dispatcher`

## Forbidden hotspots

Dependency files, `web/src/_app/providers.tsx`, global styles, other contexts'
internals (deep imports), `CURRENT_STATE.md`, refs, tags, the stand.

## Non-goals

No «График работ», no notifications by mail, no per-project ACL (role-based access as
today), no workload analytics, no full gate.

## Deliverables

Phase A: migration `0025_work_assignments` (assignment + append-only event tables,
immutability trigger like other append-only tables, FKs registered in
`access/references.py`), the `dispatch` context (commands assign/reassign/cancel/
start/complete/return with role checks and idempotent exact repeats; queries mine/all
by status and project) and tests including forward upgrade with existing rows. Phase
B: operations with the reseal, router/adapter wiring, «Диспетчер» screen in the
«Работа» menu group (admin; expert read-only of own), «Мои задачи» block on the home
screen. Report `docs/program/W61-DISPATCHER-01.md`.

## Required tests

Phase A: focused integration tests on the lane's own containers and the migration
upgrade. Phase B: `tests/contract`, `api:verify`, lint, typecheck, changed vitest
files, rendered-language guard, journey static conformance. No full gate.

## Integration contract

Phases A and B merge as one slice; until phase B the migration is inert.

## Failure/idempotency/security cases

Assign to a non-expert or archived account refused; expert cannot assign; an expert
changes only own assignments; an exact repeat returns the same state; conflicting
transitions refused; purge of an assignee refused while referenced.

## Rollback / feature flag

Revert the merge; migration 0025 downgrade drops only its two tables.
