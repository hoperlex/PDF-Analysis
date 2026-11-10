# AR-V3-BE-RM-01 — the six-scope АР beta removed from the server (step A)

Wave AR-V3-REMOVE + V3-OPTIN, rulings `R-154a` and `R-154c`. Base `origin/dev` `826470582` (VERSION 0.23.1, contract 1.49.0,
migration head `0062_hosts_stage_models`). Step A covers code, tests, scripts and infra. Step B (contract, generated client,
migration, pins) waits for the integrator's version and migration numbers; nothing under `contracts/**`, `db/migrations/**`
or `web/**` is touched here.

## What was removed

- `src/auditmanager/runs/v3_*.py` (19 modules), `src/auditmanager/analysis/profiles/ar_v3/**` (the profile, its pack tooling and
  norm map), `src/auditmanager/api/routers/ar_v3_groups.py`.
- The part of `analysis/profiles/ar_shared/**` that only the profile used (`content`, `grounding`, `v2_identities` and the six
  prompt files; a grep showed no other importer). `recognised_context.py` stays: `analysis.recognised.region_candidate` and the
  analysis public surface import it.
- `runs/analysis_kind.py` and `STANDARD_RUN_SQL`. Every run is of the one analysis now, so the readers (audit state, schedule,
  queue `live_failure_count`, comparison and optimisation run lists) lose the kind condition and `RunCandidate.standard_analysis`.
- The AR v3 branches of the shared modules: `runs/{commands,executor,carrier,preflight,public,stage_facts}.py` (group estimate,
  repeat refusals, worker chain, `ar_v3_*` digest pins, the `ar_v3` stage chip), `jobs/repository.py` (`completed_v3_call`),
  `bootstrap/{composition,adapters,providers}.py` (pack manifest, start switch, group service, replay call binding),
  `api/{security,routers,schemas}`, `findings/queries.py`, `shared/identity` (`ArV3RunGroupId`).
- Scripts, deploy and env: `scripts/ar-v3/**`, `infra/deploy/ar-v3-pack/**`, `AR_V3_BETA_PACK_MANIFEST` and
  `AR_V3_BETA_START_ALLOWED` in `compose.server.yml` and `alpha.env.example`, the two bind mounts, the `scripts/README.md`
  section, the AR v3 seed kind of `tools/measure/perf/perf_seed.py`.
- 123 test files that tested only the removed code; the shared tests lost their AR v3 cases.

## Departures from the plan (code facts)

1. **`getRunNormVerification` is removed too.** The plan names the group operations only. The adapter answered `not_found` for
   every profile except the AR v3 pair (`bootstrap/adapters.py`, `get_norm_verification`), so after the removal it could only say
   404. Its schemas `NormVerificationReport`, `NormFindingVerification`, `NormObservationCitationPartition` and the wire enum
   `UngroundedReason` (referenced by nothing else) go with it. `findings/citation_report.py`, `citation_publication.py` and
   `retrieval_set_input.py` (their only callers were the removed modules) are deleted; `findings/citation_reader.py` stays (the
   XLSX certified-package path reads it) with the AR v3 stage out of `CITE_STAGE_IDS`.
2. `RunStatus.analysis_kind`, `ar_v3_group_id`, `ar_v3_scope_id` leave the server schema (the plan said «stop naming a kind»).
3. `RunCostEstimate.scope` is `Literal["run"]` (was `run | ar_v3_group`); the field stays.
4. `ComparisonRefusal.reason` loses `analysis_not_comparable`, which only a v3 run could produce.
5. `scripts/norms/export_paragraph_rows.py` and its test are deleted, not edited: the script exists to feed the AR beta map tool
   and validates that tool's row format.
6. `infra/deploy/apply-grants.sh` and `scripts/recovery/**` are unchanged. The two tables, their triggers and the command type
   `start_ar_v3_beta_group` stay classified until the migration drops the tables (step B).
7. The wire-form (provider-safe schema) tests took their fixture from the AR v3 response schema. They now use
   `tests/support/one_of_response_schema.py`; the three tests that held the real AR v3 schema and its parser to the wire form
   are gone. The text digest of `«Сводка»` in `tests/unit/exports/test_xlsx_writer_labels.py` was re-pinned because the corpus
   profile id changed from a profile name to `profile_1`; with the old literal the writer still produces the old digest
   (checked), and `«Замечания»` is unchanged.
8. `tests/unit/measure/test_perf_harness.py`: the not-vacuous floor of reached product names goes from 25 to 23, because the seed
   no longer names the two AR v3 identifiers.

## Ambiguous decisions

- `runs/executor.py`: `v3_workflow`, `v3_state`, `v3_pretext_*`, `v3_checkpoint` are the extended-review v3 plan and stay. Only
  `v3_profile`, `v3_bundle`, `v3_exact` and the `if v3_exact:` branch were AR v3.
- `AR-V3-WIRE-SCHEMA-01` and `AR-V3-LIVENESS-01` name two generic features (the provider-safe wire schema, the attempt's signs of
  life). Both stay as code; their comments lost the task ids.
- Left as generic W57 citation infrastructure that no run produces any more: `findings/citation_reader.py`, the XLSX certified
  path, `norm_citations` / `required_value` / `stated_value` on the finding wire models and `NormCitationView`,
  `norms/citation_prep.ground_norm_observation`, `norms/retrieval` (`select_verified_retrieval_set`, `promote_cli`),
  `norm_retrieval_set_sha256` of `frozen_input_digest`, the decision-memory `NormRef` shape (capture now writes `norm_refs=()`).
  The web finding table and basis read those fields; removing them from the wire is a web change outside this wave.

## Checks

Tree `bc8da8242` (tree `4d56d555`) and its parent `89dbc2a30` (tree `18c2aee6`), host lock held, memory above 2500 MB:

- Focused batch, 190 files (the files edited here plus the unit files of the edited modules, no database):
  `.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider -rf --tb=short <190 files>` on
  `89dbc2a30`: 4554 passed, 1 skipped, 7 failed. Six were mine and are fixed (`allow_native_page_pieces` restored on
  `RunCostPreflight.estimate_run`, which tests use; the fixture made all properties required; the xlsx pin; the harness floor).
  Rerun of those files on `bc8da8242`: 247 passed, 1 failed.
- The one failure, `tests/integration/analysis_text/test_section_input_budget.py::test_ss_the_largest_prompt_reserves_its_real_length`
  (`'AR' == 'SS'`), **exists on the base**: the original-source АР profile (`3821261a7`) has the largest prompt (21278
  characters against 12086 for SS); measured on a `git archive 826470582` extract. Not caused or fixed here.
- Contract-coupled files (`contract`, `characterization`, `e2e` static tests), `--tb=line`: 384 passed, 6 failed, 66 errors. The
  six failures are the contract file still holding the removed operations (`test_openapi_document` x4, `test_openapi_conformance`
  count 236 vs 231, `test_response_baseline` scope enum) and go green when step B regenerates it. The 66 errors need real
  services (`.env` missing). Logs: `.local/evidence/lane-ar-v3-be-rm-01/`.
- Not run: tests needing the database or object store (step B stand), `tsc` (no web change).

## Step B (measured)

**Contract `contracts/api/v1/openapi.json`** (1.49.0 holds 296 paths, 324 operations, 798 schemas; the app now yields 290, 318, 779):
- operations removed (6): `startArV3BetaGroup`, `estimateArV3GroupCost`, `getArV3BetaGroup`, `getArV3BetaGroupReview`,
  `getArV3BetaPackStatus`, `getRunNormVerification`;
- schemas removed (19): `ArV3BetaGroup`, `ArV3BetaGroupMember`, `ArV3BetaGroupReview`, `ArV3BetaGroupReviewMember`,
  `ArV3BetaPackReview`, `ArV3BetaPackStatus`, `ArV3BetaStageId`, `ArV3BetaVisibleCitation`, `ArV3BetaVisibleEvidence`,
  `ArV3BetaVisibleProposal`, `ArV3BetaVisibleReview`, `ArV3BetaVisibleTopic`, `ArV3GroupCostEstimateRequest`, `ArV3RunGroupId`,
  `StartArV3BetaGroupRequest`, `NormVerificationReport`, `NormFindingVerification`, `NormObservationCitationPartition`,
  `UngroundedReason`;
- shared schemas narrowed: `RunStatus` (`analysis_kind`, `ar_v3_group_id`, `ar_v3_scope_id` gone; `degradation_set` items are
  `StageId`), `StageState.stage_id` (`StageId` only), `RunCostEstimate.scope` (`run`), `RunStageChip` (no `ar_v3`),
  `ComparisonRefusal.reason` (no `analysis_not_comparable`);
- descriptions that name the beta: `ExecutionQueuePage.live_failure_count`, `DocumentActiveRun`, `DocumentAuditCounts`,
  `RunStageChip`, `info.description` (the `AR-V3-BETA-SIX-RUN-02` passage), and the operations `uploadDocument`,
  `estimateRunCost`, `reauditRun`, `getRunStages`, `startRunFromStage` (the app's own text for the last two and for
  `listAnalysisProfiles` is already updated);
- `contracts/api/v1/README.md` (24 mentions) gets the new entry; `web/openapi/openapi.json` and the generated client follow.

**Other contract files:** delete `contracts/analysis/ar_v3_beta/**`. `contracts/domain/v1/identifiers.json` (`ar_v3_run_group_id`
prefix `arg`, entity `ArV3RunGroup`), `identifiers.schema.json` (4 places), `error-codes.json` (`conflict` note 21:
`ar_v3_start_not_enabled`, `ar_v3_member_not_repeatable`, dependency `ar_v3_trusted_pack`, aggregate `ArV3RunGroup`),
`state-machines.json` and the domain README (revision notes). `contracts/analysis/v1/stage-registry.json:435` (the optional
`norms.snapshot` input says «for AR v3»), pinned by `tests/contract/api_v1/test_w57a_citation_contract.py:118`, which changes with it.

**Versioning.** `docs/program/VERSIONING_AND_FREEZE_POLICY.md`: «backward-compatible optional addition → minor; … required
field/remove/rename/meaning/state-transition incompatibility → major or explicit compatibility bridge.» The `1.7.0` precedent read
the АР v1/v2 removal as a minor because «no field, path or operation disappears». Here six operations, 19 schemas, three
`RunStatus` properties and four enum members disappear, so the precedent does not cover it: the rule's text reads **major**
(`2.0.0` is reserved by `R-146ar`/`D-233`). A minor reading is only the owner's to make, on the ground that the beta was never
started in production and the web lane removes its consumers in the same wave.

**Database objects (all from migrations `0032`, `0033`, `0036`; nothing else carries a marker):**
- tables `ar_v3_run_group` and `ar_v3_run_group_member` (drop member first); triggers `trg_ar_v3_run_group_frozen`,
  `trg_ar_v3_run_group_member_frozen` (shared `am_immutable_row`) and the deferred constraint trigger `trg_ar_v3_group_complete`
  go with the tables; the function `am_ar_v3_group_complete()` is dropped explicitly;
- `stage_result.ck_stage_result_stage_id` (`0033`): back to the nine ids of `0002`;
- `am_verify_norm_citation_partition()` (`0036`): the stage test back to `st.stage_id = 'norm_verification'`
  (`0023`'s body), triggers `trg_finding_observation_partition` and `trg_norm_citation_partition` untouched;
- no job-kind CHECK, work-kind row or trigger names the beta (`0047` only mentions `ar_v3_run_group` in a comment);
  `command_record.command_type` has no CHECK (`start_ar_v3_beta_group` is classified only in `scripts/recovery/product_purge.py`).
- Refuse the upgrade, naming the counts, while any of these holds a row: the two tables; `audit_run` with the pair
  `ap_01M5M28ZCDD8VPSP1BTAEW92YE` / `pb_01M5M28ZCDVCR37BX1884JGSPM`; `finding_observation` with that profile;
  `stage_result.stage_id = 'ar_v3_citation_review'`; `command_record.command_type = 'start_ar_v3_beta_group'`; `job` of such a run;
  `model_call.parameters` or `provider_call_effect.parameters` with a key starting `ar_v3_`.

**Pins and tests that move with it:** `scripts/recovery/schema_coverage.py` (HEAD, tables, triggers 5/27/27, counts) and
`product_purge.py` (`PRODUCT_TABLES`; keep `start_ar_v3_beta_group` classified), `grant_classification.py`,
`infra/deploy/apply-grants.sh` (four table lines), `tests/support/expected_facts.json` (`migration_head`, `contract_version`,
the operation and schema lists), the downgrade-chain digests and the schema invariant inventory, and the table lists of
`tests/integration/p02_journey/journey.py`, `tests/integration/recovery/{test_product_purge,test_project_erase,test_project_erase_shapes,
test_synthetic_drill_compare,test_synthetic_drill_seed}.py`, `tests/integration/db/{test_schema_shape,test_schema_invariant_inventory,
test_migration_lifecycle,test_downgrade_chain_round_trip,test_pass_scope_migration}.py`. `tests/integration/db/test_ar_v3_cite_stage_id_migration.py`
and `test_cite_partition_v3_migration.py` test the history of `0033` and `0036` and stay, except that the first ties the migration
to `contracts/analysis/ar_v3_beta`, which step B deletes.

## Risks

- A deployment whose environment still names `AR_V3_BETA_*` ignores the variables silently; the operator removes them.
- `tests/contract/release_notes/test_note_follows_review_switch.py` reads the web constant `SHOW_REVIEW_INDICATION`; the web lane
  must keep that module or move the test.
- `web/src/entities/document-version/model/comparison.ts` handles `analysis_not_comparable`; the generated union loses it.
- `tests/e2e/pc01/journey` keeps the `pending_v3_activation` / `ar_bound` mechanism (`D-204`); its premise went with the beta
  and it needs a live stand to re-prove, so it is not changed here. The manifest step of the analysis settings page now expects
  only `listAnalysisProfiles`; the web lane decides what that page keeps.
- Merge: `runs/preflight.py` is shared with `V3-OPTIN-01` (different hunks); `compose.server.yml` and `alpha.env.example` likewise.
