# Task SECTION-EOM-FULL-01 — the ЭОМ (EOM) profile answers every open question of its record and is `reviewed`, without a human review

task_id: SECTION-EOM-FULL-01
status: completed in development candidate

## Outcome

The record of section `EOM` in `W59-SECTION-PROFILES-01.md` lists four «open questions for the expert reviewer». Each now has one written decision (K keep, N narrow, X exclude) in the report, the four cross-section decisions of `PRODUCTION-WAVE-PW2B.md` are applied, `system_prompt.md` is edited only where a decision is N, `profile_version` is bumped because the prompt text changed, the section's recording is rebuilt, and `profile.json` and its one line of `section_profile_expectations.json` say `reviewed`. Under `R-146ag` neither an expert nor the owner reviews the section; `reviewed` here is **not** expert verification (`A-7`).

## Depends on

- `PRODUCTION-READINESS-PLAN-01` — completed; item `PROD-14` is this lane's family.
- `PROD-14-0-EXPECTATIONS-01` — completed; it created the one-line-per-section expectations file.
- `W59-SECTION-PROFILES-01`, `SECTION-RECORDINGS-01` — completed; they created the package and the recording.
- `SECTION-KM-FULL-01`, `SECTION-GP-FULL-01` — completed on this base; they set the decisions table, the K/N/X practice and the designation audit that this lane follows.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.5.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable (the two categories, the response schema and the output contract of v1 are unchanged)
- migration head: `0032_ar_v3_run_group`, unchanged (`R-146ah`: no migration)
- base commit: `ae751f23437cc8a432e5d7f51635ae677ec51693` (`integration/ar-close-1026`, with `AI`, `PS`, `POS`, `TX`, `KJ`, `KM` and `GP` already `reviewed`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No section, package or route is added or removed. The recording directory `fixtures/recorded/sections/eom/` keeps exactly one file; its name is the new request key.

## Captured premise evidence

- premise: the package, its status and version, the five hash-pinned legacy files, the four open questions, the four cross-section questions, the expectations line and the recording are as the brief and the record describe; captured before any edit

### P-01 — the package at the base commit

- captured_at: 2026-10-26
- command: `ls -l src/auditmanager/analysis/text/profiles/eom; python3 -I -c "import json;d=json.load(open('src/auditmanager/analysis/text/profiles/eom/profile.json',encoding='utf-8'));print(d['section_code'],d['status'],d['profile_version'],d['analysis_profile_id'],d['prompt_bundle_id'])"; sha256sum src/auditmanager/analysis/text/profiles/eom/system_prompt.md`
- captured_output:
  ```text
  total 16
  -rw-r--r-- 1 root root 1248 Oct 26 16:52 profile.json
  -rw-r--r-- 1 root root 8489 Oct 26 16:52 system_prompt.md
  EOM draft 1.0.0 ap_01M5AXG1KKCKB70088QWAR8WD4 pb_01M5AXG1KKNVF7G99H0BB166TW
  41a8ff8d18ab808c32f6e9bc20832de0ab6c54770d4ca48043077dd4e66793da  src/auditmanager/analysis/text/profiles/eom/system_prompt.md
  ```
- interpretation: the package is `draft` at `1.0.0`, with the identities the record names. It holds `profile.json` and `system_prompt.md` and nothing else, so the section has no `open_questions.md` (that file belongs to the authored `PB` only).

### P-02 — the legacy source is on the host, clean, at the pinned commit, and the five hashes match

- captured_at: 2026-10-26
- command: `python3 -I -c "import json,subprocess,hashlib;m=json.load(open('src/auditmanager/analysis/text/profiles/eom/profile.json',encoding='utf-8'))['source'];print(subprocess.run(['git','-C','/root/projects/PDF-proverka','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()==m['commit'],subprocess.run(['git','-C','/root/projects/PDF-proverka','status','--short'],capture_output=True,text=True).stdout=='');[print(f['path'].rsplit('/',1)[1],hashlib.sha256(subprocess.run(['git','-C','/root/projects/PDF-proverka','show',m['commit']+':'+f['path']],check=True,capture_output=True).stdout).hexdigest()==f['sha256']) for f in m['files']]"`
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

### P-03 — the four open questions of the record

- captured_at: 2026-10-26
- command: `git show ae751f23:docs/program/W59-SECTION-PROFILES-01.md | sed -n 691,694p`
- captured_output:
  ```text
  - Формулировки «длины уточнить по месту», «уточнить при монтаже» — заполнитель (так по v1) или принятое указание монтажной организации?
  - Считать ли находкой расхождение строки «Итого» таблицы нагрузок или спецификации с суммой строк (сейчас пересчёт исключён)?
  - Щит или аппарат, названный на схеме, но отсутствующий в спецификации, — нужна ли такая находка (в v1 это не категория)?
  - Полон ли перечень мест сверки для типового комплекта ЭОМ стадий П и Р, и не даёт ли какой-то пункт систематических ложных находок?
  ```
- interpretation: exactly four questions. The fourth asks two things (completeness of the list of places; whether some bullet gives systematic false findings, without naming a bullet), so the report gives it two decisions. The two phrases of the first question, «по месту» and «при монтаже», occur in none of the five pinned files (checked by `grep`, 0 matches each), so no decision may write them into the prompt as examples. The record is not edited by this lane (`W59-SECTION-PROFILES-01.md` is a forbidden path).

### P-04 — the four cross-section questions of the record

- captured_at: 2026-10-26
- command: `git show ae751f23:docs/program/W59-SECTION-PROFILES-01.md | sed -n 171,187p`
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
- command: `grep -n '"EOM"' tests/unit/analysis/text_profiles/section_profile_expectations.json; PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py --check; ls fixtures/recorded/sections/eom`
- captured_output:
  ```text
  14:    {"code": "EOM", "status": "draft", "profile_version": "1.0.0"},
  fixtures match
  71e5232e87603a99d0f8dd688b8a2457e229824163bcee3e60959d3199964be1.json
  ```
- interpretation: one line, `draft` at `1.0.0`; the builder agrees with the one recording on disk, whose file name is its `request_sha256`, whose `origin.profile_status` is `draft`, whose `origin.prompt_bundle_sha256` begins `b775619f…` and whose `origin.task_id` is `SECTION-RECORDINGS-01`.

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

### P-07 — nothing else pins the EOM prompt hash, request key or identities

- captured_at: 2026-10-26
- command: `grep -rIl "71e5232e87603a99d0f8dd688b8a2457e229824163bcee3e60959d3199964be1\|ap_01M5AXG1KKCKB70088QWAR8WD4\|pb_01M5AXG1KKNVF7G99H0BB166TW" --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.venv --exclude=.env .`
- captured_output:
  ```text
  docs/program/W59-SECTION-PROFILES-01.md
  fixtures/recorded/sections/eom/71e5232e87603a99d0f8dd688b8a2457e229824163bcee3e60959d3199964be1.json
  src/auditmanager/analysis/text/profiles/eom/profile.json
  ```
- interpretation: only the record (forbidden path, not edited), the package and the recording carry those values, so rebuilding the recording leaves no dangling pin elsewhere.

### P-08 — baseline of the section test set before any edit

- captured_at: 2026-10-26
- command: `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages`
- captured_output:
  ```text
  211 passed in 3.09s
  ```
- interpretation: green at the base. `$BS` is the repository's bootstrap site-packages directory.

### P-09 — which numerals and class designations of the prompt are not in the pinned source

- captured_at: 2026-10-26
- command: `python3 -I audit_designations.py <worktree> eom` (the script is printed in the report, section «Audit of numerals and designations»; it reads the five files at the pinned commit)
- captured_output:
  ```text
  prompt: EOM digit-bearing tokens: []
  capital designations: ['PE', 'TBD', 'XX', 'АВР', 'ВРУ', 'ГОСТ', 'ГРЩ', 'ЖЕ', 'И', 'НЕ', 'ПУЭ', 'СП', 'ТОГО', 'ТОМ', 'УЗО', 'ЩД', 'ЩО', 'ЩР', 'ЩУ', 'ЭОМ']
    'PE'             in legacy source: True
    'TBD'            in legacy source: False
    'XX'             in legacy source: False
    'АВР'            in legacy source: True
    'ВРУ'            in legacy source: True
    'ГОСТ'           in legacy source: True
    'ГРЩ'            in legacy source: True
    'ЖЕ'             in legacy source: False
    'И'              in legacy source: False
    'НЕ'             in legacy source: False
    'ПУЭ'            in legacy source: True
    'СП'             in legacy source: True
    'ТОГО'           in legacy source: False
    'ТОМ'            in legacy source: False
    'УЗО'            in legacy source: True
    'ЩД'             in legacy source: True
    'ЩО'             in legacy source: True
    'ЩР'             in legacy source: True
    'ЩУ'             in legacy source: True
    'ЭОМ'            in legacy source: True
  ```
- interpretation: the EOM prompt carries no digit-bearing token and no class designation, so unlike `AI` nothing has to be removed, and unlike `GP` no notation is kept that the source lacks. Every panel designation (`ВРУ`, `ГРЩ`, `ЩР`, `ЩО`, `ЩД`, `ЩУ`) and every apparatus abbreviation (`УЗО`, `АВР`, `PE`) is in the source (`drawing_types.md`, `checklist.md`, `role.md`). `ГОСТ`, `СП` and `ПУЭ` are in the exclusion paragraph only, as the things the model must not check against. `TBD`, `XX`, `ЖЕ`, `И`, `НЕ`, `ТОГО`, `ТОМ` are words of v1's own text (placeholder markers and upper-case emphasis), not designations the section adds. The prompt names no cable mark, protection class, cross-section value, current value or norm number.

### P-10 — where the prompt speaks of designations, totals, sheet labels and quantities

- captured_at: 2026-10-26
- command: `git show ae751f23:src/auditmanager/analysis/text/profiles/eom/system_prompt.md | grep -n -i "подпис\|штамп\|выноск\|надпис\|итог\|сумм\|обозначени\|групп\|позици\|одинаков\|метраж"`
- captured_output:
  ```text
  21:- номинальный ток, тип и характеристика защитного аппарата одной и той же группы или
  25:- обозначение и параметры одного и того же щита (ВРУ, ГРЩ, ЩР, ЩО, ЩД, ЩУ) на
  26:  однолинейной схеме, в схеме щита, в подписях планов и в спецификации;
  31:- уставки УЗО и дифференциальных автоматов одной и той же группы на схеме щита и в
  36:- количество одинаковых щитов, аппаратов, светильников и метраж кабеля, прямо указанные
  44:   группам, линиям или помещениям. Это не противоречие, даже если признак называется
  45:   одинаково. Ищи в тексте прямое указание на то, к чему относится значение.
  ```
- interpretation: the prompt has no «Итого» and no recomputation bullet (bullet 4 compares written values of the design power, bullet 9 compares quantities «прямо указанные»), so cross-section question 2 has nothing to remove. Text read from sheet labels occurs in one bullet only (bullet 3, «в подписях планов»), and the record names no bullet as a systematic false-positive source (its fourth question says «какой-то пункт»). Three bullets (1, 6 and, with «линии», 2) identify the object by the group or line; condition 1 lists «щитам, группам, линиям» among the different objects but never says what makes two mentions one group. The record's own «Excluded» list says the same shape: «дубли групп (одинаковые обозначения)» — «одно обозначение у разных объектов по v1 (условие 1) не противоречие; оставлена сверка параметров одного и того же обозначения».

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/profiles/eom/**`
- `fixtures/recorded/sections/eom/**`
- `tests/unit/analysis/text_profiles/section_profile_expectations.json`
- `docs/program/tasks/SECTION-EOM-FULL-01.md`
- `docs/program/SECTION-EOM-FULL-01.md`

`section_profile_expectations.json` is allowed for the `EOM` line only.

## Forbidden hotspots

Every other section's files, `docs/program/W59-SECTION-PROFILES-01.md`, the registry, `P02_LOCK.json`, `contracts/**`, migrations, `web/**`, `infra/**`, `fixtures/recorded/sections/build_fixtures.py`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs, `origin/main`, tags and the deployment host.

## Non-goals

- No new finding category, no widening of what a finding is, no change to v1's two categories, response schema or output contract (`contracts/**` untouched).
- No normative number, norm reference, threshold or class designation that is not in the section's hash-pinned source; no engineering judgement written into the prompt. In particular no phrase of the record's questions («по месту», «при монтаже») is written into the prompt as an example, because the source holds neither.
- No claim that an expert or the owner verified anything (`A-7`).
- No new identity (`analysis_profile_id`, `prompt_bundle_id`): the lane does not mint ids.
- No migration (`R-146ah`), no model call, no push.
- No edit of the web label for `reviewed` (outside the allowed paths; the integrator already knows, see the `AI` report).

## Deliverables

- `src/auditmanager/analysis/text/profiles/eom/system_prompt.md`: one edit (N for question 4, appended to condition 1).
- `src/auditmanager/analysis/text/profiles/eom/profile.json`: `status` `reviewed`, `profile_version` `1.1.0`.
- `fixtures/recorded/sections/eom/<new request key>.json`, rebuilt by `fixtures/recorded/sections/build_fixtures.py`; the old file removed by the builder.
- The `EOM` line of `tests/unit/analysis/text_profiles/section_profile_expectations.json`.
- Report `docs/program/SECTION-EOM-FULL-01.md`: decisions table, the diff of the prompt in words, assumptions an expert would still want to check, mutation table, test counts, integration notes.

## Required tests

- `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages` — expected: 211 passed.
- With the lane stack: `tests/integration/composition/test_analysis_profiles_over_http.py` — expected: 4 passed.
- In `web/`: `npx vitest run tests/unit/analysis-settings` — expected: 95 passed.
- `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py --check` — expected: `fixtures match`, rc 0.
- Mutations: revert the status in `profile.json` only, and separately the `EOM` line only — expected: red naming `EOM`; also the prompt only and the recording only — expected: red.
- The governance one-liner on this file — expected: `[]`; `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` and `git diff --check` before the last commit.

## Integration contract

The integrator can rely on: the diff is confined to the five allowed path groups, the `EOM` line of the expectations file is a one-line change, the other thirteen recordings are byte-identical after the builder runs, the registry loads `EOM` as `reviewed` at `1.1.0` with the same identities, and `--check` of the builder is clean. The points under «Integration notes» of the `AI` report (the web label for `reviewed`, the stored runs of the draft profile) apply to `EOM` unchanged.

## Failure/idempotency/security cases

A prompt edit without a rebuilt recording turns the builder's `--check` and seven cases of `test_section_recordings.py` red; a status or version in `profile.json` that differs from the expectations line turns the registry, package and guard tests red (and the HTTP and web tests, which read the same line). Re-running the builder is idempotent. No security surface: static data, no code.

## Rollback / feature flag

Forward-revert of the lane's commits restores `draft`, `1.0.0`, the old prompt and the old recording together. No feature flag: the profile is served by the registry as soon as it is merged, as before; `draft` and `reviewed` are both executable.

## Handoff

- changed files: see the report
- commands/results: see the report
- known limits: see the report (assumptions an expert would still want to check; nothing was measured on real text)
- integration notes: see the report
