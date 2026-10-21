# RELEASE-0-7-0-RECORD-01 — the 0.7.0 record for the tree the owner merged into main

Lane `agent/release-0-7-0-record-01`, cut from `origin/main` `829117d3` (the owner's pull request #2,
`R-141e`). Nothing was pushed, merged into another branch or tagged; no container, npm, `make` or
whole-directory test run was started (the host has about 4 GB free). This record replaces the
cancelled candidate `agent/release-0-7-0-notes-01` (`59a1be91`), whose notes described a tree that never
reached `main`; its text was re-derived, not copied, and its two test repins were cherry-picked.

## Result

`VERSION` is `0.7.0`. `release-notes/0.7.0.json` (revision 2, date 2026-10-21, seven items, all «Новое»)
describes what a user can do on the tree that is already running from `main`, which reports `0.6.0`
(`build_id` `b60e02fff4f168d21` computed from the `829117d3` archive). `RELEASES.md` has a candidate row
and a technical record saying `not deployed`. `CURRENT_STATE.md` stays at 120 lines. `R-142` records
the owner's poll answers. **The tree has no literal `GATE OK`**: the owner merged without one (`R-141e`) and the
`R-125` completion of the predecessor lineage (`NIGHT-1020-GATE-0-7-0-01.md`) does not cover the
classification correction or the normative references.

## What changed against the cancelled candidate

- Item 1 now says a confirmation can be corrected («Исправить», reason, history), which makes the old
  sentence "a confirmation cannot be changed" false (`CLASSIFICATION-CORRECTION-01`, migration `0028`).
- Item 6 gains «Нормативные ссылки» on the run page (`NORM-REFS-RUN-01`).
- API 71/81/235 became 73/83/242 (29 operations added since `v0.6.0`, none removed or moved); head `0027`
  became `0028`; the dashboard follows the current (corrected) classification.
- The old row's `build_id` is replaced by the one of this tree. Between the two trees only comments in
  `infra/deploy` changed.

## Changed files

- `VERSION` — `0.6.0` to `0.7.0`.
- `release-notes/0.7.0.json` — new.
- `tests/contract/release_notes/test_release_notes_form.py` — the revision map and the version list follow the new entry.
- `tests/integration/releases/test_release_loader.py` — the set of note files.
- `tests/replay/text_analysis/test_offline.py`, `tests/e2e/pc01/test_acceptance.py` — the two stale pins found by the predecessor's gate completion (cherry-pick `57f25203` of `59a1be91`).
- `docs/program/RELEASES.md`, `docs/program/CURRENT_STATE.md`, `docs/program/OWNER_RULINGS_2026-09-17.md` (`R-142`), this report.

## Checks

`PY` = `/root/projects/PDF-Analysis/.local/worktrees/w55b-main-candidate/.venv/bin/python`,
`$PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <paths>`, one command at a time; the worktree's
`.venv/bootstrap` links to the shared governance interpreter (ignored by git).

| Check | Result |
| --- | --- |
| `tests/contract/release_notes` | 24 passed (shape, form, title, item count, 400-character cap, dictionary, descending versions) |
| `tests/contract/program` + `tests/contract/api_v1/test_doc_prose_facts.py` + `test_surface_counts_in_prose.py` + `tests/contract/release_notes`, one run | 128 passed |
| `tests/contract/test_alpha_acceptance_command.py` (reads `VERSION`, needs a clean tree) | 33 passed |
| `tests/integration/releases/test_build_id.py test_product_version.py` and `test_release_loader.py::test_shape_schema_matches_the_served_item_and_kind` | 21 passed |
| `tests/replay/text_analysis/test_offline.py` | 3 passed (red on `829117d3` before the repin) |
| `tests/e2e/pc01/test_acceptance.py` | **not run**: it needs `.env` and real services; the repin is the predecessor's, found by its gate completion |
| screen rule of `web/tests/unit/release-notes/current-screen.test.ts`, re-implemented in Python over the registry and the group labels | 7 of 7 items: `screen` is a registry address and `where` begins with its current group and label (npm not run) |
| every commit and test cited below, checked mechanically | the 9 new commits and 58 of the 60 commits of the old table are ancestors of the tree (the other two are the cancelled candidate's own); all 72 named Python tests and 16 web test files exist |
| `compute_build_id()` on `git archive` of `829117d3` / of the candidate tree `88ff0e4b` | `b60e02fff4f168d21` / `b42b8bb12505a5e46` (`VERSION` and `release-notes/` are inputs, so the images rebuild when this is published) |

Not run: a full gate, the web unit suite, the live journey, any container-backed test, any host command. The
container-backed tests cited below are those of the lane reports.

## Independent judge

A fresh read-only agent worked from the code before seeing this table. Verdict **PASS-WITH-EDITS**: no
sentence is contradicted, every quoted button or label exists verbatim in `web/src`, four sentences left out a
condition. Applied as revision 2 and each re-checked in the code by the author:

1. Item 1: ПБ has a section code but no profile, and every unconfirmed version (not only an old one) is refused.
2. Item 4: proposals start from «Запустить проход` and need a published run of an АР version and an АР vendor list
   (`vendor_list_missing`); «на доработку» and the proposals CSV left the text for room.
3. Item 6: the references block shows in all four terminal states; a run started before a snapshot is designated pins none
   and stays without references (`snapshot_not_pinned`).
4. Item 7: no review screen sets a severity, so the two CSV columns are normally empty.

Omitted by the seven-item cap: the per-section profile table of «Настройки анализа», the Excel refusal for a run whose
norm citations failed verification, the dashboard following the confirmed section, the old `/optimisation` redirect,
stage and section labels on version rows.

## Claim table

Every claim is a sentence of a published item. A claim with no proof would have been deleted.

### Item 1 — «Работа › Версия документа › Стадия и раздел»
Slices `W59-SECTION-SEAL-01`, `W59-SECTION-UI-01`, `W59-SECTION-PROFILES-01`, `W59-ANALYSIS-SETTINGS-01`,
`CLASSIFICATION-CORRECTION-01` ([report](CLASSIFICATION-CORRECTION-01.md)).

| # | Claim | Commits | Tests | Observation |
| --- | --- | --- | --- | --- |
| 1a | An expert confirms the stage (П or Р) and one of 15 sections on the version screen | `a23433ed`, `bd08e03c`, `28c23819`, `92fb6581`, `5a4686aa`, `5d659d03`, `a5a01614` | `tests/integration/runs/test_w59_section_routing_over_http.py::test_an_expert_classifies_and_an_exact_repeat_keeps_the_first_confirmer`, `::test_admin_alone_is_refused_and_nothing_is_written`, `::test_fifteen_choices_executable_as_registered_and_nothing_preselected`; (web) `web/tests/unit/sections/classification-panel.test.ts`, `classify-command.test.ts` | panel title «Стадия и раздел» in `web/src/widgets/version-classification/ui/version-classification.tsx` |
| 1b | Later the expert corrects the confirmation with «Исправить» and a reason; the history is visible; only an expert | `4b9a630e`, `c2e254cd`, `334b131f` | `tests/integration/runs/test_classification_correction_over_http.py::test_an_expert_corrects_and_the_review_shows_the_new_revision_and_the_history`, `::test_admin_alone_is_refused_and_nothing_is_written`, `::test_a_stale_expected_revision_is_a_conflict_and_changes_nothing`; `tests/integration/db/test_classification_corrections_migration.py`; (web) `web/tests/unit/sections/classification-correction.test.ts` | button text at `version-classification.tsx:137`; a started run keeps its pin (`::test_a_started_run_keeps_its_pin_and_a_later_start_routes_from_the_correction`) |
| 1c | Run start and re-audit work only for a confirmed section with a profile; an unconfirmed version (old or new) and ПБ are refused | `bd08e03c`, `92fb6581` | `tests/integration/runs/test_w59_section_routing_over_http.py::test_an_unclassified_version_is_refused_even_with_legacy_section_ar`, `::test_a_section_without_a_profile_is_refused_without_an_ar_fallback`, `::test_a_reaudit_routes_from_the_classification_now_and_the_source_keeps_its_pin`; (web) `web/tests/unit/sections/run-refusal.test.ts` | `0024` creates the table and inserts nothing |
| 1d | The project screen groups documents by section | `5a4686aa`, `a5a01614` | (web) `web/tests/unit/sections/project-structure.test.ts` | `web/src/widgets/project-sections/model/structure.ts` |
| 1e | The profiles of 13 sections are drafts | `e027b0d9`, `2b93655d`, `c21345ee`, `44681726` | `tests/integration/composition/test_analysis_profiles_over_http.py::test_every_row_is_the_registry_entry_the_application_routes_by`; `tests/unit/analysis/test_text_profile_registry.py::test_the_tree_registers_without_error_and_without_an_ar_package` | measured on this tree: `load_text_profile_registry().entries` is AR `builtin` plus 13 `draft`, no ПБ |

### Item 2 — «Работа › Сравнение прогонов › Сравнение версий»
Slices `W59-VERSION-UPLOAD-01` ([report](W59-VERSION-UPLOAD-01.md)), `W59-VERSION-COMPARE-01`
([report](W59-VERSION-COMPARE-01.md)), `W59-DECISION-CARRYOVER-01`
([report](W59-DECISION-CARRYOVER-01.md)). The screen is the registry's `…/comparison` address
(label «Сравнение прогонов»); its page title is «Сравнение версий».

| # | Claim | Commits | Tests | Operation or observation |
| --- | --- | --- | --- | --- |
| 2a | The next version of a document is loaded with «Загрузить новую версию» on the document page; it becomes current, earlier ones are unchanged, and its section is confirmed anew | `940a1e4d`, `49df7a16`, `5985b69d`, `6eabe898` | `tests/integration/api/test_version_upload.py::test_the_next_version_is_published_and_becomes_the_current_one`; `tests/integration/ingest/test_next_version.py::test_further_versions_take_the_next_ordinals_and_the_current_pointer`, `::test_the_new_version_inherits_nothing_and_the_older_one_keeps_every_fact`, `::test_concurrent_next_versions_get_consecutive_ordinals`; (web) `web/tests/unit/upload/version-upload-command.test.ts`, `web/tests/unit/screens/version-upload-screen.test.ts` | button text in `web/src/features/upload-document/ui/upload-document-version-form.tsx`; the nginx regexes of both proxy files admit the path (`git diff v0.6.0 HEAD -- infra/deploy/proxy`) |
| 2b | «Сравнение версий» pairs sheets and lines of two analysed versions of one stage and section | `acaab454`, `30be35c9`, `125e2673`, `f9fb5e87` | `tests/integration/composition/test_version_comparison_over_http.py::test_the_comparison_refuses_then_compares_as_its_inputs_appear` (unclassified, then no analysis, then compared), `::test_pairs_outside_the_rule_are_refused_with_a_reason`; `tests/unit/comparison/test_sheet_pairs_and_line_diff.py`; `tests/integration/comparison/test_service_db.py::test_two_500_page_versions_compare_with_bounded_pages`; (web) `web/tests/unit/comparison/version-comparison.test.ts` | refusal «У … версии нет завершённого анализа» is `analysis_missing` in `web/src/entities/document-version/model/comparison.ts` |
| 2c | The «Стадии П → Р» mode compares a П version with a later Р version | `0c8b74a4`, `125e2673`, `f9fb5e87` | `tests/unit/comparison/test_stage_section_pair.py::test_p_source_and_r_target_of_one_section_are_admitted`, `::test_every_other_pair_is_refused_and_never_relabelled`; the over-HTTP test of 2b (an Р version is refused in the default mode and compared in `mode=stage`); (web) `version-comparison.test.ts` | button text in `web/src/widgets/version-comparison/ui/version-comparison.tsx` |
| 2d | «Перенести решение» carries an expert decision onto the unchanged matched finding of the newer version | `f345b815`, `a92567c7`, `0816fe44`, `2cae90f4`, `c939b067` | `tests/integration/comparison/test_decision_carryover_db.py::test_a_confirmed_carryover_appends_one_attributed_event_with_its_provenance`, `::test_a_pair_the_comparison_does_not_propose_is_refused`, `::test_a_target_with_any_event_refuses_the_carryover`, `::test_only_an_expert_carries_and_admin_alone_does_not`; `tests/integration/decisions/test_carryover_ledger.py`; `tests/integration/composition/test_decision_carryover_over_http.py::test_a_confirmed_carryover_over_http`; (web) `web/tests/unit/comparison/carry-over-command.test.ts`, `decision-carryover.test.ts` | button text in `web/src/features/carry-over-decision/ui/carry-over-decision.tsx` |

### Item 3 — «Работа › Диспетчер»
Slice `W61-DISPATCHER-01` ([report](W61-DISPATCHER-01.md)); migration `0025_work_assignments`.

| # | Claim | Commits | Tests | Operation or observation |
| --- | --- | --- | --- | --- |
| 3a | An administrator assigns a project or one of its documents to an expert, reassigns and cancels | `3461747c`, `8d162fe0`, `8ddbba21` | `tests/integration/api/test_dispatch_operations.py::test_an_administrator_creates_and_the_answer_names_everyone`, `::test_the_seam_admits_only_admin_and_the_command_checks_again`, `::test_reassign_and_return`; `tests/integration/dispatch/test_dispatch_commands.py`; `tests/unit/dispatch/test_policy.py`; (web) `web/tests/unit/dispatcher/dispatcher.test.ts` | — |
| 3b | The expert takes the work, completes it or returns it with a reason, in «Диспетчер» and in «Мои задачи» on the home page | `8d162fe0`, `8ddbba21` | `tests/integration/api/test_dispatch_operations.py::test_the_expert_starts_and_completes_and_history_tells_it`, `::test_who_may_move`; (web) `dispatcher.test.ts` | `web/src/_pages/home/ui/home-page.tsx` mounts `MyTasks`; labels «Взять в работу», «Отметить выполненным» in `web/src/entities/assignment/model/presentation.ts` |
| 3c | Every change stays in the assignment's history | `3461747c` | `tests/integration/db/test_work_assignments_migration.py` (append-only tables, first event required); `tests/integration/api/test_dispatch_operations.py::test_the_expert_starts_and_completes_and_history_tells_it` | — |

### Item 4 — «Работа › Проект › Оптимизация»
Slices `W60-PRICE-LIST-01`, `W60-OPT-MATCH-01`, `W60-OPT-PROPOSALS-01`; migrations `0026`, `0027`.

| # | Claim | Commits | Tests | Observation |
| --- | --- | --- | --- | --- |
| 4a | An expert uploads a price list as CSV or Excel | `6d86b991`, `1ae07a62`, `accabcb5`, `263747b0`, `ca7cc724` | `tests/integration/optimisation/test_price_list_uploads.py::test_an_expert_upload_is_one_revision_bound_to_its_available_blob`, `::test_an_xlsx_upload_records_its_format_and_default_currency`, `::test_only_an_expert_uploads`; `tests/integration/composition/test_optimisation_over_http.py::test_the_upload_answers_the_revision_and_its_exact_repeat` | — |
| 4b | An administrator keeps vendor lists per section; an expert sets their own for the project | `6d86b991`, `ca7cc724` | `tests/integration/optimisation/test_vendor_lists.py::test_only_an_administrator_sets_the_global_list`, `::test_only_an_expert_overrides_a_project_list_and_inherit_carries_no_entries` | — |
| 4c | «Спецификация и цены» matches the АР specification rows to the price list; a price and an amount only on an unambiguous row | `67fd24c0`, `0b2545a2`, `98dd6c76`, `d44ebc4b` | `tests/unit/optimisation/test_matching.py::test_equally_good_candidates_are_ambiguous_even_at_one_price`, `::test_a_unit_mismatch_is_unmatched_and_adds_nothing`; `tests/integration/composition/test_specification_prices_over_http.py::test_every_state_appears_as_its_input_does` | tables are read from saved text only (`W60-OPT-MATCH-01`, "Known limitations") |
| 4d | «Предложения» start from «Запустить проход» (an expert), need an АР vendor list, and offer cheaper positions of the list's vendors; an expert accepts or rejects | `80ea0b9d`, `234a8113`, `f6a16a88`, `49082715` | `tests/integration/optimisation/proposals/test_passes.py` (`vendor_list_missing` refusals, lines 206 and 214); `tests/unit/optimisation/proposals/test_generator.py::test_a_matched_row_gets_its_cheaper_analogs_cheapest_first`, `::test_a_vendor_off_the_list_or_no_vendor_is_never_proposed`; `tests/integration/composition/test_optimisation_proposals_over_http.py::test_decisions_are_appended_counted_and_listed` | «Запустить проход» in `web/src/features/start-optimisation-pass/ui/start-optimisation-pass.tsx`; «Принять», «Отклонить» in `web/src/entities/optimisation-proposal/model/presentation.ts` |

### Item 5 — «Работа › Оптимизация разделов»
Slice `W63-SECTION-FORM7-01` ([report](W63-SECTION-FORM7-01.md)); read model `SECTION-READ-MODEL-01`
([report](SECTION-READ-MODEL-01.md)).

| # | Claim | Commits | Tests | Operation or observation |
| --- | --- | --- | --- | --- |
| 5a | The screen shows the specification of a chosen section across projects whose current version is confirmed in it | `94784b2b`, `e6d07227`, `f4161fc9`, `4a3fec18`, `84f5a5f3`, `fee74158` | `tests/integration/optimisation/test_section_specification.py::test_a_project_in_another_section_never_appears`, `::test_an_unclassified_current_version_is_excluded_even_after_an_ar_older_version`; `tests/integration/composition/test_section_specification_over_http.py::test_membership_is_the_current_versions_confirmed_in_the_section`; (web) `web/tests/unit/section-specification/section-specification.test.ts` | — |
| 5b | Rows of different projects are not merged, each is priced from its own project's list, totals are per project and currency, there is no section total | `94784b2b`, `4a3fec18` | `tests/integration/optimisation/test_section_specification.py::test_two_projects_in_one_section_keep_their_rows_apart_and_their_own_prices`, `::test_totals_exist_per_project_and_currency_only`; `tests/integration/composition/test_section_specification_over_http.py::test_each_projects_price_state_and_sources_are_its_own` | — |

### Item 6 — «Знания › Нормы»
Slices `W57B-NORMS-CATALOGUE-XLSX-01`, `NORMS-DISPLAY-DESIGNATION-01`, `NORM-REFS-RUN-01` ([report](NORM-REFS-RUN-01.md)).

| # | Claim | Commits | Tests | Observation |
| --- | --- | --- | --- | --- |
| 6a | «Каталог» lists the documents of the current set with search by designation and title and a filter by kind | `7466196c`, `7d92fe3a`, `b99211be` | `tests/integration/norms/catalogue/test_catalogue_window.py::test_the_current_snapshot_only_with_display_names_and_counts`, `::test_filters_by_text_and_kind`; (web) `web/tests/unit/norms/catalogue.test.ts` | 674 documents and 23 kinds on the lane's local real-corpus stand |
| 6b | Designations are readable (`СП 54.13330.2022`) for part of the documents | `7466196c`, `5c7ab8b3`, `03d493b2` | `tests/unit/norms/test_reader_designation.py::test_the_reader_sees_the_readable_designation`; `tests/integration/norms/search/test_display_designation_window.py::test_search_shows_the_readable_designation_and_one_per_document` | 257 of 674 designations change |
| 6c | On the page of a run in a terminal state, «Нормативные ссылки» match the cited norms with the snapshot the run pinned | `52e4c8fc`, `1e5c0089`, `4c2b816e`, `073b3c0c`, `d586c8fe`, `ac0526ab` | `tests/integration/runs/test_reference_norm_references.py::test_a_stored_run_lists_its_cited_norms_against_its_pinned_snapshot`, `::test_a_run_that_pinned_no_snapshot_says_so_and_reads_neither_text_nor_snapshot`; (web) `web/tests/unit/norm-references/norm-references.test.ts`, `run-progress-mount.test.ts` | the block is mounted for `TERMINAL_RUN_STATES` only (`web/src/widgets/run-progress/ui/run-progress.tsx:393`) |
| 6d | A loaded snapshot designated current by the administrator is needed; a run started before has no references | `d586c8fe` | `tests/integration/norms/catalogue/test_catalogue_window.py::test_no_current_snapshot_is_required_norm_unavailable`; the `snapshot_not_pinned` state test above | the stand has had neither the import nor the designation (`STAND-NORMS-IMPORT-RUNBOOK-01.md`) |

### Item 7 — «Работа › Разбор находок»

| # | Claim | Commits | Tests | Observation |
| --- | --- | --- | --- | --- |
| 7a | «Скачать Excel» sits beside the CSV export and downloads a workbook of the run's findings | `7466196c`, `cdc7e9de`, `7d92fe3a`, `b99211be` | `tests/integration/exports/test_xlsx_run_export.py::test_a_real_v1_run_exports_with_portal_labels_and_empty_norm_columns`; (web) `web/tests/unit/export/export-panel-xlsx.test.ts` | `web/src/widgets/export-panel/ui/export-panel.tsx` |
| 7b | Category and decision use the words of the screens | `4a4775e3`, `6691c74a`, `9b822a12` | `tests/unit/exports/test_xlsx_labels_lockstep.py::test_the_export_labels_equal_the_screens_labels` | — |
| 7c | No workbook for a version without the portal bundle or a run without a result | `7466196c` | `tests/integration/exports/test_xlsx_run_export.py::test_unknown_and_unfinished_runs_are_refused_as_the_csv_refuses_them` | — |
| 7d | The CSV has two severity columns, empty until a severity exists | `7466196c` | `tests/integration/exports/test_frozen_column_list.py::test_the_module_constant_matches_the_frozen_list_in_order` | `src/auditmanager/exports/query.py:87`; no review screen sets a severity |

### Technical row

| Claim in `RELEASES.md` | Proof |
| --- | --- |
| API 47/54/123 to 73/83/242, 29 added operations, none removed or moved | contract diff `v0.6.0` to the tree computed in this task (operation ids and methods compared) |
| error codes 24 to 25 | `contracts/domain/v1/error-codes.json`: 24 at `v0.6.0`, 25 on the tree (`model_identity_mismatch`) |
| migrations `0022`–`0028` | `db/migrations/versions/` lists seven files after `0021`; `0028` downgrade logs and drops its tables |
| nginx locations widened | `git diff v0.6.0 HEAD -- infra/deploy/proxy` (two files) |
| no dependency, lock or compose change | `git diff --stat v0.6.0 HEAD -- pyproject.toml uv.lock web/package.json web/package-lock.json infra/deploy/compose.server.yml infra/deploy/Dockerfile.api infra/deploy/Dockerfile.web Makefile` is empty |
| prompt and profile bundle hashes unchanged | `AR_TEXT_PROFILE`: `934705c04a71…` and `30053740f569…` on this tree |
| deploy workflow run `39561204544` | taken from the integrator's report, not re-read here (`gh` is not installed on this host) |

## Risks and known limitations

1. **No gate and no host verification** on this tree. Publication needs the owner's instruction naming the exact SHA;
   the release row's `pending` cells are filled after the workflow and `infra/deploy/verify-deployed.sh`.
2. **The notes are not live-checked.** No credentialed journey has exercised the new screens.
3. **Publishing this record redeploys** (`VERSION` and `release-notes/` feed `build_id`): new images, the update banner,
   no migration. The deploy refuses while a norms import record is open.
4. **Item 6 is conditional by design**: until the corpus is imported and a snapshot designated, the catalogue and
   search answer a typed refusal and runs pin no snapshot. Runs started before the designation never get references.
5. **Items 1 and 4 each name a second screen** (the settings table of drafts, the vendor lists): the cap of seven items forced it.
6. **`0022` can stop a deploy** by design (its backfill refuses a finding without exactly one observation); it passed on
   the stand's data at the `829117d3` deploy per the integrator's report, not re-read here.
7. **`BETA-CONTRACT-SEAL-01` will move `contract_version` to 1.0.0 on dev.** This record states the historical value
   `1.0.0-draft.1`; the integrator resolves that cell on merge.

## Integrator instructions

1. Merge `agent/release-0-7-0-record-01` into `integration/night-1020`; expect conflicts only in `OWNER_RULINGS_2026-09-17.md` (tail),
   `CURRENT_STATE.md` (the surface paragraph) and the `contract_version` cell of `RELEASES.md`.
2. For `origin/main`: obtain the owner's instruction naming the exact tip SHA of this lane, prove the fast-forward from `829117d3`,
   push, follow the workflow and `verify-deployed.sh`, then in one docs-only commit fill the `pending` cells of the `v0.7.0` row,
   drop the `not deployed` marker and tag `v0.7.0` (`RELEASE_PROCESS.md`). Recompute `build_id` on the exact SHA.

## Hotspot proof

`git diff --name-only 829117d3 HEAD` lists the files under "Changed files" and nothing else: no `src/**`, `web/**`, `contracts/**`,
migration, dependency file, other note file, ref, tag or stand.

## Addendum (2026-10-21, after the owner's pull request #3)

The owner merged `dev` into `main` again (`48c8e34ccd08a58ae61cbd09ecdba49066a5ad46`, parents `829117d3` and `3c62533b`;
workflow run `39571427597`, success, reported by the integrator and not re-read here). `VERSION` on `main` is `0.7.0`
and `release-notes/0.7.0.json` is the revision 2 written above, so **the record reached `main` through the owner's merge,
not through the fast-forward `dfae803b`** this report names in its instructions.

What the tree on `main` has beyond `dfae803b`, measured with `git diff dfae803b 48c8e34c`: 90 files; contracts, migrations,
release notes and `VERSION` identical (surface still 73/83/242, head `0028`, 25 error codes); `src` 9 files, `infra` 5,
`web/src` 9, `fixtures` 9, `scripts` 8, `tests` 41. In `RELEASES.md` this changed three statements, each corrected there:
the row's `build_id` (`bbbab3c0dfb856a39`, from `git archive` of the SHA), the proxy bullet (it is no longer "throttle lines
unchanged": the credential exchange is throttled and the two upload locations ask for a credential before the body is read),
and the compose line (comments only differ from `v0.6.0`, not "no change").

What was **re-read** against the notes: the matcher still returns a price and an amount only for an unambiguous row (the new code
makes a vendor's legal form optional when comparing names, and still compares two different legal forms as different); the two
web repairs touch the carried-decision display and the price-list upload's double press, not a sentence of an item. What was
**not** re-run: any test (the web tests changed by the repairs, and the containers-backed suites of the four slices, are the
lane reports'). The notes do not mention the hardening slices, which is deliberate: none of them is a user-facing claim.

Still owed for the row: `infra/deploy/verify-deployed.sh` on the host for `48c8e34c`, then the tag `v0.7.0` on that SHA after
the owner agrees, then one docs-only commit that fills the `pending` cell (a docs-only push to `main` needs the owner's
instruction naming its SHA).
