# AR-V3-BETA-MAP-TOOL-01 — decisions to six acceptable scope maps, offline

**Task:** [AR-V3-BETA-MAP-TOOL-01](tasks/AR-V3-BETA-MAP-TOOL-01.md). **Base:** `354a9092c48a5d5f37fe8fe3de60af4b4dff7c88`. **Policy digest:** `9d3b7e53b512fbde1ea478a77a63c3c48042e85ddc50d57c96241c79bcb91d58`. **Composition:** `79396188486c430729213279fb7c1c8fca7c13ede3f3f13388d06d9f93bbb781`.

## Result

`src/auditmanager/analysis/profiles/ar_v3/norm_map/map_pack.py` turns one recorded decision file (C01–C22) plus the supplied paragraph rows into the six canonical maps F1/F2/A1/A2/S1/S2 and a `pack-summary.json`, and re-validates a written pack. It reads no database, calls no model and approves nothing. The summary says `pending_expert`; an expert attestation is only recorded, and only if it names the exact six map digests. Everything is exercised on a **synthetic** fixture (`tests/fixtures/ar_v3_map_pack/`); no real decision, edition page, query vector or signature exists in this repository and none was invented.

What the validator proves before promotion is attempted:

1. each map is the exact canonical encoding `promotion._checked` demands, with non-empty unique `mapped_document_ids` that equal the union of the item targets;
2. the six `map_sha256` values are distinct;
3. every C item of a scope appears once, in frozen order; a `context_only` item has no `branch` / `edition_evidence`; C05, C06, C08, C09, C10, C15, C21 and C22 cannot be upgraded;
4. each target resolves to the declared first/last `npar_`, to reliable paragraphs and to the declared designation;
5. the target-only prompt part of each scope is at most 22,000 characters (checked with `scope_partition.validate_rendered_scope`; a longer part is refused, never cut);
6. `review_state` is `pending_expert` unless a complete attestation is supplied.

## Operator runbook

### What the owner/expert must supply (every input is missing today)

| Input | Present in repo? | Who | How the tool consumes it |
| --- | --- | --- | --- |
| Per-item decision: `mode`, `branch.applicability`, target spans (`ndoc_`, designation, edition label, `npar_` first/last, ordinals, kind) for all 22 items | No: the sheet `AR-NORM-MAP-APPROVAL-PREP-01` lists candidates only | Owner / qualified expert | `decisions.json` `items`; copied into the maps, sorted, checked against the policy modes |
| Official edition page evidence per provisional item (page SHA-256, pages, source id) | No: the edition audit found no fully confirmed D1–D6 edition | Owner / expert | `edition_evidence`, optional; recorded verbatim, listed as `edition_evidence_missing` in the summary when empty; source must be a text source the policy names for that item |
| Paragraph rows of the target spans from the promotion database (id, designation, title, ordinal, clause, page, text, reliability) | No exporter exists in this lane's paths; the local promotion DB has the rows | Map owner (read-only export, outside this tool) | `--paragraphs`; used to resolve targets and measure the prompt part |
| Snapshot identity: `ns_` id, reviewed content key, embedding build `bge-m3-dense-v1:<chunking profile>` | The policy pins the snapshot id only | Map owner | `identity`; a non-synthetic pack must sit on the policy snapshot |
| BGE-M3 query vectors (one artefact per scope) and their provenance | No: the BGE image is absent locally; the artefact format is only described in `W57-PLAN` §A3.1 | Map owner via `norms.embedding embed-texts` | `query_vectors`: profile, model revision, six SHA-256. **Recorded, not read**: the tool never opens a vector file |
| Expert signature | No | Qualified expert | `review` {reviewer, capacity, date, `decision_ref`, six map digests}; recorded, **not authenticated**; the signed record lives outside the tool at `decision_ref` |

### Procedure

1. Copy the shape of `tests/fixtures/ar_v3_map_pack/synthetic-decisions.json`, set `"synthetic": false`, replace every field with the real decision (the `comment` states where the decision is recorded). Build the paragraph file the same way.
2. Build the pending pack (it refuses to write into an existing file):
   `PYTHONPATH=src python -m auditmanager.analysis.profiles.ar_v3.norm_map.map_pack build --decisions decisions.json --paragraphs paragraphs.json --out pack/`
3. The expert reviews `pack-summary.json` (six digests, character counts, `edition_evidence_missing`) and the six `scope-<ID>.map.json` files.
4. To record the review, add `review` with the six digests to the decision file and build again into a new directory. The digests stay the same; `review_state` becomes `attestation_recorded`. Editing any decision changes a digest and invalidates the attestation.
5. Re-check any pack at any time: `... map_pack validate --maps pack/ --paragraphs paragraphs.json`. Exit 0 means valid; exit 2 prints `REFUSED: <code>`.
6. Hand-off to promotion (a separate task): the file bytes are the `map_bytes`, `sha256(file)` is `SetIdentity.map_sha256`; do not reformat or add a trailing newline.

`--allow-synthetic` is for the fixture only; a real run omits it and is refused if either file says `"synthetic": true`.

### Common refusal codes

`item_missing:` / `item_duplicate:` / `item_unknown`, `context_only_upgrade_refused:Cnn`, `context_only_carries_citation:Cnn`, `item_keys_invalid:Cnn`, `target_not_in_paragraphs:Cnn`, `target_paragraph_unreliable:Cnn`, `prompt_part_over_cap:<scope>:<n>><cap>`, `map_not_canonical:<scope>`, `map_digests_not_distinct`, `snapshot_not_policy_snapshot`, `synthetic_refused`, `attestation_incomplete`, `attestation_map_digest_mismatch`, `output_exists`, `summary_differs_from_maps`.

## Verification

All run from the lane directory with `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider`:

- `tests/contract/norm_map`: **102 passed** (7 existing + 95 new). The new file also drives the real oracles: `select_prompt_part` (the tool's render is byte-equal, with SHA-256 compared), `build_retrieval_set` plus `parse_v3_set_input` and `prepare_v3_prompt` for all six synthetic maps, `promotion._checked`, and `canonical_json_bytes` (encoder parity, including refusals).
- Boundary guard `tests/contract/architecture/test_alr05_boundaries.py`: red on this base for two imports in `src/auditmanager/workers/__main__.py` (`executors.operations`, `executors.runtime`), which this task does not touch; `map_pack.py` contributes no violation.
- Task governance check prints `[]`. `tests/contract/program/test_wave_governance.py` is otherwise red on this base (`test_every_task_added_after_governance_activation_satisfies_the_rules`: 17 earlier `AR-V3-BETA-*` task files lack a premise output block); `AR-V3-BETA-MAP-TOOL-01` is not among them.

### Mutation probes (single edit, run `tests/contract/norm_map/test_map_pack.py -x`, then revert)

All 50 probes went red; none survived. Failing test in brackets.

- Totality: missing, duplicate and unknown item not refused (M01–M03) [`test_every_item_c01_to_c22_must_be_decided_exactly_once`]; targets/evidence not sorted (M04) [`test_build_is_deterministic_and_independent_of_input_order`].
- Bytes and digests: round-trip check removed (M05) [`test_map_bytes_must_be_exactly_the_canonical_encoding`]; distinctness disabled (M06) [`test_the_six_map_digests_must_be_distinct`]; scope set/order (M48), policy digest (M50), scenario (M41) unchecked; pack identity may differ (M44); query-vector profile unpinned (M45); mapped ids not tied to targets (M28) or duplicates tolerated (M29).
- Modes: `context_only` upgrade allowed (M07) [`test_a_context_only_item_can_never_be_upgraded_by_the_decision_file[C05]`]; citation fields on `context_only` (M08); provisional without branch (M09); evidence from a foreign or non-text source (M10, M11).
- Strict shapes: unknown key in map (M12), target (M13), decisions (M14), paragraph row (M42); duplicate paragraph rows (M43); duplicate JSON keys (M38); NaN (M39); targets/evidence unsorted or duplicated (M46, M47).
- Synthetic and review: synthetic accepted without the flag (M15); non-boolean flag (M40); off-policy snapshot (M16); partial attestation tolerated (M17); attestation not bound to the digests (M18); synthetic pack attested (M19); `review_state` inferred as attested (M20); missing evidence hidden in the summary (M49).
- Targets and budget: unreliable paragraph (M21), first id (M22), last id (M23), missing in-span paragraph (M24), designation (M25), paragraph-file snapshot (M26) and synthetic flag (M27) unchecked; over-cap part truncated instead of refused (M30) [`test_prompt_part_of_exactly_22000_characters_passes_and_one_more_is_refused_untruncated`].
- Drift against the real functions: label numbering (M31), builder version (M32) [`test_every_map_and_its_prompt_part_pass_the_real_set_builder_and_v3_material`]; `ensure_ascii` (M33) [`test_canonical_encoder_is_byte_equal_to_the_norms_encoder`].
- CLI: exit code 1 instead of 2 (M34); existing output not detected (M35); summary not compared with the maps (M36); `python -m` entry removed (M37).

## Known limitations and integrator notes

- **Lower bound only.** The check renders target rows with zero retrieved windows, the smallest part `select_prompt_part` can return (`prompt_part_basis` in the summary). Retrieved windows and real query vectors are only known at promotion, where the real selector still decides; a pack that passes here can be refused there, never the reverse.
- **Two copies pending a public export.** `analysis` may import only `norms.public`, which exports `SetIdentity` and `PromotionRequest` but neither `canonical_json_bytes` nor `select_prompt_part`. The tool therefore carries a canonical encoder and a target-only renderer; the contract test is the drift guard. A `norms.public` export (norms context, outside this lane) would let both copies go.
- **No public map validator.** `norms` exposes none, so the contract tests call the private `promotion._checked` and `build_retrieval_set` directly as the oracle (tests are outside the ALR-05 scan); a public byte-check would let the tool drop its own copy.
- **Minimal schema.** The map carries what `build_retrieval_set`, `_checked` and the evidence bridge read, plus branch/evidence provenance. The `W57-PLAN` §A3.1 fields that no builder reads (item category, Russian check text, query text, legacy provenance SHA, excluded list, `items_sha256`) are not carried; a later map-owner slice can extend `map_schema_version`.
- **Recorded, not verified:** edition labels, page digests, query-vector digests, `reviewed_content_key` and the signature. The tool checks form and consistency only.
- **Not run:** no DB, container, promotion or live check (none needed). Every test here is container-free; there are no skipped or unrunnable tests. Full gate is deferred by `R-135`.
- Merge order: independent of the other lanes (five new paths, nothing shared). Rollback: forward-revert the five files.
