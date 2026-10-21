# Task W60-OPT-MATCH-01 — «Спецификация и цены»: the AR specification matched to the project price list

task_id: W60-OPT-MATCH-01

## Outcome

On the project's «Оптимизация» tab an expert sees, for the current AR version of a
document set, the specification rows extracted deterministically from the newest
published run's saved text (the nine Form-7 columns where present: позиция,
наименование и характеристика, тип/марка, код, завод-изготовитель, ед. изм., кол-во,
масса, примечание — with page and sheet), each matched against the current price-list
revision as matched / ambiguous / unmatched with the reason. A price and an amount
appear only on matched rows with a numeric quantity in the same unit and currency; the
total covers only those rows and states how many rows it excludes. Nothing is
persisted and no finding is changed.

## Depends on

- `W60-PRICE-LIST-01` phase A (`6d86b991`): price-list revisions/positions and effective
  vendor lists; this slice merges after it.
- `W59-SECTION-SEAL-01` (confirmed section AR), comparison's saved-text reader pattern.

## Frozen inputs

- base commit: `6d86b991` on `agent/w60-price-list-01` (contains `origin/dev` `0f0903f2`,
  dispatcher `0025`, price lists `0026`);
- binding rules: `ROADMAP-TO-BETA.md` §10 A-4/A-5 (money only from the uploaded price
  list, only for matched positions; no price → no figure, absent not 0), W60 PROJECT-OPT
  acceptance (`CODE-FIRST-SCOPE-W58-W63.md`), the legacy Form-7 column set
  (`/root/projects/PDF-proverka/docs/section_optimization.md`), rulings `R-135`, `R-139`;
  no LLM, no new dependency.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/support/expected_facts.json
- enumerator_owner: W60-OPT-MATCH-01 (phase B only, after the integrator hands over the contract slot)
- totality_query: `python3 -c "import json;d=json.load(open('tests/support/expected_facts.json'));print(d['surface'])"`

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

- `src/auditmanager/optimisation/specification.py`
- `src/auditmanager/optimisation/matching.py`
- `src/auditmanager/optimisation/project_match.py`
- `tests/unit/optimisation/test_specification*.py`
- `tests/unit/optimisation/test_matching*.py`
- `tests/integration/optimisation/test_project_match*.py`
- `src/auditmanager/optimisation/public.py`
- `contracts/api/v1/**`
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
- `web/src/_pages/project-detail/**`
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
- `docs/program/W60-OPT-MATCH-01.md`
- `docs/program/tasks/W60-OPT-MATCH-01.md`

**Phasing (binding):** phase A may touch only the first six paths and the two docs
files (and read everything). Every other path opens only after the integrator's
message that hands over the contract slot.

## Lane resources

- foundation_instance: `auditmanager-w60-opt-match`
- postgres_port: `57580`
- s3_api_port: `61180`
- s3_console_port: `61181`
- postgres_db: `auditmanager_w60_opt_match`
- s3_bucket: `auditmanager-w60-opt-match`

## Forbidden hotspots

Migrations, dependency files, `web/src/_app/providers.tsx`, global styles, the price-list
lane's other `optimisation/**` modules (read only), `findings/**`, `decisions/**`,
`CURRENT_STATE.md`, refs, tags, the stand.

## Non-goals

No proposals, no persistence, no LLM, no currency conversion, no price guessing, no
section optimisation, no full gate.

## Deliverables

Phase A: a deterministic specification extractor (tables in the saved text layer:
header detection, multi-line names, units, numeric quantities with decimal comma) and a
matcher (normalised name + unit, code/mark when present, ambiguity when two positions
tie), a project-match query, tests on recorded/saved text. Phase B: one read operation
with the reseal and the «Спецификация и цены» view on the «Оптимизация» tab. Report
`docs/program/W60-OPT-MATCH-01.md`.

## Required tests

Phase A: unit tests on real-shaped table text (including the local AR set's saved text
if present in fixtures), integration on the lane's own containers. Phase B:
`tests/contract`, `api:verify`, lint, typecheck, changed vitest files, rendered-language
guard, journey static conformance. No full gate.

## Integration contract

Phases A and B merge as one slice, after `W60-PRICE-LIST-01`.

## Failure/idempotency/security cases

No published run, unclassified or non-AR version, no current price list → explicit
states, not errors hidden as empty tables; a total never includes an unmatched,
ambiguous, unit-mismatched or currency-mismatched row.

## Rollback / feature flag

Revert the merge; nothing persisted.
