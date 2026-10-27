# Task CMP-INGEST-ZIP-01 — a safe reader for ZIP sets of whole stages

## Outcome
`auditmanager.ingest.bundle_archive.extract_bundle` takes a policy parameter. The default is the portal-bundle policy and
its behaviour is unchanged to the byte. A second policy, written in `auditmanager.ingest.comparison_zip`, reads a ZIP
**set**: many PDFs in one archive (ADR-0025 decision 12, plan `R3-17`, `Q-CMP-10`). It refuses, before anything is stored,
an archive with more than N entries, more than 2 GiB uncompressed in all, a nesting deeper than one level, a name that is
not a plain relative name, a symbolic link, an encrypted member, a name that repeats, a member that is not a PDF (or, at
the first level, a ZIP), a bomb by ratio or by absolute size, and a PDF that fails the existing PDF envelope. Member names
are display hints and never identity. Adversarial tests show each guard failing under a quoted mutation.

## Depends on
- `CMP-SEAL-C0` merged on `integration/compare-modules` (`0990de4b`)
- `CMP-ORIGINAL-READ-01` (the original's stage upload rules, `docs/program/compare/ORIGINAL-STAGE-COMPARISON-INVENTORY.md` §3.1)

## Frozen inputs
- domain contract: not changed (`validation_failed` is used; the catalogue stays at 27 codes)
- API contract: `1.9.0`, not changed
- analysis/comparison/event contract: not changed
- migration head: `0038_comparison_foundation`, not changed
- base commit: `cc3dd36b` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

The refusal reasons are new `constraint` values under the existing `validation_failed` code (ADR-0025 decision 25: «a new
reason under an existing code is the default»). `contracts/domain/v1/error-codes.json` lists the registered values in prose
notes; registering the new ones is a contract slot's edit and is out of this lane's paths. The report gives the exact note
text.

## Captured premise evidence

- premise: the wave base is contract `1.9.0` (115 paths, 130 operations, 351 schemas, 27 error codes) at migration head `0038_comparison_foundation`, and the portal bundle reader's 269 archive tests are green on it without a container.

### P-01 — the base facts of the wave
- captured_at: 2026-10-28
- command: `.venv/bin/python -I -c "import json; d=json.load(open('contracts/api/v1/openapi.json')); ops=sum(1 for p in d['paths'].values() for m in p if m in ('get','post','put','patch','delete')); e=json.load(open('contracts/domain/v1/error-codes.json')); print(d['info']['version'], len(d['paths']), ops, len(d['components']['schemas']), len(e['codes']))"; ls db/migrations/versions | tail -1; git rev-parse HEAD`
- captured_output:
  ```text
  1.9.0 115 130 351 27
  20261028_0038_comparison_foundation.py
  cc3dd36b5b05b28ed0232107c8d0a437e304f07b
  ```
- interpretation: contract `1.9.0`, 115 paths, 130 operations, 351 schemas, 27 error codes, migration head `0038_comparison_foundation`, base `cc3dd36b`: the wave's premise holds, no STOP.

### P-02 — the portal-bundle reader and its tests before this lane
- captured_at: 2026-10-28
- command: `PYTHONPATH=$PWD/src AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent .venv/bin/python -m pytest -q tests/integration/ingest/test_bundle_archive.py -p no:cacheprovider`
- captured_output:
  ```text
  269 passed in 36.78s
  ```
- interpretation: the portal reader's own archive tests are green on the base; they need no database or object store. They are the first proof that the portal policy is unchanged.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/ingest/comparison_zip/**`
- `src/auditmanager/ingest/bundle_archive.py`
- `tests/unit/ingest/comparison_zip/**`
- `docs/program/CMP-INGEST-ZIP-01.md`
- `docs/program/tasks/CMP-INGEST-ZIP-01.md`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, root dependency/lock files, the composition root, global styles
- `src/auditmanager/ingest/envelope.py` and the other modules of `ingest` outside the paths above (the lane imports them, never edits them)
- `src/auditmanager/ingest/public.py` and `src/auditmanager/ingest/__init__.py` (the lane's names are reached as `auditmanager.ingest.comparison_zip`, inside the one `ingest` context)
- `tests/integration/**` (the existing portal tests are read and run, not edited), `conftest.py`, `tests/support/**`

## Non-goals
- no HTTP operation, no batch, no storage, no database: the reader takes a seekable handle and gives temporary files (`CMP-INGEST-01` and `CMP-INGEST-02` own what is done with them)
- no comparison envelope with its own element limit (addendum item 3 of ADR-0025 gives that to `CMP-INGEST-01`; this reader accepts the PDF check as a parameter and defaults to the existing envelope)
- no new error code, no contract note, no change to the portal-bundle upload or to any of its tests

## Deliverables
- `bundle_archive.py`: the `ArchivePolicy` parameter of `extract_bundle`, `PORTAL_POLICY` as its default, and the few public names a policy needs; nothing else
- `comparison_zip/`: `SetPolicy`, `DEFAULT_SET_POLICY`, `extract_pdf_set`, `ExtractedSet`, `SetMember`, `SetMemberRefused`, `inspect_pdf_member`, `CONSTRAINTS`
- `tests/unit/ingest/comparison_zip/`: adversarial tests (zip bomb by ratio and by absolute size, traversal, absolute paths, symbolic links, encrypted members, duplicate names, nesting beyond one level, non-PDF members, too many entries) and the proof that the portal policy is unchanged
- the report `docs/program/CMP-INGEST-ZIP-01.md` with every mutation quoted

## Required tests
- command: `PYTHONPATH=$PWD/src AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent .venv/bin/python -m pytest -q tests/unit/ingest tests/integration/ingest/test_bundle_archive.py tests/integration/ingest/test_display_name_scrub.py tests/unit/jobs/test_stale_temporaries.py -p no:cacheprovider`
- expected: all pass; the 269 tests of `test_bundle_archive.py` pass unchanged
- command: `pytest -q tests/contract` minus the three files of `D-220`
- expected: as on the base

## Integration contract
`CMP-INGEST-01` and `CMP-INGEST-02` call `auditmanager.ingest.comparison_zip.extract_pdf_set(handle, policy=..., envelope=...)` with a seekable handle on the whole ZIP, and get an `ExtractedSet` (a context manager that removes the temporary directories) of `SetMember`s: a stable ordinal, a display hint, the size, the SHA-256, a temporary file and the envelope's facts. A refusal is a `DomainError` with `validation_failed`, `field: "file"` and a `comparison_zip_*` constraint; a PDF that fails the envelope is a `SetMemberRefused` (a `DomainError` that also carries the member's ordinal and keeps the envelope's own `field` and `constraint`).

## Failure/idempotency/security cases
- every refusal leaves no temporary directory; an accepted set's directories are removed on close
- no name, size or byte of the archive is put in a refusal; no name ever becomes a path (members are files named by key inside a private temporary directory)
- the declared sizes are never trusted: the bytes that come out are counted against the same bounds
- the same archive read twice gives the same members, ordinals and digests

## Rollback / feature flag
Not applicable: nothing calls the reader yet. The comparison module flag (`AUDITMANAGER_COMPARISON_MODULES`) gates the callers.

## Handoff
- changed files: `src/auditmanager/ingest/bundle_archive.py` (+77 / -3: `ArchivePolicy`, `PORTAL_POLICY`, the `policy` parameter, four public aliases);
  new `src/auditmanager/ingest/comparison_zip/` (`__init__.py`, `policy.py`, `reader.py`, `refusals.py`); new `tests/unit/ingest/comparison_zip/`
  (`test_adversarial_archives.py`, `test_set_reader.py`, `test_member_envelope.py`, `test_portal_policy_unchanged.py`, `zip_builders.py`);
  this file and `docs/program/CMP-INGEST-ZIP-01.md`. Commits on `agent/cmp-ingest-zip-01`: `7fbcc34e`, `12b40477`, `76b844e1`, `2c3e3f30`, then the
  premise repair and the report commit.
- commands/results: `tests/unit/ingest/comparison_zip` 183 passed; the unedited portal suites (`test_bundle_archive` 269, `test_bundle_envelope` 99,
  `test_uncuttable_image_block` 60, `test_block_ceilings` 11, `test_display_name_scrub` 12) and `test_stale_temporaries` pass; a differential of 558
  portal-reader outcomes is byte-identical between `cc3dd36b` and this tree; 57 mutations all turn a test red (table in the report); `tests/contract`
  minus the three `D-220` files passes; `git diff --check` rc 0.
- known limits: the thirteen `comparison_zip_*` reasons are not registered in the contract notes (a contract slot's edit; text in the report); the default
  PDF check is the portal envelope (element ceilings) and costs 361 ms a PDF, so `CMP-INGEST-01` passes its comparison envelope and `CMP-INGEST-02` should
  defer it per item; `__MACOSX/` is refused; the decision-12 security judge has not been held.
- integration notes: merge after `CMP-EXEC-IMAGES-01`, before `CMP-INGEST-01`; no wiring file, contract, migration or lock is touched; the API is
  `auditmanager.ingest.comparison_zip.extract_pdf_set(handle, policy=..., envelope=...)` (report section 6).
