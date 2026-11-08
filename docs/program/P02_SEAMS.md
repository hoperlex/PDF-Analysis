# P02 seam register — frozen at Gate A

> **Status: frozen by session `A1` on 2026-09-10.** Owner: `A1` until Gate A closes,
> then the integrator. Every Gate B session is a consumer of this document.
>
> Authority: `PROTOTYPE_WAVE_PLAN.md` §3, `GATE_A_BRIEFS.md` §6, and owner decision
> `OD-14`, which released the P02 contract family on 2026-09-10.
>
> Read-only upstream: `contracts/domain/v1/**`, `contracts/analysis/v1/**` and
> `contracts/events/v1/**`. Where this document and one of those disagree, the frozen
> contract wins and the disagreement is a defect in this file.

## 0. What this document is for, and how to use it

Gate B dispatches eight sessions at once against one commit. None of them waits on
another, which only works if the shapes they exchange are fixed before any of them
starts. This file fixes them.

If you are a Gate B session:

1. Find your seam in §1. It names what crosses it, who produces it and who consumes it.
2. Read the shape in §4, §5 or §6 and build to it exactly. Do not widen it "just in
   case" and do not narrow it because your slice does not need a field.
3. If you need something that is not here, **stop and hand it to the integrator**.
   Inventing a field, a table or a column locally is the failure mode this whole
   structure exists to prevent, and it surfaces at the Gate B convergence when it is
   expensive.

A seam change is a request with two parts: the shape you need, and the failing test
that shows why the current shape does not serve it. It is never a local edit.

## 1. The seam register

Seams `S1`–`S9` are carried over from `PROTOTYPE_EXECUTION_PLAN.md` §3.4 and re-owned
onto the Gate A/B session structure. `S10`–`S13` are the seams that structure made
newly explicit.

| Seam | What crosses it | Producer | Consumers |
|---|---|---|---|
| S1 | BlobStore access by `blob_id`, with the object-key layout confined to the adapter | `A3` | `B1`, `B2` |
| S2 | Input-manifest query for one published version | `B1` | `B5` |
| S3 | In-process stage runner returning a `StageResult` | `B2` | `B5`; `B3` registers `text_analysis` on it |
| S4 | Evidence gate returning a terminal, a published set and diagnostics | `B4` | `B5` during `validating` |
| S5 | Decision commands and finding queries | `B4` | `B6`, `B5` |
| S6 | Run commands and run status | `B5` | `B6` |
| S7 | Synchronous CSV export use case | `B5` | `B6` |
| S8 | The frozen OpenAPI document, `contracts/api/v1/openapi.json` | `A1` | `A5`, `B6` |
| S9 | Widget props and route URLs | `A5` | `B7`, `B8` |
| S10 | The P02 migration head and its constraints, `0002_pc01_schema` | `A1` | `B1`, `B2`, `B3`, `B4`, `B5`, `B6` — every session that writes a row |
| S11 | Opaque identifier value types, `auditmanager.shared.identity` | `A1` | `A3`, `B1`, `B2`, `B3`, `B4`, `B5`, `B6` |
| S12 | Engine, session and transaction construction, `auditmanager.shared.db` | `A1` | `B1`, `B2`, `B3`, `B4`, `B5`, `B6` |
| S13 | The stage-artifact shapes of §4 | `A1` (declared) / `B2`, `B3` (published) | `B3`, `B4`, `B5` |

`B1` is the only Gate B session that writes a Gate A tree: it adds the blob-metadata
repository under `src/auditmanager/storage/**`. The BlobStore port and the S3 adapter
stay exactly as `A3` left them.

## 2. Identity seams

### 2.1 The types

`src/auditmanager/shared/identity/` carries one value type per entity in
`contracts/domain/v1/identifiers.json`, with exactly the contract prefixes. Import
them; do not pass identities as bare `str`.

```python
from auditmanager.shared.identity import ProjectUid, RunId, FindingUid

run_id = RunId.new()                 # allocate
run_id = RunId.parse(untrusted_str)  # validate at the boundary
str(run_id)                          # the stored, transported, logged form
```

Three properties are enforced by construction, not by review:

* **Opaque.** There is no decoder anywhere in the codebase. `ulid.py` ships a
  generator and a shape check and nothing else, so no code can derive creation time,
  ordering or ownership from the body.
* **Type-separated.** `ProjectUid.parse("run_...")` raises `IdentifierPrefixError`. A
  mis-wired reference fails at the boundary rather than becoming a row pointing at the
  wrong table.
* **Also enforced in the database.** Every identity column carries a CHECK with the
  contract pattern for its prefix, so raw SQL cannot slip past the value type.

### 2.2 What is never an identity

`filesystem path`, `directory name`, `uploaded file name`, `S3 object key`, `bucket
name`, `URL or presigned link`, `display ordinal`, `human sheet or document number`,
`database row number or sequence value exposed to a client`, `provider request id`,
`model name`, `prompt text`, `idempotency key`, `payload fingerprint`,
`execution token`, `content checksum`.

Several of these exist as columns — `document_version.source_filename`,
`document_version.version_ordinal`, `blob.sha256`,
`expert_decision_event.sequence_no`. None is referenced by a foreign key, and none is
accepted as a path parameter. If your slice wants to key on one, that is the defect.

The object key and bucket name appear in **no** table at all. They live in `A3`'s
adapter, and that is deliberate: a column would have made them a de facto identity
within a release.

### 2.3 Non-identity value types

`CorrelationId`, `IdempotencyKey`, `PayloadFingerprint` and `Sha256` live in
`auditmanager.shared.identity.non_identity`, separated at the module level so the
distinction shows up in your import line. None may be used where an `OpaqueId` is
expected.

## 3. Persistence seam — the P02 migration head

**Original P02 head: `0002_pc01_schema`; W48 durable-effects head:
`0014_durable_analysis_effects`.** The W48 slot is the single owner of the new execution
authority/effect-journal DDL; earlier migrations remain immutable. `W54-SEAL-01` owns
`0018_norm_custody` (custody admissions and bindings, the repair-call journal, D-142's
`abandoned` publication and D-148's insert guards) and `0019_execution_workers` (the
worker registry and `lease.worker_id`). `W55A-SEAL-01` owns `0020_norms_search` (the one
current norms snapshot and its append-only history, `norm_paragraph.text_tsv` and
`norm_document.designation_tokens`). `W55B-SEAL-01` owns `0021_portal_bundles` (the
portal-bundle page ceiling of 500 and three nullable text-count columns on
`document_version`).
`W56A-SEAL-01` adds `0022_findings_v2`: seven categories, optional severity,
canonical observation identity and the fail-closed model identity code. The
default v1 profile remains unchanged. `W57A-SEAL-01A` adds
`0023_norm_citations`: an `nrs_` retrieval set, two R-76 artifact custody
roles, a frozen optional Run pin and a transaction-checked citation partition.
The v3 API and executor are separate serial work; this migration changes no
served profile. `W59-SECTION-SEAL-01` adds `0024_version_classification`: one
append-only, expert-confirmed project stage (`P`/`R`) and section per version in
`document_version_classification`, outside the immutable version row, and widens
the `document.section` CHECK by `PS` (`0011` keeps legacy's fourteen as history).
`CLASSIFICATION-CORRECTION-01` adds `0028_classification_corrections`: the append-only
`document_version_classification_correction` (revision 2, 3, ... with the correcting expert and a
reason; revision 1 is the unchanged original) and the views `version_classification_revision`
(the history) and `version_classification_current` (the latest revision, which every classification
read uses). `BETA-CONTRACT-SEAL-01` adds `0029_routing_refusal_codes`: the four stored-error
`CHECK`s (`command_record`, `audit_run`, `model_call`, `provider_call_effect`) admit the two
run-routing codes `version_classification_required` and `section_profile_unavailable` (`D-179`);
no table, column or row changes, and the downgrade refuses while a row carries either code.

### 3.1 Tables

| Table | Identity | Mutability |
|---|---|---|
| `project` | `project_uid` | mutable |
| `document` | `document_uid` | mutable; `current_version_uid` moves |
| `document_version` | `version_uid` | **immutable after insert** |
| `input_manifest_entry` | `(version_uid, role)` | **immutable after insert** |
| `blob` | `blob_id` | state transitions only; verified metadata write-once |
| `audit_run` | `run_id` | state transitions only; frozen set never edited |
| `command_record` | `command_id` | state transitions only; key and fingerprint frozen |
| `stage_result` | `(run_id, stage_id)` | mutable |
| `model_call` | `model_call_id` | **immutable after insert** |
| `job` | `job_id`; one per `run_id` | state transitions only; current Attempt is fenced |
| `attempt` | `attempt_id` | state transitions only; execution token is secret-class |
| `lease` | `lease_id`; one per Attempt | acquired once, released at terminal; `worker_id` frozen |
| `provider_call_effect` | `model_call_id` | inserted `prepared`; explicit effect-state transitions; request identity frozen |
| `analysis_artifact_publication` | `(attempt_id, stage_id, blob_id, blob_role)` | inserted `prepared`; `prepared → bound \| abandoned`; identity frozen |
| `worker` | `worker_id` | registry row; only `heartbeat_at` and `intake_enabled` change |
| `norm_custody_admission` | `norm_custody_admission_id` | custody intent and outbox; inserted `pending`; `pending → confirmed \| poisoned \| rejected`, `poisoned → pending \| rejected`; never deleted |
| `norm_custody_binding` | `norm_custody_binding_id`; one per confirmed admission | **immutable after insert**; insert needs a confirmed admission, its verified Blob and the target |
| `norm_retrieval_set` | `norm_retrieval_set_id` (`nrs_`) | **immutable after insert**; `verified` needs exact expected/observed digests and two confirmed artifact bindings |
| `norm_repair_call` | `norm_repair_call_id` (its own idempotency scope) | inserted `prepared`; `prepared → response_received → completed`, `prepared → not_processed \| outcome_unknown`; never deleted |
| `norm_current_snapshot` | one row (`singleton`) | the current norms snapshot; every insert or change names its own history event; never deleted (no unset) |
| `norm_current_snapshot_event` | `event_id` (`evt`) | **immutable after insert**: the append-only history of the current snapshot (actor, from, to, time) |
| `finding` | `finding_uid` | mutable |
| `finding_observation` | `finding_observation_id` | **immutable after insert** |
| `finding_observation_norm_citation` | `(finding_observation_id, citation_ordinal)` | **immutable after insert**; deferred count and CITE-stage proof bind each partition to the Run's verified set |
| `finding_evidence` | `(finding_observation_id, evidence_ordinal)` | **immutable after insert** |
| `expert_decision_event` | `decision_id` | **append-only: no UPDATE, no DELETE** |
| `audit_event` | `audit_event_id` | **append-only: no UPDATE, no DELETE** |
| `contract_state_transition` | reference data | frozen; not a domain aggregate |

Plus the view `finding_current_verdict`, which is §5.4.

**There is still no `import`, `export` or `comparison` table.**
W48-DURABLE-01 intentionally instantiates `job`, `attempt` and `lease`; `W54-SEAL-01`
instantiates the `worker` registry and the custody outbox (`norm_custody_admission`,
whose intent and outbox row are one record under R-76). The remaining absence set is
asserted so another scope change cannot arrive as a quiet convenience.

### 3.2 What the database refuses, and how to read the refusal

Three custom SQLSTATEs. All three map to the frozen catalog code
`state_transition_not_allowed`, whose summary names exactly these cases. They stay
distinct so an operator can tell which invariant fired without parsing a message.

| SQLSTATE | Fires when | Catalog code |
|---|---|---|
| `AM001` | a state column moves along an edge the contract does not declare, or an aggregate is inserted in a non-initial state | `state_transition_not_allowed` |
| `AM002` | UPDATE or DELETE on an append-only ledger | `state_transition_not_allowed` |
| `AM003` | UPDATE or DELETE on an immutable row, or an edit to a frozen or write-once column | `state_transition_not_allowed` |

The mapping is available as
`auditmanager.shared.db.schema.SQLSTATE_TO_CATALOG_CODE`. **Map on the SQLSTATE, never
on the message text.**

`B6`'s error middleware turns a `DBAPIError` carrying one of these into the envelope.
Nothing else in the stack should be catching them: a refusal here means the caller
asked for something the contract forbids, and the answer is the typed code.

### 3.3 The declared state topology

`contract_state_transition` holds the topology of the five machines the alpha runner
instantiates, seeded by the migration and frozen against further inserts. The trigger
consults it, so the enforcement and the declaration cannot drift.

* `audit_run` — initial `created`; `created → queued|cancelled`;
  `queued → running|cancelled|failed`; `running → validating|failed|cancelled`;
  `validating → published|partial|failed`. Terminals: `published`, `partial`,
  `failed`, `cancelled`. **There is no `succeeded` run state.**
* `blob` — initial `temporary`; `temporary → verifying|rejected`;
  `verifying → available|rejected`; `available → erasure_pending`;
  `erasure_pending → erased|available`.
* `command_idempotency`, on `command_record` — initial `in_progress`;
  `in_progress → succeeded|failed|abandoned`.
* `job` — initial `queued`; the local path walks `queued → leased → running` and then
  `running → succeeded|failed`; the complete frozen topology remains in reference data.
* `attempt` — initial `created`; the local path walks `created → leased → running` and
  then `running → succeeded|failed|lost`; the complete frozen topology remains in
  reference data.

The `import` machine remains **not instantiated**. Job and Attempt are now instantiated
only for local durable authority; remote dispatch and resume remain outside the claim.

### 3.4 Constraints your slice will meet

* `stage_result`: `succeeded` carries no `error`; every other status requires one;
  `skipped` carries no artifacts and a non-retryable error.
* `audit_run`: a `partial` run must record a non-empty `degradation_set`; a
  `published` run must record an empty one. A silent degradation cannot reach the
  success terminal.
* `audit_run`: a terminal state requires `terminal_at`; a non-terminal state forbids it.
* `command_record`: `UNIQUE (command_type, idempotency_key)`.
* `blob`: `UNIQUE (sha256, size_bytes) WHERE state = 'available'` — re-uploading
  identical content is idempotent by content, not by name.
* `finding_observation`: `grounded = (finding_uid IS NOT NULL)`, and
  `grounded = (ungrounded_reason IS NULL)`. An ungrounded item cannot appear in a
  finding query, by construction rather than by a `WHERE` clause somebody remembers.
* `finding_evidence`: `char_end - char_start = char_length(quote)`.
* `expert_decision_event`: at most one event per `command_id`.

### 3.5 Session and transaction construction

```python
from auditmanager.shared.db import session_scope, nested_transaction

with session_scope() as session:      # commits on clean exit, rolls back on any error
    ...
    with nested_transaction(session):  # SAVEPOINT for a step allowed to fail
        ...
```

No session builds an engine, reads `DATABASE_URL` or writes its own rollback. There is
no base repository, no generic CRUD service and no automatic retry — a retry that does
not consult the command record writes duplicates.

## 4. Stage-artifact shapes

Every artifact is JSON, published as a blob and referenced from the `StageResult`
`artifacts` array by `role`, `blob_id`, `sha256`, `size_bytes` and `media_type`. The
reference never carries an object key, a URL or a file name.

Every artifact document carries `artifact_role` and `artifact_version` at its root. A
consumer that reads an unexpected `artifact_version` **fails closed**; it does not
guess.

| Artifact role | Produced by | Consumed by | §  |
|---|---|---|---|
| `prepared.page_inventory` | `B2` `source_preparation` | `B2` `page_geometry_extraction` | 4.2 |
| `prepared.text_layer` | `B2` `source_preparation` | `B2` `page_geometry_extraction`, `B2` `document_context_build`, `B3` `text_analysis`, `B4` grounding gate | 4.3 |
| `geometry.block_index` | `B2` `page_geometry_extraction` | `B2` `document_context_build`, `B4` grounding gate | 4.4 |
| `geometry.page_crops` | `B2` `page_geometry_extraction` | `B6` `listVersionPortalBlocks`; `block_analysis` is W56 (`OD-04` flipped by `W55B-SEAL-01`) | 4.5 |
| `context.document_graph` | `B2` `document_context_build` | `B3` `text_analysis` | 4.6 |
| `analysis.text_observations` | `B3` `text_analysis` | `B4` grounding gate; W56a merge after grounding | 4.7 |
| `prepared.recognised_text` | `B2` `source_preparation` | `B6` `listVersionPortalBlocks`; optional marked context for W56a text analysis on text-less pages only | 4.8 |
| `findings.merged` | `B4` v2 deterministic `finding_merge` (implementation follows SEAL) | `B4` v2 finding publication | 4.11 |
| `geometry.portal_blocks` | `B2` `page_geometry_extraction` | `B6` `listVersionPortalBlocks`; `block_analysis` is W56 | 4.9 |
| `geometry.crop_image` | `B2` `page_geometry_extraction` | `B6` `streamVersionPortalBlockCrop` | 4.10 |

### 4.1 The offset rule — read this before anything else

`prepared.text_layer` defines **one document-global character sequence**. It is the
concatenation of every page's text, in ascending page order, with **no separator
inserted between pages**. Every offset anywhere in this system — evidence anchors,
block spans, the grounding gate — indexes that one sequence.

Offsets are counted in **Unicode code points** after the declared normalization. Not
bytes. Not UTF-16 code units.

This is the single most expensive thing in this document to get wrong. The corpus is
Russian: every quotation contains non-ASCII characters, so a byte offset would
misplace every anchor while still looking plausible in a test written in English. In
Python, `text[char_start:char_end]` on the concatenated sequence is the definition; a
`.encode()` anywhere near an offset calculation is the bug.

The normalization is declared once, in `text_layer.normalization.id`, and applied
once, by `source_preparation`. **No later stage normalizes again.** The grounding gate
compares exactly, after that one declared normalization and nothing else.

**What is not in this sequence** (`W55B-SEAL-01`, `R-116`, `R-117`). The portal's recognised
text (§4.8) is a separate artifact: it is never merged into `prepared.text_layer`, it has no
offsets here, and no evidence anchor indexes it. `document_version.text_character_count` is
pypdfium2's character count over the whole document -- it includes generated line breaks and
differs from this sequence's length -- and it is an input to the analysis input budget, never
an offset and never a statement about this sequence.

### 4.2 `prepared.page_inventory`

```json
{
  "artifact_role": "prepared.page_inventory",
  "artifact_version": "1.0.0",
  "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
  "source_blob_id": "blob_01M2545JSD15ETSNNV904X991H",
  "source_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "page_count": 12,
  "pages": [
    {
      "page_number": 1,
      "width_pt": 595.28,
      "height_pt": 841.89,
      "rotation_deg": 0,
      "has_text_layer": true,
      "char_count": 1873
    }
  ]
}
```

* `page_number` is 1-based, contiguous from 1 to `page_count`, and is the **only**
  page addressing in this system. There is no page index, no page label and no
  PDF-internal object number anywhere in a seam.
* `has_text_layer` is `true` for a page with extractable embedded text. A page with none is
  admitted only when the portal's block list holds at least one block on that page
  (`W55B-SEAL-01`, `R-116`: *OCR is always marked*, never substituted); otherwise it is refused
  at ingest with `validation_failed` (`every_page_has_extractable_text`) and never reaches
  this artifact. A page admitted that way is `has_text_layer: false` with `char_count: 0`, its
  text comes only from §4.8 marked `recognised`, and its number is in
  `document_version.textless_pages` when its pypdfium2 character count is below the frozen
  threshold (50). The field exists so a consumer can tell the two cases apart, not so it can
  degrade silently.
* `rotation_deg` ∈ {0, 90, 180, 270}. Geometry in §4.4 is expressed **after** rotation
  is applied, so a consumer never re-applies it.

### 4.3 `prepared.text_layer`

```json
{
  "artifact_role": "prepared.text_layer",
  "artifact_version": "1.0.0",
  "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
  "extractor": { "name": "<library>", "version": "<pinned version>", "options_sha256": "…" },
  "normalization": {
    "id": "nfc_v1",
    "description": "Unicode NFC. No case folding, no whitespace collapsing, no punctuation substitution and no line-ending rewriting beyond the extractor's own output."
  },
  "total_char_count": 24019,
  "pages": [
    { "page_number": 1, "char_start": 0, "char_end": 1873, "text": "…" },
    { "page_number": 2, "char_start": 1873, "char_end": 3940, "text": "…" }
  ]
}
```

Invariants a consumer may rely on, and `B2` must guarantee:

* `pages` is ordered by `page_number`, contiguous and gapless.
* `pages[0].char_start == 0`; `pages[i].char_start == pages[i-1].char_end`;
  `pages[-1].char_end == total_char_count`.
* `char_end - char_start == len(page.text)`, counted in code points.
* Concatenating every `page.text` in order reproduces the document-global sequence
  exactly.
* `extractor` fixes reproducibility: same bytes plus same extractor plus same options
  gives the same offsets. A change to any of the three is a new `artifact_version`.

The normalization identifier is a seam. `B4` compares against it and against nothing
else, so `B3` must not normalize model output before writing an anchor.

### 4.4 `geometry.block_index`

```json
{
  "artifact_role": "geometry.block_index",
  "artifact_version": "1.0.0",
  "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
  "text_layer_sha256": "…",
  "blocks": [
    {
      "block_id": "b_000001",
      "page_number": 1,
      "block_ordinal": 0,
      "bbox": { "x0": 56.7, "y0": 70.9, "x1": 538.6, "y1": 118.4 },
      "bbox_unit": "pt",
      "bbox_origin": "top_left",
      "char_start": 0,
      "char_end": 142
    }
  ]
}
```

* `block_id` matches `^b_[0-9]{6}$` and is assigned deterministically in
  `(page_number, block_ordinal)` order across the whole document, starting at
  `b_000001`. It is stable for one `(version_uid, artifact_version)` pair.
* **`block_id` is not `portal_block_id`.** `portal_block_id` (§4.9) is the portal's external
  identifier for a block of its own block list; the two never mix, and neither is an
  identity of this product.
* **`block_id` is not a contract identifier.** It is an anchor inside one artifact.
  It is never a foreign key, never crosses a version boundary and never appears in the
  identifier catalog. `finding_evidence.block_id` stores it as a nullable secondary
  anchor and nothing references it.
* `char_start`/`char_end` are document-global offsets per §4.1, and must lie inside
  the owning page's interval.
* `bbox_origin` is `top_left` with y increasing downwards, after rotation. `bbox`
  coordinates are points. Stating this once here is cheaper than four slices each
  guessing PDF's bottom-left default.
* `text_layer_sha256` binds this artifact to the exact text layer it was derived
  from. A consumer holding a different text layer fails closed.

### 4.5 `geometry.page_crops`

```json
{
  "artifact_role": "geometry.page_crops",
  "artifact_version": "1.0.0",
  "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
  "crop_policy": "none",
  "crops": []
}
```

`OD-04`, **flipped by `W55B-SEAL-01`** (`R-119`). The registry marks this a required output of
a stage that allows neither `partial` nor `skipped`. It is now a manifest with a content
schema, `contracts/analysis/v1/crop-manifest.schema.json`, under one of two policies:

* `none` -- `crops: []`. A version without a portal bundle (published before W55b), exactly
  as before: present, schema-valid and explicitly empty, echoed in the stage metrics as
  `crop_policy=none` and `crop_count=0`.
* `portal_image_blocks` -- one crop for each IMAGE block of the portal's block list whose page
  passed the page-box check. A block on a page marked `geometry_mismatch` has **no** crop, by
  design: a wrong crop is worse than none, and the page says so in §4.9.

```json
{
  "artifact_role": "geometry.page_crops",
  "artifact_version": "1.0.0",
  "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
  "crop_policy": "portal_image_blocks",
  "crops": [
    {
      "portal_block_id": "blk_4fd3e4dfbe094e4eafafda3adfb990a3",
      "page_number": 13,
      "bbox_norm": [0.763, 0.565, 0.973, 0.704],
      "render_profile": {
        "renderer": "pypdfium2 5.13.0", "scale": 2.5,
        "min_long_side_px": 800, "max_pixels": 4000000, "format": "png"
      },
      "blob_id": "blob_01M2545JSD15ETSNNV904X991H",
      "sha256": "…",
      "size_bytes": 412039,
      "width_px": 1026,
      "height_px": 800
    }
  ]
}
```

* The crop is a **clip render** of the PDF page, never the portal's `crop_url`, which is a
  capability URL and is neither fetched, stored for display nor rendered.
* The PNGs are content-addressed blobs of role `geometry.crop_image` (§4.10) and are referenced
  only from this manifest; the manifest carries a `blob_id` and a digest and never an object
  key or a URL.
* **Pixel bytes are stable within one image only** (the renderer and its dependencies are part
  of the bytes). A test asserts properties and same-environment repeatability, never a
  recorded crop; a consumer relies on the `sha256` recorded in the manifest it read.
* `block_analysis` still consumes this manifest as a required input and nothing consumes a
  crop in W55b: no model looks at one. The API reads it for `listVersionPortalBlocks`.

### 4.6 `context.document_graph`

```json
{
  "artifact_role": "context.document_graph",
  "artifact_version": "1.0.0",
  "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
  "block_index_sha256": "…",
  "sections": [
    {
      "section_id": "s_0001",
      "title": "Противопожарные требования",
      "level": 1,
      "parent_section_id": null,
      "page_number": 3,
      "block_ids": ["b_000041", "b_000042"]
    }
  ],
  "references": [
    { "from_block_id": "b_000042", "to_section_id": "s_0007", "kind": "cross_reference" }
  ],
  "neighbourhood": [
    { "block_id": "b_000042", "previous_block_id": "b_000041", "next_block_id": "b_000043" }
  ]
}
```

* `section_id` matches `^s_[0-9]{4}$` and, like `block_id`, is an intra-artifact
  anchor and not a contract identifier.
* Every `block_ids` entry and every `from_block_id` must exist in the bound block
  index. `to_section_id` must exist in `sections`.
* `kind` ∈ `cross_reference`, `continuation`, `table_caption`, `figure_caption`.
* The graph is a tree over `parent_section_id` with no cycle. `references` and
  `neighbourhood` are flat.

`B3` uses this to build the prompt neighbourhood. It is a convenience for the model,
never evidence: the grounding gate resolves against §4.3 and §4.4 only.

### 4.7 `analysis.text_observations`

```json
{
  "artifact_role": "analysis.text_observations",
  "artifact_version": "1.0.0",
  "run_id": "run_01M2545JSD15ETSNNV904X991K",
  "stage_id": "text_analysis",
  "analysis_profile_id": "ap_01M2545JSD15ETSNNV904X991Q",
  "prompt_bundle_id": "pb_01M2545JSD15ETSNNV904X991R",
  "provider_mode": "recorded",
  "pages_analysed": [1, 2, 3],
  "observations": [
    {
      "observation_ordinal": 0,
      "category": "internal_contradiction",
      "finding_text": "Класс огнестойкости указан по-разному на страницах 3 и 7.",
      "recommendation_text": "Согласовать класс огнестойкости между разделами.",
      "model_call_id": "mc_01M2545JSD15ETSNNV904X991S",
      "evidence": [
        {
          "evidence_ordinal": 0,
          "page_number": 3,
          "quote": "класс огнестойкости II",
          "char_start": 4821,
          "char_end": 4843,
          "block_id": "b_000042"
        }
      ]
    }
  ]
}
```

* This is `B3`'s output and `B4`'s **only** input. `B4` takes no model input of any
  other kind: the gate is deterministic.
* `observation_ordinal` and `evidence_ordinal` are positions within this artifact.
  Neither is an identity. `finding_uid` and `finding_observation_id` are allocated by
  `B4` at publication, not here.
* Every observation must carry at least one evidence item. An observation with no
  evidence is not "ungrounded" — it is malformed, and `text_analysis` rejects it
  before writing the artifact.
* `char_start`/`char_end` are document-global offsets per §4.1, and
  `char_end - char_start` must equal the code-point length of `quote`.
* Analysis reads `prepared.text_layer` and nothing else of the document: the portal's
  recognised text and its descriptions of images (§4.8) are shown, marked, and **never sent
  to a model** (`R-117`), so an `evidence.quote` is always a span of the PDF's own text layer.
* `pages_analysed` is what makes the `partial` mapping checkable: `partial` is
  reported only when usable observations were produced over a **strict subset** of
  pages, with a typed error. An unavailable provider is `failed` with
  `dependency_unavailable`, never `partial`.

### 4.8 `prepared.recognised_text`

```json
{
  "artifact_role": "prepared.recognised_text",
  "artifact_version": "1.0.0",
  "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
  "results_sha256": "…",
  "entries": [
    {
      "portal_block_id": "blk_41a8095edd934772829072bbb72b4ab1",
      "page_number": 1,
      "kind": "recognised_text",
      "quote_source": "recognised",
      "text": "ООО «СУ-10» …",
      "flags": ["mixed_script"]
    },
    {
      "portal_block_id": "blk_4fd3e4dfbe094e4eafafda3adfb990a3",
      "page_number": 13,
      "kind": "portal_description",
      "text": "План этажа подземной автостоянки …"
    }
  ]
}
```

`W55B-RECOGNISED-01` produces it from the bundle's `_results.md`. It is **optional**: absent for
a version without a portal bundle, and `source_preparation` succeeds without it.

* One entry per TEXT or IMAGE block the markdown holds (a STAMP block is only in the block
  list). A TEXT body is `kind: recognised_text` with `quote_source: recognised`; an IMAGE body
  is `kind: portal_description`, shown as «описание портала — в анализе не используется» and
  never an input of any analysis stage (`R-117`). For the future W56a v2 profile,
  recognised TEXT entries alone may enter `text_analysis` as marked context on
  pages in `document_version.textless_pages`; they remain non-citable (`R-134`).
* `flags` is a lowercase snake_case list of quality signals: mixed-script words, Latin/Cyrillic
  homoglyphs, CJK characters, doubled list markers and the norms degeneracy signals. Engineering
  designations (`1.A`, `B25`, `A500C`, `REI 150`) are exempt by a pinned pattern.
* `text` is markdown, kept as text. Nothing renders it as HTML.
* Never merged into `prepared.text_layer` (§4.1), and no entry has offsets.

### 4.9 `geometry.portal_blocks`

```json
{
  "artifact_role": "geometry.portal_blocks",
  "artifact_version": "1.0.0",
  "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
  "blocks_sha256": "…",
  "pages": [
    { "page_number": 13, "width_px": 2482, "height_px": 3510, "rotation_deg": 0, "geometry": "ok" }
  ],
  "blocks": [
    {
      "portal_block_id": "blk_4fd3e4dfbe094e4eafafda3adfb990a3",
      "page_number": 13,
      "page_label": 13,
      "ordinal": 18,
      "block_type": "image",
      "status": "recognized",
      "bbox_norm": [0.763, 0.565, 0.973, 0.704]
    }
  ]
}
```

`W55B-GEOMETRY-01` normalises the bundle's `_blocks.json` into it. **Optional**, for the reason
§4.8 gives.

* `page_number = page_index + 1`: the true 1-based PDF page and the only page addressing in this
  system. `page_label` is the portal's own integer label, kept for display.
* `portal_block_id` is the bundle's `blk_` and 32 hexadecimal digits: an **external**
  identifier (`contracts/domain/v1/identifiers.json`, `external_identifiers`), never generated
  here and addressed only together with a `version_uid`. `ordinal` is the portal's, not unique,
  and `null` for a stamp. Blocks are ordered by page, ordinal (null last) and id.
* **The page-box check.** The portal's `width_px` / `height_px` aspect is compared with the PDF
  CropBox after `/Rotate`, within the frozen tolerance (0.5 % per side; the real pages differ by
  about 0.06 %). A mismatch marks the page `geometry: geometry_mismatch`; no crop is cut for it
  and the stage still reports success -- the mismatch is visible here and in «Блоки», never a
  silent fallback.
* `rotation_deg` ∈ {0, 90, 180, 270}; `bbox_norm` is in the page's normalised top-left space
  (`coordinate_space: normalized_page_top_left`), each coordinate in [0, 1].
* The wire shape `PortalBlock` joins this artifact with §4.8 and §4.5 on `portal_block_id`.

### 4.10 `geometry.crop_image`

```json
{
  "role": "geometry.crop_image",
  "blob_id": "blob_01M2545JSD15ETSNNV904X991H",
  "sha256": "…",
  "size_bytes": 412039,
  "media_type": "image/png"
}
```

Not a JSON document: a PNG blob, shown here as the `ArtifactRef` that names it. **Zero or more
per run**, one for each crop in §4.5, content-addressed (an equal crop is the same blob), and
referenced only from the manifest. It carries no `artifact_role` root field because there is no
root; the registry declares it so that the blob role is a known one.

### 4.11 `findings.merged` (sealed for W56a)

The future deterministic merge stage emits a versioned JSON artifact: each
group names every contributing grounded observation ordinal, its canonical
ordinal, and the merge-rule version. Two observations link only in the same
category, by overlapping evidence spans on one page or equal NFC/case-folded,
whitespace-collapsed quotes of at least 20 characters on one page. Groups are
connected components; the canonical member has the earliest page/span, then
the lowest ordinal. No member or raw evidence is deleted. The SEAL declares
this role; `W56A-MERGE-01` implements it later.

```json
{
  "artifact_role": "findings.merged",
  "artifact_version": "1.0.0",
  "groups": [
    {
      "observation_ordinals": [1, 2],
      "canonical_ordinal": 1,
      "merge_rule_version": "1.0.0"
    }
  ]
}
```

## 5. Finding, observation, evidence and decision shapes

### 5.1 The grounding rule

`B4` publishes an observation as a finding only when **every** evidence item resolves:

1. the declared `(char_start, char_end)` interval lies inside the declared page's
   interval in `prepared.text_layer`;
2. the document-global sequence sliced at that interval **equals the quote exactly**,
   after the one declared normalization of §4.1 and nothing else;
3. when `block_id` is present, that interval lies inside the block's own span in
   `geometry.block_index`.

An item failing any of the three is rejected from the finding list and retained only
as a diagnostic: a `finding_observation` row with `grounded = false`, a
non-null `ungrounded_reason`, and **no** `finding_uid`. It is not counted as a
finding anywhere, and it appears in no finding query and in no CSV row. The database
enforces the pairing, so this is not something a query has to remember.

`ungrounded_reason` is one of: `quotation_absent`, `quotation_on_different_page`,
`span_outside_page`, `span_outside_block`, `span_length_mismatch`,
`quote_in_recognised_text`. The last means the candidate quote exists only
in marked recognised context, never in the PDF text layer; it cannot ground
a published finding.

### 5.2 Identity allocation

* `finding_uid` — a fresh one per published observation in v1, or per merged
  group in v2, per run. PC-01 does **no**
  cross-run matching and **no** decision carryover. Two runs over the same document
  produce two disjoint sets of `finding_uid`.
* `finding_observation_id` — immutable, bound to exactly one `run_id`. A rerun
  creates new observations and never rewrites or removes earlier ones. The database
  refuses UPDATE and DELETE.
* `finding.canonical_observation_id` — nullable until v2 publication wires the
  merge stage. Migration 0022 backfills the one legacy observation per finding;
  its composite foreign key requires the chosen observation to belong to the
  same finding. A decision on a non-canonical member is refused.

### 5.3 The decision ledger

Append-only. Every event is a new `decision_id`. Nothing is ever updated.

| Field | Rule |
|---|---|
| `decision_id` | fresh per event |
| `finding_uid` | the finding being judged |
| `finding_observation_id` | the observation the expert actually reviewed |
| `event_type` | `accept`, `reject`, `comment`; `revoke` declared, no PC-01 producer |
| `verdict` | `accepted` for accept, `rejected` for reject, `pending` for revoke, `null` for comment |
| `severity` | optional v2 decided value from the five-level enum, only on `accept`; the database refuses it on every other event |
| `comment` | required for `comment`, optional on any other type |
| `author_label` | **Since wave 42 (`R-37`): the reviewer's display name**, derived server-side from the authenticated credential and never from a request body; an account that has chosen no name falls back to its login, and the fallback is queryable rather than silent. Authorizes nothing. `OD-12`'s single configured label is gone — `P04` cannot measure whose judgement was whose when every judgement carries one name. **The sealed contract now says this too** (`D-86`, closed in wave 42), so this row is a restatement and not a second authority |
| `command_id` | at most one event per command record, enforced by a unique index |
| `recorded_at` | `clock_timestamp()`, so events inside one transaction are distinguishable |

Client-visible ordering is `(recorded_at, decision_id)`. The server's `sequence_no` is
never returned and never embedded in a cursor: the contract lists a database sequence
value exposed to a client among the non-identities.

### 5.4 The current-verdict projection

The view `finding_current_verdict` is the single definition. `B4`, `B5` and `B6` read
it; none recomputes it.

| Column | Rule |
|---|---|
| `current_verdict` | the `verdict` of the most recent verdict-bearing event; `pending` when there is none |
| `decided_severity` | severity of the latest verdict-bearing event only when that event is `accept`; null after reject or revoke |
| `latest_verdict_decision_id` | that event's identity, or null |
| `latest_comment` | the `comment` of the most recent event carrying one, whatever its `event_type` |
| `latest_decision_id` | the most recent event of **any** type |
| `decision_recorded_at` | that event's `recorded_at` — so appending a comment moves it |
| `decision_event_count` | events for this finding |

PD-01: a revocation moves the projection to `pending` and never restores an earlier
superseded verdict. A verdict after a revocation exists only where an authorized
expert appended a new event.

`needs_manual_review` is in the closed verdict enum and has **no PC-01 producer**.

## 6. The CSV column contract — `OD-11`

Nineteen columns, in this order. The first seventeen retain the frozen OD-11
order; W56a appends the two severity columns under §A3.2. `B5` produces this
list and `B8` downloads it.

| # | Column | Source |
|---|---|---|
| 1 | `project_uid` | `finding.project_uid` |
| 2 | `document_uid` | `document_version.document_uid` |
| 3 | `version_uid` | `finding.version_uid` |
| 4 | `run_id` | `finding.allocated_by_run_id` |
| 5 | `run_state` | `audit_run.state` — `published` or `partial`, carried explicitly |
| 6 | `provider_mode` | `audit_run.provider_mode` |
| 7 | `finding_uid` | `finding.finding_uid` |
| 8 | `finding_observation_id` | `finding_observation.finding_observation_id` |
| 9 | `category` | `finding.category` |
| 10 | `finding_text` | `finding_observation.finding_text` |
| 11 | `recommendation_text` | `finding_observation.recommendation_text` |
| 12 | `evidence_page` | `finding_evidence.page_number` |
| 13 | `evidence_quote` | `finding_evidence.quote` |
| 14 | `current_verdict` | `finding_current_verdict.current_verdict` |
| 15 | `latest_comment` | `finding_current_verdict.latest_comment` |
| 16 | `latest_decision_id` | `finding_current_verdict.latest_decision_id` |
| 17 | `decision_recorded_at` | `finding_current_verdict.decision_recorded_at` |
| 18 | `severity` | `finding_current_verdict.decided_severity` — latest accepted expert decision, otherwise empty |
| 19 | `severity_proposed` | canonical `finding_observation.proposed_severity` — model proposal, not an expert decision |

**Bytes.** UTF-8 with a byte-order mark; comma delimiter; CRLF line ending; RFC 4180
quoting. The BOM is there because the intended reader opens the file in Excel, which
otherwise mis-decodes Cyrillic.

**Formula injection.** A text cell is written with one leading apostrophe when a spreadsheet could read it as a
formula: when the first character that is not a space, a no-break space, a byte-order mark, a zero-width character,
a tab, a carriage return or a line feed is `=`, `+`, `-` or `@` (or its fullwidth form), or when the cell itself
starts with a tab, a carriage return or a line feed. Every other text is written as it is, an apostrophe is never
doubled, and a number or a date is never touched (`SMALL-HARDENING-02`, `R-146ax`, `D-246`, `D-253`;
`src/auditmanager/shared/spreadsheet/formula_text.py`).

**Granularity.** One row per evidence item. A finding with three quotations produces
three rows sharing columns 1–11 and 14–19. When the finding has a canonical
observation, only its evidence items are exported; the legacy null-canonical
path retains the pre-merge single-observation behavior.

**Sort key.** `(finding_uid, finding_observation_id, evidence_ordinal)`, ascending, on
the opaque identifiers. `evidence_ordinal` is not itself a column; it orders the rows
of one observation. Two exports of an unchanged run are byte-identical.

**Empty cells.** A null projection column is the empty string, never the literal
`null` and never `NULL`.

**Export policy.** The discriminator is the frozen `terminal_semantics.publishes_result`
flag, not a hand-written state list. A run whose terminal declares
`publishes_result: true` — `published` or `partial` — **is** exported, with the
degraded state visible in column 5. Everything else is refused with the typed
`state_transition_not_allowed`: a non-terminal run, and the terminal `failed`.
`cancelled` is likewise not exportable and is unreachable in PC-01.

**PC-01 never emits `partial_result_not_publishable`.** The contract raises it for "an
operation that requires a complete run"; under `OD-11` this export is explicitly not
one, and PC-01 defines no other.

**Nothing is created.** No export row, no `export_id`, no `exported_at`, no polling. A
repeat returns byte-identical bytes.

## 7. API seam — `contracts/api/v1/openapi.json`

303 operations, sealed. `A5` generates the typed client from this document; `B6`
implements the routers against it; `B7` and `B8` consume the client and never call
`fetch` directly.

Twelve until the reseal of 2026-09-18 under owner ruling `R-5`, which added the three
listings below and made published work reachable after a page reload (`DEBT_REGISTER.md`
D-16). Sixteen after `W34-CONTRACT` added `issueToken` on 2026-09-22, seventeen after
`W38-KB` added `listDecisions` under `R-24` the same day, eighteen after `W39-REVOKE`
added `changePassword` under `R-26` on 2026-09-23, and nineteen after `W45-BLOCKS` added
`getVersionBlocks` under `R-29` on 2026-09-25, twenty after `W46-SEAL` added
`getDashboardSummary` under `R-44` on 2026-09-25, and `W49-SEAL-01` then added
the account, registration and account-management operations under `R-55` ... `R-61` on
2026-10-06. `W52-SEAL-01` added the three release operations on 2026-10-08,
`W53-SEAL-01` the six execution operations on 2026-10-09, and `W54-SEAL-01` the worker
registry's `listWorkers` and `setWorkerIntake` on 2026-10-12 (stubs answering
`dependency_unavailable` until `W54-WORKER-01`). `W55A-SEAL-01` added the seven norms
operations on 2026-10-12 under `R-112` and `R-113` (stubs answering `dependency_unavailable`
until `W55A-SEARCH-01`). `W55B-SEAL-01` added the two portal-block reads on 2026-10-13 under
`R-116` and `R-119` (stubs answering `dependency_unavailable` until `W55B-GEOMETRY-01`).
`W57A-SEAL-01B` added the refusing `getRunNormVerification`. `W59-SECTION-SEAL-01` added
`classifyDocumentVersion` and `getVersionSectionReview` on 2026-10-20: a version's
expert-confirmed project stage and section, persisted by `0024_version_classification`, which
`startRun` and `reauditRun` now route the analysis profile from. `CLASSIFICATION-CORRECTION-01`
added `correctVersionClassification`: an expert's append-only correction (a numbered revision
with a reason, `0028_classification_corrections`); the current classification is the latest
revision and every read of it goes through `version_classification_current`. `W59-VERSION-COMPARE-01`
added `compareDocumentVersions` on 2026-10-20: a read-only comparison of two versions of one
set with the same confirmed section and either the same stage (`mode=version`) or a `P`
source and an `R` target (`mode=stage`, the W62 П/Р slice), whose sheet pairs and finding
matches are proposals and whose refusals are answers with a closed reason, never a
relabelled pair; a path naming no version of the document is `404`.
`W59-ANALYSIS-SETTINGS-01` added `listAnalysisProfiles` on 2026-10-20: the section-keyed
text-profile registry run start routes through, read-only, as fifteen sections in the
project-structure order, each with its profile (identities, version, status, hashes, legacy
source) or `null`.
`W59-VERSION-UPLOAD-01` added `uploadDocumentVersion` on 2026-10-20: one portal bundle, under `uploadDocument`'s
envelope and custody, published as the next immutable version of an existing document, which
becomes its current version and inherits no title, section or classification; a document of
another project is `404`.
`W59-DECISION-CARRYOVER-01` added `carryOverDecision` on 2026-10-20: an expert confirms
carrying one source decision to the target finding the recomputed comparison proposes as
`unchanged`, and the decision ledger appends one `accept` or `reject` event on the target,
authored by that expert, whose comment records the carried-from finding, decision and
versions; the comparison's `findings.carryover_candidates` lists what could be carried, and
nothing is carried without the confirmation.
`COMPARE-PERSISTED-SUMMARY-01` added `approveSheetPairing`, `withdrawSheetPairing` and `generateComparisonSummary` on 2026-10-27: an
expert's approval of one sheet pair that `compareDocumentVersions` proposed is stored as a row of an
append-only history (`comparison_sheet_link`, migration `0035_comparison_records`), and its withdrawal is
a new row; a sheet is a version, a page coordinate and the SHA-256 of the page text, never a display
number; each write has one audit event in its transaction and is refused to an account without `expert`.
`compareDocumentVersions` gains `approved_pairs`: the active approvals and, for approved pairs only, their
deterministic differences bound to the version bytes by a seal. `generateComparisonSummary` is the only
operation that calls a model about a comparison (an expert asks once; the sealed approved pairs' changed
lines are the whole input; the reply is checked against them; the summary is stored append-only beside
the differences, which it never alters, with a fixed label saying no human reviewed it); only a recorded
implementation exists, and a process in another mode answers `dependency_unavailable`.
`ANALYSIS-PRESETS-01` added `listAnalysisPresets` (any one role), `createAnalysisPreset`,
`reviseAnalysisPreset` and `archiveAnalysisPreset` (`admin`, keyed) on 2026-10-27: a named preset of
how a run starts is a name and the one setting a run start can take, the executor connection, stored as
rows of an append-only history (`analysis_preset_revision`, migration `0037_analysis_presets`); a
revision and an archive are new rows, and each write has one audit event in its transaction.
`startRun` gains the optional `preset_id` (exclusive with `executor_connection_id`: the preset's
connection is applied as if the caller had named it) and `RunStatus` the read-only `preset`.
`CMP-SEAL-C0` (contract `1.9.0`) sealed these comparison-module endpoints as stubs on 2026-10-27 -- `createComparisonUpload`, `listComparisonUploads`, `getComparisonUpload`, `getComparisonUploadProposal`, `uploadComparisonUploadPart`, `completeComparisonUploadFile`, `confirmComparisonUploadSet`, `excludeComparisonUploadSet`, `retryComparisonUploadSet`, `pauseComparisonUpload`, `resumeComparisonUpload`, `cancelComparisonUpload`, `listComparisonVersionOrders`, `appendComparisonVersionOrder`, `listVersionPageProfiles`, `getVersionPageProfile`, `streamVersionPagePreview`, `streamVersionPageThumbnail` and `streamVersionPageTile`. Reads are any one role; every write is an expert's act and keyed. Each answers `503 dependency_unavailable` until its lane (`CMP-INGEST-01`, `CMP-INGEST-02`, `CMP-PROFILE-01`) wires it (`ADR-0025` decision 25). A page is addressed by the identity of its profile (`cpr_`) and never by its number. `DocumentVersion` gains `upload_kind`, `ProductVersion` gains `comparison_modules` (the module set, default `none`), `RunnerImage` no longer requires `portal_block_id` and may carry a `crop_id`, `ClaimedExecutorTask.images` may hold eight images and the claim request may declare `max_images`. Migration `0038_comparison_foundation` adds nine tables.
`CMP-SEAL-C1` (contract `1.10.0`) sealed the version comparison core as stubs on 2026-10-28 -- the effective matrix of a document set (`getComparisonMatrix`, `prepareComparisonMatrix`, `listComparisonMatrixEdits`, `applyComparisonMatrixEdits`, `undoComparisonMatrixEdit`, `listComparisonAiLinks`), the series of adjacent transitions and their sheet pairs (`startComparisonSeries`, `listComparisonSeries`, `getComparisonSeries`, `pauseComparisonSeries`, `resumeComparisonSeries`, `cancelComparisonSeries`, `finishComparisonSeries`, `listComparisonSheetPairs`, `getComparisonSheetPair`, `streamComparisonPairTile`) and the read models `getComparisonOverview` and `getComparisonQueueSummary`. Reads are any one role; every write is an expert's act and keyed. Each answers `503 dependency_unavailable` until its lane (`CMP-MATRIX-01`, `CMP-SERIES-01`, `CMP-VIEWER-01`, `CMP-VC-OVERVIEW-01`) wires it. While the module «Сравнение версий» is on, `approveSheetPairing`, `withdrawSheetPairing` and `generateComparisonSummary` answer `503 dependency_unavailable`; migration `0039_comparison_core` adds seven tables and turns the active `0035` approvals into manual matrix edits (`ADR-0025` decision 13).
`CMP-SEAL-C2` (contract `1.11.0`) sealed the version comparison AI, specifications, launch queue and reports as stubs on 2026-10-29 -- the AI check of the doubtful pairs of a document set (`estimateComparisonAiPairCheck`, `startComparisonAiPairCheck`, `getComparisonAiPairCheck`, `pauseComparisonAiPairCheck`, `resumeComparisonAiPairCheck`, `cancelComparisonAiPairCheck`, `listComparisonAiPairHints`), the AI description of changes (per series and per sheet pair, with the «Проверить» list and the MD of one sheet), specifications (the deterministic positions of a page and of a sheet pair, and the AI comparison of whole specifications per transition), the launch queue and the installation's AI queue, and the MD summary and the PDF reports -- fifty endpoints of the API in all. Reads are any one role; every write is an expert's act and keyed. Each answers `503 dependency_unavailable` until its lane (`CMP-VC-AIPAIR-01`, `CMP-VC-AISHEET-01`, `CMP-VC-SPEC-01`, `CMP-VC-QUEUE-01`, `CMP-VC-REPORT-01`) wires it, and `comparison_modules` first while the module «Сравнение версий» is off. Every AI start carries the estimate it consents to; migration `0040_comparison_ai_reports` adds twelve tables (`ADR-0025` decisions 17, 19 and 20).
`CMP-SEAL-C3` (contract `1.12.0`) seals thirty-two stage comparison operations as typed stubs: separate resumable PDF/ZIP intake and candidate confirmation, expert-confirmed П/Р pairs and assemblies, sheet passports and append-only full map revisions, immutable raw text evidence and pinned seven-step chain runs. Reads are any one role; writes are expert acts with required idempotency keys. While `comparison_modules` excludes stages, each refuses with `comparison_modules`; otherwise it refuses its lane dependency until the C3 lanes wire it. Migration `0041_comparison_stage_core` adds fifteen project-reachable tables. D-262 still blocks first ZIP-set use until the caller enforces raw-upload, admission, disk and per-PDF validation bounds.
`CMP-SEAL-C4` (contract `1.13.0`) sealed the stage comparison's AI review, link repair, full chain and expert journal on 2026-10-30 (`docs/program/CMP-SEAL-C4.md`): the assembly reload `getStageAssembly`; the chain's estimate, resume and batches (`estimateStageChainRun`, `resumeStageChainRun`, `startStageChainBatch`, `getStageChainBatch`, `pauseStageChainBatch`, `resumeStageChainBatch`, `cancelStageChainBatch`); the AI answers `listStageAiReviews`, `listStageClassifications` and `getStageSynthesis`, and the graphic evidence `listStageGraphicEvidence`; the sheet-link repairs `listStageLinkRepairs` and `undoStageLinkRepair`; the expert's cards and verdicts (`listStageChangeCards`, `getStageChangeCard`, `applyStageCardVerdicts`, `listStageCardVerdicts`); the change journal and its three exports (`getStageChangeJournal`, `streamStageChangeJournalXlsx`, `streamStageChangeJournalPdf`, `streamStageChangeJournalHtml`); and the page profile's stage text `getStageProfileText`. `createStageReviewCard` followed under the same version: an expert asks that evidence the cards hide be reviewed, which adds a `REVIEW` card and leaves the raw evidence unchanged. Reads are any one of `expert` and `admin`; every write is an expert's act and keyed. Migration `0042_comparison_stage_review` adds twelve project-reachable tables, and `0043_stage_ai_generations` preserves the immutable AI generations for explicit recovery. AI output never edits a raw difference.
`BETA-COST-PREFLIGHT-1030` (contract `1.13.0`) added `estimateRunCost` and `estimateArV3GroupCost`: read-only cost preflights (`expert`) that write nothing and take no key. A changed source, profile, preset, route or model makes an earlier estimate digest stale; a start or a re-audit carries the consent (`cost_consent`) bound to one digest, and `startRun` gains `relaxed_limits`, the raised output limit chosen per Run.
`HOTFIX-PRESENTATION-INT-1030` (contract `1.14.0`) added `getExtendedRunReview` (the source-bound preliminary extended analysis of a Run and its explicit coverage, `expert` or `admin`), `importComparisonZip` (`expert`, keyed: a reviewed, bounded ZIP of PDFs becomes immutable upload members, and an unsafe or non-PDF member is refused before anything is created) and `streamComparisonTechnicalReport` (the saved evidence of a comparison series as a workbook or an HTML bundle, no model call).
`W57B-NORMS-CATALOGUE-XLSX-01` added `listNormDocuments` and `exportRunXlsx` on 2026-10-20:
the current norms snapshot's documents as a catalogue with display names derived from the
stored file names (any one role), and the run's W57b Excel workbook with `exportRunCsv`'s
states and role.
`W61-DISPATCHER-01` added the four «Диспетчер» operations on 2026-10-20 under roadmap Q-2:
`createAssignment` (`admin`), `listAssignments`, `getAssignment` and `transitionAssignment`,
over `0025_work_assignments`' immutable assignment and its append-only event history; the
status is the latest event's projection and the `work_assignment` machine is decided by
`auditmanager.dispatch`.
`W60-PRICE-LIST-01` added six `optimisation` operations on 2026-10-20: `uploadPriceList` stores
a project's CSV or XLSX price list (at most 10 MiB, `expert`, keyed) as an immutable revision
bound to its file, with parsed positions and a deterministic parse report in which every data
row is accepted or skipped with a reason; `listPriceListRevisions` and `listPriceListPositions`
read them; `getEffectiveVendorLists` answers the fifteen sections' vendor lists for a project;
`setGlobalVendorList` (`admin`) and `setProjectVendorList` (`expert`, `list` or `inherit`)
append versioned revisions, refusing a stale `expected_vendor_list_id`
(`conflict_reason: vendor_list_changed`). No operation answers a total, a proposal or a price a
price list does not state; migration `0026_price_lists` stores them.
`W60-OPT-MATCH-01` added `getSpecificationPrices` on 2026-10-20: «Спецификация и цены», the
specification rows of a document set's current `AR`-classified version, read deterministically
from its newest published run's saved text and matched to the project's current price list;
a price and an amount only on a row matched to one position in the same unit with a numeric
quantity, totals per currency over those rows only; a precondition that does not hold is one
`state`, and a set outside the project is `404`. Read-only, any one role.
`W60-OPT-PROPOSALS-01` added six more `optimisation` operations on 2026-10-20, the «Предложения»
of «Оптимизация проекта»: `startOptimisationPass` (`expert`, keyed) pins a document set's
current AR version, its newest published run, the current price-list revision and the effective
AR vendor list and stores the deterministic `cheaper_analog` proposals, refusing an unmet
precondition as `conflict` with its `conflict_reason` and writing nothing; `listOptimisationPasses`,
`listOptimisationProposals` and `listProposalDecisions` read them (any one role) with counts by
decision; `decideOptimisationProposal` (`expert`, keyed) appends an accept, reject or revise
decision and never changes an earlier one; `exportOptimisationProposalsCsv` is the
formula-escaped CSV of one pass. A proposal is a separate entity beside findings: no operation
here reads or changes a finding, and a saving is stated only where a price-list position and a
numeric quantity state it. Migration `0027_optimisation_proposals` stores them.
`W63-SECTION-FORM7-01` added `getSectionSpecification` on 2026-10-20: «Оптимизация разделов»,
the Form-7 rows of every project whose document set's current version an expert confirmed in
a section, each row priced from its own project's current price list. The section code is a
filter, not an identity: every row names its project, set, version, page, sheet and line span,
rows are never merged across projects, totals exist per project and currency only and there
is no section total; a current version nobody classified is listed as excluded, one confirmed
in another section never appears; a bound is a `200` with `state: section_too_large`, a
section code outside the fifteen and an unknown `project_uid` filter are `404`. Read-only,
any one role.

`NORM-REFS-RUN-01` added `getRunNormReferences` on 2026-10-20: «Нормативные ссылки» on the run
page, the normative documents the run's saved text cites, each resolved against the norms
snapshot the run pinned as `in_corpus`, `newer_edition`, `older_edition_only`, `not_in_corpus`
or `not_recognised`, with the pages it occurs on and the corpus document it points at. Computed
per request by the W57b resolver; no finding, no severity, no model. A run that pinned no
snapshot, has no saved text layer or cites more than one answer carries is a `200` with a
`state`, never an empty list; the corpus documents whose designation the parser cannot read
are listed; an unknown run is `404`. Read-only, any one role.

`EXEC-SEAL-01` added the executor connections on 2026-10-22 under `R-143` and `R-144`, namely
the operations `listExecutorConnections`, `createExecutorConnection`, `getExecutorConnection`,
`reviseExecutorConnection`, `archiveExecutorConnection`, `setExecutorSecret`,
`generateExecutorSshKey`, `requestExecutorProbe`, `listExecutorRoutes` and `setExecutorRoute`
over migration `0030_executor_connections`. A connection is `http_api`, `ssh_command` or
`pull`; a revision is its immutable non-secret settings; a secret is write-only and is sealed
by the `api` to the stand's public key, bound to the destination it was entered for, and opened
only by the worker. Every list and read is for any one role and carries no secret by schema;
every write is an administrator's. `CostBasis` gains `unmetered`. No error code is added.

`EXEC-PULL-01` added the pull channel on 2026-10-22 under `R-143` and `R-144`, over migration
`0031_executor_pull_channel`: an administrator issues a runner token for a `pull` connection
(`issueRunnerToken`: shown once, stored only as a one-way hash) and revokes it
(`revokeRunnerToken`), and a runner (a Claude Code session behind the stdio bridge, or an
unattended agent) calls `claimExecutorTask` (a long poll of at most 25 seconds), then
`extendExecutorTaskClaim`, `submitExecutorTaskAnswer` and `failExecutorTask`. A runner token is a
principal of its own: it reaches the runner operations and no others, and every other operation
refuses it as `authentication_required`. `EXEC-IMAGE-DELIVERY-01` adds
`getExecutorTaskImage`, a PNG read bound to the token's current claim. The wire is
`tools/executor-runner/RUNNER_API.md`.
`getExecutorConnection` carries a `pull` connection's token metadata and open task count. No error
code is added.

`EXEC2-SEAL-1` (contract `1.15.0`, `ADR-0026`, rulings `R-149a` to `R-149f`, migration `0046_executor_capacity_enroll`)
sealed the capacity of a connection and the universal agent: `issueExecutorEnrollment` (`admin`, keyed) shows a
single-use enrollment grant once, with the install command that carries the package version and its sha256;
`redeemExecutorEnrollment` exchanges the grant for a runner token and `reportRunnerHealth` stores the agent's
version, clients and sanitised authentication state on that token; `downloadAgentPackage` serves the agent package
by its version; `createExecutorAgentInstall`, `getExecutorAgentInstall` and `confirmExecutorAgentInstallHostKey`
are the API side of an install over SSH (the host-key fingerprint is confirmed by value, never trusted on first
use); and `setExecutorIntegrationAuthorisation` sets the administrator's mark that the clients behind a `pull`
connection are authorised for this integration. `redeemExecutorEnrollment` authenticates with the enrollment secret
(it is the one `ENROLLMENT_OPERATIONS` entry) and `reportRunnerHealth` with the runner token (it joins
`RUNNER_OPERATIONS`); neither takes an account or a role. `downloadAgentPackage`
is the fourth operation the sealed contract declares with `security: []`: the package is public code with no
secret, and its integrity is the sha256 the install command carries (decision 6); it is addressed by version,
a path parameter that is not an identity because a version is the only thing that tells two builds of that public
code apart. The catalogue gains no error code.

`EXEC2-SEAL-2` (contract `1.16.0`, `ADR-0026` decisions 10 to 17, migrations `0047_executor_groups_rules` and
`0048_dispatch_time_binding`) sealed executor groups, routing rules, the routing mode and dispatch-time binding:
`listExecutorGroups`, `createExecutorGroup`, `getExecutorGroup`, `reviseExecutorGroup`, `archiveExecutorGroup`
and `getExecutorGroupCapacity` (a group is a set of interchangeable executors of one model; a revision is
immutable and snapshots each member's connection revision); `listExecutorRoutingRules` and `setExecutorRoutingRule`
(a rule points one work kind at a group revision and is append-only; the work kind is a closed vocabulary and the
path key of the rule, not an identity); `previewExecutorRouting` and `setExecutorRoutingMode` (the cut-over from the
legacy routes to rules, bound to the `preview_digest` that was shown, and its rollback). Reads are any one of
`expert` and `admin`, except the preview, which is `admin`'s; every write is an administrator's and keyed.
`startRun` and `estimateRunCost` gain the optional `executor_group_id`, exclusive with `executor_connection_id` and
`preset_id`, and the status of a Run and of a comparison AI job gains `binding_state`, `planned`, `binding`,
`wait_reason` and `waiting_since`: with a group the connection is chosen at dispatch. The routing mode stays
`legacy` until `setExecutorRoutingMode` moves it. The catalogue gains no error code.

`UI-PARITY-P0A` (contract `1.17.0`, no migration) added the read-only filters and fields the dashboard and the knowledge base
need for the project chosen in the header, and no operation: `getDashboardSummary` takes an optional `project_uid` query
parameter (every panel is then that project's by the definitions it already has; an unknown project is `not_found`, a
malformed one `validation_failed`, and the operation stays any one role), and `listDecisions` takes the same optional
`project_uid` (a filter on the finding, not a parent: no `not_found`). `DecisionRecord` gains `document_uid`, `version_uid`,
`project_name`, `document_name` (joined at read time, stored nowhere) and the optional confirmed `section` of the finding's
version, and `DecisionRecordPage` gains `total`, the count of entries matching the filters. Neither operation is keyed, and
the catalogue gains no error code.

`UI-PARITY-QUEUE-A` (contract `1.18.0`, no migration) made the execution queue readable and added no operation:
`ExecutionQueueItem` gains `project_uid`, `project_name`, `document_uid`, `document_name`, `version_uid` and `version_ordinal`
(always present, joined at read time: a job belongs to exactly one run, a run to one version of one document of one project) and
the optional `started_at` (creation of the first attempt), `finished_at` (the job's terminal time), `error_code` (the run's
`terminal_reason`) and `interrupted_reason`, each omitted rather than sent as `null` when the job has none; `binding_state` and
`wait_reason` are omitted for an ordinary job as well. `listExecutionQueue` takes the optional `state` filter and the half-open
period `created_from` / `created_to` over `created_at`; the order is unchanged and a cursor is valid only under the filters it
was issued under (`validation_failed`, `constraint: scope`). The operation stays any one role, is not keyed, and the catalogue
gains no error code.

`UI-PARITY-DOC-AUDIT` (contract `1.34.0`, no migration, no new operation) gives `listDocuments` the audit state of each
document (`UI-A-46`): the optional `DocumentVersion.audit` (`DocumentAudit`), read for the page in one statement through
`DocumentAuditReadModel.audits` by the rules the counters use, and on this operation only. The optional `audit_state`
filter (`UI-A-38`, «не запускались» is `not_run`) and the `order` parameter (`published` or `audit`, `UI-A-49`) are applied
by the adapter to the whole narrowed listing before the router cuts a page, so the ordering is the server's and holds
across pages and the cursor is the one of the narrowed, ordered listing.

`UI-PARITY-OPT-DECISIONS` (contract `1.35.0`, migration `0056_optimisation_decisions`) brings two decisions of the original's
optimisation screen. `ProposalVerdict` gains `revoke` (`UI-B-12`, «Снять решение»): `decideOptimisationProposal` appends it
as an ordinary keyed event that takes the proposal back to `pending` (the counts and `current_verdict` read a latest
`revoke` as `pending`; `current_decision` still names it); it is refused as `conflict` / `no_decision_to_revoke` when no decision
stands, and the migration widens the verdict CHECK, its downgrade refusing while a `revoke` exists. `listAcceptedOptimisationProposals`
(`UI-B-27`, «Принято») lists the proposals whose decision in force is an acceptance, across every pass, by optional
`project_uid` and `section_code`; a product read, cursor and `total`. `exportOptimisationProposalsXlsx` and the keyed
`importOptimisationProposalDecisions` (`UI-B-15`, «Загрузить решения») are the pass's proposals as a workbook whose first
column is the proposal's identity and the decisions loaded back from it by that identity: every changed row is an ordinary
keyed decision event authored by the caller (`revoke` for «не решено» over a decision in force), and the report names every
row that carries an ID or a decision.

`AR-V3-OPT-IN` (contract `1.38.0`, no migration, no new operation) makes AR v3 an **opt-in** analysis beside the standard one
(`docs/program/AR-V3-OPT-IN-01.md`; owner answers Q1 to Q7 of 2026-11-07). The standard (imported) analysis stays the default
and `startRun` / `reauditRun` gain no path to v3; v3 remains its own operation, `startArV3BetaGroup`. Two layers, both off by
default: the pack (`AR_V3_BETA_PACK_MANIFEST`) is the capability to execute, read and review; `AR_V3_BETA_START_ALLOWED=1`,
read by the `api` service only, is the permission to start. While a pack is installed and the permission is off,
`startArV3BetaGroup` and `estimateArV3GroupCost` answer `409 conflict` / `ar_v3_start_not_enabled` and write nothing; with no
pack they answer the `dependency_unavailable` they always did; a repeat of an accepted key replays whatever the permission now
is, and runs already accepted finish because the worker does not read the variable. `ArV3BetaPackStatus.start_allowed` (present
exactly when installed) tells a screen which. `RunStatus.analysis_kind` (`standard` | `ar_v3_beta`, derived from the pinned
profile and bundle pair, `runs/analysis_kind.py`) is sent on every run, with `ar_v3_group_id` and `ar_v3_scope_id` on a member;
a member also records the account that started it (`R-151v`). **The result of a version is its newest published or partial run
of the standard analysis** (`Q3`): the counters and `listDocuments`' audit state (`STANDARD_RUN_SQL`), the schedule's facts,
the default run of a comparison and the text the optimisation reads. A v3 run named in a comparison is the refusal
`analysis_not_comparable` (the findings of the two analyses are not the same kind of object; carry-over recomputes the
comparison and inherits it); `reauditRun` (and `estimateRunCost` with `reaudit_of_run_id`) of a member is `409 conflict` /
`ar_v3_member_not_repeatable` before the key is claimed, because the repeat would route by the section and silently become the
other analysis.

`UI-PARITY-OPT-CARRYOVER` (contract `1.37.0`, migration `0057_decision_carryover`) carries the decisions of an earlier version's
optimisation pass over to the pass of a later version (`UI-B-14`, «Перенести решения из V#»). `carryOverProposalDecisions` is
a keyed expert write: it matches the source pass's decisions in force to the target pass's proposals by **content** alone (the
type, the specification row's text, the unit and currency, both positions by code, mark, name and supplier, both unit prices;
never a display number, a name alone or a place in the drawing), appends each unambiguous match as an ordinary decision event
authored by the confirming expert, only into a proposal that has no event at all, and reports every source decision as
`carried`, `target_decided`, `ambiguous` or `unmatched`. The new nullable `optimisation_proposal_decision.carried_from_decision_id`
(foreign key to the table itself, `opd_` shape, not itself, never a `revoke`) is the provenance; it reaches the wire as
`ProposalDecision.carried_from` (the source decision, pass, version and the version's display ordinal) and is `null` for a
decision made directly. `OptimisationPass.version_ordinal` names the version a pass was started over, so a screen can offer
«Перенести решения из V2». The source must be a pass of the same document set over an earlier version (`conflict` /
`carryover_source_unknown`, `carryover_source_is_target`, `carryover_source_other_document`, `carryover_source_not_earlier`).
The migration's downgrade refuses while a carried decision exists. No counts were added for the tabs of «Оптимизация разделов»:
`SectionSpecification.row_count` and `AcceptedOptimisationProposalPage.total` already are the server's figures for «Форма 7 · N»
and «Принято N».

`UI-PARITY-AUDIT-STATE` (contract `1.40.0`, no migration, no new operation) gives three screens the server data they lacked.
`DocumentAudit.active_run` (`UI-A-47`) is the version's run in flight -- its latest run of the standard analysis in state `queued`,
`running` or `validating`, in the result run's order -- read by `DocumentAuditReadModel.audits` in the same statement as the
audit and rendered by `listDocuments` only; it changes none of the four audit words and the counters never read it, and a run
of an AR v3 group is never an active run (as it is never a result). `RunStatus.estimated_finish_at` (`UI-A-65` / `UI-B-45`) is
the queue item's estimate, from the one function `execution.eta.job_estimated_finish` (the queue calls it too; `run_estimated_finish`
reads the same four facts for one run), present only while the run's job is leased or running and has started.
`OptimisationProposal.saving_percent` (`UI-B-07`) is `(current - proposed) / current * 100` over the two stored unit prices, exact
and rounded half up to two decimals, computed by `saving_percent_for` beside `saving_for`; the quantity cancels, so it exists where
`saving` is `null`. Each of the three is optional and absent when it has nothing to say; the one new schema is `DocumentActiveRun`.

`UI-PARITY-FINDING-ORIGIN` (contract `1.39.0`, migration `0058_finding_decision_origin`, no new operation) gives a carried finding
decision a structured source (`UI-A-73`, the original's «↩ Перенесено из V1»). The new nullable
`expert_decision_event.carried_from_decision_id` (foreign key to the table itself, `dec_` shape, not itself, only an `accept` or a
`reject`, a partial index) is written by `carryOverDecision` in the same statement as the carried event; before it the source
was only in the event's rendered comment, which stays and is never parsed back (events carried before the migration read as made
directly, `D-342`). The one new schema `DecisionCarriedFrom` (the source decision, its finding, its version and the version's
display ordinal) is the optional `carried_from` of `DecisionEvent` and `DecisionRecord` and the optional
`current_verdict_carried_from` of `Finding` and `FindingDetail` -- the origin of the decision that carries the current verdict,
which a later verdict of the expert replaces. `AcceptedOptimisationProposal.carried_from` (`D-335`, part) is the optimisation
side's twin on the accepted list. The downgrade of `0058` refuses while a carried event exists.

`UI-PARITY-ADMIN-C2` (contract `1.36.0`, no migration) brings the administrator's side of the original's «Пользователи»
and the «Диспетчер» counts. `Account.last_sign_in_at` (`UI-A-92`, «Последний вход») is the instant of the account's latest
`access.sign_in_succeeded` event, read from the access journal for the accounts an answer names and never by the seam's
per-request standing read; `endUserSessions` (`UI-A-93`, «Завершить сеансы») is the keyed administrator write that raises
an account's credential epoch and journals `access.sessions_ended` in the same transaction, so every credential the account
holds is refused from its next request; `listAuthEvents` (`UI-A-94`, «Журнал входов») reads the same `audit_event` journal
newest first with a cursor that is an event's own identity, an administrator's read that never sends the sequence and never
holds a password, a token, an address or a login as typed. `listAssignments` answers `total` and the per-status `overview`
the dispatcher's chips show, counted by the server over the scope filters and never from the page held.

`UI-PARITY-KB-ALL` (contract `1.32.0`, no migration) adds `listKnowledgeBaseEntries` (`R-151h`, `D-317`): the knowledge
base's «Все», both decision journals merged at the edge, newest first, each row naming its kind and carrying that
journal's own record, so neither identity is replaced; a product read.

`UI-PARITY-P0P` (contract `1.31.0`, migration `0055_work_schedule`) adds «График работ» (`R-152a`…`R-152h`), the bounded
context `schedule`: the month read (plan and fact per active expert, fact from the last verdict of a checked document), the
reserve read over `work_assignment_current`, and five keyed administrator commands. Every table is an append-only journal;
moving an assignment to another expert goes through `dispatch`'s `transition_assignment`.

`UI-PARITY-S2` (contract `1.42.0`, migration `0060`) adds `startRunFromStage`: a new run that reuses the completed stage outputs of an
earlier run before the chosen stage (`docs/program/RUN-FROM-STAGE-01.md`); the earlier run is unchanged.

`UI-PARITY-C6` (contract `1.41.0`, no migration) adds `listRunFindingBlocks`: the portal blocks that hold each published
finding's evidence, derived on read from the run's text-layer block index and page inventory and the version's portal blocks
(`analysis/geometry/finding_blocks.py`), so a finding can show the blocks it sits in and a block the findings in it.

`UI-PARITY-P0O` (contract `1.30.0`, no migration) adds `listVersionSheetLabels`: each page's sheet label from the
version's portal geometry, so a finding's page is shown with its sheet as in the original.

`UI-PARITY-P0N` (contract `1.29.0`, no migration) adds `getProject`: one project as `listProjects` lists it, `404` when
unknown, for the screens that name their project.

`UI-PARITY-P0M` (contract `1.28.0`, no migration) completes the queue group A of `UI-PARITY-01`: `listExecutionQueue`'s page
gains the overview by state, and each item a queued job's place in the dispatcher's order and its attempt count.

`UI-PARITY-P0L` (contract `1.27.0`, no migration) adds `importRunDecisions` (`R-151d`): the run's own workbook, edited,
loaded back by `finding_uid` (the new «ID замечания» column); each changed row is an ordinary decision event by the
importer, every row is reported. Keyed, `expert`.

`UI-PARITY-P0J` (contract `1.25.0`, no migration) adds `listProposalDecisionJournal` (`R-151h`): the decisions on
optimisation proposals as the knowledge base's «Предложения» half, a product read.

`UI-PARITY-P0I` (contract `1.24.0`, migration `0054_finding_execution_status`) adds the designer's execution status of an
accepted finding (`R-151g`): `setFindingExecutionStatus` (keyed, `expert`), `Finding.execution_status`. Not a decision.

`UI-PARITY-P0H` (contract `1.23.0`, migration `0053_document_tags`) adds free tags on a document (`R-151e`):
`setDocumentTags` (keyed, `expert` or `admin`) and the catalogue `listDocumentTags` (a product read); `listDocuments` filters by
`tag`; `DocumentVersion.tags`.

`UI-PARITY-P0G` (contract `1.22.0`, migration `0052_document_archive`) lets a document be archived or renamed, never deleted
(`R-151a`): `setDocumentArchived` and `renameDocument`, keyed, `expert` or `admin`; `listDocuments` hides an archived document
unless `include_archived`; `DocumentVersion.archived_at`. The history is the audit trail of `Document`.

`UI-PARITY-P0F` (contract `1.21.0`, migration `0051_run_started_by`) records who started a run (`R-151v`): `startRun` and
`reauditRun` write the subject into `audit_run.started_by_user_uid`, a frozen RESTRICT reference; `RunStatus` carries
`started_by_user_uid` and `started_by_label`, `ExecutionQueueItem` `started_by_label`, each absent for an older run.

`UI-PARITY-P0E` (contract `1.20.0`, no migration) added two reads. `listDocuments` takes the optional `section_code`
filter (a `ProjectSection`): only documents whose current version is confirmed for that section, unclassified ones never; the
section page of ruling `R-151l` reads it. `getExecutionDispatch` (`GET /execution/dispatch`) returns the durable pause state
`setExecutionPaused` writes, for the pause indicator of ruling `R-151f`; any one of `expert` and `admin`, `viewer` refused
(`R-150w`). No error code, no migration.

`UI-PARITY-P0B` (contract `1.19.0`, no migration) added the audit state of a document and its counters and no operation. A new
schema `DocumentAuditCounts` (`document_count`, `not_run`, `clean`, `awaiting_decision`, `checked`, `partial`,
`no_expert_decision`) is carried by `listProjects` (the optional `audit_counts` of each `Project`; `createProject` omits it) and
by `SectionDocumentCount` (`audit_counts` and `finding_count`, required); `DashboardSummary` gains `awaiting_decision_findings`.
The three are tallies of one read model (`dashboard/audit_state.py`): a document's current version only, its result run being the
latest `published` or `partial` run in `(created_at, run_id)` order. `VerdictCount` is described as the all-time count of every
finding of every run. `getDashboardSummary` keeps its optional `project_uid`; `listProjects` and `getDashboardSummary` stay any
one role, are not keyed, and the catalogue gains no error code. The rules and their rulings are `docs/program/UI-PARITY-METRICS.md`.

*This paragraph read "Fifteen operations, sealed" while the table below listed seventeen.*
*And then it read "Eighteen" while the table listed nineteen — the identical defect, in the
identical paragraph, found by `W45-JUDGE-A` on 2026-09-25 and not by the guard. **Both sentences
were outside the predecessor scanner**: it read `src/auditmanager/api`, `infra/deploy` and
`web/src`, and this file was in none of them. W48 now discovers tracked text without a suffix
filter and names this live seam specification explicitly; the note remains as the record of why
that scope is load-bearing.*
`tests/contract/api_v1/test_surface_counts_in_prose.py` reads `src/auditmanager/api`,
`infra/deploy` and `web/src` and does **not** read `docs/`, so the sentence outlived two
reseals with nothing able to see it. The count here is checked instead by
`tests/contract/domain_p02/test_seam_register.py`, which compares the **table** against the
frozen document -- so the table cannot rot, and until 2026-09-23 the sentence above it
could.

| Operation | Method and path |
|---|---|
| `createProject` | `POST /projects` |
| `listProjects` | `GET /projects` |
| `uploadDocument` | `POST /projects/{project_uid}/documents` |
| `uploadDocumentVersion` | `POST /projects/{project_uid}/documents/{document_uid}/versions` |
| `setDocumentArchived` | `PUT /projects/{project_uid}/documents/{document_uid}/archive` |
| `renameDocument` | `PUT /projects/{project_uid}/documents/{document_uid}/title` |
| `setDocumentTags` | `PUT /projects/{project_uid}/documents/{document_uid}/tags` |
| `listDocumentTags` | `GET /projects/{project_uid}/document-tags` |
| `setFindingExecutionStatus` | `PUT /findings/{finding_uid}/execution-status` |
| `listProposalDecisionJournal` | `GET /proposal-decisions` |
| `listKnowledgeBaseEntries` | `GET /knowledge-base/entries` |
| `listAcceptedOptimisationProposals` | `GET /optimisation-proposals/accepted` |
| `exportOptimisationProposalsXlsx` | `GET /optimisation-passes/{optimisation_pass_id}/export.xlsx` |
| `importOptimisationProposalDecisions` | `POST /optimisation-passes/{optimisation_pass_id}/decision-imports` |
| `carryOverProposalDecisions` | `POST /optimisation-passes/{optimisation_pass_id}/decision-carryovers` |
| `importRunDecisions` | `POST /runs/{run_id}/decision-imports` |
| `getProject` | `GET /projects/{project_uid}` |
| `listVersionSheetLabels` | `GET /versions/{version_uid}/sheet-labels` |
| `listRunFindingBlocks` | `GET /runs/{run_id}/finding-blocks` |
| `startRunFromStage` | `POST /runs/{run_id}/start-from-stage` |
| `getWorkSchedule` | `GET /work-schedule` |
| `getWorkScheduleReserve` | `GET /work-schedule/reserve` |
| `setWorkScheduleSettings` | `PUT /work-schedule/settings` |
| `setWorkSchedulePlans` | `PUT /work-schedule/plans` |
| `setWorkCalendarDays` | `PUT /work-calendar/days` |
| `setEngineerAbsences` | `PUT /work-schedule/absences` |
| `scheduleAssignments` | `POST /work-schedule/reserve/moves` |
| `getDocumentVersion` | `GET /versions/{version_uid}` |
| `streamDocumentVersionContent` | `GET /versions/{version_uid}/content` |
| `startRun` | `POST /runs` |
| `startArV3BetaGroup` | `POST /ar-v3-beta/groups` |
| `getArV3BetaGroup` | `GET /ar-v3-beta/groups/{group_id}` |
| `getArV3BetaGroupReview` | `GET /ar-v3-beta/groups/{group_id}/review` |
| `getArV3BetaPackStatus` | `GET /ar-v3-beta/pack` |
| `getRunStatus` | `GET /runs/{run_id}` |
| `listRunFindings` | `GET /runs/{run_id}/findings` |
| `getFinding` | `GET /findings/{finding_uid}` |
| `appendDecision` | `POST /findings/{finding_uid}/decisions` |
| `listDecisionHistory` | `GET /findings/{finding_uid}/decisions` |
| `exportRunCsv` | `GET /runs/{run_id}/export.csv` |
| `exportRunXlsx` | `GET /runs/{run_id}/export.xlsx` |
| `issueToken` | `POST /auth/token` |
| `listDocuments` | `GET /projects/{project_uid}/documents` |
| `listVersions` | `GET /documents/{document_uid}/versions` |
| `listRuns` | `GET /versions/{version_uid}/runs` |
| `listDecisions` | `GET /decisions` |
| `changePassword` | `POST /auth/password` |
| `getVersionBlocks` | `GET /versions/{version_uid}/blocks` |
| `getDashboardSummary` | `GET /dashboard` |
| `getMe` | `GET /me` |
| `updateMyProfile` | `PATCH /me` |
| `submitRegistration` | `POST /registrations` |
| `readRegistrationStatus` | `POST /registrations/status` |
| `listRegistrations` | `GET /registrations` |
| `approveRegistration` | `POST /registrations/{request_id}/approve` |
| `rejectRegistration` | `POST /registrations/{request_id}/reject` |
| `listUsers` | `GET /users` |
| `getUser` | `GET /users/{user_uid}` |
| `updateUser` | `PATCH /users/{user_uid}` |
| `archiveUser` | `POST /users/{user_uid}/archive` |
| `restoreUser` | `POST /users/{user_uid}/restore` |
| `purgeUser` | `DELETE /users/{user_uid}` |
| `resetUserPassword` | `POST /users/{user_uid}/password` |
| `endUserSessions` | `POST /users/{user_uid}/sessions/end` |
| `listAuthEvents` | `GET /auth-events` |
| `getProductVersion` | `GET /system/version` |
| `listReleases` | `GET /releases` |
| `markReleaseNotesRead` | `PUT /me/release-notes` |
| `listExecutionQueue` | `GET /execution/queue` |
| `listExecutionJournal` | `GET /execution/journal` |
| `cancelRun` | `POST /runs/{run_id}/cancel` |
| `reauditRun` | `POST /runs/{run_id}/reaudit` |
| `setJobPriority` | `PUT /execution/queue/{job_id}/priority` |
| `setExecutionPaused` | `PUT /execution/dispatch` |
| `getExecutionDispatch` | `GET /execution/dispatch` |
| `listWorkers` | `GET /execution/workers` |
| `setWorkerIntake` | `PUT /execution/workers/{worker_id}/intake` |
| `searchNorms` | `GET /norms/search` |
| `listNormDocuments` | `GET /norm-documents` |
| `getNormDocument` | `GET /norm-documents/{norm_document_id}` |
| `listNormParagraphs` | `GET /norm-documents/{norm_document_id}/paragraphs` |
| `streamNormDocumentContent` | `GET /norm-documents/{norm_document_id}/content` |
| `listNormSnapshots` | `GET /norms/snapshots` |
| `listNormSnapshotEvents` | `GET /norms/snapshots/events` |
| `setCurrentNormSnapshot` | `PUT /norms/snapshots/current` |
| `listVersionPortalBlocks` | `GET /versions/{version_uid}/portal-blocks` |
| `streamVersionPortalBlockCrop` | `GET /versions/{version_uid}/portal-blocks/{portal_block_id}/crop` |
| `getRunNormVerification` | `GET /runs/{run_id}/norm-verification` |
| `classifyDocumentVersion` | `PUT /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/classification` |
| `correctVersionClassification` | `POST /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/classification/corrections` |
| `getVersionSectionReview` | `GET /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/section-review` |
| `compareDocumentVersions` | `GET /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison` |
| `listAnalysisProfiles` | `GET /analysis/profiles` |
| `carryOverDecision` | `POST /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/carryovers` |
| `approveSheetPairing` | `POST /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/sheet-pairings` |
| `withdrawSheetPairing` | `POST /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/sheet-pairings/{sheet_link_id}/withdrawals` |
| `generateComparisonSummary` | `POST /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison/summaries` |
| `createAssignment` | `POST /assignments` |
| `listAssignments` | `GET /assignments` |
| `getAssignment` | `GET /assignments/{assignment_uid}` |
| `transitionAssignment` | `POST /assignments/{assignment_uid}/transitions` |
| `uploadPriceList` | `POST /projects/{project_uid}/price-lists` |
| `listPriceListRevisions` | `GET /projects/{project_uid}/price-lists` |
| `listPriceListPositions` | `GET /price-lists/{price_list_id}/positions` |
| `getEffectiveVendorLists` | `GET /projects/{project_uid}/vendor-lists` |
| `setGlobalVendorList` | `PUT /vendor-lists/{section_code}` |
| `setProjectVendorList` | `PUT /projects/{project_uid}/vendor-lists/{section_code}` |
| `getSpecificationPrices` | `GET /projects/{project_uid}/documents/{document_uid}/specification-prices` |
| `startOptimisationPass` | `POST /projects/{project_uid}/documents/{document_uid}/optimisation-passes` |
| `listOptimisationPasses` | `GET /projects/{project_uid}/optimisation-passes` |
| `listOptimisationProposals` | `GET /optimisation-passes/{optimisation_pass_id}/proposals` |
| `decideOptimisationProposal` | `POST /optimisation-proposals/{optimisation_proposal_id}/decisions` |
| `listProposalDecisions` | `GET /optimisation-proposals/{optimisation_proposal_id}/decisions` |
| `exportOptimisationProposalsCsv` | `GET /optimisation-passes/{optimisation_pass_id}/export.csv` |
| `getSectionSpecification` | `GET /sections/{section_code}/specification` |
| `getRunNormReferences` | `GET /runs/{run_id}/norm-references` |
| `listExecutorConnections` | `GET /executor-connections` |
| `createExecutorConnection` | `POST /executor-connections` |
| `getExecutorConnection` | `GET /executor-connections/{connection_id}` |
| `reviseExecutorConnection` | `POST /executor-connections/{connection_id}/revisions` |
| `archiveExecutorConnection` | `POST /executor-connections/{connection_id}/archive` |
| `setExecutorSecret` | `POST /executor-connections/{connection_id}/secrets` |
| `generateExecutorSshKey` | `POST /executor-connections/{connection_id}/ssh-key` |
| `requestExecutorProbe` | `POST /executor-connections/{connection_id}/probes` |
| `listExecutorRoutes` | `GET /executor-routes` |
| `setExecutorRoute` | `PUT /executor-routes` |
| `listAnalysisPresets` | `GET /analysis/presets` |
| `createAnalysisPreset` | `POST /analysis/presets` |
| `reviseAnalysisPreset` | `POST /analysis/presets/{preset_id}/revisions` |
| `archiveAnalysisPreset` | `POST /analysis/presets/{preset_id}/archive` |
| `issueRunnerToken` | `POST /executor-connections/{connection_id}/runner-tokens` |
| `revokeRunnerToken` | `POST /executor-connections/{connection_id}/runner-tokens/{token_id}/revoke` |
| `claimExecutorTask` | `POST /runner/tasks/claim` |
| `getExecutorTaskImage` | `GET /runner/tasks/{task_id}/images/{blob_id}` |
| `extendExecutorTaskClaim` | `POST /runner/tasks/{task_id}/extend` |
| `submitExecutorTaskAnswer` | `POST /runner/tasks/{task_id}/answer` |
| `failExecutorTask` | `POST /runner/tasks/{task_id}/fail` |
| `createComparisonUpload` | `POST /projects/{project_uid}/comparison-uploads` |
| `listComparisonUploads` | `GET /projects/{project_uid}/comparison-uploads` |
| `getComparisonUpload` | `GET /comparison-uploads/{comparison_upload_id}` |
| `getComparisonUploadProposal` | `GET /comparison-uploads/{comparison_upload_id}/proposal` |
| `uploadComparisonUploadPart` | `PUT /comparison-uploads/{comparison_upload_id}/files/{comparison_upload_file_id}/parts` |
| `completeComparisonUploadFile` | `POST /comparison-uploads/{comparison_upload_id}/files/{comparison_upload_file_id}/completion` |
| `confirmComparisonUploadSet` | `POST /comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/confirmation` |
| `excludeComparisonUploadSet` | `POST /comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/exclusion` |
| `retryComparisonUploadSet` | `POST /comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/retry` |
| `pauseComparisonUpload` | `POST /comparison-uploads/{comparison_upload_id}/pause` |
| `resumeComparisonUpload` | `POST /comparison-uploads/{comparison_upload_id}/resume` |
| `cancelComparisonUpload` | `POST /comparison-uploads/{comparison_upload_id}/cancellation` |
| `listComparisonVersionOrders` | `GET /projects/{project_uid}/documents/{document_uid}/comparison-version-orders` |
| `appendComparisonVersionOrder` | `POST /projects/{project_uid}/documents/{document_uid}/comparison-version-orders` |
| `listVersionPageProfiles` | `GET /versions/{version_uid}/page-profiles` |
| `getVersionPageProfile` | `GET /page-profiles/{comparison_page_profile_id}` |
| `streamVersionPagePreview` | `GET /page-profiles/{comparison_page_profile_id}/preview` |
| `streamVersionPageThumbnail` | `GET /page-profiles/{comparison_page_profile_id}/thumbnail` |
| `streamVersionPageTile` | `GET /page-profiles/{comparison_page_profile_id}/tile` |
| `getComparisonMatrix` | `GET /projects/{project_uid}/documents/{document_uid}/comparison-matrix` |
| `prepareComparisonMatrix` | `POST /projects/{project_uid}/documents/{document_uid}/comparison-matrix/preparation` |
| `listComparisonMatrixEdits` | `GET /projects/{project_uid}/documents/{document_uid}/comparison-matrix/edits` |
| `applyComparisonMatrixEdits` | `POST /projects/{project_uid}/documents/{document_uid}/comparison-matrix/edits` |
| `undoComparisonMatrixEdit` | `POST /projects/{project_uid}/documents/{document_uid}/comparison-matrix/edits/undo` |
| `listComparisonAiLinks` | `GET /projects/{project_uid}/documents/{document_uid}/comparison-ai-links` |
| `startComparisonSeries` | `POST /projects/{project_uid}/documents/{document_uid}/comparison-series` |
| `listComparisonSeries` | `GET /projects/{project_uid}/documents/{document_uid}/comparison-series` |
| `getComparisonSeries` | `GET /comparison-series/{comparison_series_id}` |
| `pauseComparisonSeries` | `POST /comparison-series/{comparison_series_id}/pause` |
| `resumeComparisonSeries` | `POST /comparison-series/{comparison_series_id}/resume` |
| `cancelComparisonSeries` | `POST /comparison-series/{comparison_series_id}/cancellation` |
| `finishComparisonSeries` | `POST /comparison-series/{comparison_series_id}/finish` |
| `listComparisonSheetPairs` | `GET /comparison-transitions/{comparison_transition_id}/sheet-pairs` |
| `getComparisonSheetPair` | `GET /comparison-sheet-pairs/{comparison_sheet_pair_id}` |
| `streamComparisonPairTile` | `GET /comparison-sheet-pairs/{comparison_sheet_pair_id}/tile` |
| `getComparisonOverview` | `GET /projects/{project_uid}/comparison-overview` |
| `getComparisonQueueSummary` | `GET /execution/comparison-queue` |
| `estimateComparisonAiPairCheck` | `GET /projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-check/estimate` |
| `getComparisonAiPairCheck` | `GET /projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-check` |
| `startComparisonAiPairCheck` | `POST /projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-check` |
| `pauseComparisonAiPairCheck` | `POST /comparison-ai-pair-checks/{comparison_ai_job_id}/pause` |
| `resumeComparisonAiPairCheck` | `POST /comparison-ai-pair-checks/{comparison_ai_job_id}/resume` |
| `cancelComparisonAiPairCheck` | `POST /comparison-ai-pair-checks/{comparison_ai_job_id}/cancellation` |
| `listComparisonAiPairHints` | `GET /projects/{project_uid}/documents/{document_uid}/comparison-ai-pair-hints` |
| `estimateComparisonAiSheetChanges` | `GET /comparison-series/{comparison_series_id}/ai-sheet-changes/estimate` |
| `getComparisonAiSheetChanges` | `GET /comparison-series/{comparison_series_id}/ai-sheet-changes` |
| `startComparisonAiSheetChanges` | `POST /comparison-series/{comparison_series_id}/ai-sheet-changes` |
| `pauseComparisonAiSheetChanges` | `POST /comparison-ai-sheet-jobs/{comparison_ai_job_id}/pause` |
| `resumeComparisonAiSheetChanges` | `POST /comparison-ai-sheet-jobs/{comparison_ai_job_id}/resume` |
| `cancelComparisonAiSheetChanges` | `POST /comparison-ai-sheet-jobs/{comparison_ai_job_id}/cancellation` |
| `finishComparisonAiSheetChanges` | `POST /comparison-ai-sheet-jobs/{comparison_ai_job_id}/finish` |
| `dequeueComparisonAiSheetChanges` | `POST /comparison-ai-sheet-jobs/{comparison_ai_job_id}/dequeue` |
| `retryComparisonAiSheetChanges` | `POST /comparison-ai-sheet-jobs/{comparison_ai_job_id}/retry` |
| `getComparisonSheetDescription` | `GET /comparison-sheet-pairs/{comparison_sheet_pair_id}/description` |
| `startComparisonSheetDescription` | `POST /comparison-sheet-pairs/{comparison_sheet_pair_id}/description` |
| `listComparisonSheetDescriptionHistory` | `GET /comparison-sheet-pairs/{comparison_sheet_pair_id}/description-history` |
| `estimateComparisonSheetDescription` | `GET /comparison-sheet-pairs/{comparison_sheet_pair_id}/description/estimate` |
| `streamComparisonSheetDescriptionMd` | `GET /comparison-sheet-pairs/{comparison_sheet_pair_id}/description/md` |
| `listComparisonReviewSheets` | `GET /comparison-transitions/{comparison_transition_id}/review-sheets` |
| `getVersionPageSpecPositions` | `GET /page-profiles/{comparison_page_profile_id}/spec-positions` |
| `getComparisonSheetPairSpecPositions` | `GET /comparison-sheet-pairs/{comparison_sheet_pair_id}/spec-positions` |
| `listComparisonSpecifications` | `GET /comparison-series/{comparison_series_id}/specifications` |
| `getComparisonSpecification` | `GET /comparison-transitions/{comparison_transition_id}/specification` |
| `startComparisonSpecification` | `POST /comparison-transitions/{comparison_transition_id}/specification` |
| `listComparisonSpecificationChanges` | `GET /comparison-transitions/{comparison_transition_id}/specification/changes` |
| `estimateComparisonSpecification` | `GET /comparison-transitions/{comparison_transition_id}/specification/estimate` |
| `cancelComparisonSpecification` | `POST /comparison-ai-spec-jobs/{comparison_ai_job_id}/cancellation` |
| `getComparisonLaunchQueue` | `GET /projects/{project_uid}/comparison-launch-queue` |
| `enqueueComparisonLaunch` | `POST /projects/{project_uid}/comparison-launch-queue/entries` |
| `pauseComparisonLaunchQueue` | `POST /projects/{project_uid}/comparison-launch-queue/pause` |
| `resumeComparisonLaunchQueue` | `POST /projects/{project_uid}/comparison-launch-queue/resume` |
| `clearComparisonLaunchQueue` | `POST /projects/{project_uid}/comparison-launch-queue/clear` |
| `removeComparisonLaunchEntry` | `POST /comparison-launch-entries/{comparison_launch_entry_id}/removal` |
| `getComparisonAiQueue` | `GET /execution/comparison-ai-queue` |
| `streamComparisonSeriesSummary` | `GET /comparison-series/{comparison_series_id}/summary-md` |
| `listComparisonReports` | `GET /comparison-series/{comparison_series_id}/reports` |
| `createComparisonReport` | `POST /comparison-series/{comparison_series_id}/reports` |
| `uploadComparisonReportSource` | `POST /comparison-series/{comparison_series_id}/reports/upload` |
| `getComparisonReport` | `GET /comparison-reports/{comparison_report_id}` |
| `startComparisonReport` | `POST /comparison-reports/{comparison_report_id}/start` |
| `cancelComparisonReport` | `POST /comparison-reports/{comparison_report_id}/cancellation` |
| `continueComparisonReport` | `POST /comparison-reports/{comparison_report_id}/continuation` |
| `rebuildComparisonReportPdf` | `POST /comparison-reports/{comparison_report_id}/pdf-rebuild` |
| `deleteComparisonReport` | `POST /comparison-reports/{comparison_report_id}/deletion` |
| `prepareComparisonClientReport` | `POST /comparison-reports/{comparison_report_id}/client-report` |
| `streamComparisonReportPdf` | `GET /comparison-reports/{comparison_report_id}/pdf` |
| `streamComparisonReportSourceMd` | `GET /comparison-reports/{comparison_report_id}/source-md` |
| `listStagePairs` | `GET /projects/{project_uid}/stage-pairs` |
| `confirmStagePair` | `POST /projects/{project_uid}/stage-pairs` |
| `getStagePair` | `GET /stage-pairs/{stage_pair_id}` |
| `listStagePairSuggestions` | `GET /projects/{project_uid}/stage-pair-suggestions` |
| `createStageAssembly` | `POST /projects/{project_uid}/stage-assemblies` |
| `reviseStageAssembly` | `POST /stage-assemblies/{stage_assembly_id}/members` |
| `setStagePairCompleteness` | `POST /stage-pairs/{stage_pair_id}/completeness` |
| `createStageUpload` | `POST /projects/{project_uid}/stage-uploads` |
| `listStageUploads` | `GET /projects/{project_uid}/stage-uploads` |
| `getStageUpload` | `GET /stage-uploads/{stage_upload_id}` |
| `uploadStageUploadPart` | `PUT /stage-uploads/{stage_upload_id}/files/{stage_upload_file_id}/parts` |
| `completeStageUploadFile` | `POST /stage-uploads/{stage_upload_id}/files/{stage_upload_file_id}/completion` |
| `confirmStageUploadCandidate` | `POST /stage-upload-candidates/{stage_upload_candidate_id}/confirmation` |
| `rejectStageUploadCandidate` | `POST /stage-upload-candidates/{stage_upload_candidate_id}/rejection` |
| `pauseStageUpload` | `POST /stage-uploads/{stage_upload_id}/pause` |
| `resumeStageUpload` | `POST /stage-uploads/{stage_upload_id}/resume` |
| `cancelStageUpload` | `POST /stage-uploads/{stage_upload_id}/cancellation` |
| `listStageSheetPassports` | `GET /stage-pairs/{stage_pair_id}/sheet-passports` |
| `listStageSheetSuggestions` | `GET /stage-pairs/{stage_pair_id}/sheet-suggestions` |
| `getStageSheetMap` | `GET /stage-pairs/{stage_pair_id}/sheet-map` |
| `applyStageSheetMap` | `POST /stage-pairs/{stage_pair_id}/sheet-map` |
| `listStageSheetMapHistory` | `GET /stage-pairs/{stage_pair_id}/sheet-map/revisions` |
| `getStageSheetMapRevision` | `GET /stage-link-revisions/{stage_link_revision_id}` |
| `listStageTextFragments` | `GET /stage-pairs/{stage_pair_id}/text-fragments` |
| `listStageTextExclusions` | `GET /stage-link-revisions/{stage_link_revision_id}/text-exclusions` |
| `listStageRawDifferences` | `GET /stage-link-revisions/{stage_link_revision_id}/raw-differences` |
| `listStageTextHints` | `GET /stage-link-revisions/{stage_link_revision_id}/text-hints` |
| `recomputeStageTextEvidence` | `POST /stage-link-revisions/{stage_link_revision_id}/text-evidence/recomputation` |
| `startStageChainRun` | `POST /stage-pairs/{stage_pair_id}/chain-runs` |
| `listStageChainRuns` | `GET /stage-pairs/{stage_pair_id}/chain-runs` |
| `getStageChainRun` | `GET /stage-chain-runs/{stage_chain_run_id}` |
| `cancelStageChainRun` | `POST /stage-chain-runs/{stage_chain_run_id}/cancellation` |
| `listExecutorGroups` | `GET /executor-groups` |
| `createExecutorGroup` | `POST /executor-groups` |
| `getExecutorGroup` | `GET /executor-groups/{group_id}` |
| `reviseExecutorGroup` | `POST /executor-groups/{group_id}/revisions` |
| `archiveExecutorGroup` | `POST /executor-groups/{group_id}/archive` |
| `getExecutorGroupCapacity` | `GET /executor-groups/{group_id}/capacity` |
| `listExecutorRoutingRules` | `GET /executor-routing-rules` |
| `setExecutorRoutingRule` | `PUT /executor-routing-rules/{work_kind}` |
| `previewExecutorRouting` | `GET /executor-routing/preview` |
| `setExecutorRoutingMode` | `POST /executor-routing/mode` |
| `issueExecutorEnrollment` | `POST /executor-connections/{connection_id}/enrollments` |
| `setExecutorIntegrationAuthorisation` | `POST /executor-connections/{connection_id}/integration-authorisation` |
| `createExecutorAgentInstall` | `POST /executor-connections/{connection_id}/agent-installs` |
| `getExecutorAgentInstall` | `GET /executor-connections/{connection_id}/agent-installs/{install_id}` |
| `confirmExecutorAgentInstallHostKey` | `POST /executor-connections/{connection_id}/agent-installs/{install_id}/confirm-host-key` |
| `redeemExecutorEnrollment` | `POST /runner/enroll` |
| `reportRunnerHealth` | `POST /runner/health` |
| `downloadAgentPackage` | `GET /runner/agent-package/{version}` |
| `estimateStageChainRun` | `GET /stage-link-revisions/{stage_link_revision_id}/chain-estimate` |
| `resumeStageChainRun` | `POST /stage-chain-runs/{stage_chain_run_id}/resume` |
| `startStageChainBatch` | `POST /projects/{project_uid}/stage-chain-batches` |
| `getStageChainBatch` | `GET /stage-chain-batches/{stage_chain_batch_id}` |
| `pauseStageChainBatch` | `POST /stage-chain-batches/{stage_chain_batch_id}/pause` |
| `resumeStageChainBatch` | `POST /stage-chain-batches/{stage_chain_batch_id}/resume` |
| `cancelStageChainBatch` | `POST /stage-chain-batches/{stage_chain_batch_id}/cancellation` |
| `listStageAiReviews` | `GET /stage-chain-runs/{stage_chain_run_id}/ai-reviews` |
| `listStageClassifications` | `GET /stage-chain-runs/{stage_chain_run_id}/classifications` |
| `getStageSynthesis` | `GET /stage-chain-runs/{stage_chain_run_id}/synthesis` |
| `listStageGraphicEvidence` | `GET /stage-chain-runs/{stage_chain_run_id}/graphic-evidence` |
| `listStageLinkRepairs` | `GET /stage-chain-runs/{stage_chain_run_id}/sheet-link-repairs` |
| `undoStageLinkRepair` | `POST /stage-link-repairs/{stage_link_repair_id}/undo` |
| `listStageChangeCards` | `GET /stage-chain-runs/{stage_chain_run_id}/cards` |
| `getStageChangeCard` | `GET /stage-change-cards/{stage_change_card_id}` |
| `applyStageCardVerdicts` | `POST /stage-chain-runs/{stage_chain_run_id}/card-verdicts` |
| `listStageCardVerdicts` | `GET /stage-change-cards/{stage_change_card_id}/verdicts` |
| `getStageChangeJournal` | `GET /stage-chain-runs/{stage_chain_run_id}/journal` |
| `streamStageChangeJournalXlsx` | `GET /stage-chain-runs/{stage_chain_run_id}/journal.xlsx` |
| `streamStageChangeJournalPdf` | `GET /stage-chain-runs/{stage_chain_run_id}/journal.pdf` |
| `streamStageChangeJournalHtml` | `GET /stage-chain-runs/{stage_chain_run_id}/journal.html` |
| `getStageProfileText` | `GET /comparison-page-profiles/{comparison_page_profile_id}/stage-text` |
| `getStageAssembly` | `GET /stage-assemblies/{stage_assembly_id}` |
| `createStageReviewCard` | `POST /stage-chain-runs/{stage_chain_run_id}/review-cards` |
| `estimateRunCost` | `POST /runs/cost-estimate` |
| `estimateArV3GroupCost` | `POST /ar-v3-beta/groups/cost-estimate` |
| `getExtendedRunReview` | `GET /runs/{run_id}/extended-review` |
| `importComparisonZip` | `POST /projects/{project_uid}/comparison-zip-uploads` |
| `streamComparisonTechnicalReport` | `GET /comparison-series/{comparison_series_id}/technical-report` |

Rules that hold across the whole surface:

* the writes that take a required `Idempotency-Key` header are `createProject`,
  `uploadDocument`, `uploadDocumentVersion`, `startRun`, `startArV3BetaGroup`, `appendDecision`,
  `approveRegistration`, `cancelRun`, `reauditRun`, `setJobPriority`,
  `setExecutionPaused`, `setWorkerIntake`, `endUserSessions`, `carryOverDecision`, `setDocumentArchived`, `renameDocument`, `setDocumentTags`, `setFindingExecutionStatus`,
  `importRunDecisions`, `importOptimisationProposalDecisions`, `carryOverProposalDecisions`, `setWorkScheduleSettings`, `setWorkSchedulePlans`, `setWorkCalendarDays`, `setEngineerAbsences`,
  `scheduleAssignments`,
  `approveSheetPairing`, `withdrawSheetPairing`, `generateComparisonSummary`, `uploadPriceList`, `startOptimisationPass`, `decideOptimisationProposal`,
  `createExecutorConnection`, `reviseExecutorConnection`, `archiveExecutorConnection`,
  `setExecutorSecret`, `generateExecutorSshKey`, `requestExecutorProbe`,
  `setExecutorRoute`, `createAnalysisPreset`, `reviseAnalysisPreset`, `archiveAnalysisPreset`,
  `issueRunnerToken`, `revokeRunnerToken`,
  `createComparisonUpload`, `uploadComparisonUploadPart`, `completeComparisonUploadFile`, `confirmComparisonUploadSet`, `excludeComparisonUploadSet`, `retryComparisonUploadSet`, `pauseComparisonUpload`, `resumeComparisonUpload`, `cancelComparisonUpload`, `appendComparisonVersionOrder`, `prepareComparisonMatrix`, `applyComparisonMatrixEdits`, `undoComparisonMatrixEdit`, `startComparisonSeries`, `pauseComparisonSeries`, `resumeComparisonSeries`, `cancelComparisonSeries`, `finishComparisonSeries`, `startComparisonAiPairCheck`, `pauseComparisonAiPairCheck`, `resumeComparisonAiPairCheck`, `cancelComparisonAiPairCheck`, `startComparisonAiSheetChanges`, `pauseComparisonAiSheetChanges`, `resumeComparisonAiSheetChanges`, `cancelComparisonAiSheetChanges`, `finishComparisonAiSheetChanges`, `dequeueComparisonAiSheetChanges`, `retryComparisonAiSheetChanges`, `startComparisonSheetDescription`, `startComparisonSpecification`, `cancelComparisonSpecification`, `enqueueComparisonLaunch`, `pauseComparisonLaunchQueue`, `resumeComparisonLaunchQueue`, `clearComparisonLaunchQueue`, `removeComparisonLaunchEntry`, `createComparisonReport`, `uploadComparisonReportSource`, `startComparisonReport`, `cancelComparisonReport`, `continueComparisonReport`, `rebuildComparisonReportPdf`, `deleteComparisonReport` and `prepareComparisonClientReport`, `confirmStagePair`, `createStageAssembly`, `reviseStageAssembly`, `setStagePairCompleteness`, `createStageUpload`, `uploadStageUploadPart`, `completeStageUploadFile`, `confirmStageUploadCandidate`, `rejectStageUploadCandidate`, `pauseStageUpload`, `resumeStageUpload`, `cancelStageUpload`, `applyStageSheetMap`, `recomputeStageTextEvidence`, `startStageChainRun`, `cancelStageChainRun`, `resumeStageChainRun`, `startStageChainBatch`, `pauseStageChainBatch`, `resumeStageChainBatch`, `cancelStageChainBatch`, `undoStageLinkRepair`, `applyStageCardVerdicts`, `createStageReviewCard`, `importComparisonZip`, `issueExecutorEnrollment`, `setExecutorIntegrationAuthorisation`, `createExecutorAgentInstall`, `confirmExecutorAgentInstallHostKey`, `createExecutorGroup`, `reviseExecutorGroup`, `archiveExecutorGroup`, `setExecutorRoutingRule`, `setExecutorRoutingMode`, and no others. A repeat of the decision carryover under another key
  that names the same pair and decision answers the event already carried (`replayed: true`)
  and appends nothing.
  `setGlobalVendorList` and `setProjectVendorList` take no key: a repeat of the latest
  revision's entries writes nothing and answers it, and a writer that read an older revision
  is refused by `expected_vendor_list_id` (`conflict_reason: vendor_list_changed`).
  A new key over exactly the inputs of a stored optimisation pass answers that pass and
  writes nothing; every decision under a new key is a new appended event.
  The key is passed through to the owning command handler and never re-derived in the
  router: an identical repeat replays the first answer, and another payload under the same
  key is `idempotency_key_reuse`. The other writes take no key. What a repeat of each does
  was measured at `W49-SEAL-01` (`tests/integration/api/test_user_management.py::TestARepeatWithoutAKey`,
  `test_registration_flow.py`, `tests/integration/auth/test_revocation.py`):
  * `issueToken` and `readRegistrationStatus` write nothing but the brakes' counters. A
    repeat of the first mints another credential; a repeat of the second answers the
    same status again;
  * `changePassword`: a repeat presents the credential the change revoked, and is
    `authentication_required`;
  * `updateMyProfile` and `updateUser` state the result, so a repeat writes the same names
    and role set again. An unchanged role set raises no credential epoch;
  * `submitRegistration`: a repeat while the first application is pending is `conflict`
    with `conflict_reason: request_pending`;
  * `rejectRegistration`, `archiveUser` and `restoreUser`: a repeat is
    `state_transition_not_allowed` on the `registration_request` or `app_user` machine;
  * `purgeUser`: a repeat is `not_found`;
  * `resetUserPassword` repeats its effect: the temporary password is set again, and every
    credential issued in between is refused;
  * `markReleaseNotesRead` raises the account's own read mark through a known release;
    a lower or equal version is a no-op and takes no key;
  * `setCurrentNormSnapshot` (`W55A-SEAL-01`) is a compare-and-set on `expected_current`:
    a repeat whose target is already current answers the current designation as a replay
    and writes no history row, and a repeat after another designation is `conflict` with
    `conflict_reason: stale_current_snapshot`;
  * `classifyDocumentVersion` (`W59-SECTION-SEAL-01`) writes one row per version: an exact
    repeat answers the stored classification with its first confirmer, and a repeat with a
    different stage or section is `conflict` with `conflict_reason:
    version_already_classified`;
  * `correctVersionClassification` (`CLASSIFICATION-CORRECTION-01`) appends a numbered
    revision and is a compare-and-set on `expected_revision`: an exact repeat (same expert,
    values, reason and `expected_revision`) answers the stored revision and writes nothing, a
    stale `expected_revision` is `conflict` with `conflict_reason:
    classification_revision_stale`, an unclassified version is `conflict` with
    `conflict_reason: version_not_classified`, and a pair equal to the current
    classification is `validation_failed`;
  * `createAssignment` (`W61-DISPATCHER-01`) keeps one open assignment per scope: an exact
    repeat (same assignee and note) answers the open assignment, and any other creation on
    that scope is `conflict` with `conflict_reason: assignment_open`;
  * `transitionAssignment` (`W61-DISPATCHER-01`): a repeat equal to the latest event (same
    kind, reason and new assignee) answers the assignment unchanged and appends nothing; any
    other move the `work_assignment` machine does not declare from the current state is
    `state_transition_not_allowed`;
  * `claimExecutorTask` (`EXEC-PULL-01`): a runner token whose connection allows one claim
    at a time and that still holds it is given the same task again with its lease
    refreshed; any other repeat takes the next open task, or waits and answers `204`;
  * `extendExecutorTaskClaim`: a repeat pushes the lease forward again, never beyond the task's
    deadline; a claim that is no longer the token's is `conflict` with `conflict_reason:
    claim_lost`;
  * `submitExecutorTaskAnswer`: the same answer again is accepted and answered as the first
    was; a different answer to an answered task is `conflict` with `conflict_reason:
    answer_differs`, and an answer to an expired, failed or cancelled task is `conflict`;
  * `failExecutorTask`: a repeat on a failed task answers it unchanged; a task already
    answered or expired is `conflict`;
  * `reportRunnerHealth` (`EXEC2-SEAL-1`): a repeat stores the same report again on the calling
    token, and a later report replaces the earlier one; a report that violates the schema is
    `validation_failed`;
  * `redeemExecutorEnrollment` (`EXEC2-SEAL-1`): a repeat from the same `runner_instance_id` inside
    the exchange window is answered idempotently, so an agent that lost the response is not
    locked out; a repeat after the window is `conflict` with `conflict_reason:
    enrollment_redeemed`, and an unknown, expired or revoked secret is `authentication_required`;
  * `estimateRunCost` and `estimateArV3GroupCost` (`BETA-COST-PREFLIGHT-1030`) are POSTs that
    write nothing: a repeat computes the estimate again, and its digest differs only when the
    source, profile, preset, route, model or rates differ;
* every response carries `X-Correlation-Id`;
* every non-2xx body is the `ErrorEnvelope`, with `retryable` pinned to the catalog
  value for the reported code;
* the viewer streams bytes from the server. There is no redirect and no presigned
  link: a URL into object storage is the internal address the contract forbids in a
  response, and it would outlive the request that authorized it;
* growing lists — projects, findings, decision history — are cursor-paginated;
* every operation requires a bearer credential **and** a credential generation the account
  still accepts, except the six a runner calls with a runner token (`EXEC-PULL-01`, `EXEC-IMAGE-DELIVERY-01`
  and `EXEC2-SEAL-1`, `RUNNER_OPERATIONS` in `src/auditmanager/api/security.py`: a principal of its own, no
  account and no role), the one an agent calls with an enrollment secret (`redeemExecutorEnrollment`, `ENROLLMENT_OPERATIONS`
  in the same module) and those the sealed contract declares with `security: []` —
  `issueToken`, `submitRegistration`, `readRegistrationStatus` and `downloadAgentPackage`, listed by
  `python3 -c "import json; d = json.load(open('contracts/api/v1/openapi.json')); print(sorted(o['operationId'] for p in d['paths'].values() for o in p.values() if isinstance(o, dict) and o.get('security') == []))"`
  and held in code as `UNAUTHENTICATED_OPERATIONS` in `src/auditmanager/api/security.py`.
  `changePassword` raises that generation, which is how a credential already issued is taken
  back: see the same module. Who may take back whom is no longer an open vocabulary:
  `R-55` gives every account a role set drawn from `expert` and `admin`, and `R-60` decides
  what each set reaches — product data is read by an active account with a complete
  profile and at least one role (`R-80`; an account whose role set is empty is suspended and
  reads only its own account, the product version and the release notes), product changes
  require `expert`, and account and registration-request
  management require `admin` — per `operationId` in `OPERATION_ROLES` of the same module.
  So an administrator takes back another account's credentials through `archiveUser`,
  `resetUserPassword` or a change of its role set in `updateUser`, each of which raises the
  generation, as `restoreUser` does. An administrator may not archive itself, reset its own
  password, end its own sessions or remove a role of its own, and the last active administrator
  can neither be archived nor lose `admin` (`W49-PLAN.md` §3.2). Since contract `1.36.0`
  (`UI-A-93`) one operation has no other effect than to revoke: `endUserSessions` ends every
  session of one account and nothing else. Bulk revocation — everyone's credentials — remains an
  operator's action from a shell (`python -m auditmanager.access.revoke`).

## 8. Owner decisions this seam register encodes

| Decision | Where it lands |
|---|---|
| `OD-04` | §4.5 — empty crop manifest under `crop_policy: none`; **flipped** by `W55B-SEAL-01` (`R-119`): a content schema, and `crop_policy: portal_image_blocks` for a bundle |
| `R-116` | §4.2, §4.8 — uploads are portal bundles; OCR is always marked and never merged into the text layer |
| `R-117` | §4.7, §4.8 — portal descriptions are shown, marked, and never used in analysis |
| `R-118` | §7 — `startRun` and `reauditRun` refuse a version above the analysis input budget up front |
| `OD-10` | `audit_run.interrupted_reason`; a stale `running` run reconciles to `failed`, and no `interrupted` state is invented |
| `OD-11` | §6 in full — bytes, granularity, sort key and the `publishes_result` discriminator |
| `OD-12` | `expert_decision_event.author_label`, a column, because deciding it later would have been a schema change |
| `OD-14` | the existence of this document and of `contracts/api/v1/**` |
| `OD-24` | §9.2 — the guards PC-01 records as unevaluated |

## 9. What PC-01 does not claim

Recorded here so the catalog does not silently promise an aggregate nobody builds.

### 9.1 Identifiers declared and deliberately unallocated

`import_id`, `export_id`,
`comparison_id`, `sheet_link_id`, `norms_snapshot_id`, `erasure_request_id`,
`object_uid`, `discipline_uid`.

The value types exist — the catalog is complete — but no PC-01 code path allocates
one, and no table carries a column for one, with two exceptions:
`audit_run.norms_snapshot_id`, which exists and stays `NULL` so that restoring norms
pinning later is not a schema change; and `worker.worker_id` with `lease.worker_id`
(migration `0019`), which `W54-SEAL-01` sealed and which stay empty and `NULL` until
`W54-WORKER-01` registers a worker process. The custody and repair identities `nad`,
`nbd` and `nrc` (migration `0018`) are not listed here: their Stage-B owners allocate
them in this same wave.

There is no `Import` aggregate at all: PC-01 ingests one portal bundle (since `W55B-SEAL-01`; one PDF
before it) through a direct upload command, the `import` state machine is not implemented, and PC-01 claims no
conformance to it.

### 9.2 `audit_run` guards recorded as unevaluated — `OD-24`

The runner uses the contract's **state names and transition topology** and claims no more.
Two guard clauses are recorded unevaluated rather than generated and left
unreachable:

1. the `NormsSnapshot` clause of the `created → queued` reference-resolution guard —
   since `W55A-PIN-01` a run pins the current norms snapshot when one is designated and
   NULL otherwise (`R-113`); no stage reads norms before W57, so the clause is still not
   evaluated as a guard. The input-manifest, `AnalysisProfile` and `PromptBundle` clauses
   of that same guard **are** evaluated;
2. the `ResultPackage` **schema** clause of `validating → published`. PC-01 publishes
   no result package and validates declared checksums and required artifact roles
   directly.

The `queued → running` and `running → validating` authority clauses are now evaluated:
the Job row and current Attempt are locked, and the opaque execution token is compared
inside every guarded publication transaction. `execution_token_invalid` and
`stale_attempt` therefore have concrete producers. Cancellation remains outside the
slice: no cancel command exists, so `cancelled` is declared and unreachable.

The suite asserts the two remaining guards **absent**, never passing, so it never
reports coverage it does not have.

### 9.3 Contract objects PC-01 does not publish

`JobPackage` and `ResultPackage` both list `attempt_authority` in their top-level
`required` array, and that object requires `run_id`, `job_id`, `attempt_id` and
`execution_token`. The local runner now produces that authority tuple internally, but
does not cross a remote-dispatch boundary; it therefore still publishes neither
envelope and claims no conformance to either schema. Neither contract file is edited.

The one analysis object PC-01 publishes as a contract is the `StageResult`, whose
`required` array contains no `attempt_authority`. PC-01 claims **full** conformance to
that schema and validates every emitted result against it.

### 9.4 Error-code producer status

`execution_token_invalid` and `stale_attempt` now have producers in the current-Attempt
guard. Neither error contains the supplied or stored token.

`partial_result_not_publishable` — see §6.

`authentication_required` and `permission_denied` — PC-01 has no authentication and no
role model. They stay in the closed enum; no route emits them.

`required_norm_unavailable` — no norms snapshot is pinned, or a run's pinned analysis profile pair
is not registered in the deployment (`reference_kind: analysis_profile`, raised by the executor).

`version_classification_required` and `section_profile_unavailable` (`BETA-CONTRACT-SEAL-01`,
`D-179`) — `startRun` and `reauditRun` refuse a version with no expert-confirmed stage and section,
and a confirmed section with no registered text profile, each with its own code and no details,
before the idempotency key is claimed; a draft reported both as `required_norm_unavailable` with
`reference_kind` `version_classification` / `analysis_profile`.

`unsupported_contract_version` — the surface carries one contract version, `1.0.0` since `BETA-CONTRACT-SEAL-01` (the domain, analysis and events families moved with it).

### 9.5 Deferred widenings, recorded so they are not rediscovered as bugs

* **Idempotency scope.** The contract scopes a command key to command type **plus
  authorized subject plus target aggregate**. `command_record` is unique on
  `(command_type, idempotency_key)` only, because PC-01 has no authenticated subject.
  Adding the subject dimension is a migration, and it is a widening rather than a
  correction.
* **A materialized verdict projection.** `finding_current_verdict` is a view. If a
  consumer needs a table, that is a request to this seam with a measurement attached,
  not a local addition.
* **Command-record retention.** `idempotency_key_stale` is the fail-closed answer once
  a record is gone. No retention window is declared anywhere: it stays under the open
  `OPEN-RETENTION` / `U-04` owner decision, and no lane may invent a numeric value.

## 10. Changing a seam

1. Write the failing test that shows the current shape does not serve your slice.
2. Hand both to the integrator. Do not edit this file, `db/migrations/**` or
   `contracts/api/v1/**` from a Gate B session.
3. A shape change reaches every consumer, so it is announced, not merged quietly.

The frozen commit of this document is recorded in the Gate A convergence report.
