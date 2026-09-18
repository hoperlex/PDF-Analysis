# `storage` boundary

The BlobStore port and its S3/MinIO adapter. Bytes become canonical only after
`temporary -> verify -> publish`; business code addresses them by opaque
`blob_id` and never sees a bucket or an object key.

Owner: `P1-STO-01` (Gate A session `A3`). Gate B session `B1` extends this tree
with the blob-metadata repository — see [Extending this
package](#extending-this-package).

## Public surface

Everything a consumer needs is re-exported from `auditmanager.storage`.

```python
from auditmanager.storage import (
    ROLE_SOURCE_DOCUMENT, S3BlobStore, S3StorageSettings, sha256_of,
)

store = S3BlobStore(S3StorageSettings.from_env())
blob = store.put_blob(
    pdf_bytes,
    declared_sha256=sha256_of(pdf_bytes),
    declared_size=len(pdf_bytes),
    role=ROLE_SOURCE_DOCUMENT,
    media_type="application/pdf",
)
assert store.read(blob.blob_id) == pdf_bytes
```

### The port — `port.BlobStore`

| Operation | Purpose |
|---|---|
| `check_access()` | Prove the configured credentials reach the private bucket. |
| `stage_temporary(source, ...)` | Upload to a temporary location. Verifies nothing. |
| `verify_temporary(temporary)` | Read the staged bytes back; prove size and SHA-256. |
| `publish(verified)` | Copy verified bytes to their canonical location. |
| `discard_temporary(temporary)` | Remove a staged upload. Idempotent. |
| `put_blob(source, ...)` | The whole sequence as one call. The business entry point. |
| `inspect(blob_id)` | Recorded facts, without reading the bytes. |
| `read(blob_id, verify=True)` | Published bytes, re-hashed on the way out by default. |

There is deliberately no `delete`, no `erase`, no `presign`, no `list` and no
way to name an object. Erasure is an `erasure_pending -> erased` transition
under an approved `erasure_request_id`, which P01 does not implement and must
not approximate.

`source` is `bytes` or a binary file object, so a large artifact never has to be
held in memory.

### The models — `models`

`PublishedBlob` is the whole public shape of a stored object:

```
blob_id  role  media_type  size  sha256  published_at  state
```

Opaque identity plus the four facts `FF-01` section 2 item 5 requires. No
`bucket`, `key`, `uri`, `url` or `path` field exists, and adding one is a
freeze-break. `TemporaryBlob` and `VerifiedBlob` carry an opaque `upload_token`
instead — only the adapter knows what object it names.

`BlobState` is the closed `machines.blob` state set from the frozen domain
contract. P01 drives `temporary -> verifying -> available` and the `-> rejected`
guards; the erasure states are declared so P02 persists this vocabulary rather
than inventing a second one.

`BlobRole` is a validated open vocabulary (`^[a-z][a-z0-9_]{2,63}$`), not a
closed enum. Every later stage that publishes an artifact brings its own role
name; a closed enum here would make each of those a rewrite of this package.

### The errors — `errors`

| Class | Contract code | Raised when |
|---|---|---|
| `StorageConfigurationError` | `validation_failed` | A frozen `S3_*` name is missing or empty. |
| `StorageBucketMissingError` | `validation_failed` | The configured bucket does not exist. |
| `StorageUnavailableError` | `dependency_unavailable` | The endpoint cannot be reached. |
| `StorageCredentialRefusedError` | `dependency_credential_refused` | The store refused the application's own credentials. Not the caller's rights: `permission_denied` means an authenticated subject, and there is none here. Renamed with its code at the wave-13 reseal, owner ruling `R-3`, `D-7`. |
| `ChecksumMismatchError` | `storage_integrity_error` | Stored SHA-256 ≠ declared. |
| `SizeMismatchError` | `storage_integrity_error` | Stored byte count ≠ declared. |
| `BlobIntegrityError` | `storage_integrity_error` | Base of the two above. |
| `TemporaryBlobLostError` | `staged_upload_lost` | A staged upload vanished mid-sequence. Carried `conflict` until owner ruling `R-8`, which is `D-18`: it and the row below were then one code, one message and one `retryable` for two opposite operator responses. 503 and `retryable: true`, because this upload is worth sending again. |
| `BlobAttributeConflictError` | `conflict` | Identical bytes already published with a different role or media type. Since `R-8` the only storage error carrying `conflict`, and `retryable: false` is right for it: the published bytes are immutable. |
| `BlobNotFoundError` | `not_found` | No published blob has that `blob_id`. |
| `BlobMetadataInvalidError` | `validation_failed` | A declaration is malformed. |
| `InvalidBlobIdError` | `validation_failed` | A string is not a well-formed `blob_id`. |

All descend from `StorageError`. `code` is the frozen
`contracts/domain/v1/error-codes.json` code the API layer maps to in P02;
nothing here builds an HTTP envelope.

## Object-key privacy — how it is enforced, not asserted

1. **The layout lives in one private module.** `_object_layout.py` is the only
   place that knows a key's shape. It is underscore-prefixed, absent from the
   package `__all__`, and imported by `s3.py` alone.
2. **No public model can carry a location.** `PublishedBlob`'s fields are
   asserted exactly in `tests/integration/storage/test_publication.py`.
3. **No error can carry one.** An error's summary is a class constant, so no
   call site can interpolate a key into it, and structured details are
   restricted to the `safe_detail_keys` the contract declares for that code.
   `bucket` and `key` are not in that vocabulary, so
   `ChecksumMismatchError(key=...)` raises `TypeError` at construction.
4. **Botocore messages are never re-raised.** Every `ClientError` is translated
   using its error *code* only, and re-raised `from None` so the original
   message reaches neither the string nor the traceback.
5. **`check.py` redacts on the way out**, so the rule holds even for text this
   package did not compose.

Asserted against `str(exc)`, `repr(exc)` and the formatted traceback in
`test_corrupt_upload.py` and `test_unavailable.py`.

## Identity and idempotency

`blob_id` is **derived**, not allocated:

```
blob_id = "blob_" + crockford_base32_26(sha256("auditmanager.blob.identity.v1|" + f"{sha256}:{size}")[:16])
```

matching the frozen wire pattern `^blob_[0-9A-HJKMNP-TV-Z]{26}$` and the frozen
rule that "re-uploading identical content is idempotent by `(sha256, size)`".

Consequences, each covered by a test:

* identical verified bytes publish once and return the same `blob_id`;
* the second publication does not rewrite the canonical object;
* the second attempt's temporary object is still cleaned up;
* identical bytes under a **different role or media type** are refused with
  `BlobAttributeConflictError` rather than silently reinterpreting an immutable
  blob;
* `_BLOB_ID_NAMESPACE` in `models.py` is part of the identity. Changing it
  changes every `blob_id` ever derived, so it is a freeze-break.

## Failure behaviour

A checksum or size mismatch leaves **nothing canonical**. Verification happens
before publication, so there is nothing to roll back and no window in which a
half-published blob is visible; the temporary object is deleted by the same call
that refuses it.

There is **no filesystem fallback**, and this package must never gain one —
`FF-01` section 4 lists "direct filesystem or JSON canonical storage" as not
approved. An unavailable store raises `StorageUnavailableError` and creates
nothing, anywhere. `test_unavailable.py::test_there_is_no_filesystem_fallback`
runs a publication against a dead endpoint from an empty directory and asserts
that directory is still empty.

## Cleanup

`_purge_published(blob_id)` deletes exactly one canonical object. It is **not on
the port and is never called by business code**; it exists so `check.py` and the
integration tests remove what they created, one key at a time. No cleanup path
in this repository is a broad bucket deletion.

## Commands

| Command | Result |
|---|---|
| `PYTHONPATH=src .venv/bin/python -m auditmanager.storage.check` | Exit `0`; prints `FOUNDATION-CHECK OK check-storage` as its last line. |
| `.venv/bin/pytest tests/integration/storage` | Exit `0` against a real S3-compatible service; leaves the bucket exactly as it found it. |

The first row is the invocation `FOUNDATION_LOCK.json` records for
`make check-storage`, run directly.

**Historical note, resolved.** When this lane ran, `make check-storage` could not
reach that invocation: it exited 127 with `exec: scrubbed_run: not found`.
`run_checked` already wrapped its arguments in `scrubbed_run`, while each
`check-*` target passed `scrubbed_run ...` in as those arguments, so the inner
`exec "$@"` tried to `exec` a shell function before any provider code ran. All
three `check-*` targets carried the identical shape. The integrator repaired it
in `P1-INT-00`'s deliverable at commit `e0ba71f`: `run_checked` now takes
`NAME=VALUE` assignments up to `--` and forwards them to its single
`scrubbed_run` call, and rejects a non-assignment rather than exporting it as a
bare variable name. This paragraph is kept because the lane's report and commit
`5528cb6` refer to the defect; it is not a live limitation.

`check.py` proves, in order: the frozen `S3_*` names are present; the configured
application credentials reach the bucket; an **unsigned** request to the same
bucket is refused; a full round trip records role, media type, size and SHA-256
and reads back byte-identically; and a corrupt upload is refused with the
`blob_id` those bytes would have taken absent afterwards. It then removes the
one object it created.

The suite does not mock and does not skip when the service is absent — a skip
would let the negative paths pass by not running.

## Known limits, deferred to P02+

* No blob-metadata table. Identity and location are derivable without one; the
  repository `B1` adds records lifecycle and provenance.
* No multipart or resumable upload; `stage_temporary` is a single PUT.
* No presigned URL, no browser-direct upload route.
* No lifecycle, retention, TTL or reconciliation of abandoned temporary
  objects. `machines.blob`'s `temporary -> rejected` reconciliation needs the
  window under the open `U-04` decision, so no value is invented here.
* No erasure path. `available -> erasure_pending -> erased` needs an approved
  `erasure_request_id` and an audit event, neither of which exists in P01.
* One bucket, one credential pair. Multiple buckets and production IAM are
  explicitly out of scope for `FF-01`.
* No retry or backoff. `max_attempts` is 1: an unavailable store is reported,
  never silently retried into apparent success.

## Extending this package

`B1` adds the blob-metadata repository. It is an addition, not a rewrite:

* it persists the `PublishedBlob` records this port already returns and the
  `BlobState` each already carries;
* it does **not** become the identity authority — `blob_id` is derived, so the
  repository's `(sha256, size)` uniqueness constraint agrees with the adapter
  rather than competing with it;
* it must not add a location column, and must not reach into
  `_object_layout`;
* the port's operation set is asserted exactly in
  `test_publication.py::test_the_port_offers_no_way_to_name_or_delete_an_object`.
  Changing it is a deliberate act, not a drive-by.
