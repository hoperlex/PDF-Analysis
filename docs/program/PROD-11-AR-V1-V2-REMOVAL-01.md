# PROD-11-AR-V1-V2-REMOVAL-01 — АР v1 and v2 are removed; the contract is resealed; the web and the journey follow

Task: `docs/program/tasks/PROD-11-AR-V1-V2-REMOVAL-01.md` (premise P-01 to P-08, decisions D-1 to D-15). Branch `agent/prod-11-ar-v1-v2-removal-01`, base `1c8d29fa` (`integration/ar-close-1026`). Wave `PW3`, lane R. Design: `ADR-0024` section 2 (`AD-12`, `R-146g`, `R-146l`, `R-146m`, `R-146w`); `D-223`. Nothing here was pushed, tagged or merged; no docker, no network, no paid call.

## Result

| Stage | Commit | State |
| --- | --- | --- |
| 0 premise | `25a17a7d` | done; one item of the brief differs (P-05), one conflict is decided (P-03, D-4) |
| 1 server | `88503541` | done |
| 2a contract content | `22c1df66` | done (`builtin` removed, `reviewed` described as it is, prose corrected) |
| 2-3 web + client + lock | `a7c0192a` | done |
| 2b contract version | `b7e5fdf1`, `56b25ebe` | done, **proposed `1.7.0`**, two commits that can be dropped or re-run |
| 4 tests / fixtures | inside stage 1 | done, with one deviation: `fixtures/recorded/text_analysis` is not deleted (P-05, D-3) |
| 5 journey | `357ceb07` | done |
| report | this commit | |

What the product does now. `startRun` and `reauditRun` on a version classified АР answer `422 section_profile_unavailable` before the idempotency key is claimed (the routing of `W59-SECTION-SEAL-01`, unchanged; the registry no longer holds АР); the error catalogue keeps its 27 codes. `listAnalysisProfiles` answers `profile: null` for АР. An unrouted `execute_run` (no registry) refuses a non-v3 run (`required_norm_unavailable`) instead of running АР. The web sends an АР version to the six-check control and tells it why there is no other start. The 33 АР-bound journey steps are reported `PENDING`, not run and not passed.

## Premise (details in the task file)

- Removal list and import graph (P-01, P-02): three surviving `src` files imported the removed set (`analysis/public.py`, `findings/public.py`, `runs/executor.py`) and all three are edited; one more took a v2 constant by name (`findings/queries.py`). After the removal the committed guard `tests/unit/analysis/test_ar_v1_v2_removal.py` proves it for `src`, `tests`, `tools` and `scripts`.
- **Differs from the brief (P-05).** `fixtures/recorded/text_analysis` is read by more than АР v1: the builder and the provenance of the 14 section recordings (`inputs/ar_baseline_text_layer.json`), `RecordedAdapter()`'s default directory (shipped in the API image), the recovery drill seed, the e2e fixtures and ~15 machinery tests. It stays; nothing in it is an АР registration.
- Versioning rule (P-03, D-1): minor for an optional addition, patch for a clarification, major or a bridge for a removal or a meaning change. This reseal removes one member of a response-only enum and narrows `startRun` for АР through an existing error code; the lane proposes **`1.7.0`** and records the strict reading (a major).

## Files

Counts from `git diff --stat 1c8d29fa..HEAD` (before this report): 284 files changed, 2535 insertions(+), 10774 deletions(-); `src` +141/-3802, `tests` +1385/-6162, `web` +376/-145; 56 files deleted (23 in `src`, 30 tests, 3 tools), 5 added, 3 renamed.

| Group | What |
| --- | --- |
| deleted `src` (23) | `analysis/profiles/ar_v2/` (14 files), `runs/recorded_v2_{merge,publication,sources,stage}.py`, `findings/{v2_publication,v2_recorded,recorded_saved_plan,merge_publication_plan}.py`, `analysis/stages/finding_merge.py` |
| edited `src` | `analysis/public.py`, `analysis/text/{__init__,__main__,profile,profile_registry,stage}.py`, `findings/{public,queries}.py`, `runs/executor.py`, `bootstrap/{composition,adapters}.py`, `api/schemas/models.py`, `api/routers/analysis_profiles.py`, docstrings of `ar_shared/{__init__,v2_identities}.py` and `executors/answers.py`; the three `CONTRACT_VERSION` constants (stage 2b) |
| contract | `contracts/api/v1/{openapi.json,README.md}`, `web/openapi/openapi.json` (byte-identical copy), `contracts/{domain,analysis,events}/**` (version literals; domain `supersedes`/`candidate_revision` 25), `tests/support/expected_facts.json` |
| web | `entities/analysis-profile`, `widgets/{analysis-profile-table,run-list,version-classification}`, `features/classify-version`, `_pages/version-detail`, the generated client (4 files), `FRONTEND_LOCK.json`, ~40 test files with the version literal (stage 2b), 4 test files edited for content, 1 added |
| tests deleted (30 files, 199 test functions) | listed below |
| tools / scripts / fixtures | `tools/evaluation/{bridge,run_sources,local_bundle}.py` deleted; `scripts/recovery/synthetic_drill_seed.py` and `fixtures/recorded/sections/ar_specification/build_fixtures.py` repointed |
| edge | 4 literals in `infra/deploy/proxy/{nginx,tls-server}.conf` (stage 2b only) |
| journey | `manifest.json` (33 marks, a reason, the registry pin), `write.mjs`, `journey.mjs`, `verify-acceptance.mjs`, `write.test.mjs`, `README.md`, `test_pc01_journey_section.py`; one line of `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` |

Deleted test files (30): `tests/integration/analysis/test_ar_v2_{merge_input,prompt_material,proposal_grounding,recorded_artifact,recorded_call,recorded_input,recorded_request,recorded_response,recorded_stage_result,registered_profile,response_parser,response_pipeline,response_schema}.py`; `tests/integration/findings/test_{analysis_public_boundary,merge_publication_plan,v2_merge_core,v2_publication_sql,v2_recorded_chain,v2_recorded_saved_plan}.py`; `tests/integration/jobs/test_recorded_v2_{executor_bridge_db_accept,publication_gate}.py`; `tests/integration/runs/test_{recorded_v2_sources,v2_recorded_durable_stage,v2_recorded_executor,v2_recorded_executor_bridge,v2_recorded_merge_stage}.py`; `tests/contract/evaluation/test_bridge.py`; `tests/integration/evaluation/test_{local_bundle,run_sources}.py`; `tests/unit/analysis/test_ar_v3_independent_of_ar_v2.py` (replaced by `test_ar_v1_v2_removal.py`). Three of the old `test_ar_v2_*` files tested modules that moved to `ar_shared` and survive: renamed `test_ar_shared_{grounding_prep,recognised_context,profile_content}.py`. The ADR's "about 65" is of the same order as 30 deleted plus 103 Python test files modified (most of them mechanically); most files that named `AR_TEXT_PROFILE` test the v1 machinery and were kept.

New: `tests/support/v1_reference_profile.py` (the removed constant's objects, same `content_sha256`), `tests/support/published_run.py`, `tests/unit/analysis/test_ar_v1_v2_removal.py` (25 tests), `web/tests/unit/screens/run-list-ar-start.test.ts` (14).

## Modified tests: what each asserted before and after

Mechanical (no assertion touched): about 55 of the modified Python test files received `text_profiles=resolve_reference_profile` or `profile=V1_REFERENCE_PROFILE` (the executor and the stage no longer default to АР) and imported `V1_REFERENCE_PROFILE` for `AR_TEXT_PROFILE`; the shared run harness seeds the reference pair instead of a random pair; `_build_provider` unpacking went from five to three names (4 files).

| Test | Before | After |
| --- | --- | --- |
| `test_text_profile_registry` empty root | registers АР from the v1 constants | registers nothing; `section_profiles()` is `{}` |
| same, `resolve` | the АР pair resolves, mismatches refused | the АР pair is unregistered, KJ's pair resolves, mismatches refused |
| same, defective package | `ar` + `AR` → `section_code_duplicate` | `section_code_not_a_text_profile` (and a `kj` directory holding АР) |
| same, real tree | АР is the v1 constants; fifteen entries | no АР entry or package; fourteen entries; `executable_sections` = the fourteen |
| `test_profile_identity_is_pinned` | pinned the profile and `resolve_profile` (unknown identity refused) | the identity, bundle, version, discipline, stage and categories stay pinned on the reference profile and on the retired id in `src`; the 3 `resolve_profile` tests are gone with the function |
| `test_profile_and_artifact` | resolved the АР profile by identity (2 tests) | those 2 are gone with `resolve_profile`; the prefix assertions stay |
| `test_ar_shared_profile_content` | `named == AR_V2_CATEGORIES` | `named == NONNORMATIVE_CATEGORIES` (same seven values, v3's constant) |
| `test_ar_v3_response_schema` | `NONNORMATIVE == V2_CATEGORIES` | `NONNORMATIVE == (the same seven literals)` |
| `test_ar_v3_prompt_material` | `material_sha256() == 01bee0…` (the v2 fingerprint of corpus + v2 rules + v2 schema) | `reviewed_content_sha256() == 0b560e…` (the corpus v3 reuses; **narrower**, the v2 scaffold no longer exists) |
| `test_runner_answers` | three schemas judgeable (v1, ar_v2, ar_v3) | two (v1, ar_v3) |
| `test_ar_v2_seeded` | also froze `local_bundle`'s manifest digest | that test is gone with the module |
| `test_analysis_profiles_over_http` | АР row `builtin`, no source; fifteen profiles | АР row `profile: null`; fourteen profiles |
| `test_w59_routed_execution` | an АР-routed run reproduces the corpus run | an АР version cannot start (422, no row, no command record); a ПБ-routed run reproduces the corpus run end to end |
| `test_w59_section_routing_over_http` | review: fifteen executable; АР pins the v1 pair | fourteen (thirteen without ПБ), АР not executable; АР start and re-audit refused 422 and leave nothing |
| `test_classification_correction_over_http` | run pinned to the АР pair, then corrected to КЖ | the same claims with КЖ then ТХ |
| `test_w59_classification_command` | `"AR" in without_kj` | `"AR" not in … and {"PB","TX"} <= …` (the refusal holds while other sections stay registered) |
| `test_section_recordings` | registry = АР + fourteen; АР entry has no source | registry = fourteen, АР absent |
| `test_the_served_application_routes_by_section` | the table covers all fifteen | fourteen, АР absent |
| composition: reports_itself, carryover, blocks, comparison | classify АР, start, publish | classify ПБ (same recording content), start, publish |
| composition: optimisation, section_specification, specification_prices; `test_ar_specification_journey` | `POST /runs` on an АР version publishes | `POST /runs` is asserted refused (422 `section_profile_unavailable`); the published run is made in-process |
| `tests/integration/qa_w55b` | classification АР | ПБ |
| characterization (`journey.py`, 4 records, 2 digest tests) | version classified АР | `KJ` with the reference profile registered under it for the journey; 4 records move by the section code alone (new digest test against the base); the 16 stale refusal records are red before and after |
| `test_provider_modes` standalone runner | `main([path, --capture …])` | `main([path, --section PB, --capture …])` (the runner needs a section) |
| `test_v3_saved_text_layer_probe` v1 control | pinned a literal pair, ran under the unrouted default | pins the reference pair and passes the resolver |
| web `analysis-settings`, `rendered-language`, `styles/screens` fixtures | АР `builtin`, no source | АР `profile: null`; `builtin` refused as an unknown status |
| web `classification-panel` | one hint for a non-executable section | АР has its own sentence; the others keep theirs (+3 tests) |

No assertion was relaxed. Narrowed with the thing it measured: the `material_sha256` pin (row above) and the two schema/fingerprint comparisons that named modules which no longer exist.

## Mutation tables

Each mutation was applied alone to the committed tree, the named tests were run, the file was restored (`git status` empty after each).

Stage 1 (container-free unless noted):

| Mutation | Result |
| --- | --- |
| M1 `NOT_A_TEXT_PROFILE` is not `AR` | 2 failed in `test_text_profile_registry` (`…not_a_text_profile`, both cases) |
| M2 АР registered again in `load_text_profile_registry` | 13 failed in registry, removal guard, `test_w59_routed_execution`, `test_w59_section_routing_over_http`, `test_analysis_profiles_over_http` (DB) |
| M3 an unrouted run falls back instead of refusing | `test_an_unrouted_run_is_refused_not_given_the_ar_profile` red |
| M4 `run_text_analysis(profile=None)` default | `test_run_text_analysis_has_no_default_profile` red |
| M5 `findings/public.py` imports `ar_v2.registered` | `test_no_python_file_imports_a_removed_module` red (+2) |
| M6 `runs/recorded_v2_stage.py` recreated | `test_the_removed_files_are_absent` red |
| M7 `AR_TEXT_PROFILE = None` back in `profile.py` | `test_the_ar_v1_profile_constant_and_its_resolver_are_gone_from_src` red |
| M8 `AR_V2_CATEGORIES` listed in `analysis/public.py` `__all__` | `…none_lists_one` red |
| M9 retired АР identity edited | `test_the_profile_identity_is_the_pinned_literal` red (+1) |
| M10 reference profile drifts (`profile_version`) | `test_the_reference_profile_of_the_tests_is_the_removed_ar_constant_byte_for_byte` red |
| M12 record 13 says `AR` again | `test_the_four_classification_records_moved_by_the_section_and_nothing_else` and the record comparison red |

Stage 3 (vitest): W1 the run list ignores the section → 9 red; W2 the page does not hand the section over → 1; W3 the table words АР as a missing profile → 1; W4 `builtin` label back → 1; W5 the form promises a profile for АР → 1; W6 the panel note promises one → 1.

Stage 5: J1 a listed step loses its mark → 3 red; J2 the loud line becomes silent → 2; J3 pending counted as checked → 2; J4 a pending run ends plain `OK` → 2; J5 the manifest gives no reason → 2. The existing instrument `prove_the_guard_can_fail.py`: 126 RED, 1 GREEN, the same one vacuous mutation as at the base (`proposal-revise-needs-a-comment`, predates the lane). The driver, run over three pending steps without a browser, printed `PENDING <step> pending_v3_activation -- NOT RUN: <reason>` for each and returned `verdicts: ["PENDING","PENDING","PENDING"]`, `failures: []`.

## Commands and counts

One pytest at a time; `PYTHONPATH=src:<bootstrap site-packages>`; the database tests on a **private** database `prod11_removal_*` created on the lane server, migrated to `0033`, and dropped at the end; the shared lane database was not touched. Free disk stayed at or above 1.7 GiB.

| Command | Result |
| --- | --- |
| `tests/unit tests/replay` (final tree, no stack) | 2202 passed, 3 skipped, **5 failed**: `test_ssh_forced_command.py`, the same 5 fail on the untouched base |
| `tests/contract` minus the three `D-220` files, on the clean committed tree (includes `tests/contract/program`, `test_doc_prose_facts`, `test_surface_counts_in_prose`, `test_contract_seal`, `analysis_packages`, `architecture`) | 1175 passed, 19283 subtests {{CONTRACT_FINAL}} |
| `tests/e2e` (static: conformance, the new section and pending checks) | 225 passed, 5 skipped |
| `node --test write.test.mjs navigation-retry.test.mjs` | 13 passed |
| `prove_the_guard_can_fail.py` | 126 RED, 1 GREEN (the same vacuous mutation as at the base) |
| web `vitest run` / `eslint .` / `tsc --noEmit` / `api:verify` | 200 files, 3040 tests passed / exit 0 / exit 0 / `OK - 104 operations`, contract sha256 `f98c4704…` |
| removal guard `tests/unit/analysis/test_ar_v1_v2_removal.py` | 25 passed (14 s) |
| Database suites on the private database, **before the version bump** (stage 2a state, after the fixes): `findings` 146, `analysis` 792 (+6 skipped), `analysis_text` 343, `sections` 178, `executors` 157 (+16 skipped), `workers` 44, `jobs` 76, `optimisation` 102, `qa_w55b` 78, `recovery` 320, `api` 666, `ingest` 738, `db` 603, `analysis_engine` 47, `comparison` 150, `execution` 7, `qa_w52` 2, `qa_w53` 7, `dashboard` 8, `decisions` 89, `dispatch` 46, `documents` 43, `releases` 59 | all passed |
| `composition`, whole, before the bump | first run 6 failed + 16 errors (all in 8 files that started an АР run through `POST /runs`); after the repointing those 8 files and `test_analysis_profiles_over_http` ran 56 passed; the rest of the directory (1254 passed) was not re-run in full (17 minutes; the edits touched only those files) |
| `characterization` | 54 passed, 16 failed: the 16 stale refusal records, the same 16 as at the base (53 passed, 16 failed there; +1 is the new digest test) |
| Database suites **after** the bump: `runs` 779 passed; `p02_journey` 60; `exports` 148 (+2 skipped); the 12 files that name the contract version (`api`, `auth`, `composition`, `qa_w52`, `runs`, `analysis`) | 220 passed |
| Not re-run after the bump (they passed before it and the bump changed only version literals): `api`, `composition`, `recovery`, `executors`, `analysis`, `optimisation`, `qa_w55b`, `sections`, `findings`, `ingest`, `db` | stopped on purpose: free disk fell to 1.57 GiB (floor 1.5), and a first sweep was killed from outside at 86 % of `api` |

## Integration notes

- Merge order: no conflict with `PW3` lanes C, G, A3 is expected except `tests/integration/runs/test_v3_saved_text_layer_probe.py` (lane C edited it; this lane changed three lines of it) and the `infra/deploy/proxy/*.conf` literals against lane I2 (stage 2b alone).
- **The contract number is a proposal.** If it changes: revert the two commits `b7e5fdf1` and `56b25ebe` (or run `python3 tools/plan/pin_sweep.py contract-version` and sweep), then set `candidate_revision` and `supersedes` of the three domain catalogues and schemas, `SEALED`/`PREVIOUS` in `test_contract_seal.py`, regenerate the client (`npm --prefix web run api:generate`) and refresh `web/FRONTEND_LOCK.json`.
- Docs the integrator owns and which now disagree: `CURRENT_STATE.md` (contract `1.6.0`, "АР builtin"), `ALPHA_ROADMAP.md` and `P02_SEAMS.md` (live claims of `1.6.0`), `CONTRACT_PIN_REGISTRY.md` (unchanged rule), `DEBT_REGISTER.md` (`D-222` closes with `PROD-11a`; `D-223`'s contract half is done here; the `reviewed` description is corrected in the contract, `W59-SECTION-PROFILES-01.md` and the ADR text are not mine). `scripts/light_acceptance.py` still does not list `tests/e2e/test_pc01_journey_section.py` (noted by `PROD-10B`).
- `tests/integration/composition` takes about 17 minutes on the lane stack (the port-completeness test); the run of this lane is in the counts above.
- To reactivate the 33 journey steps after `D-204`: remove `pending_v3_activation` from the steps and the reason from `write.ar_bound`; the conformance test then demands the marks again unless `ar_bound.steps` is emptied on purpose.
- Debt candidates (not written, not mine): `analysis/text/prompt.py` keeps `SYSTEM_PROMPT` and `AR_TEXT_PROMPT_BUNDLE`, now consumed only by tests, the drill seed, the characterization journey and the `ar_specification` builder; the offline AR v2 seeded evaluator is half gone (`tools/evaluation/matcher.py`, `tools/fixtures/seeded/`, `fixtures/evaluation/ar_v2/` remain with no runner); `scripts/rehearsal/w53/*` (D-12).

## Limits

1. Nothing in the journey ran in a browser; the pending mechanism was shown at driver level only (no stand, no browser here).
2. The two readings of the version rule (D-1) and the exit code of a run with pending steps (D-11) are the integrator's to confirm.
3. The characterization suite is red at the base on 16 stale refusal records and is red on the same 16 now; this lane did not repair them.
4. The three `D-220` contract files were not run (`test_cp00_candidate.py`, `test_validate_bootstrap.py`, `test_cp00_final_state.py`); they open `.git` as a directory and cannot pass in a worktree. They check the domain catalogues this lane edited (`candidate_revision`, `supersedes`); that edit is covered by `test_contract_seal.py` and `test_domain_identifiers_schema.py`, which passed.
5. `tests/unit/executor_runner/test_ssh_forced_command.py` (5 tests) fails at the base and now, for a reason unrelated to this lane.
6. The web wording for АР (D-14) was not seen on a screen; it is covered by rendered markup tests.

## Forbidden paths: proof

```text
$ git diff --name-only 1c8d29fa..HEAD | grep -E '^(db/|\.github/|src/auditmanager/analysis/text/profiles/|fixtures/recorded/sections/[a-z]+/[0-9a-f]{64}\.json|docs/program/P02_LOCK\.json)|DEBT_REGISTER|CURRENT_STATE|OWNER_RULINGS|/adr/'
(no output)
$ git diff --name-only 1c8d29fa..HEAD | grep -E '^(infra/|fixtures/recorded/sections/)'
fixtures/recorded/sections/ar_specification/build_fixtures.py
infra/deploy/proxy/nginx.conf
infra/deploy/proxy/tls-server.conf
```

The three paths of the second list are the exceptions D-13 and D-4 describe: a builder script (no recording file moved: `--check` prints `fixtures match`) and the four `contract_version` string literals of the edge's `401` and `429` bodies, which a test pins to the facts file. No migration, no section package, no recording, no `P02_LOCK.json`, no register, ADR or ruling was touched.
