# SECTION-SS-FULL-01 — the СС (SS) profile answers its open questions and is `reviewed`, without a human review

Task: `docs/program/tasks/SECTION-SS-FULL-01.md`. Branch `agent/section-ss-full-01`, base `f72144df` (`integration/ar-close-1026`, with `AI`, `PS`, `POS`, `TX`, `KJ`, `KM`, `OV` and `GP` already `reviewed`), product commit `b1d7573a`. Plan item `PROD-14` (section `SS`); owner rulings `R-146ag`, `R-146ah`, `R-146ai`; accepted risk `A-7`; template `SECTION-<CODE>-FULL-01` of `dispatch/PRODUCTION-WAVE-PW2B.md`. Executor: a Sonnet lane. No push, no tag, no container command, no model call, no process killed.

**Read this first (`A-7`).** Nobody reviewed this section: not an expert, not the owner. The status `reviewed` on the SS profile means a lane wrote a decision for every open question of its record and rebuilt its recording. It is **not** expert verification and must not be quoted as one.

## Result

The `SS` record in `W59-SECTION-PROFILES-01.md` has five open questions; the fifth asks two things, so there are six decisions: **K** five times (questions 1, 2, 3 and the two halves of 5) and **N** once (question 4). One more edit comes from the designation audit, not from a record question: the cable-execution examples «нг(А)-LS, нг(А)-FRLS», which the pinned source does not contain, are replaced by the source's own «FRLS/FR». The four cross-section questions are applied as the wave table fixes them (all **K**). No **X**. The prompt changed in two places, so `profile_version` is `1.1.0`, the recording is rebuilt, and `profile.json` and the `SS` line of the expectations file say `reviewed`.

Premise: **match.** Package, status and version, the five source hashes at the pinned commit, the five questions, the four cross-section questions, the expectations line and the one recording are as the brief says (task file, P-01 to P-08). The audit (P-09) is not clean for `SS`: the cable bullet carries a class designation that none of the five files holds, and the audit script of the earlier lanes did not see it (see «Audit» below).

## Decisions

Quoted question openings are the record's own words. «Condition n» means v1's numbered conditions in the prompt; «bullet n» counts the hint bullets from the top of the block «Где в документе раздела СС искать …» (eleven: 1 system types, 2 make and type of a device, 3 cable, 4 counts per apartment or floor, 5 reader and lock, 6 warning zone borders, 7 control-signal conditions, 8 signals to the control room and the channel, 9 battery capacity and runtime, 10 counts and cable length, 11 unfilled marks).

| # | Question (record) | Decision | Reason | Exact change |
|---|---|---|---|---|
| 1 | «тип оборудования уточнить по ТУ оператора связи», «по проекту оператора», «по согласованию с управляющей компанией»: placeholder (as v1) or an accepted reference to an external document? | **K** | Cross-section decision (1) applies. «уточнить по ТУ оператора связи» carries the literal mark «уточнить» of v1's second category. Condition 4 forgives only a reference to a table, schedule, specification, sheet, section or volume where the value is given; the technical conditions of a communications operator and an operator's project are not in that list, and the text does not say that the value stands in a volume of this documentation. «по согласованию с управляющей компанией» carries none of v1's marks; the profile neither lists nor excludes it, and v1's definition («и подобное») decides as before. Turning such a reference into an accepted instruction is an expert's call and would silence findings. | none |
| 2 | Fire alarm and СОУЭ are often issued as a separate volume (АПС, СОУЭ) outside section СС: keep them in this profile or move them to a separate one? | **K** | The pinned source keeps both inside SS: `role.md` lists «ОПС / АУПС» and «СОУЭ» among the areas of the section, `checklist.md` has a block for each and `finding_categories.md` a category for each (task file P-11). A separate profile needs a sixteenth section code and a new identity pair; the fifteen codes are held equal to the contract's `ProjectSection`, so that is a contract change and a new classification, outside a profile lane (`R-146ah`, no new identity). Dropping the bullets (X) is not justified: X is for a bullet that cannot be a same-document cross-check, and these can (system type, device make, zone borders, control-signal conditions, battery capacity are all written in several places of one document). When a volume holds only fire alarm and warning pages and is classified as SS, the bullets about the other systems find nothing to compare, and condition 5 keeps the empty places silent. | none |
| 3 | A list of signals to the control room, or the composition of an access point, is shorter in one place than in another: a contradiction or an incompleteness that condition 5 does not report? | **K** | Cross-section decision (4) applies: an item named in one place and absent from another is an omission, not two incompatible values, and a third kind of observation is a contract change. Condition 5 says «Утверждения просто нет … это не находка»; a shorter list says nothing about the item it leaves out. A real contradiction stays where two places give incompatible values for the same thing, for example two different channels of communication with the control room for the same object (bullet 8) or two lock types for the same door (bullet 5). The record's excluded list already keeps the required composition out («аварийные сигналы лифтов, датчики ИТП … как обязательный состав»). A sentence «a shorter list is not a contradiction» would also silence a list that one place declares exhaustive, and the lane cannot tell which case a text is in. | none |
| 4 | The number of СКС ports and TV outlets «на квартиру» often differs for different types of apartments: is condition 1 enough, or does this bullet give systematic false findings? | **N** | A stated false-positive source. Condition 1 names «квартирам» among the different objects and says «Ищи в тексте прямое указание на то, к чему относится значение», but nothing in the prompt says that apartments come in types; bullet 4 asks the model to compare the number «на одну квартиру или на этаж» across the note, the general notes and the riser diagram, and identifies the object only as «квартира». Where a document gives different numbers for different types, a bare «на квартиру» in two places is two values of two types, not one value. The source holds no notion of apartment types (task file P-12: «Количество портов на квартиру / этаж», «Количество ТВ-выводов на квартиру»), so the edit names no type, no number and no designation; «типов квартир» is the record's own wording. The edit only removes comparisons: values that the text ties to the same type, or to all apartments, are still compared. | bullet 4, see below |
| 5a | «Итого» of a specification or cable journal against the sum of its rows: a finding (recomputation is excluded now)? | **K** | Cross-section decision (2). Adding rows is arithmetic, which the exclusion paragraph keeps out («НЕ выполняешь и не перепроверяешь инженерные расчёты»); the prompt has no bullet that sums and no «итог» or «сумм» line (task file P-10). Bullet 10 compares quantities and cable length «прямо указанные» in the specification and in the text of the schemes, the cable journal or the note: two written totals that differ stay an `internal_contradiction` under v1; a total against its rows does not. | none |
| 5b | A ППКП's capacity against the number of address devices: a finding (this comparison is excluded now)? | **K** | Condition 2 already names this pair as two different characteristics («ёмкость прибора или контроллера и число фактически подключённых к нему устройств»), and no bullet compares a device's capacity with a count. To compare them is a capacity calculation, which the exclusion paragraph keeps out; the record's excluded list keeps «ПКП — ёмкость, расположение» and «контроллеры доступа: ёмкость, резервирование» out as an evaluation of sufficiency, and the source names the capacity of those devices without any count to set it against. If a text writes the capacity itself in two places with two values, that is one characteristic and v1 treats it as before. | none |
| A | Audit (not a record question): numerals and class designations of the prompt against the pinned source | **N** (edit by the audit rule) | `нг(А)-LS` and `нг(А)-FRLS`, the examples of cable execution in bullet 3, occur in none of the five files (`grep -c "нг(А)"` prints 0; task file P-09). The source's own form is «огнестойкость (FRLS/FR)» (`checklist.md`, ОПС / АУПС and СОУЭ). The rule forbids a class designation absent from the source in the section's profile, not only in additions. The bullet's scope stays «исполнение … кабеля одной и той же линии, шлейфа или магистрали», so the expected effect on findings is nil; it is a source-fidelity edit. | bullet 3, see below |

Cross-section decisions (the same for every lane; this lane agrees with them and has nothing to report against them):

| # | Question | Decision | SS-specific note |
|---|---|---|---|
| C1 | Site and contractor phrases | **K** | Covers question 1. |
| C2 | «Итого» against the sum of rows | **K** | Covers question 5a: the prompt has no recomputation bullet (task file, P-10). |
| C3 | Text read from sheets | **K** | One hint bullet reads labels on plans («в подписях планов», bullet 2; task file P-10). The SS record names it as no systematic false-positive source, so there is no bullet to narrow. Question 4 is about apartment types, not about detached text, and is decided on its own. |
| C4 | Missing items | **K** | Covers question 3. Condition 5 stays; the record's excluded list (what must be present) stays excluded. |

## The prompt change in words

Two edits in `system_prompt.md`, both inside the hint block; everything else is byte for byte what it was (the package tests hold v1's question, categories, conditions and output contract). `git diff f72144df..HEAD -- src/auditmanager/analysis/text/profiles/ss/system_prompt.md` is 8 lines added and 3 removed. Because no test holds the added words (only the recording's request key does), the exact text is given here.

1. **Bullet 3 (audit).** «(нг(А)-LS, нг(А)-FRLS)» becomes «(FRLS/FR)», and the bullet is re-wrapped around it. Nothing else in the bullet moved.
2. **Bullet 4 (question 4).** After «… на стояковой схеме;» the bullet continues:
   «для разных типов квартир это количество может быть разным, поэтому значения, отнесённые в тексте к разным типам или к разным квартирам, не противоречат друг другу; сопоставляй значения на квартиру, только если текст прямо относит оба к одному и тому же типу квартир или ко всем квартирам дома; значение, у которого не назван тип квартир и нет указания, что оно относится ко всем квартирам, не даёт основания для противоречия;»
   The sentence is about apartments only; the part of the bullet about a floor is as before.

New numerals: none. New norm references: none. New designations: none (one is removed and replaced by one the source holds). Findings: only narrower than before, or equal. The bundle's `content_sha256` moved `7cb97f2e…` to `3256b21c…` (the recording's `prompt_bundle_sha256`); the identities `ap_01M5AXG1KN9C7BDD3CCHMFTMX3` and `pb_01M5AXG1KNQRT6DYJWYC5X0C5J` are unchanged.

## Audit of numerals and designations

Run before and after the edit (task file P-09 has the base output). The script of the earlier lanes (below, «script 1») reports no digit-bearing token for `SS` and, at the base, reports `LS` and `А` as present in the source. It cannot see the defect: it tests each piece by substring, so `LS` inside `FRLS` and the single letter `А` pass although the notation `нг(А)-LS` does not occur. The lane found the notation by reading the bullet and added «script 2», which strips the surrounding punctuation of each whitespace-delimited token that holds a Latin letter, a digit or a bracket and tests the whole token. At the base script 2 reports `нг(А)-FRLS` and `нг(А)-LS` as `False`; after the edit it reports `(FRLS/FR)` as `True` and no designation of the section as `False`.

What remains that the source lacks, said plainly: only v1's own words (`TBD`, `XX`, `(?)`, upper-case emphasis such as `ЖЕ`, `НЕ`, `ТОГО`, `ТОМ`, and the field names of the output contract) and the section abbreviation in brackets «(СС)» in the opening sentence (the source has `СС` without brackets, `role.md`: «раздела СС»). No class designation, norm number or numeral of the section is kept that the source lacks. The audit can fail: with `(Г1–Г4)` put into condition 2 script 1 prints `'Г1–Г4' in legacy source: False` (row M12), and with the two cable notations put back script 2 prints the two `False` lines while script 1 stays silent (row M12b).

Script 1 (unchanged from the `OV` report):

```python
"""Audit: every digit-bearing token and capital-letter class designation in a section prompt
must occur in the section's five hash-pinned legacy files (read at the pinned commit)."""
import json, re, subprocess, sys
from pathlib import Path

root = Path(sys.argv[1])           # worktree
code = sys.argv[2]                 # e.g. SS
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

Script 2 (new in this lane; it lives outside the repository):

```python
"""Second pass of the designation audit: the first script tests each piece of a notation by substring,
so a short piece ('LS', 'А') passes through a longer notation the source lacks. This pass takes every
whitespace-delimited token of the prompt that holds a Latin letter, a digit or a bracket, strips the
surrounding punctuation, and tests the WHOLE token against the five pinned legacy files."""
import json, re, subprocess, sys
from pathlib import Path

root = Path(sys.argv[1]); code = sys.argv[2]
pdir = root / f"src/auditmanager/analysis/text/profiles/{code.lower()}"
prompt = (pdir / "system_prompt.md").read_text("utf-8")
manifest = json.loads((pdir / "profile.json").read_text("utf-8"))
legacy = Path("/root/projects/PDF-proverka")
src = ""
for f in manifest["source"]["files"]:
    src += subprocess.run(["git", "-C", str(legacy), "show", f"{manifest['source']['commit']}:{f['path']}"],
                          check=True, capture_output=True).stdout.decode("utf-8") + "\n"
body = re.sub(r"(?m)^\s*[1-5]\. ", "", prompt)
toks = set()
for raw in body.split():
    t = raw.strip(".,;:«»\"'!?—")
    # drop a trailing ")" that closes a phrase, keep brackets that open inside the token
    if t.endswith(")") and t.count("(") < t.count(")"):
        t = t[:-1]
    if t.startswith("(") and t.count("(") > t.count(")"):
        t = t[1:]
    if re.search(r"[A-Za-z0-9]", t) or "(" in t:
        toks.add(t)
for t in sorted(toks):
    print(f"  {t!r:22} whole token in legacy source: {t in src}")
```

Neither script reads Cyrillic-only vocabulary; the words are listed under «Assumptions», item 7. Cross-section suggestion for the integrator: a repository guard should use the whole-token form (this report and the `OV` one say the same about a guard).

## Assumptions an expert would still want to check

Short and honest (`A-7`): none of these was checked by anyone with domain knowledge.

1. **Question 1 (K).** «Тип оборудования уточнить по ТУ оператора связи» is still reported as a placeholder. A real SS document legitimately leaves the equipment type to the operator's conditions, so such findings will be frequent; the lane chose over-reporting to silencing. Whether a model also reports «по согласованию с управляющей компанией» is unmeasured.
2. **Question 2 (K).** A volume of fire alarm and warning pages classified as SS is checked by this profile, whose bullets cover those systems. Whether they should be a section of their own is a product decision (a new code), not a wording one.
3. **Question 3 (K).** A shorter list of signals or a shorter composition of an access point is not told apart from a list that one place declares exhaustive; a model may still report some such pairs as a contradiction. The expert may want a sentence in one direction.
4. **Question 4 (N).** Two bare «на квартиру» values (no type of apartments named, no «ко всем квартирам») that really contradict each other are no longer reported. How a model decides that a text relates a value «ко всем квартирам дома» was not measured. «Типов квартир» is the record's wording, not the source's. The sentence covers apartments only, not floors.
5. **Question 5 (K, K).** A total against the rows of a specification or cable journal, and a ППКП's capacity against the number of connected devices, are not reported.
6. **Audit (N).** The model now sees the cable execution as «(FRLS/FR)», less specific than the notation of the cable standard in use in practice. The lane did not add that notation because the source does not hold it; an expert may want the examples aligned with the cables the section really uses.
7. **Vocabulary not from the source.** Attribute words of the hint bullets that none of the five files contains, observed with a case-insensitive count over the five files and not changed because they are not numbers, norm references or class designations and no question touches them: «исполнение», «число пар или волокон», «ворот», «коммутатор», «источник питания», «позиционное обозначение», «кабельный журнал» (the record itself says the list of places is «дополненный кабельным журналом и таблицами адресов и подключений»), «управляющих сигналов», «алгоритм», «режим» (the source says «дежурный» and «тревога»), «номер шлейфа», «аккумуляторы» (the source says «АКБ»), «диспетчерский пункт» (the source says «пульт ОДС» and «диспетчерская»), «метраж», «таблица точек доступа». An expert may want them aligned or struck.
8. **Nothing was measured.** The recording is synthetic, authored by the builder over the AR corpus; it proves routing and replay and says nothing about how the profile performs on a real СС volume.

## Files changed

| File | Change |
|---|---|
| `src/auditmanager/analysis/text/profiles/ss/system_prompt.md` | the two edits above |
| `src/auditmanager/analysis/text/profiles/ss/profile.json` | `profile_version` `1.0.0` to `1.1.0`; `status` `draft` to `reviewed` |
| `fixtures/recorded/sections/ss/dd6ccee83f95994a6bff7ae3c088fbc56e29d8b4908178c44bea313b89cc70fa.json` | rebuilt by `build_fixtures.py`; replaces `9ed13e71…0bd5.json`; the differences against the old file are `origin.profile_status` (`reviewed`), `origin.prompt_bundle_sha256` (`3256b21c…8eab5`) and `request_sha256`; the authored reply, usage and latency are unchanged |
| `tests/unit/analysis/text_profiles/section_profile_expectations.json` | the `SS` line only: `reviewed`, `1.1.0` |
| `docs/program/tasks/SECTION-SS-FULL-01.md`, this report | records |

The builder writes all fourteen recordings; thirteen came out byte-identical (`git status` shows no other recording). No test file was edited, so no assertion was weakened: there is no before/after of a modified test to give. The one data line the tests read changed from `draft`/`1.0.0` to `reviewed`/`1.1.0`; before, the registry, package, guard, HTTP and web tests asserted that `profile.json` and the served row agree with the line (`draft`, `1.0.0`), after they assert the same agreement with the new values.

## Mutation table

Each row edits one thing in the committed tree (`b1d7573a`), runs the set named, restores with `git checkout HEAD --` (and deletes a temporary file), and proves the restore by a SHA-256 over the four files (prompt, `profile.json`, expectations, new recording) and an empty `git status --short` (`restored=True`, `status_clean=True` every time). The section set is `test_text_profile_registry.py`, `tests/unit/analysis/text_profiles`, `tests/integration/sections/test_section_recordings.py` and `tests/contract/analysis_packages` (211 cases). The unmutated tree: `211 passed`, before the first row and after the last.

| Mutation | Result | First red cases |
|---|---|---|
| M1 `profile.json` status `reviewed` back to `draft` (version kept) | 4 failed, 207 passed | registry `test_the_tree_registers_without_error_and_without_an_ar_package`; guard `test_every_line_agrees_with_its_package_profile_json`; packages `test_every_profile_manifest_has_the_text_profile_1_shape`; recordings `test_the_builder_reports_no_drift` |
| M2 `profile.json` version `1.1.0` back to `1.0.0` (status kept) | 3 failed, 208 passed | the first three of M1 |
| M3 the `SS` expectations line back to `draft` / `1.0.0` (`profile.json` kept) | 3 failed, 208 passed | the first three of M1 |
| M4 the `SS` expectations line, status only back to `draft` | 3 failed, 208 passed | the first three of M1 |
| M5 `system_prompt.md` back to the base text (recording kept) | 7 failed, 204 passed | recordings: `test_each_section_has_one_synthetic_recording_keyed_to_its_own_request[SS]`, `test_the_builder_reports_no_drift`, `test_the_served_adapter_answers_each_recorded_section_and_the_canonical_alone_does_not[SS]`, `test_no_other_directory_answers_a_section_request[SS]` and three more |
| M6 the recording back to the base file (new one removed) | 7 failed, 204 passed | the same recordings cases |
| M7 `origin.profile_status` `reviewed` to `draft` inside the new recording (key kept) | 1 failed, 210 passed | `test_the_builder_reports_no_drift` |
| M8a only the cable-designation edit undone (recording kept) | 7 failed, 204 passed | the same recordings cases as M5 |
| M8b only the per-apartment sentence removed (recording kept) | 7 failed, 204 passed | the same |
| M9 one character of the per-apartment sentence changed (a full stop inserted; recording kept) | 7 failed, 204 passed | the same |
| M10 the `SS` expectations line back to `draft` / `1.0.0`, on the lane stack | 1 failed, 3 passed | `test_analysis_profiles_over_http.py::test_every_row_is_the_registry_entry_the_application_routes_by` |
| M10 the same, in the web test | 1 failed, 94 passed | `has a line for exactly the packages that exist, with the status and version each declares`: `SS: status draft in the file, reviewed in profile.json` |
| M11 `profile.json` status back to `draft`, on the lane stack | 1 failed, 3 passed | the same HTTP case |
| M11 the same, in the web test | 1 failed, 94 passed | the same web case (`SS: status reviewed in the file, draft in profile.json`) |
| M12 «(Г1–Г4)» inserted into condition 2 | script 1 prints `'Г1–Г4' in legacy source: False` | not a repository test (see the limit below) |
| M12b the base cable bullet put back (`нг(А)-LS, нг(А)-FRLS`) | script 1 prints only `'LS'`, `'А'`, `'FRLS'` as `True`; script 2 prints `'нг(А)-FRLS'` and `'нг(А)-LS'` as `False` | not a repository test |

The red of the unit guards names the section: the `SS` row of the expectations test prints `'SS': {'expectations': ('reviewed', '1.1.0'), …}` against the mutated `profile.json`. A probe before the rebuild: with the prompt edited and the recording not rebuilt, the builder's `--check` exits 1 listing the new key and the old file as `(stale)`, and the 211-case set has 7 failed, 204 passed. The harness is the lane's own script (`mutate.py`, outside the repository); its single complete run is the source of every row.

## Commands and results

From `/root/projects/PDF-Analysis/.local/worktrees/section-ss-full-01`, shared venv, one pytest at a time. `$BS` is `/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages`.

| Command | Result |
|---|---|
| section set (above), base `f72144df` | `211 passed` |
| section set, after the change and the rebuild | `211 passed` |
| `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py`, then `--check` | rc 0 (`wrote` fourteen, `removed …9ed13e71…0bd5.json`); `--check` rc 0 `fixtures match` |
| `tests/integration/composition/test_analysis_profiles_over_http.py`, lane `.env` exported | `4 passed` |
| `npx vitest run tests/unit/analysis-settings` in `web/` (`node_modules` linked from `gate-night`) | 7 files, `95 passed` |
| governance one-liner on the task file | `[]` |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, `git diff --check` | see «Final checks» |

Free disk at the start of the lane 1.9 GiB, at the end 1.8 GiB (`df -h /`; the figure moves with other lanes). No docker command, no push, no model call, no process killed.

## Integration notes

1. **The web label for `reviewed` still says «проверен экспертом»** and the `AnalysisProfileStatus` docstring says «a package an expert has reviewed» (see the `AI` report, integration note 1). Both are outside this lane (`web/**`, `src/auditmanager/api/**`); the decision is the integrator's, once for all fourteen lanes.
2. **Identity:** `analysis_profile_id` and `prompt_bundle_id` are unchanged (the lane mints none), while the bundle's text and hash and the profile hash changed. A stored run of the draft `SS` profile carries the old `analysis_profile_sha256` and `prompt_bundle_sha256`; the registry resolves by the id pair and serves only the new text. Development stand only, no migration (`R-146ah`).
3. **The recording's `origin`** still names `SECTION-RECORDINGS-01` as its authoring task and now says `profile_status: reviewed`; its statement still says it is not field evidence for the profile's review.
4. **e2e manifest:** the step with the selector `tr[data-profile="draft"]` stays valid while any other section is `draft` (`VK`, `PT`, `EOM`, `ITP`, `PB` at this base).
5. **Merge:** the expectations file changes on the `SS` line only, so lanes merge without conflict; re-run the section set, the HTTP test, the web test and `build_fixtures.py --check` after the last section merges.
6. **Record:** `W59-SECTION-PROFILES-01.md` still says «Every profile is `status: draft`» and lists the five questions as open (forbidden path for the lane). When it is updated, cite this report and say that no human reviewed the decisions (`A-7`).
7. **A separate fire-alarm / warning-system profile** (question 2) is a product decision for a later wave: a sixteenth section code in `ProjectSection` and the registry, i.e. a contract change.

## Limits

- No test holds the added sentence itself. Its wording is held only by the recording's request key (so an edit without a rebuild goes red, rows M5, M8a, M8b and M9), and the absence of a designation outside the source is held only by the manual audit (rows M12 and M12b); a new guard test is outside this lane's paths. A cross-section guard that checks each prompt's tokens against its pinned source, whole token and not by piece, is a candidate for the integrator.
- The effect of the N edit on a model's answers is unmeasured; no model was called.
- An expert may disagree with any decision in the table, and the report says where.

## Forbidden paths untouched

`git diff --name-only --no-renames f72144df..HEAD` on the final tree prints exactly these seven paths, all inside the task's allowed paths (without `--no-renames` git folds the old recording into a rename and prints six):

```text
docs/program/SECTION-SS-FULL-01.md
docs/program/tasks/SECTION-SS-FULL-01.md
fixtures/recorded/sections/ss/9ed13e71c2a71fe0f616d21bac4057a83a5e24f8f8c88f1fe6e30b0a5cb90bd5.json
fixtures/recorded/sections/ss/dd6ccee83f95994a6bff7ae3c088fbc56e29d8b4908178c44bea313b89cc70fa.json
src/auditmanager/analysis/text/profiles/ss/profile.json
src/auditmanager/analysis/text/profiles/ss/system_prompt.md
tests/unit/analysis/text_profiles/section_profile_expectations.json
```

No other section's files, no `W59-SECTION-PROFILES-01.md`, registry, `P02_LOCK.json`, `contracts/**`, migration, `web/**` or `infra/**` appears; `build_fixtures.py` is unchanged. The legacy repository was only read (`git status --short` there: 0 lines before and after).

## Final checks

On the committed tree (`git status --short` empty), the last commit before this paragraph being `6ddb515a`:

| Command | Result |
|---|---|
| `pytest tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` | `105 passed` |
| governance one-liner on `docs/program/tasks/SECTION-SS-FULL-01.md` | `[]` |
| `git diff --check f72144df..HEAD` | rc 0 |
| section set, `build_fixtures.py --check`, HTTP test (lane `.env`), `vitest` analysis-settings | `211 passed`; `fixtures match` rc 0; `4 passed`; `95 passed` |

This paragraph is the only text added after `6ddb515a`; the contract run above was repeated on the tree that contains it (see the lane's final message for the tip SHA).
