# SECTION-POS-FULL-01 — the ПОС (POS) profile answers its open questions and is `reviewed`, without a human review

Task: `docs/program/tasks/SECTION-POS-FULL-01.md`. Branch `agent/section-pos-full-01`, base `3c80af0e` (`integration/ar-close-1026`). Plan item `PROD-14` (section `POS`); owner rulings `R-146ag`, `R-146ah`, `R-146ai`; template `SECTION-<CODE>-FULL-01` of `dispatch/PRODUCTION-WAVE-PW2B.md`. Format and practice follow `SECTION-AI-FULL-01.md`, `SECTION-PS-FULL-01.md` and `SECTION-KJ-FULL-01.md`.

## Result

The `POS` record in `W59-SECTION-PROFILES-01.md` has four open questions. Each has one written decision below: two are **K** (keep) and two are **N** (narrow); none is **X**. The four cross-section questions are applied as the wave table fixes them (all **K**, with the one exception the table itself allows for question 3, see C3). The prompt changed in three places, so `profile_version` is `1.1.0`, the recording is rebuilt, and `profile.json` and the `POS` line of the expectations file say `reviewed`.

**`reviewed` here is not expert verification.** Nobody has reviewed this profile: not an expert, not the owner (`R-146ag`, accepted risk `A-7`). The decisions were taken conservatively from the five hash-pinned legacy files and the record, and nothing was measured on real text. The status must not be quoted anywhere as a human review.

Premise: **match.** Package, status and version, the five source hashes at the pinned commit, the four questions, the four cross-section questions, the expectations line, the one recording and a green baseline (`211 passed`, `fixtures match`) are as the brief says (task file, P-01 to P-06). One difference from the other lanes: the POS prompt has no digit-bearing token at all, so the audit trap the AI lane met (a class designation in a condition that the source lacks) does not occur here (task file P-05).

## Decisions

Quoted question openings are the record's own words. «Condition n» means v1's numbered conditions in the prompt; «bullet» means a line of the hint block «Где в документе раздела ПОС искать …».

| # | Question (record) | Decision | Reason | Exact change |
|---|---|---|---|---|
| 1 | «марка крана уточняется в ППР», «решения уточняются при разработке ППР», «по выбору подрядной организации»: placeholder (root «уточн») or an accepted decision to defer the choice? | **K** | Cross-section decision (1) names «уточняется в ППР» itself: under v1's wording it is an explicit placeholder, and turning it into an accepted instruction is an expert's call that would silence findings. Condition 4 accepts a reference to a table, sheet, section or volume *where the value is given*; the text the model gets holds no ППР, so no value is given anywhere. «по выбору подрядной организации» carries no unfilled mark: it stays under v1's «и подобное», neither added as an example nor excluded. «ППР» and «подрядн» occur in neither the prompt nor the source (task file P-04), so nothing was written about them. | none |
| 2 | The sum of stage durations in the calendar plan is legitimately above the total because works overlap, and the «Итого» of volumes or investment by period may not give 100 %: is a total that disagrees with the sum of rows a finding? | **K** | Cross-section decision (2): recomputation stays excluded. The prompt has no bullet that sums stage durations or period shares: the durations bullet compares values written for the same stage or period in different places, and the closing paragraph already says «НЕ выполняешь и не перепроверяешь инженерные расчёты … Сравниваются только значения, прямо записанные в тексте». Two *written* totals that differ stay a finding under v1. Saying that overlapping works may exceed the total is a domain statement an expert must make. «Капитальные вложения» occur in neither the prompt nor the source. | none |
| 3 | The text layer of the calendar plan and of the workforce and machinery charts (Gantt charts, histograms) is usually torn: is a comparison of durations and headcount against them reliable, or is the bullet a systematic source of false findings? | **N**, for two bullets only | The record states the mechanism («обычно разорван» and «систематические ложные находки»), which is the exception the wave table allows for question 3 (cross-section C3: **N** for the bullet the record names, that bullet only). A number read from a chart scale, a tick or a bar loses its stage or category name, and the two bullets send the model to exactly those sources («в календарном плане», «в графике потребности в кадрах») without saying how to read them. Condition 1 asks for a direct indication of what a value relates to but is phrased for different objects, not for detached numbers. The edit adds one condition before the comparison and removes comparisons only. The machinery bullet is not changed: it names the table «ведомость потребности в машинах и механизмах», not the chart, and the question concerns durations and headcount. | durations bullet and headcount bullet, see below |
| 4 | Maximum headcount and headcount in the most numerous shift, the latter taken in the temporary-buildings calculation (often a share of the maximum): is condition 2 plus the explanation in the list of places enough that they are not compared as one? | **N** | Not enough as written. The headcount bullet itself lists «(максимальная и в наиболее многочисленную смену)» as attributes, while condition 2's near-miss list had «численность рабочих и общая численность работающих» and no pair for maximum against shift; the record states that the buildings calculation takes the shift value, so the pair is a stated false-positive source. The edit names the pair in condition 2, using the prompt's own words. Maximum is still compared with maximum and shift with shift, so a real mismatch between two values of the same attribute is still reported. No number, norm or designation. | condition 2, see below |

Cross-section decisions (the same for every lane; this lane agrees with them and has nothing to report against them):

| # | Question | Decision | POS-specific note |
|---|---|---|---|
| C1 | Site and contractor phrases | **K** | Covers question 1. The prompt keeps them as placeholders under v1's wording. |
| C2 | «Итого» against the sum of rows | **K** | Covers question 2. No recomputation bullet exists in the POS prompt. |
| C3 | Text read from sheets | **K**, except the two bullets of question 3 | The only bullets the POS record names as false-positive sources are the durations and headcount ones (question 3), narrowed as the table allows. The bullets that read labels («в подписях стройгенплана и схем монтажа», «в подписях схемы временных сетей», «в подписях разрезов котлована», «в подписях плана демонтажа») are not named by the record and stay unchanged. |
| C4 | Missing items | **K** | No third kind of observation; condition 5 stays; the record's excluded list («полнота перечня видов работ» and similar) stays excluded. |

## The prompt change in words

Three edits in `system_prompt.md`; everything else is byte for byte what it was (`test_every_system_prompt_keeps_the_v1_question_categories_and_output_contract` holds v1's question, categories, the start of conditions 1, 2 and 4, conditions 3 and 5, and the output contract).

1. **Durations bullet (question 3).** After «в календарном плане и в тексте записки» it now says: a value read from the text layer of the calendar-plan diagram is compared only if the text directly states which stage or period it belongs to; numbers of the diagram's scale and tick marks that the text leaves detached from such a statement are not compared.
2. **Headcount bullet (question 3).** After «в расчёте временных зданий и сооружений» it now says the same for the workforce chart: a value read from its text layer is compared only if the text directly states what it relates to (a category of workers, the maximum, or a period); numbers of the chart's scale and ticks detached from such a statement are not compared.
3. **Condition 2 (question 4).** The near-miss list has one more pair, «максимальная численность работающих и их численность в наиболее многочисленную смену», between the headcount pair and the crane pair. The closing sentence of the condition is unchanged.

New numerals: none. New norm references: none. New class designations: none. Findings: only narrower than before.

## Audit of numerals and designations

The same script as the AI report (`docs/program/SECTION-AI-FULL-01.md`, section «Audit of numerals and designations»; this lane ran its text unchanged, from outside the repository). Before the edit and after it the result is the same: no digit-bearing token; the capital tokens are `TBD`, `XX`, `ГОСТ`, `ЖЕ`, `И`, `ИТР`, `НЕ`, `ПОС`, `СП`, `ТОГО`, `ТОМ`. Of these `И`, `ПОС` and `СП` occur in the source; the others are v1's own words and upper-case emphasis, and `ИТР` (see assumption 5). To show the audit can fail, mutation M9 below puts «до 2,0 м (класс Г1–Г4)» into the prompt: the script then prints `'2,0' in legacy source: False` and `'Г1–Г4' in legacy source: False`.

## Assumptions an expert would still want to check

Short and honest (`A-7`): none of these was checked by anyone with domain knowledge.

1. **Question 1 (K).** Whether the model flags «по выбору подрядной организации» is left to v1's wording. The profile neither lists nor excludes it; «уточняется в ППР» stays a placeholder.
2. **Question 2 (K).** The only guard against a model that sums stage durations anyway (and finds that the sum exceeds the total) is the existing sentence that forbids recalculation. It is unmeasured, and if it fails the false findings come back.
3. **Question 3 (N).** Where the text layer of a Gantt chart or histogram is torn and the stage name is not next to its number, a real mismatch in duration or headcount is no longer reported; where the stage or category and its number stand in one row or caption, the comparison stays. The words «диаграмма», «шкала», «отметки» come from the record's question, not from the source (the source has only «Диаграмма Ганта» once). The edit does not tell a table from a chart: a calendar plan given as a clean table is covered only through «значение … из текстового слоя диаграммы», which a model may or may not apply to a table.
4. **Question 4 (N).** If an expert holds that the shift headcount must not exceed the maximum, or must be a stated share of it, that is a calculation or a judgement and outside v1's question; this profile does not check it.
5. **Terms from the earlier drafting, not from the source.** The hint bullets and condition 2 carry words that none of the five files contains: «ИТР» (an abbreviation of a staff category; not a class designation and no number, so the audit's rule does not remove it), «в наиболее многочисленную смену», «высота подъёма крюка». None of the three is an open question or a stated false-positive source, so none was changed. An expert should confirm or strike them.
6. **Nothing was measured.** The recording is synthetic, authored by hand over the AR corpus; it proves routing and replay and says nothing about how the profile performs on a real ПОС volume. No field case exists (`A-5`).

## Files changed

| File | Change |
|---|---|
| `src/auditmanager/analysis/text/profiles/pos/system_prompt.md` | the three edits above |
| `src/auditmanager/analysis/text/profiles/pos/profile.json` | `profile_version` `1.0.0` to `1.1.0`; `status` `draft` to `reviewed` |
| `fixtures/recorded/sections/pos/e399ef16a725e478d9e15734776b81de7de726140bafbc6bea8b4126223785f1.json` | rebuilt by `build_fixtures.py`; replaces `9fd79951…ea15.json`; the diff against the old file is `origin.profile_status` (`reviewed`), `origin.prompt_bundle_sha256` (`8f91b1d5…3c05` to `30c5af14…0c4c`) and `request_sha256`; the authored reply, usage and latency are unchanged |
| `tests/unit/analysis/text_profiles/section_profile_expectations.json` | the `POS` line only: `reviewed`, `1.1.0` |
| `docs/program/tasks/SECTION-POS-FULL-01.md`, this report | records |

The builder writes all fourteen recordings; the other thirteen came out byte-identical (`git status` shows no other recording).

## Modified tests: before and after

No test file is edited. The `POS` line of the expectations file is data that the registry, package, HTTP and web tests read. Before: `{"code": "POS", "status": "draft", "profile_version": "1.0.0"}`, and each of those tests asserted that `profile.json`, the registry, the HTTP list and the web fixture agree with the line. After: `{"code": "POS", "status": "reviewed", "profile_version": "1.1.0"}` and each asserts the same agreement. Nothing is weakened.

## Mutation table

Each row edits one thing in the working tree (committed at `339b45ac`), runs the guard, restores with `git checkout` and proves the restore by a SHA-256 over the three files and the recording (`restored=True`, `git status --short` empty). The section set is `test_text_profile_registry.py`, `tests/unit/analysis/text_profiles`, `tests/integration/sections/test_section_recordings.py` and `tests/contract/analysis_packages` (211 cases); the unmutated tree is `211 passed`.

| # | Mutation | Guard | Result when mutated |
|---|---|---|---|
| M1 | `profile.json` status `reviewed` back to `draft` (version kept) | section set | 4 failed, 207 passed: registry `test_the_tree_registers_without_error_and_without_an_ar_package`; `test_every_line_agrees_with_its_package_profile_json`; packages `test_every_profile_manifest_has_the_text_profile_1_shape`; recordings `test_the_builder_reports_no_drift` |
| M2 | `profile.json` version `1.1.0` back to `1.0.0` (status kept) | section set | 3 failed, 208 passed (the first three of M1) |
| M3 | the `POS` expectations line back to `draft` / `1.0.0` (`profile.json` kept) | section set | 3 failed, 208 passed (the same three) |
| M4 | the `POS` expectations line, status only back to `draft` | section set | 3 failed, 208 passed (the same three) |
| M5 | `system_prompt.md` back to the base text (recording kept) | section set | 7 failed, 204 passed: `test_each_section_has_one_synthetic_recording_keyed_to_its_own_request[POS]`, `test_the_builder_reports_no_drift`, `test_the_served_adapter_answers_each_recorded_section_and_the_canonical_alone_does_not[POS]`, `test_no_other_directory_answers_a_section_request[POS]`, `test_a_section_reply_filed_under_another_key_is_not_replayed[POS]`, `test_each_recording_replays_through_the_stage_under_its_own_profile[POS]`, `test_every_recording_carries_its_own_authored_usage_signature` |
| M6a | only the durations-bullet sentence removed | section set | 7 failed, 204 passed (the seven of M5) |
| M6b | only the headcount-bullet sentence removed | section set | 7 failed, 204 passed (the seven of M5) |
| M6c | only the condition-2 pair removed | section set | 7 failed, 204 passed (the seven of M5) |
| M7 | the recording back to the base file (new one removed) | section set | 7 failed, 204 passed (the seven of M5) |
| M8 | `origin.profile_status` `reviewed` to `draft` inside the new recording (key kept) | section set; `build_fixtures.py --check` | 1 failed, 210 passed (`test_the_builder_reports_no_drift`); `--check` rc 1 listing the file |
| M9 | a number and a designation absent from the source put into the prompt («до 2,0 м (класс Г1–Г4)») | the audit script | prints `'2,0' in legacy source: False` and `'Г1–Г4' in legacy source: False` (not a repository test, see the limit below) |
| M10 | the `POS` expectations line back to `draft` / `1.0.0`; and, separately, `profile.json` status back to `draft`, on the lane stack | `test_analysis_profiles_over_http.py` | 1 failed, 3 passed both times: `test_every_row_is_the_registry_entry_the_application_routes_by` |
| M11 | the same two mutations, in the web test | `npx vitest run tests/unit/analysis-settings` | 1 failed, 94 passed both times: `has a line for exactly the packages that exist, with the status and version each declares`, `POS: status draft in the file, reviewed in profile.json` and `POS: status reviewed in the file, draft in profile.json` |

After each restore the tests were green again. Probe before the rebuild: with the prompt edited and the recording not rebuilt, `test_section_recordings.py` had `7 failed, 102 passed` and the builder's `--check` exited 1 listing the new key and the old file as `(stale)`.

## Commands and results

From `/root/projects/PDF-Analysis/.local/worktrees/section-pos-full-01`, shared venv, one pytest at a time. `BS` is `/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages`.

| Command | Result |
|---|---|
| section set (above), base `3c80af0e` | `211 passed` |
| section set, after the change | `211 passed` |
| `PYTHONPATH=src:$BS .venv/bin/python fixtures/recorded/sections/build_fixtures.py`, then `--check` | rc 0 (`wrote …e399ef16…`, `removed …9fd79951…`); `--check` rc 0 `fixtures match` |
| `tests/integration/composition/test_analysis_profiles_over_http.py`, lane `.env` exported, base and after | `4 passed`, `4 passed` |
| `npx vitest run tests/unit/analysis-settings` in `web/` (`node_modules` linked from `gate-night`) | 7 files, `95 passed` |
| governance one-liner on the task file | `[]` |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, `git diff --check` | see «Final checks» |

Free disk at the start and at the end of the lane: 1.8 GiB and 1.7 GiB (`df -h /`). No docker command, no push, no model call, no process killed.

## Integration notes

1. **The web label of `reviewed`** was already corrected on this base (`607ee47a`, «the reviewed profile label no longer claims expert verification»); the web test passes with it (`95 passed`). Nothing for this lane.
2. **Identity:** `analysis_profile_id` and `prompt_bundle_id` are unchanged, while the bundle's text and hash and the profile hash (through the version) changed. A run of the draft `POS` profile that is already stored carries the old `analysis_profile_sha256` and `prompt_bundle_sha256`; the registry resolves by the id pair and serves only the new text. Development stand only, no migration (`R-146ah`).
3. **The recording's `origin`** still names `W59-ANALYSIS-SETTINGS-01` as its authoring task and now says `profile_status: reviewed`; its statement still says «Not field evidence for the profile's review». The builder was not touched.
4. **e2e manifest:** the step with the selector `tr[data-profile="draft"]` stays valid while any other section is `draft` (TX, KM, OV, VK, PT, EOM, SS, ITP, GP and PB are, on this base).
5. **Merge:** the expectations file changes on the `POS` line only, so lanes merge without conflict; if another lane's merge also changed any recording, re-run `build_fixtures.py --check`, then the section set, the HTTP test and the web test after the last section merges.
6. **Record:** `W59-SECTION-PROFILES-01.md` still lists the four POS questions as open and says every profile is `draft` (forbidden path for the lane). The integrator should point to this report, without calling the status an expert review.

## Limits

- No test holds the three prompt edits themselves. Their wording is held only by the recording's request key (an edit without a rebuild goes red, rows M5 to M7) and by the manual audit; a content test or a cross-section guard that checks every prompt's numerals and designations against its pinned source is outside this lane's paths and is a candidate for the integrator.
- The effect of the N edits on a model's answers is unmeasured; no model was called.
- The edits use the lane's reading of a text-only setting; an expert may disagree with any decision in the table, and the report says where.

## Forbidden paths untouched

`git diff --name-only --no-renames 3c80af0e..HEAD`, run on the tip of the branch, prints exactly these seven paths, all inside the task's allowed paths (without `--no-renames` git folds the old recording into a rename and prints six):

```text
docs/program/SECTION-POS-FULL-01.md
docs/program/tasks/SECTION-POS-FULL-01.md
fixtures/recorded/sections/pos/9fd7995188bd781df195e8aa285573d4f5dae8165d95e07c665dc11b93d2ea15.json
fixtures/recorded/sections/pos/e399ef16a725e478d9e15734776b81de7de726140bafbc6bea8b4126223785f1.json
src/auditmanager/analysis/text/profiles/pos/profile.json
src/auditmanager/analysis/text/profiles/pos/system_prompt.md
tests/unit/analysis/text_profiles/section_profile_expectations.json
```

No other section's files, no `W59-SECTION-PROFILES-01.md`, registry, `P02_LOCK.json`, `contracts/**`, migration, `web/**` or `infra/**` appears; `build_fixtures.py` is unchanged. The legacy repository was only read (`git status --short` there: 0 lines before and after).

## Final checks

On the committed tree (clean, `git status --short` empty; only this report and the task file differ from the tree the mutations ran on):

| Command | Result |
|---|---|
| `pytest tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` | `105 passed` |
| governance one-liner on `docs/program/tasks/SECTION-POS-FULL-01.md` | `[]` |
| `git diff --check 3c80af0e..HEAD` | rc 0 (a first run flagged trailing spaces in the pasted P-04 output of the task file; stripped) |
| section set, `build_fixtures.py --check`, HTTP test (lane `.env`), `vitest` analysis-settings | `211 passed`; `fixtures match` (rc 0); `4 passed`; 7 files, `95 passed` |
