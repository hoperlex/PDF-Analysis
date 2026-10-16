# Task W54-BUNDLE-ROW-VALIDATION-INGRESS-01 — reject malformed rows before custody

task_id: W54-BUNDLE-ROW-VALIDATION-INGRESS-01

## Outcome

`import_bundle` refuses a checksum-consistent bundle with semantically invalid snapshot rows before database access, Blob admission or S3 dispatch.

## Depends on

- `W54-BUNDLE-01` — completed bundle importer, row reader and transactional row validation.
- `W54-BUNDLE-PDF-SLOT-VERIFY-01` — completed ingress source PDF slot guard.

## Frozen inputs

- base commit: `eaf58965cd8bedc229f464866e3d5768b1f05797`
- W54 plan SHA-256 `b1b4acbf7ce02c4ef8b14533dedc8d7c9e64404b2f4cc0cc5c6342c9d7fdaf71`;
- W55 plan SHA-256 `9f4e0f204284347bc3ead59423a5cff830bbc9298ceaa2d47e1412f640b92b64`;
- source listing SHA-256 `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`;
- API SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- error catalogue SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256 `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- bundle format `auditmanager-norm-bundle/1`, migration head `0023_norm_citations`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the importer verifies bytes and row digest, then admits and dispatches custody before `import_snapshot` calls `validate_snapshot_rows`.

### P-01 — late semantic validation

- captured_at: 2026-10-16
- command: `git show eaf58965cd8bedc229f464866e3d5768b1f05797:src/auditmanager/norms/bundle/stand.py | rg -n 'rows = read_rows|_require_source_pdf_slots|read_state\(|reached\("admitted"\)|reached\("dispatched"\)|import_snapshot\(' && rg -n 'validate_snapshot_rows\(rows\)' src/auditmanager/norms/loader.py`
- captured_output:
  ```text
  175:def _require_source_pdf_slots(rows: SnapshotRows, manifest: Manifest) -> None:
  226:    rows = read_rows(directory)
  241:    _require_source_pdf_slots(rows, manifest)
  245:    state = read_state(stand.engine)
  330:    reached("admitted")
  336:    reached("dispatched")
  359:            imported = import_snapshot(
  171:    validate_snapshot_rows(rows)
  ```
- interpretation: row semantics are checked after custody effects. In a container-free pre-change repro, an internally consistent synthetic bundle with `paragraph_count` one above its actual ordinal range was exported and reached `Untouchable.engine.connect` instead of refusing. This does not assert that a real qualified bundle has that defect.

### P-02 — test fixture uses an invalid paragraph kind

- captured_at: 2026-10-16
- command: `rg -n 'class ParagraphKind|BODY =|HEADING =|TABLE_ROW =' src/auditmanager/norms/model.py && git show eaf58965cd8bedc229f464866e3d5768b1f05797:tests/integration/norms/bundle/support.py | rg -n 'kind="clause"'`
- captured_output:
  ```text
  src/auditmanager/norms/model.py:16:class ParagraphKind(enum.Enum):
  src/auditmanager/norms/model.py:25:    BODY = "body"
  src/auditmanager/norms/model.py:26:    HEADING = "heading"
  src/auditmanager/norms/model.py:27:    TABLE_ROW = "table_row"
  211:                    kind="clause",
  ```
- interpretation: the existing fixture would itself fail the new early validator; only its kind value needs correction. Search of bundle tests found no literal row digest or checksum golden value dependent on that fixture.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/bundle/stand.py`
- `tests/integration/norms/bundle/support.py`
- `tests/integration/norms/bundle/test_import_refusals_offline.py`
- `docs/program/tasks/W54-BUNDLE-ROW-VALIDATION-INGRESS-01.md`
- `docs/program/W54-BUNDLE-ROW-VALIDATION-INGRESS-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root, global styles, `CURRENT_STATE.md`, other task reports, real corpus and bundle payload, DB/S3/stand, credentials, refs and tags.

## Non-goals

No new bundle format or public error; no paid repair, real import/export, restore, full gate or publication. The synthetic fixture may write only pytest temp files.

## Deliverables

Call existing `validate_snapshot_rows` during verified ingress and translate its failure to `bundle_rows_invalid`; correct the fixture's invalid kind; test a checksum-consistent malformed bundle and ordinary valid import boundary; measured report.

## Required tests

- `PYTHONPATH=src:. <lock-matched-venv>/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/bundle/test_import_refusals_offline.py`;
- bounded `tests/integration/norms/bundle -k 'not postgres'`;
- compile changed Python files, reversing mutation, `git diff --check`, direct task governance, exact path proof.

## Integration contract

The importer uses the same `validate_snapshot_rows` function as `import_snapshot`, before its first DB/S3 call. A malformed row set yields internal refusal `bundle_rows_invalid`; valid rows, manifest format and replay flow retain their existing semantics. The transactional validation remains in place.

## Failure/idempotency/security cases

A forged but consistently digested bundle with a document paragraph count that disagrees with its rows refuses before DB/S3. The fixture's paragraphs use frozen `ParagraphKind.BODY.value`.

## Rollback / feature flag

Revert this local commit. No runtime flag or data rollback applies.

## Handoff

- changed files, checks, contracts, limitations and integrator note: owned result report;
- no ref publication or forbidden-hotspot ownership.
