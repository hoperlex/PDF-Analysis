# Normative corpus source/crop custody

R-76 (2026-10-09) supersedes the 2026-09-30 one-object-per-admission wording:
`blob_id` is derived from verified bytes and size. Equal corpus and project bytes are
stored once; source/crop roles belong to immutable bindings, not to Blob identity.
This W53 design handoff changes no storage code, migration or API. W54 owns implementation.

## Identity and topology

```text
NormsSnapshot ns_…
  └─ NormDocument ndoc_…
       ├─ source-PDF binding (role norm_source) ──> Blob blob_…
       └─ crop binding(s) (role norm_source) ─────> Blob blob_…
              anchors: opaque doc_… / blk_… / page_index
```

The bindings are relations, not identities. A source file name, object key, checksum,
`source_document_ref`, document slug, page label and block reference remain attributes or
lookup anchors. Each source or crop has its own binding/admission; identical verified bytes
reuse one content-derived `blob_id` after size, SHA-256 and media type are checked. A different
media type conflicts. An existing object without recorded SHA-256 is refused, never reused.
The first publisher's stored role remains as historical metadata; consumers read their role
from their binding, so a project document and corpus source can share the same bytes.

The drop's opaque `doc_…` and `blk_…` references and `page_index` stay text anchors;
they are never parsed as `document_uid`. Custody mints its own `nad`/`nbd` binding IDs.
The canonical paragraph retains its source `page_label` and `block_ref`. A crop binds to the
document/page/block source anchor, not to a retrieval chunk. Rebuilding chunks therefore never
changes custody, and a paragraph/crop link remains resolvable through the canonical anchor.

## Publication invariant

A custody binding is published only when all of the following are true:

1. a Blob metadata record exists under its content-derived `blob_id`;
2. bytes have completed `temporary -> verifying -> available` through the existing `BlobStore`;
3. read-back size, SHA-256 and media type equal the intent;
4. the binding still names the same `norms_snapshot_id`, `norm_document_id`, `norm_source` role and source
   anchor recorded when the intent was accepted;
5. one database transaction appends the confirmation/audit event and makes the binding visible.

Business reads never follow a temporary/rejected blob or a pending binding. Object existence by
itself is not publication, and a database row that has not been storage-confirmed is not
publication either.

## Command, outbox and reconciliation sequence

The implementing migration owns concrete table names. Its externally reviewable semantics must
be this sequence:

1. In one PostgreSQL transaction, validate the target snapshot/document and append a custody
   intent plus outbox row. The intent carries `command_id`, derived `blob_id`, binding role, expected size,
   SHA-256, media type and the exact PDF or crop anchor. No S3 call occurs in the transaction.
2. After commit, an at-least-once dispatcher serializes publication by `blob_id` with the
   storage metadata repository's per-blob advisory lock, shared with ingest. It reuses an
   already `available` object only after checking recorded size, SHA-256 and media type;
   otherwise it stages bytes through the storage port, reads them back and publishes them.
3. In a new transaction, the dispatcher locks the intent, verifies that its expected tuple is
   unchanged, advances Blob metadata to `available`, publishes the binding and appends the
   audit event. Replaying an already confirmed identical intent returns the recorded outcome.
4. A named custody reconciler scans pending/dispatching intents and the existing Blob metadata,
   then proves one of the explicit outcomes below. It never promotes bytes by guessing.

The idempotency scope is `command type + authorized subject + target role/anchor`. Same key and
same normalized metadata/bytes fingerprint replays. Same key with different role, target,
checksum, size or media type is `idempotency_key_reuse` and creates/publishes nothing.

## Reconciliation matrix

| Observed state | Required outcome |
|---|---|
| intent pending, no staged/canonical object | re-drive the outbox within bounded retry policy |
| temporary object vanished | `staged_upload_lost`, retryable; binding remains unpublished |
| stored bytes differ in size/SHA/media type | reject the admission or Attempt with the existing typed integrity failure; never reject the shared content-derived Blob row |
| canonical object verified, confirmation transaction absent | verify again and idempotently confirm the same `blob_id`/binding |
| binding confirmed, object absent or metadata differs | storage integrity incident; fail closed, do not allocate a replacement identity silently |
| object exists with no resolvable intent/Blob metadata | quarantine/report orphan; do not infer ownership from its key |
| retry arrives after confirmation with identical tuple | return the confirmed result, write no second Blob or binding |
| retry arrives with conflicting tuple | conflict, write nothing |

Poisoned intents remain observable with attempts, last typed failure and correlation/audit
references. W54 owns the five-try custody schedule (30 s through 2 h), `poisoned` state and
operator `admit|dispatch --until-idle|reconcile|report|requeue` commands.

## Batch and the 121-page repair ledger

The custody batch may admit the 674 source PDFs and 28,246 crop objects independently of
re-recognition. The 121 problematic pages are not special Blob identities: equal verified
crop bytes reuse the content-derived `blob_id` through separate bindings. Once provider credentials exist, re-recognition reads
only confirmed crop bindings and emits the separate immutable repair ledger. The norms loader
then validates and consumes that ledger through its DB-only transaction; it performs no MinIO
write.

Thus the recoverable order is:

```text
custody intent/outbox -> verified Blob bindings -> 121-page provider run
-> immutable repair ledger -> repaired content_key/snapshot load
```

A provider failure leaves custody intact. A ledger validation failure publishes no repaired
snapshot. Re-running either stage converges through its own idempotency boundary.

## Ownership left to the MinIO implementation task

The storage owner must name its migration slot, concrete intent/binding schema, dispatcher,
retry/poison policy, reconciler command and tests. It also decides private object-key layout;
no consumer may depend on that layout. Credential material, bucket/key names and filesystem
paths never enter caller-safe errors or the domain identity catalog.

`NORM-Q06` requires full retention of every confirmed source PDF Blob, crop Blob and binding,
with no automatic deletion or TTL. Removing a corpus or project removes only its bindings.
Physical erasure requires no live document manifest, norm binding or analysis publication,
checked through each context's public module. `reject_unpublished` refuses while a
non-terminal custody admission or Attempt declares the blob. `U-04` remains open for
system-wide retention/legal-hold authority, so no physical deletion capability is introduced
here. Only never-confirmed, unreferenced temporary bytes follow approved cleanup semantics.
