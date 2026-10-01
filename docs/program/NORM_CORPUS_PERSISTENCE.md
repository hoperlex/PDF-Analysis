# Normative corpus persistence model

## Two names that must not be confused

`norms_snapshot_id` is the durable domain identity already frozen in the identifier catalog. It
has the form `ns_<ULID>`, is allocated once, is equality-only and is the value an `audit_run`
pins.

`content_key` is the deterministic description of the effective corpus text, for example
`2026-07-23..2026-08-20+17d.4b74348debf7`. A repaired projection has a different content key.
The key is a unique comparison and idempotency value, not an entity identity and not a foreign
key exposed to another bounded context.

The loader resolves `content_key -> norms_snapshot_id` inside one transaction. Two loads of the
same effective bytes therefore converge on one opaque snapshot without deriving identity from
content.

## Stored topology

```text
norms_snapshot (opaque entity, immutable)
  ├─ norm_document (opaque entity, immutable snapshot member)
  │    ├─ norm_paragraph (opaque entity, canonical deterministic evidence)
  │    └─ norm_chunk (rebuildable retrieval projection)
  │         └─ references first/last canonical paragraph ordinals
  └─ norm_chunk_build (complete replace-only profile metadata)
```

`NormsSnapshot`, `NormDocument` and `NormParagraph` are contracted entities identified by
`ns_<ULID>`, `ndoc_<ULID>` and `npar_<ULID>`. Their numeric table keys are private
relational implementation details and may never be returned by an API. Document slugs, external
pipeline references, block references, page labels and ordinals remain attributes/anchors, not
cross-context identities. A retrieval chunk deliberately has no public identity.

## Canonical versus rebuildable

`norm_paragraph` stores the complete substantive segmentation: effective text, source block/page
anchor, kind, clause number and character offset into effective recognised text. A correction
creates a different effective content key and therefore a different snapshot; stored canonical
paragraphs are never updated in place.

`norm_chunk` stores a named `chunking_profile`, currently `characters-v1:1200`. Its text and
metadata are derived from a consecutive paragraph span. Chunk rows refuse `UPDATE`; a rebuild
deletes and reinserts one complete profile from canonical paragraphs. No audit fact may treat a
chunk row as the canonical wording of the norm.

## Transaction and idempotency boundary

The source corpus is validated and projected through the `norms` filesystem boundary. The
repository then performs only PostgreSQL writes in the caller's transaction:

1. insert the opaque snapshot guarded by unique `content_key`, or verify the existing row;
2. if it is new, allocate one fresh opaque ID for every document and paragraph, then insert
   those canonical entities and the initial chunk profile;
3. return counts and the opaque snapshot identity; an exact replay reuses every stored child ID;
4. caller commits once, or rolls the whole load back.

There is no S3 write in this command. Source-PDF/crop custody is a separate workflow requiring
its own reconciliation/outbox boundary, so a database failure cannot orphan objects here and an
object-store failure cannot leave a published snapshot half-loaded.

## Refresh and retention

A changed source byte or an applied repair changes `content_key` and creates a new opaque
snapshot with fresh document and paragraph entities. Existing rows and IDs remain immutable
because historic audit runs must continue to resolve the exact normative text they pinned.
`NORM-Q06` now requires full retention: every loaded snapshot and immutable repair ledger remains
available with no automatic deletion or TTL. A future erasure capability requires a new explicit
owner/legal/security ruling; it cannot reinterpret this decision silently.
