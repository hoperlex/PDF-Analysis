# Task SECTION-KM-FULL-01 — the КМ (KM) profile answers every open question of its record and is `reviewed`, without a human review

task_id: SECTION-KM-FULL-01
status: completed in development candidate

## Outcome

The record of section `KM` in `W59-SECTION-PROFILES-01.md` lists five «open questions for the expert reviewer». Each now has one written decision (K keep, N narrow, X exclude) in the report, the four cross-section decisions of `PRODUCTION-WAVE-PW2B.md` are applied, `system_prompt.md` is edited only where a decision is N, `profile_version` is bumped because the prompt text changed, the section's recording is rebuilt, and `profile.json` and its one line of `section_profile_expectations.json` say `reviewed`. Under `R-146ag` neither an expert nor the owner reviews the section; `reviewed` here is **not** expert verification (`A-7`).

## Depends on

- `PRODUCTION-READINESS-PLAN-01` — completed; item `PROD-14` is this lane's family.
- `PROD-14-0-EXPECTATIONS-01` — completed; it created the one-line-per-section expectations file.
- `W59-SECTION-PROFILES-01`, `SECTION-RECORDINGS-01` — completed; they created the package and the recording.
- `SECTION-KJ-FULL-01`, `SECTION-TX-FULL-01` — completed; they set the decisions table, the K/N/X practice and the designation audit that this lane follows.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.5.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable (the two categories, the response schema and the output contract of v1 are unchanged)
- migration head: `0032_ar_v3_run_group`, unchanged (`R-146ah`: no migration)
- base commit: `8a032dedc9b6bccda6f9f01849b543ec5caf891e` (`integration/ar-close-1026`, with `AI`, `PS`, `KJ` and `TX` already `reviewed`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No section, package or route is added or removed. The recording directory `fixtures/recorded/sections/km/` keeps exactly one file; its name is the new request key.

## Captured premise evidence

- premise: the package, its status and version, the five hash-pinned legacy files, the five open questions, the four cross-section questions, the expectations line and the recording are as the brief and the record describe; captured before any edit

### P-01 — the package at the base commit

- captured_at: 2026-10-26
- command: `ls -l src/auditmanager/analysis/text/profiles/km; python3 -I -c "import json;d=json.load(open('src/auditmanager/analysis/text/profiles/km/profile.json',encoding='utf-8'));print(d['section_code'],d['status'],d['profile_version'],d['analysis_profile_id'],d['prompt_bundle_id'])"; sha256sum src/auditmanager/analysis/text/profiles/km/system_prompt.md`
- captured_output:
  ```text
  total 16
  -rw-r--r-- 1 root root  1217 Oct 26 16:38 profile.json
  -rw-r--r-- 1 root root 10381 Oct 26 16:38 system_prompt.md
  KM draft 1.0.0 ap_01M5AXG1KB71SHN23H775AP551 pb_01M5AXG1KB45S6A5TZ0ZTWRVHS
  8757c4e2e8e3747c86befa74ae4503a4509bde2249cca4776a41416bdaa5eb1f  src/auditmanager/analysis/text/profiles/km/system_prompt.md
  ```
- interpretation: the package is `draft` at `1.0.0`, with the identities the record names. It holds `profile.json` and `system_prompt.md` and nothing else, so the section has no `open_questions.md` (that file belongs to the authored `PB` only).

### P-02 — the legacy source is on the host, clean, at the pinned commit, and the five hashes match

- captured_at: 2026-10-26
- command: `python3 -I -c "import json,subprocess,hashlib;m=json.load(open('src/auditmanager/analysis/text/profiles/km/profile.json',encoding='utf-8'))['source'];print(subprocess.run(['git','-C','/root/projects/PDF-proverka','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()==m['commit'],subprocess.run(['git','-C','/root/projects/PDF-proverka','status','--short'],capture_output=True,text=True).stdout=='');[print(f['path'].rsplit('/',1)[1],hashlib.sha256(subprocess.run(['git','-C','/root/projects/PDF-proverka','show',m['commit']+':'+f['path']],check=True,capture_output=True).stdout).hexdigest()==f['sha256']) for f in m['files']]"`
- captured_output:
  ```text
  True True
  role.md True
  checklist.md True
  drawing_types.md True
  project_params.md True
  finding_categories.md True
  ```
- interpretation: `PDF-proverka` HEAD is `16ba8e5d23e4782550e79355002fde1365f682b7`, its tree is clean, and each of the five files pinned in `profile.json` has the recorded SHA-256 at that commit. The lane read the files with `git show` at that commit and wrote nothing there.

### P-03 — the five open questions of the record

- captured_at: 2026-10-26
- command: `git show 8a032ded:docs/program/W59-SECTION-PROFILES-01.md | sed -n 498,502p`
- captured_output:
  ```text
  - Разные обозначения стали для одного и того же элемента (С345 по ГОСТ 27772 в спецификации и 09Г2С по ГОСТ 19281 в общих указаниях) — противоречие или допустимая замена, которую решает эксперт?
  - Формулировки «усилия в узлах — по расчёту», «катеты швов принимать по наименьшей толщине свариваемых элементов», «конструкцию узла уточнить в КМД» — заполнитель (так по v1) или принятое правило и передача решения в КМД?
  - Считать ли находкой расхождение общей массы металлоконструкций в общих данных или строки «Итого» спецификации с суммой масс по маркам (сейчас пересчёт исключён), и как отличать массу по спецификации от массы с учётом наплавленного металла?
  - Марки элементов (Б-1, К-1) нередко повторяются на схемах разных отметок для разных конструкций — не даёт ли пункт о профиле и отметках одной и той же марки систематических ложных находок (условие 1)?
  - Полон ли перечень мест сверки для КМ стадий П и Р, и не даёт ли пункт о нагрузках ложных находок из-за смешения нормативных и расчётных значений?
  ```
- interpretation: exactly five questions. The first quotes «ГОСТ 19281», which none of the five pinned files contains. The third asks two things (the «Итого» arithmetic; how to tell the specification mass from a mass with deposited metal) and the fifth asks two things (completeness of the list of places; the loads bullet). The report gives each part its own decision. The record is not edited by this lane (`W59-SECTION-PROFILES-01.md` is a forbidden path).

### P-04 — the four cross-section questions of the record

- captured_at: 2026-10-26
- command: `git show 8a032ded:docs/program/W59-SECTION-PROFILES-01.md | sed -n 171,187p`
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
- command: `grep -n '"KM"' tests/unit/analysis/text_profiles/section_profile_expectations.json; PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py --check; ls fixtures/recorded/sections/km`
- captured_output:
  ```text
  10:    {"code": "KM", "status": "draft", "profile_version": "1.0.0"},
  fixtures match
  bf6a3d2c60ccf49e287659da9ed480abc0271b487ac21cbc3ba4360877d87cfd.json
  ```
- interpretation: one line, `draft` at `1.0.0`; the builder agrees with the one recording on disk, whose file name is its `request_sha256`, whose `origin.profile_status` is `draft`, whose `origin.prompt_bundle_sha256` begins `c06f4bc5…` and whose `origin.task_id` is `SECTION-RECORDINGS-01`.

### P-06 — how `status` and `profile_version` enter the hashes

- captured_at: 2026-10-26
- command: `grep -n "status\|profile_version" src/auditmanager/analysis/text/profile.py src/auditmanager/analysis/text/prompt.py src/auditmanager/analysis/text/adapter.py`
- captured_output:
  ```text
  src/auditmanager/analysis/text/profile.py:43:    profile_version: str
  src/auditmanager/analysis/text/profile.py:60:                    "profile_version": self.profile_version,
  src/auditmanager/analysis/text/profile.py:73:    profile_version=PROFILE_VERSION,
  ```
- interpretation: `status` appears in none of the three files, so it enters no hash and no request body. `profile_version` enters the profile's `content_sha256` (line 60), not the request. The request key depends on the system prompt text through the bundle's `content_sha256`, so only a prompt edit orphans the recording; a status or version change alone does not.

### P-07 — nothing else pins the KM prompt hash, request key or identities

- captured_at: 2026-10-26
- command: `grep -rIl "bf6a3d2c60ccf49e287659da9ed480abc0271b487ac21cbc3ba4360877d87cfd\|ap_01M5AXG1KB71SHN23H775AP551\|pb_01M5AXG1KB45S6A5TZ0ZTWRVHS" --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.venv --exclude=.env .`
- captured_output:
  ```text
  docs/program/W59-SECTION-PROFILES-01.md
  fixtures/recorded/sections/km/bf6a3d2c60ccf49e287659da9ed480abc0271b487ac21cbc3ba4360877d87cfd.json
  src/auditmanager/analysis/text/profiles/km/profile.json
  ```
- interpretation: only the record (forbidden path, not edited), the package and the recording carry those values, so rebuilding the recording leaves no dangling pin elsewhere.

### P-08 — baseline of the section test set before any edit

- captured_at: 2026-10-26
- command: `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages`
- captured_output:
  ```text
  211 passed in 2.93s
  ```
- interpretation: green at the base. `$BS` is the repository's bootstrap site-packages directory.

### P-09 — which numerals and class designations of the prompt are not in the pinned source

- captured_at: 2026-10-26
- command: `python3 -I audit_designations.py <worktree> km` (the script is printed in the report, section «Audit of numerals and designations»; it reads the five files at the pinned commit)
- captured_output:
  ```text
  prompt: km digit-bearing tokens: []
  capital designations: ['M', 'N', 'Q', 'TBD', 'XX', 'ГОСТ', 'ЖЕ', 'И', 'КМ', 'НЕ', 'СП', 'ТОГО', 'ТОМ']
    'M'              in legacy source: True
    'N'              in legacy source: True
    'Q'              in legacy source: True
    'TBD'            in legacy source: False
    'XX'             in legacy source: False
    'ГОСТ'           in legacy source: True
    'ЖЕ'             in legacy source: False
    'И'              in legacy source: False
    'КМ'             in legacy source: True
    'НЕ'             in legacy source: False
    'СП'             in legacy source: True
    'ТОГО'           in legacy source: False
    'ТОМ'            in legacy source: False
  ```
- interpretation: the KM prompt carries no digit-bearing token and no class designation, so unlike `AI` nothing has to be removed. `N`, `M`, `Q` are the forces of `role.md` line 10 («усилия в элементах (N, M, Q)»; the single-letter lookups are trivially true in a substring test, the real source is that line); `ГОСТ`, `СП` and `КМ` occur in the source. `TBD`, `XX`, `ЖЕ`, `И`, `НЕ`, `ТОГО`, `ТОМ` are words of v1's own text (placeholder markers and upper-case emphasis), not designations the section adds. The prompt names no steel grade, bolt class, fire-resistance limit, norm number or sheet mark.

### P-10 — where the prompt speaks of marks, totals and sheet labels

- captured_at: 2026-10-26
- command: `git show 8a032ded:src/auditmanager/analysis/text/profiles/km/system_prompt.md | grep -n -i "подпис\|штамп\|выноск\|надпис\|итог\|сумм\|марк\|позици"`
- captured_output:
  ```text
  27:- марка стали и её категория для одного и того же элемента или группы элементов в общих
  28:  указаниях, в спецификации металлопроката и в надписях на схемах и узлах;
  32:- количество и масса одной и той же марки элементов в спецификации металлопроката, в
  34:  прямо указанная в общих данных и в итоге спецификации;
  35:- усилия (N, M, Q) для одного и того же узла или элемента в таблице усилий и в надписях
  37:- тип, катет и длина одного и того же сварного шва в надписях узла и в ведомости сварных
  38:  швов, способ сварки и сварочные материалы (марка электрода или проволоки) в общих
  41:  в надписях узла и в ведомости метизов, а для фрикционных соединений — способ обработки
  55:   конструкциям, маркам элементов, узлам или соединениям. Это не противоречие, даже если
  60:   одного элемента и общая масса всех элементов этой марки. Прежде чем сравнивать
  ```
- interpretation: «надписях» (text on schemes and nodes) occurs in four bullets (lines 28, 35, 37, 41), and none of the five questions of the record points at them, so cross-section question 3 has no section-specific false-positive bullet. The profile and elevation bullet (lines 29 to 31, «одного и того же элемента») and the mass bullet (32 to 34, «одной и той же марки») identify an object by a mark; condition 1 (line 54 to 57) lists «маркам элементов» among the different objects but never says that one mark may stand for different constructions (question 4). The only total-like bullet (lines 33 and 34) compares a total «прямо указанная» in two places and sums nothing (question 3 and cross-section 2).

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/profiles/km/**`
- `fixtures/recorded/sections/km/**`
- `tests/unit/analysis/text_profiles/section_profile_expectations.json`
- `docs/program/tasks/SECTION-KM-FULL-01.md`
- `docs/program/SECTION-KM-FULL-01.md`

`section_profile_expectations.json` is allowed for the `KM` line only.

## Forbidden hotspots

Every other section's files, `docs/program/W59-SECTION-PROFILES-01.md`, the registry, `P02_LOCK.json`, `contracts/**`, migrations, `web/**`, `infra/**`, `fixtures/recorded/sections/build_fixtures.py`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs, `origin/main`, tags and the deployment host.

## Non-goals

- No new finding category, no widening of what a finding is, no change to v1's two categories, response schema or output contract (`contracts/**` untouched).
- No normative number, norm reference, threshold or class designation that is not in the section's hash-pinned source; no engineering judgement written into the prompt. In particular no steel-grade equivalence and no norm number named in the record's questions («ГОСТ 19281» is not in the source).
- No claim that an expert or the owner verified anything (`A-7`).
- No new identity (`analysis_profile_id`, `prompt_bundle_id`): the lane does not mint ids.
- No migration (`R-146ah`), no model call, no push.
- No edit of the web label for `reviewed` (outside the allowed paths; the integrator already knows, see the `AI` report).

## Deliverables

- `src/auditmanager/analysis/text/profiles/km/system_prompt.md`: one edit (N for question 4, appended to condition 1).
- `src/auditmanager/analysis/text/profiles/km/profile.json`: `status` `reviewed`, `profile_version` `1.1.0`.
- `fixtures/recorded/sections/km/<new request key>.json`, rebuilt by `fixtures/recorded/sections/build_fixtures.py`; the old file removed by the builder.
- The `KM` line of `tests/unit/analysis/text_profiles/section_profile_expectations.json`.
- Report `docs/program/SECTION-KM-FULL-01.md`: decisions table, the diff of the prompt in words, assumptions an expert would still want to check, mutation table, test counts, integration notes.

## Required tests

- `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages` — expected: 211 passed.
- With the lane stack: `tests/integration/composition/test_analysis_profiles_over_http.py` — expected: 4 passed.
- In `web/`: `npx vitest run tests/unit/analysis-settings` — expected: 95 passed.
- `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py --check` — expected: `fixtures match`, rc 0.
- Mutations: revert the status in `profile.json` only, and separately the `KM` line only — expected: red naming `KM`; also the prompt only and the recording only — expected: red.
- The governance one-liner on this file — expected: `[]`; `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` and `git diff --check` before the last commit.

## Integration contract

The integrator can rely on: the diff is confined to the five allowed path groups, the `KM` line of the expectations file is a one-line change, the other thirteen recordings are byte-identical after the builder runs, the registry loads `KM` as `reviewed` at `1.1.0` with the same identities, and `--check` of the builder is clean. The points under «Integration notes» of the `AI` report (the web label for `reviewed`, the stored runs of the draft profile) apply to `KM` unchanged.

## Failure/idempotency/security cases

A prompt edit without a rebuilt recording turns the builder's `--check` and seven cases of `test_section_recordings.py` red; a status or version in `profile.json` that differs from the expectations line turns the registry, package and guard tests red (and the HTTP and web tests, which read the same line). Re-running the builder is idempotent. No security surface: static data, no code.

## Rollback / feature flag

Forward-revert of the lane's commits restores `draft`, `1.0.0`, the old prompt and the old recording together. No feature flag: the profile is served by the registry as soon as it is merged, as before; `draft` and `reviewed` are both executable.

## Handoff

- changed files: see the report
- commands/results: see the report
- known limits: see the report (assumptions an expert would still want to check; nothing was measured on real text)
- integration notes: see the report
