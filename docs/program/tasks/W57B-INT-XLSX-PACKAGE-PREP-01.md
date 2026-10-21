# Task W57B-INT-XLSX-PACKAGE-PREP-01 — compose the XLSX package

task_id: W57B-INT-XLSX-PACKAGE-PREP-01

## Outcome

One additive service composes the completed read adapter, projection and XLSX
writer. A ZIP-level test proves the canonical row, member, citation and
literal formula-like text survive the chain; missing authorization or source
material refuses before a package is returned.

## Depends on

- `W57B-INT-XLSX-READ-PREP-01` — completed SELECT-only finding reader.
- `W57B-INT-XLSX-PROJECTION-PREP-01` — completed typed projection.
- `W57B-INT-XLSX-WRITER-PREP-01` — completed deterministic writer.

## Frozen inputs

- base commit: `e4cf264bc71375f85625d9ab3ad110316815d046`.
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §B3.5.
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`.
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
  error catalogue SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
  analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
  provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`.
- migration head `0022_findings_v2`; no head movement.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the pinned tree has all three XLSX stages, but no package service.

### P-01 — exact base and missing additive paths

- captured_at: 2026-10-15
- command: `git rev-parse HEAD && git ls-tree -r --name-only HEAD src/auditmanager/exports/xlsx/package.py tests/integration/exports/test_xlsx_package.py docs/program/tasks/W57B-INT-XLSX-PACKAGE-PREP-01.md docs/program/W57B-INT-XLSX-PACKAGE-PREP-01.md`
- captured_output:
  ```text
  e4cf264bc71375f85625d9ab3ad110316815d046
  ```
- interpretation: the four task paths are additive on this base.

### P-02 — completed chain entrypoints

- captured_at: 2026-10-15
- command: `rg -n '^def (read_xlsx_projection|project_workbook|render_xlsx)' src/auditmanager/exports/xlsx/query.py src/auditmanager/exports/xlsx/projection.py src/auditmanager/exports/xlsx/writer.py`
- captured_output:
  ```text
  src/auditmanager/exports/xlsx/writer.py:334:def render_xlsx(source: WorkbookInput) -> RenderedWorkbook:
  src/auditmanager/exports/xlsx/projection.py:189:def project_workbook(run: RunRead, findings: tuple[FindingRead, ...]) -> WorkbookInput:
  src/auditmanager/exports/xlsx/query.py:55:def read_xlsx_projection(
  ```
- interpretation: the service can call the already completed stages without editing them; this says nothing about sealed policy or source verification.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/exports/xlsx/package.py`
- `tests/integration/exports/test_xlsx_package.py`
- `docs/program/tasks/W57B-INT-XLSX-PACKAGE-PREP-01.md`
- `docs/program/W57B-INT-XLSX-PACKAGE-PREP-01.md`

## Forbidden hotspots

Existing query, projection, writer, CSV, routes, services, contracts,
migrations, composition root, root dependencies/locks, global styles, corpus,
`CURRENT_STATE.md`, tags and remote refs.

## Non-goals

No role/state policy, proof of a policy decision, page-label or citation source
verification, filename, HTTP route, transaction ownership, live database,
spreadsheet application probe, complete gate, release or beta acceptance.

## Deliverables

Typed composition service, focused ZIP and refusal tests, task report and
exact changed-path proof.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/exports/test_xlsx_package.py tests/integration/exports/test_xlsx_read_query.py tests/integration/exports/test_xlsx_projection_prep.py tests/integration/exports/test_xlsx_writer_prep.py` — pass;
- Python compilation, direct governance, whitespace and exact changed-path proof — pass;
- no `make gate` under R-135.

## Integration contract

`prepare_xlsx_package(session, authorization=..., sources=...)` receives an
explicit `ExportAuthorization` with the exact run, principal, operation,
`allow` decision and decision reference from the future sealed caller. It
receives `ExportSources` with verified page-label and citation mappings,
nonempty source references and attribution. It calls the SELECT-only adapter,
then the pure projection and writer in the caller's consistent transaction.
It returns `PreparedXlsx` with bytes, content type, replacement count and all
three references, or `None` for an absent run. It does not interpret a claimed
decision or source reference as independent proof of authorization or custody.

## Failure/idempotency/security cases

Missing, denied or mismatched operation decisions and absent source references
refuse before SQL. Missing page labels, incomplete citation partition and
incomplete finding reads refuse before bytes. An explicit empty citation tuple
is allowed for each finding, including an empty run. Repeat inputs and reads
produce equal ZIP bytes; formula-like cell values remain literal text.

## Rollback / feature flag

Remove the additive service and test before runtime wiring; no data rollback
or feature flag is needed.

## Handoff

- changed files/checks/limits: see report;
- contracts: none;
- next: W57b seal/API owner verifies decisions and source custody, supplies one read transaction and the CSV filename source, and performs the independent spreadsheet probe.
