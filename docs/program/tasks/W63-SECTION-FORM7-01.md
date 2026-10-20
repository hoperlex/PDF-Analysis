# Task W63-SECTION-FORM7-01 — «Оптимизация разделов»: the section's combined Form-7 specification

task_id: W63-SECTION-FORM7-01

## Outcome

«Оптимизация разделов» (today an honest stub) shows, for a chosen section, the combined
Form-7 specification of the current versions of every project whose current version
is confirmed in that section: the nine columns, with project, document set, version,
page and sheet on every row, filtered by project and searched by text, plus per-row
price matches against each row's own project price list where one exists. Rows are
never merged across projects and no figure appears without a matched price. It is a
read view; replication of accepted optimisations stays a later slice.

## Depends on

- `W60-OPT-MATCH-01` phase A (`67fd24c0`: specification extractor and matcher); merges
  after it and after `W60-PRICE-LIST-01`.

## Frozen inputs

- base commit: `67fd24c0` on `agent/w60-opt-match-01`;
- binding rules: `W59-SECTION-IDENTITY-DECISION-01.md` (section code is a filter, not an
  identity; sources addressed by exact project/set/version/confirmed section; no
  automatic propagation), `ROADMAP-TO-BETA.md` §10 A-4/A-5/A-6, legacy Form 7
  (`/root/projects/PDF-proverka/docs/section_optimization.md`), rulings `R-135`,
  `R-139`; no LLM, no migration, no new dependency.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/support/expected_facts.json
- enumerator_owner: W63-SECTION-FORM7-01 (phase B only, after the integrator hands over the contract slot)
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

- `src/auditmanager/optimisation/section_specification.py`
- `tests/unit/optimisation/test_section_specification*.py`
- `tests/integration/optimisation/test_section_specification*.py`
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
- `web/src/shared/config/screen-registry.ts`
- `web/src/entities/**`
- `web/src/widgets/section-specification/**`
- `web/src/_pages/section-optimisation/**`
- `web/src/app/section-optimisation/**`
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
- `docs/program/W63-SECTION-FORM7-01.md`
- `docs/program/tasks/W63-SECTION-FORM7-01.md`

**Phasing (binding):** phase A may touch only the first three paths and the two docs
files. Every other path opens only after the integrator's message.

## Lane resources

- foundation_instance: `auditmanager-w63-section-form7`
- postgres_port: `57600`
- s3_api_port: `61200`
- s3_console_port: `61201`
- postgres_db: `auditmanager_w63_section_form7`
- s3_bucket: `auditmanager-w63-section-form7`

## Forbidden hotspots

Migrations, dependency files, `web/src/_app/providers.tsx`, global styles,
`specification.py`/`matching.py` (owned by `W60-OPT-MATCH-01`; additive use only),
`CURRENT_STATE.md`, refs, tags, the stand.

## Non-goals

No replication, no proposals, no persistence, no cross-project linking, no LLM, no full
gate.

## Deliverables

Phase A: a section query composing the extractor over every eligible project's current
version (bounded: projects and rows paged, documented caps, explicit per-project states
for missing analysis/text) and tests. Phase B: one read operation with the reseal and
the «Оптимизация разделов» page replacing the stub (section picker in S-5 order,
project filter, search, rows with provenance, matched prices per row's project).
Report `docs/program/W63-SECTION-FORM7-01.md`.

## Required tests

Phase A: unit + integration on the lane's own containers (two projects, one section,
rows never merged). Phase B: `tests/contract`, `api:verify`, lint, typecheck, changed
vitest files, rendered-language and prepared-sections guards, journey static
conformance. No full gate.

## Integration contract

Phases A and B merge as one slice, after `W60-OPT-MATCH-01`.

## Failure/idempotency/security cases

A project whose current version is in another section never appears; an unclassified
version is listed as excluded with its reason; totals never mix projects or currencies.

## Rollback / feature flag

Revert the merge; the stub returns.
