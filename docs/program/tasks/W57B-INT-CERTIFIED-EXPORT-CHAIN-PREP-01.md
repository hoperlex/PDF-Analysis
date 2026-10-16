# Task W57B-INT-CERTIFIED-EXPORT-CHAIN-PREP-01 — unserved certified XLSX chain

task_id: W57B-INT-CERTIFIED-EXPORT-CHAIN-PREP-01

## Outcome

One unserved export use case composes the completed W57b run/page preflight, W57a certified citation reader port, certified-source projection and XLSX package in the caller's read transaction. It refuses mismatched Run, Version, profile, snapshot or retrieval-set identity before returning bytes. A focused offline test obtains actual XLSX bytes and proves a changed persisted pin or foreign citation read refuses.

## Depends on

- `W57A-INT-CITE-READ-PREP-01` — completed unserved persisted citation reader.
- `W57B-INT-XLSX-RUN-SOURCE-PREFLIGHT-01` — completed exportable Run and verified page-label read.
- `W57B-INT-XLSX-PACKAGE-PREP-01` — completed caller-authorized XLSX package.
- `W57B-INT-XLSX-CERTIFIED-SOURCES-PREP-01` — completed citation-partition projection.
- `CFB-INT-DEV-PUBLISH-53` — completed development base `110d632343b35d77b9d55a5c8ae453bbeca14ef5`.

## Frozen inputs

- base commit: `110d632343b35d77b9d55a5c8ae453bbeca14ef5`
- API v1 SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain IDs SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations` SHA-256: `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- XLSX preflight SHA-256: `4e65b020e5b96ce3f5b78c6c813b799fb184c460caa253ff433a5b9386f12f34`;
- certified-source projection SHA-256: `f969187899a7eb794a258ede07e2777998854393813e68deed1503b69af93e90`;
- XLSX package SHA-256: `827481da674733c898c5d15dccc7117124c328904185379ce5d100a3d6bc9fc9`;
- citation reader SHA-256: `7ccc297b4a505837bb7a13464c46cf40dddd283b7d56aaa90e051fec5dc9ba03`;
- `docs/program/dispatch/W57-PLAN.md` B3.5–B3.6 and `CODE-FIRST-TO-BETA.md` R-135 cadence.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: dev53 has four completed, unserved XLSX source/render stages but no application-level chain that checks one Run's persisted pin around their composition. W57b `0024` and the route remain unsealed; the real LibreOffice B3.5 probe failed on this host.

### P-01 — exact base, entrypoints and absent chain

- captured_at: 2026-10-16
- command: `git rev-parse HEAD; rg -n '^def (read_xlsx_run_source_preflight|read_verified_citations|sources_from_certified_reads|prepare_xlsx_package)' src/auditmanager/exports/xlsx/preflight.py src/auditmanager/findings/citation_reader.py src/auditmanager/exports/xlsx/certified_sources.py src/auditmanager/exports/xlsx/package.py; git ls-tree -r --name-only HEAD src/auditmanager/exports/xlsx/certified_package.py tests/integration/exports/test_xlsx_certified_package.py`
- captured_output:
  ```text
  110d632343b35d77b9d55a5c8ae453bbeca14ef5
  src/auditmanager/exports/xlsx/package.py:86:def prepare_xlsx_package(
  src/auditmanager/exports/xlsx/certified_sources.py:60:def sources_from_certified_reads(
  src/auditmanager/findings/citation_reader.py:196:def read_verified_citations(
  src/auditmanager/exports/xlsx/preflight.py:40:def read_xlsx_run_source_preflight(
  ```
- interpretation: a narrow additive chain can be written without touching the completed readers, package, shared contract or migration. The listed functions are unserved and their presence does not imply qualified corpus or route readiness.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/exports/xlsx/certified_package.py`
- `tests/integration/exports/test_xlsx_certified_package.py`
- `docs/program/tasks/W57B-INT-CERTIFIED-EXPORT-CHAIN-PREP-01.md`
- `docs/program/W57B-INT-CERTIFIED-EXPORT-CHAIN-PREP-01.md`

## Forbidden hotspots

- existing XLSX readers, package, writer, public facade and CSV modules;
- findings modules/public facade, API/routers/security, bootstrap/composition root;
- `contracts/**`, migrations, root dependencies/locks, global styles;
- W54/W56b modules, corpus, DB/S3 instances, credentials, `CURRENT_STATE.md`, remote refs and tags.

## Non-goals

No `0024_norm_references` seal, `exportRunXlsx` route/role, actual authorization decision, registered v3 profile, qualified corpus, source PDF publication, real DB/S3, real LibreOffice probe, full gate, live export or beta acceptance. The caller supplies a sealed profile ID and independently authorized decision later; this chain does not make either decision.

## Deliverables

An additive XLSX use-case entrypoint, focused offline actual-XLSX and refusal tests, formal task and result report, exact-path handoff and local commit.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/exports/test_xlsx_certified_package.py tests/integration/exports/test_xlsx_certified_sources.py tests/integration/exports/test_xlsx_package.py`;
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/program/test_wave_governance.py`;
- `python3 -m py_compile src/auditmanager/exports/xlsx/certified_package.py tests/integration/exports/test_xlsx_certified_package.py`;
- frozen SHA-256, `git diff --check`, exact allowlist and `scripts/task_handoff.py` PASS.

## Integration contract

`prepare_certified_xlsx_package(session, run_id, authorization, read_blob, read_citations, profile_id, attribution)` takes the caller's consistent read transaction. The caller has already established the principal's export policy decision and supplies the sealed registered v3 profile ID, verified Blob reader and a findings-public citation-read callback. The function checks authorization shape and exact run before I/O, calls run/page preflight, reads the persisted Run pin, invokes the citation callback, compares run/project/version/state/profile/snapshot/set identity, projects certified citations and invokes the existing package. It checks the persisted pin again before returning bytes. It neither imports a findings-internal module nor opens a transaction or stores output. A future owned API/service slot may call it only after the 0024 route/role seal and real source acceptance.

## Failure/idempotency/security cases

Denied/foreign/malformed authorization or missing profile/read callbacks refuse before source reads. A changed or missing Run pin, foreign citation read, incomplete citation partition or absent package refuses. The existing readers independently fail on damaged page Blob and uncertified citation rows. Repeated immutable inputs produce equal bytes. The caller rolls back a refused read transaction; this function performs no write or commit.

## Rollback / feature flag

Unserved additive code; revert the bounded commit before runtime wiring. No data rollback or feature flag is needed.

## Handoff

- changed files: four exact allowed paths;
- checks, limitations and integration guidance: paired result report;
- contracts/migrations: none;
- forbidden hotspots: unchanged.
