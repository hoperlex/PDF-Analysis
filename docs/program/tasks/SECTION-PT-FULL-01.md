# Task SECTION-PT-FULL-01 — the ПТ (PT) profile answers every open question of its record and is `reviewed`, without a human review

task_id: SECTION-PT-FULL-01
status: completed in development candidate

## Outcome

The record of section `PT` in `W59-SECTION-PROFILES-01.md` lists five «open questions for the expert reviewer». Each now has one written decision (K keep, N narrow, X exclude) in the report, the four cross-section decisions of `PRODUCTION-WAVE-PW2B.md` are applied, `system_prompt.md` is edited only where a decision is N, `profile_version` is bumped because the prompt text changed, the section's recording is rebuilt, and `profile.json` and its one line of `section_profile_expectations.json` say `reviewed`. Under `R-146ag` neither an expert nor the owner reviews the section; `reviewed` here is **not** expert verification (`A-7`).

## Depends on

- `PRODUCTION-READINESS-PLAN-01` — completed; item `PROD-14` is this lane's family.
- `PROD-14-0-EXPECTATIONS-01` — completed; it created the one-line-per-section expectations file.
- `W59-SECTION-PROFILES-01`, `SECTION-RECORDINGS-01` — completed; they created the package and the recording.
- `SECTION-KM-FULL-01`, `SECTION-GP-FULL-01` — completed; they set the decisions table, the K/N/X practice and the designation audit that this lane follows.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.5.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable (the two categories, the response schema and the output contract of v1 are unchanged)
- migration head: `0032_ar_v3_run_group`, unchanged (`R-146ah`: no migration)
- base commit: `ae751f23` (`integration/ar-close-1026`, with `AI`, `PS`, `POS`, `TX`, `KJ`, `KM` and `GP` already `reviewed`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No section, package or route is added or removed. The recording directory `fixtures/recorded/sections/pt/` keeps exactly one file; its name is the new request key.

## Captured premise evidence

- premise: the package, its status and version, the five hash-pinned legacy files, the five open questions, the four cross-section questions, the expectations line and the recording are as the brief and the record describe; captured before any edit

### P-01 — the package at the base commit

- captured_at: 2026-10-26
- command: `ls -l src/auditmanager/analysis/text/profiles/pt; python3 -I -c "import json;d=json.load(open('src/auditmanager/analysis/text/profiles/pt/profile.json',encoding='utf-8'));print(d['section_code'],d['status'],d['profile_version'],d['analysis_profile_id'],d['prompt_bundle_id'])"; sha256sum src/auditmanager/analysis/text/profiles/pt/system_prompt.md`
- captured_output:
  ```text
  total 16
  -rw-r--r-- 1 root root  1219 Oct 26 16:52 profile.json
  -rw-r--r-- 1 root root 10767 Oct 26 16:52 system_prompt.md
  PT draft 1.0.0 ap_01M5AXG1KHY5S7A1AFVND7FPS9 pb_01M5AXG1KH4JG7TMH93XACNF6H
  5a46b266b5a75e837a23562b5de00c47e10204a9b5505212c69a856ba3b394b9  src/auditmanager/analysis/text/profiles/pt/system_prompt.md
  ```
- interpretation: the package is `draft` at `1.0.0`, with the identities the record names. It holds `profile.json` and `system_prompt.md` and nothing else, so the section has no `open_questions.md` (that file belongs to the authored `PB` only).

### P-02 — the legacy source is on the host, clean, at the pinned commit, and the five hashes match

- captured_at: 2026-10-26
- command: `python3 -I -c "import json,subprocess,hashlib;m=json.load(open('src/auditmanager/analysis/text/profiles/pt/profile.json',encoding='utf-8'))['source'];print(subprocess.run(['git','-C','/root/projects/PDF-proverka','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()==m['commit'],subprocess.run(['git','-C','/root/projects/PDF-proverka','status','--short'],capture_output=True,text=True).stdout=='');[print(f['path'].rsplit('/',1)[1],hashlib.sha256(subprocess.run(['git','-C','/root/projects/PDF-proverka','show',m['commit']+':'+f['path']],check=True,capture_output=True).stdout).hexdigest()==f['sha256']) for f in m['files']]"`
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
- command: `git show ae751f23:docs/program/W59-SECTION-PROFILES-01.md | sed -n 644,650p`
- captured_output:
  ```text
  Open questions for the expert reviewer:

  - Формулировки «гарантированный напор уточнить по ТУ», «марку насосной установки уточнить при заказе», «длину рукава уточнить по месту» — заполнитель (так по v1) или ссылка на технические условия и принятое указание поставщику и монтажной организации?
  - Подача насосов в пояснительной записке часто дана в л/с, а в спецификации — в м³/ч, напор — в метрах, а давление — в МПа; считать ли «10 л/с» и «36 м³/ч» одним значением (это уже перевод единиц, то есть счёт) или сравнивать только значения в одинаковых единицах?
  - Напор и давление у пожарных кранов законно различаются по этажам и зонам (с диафрагмами и без); не даёт ли пункт о напоре у диктующего крана ложных находок, если зона или этаж в тексте не названы?
  - Считать ли находкой расхождение расчётного расхода ВПВ с произведением числа струй на расход одной струи или итоговой строки гидравлического расчёта с суммой расходов ВПВ и АУПТ (сейчас пересчёт исключён)?
  - Полон ли перечень мест сверки для комплекта ПТ, где ВПВ и АУПТ часто оформлены одним томом, и не путает ли модель системы с похожими параметрами (ВПВ жилой части и паркинга, спринклерные секции разных этажей)?
  ```
- interpretation: exactly five questions. The first, third and fifth are one decision each; the fifth asks two things (completeness of the list of places; whether the model confuses systems with similar parameters), so the report gives it two decisions (5a, 5b); the fourth asks two things (the product of streams and a single-stream flow; the total line against the sum of ВПВ and АУПТ flows), which one rule covers (4a, 4b). The first and second quote «ТУ», «м³/ч» and «МПа»: «ТУ» occurs in none of the five pinned files, the unit notations do (P-11). The record is not edited by this lane (`W59-SECTION-PROFILES-01.md` is a forbidden path).

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
- command: `grep -n '"PT"' tests/unit/analysis/text_profiles/section_profile_expectations.json; PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py --check; ls fixtures/recorded/sections/pt; python3 -I -c "import json;print(json.load(open('fixtures/recorded/sections/pt/2fa06c3940faae012574f49a2659e077ba190614b9001c82eaaa3f8efac70f28.json',encoding='utf-8'))['origin'])"`
- captured_output:
  ```text
  13:    {"code": "PT", "status": "draft", "profile_version": "1.0.0"},
  fixtures match
  2fa06c3940faae012574f49a2659e077ba190614b9001c82eaaa3f8efac70f28.json
  {'analysis_profile_id': 'ap_01M5AXG1KHY5S7A1AFVND7FPS9', 'kind': 'synthetic', 'profile_status': 'draft', 'prompt_bundle_id': 'pb_01M5AXG1KH4JG7TMH93XACNF6H', 'prompt_bundle_sha256': '5e921520587dc1893871b97c11e87f5067359f3d1e1e3500fbb3dbf438ff37a5', 'section_code': 'PT', 'statement': "Synthetic: authored by hand for SECTION-RECORDINGS-01 to prove section routing in recorded mode. No model produced this reply and no provider call was made. Not field evidence for the profile's review.", 'task_id': 'SECTION-RECORDINGS-01', 'text_layer': 'fixtures/recorded/text_analysis/inputs/ar_baseline_text_layer.json'}
  ```
- interpretation: one line, `draft` at `1.0.0`; the builder agrees with the one recording on disk, whose file name is its `request_sha256`, whose `origin.profile_status` is `draft`, whose `origin.prompt_bundle_sha256` begins `5e921520…` and whose `origin.task_id` is `SECTION-RECORDINGS-01`.

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

### P-07 — nothing else pins the PT prompt hash, request key or identities

- captured_at: 2026-10-26
- command: `grep -rIl "2fa06c3940faae012574f49a2659e077ba190614b9001c82eaaa3f8efac70f28\|ap_01M5AXG1KHY5S7A1AFVND7FPS9\|pb_01M5AXG1KH4JG7TMH93XACNF6H" --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.venv --exclude=.env .`
- captured_output:
  ```text
  docs/program/W59-SECTION-PROFILES-01.md
  src/auditmanager/analysis/text/profiles/pt/profile.json
  fixtures/recorded/sections/pt/2fa06c3940faae012574f49a2659e077ba190614b9001c82eaaa3f8efac70f28.json
  ```
- interpretation: only the record (forbidden path, not edited), the package and the recording carry those values, so rebuilding the recording leaves no dangling pin elsewhere.

### P-08 — baseline of the section test set before any edit

- captured_at: 2026-10-26
- command: `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages`
- captured_output:
  ```text
  211 passed in 3.24s
  ```
- interpretation: green at the base (and `build_fixtures.py --check` printed `fixtures match`, rc 0). `$BS` is the repository's bootstrap site-packages directory.

### P-09 — which numerals and class designations of the prompt are not in the pinned source

- captured_at: 2026-10-26
- command: `python3 -I audit_designations.py <worktree> PT` (the script is printed in the report, section «Audit of numerals and designations»; it reads the five files at the pinned commit)
- captured_output:
  ```text
  prompt: PT digit-bearing tokens: []
  capital designations: ['TBD', 'XX', 'ГОСТ', 'ЖЕ', 'И', 'НЕ', 'ПТ', 'СП', 'ТОГО', 'ТОМ']
    'TBD'            in legacy source: False
    'XX'             in legacy source: False
    'ГОСТ'           in legacy source: True
    'ЖЕ'             in legacy source: False
    'И'              in legacy source: True
    'НЕ'             in legacy source: False
    'ПТ'             in legacy source: True
    'СП'             in legacy source: True
    'ТОГО'           in legacy source: False
    'ТОМ'            in legacy source: False
  ```
- interpretation: the PT prompt carries no digit-bearing token and no class designation (no pipe-system, valve, fire-resistance, hazard-class or sprinkler-group designation), so unlike `VK` nothing has to be removed. `ГОСТ`, `ПТ`, `СП` occur in the source. `TBD`, `XX`, `ЖЕ`, `НЕ`, `ТОГО`, `ТОМ` are words of v1's own text (placeholder markers and upper-case emphasis), not designations the section adds; `И` is a one-letter Russian word, found trivially. The prompt names no norm number, no pressure or time threshold, no pipe size and no group of premises.

### P-10 — where the prompt speaks of pressure, units, totals and sheet labels

- captured_at: 2026-10-26
- command: `grep -n -i "подпис\|штамп\|выноск\|надпис\|итог\|сумм\|диктующ\|напор\|давлен\|единиц\|л/с\|м³" src/auditmanager/analysis/text/profiles/pt/system_prompt.md`
- captured_output:
  ```text
  24:- гарантированный напор в наружной сети, требуемый напор и напор (давление) у диктующего
  31:- марка, подача, напор и мощность электродвигателя одного и того же пожарного насоса
  44:  таблице гидравлического расчёта, в подписях на расчётной схеме, в общих указаниях и в
  51:  гидравлического расчёта, а также в подписях расходов и напоров на схемах.
  60:   струи и расчётный расход внутреннего противопожарного водопровода, свободный напор у
  61:   пожарного крана и напор насоса, расчётная площадь орошения и площадь, защищаемая
  ```
- interpretation: the prompt says nothing about units of measurement (no `единиц`, no `л/с`, no `м³`) and has no total, sum or «Итого» bullet. The pressure bullet (lines 24 to 26, the second bullet of the hint block) names «диктующего пожарного крана или оросителя одной и той же системы или зоны» and compares three places; it says nothing about what to do when the text names no tap, zone or floor. Condition 1 (line 55 to 58) lists «этажам, зонам … пожарным кранам» among the different objects and ends with «Ищи в тексте прямое указание на то, к чему относится значение.» Sheet labels («подписях») occur in two bullets (lines 44, 51); none of the five questions points at them. Lines 16, 50, 68 and 74 are v1's placeholder markers and the exclusion paragraph.

### P-11 — what the pinned source says about the matters of questions 1 to 5

- captured_at: 2026-10-26
- command: `git -C /root/projects/PDF-proverka show 16ba8e5d:prompts/disciplines/PT/<file>.md | grep -n "диктующ\|м³/ч\|л/с\|МПа\|Q = n\|Расчётные формулы\|диафрагм\|Противоречия\|паркинг\|Узлы управления"` for `checklist`, `project_params`, `role`; counts of `ТУ`, `зон`, `уточн` over the five files
- captured_output:
  ```text
  == checklist
  1:### Расчётные формулы для сверки
  2:- Расход ВПВ: Q = n × q (n — число струй, q — расход одной струи, л/с)
  5:- Интенсивность орошения спринклеров: i (л/с·м²) по СП 485
  15:- Давление в системе — не более 0,4 МПа у ПК (с диафрагмой — допускается до 0,6 МПа)
  31:- Минимальное давление у диктующего оросителя (не менее 0,05 МПа для водяных)
  33:- Узлы управления: тип (мокрый, сухой), сигнализация, дренаж
  37:- Расход дренчерной завесы (л/с на погонный метр)
  44:- Основной насос: подача (м³/ч), напор (м), мощность двигателя
  == project_params
  9:- Противоречия между гидравлическим расчётом и принятыми решениями
  44:| vpv_flow_rate_lps | Расход одной струи, л/с | 2.5, 5.0 |
  53:| fire_pump_main_flow_lps | Подача основного пожарного насоса, л/с | 10, 20, 40 |
  == role
  5:Тип объектов: жилые и общественные здания (МКД, паркинги, встроенные помещения).
  13:- Узлы управления спринклерных и дренчерных систем
  ```
  counts over the five files (`grep -c` summed per file): `ТУ` 0, `зон` 0, `уточн` 0.
- interpretation: (a) the source writes the pump flow in м³/ч (`checklist.md` line 44) and in л/с (`project_params.md` line 53), the head in metres and the pressure in МПа, and holds **no conversion rule and no factor**; (b) the formula `Q = n × q` (line 2) sits under the heading «Расчётные формулы для сверки» (line 1), which the record excludes as engineering calculation; (c) the source has «диктующего оросителя» (line 31) and no «диктующего пожарного крана»; it never uses the word «зона»; the diaphragm appears only as the pressure remark of line 15; (d) the source has no «ТУ», no «уточн» (the placeholder wording is v1's own). No decision below writes a number, a unit factor, a norm or a designation that these lines do not hold.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/profiles/pt/**`
- `fixtures/recorded/sections/pt/**`
- `tests/unit/analysis/text_profiles/section_profile_expectations.json`
- `docs/program/tasks/SECTION-PT-FULL-01.md`
- `docs/program/SECTION-PT-FULL-01.md`

`section_profile_expectations.json` is allowed for the `PT` line only.

## Forbidden hotspots

Every other section's files, `docs/program/W59-SECTION-PROFILES-01.md`, the registry, `P02_LOCK.json`, `contracts/**`, migrations, `web/**`, `infra/**`, `fixtures/recorded/sections/build_fixtures.py`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs, `origin/main`, tags and the deployment host.

## Non-goals

- No new finding category, no widening of what a finding is, no change to v1's two categories, response schema or output contract (`contracts/**` untouched).
- No normative number, norm reference, threshold or class designation that is not in the section's hash-pinned source; no engineering judgement written into the prompt. In particular no unit-conversion factor, no pressure or head limit, no rule of how pressure differs by floor or zone, and no «ТУ» (none of these is in the source).
- No claim that an expert or the owner verified anything (`A-7`).
- No new identity (`analysis_profile_id`, `prompt_bundle_id`): the lane does not mint ids.
- No migration (`R-146ah`), no model call, no push.
- No edit of the web label for `reviewed` (outside the allowed paths; the integrator already knows, see the `AI` report).

## Deliverables

- `src/auditmanager/analysis/text/profiles/pt/system_prompt.md`: one edit (N for question 3, appended to the pressure bullet).
- `src/auditmanager/analysis/text/profiles/pt/profile.json`: `status` `reviewed`, `profile_version` `1.1.0`.
- `fixtures/recorded/sections/pt/<new request key>.json`, rebuilt by `fixtures/recorded/sections/build_fixtures.py`; the old file removed by the builder.
- The `PT` line of `tests/unit/analysis/text_profiles/section_profile_expectations.json`.
- Report `docs/program/SECTION-PT-FULL-01.md`: decisions table, the diff of the prompt in words, assumptions an expert would still want to check, mutation table, test counts, integration notes.

## Required tests

- `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages` — expected: 211 passed.
- With the lane stack: `tests/integration/composition/test_analysis_profiles_over_http.py` — expected: 4 passed.
- In `web/`: `npx vitest run tests/unit/analysis-settings` — expected: 95 passed.
- `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py --check` — expected: `fixtures match`, rc 0.
- Mutations: revert the status in `profile.json` only, and separately the `PT` line only — expected: red naming `PT`; also the prompt only and the recording only — expected: red.
- The governance one-liner on this file — expected: `[]`; `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` and `git diff --check` before the last commit.

## Integration contract

The integrator can rely on: the diff is confined to the five allowed path groups, the `PT` line of the expectations file is a one-line change, the other thirteen recordings are byte-identical after the builder runs, the registry loads `PT` as `reviewed` at `1.1.0` with the same identities, and `--check` of the builder is clean. The points under «Integration notes» of the `AI` report (the web label for `reviewed`, the stored runs of the draft profile) apply to `PT` unchanged.

## Failure/idempotency/security cases

A prompt edit without a rebuilt recording turns the builder's `--check` and seven cases of `test_section_recordings.py` red; a status or version in `profile.json` that differs from the expectations line turns the registry, package and guard tests red (and the HTTP and web tests, which read the same line). Re-running the builder is idempotent. No security surface: static data, no code.

## Rollback / feature flag

Forward-revert of the lane's commits restores `draft`, `1.0.0`, the old prompt and the old recording together. No feature flag: the profile is served by the registry as soon as it is merged, as before; `draft` and `reviewed` are both executable.

## Handoff

- changed files: see the report
- commands/results: see the report
- known limits: see the report (assumptions an expert would still want to check; nothing was measured on real text)
- integration notes: see the report
