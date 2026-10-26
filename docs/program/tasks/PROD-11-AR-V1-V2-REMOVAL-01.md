# Task PROD-11-AR-V1-V2-REMOVAL-01 — АР v1 and v2 are removed from the server, the contract, the web and the tests; the journey marks what has no АР source

task_id: PROD-11-AR-V1-V2-REMOVAL-01
status: in progress (see the report for the state of each stage)

## Outcome

`startRun` and `reauditRun` on a version classified АР answer the existing `section_profile_unavailable`; `AR_TEXT_PROFILE`, the АР entry of the text-profile registry, the silent `text_profile = AR_TEXT_PROFILE` default of `runs/executor.py` and the whole recorded v2 path are gone; `listAnalysisProfiles` returns `profile: null` for АР; `AnalysisProfileStatus.builtin` and the АР v2 prose are gone from the contract (one reseal, with the `reviewed` description corrected, `D-223`); the web sends an АР version to the v3 control; the tests of the removed paths are deleted and no surviving test is weakened; the 33 АР-bound journey steps carry an explicit `pending_v3_activation` mark that the conformance tests enforce. Derived from `ADR-0024` section 2 (`AD-12`, `R-146g`, `R-146l`, `R-146m`, `R-146w`) and `D-223`.

## Depends on

- `PROD-10-AR-V2-EXTRACT-01` — completed (what v3 needs moved to `analysis/profiles/ar_shared`).
- `PROD-10B-JOURNEY-REBASE-01` — completed (the journey runs on ПБ; 33 steps are АР-bound).
- `PROD-11A-V3-TEXT-LAYER-PROBE-01`, `PROD-11B-V3-STAGE-ID-MIGRATION-01`, `PROD-11C-RECORDED-COST-01` — completed (`D-222`, `D-225`: a v3 Run publishes and leaves the saved text layer).

## Frozen inputs

- domain contract: `1.6.0` (families move with the API document, see P-03)
- API contract: `1.6.0`, 92 paths, 104 operations, 301 schemas; this lane owns the one reseal of the wave
- analysis/comparison/event contract: `1.6.0` literals only
- migration head: `0033_ar_v3_cite_stage_id`, untouched
- base commit: `1c8d29fa` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

(No path, operation, schema, error code or migration is added or removed; one enum member, `AnalysisProfileStatus.builtin`, is removed from a response-only enum. `FindingCategory` and the stage ids are unchanged, `AD-12`.)

## Captured premise evidence

- premise: see P-01 to P-08; P-05 differs from the brief (the v1 recordings are read by more than АР v1), P-03 raises a contract-version conflict (four literals in a forbidden hotspot). Both are decided in "Decisions of the lane" and neither stops the work.

### P-01 — the files the removal touches

- captured_at: 2026-10-26
- command: `for t in AR_TEXT_PROFILE ar_v2 recorded_v2 v2_publication v2_recorded builtin; do echo "## git grep -l -F $t"; git grep -l -F "$t" -- src tests web/src web/tests web/openapi contracts tools scripts fixtures Makefile; done`
- captured_output:
  ```text
  ## git grep -l -F AR_TEXT_PROFILE
    fixtures/recorded/sections/ar_specification/build_fixtures.py
    fixtures/recorded/text_analysis/build_fixtures.py
    scripts/recovery/synthetic_drill_seed.py
    src/auditmanager/analysis/public.py
    src/auditmanager/analysis/text/__init__.py
    src/auditmanager/analysis/text/profile.py
    src/auditmanager/analysis/text/profile_registry.py
    src/auditmanager/analysis/text/stage.py
    src/auditmanager/runs/executor.py
    tests/integration/analysis/test_ar_v2_prompt_material.py
    tests/integration/analysis/test_ar_v2_registered_profile.py
    tests/integration/analysis/test_ar_v3_profile_seal.py
    tests/integration/analysis/test_observations_artifact_rules.py
    tests/integration/analysis/test_profile_identity_is_pinned.py
    tests/integration/analysis_text/test_live_adapter_shape.py
    tests/integration/analysis_text/test_model_identity.py
    tests/integration/analysis_text/test_profile_and_artifact.py
    tests/integration/analysis_text/test_provider_modes.py
    tests/integration/composition/test_analysis_profiles_over_http.py
    tests/integration/optimisation/test_ar_specification_journey.py
    tests/integration/p02_journey/journey.py
    tests/integration/p02_journey/test_explicit_failures.py
    tests/integration/p02_journey/test_manifest_role_seam.py
    tests/integration/p02_journey/test_retry_provenance_seam.py
    tests/integration/p02_journey/test_truncated_end_to_end.py
    tests/integration/p02_journey/test_ungrounded_diagnostic_path.py
    tests/integration/p02_journey/test_whole_journey_idempotency.py
    tests/integration/runs/test_classification_correction_over_http.py
    tests/integration/runs/test_full_chain.py
    tests/integration/runs/test_v2_recorded_executor.py
    tests/integration/runs/test_v3_execution_guard.py
    tests/integration/runs/test_w59_routed_execution.py
    tests/integration/runs/test_w59_section_routing_over_http.py
    tests/integration/sections/test_section_recordings.py
    tests/replay/text_analysis/test_replay_determinism.py
    tests/unit/analysis/test_text_profile_registry.py
  ## git grep -l -F ar_v2
    fixtures/evaluation/ar_v2/bundles/ar_v2_01.zip
    fixtures/evaluation/ar_v2/bundles/ar_v2_02.zip
    fixtures/evaluation/ar_v2/bundles/ar_v2_03.zip
    fixtures/evaluation/ar_v2/bundles/ar_v2_04.zip
    fixtures/evaluation/ar_v2/bundles/ar_v2_05.zip
    fixtures/evaluation/ar_v2/bundles/ar_v2_06.zip
    fixtures/evaluation/ar_v2/bundles/ar_v2_07.zip
    fixtures/evaluation/ar_v2/bundles/ar_v2_08.zip
    fixtures/evaluation/ar_v2/bundles/ar_v2_09.zip
    fixtures/evaluation/ar_v2/bundles/ar_v2_10.zip
    fixtures/evaluation/ar_v2/expected_issues.json
    src/auditmanager/analysis/profiles/ar_shared/__init__.py
    src/auditmanager/analysis/profiles/ar_shared/v2_identities.py
    src/auditmanager/analysis/profiles/ar_v2/merge_input.py
    src/auditmanager/analysis/profiles/ar_v2/prompt_material.py
    src/auditmanager/analysis/profiles/ar_v2/proposal_grounding.py
    src/auditmanager/analysis/profiles/ar_v2/recorded_artifact.py
    src/auditmanager/analysis/profiles/ar_v2/recorded_call.py
    src/auditmanager/analysis/profiles/ar_v2/recorded_input.py
    src/auditmanager/analysis/profiles/ar_v2/recorded_request.py
    src/auditmanager/analysis/profiles/ar_v2/recorded_response.py
    src/auditmanager/analysis/profiles/ar_v2/recorded_stage_result.py
    src/auditmanager/analysis/profiles/ar_v2/registered.py
    src/auditmanager/analysis/profiles/ar_v2/response.py
    src/auditmanager/analysis/profiles/ar_v2/response_pipeline.py
    src/auditmanager/analysis/public.py
    src/auditmanager/executors/answers.py
    tests/contract/evaluation/test_bridge.py
    tests/contract/evaluation/test_matcher_core.py
    tests/contract/fixtures_seeded/test_ar_v2_seeded.py
    tests/integration/analysis/test_ar_v2_merge_input.py
    tests/integration/analysis/test_ar_v2_profile_content.py
    tests/integration/analysis/test_ar_v2_prompt_material.py
    tests/integration/analysis/test_ar_v2_proposal_grounding.py
    tests/integration/analysis/test_ar_v2_recorded_artifact.py
    tests/integration/analysis/test_ar_v2_recorded_call.py
    tests/integration/analysis/test_ar_v2_recorded_input.py
    tests/integration/analysis/test_ar_v2_recorded_request.py
    tests/integration/analysis/test_ar_v2_recorded_response.py
    tests/integration/analysis/test_ar_v2_recorded_stage_result.py
    tests/integration/analysis/test_ar_v2_registered_profile.py
    tests/integration/analysis/test_ar_v2_response_parser.py
    tests/integration/analysis/test_ar_v2_response_pipeline.py
    tests/integration/analysis/test_ar_v2_response_schema.py
    tests/integration/analysis/test_ar_v3_prompt_material.py
    tests/integration/analysis/test_ar_v3_response_schema.py
    tests/integration/evaluation/test_local_bundle.py
    tests/integration/evaluation/test_run_sources.py
    tests/integration/findings/test_analysis_public_boundary.py
    tests/integration/findings/test_merge_publication_plan.py
    tests/integration/findings/test_v2_publication_sql.py
    tests/integration/findings/test_v2_recorded_chain.py
    tests/integration/findings/test_v2_recorded_saved_plan.py
    tests/integration/runs/test_v2_recorded_durable_stage.py
    tests/integration/runs/test_v2_recorded_executor.py
    tests/integration/runs/test_v2_recorded_merge_stage.py
    tests/unit/analysis/test_ar_v3_independent_of_ar_v2.py
    tests/unit/executors/test_runner_answers.py
    tools/evaluation/bridge.py
    tools/evaluation/matcher.py
    tools/evaluation/run_sources.py
    tools/fixtures/seeded/cases.py
    tools/fixtures/seeded/generate.py
  ## git grep -l -F recorded_v2
    src/auditmanager/analysis/profiles/ar_v2/recorded_input.py
    src/auditmanager/analysis/profiles/ar_v2/recorded_stage_result.py
    src/auditmanager/analysis/public.py
    src/auditmanager/findings/v2_recorded.py
    src/auditmanager/runs/executor.py
    src/auditmanager/runs/recorded_v2_merge.py
    src/auditmanager/runs/recorded_v2_publication.py
    src/auditmanager/runs/recorded_v2_sources.py
    src/auditmanager/runs/recorded_v2_stage.py
    tests/integration/analysis/test_ar_v2_recorded_artifact.py
    tests/integration/analysis/test_ar_v2_recorded_call.py
    tests/integration/analysis/test_ar_v2_recorded_input.py
    tests/integration/analysis/test_ar_v2_recorded_response.py
    tests/integration/analysis/test_ar_v2_recorded_stage_result.py
    tests/integration/findings/test_v2_recorded_chain.py
    tests/integration/jobs/test_recorded_v2_executor_bridge_db_accept.py
    tests/integration/jobs/test_recorded_v2_publication_gate.py
    tests/integration/p02_journey/test_ungrounded_diagnostic_path.py
    tests/integration/runs/test_recorded_v2_sources.py
    tests/integration/runs/test_v2_recorded_durable_stage.py
    tests/integration/runs/test_v2_recorded_executor.py
    tests/integration/runs/test_v2_recorded_executor_bridge.py
    tests/integration/runs/test_v2_recorded_merge_stage.py
    tests/unit/analysis/test_ar_v3_independent_of_ar_v2.py
  ## git grep -l -F v2_publication
    src/auditmanager/findings/public.py
    src/auditmanager/findings/v2_publication.py
    src/auditmanager/findings/v2_recorded.py
    src/auditmanager/runs/executor.py
    tests/contract/evaluation/test_bridge.py
    tests/integration/findings/test_analysis_public_boundary.py
    tests/integration/findings/test_v2_publication_sql.py
    tests/integration/findings/test_v2_recorded_chain.py
    tests/integration/jobs/test_recorded_v2_publication_gate.py
    tests/integration/p02_journey/test_ungrounded_diagnostic_path.py
    tests/integration/runs/test_v2_recorded_executor_bridge.py
  ## git grep -l -F v2_recorded
    tests/integration/analysis/test_ar_v2_recorded_stage_result.py
    tests/integration/findings/test_v2_recorded_chain.py
    tests/integration/findings/test_v2_recorded_saved_plan.py
    tests/integration/jobs/test_recorded_v2_executor_bridge_db_accept.py
    tests/integration/runs/test_v2_recorded_durable_stage.py
    tests/integration/runs/test_v2_recorded_merge_stage.py
  ## git grep -l -F builtin
    contracts/api/v1/openapi.json
    src/auditmanager/analysis/text/profile_registry.py
    src/auditmanager/api/routers/analysis_profiles.py
    src/auditmanager/api/schemas/models.py
    src/auditmanager/bootstrap/adapters.py
    tests/e2e/pc01/journey/manifest.json
    tests/integration/analysis_text/test_live_adapter_shape.py
    tests/integration/composition/test_analysis_profiles_over_http.py
    tests/unit/analysis/test_text_profile_registry.py
    tests/unit/analysis/text_profiles/section_profile_expectations.json
    tests/unit/analysis/text_profiles/test_section_profile_expectations.py
    tests/unit/executor_runner/test_workspace.py
    tests/unit/scripts/test_manual_scan.py
    web/openapi/openapi.json
    web/src/entities/analysis-profile/model/presentation.ts
    web/src/shared/api/generated/operations.gen.ts
    web/src/shared/api/generated/types.gen.ts
    web/src/widgets/analysis-profile-table/ui/analysis-profile-table.tsx
    web/tests/guards/rendered-language.guard.test.ts
    web/tests/unit/analysis-settings/analysis-settings.test.ts
    web/tests/unit/styles/screens.ts
  ```
- interpretation: the sets overlap (a file that names `ar_v2` often names `AR_TEXT_PROFILE`); counts by term are 36, 63, 24, 11, 6 and 21 files. `builtin` also matches unrelated Python `builtins` and the word in shell comments. The contract and web hits are the ones this lane edits; `tools/` and `scripts/` hits are the two groups outside the brief's allowed paths (decisions D-5 and D-6 below). The count in `ADR-0024` (65 test files) is of the same order: this tree has 28 test files naming `ar_v2` and 27 naming `AR_TEXT_PROFILE` (+ the `recorded_v2`, `v2_publication` and `v2_recorded` files), and a further group that calls `execute_run` or `run_text_analysis` without naming a profile and so relies on the removed default (P-04).

### P-02 — nothing that survives imports a removed module (AST import graph, as `PROD-10` did)

- captured_at: 2026-10-26
- command: `python3 graph.py .` (scratch, not committed: `ast` only; the removed set is `analysis/profiles/ar_v2/**`, `runs/recorded_v2_{merge,publication,sources,stage}.py`, `findings/{v2_publication,v2_recorded,recorded_saved_plan,merge_publication_plan}.py`, `analysis/stages/finding_merge.py`; it lists every module of `src`, `tests`, `tools`, `scripts` outside that set that imports a member of it, directly or by `from package import submodule`)
- captured_output:
  ```text
  src/auditmanager/analysis/public.py [(49, 'auditmanager.analysis.profiles.ar_v2.merge_input', 'MergePreparation'), (49, 'auditmanager.analysis.profiles.ar_v2.merge_input', 'prepare_merge'), (50, 'a...
  src/auditmanager/findings/public.py [(19, 'auditmanager.findings.recorded_saved_plan', 'SavedRecordedPublicationPlan'), (19, 'auditmanager.findings.recorded_saved_plan', 'plan_recorded_saved_public...
  src/auditmanager/runs/executor.py [(1135, 'auditmanager.runs.recorded_v2_stage', 'run_recorded_v2_stage'), (1136, 'auditmanager.runs.recorded_v2_merge', 'run_recorded_v2_merge_stage'), (1137, 'audi...
  tests/contract/evaluation/test_bridge.py [(15, 'auditmanager.analysis.profiles.ar_v2.proposal_grounding', 'GroundedProposal'), (15, 'auditmanager.analysis.profiles.ar_v2.proposal_grounding', 'Rejec...
  tests/integration/analysis/test_ar_v2_merge_input.py [(7, 'auditmanager.analysis.profiles.ar_v2.merge_input', 'prepare_merge'), (8, 'auditmanager.analysis.profiles.ar_v2.proposal_grounding', 'Groun...
  tests/integration/analysis/test_ar_v2_profile_content.py [(13, 'auditmanager.analysis.profiles.ar_v2.response_schema', 'CATEGORIES')]
  tests/integration/analysis/test_ar_v2_prompt_material.py [(10, 'auditmanager.analysis.profiles.ar_v2.prompt_material', 'PromptMaterialError'), (10, 'auditmanager.analysis.profiles.ar_v2.prompt_mate...
  tests/integration/analysis/test_ar_v2_proposal_grounding.py [(7, 'auditmanager.analysis.profiles.ar_v2.proposal_grounding', 'ground_proposals'), (9, 'auditmanager.analysis.profiles.ar_v2.response',...
  tests/integration/analysis/test_ar_v2_recorded_artifact.py [(13, 'auditmanager.analysis.profiles.ar_v2.merge_input', 'prepare_merge'), (14, 'auditmanager.analysis.profiles.ar_v2.proposal_grounding'...
  tests/integration/analysis/test_ar_v2_recorded_call.py [(13, 'auditmanager.analysis.profiles.ar_v2.recorded_call', 'RecordedCallFactsError'), (13, 'auditmanager.analysis.profiles.ar_v2.recorded_cal...
  tests/integration/analysis/test_ar_v2_recorded_input.py [(12, 'auditmanager.analysis.profiles.ar_v2.recorded_input', 'PdfPageSource'), (12, 'auditmanager.analysis.profiles.ar_v2.recorded_input', 'R...
  tests/integration/analysis/test_ar_v2_recorded_request.py [(12, 'auditmanager.analysis.profiles.ar_v2', 'prompt_material'), (12, 'auditmanager.analysis.profiles.ar_v2', 'registered'), (14, 'auditma...
  tests/integration/analysis/test_ar_v2_recorded_response.py [(13, 'auditmanager.analysis.profiles.ar_v2.recorded_input', 'prepare_recorded_v2_input'), (14, 'auditmanager.analysis.profiles.ar_v2.reco...
  tests/integration/analysis/test_ar_v2_recorded_stage_result.py [(14, 'auditmanager.analysis.profiles.ar_v2.recorded_call', 'build_recorded_call_facts'), (15, 'auditmanager.analysis.profiles.ar_v2.r...
  tests/integration/analysis/test_ar_v2_registered_profile.py [(9, 'auditmanager.analysis.profiles.ar_v2', 'registered')]
  tests/integration/analysis/test_ar_v2_response_parser.py [(10, 'auditmanager.analysis.profiles.ar_v2.response', 'V2ResponseError'), (10, 'auditmanager.analysis.profiles.ar_v2.response', 'parse_resp...
  tests/integration/analysis/test_ar_v2_response_pipeline.py [(10, 'auditmanager.analysis.profiles.ar_v2.response', 'V2ResponseError'), (11, 'auditmanager.analysis.profiles.ar_v2.response_pipeline', ...
  tests/integration/analysis/test_ar_v2_response_schema.py [(8, 'auditmanager.analysis.profiles.ar_v2.response_schema', 'CATEGORIES'), (8, 'auditmanager.analysis.profiles.ar_v2.response_schema', 'SEV...
  tests/integration/analysis/test_ar_v3_prompt_material.py [(12, 'auditmanager.analysis.profiles.ar_v2.prompt_material', 'material_sha256')]
  tests/integration/analysis/test_ar_v3_response_schema.py [(5, 'auditmanager.analysis.profiles.ar_v2.response_schema', 'CATEGORIES')]
  tests/integration/findings/test_analysis_public_boundary.py [(9, 'auditmanager.findings.merge_publication_plan', 'MergePreparation')]
  tests/integration/findings/test_merge_publication_plan.py [(10, 'auditmanager.analysis.profiles.ar_v2.merge_input', 'prepare_merge'), (11, 'auditmanager.analysis.profiles.ar_v2.proposal_grounding',...
  tests/integration/findings/test_v2_merge_core.py [(7, 'auditmanager.analysis.stages.finding_merge', 'MergeEvidence'), (7, 'auditmanager.analysis.stages.finding_merge', 'MergeObservation'), (7, 'aud...
  tests/integration/findings/test_v2_publication_sql.py [(10, 'auditmanager.analysis.profiles.ar_v2.merge_input', 'prepare_merge'), (11, 'auditmanager.analysis.profiles.ar_v2.proposal_grounding', 'Gr...
  tests/integration/findings/test_v2_recorded_chain.py [(12, 'auditmanager.analysis.profiles.ar_v2.response', 'V2ResponseError'), (14, 'auditmanager.findings.v2_publication', 'V2PublicationContext'),...
  tests/integration/findings/test_v2_recorded_saved_plan.py [(14, 'auditmanager.analysis.stages.finding_merge', 'MergeEvidence'), (14, 'auditmanager.analysis.stages.finding_merge', 'MergeObservation'...
  tests/integration/jobs/test_recorded_v2_executor_bridge_db_accept.py [(213, 'auditmanager.runs.recorded_v2_stage', None)]
  tests/integration/jobs/test_recorded_v2_publication_gate.py [(24, 'auditmanager.runs.recorded_v2_publication', '_stages'), (24, 'auditmanager.runs.recorded_v2_publication', '_terminal_without_plan'...
  tests/integration/runs/test_recorded_v2_sources.py [(20, 'auditmanager.runs.recorded_v2_sources', 'load_recorded_v2_input')]
  tests/integration/runs/test_v2_recorded_durable_stage.py [(17, 'auditmanager.analysis.profiles.ar_v2.recorded_request', 'RecordedGenerationSettings'), (19, 'auditmanager.runs', 'recorded_v2_stage')]
  tests/integration/runs/test_v2_recorded_executor.py [(133, 'auditmanager.analysis.profiles.ar_v2', 'registered')]
  tests/integration/runs/test_v2_recorded_executor_bridge.py [(123, 'auditmanager.runs', 'recorded_v2_stage'), (123, 'auditmanager.runs', 'recorded_v2_merge'), (123, 'auditmanager.runs', 'recorded_v2...
  tests/integration/runs/test_v2_recorded_merge_stage.py [(17, 'auditmanager.runs', 'recorded_v2_merge')]
  tests/unit/analysis/test_ar_v3_independent_of_ar_v2.py [(287, 'auditmanager.analysis.profiles.ar_v2', 'registered')]
  tests/unit/executors/test_runner_answers.py [(14, 'auditmanager.analysis.profiles.ar_v2.response_schema', 'response_schema')]
  35 importing files
  ```
- interpretation: in `src` exactly three surviving files import the removed set (`analysis/public.py`, `findings/public.py`, `runs/executor.py`), and all three are edited by this lane (the v2 exports and branch). Nothing under `ar_v3/`, `ar_shared/`, `analysis/recognised/`, `analysis/text/`, `sections/`, `optimisation/` imports it (`PROD-10`'s guard `tests/unit/analysis/test_ar_v3_independent_of_ar_v2.py` is green at the base: 13 passed). The surviving **tests** that import it are the v2 tests (deleted), `test_ar_v3_prompt_material.py` and `test_ar_v3_response_schema.py` (v3 tests that compare with v2 constants), `test_runner_answers.py` (a v2 response schema used as a sample) and the evaluation tests; each is handled in the report. By name rather than by module: `findings/queries.py` takes `AR_V2_RECORDED_PROFILE_ID` from `analysis.public` and `bootstrap/composition.py` takes `resolve_profile` from `analysis.text`; both are edited here.

### P-02b — who takes a removed name from a public surface (by name)

- captured_at: 2026-10-26
- command: `python3 uses.py .` (scratch: every `from auditmanager.{analysis.public,analysis,findings.public,findings,runs.executor,runs,analysis.text} import <name>` whose name is a v2 export or `AR_TEXT_PROFILE` / `resolve_profile`)
- captured_output:
  ```text
  scripts/recovery/synthetic_drill_seed.py ['AR_TEXT_PROFILE']
  src/auditmanager/analysis/public.py ['AR_TEXT_PROFILE']
  src/auditmanager/bootstrap/composition.py ['resolve_profile']
  src/auditmanager/findings/merge_publication_plan.py ['MERGE_ARTIFACT_ROLE', 'MERGE_ARTIFACT_VERSION', 'MERGE_RULE_VERSION', 'MergePreparation', 'ProposalGroundingResult', 'ProposedObservation', 'RejectedProposal', 'prepare_merge']
  src/auditmanager/findings/queries.py ['AR_V2_RECORDED_PROFILE_ID']
  src/auditmanager/findings/recorded_saved_plan.py ['MERGE_ARTIFACT_ROLE', 'MERGE_ARTIFACT_VERSION', 'MergePreparation', 'RECORDED_OBSERVATION_ARTIFACT_ROLE', 'RecordedArtifactError', 'read_recorded_merge_input']
  src/auditmanager/findings/v2_publication.py ['AR_V2_CATEGORIES', 'AR_V2_SEVERITIES', 'RejectedProposal']
  src/auditmanager/findings/v2_recorded.py ['FinishedV2Response', 'finish_response']
  src/auditmanager/runs/executor.py ['AR_TEXT_PROFILE', 'AR_V2_RECORDED_BUNDLE_ID', 'AR_V2_RECORDED_PROFILE_ID', 'RecordedGenerationSettings', 'RecordedProfileError', 'resolve_recorded_profile']
  src/auditmanager/runs/recorded_v2_merge.py ['MERGE_ARTIFACT_ROLE', 'MERGE_ARTIFACT_VERSION', 'RecordedArtifactError', 'merge_grounded', 'read_recorded_merge_input']
  src/auditmanager/runs/recorded_v2_publication.py ['V2PublicationContext', 'plan_recorded_saved_publication', 'publish_v2_merge_plan', 'resolve_recorded_profile']
  src/auditmanager/runs/recorded_v2_sources.py ['AR_V2_RECORDED_BUNDLE_ID', 'AR_V2_RECORDED_PROFILE_ID', 'RecordedGenerationSettings', 'RecordedV2Input', 'plan_recorded_v2_execution', 'prepare_recorded_v2_input']
  src/auditmanager/runs/recorded_v2_stage.py ['RecordedGenerationSettings', 'build_recorded_call_facts', 'build_recorded_observation_artifact', 'replay_recorded_response', 'seal_recorded_v2_stage_result']
  tests/contract/evaluation/test_bridge.py ['ProposalGroundingResult', 'ProposedObservation', 'prepare_merge']
  tests/integration/analysis_text/test_live_adapter_shape.py ['AR_TEXT_PROFILE']
  tests/integration/analysis_text/test_model_identity.py ['AR_TEXT_PROFILE']
  tests/integration/analysis_text/test_profile_and_artifact.py ['AR_TEXT_PROFILE', 'resolve_profile']
  tests/integration/analysis_text/test_provider_modes.py ['AR_TEXT_PROFILE']
  tests/integration/composition/test_the_run_leaves_the_request_thread.py ['resolve_profile']
  tests/integration/evaluation/test_local_bundle.py ['AR_V2_RECORDED_BUNDLE_ID', 'AR_V2_RECORDED_PROFILE_ID']
  tests/integration/evaluation/test_run_sources.py ['AR_V2_RECORDED_BUNDLE_ID', 'AR_V2_RECORDED_PROFILE_ID']
  tests/integration/jobs/test_recorded_v2_executor_bridge_db_accept.py ['AR_V2_RECORDED_BUNDLE_ID', 'AR_V2_RECORDED_PROFILE_ID', 'RecordedGenerationSettings', 'prepare_recorded_v2_input']
  tests/integration/jobs/test_recorded_v2_publication_gate.py ['AR_V2_RECORDED_BUNDLE_ID', 'AR_V2_RECORDED_PROFILE_ID', 'RecordedGenerationSettings', 'build_recorded_observation_artifact', 'prepare_recorded_v2_input', 'replay_record
  tests/integration/p02_journey/journey.py ['AR_TEXT_PROFILE']
  tests/integration/p02_journey/test_explicit_failures.py ['AR_TEXT_PROFILE']
  tests/integration/p02_journey/test_manifest_role_seam.py ['AR_TEXT_PROFILE']
  tests/integration/p02_journey/test_ungrounded_diagnostic_path.py ['AR_TEXT_PROFILE']
  tests/integration/p02_journey/test_whole_journey_idempotency.py ['AR_TEXT_PROFILE']
  tests/integration/runs/test_full_chain.py ['AR_TEXT_PROFILE']
  tests/integration/runs/test_recognised_region_db_s3_accept.py ['AR_V2_RECORDED_BUNDLE_ID', 'AR_V2_RECORDED_PROFILE_ID', 'RecordedGenerationSettings']
  tests/integration/runs/test_recorded_v2_sources.py ['RecordedGenerationSettings']
  tests/integration/runs/test_reference_text_input_db_s3_accept.py ['AR_V2_RECORDED_BUNDLE_ID', 'AR_V2_RECORDED_PROFILE_ID', 'RecordedGenerationSettings']
  tests/integration/runs/test_v2_recorded_durable_stage.py ['AR_V2_RECORDED_BUNDLE_ID', 'AR_V2_RECORDED_PROFILE_ID']
  tests/integration/runs/test_v2_recorded_executor.py ['AR_TEXT_PROFILE', 'AR_V2_RECORDED_BUNDLE_ID', 'AR_V2_RECORDED_PROFILE_ID', 'plan_recorded_v2_execution']
  tests/integration/runs/test_v2_recorded_executor_bridge.py ['AR_V2_RECORDED_BUNDLE_ID', 'AR_V2_RECORDED_PROFILE_ID', 'RecordedGenerationSettings']
  tests/integration/runs/test_v2_recorded_merge_stage.py ['AR_V2_RECORDED_BUNDLE_ID', 'AR_V2_RECORDED_PROFILE_ID']
  tests/integration/runs/test_v3_execution_guard.py ['AR_TEXT_PROFILE']
  tests/replay/text_analysis/test_replay_determinism.py ['AR_TEXT_PROFILE']
  tools/evaluation/run_sources.py ['AR_V2_RECORDED_BUNDLE_ID', 'AR_V2_RECORDED_PROFILE_ID', 'resolve_recorded_profile']
  ```
- interpretation: after the removal `analysis/public.py` still exports everything `ar_v3`, `ar_shared` and the 14 sections use: no surviving source module takes a v2 export except `findings/queries.py` (one constant) and `executor.py`. The test-side importers are listed above; a collection of the whole test tree after the edit (`pytest --collect-only`) is the machine check that nothing was missed.

### P-03 — the contract versioning rule, and what a number moves

- captured_at: 2026-10-26
- command: `sed -n 9,13p docs/program/VERSIONING_AND_FREEZE_POLICY.md; python3 tools/plan/pin_sweep.py contract-version | wc -l; git show --stat --format=%h 8c1d3863 | tail -1; grep -n "1\.6\.0" infra/deploy/proxy/nginx.conf infra/deploy/proxy/tls-server.conf | cut -c1-60`
- captured_output:
  ```text
  Machine contracts use independent versions. Drafts may use `1.0.0-draft.N` before CP-00/CP-01. Once a major contract is consumed by released checkpoint:

  - backward-compatible optional addition → minor;
  - bugfix/clarification with no machine/semantic incompatibility → patch;
  - required field/remove/rename/meaning/state-transition incompatibility → major or explicit compatibility bridge.
  74
   92 files changed, 248 insertions(+), 176 deletions(-)
  infra/deploy/proxy/tls-server.conf:197:        return 401 '{
  infra/deploy/proxy/tls-server.conf:203:        return 429 '{
  infra/deploy/proxy/nginx.conf:486:        return 401 '{"cont
  infra/deploy/proxy/nginx.conf:499:        return 429 '{"cont
  ```
- interpretation: the policy is `docs/program/VERSIONING_AND_FREEZE_POLICY.md` (`contracts/api/v1/README.md` and `CONTRACT_PIN_REGISTRY.md` point to it). A number moves ~92 files (the last seal, `8c1d3863`, did): the four families under `contracts/{api,domain,analysis,events}`, the OpenAPI mirror, the generated client, `FRONTEND_LOCK.json`, ~60 web tests, `tests/support/expected_facts.json` and **the edge's 401 and 429 bodies in `infra/deploy/proxy/nginx.conf` and `tls-server.conf`**, which the brief forbids and lane `PW3-I2` owns in this wave. The rule applied to this reseal is stated in the decision D-1.

### P-04 — what the removal of the AR default breaks outside the named list

- captured_at: 2026-10-26
- command: `grep -rln "run_to_terminal\|execute_run" tests --include=*.py | wc -l; grep -rl "text_profiles" tests --include=*.py | wc -l; grep -rn "run_text_analysis(" tests src --include=*.py | grep -v "def " | wc -l; sed -n 923,927p src/auditmanager/runs/executor.py; sed -n 308p src/auditmanager/analysis/text/stage.py`
- captured_output:
  ```text
  60
  10
  47
      text_profile = None if v3_exact else (
          AR_TEXT_PROFILE
          if recorded_v2 or text_profiles is None
          else _pinned_text_profile(run, text_profiles)
      )
      profile: AnalysisProfile = AR_TEXT_PROFILE,
  ```
- interpretation: 60 test files drive the executor and only 10 pass `text_profiles`; the other 50 run АР v1 through the executor's silent default (``execute_run`` docstring: "the in-process harness's unrouted mode ... runs the v1 AR profile"), and some of the 47 test and source calls of `run_text_analysis` use the AR default of `stage.py` (`profile: AnalysisProfile = AR_TEXT_PROFILE`). Removing the default makes each of them refuse. They exercise the **v1 machinery** (retries, durable effects, cost, exports, recovery) with the AR prompt as their vehicle. Decision D-2 keeps their assertions byte for byte.

### P-05 — the v1 recordings are NOT read by АР v1 alone (the brief's check fails)

- captured_at: 2026-10-26
- command: `git grep -l -F "recorded/text_analysis" -- . ':!docs' ':!artifacts' ':!fixtures/recorded/sections/*/*.json' | sort`
- captured_output:
  ```text
  fixtures/recorded/sections/build_fixtures.py
  fixtures/recorded/sections/README.md
  fixtures/recorded/text_analysis/build_fixtures.py
  fixtures/recorded/text_analysis/README.md
  infra/deploy/Dockerfile.api
  Makefile
  src/auditmanager/analysis/text/__main__.py
  src/auditmanager/analysis/text/proxy.py
  src/auditmanager/analysis/text/recorded.py
  tests/e2e/pc01/journey/fixtures/w28-live/make_document.py
  tests/e2e/pc01/journey/fixtures/w28-live/w28-measure.manifest.json
  tests/e2e/pc01/journey/fixtures/w28-live/w28-proxy.manifest.json
  tests/e2e/pc01/journey/fixtures/w28-live/w28-recorded.manifest.json
  tests/e2e/pc01/journey/fixtures/w28-live/w28-recorded-redden.manifest.json
  tests/e2e/pc01/journey/README.md
  tests/integration/analysis_text/conftest.py
  tests/integration/analysis_text/test_input_budget_calibration.py
  tests/integration/analysis_text/test_output_token_provenance.py
  tests/integration/analysis_text/test_provider_modes.py
  tests/integration/analysis_text/test_proxy_truncation_reaches_partial.py
  tests/integration/executors/test_agent_e2e.py
  tests/integration/executors/test_http_run_path.py
  tests/integration/executors/test_pull_run_path.py
  tests/integration/p02_journey/journey.py
  tests/integration/runs/test_call_status_and_output_tokens.py
  tests/integration/runs/test_full_chain.py
  tests/replay/text_analysis/conftest.py
  tests/unit/executors/test_identity_stage.py
  tests/unit/executors/test_unmetered_cost.py
  tools/validation/ledger_report.py
  ```
- interpretation: the brief says to confirm that the 14 sections do not read `fixtures/recorded/text_analysis`. They do: `fixtures/recorded/sections/build_fixtures.py` builds every section recording over `inputs/ar_baseline_text_layer.json` and names the path in each recording's `origin`; `RecordedAdapter()` (`analysis/text/recorded.py`, `RECORDINGS_RELPATH`) reads this directory by default and the API image copies it (`infra/deploy/Dockerfile.api:87`) for recorded mode; the recovery drill seed, the e2e fixtures and ~15 machinery tests read it. Deleting any of it breaks the 14 sections' recordings or the recorded provider. Decision D-3.

### P-06 — the web names `builtin` in seven source files

- captured_at: 2026-10-26
- command: `git grep -l -i -F builtin -- web ':!web/package-lock.json'`
- captured_output:
  ```text
  web/openapi/openapi.json
  web/src/entities/analysis-profile/model/presentation.ts
  web/src/shared/api/generated/operations.gen.ts
  web/src/shared/api/generated/types.gen.ts
  web/src/widgets/analysis-profile-table/ui/analysis-profile-table.tsx
  web/tests/guards/rendered-language.guard.test.ts
  web/tests/unit/analysis-settings/analysis-settings.test.ts
  web/tests/unit/styles/screens.ts
  ```
- interpretation: eight files (the ADR counted seven): the OpenAPI mirror, the generated client (two files), the presentation labels, the profile table widget and three tests. `profile` is already nullable in `AnalysisProfileListItem`, and `source` is already nullable (ПБ is authored), so the schema keeps its shape and loses one enum member.

### P-07 — the АР-bound journey steps

- captured_at: 2026-10-26
- command: `python3 -c "import json; m=json.load(open('tests/e2e/pc01/journey/manifest.json')); b=m['write']['ar_bound']; print({k:len(v) for k,v in b.items() if isinstance(v,list)}, len(m['write']['steps']))"`
- captured_output:
  ```text
  {'$comment': 14, 'steps': 33, 'needs_published_run': 15, 'registry_pins': 1} 112
  ```
- interpretation: 33 steps may name АР (15 of them need a published АР run, one is the registry row that names `builtin`), among 112 write steps; the lane marks them, it does not delete them.

### P-08 — the base is green where this lane will read it

- captured_at: 2026-10-26
- command: `pytest tests/unit/analysis/test_ar_v3_independent_of_ar_v2.py tests/unit/analysis/test_text_profile_registry.py`
- captured_output:
  ```text
  46 passed in 2.08s
  ```
- interpretation: the independence guard (13) and the registry tests (33) pass at the base; the former is rewritten into a guard that the removed modules stay removed, the latter loses its АР cases.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/**`
- `contracts/api/v1/**`
- `web/**`
- `tests/**`
- `fixtures/recorded/text_analysis/**`
- `docs/program/tasks/PROD-11-AR-V1-V2-REMOVAL-01.md`
- `docs/program/PROD-11-AR-V1-V2-REMOVAL-01.md`

## Lane resources

The lane stack of the integrator is up (`auditmanager-ar-close`, PostgreSQL 58640, S3 62140); the lane uses private databases on it, never resets or drops the shared one, and leaves none behind.

## Forbidden hotspots

- migrations, `infra/**`, `.github/**`, the section profile packages and recordings, `P02_LOCK.json`
- `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs
- see D-4 for the one exception the version sweep needs

## Non-goals

- no new error code, path, operation or schema; `FindingCategory` and the nine stage ids stay (`AD-12`)
- no change to `ar_v3`, `ar_shared` behaviour, to the 14 section packages or to their recordings
- no activation of АР v3 (`D-204`), no migration, no push

## Deliverables

- the removal in stages (server, contract, web, tests, journey), each committed with its tests green
- this file and `docs/program/PROD-11-AR-V1-V2-REMOVAL-01.md` (files, mutation table, before and after of modified tests, counts, limits)

## Required tests

- command: the commands of the report, one pytest at a time
- expected: green per stage; the report lists every deleted test file and every modified one

## Integration contract

What the integrator can rely on after this lane: an АР version cannot start or re-audit a Run (`section_profile_unavailable`, 27 error codes unchanged); `listAnalysisProfiles` answers `profile: null` for АР and no `builtin`; the registry holds 14 entries; no module outside the tree of removed ones imports one; the contract surface is 92 paths, 104 operations, 301 schemas at the version of D-1; the journey marks its АР-bound steps `pending_v3_activation`.

## Failure/idempotency/security cases

- an АР version on `startRun` / `reauditRun`: refused before the idempotency key is claimed, nothing written (the routing path of `W59-SECTION-SEAL-01`, unchanged)
- an unrouted `execute_run` (no `text_profiles`) for a non-v3 run: refused, never an AR substitute (`AGENTS.md` section 4)
- a run row pinned to the retired АР v1 or v2 identity that exists in some database: `execute_run` refuses it as an unregistered profile (`required_norm_unavailable`); its reads stay generic

## Rollback / feature flag

Not applicable: no flag. The change is a removal; rollback is a revert of the lane's merge commits (the contract reseal and the version sweep are separate commits).

## Decisions of the lane

Every small decision is recorded here and in the report as "decided by the lane".

- **D-1 (the contract number, proposed, the integrator confirms).** Rule: `VERSIONING_AND_FREEZE_POLICY.md` (P-03). This reseal removes one enum member from a response-only enum, rewrites three prose passages and narrows what two operations accept for АР versions (an existing, documented error). Read for a consumer written against `1.6.0`: no field, path or operation disappears; a response that used to carry `builtin` never will, so a client that handled it has a dead branch and no client that did not handle it can meet it; the narrowing is announced by an existing error code. That is not a required-field, rename or meaning change, so the proposal is a **minor, `1.7.0`**. The strict reading of "remove" is a major (`2.0.0`) and would need a bridge or a new document family; the lane does not propose it because no external consumer exists (closed beta, data purged at the release, `R-146m`) and the only consumer, the web client, is regenerated in the same change. The number is applied in **its own commit** (stage 2b), after the reseal commit (stage 2a, which keeps `1.6.0`), so that the integrator can change it with `python3 tools/plan/pin_sweep.py contract-version` or drop the commit.
- **D-2 (the v1 machinery keeps its reference profile in the tests).** `AR_TEXT_PROFILE`, `resolve_profile`, the AR registry entry and every default are removed from `src`. The ~50 machinery tests that used the AR profile as a vehicle keep their assertions byte for byte and receive the same profile object from `tests/support/v1_reference_profile.py` (built from the v1 constants that stay in `prompt.py`, with the retired identity), passed explicitly (`profile=`, `text_profiles=`). The alternative (repoint to a real section profile) would change the request checksum, the recordings and every figure those tests pin.
- **D-3 (the v1 recordings stay).** `fixtures/recorded/text_analysis/**` is not deleted: it is the recorded provider's default directory (shipped in the API image), the text layer every section recording is built over, and the reference corpus of the machinery tests (P-05). Nothing in it is АР-registration data.
- **D-4 (paths outside the brief's list that the removal forces).** `contracts/{domain,analysis,events}/**` and `tests/support/expected_facts.json` for the version literal (they move with the API document, `CONTRACT_PIN_REGISTRY.md`); the four literals of `infra/deploy/proxy/{nginx,tls-server}.conf` that a test pins to the facts file (only the string `1.6.0`, in the stage 2b commit alone); `tools/evaluation/{bridge,run_sources,local_bundle}.py` and `scripts/recovery/synthetic_drill_seed.py`, which import removed names (D-5, D-6).
- **D-5 (the offline AR v2 seeded evaluator).** `tools/evaluation/{bridge,run_sources,local_bundle}.py` project v2 publication plans and read the recorded v2 profile; with those gone they cannot import. They are deleted with their tests (`tests/contract/evaluation/test_bridge.py`, `tests/integration/evaluation/*`); `matcher.py`, the seeded generator and `fixtures/evaluation/ar_v2/**` are pure data and stay.
- **D-6 (the recovery drill seed).** `scripts/recovery/synthetic_drill_seed.py` runs АР v1 through `execute_run`; it is repointed to the v1 reference profile of D-2 (one import and one argument), so the recovery tests keep their seed.
