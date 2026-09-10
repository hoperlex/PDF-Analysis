# `tests/integration/foundation` — the cross-provider foundation suite

Owning task: **`P1-QA-00`**. This is the reserved path `make test-foundation`
forwards to, and the last step of `make foundation`.

    make foundation                 # the accepted sequence, this suite included
    .venv/bin/pytest tests/integration/foundation   # the same suite, directly

Both work. Under `make`, the fifteen frozen `FF-01` section 3 names are already
exported; run directly, `conftest.py` fills in only the missing ones from the
same git-ignored `.env` that `make` reads, never overriding an exported value.

## What this suite is for

Each authoring lane proved its own provider against its own throwaway instance.
This suite exists for the claims that need **both providers, at once, on one
instance, configured from one `.env`** — and for the one claim no disposable
instance could make at all, that state survives a restart.

| File | Claim |
| --- | --- |
| `test_real_providers.py` | The things asserted elsewhere are a real PostgreSQL 17 backend over TCP and a real MinIO endpoint — not SQLite, not a directory |
| `test_cross_provider_publication.py` | A blob published through the BlobStore adapter is reachable through the DB session boundary in the same run, carrying no bucket or key with it |
| `test_negative_paths.py` | The `FF-01` section 7 refusals: wrong checksum, wrong size, anonymous list/read/write, missing or misconfigured `DATABASE_URL` and `S3_*` |
| `test_restart_persistence.py` | `make down && make up` loses neither the migrated schema nor a published object |
| `test_idempotency.py` | Migration rerun at head, bucket re-initialization and republication all change nothing |

## Three rules

**Nothing is substituted.** No SQLite engine, no filesystem store, no `moto`, no
stub client. Where a claim could be faked by the object that made it, an
*independent* reader checks it — a raw `psycopg` connection and a separately
built `boto3` client. A record only the writer can see is not evidence that
anything reached a server.

**Nothing is skipped.** `pytest_runtest_makereport` rewrites any skipped outcome
into a failure. A missing service is the failure this suite reports, not a
reason to pass. An empty or fully deselected collection is refused too, and so
is `--collect-only`.

**Nothing is cleaned up in bulk.** Every object and row is registered and removed
by exact key — one `_purge_published` per blob, one `DELETE ... WHERE blob_id`
per row. No fixture empties a bucket, truncates a table or drops a database. A
session-scoped guard compares `git status --porcelain` before and after and
fails the run if the checkout moved.

## Every guard here has been shown to fail

A guard with no demonstration that it can fire is not evidence. Each row below
was produced by mutating **the thing the guard protects** — service state, or
provider behaviour patched at run time — never by weakening the assertion. No
mutation edited a tracked file; provider trees are not this task's to change.

| Guard | Mutation applied | Result |
| --- | --- | --- |
| skips are failures | `pytest.skip()` in a passing test | that test FAILED with the refusal message |
| empty collection | `-k` matching nothing | exit 4, explicit refusal |
| `--collect-only` | passed the flag | exit 4, explicit refusal |
| checkout unchanged | a test wrote a file into the repository root | session teardown ERROR naming the new path |
| anonymous list/read denied | `mc anonymous set download` | 3 privacy tests FAILED (SDK list, SDK read, bare HTTP) |
| anonymous write denied | `mc anonymous set upload` | the write test FAILED — `DID NOT RAISE ClientError` |
| refused upload leaves no residue | `discard_temporary` patched to a no-op | staged key still present, FAILED |
| wrong checksum/size publish nothing | `verify_temporary` patched to accept anything | 3 integrity tests FAILED, canonical objects appeared |
| republication does not rewrite | `publish` patched to copy unconditionally | `copy_object` count 2, FAILED |
| the unit of work commits | `Session.commit` patched to a no-op | the independent reader saw no row, FAILED |
| no SQLite substitute | `.env` set to `sqlite:///foundation.db` | 15 errors, 1 failure, exit 1 |
| no filesystem substitute | `.env` set to `file:///tmp/local-blobs` | 16 errors, 5 failures, exit 1 |
| only one BlobStore implementation | a `LocalDirectoryBlobStore` injected into the package | the package scan FAILED, naming it |
| migration rerun is safe at head | database stamped back to `0001_baseline` | both migration tests FAILED |
| bucket re-init is a no-op | bucket removed just before the rerun | FAILED — the initializer reported "created", not "no-op" |
| the restart really happened | `make down` rewritten to `true` | FAILED — `DID NOT RAISE StorageUnavailableError` |
| state survives the restart | the two named volumes removed on stop | FAILED — `relation "blob" does not exist` |

## One measured note on timestamps

`test_publishing_identical_content_twice_does_not_rewrite_the_object` counts
`copy_object` calls rather than comparing timestamps, and the comment there says
why. Measured against the always-rewrite mutation on this instance: MinIO
records `LastModified` to one-second resolution, both publications landed in the
same second, and the `LastModified` and `ETag` comparisons **passed while
`copy_object` had run twice**. A timestamp-only assertion would have certified a
store that rewrote the bytes on every republication.

The same comparison *is* load-bearing in `test_restart_persistence.py`, because a
restart takes tens of seconds — far more than the resolution that makes it
useless above.
