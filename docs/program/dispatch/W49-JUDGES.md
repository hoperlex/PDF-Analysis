# W49 judges — identity, crash recovery and corpus integrity

These are candidate briefs. `W49-FREEZE-01` replaces symbolic subjects and paths with exact SHAs
before dispatch. Judges own report files only, repair nothing, never use alpha credentials and
restore every disposable probe.

## `W49-JUDGE-A` — contract and identity seal

**Subject:** `W49-CUSTODY-SEAL` before implementation dispatch.
**Allowed path:** `docs/program/reviews/W49-JUDGE-A.md`.

Attack the contradiction the seal is intended to resolve:

1. Submit byte-identical PDF/PDF, crop/crop and PDF/crop admissions under different anchors.
   Enumerate the identities and idempotency results required by the chosen owner ruling.
2. Replay one command with identical bytes and then with changed role, target, checksum, size and
   media type. Exact replay must converge; every conflict writes nothing.
3. Walk every existing `blob_id` contract consumer. Prove no old upload/version/manifest
   semantics changed accidentally, or prove the reseal changes all of them coherently.
4. Interrupt at intent commit, staging, canonical write, read-back and confirmation. For every
   state, identify the sole legal reconciliation transition and visible business result.
5. Mutate each migration constraint and upgrade both a fresh database and a restored predecessor.
6. Attempt to derive identity from path, filename, object key, checksum, document slug, page,
   ordinal or content key. Each must be impossible by contract.
7. Verify caller-safe faults reveal no bucket, key, host, credential or source text.

The verdict is blocking. Storage/corpus implementation cannot start on an ambiguous identity or
an untested migration.

## `W49-JUDGE-X` — operational fault and security entry point

**Subject:** one merged W49 implementation SHA after the disposable full rehearsal.
**Allowed path:** `docs/program/reviews/W49-JUDGE-X.md`.

Start from running commands and external boundaries without reading the implementation diff:

- run every command with missing origin/path/credential, unreachable S3, unavailable provider,
  full disk simulation, timeout and process termination;
- kill the dispatcher after bytes are written but before DB confirmation, then restart and
  require the original identity and one binding;
- poison checksum/media metadata and verify fail-closed quarantine rather than retry forever;
- stop repair before and after a provider call and at the USD 5 boundary; costs and completed
  rows must neither vanish nor repeat silently;
- stop snapshot and embedding transactions at multiple points; no incomplete state is readable;
- run the worker with network denied and a cold cache/artifact mount;
- probe public routes and generated OpenAPI for any corpus text/search surface;
- inspect logs/reports/process arguments for credentials, provider bodies, corpus text and object
  keys.

Only after black-box results are captured may X read the diff and mutate the new guards.

## `W49-JUDGE-Y` — data lineage and architecture entry point

**Subject:** the same merged SHA as X.
**Allowed path:** `docs/program/reviews/W49-JUDGE-Y.md`.

Start from the checkpoint that W49 promises and trace every claim backward:

- reconcile 674 PDF inputs and 28,246 crop inputs against intent, Blob/object and confirmed
  binding populations without counting a join expansion as independent evidence;
- select equal-byte admissions and prove the accepted identity ruling, not an accidental adapter
  behaviour;
- trace all 121 ledger outcomes to confirmed crop anchors, provider attempt/cost records and the
  repaired projection; find any raw-text fallback or unaccounted row;
- recompute the repaired content key, snapshot projection digest and measured paragraph/chunk
  counts independently;
- recompute tokenizer coverage and complete-build digest; compare exact scan with HNSW and ensure
  result evidence resolves to canonical paragraph anchors, never private window IDs;
- verify routers/components contain no direct SQL/S3/filesystem work and alpha has no local-corpus
  mount or floating model download;
- restore backup into a fresh environment, run reconciliation and compare the manifest;
- prove all pre-W49 snapshots/Blobs/ledgers remain retained and addressable.

Y must treat a hard-coded base count presented as repaired output as a release-blocking
false-green.

## Cross-examination

X and Y exchange reports before repairs. For every finding, the other judge records **upheld**,
**narrowed** or **falsified**, one independent measurement, any shared assumption and the minimum
safe path grant. A shared query or the subject's own manifest is not independent confirmation.

Judge A separately re-reads the final identity/migration bytes after any fix touching its seal.
If they changed, its entire blocking verdict is rerun.

## Required report shape

Each report names exact subject SHA, environment, disposable data source, commands and exit
status, mutations, findings with path/line/consequence/reproduction, untested questions, final
verdict and `git diff --name-only <subject>..HEAD`. Evidence may contain hashes, opaque IDs,
counts and redacted failure classes, but never credentials, object keys, source text or provider
bodies.
