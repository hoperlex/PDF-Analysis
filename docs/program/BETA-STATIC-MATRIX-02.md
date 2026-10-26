# BETA-STATIC-MATRIX-02 — static B1–B12 coverage matrix on the `AR-CLOSE-1026` tree

**Tree:** branch `integration/ar-close-1026` at `0dbbfc68` (the base of lane M1; `CURRENT_STATE.md` is dated 2026-10-26). **Branch:**
`agent/beta-static-matrix-02`. **Task:** `docs/program/tasks/BETA-STATIC-MATRIX-02.md`. **Asked for by:** `CODE-FIRST-TO-BETA.md` §3 (the static matrix
before the final gates). **Refreshes:** `BETA-MATRIX-02.md` (tree `d087c101`, migration head `0029_routing_refusal_codes`, 2026-10-22) and
`BETA-MATRIX-01.md`; both stay as written, as the records of their days. **Rulings:** `R-135`, `R-141c`, `R-143d`, `R-144`.
Documentation only. The lane ran no test suite, no stand, no container and no build. It ran `pytest --collect-only` on the cited Python test files, the
governance check of its task file, the documentation guards `tests/contract/program`, `tests/contract/api_v1/test_doc_prose_facts.py` and
`tests/contract/api_v1/test_surface_counts_in_prose.py`, and its own existence check (see "Verification of this document").

**This matrix gives no `PASS`.** `ROADMAP-TO-BETA.md` §9 defines B1–B12 as measurements on a deployed stand; `CODE-FIRST-TO-BETA.md` §3 says the
static matrix puts no `PASS` on any of them. A row says which implemented paths and which tests exist on this tree and, separately, what still
needs a stand, an expert, real documents, a policy decision or a publication. A test file named here exists and collects; this document says
nothing about its result except where it quotes a recorded figure with its source.

**Scope under `R-141c`** (`OWNER_RULINGS_2026-09-17.md`): the first beta is a closed beta on test data. The owner accepted B1, B2, B4, B6 (local
drill), B7, B8, B9, B12 for it and deferred B3, B5, B10, B11 with their text unweakened. The matrix covers all twelve, as `CODE-FIRST-TO-BETA.md`
asks. **Stand state is not readable from the tree:** nothing here says what is deployed on any stand.

**Words.** *Kind*: `code property` (a repository can hold it), `stand measurement` (a run on a deployed stand), `expert`, `owner policy`.
*Status* (one per row, never `PASS`): `code present`; `code partial (what is missing)`; `code missing`; `not a code property`. The status speaks
only of the code-property part of the criterion; the last column is what the rest needs. Debt ids are rows of `DEBT_REGISTER.md` as it stands on this
tree; a closed row is written `(closed)` after its id. The order of the activation sequence is `AR-V3-BETA-ACTIVATION-RUNBOOK-01.md`.

## The matrix

The table gives each criterion's main items; the sections below it hold the full lists (B6 and B12 list every tool, test file and menu destination).

| B | Criterion (short quote) | Kind | Implemented paths | Pinning tests | Status | What remains, and who owns it |
| --- | --- | --- | --- | --- | --- | --- |
| B1 | "accounts, roles, registration, shell accepted live" | code property; stand measurement | `src/auditmanager/access/`, `src/auditmanager/api/security.py`; `issueToken`, `submitRegistration`, `approveRegistration`, `updateUser`, `resetUserPassword`; `0015_accounts_roles_registration`; `/login`, `/register`, `/account`, `/admin/users`, `/admin/registrations` | `tests/integration/api/test_registration_flow.py::test_the_pair_proves_a_pending_application`; `tests/integration/auth/test_revocation.py::test_a_credential_stops_being_accepted_the_moment_the_account_is_revoked`; `web/tests/guards/screen-registry.guard.test.ts` | `code present` | live run on a stand and the human A13–A20 pass: `D-137` (owner, operator); host terminator `D-191` (owner) |
| B2 | "corpus snapshot loaded, every PDF and crop in S3 with a confirmed binding, embedding build complete, search answers with citations" | code property; stand measurement | `src/auditmanager/norms/`; `searchNorms`, `listNormDocuments`, `setCurrentNormSnapshot`; `0018_norm_custody`, `0013_norm_embeddings`, `0020_norms_search`; `/norms`, `/norms/document`; `infra/deploy/push-bundle.sh` | `tests/integration/norms/custody/test_two_phase_custody.py::test_a_process_lost_at_each_interruption_point_converges`; `tests/integration/norms/search/test_norm_pdf_window.py::test_the_pdf_is_served_only_through_a_confirmed_binding` | `code present` | the stand import has not run (`STAND-NORMS-IMPORT-RUNBOOK-01`; `D-204` step 1): owner window; `D-123`, `D-188` (operator) |
| B3 | "every beta-eligible new АР start route/preset runs all applicable text, block, merge, review and norm-verification stages; every published finding grounded; … real-set quality at or above the ruled … thresholds" | code property; stand measurement; expert; real documents | v1 `startRun`, `src/auditmanager/analysis/text/stage.py`; v2 `src/auditmanager/runs/recorded_v2_stage.py`; v3 `startArV3BetaGroup`, `getArV3BetaGroupReview`, `src/auditmanager/runs/v3_worker.py`, `0032_ar_v3_run_group` | `tests/integration/runs/test_full_chain.py::test_a_full_run_over_the_corpus_reaches_a_terminal_and_publishes_findings`; `tests/integration/findings/test_v2_recorded_chain.py::test_recorded_chain_merges_grounded_members_and_keeps_rejected_diagnostic`; `tests/integration/runs/test_v3_worker_pipeline.py::test_first_attempt_dispatches_then_cites_then_terminates` | `code partial` (no block or region analysis stage; no critic; no served multi-call or chunked text analysis; no served norm verification on the v1 route, and `getRunNormVerification` answers a typed 503; the v2 route is recorded-only with no live model pin; the v3 route is review-only behind an empty reviewed-pack registry) | v3 activation data `D-204` (owner, qualified expert); profile review `D-178`, `D-183`; quality `D-167`; model pin `D-197`, `D-199` |
| B4 | "durable execution: provider failure retried, restart resumes, Журнал выполнения shows it" | code property; stand measurement | `src/auditmanager/jobs/`, `src/auditmanager/workers/service.py`, `src/auditmanager/runs/retry.py`; `listExecutionJournal`, `listExecutionQueue`, `listWorkers`; `0017_execution_queue`, `0019_execution_workers`; `/logs`, `/queue`, `/workers` | `tests/integration/runs/test_retry_policy.py::test_an_unreachable_provider_is_retried_and_the_run_still_publishes`; `tests/integration/workers/test_worker_service.py::test_drain_finishes_the_run_in_flight_and_claims_no_more`; `tests/integration/jobs/test_d150_and_worker_claims.py::test_a_live_prepared_effect_still_fails_the_run` | `code present` | no stand observation; a live provider failure cannot be induced on a stand; `D-155`, `D-153`, `D-154` (contract-bound); operator |
| B5 | "real АР documents within the separately ruled full-analysis envelope accepted end to end; … typed refusal for a larger input demonstrated without silent truncation" | stand measurement; real documents | `src/auditmanager/ingest/pdf_reader.py`, `src/auditmanager/runs/commands.py` (`analysis_input_budget_exceeded`), `src/auditmanager/analysis/text/chunk_preflight.py`; `uploadDocument`, `startRun` | `tests/integration/ingest/test_size_guard_boundary.py::test_a_body_inside_the_window_is_refused_by_the_envelope`; `tests/integration/runs/test_input_budget.py::test_a_start_above_the_budget_is_refused_with_both_figures`; `tests/integration/ingest/test_pdf_reader_bounds.py::test_a_small_pdf_that_would_cost_gigabytes_is_refused_by_its_rule_in_seconds` | `code partial` (a larger text input gets a typed refusal; chunked analysis of it is prepared in `src/auditmanager/analysis/text/chunk_preflight.py` and consumed by no served stage) | no real document was run; `D-162`, `D-171`, `D-175`, `D-168`; owner (deferred by `R-141c`) |
| B6 | "backup and restore drill passed within the last wave" | code property; stand measurement | `scripts/recovery/` (17 tools), `scripts/stand-copy/restore-test.sh`, `infra/deploy/purge-product-data.sh` | `tests/integration/recovery/test_schema_coverage.py::test_the_declared_head_is_the_alembic_head`; `tests/integration/recovery/test_synthetic_drill_runner.py::test_nonempty_bucket_refuses_before_engine_or_restore` | `code present` | the real drill is a stand act; the last recorded drill is at head `0029` (`RECOVERY-DRILL-0029-01`), none at `0032`; `D-123`, `D-156` (owner, operator) |
| B7 | "deploy bound to the gate; version endpoint reports the tagged version; release history truthfully shows every actually published numbered release" | code property; stand measurement; owner policy | `VERSION`, `src/auditmanager/releases/`, `release-notes/`, `.github/workflows/deploy-auto.yml`, `infra/deploy/verify-deployed.sh`; `getProductVersion`, `listReleases`, `markReleaseNotesRead`; `0016_release_notes` | `tests/integration/releases/test_release_loader.py::test_loader_is_idempotent_and_serves_the_highest_revision`; `tests/contract/release_notes/test_release_notes_form.py::test_authored_shape_and_form`; `tests/contract/test_deploy_auto_workflow.py` | `code present` | no `GATE OK` and no `v0.7.0` tag, host verifier owed: `D-188`, `D-203`, `D-138`, `D-140`, `D-205`, `D-120`, `D-121` (owner, integrator) |
| B8 | "exposure review: nothing reachable that the owner did not decide to expose (`R-29` clause 2)" | owner policy; stand measurement | `src/auditmanager/api/security.py`, `infra/deploy/compose.server.yml`, `infra/deploy/proxy/nginx.conf`, `infra/deploy/proxy/trusted-proxies.sh` | `tests/integration/api/test_authorization.py::test_the_open_surface_is_exactly_the_register`; `tests/integration/api/test_role_register.py::test_every_guarded_operation_is_in_the_role_register`; `tests/contract/test_proxy_rate_limits.py` | `code present` | the review `EXPOSURE-REVIEW-01` predates the runner channel and the v3 routes; host terminator `D-191`, `D-144`, `D-165`, `D-166`, `D-122`, `D-212` (owner, operator) |
| B9 | "contract `1.0.0` and error catalog frozen" | code property; stand measurement | `contracts/api/v1/openapi.json`, `contracts/domain/v1/error-codes.json`, `src/auditmanager/shared/errors/codes.py`; `0029_routing_refusal_codes` | `tests/contract/api_v1/test_contract_seal.py::test_the_facts_file_names_the_sealed_version`; `tests/contract/api_v1/test_contract_seal.py::test_the_catalog_is_frozen_with_all_twenty_seven_codes` | `code present` | the tree declares `1.5.0`, not the `1.0.0` the criterion names: whether the additive minor line satisfies B9 is the owner's reading; served `contract_version` unread on a stand; `D-145`, `D-163`, `D-172`, `D-210` |
| B10 | "2–3 expert smoke sessions completed with no blocking finding" | expert | `scripts/manual-alpha-check.sh`; the screens of B12 | `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` (the protocol, not a test) | `not a code property` | named experts with slots (`OD-18`); `D-137`, `D-139` (owner) |
| B11 | "for any retained real client data: provenance, access, backup/evidence retention and `U-04` policy decided and required controls effective before upload; for external beta also licensing (NORM-Q04), exposure and registration mail" | owner policy | `infra/deploy/reset.sh`, `infra/deploy/purge-product-data.sh`, `scripts/recovery/product_purge.py` | `tests/integration/recovery/test_product_purge.py`; `tests/integration/recovery/test_product_purge_script.py` | `not a code property` | `U-04` undecided, `D-156` (the purge has not been run on the stand), the licence and mail decisions (owner); `D-215` |
| B12 | "every menu destination visible on the beta tree has an actual role-appropriate action, result and live acceptance; a visible stub fails. Account-menu actions are included … the full АР function matrix is tested" | code property; stand measurement; owner policy | `web/src/shared/config/screen-registry.ts` (14 in-menu rows), `web/src/_app/account-menu.tsx`, `web/src/_pages/`, `web/src/widgets/`, `web/src/features/` | `tests/e2e/test_pc01_journey_conformance.py::test_the_journey_walks_every_screen_the_application_offers`; `web/tests/guards/screen-set.guard.test.ts`; `web/tests/guards/screen-registry.guard.test.ts` | `code present` | live acceptance on a stand (`D-186`); the "full АР function matrix" has no definition in the tree; 27 operations no manifest step or route names (B12 section); `D-149` (owner, operator) |

## B1 — accounts, roles, registration, shell

- **Kind.** Code property (the account model, the roles, the registration flow, the shell); stand measurement ("accepted live").
- **Implemented paths.**
  - Source: `src/auditmanager/access/accounts.py`, `src/auditmanager/access/registrations.py`, `src/auditmanager/access/grant.py`,
    `src/auditmanager/access/revoke.py`, `src/auditmanager/access/passwords.py`, `src/auditmanager/access/policy.py`,
    `src/auditmanager/access/profile.py`, `src/auditmanager/access/unlock.py`; the seam `src/auditmanager/api/security.py` (the register
    `UNAUTHENTICATED_OPERATIONS` is `issueToken`, `submitRegistration`, `readRegistrationStatus`); routers `src/auditmanager/api/routers/auth.py`,
    `src/auditmanager/api/routers/users.py`, `src/auditmanager/api/routers/registrations.py`, `src/auditmanager/api/routers/me.py`.
  - Operations: `issueToken`, `changePassword`, `getMe`, `updateMyProfile`, `submitRegistration`, `readRegistrationStatus`, `listRegistrations`,
    `approveRegistration`, `rejectRegistration`, `listUsers`, `getUser`, `updateUser`, `archiveUser`, `restoreUser`, `resetUserPassword`, `purgeUser`.
  - Migrations: `0006_app_user`, `0007_credential_epoch`, `0008_sign_in_throttle`, `0015_accounts_roles_registration`.
  - Screens: `/login`, `/register`, `/register/submitted`, `/account`, `/account/password`, `/admin/users`, `/admin/users/[user_uid]`,
    `/admin/registrations`; features `web/src/features/sign-in`, `web/src/features/register`, `web/src/features/decide-registration`,
    `web/src/features/manage-user`, `web/src/features/edit-profile`, `web/src/features/change-password`; shell `web/src/_app/navigation.ts`,
    `web/src/_app/account-menu.tsx`.
- **Pinning tests.** `tests/integration/api/test_registration_flow.py::test_the_pair_proves_a_pending_application`,
  `tests/integration/api/test_role_register.py::test_a_roleless_account_reads_no_product_data`,
  `tests/integration/access/test_registrations.py::test_approval_creates_the_account_from_the_request_in_one_transaction`,
  `tests/integration/auth/test_revocation.py::test_a_credential_stops_being_accepted_the_moment_the_account_is_revoked`,
  `web/tests/unit/shell/screen-decision.test.ts`, `web/tests/unit/shell/navigation.test.ts`, `web/tests/guards/screen-registry.guard.test.ts`.
  The identity continuation `tests/e2e/pc01/journey/identity.mjs` ran green on a recorded local stack, 12 operations and 18 checks, with migrations
  at `0029` (`PC01-JOURNEY-GAPS-01`); that is a lane stack, not a stand.
- **Status.** `code present`.
- **What remains and who owns it.** The identity continuation and the human A13–A20 pass on the stand: `D-137` (owner, operator). The session cookie
  behind the host's TLS terminator and the client-address throttle: `D-191`, `D-144` (owner decision on the host server block, operator setting).
  The live state of the seeded `admin` credential is not in the tree (`EXPOSURE-REVIEW-01` E-1).

## B2 — corpus, bindings, embeddings, cited search

- **Kind.** Code property; stand measurement (the stand holds the snapshot).
- **Implemented paths.**
  - Source: `src/auditmanager/norms/bundle`, `src/auditmanager/norms/custody`, `src/auditmanager/norms/embedding`, `src/auditmanager/norms/search`,
    `src/auditmanager/norms/catalogue`, `src/auditmanager/norms/current_snapshot.py`, `src/auditmanager/norms/loader.py`; router
    `src/auditmanager/api/routers/norms.py`.
  - Operations: `searchNorms`, `listNormDocuments`, `getNormDocument`, `listNormParagraphs`, `streamNormDocumentContent`, `listNormSnapshots`,
    `listNormSnapshotEvents`, `setCurrentNormSnapshot`; for project crops `listVersionPortalBlocks`, `streamVersionPortalBlockCrop`.
  - Migrations: `0012_norms_corpus`, `0013_norm_embeddings`, `0018_norm_custody`, `0020_norms_search`, `0021_portal_bundles`, `0023_norm_citations`.
  - Stand verbs: `infra/deploy/push-bundle.sh`, `infra/deploy/receive-bundle.sh`, `infra/deploy/copy-serve.sh`, `infra/deploy/pull-copy.sh`,
    `scripts/stand-copy/restore-test.sh`; the operator's order is `STAND-NORMS-IMPORT-RUNBOOK-01.md`.
  - Screens: `/norms`, `/norms/document`; widgets `web/src/widgets/norm-search`, `web/src/widgets/norm-snapshots`, `web/src/widgets/norm-catalogue`,
    `web/src/widgets/norm-document`.
- **Pinning tests.** `tests/integration/norms/bundle/test_bundle_postgres.py::test_postgres_an_exact_replay_is_a_no_op`,
  `tests/integration/norms/custody/test_two_phase_custody.py::test_a_process_lost_at_each_interruption_point_converges`,
  `tests/integration/norms/embedding/test_digest.py::test_the_digest_is_the_documented_canonical_serialisation`,
  `tests/integration/norms/search/test_norm_pdf_window.py::test_the_pdf_is_served_only_through_a_confirmed_binding`,
  `tests/integration/norms/search/test_search_bulkhead.py::test_the_cap_leaves_the_pool_to_other_operations`,
  `tests/integration/norms/search/test_display_designation_window.py::test_search_shows_the_readable_designation_and_one_per_document`,
  `tests/integration/ingest/test_reconciliation_custody_blobs.py::test_custody_blobs_are_neither_unattributed_nor_rejectable`.
- **Evidence in hand (local only).** `W54-LOCAL-IMPORT-01` (the bundle imported into an isolated local stack and served from it) and
  `AR-BETA-LOCAL-CUSTODY-01` (the full repaired snapshot passed isolated local custody qualification). Neither is a stand.
- **Status.** `code present`.
- **What remains and who owns it.** `CURRENT_STATE.md`: the stand import, its copy record and the administrator's designation of a current snapshot
  have not run and need an owner window; the same step opens the activation sequence (`AR-V3-BETA-ACTIVATION-RUNBOOK-01`, step 1, `D-204`). The
  stand MinIO was never inventoried (`D-123`); the host verifier has not been run by an integrating session (`D-188`). Project crops exist only after
  a run on a document; their custody test is the last one above. Owner (window, keys, designation), operator.

## B3 — the АР route: three paths, none of them a finished B3

B3 reads: every beta-eligible new АР start route runs all applicable text, block, merge, review and norm-verification stages, every published
finding is grounded, and real-set quality meets the ruled thresholds. **Kind:** code property (the stages exist and refuse correctly), stand
measurement, expert (the thresholds, the profile review) and real documents. `R-141c` deferred it with its text unweakened.

**Path 1 — the served v1 route.** `startRun` routes a version by its expert-confirmed section through the text-profile registry; AR is registered
from the v1 constants unchanged (`src/auditmanager/analysis/text/profile_registry.py`, `src/auditmanager/analysis/text/profile.py`), and a section
with no profile is refused with no AR fallback. The run drives the four stages of `PC01_STAGES` (`source_preparation`, `page_geometry_extraction`,
`document_context_build`, `text_analysis`) and then the evidence gate.
- Source: `src/auditmanager/runs/commands.py`, `src/auditmanager/runs/executor.py`, `src/auditmanager/analysis/text/stage.py`,
  `src/auditmanager/analysis/stages/source_preparation.py`, `src/auditmanager/analysis/stages/page_geometry_extraction.py`,
  `src/auditmanager/analysis/stages/document_context_build.py`, `src/auditmanager/findings/grounding.py`, `src/auditmanager/findings/publication.py`,
  `src/auditmanager/sections/routing.py`; operations `startRun`, `getRunStatus`, `listRunFindings`, `getFinding`, `appendDecision`,
  `classifyDocumentVersion`, `getRunNormReferences`, `exportRunCsv`, `exportRunXlsx`; migrations `0024_version_classification`,
  `0028_classification_corrections`, `0029_routing_refusal_codes`.
- Tests: `tests/integration/runs/test_full_chain.py::test_a_full_run_over_the_corpus_reaches_a_terminal_and_publishes_findings`,
  `tests/integration/runs/test_w59_routed_execution.py::test_an_ar_routed_run_reproduces_the_recorded_corpus_run`,
  `tests/integration/composition/test_the_served_application_routes_by_section.py::test_start_run_passes_the_section_table_and_no_profile`,
  `tests/integration/sections/test_routing.py::test_unknown_code_never_uses_ar_profile`,
  `tests/integration/analysis_text/test_offsets_and_grounding.py::test_emitted_anchors_slice_back_to_their_own_quotation`,
  `tests/integration/analysis_text/test_model_identity.py::test_a_reply_naming_another_model_is_a_typed_identity_mismatch_that_keeps_the_usage`,
  `tests/integration/runs/test_input_budget.py::test_a_start_above_the_budget_is_refused_with_both_figures`.
- This route has no block-analysis stage, no merge stage, no critic and no norm-verification stage; its text stage is a single-call stage
  (`ROADMAP-TO-BETA.md` §10.14, H-10). `getRunNormReferences` lists the standards a run's saved text cites against the pinned snapshot with no
  model and no finding; it is not norm verification of the document's values.

**Path 2 — the v2 recorded profile.** A recorded-only AR v2 profile exists: seven categories, proposed and decided severity, a deterministic
`finding_merge`, grounding and a publication gate. `execute_run` takes it only for a persisted Run already pinned to the v2 identities, with a
`RecordedAdapter`, recorded provider configuration and an explicit `fixture/<id>` model; **no operation of the API and no screen creates such a
Run** (no file under `src/auditmanager/bootstrap/` or `src/auditmanager/api/` names the v2 identities; `docs/program/tasks/BETA-STATIC-MATRIX-02.md`
P-03). The served read side (`listRunFindings`, `getFinding`) groups merged v2 findings.
- Source: `src/auditmanager/analysis/profiles/ar_v2/registered.py`, `src/auditmanager/analysis/profiles/ar_v2/grounding.py`,
  `src/auditmanager/runs/recorded_v2_sources.py`, `src/auditmanager/runs/recorded_v2_stage.py`, `src/auditmanager/runs/recorded_v2_merge.py`,
  `src/auditmanager/runs/recorded_v2_publication.py`, `src/auditmanager/findings/v2_publication.py`, `src/auditmanager/findings/queries.py`,
  `src/auditmanager/analysis/stages/finding_merge.py`; migrations `0022_findings_v2`, `0023_norm_citations`.
- Tests: `tests/integration/runs/test_v2_recorded_executor_bridge.py::test_v2_bridge_commits_authority_before_stages_and_calls_gate_last`,
  `tests/integration/runs/test_v2_recorded_executor_bridge.py::test_v1_row_refuses_stray_v2_fixture_before_effects`,
  `tests/integration/findings/test_v2_recorded_chain.py::test_recorded_chain_merges_grounded_members_and_keeps_rejected_diagnostic`,
  `tests/integration/findings/test_v2_recorded_chain.py::test_live_context_is_refused_before_processing_or_writing`,
  `tests/integration/findings/test_v2_merged_read_projection.py::test_list_and_detail_return_one_canonical_finding_with_merged_member`,
  `tests/integration/findings/test_v2_merge_core.py::test_touching_endpoints_are_not_overlap`.
- Missing: the live model pin. `W56A-MODEL-PIN-01` is stopped (`CURRENT_STATE.md`); `D-197` and `D-199` name what changes the day a model is
  pinned. The recorded cases are synthetic (`D-183`).

**Path 3 — the v3 six-run beta behind the empty reviewed-pack registry.** One call of `startArV3BetaGroup` starts an atomic group of six Runs
(F1, F2, A1, A2, S1, S2) with immutable pins; `getArV3BetaGroup` and `getArV3BetaGroupReview` read them; `getArV3BetaPackStatus` says whether a
reviewed pack is installed. Both composition roots load the pack from the `AR_V3_BETA_PACK_MANIFEST` file; without it the registry is empty and a
start refuses `dependency_unavailable / ar_v3_trusted_pack` before any write or provider action. A started Run is dispatched, its reply is journaled
and saved, the CITE stage checks the citations, and the Run ends review-only: a provisional citation for expert verification, with no canonical
finding and no numerical conclusion.
- Source: `src/auditmanager/runs/v3_group.py`, `src/auditmanager/runs/v3_pack_manifest.py`, `src/auditmanager/runs/v3_pack_cli.py`,
  `src/auditmanager/runs/v3_execution_binding.py`, `src/auditmanager/runs/v3_execution_request.py`, `src/auditmanager/runs/v3_provider_call.py`,
  `src/auditmanager/runs/v3_reply_custody.py`, `src/auditmanager/runs/v3_cite_stage.py`, `src/auditmanager/runs/v3_review_terminal.py`,
  `src/auditmanager/runs/v3_review_reader.py`, `src/auditmanager/runs/v3_group_review.py`, `src/auditmanager/runs/v3_worker.py`,
  `src/auditmanager/analysis/profiles/ar_v3/v3_profile.py`, `src/auditmanager/analysis/profiles/ar_v3/citation_grounding.py`,
  `src/auditmanager/analysis/profiles/ar_v3/norm_map/map_pack.py`, `src/auditmanager/norms/retrieval/promote_cli.py`,
  `src/auditmanager/api/routers/ar_v3_groups.py`; migration `0032_ar_v3_run_group`; tools `auditmanager.analysis.profiles.ar_v3.norm_map.map_pack`,
  `auditmanager.norms.retrieval.promote_cli`, `auditmanager.runs.v3_pack_cli`, `scripts/norms/export_paragraph_rows.py`; deploy
  `infra/deploy/ar-v3-pack/README.md`, `infra/deploy/compose.server.yml`.
- Web: `web/src/features/start-ar-v3-group`, `web/src/widgets/ar-v3-beta-pack`, `web/src/widgets/ar-v3-beta-review`,
  `web/src/widgets/ar-v3-beta-status`, `/analysis-settings`.
- Tests: `tests/integration/db/test_ar_v3_run_group.py::test_no_pack_refuses_before_any_write`,
  `tests/integration/db/test_ar_v3_run_group.py::test_six_pins_replay_readback_and_refusals`,
  `tests/integration/api/test_ar_v3_pack_status_route.py::test_without_a_pack_the_answer_is_exactly_not_installed`,
  `tests/integration/api/test_ar_v3_group_review_route.py::test_group_review_route_returns_six_safe_outcomes`,
  `tests/integration/composition/test_v3_pack_install.py::test_without_the_variable_the_registry_is_empty`,
  `tests/integration/runs/test_v3_execution_guard.py::test_v3_identity_refuses_before_every_effect`,
  `tests/integration/runs/test_v3_worker_pipeline.py::test_first_attempt_dispatches_then_cites_then_terminates`,
  `tests/integration/runs/test_v3_cite_stage.py::test_success_commits_intent_before_blob_then_result_and_binding_together`,
  `tests/integration/runs/test_v3_review_terminal.py::test_success_publishes_only_review_stage`,
  `tests/integration/runs/test_v3_group_review.py::test_projection_excludes_internal_custody_and_model_payload`,
  `tests/integration/analysis/test_ar_v3_citation_grounding.py::test_norm_quote_and_both_value_failures_withhold_whole_proposal`,
  `tests/contract/norm_map/test_map_pack.py`, `tests/integration/norms/custody/test_promote_cli_db.py`,
  `web/tests/unit/analysis-settings/ar-v3-beta-pack-status.test.ts`, `web/tests/unit/analysis-settings/ar-v3-group-start-command.test.ts`.
- Owed from outside the repository (`D-204`, `AR-V3-BETA-ACTIVATION-RUNBOOK-01`): the owner's include / revise / exclude decision for each C01–C22
  branch; the missing official source pages; BGE-M3 query vectors with reproducible provenance; six reviewed maps and six verified sets; the
  qualified reviewer's attestation; the stand import. The reviewer attestation in the manifest is a record the loader checks for shape only (`D-212`).
  The activation runbook's last step (`AR-V3-BETA-ACCEPT-01`: recorded cases, a controlled live provider and cost check, the complete gate, user
  review of source-PDF links) has not run.
- Small code debts on this path: `D-207`, `D-208`, `D-184`.

**Status.** `code partial` — what is missing, each from the documents: (1) block and region analysis: the readers exist and are consumed by no
stage (see "Code that is still missing"); (2) a critic and chunked multi-call text analysis with safe resume; (3) a served norm-verification reader:
`getRunNormVerification` answers a typed 503 and no web file calls it; (4) a live pinned model for the v2 route; (5) the v3 route is review-only and
unactivated. **Remains:** the owner and a qualified expert for `D-204` and `D-178`; real-set quality (`D-167` is in-sample); the thresholds are
the owner's and are not in this tree.

## B4 — durable execution

- **Kind.** Code property; stand measurement.
- **Implemented paths.** `src/auditmanager/jobs/repository.py`, `src/auditmanager/jobs/lease.py`, `src/auditmanager/jobs/commands.py`,
  `src/auditmanager/jobs/events.py`, `src/auditmanager/runs/executor.py`, `src/auditmanager/runs/retry.py`, `src/auditmanager/runs/reconciliation.py`,
  `src/auditmanager/workers/service.py`, `src/auditmanager/workers/registry.py`, `src/auditmanager/execution/public.py`; operations
  `listExecutionJournal`, `listExecutionQueue`, `cancelRun`, `reauditRun`, `setJobPriority`, `setExecutionPaused`, `listWorkers`, `setWorkerIntake`;
  migrations `0014_durable_analysis_effects`, `0017_execution_queue`, `0019_execution_workers`; screens `/logs`, `/queue`, `/workers`; widget
  `web/src/widgets/execution-journal`.
- **Pinning tests.** `tests/integration/runs/test_retry_policy.py::test_an_unreachable_provider_is_retried_and_the_run_still_publishes`,
  `tests/integration/workers/test_worker_service.py::test_drain_finishes_the_run_in_flight_and_claims_no_more`,
  `tests/integration/workers/test_worker_service.py::test_a_killed_workers_run_is_reclaimed_and_finished_by_another_worker`,
  `tests/integration/jobs/test_d150_and_worker_claims.py::test_a_recorded_prepared_effect_is_settled_not_processed_and_the_run_resumes`,
  `tests/integration/jobs/test_d150_and_worker_claims.py::test_a_live_prepared_effect_still_fails_the_run`,
  `tests/integration/jobs/test_repeated_kill_names_the_stage.py::test_the_same_stage_killing_three_workers_is_named_on_the_run`,
  `tests/integration/runs/test_durable_effect_boundaries.py::test_an_ambiguous_live_failure_is_journalled_once_and_not_retried`,
  `tests/integration/qa_w53/test_queue_and_effect_journal.py::test_lease_reclaim_journals_the_effect_outcome`,
  `tests/integration/runs/test_w53_execution.py::test_journal_cursor_handles_equal_timestamps_and_newer_insert`,
  `web/tests/unit/execution/execution-screens.test.ts`.
- **Status.** `code present`.
- **What remains and who owns it.** No observation on a stand. By design a run in flight when a worker dies keeps its lease until it expires, and is
  then resumed when no provider effect can have spent (every recorded call, `D-150` (closed)) and failed as `provider_outcome_unknown` otherwise
  (`infra/deploy/README.md`, "The worker service"); so "restart resumes" holds for a recorded call and for a kill outside a live provider call, not for
  a live paid call. A provider failure cannot be induced on a live stand: its evidence is the database tests above or a fault-injecting proxy. Open:
  `D-155` (the pause is not in the journal; a contract change), `D-153`, `D-154`, `D-171`. Operator, integrator.

## B5 — real documents and the analysis envelope

- **Kind.** Stand measurement; real documents.
- **Implemented paths.** `src/auditmanager/ingest/pdf_reader.py`, `src/auditmanager/ingest/service.py`, `src/auditmanager/runs/commands.py`
  (`analysis_input_budget_exceeded`, 422, raised before the key is claimed), `src/auditmanager/analysis/text/budget.py`,
  `src/auditmanager/analysis/text/chunk_preflight.py`; operations `uploadDocument`, `uploadDocumentVersion`, `startRun`; edge `infra/deploy/proxy/nginx.conf`.
- **Pinning tests.** `tests/integration/ingest/test_size_guard_boundary.py::test_a_body_inside_the_window_is_refused_by_the_envelope`,
  `tests/integration/ingest/test_pdf_reader_bounds.py::test_a_small_pdf_that_would_cost_gigabytes_is_refused_by_its_rule_in_seconds`,
  `tests/integration/runs/test_input_budget.py::test_a_start_above_the_budget_is_refused_with_both_figures`,
  `tests/integration/runs/test_input_budget.py::test_a_start_exactly_at_the_budget_is_accepted`,
  `tests/integration/runs/test_input_budget_over_http.py`, `tests/integration/analysis_text/test_chunk_preflight.py`.
- **Status.** `code partial` (a larger text input gets a typed refusal; chunked analysis of it is prepared in `src/auditmanager/analysis/text/chunk_preflight.py` and consumed by no served stage).
- **What remains and who owns it.** No real document was run. The criterion's "separately ruled full-analysis envelope" is not defined in one place
  in the tree; the nearest rulings are the roadmap's `G-2` (a project document up to 500 pages and 250 MiB) and `G-11` (analysis up to an input
  budget, refused up front, chunked analysis left to W56). `D-162` (the budget models cost, not the model's context; the token constant was never
  measured on a live run of a real set), `D-171` and `D-175` (stage time against the 900 s attempt watchdog), `D-160`, `D-174` (the BFF upload memory
  was measured on the forward function alone), `D-168` (a PC-02 corpus check is red). Owner (the deferral `R-141c`), operator.

## B6 — backup and restore

- **Kind.** Code property (the tools and their refusals); stand measurement (the drill).
- **Implemented paths.** The `scripts/recovery/` tools, each with the test file of the same stem in `tests/integration/recovery/`:
  - drill and restore: `scripts/recovery/synthetic_drill_runner.py`, `scripts/recovery/synthetic_drill_fixture.py`,
    `scripts/recovery/synthetic_drill_seed.py`, `scripts/recovery/synthetic_drill_compare.py`, `scripts/recovery/isolated_restore_drill.py`,
    `scripts/recovery/isolated_postgres_restore.py`, `scripts/recovery/target_object_restore.py`, `scripts/recovery/target_blob_readback.py`;
  - evidence and audit: `scripts/recovery/offline_restore_preflight.py`, `scripts/recovery/offline_restore_audit.py`,
    `scripts/recovery/blob_reference_audit.py`, `scripts/recovery/blob_object_binding.py`, `scripts/recovery/copy_record_binding.py`,
    `scripts/recovery/schema_coverage.py` (declared head `0032_ar_v3_run_group`);
  - copies: `scripts/recovery/source_object_mirror.py`, `scripts/recovery/object_copy.py`;
  - the data purge: `scripts/recovery/product_purge.py`.
  Beside them: `scripts/stand-copy/restore-test.sh`, `infra/deploy/reset.sh`, `infra/deploy/purge-product-data.sh`, `infra/deploy/pull-copy.sh`.
- **Pinning tests.** Every test file of `tests/integration/recovery/` (318 passed with 0 failed on the lane stack, as recorded in
  `CURRENT_STATE.md`): `tests/integration/recovery/test_blob_object_binding.py`, `tests/integration/recovery/test_blob_reference_audit.py`,
  `tests/integration/recovery/test_copy_record_binding.py`, `tests/integration/recovery/test_isolated_postgres_restore.py`,
  `tests/integration/recovery/test_isolated_restore_drill.py`, `tests/integration/recovery/test_object_copy.py`,
  `tests/integration/recovery/test_offline_restore_audit.py`, `tests/integration/recovery/test_offline_restore_preflight.py`,
  `tests/integration/recovery/test_product_purge.py`, `tests/integration/recovery/test_product_purge_executor_events.py`,
  `tests/integration/recovery/test_product_purge_run_group.py`, `tests/integration/recovery/test_product_purge_script.py`,
  `tests/integration/recovery/test_schema_coverage.py`, `tests/integration/recovery/test_source_object_mirror.py`,
  `tests/integration/recovery/test_synthetic_drill_compare.py`, `tests/integration/recovery/test_synthetic_drill_fixture.py`,
  `tests/integration/recovery/test_synthetic_drill_runner.py`, `tests/integration/recovery/test_synthetic_drill_seed.py`,
  `tests/integration/recovery/test_target_blob_readback.py`, `tests/integration/recovery/test_target_object_restore.py`. Key functions:
  `tests/integration/recovery/test_schema_coverage.py::test_the_declared_head_is_the_alembic_head`,
  `tests/integration/recovery/test_synthetic_drill_runner.py::test_nonempty_bucket_refuses_before_engine_or_restore`,
  `tests/integration/recovery/test_isolated_restore_drill.py::test_coordinator_restores_db_before_target_write_then_reads_all_target_bytes`,
  `tests/integration/recovery/test_blob_reference_audit.py::test_healthy_database_returns_all_available_blob_facts_and_reads_only`.
- **Evidence in hand.** `RECOVERY-REBASE-01` (a synthetic drill at head `0028`) and `RECOVERY-DRILL-0029-01` (2026-10-22, head `0029`, recorded provider,
  exit 0 at every step: 23 of 23 objects and Blobs, 55 of 55 tables equal, an independent compare with no differences); the stand-copy tooling record
  `W54-STAND-COPY-01` (copy key, test-data waiver, deploy refusals). The `CURRENT_STATE.md` wording: a synthetic restore passed and the real drill was
  not run.
- **Status.** `code present`.
- **What remains and who owns it.** The real drill is a stand act, and no drill at head `0032` is recorded in the tree (the declared head moved
  from `0029` to `0032` in `DEV-PURGE-INVENTORY-01`). Not claimed by those records: a real stand backup, the stand's Blob store, `norm*` data,
  roles, W54 scale. `D-123` (the stand MinIO was never inventoried), `D-156` (the stand's test-data purge has not been run), `D-213` (hand-kept
  table inventories drift with every migration), `D-215` (the purge's quiescence guard ignores a claimed probe task). The owner judges whether a
  synthetic set is a B6 drill; the operator runs it.

## B7 — deploy bound to the gate, version, release history

- **Kind.** Code property; stand measurement; owner policy (the history entries).
- **Implemented paths.** `VERSION` (`0.8.1`), `src/auditmanager/releases/product_version.py`, `src/auditmanager/releases/build_id.py`,
  `src/auditmanager/releases/load.py`, `src/auditmanager/releases/notes.py`, `src/auditmanager/releases/repository.py`, `release-notes/0.8.1.json`
  (the notes run `0.2.0` to `0.8.1`), `docs/program/RELEASES.md`, `.github/workflows/deploy-auto.yml`, `infra/deploy/verify-deployed.sh`,
  `src/auditmanager/api/routers/releases.py`; operations `getProductVersion`, `listReleases`, `markReleaseNotesRead`; migration `0016_release_notes`;
  web `web/src/widgets/version-history`, `web/src/_app/release-notices.tsx`.
- **Pinning tests.** `tests/integration/releases/test_release_loader.py::test_loader_is_idempotent_and_serves_the_highest_revision`,
  `tests/integration/api/test_release_routes.py::test_stage_c_adapter_serves_the_running_version_and_visible_history`,
  `tests/contract/release_notes/test_release_notes_form.py::test_authored_shape_and_form`,
  `tests/contract/test_deploy_auto_workflow.py`, `web/tests/unit/release/history.test.ts`.
- **Status.** `code present`.
- **What remains and who owns it.** `CURRENT_STATE.md`: there is no `GATE OK`, no beta acceptance, and no complete gate can run on this host
  (`D-205`). The host verifier has not been run by an integrating session (`D-188`) and, in `CURRENT_STATE.md`'s words, host verification and the `v0.7.0` tag
  are owed; `RELEASES.md` rows and the `0.5.1` entry are behind the tree (`D-203`); the full-gate evidence for the release candidate is still due
  (`D-138`, `D-140`). "Bound to the gate" is an accepted process control, not a mechanism
  (`D-120`); the served build identity is a content digest (`D-121`). Owner (publication, tags), integrator (records), operator (verifier).

## B8 — exposure review

- **Kind.** Owner policy (what is exposed on purpose); stand measurement (a probe of the deployed origin).
- **Implemented paths.** `src/auditmanager/api/security.py` (the open register `UNAUTHENTICATED_OPERATIONS`; `RUNNER_OPERATIONS`, which are
  `claimExecutorTask`, `extendExecutorTaskClaim`, `submitExecutorTaskAnswer`, `failExecutorTask`, `getExecutorTaskImage`, authenticated by a runner
  token and by nothing else), `infra/deploy/compose.server.yml`, `infra/deploy/proxy/nginx.conf`, `infra/deploy/proxy/trusted-proxies.sh`,
  `web/src/app/bff/v1/[...path]/route.ts`.
- **Pinning tests.** `tests/integration/api/test_authorization.py::test_the_open_surface_is_exactly_the_register`,
  `tests/integration/api/test_role_register.py::test_every_guarded_operation_is_in_the_role_register`,
  `tests/contract/test_proxy_security_headers.py`, `tests/contract/test_proxy_rate_limits.py`,
  `tests/integration/composition/test_edge_credential_gate.py`, `tests/integration/composition/test_exposure_text_is_current.py`,
  `tests/integration/composition/test_real_client_address_at_the_edge.py`, `tests/e2e/test_upload_limit_headroom.py`.
- **Status.** `code present`.
- **What remains and who owns it.** The only review in the tree is `EXPOSURE-REVIEW-01`, dated 2026-10-21: it predates the runner channel
  (`0031_executor_pull_channel`) and the v3 routes, and the lane found no later probe of a deployed origin recorded. Open: `D-191` (the host's TLS terminator is outside the
  repository: the `Secure` cookie, HSTS, certificate renewal), `D-144`, `D-165` (the edge buffers an authenticated upload body), `D-166` (no
  container memory limit), `D-122` (no dependency or image scan), `D-212` (the pack manifest is tamper evidence, not a signature). Owner decisions
  and the operator's host settings; a fix that touches `infra/**` also needs a complete gate (`AGENTS.md` §8).

## B9 — contract and error catalogue frozen

- **Kind.** Code property (the freeze and its pins); stand measurement (the served `contract_version`).
- **Implemented paths.** `contracts/api/v1/openapi.json` and its copy `web/openapi/openapi.json`; `contracts/domain/v1/error-codes.json`
  (27 codes), `contracts/domain/v1/identifiers.json`, `contracts/domain/v1/state-machines.json`; `contracts/analysis/v1/`, `contracts/events/v1/`;
  `src/auditmanager/shared/errors/codes.py`; `web/FRONTEND_LOCK.json`; migration `0029_routing_refusal_codes`.
- **Pinning tests.** `tests/contract/api_v1/test_contract_seal.py::test_the_facts_file_names_the_sealed_version`,
  `tests/contract/api_v1/test_contract_seal.py::test_every_json_artifact_of_a_family_declares_only_the_sealed_version`,
  `tests/contract/api_v1/test_contract_seal.py::test_the_application_constants_are_the_sealed_version`,
  `tests/contract/api_v1/test_contract_seal.py::test_the_catalog_is_frozen_with_all_twenty_seven_codes`,
  `tests/contract/api_v1/test_routing_refusal_codes.py`, `tests/integration/db/test_routing_refusal_codes_migration.py`.
- **Status.** `code present`.
- **What remains and who owns it.** The criterion names `1.0.0`; the shared contract is `1.5.0` (additive minors after the `1.0.0` seal,
  `BETA-CONTRACT-SEAL-01`; the last is `AR-V3-BETA-PACK-STATUS-API-01`). `CODE-FIRST-TO-BETA.md` §3 says the contract version changes only in the
  final beta seal. Whether the `1.x` line meets B9 as written is the owner's reading and is not decided here. The served `contract_version` has not
  been read from a stand; no complete gate exists (`D-205`). Contract-bound rows carried on purpose: `D-145`, `D-163`, `D-172`; two literal `1.0.0`
  values remain in tests (`D-210`). Owner, integrator.

## B10 — expert smoke sessions

- **Kind.** Expert. **Status.** `not a code property`.
- **What exists.** The protocol `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`, the acceptance script `scripts/manual-alpha-check.sh`, and the
  screens of B12 for the experts to use.
- **What remains and who owns it.** Named experts with committed slots (`OD-18`); the stand run and the human pass (`D-137`, `D-139`). Owner,
  experts. Deferred by `R-141c`.

## B11 — retained client data

- **Kind.** Owner policy. **Status.** `not a code property`.
- **What exists.** The wipe `infra/deploy/reset.sh`; the explicit, dry-run-first purge `infra/deploy/purge-product-data.sh` over
  `scripts/recovery/product_purge.py`, which keeps accounts and the norm corpus; tests `tests/integration/recovery/test_product_purge.py` and
  `tests/integration/recovery/test_product_purge_script.py`. `R-141c` says no real client document is uploaded to a closed-beta stand.
- **What remains and who owns it.** The retention policy `U-04` is undecided (the contract's `OPEN-RETENTION` declares no window); `D-156` closes
  only when the operator has run the purge on the stand; the licence question for an external beta (`NORM-Q04`) and the exposure and registration
  mail decisions are the owner's. `D-215` is a small open code defect in the purge's quiescence guard. Deferred by `R-141c`.

## B12 — every menu destination: action, result, live acceptance

**Source of the list:** the rows of `web/src/shared/config/screen-registry.ts` with `inMenu: true` (14 destinations), read by the lane, each through its
route file `web/src/app/…/page.tsx` to its page component under `web/src/_pages/`. **The stub inventory is static: it reads source, not a browser.**
`RoutePlaceholder` is defined in `web/src/shared/ui/route-placeholder.tsx` and no source file outside `web/src/shared/ui` references it
(`docs/program/tasks/BETA-STATIC-MATRIX-02.md` P-02). That a component imports a widget says nothing about what a browser renders; `D-149` records
that the web has no DOM interaction-test layer (Vitest runs in `node`).

| Destination (registry label) | Address | Page component | What acts behind it | Journey route and write steps (names in `tests/e2e/pc01/journey/manifest.json`) |
| --- | --- | --- | --- | --- |
| Главная | `/` | `HomePage`, `web/src/_pages/home/ui/home-page.tsx` | `web/src/widgets/home-tiles`, `web/src/widgets/my-tasks` (take, complete, return an assignment) | `root`; `my-tasks-take-the-work`, `my-tasks-give-the-work-back` |
| Проекты | `/projects` | `ProjectsPage`, `web/src/_pages/projects/ui/projects-page.tsx` | `web/src/features/create-project`, `web/src/widgets/project-list`; the project screens below it (upload, classify, run, review, compare, price lists, proposals) | `projects`, `project`, `document`, `version`, `comparison`, `run`, `review`; `create-project`, `upload-document`, `classify-version`, `start-run`, `record-decision`, `compare-versions-read-only`, `carry-over-decision`, `price-list-upload`, `optimisation-pass`, `proposal-accept`, `classification-correction` |
| Дашборд | `/dashboard` | `DashboardPage`, `web/src/_pages/dashboard/ui/dashboard-page.tsx` | `web/src/widgets/dashboard` (`getDashboardSummary`) | `dashboard`; `dashboard-sections-panel` |
| Оптимизация разделов | `/section-optimisation` | `SectionOptimisationPage`, `web/src/_pages/section-optimisation/ui/section-optimisation-page.tsx` | `web/src/widgets/section-specification` (`getSectionSpecification`) | `section-optimisation`; `section-form7`, `section-form7-without-members` |
| Диспетчер | `/dispatcher` | `DispatcherPage`, `web/src/_pages/dispatcher/ui/dispatcher-page.tsx` | `web/src/features/create-assignment`, `web/src/features/transition-assignment`, `web/src/widgets/assignment-board` | `dispatcher`; `assign-work`, `dispatcher-expert-sees-only-the-own-work`, `assign-work-to-be-given-back` |
| База знаний | `/knowledge-base` | `KnowledgeBasePage`, `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx` | `web/src/widgets/knowledge-base` (`listDecisions`; read-only by design) | `knowledge-base`; no write step |
| Блоки | `/blocks` | `BlocksPage`, `web/src/_pages/blocks/ui/blocks-page.tsx` | `web/src/widgets/portal-blocks` (`listVersionPortalBlocks`, `streamVersionPortalBlockCrop`, `getVersionBlocks`) | `blocks`; `blocks-portal-blocks-of-a-version-with-a-run`, `blocks-text-lines-of-the-same-version`, `blocks-a-version-no-run-has-read-says-so` |
| Нормы | `/norms` | `NormsPage`, `web/src/_pages/norms/ui/norms-page.tsx` (`NormDocumentPage` for `/norms/document`) | `web/src/features/set-current-snapshot`, `web/src/widgets/norm-search`, `web/src/widgets/norm-catalogue`, `web/src/widgets/norm-snapshots`, `web/src/widgets/norm-document` | `norms`, `norm-document`; `norms-designate-the-current-snapshot`, `norms-search`, `norms-catalogue`, `norms-document-text-and-pdf` |
| Журнал выполнения | `/logs` | `LogsPage`, `web/src/_pages/logs/ui/logs-page.tsx` | `web/src/widgets/execution-journal` (`listExecutionJournal`; read-only by design) | `logs`; no write step |
| Исполнители | `/workers` | `WorkersPage`, `web/src/_pages/workers/ui/workers-page.tsx` | `web/src/features/set-worker-intake`, `web/src/widgets/worker-list`, `web/src/widgets/executor-connections`, `web/src/widgets/executor-routes` | `workers`; `workers-list-the-worker`, `worker-stops-taking-new-work`, `worker-takes-new-work-again` |
| Настройки анализа | `/analysis-settings` | `AnalysisSettingsPage`, `web/src/_pages/analysis-settings/ui/analysis-settings-page.tsx` | `web/src/widgets/analysis-profile-table` (`listAnalysisProfiles`), `web/src/widgets/ar-v3-beta-pack`, `web/src/widgets/ar-v3-beta-review`, `web/src/widgets/ar-v3-beta-status` | `analysis-settings`; `analysis-settings-lists-the-profiles`, `analysis-settings-for-an-expert` |
| Очередь | `/queue` | `QueuePage`, `web/src/_pages/queue/ui/queue-page.tsx` | `web/src/features/pause-execution`, `web/src/features/set-job-priority`, `web/src/features/cancel-run`, `web/src/features/reaudit-run`, `web/src/widgets/execution-queue` | `queue`; `queue-pause-dispatch`, `queue-change-priority`, `queue-cancel-the-waiting-run`, `queue-reaudit-the-cancelled-run`, `queue-resume-dispatch` |
| Пользователи (admin) | `/admin/users` | `AdminUsersPage`, `web/src/_pages/admin-users/ui/admin-users-page.tsx` | `web/src/widgets/user-list`; the user card on `/admin/users/[user_uid]` | `admin-users`, `admin-user`; `user-archive`, `user-restore`, `user-password-reset` |
| Заявки на регистрацию (admin) | `/admin/registrations` | `AdminRegistrationsPage`, `web/src/_pages/admin-registrations/ui/admin-registrations-page.tsx` | `web/src/widgets/registration-queue`, `web/src/features/decide-registration` | `admin-registrations`; no write step in the core journey (approve and reject are in the identity continuation) |

**Account menu** (`web/src/_app/account-menu.tsx`, four actions): «Профиль» opens `/account` (steps `profile-update`), «Сменить пароль» opens
`/account/password` (steps `password-change`), «История версий» opens the panel `web/src/widgets/version-history` (step `release-history-panel`),
«Выйти» posts to the session door `web/src/app/bff/v1/[...path]/route.ts` (steps `sign-out`, `signed-out-session-is-gone`).

- **Operations that no manifest `operationId` field names** (read from the manifest by the lane; 27 of the 104): `archiveExecutorConnection`,
  `changePassword`, `claimExecutorTask`, `createExecutorConnection`, `extendExecutorTaskClaim`, `failExecutorTask`, `generateExecutorSshKey`,
  `getArV3BetaGroup`, `getArV3BetaGroupReview`, `getArV3BetaPackStatus`, `getAssignment`, `getExecutorTaskImage`, `getProductVersion`,
  `getRunNormVerification`, `issueRunnerToken`, `issueToken`, `listOptimisationPasses`, `listPriceListPositions`, `listProposalDecisions`,
  `readRegistrationStatus`, `requestExecutorProbe`, `reviseExecutorConnection`, `revokeRunnerToken`, `setExecutorRoute`, `setExecutorSecret`,
  `startArV3BetaGroup`, `submitExecutorTaskAnswer`. The administrator's executor writes (connections, routes, tokens, the key form) and the AR v3 group
  start are pinned by unit and integration tests, not by a journey step: `web/tests/unit/workers/executor-connections.test.ts`,
  `web/tests/unit/workers/executor-commands.test.ts`, `web/tests/unit/workers/executor-secret-door.test.ts`,
  `web/tests/unit/analysis-settings/ar-v3-group-start-command.test.ts`, `tests/integration/executors/test_executor_commands.py`,
  `tests/integration/executors/test_runner_channel.py`. The five runner operations are never called by a browser.
- **Pinning tests.** `tests/e2e/test_pc01_journey_conformance.py::test_the_journey_walks_every_screen_the_application_offers`,
  `tests/e2e/test_pc01_journey_conformance.py::test_the_night_window_steps_agree_with_the_contract_and_with_each_other`,
  `web/tests/guards/screen-registry.guard.test.ts`, `web/tests/guards/screen-set.guard.test.ts`, `web/tests/guards/prepared-sections.guard.test.ts`,
  `web/tests/guards/rendered-language.guard.test.ts`, `web/tests/unit/shell/navigation.test.ts`, `web/tests/unit/ui/menu.test.ts`; per screen
  `web/tests/unit/dispatcher`, `web/tests/unit/execution`, `web/tests/unit/norms`, `web/tests/unit/sections`, `web/tests/unit/section-specification`,
  `web/tests/unit/optimisation`, `web/tests/unit/optimisation-proposals`, `web/tests/unit/comparison`, `web/tests/unit/workers`,
  `web/tests/unit/release`, `web/tests/unit/session`, `web/tests/unit/analysis-settings`; backend `tests/integration/dispatch`,
  `tests/integration/optimisation`, `tests/integration/sections`, `tests/integration/comparison`, `tests/integration/exports`,
  `tests/integration/dashboard`.
- **Status.** `code present`: every in-menu row reaches a page component that reaches a widget or feature, and the four account actions exist.
- **What remains and who owns it.** (1) Live acceptance on a stand. The journey (109 write steps, 29 routes; `PC01-JOURNEY-GAPS-01`) ran green on a
  recorded local stack at migration head `0029`; `scripts/manual-alpha-check.sh` runs the `core` phase on a stand and `--phase all` needs
  `--allow-spend` (`D-186`). (2) The clause "the full АР function matrix is tested" has no definition in the tree (`PC01-JOURNEY-GAPS-01` says
  so); the owner defines it. (3) Three rows of the table above have no write step in the core journey: «База знаний» and «Журнал выполнения» are read-only by design, and
  «Заявки на регистрацию» acts (approve, reject) only in the identity continuation. None is a stub by the static scan; whether reading counts as "an
  actual action" is the owner's reading. (4) `D-149`, `D-186`. Owner, operator.

## Cross-cutting facts measured on 2026-10-26

Only numbers recorded in `docs/program/CURRENT_STATE.md` or in the lane reports it names; this lane re-measured none of them except the surface and the
menu (the lane re-read `openapi.json`, `VERSION` and the registry; `docs/program/tasks/BETA-STATIC-MATRIX-02.md` P-01 and P-02).

- Development API surface **92 paths / 104 operations / 300 schemas**; the error catalogue has 27 codes; migration head `0032_ar_v3_run_group`;
  `VERSION` `0.8.1`; shared contract `1.5.0`.
- Measured by the `AR-CLOSE-1026` integrator on the exact tree `5ed7aa62`, with no complete gate (`CURRENT_STATE.md`): `tests/contract` 1143 passed;
  web lint and typecheck clean; the full Vitest suite 2934 passed in 193 files; the whole `tests/integration` directory 8537 passed, 26 skipped,
  0 failed on a real PostgreSQL and MinIO lane with the corpus symlink attached. Later commits changed documents, one test comment and the audit-event
  keep predicate of `scripts/recovery/product_purge.py` with its tests, after which the whole `tests/integration/recovery` directory ran 318 passed,
  0 failed. That directory had been red on the clean `origin/dev` tip `354a9092`; see `D-213` and `D-214`.
- **No complete `make gate` was run and none can run on this host** (`D-205`): there is no `GATE OK` and no beta acceptance, and `origin/main` is
  untouched in this window (`CURRENT_STATE.md`).
- The debt register was re-measured by three audits (`DEBT-AUDIT-1`, `DEBT-AUDIT-2`, `DEBT-AUDIT-3`); `D-206` records that it was stale in places.
  `CURRENT_STATE.md` puts open work at `D-204` to `D-212` and the rows the audits kept open; `D-213`, `D-214` and `D-215` were registered afterwards.
  Every row this document calls open or closed was read in the register on this tree.
- The activation sequence for the AR v3 beta is `AR-V3-BETA-ACTIVATION-RUNBOOK-01`; its steps are data and review that no code supplies (`D-204`).

## Code that is still missing

Each item is taken from the documents named; none is inferred.

**Code.**

1. **Block, region and drawing analysis (W56b).** The Attempt-fenced readers for text windows, crops and recognised regions exist
   (`src/auditmanager/runs/text_window_input.py`, `src/auditmanager/runs/geometry_crop_input.py`, `src/auditmanager/runs/geometry_crop_item_input.py`,
   `src/auditmanager/runs/recognised_region_input.py`) and no executor stage consumes them. `CURRENT_STATE.md`: no run stage sends an image until
   W56b activates its image policy, and the image stage still does not create a task; a graphical-analysis stage needs the W56b prompt and evidence
   policy first. The vision budget is the owner's (`ROADMAP-TO-BETA.md` G-3).
2. **A critic and multi-call text analysis with safe resume.** `ROADMAP-TO-BETA.md` H-10 puts the critic in W56b; `src/auditmanager/analysis/text/budget.py`
   says a stage that adds calls must revisit the input budget; no source file implements a critic.
3. **A served norm-verification reader.** `getRunNormVerification` answers a typed 503 `dependency_unavailable` (`src/auditmanager/api/routers/runs.py`,
   `src/auditmanager/bootstrap/adapters.py`) and has no web caller.
4. **The AR v2 live model pin.** `W56A-MODEL-PIN-01` is stopped (`CURRENT_STATE.md`); `D-197` and `D-199` name what changes the day a model is pinned.
5. **Other code debts still open on this tree:** `D-184` (geometry-aware specification extraction), `D-185` (a work-estimate refusal needs a contract
   change), `D-207`, `D-208`, `D-209`, `D-210`, `D-215`, `D-164`, `D-160`.
6. **Contract-bound rows carried on purpose past the seal:** `D-145`, `D-163`, `D-172`; and `D-153`, `D-154`, `D-155`.

**Listed with the code because the criteria need them, but not code.**

7. **The v3 activation.** An installed reviewed pack and the data behind it (`D-204`); until then every group start refuses. Numerical findings stay
   unavailable until an expert decision and an edition check exist (`AR-V3-BETA-ACTIVATION-RUNBOOK-01`).
8. **A real restore drill.** A stand act; `CURRENT_STATE.md` records that the synthetic restore passed and the real drill was not run.
9. **Expert review of the 14 non-AR text profiles** (`D-178`) and field recordings (`D-183`); all of them are synthetic.

## What this matrix does not establish

- That any criterion is met. B1–B12 are measurements on a deployed stand; no row is `PASS`, and the stand is not described here.
- That a cited test passes. The lane checked that each named file and function exists and that the Python files collect. The recorded figures
  above are copied from `CURRENT_STATE.md` and belong to the tree it names.
- That the screens render or behave. The stub inventory is static. The recorded browser-journey runs (`BETA-LIVE-JOURNEY-01`,
  `PC01-JOURNEY-GAPS-01`) were on recorded local stacks at trees older than this one, the latter at head `0029`, and nothing here re-ran them. The web
  has no DOM interaction-test layer (`D-149`).
- That the debt register is exact. `D-206` says it was stale in places; the lane read each cited row and its open or closed state on this tree and
  did not run the rows' own check commands.
- Anything about `origin/main`, tags, deployments, workflow runs, host verification or the live `admin` credential: none is readable from the tree.
- That a recorded profile, a draft section profile or a review-only citation is an expert's decision, a legal-source check or an approval. No
  approval and no expert decision is claimed anywhere in this document.
- Quality. The only quality figure this document cites is the in-sample precision `D-167` records; the lane did not look for others, and a recorded
  or synthetic case is not field evidence (`D-183`).

## Verification of this document

The lane's existence check lives outside git (the lane's scratchpad, `m1/verify_matrix.py`). It extracts every backticked token, and every path-like
word of a backticked command, that looks like a path, an `operationId`, an API route, a migration name, a screen address, a journey step name, a debt
id (and checks its open or closed state against the `(closed)` mark), a test function, a python module, a task or report id or a ruling id, and checks
it against the tree, `contracts/api/v1/openapi.json`, `tests/e2e/pc01/journey/manifest.json` and the register. It also checks that the matrix has one
row per criterion with exactly one status word, that the B12 table names all 14 in-menu addresses derived from the registry, that the list of
operations no manifest field names equals the set derived from the manifest, that every `scripts/recovery/` tool and every test file of
`tests/integration/recovery/` is named, and that every figure of the form "N passed", "N files" or "N skipped" is one `CURRENT_STATE.md` records.
Its final output, the collect-only result, the guard results and the mutation proofs (each check shown to fail under a quoted mutation) are quoted
in the Handoff of `docs/program/tasks/BETA-STATIC-MATRIX-02.md` and in the lane's hand-back.
