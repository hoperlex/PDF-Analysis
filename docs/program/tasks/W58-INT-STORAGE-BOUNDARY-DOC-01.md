# Task W58-INT-STORAGE-BOUNDARY-DOC-01 — align storage boundary descriptions

task_id: W58-INT-STORAGE-BOUNDARY-DOC-01

## Outcome

Storage package docstrings accurately describe the new recovery-only public
key resolver while retaining opaque Blob IDs as the product identity.

## Depends on

- `W58-INT-STORAGE-KEY-RESOLVER-01` — completed at `118c866d`.

## Frozen inputs

- base commit: `118c866dfa2fe000acaae379a103b6730c5a57b5`;
- storage package root SHA-256: `f3bd45bf6329ad017d02d9201b09fb7274a4ea20c16bd274b59436127abd6300`;
- private layout SHA-256: `33cc2c9693d319088a14bcd913af26eec7ef89dd024352212ca0c7f359e907df`;
- storage public SHA-256: `b8f1c8163827e9e86ae7e3a96a286e15e7fb41afc35813cadb7f705f9c54247c`;
- migration head: `0022_findings_v2`; no contract change.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the previous storage docstrings say only the S3 adapter imports the
  key layout and no public accessor exists, while the completed W58 task adds a
  recovery-only resolver through `storage.public`.

### P-01 — stale descriptions and new resolver

- captured_at: 2026-10-15
- command: `rg -n 'imported by|accessor|canonical_object_key_for_recovery' src/auditmanager/storage/__init__.py src/auditmanager/storage/_object_layout.py src/auditmanager/storage/public.py`
- captured_output:
  ```text
  src/auditmanager/storage/public.py:34:def canonical_object_key_for_recovery(blob_id: BlobId) -> str:
  src/auditmanager/storage/public.py:65:    "canonical_object_key_for_recovery",
  src/auditmanager/storage/_object_layout.py:5:from the package's ``__all__``, and imported by ``s3.py`` and by nothing else.
  src/auditmanager/storage/__init__.py:6:not exported and is imported by the adapter alone.
  src/auditmanager/storage/__init__.py:20:``blob.blob_id`` is the only thing a consumer keeps. There is no accessor for a
  ```
- interpretation: both descriptions need a narrow correction, without
  changing the actual layout or product identity rule.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/storage/__init__.py` — docstring only;
- `src/auditmanager/storage/_object_layout.py` — docstring only;
- `docs/program/tasks/W58-INT-STORAGE-BOUNDARY-DOC-01.md`;
- `docs/program/W58-INT-STORAGE-BOUNDARY-DOC-01.md`.

## Forbidden hotspots

Storage function bodies, imports, exports and constants; `storage.public` and
the S3 adapter; `contracts/**`, migrations, root dependencies/lockfiles,
composition root, global styles, corpus, recovery scripts, tests and Git refs.

## Non-goals

No key algorithm or runtime behavior change, real restore/S3 readback,
recovery acceptance, full gate, push or deployment.

## Deliverables

Two exact docstring corrections, this task and result report.

## Required tests

Direct governance, `git diff --check`, exact changed-path and docstring-only
diff proof. Runtime tests are unnecessary for prose-only changes; full gate is
deferred under R-135.

## Integration contract

The package root still does not export a key; product callers retain opaque
Blob IDs. `storage.public` has one recovery-only resolver delegated to the
private rule. The two docstrings must describe those facts without editing
the rule itself.

## Failure/idempotency/security cases

Do not suggest that product routers may expose keys or that a derived key is
an identity. Repeating this edit changes no stored bytes or object locations.

## Rollback / feature flag

Revert the two docstrings and task/report; no feature flag or data migration.

## Handoff

- changed files/checks: accompanying report;
- contracts: none;
- next: real W58 recovery still requires an isolated DB+S3 drill.
