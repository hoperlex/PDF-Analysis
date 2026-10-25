# Task AR-V3-BETA-MAP-TOOL-01 — offline toolchain from recorded decisions to the six AR scope maps

task_id: AR-V3-BETA-MAP-TOOL-01
status: completed in development candidate (unserved, offline tool)

## Outcome

A deterministic, offline, reviewable tool turns one human **decision file** (what the owner/expert decided for each of C01–C22) into the six canonical scope map byte-strings F1, F2, A1, A2, S1, S2 of the frozen composition (SHA-256 `79396188486c430729213279fb7c1c8fca7c13ede3f3f13388d06d9f93bbb781`), and a validator proves the six maps acceptable before anyone spends time on promotion:

- every map is exactly the canonical JSON that `promotion._checked` requires, with a non-empty, unique `mapped_document_ids`;
- the six `map_sha256` values are distinct (0023's verified-set unique key needs that);
- every C item of a scope appears exactly once, in the frozen order, with its decided mode; a `context_only` item carries no citation branch and no edition evidence; the eight topics the beta policy fixes as `context_only` (C05, C06, C08, C09, C10, C15, C21, C22) can never be upgraded by a decision file;
- the target-only prompt part of each scope, rendered from the supplied paragraph rows, is at most 22,000 characters — refused, never cut;
- nothing is approved by the tool: the summary says `pending_expert` unless the decision file carries a complete attestation, which is only recorded and must name the exact six map digests.

The real decisions, official-edition page evidence, BGE-M3 query vectors and expert signature do not exist in this repository and are not invented here; the tool is exercised with a clearly labelled SYNTHETIC fixture.

## Depends on

- `AR-NORM-MAP-APPROVAL-PREP-01` — completed C01–C22 decision sheet.
- `AR-BETA-AVAILABLE-SOURCE-GATE-01` — completed source policy (`beta_sources.json`, 14 provisional and 8 context-only topics).
- `AR-SIX-RUN-SCOPE-BRIDGE-01` — completed fixed six-group composition.
- `AR-V3-BETA-PROMPT-SEAL-01` — completed sealed v3 beta profile (consumes the 22,000-character part).

## Frozen inputs

- domain contract: `1.4.0` shared contract as in `docs/program/CURRENT_STATE.md`; this task changes none.
- API contract: unchanged.
- analysis/comparison/event contract: unchanged.
- migration head: `0032_ar_v3_run_group`; unchanged.
- base commit: `354a9092c48a5d5f37fe8fe3de60af4b4dff7c88` on `integration/ar-close-1026`.
- source policy digest `9d3b7e53b512fbde1ea478a77a63c3c48042e85ddc50d57c96241c79bcb91d58`, scenario `new_multi_apartment_residential_F1.3`, snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74`.
- map byte rules of `norms/retrieval/{artifact,candidate,evidence_bridge,promotion}.py` and prompt-part rules of `norms/retrieval/ranking.py` (`PROMPT_CHAR_CAP` 22,000, builder `norm-ranking-prep-v1`), read-only.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `analysis` cannot import the norms byte/render helpers; the policy fixes 8 topics context-only; no map, vector or decision artefact exists in the tree; `_checked` requires canonical map bytes.

### P-01 — the norms public surface has no canonical-bytes or renderer name

- captured_at: 2026-10-26
- command: `grep -n "SetIdentity\|PromotionRequest\|canonical_json_bytes\|select_prompt_part" src/auditmanager/norms/public.py`
- captured_output:
  ```text
  159:    PromotionRequest,
  167:from auditmanager.norms.retrieval.artifact import SetIdentity
  210:    "SetIdentity",
  283:    "PromotionRequest",
  ```
- interpretation: `SetIdentity` and `PromotionRequest` are public; `canonical_json_bytes` and `select_prompt_part` are not. The ALR-05 boundary forbids a deep import, so this tool carries a small canonical encoder and a target-only renderer of its own (as `set_input.py` already does for its parser) and a contract test holds both byte-equal to the real functions. A public export would remove the copies.

### P-02 — the policy fixes exactly eight context-only topics

- captured_at: 2026-10-26
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -c "from auditmanager.analysis.profiles.ar_v3.norm_map.beta_sources import load_beta_source_policy as l; p=l(); print(p.sha256); print(sum(i.mode=='provisional_citation' for i in p.items)); print([i.item_id for i in p.items if i.mode=='context_only'])"`
- captured_output:
  ```text
  9d3b7e53b512fbde1ea478a77a63c3c48042e85ddc50d57c96241c79bcb91d58
  14
  ['C05', 'C06', 'C08', 'C09', 'C10', 'C15', 'C21', 'C22']
  ```
- interpretation: the ceiling a decision file may not exceed. A decision may downgrade a provisional topic to context-only, never the reverse.

### P-03 — no map, vector or decision artefact exists at the base

- captured_at: 2026-10-26
- command: `git ls-tree -r --name-only 354a9092c48a5d5f37fe8fe3de60af4b4dff7c88 | grep -E "norm_map/|map\.json|query_vectors|items\.json"`
- captured_output:
  ```text
  contracts/analysis/v1/legacy-stage-map.json
  contracts/analysis/v1/legacy-stage-name-map.json
  src/auditmanager/analysis/profiles/ar_v3/norm_map/__init__.py
  src/auditmanager/analysis/profiles/ar_v3/norm_map/beta_sources.json
  src/auditmanager/analysis/profiles/ar_v3/norm_map/beta_sources.py
  tests/contract/norm_map/test_ar_beta_sources.py
  tests/contract/norm_map/test_beta_status_mirror.py
  ```
- interpretation: the two `legacy-stage-*` files are unrelated stage maps. There is no `map.json`, `items.json` or `query_vectors.json`; the only norm-map files are the sealed source policy and its tests.

### P-04 — promotion refuses non-canonical map bytes

- captured_at: 2026-10-26
- command: `grep -n "canonical_json_bytes(mapping) != request.map_bytes" src/auditmanager/norms/retrieval/promotion.py`
- captured_output:
  ```text
  119:        if not isinstance(mapping, dict) or canonical_json_bytes(mapping) != request.map_bytes:
  ```
- interpretation: a map file must be exactly the canonical encoding (no trailing newline, no indentation) or promotion refuses it; the tool writes the map files byte-exact and re-checks this on every read.

### P-05 — the zero-window render is the smallest prompt part the real selector can return

- captured_at: 2026-10-26
- command: `grep -n "item has no reviewed target span\|for limit in (3, 2, 1, 0)\|raise RankingRefused(\"prompt part remains" src/auditmanager/norms/retrieval/ranking.py`
- captured_output:
  ```text
  198:            raise RankingRefused("item has no reviewed target span")
  280:    for limit in (3, 2, 1, 0):
  284:    raise RankingRefused("prompt part remains above character cap with target rows alone")
  ```
- interpretation: every map item needs a target span (so a context-only topic still carries its context spans), and a target-only part above the cap can never be rescued by the reduction order. The tool's budget check is therefore a necessary condition, not the final one: retrieved windows are only known at promotion.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v3/norm_map/map_pack.py`
- `tests/contract/norm_map/test_map_pack.py`
- `tests/fixtures/ar_v3_map_pack/**`
- `docs/program/tasks/AR-V3-BETA-MAP-TOOL-01.md`
- `docs/program/AR-V3-BETA-MAP-TOOL-01.md`

## Forbidden hotspots

`norm_map/beta_sources.json` and `beta_sources.py` (sealed by tests and mirrored in the web screen), `contracts/**`, `db/migrations/**`, `infra/**`, root dependency/lock files, `src/auditmanager/runs/**`, `src/auditmanager/norms/**`, `src/auditmanager/bootstrap/**`, `web/**`, global styles, `origin/main`, tags.

## Non-goals

No database, S3, corpus or PDF read; no promotion, set, Run or provider call; no choice of target spans, editions or branches (those are the owner's decisions); no verification that a paragraph, edition or page digest is the real official one; no authentication of the expert's signature; no change to the sealed source policy; no served behaviour. The tool refuses to run on the synthetic fixture unless `--allow-synthetic` is given and never produces anything usable as a real map from it.

## Deliverables

- `map_pack.py`: pure `build_scope_maps`, `check_scope_maps`, `validate_scope_maps`, strict `parse_decisions` / `parse_paragraphs`, and a thin CLI (`build`, `validate`; exit 2 on any refusal).
- `tests/fixtures/ar_v3_map_pack/synthetic-decisions.json` and `synthetic-paragraphs.json` (both `"synthetic": true`).
- `tests/contract/norm_map/test_map_pack.py`: 95 tests, every guard shown red under a quoted mutation in the report.
- This task file (the format below) and the operator runbook in `docs/program/AR-V3-BETA-MAP-TOOL-01.md`.

### Formats (all strict: an unknown or missing key is a refusal)

**Decision file** (`ar-beta-map-decisions-v1`): keys `decision_version`, `synthetic` (boolean), `comment` (non-empty text: provenance of the decisions), `identity` {`norms_snapshot_id`, `reviewed_content_key`, `embedding_build` = `bge-m3-dense-v1:characters-v{1,2}:<n>`, `scenario` = the policy scenario}, `query_vectors` {`profile` = `bge-m3-dense-v1`, `model_revision` (40 hex), `sha256_by_scope` (six SHA-256, one per scope)}, `items` (C01–C22 exactly once, any order), optional `review`.

**Item**: `{id, mode, targets}` for `context_only`; `{id, mode, targets, branch, edition_evidence}` for `provisional_citation`. `mode` can only be at most as permissive as the policy. A `target` is `{norm_document_id (ndoc_), designation, edition, kind (clause|table|range), ordinal_first, ordinal_last, norm_paragraph_id_first, norm_paragraph_id_last (npar_)}`; targets are unique and sorted by (document, first, last) — the builder sorts, the validator requires it. `branch` is `{id, applicability}` (the owner's statement of the N/R/P or route branch). `edition_evidence` is a possibly empty list of `{source_id, pages, page_sha256}`; `source_id` must be a text source (official PDF/excerpt or public copy) the policy names for that item, never a card or the local bundle.

**Attestation** (`review`): `{reviewer, capacity, date (YYYY-MM-DD), decision_ref, map_sha256 {six scope -> digest}}`. Partial is refused (never downgraded to pending); the digests must equal the built maps; a synthetic pack cannot be attested. It is recorded in `pack-summary.json` only, so the map digests are the same before and after review.

**Paragraph file** (`ar-beta-map-paragraphs-v1`): `{paragraphs_version, synthetic, norms_snapshot_id, paragraphs: [{norm_document_id, norm_paragraph_id, designation, title, ordinal, clause_number|null, page_label|null, text, reliable}]}`. It must cover at least every target span, carry the pack's snapshot and the same `synthetic` flag. Targets must resolve to the declared first/last paragraph ids, to reliable paragraphs and to the declared designation.

**Map** (`ar-beta-scope-map-v1`, canonical bytes, file `scope-<ID>.map.json`): `map_schema_version`, `scope_id`, `composition_sha256`, `policy_sha256`, `scenario`, `synthetic`, `norms_snapshot_id`, `reviewed_content_key`, `embedding_build`, `query_vectors` {`profile`, `model_revision`, `sha256`}, `mapped_document_ids` (sorted unique union of target documents), `items` (the scope's items in frozen order). `reviewed_content_key`, `norms_snapshot_id`, `embedding_build`, `mapped_document_ids` and `items[].id` are exactly the fields `build_retrieval_set` and `_checked` read; the rest is provenance and scope identity.

**Summary** (`pack-summary.json`, `ar-beta-map-pack-summary-v1`): composition and policy digests, `synthetic`, `review_state` (`pending_expert` | `attestation_recorded`), `review`, the cap, the basis `target_rows_only_zero_retrieved_windows`, and per scope: item ids, `map_sha256`, `map_bytes`, `prompt_part_characters`, `prompt_part_sha256`, provisional / context-only ids and `edition_evidence_missing`.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/norm_map`
- expected: all pass (existing `norm_map` tests plus 95 new).
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/AR-V3-BETA-MAP-TOOL-01.md',encoding='utf-8').read())))"`
- expected: `[]`
- `git diff --check` and the exact allowed-path inventory. No full `make gate` (`R-135`).

## Integration contract

Provider: `python -m auditmanager.analysis.profiles.ar_v3.norm_map.map_pack {build,validate}` and the pure functions above. Consumer: the map owner, who feeds each `scope-<ID>.map.json` byte-exact to `SetIdentity(map_sha256=sha256(file))` and `PromotionRequest.map_bytes`, and the reviewer, who signs the six digests from `pack-summary.json`. The integrator can rely on: output always re-validates; the same decisions give identical bytes; an exit code of 2 means a refusal with a reason code on stderr. The tool never writes into the repository tree on its own and never overwrites an existing pack.

## Failure/idempotency/security cases

Refused with a reason code: duplicate/unknown/missing item, unknown key at any level, upgrade of a policy `context_only` topic, citation fields on a `context_only` item, evidence from a non-text or foreign source, non-canonical or non-NFC bytes, wrong scope/composition/policy/scenario, inconsistent pack identity, duplicate map digests, empty/duplicate/unrelated `mapped_document_ids`, a target that does not resolve to declared reliable paragraphs, an over-cap prompt part (never truncated), synthetic input without `--allow-synthetic`, a non-synthetic pack off the policy snapshot, a partial or stale attestation, an existing output file, a summary that differs from the maps. Re-running with the same inputs is idempotent (identical bytes, same digests).

## Rollback / feature flag

Not applicable: nothing consumes the tool yet. Forward-revert the five files.

## Handoff

- changed files: see the report.
- commands/results: see the report.
- known limits: target-only lower bound; copies of two norms helpers pending a public export; schema carries only the fields the existing builders read; digests and edition labels are recorded, not verified.
- integration notes: see the report's runbook.
