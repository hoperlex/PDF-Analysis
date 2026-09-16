# `W11-RD` — the read path does not verify what the manifest promised

Session `W11-RD`, worktree `/root/w11rd`, branch `agent/w11-rd`.

`HEAD` on arrival: **`5d14921`** ("docs: the wave 11 dispatch — repair what wave 10 found"),
which is `origin/dev`. The brief says base `30d129c` "or later"; `5d14921` is that commit plus
two docs-only commits.

Instance `gate-w11a`: `POSTGRES_PORT=55630`, `S3_API_PORT=59230`, `S3_CONSOLE_PORT=59231`,
`POSTGRES_DB=audit_w11a`, bucket `auditmanager-gate-w11a`. Logs in `/root/w11rd-logs/`.

## Baseline

`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`, `npm --prefix web ci`, then `make gate`
at `5d14921` before any change:

```
1264 passed, 5 skipped, 116 subtests passed in 191.55s
GATE OK: battery, foundation, frontend and whitespace all pass
```

The brief's expected counts are exact. (`/root/w11rd-logs/gate-baseline.log`)

## What the tree actually does — before the repair

Three facts, read off the tree rather than off the brief:

1. `IngestService.read_source_bytes` (`src/auditmanager/ingest/service.py`) resolves
   `entry = self.require_source_entry(version_uid)` — which carries `entry.sha256` and
   `entry.size_bytes` — and returns `self._store.read(entry.blob_id)`. It uses `entry.sha256`
   in exactly one place: as a *detail* on the `storage_integrity_error` it raises when the
   object is **absent**. It never compares it to the bytes. Confirmed.
2. `S3BlobStore.read` (`src/auditmanager/storage/s3.py`) re-hashes what it read and compares
   it to `_metadata_value(response, _META_SHA256)` — the **object's own** recorded digest —
   under `if recorded is not None and recorded != actual`. An object carrying no
   `content-sha256` user metadata is returned with no check at all, from a method whose
   parameter is named `verify` and defaults to `True`. Confirmed.
3. `Reconciler.verify_version` (`src/auditmanager/ingest/reconciliation.py`) does hold a
   manifest comparison — `if published.sha256 != entry.sha256 or published.size !=
   entry.size_bytes` — but `published` comes from `self._store.inspect(...)`, which is a
   `head_object`. It compares the manifest against the object's **recorded metadata**, and
   never against bytes. The brief said to check `verify_version` first in case it already held
   the comparison the read path needs: it does not. It holds a comparison of two *declarations*.
   Nothing in the tree hashes stored bytes and compares the result to the manifest.

## The repair, and the argument for its shape

Both halves of the choice the brief offered, because they answer two different faults —
but they are not symmetric, and the first one is the load-bearing one.

### 1. `read_source_bytes` hashes the bytes and compares them to the manifest

```python
actual_sha256 = sha256_of(data)
if actual_sha256 != entry.sha256:
    raise DomainError(
        ErrorCode.STORAGE_INTEGRITY_ERROR,
        blob_id=str(entry.blob_id), role=entry.role,
        expected_sha256=entry.sha256, actual_sha256=actual_sha256,
    )
```

**Why this one and not only the store-level one.** The adapter can only ever establish that
an object agrees with *its own* recorded metadata. That is self-consistency, and an object
replaced out of band **together with its metadata** satisfies it perfectly while being the
wrong document. That is not a hypothetical shape: it is exactly what `W10-RUN`'s own
`_publish_impostor_at(store, blob_id=..., content=impostor_bytes)` builds, with the
impostor's digest recorded on the impostor's bytes. No amount of strictness inside
`S3BlobStore` can refuse it. The manifest entry is the only digest in the system that is
*independent of the object*, so the comparison has to happen at the layer that holds the
manifest. Same code and same details as `verify_version` gives over the same row: one
fault, one answer, whichever path reaches it.

**Only the digest is compared.** The manifest also records `size_bytes`, and
`verify_version` compares both, but it compares two *declarations*, where size is recorded
independently of the digest. Here the digest is computed from the bytes in hand, and bytes
whose SHA-256 is `entry.sha256` and whose length is not `entry.size_bytes` are not
constructible. A size clause would be a branch no test could ever redden, which is the shape
wave 10 spent a stream finding.

### 2. `S3BlobStore.read(verify=True)` refuses an object with no recorded digest

```python
recorded = _metadata_value(response, _META_SHA256)
if recorded is None:
    raise BlobMetadataInvalidError(
        field=_META_SHA256,
        constraint="recorded on every object this adapter publishes",
    )
```

`publish` stamps `content-sha256` on every canonical object, so an object without it was not
published through this adapter. Returning it from a call whose parameter is named `verify`
and defaults to `True` is a claim the adapter cannot support. This also closes the hole for
the three callers I do not own — `analysis/stages/source_preparation.py`,
`analysis/stages/page_geometry_extraction.py` and `analysis/ports/artifacts.py` all call
`read(..., verify=True)` and none of them has a manifest digest to compare against. `verify=False`
is untouched and remains the explicit opt-out.

### The two causes stay two

`validation_failed` for "this store cannot vouch for this object — there is no declaration to
compare anything to, and nothing was compared to any bytes", `storage_integrity_error` for
"these bytes are not the promised bytes". One code for both would be the `analysis_failed`
flattening wave 3 undid. **No new error code was introduced** — the 21st code is owner-blocked,
and `BlobMetadataInvalidError` (`validation_failed`, `field`/`constraint`) already existed for
exactly "a declaration is absent or malformed; nothing was compared against stored bytes".
A third mutation below exists solely to prove the two do not collapse.

## The guards, shown red and green

`make mutation-copy MUT=/root/w11rd-mut`, and the copy baselined **unmutated** first:
`tests/integration/storage tests/integration/ingest` → **141 passed**
(`/root/w11rd-logs/mut-baseline.log`), with `auditmanager.__file__`,
`auditmanager.ingest.service.__file__` and `auditmanager.storage.s3.__file__` all asserted to
resolve under `/root/w11rd-mut/` from **inside a pytest run**, not just from a bare
interpreter.

| # | Mutation (on the copy) | Result |
|---|---|---|
| 1 | `read_source_bytes`: delete the digest comparison, `return data` straight from the store — the defect verbatim | **1 failed, 140 passed**. `test_a_version_whose_stored_checksum_disagrees_with_its_manifest_is_refused` → `Failed: DID NOT RAISE DomainError` |
| 2 | `s3.read`: restore `if recorded is not None and recorded != actual` | **2 failed, 139 passed**. `test_an_object_with_no_recorded_digest_is_refused_rather_than_returned` → `DID NOT RAISE BlobMetadataInvalidError`; `test_a_source_object_carrying_no_recorded_digest_is_not_read_as_the_document` → `DID NOT RAISE DomainError` |
| 3 | `s3.read`: answer the absent digest with `ChecksumMismatchError` instead — the flattening | **2 failed, 139 passed**, both on the code: `assert STORAGE_INTEGRITY_ERROR is VALIDATION_FAILED` |

Logs: `mut1-readpath.log`, `mut2-storeread.log`, `mut3-flatten.log`. The attribution is clean —
mutation 1 reddens only the manifest guard, mutation 2 only the two "cannot vouch" guards, and
each red is a refusal that did not happen rather than a collection error.

Unmutated, the same two suites are **141 passed** and the full gate is:

```
1267 passed, 5 skipped, 116 subtests passed in 201.38s
GATE OK: battery, foundation, frontend and whitespace all pass
```

1264 → 1267 is the three tests added. (`/root/w11rd-logs/gate-after.log`)

### `W10-RUN`'s pin is gone

`tests/integration/ingest/test_reconciliation_rules_with_no_guard.py` asserted
`sha256_of(returned) == impostor_sha256` with a comment naming `W10-RUN.md`. That assertion —
the only test in the tree asserting the old behaviour — is now a `pytest.raises(DomainError)`
over the same precondition, asserting the code, `retryable is False` and all four details. No
test asserts the old behaviour anywhere; `grep -rn "read_source_bytes" tests/` was re-run to
confirm.

## What an operator or a stored row observes differently

**No stored row changes.** Nothing in this repair writes: no new column, no new state, no new
row, no migration. A version that was readable before is byte-for-byte as readable now, and the
happy path costs one SHA-256 over an in-memory buffer already in hand.

What changes is what a *broken* read answers:

| Situation | Before | After |
|---|---|---|
| Object replaced out of band, its metadata replaced with it (internally consistent) | the impostor bytes, HTTP 200, no error anywhere on the read path | `422 storage_integrity_error`, `blob_id`, `role`, `expected_sha256` (the manifest's), `actual_sha256` (what was read) |
| Object replaced out of band with its metadata dropped | the impostor bytes, HTTP 200 | `422 validation_failed`, `field=content-sha256` |
| Object with correct bytes but no recorded metadata | the bytes, unverified | `422 validation_failed` — refused although the bytes are in fact right |

The third row is the only place this is *stricter than necessary*, and it is deliberate: an
object the adapter did not stamp is an object it cannot vouch for, and fail-closed is this
package's stated stance ("no silent degradation", `storage/errors.py`). Nothing the adapter
publishes can land in that state, so no supported sequence reaches it.

Neither message or detail set can carry a bucket or a key — both guards assert that explicitly
against the real bucket name and the real object key, and both run `screen_message`.

**Re-certification debt.** This is the first `src/` change since `c0d7daf`, and per the brief I
do not certify it. I assert only what I ran: the gate is green at 1267/5/116 and each new guard
has been shown red under a mutation back to the defect. I make **no** claim about whether PC-01
or either certification still holds; wave 12 re-certifies. Consistent with the brief, I found no
way to reach either fault through the twelve operations — both guards had to write behind the
adapter with an independent boto3 client — but that is an observation from three tests, not a
certification of the inducibility limit.
