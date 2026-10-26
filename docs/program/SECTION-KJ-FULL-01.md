# SECTION-KJ-FULL-01 — the КЖ (KJ) profile: every open question decided, recording rebuilt, status `reviewed`

Task: `docs/program/tasks/SECTION-KJ-FULL-01.md`. Branch `agent/section-kj-full-01`, base `0e663fd0e608fcf5f79075ea71713c24ddf027e5` (`integration/ar-close-1026`). Rulings: `R-146ag`, `R-146ah`, `R-146ai`; risk `A-7`. Executor: a Sonnet lane. No push, no tag, no container command, no model call.

**Read this first (`A-7`).** Nobody reviewed this section: not an expert, not the owner. The status `reviewed` on the KJ profile means a lane wrote a decision for every open question of its record and rebuilt its recording. It is **not** expert verification and must not be quoted as one.

## Result

The five open questions of the KJ record in `W59-SECTION-PROFILES-01.md` (and the four cross-section questions) have one written decision each. Three are K (keep), two are N (narrow; both are edits of the hint block of `system_prompt.md`, and the second N covers two bullets), none is X. `profile.json` now says `reviewed` at `1.1.0`, the synthetic recording is rebuilt by the builder, and the `KJ` line of the expectations file agrees. The two v1 categories, the response schema, the token limits and the output contract are untouched; no contract or migration changes (`R-146ah`: head stays `0032_ar_v3_run_group`).

## Decisions

Premise first: all inputs were as described (task file, P-01 to P-06). The legacy source is on the host at the pinned commit `16ba8e5d`, clean, and its five KJ hashes equal the pins.

| # | Question (short) | Decision | Reason | Exact change |
| --- | --- | --- | --- | --- |
| C1 | Site and contractor phrases (cross-section) | **K** | Brief: they stay explicit placeholders under v1's wording; turning them into accepted instructions is an expert's call and would silence findings. No disagreement. | none; applied through Q2 |
| C2 | «Итого» against the sum of rows (cross-section) | **K** | Brief: recomputation stays excluded. No disagreement. | none; applied through Q4 |
| C3 | Text read from sheets (cross-section) | **K** | Brief: K unless the section's record names a systematic false-positive bullet for sheet text. The KJ record names none (Q5c is about conditions, Q3 about the register; both decided on their own). | none |
| C4 | Missing items (cross-section) | **K** | Brief: no third kind of observation (a contract change). | none |
| Q1 | Old and new rebar designations (А-III and А400, А-I and А240) or concrete class and mark (В25 and М350) for one item: contradiction or one value? | **K** | Saying they are one value needs an equivalence table. «А400», «А-I» and «М350» occur nowhere in the five hash-pinned legacy files (P-04), so writing it would add class designations the source does not hold, which the brief forbids. A general sentence «different notation is not a contradiction» would also silence real conflicts between genuinely different classes (the source names А-III and А500С as separate classes). v1's condition 2 («убедись, что это буквально одна и та же характеристика») stays the only guidance, and a finding is an observation the expert decides on. | none |
| Q2 | «длину стержней уточнить по месту», «отверстия выполнять по заданию смежных разделов», «отметки уточнить по факту»: placeholder or accepted instruction? | **K** | Cross-section C1. As the prompt reads, a phrase carrying one of the marks («уточнить», «уточняется», …) is an explicit placeholder; a phrase with no such mark that points to other sections («по заданию смежных разделов») falls under condition 4 (a reference to the place where the decision is given). Changing that is an expert's call. | none |
| Q3 | The deviation register holds two values of one attribute (по ПД and по РД) by nature: false findings, keep the bullet? | **N** (not X) | By definition the register lists deviations of the рабочая документация from the проектная (`drawing_types.md` line 4; `checklist.md` line 116), so a row carries two different values on purpose and nothing in the prompt said that this pair is not a conflict. Dropping the bullet (X) would silence the real cross-check of the accepted value against the sheets, which the source asks for («Соответствие отклонений техническим решениям»). The edit removes one false-positive source and adds no comparison. | one sentence appended to the register bullet (see below) |
| Q4 | «Итого» of the steel consumption sheet or the rebar specification against the sum of rows? | **K** | Cross-section C2. Recomputation is arithmetic, which the prompt excludes («НЕ выполняешь и не перепроверяешь … расчёты»). The mass bullet keeps comparing values written in two places («прямо указанные»), not a total against its rows. | none |
| Q5a | Is the list of places complete for stages П and Р (no reinforcement sheets at П)? | **K** | The list is a hint, not a list of required findings; a place absent at stage П yields nothing under condition 5 («утверждения просто нет — это не находка»). By my reading every sheet type of `drawing_types.md` that carries attribute values maps onto a bullet (`general_view`, `title_block`, `other` carry none). Adding places is widening. | none |
| Q5b | Cross-check the set code (шифр комплекта) in the sheets' title blocks? | **K** (stays excluded) | A document requisite, not an attribute of a construction. The source writes it as a template with variable parts («13АВ-РД-КЖx.y-Kn», `project_params.md` line 13), so codes on different sheets can differ by design; a new bullet would add a false-positive source and a new comparison, which is widening. Whether they differ in a real document is the expert's knowledge. | none |
| Q5c | Do the cover and anchorage bullets give systematic false findings under different conditions (top and bottom bars, tension and compression, concrete class)? | **N** | The anchorage bullet said «при одних и тех же условиях» without saying which, and the cover bullet separated only the bar position. The source ties cover to contact with the ground and to exterior surfaces (`checklist.md` line 42), and speaks of the tension zone (line 33) and of top and bottom bars (lines 25, 57, 87). The edits tell the model that values the text itself attributes to different conditions are not a contradiction. They only remove comparisons. | two bullets edited (see below) |

Q5 is three questions in one sentence; each part has exactly one decision (K, K, N).

## The diff of the prompt, in words

`git diff 0e663fd0 HEAD -- src/auditmanager/analysis/text/profiles/kj/system_prompt.md`: 8 lines added and 2 removed, all inside the hint block «Где в документе раздела КЖ искать …». The opening, the question, the two categories, the five conditions, the exclusion paragraph and the output contract are byte for byte as before (the package test holds them).

1. **Cover bullet** (Q5c). The parenthesis «отдельно для верхней, нижней и поперечной арматуры» now also says «а также отдельно для поверхностей, соприкасающихся с грунтом, и наружных поверхностей», and the bullet ends with «значения, отнесённые в тексте к разным условиям, не противоречат друг другу».
2. **Anchorage and lap bullet** (Q5c). Ends with «значения, отнесённые в тексте к разным условиям (верхняя или нижняя арматура, растянутая или сжатая зона, разные классы бетона), не противоречат друг другу».
3. **Register bullet** (Q3). Ends with «реестр по своему назначению приводит для одного признака два значения — проектной и рабочей документации, — и их различие внутри самого реестра не противоречие».

`profile.json`: `status` `draft` to `reviewed`, `profile_version` `1.0.0` to `1.1.0` (the prompt text changed, so the version moves; the value follows the example of `PROD-14-0-EXPECTATIONS-01`). Identities unchanged; the bundle `content_sha256` moved `3ac1ac03…4d70` to `3feca94f…56aa`.

## Assumptions an expert would still want to check

Short and honest (`A-7`): none of this was checked by a person.

- The three N edits are the lane's reading of the record and the legacy files. Their effect on a real model is not measured: the recording is synthetic, authored by the builder, and no model was called.
- Q1 leaves the question of old and new designations to v1's behaviour. An expert may want an explicit equivalence rule; none was written because the source holds none.
- In the anchorage sentence, the conditions «сжатая зона» and «разные классы бетона» come from the record's question, not from the legacy files (the files hold «растянутой зоне» and top and bottom bars only). No number, norm reference or class designation was added.
- The prompt says «степень агрессивного воздействия среды» and «коэффициент надёжности по ответственности» where the source says «класс агрессивности среды» and «коэффициент надёжности по назначению». Not an open question, so left unchanged; an expert may want it aligned.
- The recorded KJ reply is the builder's generic fire-resistance reply over the AR corpus (unchanged); it proves routing and parsing, not КЖ quality. The profile still has no field case (`A-5`).

## Changed files

| File | Change |
| --- | --- |
| `src/auditmanager/analysis/text/profiles/kj/system_prompt.md` | the three edits above |
| `src/auditmanager/analysis/text/profiles/kj/profile.json` | `reviewed`, `1.1.0` |
| `fixtures/recorded/sections/kj/0f61471253016dc653d9df836d5a0449443eff32c8be2836a2f7b780459e4bea.json` | rebuilt by `build_fixtures.py`; renamed from `7208e6f7…4938` (the key is the digest of the request, which carries the prompt); `origin.profile_status` is now `reviewed`, `prompt_bundle_sha256` is the new one |
| `tests/unit/analysis/text_profiles/section_profile_expectations.json` | the `KJ` line only |
| `docs/program/tasks/SECTION-KJ-FULL-01.md`, `docs/program/SECTION-KJ-FULL-01.md` | this task and report |

The builder rewrites all fourteen recordings; the other thirteen came out byte for byte as before (`git status` showed only the KJ directory).

## Before and after of modified tests

No test file is modified. The one data line that the tests read changed from `{"code": "KJ", "status": "draft", "profile_version": "1.0.0"}` to `{"code": "KJ", "status": "reviewed", "profile_version": "1.1.0"}`. Before, the pin tests asserted that `profile.json`, the registry and the HTTP list agree with the line (`draft`, `1.0.0`); after, they assert the same agreement with `reviewed`, `1.1.0`. Nothing was weakened: every assertion still compares the package with the line.

## Commands and counts

From `.local/worktrees/section-kj-full-01`, `BS` as in the brief, one pytest at a time, `PYTHONDONTWRITEBYTECODE=1`. Status read from the output, not from a pipe.

| Command | Base | After |
| --- | --- | --- |
| `pytest tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages` | `211 passed` | `211 passed` |
| the same, after the prompt edit and before the rebuild | not run | `test_section_recordings.py`: `7 failed, 102 passed`; `--check`: rc 1 (new key differs, old file stale) |
| `build_fixtures.py --check` | `fixtures match` | `fixtures match` (rc 0) after the rebuild |
| `tests/integration/composition/test_analysis_profiles_over_http.py`, lane `.env` exported | `4 passed` | `4 passed` |
| `npx vitest run tests/unit/analysis-settings` (in `web/`, `node_modules` linked from `gate-night`) | not run | `7 files, 95 passed` |

Final runs on the committed tree (`tests/contract/program`, the two prose guards, `git diff --check`, the governance one-liner) are listed under «Final checks» below.

## Mutation proofs

Each mutation edits one file in the tree (committed at `43c957e0`), runs the guard, and is restored with `git checkout` (clean tree proved by `git status --short`, then a green run of the full battery). «Unit set» is `test_text_profile_registry.py` plus `tests/unit/analysis/text_profiles` (50 tests); «recordings» is `test_section_recordings.py` (109).

| # | Mutation | Guard | Result when mutated |
| --- | --- | --- | --- |
| M1 | `profile.json` status back to `draft`, nothing else | unit set | `3 failed, 47 passed` (registry tree test, expectations agreement, package shape) |
| M2 | `profile.json` version back to `1.0.0`, nothing else | unit set | `3 failed, 47 passed` |
| M3 | expectations line back to `draft` / `1.0.0`, nothing else | unit set | `3 failed, 47 passed` |
| M4 | expectations version `1.0.1`, nothing else | unit set | `3 failed, 47 passed` |
| M5 | prompt back to the base text, recording kept | recordings; builder `--check` | `7 failed, 102 passed`; `--check` rc 1 |
| M6 | only the register sentence removed | recordings | `7 failed, 102 passed` |
| M7 | only the anchorage sentence removed | recordings | `7 failed, 102 passed` |
| M8 | only the cover sentence removed | recordings | `7 failed, 102 passed` |
| M9 | recording back to the base file (new key removed) | recordings; builder `--check` | `7 failed, 102 passed`; `--check` rc 1 |
| M10 | expectations line to `draft` / `1.0.0`, nothing else | HTTP test (stack); web test | HTTP `1 failed, 3 passed`; web `1 failed, 94 passed` |
| M11 | `profile.json` status to `draft`, nothing else | HTTP test (stack); web test | HTTP `1 failed, 3 passed`; web `1 failed, 94 passed` |

All eleven went green again after the restore (`211 passed`, HTTP `4 passed`, web `95 passed`).

**Limit of the proofs.** No test pins the wording of the three N edits. The wording is held only through the recording key: any change to the prompt text turns M5 to M8 red until the recording is rebuilt. A later edit that is rebuilt consistently would pass; that is the same position as for every other section prompt. This lane may not add a test (allowed paths).

## Instruction for the integrator

- Merge in any order with the other section lanes: this lane touches one line of the expectations file and its own directories. If another lane's merge also rewrote `build_fixtures.py` output, rerun `build_fixtures.py --check` after the merge.
- After the merge: the four test files of the brief, `build_fixtures.py --check`, the HTTP test on the lane stack, and `npx vitest run tests/unit/analysis-settings`.
- `tests/e2e/pc01/journey/manifest.json` keeps a step on `tr[data-profile="draft"]`; the other thirteen sections stay `draft`, so it is not affected by this lane.
- `W59-SECTION-PROFILES-01.md` still lists the five questions as open (that file is outside this lane); the answers are in this report. If the register of decisions is updated, cite this file and say that no human reviewed them (`A-7`).
- Judge: read the table above against the legacy files named in P-04, not against this lane's summary.

## Limits

- No expert or owner reviewed any decision (`A-7`); no field case (`A-5`); the recording is synthetic.
- `origin.profile_status` of the recording moved to `reviewed` with the builder; nothing asserts it.
- The lane did not run the full gate, the whole `tests/integration` or the live journey (common rules).

## Forbidden paths untouched

`git diff --name-only 0e663fd0e608fcf5f79075ea71713c24ddf027e5..HEAD`, run on the tip of the branch:

```text
docs/program/SECTION-KJ-FULL-01.md
docs/program/tasks/SECTION-KJ-FULL-01.md
fixtures/recorded/sections/kj/0f61471253016dc653d9df836d5a0449443eff32c8be2836a2f7b780459e4bea.json
src/auditmanager/analysis/text/profiles/kj/profile.json
src/auditmanager/analysis/text/profiles/kj/system_prompt.md
tests/unit/analysis/text_profiles/section_profile_expectations.json
```

Every path is in the task's allowed list (git reports the old recording `fixtures/recorded/sections/kj/7208e6f7…4938.json` as renamed to the new one; with `--no-renames` it appears as a deletion in the same directory). Nothing under `contracts/**`, `db/**`, `infra/**`, `web/`, the registry, the builder, `W59-SECTION-PROFILES-01.md`, `P02_LOCK.json`, any other section or any test file changed. The legacy repository was only read (`git status --short` there: 0 lines before and after).

## Final checks

On the committed tree (clean, `git status --short` empty), last commit before this paragraph:

| Command | Result |
| --- | --- |
| `pytest tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` | `105 passed` |
| governance one-liner on `docs/program/tasks/SECTION-KJ-FULL-01.md` | `[]` |
| `git diff --check` | rc 0 |
| `pytest` (registry, text_profiles, section recordings, analysis_packages), `build_fixtures.py --check`, HTTP test, `vitest` analysis-settings | `211 passed`; `fixtures match`; `4 passed`; `95 passed` |
