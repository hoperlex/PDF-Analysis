# Task SECTION-KJ-FULL-01 — the КЖ (KJ) profile answers every open question of its record and leaves `draft`

task_id: SECTION-KJ-FULL-01
status: completed in development candidate

## Outcome

The record of the КЖ section in `docs/program/W59-SECTION-PROFILES-01.md` lists five open questions «for the expert reviewer» and four cross-section questions. Under `R-146ag` no expert reviews the section, so a lane answers each one with a written decision (K keep, N narrow, X exclude), applies the decisions to `system_prompt.md`, rebuilds the section's synthetic recording and moves the section to `reviewed`. `A-7`: the status `reviewed` on this profile carries **no human review**; it is not expert verification and must not be read as one. Product behaviour changes only inside the hint block of the KJ prompt (three narrowing edits); no finding category, schema, contract or migration changes (`R-146ah`).

## Depends on

- `PROD-14-0-EXPECTATIONS-01` — completed; it made the status and version pins data (`section_profile_expectations.json`).
- `W59-SECTION-PROFILES-01`, `SECTION-RECORDINGS-01` — completed; they created the package and its recording.
- `PRODUCTION-WAVE-PW2B` (lane template `SECTION-<CODE>-FULL-01`, `R-146ag`, `R-146ah`, `R-146ai`) — the brief.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.5.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable (the two v1 categories and the response schema are unchanged)
- migration head: `0032_ar_v3_run_group`, unchanged (`R-146ah`)
- base commit: `0e663fd0e608fcf5f79075ea71713c24ddf027e5` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No package, recording directory or expectations line is added or removed; one line of the expectations file changes value.

## Captured premise evidence

- premise: the package, its five legacy source files, the record's five open questions, the recording and the expectations line are as the brief and the plan describe; captured at the base commit before any edit

### P-01 — the package, its recording and its expectations line at the base

- captured_at: 2026-10-26
- command: `git rev-parse HEAD && sha256sum src/auditmanager/analysis/text/profiles/kj/profile.json src/auditmanager/analysis/text/profiles/kj/system_prompt.md fixtures/recorded/sections/kj/*.json && grep -n KJ tests/unit/analysis/text_profiles/section_profile_expectations.json`
- captured_output:
  ```text
  0e663fd0e608fcf5f79075ea71713c24ddf027e5
  97cbc285f43fce8263da194d3f53cf121d9020412d5a4edcd1ca84bf19f73d8b  src/auditmanager/analysis/text/profiles/kj/profile.json
  c89ce0d5ccbfbfd0ff272f1ddb62c159838257ec8071af556f53f08fa2d2ef3b  src/auditmanager/analysis/text/profiles/kj/system_prompt.md
  8538aa847cf82511546b965f68280212ca8bfede03afe16891d2f4bb0765e6cc  fixtures/recorded/sections/kj/7208e6f756ad1596b76ec1902e073a1068cbd586a8a2f60c0a0230525a864938.json
  9:    {"code": "KJ", "status": "draft", "profile_version": "1.0.0"},
  ```
- interpretation: the package has exactly `profile.json` and `system_prompt.md` (no `open_questions.md`, which only `PB` carries); the one recording is keyed `7208e6f7…4938`; the expectations line says `draft` at `1.0.0`, agreeing with `profile.json` (`KJ draft 1.0.0`, identities `ap_01M5AXG1K82P9BCJ1NRYSTC2NY` / `pb_01M5AXG1K8EDTH597XY32Z696Y`).

### P-02 — the five open questions of the KJ record

- captured_at: 2026-10-26
- command: `sed -n 446,452p docs/program/W59-SECTION-PROFILES-01.md`
- captured_output:
  ```text
  Open questions for the expert reviewer:

  - Обозначения класса арматуры в старой и новой системе (А-III и А400, А-I и А240) или класса и марки бетона (В25 и М350) для одной и той же позиции — противоречие или одно значение в разных обозначениях?
  - Формулировки «длину стержней уточнить по месту», «отверстия выполнять по заданию смежных разделов», «отметки уточнить по факту» — заполнитель (так по v1) или принятое указание производителю работ?
  - Реестр отклонений РД от ПД по своей природе приводит два значения одного признака (по ПД и по РД) — не даёт ли пункт о реестре ложных находок, и стоит ли его оставить?
  - Считать ли находкой расхождение строки «Итого» ведомости расхода стали или спецификации арматуры с суммой строк (сейчас пересчёт исключён)?
  - Полон ли перечень мест сверки для КЖ стадий П и Р (на стадии П листов армирования обычно нет), нужна ли сверка шифра комплекта в основных надписях листов, и не дают ли пункты о защитном слое и длинах анкеровки систематических ложных находок из-за разных условий (верхняя и нижняя арматура, сжатие и растяжение, класс бетона)?
  ```
- interpretation: five questions (lines 448 to 452 of the record, unedited at the base), the fifth compound: it asks three things (completeness of the places for stages П and Р; the set code in title blocks; false findings of the cover and anchorage bullets under different conditions). The lane answers the fifth as 5a, 5b and 5c so that each gets exactly one decision.

### P-03 — the legacy source on this host is the pinned one, clean, and hashes agree

- captured_at: 2026-10-26
- command: `git -C /root/projects/PDF-proverka rev-parse HEAD && git -C /root/projects/PDF-proverka status --short | wc -l && for f in role checklist drawing_types project_params finding_categories; do git -C /root/projects/PDF-proverka show 16ba8e5d23e4782550e79355002fde1365f682b7:prompts/disciplines/KJ/$f.md | sha256sum; done`
- captured_output:
  ```text
  16ba8e5d23e4782550e79355002fde1365f682b7
  0
  29004c6454798d53b5eb518b25990f39b223ce1b7b0b86c85aa723e85fe0f2af  -
  07ecdfce7696f16d004877117a58479edafca6f2fa8d81d530c6b20201b12801  -
  a50d6c11bcdd38e4678dbd380fda27869c27bfd718070600b15eed57b2761db8  -
  0a32c5a0eede3b3b69af0676a087220b30ad724a3dcfdee9b877e41fc7cdbafb  -
  9efdf059b322a51cbb5109e06190948cd30f6ea50e901c9d47d8a79ffbce48ee  -
  ```
- interpretation: the five hashes equal the five pins in `profile.json` (and in the record), in the order role, checklist, drawing_types, project_params, finding_categories. The legacy tree is at the pinned commit with no local change; the lane only read it.

### P-04 — what the legacy source does and does not contain (bounds on any wording)

- captured_at: 2026-10-26
- command: `cd /root/projects/PDF-proverka/prompts/disciplines/KJ && grep -c -E 'А400|А-I([^IV]|$)|М350|сжатой|сжатая' role.md checklist.md drawing_types.md project_params.md finding_categories.md`
- captured_output:
  ```text
  role.md:0
  checklist.md:0
  drawing_types.md:0
  project_params.md:0
  finding_categories.md:0
  ```
- interpretation: the old/new rebar designations «А400», «А-I» and the concrete mark «М350» that the first open question names occur nowhere in the source, so no equivalence between designations can be written into the prompt without adding a class designation the source does not hold (forbidden by the brief). The words «сжатой/сжатая» do not occur either (they come from the record's own question); the brief's ban is on norm numbers, references, thresholds and class designations, and a plain description of a zone is none of those, but it is listed as an assumption in the report. The same source does hold: «растянутой зоне» (checklist line 33), «наличия контакта с грунтом / наружными поверхностями» (line 42), the register «Реестр отклонений РД от ПД» as «Приложение с перечнем отклонений рабочей документации от проектной» (drawing_types line 4) and the «Шифр комплекта (например, 13АВ-РД-КЖx.y-Kn)» (project_params line 13).

### P-05 — what a status or prompt edit moves: the identity, the recording key, the tests that pin them

- captured_at: 2026-10-26
- command: `grep -rn "profile_status" fixtures/recorded/sections/build_fixtures.py fixtures/recorded/sections/kj tests | cut -c1-170 && PYTHONPATH=src:$BS .venv/bin/python fixtures/recorded/sections/build_fixtures.py --check; echo rc=$?`
- captured_output:
  ```text
  fixtures/recorded/sections/kj/7208e6f756ad1596b76ec1902e073a1068cbd586a8a2f60c0a0230525a864938.json:8:    "profile_status": "draft",
  fixtures/recorded/sections/build_fixtures.py:346:                "profile_status": registered.status,
  fixtures match
  rc=0
  ```
- interpretation: the recording's file name is the digest of the request body, which carries the section's prompt; `profile_version` enters the profile's `content_sha256` (`AnalysisProfile.content_sha256` in `profile.py`) and `status` enters neither. The builder writes `registered.status` into `origin.profile_status`, so the recording changes content with the status even where the key would not move; `--check` is green at the base. No test asserts `profile_status` (informational, as `PROD-14-0-EXPECTATIONS-01` records).

### P-06 — the test battery at the base (before any edit)

- captured_at: 2026-10-26
- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages`
- captured_output:
  ```text
  211 passed in 12.36s
  ```
- interpretation: green at the base. With the lane `.env` exported, `tests/integration/composition/test_analysis_profiles_over_http.py` also gave `4 passed` at the base.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

`W59-SECTION-PROFILES-01.md` is immutable here: its KJ open questions stay as written and are answered in `docs/program/SECTION-KJ-FULL-01.md`.

## Publication authority

- development_target: none
- origin_main_authority: none

The lane pushes nothing; the integrator merges and publishes (`AGENTS.md` section 6).

## Allowed paths

- `src/auditmanager/analysis/text/profiles/kj/**`
- `fixtures/recorded/sections/kj/**`
- `tests/unit/analysis/text_profiles/section_profile_expectations.json`
- `docs/program/tasks/SECTION-KJ-FULL-01.md`
- `docs/program/SECTION-KJ-FULL-01.md`

Only the `KJ` line of the expectations file is edited.

## Forbidden hotspots

Every other section's files, `docs/program/W59-SECTION-PROFILES-01.md`, the registry (`profile_registry.py`), `fixtures/recorded/sections/build_fixtures.py`, `docs/program/P02_LOCK.json`, `contracts/**`, migrations, the web, `infra/**`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs, root dependency/lock files, the composition root, global styles, `origin/main`, tags, and the legacy repository `/root/projects/PDF-proverka` (read only).

## Non-goals

- No expert review and no claim of one: `reviewed` here means a lane wrote a decision for each question (`R-146ag`, `A-7`).
- No widening of what a finding is, no third category, no norm reference, number, threshold or class designation beyond the section's hash-pinned legacy source.
- No change to the builder, the registry or any test file; no model call; no database or schema change (`R-146ah`).
- No decision for another section; the cross-section questions are decided once by the brief and applied here.

## Deliverables

- `src/auditmanager/analysis/text/profiles/kj/system_prompt.md`: three narrowing edits to the hint block.
- `src/auditmanager/analysis/text/profiles/kj/profile.json`: `status` `reviewed`, `profile_version` `1.1.0`.
- `fixtures/recorded/sections/kj/0f61471253016dc653d9df836d5a0449443eff32c8be2836a2f7b780459e4bea.json`: the rebuilt synthetic recording (the old `7208e6f7…4938` file is removed by the builder).
- The `KJ` line of `section_profile_expectations.json`: `reviewed`, `1.1.0`.
- `docs/program/SECTION-KJ-FULL-01.md`: the decisions table, the prompt diff in words, the assumptions an expert would still check, the mutation table, counts.

## Required tests

- `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages` — expected: 211 passed.
- The same with the lane `.env` exported, on `tests/integration/composition/test_analysis_profiles_over_http.py` — expected: 4 passed.
- `npx vitest run tests/unit/analysis-settings` in `web/` — expected: 7 files, 95 passed.
- `PYTHONPATH=src:$BS .venv/bin/python fixtures/recorded/sections/build_fixtures.py --check` — expected: `fixtures match`, exit 0.
- `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` on the committed tree, and `git diff --check`.
- The governance one-liner on this file — expected: `[]`.
- Mutations: status only, version only, the expectations line only (two ways), the prompt only, each narrowing sentence alone, the recording only; each red, restored, green (table in the report).

## Integration contract

The integrator can rely on: the KJ package declares `reviewed` at `1.1.0` and so does its line of the expectations file; the registry serves it with `analysis_profile_id` and `prompt_bundle_id` unchanged and a new `content_sha256` for the bundle (the prompt text changed); the recorded-mode run of a КЖ-classified version replays the rebuilt recording (key `0f614712…4bea`) and a stale or foreign key is still refused. The two v1 categories, the response schema, token limits and every other section are unchanged. The lane edits no test file and no shared fixture, so it merges without conflict with the other section lanes (one expectations line each). **Nobody reviewed this section** (`A-7`).

## Failure/idempotency/security cases

A status edit without the expectations line, or the reverse, a version edit without the line, a prompt edit without the rebuilt recording (and a rebuilt recording without the prompt) are each red; the builder `--check` is idempotent (`fixtures match` after the rebuild, the other thirteen recordings rewritten byte for byte). No secret, credential or network access is involved.

## Rollback / feature flag

Forward-revert of the commits restores `draft` at `1.0.0` and the old recording key; no data migration exists and profiles are files. No feature flag: the registry serves what the package declares.

## Handoff

- changed files: the five paths above
- commands/results: see `docs/program/SECTION-KJ-FULL-01.md`
- known limits: see the report (no expert review; the wording of the three narrowing edits is pinned only through the recording key; the recording reply is the builder's synthetic one, unchanged)
- integration notes: merge in any order with the other section lanes; run the section tests and `--check` after the merge
