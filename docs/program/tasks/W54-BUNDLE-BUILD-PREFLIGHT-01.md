# Task W54-BUNDLE-BUILD-PREFLIGHT-01 — verify complete build before custody

task_id: W54-BUNDLE-BUILD-PREFLIGHT-01

## Outcome

`import_bundle` refuses a checksum-consistent bundle with a malformed or divergent embedding build before database access, Blob admission or S3 dispatch.

## Depends on

- `W54-BUNDLE-01` — completed bundle importer, build reader and build transaction.
- `W54-BUNDLE-ROW-VALIDATION-INGRESS-01` — completed semantic row ingress guard.

## Frozen inputs

- base commit: `100307cecc47056005d79e388b2dde1a8e4c99ed`
- W54 plan SHA-256 `b1b4acbf7ce02c4ef8b14533dedc8d7c9e64404b2f4cc0cc5c6342c9d7fdaf71`;
- W55 plan SHA-256 `9f4e0f204284347bc3ead59423a5cff830bbc9298ceaa2d47e1412f640b92b64`;
- source listing SHA-256 `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`;
- API SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- error catalogue SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256 `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- bundle format `auditmanager-norm-bundle/1`, build digest `norm-embedding-set/2`, migration head `0023_norm_citations`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: byte verification precedes DB/S3, but the build's JSONL/vector and embedding digest are read only in step 4 after custody and row insertion.

### P-01 — build parse after custody

- captured_at: 2026-10-16
- command: `git show 100307cecc47056005d79e388b2dde1a8e4c99ed:src/auditmanager/norms/bundle/stand.py | rg -n 'manifest, discarded|rows = read_rows|_require_source_pdf_slots|state = read_state|reached\("admitted"\)|reached\("dispatched"\)|chunks=iter_build'`
- captured_output:
  ```text
  176:def _require_source_pdf_slots(rows: SnapshotRows, manifest: Manifest) -> None:
  218:    manifest, discarded = _verified_manifest(directory, only_manifest=False)
  227:    rows = read_rows(directory)
  246:    _require_source_pdf_slots(rows, manifest)
  250:    state = read_state(stand.engine)
  335:    reached("admitted")
  341:    reached("dispatched")
  392:                chunks=iter_build(directory, [entry.path for entry in manifest.files_of("build")]),
  564:    manifest, discarded = _verified_manifest(directory, only_manifest=True)
  ```
- interpretation: a synthetic bundle whose first vector was replaced by invalid base64, then whose file digest, manifest SHA, SHA256SUMS and directory name were recomputed, passed bundle verification and reached `Untouchable.engine.connect`. This is a test case, not a claim about the real corpus.

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
- `docs/program/tasks/W54-BUNDLE-BUILD-PREFLIGHT-01.md`
- `docs/program/W54-BUNDLE-BUILD-PREFLIGHT-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root, global styles, `CURRENT_STATE.md`, other tasks/reports, source corpus/sums, promotion DB/dump, repair journal, real bundle payload, credentials, S3/stand, refs and tags.

## Non-goals

No changed bundle format or public error, no reconstruction of source chunk text at ingress, no paid repair, real export/import, DB/S3 publication, restore, full gate or beta qualification.

## Deliverables

A streaming ingress pass over `iter_build` that retains only one chunk at a time plus a set of document references, and checks vector data, canonical order, document references, counts and embedding-set digest against the verified manifest; self-consistently re-signed malformed and divergent build regressions; focused tests and measured report.

## Required tests

- `PYTHONPATH=src:. <lock-matched-venv>/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/bundle/test_import_refusals_offline.py`;
- bounded `tests/integration/norms/bundle -k 'not postgres'`;
- compile changed Python files, reversing mutation, `git diff --check`, direct task governance and exact path proof.

## Integration contract

The verified build is streamed once before the first database or S3 call. The same verified bundle remains subject to the existing transactional `ensure_build` and read-back checks. Invalid build bytes or digest/count mismatch refuse as `bundle_build_invalid`; no successful import step is removed or reordered.

## Failure/idempotency/security cases

A re-signed invalid vector or an internally consistent build file that differs from the declared embedding digest refuses before custody. Iteration retains only one chunk and a digest state; a replay recomputes the same result.

## Rollback / feature flag

Revert this local commit. No runtime flag or data rollback applies.

## Handoff

- changed files, checks, contracts, limits and integrator note: owned result report;
- no ref publication or forbidden-hotspot ownership.
