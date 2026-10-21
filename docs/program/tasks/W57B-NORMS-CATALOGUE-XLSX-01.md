# Task W57B-NORMS-CATALOGUE-XLSX-01 — norms catalogue and the run's Excel export

task_id: W57B-NORMS-CATALOGUE-XLSX-01

## Outcome

1. «Нормы» gains a catalogue: every norm document of the current snapshot listed
   with a readable designation, title, kind/status where the corpus has them, page
   count and paragraph count, filtered by text and kind, paged and sorted by
   designation; each row opens the existing norm document page. Truncated
   designations derived from file names (e.g. «Приказ МЧС России от 24 04 2013 N 288
   (ред») are shown through a deterministic display derivation, never by altering
   snapshot rows.
2. A run's page offers «Скачать Excel»: the run's findings in the legacy layout of
   `W57-PLAN.md` §B3.5 through the existing certified XLSX chain
   (`src/auditmanager/exports/xlsx/**`); norm columns carry a finding's citations
   when present and stay empty otherwise.

## Depends on

- `W54-LOCAL-IMPORT-01` — completed (local stand with the real corpus at
  `127.0.0.1:57490`/`57590` for read-only probes).
- Completed XLSX preparations of W57b (`exports/xlsx/**`).

## Frozen inputs

- base commit: `890deb80d3fe66778e7d920ee5bfe784ce007c3f` (`integration/night-1020`);
- API contract at base: 48 paths / 55 operations / 131 schemas; before phase B the
  seal and comparison lanes move it — phase B starts from the integration commit
  the integrator names;
- rulings: `R-135`, `R-139`; `W57-PLAN.md` §B3.5–§B3.7 (layout, screens).

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/support/expected_facts.json
- enumerator_owner: W57B-NORMS-CATALOGUE-XLSX-01 (phase B only, after the integrator hands over the contract slot)
- totality_query: `python3 -c "import json;d=json.load(open('tests/support/expected_facts.json'));print(d['path_count'],len(d['operations']),len(d['schema_names']))"`

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

- `src/auditmanager/norms/catalogue/**`
- `src/auditmanager/norms/public.py`
- `src/auditmanager/exports/**`
- `tests/integration/norms/**`
- `tests/unit/norms/**`
- `tests/integration/exports/**`
- `tests/unit/exports/**`
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
- `web/src/_pages/norms/**`
- `web/src/_pages/run/**`
- `web/src/app/norms/**`
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
- `docs/program/W57B-NORMS-CATALOGUE-XLSX-01.md`
- `docs/program/tasks/W57B-NORMS-CATALOGUE-XLSX-01.md`

**Phasing (binding):** phase A may touch only `src/auditmanager/norms/catalogue/**`,
`src/auditmanager/norms/public.py`, `src/auditmanager/exports/**`, the norms/exports
test directories and the two docs files. Every other path opens only after the
integrator's message that hands over the contract slot, from the commit it names.

## Lane resources

- foundation_instance: `auditmanager-w57b-catalogue-xlsx`
- postgres_port: `57510`
- s3_api_port: `61110`
- s3_console_port: `61111`
- postgres_db: `auditmanager_w57b_catalogue_xlsx`
- s3_bucket: `auditmanager-w57b-catalogue-xlsx`

## Forbidden hotspots

Migrations, dependency files, `web/src/_app/providers.tsx`, global styles,
`CURRENT_STATE.md`, snapshot rows and the bundle, the local norms stand's data
(read-only probes only), refs, tags, the stand.

## Non-goals

No `normative_refs` category, no 0024/0025 migration, no new error code, no
LibreOffice probe on this host (it failed before; the zip/XML structure is tested
directly), no live provider call, no full gate.

## Deliverables

Phase A: catalogue query/service and the XLSX serving service with tests. Phase B:
`listNormDocuments` and `exportRunXlsx` with the reseal, routers/adapters/role table
(catalogue: any role; export: as `exportRunCsv`), the catalogue view on `/norms` and
the export button on the run page. Report `docs/program/W57B-NORMS-CATALOGUE-XLSX-01.md`.

## Required tests

Phase A: focused unit/integration tests; read-only probe of the catalogue query on
the local real-corpus stand (counts, sample designations). Phase B: `tests/contract`,
`api:verify`, lint, typecheck, changed vitest files, journey static conformance. No
full gate, no live journey.

## Integration contract

Phase A and B merge together as one slice. The catalogue reads the current snapshot
only; with no current snapshot it answers like `searchNorms` (422
`required_norm_unavailable`).

## Failure/idempotency/security cases

Unknown filters refused by validation; paging stable; export of a foreign/unfinished
run refused as `exportRunCsv` does; XLSX bytes deterministic for the same run state.

## Rollback / feature flag

Revert the merge; no data migration.
