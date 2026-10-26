# Task SECTION-GP-FULL-01 — the ГП (GP) profile answers every open question of its record and leaves `draft`

task_id: SECTION-GP-FULL-01
status: completed in development candidate

## Outcome

The record of the ГП section in `docs/program/W59-SECTION-PROFILES-01.md` lists five open questions «for the expert reviewer» and four cross-section questions. Under `R-146ag` no expert reviews the section, so a lane answers each one with a written decision (K keep, N narrow, X exclude), applies the decisions to `system_prompt.md`, rebuilds the section's synthetic recording and moves the section to `reviewed`. `A-7`: the status `reviewed` on this profile carries **no human review**; it is not expert verification and must not be read as one. Product behaviour changes only inside the GP prompt (two narrowing edits: one pair in condition 2, one sentence in one hint bullet); no finding category, schema, contract or migration changes (`R-146ah`).

## Depends on

- `PROD-14-0-EXPECTATIONS-01` — completed; it made the status and version pins data (`section_profile_expectations.json`).
- `W59-SECTION-PROFILES-01`, `SECTION-RECORDINGS-01` — completed; they created the package and its recording.
- `PRODUCTION-WAVE-PW2B` (lane template `SECTION-<CODE>-FULL-01`, `R-146ag`, `R-146ah`, `R-146ai`) — the brief.
- `SECTION-AI-FULL-01`, `SECTION-PS-FULL-01`, `SECTION-KJ-FULL-01` — completed on this base; their reports fix the decisions-table format and the audit of designations.

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

- premise: the package, its five legacy source files, the record's five open questions, the recording and the expectations line are as the brief describes; captured at the base commit before any edit

### P-01 — the package, its recording and its expectations line at the base

- captured_at: 2026-10-26
- command: `git rev-parse HEAD && sha256sum src/auditmanager/analysis/text/profiles/gp/profile.json src/auditmanager/analysis/text/profiles/gp/system_prompt.md fixtures/recorded/sections/gp/*.json && grep -n GP tests/unit/analysis/text_profiles/section_profile_expectations.json`
- captured_output:
  ```text
  3c80af0e62c71f04d1e5b1178e0afbe7db6f7d6c
  d8d7d9ead7cb1125dfdb6b427fa8c5723eba44a3cc12404549aa2ae1f415140b  src/auditmanager/analysis/text/profiles/gp/profile.json
  b7a3ea148d63566a23d349b31056cc402c04ab2a9f4838ebdf701ee224752176  src/auditmanager/analysis/text/profiles/gp/system_prompt.md
  6b403ca7bebb9ad42eb4c8d4a5193e0b3099a9cc6a2601165667a34b6d36b35b  fixtures/recorded/sections/gp/d6e106170da12a9a764a218a5bdb7207a355b02563d25e759663e2fcc2f7466e.json
  17:    {"code": "GP", "status": "draft", "profile_version": "1.0.0"},
  ```
- interpretation: the package has exactly `profile.json` and `system_prompt.md` (no `open_questions.md`, which only `PB` carries); the one recording is keyed `d6e10617…466e`; the expectations line says `draft` at `1.0.0`, agreeing with `profile.json` (identities `ap_01M5AXG1KSSZM53N2CBV6XX83E` / `pb_01M5AXG1KSRDEWMP2WT3KNGWJ2`). On this base AI, PS and KJ are already `reviewed` at `1.1.0`.

### P-02 — the five open questions of the GP record

- captured_at: 2026-10-26
- command: `sed -n 857,863p docs/program/W59-SECTION-PROFILES-01.md`
- captured_output:
  ```text
  Open questions for the expert reviewer:

  - Если сумма позиций баланса территории не равна 100 % или площади участка, считать ли это находкой (сейчас арифметический пересчёт исключён)?
  - Площадь участка по ГПЗУ, площадь в границах благоустройства (включая благоустройство за границей участка) и площадь в границах проектирования часто приводятся рядом: не даёт ли пункт о балансе территории систематических ложных находок?
  - Технико-экономические показатели часто приводят значения и по этапам (очередям) строительства, и на весь комплекс: достаточно ли условия 1, чтобы такие значения не сопоставлялись?
  - Отметки и уклоны в текстовом слое планов и профилей оторваны от того, к чему относятся: надёжна ли сверка «в подписях плана организации рельефа», или её лучше ограничить пояснительной запиской, профилями и ведомостями?
  - Формулировки «уточнить по результатам инженерных изысканий», «по согласованию с владельцами сетей», «ассортимент растений уточнить на стадии Р», «отметки уточнить по месту» — заполнитель (так по v1) или принятое указание?
  ```
- interpretation: five questions, each single. The second quotes a hypothetical fact («часто приводятся рядом»), the fourth names one hint bullet and says its text is detached from its object (so cross-section rule 3 can apply to that bullet only). The record's text is unedited at the base (`### GP` at line 812).

### P-03 — the legacy source on this host is the pinned one, clean, and hashes agree

- captured_at: 2026-10-26
- command: `git -C /root/projects/PDF-proverka rev-parse HEAD && git -C /root/projects/PDF-proverka status --short | wc -l && for f in role checklist drawing_types project_params finding_categories; do git -C /root/projects/PDF-proverka show 16ba8e5d23e4782550e79355002fde1365f682b7:prompts/disciplines/GP/$f.md | sha256sum; done`
- captured_output:
  ```text
  16ba8e5d23e4782550e79355002fde1365f682b7
  0
  3a5fdbafcca2b0ada0ad50d53145599b45c771bd3bfa95d1c157469d1b44bd0a  -
  c6d42f648e73bde0e434efe54e6c544d3eaf181c594b27d76eb6041b7e1fc247  -
  e382963ebbe0ce8b14e27e51fa9b914b8a6aa07ed643f1404f82c88ec08bf799  -
  fe02d212adddc7dba97962328862428051951b1e2e32fc2d0b4ecf6d3e6caa93  -
  0568f133ba2cc85e85078f6f2c949b1839dc0a015b674ce26a0d988704d2107d  -
  ```
- interpretation: the five hashes equal the five pins in `profile.json` (and in the record), in the order role, checklist, drawing_types, project_params, finding_categories. The legacy tree is at the pinned commit with no local change; the lane only read it.

### P-04 — what the legacy source does and does not contain (bounds on any wording)

- captured_at: 2026-10-26
- command: `cd <the five GP files exported from the pinned commit> && grep -c -E 'ГПЗУ|границах проектирования|границах благоустройства|подпис|0,000|абсолютн|перечётн|колодц' role.md checklist.md drawing_types.md project_params.md finding_categories.md`
- captured_output:
  ```text
  role.md:0
  checklist.md:0
  drawing_types.md:0
  project_params.md:0
  finding_categories.md:0
  ```
  (one count per file, all zero; the tool that printed it returned the five lines in varying order, listed here in argument order)
- interpretation: none of these words occurs in the source: not «ГПЗУ», not the areas «в границах проектирования» / «в границах благоустройства», not label text («подпис…»), not the zero-mark notation «0,000», not «абсолютн…». The source holds the sheet types (`drawing_types.md`: «Разбивочный план … привязки … к координатам/осям», «План вертикальной планировки … Проектные отметки, уклоны»), the pipe designations in `project_params.md` (`["В1", "К1", "К2", "Т1", "ЭС", "СС"]`) and the balance and ТЭП items. So any wording added by this lane may use the record's own plain words but must carry no number, norm reference, threshold or class designation (and none does: see the audit P-07).

### P-05 — what a status or prompt edit moves: the identity, the recording key, the tests that pin them

- captured_at: 2026-10-26
- command: `git grep -n "profile_status" 3c80af0e -- fixtures/recorded/sections/build_fixtures.py fixtures/recorded/sections/gp && PYTHONPATH=src:$BS .venv/bin/python fixtures/recorded/sections/build_fixtures.py --check; echo rc=$?`
- captured_output:
  ```text
  3c80af0e:fixtures/recorded/sections/build_fixtures.py:346:                "profile_status": registered.status,
  3c80af0e:fixtures/recorded/sections/gp/d6e106170da12a9a764a218a5bdb7207a355b02563d25e759663e2fcc2f7466e.json:8:    "profile_status": "draft",
  fixtures match
  rc=0
  ```
- interpretation: the recording's file name is the digest of the request body, which carries the section's prompt; `profile_version` enters the profile's `content_sha256` and `status` enters neither. The builder writes `registered.status` into `origin.profile_status`, so the recording changes content with the status even where the key would not move; `--check` is green at the base. The recording's wording («Not field evidence for the profile's review») is unchanged by this lane.

### P-06 — the test battery at the base (before any edit)

- captured_at: 2026-10-26
- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages`
- captured_output:
  ```text
  211 passed in 3.74s
  ```
- interpretation: green at the base. With the lane `.env` exported, `tests/integration/composition/test_analysis_profiles_over_http.py` gave `4 passed` at the base.

### P-07 — audit of numerals and designations of the base prompt against the pinned source

- captured_at: 2026-10-26
- command: `python3 -I audit.py <worktree> GP` (the script is printed in `docs/program/SECTION-GP-FULL-01.md`; run on the base prompt before the edit)
- captured_output:
  ```text
  prompt: GP digit-bearing tokens: ['0,000,', 'В1,', 'К1,', 'К2,', 'Т1']
    '0,000,'         in legacy source: False
    'В1,'            in legacy source: False
    'К1,'            in legacy source: False
    'К2,'            in legacy source: False
    'Т1'             in legacy source: True
  capital designations: ['TBD', 'XX', 'В1', 'ГОСТ', 'ГП', 'ЖЕ', 'И', 'К1', 'К2', 'МГН', 'НЕ', 'СП', 'Т1', 'ТОГО', 'ТОМ']
    'TBD'            in legacy source: False
    'XX'             in legacy source: False
    'В1'             in legacy source: True
    'ГОСТ'           in legacy source: True
    'ГП'             in legacy source: True
    'ЖЕ'             in legacy source: False
    'И'              in legacy source: True
    'К1'             in legacy source: True
    'К2'             in legacy source: True
    'МГН'            in legacy source: True
    'НЕ'             in legacy source: False
    'СП'             in legacy source: True
    'Т1'             in legacy source: True
    'ТОГО'           in legacy source: False
    'ТОМ'            in legacy source: False
  ```
- interpretation: the entries with a trailing comma (`В1,`, `К1,`, `К2,`) are an artefact of the script's tokenizer; the same designations without the comma (`В1`, `К1`, `К2`, `Т1`) are in the source (`project_params.md`, the `utility_networks` example). `TBD`, `XX`, `ЖЕ`, `НЕ`, `ТОГО`, `ТОМ` are v1's own words and emphasis (`НЕ`, `ЖЕ`, `ТОГО`, `ТОМ` are fragments of upper-case words, not designations). **The one real finding is `0,000`**: the notation of a building's zero mark in the second hint bullet. It is not a norm, a threshold or a class designation and states no value to compare; the lane keeps it and discloses it (report, assumptions). No class designation absent from the source stays in the prompt.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

`W59-SECTION-PROFILES-01.md` is immutable here: its GP open questions stay as written and are answered in `docs/program/SECTION-GP-FULL-01.md`.

## Publication authority

- development_target: none
- origin_main_authority: none

The lane pushes nothing; the integrator merges and publishes (`AGENTS.md` section 6).

## Allowed paths

- `src/auditmanager/analysis/text/profiles/gp/**`
- `fixtures/recorded/sections/gp/**`
- `tests/unit/analysis/text_profiles/section_profile_expectations.json`
- `docs/program/tasks/SECTION-GP-FULL-01.md`
- `docs/program/SECTION-GP-FULL-01.md`

Only the `GP` line of the expectations file is edited.

## Forbidden hotspots

Every other section's files, `docs/program/W59-SECTION-PROFILES-01.md`, the registry (`profile_registry.py`), `fixtures/recorded/sections/build_fixtures.py`, `docs/program/P02_LOCK.json`, `contracts/**`, migrations, the web, `infra/**`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs, root dependency/lock files, the composition root, global styles, `origin/main`, tags, and the legacy repository `/root/projects/PDF-proverka` (read only).

## Non-goals

- No expert review and no claim of one: `reviewed` here means a lane wrote a decision for each question (`R-146ag`, `A-7`).
- No widening of what a finding is, no third category, no norm reference, number, threshold or class designation beyond the section's hash-pinned legacy source.
- No change to the builder, the registry or any test file; no model call; no database or schema change (`R-146ah`).
- No decision for another section; the cross-section questions are decided once by the brief and applied here.
- The web label for `reviewed` («проверен экспертом») and the schema docstring are not touched; they are the integrator's, once for all fourteen lanes (see the report, integration notes).

## Deliverables

- `src/auditmanager/analysis/text/profiles/gp/system_prompt.md`: two narrowing edits (one pair in condition 2; one sentence in the hint bullet on elevations and slopes).
- `src/auditmanager/analysis/text/profiles/gp/profile.json`: `status` `reviewed`, `profile_version` `1.1.0`.
- `fixtures/recorded/sections/gp/9dbe139a3b025683b91448992b6890a0a7bd54750e95969a3a396c60b7a8b959.json`: the rebuilt synthetic recording (the old `d6e10617…466e` file is removed by the builder).
- The `GP` line of `section_profile_expectations.json`: `reviewed`, `1.1.0`.
- `docs/program/SECTION-GP-FULL-01.md`: the decisions table, the prompt diff in words, the assumptions an expert would still check, the mutation table, counts.

## Required tests

- `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages` — expected: 211 passed.
- The same with the lane `.env` exported, on `tests/integration/composition/test_analysis_profiles_over_http.py` — expected: 4 passed.
- `npx vitest run tests/unit/analysis-settings` in `web/` — expected: 7 files, 95 passed.
- `PYTHONPATH=src:$BS .venv/bin/python fixtures/recorded/sections/build_fixtures.py --check` — expected: `fixtures match`, exit 0.
- `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` on the committed tree, and `git diff --check`.
- The governance one-liner on this file — expected: `[]`.
- Mutations: status only, version only, the expectations line only (two ways), the prompt only, each narrowing edit alone, the recording only, the recording's origin only; each red, restored, green (table in the report).

## Integration contract

The integrator can rely on: the GP package declares `reviewed` at `1.1.0` and so does its line of the expectations file; the registry serves it with `analysis_profile_id` and `prompt_bundle_id` unchanged and a new `content_sha256` for the bundle (the prompt text changed); the recorded-mode run of a ГП-classified version replays the rebuilt recording (key `9dbe139a…b959`) and a stale or foreign key is still refused. The two v1 categories, the response schema, token limits and every other section are unchanged. The lane edits no test file and no shared fixture, so it merges without conflict with the other section lanes (one expectations line each). **Nobody reviewed this section** (`A-7`).

## Failure/idempotency/security cases

A status edit without the expectations line, or the reverse, a version edit without the line, a prompt edit without the rebuilt recording (and a rebuilt recording without the prompt) are each red; the builder `--check` is idempotent (`fixtures match` after the rebuild, the other thirteen recordings rewritten byte for byte). No secret, credential or network access is involved.

## Rollback / feature flag

Forward-revert of the commits restores `draft` at `1.0.0` and the old recording key; no data migration exists and profiles are files. No feature flag: the registry serves what the package declares.

## Handoff

- changed files: the five paths above
- commands/results: see `docs/program/SECTION-GP-FULL-01.md`
- known limits: see the report (no expert review; the wording of the two narrowing edits is pinned only through the recording key; the recording reply is the builder's synthetic one, unchanged; the zero-mark notation «0,000» is not in the source and is kept)
- integration notes: merge in any order with the other section lanes; run the section tests and `--check` after the merge
