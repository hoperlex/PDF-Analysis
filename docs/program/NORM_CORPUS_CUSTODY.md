# Normative corpus and retrieval artifact custody

R-76 (2026-10-09) supersedes the 2026-09-30 one-object-per-admission wording:
`blob_id` is derived from verified bytes and size. Equal corpus and project bytes are
stored once; source/crop roles belong to immutable bindings, not to Blob identity.
R-104 (2026-10-12) fixes the two-phase sequence below and the road to the stand.
`W54-SEAL-01` sealed the schema (migration `0018_norm_custody`); `W54-CUSTODY-01` owns the
behaviour (`norms/custody/**`) and W57a owns the roles section from its freeze on.

## Identity and topology

```text
NormsSnapshot ns_…
  └─ NormDocument ndoc_…                       (target_kind norm_document)
       ├─ admission nad_… ─(confirmed)─> binding nbd_… (role norm_source, anchor pdf)  ──> Blob blob_…
       └─ admission nad_… ─(confirmed)─> binding nbd_… (role norm_source, anchor crop) ──> Blob blob_…
              anchors: opaque doc_… / blk_… / page_index text
```

The bindings are relations, not identities. A source file name, object key, checksum,
`source_document_ref`, document slug, page label and block reference remain attributes or
lookup anchors. Each source or crop has its own admission and binding; identical verified bytes
reuse one content-derived `blob_id` after size, SHA-256 and media type are checked. A different
media type conflicts. An existing object without recorded SHA-256 is refused, never reused.
The first publisher's stored role remains as historical metadata; consumers read their role
from their binding, so a project document and corpus source can share the same bytes.

The drop's opaque `doc_…` and `blk_…` references and `page_index` stay text anchors;
they are never parsed as `document_uid`. Custody mints its own `nad`/`nbd` identities
(`contracts/domain/v1/identifiers.json`).
The canonical paragraph retains its source `page_label` and `block_ref`. A crop binds to the
document/page/block source anchor, not to a retrieval chunk. Rebuilding chunks therefore never
changes custody, and a paragraph/crop link remains resolvable through the canonical anchor.

## Roles and targets

Admissions and bindings carry `role`, `target_kind` and `target_id` (text) plus `anchor_kind`
and `anchor`. One CHECK name, `ck_norm_custody_role_shape`, on both tables, maps each role to
its target kind and anchor kinds:

| Role | Target kind | `target_id` | Anchor kinds | Added by |
|---|---|---|---|---|
| `norm_source` | `norm_document` | `ndoc_<ULID>` | `pdf`, `crop` | `0018_norm_custody` |
| `norm_retrieval_set` | `norm_retrieval_set` | `nrs_<ULID>` | `artifact` | `0023_norm_citations` |
| `norm_catalogue` | `norm_retrieval_set` | `nrs_<ULID>` | `artifact` | `0023_norm_citations` |

An unknown role, target kind or anchor kind is refused by that CHECK, and the binding's insert
guard refuses an unknown target kind a second time. The 0023 guard accepts an `nrs_`
target only after a verified set row exists. A deferred constraint trigger then requires
exactly one confirmed binding for each artifact role, with the row's expected and observed
digest, size and Blob identity. A rejected set cannot receive a published binding or be
pinned by a Run. `norms/custody/roles.py` mirrors these exact role shapes.

## Publication invariant

A custody binding is published only when all of the following are true:

1. a Blob metadata record exists under its content-derived `blob_id`;
2. bytes have completed `temporary -> verifying -> available` through the existing `BlobStore`;
3. read-back size, SHA-256 and media type equal the admission;
4. **at publication time**, in the transaction that holds the target rows, the target exists
   and the binding names exactly the admission's role, target and anchor (moved by R-104 from
   intent time, so an admission may precede its target);
5. one database transaction appends the confirmation/audit event and makes the binding visible.

`trg_norm_custody_binding_guard` re-checks 1–4 in the database on every insert: a confirmed
admission, its `available` Blob with the declared size, SHA-256 and media type, and an existing
target. The composite foreign key `fk_norm_custody_binding_admission_tuple` makes the binding's
role, target, anchor and `blob_id` the admission's own. A published binding is immutable and
never deleted (NORM-Q06).

Business reads never follow a temporary/rejected blob or an unbound admission. Object existence
by itself is not publication, and a database row that has not been storage-confirmed is not
publication either.

## The two phases

**Phase 1 — admission** (`admit`, then `dispatch --until-idle`).

1. In one PostgreSQL transaction, check the tuple against the verified bundle manifest and
   append one `norm_custody_admission` row: role, target, anchor, derived `blob_id`, declared
   size, SHA-256 and media type, state `pending`. The admission row **is** the outbox row; no
   separate outbox table exists. No S3 call occurs in the transaction, and the target need not
   exist yet.
2. After commit, an at-least-once dispatcher takes `pending` rows in `available_at` order and
   serialises publication by `blob_id` with the storage metadata repository's per-blob advisory
   lock, shared with ingest (D-146 makes `record_declared` idempotent under that lock). It reuses
   an already `available` object only after checking recorded size, SHA-256 and media type;
   otherwise it stages bytes through the storage port, reads them back and publishes them.
3. In a new transaction it locks the admission, verifies the tuple is unchanged, advances Blob
   metadata to `available` and marks the admission `confirmed`. **No binding is visible yet.**
   Replaying an already confirmed identical admission returns the recorded outcome.
4. A failed try records `last_failure`, increments `attempt_count` and moves `available_at`
   along the schedule; the fifth failed try (30 s … 2 h, E-7) leaves the row `poisoned`.
   `requeue` returns a poisoned row to `pending` with a fresh count. A byte mismatch
   `rejected`s the admission, never the shared Blob row; the slot is then free for a corrected
   admission with a new `nad` identity.

**Phase 2 — binding publication** (`publish_bindings(role, target)`, CD-19).

5. The transaction that inserts or holds the target rows (the bundle importer's, for
   `norm_source`) locks each confirmed admission for that role and target, checks invariant 4
   there, and inserts the `norm_custody_binding` with its audit event. A confirmed admission whose
   target never arrives stays unbound and is reported; it is never bound by guessing.

States of an admission: `pending → confirmed | poisoned | rejected`, `poisoned → pending |
rejected`; `confirmed` and `rejected` are terminal, and no admission is deleted. The guard is
`trg_norm_custody_admission_guard`.

The idempotency scope is `command type + authorized subject + target role/anchor`. Same key and
same normalized metadata/bytes fingerprint replays. Same key with different role, target,
checksum, size or media type is `idempotency_key_reuse` and creates/publishes nothing. One live
admission per binding slot is enforced by `uq_norm_custody_admission_live_slot`.

## Reconciliation matrix

| Observed state | Required outcome |
|---|---|
| admission pending, no staged/canonical object | re-drive within the five-try schedule |
| temporary object vanished | `staged_upload_lost`, retryable; the admission stays unconfirmed |
| stored bytes differ in size/SHA/media type | reject the admission or Attempt with the existing typed integrity failure; never reject the shared content-derived Blob row |
| canonical object verified, confirmation transaction absent | verify again and idempotently confirm the same admission |
| admission confirmed, target absent | leave it unbound and report it; bind only in the target's transaction |
| binding published, object absent or metadata differs | storage integrity incident; fail closed, do not allocate a replacement identity silently |
| object exists with no resolvable admission/Blob metadata | quarantine/report orphan; do not infer ownership from its key |
| retry arrives after confirmation with identical tuple | return the confirmed result, write no second Blob, admission or binding |
| retry arrives with conflicting tuple | conflict, write nothing |

Poisoned admissions remain observable with attempts, last typed failure and correlation/audit
references. The operator commands are `admit|dispatch --until-idle|reconcile|report|requeue`.

**D-143.** There is no Blob state-machine edge out of `rejected`. `report` lists `rejected`
Blob rows, and an admission whose bytes resolve to a `rejected` Blob is refused, naming D-143.
P2's copy record measures the stand's `rejected` count: zero closes D-143; rows outside any
manifest stay registered and never stop P4; only a `rejected` manifest Blob is refused.

## Where the custody objects come from, and the repair order

The only source of custody objects is a **verified bundle on the stand**
(`python -m auditmanager.norms.bundle import`). The drop under `.local/norms/` is never admitted;
it is read only on this host, digest-verified, by re-recognition and by the bundle export
(R-104 amends `ADR-0020` L41-42 accordingly).

The 121 problematic pages are repaired **before** any custody, on this machine, against the
promotion database (`W54-PLAN.md` §3.2–§3.3):

```text
drop + operator SHA256SUMS (step 0) -> base snapshot in the promotion database (step 1)
-> priced sample, then the 121 repair calls through norm_repair_call and the fsynced
   local journal (step 2) -> repaired snapshot, +<n>r+<m>u key (step 3)
-> complete embedding build (step 3) -> verified bundle (step 4)
-> on the stand: admit -> dispatch until every admission is confirmed
-> one transaction: snapshot rows + publish_bindings('norm_source', snapshot) -> build -> report
```

Re-recognition reads crops from the drop, checked against the operator's `SHA256SUMS`; it never
reads a confirmed crop binding, because none exists on this machine. A provider failure leaves
the base snapshot intact. A ledger validation failure publishes no repaired snapshot. Every block
that does not end `REPAIRED` is unreliable (`norm_paragraph.text_reliability`,
`norms_snapshot.unreliable_count`). Re-running either stage converges through its own
idempotency boundary: a repair call's scope is its own `nrc` identity, and an `outcome_unknown`
call is never re-paid.

## Retention and erasure

`NORM-Q06` requires full retention of every confirmed source PDF Blob, crop Blob and binding,
with no automatic deletion or TTL. Physical erasure requires no live document manifest, norm
binding or analysis publication, checked through each context's public module.
`reject_unpublished` refuses while a non-terminal custody admission or Attempt declares the blob.
`U-04` remains open for system-wide retention/legal-hold authority, so no physical deletion
capability is introduced here. Only never-confirmed, unreferenced temporary bytes follow approved
cleanup semantics. Credential material, bucket/key names and filesystem paths never enter
caller-safe errors or the domain identity catalog; no consumer depends on the private object-key
layout.
