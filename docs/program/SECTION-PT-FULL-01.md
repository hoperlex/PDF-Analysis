# SECTION-PT-FULL-01 — the ПТ (PT) profile answers its open questions and is `reviewed`, without a human review

Task: `docs/program/tasks/SECTION-PT-FULL-01.md`. Branch `agent/section-pt-full-01`, base `ae751f23` (`integration/ar-close-1026`, with `AI`, `PS`, `POS`, `TX`, `KJ`, `KM` and `GP` already `reviewed`), product commit `b71a7ec5`. Plan item `PROD-14` (section `PT`); owner rulings `R-146ag`, `R-146ah`, `R-146ai`; accepted risk `A-7`; template `SECTION-<CODE>-FULL-01` of `dispatch/PRODUCTION-WAVE-PW2B.md`. Executor: a Sonnet lane. No push, no tag, no container command, no model call, no process killed.

**Read this first (`A-7`).** Nobody reviewed this section: not an expert, not the owner. The status `reviewed` on the PT profile means a lane wrote a decision for every open question of its record and rebuilt its recording. It is **not** expert verification and must not be quoted as one. Nothing was measured on real text.

## Result

The `PT` record in `W59-SECTION-PROFILES-01.md` has five open questions; the fourth and the fifth each ask two things, so there are seven decisions: **K** six times and **N** once (question 3). The four cross-section questions are applied as the wave table fixes them (all **K**). No **X**. The N decision is one sentence appended to the second hint bullet of `system_prompt.md` (the head and pressure bullet); nothing else in the prompt moved. The prompt changed, so `profile_version` is `1.1.0`, the recording is rebuilt, and `profile.json` and the `PT` line of the expectations file say `reviewed`.

Premise: **match.** The package, its status and version, the five source hashes at the pinned commit, the five questions, the four cross-section questions, the expectations line, the one recording and a green baseline (211 passed, `fixtures match`) were as the brief says (task file, P-01 to P-08). The audit of numerals and class designations (P-09) is clean for `PT`: the prompt has no digit-bearing token and no class designation, so nothing had to be removed. Two premise details the record does not flag: question 1 quotes «ТУ» and the source never uses that word, and question 3 speaks of «зонам» and a «диктующего крана», while the source has no word «зона» and names a dictating *sprinkler* only (P-11). No decision writes any of them into the prompt as a rule.

## Decisions

Quoted question openings are the record's own words. «Condition n» means v1's numbered conditions in the prompt; «bullet n» counts the bullets of the hint block from the top (the list is under «Places of question 5a» below).

| # | Question (record, shortened) | Decision | Reason | Exact change |
|---|---|---|---|---|
| 1 | «гарантированный напор уточнить по ТУ», «марку насосной установки уточнить при заказе», «длину рукава уточнить по месту»: a placeholder (as v1) or a reference to the technical conditions and an accepted instruction to the supplier and the installer? | **K** | Cross-section decision (1) applies to the whole question. Each phrase carries the literal «уточнить», so under v1 it is an explicit placeholder unless condition 4 applies, and condition 4 forgives only a reference to a table, schedule, specification, sheet, section or volume where the value is given. The technical conditions are not on that list (and «ТУ» is in none of the five pinned files); «при заказе» defers to the supplier and «по месту» to the installer, and the profile sees only this document's text, so it cannot tell whether the value is filed anywhere. Making the three phrases accepted instructions is an expert's call and would silence findings. | none |
| 2 | Pump flow in л/с in the note and in м³/ч in the specification, head in metres and pressure in МПа: are «10 л/с» and «36 м³/ч» one value (a unit conversion, that is counting), or are only values in the same units compared? | **K** | The first alternative needs a conversion, which the record itself calls counting; the profile excludes calculation («НЕ выполняешь и не перепроверяешь инженерные расчёты», «Сравниваются только значения, прямо записанные в тексте»), and the source holds **no conversion rule and no factor** (the pump flow is written in м³/ч at `checklist.md` line 44 and in л/с at `project_params.md` line 53, the head in metres, the pressure in МПа; P-11). A factor would be a number the source lacks, which the brief forbids. The second alternative would be a new sentence «values in different units are not compared»: the record gives no false finding that this prevents, only a doubt (no field case, `A-5`), and the sentence would also silence a real conflict between two writings of one pump's flow in different units, which is a cost an expert pays more dearly than a rejected finding. Condition 2 already requires «буквально одна и та же характеристика». What a model does with two units is therefore left to v1 and is listed under assumptions. | none |
| 3 | The head and pressure at fire cocks legitimately differ by floor and zone (with and without diaphragms): does the bullet on the head at the dictating cock give false findings when the zone or floor is not named? | **N** (this bullet only) | A stated false-positive source, and the record names the bullet. Condition 1 lists «этажам, зонам … пожарным кранам» among the different objects and ends with «Ищи в тексте прямое указание на то, к чему относится значение», but nothing says what to do when the text gives none; and the bullet compares three places with only «диктующего пожарного крана или оросителя одной и той же системы или зоны». The sentence adds a condition before a comparison: a head or pressure at a fire cock is compared with another value only if the text directly puts both values at one and the same cock, in one and the same zone, or on one and the same floor. It removes comparisons only; it adds no number, norm reference or designation, writes no rule of how a head differs by floor or zone (the source holds none; its only remark is the diaphragm in the pressure limit at `checklist.md` line 15), and covers fire cocks only, because the record names them. Two values that both name the dictating cock, or the same zone or floor, are compared as before. | one sentence appended to hint bullet 2, see below |
| 4a | A design flow of the ВПВ against the product of the number of jets and the single-jet flow: a finding? | **K** | Cross-section decision (2). The product is an arithmetic recomputation; the formula `Q = n × q` stands in the source under «Расчётные формулы для сверки» (`checklist.md` lines 1 and 2), which the record excludes as engineering calculation, and condition 2 already lists «расход одной пожарной струи и расчётный расход внутреннего противопожарного водопровода» as two different characteristics. Bullet 1 compares the written number of jets, the written single-jet flow and the written design flow between places and multiplies nothing. Two design flows that are both written and differ stay an `internal_contradiction` under v1; only the multiplication stays out. | none |
| 4b | The total line of the hydraulic calculation against the sum of the ВПВ and АУПТ flows: a finding? | **K** | Cross-section decision (2). Adding the flows of two systems is arithmetic and the exclusion paragraph keeps recomputation out; condition 1 also names «системам, установкам» as different objects, so a flow of the ВПВ and a flow of an АУПТ are not one characteristic. No bullet compares a total with its parts; the bullet on written design flows compares each written value across places. The source's wording «Противоречия между гидравлическим расчётом и принятыми решениями» (`project_params.md` line 9) was kept in the record as a comparison of written values without recomputation. | none |
| 5a | Is the list of places complete for a ПТ set in which the ВПВ and the АУПТ are issued in one volume? | **K** | The list is a hint, not a list of required findings; a place absent from a set yields nothing under condition 5 («Утверждения просто нет … это не находка»). Every sheet type of `drawing_types.md` that carries attribute values maps onto a bullet (table below). The plans (`fire_water_plan`, `sprinkler_plan`, `drench_plan`) have no dedicated place on purpose: counts and lengths taken off a plan are conclusions from graphics, which the record excludes («метражи и количество пожарных кранов и оросителей, снятые с планов»). One volume for both systems is the case the profile reads: it reads one document, and the ВПВ and АУПТ bullets are separate. Adding places is widening. | none |
| 5b | Does the model confuse systems with similar parameters (the ВПВ of the residential part and of the parking, sprinkler sections of different floors)? | **K** | A doubt, not a stated false-positive bullet, and no field case (`A-5`). Both examples are objects that condition 1 names («системам», «зонам», «секциям», «этажам», «пожарным отсекам»), and the bullets carry the qualifier of the object each time: «одной и той же системы или зоны» (bullet 2), «одного и того же защищаемого помещения или завесы» (3), «одного и того же помещения или секции» (6), «одной и той же секции» (7), «одного и того же расчётного участка или одной и той же сети» (8). Naming the residential part and the parking would add vocabulary the profile does not need to keep objects apart. | none |
| A-1 | Audit (not a record question): numerals and class designations of the prompt against the pinned source | **K** | Clean: the prompt has no digit-bearing token and no class designation (P-09). Nothing was kept that the source lacks as a notation. | none |

Cross-section decisions (the same for every lane; this lane agrees with them and has nothing to report against them):

| # | Question | Decision | PT-specific note |
|---|---|---|---|
| C1 | Site and contractor phrases | **K** | Covers question 1. |
| C2 | «Итого» against the sum of rows | **K** | Covers questions 4a and 4b: the prompt has no recomputation bullet. |
| C3 | Text read from sheets | **K** | The record names no bullet whose false findings come from detached sheet text. The two bullets that read labels («в подписях на расчётной схеме», bullet 8; «в подписях расходов и напоров на схемах», bullet 11) keep their words. Question 3 is about the identity of the object a value belongs to (which cock, zone or floor), not about detached text, and is decided on its own. |
| C4 | Missing items | **K** | Condition 5 stays; the record's excluded list (what must be present: reserve pump, jockey pump, start automation, level gauges and the like) stays excluded. |

Places of question 5a, by sheet type of `drawing_types.md` and bullet of the hint block (bullets: 1 jets, flows and operating time of the ВПВ; 2 the guaranteed head in the external network, the required head and the head (pressure) at the dictating fire cock or sprinkler; 3 group of premises, intensity, design area and flow of the extinguishing installation; 4 pump mark, flow, head, power and the written number of pumps; 5 fire cocks (valve, hose, nozzle, cabinet, mounting height); 6 sprinklers; 7 control node, its type, diameter, actuation and number of sprinklers; 8 pipe material and diameter; 9 reservoir volume and number; 10 building height, storeys, hazard class and fire-resistance degree; 11 placeholders in graphs and labels):

| Sheet types | Bullet(s) |
| --- | --- |
| `fire_water_plan`, `sprinkler_plan`, `drench_plan` | none dedicated: counts and lengths off a plan are graphics (excluded) |
| `fire_pump_station` | 2, 4 (the scheme of the pump installation) |
| `riser_diagram`, `axonometric_scheme` | none dedicated; read through «на схеме» (7, 9), «в подписях на расчётной схеме» (8) and «на схемах» (11) |
| `control_node` | 7 (and the generic «на узлах» of 5) |
| `hydraulic_calc` | 1, 2, 3, 6, 8, 11 |
| `specification` | 4, 5, 6, 7, 8, 11 |
| `detail` (nodes) | 5 («на узлах») |
| `general_notes` | 1, 3, 5, 6, 8, 9, 10 |
| `title_block`, `other` | none: no attribute values to compare |

The explanatory note is named in bullets 1, 2, 3, 4, 7, 9 and 10; it is a document part, not a sheet type of the source.

## The prompt change in words

One edit in `system_prompt.md`; everything else is byte for byte what it was (the package tests hold v1's question, categories, conditions and output contract).

**Hint bullet 2, the head and pressure bullet (question 3).** The bullet used to end with «… в таблице гидравлического расчёта и на схеме насосной установки;». It now continues, in the same bullet and before the next one, with: «напор или давление у пожарного крана сопоставляй с другим значением, только если текст прямо относит оба значения к одному и тому же пожарному крану, к одной и той же зоне или к одному и тому же этажу;». The list of places in the bullet and its objects («диктующего пожарного крана или оросителя одной и той же системы или зоны») are unchanged.

New numerals: none. New norm references: none. New designations: none. New nouns: none (the words «зона», «этаж» and «пожарный кран» are in v1's condition 1 and bullets already). Findings: only narrower than before.

`git diff ae751f23..HEAD -- src/auditmanager/analysis/text/profiles/pt/system_prompt.md` is 4 added lines and 1 removed (the removed line is the old last line of the bullet, which now continues). The bundle `prompt_bundle_sha256` of the recording moved `5e921520…` to `1d943079…` and the request key `2fa06c39…` to `3fadac5b…`; the identities `ap_01M5AXG1KHY5S7A1AFVND7FPS9` and `pb_01M5AXG1KH4JG7TMH93XACNF6H` are unchanged.

## Audit of numerals and designations

Run before the edit (task file P-09) and after it: before and after, the prompt has no digit-bearing token, and the capital-letter tokens are `ГОСТ`, `СП`, `ПТ` (in the source) and v1's own words (`TBD`, `XX`, upper-case emphasis). With a designation and a number put into condition 2 (mutation M12 below) the script reports `'Г1–Г4' in legacy source: False` and `'0,35' in legacy source: False`, so it can fail. The script (it lives outside the repository; it is the one the `KM` and `GP` reports print, unchanged):

```python
"""Audit: every digit-bearing token and capital-letter class designation in a section prompt
must occur in the section's five hash-pinned legacy files (read at the pinned commit)."""
import json, re, subprocess, sys
from pathlib import Path

root = Path(sys.argv[1])           # worktree
code = sys.argv[2]                 # e.g. PT
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

Limit of the script: it checks numerals and capital-letter designations only. It does not check ordinary words, and a single-letter token is trivially found by the substring test.

## Assumptions an expert would still want to check

Short and honest (`A-7`): none of these was checked by anyone with domain knowledge.

1. **Question 1 (K).** «гарантированный напор уточнить по ТУ» is still reported as a placeholder, although an expert may accept a reference to the technical conditions as the decision; «ТУ» is not in the source and is not written. The same for «при заказе» and «по месту».
2. **Question 2 (K).** The prompt is silent on units. A model may (a) treat «10 л/с» and «36 м³/ч» as a mismatch because the numbers differ (a false finding the expert rejects), (b) convert and then report or not report (counting, outside v1), or (c) compare nothing. Which of them happens was not measured. The lane chose possible over-reporting to a rule that silences a real conflict and wrote no conversion factor, because the source has none.
3. **Question 3 (N).** Where a head or pressure at a fire cock is written with no named cock, zone or floor in either place, a real mismatch between them is no longer reported. The sentence covers fire cocks only: the head at a sprinkler, the pump head and the guaranteed head are as in v1. How a model decides that the text «directly» puts both values at one cock, zone or floor was not measured. The base bullet's «диктующего пожарного крана» is not in the source (the source has «диктующего оросителя»); the lane did not change it.
4. **Question 4 (K, K).** A design flow that differs from the product of jets and single-jet flow, or a total that differs from the sum of the flows of two systems, is not reported; two written design flows that differ are.
5. **Question 5 (K, K).** The plans have no place in the list, and the bullet on the reservoir (bullet 9) names no object («объём … и число резервуаров»); with several reservoirs the model relies on condition 1 and on the written designation of each. Systems of the same kind in one volume are kept apart by condition 1 and by the «одной и той же» qualifiers; nothing was measured.
6. **Vocabulary not from the source.** Terms in the prompt that none of the five files contains, observed with `grep` and not changed because they are not numbers, norm references or class designations and no question touches them: «водозаполненный», «воздушный» (the source says «мокрый, сухой»), «коэффициент производительности», «диаметр спрыска ствола» (the source says «Диаметр выходного отверстия ствола»), «тип шкафа» (the source says «Пожарные шкафы ШП/ШПК»), «высота установки» (the source says «Размещение ПК на высоте»), «монтажное положение», «число резервуаров», «диктующего пожарного крана», and the noun «зона» (the source never uses a word with the root «зон»). An expert may want them aligned or struck.
7. **Nothing was measured.** The recording is synthetic, authored by hand over the AR corpus (its reply talks about a fire-resistance degree given as II and as III and about the filling of window openings, not about heads, flows or pumps); it proves routing and replay and says nothing about how the profile performs on a real ПТ volume.

## Files changed

| File | Change |
| --- | --- |
| `src/auditmanager/analysis/text/profiles/pt/system_prompt.md` | the one edit above |
| `src/auditmanager/analysis/text/profiles/pt/profile.json` | `profile_version` `1.0.0` to `1.1.0`; `status` `draft` to `reviewed` |
| `fixtures/recorded/sections/pt/3fadac5b0a48465caa3b35b7c3eb9ca81ad0fabca56f3c7dd09ff20ffb037c7d.json` | rebuilt by `build_fixtures.py`; replaces `2fa06c3940faae012574f49a2659e077ba190614b9001c82eaaa3f8efac70f28.json`; the diff against the old file is exactly three lines: `origin.profile_status` (`reviewed`), `origin.prompt_bundle_sha256` (`1d943079…`) and `request_sha256`; the authored reply, usage and latency are unchanged |
| `tests/unit/analysis/text_profiles/section_profile_expectations.json` | the `PT` line only: `reviewed`, `1.1.0` |
| `docs/program/tasks/SECTION-PT-FULL-01.md`, this report | records |

The builder writes all fourteen recordings; thirteen came out byte-identical (`git status` showed no other recording).

## Before and after of modified tests

No test file is modified. The one data line that the tests read changed from `{"code": "PT", "status": "draft", "profile_version": "1.0.0"}` to `{"code": "PT", "status": "reviewed", "profile_version": "1.1.0"}`. Before, the pin tests (registry, package shape, the expectations guard, the HTTP list, the web fixture test) asserted that `profile.json` and the registry agree with the line (`draft`, `1.0.0`); after, they assert the same agreement with `reviewed`, `1.1.0`. Every assertion still compares the package with the line; nothing is weakened.

## Mutation table

Each row edits one thing in the committed tree (`b71a7ec5`), runs the guard, restores with `git checkout` and proves the restore by a SHA-256 over the four product files (prompt, `profile.json`, expectations, new recording; `restored=True` and a clean `git status --short` every time). «Set» is the 211-case set: `test_text_profile_registry.py`, `tests/unit/analysis/text_profiles`, `tests/integration/sections/test_section_recordings.py`, `tests/contract/analysis_packages`. The unmutated tree: `211 passed`.

| # | Mutation | Guard | Result when mutated |
| --- | --- | --- | --- |
| M1 | `profile.json` status `reviewed` back to `draft` (version kept) | set | `4 failed, 207 passed`: registry `test_the_tree_registers_without_error_and_without_an_ar_package`; guard `test_every_line_agrees_with_its_package_profile_json`; packages `test_every_profile_manifest_has_the_text_profile_1_shape`; recordings `test_the_builder_reports_no_drift` |
| M2 | `profile.json` version `1.1.0` back to `1.0.0` (status kept) | set | `3 failed, 208 passed` (the first three of M1) |
| M3 | the `PT` expectations line back to `draft` / `1.0.0` (`profile.json` kept) | set | `3 failed, 208 passed` (the first three of M1) |
| M4 | the `PT` expectations line, status only back to `draft` | set | `3 failed, 208 passed` (the first three of M1) |
| M5 | `system_prompt.md` back to the base text (recording kept) | set | `7 failed, 204 passed`: five recordings tests for `[PT]` (keyed to its own request, served adapter, no other directory answers, filed under another key, replays through the stage) plus `test_the_builder_reports_no_drift` and `test_every_recording_carries_its_own_authored_usage_signature` |
| M6 | the recording back to the base file (new one removed) | set | `7 failed, 204 passed` (the same seven) |
| M7 | `origin.profile_status` `reviewed` to `draft` inside the new recording (key kept) | set | `1 failed, 210 passed`: `test_the_builder_reports_no_drift` |
| M8 | only the added N sentence removed from the prompt (recording kept) | set | `7 failed, 204 passed` (the same seven) |
| M9 | one character of the N sentence changed (a full stop inserted; recording kept) | set | `7 failed, 204 passed` (the same seven) |
| M10a | the `PT` expectations line back to `draft` / `1.0.0`, on the lane stack | `test_analysis_profiles_over_http.py` | `1 failed, 3 passed`: `test_every_row_is_the_registry_entry_the_application_routes_by` |
| M10b | the same, in the web test | `npx vitest run tests/unit/analysis-settings` | `1 failed, 94 passed`: `has a line for exactly the packages that exist, with the status and version each declares` (`PT: status draft in the file, reviewed in profile.json`) |
| M11a | `profile.json` status `draft` (version kept), on the lane stack | HTTP test | `1 failed, 3 passed` (as M10a) |
| M11b | the same, in the web test | web test | `1 failed, 94 passed` (`PT: status reviewed in the file, draft in profile.json`) |
| M12 | «(класс Г1–Г4, не менее 0,35 МПа)» put into condition 2 | the audit script | prints `'0,35' in legacy source: False` and `'Г1–Г4' in legacy source: False` (not a repository test; see the limit below) |

After each restore the guards were green again (`211 passed`; HTTP `4 passed`; web `95 passed`). A probe before the rebuild: with the prompt edited and the recording not rebuilt, `build_fixtures.py --check` exits 1 listing the new key and the old file as `(stale)`, and the 211-case set has `7 failed, 204 passed`.

**What the table says about the new wording.** No test reads the added sentence; its only guard is the recording key, which is the digest of the exact prompt bytes, so any change to the N wording is red until the recording is rebuilt (M5, M8, M9). The reverse also holds: a rebuilt recording over a changed prompt would pass. A test that pins the sentence by content needs a file outside this lane's allowed paths and is not written.

## Commands and results

From `/root/projects/PDF-Analysis/.local/worktrees/section-pt-full-01`, shared venv, one pytest at a time, `PYTHONDONTWRITEBYTECODE=1`. `$BS` is `/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages`. Results are read from the pytest output, not from a pipe.

| Command | Base `ae751f23` | After the change |
| --- | --- | --- |
| section set (above) | `211 passed` | `211 passed` |
| the same, after the prompt edit and before the rebuild | not run | `7 failed, 204 passed`; `--check` rc 1 |
| `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py`, then `--check` | `fixtures match` | rc 0 (`wrote` fourteen, `removed …2fa06c39…`); `--check` rc 0 `fixtures match` |
| `tests/integration/composition/test_analysis_profiles_over_http.py`, lane `.env` exported | not run | `4 passed` |
| `npx vitest run tests/unit/analysis-settings` in `web/` (`node_modules` linked from `gate-night`, untracked) | not run | 7 files, `95 passed` |
| governance one-liner on the task file | not run | `[]` |

The final contract run, `git diff --check` and the path proof are under «Final checks» below. Free disk (`df -h /`): 1.9 GiB at the start. No docker command, no push, no model call, no process killed.

## Integration notes

1. **The web label for `reviewed`** was a false statement under `A-7` («проверен экспертом»); it is already changed on this base by `607ee47a` (see the `GP` report, integration note 1). This lane touches no web file.
2. **Identity:** `analysis_profile_id` and `prompt_bundle_id` are unchanged (the lane mints none), while the bundle's text and hash and the profile hash changed. A stored run of the draft `PT` profile carries the old `analysis_profile_sha256` and `prompt_bundle_sha256`; the registry resolves by the id pair and serves only the new text. Development stand only, no migration (`R-146ah`).
3. **The recording's `origin`** still names `SECTION-RECORDINGS-01` as its authoring task and now says `profile_status: reviewed`; its statement still says it is not field evidence for the profile's review.
4. **e2e manifest:** the step with the selector `tr[data-profile="draft"]` stays valid while any other section is `draft`.
5. **Merge:** the expectations file changes on the `PT` line only, so lanes merge without conflict; if another lane's merge brings a regenerated expectations file, take the line of every merged section from its `profile.json` and re-run the section set, the HTTP test, the web test and `build_fixtures.py --check` after the last section merges.
6. **Record:** `W59-SECTION-PROFILES-01.md` still says every profile is `draft` and lists the five PT questions as open (forbidden path for the lane). When it is updated, cite this report and say that no human reviewed the decisions (`A-7`).
7. **Judge:** read the decisions table against the five legacy files named in P-02 and P-11, not against this lane's summary.

## Limits

- No expert or owner reviewed any decision (`A-7`); no field case (`A-5`); the recording is synthetic.
- No test holds the added sentence by content; the audit script is run by hand and is not a repository guard (row M12). A cross-section guard that checks each prompt's numerals and designations against its pinned source is a candidate for the integrator (the `AI`, `TX`, `KM` and `GP` reports say the same).
- The effect of the N edit on a model's answers is unmeasured; no model was called.
- An expert may disagree with any decision in the table, and the report says where.

## Forbidden paths untouched

`git diff --name-only --no-renames ae751f23..HEAD` on the final tree prints exactly these seven paths, all inside the task's allowed paths (without `--no-renames` git folds the old recording into a rename and prints six):

```text
docs/program/SECTION-PT-FULL-01.md
docs/program/tasks/SECTION-PT-FULL-01.md
fixtures/recorded/sections/pt/2fa06c3940faae012574f49a2659e077ba190614b9001c82eaaa3f8efac70f28.json
fixtures/recorded/sections/pt/3fadac5b0a48465caa3b35b7c3eb9ca81ad0fabca56f3c7dd09ff20ffb037c7d.json
src/auditmanager/analysis/text/profiles/pt/profile.json
src/auditmanager/analysis/text/profiles/pt/system_prompt.md
tests/unit/analysis/text_profiles/section_profile_expectations.json
```

No other section's files, no `W59-SECTION-PROFILES-01.md`, registry, `P02_LOCK.json`, `contracts/**`, migration, `web/**` or `infra/**` appears; `build_fixtures.py` is unchanged. The legacy repository was only read (`git -C /root/projects/PDF-proverka status --short | wc -l` prints `0` before and after).

## Final checks

To be filled from the committed tree.
