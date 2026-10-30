# BLOCK4-STAGE-1030 — source-bound global V3 consolidation

UNVERIFIED source candidate. Fresh `windowed-global-v1` comparison adds real cross-batch Consolidator calls after local Dedupe and independent parameter verification. Original events, hints, source quotes and verification results remain retained; grouping is a preliminary machine recommendation, never an expert verdict.

## Changed paths

- New `src/auditmanager/comparison/stage_v3/consolidation.py`.
- New `src/auditmanager/comparison/stage_v3/original_consolidator/{__init__.py,features.py,CONSOLIDATOR_PROMPT.txt,SOURCE.json}`.
- `src/auditmanager/comparison/stage_v3/{policy,bridge,procedures,mode}.py`.
- `src/auditmanager/comparison/stage_ai/runtime.py`: preserve the exact changed-policy refusal code.
- This report.

No StageRun start/batch, UI, ordinary-analysis, shared contract, migration, root lock/dependency, composition-root, global-style, test or fixture file was edited by this lane in BLOCK4. Existing generic accepted-command plumbing carries the new policy without a new API field.

## Genuine cross-batch work

The original local Dedupe still considers bounded eight-event batches. The new planner examines pairs across those batch boundaries, using actual shared native-source identities and bounded subject/page/transition signals. It reuses pure `stems`, `jaccard` and designation extraction from the original Consolidator feature module. A formal candidate is not treated as a merge decision.

Up to 128 ranked candidates enter the explicit global comparison window. All eligible-candidate counts, unplanned/uncompared counts and a digest of excluded candidate IDs are recorded. No original event disappears when its pair is outside the window. This is deliberately not a claim of unrestricted global semantic recall.

New bounded Consolidator requests compare at most four pairs each, or fewer to fit the actual payload. They use the original Consolidator prompt followed by an explicit adaptation to the current closed pair schema. Every requested pair must occur exactly once in the response, with unchanged event IDs. Decisions are `DUPLICATE`, `RELATED`, `SEPARATE`, `NEEDS_CONTEXT`. A duplicate recommendation requires exact quotes from actually supplied native-source passages covering both member events.

Only evidence-bound duplicate recommendations create connected global groups. Before applying an edge, the deterministic layer checks all resulting component members for conflicting typed parameters at the same name/location and for related `SOURCE_CONFLICT` hints. Conflicts keep the original model decision but set `applied_decision=RELATED_CONFLICT`; truncated event/parameter input prevents automatic grouping and sets `NEEDS_CONTEXT`. Original and independently verified values remain separate; there is no arithmetic/unit conversion or expert act.

Global groups join the existing source-partitioned REVIEW card envelopes while preserving all related events, parameter identities, verification records and source anchors. A source-connected envelope can contain several distinct global groups; the manifest lists exact group members rather than declaring every event in a card identical. Fresh display-excerpt metadata is recomputed against the full joined source catalogue. No raw `stage_text_fragment` or deterministic comparison row is rewritten.

## Provenance

Copied from PDF-proverka commit `3c99481719218b9cfa7560886529916646c61939`:

- `backend/app/services/project_change_consolidator/features.py`.
- `backend/app/services/project_change_consolidator/prompts/CONSOLIDATOR_PROMPT.txt`.

The files are copied under `original_consolidator`, with source paths/commit and adaptation limits in `SOURCE.json`. The new bundle hashes the actual copied assets, its implementation and the bounded native-window bundle. No original filesystem, provider, thread/job or storage implementation is imported. Candidate-window rules and the pair-decision schema are authored adaptations, not a claim that the original complete recomposition/channel/hint-disposition runtime has been ported unchanged.

## Frozen authority and consent

`AUDITMANAGER_STAGE_V3_PLAN` accepts `legacy`, `windowed-v1`, `windowed-global-v1`; the fresh default is `windowed-global-v1`. Fresh accepted policy includes the global bundle and limits. Existing start/batch fingerprints remain limited to actual client fields and are replayed before consulting the fresh default. Parent batches retain their accepted policy for children.

The accepted legacy native branch is unchanged. Stored policy readers accept both windowed revisions and continue to expose historical results. Because the earlier windowed bundle explicitly hashes its parser/policy dependencies, this code change causes an older accepted windowed bundle to refuse new paid continuation instead of silently interpreting replies under changed code. The exact failure reason is retained as `v3_windowed_policy_changed_requires_fresh_run`; saved replies are not deleted and read-only history/replay remains available.

The existing one-request-per-explicit-consent fence remains. Resume estimates the exact next known global plan. Existing prior-call, unknown-effect, technical-retry, spend, quota and lease guards remain; no global budget increase or blind resend was added. No Consolidator call is made when there are no candidates. With request-size splitting, 128 pairs can require up to 128 additional calls; the four-pair batch size is not a promise of only 32 calls. Every such call requires its own accepted consent window and remains subject to the existing cost ceiling.

Native bounds remain 64 total pages /240,000 characters /1,600 fragments; encoded request bound remains 240,000 characters including validation metadata. Candidate request packing uses a lower 180,000-character target and explicit refusal for an oversized single pair. Event/parameter/source excerpts sent to the model are marked; full originals remain in the saved manifest. Conflict summaries are bounded and carry explicit counts/truncation flags; their full underlying event and verification data remain retained.

## Consumer JSON seam

Only the global revision adds a `Consolidator` procedure with actual known durable-unit `planned/completed/pending` counts. Legacy and earlier windowed progress do not pretend that this procedure ran.

The final run source report adds:

```text
source_report.global_consolidation = {
  version: 'source-bound-global/1', manifest_sha256,
  coverage: {candidate_pairs, planned_pairs, compared_pairs, not_compared_pairs,
             not_planned_pairs, excluded_pair_ids_sha256, global_semantic_complete:false, ...},
  groups: [{group_id, event_ids}],
  decisions: [{pair_id, event_ids, model_decision, applied_decision, reason,
               source_evidence, typed_conflicts, typed_conflict_count,
               typed_conflicts_truncated, source_conflict_hint_ids, input_truncated}],
  original_events: [...], original_hints: [...], parameter_verifications: [...]
}
```

Original event/hint fields use the existing run-global source-unit namespace; exact paid replies remain immutable in their durable units. Parameter verification records retain the original Miner parameter and separate independent response. A card retains `experimental.original_events` and `experimental.original_hints` for its actual sources, plus `experimental.global_consolidation = {manifest_sha256,group_ids,event_ids,coverage}`. Existing `related_events`, parameters, source catalogue and display-text hashes remain present.

`model_decision` uses the four model enums above. `applied_decision` may additionally be `RELATED_CONFLICT`; it is the deterministic grouping outcome, not an expert decision. `typed_conflicts` contains up to 64 detailed examples with the full count/truncation flag. No value or conflict is resolved by replacing the original data. The UI/export owner received these exact paths and enums before its freeze.

When eligible candidate pairs remain outside the comparison window, final experimental progress reports a partial result. Page-processing coverage and global candidate coverage remain distinct, and global semantic completeness is always false.

## Verification, risks and integration

**No tests, checks, imports/compile, lint, typecheck/build, browser, DB, provider/model calls, Git or fixture work were performed**, as explicitly directed. Static source reads and edits only; no `PASS` or quality benchmark is claimed.

Model/schema behavior, larger-candidate latency/memory, conflict-group behavior and complete runtime integration remain unverified. Candidate ranking can miss source-disjoint paraphrases; the explicit window can omit eligible comparisons. Exact lexical parameter/location keys are conservative and do not establish a complete engineering ontology. The adapted pair stage does not implement all original Consolidator recomposition, parameter-placeholder, channel or location-registry semantics.

The integrator alone publishes the owned source files to `origin/dev`; the owner deploys. No new API/bootstrap/migration seam is needed. Roll back fresh selection through the existing plan switch or forward revert, without reinterpreting saved replies or resending ambiguous provider effects. The lane is frozen after this source-only handback; subsequent implementation requires the next assigned block.
