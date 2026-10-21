# Task W56B-INT-RUN-CROP-READ-01 — read saved IMAGE crops under current Attempt

task_id: W56B-INT-RUN-CROP-READ-01

## Outcome

An unserved read adapter binds the successful saved geometry StageResult of one
persisted Run to its frozen VersionUid and current Job/Attempt authority, reads
the exact referenced portal, crop manifest and PNG bytes through BlobStore,
and returns a checked IMAGE cohort only after a second authority and saved-row
check. No provider call is made.

## Depends on

- `W55B-GEOMETRY-01` — completed saved geometry/crop producers.
- `W56B-INT-CROP-COHORT-PREP-01` — completed IMAGE crop cohort.
- `W56B-INT-SAVED-CROP-CUSTODY-PREP-01` — completed supplied-byte verifier.

## Frozen inputs

- base commit: `5fa9473c54a5fb009ec8c0a6a45327a3a7f1dc15`
- base ref at freeze: `origin/dev`, candidate 32;
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- domain identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- crop-manifest schema SHA-256: `0a745c5477bf83a4ba1b14de9b42023525b29b862a3b7104e70fed91a63c4968`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- migration head: `0023_norm_citations`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the pure crop-byte verifier explicitly requires a future run-scoped
  repository query and real BlobStore reads; these production ports already
  exist, but the W56b read adapter does not.

### P-01 — existing W56b verifier and runs boundary at exact base

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only 5fa9473c54a5fb009ec8c0a6a45327a3a7f1dc15 src/auditmanager/analysis/geometry/saved_crop_custody.py src/auditmanager/runs/geometry_crop_input.py`
- captured_output:
  ```text
  src/auditmanager/analysis/geometry/saved_crop_custody.py
  ```
- interpretation: supplied-byte verification exists; a run-scoped read adapter
  is absent. This does not prove real DB/S3 integration.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/public.py`
- `src/auditmanager/runs/geometry_crop_input.py`
- `tests/integration/runs/test_geometry_crop_input.py`
- `docs/program/tasks/W56B-INT-RUN-CROP-READ-01.md`
- `docs/program/W56B-INT-RUN-CROP-READ-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, existing geometry producers and verifier,
`runs/repository.py`, `jobs/**`, storage adapters, API/UI, composition, W57a,
W58, root dependencies/locks, global styles, `CURRENT_STATE.md`, remote refs
and tags. `analysis/public.py` is reserved to this task for a narrow export by
the integrator; no other public API change is granted.

## Non-goals

No provider/vision call or journal, model budget, W56b stage registration,
served route, finding/citation, write, external DB/S3 test, contract/migration,
deployment or beta acceptance.

## Deliverables

One additive runs read adapter, minimal public export of the existing verifier,
focused offline port tests, and the paired report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_geometry_crop_input.py tests/integration/analysis/geometry/test_saved_crop_custody.py` — pass;
- Python compilation, direct task governance, frozen SHA-256 readback,
  `git diff --check` and exact allowed-path proof — pass;
- no Docker/PostgreSQL/S3/full beta gate while W55b gate owns the host.

## Integration contract

The caller supplies its existing SQLAlchemy transaction, current
`AttemptAuthority`, BlobStore and an explicit positive aggregate input-byte
ceiling. The adapter calls `JobRepository.require_current` before and after
the read, fetches Run and StageResult through `RunRepository` for the exact
authority run ID, reads the exact saved Blob references with full-stream
SHA-256/size verification, and invokes `check_saved_crop_bytes` on them. It
returns only checked crop bytes and cohort metadata. The caller must retain
or reacquire current Attempt authority and journal the effect before any
later provider call; this read does not grant perpetual execution authority.

## Failure/idempotency/security cases

Stale Attempt, non-running/changed Run, absent/duplicate/changed stage row,
foreign VersionUid, wrong artifact roles, input larger than the explicit
ceiling, missing/corrupt Blob or invalid crop cohort refuse the whole read.
No partial result, cache or fallback is returned. Repeated stable reads agree.

## Rollback / feature flag

Remove the additive adapter and export before wiring. No runtime flag or DB
rollback is needed because no served caller exists.

## Handoff

- changed files/checks/limits: paired report;
- contracts: none;
- next: integration into a formally frozen W56b stage with real isolated
  DB/S3 acceptance, provider/budget policy, effect journal and release gate.
