# Task SECTION-AI-FULL-01 — the АИ (AI) profile answers every open question of its record and is `reviewed`, without a human review

task_id: SECTION-AI-FULL-01
status: completed in development candidate

## Outcome

The record of section `AI` in `W59-SECTION-PROFILES-01.md` lists four «open questions for the expert reviewer». Each now has one written decision (K keep, N narrow, X exclude) in the report, the four cross-section decisions of `PRODUCTION-WAVE-PW2B.md` are applied, `system_prompt.md` is edited only where a decision is N, `profile_version` is bumped because the prompt text changed, the section's recording is rebuilt, and `profile.json` and its one line of `section_profile_expectations.json` say `reviewed`. Under `R-146ag` neither an expert nor the owner reviews the section; `reviewed` here is **not** expert verification (`A-7`).

## Depends on

- `PRODUCTION-READINESS-PLAN-01` — completed; item `PROD-14` is this lane's family.
- `PROD-14-0-EXPECTATIONS-01` — completed; it created the one-line-per-section expectations file.
- `W59-SECTION-PROFILES-01`, `SECTION-RECORDINGS-01` — completed; they created the package and the recording.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.5.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable (the two categories, the response schema and the output contract of v1 are unchanged)
- migration head: `0032_ar_v3_run_group`, unchanged (`R-146ah`: no migration)
- base commit: `0e663fd0` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No section, package or route is added or removed. The recording directory `fixtures/recorded/sections/ai/` keeps exactly one file; its name is the new request key.

## Captured premise evidence

- premise: the package, its status and version, the five hash-pinned legacy files, the four open questions, the four cross-section questions, the expectations line and the recording are as the brief and the record describe; captured before any edit

### P-01 — the package at the base commit

- captured_at: 2026-10-26
- command: `ls -l src/auditmanager/analysis/text/profiles/ai; python3 -I -c "import json;d=json.load(open('src/auditmanager/analysis/text/profiles/ai/profile.json',encoding='utf-8'));print(d['section_code'],d['status'],d['profile_version'],d['analysis_profile_id'],d['prompt_bundle_id'])"; sha256sum src/auditmanager/analysis/text/profiles/ai/system_prompt.md`
- captured_output:
  ```text
  total 24
  -rw-r--r-- 1 root root  1228 Oct 26 16:14 profile.json
  -rw-r--r-- 1 root root 10222 Oct 26 16:14 system_prompt.md
  AI draft 1.0.0 ap_01M5AXG1K03864N3KSY4AM9P10 pb_01M5AXG1K095VZEZ6BHYM6W9QV
  f2b10f1f550869cee31d7f912a3ea52f2be29e7b6f9d3d1d6b53eeaf8333f0d9  src/auditmanager/analysis/text/profiles/ai/system_prompt.md
  ```
- interpretation: the package is `draft` at `1.0.0`, with the identities the record names. It holds `profile.json` and `system_prompt.md` and nothing else, so the section has no `open_questions.md` (that file belongs to the authored `PB` only).

### P-02 — the legacy source is on the host, clean, at the pinned commit, and the five hashes match

- captured_at: 2026-10-26
- command: `python3 -I -c "import json,subprocess,hashlib;m=json.load(open('src/auditmanager/analysis/text/profiles/ai/profile.json',encoding='utf-8'))['source'];print(subprocess.run(['git','-C','/root/projects/PDF-proverka','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()==m['commit'],subprocess.run(['git','-C','/root/projects/PDF-proverka','status','--short'],capture_output=True,text=True).stdout=='');[print(f['path'].rsplit('/',1)[1],hashlib.sha256(subprocess.run(['git','-C','/root/projects/PDF-proverka','show',m['commit']+':'+f['path']],check=True,capture_output=True).stdout).hexdigest()==f['sha256']) for f in m['files']]"`
- captured_output:
  ```text
  True True
  role.md True
  checklist.md True
  drawing_types.md True
  project_params.md True
  finding_categories.md True
  ```
- interpretation: `PDF-proverka` HEAD is `16ba8e5d23e4782550e79355002fde1365f682b7`, its tree is clean, and each of the five files pinned in `profile.json` has the recorded SHA-256 at that commit. The lane read the files from the working tree (their `sha256sum` equals the same values) and wrote nothing there.

### P-03 — the four open questions of the record

- captured_at: 2026-10-26
- command: `git show HEAD:docs/program/W59-SECTION-PROFILES-01.md | sed -n 239,244p`
- captured_output:
  ```text
  Open questions for the expert reviewer:

  - Формулировки «цвет — по выбору заказчика», «артикул согласовать с заказчиком», «по утверждённому образцу» — заполнитель или принятое решение оставить выбор до закупки и авторского надзора?
  - Общая высота в общих указаниях («высота помещений в чистоте 2,70 м») и меньшая высота конкретного помещения с подвесным потолком в ведомости отделки — противоречие или общая величина, от которой отдельные помещения законно отступают?
  - Общие указания задают класс для путей эвакуации («отделка стен и потолков — КМ1»), а в ведомости отделки коридора стоит материал КМ2: это внутреннее противоречие или скрытая проверка соответствия нормам, которую нужно оставить W57?
  - Ведомость отделки и экспликации часто составляются на тип квартиры, а номера помещений повторяются на этажах и в разных типах: хватает ли условия 1, или сверка наименований и площадей по номеру помещения даст систематические ложные находки?
  ```
- interpretation: exactly four questions, as the brief implies; the template's «every open question gets exactly one decision» therefore means four decisions plus the four cross-section ones. The record is not edited by this lane (`W59-SECTION-PROFILES-01.md` is a forbidden path).

### P-04 — the four cross-section questions of the record

- captured_at: 2026-10-26
- command: `git show HEAD:docs/program/W59-SECTION-PROFILES-01.md | sed -n 171,187p`
- captured_output:
  ```text
  These questions apply to every profile, so they are asked once here:

  1. **Site and contractor phrases.** «уточнить по месту», «уточнить при монтаже»,
     «уточняется в ППР», «по проекту оператора» and similar phrases. Under v1's
     wording each is an explicit placeholder. Are they placeholders, or accepted site
     or contractor instructions that should go into condition 4?
  2. **«Итого» against the sum of rows.** An «Итого» line in a specification, a ТЭП
     table or a schedule that disagrees with the sum of its rows. Recomputation is
     excluded today. Should this one arithmetic case be an `internal_contradiction`?
  3. **Text read from sheets.** Values read from the text layer of drawing sheets
     (labels, title blocks, leaders). These are text, but they are often detached from
     their objects. Do the bullets that name "подписи планов/схем" give systematic false
     findings?
  4. **Missing items.** An item named in one place and absent from another (a panel on
     a scheme but not in the specification). This is an omission, not two
     incompatible values. Is a third kind of observation wanted? That would be a
     contract change, not a profile edit.
  ```
- interpretation: the four questions that the brief fixes as K, K, K unless the section's own record names a systematic false-positive bullet (then N for that bullet only), K.

### P-05 — the expectations line, the builder and the recording at the base commit

- captured_at: 2026-10-26
- command: `grep -n '"AI"' tests/unit/analysis/text_profiles/section_profile_expectations.json; PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py --check; ls fixtures/recorded/sections/ai`
- captured_output:
  ```text
  5:    {"code": "AI", "status": "draft", "profile_version": "1.0.0"},
  fixtures match
  a03cfde3562613cfc7db02912f3ff883afa88f21719528ce87a13d8b0c04bf8f.json
  ```
- interpretation: one line, `draft` at `1.0.0`; the builder agrees with the one recording on disk, whose file name is its `request_sha256` and whose `origin.profile_status` is `draft`, `origin.prompt_bundle_sha256` begins `1e81884a…`, `origin.task_id` is `W59-ANALYSIS-SETTINGS-01`.

### P-06 — how `status` and `profile_version` enter the hashes

- captured_at: 2026-10-26
- command: `grep -n "status\|profile_version" src/auditmanager/analysis/text/profile.py src/auditmanager/analysis/text/prompt.py src/auditmanager/analysis/text/adapter.py`
- captured_output:
  ```text
  src/auditmanager/analysis/text/profile.py:43:    profile_version: str
  src/auditmanager/analysis/text/profile.py:60:                    "profile_version": self.profile_version,
  src/auditmanager/analysis/text/profile.py:73:    profile_version=PROFILE_VERSION,
  ```
- interpretation: `status` appears in none of the three files, so it enters no hash and no request body (it is only a field of `RegisteredTextProfile` and of the recording's informational `origin.profile_status`). `profile_version` enters the profile's `content_sha256` (line 60), not the request. The request key (`request_sha256`) depends on the system prompt text through `PromptBundle.content_sha256`, so only a prompt edit orphans the recording; a status or version change alone does not.

### P-07 — nothing else pins the AI prompt hash, request key or identities

- captured_at: 2026-10-26
- command: `grep -rIl "1e81884a24920897950685528c42c9c002058d37044e8a681af188d6d6d0f956\|a03cfde3562613cfc7db02912f3ff883afa88f21719528ce87a13d8b0c04bf8f\|ap_01M5AXG1K03864N3KSY4AM9P10\|pb_01M5AXG1K095VZEZ6BHYM6W9QV" --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.venv .`
- captured_output:
  ```text
  docs/program/W59-SECTION-PROFILES-01.md
  src/auditmanager/analysis/text/profiles/ai/profile.json
  fixtures/recorded/sections/ai/a03cfde3562613cfc7db02912f3ff883afa88f21719528ce87a13d8b0c04bf8f.json
  ```
- interpretation: only the record (forbidden path, not edited), the package and the recording carry those values, so rebuilding the recording leaves no dangling pin elsewhere.

### P-08 — baseline of the section test set before any edit

- captured_at: 2026-10-26
- command: `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages`
- captured_output:
  ```text
  211 passed in 5.49s
  ```
- interpretation: green at the base. `$BS` is the repository's bootstrap site-packages directory.

### P-09 — which numerals and class designations of the prompt are not in the pinned source

- captured_at: 2026-10-26
- command: `python3 -I audit_designations.py <worktree> AI`
- captured_output:
  ```text
  prompt: AI digit-bearing tokens: ['Г1–Г4', 'Е0,5', 'Е1,']
    'Г1–Г4'          in legacy source: False
    'Е0,5'           in legacy source: True
    'Е1,'            in legacy source: True
  capital designations: ['TBD', 'XX', 'АИ', 'Г1–Г4', 'ГОСТ', 'Е0,5', 'Е1', 'ЖЕ', 'И', 'КМ', 'НЕ', 'СП', 'ТОГО', 'ТОМ']
    'TBD'            in legacy source: False
    'XX'             in legacy source: False
    'АИ'             in legacy source: True
    'Г1–Г4'          in legacy source: False
    'ГОСТ'           in legacy source: False
    'Е0,5'           in legacy source: True
    'Е1'             in legacy source: True
    'ЖЕ'             in legacy source: False
    'И'              in legacy source: True
    'КМ'             in legacy source: True
    'НЕ'             in legacy source: False
    'СП'             in legacy source: True
    'ТОГО'           in legacy source: False
    'ТОМ'            in legacy source: False
  ```
- interpretation: the audit script (printed in the report, section «Audit of numerals and designations») reads the five files at the pinned commit and checks every digit-bearing token and every capital-letter token of the prompt. The tokens `TBD`, `XX`, `ГОСТ`, `ЖЕ`, `НЕ`, `ТОГО`, `ТОМ` are words of v1's own text (placeholder markers, the norm-family list of the exclusion sentence, upper-case emphasis), not designations the section adds. At the base, `Г1–Г4` (condition 2) is the one class designation that the section's own source does not contain (`role.md` says only «классы горючести»), so the rule «no class designation that is not in the section's source» applies to the profile as it stands, not only to additions. This is the one finding beyond the four questions.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/profiles/ai/**`
- `fixtures/recorded/sections/ai/**`
- `tests/unit/analysis/text_profiles/section_profile_expectations.json`
- `docs/program/tasks/SECTION-AI-FULL-01.md`
- `docs/program/SECTION-AI-FULL-01.md`

`section_profile_expectations.json` is allowed for the `AI` line only.

## Forbidden hotspots

Every other section's files, `docs/program/W59-SECTION-PROFILES-01.md`, the registry, `P02_LOCK.json`, `contracts/**`, migrations, `web/**`, `infra/**`, `fixtures/recorded/sections/build_fixtures.py`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs, `origin/main`, tags and the deployment host.

## Non-goals

- No new finding category, no widening of what a finding is, no change to v1's two categories, response schema or output contract (`contracts/**` untouched).
- No normative number, norm reference, threshold or class designation that is not in the section's hash-pinned source; no engineering judgement written into the prompt.
- No claim that an expert or the owner verified anything (`A-7`).
- No new identity (`analysis_profile_id`, `prompt_bundle_id`): the lane does not mint ids.
- No migration (`R-146ah`), no model call, no push.
- No edit of the web label for `reviewed` (outside the allowed paths; reported to the integrator).

## Deliverables

- `src/auditmanager/analysis/text/profiles/ai/system_prompt.md`: two edits (N for question 4; removal of the unsourced designation).
- `src/auditmanager/analysis/text/profiles/ai/profile.json`: `status` `reviewed`, `profile_version` `1.1.0`.
- `fixtures/recorded/sections/ai/<new request key>.json`, rebuilt by `fixtures/recorded/sections/build_fixtures.py`; the old file removed by the builder.
- The `AI` line of `tests/unit/analysis/text_profiles/section_profile_expectations.json`.
- Report `docs/program/SECTION-AI-FULL-01.md`: decisions table, the diff of the prompt in words, assumptions an expert would still want to check, mutation table, test counts, integration notes.

## Required tests

- `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages` — expected: 211 passed.
- With the lane stack: `tests/integration/composition/test_analysis_profiles_over_http.py` — expected: 4 passed.
- In `web/`: `npx vitest run tests/unit/analysis-settings` — expected: 95 passed.
- `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py --check` — expected: `fixtures match`, rc 0.
- Mutations: revert the status in `profile.json` only, and separately the `AI` line only — expected: red naming `AI`; also the prompt only and the recording only — expected: red.
- The governance one-liner on this file — expected: `[]`; `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` and `git diff --check` before the last commit.

## Integration contract

The integrator can rely on: the diff is confined to the five allowed path groups, the `AI` line of the expectations file is a one-line change, the other thirteen recordings are byte-identical after the builder runs, the registry loads `AI` as `reviewed` at `1.1.0` with the same identities, and `--check` of the builder is clean. The integrator must decide the points listed in the report under «Integration notes», in particular that the web label for `reviewed` reads «проверен экспертом».

## Failure/idempotency/security cases

A prompt edit without a rebuilt recording turns the builder's `--check` and eight cases of `test_section_recordings.py` red; a status or version in `profile.json` that differs from the expectations line turns the registry, package and guard tests red (and the HTTP and web tests, which read the same line). Re-running the builder is idempotent. No security surface: static data, no code.

## Rollback / feature flag

Forward-revert of the lane's commits restores `draft`, `1.0.0`, the old prompt and the old recording together. No feature flag: the profile is served by the registry as soon as it is merged, as before; `draft` and `reviewed` are both executable.

## Handoff

- changed files: see the report
- commands/results: see the report
- known limits: see the report (assumptions an expert would still want to check; nothing was measured on real text)
- integration notes: see the report; the web label for `reviewed` needs a decision before any section is shown as `reviewed`
