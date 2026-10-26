# Task SECTION-VK-FULL-01 — the ВК (VK) profile answers every open question of its record and leaves `draft`

task_id: SECTION-VK-FULL-01
status: completed in development candidate

## Outcome

The record of the ВК section in `docs/program/W59-SECTION-PROFILES-01.md` lists five open questions «for the expert reviewer» and four cross-section questions. Under `R-146ag` no expert reviews the section, so a lane answers each one with a written decision (K keep, N narrow, X exclude), applies the decisions to `system_prompt.md`, rebuilds the section's synthetic recording and moves the section to `reviewed`. `A-7`: the status `reviewed` on this profile carries **no human review**; it is not expert verification and must not be read as one. Product behaviour changes only inside the VK prompt (one narrowing sentence in one hint bullet, and three plain-word replacements of notations that the pinned source does not contain); no finding category, schema, contract or migration changes (`R-146ah`).

## Depends on

- `PROD-14-0-EXPECTATIONS-01` — completed; it made the status and version pins data (`section_profile_expectations.json`).
- `W59-SECTION-PROFILES-01`, `SECTION-RECORDINGS-01` — completed; they created the package and its recording.
- `PRODUCTION-WAVE-PW2B` (lane template `SECTION-<CODE>-FULL-01`, `R-146ag`, `R-146ah`, `R-146ai`) — the brief.
- `SECTION-AI-FULL-01`, `SECTION-PS-FULL-01`, `SECTION-KJ-FULL-01`, `SECTION-TX-FULL-01`, `SECTION-GP-FULL-01` — completed on this base; their reports fix the decisions-table format and the audit of designations.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.5.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable (the two v1 categories and the response schema are unchanged)
- migration head: `0032_ar_v3_run_group`, unchanged (`R-146ah`)
- base commit: `bb18c3235e2a71cf722560f3616185cf2b096970` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No package, recording directory or expectations line is added or removed; one line of the expectations file changes value.

## Captured premise evidence

- premise: the package, its five legacy source files, the record's five open questions, the recording and the expectations line are as the brief describes; captured at the base commit before any edit

### P-01 — the package, its recording and its expectations line at the base

- captured_at: 2026-10-26
- command: `git rev-parse HEAD && sha256sum src/auditmanager/analysis/text/profiles/vk/profile.json src/auditmanager/analysis/text/profiles/vk/system_prompt.md fixtures/recorded/sections/vk/*.json && grep -n VK tests/unit/analysis/text_profiles/section_profile_expectations.json`
- captured_output:
  ```text
  bb18c3235e2a71cf722560f3616185cf2b096970
  89b7e92a4abb0a8440ee252e0c3ca51fe5ca3b2e53956dd1b538443785324102  src/auditmanager/analysis/text/profiles/vk/profile.json
  118d408091f9f0cc232f0f6d1194d88d791b304ff1906e08896ad08264c66239  src/auditmanager/analysis/text/profiles/vk/system_prompt.md
  44b7c422ee3e298454e1cea8196b251d4f930b2ab70ab6157afa7e69ec27143a  fixtures/recorded/sections/vk/de50151c9fb7a1a31f36e74829aaa4dce7729bed4507653413b340352990378a.json
  12:    {"code": "VK", "status": "draft", "profile_version": "1.0.0"},
  ```
- interpretation: the package has exactly `profile.json` and `system_prompt.md` (no `open_questions.md`, which only `PB` carries); the one recording is keyed `de50151c…378a`; the expectations line says `draft` at `1.0.0`, agreeing with `profile.json` (identities `ap_01M5AXG1KF7NGNYMEFN97BW9ZN` / `pb_01M5AXG1KFMA8QCKP6YM1K5M5W`). On this base AI, PS, KJ, TX and GP are already `reviewed` at `1.1.0`.

### P-02 — the five open questions of the VK record

- captured_at: 2026-10-26
- command: `sed -n 592,598p docs/program/W59-SECTION-PROFILES-01.md`
- captured_output:
  ```text
  Open questions for the expert reviewer:

  - Формулировки «напор в точке подключения уточнить по ТУ», «отметки выпусков уточнить по месту», «марку насосов уточнить при заказе» — заполнитель (так по v1) или ссылка на технические условия и принятое указание монтажной организации и поставщику?
  - Диаметры полимерных труб в спецификации обычно заданы наружным диаметром и толщиной стенки, а на схемах — условным проходом; достаточно ли примера в условии 2, или сверка диаметров даст систематические ложные находки?
  - Температура горячей воды законно различается в разных точках (на выходе из теплообменника, у водоразборных приборов, в циркуляционном трубопроводе); не даёт ли пункт о температуре ложных находок, если точка в тексте не названа?
  - Считать ли находкой расхождение общего расхода здания с суммой расходов по системам или потребителям в таблице расчётных расходов (сейчас пересчёт исключён)?
  - Полон ли перечень мест сверки для типового комплекта ВК стадий П и Р, и нужно ли отдельно учитывать внутренний противопожарный водопровод (В2), если он оформлен в том же томе ВК?
  ```
- interpretation: five questions; the fifth asks two things (the list of places; the fire water supply В2), so six decisions. The third names one hint bullet (the temperature of hot water) and states a false-positive source (the point of measurement is not named), so a narrowing is allowed there. The second asks whether the example already in condition 2 («условный проход (DN) и наружный диаметр трубы») is enough. The record's text is unedited at the base (`### VK` at line 553). Note: «В2», «ТУ» and «водоразборных» occur in the record only, not in the source (P-04).

### P-03 — the legacy source on this host is the pinned one, clean, and hashes agree

- captured_at: 2026-10-26
- command: `git -C /root/projects/PDF-proverka rev-parse HEAD && git -C /root/projects/PDF-proverka status --short | wc -l && for f in role checklist drawing_types project_params finding_categories; do git -C /root/projects/PDF-proverka show 16ba8e5d23e4782550e79355002fde1365f682b7:prompts/disciplines/VK/$f.md | sha256sum; done`
- captured_output:
  ```text
  16ba8e5d23e4782550e79355002fde1365f682b7
  0
  5140872cd9a8be7e6ca091fcc95a11e54c665b5a93ae5004f93e1377b5927781  -
  5bcccef4fbe706983b1f125dbdcded15d97ba697677eb8b07998da72147eabd1  -
  b6e1ed44f153d0e3e61f25c17da7aff5bd5bdd917356e48b6a0336302e802a20  -
  45c73d4b95b95da870598020fc4f747d8201adab0dde1d5d9e13cfb1b6905724  -
  84f8c7bb03f58c603ae42c8e9286872142922e5bbeef84a27e1f47b6feff5977  -
  ```
- interpretation: the five hashes equal the five pins in `profile.json` (and in the record), in the order role, checklist, drawing_types, project_params, finding_categories. The legacy tree is at the pinned commit with no local change; the lane only read it.

### P-04 — what the legacy source does and does not contain (bounds on any wording)

- captured_at: 2026-10-26
- command: the five VK files exported from the pinned commit into one directory outside the repository, then `cat *.md | grep -c -- '<token>'` for each token (case-sensitive, a line count over all five files)
- captured_output:
  ```text
  designations (Cyrillic and Latin look-alikes):  В1=0 К1=0 К2=0 Т3=0 Т4=0 В2=0 B1=0 K1=0 K2=0 T3=0 T4=0 B2=0 ; "Ст " (with a space)=0
  plain words the prompt or the record uses:      часов=0 секунд=0 подач=0 рабоч=0 водонагреват=0 водоразбор=0 ТУ=0 подпис=0
  plain words the source does contain:            ХВС=11 ГВС=18 канализац=17 стояк=13 ИТП=3 теплообменник=1 циркуляц=4 калибр=3 "класс точности"=1 повысительн=4
  ```
- interpretation: the source holds no pipe or riser designation at all: not «В1», «К1», «К2», «Т3», «Т4», not the compounds «Ст В1-1», «К1-1», «К1-2», not «В2». It names the systems in words only (ХВС, ГВС, бытовая и ливневая канализация; `project_params.md` fields `pipe_material_cold`, `pipe_material_hot`, `pipe_material_sewerage`). So the base prompt names designations that the source lacks (P-07), and any wording this lane adds must carry no number, norm reference, threshold or class designation. The words «часовой», «секундный», «подача», «водонагреватель», «водоразборных» are plain words that are not in the source (none is a number or designation); the lane adds only «водоразборных» (the record's own word).

### P-05 — what a status or prompt edit moves: the identity, the recording key, the tests that pin them

- captured_at: 2026-10-26
- command: `git grep -n "profile_status" HEAD -- fixtures/recorded/sections/build_fixtures.py fixtures/recorded/sections/vk && PYTHONPATH=src:$BS .venv/bin/python fixtures/recorded/sections/build_fixtures.py --check; echo rc=$?`
- captured_output:
  ```text
  HEAD:fixtures/recorded/sections/build_fixtures.py:346:                "profile_status": registered.status,
  HEAD:fixtures/recorded/sections/vk/de50151c9fb7a1a31f36e74829aaa4dce7729bed4507653413b340352990378a.json:8:    "profile_status": "draft",
  fixtures match
  rc=0
  ```
- interpretation: the recording's file name is the digest of the request body, which carries the section's prompt; `profile_version` enters the profile's `content_sha256` and `status` enters neither. The builder writes `registered.status` into `origin.profile_status`, so the recording changes content with the status even where the key would not move; `--check` is green at the base. The recording's wording («Not field evidence for the profile's review») is unchanged by this lane.

### P-06 — the test battery at the base (before any edit)

- captured_at: 2026-10-26
- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages`
- captured_output:
  ```text
  211 passed in 3.21s
  ```
- interpretation: green at the base. With the lane `.env` exported, `tests/integration/composition/test_analysis_profiles_over_http.py` gave `4 passed` at the base.

### P-07 — audit of numerals and designations of the base prompt against the pinned source

- captured_at: 2026-10-26
- command: `python3 -I audit.py <worktree> VK` (the script is printed in `docs/program/SECTION-VK-FULL-01.md`; run on the base prompt before the edit)
- captured_output:
  ```text
  prompt: VK digit-bearing tokens: ['В1,', 'В1-1,', 'К1,', 'К1-1', 'К1-2,', 'К2', 'Т3', 'Т3,', 'Т4', 'Т4,']
    'В1,'            in legacy source: False
    'В1-1,'          in legacy source: False
    'К1,'            in legacy source: False
    'К1-1'           in legacy source: False
    'К1-2,'          in legacy source: False
    'К2'             in legacy source: False
    'Т3'             in legacy source: False
    'Т3,'            in legacy source: False
    'Т4'             in legacy source: False
    'Т4,'            in legacy source: False
  capital designations: ['DN', 'TBD', 'XX', 'В1', 'В1-1', 'ВК', 'ГОСТ', 'ЖЕ', 'И', 'ИТП', 'К1', 'К1-1', 'К1-2', 'К2', 'НЕ', 'СП', 'Т3', 'Т4', 'ТОГО', 'ТОМ', 'ЦТП']
    'DN'             in legacy source: True
    'TBD'            in legacy source: False
    'XX'             in legacy source: False
    'В1'             in legacy source: False
    'В1-1'           in legacy source: False
    'ВК'             in legacy source: True
    'ГОСТ'           in legacy source: True
    'ЖЕ'             in legacy source: False
    'И'              in legacy source: True
    'ИТП'            in legacy source: True
    'К1'             in legacy source: False
    'К1-1'           in legacy source: False
    'К1-2'           in legacy source: False
    'К2'             in legacy source: False
    'НЕ'             in legacy source: False
    'СП'             in legacy source: True
    'Т3'             in legacy source: False
    'Т4'             in legacy source: False
    'ТОГО'           in legacy source: False
    'ТОМ'            in legacy source: False
    'ЦТП'            in legacy source: True
  ```
- interpretation: **three bullets of the base prompt name system and riser designations that none of the five files contains**: `Ст В1-1`, `Ст К1-2`, `выпуск К1-1` (the riser and outlet bullet), `В1, Т3, Т4, К1, К2` (the pipe material bullet) and `систем Т3 и Т4` (the hot-water bullet). They are notations of drawing convention, not norms or thresholds, but the rule of the brief is that a notation absent from the pinned source must not stay, so the lane replaces them by plain words from the source (ХВС, ГВС, канализации) and says so. `TBD`, `XX` are the v1 marker examples of the placeholder category; `ЖЕ`, `НЕ`, `ТОГО`, `ТОМ` are fragments of upper-case emphasis words (`ОДНОГО И ТОГО ЖЕ`, `НЕ`, `ТОМ`); none is a designation.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

`W59-SECTION-PROFILES-01.md` is immutable here: its VK open questions stay as written and are answered in `docs/program/SECTION-VK-FULL-01.md`.

## Publication authority

- development_target: none
- origin_main_authority: none

The lane pushes nothing; the integrator merges and publishes (`AGENTS.md` section 6).

## Allowed paths

- `src/auditmanager/analysis/text/profiles/vk/**`
- `fixtures/recorded/sections/vk/**`
- `tests/unit/analysis/text_profiles/section_profile_expectations.json`
- `docs/program/tasks/SECTION-VK-FULL-01.md`
- `docs/program/SECTION-VK-FULL-01.md`

Only the `VK` line of the expectations file is edited.

## Forbidden hotspots

Every other section's files, `docs/program/W59-SECTION-PROFILES-01.md`, the registry (`profile_registry.py`), `fixtures/recorded/sections/build_fixtures.py`, `docs/program/P02_LOCK.json`, `contracts/**`, migrations, the web, `infra/**`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs, root dependency/lock files, the composition root, global styles, `origin/main`, tags, and the legacy repository `/root/projects/PDF-proverka` (read only).

## Non-goals

- No expert review and no claim of one: `reviewed` here means a lane wrote a decision for each question (`R-146ag`, `A-7`).
- No widening of what a finding is, no third category, no norm reference, number, threshold or class designation beyond the section's hash-pinned legacy source.
- No change to the builder, the registry or any test file; no model call; no database or schema change (`R-146ah`).
- No decision for another section; the cross-section questions are decided once by the brief and applied here.
- The web label for `reviewed` and the schema docstring are not touched; they are the integrator's, once for all fourteen lanes.

## Deliverables

- `src/auditmanager/analysis/text/profiles/vk/system_prompt.md`: one narrowing sentence in the hot-water bullet and three plain-word replacements of notations absent from the source.
- `src/auditmanager/analysis/text/profiles/vk/profile.json`: `status` `reviewed`, `profile_version` `1.1.0`.
- `fixtures/recorded/sections/vk/7a2b54d03453228ba23a1146c18f46c84aaa08fcda193f65f2c3e55775640e54.json`: the rebuilt synthetic recording (the old `de50151c…378a` file is removed by the builder).
- The `VK` line of `section_profile_expectations.json`: `reviewed`, `1.1.0`.
- `docs/program/SECTION-VK-FULL-01.md`: the decisions table, the prompt diff in words, the assumptions an expert would still check, the mutation table, counts.

## Required tests

- `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages` — expected: 211 passed.
- The same with the lane `.env` exported, on `tests/integration/composition/test_analysis_profiles_over_http.py` — expected: 4 passed.
- `npx vitest run tests/unit/analysis-settings` in `web/` — expected: 7 files, 95 passed.
- `PYTHONPATH=src:$BS .venv/bin/python fixtures/recorded/sections/build_fixtures.py --check` — expected: `fixtures match`, exit 0.
- `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` on the committed tree, and `git diff --check`.
- The governance one-liner on this file — expected: `[]`.
- Mutations: status only, version only, the expectations line only (two ways), the prompt only, the temperature sentence alone, each designation replacement alone (with the audit script), the recording only, the recording's origin only; each red, restored, green (table in the report).

## Integration contract

The integrator can rely on: the VK package declares `reviewed` at `1.1.0` and so does its line of the expectations file; the registry serves it with `analysis_profile_id` and `prompt_bundle_id` unchanged and a new `content_sha256` for the bundle (the prompt text changed); the recorded-mode run of a ВК-classified version replays the rebuilt recording (key `7a2b54d0…0e54`) and a stale or foreign key is still refused. The two v1 categories, the response schema, token limits and every other section are unchanged. The lane edits no test file and no shared fixture, so it merges without conflict with the other section lanes (one expectations line each). **Nobody reviewed this section** (`A-7`).

## Failure/idempotency/security cases

A status edit without the expectations line, or the reverse, a version edit without the line, a prompt edit without the rebuilt recording (and a rebuilt recording without the prompt) are each red; the builder `--check` is idempotent (`fixtures match` after the rebuild, the other thirteen recordings rewritten byte for byte). No secret, credential or network access is involved.

## Rollback / feature flag

Forward-revert of the commits restores `draft` at `1.0.0` and the old recording key; no data migration exists and profiles are files. No feature flag: the registry serves what the package declares.

## Handoff

- changed files: the five paths above
- commands/results: see `docs/program/SECTION-VK-FULL-01.md`
- known limits: see the report (no expert review; the wording of the prompt edits is pinned only through the recording key; the recording reply is the builder's synthetic one, unchanged; the notations `ХВС`, `ГВС`, «канализации» replace designations the source lacks, and the plain words «часовой», «секундный», «водонагреватель» stay although the source lacks them)
- integration notes: merge in any order with the other section lanes; run the section tests and `--check` after the merge
