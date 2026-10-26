# SECTION-EOM-FULL-01 — the ЭОМ (EOM) profile answers its open questions and is `reviewed`, without a human review

Task: `docs/program/tasks/SECTION-EOM-FULL-01.md`. Branch `agent/section-eom-full-01`, base `ae751f23437cc8a432e5d7f51635ae677ec51693` (`integration/ar-close-1026`, with `AI`, `PS`, `POS`, `TX`, `KJ`, `KM` and `GP` already `reviewed`), product commit `4ccc8880`. Plan item `PROD-14` (section `EOM`); owner rulings `R-146ag`, `R-146ah`, `R-146ai`; accepted risk `A-7`; template `SECTION-<CODE>-FULL-01` of `dispatch/PRODUCTION-WAVE-PW2B.md`. Executor: a Sonnet lane. No push, no tag, no container command, no model call, no process killed.

**Read this first (`A-7`).** Nobody reviewed this section: not an expert, not the owner. The status `reviewed` on the EOM profile means a lane wrote a decision for every open question of its record and rebuilt its recording. It is **not** expert verification and must not be quoted as one.

## Result

The `EOM` record in `W59-SECTION-PROFILES-01.md` has four open questions; the fourth asks two things, so there are five decisions: **K** four times and **N** once (question 4, second half). The four cross-section questions are applied as the wave table fixes them (all **K**). No **X**. The N decision is three lines appended to condition 1 of `system_prompt.md`; nothing else in the prompt moved. The prompt changed, so `profile_version` is `1.1.0`, the recording is rebuilt, and `profile.json` and the `EOM` line of the expectations file say `reviewed`.

Premise: **match.** Package, status and version, the five source hashes at the pinned commit, the four questions, the four cross-section questions, the expectations line and the one recording are as the brief says (task file, P-01 to P-08). The audit of numerals and class designations (P-09) is clean for `EOM`: the prompt has no digit-bearing token and every designation it uses occurs in the source, so nothing had to be removed and no notation is kept that the source lacks. One detail the record does not flag: the two phrases of question 1 («по месту», «при монтаже») occur in none of the five pinned files, so no decision may write them into the prompt, and none does.

## Decisions

Quoted question openings are the record's own words. «Condition n» means v1's numbered conditions in the prompt; «bullet n» counts the bullets of the hint block from the top (the list is under «Places of question 4a» below).

| # | Question (record) | Decision | Reason | Exact change |
|---|---|---|---|---|
| 1 | Формулировки «длины уточнить по месту», «уточнить при монтаже» — заполнитель (так по v1) или принятое указание монтажной организации? | **K** | Cross-section decision (1). Both phrases carry the literal mark «уточнить», which is v1's first example of an unfilled mark; condition 4 forgives only a reference to a table, schedule, specification, sheet, section or volume where the value is given, and «по месту» and «при монтаже» name no such place (they defer the value to the site and to the installer, and the text the model gets holds neither). Bullet 10 already points at exactly this place: marks of unfilled «в графах спецификации, кабельного журнала и таблиц нагрузок», and a length column of a cable journal is one of them. Turning such a deferral into an accepted instruction is an expert's call and would silence findings. The phrases are in the record, not in the source, so they are not added to the prompt as examples either; they stay under v1's «и подобное». | none |
| 2 | Считать ли находкой расхождение строки «Итого» таблицы нагрузок или спецификации с суммой строк (сейчас пересчёт исключён)? | **K** | Cross-section decision (2). Adding rows is arithmetic and the exclusion paragraph keeps it out («НЕ выполняешь и не перепроверяешь инженерные расчёты … Сравниваются только значения, прямо записанные в тексте»). The prompt has no recomputation bullet and no «Итого»: bullet 4 compares the design power as it is written in the general data, the explanations, the schemes and the load tables, and bullet 9 compares quantities «прямо указанные». Two *written* totals that differ stay an `internal_contradiction` under v1; a total against its rows does not. The source asks for the arithmetic only as an engineering check (`checklist.md`, «Расчётные формулы для сверки»), which the record lists as excluded. | none |
| 3 | Щит или аппарат, названный на схеме, но отсутствующий в спецификации, — нужна ли такая находка (в v1 это не категория)? | **K** | Cross-section decision (4): no third kind of observation, because it would be a contract change. Condition 5 stays («Утверждения просто нет … это не находка»). Bullet 3 compares the parameters of a panel that is written in both places, and bullet 9 compares a quantity written in both places; when one place does not name the item there is nothing to compare. The record's excluded list already says the same: «все щиты с плана присутствуют в спецификации» without a stated quantity is an omission, not two incompatible values. | none |
| 4a | Полон ли перечень мест сверки для типового комплекта ЭОМ стадий П и Р? | **K** | The list is a hint, not a list of required findings; a place absent at stage П yields nothing under condition 5. Every sheet type of `drawing_types.md` that carries attribute values maps onto a bullet (table below), except as stated there. Adding a place is adding a comparison, which is widening. Three things the record's «Kept» list holds have no dedicated bullet (the entry node, the power factor and the design current, the earthing sheet); they are listed under the assumptions for an expert to decide, and none is added here. | none |
| 4b | … и не даёт ли какой-то пункт систематических ложных находок? | **N** (condition 1, one object kind) | The record names no bullet, so the lane looked for a mechanism that the record or the source states. The record states one in its own «Excluded» list: «дубли групп (одинаковые обозначения)» — «одно обозначение у разных объектов по v1 (условие 1) не противоречие; оставлена сверка параметров одного и того же обозначения». Bullets 1 and 6 compare «одной и той же группы» and bullet 2 «одной и той же линии», and the prompt nowhere says what makes two mentions one group: condition 1 lists «группам» among the different objects and says only «Ищи в тексте прямое указание на то, к чему относится значение». A group designation is a display label, not an identity (`AGENTS.md` section 4: «path/filename/display number as identity» is forbidden). The sentence adds a condition before a comparison: the group is compared by its designation when the text puts both mentions at one panel, or when in the document the designation belongs to one panel only. It widens nothing and adds no number, norm reference or designation. It is limited to groups on purpose: the record says nothing about lines or panel designations, so those stay as v1 had them. A stricter reader who allows N only where the question names the bullet should read this row as K; the edit is three lines and reverts cleanly (mutation M8 shows the recording follows). | three lines appended to condition 1, see below |
| A | Audit (not a record question): numerals and class designations of the prompt against the pinned source | **K** (nothing to change) | P-09: no digit-bearing token; every designation (`ВРУ`, `ГРЩ`, `ЩР`, `ЩО`, `ЩД`, `ЩУ`, `УЗО`, `АВР`, `PE`, `ЭОМ`) is in the source; `ГОСТ`, `СП`, `ПУЭ` occur only in the exclusion paragraph, as what the model must not check. No notation is kept that the source lacks. The compound `PE-проводника` is not in the source as such (it has «PE-шины»); the token `PE` is, and the pair is a near-miss that tells the model not to compare, so it narrows. | none |

Cross-section decisions (the same for every lane; this lane agrees with them and has nothing to report against them):

| # | Question | Decision | EOM-specific note |
|---|---|---|---|
| C1 | Site and contractor phrases | **K** | Covers question 1. |
| C2 | «Итого» against the sum of rows | **K** | Covers question 2: the prompt has no recomputation bullet. |
| C3 | Text read from sheets | **K** | The record names no bullet whose false findings come from detached sheet text (P-10: «подписях планов» occurs in bullet 3 only, and question 4 says «какой-то пункт»). The N edit of question 4b is about the identity of a group, not about detached text, and is decided on its own. |
| C4 | Missing items | **K** | Covers question 3; condition 5 stays; the record's excluded list («наличие … требуется», «все щиты с плана присутствуют в спецификации») stays excluded. |

Places of question 4a, by sheet type of `drawing_types.md` and bullet of the hint block (bullets: 1 protective device of a group or line; 2 cable mark, cross-section and length of a line; 3 designation and parameters of a panel; 4 reliability category, network voltage, earthing system, design power; 5 current transformers and metering; 6 settings of residual-current devices and differential breakers; 7 consumers connected through the transfer switch; 8 cable marks of fire-protection lines; 9 quantities of identical panels, apparatus, luminaires and cable meterage; 10 marks of unfilled in schedules, journals and load tables):

| Sheet types | Bullet(s) |
|---|---|
| `single_line_diagram` | 1, 2, 3, 4, 5, 7, 8 |
| `panel_schedule` | 1, 3, 6 |
| `floor_plan`, `parking_plan` | 3 («в подписях планов») |
| `cable_routing` (cable journal) | 2, 10 |
| `specification` | 1, 2, 3, 5, 6, 8, 9, 10 |
| `general_notes` | 4, 7, 8 |
| `grounding` | 4 (the earthing system only); no dedicated place for the contour or bonding |
| `entry_node` | 2 (the cross-section of a line only); no dedicated place for the input node or its laying method |
| `title_block`, `detail`, `other` | none: no attribute values to compare |

The load tables named in bullets 4 and 10 are not a sheet type of the source; they are read wherever the text puts them.

## The prompt change in words

One edit in `system_prompt.md`; everything else is byte for byte what it was (the package tests hold v1's question, categories, conditions and output contract).

**Condition 1 (question 4b).** After the sentence «Ищи в тексте прямое указание на то, к чему относится значение.» three lines are added: the designation of a group does not by itself make two mentions the same group; compare a group by its designation only if the text directly places both mentions at one panel, or if in the document the designation belongs to one panel only.

New numerals: none. New norm references: none. New designations: none. Findings: only narrower than before. Bullets 1 and 6 are the ones affected; bullet 2 and every other bullet are not named in the sentence. The sentence does not say that groups of different panels bear the same designation; it only says what is required before two mentions are taken for one group.

`git diff ae751f23..HEAD -- src/auditmanager/analysis/text/profiles/eom/system_prompt.md` is 3 added lines and 0 removed. The bundle `content_sha256` moved `b775619f…` to `5bd11060…`; the identities `ap_01M5AXG1KKCKB70088QWAR8WD4` and `pb_01M5AXG1KKNVF7G99H0BB166TW` are unchanged. The wording of the sentence is pinned **only** by the recording key (rows M5, M8 and M9 below): a change to it without a rebuild is red, and a rebuilt recording over a changed prompt would pass.

## Audit of numerals and designations

Run before the edit (task file P-09) and after it: before and after, the prompt has no digit-bearing token, and the capital-letter tokens are the same twenty (the new sentence adds none). With a numeral and a designation put into condition 2 (mutation M12 below) the script reports `'IP65' … False` and `'С16' … False`, so it can fail. The script (it lives outside the repository; it is the one the `KM` and `GP` reports print, unchanged):

```python
"""Audit: every digit-bearing token and capital-letter class designation in a section prompt
must occur in the section's five hash-pinned legacy files (read at the pinned commit)."""
import json, re, subprocess, sys
from pathlib import Path

root = Path(sys.argv[1])           # worktree
code = sys.argv[2]                 # e.g. EOM
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

Limit of the script: a single-letter or short token is trivially found in any text by the substring test, and it tests designations and numerals only, not ordinary words (see assumption 6).

## Assumptions an expert would still want to check

Short and honest (`A-7`): none of these was checked by anyone with domain knowledge.

1. **Question 1 (K).** «длины уточнить по месту» in a cable-journal column is still reported as a placeholder (it carries «уточнить»); «уточнить при монтаже» likewise. A phrase without the mark («по месту», «при монтаже» alone) is decided by v1's definition («и подобное»), and nothing was measured. An expert may want the handover to the installer accepted.
2. **Question 2 (K).** A load-table «Итого» against the sum of its rows is not reported. A written «Итого» of the design power against the power in the general data is reported when the two differ and condition 2 does not separate them (it names «установленная и расчётная мощность»).
3. **Question 3 (K).** A panel or apparatus on a scheme and absent in the specification is not reported. Nothing was measured on how often that is the real defect of a set.
4. **Question 4a (K).** The record's «Kept» list holds three things that the prompt has no dedicated bullet for, and the lane added none because an added place is an added comparison: the entry node (the cross-section of input cables is covered through bullet 2 only for a line; the laying method has no place), the power factor and the design current (`project_params.md`: «Расчётные параметры (Рр, cos_phi, Iр, категория ЭС)»; bullet 4 names the design power but not them), and the earthing sheet beyond the earthing system.
5. **Question 4b (N).** Where a group designation stands in the text without its panel and occurs under more than one panel, a real mismatch between two mentions is no longer reported. How a model decides «belongs to one panel only» was not measured. The sentence covers groups only: line designations (bullet 2, cable journal numbers) and panel designations (which can repeat in different buildings or sections) are as in v1. One more possible source of false findings was seen and **not** acted on, because neither the record nor the source states it: the length of one line against the specification's meterage of a cable mark (bullets 2 and 9), which condition 2 does not name as a near-miss pair.
6. **Vocabulary not from the source.** Words in the prompt with no match in the five files (observed with `grep`, 0 matches each) and not changed, because they are not numbers, norm references or class designations and no question touches them: «секциям», «светильников», «уставки», «характеристика защитного аппарата», «приборов учёта», «дифференциальных автоматов» (the source says «дифавтоматов»), «противопожарной защиты» (the source says «СПЗ»), «номинальный ток» (the source says «Номинал»), «PE-проводника» (the source says «PE-шины»), «подписях планов», «пояснениях». An expert may want them aligned or struck.
7. **Nothing was measured.** The recording is synthetic, authored by the builder over the AR corpus; it proves routing and replay and says nothing about how the profile performs on a real ЭОМ volume.

## Files changed

| File | Change |
|---|---|
| `src/auditmanager/analysis/text/profiles/eom/system_prompt.md` | the one edit above |
| `src/auditmanager/analysis/text/profiles/eom/profile.json` | `profile_version` `1.0.0` to `1.1.0`; `status` `draft` to `reviewed` |
| `fixtures/recorded/sections/eom/966f4f6fd773c064d26b8e27a798967a919be2aa1d0c04ba80497829637d8098.json` | rebuilt by `build_fixtures.py`; replaces `71e5232e…1be1.json`; the diff against the old file is exactly three lines: `origin.profile_status` (`reviewed`), `origin.prompt_bundle_sha256` (`5bd11060…`) and `request_sha256`; the authored reply, usage and latency are unchanged |
| `tests/unit/analysis/text_profiles/section_profile_expectations.json` | the `EOM` line only: `reviewed`, `1.1.0` |
| `docs/program/tasks/SECTION-EOM-FULL-01.md`, this report | records |

The builder writes all fourteen recordings; thirteen came out byte-identical (`git status` showed no other recording). No test file was edited, so no assertion was weakened: there is no before/after of a modified test to give. The one data line the tests read changed from `draft`/`1.0.0` to `reviewed`/`1.1.0`; before, the registry, package, guard, HTTP and web tests asserted that `profile.json` and the served row agree with the line (`draft`, `1.0.0`), after they assert the same agreement with the new values.

## Mutation table

Each row edits one thing in the committed tree (`4ccc8880`), runs the section test set, restores with `git checkout` and proves the restore by a SHA-256 over the four product files (prompt, `profile.json`, expectations, new recording; `restored=True` and a clean `git status --short` every time). The set is `test_text_profile_registry.py`, `tests/unit/analysis/text_profiles`, `tests/integration/sections/test_section_recordings.py` and `tests/contract/analysis_packages` (211 cases). The unmutated tree: `211 passed`. One complete run; no correction of the harness was needed.

| Mutation | Result | First red cases |
|---|---|---|
| M1 `profile.json` status `reviewed` back to `draft` (version kept) | 4 failed | registry `test_the_tree_registers_without_error_and_without_an_ar_package`; guard `test_every_line_agrees_with_its_package_profile_json`; packages `test_every_profile_manifest_has_the_text_profile_1_shape`; recordings `test_the_builder_reports_no_drift` |
| M2 `profile.json` version `1.1.0` back to `1.0.0` (status kept) | 3 failed | the first three of M1 |
| M3 the `EOM` expectations line back to `draft` / `1.0.0` (`profile.json` kept) | 3 failed | the first three of M1 |
| M4 the `EOM` expectations line, status only back to `draft` | 3 failed | the first three of M1 |
| M5 `system_prompt.md` back to the base text (recording kept) | 7 failed | recordings: `test_each_section_has_one_synthetic_recording_keyed_to_its_own_request[EOM]`, `test_the_builder_reports_no_drift`, `test_the_served_adapter_answers_each_recorded_section_and_the_canonical_alone_does_not[EOM]`, `test_no_other_directory_answers_a_section_request[EOM]`, `test_a_section_reply_filed_under_another_key_is_not_replayed[EOM]`, `test_each_recording_replays_through_the_stage_under_its_own_profile[EOM]`, `test_every_recording_carries_its_own_authored_usage_signature` |
| M6 the recording back to the base file (new one removed) | 7 failed | the same seven as M5 |
| M7 `origin.profile_status` `reviewed` to `draft` inside the new recording (key kept) | 1 failed | `test_the_builder_reports_no_drift` |
| M8 only the added N sentence removed from the prompt (recording kept) | 7 failed | the same seven as M5 |
| M9 one character of the N sentence changed (a full stop inserted; recording kept) | 7 failed | the same seven as M5 |
| M10 the `EOM` expectations line back to `draft` / `1.0.0`, on the lane stack | 1 failed, 3 passed | `test_analysis_profiles_over_http.py::test_every_row_is_the_registry_entry_the_application_routes_by` |
| M10 the same, in the web test | 1 failed, 94 passed | `has a line for exactly the packages that exist, with the status and version each declares`: `EOM: status draft in the file, reviewed in profile.json` |
| M11 `profile.json` status back to `draft`, on the lane stack | 1 failed, 3 passed | the same HTTP case |
| M11 the same, in the web test | 1 failed, 94 passed | the same web case (`EOM: status reviewed in the file, draft in profile.json`) |
| M12 «(степень защиты IP65, ступень С16)» inserted into condition 2 | the audit script prints `'IP65' in legacy source: False` and `'С16' in legacy source: False` | not a repository test (see the limit below) |

After each restore the SHA-256 was equal to the one taken before and the tests were green again (`211 passed`; HTTP `4 passed`; web `95 passed`). A probe before the rebuild: with the prompt edited and the recording not rebuilt, the builder's `--check` exits 1 listing the new key and the old file as `(stale)`, and the 211-case set has 7 failed, 204 passed.

## Commands and results

From `/root/projects/PDF-Analysis/.local/worktrees/section-eom-full-01`, shared venv, one pytest at a time. `$BS` is `/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages`.

| Command | Result |
|---|---|
| section set (above), base `ae751f23` | `211 passed` |
| section set, after the change and the rebuild | `211 passed` |
| `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py`, then `--check` | rc 0 (`wrote` fourteen, `removed …71e5232e…1be1.json`); `--check` rc 0 `fixtures match` |
| `tests/integration/composition/test_analysis_profiles_over_http.py`, lane `.env` exported | `4 passed` |
| `npx vitest run tests/unit/analysis-settings` in `web/` (`node_modules` linked from `gate-night`, untracked) | 7 files, `95 passed` |
| governance one-liner on the task file | `[]` |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, `git diff --check` | see «Final checks» |

Free disk at the start of the lane 1.8 GiB, at the end 1.8 GiB (`df -h /`). No docker command, no push, no model call, no process killed.

## Integration notes

1. **The web label for `reviewed`** was a false statement under `A-7` («проверен экспертом»); the `GP` report records it as already changed on its base by `607ee47a`. This lane touches no web file.
2. **Identity:** `analysis_profile_id` and `prompt_bundle_id` are unchanged (the lane mints none), while the bundle's text and hash and the profile hash changed. A stored run of the draft `EOM` profile carries the old `analysis_profile_sha256` and `prompt_bundle_sha256`; the registry resolves by the id pair and serves only the new text. Development stand only, no migration (`R-146ah`).
3. **The recording's `origin`** still names `SECTION-RECORDINGS-01` as its authoring task and now says `profile_status: reviewed`; its statement still says it is not field evidence for the profile's review.
4. **e2e manifest:** the step with the selector `tr[data-profile="draft"]` stays valid while any other section is `draft` (`OV`, `VK`, `PT`, `SS`, `ITP`, `PB` at this base).
5. **Merge:** the expectations file changes on the `EOM` line only, so lanes merge without conflict; re-run the section set, the HTTP test, the web test and `build_fixtures.py --check` after the last section merges. This lane's base lacks sections merged later (`OV` on the integration tip); the builder wrote the thirteen other recordings byte-identically against this base only.
6. **Record:** `W59-SECTION-PROFILES-01.md` still says «Every profile is `status: draft`» and lists the four EOM questions as open (forbidden path for the lane). When it is updated, cite this report and say that no human reviewed the decisions (`A-7`).
7. **Judge:** read the decisions table against the five legacy files named in P-02 and P-10, not against this lane's summary; row 4b is the one decision whose stated source is the record's «Excluded» list and not the question.

## Limits

- No test holds the added sentence itself. Its wording is held only by the recording's request key (so an edit without a rebuild goes red, rows M5, M8 and M9), and the absence of a designation outside the source is held only by the manual audit (row M12); a new guard test is outside this lane's paths. A cross-section guard that checks each prompt's numerals and designations against its pinned source is a candidate for the integrator (the `AI`, `TX`, `KM` and `GP` reports say the same).
- The effect of the N edit on a model's answers is unmeasured; no model was called.
- An expert may disagree with any decision in the table, and the report says where.

## Forbidden paths untouched

`git diff --name-only --no-renames ae751f23437cc8a432e5d7f51635ae677ec51693..HEAD` on the final tree prints exactly these seven paths, all inside the task's allowed paths (without `--no-renames` git folds the old recording into a rename and prints six):

```text
docs/program/SECTION-EOM-FULL-01.md
docs/program/tasks/SECTION-EOM-FULL-01.md
fixtures/recorded/sections/eom/71e5232e87603a99d0f8dd688b8a2457e229824163bcee3e60959d3199964be1.json
fixtures/recorded/sections/eom/966f4f6fd773c064d26b8e27a798967a919be2aa1d0c04ba80497829637d8098.json
src/auditmanager/analysis/text/profiles/eom/profile.json
src/auditmanager/analysis/text/profiles/eom/system_prompt.md
tests/unit/analysis/text_profiles/section_profile_expectations.json
```

No other section's files, no `W59-SECTION-PROFILES-01.md`, registry, `P02_LOCK.json`, `contracts/**`, migration, `web/**` or `infra/**` appears; `build_fixtures.py` is unchanged. The legacy repository was only read (`git status --short` there: 0 lines before and after).

## Final checks

See the lane's final message for the tip SHA and the last runs on the committed tree.
