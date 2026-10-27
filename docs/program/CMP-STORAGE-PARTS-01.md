# CMP-STORAGE-PARTS-01 — multipart staging in the storage port

Written 2026-10-28 by the Sonnet lane `CMP-STORAGE-PARTS-01` (branch `agent/cmp-storage-parts-01`, base `cc3dd36b` on `integration/compare-modules`; nothing pushed, nothing merged). Task file: [`tasks/CMP-STORAGE-PARTS-01.md`](tasks/CMP-STORAGE-PARTS-01.md). The decision implemented is [`ADR-0025`](../architecture/adr/ADR-0025-comparison-modules.md) decision 10; the tables it stages for are those of [`CMP-SEAL-C0`](CMP-SEAL-C0.md).

No operation of the seal is wired, no table is read or written by `src/`, no work kind is registered. The lane adds functions that `CMP-INGEST-01` and `CMP-INGEST-02` call.

## 1. Base facts, printed before any edit

`git show HEAD:contracts/api/v1/openapi.json` read with `json`: contract `1.9.0`, **115 paths / 130 operations / 351 schemas**, 27 error codes; head `0038_comparison_foundation`; the table's bounds `MAX_PART_NUMBER = 10_000` and `PART_SIZE_BYTES = 16 * 1024 * 1024`. They equal the premise (task file P-01), so the lane went on. After the lane: contract, migration, `VERSION` and every dependency file untouched.

Baseline before the first edit: `pytest -q tests/unit/storage tests/integration/storage` on the lane's own MinIO (`RELEASE.2025-10-15T17-29-55Z`) and PostgreSQL 17: **106 passed**.

## 2. What was built, and why it has this shape

### 2.1 A second port, not a widening of the first

`BlobStore` is pinned twice: `tests/integration/storage/test_publication.py::test_the_port_offers_no_way_to_name_or_delete_an_object` asserts its exact member set, and eight test doubles implement it. `test_the_package_ships_no_filesystem_adapter` (`test_unavailable.py`) pins every exported name ending `BlobStore` to `{BlobStore, S3BlobStore}`. Multipart staging is therefore a second `Protocol`, **`MultipartStaging`** (`storage/port.py`), that `S3BlobStore` also satisfies. `BlobStore`, `DurablePublicationStore`, `stage_temporary`, `verify_temporary`, `publish` and `put_blob` are not touched: `git diff cc3dd36b -U0 -- src/auditmanager/storage/s3.py` has **no removed line**, and the removed lines of the whole diff are three import lines (`from .port import ...` in `__init__.py`, `from collections.abc import Generator` in the port, `from auditmanager.storage.port import ...` in `public.py`, each re-added with the new name), the port's and the audit script's `__all__` (re-added with the new names) and the signature and docstring of `audit_blob_references` (moved, see 2.5). The pre-existing 106 tests are unchanged and green.

### 2.2 The token, and why nothing but the token is persisted

`comparison_upload_file.multipart_token` is the only column the seal gave to this (write-once, `1..1024` characters), and the trigger refuses a part row for a file without it. So:

* the caller **mints** the token (`new_multipart_token()`: `mpu-` plus 32 lowercase hex, 128 random bits, pure and local, no store is asked), **persists it**, commits, and only then calls `begin_multipart`;
* the token is the stem of the object key (`temporary/<token>`); the in-progress S3 upload (its `UploadId` is S3's own and is **not** stored anywhere) is found by an exact-key `ListMultipartUploads` on every call (one extra request per call, prefix-scoped, never a listing of the bucket);
* there is no window in which the store holds an upload that no row names. A process killed after the commit leaves a token with an owner and, at worst, an upload that the same token aborts. This is why the sweep (2.4) is database-owned and needs no bucket listing;
* only the minted form is accepted by every call (`parse_multipart_token`), so a token cannot be a path (`../`, `temporary/...`) and cannot collide with the free-form handle of `stage_temporary`.

### 2.3 Completion is the existing verify-and-publish path

`complete_multipart` joins the parts **under the temporary key of the token** and then calls the very `verify_temporary` and `publish` that `put_blob` calls. "Nothing canonical without verification" is one rule with one implementation: the assembled object is read back, its size and SHA-256 are compared with the declaration, a mismatch deletes it, and a match is published by content identity (idempotent: bytes already published are reused and no temporary is left).

Before anything is assembled the adapter refuses (the upload is left exactly as it was, so the caller can correct the list or abort):

* no parts, a repeated number, a gap, numbers not ascending from 1, a part outside `1..16 MiB` or without its facts (`MultipartPartsError`);
* sizes that do not add up to the declared size (`SizeMismatchError`, `storage_integrity_error`);
* a listed part that the store does not hold with the receipted ETag **and size** (`MultipartPartsError`; `ListParts`, paginated).

Measured on the lane's MinIO with a throwaway probe (not committed): a completion of **`[1, 3]`, `[2, 3]` and even `[1, 1, 2, 3]` is accepted** and assembles a file (a repeated part is joined twice); the store refuses only an empty list (`InvalidRequest`), a disordered one (`InvalidPartOrder`), a part it does not hold or holds with another ETag (`InvalidPart`) and a part but the last under 5 MiB (`EntityTooSmall`; the adapter turns the last three into `MultipartPartsError` as well). The adapter's own check of the numbering is therefore **the** guard against a list that would publish a file nobody meant, not a duplicate of the store's.

**Retryable.** With no open upload and an assembled object present (a process killed between assembly and verification), a second `complete_multipart` resumes at the verification. With neither, `verify_temporary` raises `TemporaryBlobLostError`. A transient failure (store unreachable, 5xx) does **not** delete the assembly: a 250 MiB file is not cheap to send again, and the sweep removes it later.

**The seam.** `complete_multipart(..., before_publish=None)` is the seam `DurablePublicationStore` already has: called with the `VerifiedBlob` after the verification and before the canonical copy, so the caller can commit `verifying` for the declared `blob_id` (`BlobMetadataRepository.record_verified`). If it raises, nothing is published and the assembly is kept. It is the one addition beyond the brief, so that `CMP-INGEST-01` does not need a storage FIX slot to record the checkpoint; it is exercised end to end in section 5.

### 2.4 The abort, and the sweep a work handler calls

`abort_multipart(token) -> bool` aborts the open upload (every upload the key has) and **then** deletes an assembled-but-unverified object, in that order, so a completion racing it either finds no upload and fails typed, or has assembled and has its object deleted. It touches `temporary/<token>` only: **a published blob survives**, and a straggler `upload_part` or `complete_multipart` after the abort raises `TemporaryBlobLostError` (`staged_upload_lost`). Idempotent: `False` when the store holds nothing.

`abort_multipart_sweep(store, upload_tokens) -> MultipartSweepReport(aborted, absent, rejected)` is the function; it selects nothing and writes no row. The database owns the decision: the handler (INGEST-02, or INGEST-01 for a cancelled batch) first moves the file and its parts out of the states that accept a part, commits, then passes the tokens. A malformed token is `rejected` (one bad row cannot block the rest); a repeated token is handled once; **a store-wide fault is raised, not recorded per token**, so the handler's attempt fails and retries the same tokens, which is safe because every step is idempotent. The work kind (`ADR-0025` decision 17) is registered by the lane that uses it, as the brief says.

### 2.5 The unreferenced-blob report

`scripts/recovery/blob_reference_audit.py::report_unreferenced_comparison_blobs(session) -> UnreferencedBlobReport(attributed, unattributed)`, SELECT only. `audit_blob_references` starts from the references; the fault a comparison upload makes possible is the opposite one: the object is verified and published (`blob` is `available`) and the process dies before `comparison_upload_file.blob_id` is written. The report lists every `available` Blob that none of the **eleven** registered columns names (a `NOT EXISTS` per column, built from the closed `_SOURCES` set; the set is written out in the test, so adding a source must change it on purpose). `attributed`: the Blob has the identity of the declared bytes of one or more comparison files that hold no Blob yet (`derive_blob_id` of the declared SHA-256 and size), and carries their ids; `unattributed`: nothing in the database explains it. It refuses (like the audit) unless the head is the pinned one and the set of blob-referencing columns is the closed set, so a new reference cannot make a referenced Blob look orphaned. `audit_blob_references` keeps its statements and their order (the head and the catalog check moved into `_require_pinned_schema`, executed first, in the same order); `tests/integration/recovery/test_blob_reference_audit.py` (39 tests, outside the lane's paths) is unchanged and green.

### 2.6 Errors

No new code. Two classes under `validation_failed` (subclasses of `BlobMetadataInvalidError`, details `field` and `constraint` only, so `SAFE_DETAIL_KEYS` and its contract test are unchanged): `MultipartPartError` (`field` `part_number` or `part_size`: the contract's `comparison_part_number` / `comparison_part_size`) and `MultipartPartsError` (`field` `parts`). Integrity refusals reuse `ChecksumMismatchError` / `SizeMismatchError` (`storage_integrity_error`, so `domain_error_from_storage(exc, role="comparison_file_size")` gives the contract's size reason), and a vanished upload reuses `TemporaryBlobLostError` (`staged_upload_lost`, retryable).

## 3. The public API for `CMP-INGEST-01` (and `-02`)

Import from `auditmanager.storage.public` (the cross-context boundary test refuses deeper paths).

```python
new_multipart_token() -> str                      # "mpu-" + 32 hex; pure, local
MULTIPART_PART_BYTES_MAX == 16 * 1024 * 1024      # MULTIPART_PART_NUMBER_MAX == 10_000

@dataclass(frozen=True, slots=True)
class UploadedPart:                                # what the caller records in comparison_upload_part
    part_number: int; size_bytes: int; sha256: str; etag: str   # etag unquoted, <= 256 chars

# S3BlobStore (satisfies the MultipartStaging Protocol):
begin_multipart(upload_token: str) -> None        # idempotent
upload_part(upload_token: str, part_number: int, source: bytes | bytearray | BinaryIO) -> UploadedPart
complete_multipart(upload_token: str, parts: Sequence[UploadedPart], *,
                   declared_sha256: str, declared_size: int, role: BlobRole, media_type: str,
                   before_publish: Callable[[VerifiedBlob], None] | None = None) -> PublishedBlob
abort_multipart(upload_token: str) -> bool        # idempotent; never touches a published blob

@dataclass(frozen=True, slots=True)
class MultipartSweepReport: aborted: tuple[str, ...]; absent: tuple[str, ...]; rejected: tuple[str, ...]  # .handled
abort_multipart_sweep(store: MultipartStaging, upload_tokens: Iterable[str]) -> MultipartSweepReport

# errors (all StorageError, all with .code and .details):
MultipartPartError, MultipartPartsError            # validation_failed
BlobIntegrityError (-> ChecksumMismatchError, SizeMismatchError)   # storage_integrity_error
TemporaryBlobLostError                             # staged_upload_lost
StorageUnavailableError                            # dependency_unavailable

# scripts.recovery.blob_reference_audit:
report_unreferenced_comparison_blobs(session) -> UnreferencedBlobReport(attributed, unattributed, .total_bytes)
```

`ChecksumMismatchError` and `SizeMismatchError` are not re-exported by `storage.public`; catch `BlobIntegrityError`, or read `exc.details` (`expected_sha256`/`actual_sha256`, `expected_size`/`actual_size`).

### The sequence the lane's tests run end to end (`TestTheSequenceAComparisonUploadWillRun`)

1. First part of a file, one transaction, committed **before any byte moves**: `BlobMetadataRepository.record_declared(session, declare_blob(sha256=file.declared_sha256, size=file.declared_size_bytes, role=..., media_type="application/pdf"))` (the declared Blob: the database owner of the bytes); `token = new_multipart_token()`; `UPDATE comparison_upload_file SET multipart_token = :token, state = 'uploading'`; insert the part row (`declared`).
2. `store.begin_multipart(token)`; `receipt = store.upload_part(token, n, body)`; then `UPDATE comparison_upload_part SET state = 'staged', size_bytes, sha256, etag` from the receipt. Each further part: row, then bytes, then receipt.
3. Completion: `published = store.complete_multipart(token, [UploadedPart(...) from the rows], declared_sha256=..., declared_size=..., role=..., media_type=..., before_publish=lambda v: (repo.record_verified(session, v), session.commit()))`, then `repo.mark_available(session, published.blob_id)`, then `UPDATE comparison_upload_file SET state = 'verified', blob_id = :blob_id` and the parts to `completed`.
4. On `BlobIntegrityError`: mark the file `failed` (the token stays; a re-send calls `begin_multipart` again, which opens a new upload under the same token), `domain_error_from_storage(exc, role="comparison_file_size")` for a size mismatch.
5. A cancelled or expired file: mark file and parts in the database, commit, then `abort_multipart_sweep(store, tokens)` from a work handler; a part sent afterwards is refused by the store as `staged_upload_lost`.

## 4. Tests

Commands run from the worktree root with `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider`:

| Run | Result |
| --- | --- |
| `tests/unit/storage tests/integration/storage` (lane's MinIO and PostgreSQL) | **259 passed** = 106 pre-existing + 153 new |
| of which `tests/unit/storage/test_multipart_offline.py` (no container) | 76 |
| `tests/integration/storage/test_multipart_staging.py` (real MinIO, independent boto3 client for every "nothing is left" assertion) | 60 |
| `tests/integration/storage/test_unreferenced_comparison_blobs.py` (real PostgreSQL at head `0038` and MinIO) | 17 |
| `tests/integration/recovery/test_blob_reference_audit.py tests/contract/domain_p02/test_narrow_sets_against_contracts.py tests/contract/architecture` | 55 passed |
| `tests/contract` minus the three `D-220` files, on the clean committed tree | 1307 passed, 19283 subtests passed (2 m 16 s) |
| `git diff --check` | clean |

The offline suite exists because a real store refuses a bad part list itself: a bucket can show that a list was refused, not that the adapter refused it **before asking the store to assemble**. Its stand-in records every call, so "nothing was assembled" is an assertion about calls; it also reaches the pagination of `ListParts` and `ListMultipartUploads` and the exact-key filter, which a single-digit-part upload on a real store cannot.

Not run, by `R-126` / `R-135`: any other database suite, the live journey, the full gate. The lane changes no existing behaviour (no removed line in `s3.py`).

## 5. Mutation proofs

Each row: the mutation applied to the committed file with a one-occurrence replace, the suites run, the result, and the file restored by `git checkout --` with `git status --short` empty afterwards. "Offline" is `test_multipart_offline.py` (76), "real" is `test_multipart_staging.py`, "db" is `test_unreferenced_comparison_blobs.py`. The three the brief names are M1, M2 and M3.

| Id | Mutation | Red |
| --- | --- | --- |
| **M1** | `complete_multipart` builds the `VerifiedBlob` from the declaration instead of `verify_temporary` (a wrong digest is published) | 5 failed (offline + real: wrong digest, flipped byte, second completion, integrity family) |
| **M2** | `abort_multipart` iterates `[]` instead of the open uploads | 6 failed (real: aborted upload leaves nothing, abort again, sweep; offline: two) |
| **M3a** | `check_parts_for_completion` loses the ascending-from-1 check | 15 failed. On the real store three tests go red with `DID NOT RAISE MultipartPartsError` (gap `[1, 3]`, start at 2, repeat `[1, 1, 2, 3]`, each declared with the size and digest the list would assemble, so the file is published: the store accepts these lists); the disordered list stays green on the real store because S3 refuses it itself (`InvalidPartOrder`), and the offline stand-in sees the `complete_multipart_upload` call |
| **M3b** | `_require_staged` removed (a listed part the store does not hold or holds differently) | 5 failed (offline: phantom part, size, ETag, pagination; real: receipt with another size) |
| **M3c** | the sum of part sizes no longer compared with the declared size | 4 failed |
| M4 | any string accepted as a token | 17 failed |
| M5 | `begin_multipart` always creates | 2 failed |
| M6 | a completion with no open upload gives up instead of resuming at the verification | 1 failed (real: killed-before-verify resumes) |
| M7 | the later of two open uploads chosen | 2 failed |
| M8 | the upload listing not narrowed to the exact key | 1 failed, **offline only**: on a real store the prefix already narrows it and tokens have a fixed length, so no sibling key exists; the real-store test `test_an_abort_touches_only_its_own_token` is a regression pin, not a proof of this filter |
| M9a / M9b | part size bound / part number bound removed | 5 / 7 failed |
| M10 | an oversized stream cut at the bound instead of refused | 2 failed |
| M11 / M12 | the sweep stops setting a malformed token aside / stops handling a repeat once | 3 / 2 failed |
| M13 / M14 | `ListParts` / `ListMultipartUploads` stop after the first page | 1 / 1 failed (offline) |
| M15 | the abort leaves an unverified assembly behind | 1 failed (real) |
| M16 | the spare upload of a race is not aborted at completion | 1 failed (real) |
| M17 | the sweep swallows a store-wide fault per token | 2 failed |
| M24 / M25 | the `before_publish` seam never called / called before the verification | 2 / 2 failed of the 60 (real); M24 again on the end-to-end sequence with the database: 2 failed of 17 |
| M18 | the report drops the `comparison_upload_file` source from its `NOT EXISTS` clauses | 3 failed of 17 |
| M19 | the report does not check the head and the closed catalog | 3 failed |
| M20 / M23 | no attribution to the declaring file / attribution by a digest that ignores the size | 2 / 2 failed |
| M21 | Blobs that are not `available` listed too | 1 failed |
| M22 | a Blob row whose identity disagrees with its content accepted | 1 failed |

Not provable by mutation: "the abort never removes a published blob" is structural (the abort has no way to name a canonical key; its only keys are `temporary/<token>`), pinned as a regression by `test_the_abort_never_removes_a_published_blob` and `test_a_second_completion_after_the_publication_finds_nothing_to_resume`.

## 6. Risks and known limits

1. **The 5 MiB minimum of every part but the last** is S3's, not ours. The contract's 16 MiB chunk always satisfies it; a test of the INGEST lane that stages parts of a few bytes gets `MultipartPartsError` at completion (the adapter says so in the constraint).
2. **A completion re-reads the whole object through the API process** (`verify_temporary`, 1 MiB at a time, never held whole), bounded by the envelope's 250 MiB per PDF. That is the existing verification, not a new cost, but it is one more full read per file than the portal upload makes for a small bundle.
3. **`upload_part` holds one part (at most 16 MiB) in memory** and hashes it; the router already reads the body before the port is called (CMP-SEAL-C0, section on `uploadComparisonUploadPart`).
4. **A re-sent file reuses the token** (it is write-once). After an integrity refusal the assembly is gone, so the caller calls `begin_multipart` again; after a pre-assembly refusal the upload is still open with its old parts, and parts sent again replace by number while unlisted ones are dropped at assembly.
5. **`begin_multipart` after an abort opens a new upload** for the same token. The guard against a straggler is the database state (a part for a failed or cancelled file is refused before the store is asked) plus the store's `staged_upload_lost` for `upload_part`; `begin_multipart` is only to be called for a file the database still accepts parts for.
6. **The report on a live database shows an in-flight publication as an orphan** between the publish and the write of `blob_id`; run it on the isolated snapshot like the audit. It is not wired to a CLI or to the restore drill.
7. **Stale multipart uploads at the store** (a lifecycle rule such as `AbortIncompleteMultipartUpload`, MinIO's own expiry) were not configured or measured here and are not relied on; the database-owned sweep is the mechanism.
8. **Container hygiene:** an upload left open by a refused completion is aborted by the integration suite's teardown; the bucket per test is dropped by the existing `settings` fixture.

## 7. Instructions for the integrator

* Merge position: `WORK → STORAGE-PARTS → SPEND → ...` (brief section 3). The lane touches **no wiring file** (`bootstrap/**`, `api/routers/ports.py`, the stub enumerators, `grant_classification.py`) and no contract or migration, so it cannot conflict with the hunks of the other lanes.
* `CMP-INGEST-01` is unblocked: section 3 is its interface. It owns the SQL on `comparison_upload_file` / `comparison_upload_part` and must remove those tables from `SEALED_NOT_YET_WRITTEN` when it writes them.
* The abort sweep's work kind is registered by INGEST-01/02 over `CMP-WORK-01`'s handler registry; the kind's selector (which files are expired) is theirs.
* `tests/integration/storage/test_unreferenced_comparison_blobs.py` creates databases on the host's PostgreSQL by `CREATE DATABASE ... TEMPLATE` and drops them; it reads `DATABASE_URL` from the environment or the repository-root `.env`, fails loudly when absent and never skips. It runs `alembic upgrade head` once per module.

## 8. Forbidden hotspots

`git diff --stat cc3dd36b` lists exactly: `docs/program/tasks/CMP-STORAGE-PARTS-01.md`, `docs/program/CMP-STORAGE-PARTS-01.md`, `scripts/recovery/blob_reference_audit.py`, `src/auditmanager/storage/{__init__,errors,multipart,port,public,s3}.py`, `tests/unit/storage/test_multipart_offline.py`, `tests/integration/storage/{test_multipart_staging,test_unreferenced_comparison_blobs}.py`. No file of `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `src/auditmanager/bootstrap/**`, `src/auditmanager/api/**`, `src/auditmanager/comparison/**`, any `conftest.py`, `tests/support/**`, or any other lane's paths. The lane's `.env` and the `.venv` symlink are git-ignored.

## 9. Environment

Stack `auditmanager-cmp-storage-parts-01` (PostgreSQL `57730`, MinIO `61730`/`61731`, database `auditmanager_cmp_storage_parts_01`, bucket `auditmanager-cmp-storage-parts-01`), started with `make up` and stopped with `make down`; `df -h /` before every start and long run (3.2 G before `make up`, never below 2.6 G during the lane; the stop line is 1.5 G). No process was killed.
