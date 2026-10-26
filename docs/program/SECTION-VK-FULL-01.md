# SECTION-VK-FULL-01 — the ВК (VK) profile answers its open questions and is `reviewed`, without a human review

Task: `docs/program/tasks/SECTION-VK-FULL-01.md`. Branch `agent/section-vk-full-01`, base `bb18c3235e2a71cf722560f3616185cf2b096970` (`integration/ar-close-1026`, with `AI`, `PS`, `KJ`, `TX` and `GP` already `reviewed`), product commit `91a2ff33`. Plan item `PROD-14` (section `VK`); owner rulings `R-146ag`, `R-146ah`, `R-146ai`; accepted risk `A-7`; template `SECTION-<CODE>-FULL-01` of `dispatch/PRODUCTION-WAVE-PW2B.md`. Executor: a Sonnet lane. No push, no tag, no container command, no model call, no process killed.

**Read this first (`A-7`).** Nobody reviewed this section: not an expert, not the owner. The status `reviewed` on the VK profile means a lane wrote a decision for every open question of its record and rebuilt its recording. It is **not** expert verification and must not be quoted as one.

## Result

The `VK` record in `W59-SECTION-PROFILES-01.md` has five open questions (the fifth asks two things, so six decisions) and the four cross-section questions. Each has one written decision: **K** for VK-1, VK-2, VK-4, VK-5a, VK-5b and for cross-section 1 to 4; **N** for VK-3 (one sentence in one hint bullet); **X** never. One more change comes from the audit that the template does not name (every numeral and class designation of the prompt against the pinned source): the base prompt names pipe-system and riser designations (`В1`, `Т3`, `Т4`, `К1`, `К2`, `Ст В1-1`, `Ст К1-2`, `К1-1`) that none of the five legacy files contains, so they are replaced by plain words from the source. `profile_version` is `1.1.0`, `status` is `reviewed` in `profile.json` and in the `VK` line of the expectations file, and the recording is rebuilt by `build_fixtures.py`.

Premise: **match.** The package, the five open questions, the four cross-section questions, the legacy repository at `16ba8e5d…` with all five hashes equal to `vk/profile.json`, the `VK` expectations line and a green baseline (211 and 4 passed, `fixtures match`) were as the brief says (task file, P-01 to P-06). The audit (P-07) found the designations above; that is a finding, not a mismatch of the premise.

## Decisions

Quoted question openings are the record's own words. «Condition n» means v1's numbered conditions in the prompt.

| # | Question (record, shortened) | Decision | Reason | Exact change |
|---|---|---|---|---|
| VK-1 | «напор в точке подключения уточнить по ТУ», «отметки выпусков уточнить по месту», «марку насосов уточнить при заказе»: placeholder or an accepted instruction? | **K** | Cross-section rule 1. Each phrase carries the literal «уточнить», so under v1 it is an explicit placeholder unless condition 4 applies (a reference to the table, schedule, specification, sheet, section or volume where the value is given). The technical conditions, the installing organisation and the supplier are not on that list, and the profile sees only this document's text, so it cannot tell whether the value is filed anywhere. Adding them to condition 4 would turn a deferral to an outside document or party into an accepted instruction, which is an expert's call and would silence findings. | none |
| VK-2 | Polymer pipes: the specification gives the outer diameter and wall thickness, the schemes give the nominal bore: is the example in condition 2 enough, or do diameters give systematic false findings? | **K** | Condition 2 already names this very pair: «условный проход (DN) и наружный диаметр трубы», and ends with «убедись, что это буквально одна и та же характеристика». The record states a doubt, not a measured rate, and there is no field case (`A-5`). A wording that told the model never to compare a diameter written one way with a diameter written another way would also silence real conflicts (two different nominal bores for one riser), and an extra example for the wall thickness is a wording change that nothing shows to be needed. | none |
| VK-3 | Hot-water temperature legitimately differs at the heat exchanger outlet, at the fixtures and in the circulation line: does the temperature bullet give false findings when the point is not named? | **N** (this bullet only) | A stated false-positive source: the bullet told the model to compare the design temperature between the general data, the explanatory note and the schemes, with no word about the point it belongs to. The sentence added removes comparisons only: values the text itself attributes to different points are not a contradiction, and a value with a named point is not compared with a value that names none (the model cannot tell they are the same characteristic, condition 2). It adds no number, norm or designation and does not say what any temperature should be. Two temperatures that name no point at all are still compared as before; that residual case is listed under assumptions. | the hot-water bullet gets one sentence (below) |
| VK-4 | Total flow of the building against the sum of the flows by system or consumer in the table of design flows: a finding? | **K** | Cross-section rule 2. Adding up rows is an arithmetic recomputation, which cross-section rule 2 keeps excluded (the record also excludes the checklist's calculation formulas as engineering calculation) and the prompt excludes («НЕ выполняешь и не перепроверяешь инженерные расчёты»). The first hint bullet compares the written flow of one system, and of the building as a whole, between places; it sums nothing. Two totals that are both written in the text and differ stay an `internal_contradiction` under v1; only counting the rows stays out. | none |
| VK-5a | Is the list of places complete for a typical VK set of stages П and Р? | **K** | The list is a hint, not a list of required findings; a place absent at stage П yields nothing under condition 5 («Утверждения просто нет … это не находка»). Every sheet type of `drawing_types.md` that carries attribute values maps onto a bullet (table below). The ones without a dedicated bullet (`detail`, `title_block`, `other`) carry no values to compare. A new place would add a comparison, which is widening. | none |
| VK-5b | Is the internal fire water supply (В2), if it is in the same VK volume, to be taken into account separately? | **K** (not added) | `role.md` assigns the fire water supply and the fire pumps to a coordination with the ПТ section, and the record lists that coordination as excluded (a comparison with another section). The designation `В2` occurs nowhere in the five files, so naming it would add a designation the source lacks, which the brief forbids. The prompt neither lists nor excludes the system: whatever the document writes under a pump, diameter, material or quantity bullet is read by those bullets as before, with condition 1 keeping the values of different systems apart. | none |
| A-1 | Audit (not a record question): numerals and class designations of the prompt against the pinned source | **N** | `В1`, `Т3`, `Т4`, `К1`, `К2`, `Ст В1-1`, `Ст К1-2`, `К1-1` are in no one of the five files (P-04, P-07); the source names the systems in words (ХВС, ГВС, канализация). The rule of the brief says such a notation must not stay in a bullet. The bullets keep their content; only the notation goes, replaced by plain words that the source contains. | three replacements (below) |

Cross-section decisions (the same for every lane; this lane agrees with the table and has nothing to report against it):

| # | Question | Decision | VK-specific note |
|---|---|---|---|
| 1 | Site and contractor phrases | **K** | Covers VK-1. |
| 2 | «Итого» against the sum of rows | **K** | Covers VK-4. The prompt has no bullet that recomputes a total. |
| 3 | Text read from sheets | **K** | The VK record names no bullet whose false findings come from detached sheet text. The bullets that read labels («в подписях планов» in the riser bullet, «в подписях диаметров и высотных отметок на схемах» in the last bullet) are not named by the record and keep those words. The change to the riser bullet under A-1 is the removal of example notations, not a decision on this question, and it leaves «в подписях планов» as it was. |
| 4 | Missing items | **K** | No third kind of observation; condition 5 stays; the excluded list (what must be present: filters, valves, circulation line, reserve pump and the like) stays excluded. |

Places of VK-5a, by sheet type of `drawing_types.md` and bullet of the prompt (bullets numbered from the top of the hint block, as the prompt now reads: 1 flows, 2 water source and inlets, 3 pressure, 4 meter unit and valves, 5 pumps, 6 risers, inlets and outlets, 7 pipe material and insulation, 8 hot-water preparation and temperature, 9 storm drains, 10 quantities, 11 placeholders in graphs and labels):

| Sheet types | Bullet(s) |
|---|---|
| `cold_water_plan` | 6, 7, 10 |
| `hot_water_plan` | 6, 7, 8, 10 |
| `sewerage_plan` | 6, 7 |
| `storm_drain_plan` | 9 |
| `water_meter_unit` | 1, 4, 10 |
| `pump_station` | 3, 5, 10 |
| `riser_diagram`, `axonometric_scheme` | 6, 7, 8, 11 |
| `specification` | 4, 5, 7, 9, 10, 11 |
| `section` | 6 |
| `general_notes` (general data and general instructions) | 1, 2, 3, 7, 8, 9, 11 |
| `detail`, `title_block`, `other` | none dedicated: no attribute values to compare |

## The prompt change in words

`git diff bb18c323 HEAD -- src/auditmanager/analysis/text/profiles/vk/system_prompt.md`: 7 lines added and 4 removed, all inside the hint block «Где в документе раздела ВК искать …». The opening, the question, the two categories, the five conditions, the exclusion paragraph and the output contract are byte for byte as before; the package test holds them.

1. **Hot-water bullet (VK-3).** After «и её расчётная температура в общих данных, в пояснительной записке и на схемах систем …» the bullet now continues: «температуры, которые текст относит к разным точкам (на выходе из водонагревателя или теплообменника, у водоразборных приборов, в циркуляционном трубопроводе), не противоречат друг другу, а значение с названной точкой и значение без неё не сравнивай;». The list of places and the preparation methods (ИТП, ЦТП, водонагреватель) are unchanged.
2. **Notations the source lacks (A-1), three replacements.**
   - riser, inlet and outlet bullet: «(Ст В1-1, Ст К1-2, выпуск К1-1 и т. п.)» becomes «(по обозначению, записанному в тексте)»; the object is still identified by what the document writes, as condition 1 already asks;
   - pipe material and insulation bullet: «(В1, Т3, Т4, К1, К2)» becomes «(ХВС, ГВС, канализации)», the three systems whose pipe materials the source lists (`pipe_material_cold`, `pipe_material_hot`, `pipe_material_sewerage`);
   - hot-water bullet: «на схемах систем Т3 и Т4» becomes «на схемах систем ГВС».

`profile.json`: `status` `draft` to `reviewed`, `profile_version` `1.0.0` to `1.1.0` (the prompt text changed). Identities unchanged; the recording's `prompt_bundle_sha256` moved `5a0ac9e0…713b` to `d80dc122…4c16`.

New numerals: none. New norm references: none. New class designations: none (eight notations removed). Findings: only narrower than before, with one caveat the lane states plainly: the system codes were examples of how a document labels its systems; with them gone, a document that labels its systems only by code is read from its own text, as condition 1 already requires, and the lane did not measure whether that reads differently.

## Audit of numerals and designations

Run before the edit (task file P-07) and after it. After the edit the prompt has no digit-bearing token at all, and every capital-letter token is in the source (`DN`, `ВК`, `ГВС`, `ГОСТ`, `ИТП`, `СП`, `ХВС`, `ЦТП`, `И`) or is v1's own word or marker (`TBD`, `XX`, and the upper-case emphasis fragments `ЖЕ`, `НЕ`, `ТОГО`, `ТОМ`). Putting any of the three replaced notations back makes the script print `False` for it (mutations A1 to A3 below), so the audit can fail. The script (it lives outside the repository; this is its exact text):

```python
"""Audit: every digit-bearing token and capital-letter class designation in a section prompt
must occur in the section's five hash-pinned legacy files (read at the pinned commit)."""
import json, re, subprocess, sys
from pathlib import Path

root = Path(sys.argv[1])           # worktree
code = sys.argv[2]                 # e.g. VK
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

The audit covers numerals and class designations only. Plain words that the five files do not contain are a separate matter and are disclosed, not removed: the base prompt's «часовой» and «секундный» расход, «подача» and «водонагреватель» (none is a number, norm, threshold or designation, and removing them would change what the bullets ask with no stated false-positive source), and the one word this lane adds from the record, «водоразборных» (P-04: 0 in every file). «теплообменник», «циркуляционный», «ХВС», «ГВС» are in the source.

## Assumptions an expert would still want to check

Short and honest (`A-7`): none of these was checked by anyone with domain knowledge.

1. **VK-1 (K).** Whether a model reads «по ТУ» as a reference to a place where the value is given (condition 4, which does not name the technical conditions) or as a placeholder is left to v1's wording and was not measured. The lane did not widen condition 4.
2. **VK-2 (K).** The whole answer rests on one pair in condition 2 (nominal bore against outer diameter). A specification line that gives the outer diameter with the wall thickness against a scheme that gives only the outer diameter, or a different wall thickness for one pipe, is left to the model's reading. Unmeasured.
3. **VK-3 (N).** A temperature written with a named point in one place and without one in another is no longer compared, so a real mismatch hiding in that pair is missed. Two temperatures that name no point are still compared, so the false-positive source the record names stays for that case. The lane did not say which point a bare «температура ГВС» means.
4. **VK-4 (K).** A total that disagrees with the sum of its rows is still not reported, unless the document writes two incompatible totals itself.
5. **VK-5 (K).** The internal fire water supply is neither listed nor excluded; whether a model compares its pumps or diameters with the other systems' is left to condition 1. The comparison with the ПТ section stays out (source: «координация с ПТ»).
6. **A-1 (N).** The lane does not know what `К2` stood for in the earlier drafting (the source does not say) and did not decide it. «(ХВС, ГВС, канализации)» replaces the five codes with the three systems the source names for pipe materials; whether the storm-drain pipes are meant to be read under the pipe material bullet is not decided here (the storm-drain bullet is separate and unchanged).
7. **Nothing was measured.** The recording is synthetic, authored by hand over the AR corpus (its reply is one placeholder about the filling of window openings, page 8, not anything about water supply); it proves routing and replay and says nothing about how the profile performs on a real ВК volume.

## Files changed

| File | Change |
|---|---|
| `src/auditmanager/analysis/text/profiles/vk/system_prompt.md` | the edits above |
| `src/auditmanager/analysis/text/profiles/vk/profile.json` | `profile_version` `1.0.0` to `1.1.0`; `status` `draft` to `reviewed` |
| `fixtures/recorded/sections/vk/7a2b54d03453228ba23a1146c18f46c84aaa08fcda193f65f2c3e55775640e54.json` | rebuilt by `build_fixtures.py`; replaces `de50151c9fb7a1a31f36e74829aaa4dce7729bed4507653413b340352990378a.json`; the diff against the old file is exactly three lines: `origin.profile_status` (`reviewed`), `origin.prompt_bundle_sha256` and `request_sha256`; the authored reply, usage and latency are unchanged |
| `tests/unit/analysis/text_profiles/section_profile_expectations.json` | the `VK` line only: `reviewed`, `1.1.0` |
| `docs/program/tasks/SECTION-VK-FULL-01.md`, this report | records |

The builder writes all fourteen recordings; thirteen came out byte-identical (`git status` showed only the VK directory).

## Before and after of modified tests

No test file is modified. The one data line that the tests read changed from `{"code": "VK", "status": "draft", "profile_version": "1.0.0"}` to `{"code": "VK", "status": "reviewed", "profile_version": "1.1.0"}`. Before, the pin tests (registry, package shape, the expectations guard, the HTTP list, the web fixture test) asserted that `profile.json` and the registry agree with the line (`draft`, `1.0.0`); after, they assert the same agreement with `reviewed`, `1.1.0`. Every assertion still compares the package with the line; nothing is weakened.

## Mutation table

Each row edits one thing in the committed tree (`91a2ff33`), runs the guard, restores with `git checkout HEAD --` and proves the restore by a SHA-256 over the four product files (`restored=True`, `git status --short` empty). «Set» is the 211-case set: `test_text_profile_registry.py`, `tests/unit/analysis/text_profiles`, `tests/integration/sections/test_section_recordings.py`, `tests/contract/analysis_packages`. The unmutated tree: `211 passed`.

| # | Mutation | Guard | Result when mutated |
|---|---|---|---|
| M1 | `profile.json` status `reviewed` back to `draft` (version kept) | set | `4 failed, 207 passed`: registry `test_the_tree_registers_without_error_and_without_an_ar_package`; `test_every_line_agrees_with_its_package_profile_json`; packages `test_every_profile_manifest_has_the_text_profile_1_shape`; recordings `test_the_builder_reports_no_drift` |
| M2 | `profile.json` version `1.1.0` back to `1.0.0` (status kept) | set | `3 failed, 208 passed` (the first three of M1) |
| M3 | the `VK` expectations line back to `draft` / `1.0.0` (`profile.json` kept) | set | `3 failed, 208 passed` (the same three) |
| M4 | the `VK` expectations line, status only back to `draft` | set | `3 failed, 208 passed` (the same three) |
| M5 | `system_prompt.md` back to the base text (recording kept) | set | `7 failed, 204 passed`: five recordings tests for `[VK]` (keyed to its own request, served adapter, no other directory answers, filed under another key, replays through the stage) plus `test_the_builder_reports_no_drift` and `test_every_recording_carries_its_own_authored_usage_signature` |
| M6 | only the new temperature sentence removed | set | `7 failed, 204 passed` (the same seven) |
| M7a | only the riser parenthesis put back to `Ст В1-1, Ст К1-2, выпуск К1-1 и т. п.` | set | `7 failed, 204 passed` (the same seven) |
| M7b | only `(ХВС, ГВС, канализации)` put back to `(В1, Т3, Т4, К1, К2)` | set | `7 failed, 204 passed` (the same seven) |
| M7c | only `систем ГВС` put back to `систем Т3 и Т4` | set | `7 failed, 204 passed` (the same seven) |
| M7d | one comma added inside the new sentence | set | `7 failed, 204 passed` (the same seven) |
| M8 | the recording back to the base file (new one removed) | set | `7 failed, 204 passed` (the same seven) |
| M9 | `origin.profile_status` `reviewed` to `draft` inside the new recording (key kept) | set | `1 failed, 210 passed`: `test_the_builder_reports_no_drift` |
| M9b | `system_prompt.md` back to the base text | `build_fixtures.py --check` | rc 1: the old key listed as the file the script would write, the new one `(stale)` |
| M10 | the `VK` expectations line back to `draft` / `1.0.0`, on the lane stack | `test_analysis_profiles_over_http.py` | `1 failed, 3 passed`: `test_every_row_is_the_registry_entry_the_application_routes_by` |
| M11 | the same, in the web test | `npx vitest run tests/unit/analysis-settings` | `1 failed, 94 passed`: `has a line for exactly the packages that exist, with the status and version each declares` |
| M12 | `profile.json` status `draft` (version kept), on the lane stack | HTTP test | `1 failed, 3 passed` (as M10) |
| M13 | `profile.json` status `draft` (version kept) | web test | `1 failed, 94 passed` (as M11) |
| A1 | M7a, then the audit script | the audit script | prints `False` for `'В1-1'`, `'К1-1'`, `'К1-2'` (not a repository test; see the limit below) |
| A2 | M7b, then the audit script | the audit script | prints `False` for `'В1'`, `'К1'`, `'К2'`, `'Т3'`, `'Т4'` |
| A3 | M7c, then the audit script | the audit script | prints `False` for `'Т3'`, `'Т4'` |

After the last restore the guards were green again (`211 passed`; HTTP `4 passed`; web `95 passed`; `fixtures match`).

**What the table says about the new wording.** No test reads the added sentence or the three replacements; their only guard is the recording key, which is the digest of the exact prompt bytes, so any change to the wording is red until the recording is rebuilt (M5 to M8). The reverse also holds: a rebuilt recording over a changed prompt would pass, and so would a prompt that gets a designation back together with a rebuilt recording (only the manual audit would show it). A test that pins the edits by content, or the audit as a repository guard, needs a file outside this lane's allowed paths and is not written.

## Commands and results

From `/root/projects/PDF-Analysis/.local/worktrees/section-vk-full-01`, shared venv, one pytest at a time, `PYTHONDONTWRITEBYTECODE=1`, `$BS` = `/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages`. Results are read from the pytest output, not from a pipe.

| Command | Base `bb18c323` | After the change |
|---|---|---|
| section set (above) | `211 passed` | `211 passed` |
| the same, after the prompt edit and before the rebuild | not run | `7 failed, 204 passed` (the seven recording tests); `--check` rc 1 |
| `build_fixtures.py --check` | `fixtures match` | `fixtures match` (rc 0) after the rebuild |
| `tests/integration/composition/test_analysis_profiles_over_http.py`, lane `.env` exported | `4 passed` | `4 passed` |
| `npx vitest run tests/unit/analysis-settings` in `web/` (`node_modules` linked from `gate-night`, untracked) | not run | `7 files, 95 passed` |
| governance one-liner on the task file | not run | `[]` |

The final contract run, `git diff --check` and the path proof are under «Final checks» below.

Free disk (`df -h /`): 1.9 GiB at the start and at the end. No docker command, no push, no model call, no process killed.

## Integration notes

1. **The web label for `reviewed`** was a false statement under `A-7` («проверен экспертом»); it is already changed on this base by `607ee47a` (an ancestor of the base). This lane touches no web file.
2. **Identity:** `analysis_profile_id` and `prompt_bundle_id` are unchanged, while the bundle's text and hash changed and the profile hash changed with the version. A stored run of the draft VK profile carries the old `analysis_profile_sha256` and `prompt_bundle_sha256`; the registry resolves by the id pair and serves only the new text. Development stand only, no migration (`R-146ah`).
3. **The recording's `origin`** still names `SECTION-RECORDINGS-01` as its authoring task and now says `profile_status: reviewed`; its statement still says «Not field evidence for the profile's review». The builder was not touched.
4. **e2e manifest:** the step with the selector `tr[data-profile="draft"]` stays valid while any other section is `draft` (eight of the fourteen sections are, after this lane).
5. **Merge:** the expectations file changes on the `VK` line only, so lanes merge without conflict. If another lane's merge changes `build_fixtures.py` output, re-run `build_fixtures.py --check`, the section set, the HTTP test and the web test after the last section merges.
6. **Record:** `W59-SECTION-PROFILES-01.md` still says every profile is `draft` and lists the five VK questions as open. It is a forbidden path for the lane; the integrator should point it at this report without calling the status an expert review.
7. **Other sections:** the audit that found the notations (P-07) is cheap. A read-only run of the same script on the base prompts of the seven other draft sections (nothing was edited there) printed `False` for these tokens: `OV` `ВД1`, `ПД1` (and `ГОСТ`); `POS` `ИТР`, `ГОСТ`; `KM` and `EOM` the conjunction `И` only; `PT`, `SS` and `ITP` nothing. Whether those are real findings is for the lanes that own those sections (`ВД1` and `ПД1` look like system codes of the same kind as `Т3`).
8. **Judge:** read the decisions table against the five legacy files named in P-03 and P-04, not against this lane's summary.

## Limits

- No expert or owner reviewed any decision (`A-7`); no field case (`A-5`); the recording is synthetic.
- No test holds the prompt edits by content; the audit script is run by hand and is not a repository guard. A cross-section guard that checks each prompt's numerals and designations against its pinned source would be a candidate for the integrator.
- The effect of the edits on a model's answers is unmeasured; no model was called.
- The plain words «часовой», «секундный», «подача», «водонагреватель» stay although the source lacks them (see the audit section).
- The lane decided nothing about what `К2` meant or about how the storm-drain pipes are read under the pipe material bullet (assumption 6).

## Forbidden paths untouched

`git diff --name-only --no-renames bb18c3235e2a71cf722560f3616185cf2b096970..HEAD` on the tip of the branch prints exactly these seven paths, all inside the task's allowed paths (without `--no-renames` git folds the old recording into a rename and prints six):

```text
docs/program/SECTION-VK-FULL-01.md
docs/program/tasks/SECTION-VK-FULL-01.md
fixtures/recorded/sections/vk/7a2b54d03453228ba23a1146c18f46c84aaa08fcda193f65f2c3e55775640e54.json
fixtures/recorded/sections/vk/de50151c9fb7a1a31f36e74829aaa4dce7729bed4507653413b340352990378a.json
src/auditmanager/analysis/text/profiles/vk/profile.json
src/auditmanager/analysis/text/profiles/vk/system_prompt.md
tests/unit/analysis/text_profiles/section_profile_expectations.json
```

No other section's files, no `W59-SECTION-PROFILES-01.md`, registry, `P02_LOCK.json`, `contracts/**`, migration, `web/**`, `infra/**` or test file appears; `build_fixtures.py` is unchanged. The legacy repository was only read (`git -C /root/projects/PDF-proverka status --short | wc -l` prints `0` before and after).

## Final checks

On the committed tree (`git status --short` empty), at the commit before this paragraph:

| Command | Result |
|---|---|
| `pytest tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` | filled in below |
| governance one-liner on `docs/program/tasks/SECTION-VK-FULL-01.md` | filled in below |
| `git diff --check bb18c323..HEAD` | filled in below |
| section set, `build_fixtures.py --check`, HTTP test, web test | `211 passed`; `fixtures match`; `4 passed`; `95 passed` |
