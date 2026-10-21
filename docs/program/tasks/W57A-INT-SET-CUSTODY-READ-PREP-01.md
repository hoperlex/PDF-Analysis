# Task W57A-INT-SET-CUSTODY-READ-PREP-01 — unserved saved retrieval-set Blob reader

task_id: W57A-INT-SET-CUSTODY-READ-PREP-01

## Outcome

An unserved read adapter returns the exact saved retrieval-set bytes for one
current Run/Attempt only after checking the frozen verified set, confirmed set
and catalogue custody, available Blob metadata, a bounded full Blob read and
the current Attempt again. Offline tests prove refusal before returning corrupt
or stale input to the existing citation transaction writer.

## Depends on

- `W57A-SEAL-01A` — complete at `c71048f788e5d0bee39a312217dfd4c0912e5bc1`.
- `W57A-SEAL-01B` — complete at `c08182cab78bed70afbc777019d43de6c0bd2e18`.
- `W57A-INT-CITE-TXN-PREP-01` — complete in `CFB-INT-DEV-PUBLISH-33`.
- `W57A-INT-CITE-READ-PREP-01` — complete in `CFB-INT-DEV-PUBLISH-34`.
- `CFB-INT-DEV-PUBLISH-34` — complete at `b9e26b0c154c1369742fe8124a91f3e5fdf986aa`.

## Frozen inputs

- base commit: `b9e26b0c154c1369742fe8124a91f3e5fdf986aa`;
- API v1 SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- analysis stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head: `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- `W57-PLAN.md` A3.3–A3.5, R-76, R-80 and R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the citation writer requires exact set bytes from a custody-checked
  Blob, while the published dev34 tree has no set-byte reader.

### P-01 — exact base and unserved writer requirement

- captured_at: 2026-10-16
- command: `git rev-parse HEAD; git ls-tree -r --name-only HEAD src/auditmanager/findings/retrieval_set_input.py; rg -n 'custody-aware port|The caller must have obtained' src/auditmanager/findings/citation_publication.py`
- captured_output:
  ```text
  b9e26b0c154c1369742fe8124a91f3e5fdf986aa
  3:The caller reads the retrieval-set Blob through its custody-aware port, runs
  237:    The caller must have obtained ``set_bytes`` from the custody-checked Blob,
  ```
- interpretation: this task supplies saved bytes through an additive reader;
  it does not serve the writer or establish the model response provenance.

### P-02 — frozen storage and migration seam

- captured_at: 2026-10-16
- command: `sha256sum contracts/api/v1/openapi.json contracts/analysis/v1/stage-registry.json contracts/domain/v1/identifiers.json contracts/domain/v1/error-codes.json db/migrations/versions/20261016_0023_norm_citations.py`
- captured_output:
  ```text
  7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388  contracts/api/v1/openapi.json
  58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1  contracts/analysis/v1/stage-registry.json
  5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2  contracts/domain/v1/identifiers.json
  918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc  contracts/domain/v1/error-codes.json
  fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e  db/migrations/versions/20261016_0023_norm_citations.py
  ```
- interpretation: the reader consumes existing 0023 row shapes and the public
  `BlobStore.open_stream` port, with no contract or migration edit.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/findings/retrieval_set_input.py`
- `tests/integration/findings/test_w57a_retrieval_set_input_offline.py`
- `docs/program/tasks/W57A-INT-SET-CUSTODY-READ-PREP-01.md`
- `docs/program/W57A-INT-SET-CUSTODY-READ-PREP-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies and locks;
- API routes/schemas, `src/auditmanager/bootstrap/**`, composition root;
- existing findings modules/public facades, Run/Job/Storage modules;
- `CURRENT_STATE.md`, UI/global styles, remote refs, tags and stand services.

## Non-goals

No qualified W54 set, new custody publication, registered v3 profile,
provider call, saved response-to-candidate binding, CITE StageResult,
finding publication, served route, real DB/S3 acceptance or beta claim.

## Deliverables

One additive read-only adapter, focused offline refusal tests, task and result
report. The caller passes the returned `.data` to the existing transaction
writer only after independently binding the recorded call and pure gates.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/findings/test_w57a_retrieval_set_input_offline.py tests/integration/findings/test_w57a_citation_publication_offline.py`;
- `python3 -m py_compile src/auditmanager/findings/retrieval_set_input.py tests/integration/findings/test_w57a_retrieval_set_input_offline.py`;
- `git diff --check`, frozen SHA-256 and direct task governance findings `[]`;
- no PostgreSQL, S3, Docker or full gate while W55b holds the host.

## Integration contract

The caller supplies a separately authorized `AttemptAuthority`, SQLAlchemy
transaction and `BlobStore`. The adapter invokes `JobRepository.require_current`
before and after the full object read, requires a running/validating Run pinned
to one verified set, checks confirmed custody for set and catalogue and
available matching Blob metadata, applies a 10 MB hard ceiling, requests a
full stream with expected digest/size, independently hashes the returned bytes
and rechecks the SQL pin. The caller still must recheck at publication: a read
cannot reserve future model or finding authority. Errors refuse without writes.

## Failure/idempotency/security cases

Missing or duplicate rows, wrong Run state, oversized object, corrupt object,
lost object or changed custody/Attempt refuse. The object stream is closed on
both success and failure. No fallback source or external write is used. A
caller must roll back any transaction after a refusal and must not hold Run
locks beyond the short read and subsequent publication gate.

## Rollback / feature flag

Unserved additive source only. Revert the bounded commit before activation;
no runtime feature flag or data rollback applies.

## Handoff

- changed files: the four exact allowed paths;
- commands/results: accompanying result report;
- known limits: offline proof, no real DB/S3 acceptance or served v3 caller;
- integration notes: cherry-pick after dev34, then prove real custody read in
  an isolated DB/S3 lane after the W55b gate releases the host.
