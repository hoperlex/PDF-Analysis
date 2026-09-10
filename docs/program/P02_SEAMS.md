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
| S10 | The P02 migration head and its constraints, `0002_pc01_schema` | `A1` | every session that writes a row |
| S11 | Opaque identifier value types, `auditmanager.shared.identity` | `A1` | every session |
| S12 | Engine, session and transaction construction, `auditmanager.shared.db` | `A1` | every session that touches the database |
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

**Head: `0002_pc01_schema`**, parent `0001_baseline`. One head, one owner. No Gate B
session writes DDL.

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
| `finding` | `finding_uid` | mutable |
| `finding_observation` | `finding_observation_id` | **immutable after insert** |
| `finding_evidence` | `(finding_observation_id, evidence_ordinal)` | **immutable after insert** |
| `expert_decision_event` | `decision_id` | **append-only: no UPDATE, no DELETE** |
| `audit_event` | `audit_event_id` | **append-only: no UPDATE, no DELETE** |
| `contract_state_transition` | reference data | frozen; not a domain aggregate |

Plus the view `finding_current_verdict`, which is §5.4.

**There is no `job`, `attempt`, `lease`, `import`, `export`, `worker`, `comparison`,
`norms_snapshot` or `outbox` table.** PC-01 instantiates none of those aggregates. A
test asserts their absence, so adding one is a visible scope change rather than a
quiet convenience.

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

`contract_state_transition` holds the topology of the three machines PC-01
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

The `import`, `job` and `attempt` machines are **not instantiated**. PC-01 has no
Import, no Job and no Attempt, so there is no table, no state column and no
conformance claim.

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
| `geometry.page_crops` | `B2` `page_geometry_extraction` | none in PC-01 (`OD-04`) | 4.5 |
| `context.document_graph` | `B2` `document_context_build` | `B3` `text_analysis` | 4.6 |
| `analysis.text_observations` | `B3` `text_analysis` | `B4` grounding gate | 4.7 |

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
* `has_text_layer` must be `true` for every page. A page without extractable embedded
  text is refused at ingest with `validation_failed`; it never reaches this artifact.
  The field exists so the refusal is provable, not so a consumer can degrade.
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

`OD-04`. The registry marks this a required output of a stage that allows neither
`partial` nor `skipped`, and PC-01 does no visual detection. So the role is present,
schema-valid and explicitly empty under a declared `crop_policy: none`, echoed in the
stage metrics as `crop_policy=none` and `crop_count=0`. Its only contract consumer,
`block_analysis`, is out of PC-01 scope and would fail closed on an empty list rather
than degrade.

**Flip condition, carried from `OD-04`:** if any task adds a content schema for the
crop manifest, this decision reopens.

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
* `pages_analysed` is what makes the `partial` mapping checkable: `partial` is
  reported only when usable observations were produced over a **strict subset** of
  pages, with a typed error. An unavailable provider is `failed` with
  `dependency_unavailable`, never `partial`.

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
`span_outside_page`, `span_outside_block`, `span_length_mismatch`.

### 5.2 Identity allocation

* `finding_uid` — a fresh one per published observation, per run. PC-01 does **no**
  cross-run matching and **no** decision carryover. Two runs over the same document
  produce two disjoint sets of `finding_uid`.
* `finding_observation_id` — immutable, bound to exactly one `run_id`. A rerun
  creates new observations and never rewrites or removes earlier ones. The database
  refuses UPDATE and DELETE.

### 5.3 The decision ledger

Append-only. Every event is a new `decision_id`. Nothing is ever updated.

| Field | Rule |
|---|---|
| `decision_id` | fresh per event |
| `finding_uid` | the finding being judged |
| `finding_observation_id` | the observation the expert actually reviewed |
| `event_type` | `accept`, `reject`, `comment`; `revoke` declared, no PC-01 producer |
| `verdict` | `accepted` for accept, `rejected` for reject, `pending` for revoke, `null` for comment |
| `comment` | required for `comment`, optional on any other type |
| `author_label` | `OD-12`: one configured local reviewer label, persisted server-side. A label, not a subject identity; it authorizes nothing |
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

Seventeen columns, in this order. This is the frozen list; `B5` produces it and `B8`
downloads it.

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

**Bytes.** UTF-8 with a byte-order mark; comma delimiter; CRLF line ending; RFC 4180
quoting. The BOM is there because the intended reader opens the file in Excel, which
otherwise mis-decodes Cyrillic.

**Granularity.** One row per evidence item. A finding with three quotations produces
three rows sharing columns 1–11 and 14–17.

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

Twelve operations, frozen. `A5` generates the typed client from this document; `B6`
implements the routers against it; `B7` and `B8` consume the client and never call
`fetch` directly.

| Operation | Method and path |
|---|---|
| `createProject` | `POST /projects` |
| `listProjects` | `GET /projects` |
| `uploadDocument` | `POST /projects/{project_uid}/documents` |
| `getDocumentVersion` | `GET /versions/{version_uid}` |
| `streamDocumentVersionContent` | `GET /versions/{version_uid}/content` |
| `startRun` | `POST /runs` |
| `getRunStatus` | `GET /runs/{run_id}` |
| `listRunFindings` | `GET /runs/{run_id}/findings` |
| `getFinding` | `GET /findings/{finding_uid}` |
| `appendDecision` | `POST /findings/{finding_uid}/decisions` |
| `listDecisionHistory` | `GET /findings/{finding_uid}/decisions` |
| `exportRunCsv` | `GET /runs/{run_id}/export.csv` |

Rules that hold across the whole surface:

* every write takes a required `Idempotency-Key` header, passed through to the owning
  command handler and never re-derived in the router;
* every response carries `X-Correlation-Id`;
* every non-2xx body is the `ErrorEnvelope`, with `retryable` pinned to the catalog
  value for the reported code;
* the viewer streams bytes from the server. There is no redirect and no presigned
  link: a URL into object storage is the internal address the contract forbids in a
  response, and it would outlive the request that authorized it;
* growing lists — projects, findings, decision history — are cursor-paginated.

## 8. Owner decisions this seam register encodes

| Decision | Where it lands |
|---|---|
| `OD-04` | §4.5 — empty crop manifest under `crop_policy: none`, with its flip condition |
| `OD-10` | `audit_run.interrupted_reason`; a stale `running` run reconciles to `failed`, and no `interrupted` state is invented |
| `OD-11` | §6 in full — bytes, granularity, sort key and the `publishes_result` discriminator |
| `OD-12` | `expert_decision_event.author_label`, a column, because deciding it later would have been a schema change |
| `OD-14` | the existence of this document and of `contracts/api/v1/**` |
| `OD-24` | §9.2 — the guards PC-01 records as unevaluated |

## 9. What PC-01 does not claim

Recorded here so the catalog does not silently promise an aggregate nobody builds.

### 9.1 Identifiers declared and deliberately unallocated

`import_id`, `job_id`, `attempt_id`, `lease_id`, `worker_id`, `export_id`,
`comparison_id`, `sheet_link_id`, `norms_snapshot_id`, `erasure_request_id`,
`object_uid`, `discipline_uid`.

The value types exist — the catalog is complete — but no PC-01 code path allocates
one, and no table carries a column for one, with the single exception of
`audit_run.norms_snapshot_id`, which exists and stays `NULL` so that restoring norms
pinning later is not a schema change.

There is no `Import` aggregate at all: PC-01 ingests one PDF through a direct upload
command, the `import` state machine is not implemented, and PC-01 claims no
conformance to it.

### 9.2 `audit_run` guards recorded as unevaluated — `OD-24`

PC-01 uses the contract's **state names and transition topology** and claims no more.
Four guard clauses are recorded unevaluated rather than generated and left
unreachable:

1. the `NormsSnapshot` clause of the `created → queued` reference-resolution guard —
   PC-01 pins no norms snapshot. The input-manifest, `AnalysisProfile` and
   `PromptBundle` clauses of that same guard **are** evaluated;
2. the whole `queued → running` guard, which requires a Job whose current Attempt
   holds the execution token — no producer for `execution_token_invalid`;
3. the whole `running → validating` guard, which requires every delivered result to
   come from the current Attempt — no producer for `stale_attempt`;
4. the `ResultPackage` **schema** clause of `validating → published`. PC-01 publishes
   no result package and validates declared checksums and required artifact roles
   directly.

Cancellation and Attempt publication authority are outside PC-01 entirely: no cancel
command exists, so `cancelled` is declared and unreachable.

The suite asserts these guards **absent**, never passing, so it never reports coverage
it does not have.

### 9.3 Contract objects PC-01 does not publish

`JobPackage` and `ResultPackage` both list `attempt_authority` in their top-level
`required` array, and that object requires `run_id`, `job_id`, `attempt_id` and
`execution_token`. PC-01 has no Job and no Attempt, so it publishes neither envelope
and claims no conformance to either schema. Neither contract file is edited.

The one analysis object PC-01 publishes as a contract is the `StageResult`, whose
`required` array contains no `attempt_authority`. PC-01 claims **full** conformance to
that schema and validates every emitted result against it.

### 9.4 Error codes with no PC-01 producer

`execution_token_invalid` and `stale_attempt` — no Job and no Attempt to raise them.

`partial_result_not_publishable` — see §6.

`authentication_required` and `permission_denied` — PC-01 has no authentication and no
role model. They stay in the closed enum; no route emits them.

`required_norm_unavailable` — no norms snapshot is pinned.

`unsupported_contract_version` — the surface carries one contract version.

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
