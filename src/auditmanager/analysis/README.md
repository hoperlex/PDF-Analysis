# `analysis` boundary

The stage engine and the three deterministic preparation stages of `P2-ENG-01`.

```python
from auditmanager.analysis.public import run_stage, StageStatus, document_text

result = run_stage(
    "source_preparation",
    version_uid=version_uid,          # a DocumentVersion identity, never allocated here
    inputs={"source.document": blob_id},
    blob_store=store,
)
assert result.status is StageStatus.SUCCEEDED
text_layer_blob = result.artifact("prepared.text_layer").blob_id
```

## The offset rule — read this before anything else

`prepared.text_layer` defines **one document-global character sequence**: every page's
text concatenated in ascending page order, **with no separator between pages**. Every
offset in this system — evidence anchors, block spans, the grounding gate — indexes
that one sequence, and `document_text()` is its single implementation.

Offsets are **Unicode code points** after the declared normalization. Not bytes, not
UTF-16 code units. `text[char_start:char_end]` on the concatenated sequence is the
definition, and **an `.encode()` anywhere near an offset calculation is the bug**.

The corpus is Russian, so this is measurable rather than a matter of care: the baseline
document is 3 740 code points and 6 621 UTF-8 bytes. A byte-offset implementation
misplaces every anchor while still looking plausible in a test written in English.
`tests/integration/analysis_engine/test_preparation_stages.py::test_offsets_are_code_points_and_not_bytes`
and `::test_manifest_quotations_resolve_at_their_declared_pages` are the two tests that
catch it; under a byte-offset mutation the second reports `0 == 12` quotations resolved.

Normalization is `nfc_v1`, applied **once**, by `source_preparation`, and declared in
`text_layer.normalization.id`. **No later stage normalizes again.** `B4`'s grounding
gate compares exactly, after that one normalization and nothing else, so `B3` must not
normalize model output before writing an anchor.

## What is here

| Module | What it owns |
|---|---|
| `engine/registry.py` | The stage registry loader. Canonical identity and version are read from `contracts/analysis/v1/stage-registry.json`; an unknown stage is refused, and no legacy alias is resolved. |
| `engine/result.py` | `StageResult`, `ArtifactRef`, `StageError`. Maps onto `stage-result.schema.json` and onto nothing else. |
| `engine/runner.py` | `run_stage`: the in-process seam, with the fail-closed mapping. |
| `engine/serialization.py` | Canonical JSON. The one legitimate `.encode()` in the package. |
| `ports/artifacts.py` | Artifact roles, the `artifact_role`/`artifact_version` envelope, publication through `BlobStore`. |
| `ports/stage.py` | `StageContext` and `StageProduction`, the stage seam. |
| `stages/extraction.py` | The pinned `pdfplumber` extraction and the single normalization. |
| `stages/*.py` | The three stage implementations. |

`src/auditmanager/analysis/text/**` is **not** part of this task. It belongs to
`P2-AI-01`, which registers `text_analysis` on this same seam.

## The stage-runner signature

```python
def run_stage(
    stage_id: str,
    *,
    version_uid: str,
    inputs: Mapping[str, BlobId],     # registry input role -> blob_id
    blob_store: BlobStore,
    handler: StageHandler | None = None,   # defaults to the registered implementation
    registry: StageRegistry | None = None,
    clock: Clock = _utc_now,
) -> StageResult
```

It requires **no attempt authority**, and it constructs **no `JobPackage` and no
`ResultPackage`**. Those envelopes carry attempt authority because they exist to cross
a *remote dispatch* boundary, and `PC-01` does not dispatch remotely. `StageContext`
has no field in which an attempt id, execution token, lease or worker identity could be
carried, and a contract test asserts that neither package name is defined or
constructed anywhere in this package.

`stage_id` must be **canonical**. The registry's `alias_resolution` rule puts legacy
name resolution at the control plane's boundary and says the engine never accepts a
legacy name; there is no alias table here to consult.

## The fail-closed mapping

Three guards run around every handler:

1. **Before.** Every registry-required input role must be supplied. A missing one is
   `failed` with `analysis_input_invalid`, and the handler is never entered.
2. **The handler.** It returns, or it raises `DomainError`. A raise is `failed`
   carrying that error's own catalog code — there is no second error type in this
   package.
3. **After.** Every registry-required output role must be present. A missing one is
   `failed` with `analysis_failed` *even though the handler returned normally*.

`partial` and `skipped` are **structurally impossible** for these three stages.
`StageProduction` carries artifacts and metrics and has no status field, so no handler
return value maps to `partial`; two outcomes in, two statuses out. `assert_status_allowed`
additionally refuses any status the stage's registry `status_policy` forbids, so a
future caller reaching past the runner is refused by the policy rather than by a
comment.

A `failed` result carries **no artifact reference**, and an unreadable source publishes
nothing.

## The artifact shapes

All four carry `artifact_role` and `artifact_version` at their root, and a consumer
reading an unexpected `artifact_version` **fails closed**. Shapes are `P02_SEAMS`
sections 4.2 to 4.6 verbatim.

* **`prepared.page_inventory`** — `page_count` and, per page, `page_number` (1-based,
  contiguous), `width_pt`, `height_pt`, `rotation_deg`, `has_text_layer`, `char_count`.
  `has_text_layer` is `true` for every page or nothing is published: a page with no
  extractable embedded text is refused with `validation_failed`, and OCR is never
  silently substituted.
* **`prepared.text_layer`** — `extractor`, `normalization`, `total_char_count` and the
  per-page `char_start`/`char_end`/`text` spans. See the offset rule above.
* **`geometry.block_index`** — one block per extracted line, `block_id` matching
  `^b_[0-9]{6}$` assigned in `(page_number, block_ordinal)` order from `b_000001`.
  `bbox_unit` is `pt` and `bbox_origin` is `top_left` with y increasing downwards,
  after rotation. `text_layer_sha256` binds the artifact to the exact text layer its
  spans were computed against, and consumers **must** check it — a longer document's
  text layer can hold every one of those offsets and still be entirely different text,
  so a span that resolves is not evidence that it resolves to the right characters.
  **`block_id` is not a contract identifier**: it is an anchor inside one artifact,
  never a foreign key, and it never crosses a version boundary.
* **`geometry.page_crops`** — present, schema-valid and explicitly empty under a
  declared `crop_policy: none`, echoed in the metrics as `crop_policy=none` and
  `crop_count=0`.
* **`context.document_graph`** — `sections`, `references` and `neighbourhood` over
  stable block identities, bound by `block_index_sha256`.

## The page-crop policy actually implemented

`crop_policy: none`, with an empty `crops` list — `OD-04` as fixed in `P02_SEAMS`
section 4.5. `PC-01` does no visual detection, and the registry marks the role a
required output of a stage that allows neither `partial` nor `skipped`, so the role is
present and explicitly empty rather than absent. Its only contract consumer,
`block_analysis`, is out of `PC-01` scope and would fail closed on an empty list rather
than degrade.

**Flip condition, carried from `OD-04`:** if any task adds a content schema for the
crop manifest, this decision reopens.

## The document graph is a convenience, never evidence

`B3` uses it to build the prompt neighbourhood. The grounding gate resolves against
the text layer and the block index **only**, so nothing in the graph is an anchor of
record. Its three rules are deterministic and derived from the published artifacts
alone:

* **Heading** — a block opening with dotted-decimal numbering whose cased letters are
  at least 80% upper case. Font size would discriminate better but is not in the block
  index, whose shape section 4.4 fixes; deriving the graph from what a consumer can
  actually see keeps it reproducible from the seam. *Declared limitation:* a
  mixed-case heading is not recognised and its blocks fall to the preceding section.
* **Front matter** — blocks preceding the first heading belong to a synthetic section
  titled from the first of them, so assignment is total: every block belongs to exactly
  one section.
* **References** — `continuation` for a block whose predecessor ended mid-sentence and
  which does not open a numbered clause; `cross_reference` for a block naming a
  section, clause or table number whose leading component is an existing section;
  `table_caption` and `figure_caption` for a block opening `Таблица N` or `Рисунок N`.
  Every emitted reference resolves; one that would not is not emitted.

## Determinism

Same bytes plus same extractor plus same options gives the same offsets, and a change
to any of the three is a new `artifact_version`. `extractor.options_sha256` records the
options. Artifacts are serialized by `canonical_bytes` — sorted keys, no insignificant
whitespace, `ensure_ascii=False` — so two runs over one source publish byte-identical
text layer and block index bytes, and `blob_id` is derived from `(sha256, size)` so a
rerun resolves to the same identity.

## Notes for the sessions downstream

* The engine writes **no canonical metadata row**. `P2-RUN-01` owns persistence; a test
  takes the row count of every public table before and after a stage run and requires
  it unchanged.
* Artifact references are content-addressed only. There is no `bucket`, `key`, `uri`,
  `url`, `path` or credential field, and a test asserts no reference value contains a
  `/`, `\` or `://` outside `role` and `media_type`.
* `pdfplumber`'s `extract_text()` collapses runs of spaces, so the published page text
  is **not** byte-identical to `baseline.page_text_sha256` in
  `fixtures/synthetic/ar/expected_issues.json`, which records the reference extractor's
  output. The divergence is confined to the trailing footer line of each page, after
  every declared anchor, so all twelve quotations still resolve at their declared page
  offsets. Do not assert `page_text_sha256` against this text layer.
