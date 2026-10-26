# Task SECTION-POS-FULL-01 — the ПОС (POS) profile answers every open question of its record and leaves `draft`

task_id: SECTION-POS-FULL-01
status: completed in development candidate

## Outcome

The record of the ПОС section in `docs/program/W59-SECTION-PROFILES-01.md` lists four open questions «for the expert reviewer» and the record's four cross-section questions. Under `R-146ag` no expert reviews the section, so a lane answers each one with a written decision (K keep, N narrow, X exclude), applies the decisions to `system_prompt.md`, rebuilds the section's synthetic recording and moves the section to `reviewed`. `A-7`: the status `reviewed` on this profile carries **no human review**; it is not expert verification and must not be read as one. Product behaviour changes only inside the POS prompt (three narrowing edits: two hint bullets and one near-miss pair of condition 2); no finding category, schema, contract or migration changes (`R-146ah`).

## Depends on

- `PROD-14-0-EXPECTATIONS-01` — completed; it made the status and version pins data (`section_profile_expectations.json`).
- `W59-SECTION-PROFILES-01`, `SECTION-RECORDINGS-01` — completed; they created the package and its recording.
- `PRODUCTION-WAVE-PW2B` (lane template `SECTION-<CODE>-FULL-01`, `R-146ag`, `R-146ah`, `R-146ai`) — the brief.
- `SECTION-AI-FULL-01`, `SECTION-PS-FULL-01`, `SECTION-KJ-FULL-01` — completed on this base; their reports fix the decisions-table format and the audit.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.5.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable (the two v1 categories and the response schema are unchanged)
- migration head: `0032_ar_v3_run_group`, unchanged (`R-146ah`)
- base commit: `3c80af0e62c71f04d1e5b1178e0afbe7db6f7d6c` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No package, recording directory or expectations line is added or removed; one line of the expectations file changes value.

## Captured premise evidence

- premise: the package, its five legacy source files, the record's four open questions, the recording and the expectations line are as the brief and the plan describe; captured at the base commit before any edit

### P-01 — the package, its recording and its expectations line at the base

- captured_at: 2026-10-26
- command: `git rev-parse HEAD && sha256sum src/auditmanager/analysis/text/profiles/pos/profile.json src/auditmanager/analysis/text/profiles/pos/system_prompt.md fixtures/recorded/sections/pos/*.json && grep -n POS tests/unit/analysis/text_profiles/section_profile_expectations.json`
- captured_output:
  ```text
  3c80af0e62c71f04d1e5b1178e0afbe7db6f7d6c
  c0ddd796d8fd74138bac21a822ee62a6cb72faaed0424cb4f001a5cd766aa530  src/auditmanager/analysis/text/profiles/pos/profile.json
  f2e80a457a6c49978200571b20303f4eb76d5deb53f00ced3c612cdf80581cf0  src/auditmanager/analysis/text/profiles/pos/system_prompt.md
  9b18c354df244192d3f970d50fa7be6ff2e785ff8299f4e51ea00de2e6601ef4  fixtures/recorded/sections/pos/9fd7995188bd781df195e8aa285573d4f5dae8165d95e07c665dc11b93d2ea15.json
  7:    {"code": "POS", "status": "draft", "profile_version": "1.0.0"},
  ```
- interpretation: the package has exactly `profile.json` and `system_prompt.md` (no `open_questions.md`, which only `PB` carries); the one recording is keyed `9fd79951…ea15`; the expectations line says `draft` at `1.0.0`, agreeing with `profile.json` (`POS draft 1.0.0`, identities `ap_01M5AXG1K4V1JCGK60TZRM9B96` / `pb_01M5AXG1K4QP84XW1DNYM72HN6`). On this base AI, PS and KJ are already `reviewed` at `1.1.0`; the other eleven are `draft`.

### P-02 — the four open questions of the POS record

- captured_at: 2026-10-26
- command: `sed -n 339,344p docs/program/W59-SECTION-PROFILES-01.md`
- captured_output:
  ```text
  Open questions for the expert reviewer:

  - Формулировки «марка крана уточняется в ППР», «решения уточняются при разработке ППР», «по выбору подрядной организации» — заполнитель (корень «уточн») или принятое в ПОС решение отложить выбор до проекта производства работ?
  - Сумма продолжительностей этапов в календарном плане законно больше общей продолжительности из-за совмещения работ, а «Итого» распределения объёмов или капитальных вложений по периодам может не давать 100 %: считать ли находкой расхождение итоговой строки с суммой (сейчас пересчёт исключён)?
  - Текстовый слой календарного плана и графиков потребности в кадрах и механизмах (диаграммы Ганта, гистограммы) обычно разорван: надёжна ли сверка продолжительностей и численности с ними, или этот пункт даст систематические ложные находки?
  - Максимальная численность работающих и численность в наиболее многочисленную смену, принятая в расчёте временных зданий (часто долей от максимума), — хватает ли условия 2 и пояснения в перечне мест, чтобы эти значения не сравнивались как одно?
  ```
- interpretation: four questions (lines 341 to 344 of the record, unedited at the base: `git diff 3c80af0e -- docs/program/W59-SECTION-PROFILES-01.md` is empty), none compound. The four cross-section questions are at lines 169 to 190 of the same file (site and contractor phrases; «Итого» against the sum of rows; text read from sheets; missing items) and are decided once by the brief.

### P-03 — the legacy source on this host is the pinned one, clean, and hashes agree

- captured_at: 2026-10-26
- command: `git -C /root/projects/PDF-proverka rev-parse HEAD && git -C /root/projects/PDF-proverka status --short | wc -l && for f in role checklist drawing_types project_params finding_categories; do git -C /root/projects/PDF-proverka show 16ba8e5d23e4782550e79355002fde1365f682b7:prompts/disciplines/POS/$f.md | sha256sum; done`
- captured_output:
  ```text
  16ba8e5d23e4782550e79355002fde1365f682b7
  0
  19e2951c15fe0cb0ae328eb8fdcb60861265df8a2749296b49c811116b89e8cb  -
  a4c5bba5d83e46841e1182f714adb4b459ce646f49b511b3f05ebac215d6a722  -
  cf608107fe49ba9fb0de02cd8522381e638e66563ce07f0b33fefd11bcb1ebb5  -
  42f8346450816b49b00082f91a3b798e4714fe2264e0be6a1ecc499537939032  -
  6c10f378c333711e58a00cabd2853ff1e4097723cb4550a079a4b8ddc920c816  -
  ```
- interpretation: the five hashes equal the five pins in `profile.json` (and in the record), in the order role, checklist, drawing_types, project_params, finding_categories. The legacy tree is at the pinned commit with no local change; the lane only read it (a copy of the five blobs went to the lane's scratch directory, outside the repository).

### P-04 — what the legacy source does and does not contain (bounds on any wording)

- captured_at: 2026-10-26
- command: `cd <scratch>/pos-src && for w in 'ППР' 'уточн' 'подрядн' 'смен' 'ИТР' 'гистограмм' 'Ганта' 'диаграмм' 'шкал' 'крюк'; do printf '%-12s' "$w"; grep -c -- "$w" role.md checklist.md drawing_types.md project_params.md finding_categories.md | tr '\n' ' '; echo; done` (the five files are `git show 16ba8e5d…:prompts/disciplines/POS/<name>.md`, checked byte-identical with `cmp`)
- captured_output:
  ```text
  ППР      project_params.md:0 finding_categories.md:0 drawing_types.md:0 role.md:0 checklist.md:0
  уточн  role.md:0 project_params.md:0 finding_categories.md:0 drawing_types.md:0 checklist.md:0
  подряднdrawing_types.md:0 project_params.md:0 finding_categories.md:0 role.md:0 checklist.md:0
  смен    drawing_types.md:0 finding_categories.md:0 role.md:0 project_params.md:0 checklist.md:0
  ИТР      project_params.md:0 role.md:0 finding_categories.md:0 checklist.md:0 drawing_types.md:0
  гистограммdrawing_types.md:0 checklist.md:0 finding_categories.md:0 project_params.md:0 role.md:0
  Ганта  drawing_types.md:1 role.md:0 project_params.md:0 checklist.md:0 finding_categories.md:0
  диаграммdrawing_types.md:0 finding_categories.md:0 role.md:0 project_params.md:0 checklist.md:0
  шкал    drawing_types.md:0 project_params.md:0 role.md:0 finding_categories.md:0 checklist.md:0
  крюк    drawing_types.md:0 role.md:0 project_params.md:0 checklist.md:0 finding_categories.md:0
  ```
- interpretation: the source holds neither «ППР», «уточн», «подрядн» (the first question's phrases cannot be restated from it), nor «смен», «ИТР», «гистограмм», «шкал», «крюк». It holds «Диаграмма Ганта» once (`drawing_types.md` line 4, capital Д, hence 0 for the lower-case «диаграмм»). The base prompt has no digit-bearing token at all (P-05), so no wording of the three edits needs a number, norm reference, threshold or class designation, and none is added. «ИТР», «в наиболее многочисленную смену» and «высота подъёма крюка» are in the base prompt and not in the source: they are not changed and are listed in the report.

### P-05 — numerals and designations of the base prompt against the source; what a status or prompt edit moves

- captured_at: 2026-10-26
- command: `python3 -I audit.py . POS` (the script of `docs/program/SECTION-AI-FULL-01.md`, section «Audit of numerals and designations», unchanged) and `grep -rn "profile_status" fixtures/recorded/sections/build_fixtures.py fixtures/recorded/sections/pos | cut -c1-150` and `build_fixtures.py --check; echo rc=$?`
- captured_output:
  ```text
  prompt: POS digit-bearing tokens: []
  capital designations: ['TBD', 'XX', 'ГОСТ', 'ЖЕ', 'И', 'ИТР', 'НЕ', 'ПОС', 'СП', 'ТОГО', 'ТОМ']
    in legacy source: TBD False, XX False, ГОСТ False, ЖЕ False, И True, ИТР False, НЕ False, ПОС True, СП True, ТОГО False, ТОМ False
  fixtures/recorded/sections/build_fixtures.py:346:                "profile_status": registered.status,
  fixtures/recorded/sections/pos/9fd7995188bd781df195e8aa285573d4f5dae8165d95e07c665dc11b93d2ea15.json:8:    "profile_status": "draft",
  fixtures match
  rc=0
  ```
- interpretation: the POS prompt carries no numeral, so the trap met by the AI lane (a class designation in a condition that the source lacks) does not occur here; the capital tokens are v1's own words and upper-case emphasis (`TBD`, `XX`, `ГОСТ`, `ЖЕ`, `НЕ`, `ТОГО`, `ТОМ`), the section's own name and the conjunction `И` in upper-case emphasis, plus `ИТР`, a staff-category abbreviation from the earlier drafting that is not in the source and is not a class designation (kept, listed in the report). The recording's file name is the digest of the request body, which carries the section's prompt; `profile_version` enters the profile's `content_sha256` and `status` enters neither; the builder writes `registered.status` into `origin.profile_status`, so the recording changes content with the status even where the key would not move.

### P-06 — the test battery at the base (before any edit)

- captured_at: 2026-10-26
- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages`
- captured_output:
  ```text
  211 passed in 3.68s
  ```
- interpretation: green at the base. With the lane `.env` exported, `tests/integration/composition/test_analysis_profiles_over_http.py` gave `4 passed` at the base (the three package files restored from the base for the run, then put back).

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

`W59-SECTION-PROFILES-01.md` is immutable here: its POS open questions stay as written and are answered in `docs/program/SECTION-POS-FULL-01.md`.

## Publication authority

- development_target: none
- origin_main_authority: none

The lane pushes nothing; the integrator merges and publishes (`AGENTS.md` section 6).

## Allowed paths

- `src/auditmanager/analysis/text/profiles/pos/**`
- `fixtures/recorded/sections/pos/**`
- `tests/unit/analysis/text_profiles/section_profile_expectations.json`
- `docs/program/tasks/SECTION-POS-FULL-01.md`
- `docs/program/SECTION-POS-FULL-01.md`

Only the `POS` line of the expectations file is edited.

## Forbidden hotspots

Every other section's files, `docs/program/W59-SECTION-PROFILES-01.md`, the registry (`profile_registry.py`), `fixtures/recorded/sections/build_fixtures.py`, `docs/program/P02_LOCK.json`, `contracts/**`, migrations, the web, `infra/**`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs, root dependency/lock files, the composition root, global styles, `origin/main`, tags, and the legacy repository `/root/projects/PDF-proverka` (read only).

## Non-goals

- No expert review and no claim of one: `reviewed` here means a lane wrote a decision for each question (`R-146ag`, `A-7`).
- No widening of what a finding is, no third category, no norm reference, number, threshold or class designation beyond the section's hash-pinned legacy source.
- No change to the builder, the registry or any test file; no model call; no database or schema change (`R-146ah`).
- No decision for another section; the cross-section questions are decided once by the brief and applied here.

## Deliverables

- `src/auditmanager/analysis/text/profiles/pos/system_prompt.md`: three narrowing edits (the durations bullet, the headcount bullet, the near-miss list of condition 2).
- `src/auditmanager/analysis/text/profiles/pos/profile.json`: `status` `reviewed`, `profile_version` `1.1.0`.
- `fixtures/recorded/sections/pos/e399ef16a725e478d9e15734776b81de7de726140bafbc6bea8b4126223785f1.json`: the rebuilt synthetic recording (the old `9fd79951…ea15` file is removed by the builder).
- The `POS` line of `section_profile_expectations.json`: `reviewed`, `1.1.0`.
- `docs/program/SECTION-POS-FULL-01.md`: the decisions table, the prompt diff in words, the assumptions an expert would still check, the mutation table, counts.

## Required tests

- `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages` — expected: 211 passed.
- The same with the lane `.env` exported, on `tests/integration/composition/test_analysis_profiles_over_http.py` — expected: 4 passed.
- `npx vitest run tests/unit/analysis-settings` in `web/` — expected: 7 files, 95 passed.
- `PYTHONPATH=src:$BS .venv/bin/python fixtures/recorded/sections/build_fixtures.py --check` — expected: `fixtures match`, exit 0.
- `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` on the committed tree, and `git diff --check`.
- The governance one-liner on this file — expected: `[]`.
- Mutations: status only, version only, the expectations line only (two ways), the prompt only, each of the three narrowing edits alone, the recording only (two ways), the numerals audit on a prompt with a number and a designation; each red, restored, green (table in the report).

## Integration contract

The integrator can rely on: the POS package declares `reviewed` at `1.1.0` and so does its line of the expectations file; the registry serves it with `analysis_profile_id` and `prompt_bundle_id` unchanged and a new `content_sha256` for the bundle (the prompt text changed); the recorded-mode run of a ПОС-classified version replays the rebuilt recording (key `e399ef16…85f1`) and a stale or foreign key is still refused. The two v1 categories, the response schema, token limits and every other section are unchanged. The lane edits no test file and no shared fixture, so it merges without conflict with the other section lanes (one expectations line each). **Nobody reviewed this section** (`A-7`).

## Failure/idempotency/security cases

A status edit without the expectations line, or the reverse, a version edit without the line, a prompt edit without the rebuilt recording (and a rebuilt recording without the prompt) are each red; the builder `--check` is idempotent (`fixtures match` after the rebuild, the other thirteen recordings rewritten byte for byte). No secret, credential or network access is involved.

## Rollback / feature flag

Forward-revert of the commits restores `draft` at `1.0.0` and the old recording key; no data migration exists and profiles are files. No feature flag: the registry serves what the package declares.

## Handoff

- changed files: the five paths above
- commands/results: see `docs/program/SECTION-POS-FULL-01.md`
- known limits: see the report (no expert review; the wording of the three narrowing edits is pinned only through the recording key; the recording reply is the builder's synthetic one, unchanged)
- integration notes: merge in any order with the other section lanes; run the section tests and `--check` after the merge
