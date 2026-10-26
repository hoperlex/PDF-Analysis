# OPT-PROJECT-ALL-SECTIONS-01 — report (2026-10-27)

Lane OP of wave PW4. Base `6075df88` (`integration/ar-close-1026`), branch `agent/opt-project-all-sections-01`. Task file: [`tasks/OPT-PROJECT-ALL-SECTIONS-01.md`](tasks/OPT-PROJECT-ALL-SECTIONS-01.md) (premises P-01 to P-12).

## History and verdict

The lane first **stopped at the premise** (commits `555bd21f`, `2bc4e0b9`): the database trigger `am_check_optimisation_pass_scope` (`0027`, replaced in `0028`) required the version's classification and the pinned vendor list to be `AR`, so lifting the two Python-side AR assumptions made `startOptimisationPass` fail at the INSERT (`AM001`, task P-05, P-06). The integrator chose **option A** and gave the lane the migration slot. This report is of the finished lane.

**Done.** «Спецификация и цены» (`getSpecificationPrices`) and «Предложения» (`startOptimisationPass` and the passes' screens) accept a version an expert confirmed in **any of the fifteen sections**. A pass pins the effective vendor list of the version's own section, and the database holds the same equality. `section_not_ar` is no longer produced and **stays** in the enum. The version stays unclassified → `version_unclassified`. An АР version behaves as before.

## What changed

**Migration `0034_pass_scope_all_sections`** (`db/migrations/versions/20261027_0034_pass_scope_all_sections.py`). `CREATE OR REPLACE` of `am_check_optimisation_pass_scope()`: `0028`'s body with `AND c.section_code = 'AR'` removed and `AND l.section_code = 'AR'` replaced by `AND l.section_code = c.section_code`; every other condition and the `AM001` raise are `0028`'s (only the exception text stopped saying «AR»). No table, column, CHECK, trigger, view or enum moved. The downgrade refuses (`0034 downgrade refused: N optimisation pass(es) pin a vendor list of a section other than AR`) while any pass pins a non-AR vendor list; otherwise it restores `0028`'s function byte for byte. **Deviation from the grant:** the revision id is `0034_pass_scope_all_sections` (28 characters), not `0034_optimisation_pass_scope_all_sections` (40): `alembic_version.version_num` is `varchar(32)` (task P-12).

*Measured* (a fresh database upgraded to `0033`, then `0034`, every family of `test_schema_invariant_inventory.py` recomputed): **only `functions` moved** (32 rows kept, digest `38aa2359…67ab` → `da49fd30…6bef`); columns 736, relations 76, constraints 814, indexes 184, triggers 86, views 5, extensions 1, sequences 7, policies 0, state topology 51 are identical.

**Server.** `optimisation/project_match.py`: the `SECTION_AR` constant and the guard are gone (the section is carried on the answer and changes nothing else); `STATE_SECTION_NOT_AR` stays in `STATES`. `optimisation/proposals/commands.py`: the effective vendor list is read for `prices.section_code`. Docstrings of the slice, the two routers' descriptions and `SpecificationPrices` in `models.py` say what is true.

**Contract (prose only; `1.7.0` kept).** `contracts/api/v1/openapi.json` and its mirror `web/openapi/openapi.json`: the descriptions of `getSpecificationPrices` and `startOptimisationPass` (the `409` reason list no longer lists `section_not_ar`; the value is documented as «stays in the enum, no longer produced for a confirmed section»), the `SpecificationPrices` schema description, the two W60 paragraphs of `info.description` corrected in place and one reseal paragraph added, **`uploadDocument`** (the stale «analysis is built for AR … applied to any uploaded document» now describes the routing by the confirmed classification), **`getDashboardSummary`** («fourteen frozen sections» → «fifteen sections», the integrator's addendum). `contracts/domain/v1/error-codes.json`: the pass refusal reasons in prose. **Version:** it did not have to move — the precedent is `22c1df66` (prose without a version commit), no path, operation, schema, enum value or error code changes, and `tests/contract/api_v1` (366) and the domain-family contract tests (174) accept it. The generated client was regenerated (`npm --prefix web run api:generate`), `web/FRONTEND_LOCK.json` re-sealed (digests, `content_commit` `19f4781d`), `npm --prefix web run api:verify` OK (contract sha256 `14375c44…9357a`).

**Web (copy and the two filters only).** `widgets/specification-prices` and `widgets/optimisation-proposals`: `arDocumentSets` → `classifiedDocumentSets` (every set whose current version is classified), the chooser names each set's section, the empty state and the rule texts say what is true; `features/start-optimisation-pass` (hint text), `widgets/optimisation-proposals/ui/pass-summary.tsx` («Вендор-лист раздела»), `entities/specification-price` and `entities/optimisation-proposal` (the sentences for `version_unclassified`, `section_not_ar`, `vendor_list_missing`). Not touched: `entities/project/**`, `widgets/dashboard/**`, `routing-refusal.ts`, `catalog-message.ts`. `tsc` and `eslint` clean on the changed files.

**Head pins.** `scripts/recovery/schema_coverage.py` `HEAD`, `tests/support/expected_facts.json` `migration_head`, the upgrade-surface digest of `0034` in `test_downgrade_chain_round_trip.py`, the `functions` digest of `test_schema_invariant_inventory.py`, and the head sentences of `docs/program/CURRENT_STATE.md` (two) and `docs/manual-tests/PC-01_prototype.md` that the prose guard reads. `test_project_erase_pure.py` and `test_erase_project_script.py` name `0033` only in synthetic plan texts and needed no change.

## Files

New: `db/migrations/versions/20261027_0034_pass_scope_all_sections.py`; tests `tests/unit/sections/test_pass_scope_migration_text.py`, `tests/integration/db/test_pass_scope_migration.py`, `tests/unit/optimisation/test_project_match_sections.py`, `tests/integration/runs/test_section_run_text_layer_is_what_optimisation_reads.py`; the two docs of the lane. Modified: see `git diff --name-only 6075df88..HEAD` below.

## Which sections' saved text the specification extraction understands — and what is NOT measured

* **Not measured: the extraction of a real section run's Form-7 table.** No recorded section fixture contains a specification table: the 14 section recordings were all built over the АР corpus text layer (`fixtures/recorded/sections/README.md`), whose text has no table (`extract_specification` finds 0 tables, asserted in `test_section_run_text_layer_is_what_optimisation_reads.py`). No recording was added (`fixtures/recorded/sections/**` is outside the lane). So nothing here says that the extraction understands a real ПБ, ОВ or КЖ volume's table; a real volume may need a section-specific reading, and decision rule 2 says that is not built here (the honest answers stay `analysis_missing`, `text_unavailable`, an empty table, `price_list_missing`).
* **Measured: the reader path.** For `KJ`, `OV` and `PB`, a version run in recorded mode to `published` under its own section profile and recording leaves the layer that `_SpecificationTextReader` returns (8 pages, verified digest), and that digest equals the one a v1-reference-profile run of the same bytes leaves (3 passed). The extraction, the matcher and the generator never mention a section (task P-04).
* **Unit level, fake saved-text reader:** the Form-7 page of the АР tests is read and priced for each of the **15** section codes with identical rows, statuses, amounts and totals (`test_project_match_sections.py`, 37 passed); `PB`, `OV`, `KJ` are also read with real PostgreSQL against an АР version of the same text (`test_project_match.py`). These are the same text; they are not field evidence for any section.

## Mutation table

| # | Mutation | Tests that go red (restored afterwards; `cmp` equal) |
| --- | --- | --- |
| M1 | `0034`: the two `'AR'` literals back in `_FUNCTION_0034` | 7 of 28 in the migration tests: unit text test, `test_after_the_step_every_section…`, `…current_classification…`, `…pb_pass_is_accepted_at_the_head`, `…populated_0033…`, both downgrade tests |
| M2 | `0034`: the line `l.section_code = c.section_code` removed | 8: five mismatched-pair parameters (PB/AR list, AR/PB list, KJ/PB, KJ/AR, PB/OV), `…current_classification…`, `…pb_pass_is_accepted_at_the_head`, the unit diff test (the two unclassified-version parameters stay green: the join refuses them) |
| M3 | `0034`: downgrade refusal disabled (`if False and other`) | `test_the_downgrade_is_refused_while_a_pass_pins_a_non_ar_list_and_only_then` |
| M4 | `0034`: downgrade restores `_FUNCTION_0034` | the restore round-trip test and the unit source test |
| MA | `project_match.py`: the AR guard restored | unit 31 of 37; integration 13 of 48 (`test_project_match` 4, `test_passes` 6, both composition files 3) |
| MB | `commands.py`: the vendor list taken for `"AR"` again | `test_passes` 6, `kj_started` HTTP test 1 |
| MR | `bootstrap/adapters.py` `_SOURCE_STAGE` = `"text_analysis"` (restored by `cmp`; the file is not part of the diff) | the 3 reader-path tests |
| W1 | both web filters back to `section_code === 'AR'` | 4 web tests |
| W2 | `vendor_list_missing` sentence names «раздела АР» again | `failure.test.ts` 1 |

## Before / after of every modified test

| Test | Before | After |
| --- | --- | --- |
| `test_project_match.py::test_a_version_classified_as_another_section_is_not_priced` | KJ → `section_not_ar`, `rows is None`, no run asked | renamed `…goes_on_to_the_price_list`: KJ → `price_list_missing`, section `KJ`, stage `R`, state is not `section_not_ar`, `rows`/`price_list` None, no run asked; **new** `…priced_exactly_like_an_ar_one_of_the_same_text[PB, OV, KJ]` (8 rows, rows/totals/exclusions equal an АР version's) |
| `proposals/test_passes.py::test_a_version_of_another_section_is_refused` | KJ + AR list → `409 section_not_ar`, nothing written | replaced by `…takes_a_pass_with_that_sections_vendor_list[PB, OV, KJ, EOM]` (pass created, pins that list, 6/4/4/4, vendors), `…vendor_list_of_another_section_does_not_apply…` (PB + only an АР list → `vendor_list_missing`), `…project_override_of_the_versions_section…`; the unclassified, no-price-list, no-run, no-text, `vendor_list_missing` (АР + KJ list) cases are unchanged |
| `proposals/conftest.py::project_vendors` | section fixed to `AR` | `section` parameter, default `AR` (callers unchanged) |
| `test_specification_prices_over_http.py::test_a_set_of_another_section_is_not_priced` | KJ → `section_not_ar`, `rows null` | `…is_read_like_any_other`: KJ → `analysis_missing` (price list named), then a real KJ section run publishes (in-process, recorded) and the answer is `ready` with section `KJ`, the run, 64-hex layer digest and the honest empty table |
| `test_optimisation_proposals_over_http.py::test_every_refusal_names…` | reasons `[version_unclassified, section_not_ar, price_list_missing, analysis_missing, vendor_list_missing]`, `>= 4` | `[version_unclassified, price_list_missing, price_list_missing, analysis_missing, analysis_missing, vendor_list_missing]`, `section_not_ar` absent, `>= 5` (the world also refuses the KJ set after the price list); **new** `kj_started` fixture and `test_a_pass_over_a_set_of_another_section_pins_that_sections_vendor_list` (201 through the trigger, KJ list id, 3/3/3/3) |
| `test_schema_invariant_inventory.py` | `functions` digest `38aa2359…` | `da49fd30…` (count 32), comment block of the measurement |
| `test_downgrade_chain_round_trip.py` | 12 upgrade-surface digests | + one for `0034` (no existing digest moved) |
| `specification-prices.test.ts` | filter returns `[DOCUMENT]`; empty state «…комплектов раздела АР»; chooser `1`, no «Конструкции» | filter returns `[DOCUMENT, OTHER_DOCUMENT]`; empty state «…комплектов с подтверждённым разделом», no «раздела АР»; chooser `2` with «…версия 2, раздел АР» and «Конструкции — версия 1, раздел КЖ» |
| `optimisation-proposals/rendering.test.ts` | `arDocumentSets` returns the АР set only; shape `proposals-no-ar-sets` with a KJ set | `classifiedDocumentSets` returns АР and КЖ; shape `proposals-no-classified-sets` with an unclassified set; chooser and loaded section name each set's section |
| `optimisation-proposals/failure.test.ts` | every registered reason has a sentence | the same, plus no sentence says «только для АР» / «раздела АР» and the vendor-list sentence names «раздела этого комплекта» |
| `fixtures.ts` (proposals) | local `unclassified()` in the test | exported `unclassifiedVersion()` |

No assertion was removed or loosened: every refusal that still exists (`version_unclassified`, `price_list_missing`, `analysis_missing`, `text_unavailable`, `specification_too_large`, `vendor_list_missing`, the `AM001` mismatches, the permission and scope refusals) keeps its test.

## Commands and results (lane stack `.env`, one pytest at a time; tests that write used a private database or the suites' own throw-away clones; no docker, no network)

| Command | Result |
| --- | --- |
| `pytest tests/unit/sections/test_pass_scope_migration_text.py` | 5 passed |
| `pytest tests/integration/db/test_pass_scope_migration.py` | 23 passed, 41 s |
| `pytest tests/integration/db/test_downgrade_chain_round_trip.py test_schema_invariant_inventory.py` | 20 passed |
| `pytest …/db/test_migration_lifecycle.py test_ar_v3_cite_stage_id_migration.py test_optimisation_proposals_migration.py test_classification_corrections_migration.py tests/unit/sections tests/unit/recovery/test_project_erase_pure.py` | 294 passed |
| `pytest …/recovery/test_schema_coverage.py test_grant_classification.py …/db/test_application_role_grants.py …/composition/test_erase_project_script.py` | 281 passed |
| `pytest …/recovery/test_synthetic_drill_fixture.py test_synthetic_drill_seed.py test_project_erase.py …/runs/test_v3_saved_text_layer_probe.py` | 167 passed |
| `pytest tests/unit/optimisation tests/integration/optimisation` (private DB) | 475 passed, 123 s |
| `pytest …/composition/test_specification_prices_over_http.py`; `…/test_optimisation_proposals_over_http.py` (private DB) | 6 passed; 6 passed |
| `pytest …/runs/test_section_run_text_layer_is_what_optimisation_reads.py` (private DB) | 3 passed |
| `pytest tests/contract/api_v1` | 366 passed; `tests/contract/domain_p02 shared_kernel architecture test_domain_identifiers_schema.py` 174 passed, 32 subtests |
| `npm --prefix web run api:verify` | OK, 104 operations, contract sha256 `14375c44…9357a` |
| `npx vitest run tests/unit/specification-prices tests/unit/optimisation-proposals tests/unit/optimisation tests/guards/frontend-lock.guard.test.ts` | 11 files, 137 passed |
| `npx vitest run tests/guards tests/unit/styles` | 27 files, 364 passed |
| `npx tsc --noEmit`; `npx eslint --quiet <changed files>`; `git diff --check` | exit 0; exit 0; exit 0 |

On the final committed tree (clean `git status`): `pytest tests/contract/program tests/contract/api_v1` **394 passed** in 38.8 s; `npm --prefix web run api:verify` OK; the governance one-liner on the task file prints `[]`. Private databases: one (`optall_*`, migrated to head, 15 MB) created for the writing suites and dropped; `list` afterwards `[]`. The suites' own throw-away clones were dropped by their fixtures. Observation, not mine: ten stale `a1_tpl_*` template databases (about 120 MB, last written 2026-10-26 01:43 to 19:03 UTC, no connections) belong to earlier runs and were left alone. Free disk stayed at 1.8 to 2.0 GiB.

## Integration notes

1. **Merge order with lane B.** `0034` is taken by this lane (PW4 section 8 reserved it for B); B becomes `0035`. B's final head pins are the same files as here (`schema_coverage.py`, `expected_facts.json`, the downgrade-chain digest, the `functions`/`constraints` digest of the invariant inventory, three prose sentences).
2. **Conflicts to expect.** `docs/program/CURRENT_STATE.md` line 12 and `docs/manual-tests/PC-01_prototype.md` line 39 (head sentences), `web/FRONTEND_LOCK.json` and the four generated client files (regenerate, do not merge by hand: `npm --prefix web run api:generate`, then set the digests), `contracts/api/v1/openapi.json` with its mirror. Lane WC (`d1400994`) touches `entities/project/**` and `widgets/dashboard/**`; this lane imports `projectSectionOf` from `@/entities/project` (read only) and does not edit it.
3. **Deploy.** Migration `0034` runs on `docker compose run migrate`; it is a function replacement, no table rewrite, no lock beyond the function. Rollback: `alembic downgrade 0033_ar_v3_cite_stage_id` is refused while any ПБ/ОВ/… pass exists; restore a backup instead.
4. **The browser journey is untouched.** 33 steps of `tests/e2e/pc01/journey/manifest.json` stay `pending_v3_activation` (P-10). They could now be re-bound to the journey's ПБ set; that is a separate `tests/e2e/**` lane.
5. **Residual AR wording** outside the lane: comments in `web/src/shared/api/query-keys.ts`, `web/src/_pages/project-detail/ui/project-detail-page.tsx`, and `docs/program/W60-OPT-*.md` reports (history, not edited). `entities/audit-run/model/routing-refusal.ts` and `shared/api/catalog-message.ts` are the integrator's.

## Limits

* The extraction of a real non-АР section run's Form-7 table is **not measured** (see above); the unit and integration positives use the АР tests' fake-reader page.
* An АР version still has a saved text layer only after a v3 Run publishes (`D-222`, `D-225`); this lane does not change that, so on a deployed stand «Спецификация и цены» for АР answers `analysis_missing` until the reviewed pack is installed.
* `PASS_REFUSAL_REASONS` and `STATES` still contain `section_not_ar`; nothing produces it. If the owner later wants the value gone, that is a breaking contract change.
* Vendor lists are per section already, but nothing seeds the other 14 sections' lists: an expert or administrator must set one before a pass over that section (`vendor_list_missing` says so in the screen's words).
* The proposals' «same kind of product» rule (`generator.py`) is unchanged and was written against АР vocabulary; its quality for other sections is unmeasured.

## Forbidden paths untouched

`git diff --name-only 6075df88..HEAD` lists 48 paths, every one in the task file's allowed list (contract, migration, server, tests, web, docs): no `bootstrap/**`, `analysis/**`, `runs/**`, `comparison/**`, `infra/**`, `fixtures/recorded/sections/**`, `tests/e2e/**`, `tests/support/**` other than `expected_facts.json`, `web/src/entities/project/**`, `web/src/widgets/dashboard/**`, root lock files, `DEBT_REGISTER.md`, rulings or ADRs; one migration only.
