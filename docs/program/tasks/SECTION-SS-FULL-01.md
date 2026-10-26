# Task SECTION-SS-FULL-01 — the СС (SS) profile answers every open question of its record and is `reviewed`, without a human review

task_id: SECTION-SS-FULL-01
status: completed in development candidate

## Outcome

The record of section `SS` in `W59-SECTION-PROFILES-01.md` lists five «open questions for the expert reviewer». Each now has one written decision (K keep, N narrow, X exclude) in the report, the four cross-section decisions of `PRODUCTION-WAVE-PW2B.md` are applied, `system_prompt.md` is edited only where a decision is N (and for one audit finding of a designation absent from the pinned source), `profile_version` is bumped because the prompt text changed, the section's recording is rebuilt, and `profile.json` and its one line of `section_profile_expectations.json` say `reviewed`. Under `R-146ag` neither an expert nor the owner reviews the section; `reviewed` here is **not** expert verification (`A-7`).

## Depends on

- `PRODUCTION-READINESS-PLAN-01` — completed; item `PROD-14` is this lane's family.
- `PROD-14-0-EXPECTATIONS-01` — completed; it created the one-line-per-section expectations file.
- `W59-SECTION-PROFILES-01`, `SECTION-RECORDINGS-01` — completed; they created the package and the recording.
- `SECTION-AI-FULL-01`, `SECTION-PS-FULL-01`, `SECTION-POS-FULL-01`, `SECTION-TX-FULL-01`, `SECTION-KJ-FULL-01`, `SECTION-KM-FULL-01`, `SECTION-OV-FULL-01`, `SECTION-GP-FULL-01` — completed; they set the decisions format, the K/N/X practice and the designation audit.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.5.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable (the two categories, the response schema and the output contract of v1 are unchanged)
- migration head: `0032_ar_v3_run_group`, unchanged (`R-146ah`: no migration)
- base commit: `f72144df` (`integration/ar-close-1026`, with `AI`, `PS`, `POS`, `TX`, `KJ`, `KM`, `OV` and `GP` already `reviewed`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No section, package or route is added or removed. The recording directory `fixtures/recorded/sections/ss/` keeps exactly one file; its name is the new request key.

## Captured premise evidence

- premise: the package, its status and version, the five hash-pinned legacy files, the five open questions, the four cross-section questions, the expectations line and the recording are as the brief and the record describe; captured before any edit

### P-01 — the package at the base commit

- captured_at: 2026-10-26
- command: `ls -l src/auditmanager/analysis/text/profiles/ss; python3 -I -c "import json;d=json.load(open('src/auditmanager/analysis/text/profiles/ss/profile.json',encoding='utf-8'));print(d['section_code'],d['status'],d['profile_version'],d['analysis_profile_id'],d['prompt_bundle_id'])"; sha256sum src/auditmanager/analysis/text/profiles/ss/system_prompt.md`
- captured_output:
  ```text
  total 16
  -rw-r--r-- 1 root root  1205 Oct 26 16:52 profile.json
  -rw-r--r-- 1 root root 10753 Oct 26 16:52 system_prompt.md
  SS draft 1.0.0 ap_01M5AXG1KN9C7BDD3CCHMFTMX3 pb_01M5AXG1KNQRT6DYJWYC5X0C5J
  9967693230a1a680fff3caf63bcc718e7c79af6fbd3c582bf66912690a9acb37  src/auditmanager/analysis/text/profiles/ss/system_prompt.md
  ```
- interpretation: the package is `draft` at `1.0.0`, with the identities the record names. It holds `profile.json` and `system_prompt.md` and nothing else, so the section has no `open_questions.md` (that file belongs to the authored `PB` only).

### P-02 — the legacy source is on the host, clean, at the pinned commit, and the five hashes match

- captured_at: 2026-10-26
- command: `python3 -I -c "import json,subprocess,hashlib;m=json.load(open('src/auditmanager/analysis/text/profiles/ss/profile.json',encoding='utf-8'))['source'];print(subprocess.run(['git','-C','/root/projects/PDF-proverka','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()==m['commit'],subprocess.run(['git','-C','/root/projects/PDF-proverka','status','--short'],capture_output=True,text=True).stdout=='');[print(f['path'].rsplit('/',1)[1],hashlib.sha256(subprocess.run(['git','-C','/root/projects/PDF-proverka','show',m['commit']+':'+f['path']],check=True,capture_output=True).stdout).hexdigest()==f['sha256']) for f in m['files']]"`
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
- command: `git show f72144df:docs/program/W59-SECTION-PROFILES-01.md | sed -n 746,752p`
- captured_output:
  ```text
  Open questions for the expert reviewer:

  - Формулировки «тип оборудования уточнить по ТУ оператора связи», «по проекту оператора», «по согласованию с управляющей компанией» — заполнитель (так по v1, если значения в документе нет) или принятая ссылка на внешний документ?
  - Пожарная сигнализация и СОУЭ нередко выпускаются отдельным томом (АПС, СОУЭ) вне раздела СС: оставить их в этом профиле или вынести в отдельный?
  - Если перечень сигналов, выводимых на диспетчерский пункт, или состав оборудования точки доступа в одном месте короче, чем в другом, — это противоречие или неполнота, о которой по условию 5 не сообщают?
  - Количество портов СКС и ТВ-выводов «на квартиру» часто различается для разных типов квартир: достаточно ли условия 1, или этот пункт будет давать систематические ложные находки?
  - Строка «Итого» спецификации или кабельного журнала против суммы строк, ёмкость ППКП против числа адресных устройств — сейчас пересчёт и такое сравнение исключены; нужна ли какая-либо из этих находок?
  ```
- interpretation: exactly five questions. The last one asks two things (a total against its rows; a device's capacity against the number of connected devices); the report gives each part its own decision. The record is not edited by this lane (`W59-SECTION-PROFILES-01.md` is a forbidden path).

### P-04 — the four cross-section questions of the record

- captured_at: 2026-10-26
- command: `git show f72144df:docs/program/W59-SECTION-PROFILES-01.md | sed -n 171,187p`
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
- command: `grep -n '"SS"' tests/unit/analysis/text_profiles/section_profile_expectations.json; PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py --check; ls fixtures/recorded/sections/ss`
- captured_output:
  ```text
  15:    {"code": "SS", "status": "draft", "profile_version": "1.0.0"},
  fixtures match
  9ed13e71c2a71fe0f616d21bac4057a83a5e24f8f8c88f1fe6e30b0a5cb90bd5.json
  ```
- interpretation: one line, `draft` at `1.0.0`; the builder agrees with the one recording on disk, whose file name is its `request_sha256`.

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

### P-07 — nothing else pins the SS prompt hash, request key or identities

- captured_at: 2026-10-26
- command: `grep -rIl "9ed13e71c2a71fe0f616d21bac4057a83a5e24f8f8c88f1fe6e30b0a5cb90bd5\|ap_01M5AXG1KN9C7BDD3CCHMFTMX3\|pb_01M5AXG1KNQRT6DYJWYC5X0C5J" --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.venv .`
- captured_output:
  ```text
  src/auditmanager/analysis/text/profiles/ss/profile.json
  fixtures/recorded/sections/ss/9ed13e71c2a71fe0f616d21bac4057a83a5e24f8f8c88f1fe6e30b0a5cb90bd5.json
  docs/program/W59-SECTION-PROFILES-01.md
  ```
- interpretation: only the package, the recording and the record (forbidden path, not edited) carry those values, so rebuilding the recording leaves no dangling pin elsewhere.

### P-08 — baseline of the section test set before any edit

- captured_at: 2026-10-26
- command: `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages`
- captured_output:
  ```text
  211 passed in 3.15s
  ```
- interpretation: green at the base. `$BS` is the repository's bootstrap site-packages directory.

### P-09 — which numerals and class designations of the prompt are not in the pinned source

- captured_at: 2026-10-26
- command: `python3 -I audit_designations.py <worktree> SS`, then `python3 -I audit_whole_tokens.py <worktree> SS` (both scripts are printed in the report, section «Audit of numerals and designations»; they read the five files at the pinned commit)
- captured_output:
  ```text
  prompt: SS digit-bearing tokens: []
  capital designations: ['FRLS', 'GPON', 'LS', 'TBD', 'XX', 'А', 'ГОСТ', 'ЖЕ', 'И', 'ИТП', 'НЕ', 'ППКП', 'СКС', 'СКУД', 'СОУЭ', 'СП', 'СС', 'ТВ', 'ТОГО', 'ТОМ']
    'FRLS'           in legacy source: True
    'GPON'           in legacy source: True
    'LS'             in legacy source: True
    'TBD'            in legacy source: False
    'XX'             in legacy source: False
    'А'              in legacy source: True
    'ГОСТ'           in legacy source: True
    'ЖЕ'             in legacy source: False
    'И'              in legacy source: True
    'ИТП'            in legacy source: True
    'НЕ'             in legacy source: False
    'ППКП'           in legacy source: True
    'СКС'            in legacy source: True
    'СКУД'           in legacy source: True
    'СОУЭ'           in legacy source: True
    'СП'             in legacy source: True
    'СС'             in legacy source: True
    'ТВ'             in legacy source: True
    'ТОГО'           in legacy source: False
    'ТОМ'            in legacy source: False
  (second script, whole tokens)
    '(?)'                  whole token in legacy source: False
    '(СС)'                 whole token in legacy source: False
    'GPON'                 whole token in legacy source: True
    'TBD'                  whole token in legacy source: False
    'XX'                   whole token in legacy source: False
    'category'             whole token in legacy source: True
    'evidence'             whole token in legacy source: False
    'explicit_placeholder' whole token in legacy source: False
    'finding_text'         whole token in legacy source: False
    'internal_contradiction' whole token in legacy source: False
    'observations'         whole token in legacy source: False
    'page_number'          whole token in legacy source: False
    'quote'                whole token in legacy source: False
    'recommendation_text'  whole token in legacy source: False
    'нг(А)-FRLS'           whole token in legacy source: False
    'нг(А)-LS'             whole token in legacy source: False
  ```
- interpretation: unlike `KM` and `TX`, the SS prompt carries a class designation of a cable that the source lacks, and the first script does not see it: it tests pieces by substring, so `LS` (inside `FRLS`) and `А` pass although the notation `нг(А)-LS` / `нг(А)-FRLS` does not occur (`grep -c "нг(А)"` over the five files prints `0`; the source's only form is «огнестойкость (FRLS/FR)» in `checklist.md`, ОПС / АУПС and СОУЭ). The lane found it by reading the bullet and added the whole-token pass. `TBD`, `XX`, `ЖЕ`, `НЕ`, `ТОГО`, `ТОМ` are words of v1's own text (placeholder markers, upper-case emphasis). `(СС)` is the section's abbreviation in brackets from the opening sentence (the source has `СС` without brackets: `role.md`, «раздела СС»). So there is one audit finding to correct.

### P-10 — where the prompt speaks of sheet labels, totals and unfilled marks

- captured_at: 2026-10-26
- command: `git show f72144df:src/auditmanager/analysis/text/profiles/ss/system_prompt.md | grep -n -i "подпис\|штамп\|выноск\|надпис\|итог\|сумм"`
- captured_output:
  ```text
  26:  источник питания) на структурной схеме, на схеме подключений, в подписях планов и в
  ```
- interpretation: one hint bullet (the second, lines 24 to 27) reads labels on plans. The SS record's five questions name it as no source of systematic false findings, so cross-section question 3 has no bullet to narrow (K). No bullet sums anything and the prompt has no «итог» or «сумм» line at all, so cross-section question 2 and the first half of record question 5 meet the exclusion paragraph only.

### P-11 — the fire alarm and the warning system belong to SS in the source, and the section set is closed

- captured_at: 2026-10-26
- command: `git -C /root/projects/PDF-proverka show 16ba8e5d23e4782550e79355002fde1365f682b7:prompts/disciplines/SS/role.md | grep -n "ОПС\|СОУЭ"; git -C /root/projects/PDF-proverka show 16ba8e5d23e4782550e79355002fde1365f682b7:prompts/disciplines/SS/finding_categories.md | grep -n "fire_alarm\|pa_system"; sed -n 78,80p src/auditmanager/analysis/text/profile_registry.py`
- captured_output:
  ```text
  13:- ОПС / АУПС (охранно-пожарная сигнализация, автоматическая установка пожарной сигнализации)
  14:- СОУЭ (система оповещения и управления эвакуацией)
  9:| `fire_alarm` | ОПС/АУПС: извещатели, шлейфы, ПКП, интеграция с СОУЭ и инженерными системами |
  10:| `pa_system` | СОУЭ: тип системы, зоны оповещения, мощность, кабели |
  #: The fifteen section codes. Restated, not imported: ``analysis`` does not depend on the
  #: ``sections`` package, and ``tests/unit/analysis/test_text_profile_registry.py`` holds this
  #: set equal to the sections catalogue and the contract's ``ProjectSection``.
  ```
- interpretation: the source lists ОПС / АУПС and СОУЭ among the areas of the SS discipline and gives each a category of its own; the product has fifteen section codes held equal to the contract's `ProjectSection`, with no code for a fire alarm or warning volume. A separate profile would therefore need a sixteenth code and a new identity pair, which is a contract change outside a profile lane.

### P-12 — what the source says about apartments and about the cable execution

- captured_at: 2026-10-26
- command: `git -C /root/projects/PDF-proverka show 16ba8e5d23e4782550e79355002fde1365f682b7:prompts/disciplines/SS/checklist.md | grep -n "квартир\|FRLS"`
- captured_output:
  ```text
  6:- Количество портов на квартиру / этаж -- соответствие проекту
  70:- Разводка по квартирам: коаксиал / оптика
  72:- Количество ТВ-выводов на квартиру
  70:- Кабели шлейфов: огнестойкость (FRLS/FR), способ прокладки
  81:- Кабели: огнестойкость (FRLS/FR), прокладка в огнестойких коробах
  ```
- interpretation: the source speaks of ports and TV outlets «на квартиру» and holds no notion of apartment types, so an edit for question 4 may use the record's own words «типов квартир» but no type, no count and no designation. The only cable execution notation is `FRLS/FR`.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/profiles/ss/**`
- `fixtures/recorded/sections/ss/**`
- `tests/unit/analysis/text_profiles/section_profile_expectations.json`
- `docs/program/tasks/SECTION-SS-FULL-01.md`
- `docs/program/SECTION-SS-FULL-01.md`

`section_profile_expectations.json` is allowed for the `SS` line only.

## Forbidden hotspots

Every other section's files, `docs/program/W59-SECTION-PROFILES-01.md`, the registry, `P02_LOCK.json`, `contracts/**`, migrations, `web/**`, `infra/**`, `fixtures/recorded/sections/build_fixtures.py`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs, `origin/main`, tags and the deployment host.

## Non-goals

- No new finding category, no widening of what a finding is, no change to v1's two categories, response schema or output contract (`contracts/**` untouched).
- No normative number, norm reference, threshold or class designation that is not in the section's hash-pinned source; no engineering judgement written into the prompt.
- No claim that an expert or the owner verified anything (`A-7`).
- No new identity (`analysis_profile_id`, `prompt_bundle_id`) and no new section code: the lane does not mint ids, and a separate profile for a fire alarm volume is not a profile edit.
- No migration (`R-146ah`), no model call, no push.
- No edit of the web label for `reviewed` (outside the allowed paths; the integrator already knows, see the `AI` report).

## Deliverables

- `src/auditmanager/analysis/text/profiles/ss/system_prompt.md`: two edits (N for question 4 in the hint bullet on counts per apartment; the audit correction of the cable execution in the cable bullet).
- `src/auditmanager/analysis/text/profiles/ss/profile.json`: `status` `reviewed`, `profile_version` `1.1.0`.
- `fixtures/recorded/sections/ss/<new request key>.json`, rebuilt by `fixtures/recorded/sections/build_fixtures.py`; the old file removed by the builder.
- The `SS` line of `tests/unit/analysis/text_profiles/section_profile_expectations.json`.
- Report `docs/program/SECTION-SS-FULL-01.md`: decisions table, the diff of the prompt in words, assumptions an expert would still want to check, mutation table, test counts, integration notes.

## Required tests

- `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages` — expected: 211 passed.
- With the lane stack: `tests/integration/composition/test_analysis_profiles_over_http.py` — expected: 4 passed.
- In `web/`: `npx vitest run tests/unit/analysis-settings` — expected: 95 passed.
- `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py --check` — expected: `fixtures match`, rc 0.
- Mutations: revert the status in `profile.json` only, and separately the `SS` line only — expected: red naming `SS`; also the prompt only and the recording only — expected: red.
- The governance one-liner on this file — expected: `[]`; `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` and `git diff --check` before the last commit.

## Integration contract

The integrator can rely on: the diff is confined to the five allowed path groups, the `SS` line of the expectations file is a one-line change, the other thirteen recordings are byte-identical after the builder runs, the registry loads `SS` as `reviewed` at `1.1.0` with the same identities, and `--check` of the builder is clean. The points under «Integration notes» of the `AI` report (the web label for `reviewed`, the stored runs of the draft profile) apply to `SS` unchanged.

## Failure/idempotency/security cases

A prompt edit without a rebuilt recording turns the builder's `--check` and seven cases of `test_section_recordings.py` red; a status or version in `profile.json` that differs from the expectations line turns the registry, package and guard tests red (and the HTTP and web tests, which read the same line). Re-running the builder is idempotent. No security surface: static data, no code.

## Rollback / feature flag

Forward-revert of the lane's commits restores `draft`, `1.0.0`, the old prompt and the old recording together. No feature flag: the profile is served by the registry as soon as it is merged, as before; `draft` and `reviewed` are both executable.

## Handoff

- changed files: see the report
- commands/results: see the report
- known limits: see the report (assumptions an expert would still want to check; nothing was measured on real text)
- integration notes: see the report
