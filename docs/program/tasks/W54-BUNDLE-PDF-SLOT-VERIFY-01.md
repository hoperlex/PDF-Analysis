# Task W54-BUNDLE-PDF-SLOT-VERIFY-01 — bind imported PDF custody slots to document rows

task_id: W54-BUNDLE-PDF-SLOT-VERIFY-01

## Outcome

The actual bundle importer refuses a self-consistent, fully re-signed bundle whose manifest lacks a document's source-PDF custody slot or gives that slot an anchor other than the row's opaque `source_document_ref`. Refusal occurs before any database or S3 access.

## Depends on

- `W54-BUNDLE-01` — completed verified bundle, row reader, custody manifest and importer.

## Frozen inputs

- base/published development commit: `ee70edaa56c30255558873cb9f0a777daa11ee58`;
- W54 plan SHA-256: `b1b4acbf7ce02c4ef8b14533dedc8d7c9e64404b2f4cc0cc5c6342c9d7fdaf71`;
- W55 plan SHA-256: `9f4e0f204284347bc3ead59423a5cff830bbc9298ceaa2d47e1412f640b92b64`;
- source listing SHA-256: `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`;
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- development API 48 paths / 55 operations / 131 schemas, errors 25, migration head `0023_norm_citations`;
- bundle format `auditmanager-norm-bundle/1`; PDF slot anchor is the document row's `source_document_ref` (`W54-BUNDLE-01`).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the importer checks the manifest and row digests independently, but does not compare PDF slot anchors with document rows before database access.

### P-01 — row and manifest checks stop at snapshot facts

- captured_at: 2026-10-16
- command: `rg -n 'def import_bundle|rows = read_rows|row_facts =|if row_facts|say\(f"bundle:|def validate_manifest|targets = set\(manifest.targets\)' src/auditmanager/norms/bundle/stand.py src/auditmanager/norms/bundle/manifest.py`
- captured_output:
  ```text
  src/auditmanager/norms/bundle/manifest.py:549:def validate_manifest(manifest: Manifest) -> None:
  src/auditmanager/norms/bundle/manifest.py:595:    targets = set(manifest.targets)
  src/auditmanager/norms/bundle/stand.py:182:def import_bundle(
  src/auditmanager/norms/bundle/stand.py:207:    rows = read_rows(directory)
  src/auditmanager/norms/bundle/stand.py:216:    row_facts = snapshot_facts(rows.snapshot)
  src/auditmanager/norms/bundle/stand.py:217:    if row_facts != manifest.snapshot:
  src/auditmanager/norms/bundle/stand.py:222:    say(f"bundle: {manifest.content_key} verified ({len(manifest.files)} files"
  ```
- interpretation: the ingress comparison covers snapshot facts, while the manifest validator only compares its target count to document count. A container-free synthetic bundle with a PDF object/slot removed, every manifest count/digest and bundle name re-signed, still passes `validate_manifest` and reaches the test's forbidden database connection. This does not claim such a bundle exists on the real host.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/bundle/stand.py`
- `tests/integration/norms/bundle/test_import_refusals_offline.py`
- `docs/program/tasks/W54-BUNDLE-PDF-SLOT-VERIFY-01.md`
- `docs/program/W54-BUNDLE-PDF-SLOT-VERIFY-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root, global styles, `CURRENT_STATE.md`, other tasks/reports, source corpus/sums, promotion database/dump, repair journal, build/bundle payloads, credentials, S3/stand, refs and tags.

## Non-goals

No new bundle field, manifest format, ledger/content identity, source-PDF byte provenance proof, paid repair, real bundle export/import, DB/S3 publication, full gate or beta qualification. The synthetic fixture alone may write to pytest's temporary directory.

## Deliverables

A pre-database ingress guard against missing/wrong/extra PDF slots, a self-consistently re-signed bundle regression that fails on the base code, focused tests and a measured report.

## Required tests

- `PYTHONPATH=src:. <lock-matched-venv>/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/bundle/test_import_refusals_offline.py`;
- bounded `tests/integration/norms/bundle -k 'not postgres'`;
- `python3 -m compileall -q src/auditmanager/norms/bundle/stand.py tests/integration/norms/bundle/test_import_refusals_offline.py`;
- one reversing mutation, direct task governance, `git diff --check`, exact allowed-path proof.

## Integration contract

For every imported `DocumentRow`, exactly one PDF custody slot must target its `norm_document_id` and name its exact `source_document_ref` as anchor. Extra PDF slots are refused. The guard runs after verified bytes/rows but before database state and S3 access. Crop slot semantics, manifest format and successful imports are unchanged.

## Failure/idempotency/security cases

A missing PDF object/slot, a wrong PDF anchor and an extra PDF slot refuse before any database or object-store call even if the bundle's own checksums have been recomputed. A valid replay stays idempotent.

## Rollback / feature flag

Revert this offline importer/test/docs commit. No runtime flag or data rollback applies.

## Handoff

- changed files, checks, contracts, limitations and integration note: result report;
- no publication authority or forbidden hotspot ownership.
