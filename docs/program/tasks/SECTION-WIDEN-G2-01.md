# Task SECTION-WIDEN-G2-01 — the КМ, ОВ, ВК and ПТ prompts ask for the same-document total-against-its-rows checks that the gap report marks reinstatable, under the two existing categories

task_id: SECTION-WIDEN-G2-01
status: completed in development candidate

## Outcome

For the four sections `KM`, `OV`, `VK` and `PT` the system prompt asks for the checks that `ROADMAP-GAP-2026-10-27.md` section 2.3 («Reinstatable now») lists for them, each under the conservative rules (1) to (6) of `PRODUCTION-WAVE-PW4.md` section 6: a total against the sum of its rows (КМ mass, ОВ air exchange and heat loads, ВК daily consumption), and for ПТ the same flow in л/с and м³/ч, the product of jets and single-jet flow, and the ВПВ + АУПТ sum. Every finding stays `internal_contradiction`; no category, field, severity or norm is added. Each topic has a written decision (W widen, K keep, N narrow, X exclude) with the exact sentence in the report. `profile_version` moves `1.1.0` to `1.2.0` with `status` `reviewed`; the four routing recordings are rebuilt; each section gets one synthetic positive and one synthetic negative specimen, kept in the report with the replay through the real stage and the machine-readable table of the fragments added to each prompt. Under `R-146ag` and `A-7` nobody reviews the result: `reviewed` is **not** expert verification.

## Depends on

- `SECTION-KM-FULL-01`, `SECTION-OV-FULL-01`, `SECTION-VK-FULL-01`, `SECTION-PT-FULL-01` — completed; they set the 1.1.0 prompts and the K/N/X decisions this lane widens.
- `SECTION-RECORDINGS-01`, `SECTION-PROMPT-TOKEN-GUARD-01`, `PROD-14-0-EXPECTATIONS-01` — completed; the recording builder, the designation guard and the expectations file.
- `ROADMAP-GAP-2026-10-27` — completed; section 2.3 is this lane's list of topics.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.7.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable (the two categories, the response schema, `prompt.py`, `response.py`, `stage.py` and the output contract of v1 are unchanged)
- migration head: `0033_ar_v3_cite_stage_id`, unchanged (no migration)
- base commit: `6075df88` (`integration/ar-close-1026`, product `VERSION` `0.8.2`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No section, package or route is added or removed. The expectations file keeps its fourteen lines; four versions move.

## Captured premise evidence

- premise: the packages, their pinned legacy sources, the gap report's rows, the record's questions, the recording and guard pins that decide where the new fixtures can live, the unit factor and the baseline test count are as the brief describes; captured at the start of the lane (P-10 on the base before the first edit, the others by commands that read the base commit or files the lane does not change)

### P-01 — the four packages at the base commit

- captured_at: 2026-10-27
- command: `for c in km ov vk pt; do git show 6075df88:src/auditmanager/analysis/text/profiles/$c/profile.json | python3 -I -c "import json,sys;d=json.load(sys.stdin);print(d['section_code'],d['status'],d['profile_version'],d['analysis_profile_id'],d['prompt_bundle_id'])"; git show 6075df88:src/auditmanager/analysis/text/profiles/$c/system_prompt.md | sha256sum; done; git ls-tree --name-only 6075df88 src/auditmanager/analysis/text/profiles/km/ src/auditmanager/analysis/text/profiles/ov/ src/auditmanager/analysis/text/profiles/vk/ src/auditmanager/analysis/text/profiles/pt/`
- captured_output:
  ```text
  KM reviewed 1.1.0 ap_01M5AXG1KB71SHN23H775AP551 pb_01M5AXG1KB45S6A5TZ0ZTWRVHS
  7c50a10b1a4f61a946b9f81b321ccfb7cdeb539e4e426bfd44896fd31d7ccbb5  -
  OV reviewed 1.1.0 ap_01M5AXG1KDVXRHH20N7KGBKPZ4 pb_01M5AXG1KDEVEZ88HR6KYX2YP9
  f477c1fb820a08bf4e03c639674ea2cfad82c72bd22d63323fe9020d90dbc3f5  -
  VK reviewed 1.1.0 ap_01M5AXG1KF7NGNYMEFN97BW9ZN pb_01M5AXG1KFMA8QCKP6YM1K5M5W
  578000d2bf0a3eca40485200cefdec02dee3b42afa5616f11b487fa296b7544d  -
  PT reviewed 1.1.0 ap_01M5AXG1KHY5S7A1AFVND7FPS9 pb_01M5AXG1KH4JG7TMH93XACNF6H
  b6fa8aaa0b044a736c5635d9951f7dbba0631667bdcdb62971f6c7f2b4a3020f  -
  src/auditmanager/analysis/text/profiles/km/profile.json
  src/auditmanager/analysis/text/profiles/km/system_prompt.md
  src/auditmanager/analysis/text/profiles/ov/profile.json
  src/auditmanager/analysis/text/profiles/ov/system_prompt.md
  src/auditmanager/analysis/text/profiles/pt/profile.json
  src/auditmanager/analysis/text/profiles/pt/system_prompt.md
  src/auditmanager/analysis/text/profiles/vk/profile.json
  src/auditmanager/analysis/text/profiles/vk/system_prompt.md
  ```
- interpretation: all four are `reviewed` at `1.1.0` with the identities the record names; each package is `profile.json` plus `system_prompt.md` and nothing else (the ls-tree lines). The prompt hashes are the base the report's diffs are taken against.

### P-02 — the legacy source is on the host, at the pinned commit, clean, and the five hashes of each section match

- captured_at: 2026-10-27
- command: `for c in km ov vk pt; do git show 6075df88:src/auditmanager/analysis/text/profiles/$c/profile.json | python3 -I -c "import json,sys,subprocess,hashlib;m=json.load(sys.stdin)['source'];print(m['files'][0]['path'].split('/')[2],[hashlib.sha256(subprocess.run(['git','-C','/root/projects/PDF-proverka','show',m['commit']+':'+f['path']],check=True,capture_output=True).stdout).hexdigest()==f['sha256'] for f in m['files']],subprocess.run(['git','-C','/root/projects/PDF-proverka','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()==m['commit'],subprocess.run(['git','-C','/root/projects/PDF-proverka','status','--short'],capture_output=True,text=True).stdout=='')"; done`
- captured_output:
  ```text
  KM [True, True, True, True, True] True True
  OV [True, True, True, True, True] True True
  VK [True, True, True, True, True] True True
  PT [True, True, True, True, True] True True
  ```
- interpretation: per section: the five hashes agree (the list), the pinned commit is the legacy `HEAD` (first value after the list) and its working tree is clean (second value). The legacy repository was only read.

### P-03 — the gap report's rows «Reinstatable now» for the four sections (the second table of section 2.3)

- captured_at: 2026-10-27
- command: `grep -n -E '^\| (KM|OV|VK|PT) \| (a total mass|a system|the building|the same quantity)' docs/program/ROADMAP-GAP-2026-10-27.md`
- captured_output:
  ```text
  210:| KM | a total mass against the sum of marks (q3), conditional on a stated basis (with or without weld metal) | the 11 legacy categories (ex 11) | design scheme, strength, stability, deflection (ex 1, 3); suitability of steel grades, assembly order (ex 4); ГОСТ 27772, minimum weld leg, tolerances (ex 5); presence of end plates, washers, certificates (ex 6); the С345 and 09Г2С designations as one value (q1) | loads against АР, ОВиК, ТХ (ex 2) |
  211:| OV | a system's flow against the sum of its room flows; a heat-load total against its rows (q4) | the 11 legacy categories (ex 10); grille and diffuser positions, duct routes, lengths taken from plans (ex 6) | flow, power, velocity, pressure-loss formulas (ex 1); СП 60 air exchange and smoke-exhaust norms (ex 2); equipment against design loads, duct sections, tank volumes (ex 3); suitability of devices, redundancy (ex 4); presence of filters, dampers, valves, heat metering (ex 5); the fire-resistance of ducts by section (q3) | the electrical supply of units against ЭОМ (ex 8) |
  212:| VK | the building's total flow against the sum over systems (q4) | the 11 legacy categories (ex 7); riser topology and fittings from drawings (ex 5) | q = 5·q0·α, head losses, minimum free head (ex 1); meter size and diameters against flow (ex 2); hot water ≥ 60 °C, slopes, access eyes, vent stack height (ex 3); required filters, valves, pump redundancy, traps (ex 4); ГОСТ references (ex 6) | internal fire water «in coordination with ПТ» (ex 8) |
  213:| PT | the same quantity in different units (л/с and м³/ч, metres and MPa; q2); design flow as jets times single-jet flow, and the total of ВПВ and АУПТ (q4) | the 10 legacy categories (ex 11) | all formulas and limits of СП 10, СП 485 (ex 1–5); pump redundancy, power category, start logic (ex 6); reservoir volume and level devices (ex 7); network velocities, ring rule, steel grades (ex 8); pipe marks (ex 9); «required» flags (ex 10) | — |
  ```
- interpretation: this is the list of topics: КМ one (conditional on a stated basis), ОВ two, ВК one, ПТ two groups (units; the product and the sum). Metres against МПа is named by the report for ПТ and is decided N in the report because it is not one of the definitional factors of rule 4 of the brief.

### P-04 — the record's own questions behind those rows

- captured_at: 2026-10-27
- command: `grep -n -F -e 'Считать ли находкой расхождение общей массы' -e 'Считать ли находкой расхождение расхода системы с суммой' -e 'Считать ли находкой расхождение общего расхода здания' -e 'Подача насосов в пояснительной записке часто дана в л/с' -e 'Считать ли находкой расхождение расчётного расхода ВПВ' docs/program/W59-SECTION-PROFILES-01.md`
- captured_output:
  ```text
  502:- Считать ли находкой расхождение общей массы металлоконструкций в общих данных или строки «Итого» спецификации с суммой масс по маркам (сейчас пересчёт исключён), и как отличать массу по спецификации от массы с учётом наплавленного металла?
  552:- Считать ли находкой расхождение расхода системы с суммой расходов по помещениям в таблице воздухообмена или строки «Итого» таблицы тепловых нагрузок с суммой строк (сейчас пересчёт исключён)?
  599:- Считать ли находкой расхождение общего расхода здания с суммой расходов по системам или потребителям в таблице расчётных расходов (сейчас пересчёт исключён)?
  648:- Подача насосов в пояснительной записке часто дана в л/с, а в спецификации — в м³/ч, напор — в метрах, а давление — в МПа; считать ли «10 л/с» и «36 м³/ч» одним значением (это уже перевод единиц, то есть счёт) или сравнивать только значения в одинаковых единицах?
  650:- Считать ли находкой расхождение расчётного расхода ВПВ с произведением числа струй на расход одной струи или итоговой строки гидравлического расчёта с суммой расходов ВПВ и АУПТ (сейчас пересчёт исключён)?
  ```
- interpretation: five open questions of the W59 record ask exactly for these topics; the 1.1.0 lanes answered each K («пересчёт исключён»). `PRODUCTION-WAVE-PW4.md` section 6 reverses that for these topics only, under rules (1) to (6).

### P-05 — what the pinned legacy files say about the quantities (traceability of each topic)

- captured_at: 2026-10-27
- command: `cd /root/projects/PDF-proverka && for f in PT/checklist PT/project_params OV/project_params VK/project_params KM/checklist; do echo "== $f"; git show 16ba8e5d23e4782550e79355002fde1365f682b7:prompts/disciplines/$f.md | grep -n -E 'Расход ВПВ|Основной насос|fire_pump_main_flow_lps|vpv_flow_rate_lps|vpv_streams_count|total_supply_air_m3h|total_exhaust_air_m3h|Расходы приточного|Тепловые нагрузки|daily_water_demand_m3|Суммарный расход|Соответствие спецификации металла'; done`
- captured_output:
  ```text
  == PT/checklist
  2:- Расход ВПВ: Q = n × q (n — число струй, q — расход одной струи, л/с)
  44:- Основной насос: подача (м³/ч), напор (м), мощность двигателя
  == PT/project_params
  16:  "vpv_streams_count": 2,
  17:  "vpv_flow_rate_lps": 2.5,
  26:  "fire_pump_main_flow_lps": 0,
  43:| vpv_streams_count | Количество пожарных струй | 1, 2, 3, 4 |
  44:| vpv_flow_rate_lps | Расход одной струи, л/с | 2.5, 5.0 |
  53:| fire_pump_main_flow_lps | Подача основного пожарного насоса, л/с | 10, 20, 40 |
  == OV/project_params
  5:- Расходы приточного/вытяжного воздуха по помещениям
  6:- Тепловые нагрузки на отопление и вентиляцию
  17:  "total_supply_air_m3h": 0,
  18:  "total_exhaust_air_m3h": 0,
  32:| total_supply_air_m3h | Суммарный расход приточного воздуха, м3/ч | 15000 |
  33:| total_exhaust_air_m3h | Суммарный расход вытяжного воздуха, м3/ч | 14500 |
  == VK/project_params
  18:  "daily_water_demand_m3": 0,
  36:| daily_water_demand_m3 | Суточное водопотребление здания, м³/сут | 120 |
  == KM/checklist
  72:- Соответствие спецификации металла чертежам (марки, профили, массы)
  75:- Суммарный расход стали, сравнение с расчётом
  ```
- interpretation: ПТ: the source writes the pump flow in м³/ч (`checklist.md` line 44) and in л/с (`project_params.md` line 53) and gives `Q = n × q` with n the number of jets and q the flow of one jet (`checklist.md` line 2), so the unit equivalence and the product add no number the source lacks except the unit factor. ОВ: the source names flows by room and the building totals of supply and exhaust air. ВК: the daily consumption of the building (м³/сут). КМ: the masses of marks and «Суммарный расход стали». None of the files holds a rule for a basis, a tolerance or weld metal.

### P-06 — the existing recording pins that decide where the positive and negative recordings can live

- captured_at: 2026-10-27
- command: `grep -n -e 'iterdir()) == \[f' -e 'len(planned) == len(RECORDED_SECTIONS) == 14' tests/integration/sections/test_section_recordings.py`
- captured_output:
  ```text
  97:    assert sorted(item.name for item in directory.iterdir()) == [f"{request.request_sha256}.json"]
  156:    assert len(planned) == len(RECORDED_SECTIONS) == 14
  ```
- interpretation: `test_section_recordings.py` pins exactly one file in each `fixtures/recorded/sections/<code>/` (line 97) and exactly fourteen planned entries of `build_fixtures.py` (line 156), and the default `RecordedAdapter()` searches every directory there. A second and third recording per section in that directory would turn that suite red, and editing the suite or the builder is outside this lane's allowed paths. The coordinator confirmed after `SECTION-WIDEN-G1-01` that these two files are not to be edited and that the specimens go into the report for a later integrator lane. (The lane first built them as a sibling directory with its own builder and test, commit `b91e2022`, then removed them from the tip in `0690d6d5`.)

### P-07 — the token guard's pattern for the report that discloses an allowlist entry

- captured_at: 2026-10-27
- command: `git show 6075df88:tests/unit/analysis/text_profiles/test_prompt_token_guard.py | grep -n 'fullmatch(r"SECTION'`
- captured_output:
  ```text
  330:        assert re.fullmatch(r"SECTION-[A-Z]+-FULL-01\.md", entry["disclosed_by"]), identity
  ```
- interpretation: at the base the `disclosed_by` of every allowlist entry must match `SECTION-<LETTERS>-FULL-01.md`. The brief asks for the unit factor `3,6` to go into the allowlist with a reason, and this lane's report is its disclosure (`SECTION-WIDEN-G2-01.md`), which that pattern refuses. The coordinator ordered the identical one-line edit that is on `integration/ar-close-1026` (`fa7f2ae6`): `SECTION-(?:[A-Z]+-FULL|WIDEN-G[0-9]+)-01`. The lane makes that line and no other edit to the test; the file-exists and token-occurs checks beside it are unchanged.

### P-08 — the expectations lines of the four sections at the base

- captured_at: 2026-10-27
- command: `git show 6075df88:tests/unit/analysis/text_profiles/section_profile_expectations.json | grep -E '"code": "(KM|OV|VK|PT)"'`
- captured_output:
  ```text
      {"code": "KM", "status": "reviewed", "profile_version": "1.1.0"},
      {"code": "OV", "status": "reviewed", "profile_version": "1.1.0"},
      {"code": "VK", "status": "reviewed", "profile_version": "1.1.0"},
      {"code": "PT", "status": "reviewed", "profile_version": "1.1.0"},
  ```
- interpretation: the four lines read `reviewed` at `1.1.0`; the lane moves these four lines to `1.2.0` and no other line of the file.

### P-09 — the unit factor of the equality 1 л/с = 3,6 м³/ч

- captured_at: 2026-10-27
- command: `python3 -I -c "from fractions import Fraction;print(Fraction(3600,1000), float(Fraction(3600,1000)))"`
- captured_output:
  ```text
  18/5 3.6
  ```
- interpretation: one litre per second is 3600 litres per hour, that is 3600/1000 = 18/5 = 3,6 cubic metres per hour: a consequence of the definitions of the litre, the cubic metre, the second and the hour. The brief writes the first half of its rule inverted («1 м³/ч = 3.6 · 1 л/с»); its second half («1 л/с = 3.6 м³/ч») is the correct one and the only form the prompt uses.

### P-10 — the baseline test run before the first edit (captured at the base, not repeatable on the edited tree)

- captured_at: 2026-10-27
- command: `PYTHONPATH=src:/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages`
- captured_output:
  ```text
  ........................................................................ [ 22%]
  ........................................................................ [ 44%]
  ........................................................................ [ 67%]
  ........................................................................ [ 89%]
  ..................................                                       [100%]
  322 passed in 3.19s
  ```
- interpretation: 322 tests pass on the base before any edit; `df -h /` printed 1.8 GiB available, above the 1.2 GiB below which the stack's tests fail as `dependency_unavailable`.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

The earlier lane reports (`SECTION-<CODE>-FULL-01.md`), the ledger and the record in `W59-SECTION-PROFILES-01.md` are not edited; the lane's report states what it changes against each decision.

## Publication authority

- development_target: none
- origin_main_authority: none

Nothing is pushed or tagged by the lane; the integrator merges with `--no-ff` and publishes to `origin/dev` after its own acceptance.

## Allowed paths

- `src/auditmanager/analysis/text/profiles/km/**`
- `src/auditmanager/analysis/text/profiles/ov/**`
- `src/auditmanager/analysis/text/profiles/vk/**`
- `src/auditmanager/analysis/text/profiles/pt/**`
- `fixtures/recorded/sections/km/**`
- `fixtures/recorded/sections/ov/**`
- `fixtures/recorded/sections/vk/**`
- `fixtures/recorded/sections/pt/**`
- `tests/unit/analysis/text_profiles/section_profile_expectations.json`
- `tests/unit/analysis/text_profiles/prompt_token_allowlist.json`
- `docs/program/tasks/SECTION-WIDEN-G2-01.md`
- `docs/program/SECTION-WIDEN-G2-01.md`
- `tests/unit/analysis/text_profiles/test_prompt_token_guard.py`

The last path is **not** in the brief's list: it is the one-line edit of P-07, ordered by the coordinator and identical to the line on the integration branch; the report gives its before and after.

## Forbidden hotspots

- every other section's files and the files of groups `G1` and `G3`
- `docs/program/W59-SECTION-PROFILES-01.md`, `docs/program/SECTION-REVIEW-LEDGER-01.md`, the earlier `SECTION-<CODE>-FULL-01.md` reports, `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, the rulings
- the registry, `prompt.py`, `response.py`, `stage.py`, `fixtures/recorded/sections/build_fixtures.py`, `tests/integration/sections/test_section_recordings.py`, `P02_LOCK.json`
- `contracts/**`, `db/migrations/**`, the web, `infra/**`, root dependency/lock files, the composition root

## Non-goals

- A norm, a threshold, a class designation or a number outside the section's pinned legacy source; the only new numeral is the unit factor `3,6` (rule 4).
- A new category, field, severity or norm; `documentation`, a proposed severity, facets, OCR text, the omission pair and cross-volume checks stay owner choices (`D-236`).
- Any claim that an expert verified anything; the recordings are authored, not measured.
- Equivalence of `С345` and `09Г2С`, of `REI` and `EI`, of metres and МПа (rule 5 and the report); any omission check («named in one place, absent from another»), which the coordinator confirmed as X.
- A live model call, a measurement of what a model answers on these prompts, a change of the served adapter.

## Deliverables

- `system_prompt.md` and `profile.json` (version `1.2.0`, status `reviewed`) of `km`, `ov`, `vk`, `pt`; the four routing recordings rebuilt.
- In the report: eight synthetic specimens (a positive and a negative text per section, with the reply), their replay through the real stage, and the table of added fragments in machine-readable form with its check command. No fixture file and no test is filed for them (P-06).
- The four lines of `section_profile_expectations.json`; one appended entry of `prompt_token_allowlist.json` (`PT`, `3,6`); the one-line edit of the `disclosed_by` pattern in `test_prompt_token_guard.py`.
- This task file and `docs/program/SECTION-WIDEN-G2-01.md` (decisions table, prompt diffs in words, added fragments verbatim, assumptions, token-guard additions, mutation table, counts, proof of untouched paths).

## Required tests

- command: `pytest tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages`
- expected: all pass; counts in the report
- command: `python3 -I fixtures/recorded/sections/build_fixtures.py --check` (with `PYTHONPATH=src`), run last
- expected: `fixtures match`
- command: `pytest tests/integration/composition/test_analysis_profiles_over_http.py` on the integrator's lane stack, once; `npx vitest run tests/unit/analysis-settings` in `web/`
- expected: 4 passed; 96 passed
- command: `pytest tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` on the committed tree, then `git diff --check`
- expected: all pass; no output

## Integration contract

The integrator can rely on: the four expectations lines read `1.2.0`; merge conflicts, if any, are only in `section_profile_expectations.json` (regenerate the four lines from each `profile.json`), `prompt_token_allowlist.json` (append-only: keep every group's entries) and the one `disclosed_by` line of `test_prompt_token_guard.py` (identical to the line on the integration branch, so it merges cleanly). The positive and negative specimens are not filed; the report holds them for a later integrator lane. After the merge, `fixtures/recorded/sections/build_fixtures.py --check` must still print `fixtures match` and the section replay suite must still hold one file per section directory.

## Failure/idempotency/security cases

- A prompt edit without a rebuild turns the builder's `--check` and `test_section_recordings.py` red (mutations M3, M5).
- A prompt edit with a consistent rebuild is caught only by the report's fragment check (M3c) until `SECTION-PROMPT-SENTENCE-GUARD-01` reads the table; that is the `D-224` residual, narrowed to a documented table.
- A numeral or class designation not in the pinned source, `v1` or the allowlist turns the token guard red (M14); removing the allowlist entry does (M4).
- The specimens carry no provider mode, no credential and no client text (the invented texts are fictional).

## Rollback / feature flag

Not applicable: the change is data in a package (`profile_version` `1.2.0`). To undo it, revert the lane's commits (the packages return to `1.1.0` and their recordings with them). There is no flag.

## Handoff

- changed files: see the report, section «Files»
- commands/results: see the report, section «Commands and counts»
- known limits: see the report, sections «Assumptions an expert would still check» and «Limits»
- integration notes: see the report, section «Integration notes»
