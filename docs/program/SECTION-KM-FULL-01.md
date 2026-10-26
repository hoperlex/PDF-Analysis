# SECTION-KM-FULL-01 — the КМ (KM) profile answers its open questions and is `reviewed`, without a human review

Task: `docs/program/tasks/SECTION-KM-FULL-01.md`. Branch `agent/section-km-full-01`, base `8a032dedc9b6bccda6f9f01849b543ec5caf891e` (`integration/ar-close-1026`, with `AI`, `PS`, `KJ` and `TX` already `reviewed`). Plan item `PROD-14` (section `KM`); owner rulings `R-146ag`, `R-146ah`, `R-146ai`; template `SECTION-<CODE>-FULL-01` of `dispatch/PRODUCTION-WAVE-PW2B.md`. Executor: a Sonnet lane. No push, no tag, no container command, no model call, no process killed.

## Result

The `KM` record in `W59-SECTION-PROFILES-01.md` has five open questions; the third and the fifth each ask two things, so there are seven decisions: **K** six times and **N** once (question 4). The four cross-section questions are applied as the wave table fixes them (all **K**). No **X**. The N decision is one sentence appended to condition 1 of `system_prompt.md`; nothing else in the prompt moved. The prompt changed, so `profile_version` is `1.1.0`, the recording is rebuilt, and `profile.json` and the `KM` line of the expectations file say `reviewed`.

**`reviewed` here is not expert verification.** Nobody has reviewed this profile: not an expert, not the owner (`R-146ag`, accepted risk `A-7`). The decisions were taken conservatively from the five hash-pinned legacy files and the record, and nothing was measured on real text. The status must not be quoted anywhere as a human review.

Premise: **match.** Package, status and version, the five source hashes at the pinned commit, the five questions, the four cross-section questions, the expectations line and the one recording are as the brief says (task file, P-01 to P-08). The audit of numerals and class designations that the `AI` lane found necessary (P-09) is clean for `KM`: the prompt has no digit-bearing token and no class designation, so nothing had to be removed. One premise detail the record does not flag: question 1 quotes «ГОСТ 19281», which none of the five pinned files contains (checked by `grep`), so no decision may write it into the prompt, and none does.

## Decisions

Quoted question openings are the record's own words. «Condition n» means v1's numbered conditions in the prompt; «bullet n» counts the bullets of the hint block from the top (the list is under «Places of question 5a» below).

| # | Question (record) | Decision | Reason | Exact change |
|---|---|---|---|---|
| 1 | Different designations of steel for one element (the record's example: С345 in the specification, 09Г2С in the general notes): a contradiction or an admissible replacement that an expert decides? | **K** | Calling them one value needs an equivalence or applicability rule, and the pinned source holds none: `checklist.md` lines 10 and 11 present С345 («ответственные конструкции») and 09Г2С («для низкотемпературных условий и сварных конструкций») as separate grades with separate uses, and the applicability rules are among the items the record excludes as engineering judgement. A general sentence «another name is not a contradiction» would silence real conflicts. Bullet 3 compares the grade «для одного и того же элемента», and condition 2 already requires «буквально одна и та же характеристика»; two different grades named for one element are two values for one characteristic, which v1 reports and the expert accepts or rejects. «ГОСТ 19281» (the record's wording) is not in the source and is not added. | none |
| 2 | «усилия в узлах — по расчёту», «катеты швов принимать по наименьшей толщине свариваемых элементов», «конструкцию узла уточнить в КМД»: a placeholder (as v1) or an accepted rule and a handover of the decision to КМД? | **K** | Cross-section decision (1) applies. «конструкцию узла уточнить в КМД» carries the mark «уточнить», and condition 4 forgives only a reference to a table, schedule, specification, sheet, section or volume where the value is given; a handover to a later set of drawings is not that place (the name «КМД» does not occur in the source). Treating such a handover as an accepted instruction is an expert's call and would silence findings. The other two phrases carry none of v1's marks of unfilled; the profile neither lists nor excludes them and v1's definition decides them as before. | none |
| 3a | A discrepancy of the total mass in the general data, or of the «Итого» row of the specification, with the sum of the masses by mark (recomputation is excluded now): a finding? | **K** | Cross-section decision (2). Adding rows is arithmetic and the exclusion paragraph keeps recomputation out. The one mass-total bullet (bullet 5, second half) compares a total «прямо указанная» in the general data with the итог of the specification: two written totals that differ stay an `internal_contradiction` under v1; a total against its rows does not. | none |
| 3b | How to tell the specification mass from a mass that includes deposited metal? | **K** | Condition 2 already says to compare values only after establishing that they are «буквально одна и та же характеристика» and names the mass of one element against the total mass of a mark as a near-miss. If the text itself labels the basis of a mass, the two masses are different characteristics and nothing is reported. If it does not label it, nothing in the text tells the two cases apart, and a rule to overlook such a difference would silence a real discrepancy between two written totals; whether it is one is the expert's call. «наплавленный металл» occurs nowhere in the five pinned files, so naming it would add vocabulary and a domain rule the source does not hold. The record names no false-positive bullet here; it asks how to tell. | none |
| 4 | Marks of elements repeat on the schemes of different elevations for different constructions: does the bullet about the profile and the elevations of one and the same mark give systematic false findings (condition 1)? | **N** | Condition 1 lists «маркам элементов» among the different objects, but nowhere says that one and the same mark may stand for different constructions at different elevations. Bullet 4 compares «профиль … и отметки одного и того же элемента» in four places (schemes, table of sections, node drawings, specification), and the object is identified only by the element, in practice by its mark. A mark is a designation, not an identity (`AGENTS.md` section 4: «path/filename/display number as identity» is forbidden), and the elevation of one mark is different by nature when the mark is repeated. The sentence adds a condition before a comparison: the comparison by mark is made when the text puts both mentions in one construction, one elevation or one node, or when the mark belongs to one construction only in the document. It widens nothing and adds no number, norm reference or designation (the record's examples of marks are not written into the prompt: they are not in the source). | one sentence appended to condition 1, see below |
| 5a | Is the list of places complete for stages П and Р? | **K** | The list is a hint, not a list of required findings; a place absent at stage П yields nothing under condition 5 («Утверждения просто нет … это не находка»). Every sheet type of `drawing_types.md` that carries attribute values maps onto a bullet, with the exceptions listed below (the sheets of trusses, columns, beams and bracing have no dedicated place, but the bullets about grades, profiles and node notes name «схемах» and «надписях»). Adding places is widening. | none |
| 5b | Does the loads bullet give false findings by mixing the normative and the design values? | **K** | The prompt separates them twice already: bullet 2 reads «отдельно нормативные и расчётные» and condition 2 names «нормативное и расчётное значение нагрузки» as its first example of two different characteristics. A third mention would repeat, not narrow. The source's other cause of a difference between two design values (combinations of loads, the coefficients «по нагрузке») belongs to the engineering items the record excludes, and a rule about it would be a judgement the source does not hold. | none |

Cross-section decisions (the same for every lane; this lane agrees with them and has nothing to report against them):

| # | Question | Decision | KM-specific note |
|---|---|---|---|
| C1 | Site and contractor phrases | **K** | Covers question 2. |
| C2 | «Итого» against the sum of rows | **K** | Covers question 3a: the prompt has no recomputation bullet. |
| C3 | Text read from sheets | **K** | The record names no bullet whose false findings come from detached sheet text (P-10: «надписях» occurs in four bullets, none of the five questions points at them). Question 4 is about the identity of a mark, not about detached text, and is decided on its own. |
| C4 | Missing items | **K** | Condition 5 stays; the record's excluded list («наличие … требуется») stays excluded. |

Places of question 5a, by sheet type of `drawing_types.md` and bullet of the hint block (bullets: 1 frame, spans, regions, class of responsibility; 2 loads; 3 steel grade; 4 profile and elevations; 5 quantity and mass of a mark, total mass; 6 forces N, M, Q; 7 welds, welding method; 8 bolts; 9 fire protection; 10 anticorrosion protection; 11 unfilled marks in the columns of schedules):

| Sheet types | Bullet(s) |
|---|---|
| `framing_plan` (schemes of arrangement) | 3, 4 |
| `assembly_plan` | 5 |
| `connection_detail`, `detail` (node notes) | 3, 4, 6, 7, 8, 11 |
| `specification` (specification, schedules of bolts and welds) | 3, 4, 5, 7, 8, 11 |
| `general_notes` (general data and notes) | 1, 2, 3, 7, 8, 9, 10 |
| `cross_section` | 4 (the table of sections) |
| `truss_drawing`, `column_drawing`, `beam_drawing`, `bracing_scheme`, `general_view` | none dedicated; read through «надписях на схемах и узлах» (3) and «схемах расположения» (4) |
| `title_block`, `other` | none: no attribute values to compare |

The tables named in bullets 2, 6, 9 and 10 (loads, forces, fire protection, anticorrosion) are not sheet types of the source; they are read wherever the text puts them.

## The prompt change in words

One edit in `system_prompt.md`; everything else is byte for byte what it was (the package tests hold v1's question, categories, conditions and output contract).

**Condition 1 (question 4).** After the sentence «Ищи в тексте прямое указание на то, к чему относится значение.» five lines are added: the mark of an element does not by itself make two mentions the same object, because the same mark can be given to different constructions at different elevations; compare the profile and the elevations by mark only if the text directly places both mentions in one construction, one elevation or one node, or if in the document the mark belongs to one construction only.

New numerals: none. New norm references: none. New designations: none. Findings: only narrower than before. The quantity and mass by mark (bullet 5) are not named in the sentence; for them condition 1's existing rule on different elevations is all that applies.

`git diff 8a032ded..HEAD -- src/auditmanager/analysis/text/profiles/km/system_prompt.md` is 5 added lines and 1 removed (the last line of condition 1 is the same text, now continued). The bundle `content_sha256` moved `c06f4bc5…` to `4c33f7bf…`; the identities `ap_01M5AXG1KB71SHN23H775AP551` and `pb_01M5AXG1KB45S6A5TZ0ZTWRVHS` are unchanged.

## Audit of numerals and designations

Run before the edit (task file P-09) and after it: before and after, the prompt has no digit-bearing token, and the capital-letter tokens are `N`, `M`, `Q` (`role.md` line 10), `КМ`, `СП`, `ГОСТ` (in the source) and v1's own words (`TBD`, `XX`, upper-case emphasis). With a designation put into condition 2 (mutation M12 below) the script reports `'А500С' in legacy source: False`, so it can fail. The script (it lives outside the repository; it is the one the `TX` report prints, unchanged):

```python
"""Audit: every digit-bearing token and capital-letter class designation in a section prompt
must occur in the section's five hash-pinned legacy files (read at the pinned commit)."""
import json, re, subprocess, sys
from pathlib import Path

root = Path(sys.argv[1])           # worktree
code = sys.argv[2]                 # e.g. TX
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

Limit of the script: a single-letter token (`N`, `M`, `Q`) is trivially found in any text by the substring test; for those three the real source is the line quoted above.

## Assumptions an expert would still want to check

Short and honest (`A-7`): none of these was checked by anyone with domain knowledge.

1. **Question 1 (K).** A document that deliberately names two grades for one element (a replacement that is allowed in practice) will show a finding. The lane chose over-reporting to silencing and wrote no equivalence, because the source holds none; «ГОСТ 19281» of the record is not in the source and is not written.
2. **Question 2 (K).** «конструкцию узла уточнить в КМД» is still reported as a placeholder. The other two phrases are not named by v1's wording; since v1's definition ends in «и подобное», a model may still report them, and nothing was measured. An expert may want the handover to КМД accepted.
3. **Question 3 (K, K).** A total against the sum of rows is not reported. A total mass in the general data against the итог of the specification is reported when the two differ and the text does not itself label their bases (for example with or without deposited metal); an expert may want a rule for that case, and none was written because «наплавленный металл» is not in the source.
4. **Question 4 (N).** Where a mark repeats and the text gives no construction, elevation or node for either mention, a real mismatch of profile or elevation is no longer reported; where the mark belongs to one construction in the document, the comparison stays. How a model decides «belongs to one construction only» was not measured. The sentence covers profile and elevations only; quantity and mass by mark are as in v1.
5. **Question 5 (K, K).** Trusses, columns, beams and bracing have no dedicated place in the list. The loads bullet is unchanged; if an expert knows another systematic source of false findings in it (for example load combinations), it is not covered.
6. **Vocabulary not from the source.** Terms in the prompt that none of the five files contains, observed with `grep` and not changed because they are not numbers, norm references or class designations and no question touches them: «степень агрессивного воздействия среды» (the source says «Класс агрессивности среды»), «коэффициент надёжности по ответственности» (the source says «по назначению», in `checklist.md` and `project_params.md`), «число слоёв» and «общая толщина» (the source says «количество слоёв», «толщина»), «пояснительной записке», the names of tables «таблица нагрузок», «таблица сечений», «таблица усилий», «ведомость элементов». An expert may want them aligned or struck.
7. **Nothing was measured.** The recording is synthetic, authored by the builder over the AR corpus; it proves routing and replay and says nothing about how the profile performs on a real КМ volume.

## Files changed

| File | Change |
|---|---|
| `src/auditmanager/analysis/text/profiles/km/system_prompt.md` | the one edit above |
| `src/auditmanager/analysis/text/profiles/km/profile.json` | `profile_version` `1.0.0` to `1.1.0`; `status` `draft` to `reviewed` |
| `fixtures/recorded/sections/km/3d3fb6f0…9458.json` | rebuilt by `build_fixtures.py`; replaces `bf6a3d2c…7cfd.json`; the differences against the old file are `origin.profile_status` (`reviewed`), `origin.prompt_bundle_sha256` (`4c33f7bf…`) and `request_sha256`; the authored reply, usage and latency are unchanged |
| `tests/unit/analysis/text_profiles/section_profile_expectations.json` | the `KM` line only: `reviewed`, `1.1.0` |
| `docs/program/tasks/SECTION-KM-FULL-01.md`, this report | records |

The builder writes all fourteen recordings; thirteen came out byte-identical (`git status` showed no other recording). No test file was edited, so no assertion was weakened: there is no before/after of a modified test to give. The one data line the tests read changed from `draft`/`1.0.0` to `reviewed`/`1.1.0`; before, the registry, package, guard, HTTP and web tests asserted that `profile.json` and the served row agree with the line (`draft`, `1.0.0`), after they assert the same agreement with the new values.

## Mutation table

Each row edits one thing in the committed tree (`850514b2`), runs the section test set, restores with `git checkout` and proves the restore by a SHA-256 over the four files (prompt, `profile.json`, expectations, new recording; `restored=True` and a clean `git status --short` every time). The set is `test_text_profile_registry.py`, `tests/unit/analysis/text_profiles`, `tests/integration/sections/test_section_recordings.py` and `tests/contract/analysis_packages` (211 cases). The unmutated tree: `211 passed`.

| Mutation | Result | First red cases |
|---|---|---|
| M1 `profile.json` status `reviewed` back to `draft` (version kept) | 4 failed | registry `test_the_tree_registers_without_error_and_without_an_ar_package`; guard `test_every_line_agrees_with_its_package_profile_json`; packages `test_every_profile_manifest_has_the_text_profile_1_shape`; recordings `test_the_builder_reports_no_drift` |
| M2 `profile.json` version `1.1.0` back to `1.0.0` (status kept) | 3 failed | the first three of M1 |
| M3 the `KM` expectations line back to `draft` / `1.0.0` (`profile.json` kept) | 3 failed | the first three of M1 |
| M4 the `KM` expectations line, status only back to `draft` | 3 failed | the first three of M1 |
| M5 `system_prompt.md` back to the base text (recording kept) | 7 failed | recordings: `test_each_section_has_one_synthetic_recording_keyed_to_its_own_request[KM]`, `test_the_builder_reports_no_drift`, `test_the_served_adapter_answers_each_recorded_section_and_the_canonical_alone_does_not[KM]` and four more |
| M6 the recording back to the base file (new one removed) | 7 failed | the same recordings cases as M5 |
| M7 `origin.profile_status` `reviewed` to `draft` inside the new recording (key kept) | 1 failed | `test_the_builder_reports_no_drift` |
| M8 only the added N sentence removed from the prompt (recording kept) | 7 failed | the same recordings cases as M5 |
| M9 one character of the N sentence changed (a full stop inserted; recording kept) | 7 failed | the same recordings cases as M5 |
| M10 the `KM` expectations line back to `draft` / `1.0.0`, on the lane stack | 1 failed, 3 passed | `test_analysis_profiles_over_http.py::test_every_row_is_the_registry_entry_the_application_routes_by` |
| M10 the same, in the web test | 1 failed, 94 passed | `has a line for exactly the packages that exist, with the status and version each declares`: `KM: status draft in the file, reviewed in profile.json` |
| M11 `profile.json` status back to `draft`, on the lane stack | 1 failed, 3 passed | the same HTTP case |
| M11 the same, in the web test | 1 failed, 94 passed | the same web case (`KM: status reviewed in the file, draft in profile.json`) |
| M12 «(А500С)» inserted into condition 2 | the audit script prints `'А500С' in legacy source: False` | not a repository test (see the limit below) |

After each restore the SHA-256 was equal to the one taken before and the tests were green again (`211 passed`; HTTP `4 passed`; web `95 passed`). A probe before the rebuild: with the prompt edited and the recording not rebuilt, the builder's `--check` exits 1 listing the new key and the old file as `(stale)`, and the 211-case set has 7 failed, 204 passed. Two corrections of the lane's own harness are worth stating: the first run of the mutation script stopped at M1 because it asked `git checkout` to restore a path that the base commit did not hold; the tree was restored by hand and the script was fixed and run again from the start, so every row above is from the second, complete run.

## Commands and results

From `/root/projects/PDF-Analysis/.local/worktrees/section-km-full-01`, shared venv, one pytest at a time. `$BS` is `/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages`.

| Command | Result |
|---|---|
| section set (above), base `8a032ded` | `211 passed` |
| section set, after the change and the rebuild | `211 passed` |
| `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py`, then `--check` | rc 0 (`wrote` fourteen, `removed …bf6a3d2c…7cfd.json`); `--check` rc 0 `fixtures match` |
| `tests/integration/composition/test_analysis_profiles_over_http.py`, lane `.env` exported | `4 passed` |
| `npx vitest run tests/unit/analysis-settings` in `web/` (`node_modules` linked from `gate-night`) | 7 files, `95 passed` |
| governance one-liner on the task file | `[]` |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, `git diff --check` | see «Final checks» |

Free disk at the start of the lane 1.8 GiB, at the end 1.9 GiB (`df -h /`). No docker command, no push, no model call, no process killed.

## Integration notes

1. **The web label for `reviewed` still says «проверен экспертом»** and the `AnalysisProfileStatus` docstring says «a package an expert has reviewed» (see the `AI` report, integration note 1). Both are outside this lane (`web/**`, `src/auditmanager/api/**`); the decision is the integrator's, once for all fourteen lanes.
2. **Identity:** `analysis_profile_id` and `prompt_bundle_id` are unchanged (the lane mints none), while the bundle's text and hash and the profile hash changed. A stored run of the draft `KM` profile carries the old `analysis_profile_sha256` and `prompt_bundle_sha256`; the registry resolves by the id pair and serves only the new text. Development stand only, no migration (`R-146ah`).
3. **The recording's `origin`** still names `SECTION-RECORDINGS-01` as its authoring task and now says `profile_status: reviewed`; its statement still says it is not field evidence for the profile's review.
4. **e2e manifest:** the step with the selector `tr[data-profile="draft"]` stays valid while any other section is `draft` (`POS`, `OV`, `VK`, `PT`, `EOM`, `SS`, `ITP`, `GP`, `PB` at this base).
5. **Merge:** the expectations file changes on the `KM` line only, so lanes merge without conflict; re-run the section set, the HTTP test, the web test and `build_fixtures.py --check` after the last section merges.
6. **Record:** `W59-SECTION-PROFILES-01.md` still says «Every profile is `status: draft`» and lists the five questions as open (forbidden path for the lane). When it is updated, cite this report and say that no human reviewed the decisions (`A-7`).

## Limits

- No test holds the added sentence itself. Its wording is held only by the recording's request key (so an edit without a rebuild goes red, rows M5, M8 and M9), and the absence of a designation outside the source is held only by the manual audit (row M12); a new guard test is outside this lane's paths. A cross-section guard that checks each prompt's numerals and designations against its pinned source is a candidate for the integrator (the `AI` and `TX` reports say the same).
- The effect of the N edit on a model's answers is unmeasured; no model was called.
- An expert may disagree with any decision in the table, and the report says where.

## Forbidden paths untouched

`git diff --name-only --no-renames 8a032ded..HEAD` on the final tree prints exactly these seven paths, all inside the task's allowed paths (without `--no-renames` git folds the old recording into a rename and prints six):

```text
PLACEHOLDER-DIFF-LIST
```

No other section's files, no `W59-SECTION-PROFILES-01.md`, registry, `P02_LOCK.json`, `contracts/**`, migration, `web/**` or `infra/**` appears; `build_fixtures.py` is unchanged. The legacy repository was only read (`git status --short` there: 0 lines before and after).

## Final checks

PLACEHOLDER-FINAL
