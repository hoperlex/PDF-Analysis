# W58-INT-SOURCE-OBJECT-MIRROR-PREP-01 — source object mirror preparation

**Frozen base:** `origin/dev` at
`08055ca094a9c3e4676a5907a0b3020f0bee4fb8`.
**Status:** unactivated recovery transport preparation, not a DB+Blob backup or
restore result.

## Result

`scripts/recovery/source_object_mirror.py` accepts a W54 `inventory.tsv`, an
injected GetObject reader and an existing owner-private objects directory.
It requests every inventory key with `IfMatch`, checks the response ETag and
ContentLength, streams and hashes all returned bytes, then writes each object
through a no-follow private directory path and a fsynced temporary file.
Atomic linking refuses replacement of an existing object. A retry reads the
source again and accepts the existing file only if its full byte hash and
size match. After all objects, the existing W58 `object_copy` scanner
rehashes the entire mirror and produces a canonical manifest for the caller
to seal separately. No complete result is returned on an interruption.

ETag is used only as a conditional-read change token. The SHA-256 in the
manifest comes from payload bytes, not from ETag or object naming. Object
keys remain transport locators, not Blob identities.

## Checks

- Focused fake-S3 and object-copy suite: **31 passed**. Cases include every
  listed object and empty inventory, exact repeat, bad ordering/duplicates,
  unsafe key, wrong ETag/length, short/long/non-byte/interrupted body,
  symlink/hardlink and extra object, and retry after partial transfer without
  replacing a prior object. The complete-result test passes the returned
  manifest through `object_copy.verify_manifest`.
- Program task governance: **16 passed**; direct task findings: `[]`.
- Python compilation and `git diff --check`: passed.
- The task's frozen source/contract/scope hashes match this base; migration
  head remains `0022_findings_v2`.
- Exact changed paths: this report, its task file, the new helper and its
  focused test. No frozen contract, migration, existing script, storage
  module, root dependency/lock, composition root or ref changed.

## Integration boundary and limits

No network call was made in this task; the helper calls only its injected
reader when a caller invokes it. It contains no credentials, endpoint or
production entrypoint. The current W54 copy key admits `fetch
<STAMP> db|inventory|record` only. It cannot invoke this helper or transport
object payloads, and `fetch` does not hold a copy lock across a batch. A later
W58 source-transport owner, after W56b code close, must grant a narrow
stand-side payload channel that keeps the writers quiesced and prevents
`resume` for the whole transfer (or an equivalent lease). It must bind the
source bucket, open copy record, stamp and exact inventory, then prove source
and target S3 readback, isolated DB+Blob restore, references and safe retry.

The helper cannot prove that the source bucket was stable before or during
its GetObject calls, that the W54 record is still open, or that an external
writer did not alter a same-ETag object. Its returned manifest is preparation
for the existing write-once seal, not an attestation or recovery verdict.
No Docker, live S3, database, stand copy or full gate was run.

Rollback is deletion of the additive helper/test/task/report before transport
wiring. No data migration or feature flag is involved.
