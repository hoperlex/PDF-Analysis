# Task W57B-INT-XLSX-CERTIFIED-SOURCES-PREP-01 — certified citation input for XLSX

task_id: W57B-INT-XLSX-CERTIFIED-SOURCES-PREP-01

## Outcome

The existing XLSX package can receive actual W57a certified canonical and member citation partitions, together with the same run's verified page labels. A focused test renders XLSX bytes and reads its norm columns from `sheet2.xml`, including a certified zero case. No route is activated.

## Depends on

- `W57A-INT-CITE-READ-PREP-01` — completed unserved 0023 certified citation reader.
- `W57B-INT-XLSX-RUN-SOURCE-PREFLIGHT-01` — completed exportable-run and verified-page source.
- `W57B-INT-XLSX-PACKAGE-PREP-01` — completed caller-authorized XLSX composition.
- `CFB-INT-DEV-PUBLISH-46` — completed development base `95de4f6b4e10a8b60f57ae84ab66156917c7b96c`.

## Frozen inputs

- base commit: `95de4f6b4e10a8b60f57ae84ab66156917c7b96c`
- API v1 SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain IDs SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations` SHA-256: `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- citation reader SHA-256: `7ccc297b4a505837bb7a13464c46cf40dddd283b7d56aaa90e051fec5dc9ba03`;
- XLSX preflight SHA-256: `4e65b020e5b96ce3f5b78c6c813b799fb184c460caa253ff433a5b9386f12f34`;
- XLSX package SHA-256: `827481da674733c898c5d15dccc7117124c328904185379ce5d100a3d6bc9fc9`;
- `docs/program/dispatch/W57-PLAN.md` B3.5–B3.6 and R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: dev46 has a certified W57a citation read and a W57b XLSX package that requires caller-supplied citations, but no adapter carries those partitions into the workbook.

### P-01 — exact base and available entrypoints

- captured_at: 2026-10-16
- command: `git rev-parse HEAD; rg -n '^def (read_verified_citations|read_xlsx_run_source_preflight|prepare_xlsx_package)' src/auditmanager/findings/citation_reader.py src/auditmanager/exports/xlsx/preflight.py src/auditmanager/exports/xlsx/package.py; git ls-tree -r --name-only HEAD src/auditmanager/exports/xlsx/certified_sources.py`
- captured_output:
  ```text
  95de4f6b4e10a8b60f57ae84ab66156917c7b96c
  src/auditmanager/exports/xlsx/package.py:86:def prepare_xlsx_package(
  src/auditmanager/findings/citation_reader.py:196:def read_verified_citations(
  src/auditmanager/exports/xlsx/preflight.py:40:def read_xlsx_run_source_preflight(
  ```
- interpretation: completed readers/package exist, while this additive source adapter does not. Their presence does not prove qualified corpus publication, real DB/Blob custody or API readiness.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/exports/xlsx/certified_sources.py`
- `tests/integration/exports/test_xlsx_certified_sources.py`
- `docs/program/tasks/W57B-INT-XLSX-CERTIFIED-SOURCES-PREP-01.md`
- `docs/program/W57B-INT-XLSX-CERTIFIED-SOURCES-PREP-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies and lockfiles;
- existing W57a findings reader/public facade, W57b XLSX query/package/writer;
- W54/W56b modules, CSV service, API/routers, bootstrap/composition root;
- `CURRENT_STATE.md`, UI/global styles, remote refs and tags.

## Non-goals

No `0024_norm_references` seal, `exportRunXlsx` API/role/route, real Run/Blob/corpus publication, qualified snapshot, registered v3 profile, W57a CITE activation, authorization grant, transaction ownership, download filename, spreadsheet-application probe or beta claim. Constructed DTOs and source references do not independently prove custody.

## Deliverables

Additive citation-to-XLSX source adapter, actual XLSX-cell and refusal tests, formal task and result report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/exports/test_xlsx_certified_sources.py tests/integration/exports/test_xlsx_package.py tests/integration/exports/test_xlsx_preflight.py tests/integration/findings/test_w57a_citation_reader_offline.py`;
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/program/test_wave_governance.py`;
- `python3 -m py_compile src/auditmanager/exports/xlsx/certified_sources.py tests/integration/exports/test_xlsx_certified_sources.py`;
- `git diff --check`, frozen SHA-256 and `scripts/task_handoff.py` PASS.

## Integration contract

The later authorized caller supplies `VerifiedXlsxRunSource` and the W57a reader's certified citation DTO from one consistent transaction, plus explicit attribution. The adapter checks exact run/version/state and page source identity, requires each supplied observation partition's certified count, ordered citations and unique observation identity, then carries canonical citations followed by all member citations into `ExportSources`; an explicit certified zero yields `()`. The existing XLSX query requires a citation entry for every finding and refuses a missing finding partition. The adapter intentionally avoids a deep import into the findings bounded context; a later owned public facade/API slot must expose that read to runtime. The caller must establish the actual reader provenance and sealed authorization separately.

## Failure/idempotency/security cases

Foreign run, version, state or page source, duplicate finding or observation, missing canonical partition, absent citation rows, count mismatch and noncontiguous ordinals refuse. A missing finding cannot silently become certified zero: the package query checks the complete finding-key partition. The transformation is read-only and deterministic; repeated inputs produce equal XLSX bytes. Formula-like values remain text under the existing writer.

## Rollback / feature flag

Unserved additive source; revert the bounded commit before activation. No data rollback or feature flag.

## Handoff

- changed files: four exact allowed paths;
- commands/results: accompanying report and ignored technical handoff;
- known limits: synthetic reader DTOs and fake SELECTs only, no real service/corpus acceptance;
- integration notes: cherry-pick after dev46; bind through later W57a public-reader and W57b 0024/API owners.
