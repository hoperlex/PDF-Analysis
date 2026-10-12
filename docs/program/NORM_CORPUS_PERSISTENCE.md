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

The key also names how the text is cut (`D-126`, `W54-SNAPSHOT-01`): any segmentation profile
other than the literal `markdown-v1` appends `+seg-<profile>` after the digest, to both
`content_key` and `base_content_key`, for example
`2026-07-23..2026-08-20+17d+118r+3u.<12 hex>+seg-markdown-v2`. A raised profile therefore
loads as a second snapshot beside the first instead of conflicting on its key; `markdown-v1`
adds nothing, so every key minted before W54 is unchanged. The repair ledger's
`base_snapshot_id` stays the unqualified key of the corpus bytes, which no profile changes.

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
anchor, kind, clause number, character offset into effective recognised text and
`text_reliability`. A correction creates a different effective content key and therefore a
different snapshot; stored canonical paragraphs are never updated in place.

**Reliability (`F-4`, `0018`).** Every block the repair ledger holds that did not end
`repaired` is unreliable: its corpus text stands, each paragraph drawn from it is stored with
`text_reliability = 'unreliable'`, and `norms_snapshot.unreliable_count` records the number of
such blocks (the `m` of the key's `+<m>u`). `ck_norms_snapshot_raw_key` holds
`repair_count = 0 AND unreliable_count = 0 ⇔ base_content_key = content_key`.

`norm_chunk` stores a named `chunking_profile`: `<version>:<target characters>`. Its text and
metadata are derived from a consecutive paragraph span. Chunk rows refuse `UPDATE`; a rebuild
deletes and reinserts one complete profile from canonical paragraphs. No audit fact may treat a
chunk row as the canonical wording of the norm. Two versions exist:

| version | joins | over `unreliable_count > 0` |
| --- | --- | --- |
| `characters-v1` | every paragraph (W33) | refused, by the projection and by the repository on the stored count |
| `characters-v2` | reliable paragraphs only; each unreliable paragraph ends the chunk | built; the loader's default |

`characters-v2`'s invariant, checked before any chunk row is written: chunks are ordinals
`0..n-1`, each spans consecutive canonical paragraphs, spans are disjoint and ascending, and
their union is exactly the reliable paragraph set. With nothing unreliable the two versions
agree chunk for chunk.

## Transaction and idempotency boundary

The source corpus is validated and projected through the `norms` filesystem boundary. The
repository then performs only PostgreSQL writes in the caller's transaction:

1. insert the opaque snapshot guarded by unique `content_key`, or verify the existing row;
2. if it is new, allocate one fresh opaque ID for every document and paragraph, then insert
   those canonical entities and the initial chunk profile;
3. return counts and the opaque snapshot identity; an exact replay reuses every stored child ID;
4. caller commits once, or rolls the whole load back.

A replay that names a chunk profile the stored snapshot lacks builds that profile from the
stored canonical paragraphs inside the same transaction; nothing else is written.

## Import with ids and the row digest

The promotion database (`W54-PLAN.md` §3.2) is the only place opaque norm ids are minted.
Another database receives them through `import_snapshot(session, rows, chunking_profiles=…,
expected_row_digest=…)`, which takes `SnapshotRows` — the snapshot row, every document and
every paragraph with their opaque ids and declared columns — and, in one SAVEPOINT:

1. validates the rows as one snapshot (id formats and uniqueness, counts and ordinals, the
   vocabularies, unreliable paragraphs only under `unreliable_count > 0`, the `+seg-` term)
   and compares their digest with the expected one; refuses `characters-v1` over unreliable
   text — all before reading the database;
2. **exact replay** (same id, same key, equal stored digest, every named profile built) is a
   no-op; the same key under another id, the same id under another key, equal ids with other
   rows, an unbuilt profile on replay, or a document or paragraph id held by another snapshot
   is refused (`SnapshotImportConflict`) with nothing written;
3. otherwise inserts every row with its own id (private keys minted and remapped by the
   document's id), builds each named profile from the inserted paragraphs, and re-reads the
   row digest, which must equal the rows'.

**Row digest** (`norm-snapshot-rows/1`): SHA-256 over a version line, then one line per row —
`S`, `D` or `P` followed by a compact JSON array of the declared columns in a fixed order —
with documents sorted by `norm_document_id` and paragraphs by `(norm_document_id, ordinal)`
(code-point order, `COLLATE "C"` in SQL). It covers ids, text and `text_reliability`; private
keys, timestamps, generated columns and the rebuildable chunks are not covered. The loader
prints it; the repository recomputes it from the database as a stream.

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
