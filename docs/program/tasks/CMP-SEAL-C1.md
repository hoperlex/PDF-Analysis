# Task CMP-SEAL-C1 — the seal of wave C1: contract 1.10.0, migration 0039, the version-comparison core surface

## Outcome
On `integration/compare-modules` the contract is `1.10.0` with every C1 operation sealed as a stub, migration `0039`
creates the C1 tables and migrates the `0035` sheet-pair approvals into manual matrix edits (`Q-CMP-8`), the carried
contract prose and reason registrations are done, and every pin these facts move is updated, so that the C1 lanes
(MATRIX, ENGINE, VIEWER, SERIES, OVERVIEW, VC-UI-01) start on a green tree.

## Depends on
- wave C0 closed (`docs/program/CMP-WAVE-C0-REPORT.md`); `origin/dev` `a5c0889e` merged (`b8ff0f8e`)

## Frozen inputs
- API contract: `1.9.0`, 115/130/351 at the base; domain contract `contracts/domain/v1/**` at the base
- analysis/comparison/event contract: ADR-0025 decisions 3, 13, 14, 15, 21, 23, 25 and the addendum
- migration head: `0038_comparison_foundation` (this seal takes `0039`, revision id ≤ 32 characters)
- base commit: the integration tip named in the dispatch message

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json`
- enumerator_owner: CMP-SEAL-C1
- totality_query: the `tools/plan/pin_sweep.py` modes used by CMP-SEAL-C0 (see `docs/program/CMP-SEAL-C0.md` §6)

## Captured premise evidence
- premise: print contract version, surface counts, head and VERSION before any edit; STOP if they differ from the
  dispatch message

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- the allowed paths of `docs/program/tasks/CMP-SEAL-C0.md`, plus any file the disposable probe proves pins a fact this
  seal moves (listed with its reason in the report)

## Lane resources
- foundation_instance: `auditmanager-cmp-seal-c1`
- postgres_port: `57820`
- s3_api_port: `61820`
- s3_console_port: `61821`
- postgres_db: `auditmanager_cmp_seal_c1`
- s3_bucket: `auditmanager-cmp-seal-c1`

## Forbidden hotspots
- as CMP-SEAL-C0; no product logic beyond stubs; `src/auditmanager/jobs/**`, `infra/deploy/compose.server.yml`

## Non-goals
- no matrix algorithm, engine, series runner, viewer or screen; the C1 lanes build them

## Deliverables
1. Disposable apply-and-run probe first; its red list is the grant list.
2. Contract `1.10.0` (additive minor), sealed stubs, roles per ADR-0025 decision 16, keyed writes, for (names are
   proposals; keep the `cpr_` style of addressing, no ordinal in a path):
   - the effective matrix of a document set (rows = sheet identities, columns = versions in the current comparison
     order, cells with confidence `high|medium|group|manual|ai`, flags split/duplicate/scan/bridge, unmatched cells with
     candidates, absent cells), its revision, staleness against the order revision and the profiles;
   - manual matrix edits as a keyed batch carrying the base matrix revision (stale base → `conflict` with a reason),
     undo of the last edit, the edit history;
   - accepted AI links (table and read only; C2 writes them);
   - series of adjacent transitions for the current order: start («Запустить» / «Заново»), read, pause, resume,
     cancel, «Досчитать»; per transition the summary counts and the deterministic verdict;
   - per-sheet-pair results of a transition: status, reasons, the eight channels, region classes, text changes with
     numbers, permit reconciliation, parts coverage; a pair tile read (`overlay|a|b`, level/column/row, layers,
     `align_blocks`);
   - the overview of a project for «Проекты и этапы» (per set: the seven steps' states and counts, the next step,
     totals, pending uploads);
   - a read for the read-only «Сравнение» block of «Очередь» (CMP-WORK-01 finding);
   - an optional field on the upload for «После подготовки сравнить все соседние версии» (CMP-INGEST-02 finding).
3. Migration `0039`: the tables for the above (per-version/per-project rows reachable from `project`; content-keyed
   results with ULID ids and a unique content key incl. `project_uid`, ADR-0025 decision 15); the data migration that
   turns every active `comparison_sheet_link` approval into a manual matrix edit with the `0035` ids in its provenance
   (`0035` rows stay immutable history); up/down on an isolated database; the per-table family (`CMP-SEAL-C0` §6).
4. While the versions module is on, `approveSheetPairing`, `withdrawSheetPairing` and `generateComparisonSummary`
   answer `dependency_unavailable` with a reason naming the new module (ADR-0025 decision 13; implement this guard —
   it is one condition on an existing operation, not product logic).
5. Contract prose carried from the PW5 integrator (D-246, D-251, D-253): `submitRegistration` and its state machine
   (day cap 40 per 24 h counting pending and approved; the 100-pending cap), `exportRunCsv` (leading-apostrophe rule),
   the preset error words (unknown_preset, preset_archived, preset_name_in_use, preset_limit_reached,
   differs_from_current, conflicts_with_executor_connection_id).
6. Register the reasons not yet in the contract notes: the 13 `comparison_zip_*` (`docs/program/CMP-INGEST-ZIP-01.md`
   §7) and those of `docs/program/CMP-INGEST-01.md` §6 item 7.
7. Generated client, `FRONTEND_LOCK.json` reseal, pins (contract version, surface, head, per-table family, identifier
   catalogue for new prefixes, stub enumerators, P02_TABLES), the report `docs/program/CMP-SEAL-C1.md` with a per-lane
   table (operations and tables each C1 lane implements).

## Required tests
- as `docs/program/tasks/CMP-SEAL-C0.md` (contract minus D-220, web lint/typecheck/vitest/api:verify, journey
  conformance, the db/recovery/composition/p02_journey/foundation directories on the lane stack, migration round
  trip including the data migration on a database seeded with `0035` approvals)

## Integration contract
Every C1 operation answers `503 dependency_unavailable` until its lane wires it; lanes STOP to the FIX slot for a
missing field.

## Failure/idempotency/security cases
- the data migration is idempotent and never deletes or edits a `0035` row; a stale base revision never applies an
  edit; content keys include `project_uid`

## Rollback / feature flag
`comparison_modules` stays `none` by default; the three `0035` operations keep working while the module is off.

## Handoff
- changed files:
- commands/results:
- known limits:
- integration notes:
