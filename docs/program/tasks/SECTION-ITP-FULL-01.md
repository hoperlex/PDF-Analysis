# Task SECTION-ITP-FULL-01 — the ИТП (ITP) profile answers every open question of its record and leaves `draft`

task_id: SECTION-ITP-FULL-01
status: completed in development candidate

## Outcome

The record of the ИТП section in `docs/program/W59-SECTION-PROFILES-01.md` lists five open questions «for the expert reviewer» and four cross-section questions. Under `R-146ag` no expert reviews the section, so a lane answers each one with a written decision (K keep, N narrow, X exclude), applies the decisions to `system_prompt.md`, rebuilds the section's synthetic recording and moves the section to `reviewed`. `A-7`: the status `reviewed` on this profile carries **no human review**; it is not expert verification and must not be read as one. Product behaviour changes only inside the ITP prompt (one narrowing sentence in one hint bullet, and one symbol removed from an example in condition 2); no finding category, schema, contract or migration changes (`R-146ah`).

## Depends on

- `PROD-14-0-EXPECTATIONS-01` — completed; it made the status and version pins data (`section_profile_expectations.json`).
- `W59-SECTION-PROFILES-01`, `SECTION-RECORDINGS-01` — completed; they created the package and its recording.
- `PRODUCTION-WAVE-PW2B` (lane template `SECTION-<CODE>-FULL-01`, `R-146ag`, `R-146ah`, `R-146ai`) — the brief.
- `SECTION-AI-FULL-01`, `SECTION-PS-FULL-01`, `SECTION-POS-FULL-01`, `SECTION-TX-FULL-01`, `SECTION-KJ-FULL-01`, `SECTION-KM-FULL-01`, `SECTION-OV-FULL-01`, `SECTION-VK-FULL-01`, `SECTION-GP-FULL-01` — completed on this base; their reports fix the decisions-table format and the audit of designations.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.5.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable (the two v1 categories and the response schema are unchanged)
- migration head: `0032_ar_v3_run_group`, unchanged (`R-146ah`)
- base commit: `23e30b4c17a3c930469f3f94733c6d8c16eff1ed` (`integration/ar-close-1026`)

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
- command: `git rev-parse HEAD && sha256sum src/auditmanager/analysis/text/profiles/itp/profile.json src/auditmanager/analysis/text/profiles/itp/system_prompt.md fixtures/recorded/sections/itp/*.json && grep -n ITP tests/unit/analysis/text_profiles/section_profile_expectations.json`
- captured_output:
  ```text
  23e30b4c17a3c930469f3f94733c6d8c16eff1ed
  fb6c227148956f335451cab91724e3be5add034b87d4145e71d66d8a863e0a11  src/auditmanager/analysis/text/profiles/itp/profile.json
  fc09f8b000bda0bb174f028e897bfd0b18be43933fae22db7730094b07ce29e6  src/auditmanager/analysis/text/profiles/itp/system_prompt.md
  6c9230f6a70b4e6f0c05432c25592805ee8bf18fd72050fad441350dd100fa50  fixtures/recorded/sections/itp/cc1fab2363e9a6700d8ca840c4362e85a226b1c86bd8c3e58d9a2cf34e08f57d.json
  16:    {"code": "ITP", "status": "draft", "profile_version": "1.0.0"},
  ```
- interpretation: the package has exactly `profile.json` and `system_prompt.md` (no `open_questions.md`, which only `PB` carries); the one recording is keyed `cc1fab23…f57d`; the expectations line says `draft` at `1.0.0`, agreeing with `profile.json` (identities `ap_01M5AXG1KQSW41PC130SWCS8CD` / `pb_01M5AXG1KQR5A6ZPWDX4CC3CTS`). On this base AI, PS, POS, TX, KJ, KM, OV, VK and GP are already `reviewed` at `1.1.0`; PT, EOM, SS, ITP and PB are `draft`.

### P-02 — the five open questions of the ITP record

- captured_at: 2026-10-26
- command: `sed -n 804,810p docs/program/W59-SECTION-PROFILES-01.md`
- captured_output:
  ```text
  Open questions for the expert reviewer:

  - Тепловые нагрузки в одних местах записаны в Гкал/ч, в других — в кВт или МВт: считать ли значения, совпадающие после перевода единиц, согласованными, и не даст ли округление при переводе ложных находок?
  - Температурный график, записанный в одном месте как «150/70 со срезкой на 130 °C», а в другом как «130/70», — противоречие или один и тот же график в разной записи?
  - Параметры насоса или теплообменника в спецификации (выбранное изделие) и в опросном листе или таблице расчёта (требуемые значения) сейчас считаются разными признаками (условие 2); нужна ли когда-нибудь находка о таком расхождении?
  - Формулировки «подбор оборудования уточнить после получения ТУ», «марку теплосчётчика согласовать с теплоснабжающей организацией», «уставки уточнить при пусконаладке» — заполнитель (так по v1) или принятое указание?
  - Строка «Итого» тепловых нагрузок против суммы нагрузок по контурам — сейчас пересчёт исключён; нужна ли такая находка?
  ```
- interpretation: five questions, one decision each (the record has no question about the completeness of the list of places, unlike OV and VK). The first names one hint bullet (the heat loads) and states a false-positive source (rounding at a unit conversion), so a narrowing is allowed there. The second asks whether two notations of a temperature graph are one graph, which is a domain equivalence. The third asks for a new kind of finding. The fourth is cross-section question 1 and names three phrases, only two of which carry the literal «уточнить». The fifth is cross-section question 2. The record's text is unedited at the base (`### ITP` at line 754). Note: «Гкал/ч», «МВт», «срезкой», «опросном листе», «ТУ» occur in the record, not in the source (P-04).

### P-03 — the legacy source on this host is the pinned one, clean, and hashes agree

- captured_at: 2026-10-26
- command: `git -C /root/projects/PDF-proverka rev-parse HEAD && git -C /root/projects/PDF-proverka status --short | wc -l && for f in role checklist drawing_types project_params finding_categories; do git -C /root/projects/PDF-proverka show 16ba8e5d23e4782550e79355002fde1365f682b7:prompts/disciplines/ITP/$f.md | sha256sum; done`
- captured_output:
  ```text
  16ba8e5d23e4782550e79355002fde1365f682b7
  0
  18cb5f3e4f321b3f9eb526e0702d3f7bc49e972c4555bd0ab02b0f86d1bc2ca1  -
  22aa3697b2557feb65e2e25f1478e81ec2d48ba815818f62eef40a8059f0dbb1  -
  5ba8823dd2d2a8291dd9c17dc4a9d9a480af8dc3ade9b8a48efa652d0858b1ee  -
  0fbb238e3fe676e744610e4af63caed85014e30a4b3eb9b0652bc1f4fba19796  -
  113fe584e10e12b5c28ec4bb4342b58bd8277e1724cbfb8a712ac53fbdbe7e13  -
  ```
- interpretation: the five hashes equal the five pins in `profile.json` (and in the record), in the order role, checklist, drawing_types, project_params, finding_categories. The legacy tree is at the pinned commit with no local change; the lane only read it.

### P-04 — what the legacy source does and does not contain (bounds on any wording)

- captured_at: 2026-10-26
- command: the five ITP files exported from the pinned commit into one directory outside the repository, then `cat *.md | grep -c -- '<token>'` for each token (case-sensitive, a line count over all five files)
- captured_output:
  ```text
  units and symbols:                 кВт=4 Гкал=0 МВт=0 Kvs=4 "Kv " (Kv not followed by s)=0 "130/70"=2 "150/70"=0 "срезк"=0
  words of the record and the prompt: опросн=0 уставк=0 согласов=0 уточн=0 ТУ=0 "Технические условия"=1 теплоснабжающ=2 Итого=0 "итог"=0 Суммарн=1
  words of the prompt's examples:     среднечас=0 максималь=0 пропускн=0 подогрев=0 СНиП=0 таблиц=0
  words of the lane's new sentence:   единиц=0 округл=0 пересчёт=0 пересчет=0
  words the source does contain:      "Правилам коммерческого учёта"=1 "тепловой энергии"=2 PN=1 "двух-/трёхходовой"=1
  the only lines holding "Kv":        role.md:12 "Kvs"; checklist.md:31 "Kvs клапана…"; checklist.md:86 "…Kvs"; finding_categories.md:5 "Kvs"
  ```
- interpretation: the source holds no digit-bearing designation that the prompt uses; its only notation of the valve capacity is `Kvs`. `Kv` (the base prompt's condition 2 writes «расчётная пропускная способность Kv») occurs in the source only as the first two letters of `Kvs`. The source never says «Итого» and names no unit of heat load other than kW (`heat_load_*_kW`), and it holds no conversion factor between units, so any wording this lane adds must carry no unit name, conversion factor, number, norm or designation of its own. The plain words listed under «words of the prompt's examples» are in the base prompt although the source lacks them (disclosed in the report, not removed).

### P-05 — what a status or prompt edit moves: the identity, the recording key, the tests that pin them

- captured_at: 2026-10-26
- command: `git grep -n "profile_status" 23e30b4c -- fixtures/recorded/sections/build_fixtures.py fixtures/recorded/sections/itp && PYTHONPATH=src:$BS .venv/bin/python fixtures/recorded/sections/build_fixtures.py --check; echo rc=$?`
- captured_output:
  ```text
  23e30b4c:fixtures/recorded/sections/build_fixtures.py:346:                "profile_status": registered.status,
  23e30b4c:fixtures/recorded/sections/itp/cc1fab2363e9a6700d8ca840c4362e85a226b1c86bd8c3e58d9a2cf34e08f57d.json:8:    "profile_status": "draft",
  fixtures match
  rc=0
  ```
- interpretation: the recording's file name is the digest of the request body, which carries the section's prompt; `profile_version` enters the profile's `content_sha256` and `status` enters neither. The builder writes `registered.status` into `origin.profile_status`, so the recording changes content with the status even where the key would not move; `--check` is green at the base. The recording's wording («Not field evidence for the profile's review») is unchanged by this lane.

### P-06 — the test battery at the base (before any edit)

- captured_at: 2026-10-26
- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages`
- captured_output:
  ```text
  211 passed in 4.33s
  ```
- interpretation: green at the base. With the lane `.env` exported, `tests/integration/composition/test_analysis_profiles_over_http.py` gave `4 passed` at the base, and `npx vitest run tests/unit/analysis-settings` in `web/` gave `7 files, 95 passed`.

### P-07 — audit of numerals and designations of the base prompt against the pinned source

- captured_at: 2026-10-26
- command: `python3 -I audit.py <worktree> ITP` (the script is printed in `docs/program/SECTION-ITP-FULL-01.md`; run on the base prompt before the edit)
- captured_output:
  ```text
  prompt: ITP digit-bearing tokens: []
  capital designations: ['PN', 'TBD', 'XX', 'ГВС', 'ГОСТ', 'ЖЕ', 'И', 'ИТП', 'НЕ', 'СП', 'ТОГО', 'ТОМ']
    'PN'             in legacy source: True
    'TBD'            in legacy source: False
    'XX'             in legacy source: False
    'ГВС'            in legacy source: True
    'ГОСТ'           in legacy source: True
    'ЖЕ'             in legacy source: False
    'И'              in legacy source: True
    'ИТП'            in legacy source: True
    'НЕ'             in legacy source: False
    'СП'             in legacy source: True
    'ТОГО'           in legacy source: False
    'ТОМ'            in legacy source: False
  ```
- interpretation: unlike `VK` and `OV`, the base ITP prompt has no digit-bearing token and no class designation or system mark that the source lacks. `TBD` and `XX` are the v1 marker examples of the placeholder category; `ЖЕ`, `НЕ`, `ТОГО`, `ТОМ` are fragments of upper-case emphasis words. The script matches capital-letter tokens only, so it cannot see a mixed-case symbol; a second, whole-word pass over the Latin words (P-08) is the only place where the base prompt's `Kv` shows.

### P-08 — whole Latin words of the base prompt against the source

- captured_at: 2026-10-26
- command: `python3 -I latin_audit.py <base prompt> src/auditmanager/analysis/text/profiles/itp/profile.json` (the script reads the five files at the pinned commit; its exact text is in `docs/program/SECTION-ITP-FULL-01.md`; output filtered to the words that are not v1's output-contract field names or markers)
- captured_output:
  ```text
  'Kvs'              whole word in legacy source: True
  'PN'               whole word in legacy source: True
  'Kv'               whole word in legacy source: False
  ```
- interpretation: one symbol of the base prompt is absent from the source as a word: `Kv`, in the condition 2 example «условная пропускная способность клапана Kvs и расчётная пропускная способность Kv». It is not a digit, a norm reference or a class designation, so the brief's rule does not oblige a removal; the lane removes the symbol anyway and keeps the words (decision A-1 in the report). The v1 words `СНиП` (exclusion list) and the plain words of P-04 stay and are disclosed.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

`W59-SECTION-PROFILES-01.md` is immutable here: its ITP open questions stay as written and are answered in `docs/program/SECTION-ITP-FULL-01.md`.

## Publication authority

- development_target: none
- origin_main_authority: none

The lane pushes nothing; the integrator merges and publishes (`AGENTS.md` section 6).

## Allowed paths

- `src/auditmanager/analysis/text/profiles/itp/**`
- `fixtures/recorded/sections/itp/**`
- `tests/unit/analysis/text_profiles/section_profile_expectations.json`
- `docs/program/tasks/SECTION-ITP-FULL-01.md`
- `docs/program/SECTION-ITP-FULL-01.md`

Only the `ITP` line of the expectations file is edited.

## Forbidden hotspots

Every other section's files, `docs/program/W59-SECTION-PROFILES-01.md`, the registry (`profile_registry.py`), `fixtures/recorded/sections/build_fixtures.py`, `docs/program/P02_LOCK.json`, `contracts/**`, migrations, the web, `infra/**`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs, root dependency/lock files, the composition root, global styles, `origin/main`, tags, and the legacy repository `/root/projects/PDF-proverka` (read only).

## Non-goals

- No expert review and no claim of one: `reviewed` here means a lane wrote a decision for each question (`R-146ag`, `A-7`).
- No widening of what a finding is, no third category, no norm reference, number, threshold, unit conversion factor or class designation beyond the section's hash-pinned legacy source.
- No change to the builder, the registry or any test file; no model call; no database or schema change (`R-146ah`).
- No decision for another section; the cross-section questions are decided once by the brief and applied here.
- The web label for `reviewed` and the schema docstring are not touched; they are the integrator's, once for all fourteen lanes.

## Deliverables

- `src/auditmanager/analysis/text/profiles/itp/system_prompt.md`: one narrowing sentence in the heat-load bullet; the symbol `Kv` removed from the condition 2 example.
- `src/auditmanager/analysis/text/profiles/itp/profile.json`: `status` `reviewed`, `profile_version` `1.1.0`.
- `fixtures/recorded/sections/itp/b9b9d6a8dc98d75291fd0ad13bf1d532204a25270691511d4e6522f61279953b.json`: the rebuilt synthetic recording (the old `cc1fab23…f57d` file is removed by the builder).
- The `ITP` line of `section_profile_expectations.json`: `reviewed`, `1.1.0`.
- `docs/program/SECTION-ITP-FULL-01.md`: the decisions table, the prompt diff in words, the assumptions an expert would still check, the mutation table, counts.

## Required tests

- `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages` — expected: 211 passed.
- The same with the lane `.env` exported, on `tests/integration/composition/test_analysis_profiles_over_http.py` — expected: 4 passed.
- `npx vitest run tests/unit/analysis-settings` in `web/` — expected: 7 files, 95 passed.
- `PYTHONPATH=src:$BS .venv/bin/python fixtures/recorded/sections/build_fixtures.py --check` — expected: `fixtures match`, exit 0.
- `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` on the committed tree, and `git diff --check`.
- The governance one-liner on this file — expected: `[]`.
- Mutations: status only, version only, the expectations line only (three ways), the prompt only, the new sentence alone, `Kv` alone, one comma inside the new sentence, the recording only, the recording's origin only; the audit scripts with an inserted designation; each red, restored, green (table in the report).

## Integration contract

The integrator can rely on: the ITP package declares `reviewed` at `1.1.0` and so does its line of the expectations file; the registry serves it with `analysis_profile_id` and `prompt_bundle_id` unchanged and a new `content_sha256` for the bundle (the prompt text changed); the recorded-mode run of an ИТП-classified version replays the rebuilt recording (key `b9b9d6a8…953b`) and a stale or foreign key is still refused. The two v1 categories, the response schema, token limits and every other section are unchanged. The lane edits no test file and no shared fixture, so it merges without conflict with the other section lanes (one expectations line each). **Nobody reviewed this section** (`A-7`).

## Failure/idempotency/security cases

A status edit without the expectations line, or the reverse, a version edit without the line, a prompt edit without the rebuilt recording (and a rebuilt recording without the prompt) are each red; the builder `--check` is idempotent (`fixtures match` after the rebuild, the other thirteen recordings rewritten byte for byte). No secret, credential or network access is involved.

## Rollback / feature flag

Forward-revert of the commits restores `draft` at `1.0.0` and the old recording key; no data migration exists and profiles are files. No feature flag: the registry serves what the package declares.

## Handoff

- changed files: the five paths above
- commands/results: see `docs/program/SECTION-ITP-FULL-01.md`
- known limits: see the report (no expert review; the wording of the prompt edits is pinned only through the recording key; the recording reply is the builder's synthetic one, unchanged; a section that writes one load in two units is no longer compared across them; the plain words «максимальная», «среднечасовая», «пропускная способность», «опросный лист», «уставки», «подогрев» of the base prompt stay although the source lacks them)
- integration notes: merge in any order with the other section lanes; run the section tests and `--check` after the merge
