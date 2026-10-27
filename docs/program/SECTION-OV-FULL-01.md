# SECTION-OV-FULL-01 — the ОВ (OV) profile answers its open questions and is `reviewed`, without a human review

Task: `docs/program/tasks/SECTION-OV-FULL-01.md`. Branch `agent/section-ov-full-01`, base `8a032ded` (`integration/ar-close-1026`, with `AI`, `PS`, `KJ` and `TX` already `reviewed`). Plan item `PROD-14` (section `OV`); owner rulings `R-146ag`, `R-146ah`, `R-146ai`; template `SECTION-<CODE>-FULL-01` of `dispatch/PRODUCTION-WAVE-PW2B.md`. Executor: a Sonnet lane. No push, no tag, no container command, no model call, no process killed.

## Result

The `OV` record in `W59-SECTION-PROFILES-01.md` has five open questions; the last asks two things, so there are six decisions: **K** four times (questions 1, 4 and the two halves of 5) and **N** twice (questions 2 and 3). One more edit comes from the designation audit that the `AI` lane introduced, not from a record question: two system-mark examples that the pinned source does not contain are replaced by the source's own. The four cross-section questions are applied as the wave table fixes them (all **K**). No **X**. The prompt changed in three places, so `profile_version` is `1.1.0`, the recording is rebuilt, and `profile.json` and the `OV` line of the expectations file say `reviewed`.

**`reviewed` here is not expert verification.** Nobody has reviewed this profile: not an expert, not the owner (`R-146ag`, accepted risk `A-7`). The decisions were taken conservatively from the five hash-pinned legacy files and the record, and nothing was measured on real text. The status must not be quoted anywhere as a human review.

Premise: **match.** Package, status and version, the five source hashes at the pinned commit, the five questions, the four cross-section questions, the expectations line and the one recording are as the brief says (task file, P-01 to P-08). The audit (P-09) is not clean for `OV`, unlike `TX`: `ВД1` and `ПД1` are absent from the source, and the lane corrected them.

## Decisions

Quoted question openings are the record's own words. «Condition n» means v1's numbered conditions in the prompt; «bullet n» counts the hint bullets from the top of the block «Где в документе раздела ОВ искать …».

| # | Question (record) | Decision | Reason | Exact change |
|---|---|---|---|---|
| 1 | «расход уточнить при наладке», «тип решёток уточнить при заказе оборудования»: placeholder (as v1 reads it) or an accepted instruction to the commissioning body and the supplier? | **K** | Cross-section decision (1) applies. Both phrases carry «уточнить», a literal mark of v1's second category. Condition 4 forgives only a reference to a table, schedule, specification, sheet, section or volume where the value is given; «при наладке» and «при заказе оборудования» name a later event, not a place where the value stands. Turning a deferral into an accepted instruction is an expert's call and would silence findings. | none |
| 2 | The unit's capacity in the table of characteristics and in the specification is often larger than the system's design flow by suction and losses: is the example in condition 2 enough, or does comparing flows still give systematic false findings? | **N** | The example is there («расчётный расход воздуха системы и производительность установки с учётом подсосов») but names only suction, while the record's stated source is «подсосы и потери». And the prompt itself puts both attributes into the same places: bullet 1 compares the system's flow and bullet 2 the unit's flow, both in «таблице характеристик систем» (bullet 2 also in the specification), so the pair the example separates can stand side by side in one table or one specification. The source gives the model no help here: `checklist.md` asks for the system's flow on the scheme and the plan and for the unit's «расход, напор, мощность» in the specification, and never says they are equal. The edit adds «и потерь» to the example and says the pair is not one attribute even when both values stand in that table or that specification. It removes a comparison and adds none; where the text names both values as the same attribute of the same unit, condition 2's last sentence still sends the model to compare. | condition 2, see below |
| 3 | The fire-resistance limits of the ducts of one smoke-ventilation system legitimately differ by section (within the served fire compartment, transit, shaft): does the bullet give false findings when the text does not name the section? | **N** (not X) | The bullet compares the limit and the method of fire protection «одной и той же системы … или одного и того же транзитного участка» in three places, and condition 1 only says «Ищи в тексте прямое указание на то, к чему относится значение» without saying what to do when none is found, so two limits of one system with no section named are compared as one. The source itself lists two limits for the ducts of the smoke systems (`checklist.md` «Огнестойкость воздуховодов дымоудаления (EI 150 / EI 60)»; the values are not copied into the prompt), so a legitimate difference inside one system is not the record's invention. Dropping the bullet (X) would silence the real cross-check of one stated limit against another where the text names the same section or says the value is for the whole system. The edit appends to the bullet that values assigned to different sections do not contradict, and that a value with neither a named section nor «the whole system» is not a basis for a contradiction. It only removes comparisons. | the fire-resistance bullet, see below |
| 4 | A system's flow against the sum of room flows in the air-exchange table, or the «Итого» line of the heat-load table against the sum of rows: a finding (recomputation is excluded now)? | **K** | Cross-section decision (2). Counting rows is arithmetic, which the exclusion paragraph keeps out («НЕ выполняешь и не перепроверяешь инженерные расчёты»). The bullets compare values «прямо указанные»: bullet 1 the system's flow in the table, the note, the scheme and the plan labels, bullet 3 a room's flow in the air-exchange table and the plan labels, bullet 8 the heat loads in the general data, the note, the load table and the ITP scheme. Two written totals that differ (for example the load stated in the note against the «Итого» line of the table) stay an `internal_contradiction` under v1; a total against its rows does not. | none |
| 5a | Is the list of places complete for a typical OV set of stages П and Р, in particular for air conditioning (brands and cooling capacity of outdoor and indoor units)? | **K** | The list is a hint, not a list of required findings; a place with no values yields nothing under condition 5. The brand, the flow and the power of an air-conditioning unit are bullet 2 («марка, расход, давление или напор и мощность … блока кондиционирования» in the table, the scheme and the specification). «Холодопроизводительность» is not a word of the list; the only attribute word is «мощность». Naming cooling capacity would add an attribute to compare, which is widening, and the source holds neither the word nor a conditioning bullet (`checklist.md` has no air-conditioning section; `role.md` and `drawing_types.md` only name the systems). An outdoor and an indoor unit are different objects (condition 1), and the capacity of the outdoor unit against the sum of the indoor ones is a sum, which is excluded. | none |
| 5b | The same, for the ITP if it is part of the OV volume. | **K** | The ITP is already in the list: bullet 8 compares the temperature schedule and the heat loads on «схеме ИТП или узла ввода», bullet 2 the pump and the heat exchanger on the scheme and in the specification, bullets 9 and 10 the insulation and the quantities in the specification. They map the source's «Схемы обвязки оборудования» (heat-carrier parameters, circulation pump head and flow). The other items of that source section are presence or design items that the exclusion paragraph and condition 5 keep out («Узлы учёта тепловой энергии», «Расширительные баки — объём по расчёту», «Предохранительные клапаны»). | none |
| A | Audit (not a record question): numerals and class designations of the prompt against the pinned source | **N** (edit by the audit rule) | `ВД1` and `ПД1` in bullet 1 are system marks that none of the five files contains (P-09); the source's own example is «П1, П2, В1, В2...» (`checklist.md`, «Планы вентиляции»). The rule forbids a designation absent from the source in the section's profile, not only in additions. The bullet's scope stays «одной и той же системы … и т. п.», so the expected effect on findings is nil; it is a source-fidelity edit. | bullet 1, see below |

Cross-section decisions (the same for every lane; this lane agrees with them and has nothing to report against them):

| # | Question | Decision | OV-specific note |
|---|---|---|---|
| C1 | Site and contractor phrases | **K** | Covers question 1. |
| C2 | «Итого» against the sum of rows | **K** | Covers question 4: the prompt has no recomputation bullet and no «итог» or «сумм» line (task file, P-10). |
| C3 | Text read from sheets | **K** | Five hint bullets read labels on plans and schemes («подписях планов», «подписях помещений на планах», «подписях на плане», «подписях расходов на схемах»; task file, P-10). The OV record names none of them as a systematic false-positive source, so there is no bullet to narrow. |
| C4 | Missing items | **K** | Condition 5 stays; the record's excluded list («наличие всех элементов: фильтры, нагреватели …», «КОЗ в местах пересечения противопожарных преград», «узлы учёта тепловой энергии» and similar) stays excluded. |

Places of question 5, by sheet type of `drawing_types.md` and bullet of the prompt. The table of system characteristics, the air-exchange table, the heat-load table and the explanatory note are not sheet types of the source; the bullets name them directly (1, 2, 3, 8).

| Sheet type | Bullet(s) |
|---|---|
| `ventilation_plan` | 1, 3, 4 (labels on plans) |
| `heating_plan` | 7 (labels on the plan) |
| `duct_layout` | 1, 2, 4, 11 |
| `piping_diagram` | 7, 8 |
| `equipment_schedule` (ПУ, ИТП, ЦТП) | 2, 8 |
| `smoke_exhaust_plan` | 1, 4 |
| `air_handling_unit` | 1, 2, 4, 11 |
| `conditioning_plan` | 1, 3; unit marks and capacity are read from the table, the scheme and the specification only (bullet 2 names no plan) |
| `specification` | 2, 4, 5, 7, 9, 10, 11 |
| `general_notes` | 5, 6, 8, 9 |
| `title_block`, `detail`, `other` | none: no attribute values to compare |

## The prompt change in words

Three edits in `system_prompt.md`, all inside the hint block and condition 2; everything else is byte for byte what it was (the package tests hold v1's question, categories, conditions and output contract). `git diff 8a032ded..HEAD -- src/auditmanager/analysis/text/profiles/ov/system_prompt.md` is 10 lines added and 5 removed.

1. **Bullet 1 (audit).** The examples of system marks «(П1, В1, ВД1, ПД1 и т. п.)» become «(П1, П2, В1, В2 и т. п.)», the source's own list.
2. **Bullet 5, fire resistance of ducts (question 3).** Five lines are appended: the ducts of one system may have different fire-resistance limits on different sections (within the served fire compartment, a transit section, a shaft); values assigned in the text to different sections do not contradict each other; and if the text does not name which section, or the whole system, a value relates to, differing values are not to be treated as a contradiction.
3. **Condition 2 (question 2).** «с учётом подсосов» becomes «с учётом подсосов и потерь (даже если оба значения стоят в таблице характеристик систем или в спецификации)»; the rest of the condition, including its last sentence («убедись, что это буквально одна и та же характеристика»), is as before.

New numerals: none (two are replaced by two that the source holds). New norm references: none. New designations: none. Findings: only narrower than before, or equal.

## Audit of numerals and designations

Run before and after the edit (task file P-09 has the base output). Before: `ВД1` and `ПД1` reported `in legacy source: False`. After: the digit-bearing tokens are `В1,`, `В2`, `П1,`, `П2,`, all `True`; the capital-letter tokens left are `ИТП`, `ОВ`, `СП` and the single letters in the source and v1's own words (`TBD`, `XX`, `ГОСТ`, upper-case emphasis). The audit can fail: with `Г1–Г4` put into condition 2 it reports `'Г1–Г4' in legacy source: False` (row M12 below), and on the base prompt it reports the two marks again (row M13). The script that was run (it lives outside the repository; this is its exact text):

```python
"""Audit: every digit-bearing token and capital-letter class designation in a section prompt
must occur in the section's five hash-pinned legacy files (read at the pinned commit)."""
import json, re, subprocess, sys
from pathlib import Path

root = Path(sys.argv[1])           # worktree
code = sys.argv[2]                 # e.g. OV
prompt = (root / f"src/auditmanager/analysis/text/profiles/{code.lower()}/system_prompt.md").read_text("utf-8")
manifest = json.loads((root / f"src/auditmanager/analysis/text/profiles/{code.lower()}/profile.json").read_text("utf-8"))
legacy = Path("/root/projects/PDF-proverka")
src = ""
for f in manifest["source"]["files"]:
    src += subprocess.run(["git", "-C", str(legacy), "show", f"{manifest['source']['commit']}:{f['path']}"],
                          check=True, capture_output=True).stdout.decode("utf-8") + "\n"
# drop the numbered conditions "1." .. "5." and the page/field words of the v1 text
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

## Assumptions an expert would still want to check

Short and honest (`A-7`): none of these was checked by anyone with domain knowledge.

1. **Question 1 (K).** «Расход уточнить при наладке» and «тип решёток уточнить при заказе оборудования» are still reported as placeholders. A real OV document legitimately leaves such items to commissioning and to the order, so these findings will be frequent; the lane chose over-reporting to silencing.
2. **Question 2 (N).** The sentence says that a system's design flow and a unit's capacity with suction and losses are not one attribute even when both stand in the same table or specification. It leaves the model to decide, from the text, whether two values are named as the same attribute of the same unit. «Потери» in the sense of air losses comes from the record's wording, not from the source (the source's «потери» are pressure and heat losses). The effect is unmeasured.
3. **Question 3 (N).** A fire-resistance limit with no section named and no «whole system» is no longer compared. A genuine contradiction between two such statements is not reported now; the expert may prefer to see it. The words «пожарного отсека» and «шахта» come from the record, not from the source. No limit value is written anywhere in the prompt.
4. **Question 4 (K).** A system's flow against the sum of its rooms and a heat-load total against its rows are not reported.
5. **Question 5 (K, K).** Cooling capacity of outdoor and indoor units has no word of its own («мощность» only), and unit marks on conditioning plans are not read from plan labels. The ITP is covered only through the temperature schedule, the heat loads, the pump, the exchanger, insulation and quantities.
6. **Not asked, not changed.** Bullet 8 lists «расчётные температуры наружного воздуха» in the general data, the note, the load table and the ITP scheme; the outdoor design temperature for the cold period, for the warm period and for ventilation differ by nature (the source's `project_params.md` has both a winter and a summer field). Condition 2 names the warm and the cold period only for the air flow. The record does not ask, so the lane left it; an expert may want an example there.
7. **Vocabulary not from the source.** Attribute words of the hint bullets that none of the five files contains, observed with a word count over the five files and not changed because they are not numbers, norm references or class designations and no question touches them: «нормально открытый / нормально закрытый» and «исполнение», «задержка» and «очерёдность» (the source says «алгоритм включения»), «узла ввода», «тепловой сети», «внутреннем контуре», «общеобменной», «толщина», «стояки», «подсосов» and «транзитного участка». An expert may want them aligned or struck.
8. **Nothing was measured.** The recording is synthetic, authored by hand over the AR corpus; it proves routing and replay and says nothing about how the profile performs on a real ОВ volume.

## Files changed

| File | Change |
|---|---|
| `src/auditmanager/analysis/text/profiles/ov/system_prompt.md` | the three edits above |
| `src/auditmanager/analysis/text/profiles/ov/profile.json` | `profile_version` `1.0.0` to `1.1.0`; `status` `draft` to `reviewed` |
| `fixtures/recorded/sections/ov/93087ffb2bff43d5fb132e05667372e6f861bc8d65795cdcc81cdfe6db9edc96.json` | rebuilt by `build_fixtures.py`; replaces `12c35374…49d9ef.json`; the differences against the old file are `origin.profile_status` (`reviewed`), `origin.prompt_bundle_sha256` (`e855ec2f…f5a4`) and `request_sha256`; the authored reply, usage and latency are unchanged |
| `tests/unit/analysis/text_profiles/section_profile_expectations.json` | the `OV` line only: `reviewed`, `1.1.0` |
| `docs/program/tasks/SECTION-OV-FULL-01.md`, this report | records |

The builder writes all fourteen recordings; thirteen came out byte-identical (`git status` shows no other recording). No test file was edited, so no assertion was weakened: there is no before/after of a modified test to give. The one data line the tests read changed from `draft`/`1.0.0` to `reviewed`/`1.1.0`; before, the registry, package, guard, HTTP and web tests asserted that `profile.json` and the served row agree with the line, after they assert the same agreement with the new values.

## Mutation table

Each row edits one thing in the committed tree (`17e9f551`), runs the set named, restores with `git checkout` (or deletes the temporary file) and proves the restore by a SHA-256 over the four files (prompt, `profile.json`, expectations, new recording) and an empty `git status --short` (`restored=True` every time). The section set is `test_text_profile_registry.py`, `tests/unit/analysis/text_profiles`, `tests/integration/sections/test_section_recordings.py` and `tests/contract/analysis_packages` (211 cases). The unmutated tree: `211 passed`.

| Mutation | Result | First red cases |
|---|---|---|
| M1 `profile.json` status `reviewed` back to `draft` (version kept) | 4 failed, 207 passed | registry `test_the_tree_registers_without_error_and_without_an_ar_package`; guard `test_every_line_agrees_with_its_package_profile_json`; packages `test_every_profile_manifest_has_the_text_profile_1_shape`; recordings `test_the_builder_reports_no_drift` |
| M2 `profile.json` version `1.1.0` back to `1.0.0` (status kept) | 3 failed, 208 passed | the first three of M1 |
| M3 the `OV` expectations line back to `draft` / `1.0.0` (`profile.json` kept) | 3 failed, 208 passed | the first three of M1 |
| M4 the `OV` expectations line, status only back to `draft` | 3 failed, 208 passed | the first three of M1 |
| M5 `system_prompt.md` back to the base text (recording kept) | 7 failed, 204 passed | recordings: `test_each_section_has_one_synthetic_recording_keyed_to_its_own_request[OV]`, `test_the_builder_reports_no_drift`, `test_the_served_adapter_answers_each_recorded_section_and_the_canonical_alone_does_not[OV]`, `test_no_other_directory_answers_a_section_request[OV]` and three more |
| M6 the recording back to the base file (new one removed) | 7 failed, 204 passed | the same recordings cases |
| M7 `origin.profile_status` `reviewed` to `draft` inside the new recording (key kept) | 1 failed, 210 passed | `test_the_builder_reports_no_drift` |
| M8a only the bullet 1 edit undone (`ВД1`, `ПД1` back; recording kept) | 7 failed, 204 passed | the same recordings cases as M5 |
| M8b only the condition 2 edit undone (recording kept) | 7 failed, 204 passed | the same |
| M8c only the fire-resistance sentence removed (recording kept) | 7 failed, 204 passed | the same |
| M9 one character of the fire-resistance sentence changed (a full stop inserted; recording kept) | 7 failed, 204 passed | the same |
| M10 the `OV` expectations line back to `draft` / `1.0.0`, on the lane stack | 1 failed, 3 passed | `test_analysis_profiles_over_http.py::test_every_row_is_the_registry_entry_the_application_routes_by` |
| M10 the same, in the web test | 1 failed, 94 passed | `has a line for exactly the packages that exist, with the status and version each declares` |
| M11 `profile.json` status back to `draft`, on the lane stack | 1 failed, 3 passed | the same HTTP case |
| M11 the same, in the web test | 1 failed, 94 passed | the same web case |
| M12 «(Г1–Г4)» inserted into condition 2 | the audit script prints `'Г1–Г4' in legacy source: False` | not a repository test (see the limit below) |
| M13 the base prompt put through the audit script | prints `'ВД1' … False` and `'ПД1' … False` | not a repository test |

The red of the unit guards names the section: the `OV` rows of the expectations test print `'OV': {'expectations': ('reviewed', '1.1.0'), …}` against the mutated `profile.json`. After each restore the SHA-256 was equal to the one taken before and the tests were green again. A probe before the rebuild: with the prompt edited and the recording not rebuilt, the builder's `--check` exits 1 listing the new key and the old file as `(stale)`, and the 211-case set has 7 failed, 204 passed.

## Commands and results

From `/root/projects/PDF-Analysis/.local/worktrees/section-ov-full-01`, shared venv, one pytest at a time. `$BS` is `/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages`.

| Command | Result |
|---|---|
| section set (above), base `8a032ded` | `211 passed` |
| section set, after the change and the rebuild | `211 passed` |
| `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py`, then `--check` | rc 0 (`wrote` fourteen, `removed …12c35374…49d9ef.json`); `--check` rc 0 `fixtures match` |
| `tests/integration/composition/test_analysis_profiles_over_http.py`, lane `.env` exported | `4 passed` |
| `npx vitest run tests/unit/analysis-settings` in `web/` (`node_modules` linked from `gate-night`) | 7 files, `95 passed` |
| governance one-liner on the task file | `[]` |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, `git diff --check` | see «Final checks» |

Free disk at the start of the lane 1.8 GiB, at the end 2.0 GiB (`df -h /`; the figure moves with other lanes). No docker command, no push, no model call, no process killed.

## Integration notes

1. **The web label for `reviewed` still says «проверен экспертом»** and the `AnalysisProfileStatus` docstring says «a package an expert has reviewed» (see the `AI` report, integration note 1). Both are outside this lane (`web/**`, `src/auditmanager/api/**`); the decision is the integrator's, once for all fourteen lanes.
2. **Identity:** `analysis_profile_id` and `prompt_bundle_id` are unchanged (the lane mints none), while the bundle's text and hash and the profile hash changed. A stored run of the draft `OV` profile carries the old `analysis_profile_sha256` and `prompt_bundle_sha256`; the registry resolves by the id pair and serves only the new text. Development stand only, no migration (`R-146ah`).
3. **The recording's `origin`** still names `SECTION-RECORDINGS-01` as its authoring task and now says `profile_status: reviewed`; its statement still says «Not field evidence for the profile's review».
4. **e2e manifest:** the step with the selector `tr[data-profile="draft"]` stays valid while any other section is `draft` (`POS`, `KM`, `VK`, `PT`, `EOM`, `SS`, `ITP`, `GP`, `PB` at this base).
5. **Merge:** the expectations file changes on the `OV` line only, so lanes merge without conflict; re-run the section set, the HTTP test, the web test and `build_fixtures.py --check` after the last section merges.
6. **Record:** `W59-SECTION-PROFILES-01.md` still says «Every profile is `status: draft`» and lists the five questions as open (forbidden path for the lane). When it is updated, cite this report and say that no human reviewed the decisions (`A-7`).

## Limits

- No test holds the added sentences themselves. Their wording is held only by the recording's request key (so an edit without a rebuild goes red, rows M5, M8a to M8c and M9), and the absence of a designation outside the source is held only by the manual audit (rows M12 and M13); a new guard test is outside this lane's paths. A cross-section guard that checks each prompt's numerals and designations against its pinned source is a candidate for the integrator (the `AI` and `TX` reports say the same).
- The effect of the two N edits on a model's answers is unmeasured; no model was called.
- An expert may disagree with any decision in the table, and the report says where.

## Forbidden paths untouched

`git diff --name-only --no-renames 8a032ded..HEAD` on the final tree prints exactly these seven paths, all inside the task's allowed paths (without `--no-renames` git folds the old recording into a rename and prints six):

```text
docs/program/SECTION-OV-FULL-01.md
docs/program/tasks/SECTION-OV-FULL-01.md
fixtures/recorded/sections/ov/12c35374f81843f139bdd209e94983af209826679c462e03e3219a790549d9ef.json
fixtures/recorded/sections/ov/93087ffb2bff43d5fb132e05667372e6f861bc8d65795cdcc81cdfe6db9edc96.json
src/auditmanager/analysis/text/profiles/ov/profile.json
src/auditmanager/analysis/text/profiles/ov/system_prompt.md
tests/unit/analysis/text_profiles/section_profile_expectations.json
```

No other section's files, no `W59-SECTION-PROFILES-01.md`, registry, `P02_LOCK.json`, `contracts/**`, migration, `web/**` or `infra/**` appears; `build_fixtures.py` is unchanged. The legacy repository was only read (`git status --short` there: 0 lines before and after).

## Final checks

On the committed tree (`git status --short` empty), the last commit before this paragraph being `452e2424`:

| Command | Result |
|---|---|
| `pytest tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` | `105 passed` |
| governance one-liner on `docs/program/tasks/SECTION-OV-FULL-01.md` | `[]` |
| `git diff --check 8a032ded..HEAD` | rc 0 |
| section set, `build_fixtures.py --check`, HTTP test (lane `.env`), `vitest` analysis-settings | `211 passed`; `fixtures match` rc 0; `4 passed`; `95 passed` |

This paragraph is the only text added after `452e2424`; the contract run above was repeated on the tree that contains it (see the lane's final message for the tip SHA).
