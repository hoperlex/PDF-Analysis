# W57A-INT-SET-CUSTODY-READ-PREP-01 — saved retrieval-set input

**Base:** exact published dev34
`b9e26b0c154c1369742fe8124a91f3e5fdf986aa`.
**Status:** isolated, unserved read candidate. No database, S3, provider,
remote publication or full gate operation was used.

## Result

`findings/retrieval_set_input.py` supplies one bounded set of saved bytes to
the existing `citation_publication.py` caller. It checks current Job/Attempt
authority through the public jobs port, reads the Run's frozen verified set,
confirmed set and catalogue admissions/bindings, matching available Blob
metadata and snapshot content key, then streams the set Blob by opaque ID.
The full read is bounded to 10 MB and independently checked for exact length
and SHA-256. It closes the stream and repeats both current-Attempt and SQL pin
checks before returning the bytes.

The read holds current Attempt locks across the object request. The caller
must keep this transaction short and run its own publication authority check
after any subsequent model or pure-gate work. The returned bytes are input to
the writer, not evidence that a model response or citation candidate is
grounded. A missing or changed set, custody row, available object or Attempt
refuses without a fallback or write.

## Evidence

- Focused offline set-reader and existing citation-writer tests: **20 passed**.
- Programme governance suite: **16 passed**. Python compilation, frozen
  SHA-256 comparison and direct task governance findings `[]`: **passed**.
  Staged whitespace check is recorded at commit.
- Offline probes cover an accepted full read and refusal for absent/duplicate
  set, terminal Run, byte ceiling, short/long/corrupt object, post-read SQL or
  Attempt drift and an absent object.

## Limits and integration

The offline fake models row results but does not prove the SQL on PostgreSQL,
the S3 adapter's metadata semantics, the lock duration under load or the
0023 deferred commit rules. A later isolated real DB/S3 lane must exercise an
actual verified set and custody publication before serving v3. The reader has
no role authorization, provider call, registered v3 profile or route wiring.
The `citation_publication.py` caller still must bind a recorded model response
to the candidate and execute the pure PDF and norm grounding gates.

Changed paths are exactly this report, its formal task, the additive adapter
and its offline test. `contracts/**`, migrations, root dependencies/locks,
composition, existing readers/writers, API, UI, `CURRENT_STATE.md`, remote
refs and tags are untouched. The integrator may cherry-pick this source
commit after dev34 and keep it unserved. Rollback is that bounded commit; no
feature flag or data rollback applies before activation.
