# Task W59-DECISION-CARRYOVER-01 — expert-confirmed carryover of decisions to the next version

task_id: W59-DECISION-CARRYOVER-01

## Outcome

On «Сравнение версий», for a finding-match proposal «Без изменений» whose source
finding carries an expert decision, an expert confirms «Перенести решение»; the
target finding receives a new decision event that records the carried-from finding,
decision and version, the confirming expert and time. Nothing is carried without that
confirmation; source decisions, findings and the raw comparison evidence are never
modified; a «Вероятно, устранено» source can be marked resolved only by an explicit
expert decision on the target.

## Depends on

- `W59-VERSION-COMPARE-01` — completed, merged.
- Completed preparations `W59-INT-DECISION-CARRYOVER-PREP-01`, `W59-INT-CARRYOVER-BOUNDS-01`.

## Frozen inputs

- base commit: `1049367e110cea2437abb85be8bbc532e018e26b` (`origin/dev`);
- API at base: 51 paths / 58 operations / 147 schemas; head `0024_version_classification`;
  `W61-DISPATCHER-01` owns migration `0025` on its branch — this task may take `0026`
  only on top of it;
- rulings: `R-60` (admin without expert does not decide), `R-135`, `R-139`; AGENTS §4
  (LLM output never the canonical decision; AI never edits raw comparison evidence).

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/support/expected_facts.json
- enumerator_owner: W59-DECISION-CARRYOVER-01 (phase B only, after the integrator hands over the contract slot)
- totality_query: `python3 -c "import json;d=json.load(open('tests/support/expected_facts.json'));print(d['surface'],d['migration_head'])"`

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

- `src/auditmanager/comparison/**`
- `src/auditmanager/decisions/**`
- `tests/integration/comparison/**`
- `tests/integration/decisions/**`
- `tests/unit/comparison/**`
- `db/migrations/versions/**`
- `tests/integration/db/**`
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
- `web/src/entities/**`
- `web/src/features/**`
- `web/src/widgets/**`
- `web/src/_pages/stage-comparison/**`
- `web/src/app/projects/**`
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
- `docs/program/W59-DECISION-CARRYOVER-01.md`
- `docs/program/tasks/W59-DECISION-CARRYOVER-01.md`

**Phasing (binding):** phase A may touch only the first five paths, plus — only if a
column/table is unavoidable — `db/migrations/versions/**` and `tests/integration/db/**`
for a migration `0026` chained on `W61-DISPATCHER-01`'s `0025` after merging that
lane's phase A commit, and the two docs files. Every other path opens only after the
integrator's message that hands over the contract slot.

## Lane resources

- foundation_instance: `auditmanager-w59-carryover`
- postgres_port: `57560`
- s3_api_port: `61160`
- s3_console_port: `61161`
- postgres_db: `auditmanager_w59_carryover`
- s3_bucket: `auditmanager-w59-carryover`

## Forbidden hotspots

Dependency files, `web/src/_app/providers.tsx`, global styles, the dispatcher's
`dispatch/**` and migration `0025`, `CURRENT_STATE.md`, refs, tags, the stand.

## Non-goals

No automatic carryover, no AI summary, no carryover across different sections/stages
except the П→Р mode's explicit pairs, no bulk «перенести всё» without listing each
item, no full gate.

## Deliverables

Phase A: carryover command/query over the prepared modules with tests. Phase B: one
write operation (and a read if needed) with the reseal, and the confirm action on the
comparison page. Report `docs/program/W59-DECISION-CARRYOVER-01.md`.

## Required tests

Phase A: focused integration tests on the lane's own containers. Phase B:
`tests/contract`, `api:verify`, lint, typecheck, changed vitest files, rendered-language
guard, journey static conformance. No full gate.

## Integration contract

Phases A and B merge as one slice, after `W61-DISPATCHER-01` if a migration `0026`
exists.

## Failure/idempotency/security cases

Expert-only; exact repeat returns the same event; a target that already has a
decision refuses a conflicting carryover; foreign or mismatched pairs refused; the
proposal list is recomputed and must still contain the pair at confirmation time.

## Rollback / feature flag

Revert the merge; carried decisions remain ordinary append-only decision events.
