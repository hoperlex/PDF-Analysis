# DECISION-MEMORY-01 — expert decision memory, and normative material for external executors

**Status: design only.** Written 2026-11-07 by design lane M (`agent/lane-decision-memory-01`), base
`origin/dev` `dcb0083b9` (API contract `1.35.0`, migration head `0056_optimisation_decisions`). This document
changes no contract, migration, product code or test. Everything in sections 3 to 8 is a proposal until the owner
has answered section 9, where the decisions only the owner can make are collected. Sources are cited as `path:line` at
the base commit; what was not verified is listed in section 10.

## 1. Goal and non-goals

### 1.1 The owner's words

Recorded in `docs/program/ROADMAP.md:247-268` (section «Owner goals of 2026-11-07», items 2 and 3), and relayed to
this lane as:

> a system for saving expert decisions together with the crops they concern, in a vectorised segment of the
> database, to be used later — so that projects and documents can be deleted without losing the context of decisions
> taken. In effect, data collection for fine-tuning a model or building dynamic prompts, not to mention hints for
> experts in the interface in similar cases.
>
> dynamic delivery of the needed crops of the normative base to an external executor when needed.

ROADMAP's own wording adds two constraints this design keeps: the memory is filled **when the decision is taken**, and
«the stored decision is the expert's recorded fact (AGENTS.md §4: model output is never the canonical decision); a hint
drawn from it is labelled as a hint».

### 1.2 Outcomes (each checkable)

- **O1 Capture.** A decision on a finding leaves a memory case holding the decision fact, the finding text, the
  evidence quotes with page geometry, the normative references and the crop images or text spans the expert looked at.
  Erasing the project or the document afterwards leaves the case readable.
- **O2 Search.** Cases are found by meaning (pgvector, the profile the normative corpus already uses) together with
  filters (section, category, verdict, status).
- **O3 Export.** An operator exports a filtered, consent-gated, auditable training dataset.
- **O4 Dynamic prompts.** A model call may carry a few similar decided cases, labelled as examples.
- **O5 Hints.** An expert looking at a finding sees «похожие случаи», labelled as a hint.
- **O6 Normative material.** A task for an external executor carries exactly the normative paragraphs and crops it
  declared, never the corpus, under an explicit consent flag, and the answer cites them back verifiably.

### 1.3 Non-goals

- The memory is **not a decision authority.** While the source finding exists, the ledger decides what stands
  (`finding_current_verdict`); no product behaviour reads a verdict from the memory. Once the source is gone the memory
  is the only remaining copy of the *context*, and is read-only history.
- No model writes a memory decision, labels a case or ranks one as «correct». No fine-tuning job runs here; the output
  is a dataset file.
- No image embedding (the profile is text-only), no cross-organisation sharing (`R-146d`: one organisation), no
  automatic retention limit (`R-146c`).
- No change to `JobPackage v1` (the internal engine package), to analysis results or to comparison evidence. Decisions
  on optimisation proposals (`optimisation_proposal_decision`, `opd_`) are the same idea in another shape: phase M8.
- The executor never searches the corpus and never receives more than its task declared.

## 2. What the tree says today (premises)

| # | Fact | Where |
| --- | --- | --- |
| P1 | An expert decision is a row of `expert_decision_event`; `UPDATE` and `DELETE` raise `AM002` from a trigger. The model never writes one. Every producer ends in `record_decision`: `appendDecision` (through `DecisionAdapter.append_decision` and `append_decision_under_key`), the confirmed carryover, and the workbook import. | `src/auditmanager/decisions/ledger.py:3-14`, `:276-408`, `:538`; `src/auditmanager/bootstrap/adapters.py:2527-2542`; `src/auditmanager/decisions/carryover.py:312`; `src/auditmanager/exports/xlsx/decision_import.py:183`; trigger `db/migrations/versions/20260910_0002_pc01_schema.py:208-214`, `:1270-1276` |
| P2 | The event holds `decision_id`, `finding_uid`, `finding_observation_id`, `event_type` (`accept`, `reject`, `comment`; `revoke` is refused), `verdict`, `severity`, `comment` (≤ 4000), `author_label`, `author_user_uid`, `recorded_at`, `command_id`. The request must name the observation the expert reviewed. | `ledger.py:96-108`, `:193-218`; `contracts/api/v1/openapi.json` `AppendDecisionRequest`, `DecisionEvent` |
| P3 | The carryover renders its provenance into the event's `comment`; the workbook import calls `record_decision` with **no `command_id`**, so neither "carried" nor "imported" is a column. | `carryover.py:1-30`, `:137-150`; `decision_import.py:183-186` |
| P4 | Project, document and version names are **joined at read time and stored nowhere**; the version's section is `version_classification_current.section_code`. | `src/auditmanager/decisions/journal.py:54-67` |
| P5 | `ADR-0012`: the similar-case index is a *rebuildable projection*; owner `R-16`: «never a source of truth». The one exception is the operator project erase (`R-146o`), which deletes a project's decision events with the project and keeps only the record of the erasure. | `docs/architecture/adr/ADR-0012-expert-decision-ledger-and-kb-projection.md:7-23`; `docs/program/OWNER_RULINGS_2026-09-17.md:266-283`; `docs/architecture/adr/ADR-0022-production-data-governance.md:89-134` |
| P6 | Evidence of an observation: `finding_text`, `recommendation_text` (≤ 4000 each); `finding_evidence` rows (`page_number`, `quote` ≤ 2000, `char_start`/`char_end` into the *prepared text layer*, optional `block_id` `b_NNNNNN`); up to five verified `finding_observation_norm_citation` rows (ids, `quote` 20–4000). **No evidence row names a crop or a portal block.** | `20260910_0002_pc01_schema.py:916-1009`; `20261016_0023_norm_citations.py:355-385`; `openapi.json` `Evidence`, `NormCitation`, `FindingObservation` |
| P7 | Crops exist only for **portal IMAGE blocks** (`crop_policy: portal_image_blocks`), as PNG Blobs (long side ≥ 800 px, ≤ 4 000 000 px) named in `geometry.page_crops`; a version without a bundle has `crops: []`. They are served by `streamVersionPortalBlockCrop`. | `src/auditmanager/api/schemas/blocks.py:15-26`; `contracts/analysis/v1/crop-manifest.schema.json`; `src/auditmanager/ingest/crop_geometry.py:48-56`; `src/auditmanager/api/routers/blocks.py:127-160`; `adapters.py:2301-2326` |
| P8 | Block geometry (`bbox`, `bbox_unit`, `bbox_origin`, `char_start`/`char_end`) is a property of the version, served by `getVersionBlocks`. | `schemas/blocks.py:50-62`; `blocks.py:56-75` |
| P9 | `blob_id` is derived from `(sha256, size)`; equal bytes are one Blob; a role belongs to the *binding*, not the Blob; the storage port has **no delete**; object keys are private. | `src/auditmanager/storage/README.md:45-50`, `:120-150` |
| P10 | The product purge classifies every table `PRODUCT`/`KEEP`/`MIXED` and stops on an unclassified one. A Blob referenced by **any `KEEP` table stays with its object**; the set is read from the live catalog. `expert_decision_event`, `finding*`, `project`, `document*` are `PRODUCT`. | `scripts/recovery/product_purge.py:1-46`, `:120-125`, `:134-166`, `:523-543` |
| P11 | The project erase deletes every row reachable from `project` by a **foreign-key closure**, switches one append-only trigger off at a time, deletes Blobs no other project and no `KEEP` table references, in four resumable phases, and keeps `erasure.requested`/`erasure.completed`. It refuses without an owner-permission reference (`R-146aj`). | `scripts/recovery/project_erase.py:1-60`; `ADR-0022:89-175` |
| P12 | No API operation deletes a project or a document; the only user-facing «delete» is the reversible document archive (`R-151a`). Deletion is an operator act. | `openapi.json` (operations named `archive*`, `purge*`, `setDocumentArchived`); `OWNER_RULINGS_2026-09-17.md:1919` |
| P13 | `expert_decision_event.author_user_uid` is a `RESTRICT` foreign key registered in `ACCOUNT_REFERENCES`, so an author's account cannot be purged (`R-61`). | `src/auditmanager/access/references.py:1-35`, `:70-75` |
| P14 | Vectors: pgvector 0.8.6; profile `bge-m3-dense-v1` (BAAI/bge-m3), 1024 dimensions, unit norm (CHECK), inner product, windows ≤ 512 tokens; HNSW `vector_ip_ops`, `m = 16`, `ef_construction = 64`; filtered search sets `hnsw.iterative_scan = strict_order`. | `db/migrations/versions/20261001_0013_norm_embeddings.py:25-27`, `:157`, `:172-176`; `src/auditmanager/norms/embedding/profile.py:14-21`; `src/auditmanager/norms/embedding_repository.py:24-28` |
| P15 | The encoder runs **only offline, inside the norms-worker image**; the corpus build runs there with `--network none` and no database; `embed-texts` refuses a text over 512 tokens instead of cutting it. `ADR-0020`: the embedding producer «may run as a separate execution process … publishes only through the existing transactional PostgreSQL boundary». | `src/auditmanager/norms/embedding/encoder.py:1-12`; `src/auditmanager/norms/README.md:92-126`; `ADR-0020-normative-corpus-alpha-runtime.md:48-50` |
| P16 | Pull-channel executors claim a task holding `system`, `user_text`, `output_schema` and **up to 8 PNG descriptors**; bytes are fetched one by one through the claim-bound `getExecutorTaskImage`; limits 8 images, 16 MiB each, 32 MiB in all; the payload is cleared 7 days after the task ends, only when a runner polls. | `openapi.json` `ClaimedExecutorTask`, `RunnerImage`; `src/auditmanager/executors/runner.py:155`, `:430-457`; `src/auditmanager/executors/image_input.py:1-25`, `:51-52` |
| P17 | The pull adapter writes a task and **waits for the answer inside the Attempt**, with a deadline derived from the watchdog; a task never claimed is `not_sent`. | `src/auditmanager/executors/pull.py:1-30` |
| P18 | Norm text reaches a model through the Run's pinned, verified **retrieval set** (a Blob) and prompt labels; a citation is verified against canonical paragraph text (`norm-quote-v1`) and stored with ids. | `src/auditmanager/findings/retrieval_set_input.py:1-15`; `src/auditmanager/runs/v3_citations.py:1-10`; `src/auditmanager/norms/citation_prep.py:1-10`, `:49`; `0023_norm_citations.py:355-385` |
| P19 | Norm source **crops are single-page PDFs** bound to a `norm_document` with anchor kind `crop` (opaque `blk_…`); the corpus has one whole-page block per page. Local drop: 28 246 crop PDFs; a random sample of 200 (python3, seed 1, `.local/norms/corpus/*/crops/*.pdf`): median 145 016 B, p95 210 577 B, max 11 212 554 B. | `docs/program/NORM_CORPUS_CUSTODY.md:5-33`; `src/auditmanager/norms/custody/roles.py:25-60`; `src/auditmanager/norms/corpus_source.py:483-489`; `OWNER_RULINGS_2026-09-17.md:284-294` |
| P20 | `allow_client_documents` is stored on every executor revision and **checked nowhere** (`D-291`, `ADR-0026` decision 19). The corpus is **internal use only** (`NORM-Q04`). Document text already reaches the provider (`A-2`); the runner channel hands the complete prompt to the operator's own session (`A-9`). | `docs/program/DEBT_REGISTER.md:188`; `docs/program/NORM_CORPUS_DECISION_BACKLOG.md:12`; `OWNER_RULINGS_2026-09-17.md:1810`; `ADR-0022:210` |
| P21 | Cross-context imports go through `<context>.public` only; `bootstrap` and `shared` are exempt. Identity prefixes are globally unique and frozen in the domain contract; the error catalogue has 27 codes and `EXEC-2` added none. | `tests/contract/architecture/test_alr05_boundaries.py:16-17`, `:116-122`; `src/auditmanager/shared/identity/ids.py:84-93`; `contracts/domain/v1/identifiers.json`, `error-codes.json`; `ADR-0026:` decision 18 |
| P22 | Roles: `appendDecision` is expert-only, `listDecisions` is any product role including viewer. The product has **no owner role**; the owner's permission enters as an operator-supplied reference. | `src/auditmanager/api/security.py:353-365`, `:594`, `:667`; `project_erase.py:44-46` |

## 3. Data model

### 3.1 Two records, two jobs

The ledger event stays the authority while its source exists. The **memory case** is a copy made in the same
transaction, for later use. Two parts of it have different standing, and the design keeps them apart:

- the **case content** (what the expert saw and said) is a *primary record from the moment of capture*: after the
  source is erased nothing can rebuild it. This amends `R-16`/`ADR-0012` for the content only (open question Q1);
- the **vectors and probes** stay *rebuildable projections*, exactly as `R-16` says.

Unit of capture: one **case** per `finding_observation_id` the expert reviewed (an immutable snapshot, unique on that
id, so capture is idempotent) and one **memory decision** per ledger event on it.

### 3.2 What is copied at decision time

| Field | Taken from | Class |
| --- | --- | --- |
| `source_decision_id`, `event_type`, `verdict`, `severity`, `decided_at` (= `recorded_at`) | the ledger event (P2) | fact |
| `comment` | the event | content (expert words, may quote the document) |
| `author_user_uid` | the event | opaque reference (not a name) |
| `origin_kind` ∈ `direct`, `carried`, `imported` | **new keyword on `record_decision`**, set by the carryover and the import (derivable only for the carryover, from its command type; the import writes no `command_id`, P3) | fact |
| `category`, `proposed_severity`, `required_value`, `stated_value` | the observation | content |
| `finding_text`, `recommendation_text` | the observation | content |
| evidence items: `ordinal`, `page_number`, `quote`, `char_start`, `char_end`, `block_ref`, and when the block is known `bbox` with `bbox_unit`/`bbox_origin` | `finding_evidence` and the version's block index (P6, P8) | content + geometry |
| normative references: `norms_snapshot_id`, `norm_document_id`, `norm_paragraph_id`, `designation`, `clause_number`, `page_label`, `quote`, `state` | `finding_observation_norm_citation` (P18) | opaque ids + quoted norm text |
| `section_code` **as of capture** | `version_classification_current` (P4) | fact |
| provenance: `stage_id`, `analysis_profile_id`, `prompt_bundle_id`, `provider_mode`, `model_identity` | the observation | identities and classifiers only |
| crops (3.5) with `selection_rule`, `page_number`, `bbox_norm`, `sha256`, `size_bytes`, pixels, and the portal's recognised text / description when present | the geometry artifacts (P7) | content |
| `data_class` ∈ `test`, `real` | an installation setting at capture time (Q3) | fact |
| `capture_version`, `content_sha256`, `captured_at` | the capture | fact |

**Not copied:** `author_label`, logins, project name, document title, file names, prompts, model responses, anything
from `model_call` (which stores checksums only, `ADR-0022:30-34`).

### 3.3 Identities that survive deletion

| Column | Meaning | Foreign key? | Resolvable after erase? |
| --- | --- | --- | --- |
| `origin_project_uid`, `origin_document_uid`, `origin_version_uid`, `origin_run_id`, `origin_finding_uid`, `origin_observation_id` | where the case came from | **none** | no — a lookup answers «источник удалён» |
| `source_decision_id` | the ledger event | **none** (the event is deleted by erase) | no |
| `norm_*` ids | the corpus rows cited | none (corpus retention is full, `NORM-Q06`) | yes |
| `author_user_uid` | the deciding account | **none** (Q7) | until the account is purged; then an orphan opaque id |
| `blob_id` of a crop | custody | **yes**, to `blob` | yes — kept alive by the binding (3.5) |

Rules: format `CHECK`s on every id as elsewhere; page numbers, block references and character offsets are
*attributes*, never identity (AGENTS §4); a column that names an account without a foreign key is a deliberate
exception and is written into the header of `access/references.py` with a test (P13).

### 3.4 Tables (context `decision_memory`)

*Identity side* — immutable (`am_immutable_row`), never deleted by any operation:

| Table | Key | Holds |
| --- | --- | --- |
| `decision_memory_case` | `dmc_<ULID>`; `UNIQUE (origin_observation_id)` | origin refs, `category`, `section_code`, `data_class`, `capture_version`, `content_sha256`, `captured_at` |
| `decision_memory_decision` | `dmd_<ULID>`; `UNIQUE (source_decision_id)` | `case_id`, `event_type`, `verdict`, `severity`, `author_user_uid`, `origin_kind`, `decided_at` |
| `decision_memory_status_event` | `dmw_<ULID>` | `case_id`, `kind` ∈ `withdraw`, `restore`, `forget`, closed `reason_code`, `actor_user_uid` (foreign key, `RESTRICT`), `command_id` (keyed ops), `owner_permission_ref` (forget only), `created_at` |
| `decision_memory_export` | `dme_<ULID>` | filter digest, counts, manifest sha256, actor, owner-permission reference, `data_class` mix, time |

*Content side* — written at capture and changed only by guarded state transitions (crops, intents); **deletable only
by `forget`** (4.5); keyed `(case_id, revision)` with `revision = 1` in v1 (a recapture after a capture defect, while
the source exists, would add revision 2):

| Table | Holds |
| --- | --- |
| `decision_memory_content` | `finding_text`, `recommendation_text`, severities, values, provenance |
| `decision_memory_decision_text` | the expert's `comment`, per memory decision |
| `decision_memory_evidence` | the evidence items and geometry |
| `decision_memory_norm_ref` | the normative references |
| `decision_memory_crop` | crop custody (3.5) |
| `decision_memory_embedding` (+ `…_intent`) | vectors (3.6) |

*Product class (deleted with the project):* `decision_memory_probe` — the query vector of a finding not yet decided
(5.3), with a foreign key to `finding_observation`, so the erase's closure removes it.

The split exists so that `forget` can delete content without ever updating an immutable row, and still leave a
tombstone (who, when, which `content_sha256` was forgotten) that proves what is gone without holding it.

### 3.5 Crop custody (objects owned by the memory, not by the document)

- A crop is a `decision_memory_crop` row with `blob_id → blob`. Because `blob_id` is content-derived (P9), «copying»
  a portal crop is **a binding, not a byte copy**: the existing Blob is referenced from a `KEEP` table, and the
  existing purge/erase logic keeps a Blob a `KEEP` table references (P10, P11). Capture of an existing crop therefore
  has **no external side effect** and cannot be a dual write.
- A text-evidence region has no crop today (P6, P7). If the owner wants pixels for it (Q6), the memory renders the
  evidence block's bbox with the geometry stage's own plan rules (long side ≥ 800 px, ≤ 4 MP) under `PDFIUM_LOCK`. That
  *is* an external effect (a new object), so the capture writes a `pending` crop row — intent and outbox in one,
  the shape of `norm_custody_admission` (`0018_norm_custody.py:7-13`) — and a dispatcher renders, publishes through
  `BlobStore.put_blob`, and moves the row to `ready`; five tries, then `poisoned` and visible; `requeue` returns it.
- **Selection rule v1** (capture, per case, at most 4 crops, size limits of P16 apply): (a) when the version has a
  portal bundle, the IMAGE blocks of the evidence page whose box intersects the evidence block's box; (b) when Q6 says
  yes, a region render of the evidence block; (c) otherwise the case records `crop_state = none_available` as an
  explicit fact. Because the ledger does not link evidence to portal blocks (P6), rule (a) is a geometric
  heuristic: every crop stores `selection_rule = 'page_intersect/1'` so a better rule is distinguishable later.
- Verification: sha256, size and media type are checked at publication as the geometry stage does; the blob
  reference audit gets the new source column (`scripts/recovery/blob_reference_audit.py:46`), so a restore proves the
  memory's crops exist.
- Serving: a memory-owned read (`streamDecisionMemoryCrop`), `ETag` = sha256, private cache, as P7.

### 3.6 Embedding

- **What is embedded:** text only. Two views per case: `evidence_v1` (the evidence quotes plus the portal's
  recognised text/description of the crops) answers «what did the document say here»; `finding_v1` (category label,
  `finding_text`, head of `recommendation_text`) answers «what was called out». The builder
  `decision-memory-embedding-input/1` applies a fixed character budget so a view fits 512 tokens; the encoder refuses
  longer text (P15), so a budget miss becomes a visible `poisoned` intent, never silent truncation. The budget is
  calibrated against the tokenizer in phase M4 (not measured here).
- **Model:** `bge-m3-dense-v1`, 1024 dimensions, unit norm, inner product. Stored per row: `embedding_profile`,
  `model_revision`, `input_sha256`, `embedding_sha256`, `vector(1024)` with the unit-norm CHECK of `0013`. Arithmetic,
  not measurement: 1024 × 4 B = 4 KiB per vector, ≈ 8 KiB per case before index overhead.
- **Index:** HNSW `vector_ip_ops`, `m = 16`, `ef_construction = 64`, the type the corpus index already uses
  (`0013_norm_embeddings.py:172-176`); IVFFlat is rejected because it needs training data. Queries use the same
  `iterative_scan = strict_order` settings and refuse a short answer (P14). Filters (section, category, status,
  `data_class`) apply after the scan; for a small case count an exact scan is acceptable and M4 chooses on
  measurement.
- **Re-embedding policy:** vectors are projections. A new profile adds rows keyed `(case, view, profile)`; the old
  stay until the owner drops that profile; the current profile is a setting. A different dimension needs a new
  column or table because a pgvector index is fixed-dimension. Re-embedding reads `decision_memory_content` and the
  evidence rows only, never the source product tables, so it works after erase.
- **Producer:** a separate embedder process in the norms-worker image (`ADR-0020:48-50`) claims
  `decision_memory_embedding_intent` rows (`FOR UPDATE SKIP LOCKED`, five tries, then `poisoned`) and writes the vector
  and the `done` transition in one transaction. It needs database access, so the corpus build's `--network none`,
  no-database isolation does not carry over: it gets its own restricted role (`SELECT` on the content tables,
  `INSERT` on embeddings and probes, nothing else). This is the main deployment risk (section 8, R6).

### 3.7 Append-only, correction and withdrawal

- The four identity tables are immutable. A later expert decision on the same finding is a new ledger event and
  therefore a **new `decision_memory_decision` row of the same case**; the memory's current verdict is the latest
  verdict-bearing row (a view `decision_memory_case_current`, mirroring `finding_current_verdict`). A `comment` event
  is a row with `verdict` NULL.
- There is **no edit path** for a memory decision. A case whose source is gone accepts only status events.
- **Withdraw** (reversible) excludes a case from hints, prompts and exports; **restore** reverses it; both are
  append-only status events with a closed `reason_code` (`capture_defect`, `wrong_decision`, `client_request`,
  `test_data`, `other`; no free text, for the reason `ADR-0022:101-104` gives for the erase). The current status is the
  latest event. History is never rewritten. **Forget** is terminal and is 4.5.
- `origin_kind` `carried` and `imported` cases are kept but are **not independent judgements** of the expert for the
  new finding: training export excludes them by default (5.1); hints show them with their label.

## 4. Deletion semantics

### 4.1 What deleting a project or a document does to the memory

Nothing. The memory has no foreign-key path to any project-scoped table, so the erase's closure cannot reach it; every
memory table except the probe is `KEEP` in the purge; the crops' Blobs are kept by the rule of P10/P11.

| Operation | Case, decisions, content | Crop Blobs | Probe |
| --- | --- | --- | --- |
| archive a document (`R-151a`) | untouched | untouched | untouched |
| project erase (`ADR-0022` §3) | **untouched** (origin refs dangle by design) | kept | deleted with the project |
| project erase of a client's data on request | untouched unless the operator also runs `forget` for the project (Q2) | as forget decides | deleted |
| product purge at the 1.0 release (`ADR-0022` §4) | kept unless the operator passes a memory flag (Q3) | kept | deleted |
| `purgeUser` | allowed (no foreign key); the author id becomes an orphan | n/a | n/a |
| restore from a dump | restored with the database; crops need the bucket mirror, and the blob audit checks them | audited | rebuilt |

### 4.2 Personal data

- **Kept:** `author_user_uid` (an opaque id; the `app_user` row is the only link to a person, and `purgeUser` cuts it),
  decision times, the expert's comment verbatim.
- **Not copied:** display name, login, project and document names (3.2).
- **Not removable automatically:** names, addresses and signatures *inside* quotes, comments and crops (title blocks,
  stamps). v1 does no automatic redaction; the protection is control of who may read and what may leave: reads need
  `expert`/`admin`, exports need an owner-permission reference for `real` data (5.1). An optional exact-string scrub of
  the project's and the document's own names from text fields, recorded as a count, is a phase M5 option.

### 4.3 Classification in the recovery tools

The forcing function already exists: the purge, the erase and `schema_coverage` all stop on an unclassified table, so
the migration cannot merge without these edits (`product_purge.py:1-20`).

| File | Change |
| --- | --- |
| `scripts/recovery/product_purge.py:120` | add `KEEP_MEMORY_TABLES` (all memory tables except the probe) to `KEEP_TABLES`; `decision_memory_probe` to `PRODUCT_TABLES` (`:134`) |
| `product_purge.py:170`, `:176` | `KEEP_EVENT_PREFIXES += "memory."`; `KEEP_COMMAND_TYPES += withdraw_decision_memory_case, restore_decision_memory_case` (their `command_record` rows are referenced by `KEEP` rows) |
| `scripts/recovery/schema_coverage.py:41`, `:44`, `:113` | `HEAD`, `TABLES`, `TRIGGERS` (immutable guards, state guards, forget guard) |
| `scripts/recovery/blob_reference_audit.py:46` | the crop column as a Blob source |
| `scripts/recovery/project_erase.py` | guards G1/G2 (4.4); the closing message says the memory remains; optional `--forget-memory` (Q2) |
| `src/auditmanager/access/references.py` | register the `RESTRICT` keys `decision_memory_status_event.actor_user_uid` and `decision_memory_export.actor_user_uid`; header note for the one account column without a key (Q7) |
| a new catalog test | no foreign-key path from `project` reaches a memory table; every memory table is `KEEP` or the probe `PRODUCT` |

### 4.4 Two guards that make «captured when taken» true

A guard needs a test proving it can fail; both follow the `# >>> guard:` convention of `product_purge.py:43-46`.

- **G1 uncaptured decisions.** Erase and purge refuse when any ledger event in scope has no `decision_memory_decision`
  row (read-only query). The sweep (7.2) normally closes any gap in seconds.
- **G2 pending crops.** They refuse when any `decision_memory_crop` of the scope is `pending` or `poisoned`, because a
  render needs the PDF. An explicit `--accept-memory-loss` writes the loss counts into the `erasure.requested` payload.

### 4.5 Forget (owner-only, audited)

- **What it removes:** the content-side rows of chosen cases (`--case`, `--origin-project`, or all), the vectors, the
  crop bindings and any Blob nothing else references. **What stays:** the case, its decisions and a `forget` status
  event with `owner_permission_ref` and the forgotten `content_sha256` — proof of what was forgotten, without content.
- **How:** an operator tool, `scripts/recovery/memory_forget.py`, modelled on `project_erase.py`: plan (dry run, digest)
  → one transaction (status events, delete content rows, exclusive Blobs to `erasure_pending`) → objects by exact key
  → finish; resumable; table-owner role; closed `--reason`; `--owner-permission-ref` required (`R-146aj`);
  `memory.forget_requested`/`memory.forget_completed` audit events with identities, counts and digests only.
  The guard on the content tables permits `DELETE` only when a `forget` event for that case was inserted in the **same
  transaction**; the application role holds no `DELETE` on them.
- **Why not an API operation:** the storage port deliberately has no delete (P9), and `ADR-0012`'s addendum keeps «no API
  operation, screen or job deletes or rewrites an expert decision event» for every product path; the copy should not be
  easier to delete than the ledger. An API operation that merely *requests* a forget is possible later (Q5).
- **What forget does not reach:** exports already produced, prompts already sent, dumps, and any model trained on an
  export — the list of `ADR-0022:175-181`, extended by the last item.

## 5. Uses

### 5.1 Training dataset export

- **Tool:** an operator command `python -m auditmanager.decision_memory.export` (an admin API operation may follow).
  It writes a directory: `manifest.json` (`auditmanager-decision-memory-export/1`), `cases.jsonl`,
  `images/<sha256>.png`.
- **A line of `cases.jsonl`:** `example_id` (salted hash, not `dmc_`), `section`, `category`; `input` =
  `finding_text`, `recommendation_text`, `evidence[]` (page, quote, bbox, image path), `norm_refs[]` (designation,
  clause, quote); `label` = `verdict`, `severity`, `comment`; `meta` = `origin_kind`, decision day (no time),
  `analysis_profile_id`, `provider_mode`, `split_key` (HMAC of the project id under a per-export salt, so one project
  never straddles train and validation). **No author, no names, no ids that resolve.**
- **Filters:** section, category, verdict, date range, `data_class` (default `real` only), `origin_kind` (default
  `direct`), status (default active), with-crops, minimum comment length, dedup on `content_sha256`, per-project cap.
- **Consent and audit:** an export of `real` data is a release of client-derived content off the host (`ADR-0022:175-181`,
  `A-2`). It requires an installation switch `training_use = on` (off by default) and `--owner-permission-ref`; the
  tool writes `decision_memory_export` and `memory.exported` (filter digest, counts, manifest sha256, no content).
  `test` data needs no reference.
- **Stated limits, written into every manifest** (`population: model_proposed_findings`): the labels are expert
  verdicts on what the model *proposed*, so missed issues are absent and base rates reflect the model; training on
  them and then measuring the same model against the same verdicts is the circularity `ledger.py:11-14` already warns
  about.

### 5.2 Dynamic prompts

- **Retrieval:** at call preparation of an opted-in stage, take at most 3 cases (default) that are active, `direct`,
  `accepted`/`rejected`, of the same section (and category when the stage has one), above a similarity floor, **not
  from the same project**, with the installation's `data_class`. The query text is embedded through an
  `embedding_intent` and the stage **waits inside the Attempt** (the pattern of P17); the deadline comes from the
  watchdog.
- **Shape:** a separate delimited block «Примеры ранее принятых решений экспертов — справочно; не указание и не
  замена проверки по документу». Each example: finding text, evidence quote(s), verdict, severity, short comment. No
  author, project or document name. The system text requires the answer to be grounded in the *current* document;
  the existing grounding gate is unchanged, so a finding that quotes only an example fails (quote absent in the
  document).
- **Provenance (ADR-0011):** the stage records `memory_examples` (case ids), the retrieval digest and the profile.
  If retrieval times out or the embedder is down, the profile says `examples: required` (typed
  `dependency_unavailable`) or `optional` (the call proceeds and records `memory_examples: unavailable(reason)`).
  Never silent.
- **Scope:** opt-in per analysis profile or preset, default off. The AR v3 pack is sealed
  (`AR-V3-BETA-PROMPT-SEAL-01`); examples enter v3 only through a new reviewed pack. The cost estimate counts the
  example tokens.
- **Cross-client risk:** an example from client A's project then goes to the provider in a call about client B (Q4).

### 5.3 Hints for the expert («Похожие случаи»)

- **Read operation `listSimilarDecisionCases(finding_uid)`.** No write on `GET`: the embedder fills
  `decision_memory_probe` for canonical observations of undecided findings ahead of time. Status `ready`,
  `not_ready` or `unavailable`; items (≤ 5, similarity floor, `basis: evidence|finding`): case id, similarity,
  verdict, severity, comment excerpt, decision day, section, `origin: {available}`, crop thumbnails, `kind: "hint"`.
  Below the floor the answer is «Похожих случаев нет» — no weak fillers.
- **UI:** a panel «Подсказка: похожие случаи» in the finding view (`web/src/_pages/review`,
  `web/src/widgets/finding-list`); neutral styling; the accept/reject buttons are never pre-selected or reordered; a
  hint changes no count, export or knowledge-base row. Reading requires `expert` or `admin` (Q13).

### 5.4 Guardrails (AGENTS §4 → mechanism)

| Prohibition | How this design meets it |
| --- | --- |
| LLM output as the canonical expert decision | memory decisions are only captured from ledger events with a human `author_user_uid`; no insert path for a model; hints and examples are labelled and never feed a verdict; export manifests state the population |
| path/filename/display number as identity | ULIDs and opaque refs; page, block reference and offsets are attributes (3.3) |
| dual-write DB + external side effect | capture is DB-only and in the decision's transaction; renders, embeddings and object deletion go through intent rows with a dispatcher and a sweep (3.5, 3.6, 4.5, 7.2) |
| deep imports | `decision_memory` imports `shared` and `storage.public` only; the assembler is in the composition root (7.1) |
| direct SQL/S3 from a router | routers call ports |
| job state only in memory | intents are rows |
| silent fallback | explicit `none_available`, `unavailable(reason)`, `poisoned`, `pending` states |
| generic repository/base service | typed repositories only |
| AI modifying raw deterministic comparison evidence | the memory is not read by comparison and writes nothing there |

## 6. Normative material for external executors

### 6.1 Principle: the server packs, the executor never searches

The pull channel is one-directional by design (P16, P17): the runner receives what the task contains and fetches
only descriptors the claim holds. Dynamic delivery is therefore **a manifest of declared needs, with lazy byte
retrieval of crops**, bounded by the manifest.

### 6.2 Declaration

A stage building its request declares `norm_needs`: items `{kind: text | crop, norm_paragraph_id, label}`. Each is
resolved **only inside the Run's pinned snapshot and verified retrieval set** (P18); a need outside it is refused,
`validation_failed` with `reason: norm_need_outside_pinned_set`. A `crop` need is admitted when the stage asks for the
source layout (a table, a figure, a formula); the paragraph's text is delivered with it, because the citation target
is always the text.

### 6.3 Packaging

The claimed task gains an optional `norm_material` array (the prompt in `user_text` refers to items by `label`; the array
is the structured, journalled record of what the task carries). Each item: `label`, `norm_document_id`,
`norm_paragraph_id`, `designation`, `clause_number`, `page_label`, `source_attribution`, `text` (verbatim canonical
paragraph text), and optionally `crop` = `{crop_id: "norm.<nbd_ULID>", blob_id, sha256, size_bytes, media_type,
width_px, height_px}`.

- **Bytes:** a crop is announced in `images` with `crop_id` (the opaque form `image_input.py` already supports) and
  fetched through the existing claim-bound `getExecutorTaskImage` — no new byte path.
- **Format:** custody stores a one-page PDF (P19) while `RunnerImage.media_type` is the constant `image/png`. The
  design renders once to PNG under `PDFIUM_LOCK`, publishes a Blob and records it in a derived-render row
  (`norm_crop_render`: source binding, render profile, `blob_id`) so repeated deliveries reuse it. Delivering the PDF
  instead is a contract change (Q9).
- **Limits:** the existing 8 images, 16 MiB each, 32 MiB total (P16), plus per-task caps proposed here and not
  measured: at most 12 paragraphs and 24 000 characters of norm text. Over a cap: `validation_failed`,
  `reason: norm_material_budget`. A copy of the corpus is impossible: items come from the pinned set and are bounded.
- **A crop that cannot be produced** is listed as `crop: {unavailable: <reason>}`; the text is still delivered; the
  gap is recorded, never dropped.

### 6.4 Custody and consent

- **Flag `allow_norm_material`** on the executor connection revision, default false, set by an administrator as a
  recorded revision, **enforced at packaging from its first commit**: a task for a connection without it is refused
  before any send with `conflict` (`reason: norm_material_not_allowed`). It is independent of
  `allow_client_documents` (client content, unenforced, `D-291`); the guard test must show the flag can refuse.
  Rationale: the corpus is internal-use (`NORM-Q04`) and a page crop is more than an excerpt (Q9).
- **Delivery journal:** append-only `norm_material_delivery` (`KEEP`): opaque task id, connection revision, run id,
  `[(norm_paragraph_id, binding id, sha256)]`, counts and bytes, time. It answers «what left the host» for `NORM-Q04`
  and `A-9`; it holds no content.
- **Retention:** norm material lives in the task payload, so the 7-day clearing of P16 applies unchanged.
- **Non-pull executors** (`http_api`, `ssh`): the same builder; images ride the request; the call's request checksum
  covers the descriptors; the journal is written the same way.

### 6.5 Result citing back

The executor cites by `label`, the mechanism `citation_prep.py` already has. The server accepts only labels present
in the task's manifest and verifies each quote verbatim against the canonical paragraph text (`norm-quote-v1`); the
stored `finding_observation_norm_citation` names paragraph ids. A crop is **context, never a citation target**; a paragraph without reliable text cannot be cited at all (it is
excluded from labels, `citation_prep.py:200`, `:233`, and refused by `am_verify_norm_citation`,
`0023_norm_citations.py:422`). The answer schema
gains no crop field, and deterministic evidence is untouched.

`JobPackage v1` (the internal engine package, content-addressed artifact refs only) is not changed; extending it with
an optional `norm_material` property later is a minor contract change if the owner wants engine stages to receive
the same material.

## 7. Contract slice, migration sketch, bounded context, integration

### 7.1 Bounded context

New `src/auditmanager/decision_memory/` with `public.py`. It imports `auditmanager.shared` and
`auditmanager.storage.public` only. It is **not** part of `decisions`: that package's invariant is «views rebuild from
events» (`decisions/README.md`), the memory's content does not; retention, deployment (an embedder) and failure modes
differ; and `journal.py:8-15` is the precedent for keeping a differently-shaped read out of the ledger module.

- `decisions.public` gains a typed port `DecisionRecorded(session, event, origin_kind)` and a registration function;
  the ledger calls it and imports nothing from the memory.
- The **capture assembler** lives in the composition root (`bootstrap/adapters.py`, exempt from ALR-05, a hotspot):
  it reads finding, observation, evidence, citations, block geometry, section and crop manifest through the public
  APIs of `findings`, `documents`, `analysis` and `norms`, builds a plain snapshot and calls
  `decision_memory.public`.
- Normative material (section 6): resolution and render binding in `norms`; the flag, payload and journal in
  `executors`; nothing in `decision_memory`.

### 7.2 Where the decision write path copies into the memory

1. **Hook.** `record_decision` calls the port **after** the insert and the savepoint block, between
   `ledger.py:394` and `:396`, in the caller's transaction. All three producers pass through it (P1), so the hook
   covers them by construction. A capture failure propagates: the decision fails loudly (AGENTS §4, no silent
   fallback). Replays return before the insert (`ledger.py:338-341`, `:521-532`) and capture nothing new.
2. **Same transaction, not an outbox, for tier 1.** Tier 1 is DB-only reads of immutable rows and DB-only inserts
   (case, decision, content, evidence, norm refs, references to existing crop Blobs, intents). There is no external
   side effect to reconcile, and one transaction removes the window in which an erase could win. The outbox shape is
   used exactly where an external effect exists: crop render and publish, embedding, object deletion on forget.
3. **Idempotency.** `INSERT … ON CONFLICT DO NOTHING` on `origin_observation_id` and `source_decision_id`; a
   differing `content_sha256` for an existing case is `conflict`, not an overwrite.
4. **Sweep and backfill.** `decision_memory.sweep` (a loop step of the worker) selects ledger events with no memory
   decision (anti-join on `decision_id`) and captures them. It performs the first backfill of every existing
   decision, and it is the repair path for a gap; G1 (4.4) keeps a gap from becoming a loss.

### 7.3 Contract slice (proposal; one contract-owner slot, minor bump)

| Operation | Method path | Role | Keyed | Notes |
| --- | --- | --- | --- | --- |
| `listDecisionMemoryCases` | `GET /decision-memory/cases` | expert, admin | no | filters: section, category, verdict, status, `data_class`, `origin_project_uid`; cursor |
| `getDecisionMemoryCase` | `GET /decision-memory/cases/{case_id}` | expert, admin | no | content, decisions, status, crops; a forgotten case answers its tombstone only |
| `streamDecisionMemoryCrop` | `GET /decision-memory/cases/{case_id}/crops/{crop_id}` | expert, admin | no | `image/png`, `ETag` = sha256 |
| `listSimilarDecisionCases` | `GET /findings/{finding_uid}/similar-cases` | expert, admin | no | the hint (5.3); no side effect |
| `withdrawDecisionMemoryCase`, `restoreDecisionMemoryCase` | `POST /decision-memory/cases/{case_id}/withdraw`, `…/restore` | admin | yes | `state_transition_not_allowed` if already in that state |
| `getDecisionMemoryStatus` | `GET /decision-memory/status` | admin | no | counts by status and `data_class`; pending crops and embeddings |
| (task payload) | `ClaimedExecutorTask.norm_material` | runner token | n/a | 6.3 |
| (revision field) | `ExecutorConnectionRevision.allow_norm_material` | admin | existing ops | 6.4 |

Training export and forget are operator tools in v1 (4.5, 5.1). **No new error code**, following `ADR-0026` decision 18:
`not_found`, `validation_failed` (`norm_need_outside_pinned_set`, `norm_material_budget`), `conflict`
(`memory_case_forgotten`, `memory_case_withdrawn`, `norm_material_not_allowed`), `state_transition_not_allowed`,
`dependency_unavailable` (`dependency: memory_embedder`), `permission_denied`. Domain contract: identity prefixes
`dmc`, `dmd`, `dmx`, `dmw`, `dme`, `dmi`, `nmd`, `ncr` (none is in use, `ids.py`), and the state sets of the crop and
embedding intents.

### 7.4 Migration sketch (`0057_decision_memory`; take the next free head at integration)

```text
decision_memory_case        (case_id dmc PK, origin_observation_id UNIQUE, origin_finding_uid, origin_project_uid,
                             origin_document_uid, origin_version_uid, origin_run_id, category, section_code NULL,
                             data_class CHECK IN ('test','real'), capture_version, content_sha256, captured_at)
decision_memory_decision    (memory_decision_id dmd PK, case_id FK, source_decision_id UNIQUE, event_type, verdict NULL,
                             severity NULL, author_user_uid (no FK), origin_kind CHECK IN ('direct','carried','imported'),
                             decided_at, captured_at)
decision_memory_status_event(status_event_id dmw PK, case_id FK, kind CHECK IN ('withdraw','restore','forget'),
                             reason_code CHECK (closed list), actor_user_uid FK app_user RESTRICT,
                             command_id FK command_record NULL, owner_permission_ref NULL, created_at DEFAULT now())
decision_memory_content     (case_id, revision, finding_text, recommendation_text, proposed_severity, required_value,
                             stated_value, stage_id, analysis_profile_id, prompt_bundle_id, provider_mode,
                             model_identity, PK(case_id, revision))
decision_memory_decision_text (memory_decision_id PK, comment NULL, CHECK length <= 4000)
decision_memory_evidence    (case_id, revision, ordinal, page_number, quote, char_start, char_end, block_ref NULL,
                             bbox_x0..y1 NULL, bbox_unit NULL, bbox_origin NULL, PK(case_id, revision, ordinal))
decision_memory_norm_ref    (case_id, revision, ordinal, norms_snapshot_id, norm_document_id, norm_paragraph_id,
                             designation, clause_number NULL, page_label, quote, citation_state)
decision_memory_crop        (crop_id dmx PK, case_id, revision, evidence_ordinal NULL, kind, selection_rule, page_number,
                             bbox_norm, state CHECK IN ('pending','ready','poisoned'), attempts, blob_id NULL FK blob,
                             sha256, size_bytes, media_type CHECK 'image/png', width_px, height_px, source_ref NULL;
                             CHECK state='ready' => blob_id NOT NULL; state-guard trigger like analysis_artifact_publication)
decision_memory_embedding_intent (intent id dmi PK, case_id, revision, view_kind, embedding_profile,
                             state CHECK IN ('pending','done','poisoned'), attempts, UNIQUE(case_id,revision,view_kind,embedding_profile))
decision_memory_embedding   (case_id, revision, view_kind, embedding_profile, model_revision CHAR(40), input_sha256,
                             embedding_sha256, embedding vector(1024) NOT NULL,
                             CHECK abs(vector_norm(embedding) - 1.0) <= 0.0001, PK(case_id, revision, view_kind, embedding_profile))
decision_memory_export      (export_id dme PK, filter_digest, counts, manifest_sha256, actor_user_uid FK RESTRICT,
                             owner_permission_ref NULL, created_at)
decision_memory_probe       (finding_observation_id FK finding_observation, view_kind, embedding_profile, input_sha256,
                             embedding vector(1024), PK(...))   -- PRODUCT class
VIEW decision_memory_case_current  (latest status event, latest verdict-bearing decision)
INDEX ix_decision_memory_embedding_hnsw_ip ON decision_memory_embedding USING hnsw (embedding vector_ip_ops)
      WITH (m = 16, ef_construction = 64)          -- the extension is already installed by 0013
INDEX (section_code, category), (origin_project_uid), (case_id, created_at) on the status events
TRIGGERS  am_immutable_row on case, decision, status_event, export; state guard on crop and intents;
          forget guard on the content tables (DELETE only with a same-transaction 'forget' event)
```

The downgrade refuses while any row exists (the pattern of `0020`/`0056`): a populated memory is restored from a
backup, never dropped silently. A second migration, owned by the executors/norms slot, adds
`executor_connection_revision.allow_norm_material`, `norm_material_delivery` and `norm_crop_render`.

**Hotspots that need one owner at a time (AGENTS §3):** `contracts/**` (API, domain identifiers, state machines), the
migration head, `bootstrap/adapters.py`, `scripts/recovery/{product_purge,project_erase,schema_coverage,blob_reference_audit}.py`,
`api/security.py` `OPERATION_ROLES`, the generated web client. The phases below are cut accordingly.

## 8. Phases, sizes, risks

Sizes are relative: **S** ≈ one lane, **M** ≈ two to three lanes, **L** ≈ a wave. They are not measured estimates.

| Phase | Content | Size | After | Checkable result |
| --- | --- | --- | --- | --- |
| M0 | Owner answers (section 9); `ADR-0027` and addenda to `ADR-0012`, `ADR-0022` §1; contract and prefixes reserved | S | — | the addenda exist |
| M1 | Capture core: migration, context, port hook, assembler (text, evidence, norm refs, portal-crop references), sweep and backfill, classification edits (4.3), G1, `origin_kind` keyword | M | M0 | decide → case exists; erase and purge leave it; unclassified-table and no-FK-path tests |
| M2 | Forget tool, withdraw/restore operations, status read, `data_class` and `training_use` settings | M | M1 | forget plan/commit/resume proved; guard mutation tests |
| M3 | Region renders, intent dispatcher, G2, crop stream operation | M | M1 | a pending crop blocks an erase; a rendered crop survives it |
| M4 | Embedder process, role and image deployment; intents; probes; HNSW; hint operation and panel; **measure** latency, recall, token budget | L | M1 | hints on a synthetic set; measured figures recorded with their command |
| M5 | Export tool, manifest, splits, audit; optional name scrub | M | M2 | a re-run produces the same manifest sha256 |
| M6 | Dynamic prompts: embed-wait path, profile flag, provenance, cost estimate | M–L | M2, M4 | a recorded call lists its example ids |
| M7 | Normative material: resolution, render binding, flag + migration, packaging, delivery journal, citation-back checks | L | M0 (independent of M1–M6) | a task carries only declared items; flag refusal proved; journal rows |
| M8 | Memory of optimisation proposal decisions (`case_kind`) | M | M1 | same guarantees for `opd_` |

M7 can run in parallel with the memory phases; M3 and M4 can run in parallel after M1.
### Risks

| # | Risk | Mitigation |
| --- | --- | --- |
| R1 | **Test data enters the production memory** and later exports: the 1.0 purge keeps `KEEP` tables | `data_class` on every case; export defaults to `real`; the purge flag is a question for the owner (Q3) |
| R2 | A client's erase request conflicts with a memory that holds their content | `forget --origin-project`; the erase tool's closing message names it; Q2 |
| R3 | A decision commits but its crop was never rendered and the PDF is erased | G2 refuses; `--accept-memory-loss` records the loss |
| R4 | A fourth producer of decisions skips capture | the hook is inside `record_decision`; sweep; G1 |
| R5 | Cross-client content in prompts and exports (`A-2`) | same-project exclusion, `data_class` filter, consent switch, Q4 |
| R6 | The embedder needs database access that the corpus build deliberately lacks; heavy CPU/RAM on a shared VPS; offline-only model | separate process and restricted role; measured in M4 before any promise; nothing in M1–M3 depends on it |
| R7 | Labels reflect only model proposals; circular evaluation | manifest `population`; separate evaluation set from independent review |
| R8 | Hints anchor the expert (rubber-stamping) | label, no pre-selection, similarity floor, `origin_kind` shown; agreement measurement is a later option |
| R9 | Few cases early: hints are noise | floor and «Похожих случаев нет»; no fillers |
| R10 | Personal data inside quotes and crops cannot be redacted | access control, consent, owner reference (4.2) |
| R11 | Norm material leaves the host contrary to `NORM-Q04` | flag default false, enforced; delivery journal |
| R12 | Contract, migration and composition-root hotspots collide with the other lanes | one owner per hotspot (list after 7.4) |

## 9. Questions only the owner can decide

- **Q1. Amend `R-16`/`ADR-0012`.** `R-16` says the similar-case index is «never a source of truth». The 2026-11-07 goal
  needs the *case content* to be a primary record that outlives its source, with only vectors and probes rebuildable.
  Confirm this amendment (and the matching one to `R-146o`, which says an erase leaves only the record of the
  erasure). *Recommendation: confirm; record as `ADR-0027`.*
- **Q2. Client erase.** When an operator erases a project on a client's request (`reason: client_request`), should the
  memory derived from it be forgotten in the same run, or stay unless asked? *Recommendation: stay by default,
  `--forget-memory` available, the closing message names it.*
- **Q3. Test data, real data and training use.** (a) Does the 1.0 release purge also clear memory built from the
  closed beta's test data? (b) May decisions on real client documents be exported for fine-tuning at all, to whom, and
  under what client-confidentiality terms? (c) Is `training_use` off until you switch it on? *Recommendation: (a) yes,
  by explicit flag; (b) your decision; (c) off by default.*
- **Q4. Cross-client examples.** May a decided case from client A's document appear as an example in a provider call
  about client B's document (`R-146d`: one organisation, but `A-2`: provider side)? *Recommendation: allowed only
  within one project until you decide otherwise.*
- **Q5. Who may forget.** An operator tool needing your permission reference (recommended, as for the project erase),
  or also an admin API request that an operator then executes?
- **Q6. Crops for text evidence.** Only existing portal image-block crops in v1, or also rendered regions of text
  evidence (title blocks contain names)? Cap per case (proposed 4)?
- **Q7. Author in the memory.** An opaque `user_uid` without a foreign key (recommended: `purgeUser` stays possible),
  with a `RESTRICT` key (blocks purging any author, `R-61`), or no author?
- **Q8. Which decisions.** Only `accept`/`reject`, or also `comment`; are carried and imported decisions kept (proposed:
  kept, excluded from training, shown in hints with a label)?
- **Q9. Normative material.** (a) May norm text and page crops leave the host to a configured executor at all
  (`NORM-Q04`: internal use only)? (b) Page crops as PNG renders (recommended) or as PDF (a contract change)?
  (c) Per-task caps (proposed 12 paragraphs, 24 000 characters)?
- **Q10. Embedder.** A resident process with database access in the norms-worker image (recommended; the only way to live hints
  and dynamic prompts; latency unmeasured), or batch embedding at night only (no live hints, no dynamic prompts)?
- **Q11. Fine-tuning target.** Text-only model or vision-language model, and which provider's format? It decides whether
  crops are exported and the line format.
- **Q12. Retention.** No automatic limit for the memory, consistent with `R-146c` — confirm.
- **Q13. Who sees hints.** Experts and admins (proposed), or viewers too?

## 10. Not verified in this design

- Embedding latency and recall, the character budget per view and the HNSW overhead: not measured; M4 measures them and
  records the command and the tree.
- PNG sizes of rendered norm crops (only the PDF sizes of P19 were sampled, on the local drop, not on a stand); how often
  an evidence page holds an IMAGE block that intersects the evidence block (the value of selection rule (a)); the number
  of decisions that exist today (the backfill's size).
- That the `DecisionRecorded` port passes the ALR-05 test as designed: the test reads imports only, and the composition
  root that registers the port is exempt. The web file layout named for the hint panel may move.
