# SECTION-ITP-FULL-01 — the ИТП (ITP) profile answers its open questions and is `reviewed`, without a human review

Task: `docs/program/tasks/SECTION-ITP-FULL-01.md`. Branch `agent/section-itp-full-01`, base `23e30b4c17a3c930469f3f94733c6d8c16eff1ed` (`integration/ar-close-1026`, with `AI`, `PS`, `POS`, `TX`, `KJ`, `KM`, `OV`, `VK` and `GP` already `reviewed`), product commit `521cd0ad`. Plan item `PROD-14` (section `ITP`); owner rulings `R-146ag`, `R-146ah`, `R-146ai`; accepted risk `A-7`; template `SECTION-<CODE>-FULL-01` of `dispatch/PRODUCTION-WAVE-PW2B.md`. Executor: a Sonnet lane. No push, no tag, no container command, no model call, no process killed.

**Read this first (`A-7`).** Nobody reviewed this section: not an expert, not the owner. The status `reviewed` on the ITP profile means a lane wrote a decision for every open question of its record and rebuilt its recording. It is **not** expert verification and must not be quoted as one.

## Result

The `ITP` record in `W59-SECTION-PROFILES-01.md` has five open questions and the four cross-section questions. Each has one written decision: **N** for question 1 (one sentence in one hint bullet), **K** for questions 2, 3, 4 and 5 and for cross-section 1 to 4; **X** never. One more edit comes from the designation audit that the template does not name: the symbol `Kv`, which the pinned source lacks, is removed from the condition 2 example (the words stay). `profile_version` is `1.1.0`, `status` is `reviewed` in `profile.json` and in the `ITP` line of the expectations file, and the recording is rebuilt by `build_fixtures.py`.

Premise: **match.** The package, the five open questions, the four cross-section questions, the legacy repository at `16ba8e5d…` with all five hashes equal to `itp/profile.json`, the `ITP` expectations line and a green baseline (211, 4 and 95 passed, `fixtures match`) were as the brief says (task file, P-01 to P-06). Unlike `VK` and `OV`, the audit (P-07) finds no digit-bearing token and no class designation or system mark that the source lacks; its only finding is the mixed-case symbol `Kv` (P-08), which the audit script of the earlier lanes cannot see.

## Decisions

Quoted question openings are the record's own words. «Condition n» means v1's numbered conditions in the prompt; «bullet n» counts the hint bullets from the top of the block «Где в документе раздела ИТП искать …» (1 connection and DHW scheme, 2 heat loads, 3 temperature graphs and pressures, 4 heat exchanger, 5 pump, 6 control valve, 7 setpoints, 8 metering unit, 9 pipeline and valves, 10 quantities, 11 placeholders).

| # | Question (record, shortened) | Decision | Reason | Exact change |
|---|---|---|---|---|
| ITP-1 | Loads written in «Гкал/ч» in one place and in «кВт» or «МВт» in another: are values that coincide after conversion consistent, and does rounding at conversion give false findings? | **N** (bullet 2 only) | A stated false-positive source: the record names the rounding at a conversion. The prompt cannot decide whether two values coincide after conversion without converting, and converting is arithmetic that the exclusion paragraph keeps out («НЕ выполняешь и не перепроверяешь инженерные расчёты»). The source holds no conversion factor and names no unit of heat load other than kW (P-04), so the lane may not supply one. The only narrowing that adds nothing is to stop comparing values of one load across different units: such a pair is not reported as a contradiction. The sentence adds no unit name, number, factor or norm. Values in one and the same unit are compared as before. What it costs: a pair that disagrees beyond any rounding but is written in two units is no longer reported either (assumption 1). | the heat-load bullet gets one sentence (below) |
| ITP-2 | «150/70 со срезкой на 130 °C» in one place, «130/70» in another: a contradiction or one graph written two ways? | **K** | Whether the two notations are one graph is a domain equivalence (the nominal graph against the value after the cut-off) that no source file states: «срезка» occurs in none of the five files and «150/70» in none, while «130/70» occurs only as an example value in `project_params.md` (P-04). A sentence that declared the two equivalent would bring a rule from outside the source and silence the one pair the question fears. Under v1 both quotes are shown to the reviewer, who decides; condition 2 already requires «буквально одна и та же характеристика». The record states a doubt, not a measured rate, and there is no field case (`A-5`). | none |
| ITP-3 | The selected product in the specification against the requested values in a questionnaire or calculation table: is a finding ever needed? | **K** | A finding on the selected rating against the required value is a comparison with a calculation and a judgement of the solution. The record excludes exactly that from the same checklist sections (heat exchanger: «соответствие мощности расчётным тепловым нагрузкам»; pumps: «соответствие расхода и напора расчётным значениям»; valves: «Kvs — соответствие расчётному расходу») and the `hydraulic_scheme` sheet type of the source, which holds the design flows and losses, is deliberately not a place of comparison. A new finding kind would also be widening. Condition 2 already names one such pair for the exchanger («расчётная тепловая нагрузка контура и номинальная мощность теплообменника»). The gap this leaves is stated under assumptions 3. | none |
| ITP-4 | «подбор оборудования уточнить после получения ТУ», «марку теплосчётчика согласовать с теплоснабжающей организацией», «уставки уточнить при пусконаладке»: placeholder or accepted instruction? | **K** | Cross-section rule 1. «Уточнить» in the first and third is a literal mark of v1's second category, forgiven by condition 4 only for a reference to a table, schedule, specification, sheet, section or volume where the value is given. «После получения ТУ» names a document of the heat-supplying organisation, which the source itself treats as outside this document («Технические условия теплоснабжающей организации»), and «при пусконаладке» names a later event; neither is on the list. Turning them into accepted instructions is an expert's call and would silence findings. The second phrase has none of v1's literal marks («уточнить», «уточняется», «TBD», «XX», «___», «(?)»); whether «и подобное» reaches «согласовать» is left to the model's reading of v1's definition. The lane did not add «согласовать» to the marks (that widens the category) and did not exclude it. | none |
| ITP-5 | «Итого» of heat loads against the sum of the loads by circuit: a finding? | **K** | Cross-section rule 2. Adding up the circuits is arithmetic recomputation, excluded by the exclusion paragraph and by the record. Bullet 2 compares the total «как они записаны» in four places and sums nothing; two totals written in the text that differ stay an `internal_contradiction` under v1, a total against its rows does not. The source never says «Итого» (P-04): the total is a parameter (`heat_load_total_kW`), not a checked sum. | none |
| A-1 | Audit (not a record question): numerals, class designations and symbols of the prompt against the pinned source | **N** (edit by the audit rule, no stated false-positive source) | The prompt has no digit-bearing token and no capital-letter designation that the source lacks (P-07). One mixed-case symbol is absent from the source as a whole word: `Kv` in the condition 2 example (P-08). It is neither a digit, a norm reference nor a class designation, so the brief's rule does not oblige a removal; the lane removes it anyway, because the source writes only `Kvs` and the rule is that a notation absent from the source does not stay. The words of the example stay, so what condition 2 excludes (a rating against a calculated capacity is not one attribute) is unchanged. | `Kv` removed (below) |

Cross-section decisions (the same for every lane; this lane agrees with the table and has nothing to report against it):

| # | Question | Decision | ITP-specific note |
|---|---|---|---|
| C1 | Site and contractor phrases | **K** | Covers ITP-4. |
| C2 | «Итого» against the sum of rows | **K** | Covers ITP-5. The prompt has no bullet that recomputes a total. |
| C3 | Text read from sheets | **K** | The ITP record names no bullet whose false findings come from detached sheet text. The bullets read the schemes, the tables and the specification by name («на принципиальной схеме», «на функциональной схеме автоматизации», «на схеме узла учёта»); none uses the phrase «подписи». |
| C4 | Missing items | **K** | No third kind of observation; condition 5 stays; the record's excluded list (all circuits present, check valves, mud filters, safety valves, controller, sensors, sealed sections, drainage, power supply category and the like) stays excluded. |

Places by sheet type of `drawing_types.md` and bullet of the prompt (the record asks no question about the completeness of the list, so this table is for traceability only and changes nothing):

| Sheet type | Bullet(s) |
|---|---|
| `principal_scheme` | 1, 2, 3, 4, 5, 6, 9; 10 as «текст схем» |
| `axonometric` | 9 |
| `automation_scheme` | 3, 6, 7 |
| `metering_scheme` | 8 |
| `electrical_scheme` | 5 |
| `specification` | 4, 5, 6, 8, 9, 10, 11 |
| `general_notes` (general data, explanatory note, general instructions) | 1, 2, 3, 7, 8, 9, 10 |
| `itp_layout`, `hydraulic_scheme`, `section`, `piping_detail`, `title_block`, `other` | none dedicated: layout and sections are read from graphics (excluded in the record), the hydraulic scheme holds design values (ITP-3), the rest carry no attribute values to compare |

## The prompt change in words

`git diff 23e30b4c HEAD -- src/auditmanager/analysis/text/profiles/itp/system_prompt.md`: 4 lines added and 2 removed (the numstat of the whole branch is in the path proof below). The opening, the question, the two categories, the five conditions except the example in condition 2, the exclusion paragraph and the output contract are byte for byte as before; the package tests hold them.

1. **Heat-load bullet (ITP-1).** After «… в таблице тепловых нагрузок и на принципиальной схеме» the bullet now continues: «значения одной нагрузки, записанные в разных единицах измерения, между собой не сравнивай: пересчёт единиц и округление при нём — вычисление, которого ты не выполняешь;». The list of places and of loads (отопление, вентиляция, ГВС, суммарная нагрузка) is unchanged.
2. **Condition 2 (A-1).** «расчётная пропускная способность Kv.» becomes «расчётная пропускная способность.». The other two near-miss pairs (maximum and hourly-average DHW load; design circuit load and nominal exchanger power) and the first half of the pair (`Kvs`, which the source contains) are unchanged.

`profile.json`: `status` `draft` to `reviewed`, `profile_version` `1.0.0` to `1.1.0` (the prompt text changed). Identities unchanged; the recording's `prompt_bundle_sha256` moved `6f146314…b7dd` to `352c5a07…6bfb`.

New numerals: none. New norm references: none. New class designations: none (one symbol removed). New unit names or conversion factors: none. Findings: only narrower than before. The one caveat the lane states plainly: the sentence also silences a real mismatch that happens to be written in two units (assumption 1), and nothing measures how often that occurs.

## Audit of numerals, designations and symbols

Two passes, both run before the edit (task file P-07, P-08) and after it. The first is the script of the earlier lanes (numerals and capital-letter designations); it cannot see a mixed-case symbol, so a second pass over every whole Latin word was added. After the edit the prompt has no digit-bearing token at all; every capital-letter token is in the source (`PN`, `ГВС`, `ГОСТ`, `И`, `ИТП`, `СП`) or is v1's own word or marker (`TBD`, `XX`, and the upper-case emphasis fragments `ЖЕ`, `НЕ`, `ТОГО`, `ТОМ`); every Latin word is `Kvs` and `PN` (in the source), `TBD` and `XX` (v1's markers) or a v1 output-contract field name (`category`, `evidence`, `finding`, `quote`, `observations`, …). Putting a designation in makes the first script print `False` for it (A2, A3 below); putting `Kv` back makes the second print `False` for `'Kv'` (A1). Both scripts live outside the repository; this is their exact text.

```python
"""Audit: every digit-bearing token and capital-letter class designation in a section prompt
must occur in the section's five hash-pinned legacy files (read at the pinned commit)."""
import json, re, subprocess, sys
from pathlib import Path

root = Path(sys.argv[1])           # worktree
code = sys.argv[2]                 # e.g. ITP
prompt = (root / f"src/auditmanager/analysis/text/profiles/{code.lower()}/system_prompt.md").read_text("utf-8")
manifest = json.loads((root / f"src/auditmanager/analysis/text/profiles/{code.lower()}/profile.json").read_text("utf-8"))
legacy = Path("/root/projects/PDF-proverka")
src = ""
for f in manifest["source"]["files"]:
    src += subprocess.run(["git", "-C", str(legacy), "show", f"{manifest['source']['commit']}:{f['path']}"],
                          check=True, capture_output=True).stdout.decode("utf-8") + "\n"
body = re.sub(r"(?m)^\s*[1-5]\. ", "", prompt)
digit_tokens = sorted(set(re.findall(r"[A-Za-zА-ЯЁа-яё]*\d[\d,–\-]*[A-Za-zА-ЯЁа-яё\d]*", body)))
designations = sorted(set(re.findall(r"\b[А-ЯA-Z]{1,4}\d?[\d,]*(?:[–\-][А-ЯA-Z]{0,4}\d+)?\b", body)))
print("prompt:", code, "digit-bearing tokens:", digit_tokens)
for t in digit_tokens:
    print(f"  {t!r:16} in legacy source: {t in src}")
print("capital designations:", designations)
for t in designations:
    print(f"  {t!r:16} in legacy source: {t in src}")
```

```python
"""Supplementary audit: every whole Latin word of the prompt against the five pinned legacy files.
Usage: latin_audit.py <prompt-file> <profile.json>"""
import json, re, subprocess, sys
from pathlib import Path
prompt = Path(sys.argv[1]).read_text("utf-8")
m = json.loads(Path(sys.argv[2]).read_text("utf-8"))
src = ""
for f in m["source"]["files"]:
    src += subprocess.run(["git", "-C", "/root/projects/PDF-proverka", "show", f"{m['source']['commit']}:{f['path']}"],
                          check=True, capture_output=True).stdout.decode("utf-8") + "\n"
for t in sorted(set(re.findall(r"[A-Za-z]+", prompt))):
    w = bool(re.search(r"(?<![A-Za-z])" + re.escape(t) + r"(?![A-Za-z])", src))
    print(f"  {t!r:18} whole word in legacy source: {w}")
```

**Notations and words that stay although the source lacks them (disclosed, not removed).** The audits cover numerals, class designations and symbols. Plain words are a separate matter: removing them would change what a bullet asks with no stated false-positive source. The base prompt's condition 2 names «максимальная и среднечасовая тепловая нагрузка на ГВС» and «пропускная способность» (none of «максималь», «среднечас», «пропускн» is in the source); bullets 4 and 11 name «опросный лист» and bullets 7 and 11 «уставки» (the source writes neither); condition 1 names «ступеням подогрева ГВС» («подогрев» is not in the source); the exclusion paragraph names «СНиП» (v1's own list, the source has «СП» and «ГОСТ» only). The words this lane adds — «единицах измерения», «пересчёт», «округление» — are likewise not in the source (P-04). None is a number, a norm reference, a threshold or a class designation. No digit-bearing token is kept.

## Assumptions an expert would still want to check

Short and honest (`A-7`): none of these was checked by anyone with domain knowledge.

1. **ITP-1 (N).** A load written in kW in one place and in another unit elsewhere is no longer compared, so a real mismatch hiding in such a pair is missed; the lane did not say which units count as «разные» (a model decides, so kW against MW may or may not be treated as different). Two values in the same unit still differ as before, including a difference that is only rounding in that unit. The lane did not give the conversion and did not say that values which coincide after conversion are consistent; it only stopped comparing them.
2. **ITP-2 (K).** Whether a model reports «150/70 со срезкой на 130» against «130/70» is left to v1's wording and was not measured. If a document writes the cut-off next to the nominal graph, the model sees it; whether it then treats the second notation as the same graph is unknown.
3. **ITP-3 (K).** Bullet 4 names «таблица характеристик или опросный лист» among the places of the exchanger's thermal power, area and pressure loss, and no sentence says that a questionnaire holds requested values while the specification holds the selected ones. Condition 2 gives one pair (design load against nominal power). Whether a model carries that over to area, pressure loss, or to a pump's flow and head, is unmeasured, and a requested value that differs from the selected one may still be reported. The lane did not widen the prompt to settle this either way.
4. **ITP-4 (K).** «Согласовать с теплоснабжающей организацией» has none of v1's literal marks; whether it is read as a placeholder is the model's reading of «и подобное» and was not measured. «После получения ТУ» and «при пусконаладке» are placeholders under v1 only because of the word «уточнить».
5. **ITP-5 (K).** A total that disagrees with the sum of the circuits is still not reported, unless the document writes two incompatible totals itself.
6. **A-1 (N).** The example now reads «условная пропускная способность клапана Kvs и расчётная пропускная способность»; how a model reads it without the symbol was not measured. The plain word «расчётная» still carries the distinction from the rated `Kvs`.
7. **Nothing was measured.** The recording is synthetic, authored by hand over the AR corpus (its one reply is a contradiction about the fire-resistance degree of the building, pages 2 and 6, not anything about a heating point); it proves routing and replay and says nothing about how the profile performs on a real ИТП volume.

## Files changed

| File | Change |
|---|---|
| `src/auditmanager/analysis/text/profiles/itp/system_prompt.md` | the two edits above |
| `src/auditmanager/analysis/text/profiles/itp/profile.json` | `profile_version` `1.0.0` to `1.1.0`; `status` `draft` to `reviewed` |
| `fixtures/recorded/sections/itp/b9b9d6a8dc98d75291fd0ad13bf1d532204a25270691511d4e6522f61279953b.json` | rebuilt by `build_fixtures.py`; replaces `cc1fab2363e9a6700d8ca840c4362e85a226b1c86bd8c3e58d9a2cf34e08f57d.json`; the diff against the old file is exactly three lines: `origin.profile_status` (`reviewed`), `origin.prompt_bundle_sha256` and `request_sha256`; the authored reply, usage and latency are unchanged |
| `tests/unit/analysis/text_profiles/section_profile_expectations.json` | the `ITP` line only: `reviewed`, `1.1.0` |
| `docs/program/tasks/SECTION-ITP-FULL-01.md`, this report | records |

The builder writes all fourteen recordings; thirteen came out byte-identical (`git status` showed only the ITP directory).

## Before and after of modified tests

No test file is modified. The one data line that the tests read changed from `{"code": "ITP", "status": "draft", "profile_version": "1.0.0"}` to `{"code": "ITP", "status": "reviewed", "profile_version": "1.1.0"}`. Before, the pin tests (registry, package shape, the expectations guard, the HTTP list, the web fixture test) asserted that `profile.json` and the registry agree with the line (`draft`, `1.0.0`); after, they assert the same agreement with `reviewed`, `1.1.0`. Every assertion still compares the package with the line; nothing is weakened.

## Mutation table

Each row edits one thing in the committed tree (`521cd0ad`), runs the guard, restores with `git checkout HEAD --` (and removes a planted file), and proves the restore by a SHA-256 over the four product files (the driver printed `final digest equal: True` after every batch; `git status --short` shows no tracked change). «Set» is the 211-case set: `test_text_profile_registry.py`, `tests/unit/analysis/text_profiles`, `tests/integration/sections/test_section_recordings.py`, `tests/contract/analysis_packages`. The unmutated tree: `211 passed`. The driver is outside the repository.

| # | Mutation | Guard | Result when mutated |
|---|---|---|---|
| M1 | `profile.json` status `reviewed` back to `draft` (version kept) | set | `4 failed, 207 passed`: registry `test_the_tree_registers_without_error_and_without_an_ar_package`; `test_every_line_agrees_with_its_package_profile_json`; packages `test_every_profile_manifest_has_the_text_profile_1_shape`; recordings `test_the_builder_reports_no_drift` |
| M2 | `profile.json` version `1.1.0` back to `1.0.0` (status kept) | set | `3 failed, 208 passed` (the first three of M1) |
| M3 | the `ITP` expectations line back to `draft` / `1.0.0` (`profile.json` kept) | set | `3 failed, 208 passed` (the same three) |
| M4 | the `ITP` expectations line, status only back to `draft` | set | `3 failed, 208 passed` |
| M4b | the `ITP` expectations line, version only back to `1.0.0` | set | `3 failed, 208 passed` (the same three) |
| M5 | `system_prompt.md` back to the base text (recording kept) | set | `7 failed, 204 passed`: five recordings tests for `[ITP]` (keyed to its own request, served adapter, no other directory answers, filed under another key, replays through the stage) plus `test_the_builder_reports_no_drift` and `test_every_recording_carries_its_own_authored_usage_signature` |
| M6 | only the new units sentence removed | set | `7 failed, 204 passed` (the same seven) |
| M7 | only `Kv` put back in condition 2 | set | `7 failed, 204 passed` (the same seven) |
| M7d | one comma added inside the new sentence | set | `7 failed, 204 passed` (the same seven) |
| M8 | the recording back to the base file (new one removed) | set | `7 failed, 204 passed` (the same seven) |
| M9 | `origin.profile_status` `reviewed` to `draft` inside the new recording (key kept) | set | `1 failed, 210 passed`: `test_the_builder_reports_no_drift` |
| M9b | `system_prompt.md` back to the base text | `build_fixtures.py --check` | rc 1: the old key listed as the file the script would write, the new one `(stale)` |
| M10 | the `ITP` expectations line back to `draft` / `1.0.0`, on the lane stack | `test_analysis_profiles_over_http.py` | `1 failed, 3 passed`: `test_every_row_is_the_registry_entry_the_application_routes_by` |
| M11 | the same, in the web test | `npx vitest run tests/unit/analysis-settings` | `1 failed, 94 passed`: `has a line for exactly the packages that exist, with the status and version each declares` |
| M12 | `profile.json` status `draft` (version kept), on the lane stack | HTTP test | `1 failed, 3 passed` (as M10) |
| M13 | `profile.json` status `draft` (version kept) | web test | `1 failed, 94 passed` (as M11) |
| A0 | the committed tree | the first audit script | prints `False` only for `TBD`, `XX`, `ЖЕ`, `НЕ`, `ТОГО`, `ТОМ` (v1's markers and emphasis fragments) |
| A1 | `Kv` put back, on a scratch copy of the prompt | the second (Latin) audit script | prints `'Kv' whole word in legacy source: False`; the committed prompt prints no line for `Kv`. The first script prints nothing new for it (it matches capital-letter tokens only; see the limit below) |
| A2 | the designation `Т3` inserted into condition 2 | the first audit script | prints `False` for `'Т3'` |
| A3 | the designation `ТП-2` inserted after «схема присоединения к тепловой сети» | the first audit script | prints `False` for `'ТП-2'` |

After the last restore the guards were green again (`211 passed`; HTTP `4 passed`; web `95 passed`; `fixtures match`).

**What the table says about the new wording.** No test reads the added sentence or the removed symbol; their only guard is the recording key, which is the digest of the exact prompt bytes, so any change to the wording is red until the recording is rebuilt (M5 to M8). The reverse also holds: a rebuilt recording over a changed prompt would pass, and so would a prompt that gets a designation back together with a rebuilt recording (only the manual audit would show it). A test that pins the edits by content, or the audit as a repository guard, needs a file outside this lane's allowed paths and is not written.

## Commands and results

From `/root/projects/PDF-Analysis/.local/worktrees/section-itp-full-01`, shared venv, one pytest at a time, `PYTHONDONTWRITEBYTECODE=1`, `$BS` = `/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages`. Results are read from the pytest output, not from a pipe.

| Command | Base `23e30b4c` | After the change |
|---|---|---|
| section set (above) | `211 passed` | `211 passed` |
| the same, after the prompt, profile and expectations edit and before the rebuild | not run | `7 failed, 204 passed` (the seven recording tests); `--check` rc 1 |
| `build_fixtures.py --check` | `fixtures match` | `fixtures match` (rc 0) after the rebuild |
| `tests/integration/composition/test_analysis_profiles_over_http.py`, lane `.env` exported | `4 passed` | `4 passed` |
| `npx vitest run tests/unit/analysis-settings` in `web/` (`node_modules` linked from `gate-night`, untracked) | `7 files, 95 passed` | `7 files, 95 passed` |
| governance one-liner on the task file | not run | `[]` |

The final contract run, `git diff --check` and the path proof are under «Final checks» below.

Free disk (`df -h /`): 1.8 GiB at the start and at the end. No docker command, no push, no model call, no process killed.

## Integration notes

1. **The web label for `reviewed`** was a false statement under `A-7` («проверен экспертом»); it is already changed on this base by `607ee47a` (an ancestor of the base). This lane touches no web file.
2. **Identity:** `analysis_profile_id` and `prompt_bundle_id` are unchanged, while the bundle's text and hash changed and the profile hash changed with the version. A stored run of the draft ITP profile carries the old `analysis_profile_sha256` and `prompt_bundle_sha256`; the registry resolves by the id pair and serves only the new text. Development stand only, no migration (`R-146ah`).
3. **The recording's `origin`** still names `SECTION-RECORDINGS-01` as its authoring task and now says `profile_status: reviewed`; its statement still says «Not field evidence for the profile's review». The builder was not touched.
4. **e2e manifest:** the step with the selector `tr[data-profile="draft"]` (named in `PROD-14-0-EXPECTATIONS-01.md`) stays valid while any section is `draft`. On this base after this lane `PT`, `EOM`, `SS` and `PB` are `draft`; `PB` is expected to stay so, but the integrator should check after the last merge that at least one row is still `draft`.
5. **Merge:** the expectations file changes on the `ITP` line only, so lanes merge without conflict. If another lane's merge changes `build_fixtures.py` output, re-run `build_fixtures.py --check`, the section set, the HTTP test and the web test after the last section merges.
6. **Record:** `W59-SECTION-PROFILES-01.md` still says every profile is `draft` and lists the five ITP questions as open. It is a forbidden path for the lane; the integrator should point it at this report without calling the status an expert review.
7. **Other sections:** a read-only run of both audit scripts on the base prompts of the other draft sections (nothing was edited there) printed `False` for these tokens only: `EOM` the conjunction `И`; `SS` the Latin word `LS`; `PT` nothing; `PB` has no legacy source. Whether `LS` is a real finding is for the `SS` lane.
8. **Judge:** read the decisions table against the five legacy files named in P-03 and P-04, not against this lane's summary.

## Limits

- No expert or owner reviewed any decision (`A-7`); no field case (`A-5`); the recording is synthetic.
- No test holds the prompt edits by content; the audit scripts are run by hand and are not a repository guard. A cross-section guard that checks each prompt's numerals, designations and Latin symbols against its pinned source would be a candidate for the integrator. The first audit script cannot see a mixed-case symbol such as `Kv`; the second pass exists for that and is equally manual.
- The effect of the edits on a model's answers is unmeasured; no model was called.
- The plain words listed under the audit stay although the source lacks them.
- The lane decided nothing about what counts as a different unit, about the equivalence of a cut-off graph and a nominal one, or about requested against selected values (assumptions 1 to 3).

## Forbidden paths untouched

`git diff --name-only --no-renames 23e30b4c17a3c930469f3f94733c6d8c16eff1ed..HEAD` on the tip of the branch prints exactly these seven paths, all inside the task's allowed paths (without `--no-renames` git folds the old recording into a rename and prints six):

```text
docs/program/SECTION-ITP-FULL-01.md
docs/program/tasks/SECTION-ITP-FULL-01.md
fixtures/recorded/sections/itp/b9b9d6a8dc98d75291fd0ad13bf1d532204a25270691511d4e6522f61279953b.json
fixtures/recorded/sections/itp/cc1fab2363e9a6700d8ca840c4362e85a226b1c86bd8c3e58d9a2cf34e08f57d.json
src/auditmanager/analysis/text/profiles/itp/profile.json
src/auditmanager/analysis/text/profiles/itp/system_prompt.md
tests/unit/analysis/text_profiles/section_profile_expectations.json
```

No other section's files, no `W59-SECTION-PROFILES-01.md`, registry, `P02_LOCK.json`, `contracts/**`, migration, `web/**`, `infra/**` or test file appears; `build_fixtures.py` is unchanged. The legacy repository was only read (`git -C /root/projects/PDF-proverka status --short | wc -l` prints `0` before and after).

## Final checks

See the commit that follows this one: it records the results of the contract run, `git diff --check` and the path proof on the committed tree.
