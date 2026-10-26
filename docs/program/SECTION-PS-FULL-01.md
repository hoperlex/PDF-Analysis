# SECTION-PS-FULL-01 — the ПЗ (PS) section profile: every open question answered, status `reviewed` with no human review

Task: `docs/program/tasks/SECTION-PS-FULL-01.md`. Branch `agent/section-ps-full-01`, base `0e663fd0e608fcf5f79075ea71713c24ddf027e5` (`integration/ar-close-1026`), product commit `ca5b18d1`. Dispatch: `docs/program/dispatch/PRODUCTION-WAVE-PW2B.md`, section lane template; owner rulings `R-146ag`, `R-146ah`, `R-146ai`; accepted risk `A-7`.

## Result

The five open questions of the `PS` record in `W59-SECTION-PROFILES-01.md` and the four cross-section questions each have one decision: `K` seven times (three of the five section questions and all four cross-section questions), `N` twice (the other two section questions), `X` never. The two `N` decisions are one edit of condition 2 of `ps/system_prompt.md`; nothing else in the prompt moved. `profile_version` is `1.1.0` (the prompt text changed), `status` is `reviewed` in `profile.json` and in the `PS` line of the expectations file, and the recording is rebuilt by `build_fixtures.py`.

**`reviewed` here carries no human review.** Neither an expert nor the owner read this section (`R-146ag`, `A-7`). The word records that a lane answered the questions of the record conservatively and traceably; it is not verification of anything, and no sentence of this report says an expert checked a thing.

Premise: **match.** The package, the record's five questions, the four cross-section questions, the legacy repository at `16ba8e5d…` with all five hashes equal to `ps/profile.json`, the `PS` expectations line and a green baseline (50 + 161 passed, `fixtures match`) were all as the dispatch says (outputs in the task file, P-01 to P-06). No discrepancy, nothing to stop for.

## Decisions

| # | Question (record wording, shortened) | Decision | Reason | Exact change |
|---|---|---|---|---|
| PS-1 | Строка «Итого» (квартирография, ТЭП) against the sum of rows: a finding? | **K** | Cross-section rule (2). The prompt already excludes recomputation («НЕ выполняешь и не перепроверяешь инженерные расчёты … Сравниваются только значения, прямо записанные в тексте»). Two totals that are both *written* in the text and differ stay an `internal_contradiction` under v1; only counting the rows is out. | none |
| PS-2 | Values from the ГПЗУ and the technical conditions (предельная этажность, максимальный процент застройки, разрешённая мощность) next to design values: compared or not? | **N** | A stated false-positive source. A limit and the design value of the same indicator differ by nature, and putting them side by side is a check of the design against an external requirement, which the prompt already excludes for СП, ГОСТ, ПП РФ № 87 and the laws. The prompt already names the same shape for energy («расчётное и нормируемое значение»). Wording only: no number, no norm, no class. It narrows only: the pair names a limit against a design value, not a limit against a limit, so v1's rule for two statements of the same limit is not touched by the wording. | condition 2 gets the pair «предельное значение показателя, приведённое из ГПЗУ или технических условий, и проектное значение того же показателя» |
| PS-3 | «будет определено на стадии РД», «уточняется заданием на проектирование», «ТУ будут получены»: placeholder or deferred decision? | **K** | Cross-section rule (1): turning a deferral into an accepted instruction is an expert's call and would silence findings. v1's condition 4 already accepts a reference to a table, sheet, section or volume where the value *is* given; a deferral to a later stage or to a document outside the text is not that. «ТУ будут получены» carries no unfilled mark and v1's definition decides it as before. | none |
| PS-4 | Values of other volumes retold in the записка («по разделу АР общая площадь …») against the записка's own ТЭП: `internal_contradiction` or an excluded cross-volume check? | **K** | Both values are written in this one document, so the case is v1's single question (two places of one document). What is excluded is comparison with a volume the model does not have (the record's «Other volumes»); nothing of the other volume is available here. Excluding the retelling would silence a real in-document inconsistency. A retelling that names a different variant, stage or building is already no finding under condition 1. | none |
| PS-5 | Outdoor-air design temperatures of different probability and for different systems; architectural against fire-technical height: is condition 2 enough? | **N** | A stated and near-certain false-positive source: a записка legitimately carries several outdoor design temperatures (heating, ventilation, different probability) and two heights, so the bullets «расчётная температура наружного воздуха» and «высота здания (архитектурная и пожарно-техническая)» would bring differing values to the model every time. Wording only, no value anywhere. | condition 2 gets «расчётные температуры наружного воздуха для разных систем или разной обеспеченности, архитектурная и пожарно-техническая высота здания» |
| C-1 | Site and contractor phrases («уточнить по месту») | **K** | Dispatch table: they stay explicit placeholders under v1's wording. | none |
| C-2 | «Итого» against the sum of rows | **K** | Dispatch table; same as PS-1. | none |
| C-3 | Text read from sheets (labels, title blocks, leaders) | **K** | Dispatch table: `K` unless the section's own record names a systematic false-positive bullet. The `PS` prompt has no bullet about sheet labels («подписи планов/схем» does not occur; `grep` for «подпис», «штамп», «выноск», «планов» finds nothing; the places it lists are chapters, tables, the energy passport, the initial data and the appendices). So there is no bullet to narrow. | none |
| C-4 | Missing items | **K** | Dispatch table: no third kind of observation (it would be a contract change). | none |

The lane agrees with the table of the dispatch and has nothing to report against it.

## The prompt diff in words

Only condition 2 («Разные признаки») changed. Its list of near-miss pairs, which had three (этажность и количество этажей; общая площадь здания и общая площадь квартир; расчётное и нормируемое значение удельной характеристики расхода тепловой энергии), has three more: a limit taken from the ГПЗУ or the technical conditions against the design value of the same indicator; outdoor-air design temperatures for different systems or of different probability; the architectural and the fire-technical height of the building. The closing sentence of the condition («убедись, что это буквально одна и та же характеристика») is unchanged. Condition 2 now spans `ps/system_prompt.md` lines 66 to 72 (it was 66 to 69); the diff adds no digit, no norm reference and no class designation (`ПП РФ № 87` was there before and is in the legacy `role.md`). The question, both categories, conditions 1 and 3 to 5, the no-verdict sentence and the whole output contract are byte-for-byte as before, which `test_every_system_prompt_keeps_the_v1_question_categories_and_output_contract` holds.

## Files

| File | Change |
|---|---|
| `src/auditmanager/analysis/text/profiles/ps/system_prompt.md` | condition 2, three pairs added |
| `src/auditmanager/analysis/text/profiles/ps/profile.json` | `profile_version` `1.0.0` to `1.1.0`, `status` `draft` to `reviewed` |
| `tests/unit/analysis/text_profiles/section_profile_expectations.json` | the `PS` line only: `reviewed`, `1.1.0` |
| `fixtures/recorded/sections/ps/caf8aa0f…ab85.json` | new, built by `build_fixtures.py` (key = digest of the new request; `origin.profile_status` is `reviewed`, `prompt_bundle_sha256` `6a34bb49…`) |
| `fixtures/recorded/sections/ps/5dad5c5f…11f3.json` | removed by the same run (its key belonged to the old prompt) |
| `docs/program/tasks/SECTION-PS-FULL-01.md`, this report | records |

The builder rewrote the other thirteen sections' files too and every one came out byte-for-byte as it was (`git status` shows only the two `ps/` files). The recording's reply (a synthetic fire-resistance finding) is unchanged apart from its key and origin; it proves routing, nothing about the profile (`fixtures/recorded/sections/README.md`).

## Modified tests: before and after

No test file is edited. The `PS` line of the expectations file is data that the registry, package, HTTP and web tests read; each of them asserted `(status, profile_version) == the line` before and asserts the same after. Nothing is weakened.

## Mutation table (every guard shown failing)

One mutation at a time, applied to the real file, one test group run, the file restored and its SHA-256 checked, then the group run again (green). `unit` = `tests/unit/analysis/test_text_profile_registry.py` + `tests/unit/analysis/text_profiles` (50 tests); `rec` = `tests/integration/sections/test_section_recordings.py` (109); `http` = `test_analysis_profiles_over_http.py` (4, lane stack); `web` = `analysis-settings.test.ts` (22).

| Mutation | unit | rec | http / web |
|---|---|---|---|
| `profile.json` status back to `draft` (the dispatch's first proof) | 3 failed, 47 passed (registry tree, line-agrees, manifest shape) | 1 failed (`test_the_builder_reports_no_drift`: `origin.profile_status`) | web: 1 failed, 21 passed: `PS: status reviewed in the file, draft in profile.json` |
| `profile.json` version back to `1.0.0` | 3 failed | 109 passed (the recording test does not read a version) | not run |
| the `PS` line only back to `draft` / `1.0.0` (the dispatch's second proof) | 3 failed | 109 passed | http: 1 failed, 3 passed: `PS: the served (status, profile_version) is not the expectations file's` |
| the `PS` line, status only back to `draft` | 3 failed | not run | not run |
| prompt: remove the ГПЗУ/ТУ pair | 50 passed (no test names the wording) | 8 failed, 101 passed | not run |
| prompt: remove the temperature and height pairs | 50 passed | 8 failed, 101 passed | not run |
| prompt: one letter of the added text changed | 50 passed | 8 failed, 101 passed | not run |
| the new recording deleted | not run | 8 failed, 101 passed (`recording_missing`, drift) | not run |
| the old recording restored beside the new one | not run | 2 failed, 107 passed (stale file, one recording per section) | not run |

All restored runs: unit 50 passed, rec 109 passed, http 4 passed, web 22 passed.

**What the table says about the new wording.** No test reads the added sentence; its only guard is the recording key, which is the digest of the exact prompt bytes, so any change to the `N` wording is red until the recording is rebuilt (rows 5 to 7). A test that pins the two pairs by content would need a file outside this lane's allowed paths; it is not written (limit below).

## Commands and counts

Run in `.local/worktrees/section-ps-full-01`, one pytest at a time, `PYTHONPATH=src:<bootstrap site-packages>` with the repository `.venv`; the HTTP test with the lane `.env` exported.

| Command | Result |
|---|---|
| `pytest -q tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles` | 50 passed |
| `pytest -q tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages` | 161 passed |
| `python fixtures/recorded/sections/build_fixtures.py --check` | `fixtures match` |
| `pytest -q tests/integration/composition/test_analysis_profiles_over_http.py` (lane `.env`) | 4 passed |
| `npx vitest run tests/unit/analysis-settings` in `web/` | 7 files, 95 passed |
| governance one-liner on the task file | `[]` |
| `pytest -q tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` | see the end of this section |
| `git diff --check` | exit 0 |

## Integration notes

- The lane touches nothing outside its five paths: `git diff --name-only 0e663fd0..HEAD` lists the `ps` prompt, the `ps` profile, the two `ps` recordings, the expectations file and the two docs.
- The expectations file is one line per section, so this lane merges without conflict with the other section lanes; the `PS` line is the only one changed.
- **The web label of `reviewed` says «проверен экспертом»** (`web/src/entities/analysis-profile/model/presentation.ts`, `ANALYSIS_PROFILE_STATUS_LABELS`, pinned in `analysis-settings.test.ts`). With the first section lane merged, the settings screen will show the words «проверен экспертом» on a profile no expert saw, which is what `A-7` says must not happen. This is outside the lane (`web/**` is forbidden) and is the integrator's to settle: a different label for the section profiles, or the owner's decision to live with it.
- `tests/e2e/pc01/journey/manifest.json` selects `tr[data-profile="draft"]` (the journey step that reads a draft row). While any section is still `draft` it passes; when the last section lane merges, no row matches. `PB` is the one that may stay `draft` (no legacy source), but the integrator should check before the last merge.
- `W59-SECTION-PROFILES-01.md` still says every profile is `draft` and a debt (the dispatch forbids editing it). Prose that says «all draft» about the packages is stale for `PS` from this lane on.
- The rebuilt recording has `origin.profile_status: reviewed` and the unchanged statement «Not field evidence for the profile's review», which stays true; its `task_id` stays `W59-ANALYSIS-SETTINGS-01` (the builder pins it for the first four sections and a test holds that).
- An independent read-only judge of the decisions (`R-146ag`, quality control) reads the table above and the prompt diff; it needs no stack.

## Limits and what a domain expert would still check

Short and honest (`A-7`): none of this was reviewed by a person.

1. **The two pairs are wording, not evidence.** There is no field case for the `PS` profile (no positive, no negative case, no real записка run). `N` was chosen because the pair names a false-positive source the record itself states; whether a real записка would have produced those false findings is unmeasured.
2. **Temperature wording.** «Разной обеспеченности» and «для разных систем» come from the W59 record's question, not from the legacy files (checked: none of «обеспеченност», «температур», «ГПЗУ», «предельн», «пожарно-техническ» occurs in the five legacy files). They are words that exclude, with no number; an expert may prefer other words for which values count as one attribute.
3. **A limit exceeded by the design** is now outside what this profile reports even when both numbers are in the text; that is a conformity check (out of v1's scope and for the norms stage), not a contradiction of one attribute.
4. **Deferral phrases stay placeholders** (PS-3). If an expert accepts «на стадии РД» as a decision, the profile will over-report on it; the lane chose over-reporting to silencing.
5. **Vocabulary already in the draft prompt that the legacy files do not contain**, observed and *not* changed because it is outside the five questions: «ГПЗУ» and «задание на проектирование» (placeholder bullet), «снеговой и ветровой районы» and «сейсмичность» (climate bullet), the technical floor in «этажей (надземных, подземных, технических)», and «лифтов … для транспортирования пожарных подразделений» (the legacy has «лифты для МГН» and «типы»; this last phrase is the closest to a class designation among them, though it names no class or number). They are attribute names inside the «where to look» hints, which the prompt says are not a third category and not a list of required findings. An expert should confirm or strike them.
6. The recording is synthetic and proves routing, not detection.
7. The wording of the `N` edits is pinned by the recording key only (mutation table), not by a content test.
