# SECTION-PB-FULL-01 — the ПБ (PB) profile answers its open questions and is `reviewed`, without a human review

Task: `docs/program/tasks/SECTION-PB-FULL-01.md`. Branch `agent/section-pb-full-01`, base `82068f3bfdcc54ff1725dc813482112accb17234` (`integration/ar-close-1026`, with `AI`, `PS`, `POS`, `TX`, `KJ`, `KM`, `OV`, `VK`, `EOM` and `GP` already `reviewed`), product commit `a6484e75`. Plan item `PROD-14` (section `PB`); owner rulings `R-146ag`, `R-146ah`, `R-146ai`; accepted risk `A-7`; template `SECTION-<CODE>-FULL-01` of `dispatch/PRODUCTION-WAVE-PW2B.md`. Executor: a Sonnet lane. No push, no tag, no container command, no model call, no process killed.

**Read this first (`A-7`).** Nobody reviewed this section: not an expert, not the owner. The status `reviewed` on the PB profile means a lane wrote a decision for every open question of its record and rebuilt its recording. It is **not** expert verification and must not be quoted as one. `PB` is also the weakest of the fourteen in one respect the others do not share: it has **no pinned source at all** (`"source": null`). Its hint block, its near-miss pairs and its vocabulary were authored by an earlier lane (`PB-PROFILE-01`) without any reference text, and nothing in this lane checks them against one. The decisions below therefore stay inside v1's wording and the record's own statements.

## Result

The `PB` record (`PB-PROFILE-01.md` and the package's `open_questions.md`) has eleven open questions, each single-barrelled, so there are eleven decisions: **K** ten times and **N** once (question 4). The four cross-section questions are applied as the wave table fixes them (all **K**). No **X**. The N decision restores one phrase of v1 in condition 1 of `system_prompt.md`; nothing else in the prompt moved. The prompt changed, so `profile_version` is `1.1.0`, the recording is rebuilt, and `profile.json` and the `PB` line of the expectations file say `reviewed`. `open_questions.md` keeps all eleven questions, carries a decision under each, and its opening paragraph now tells the truth under `R-146ag` (it said the profile is not counted until an expert answers, and that it has no recorded answers; both were untrue after this lane, and the second had been stale since `SECTION-RECORDINGS-01`).

The profile could honestly leave `draft` under the definition of `R-146ag` (every open question answered by a written decision, the recording rebuilt, the expectations line says `reviewed`, no human review): all three hold. Whether ten answers of the kind «no source to decide from» deserve the word is the integrator's call; the revert is cheap (see the integration notes) and the prompt edit does not depend on the status.

Premise: **match, with two corrections of prose.** Package, status and version, `source: null`, the eleven questions, the four cross-section questions, the expectations line and the one recording are as the brief says (task file, P-01 to P-08). The audit (P-09) is clean for `PB`: no token is in neither v1's prompt nor the record. Two things the record did not say: (1) the PB list of «different objects» in condition 1 had **lost** v1's «частям здания» (P-10) — the one place where v1's own wording answers a risk that the record states; (2) the opening paragraph of `open_questions.md` claimed «записанных ответов у профиля нет», which `SECTION-RECORDINGS-01` had already made untrue (the answer is synthetic, but it exists).

## Decisions

Quoted question openings are the record's own words (`open_questions.md`, numbering as there). «Condition n» means v1's numbered conditions in the prompt. «Basis» names what the decision rests on: **v1** (the wording the prompt keeps from v1), **record** (a statement in `PB-PROFILE-01.md` or in the question file), **cross** (a cross-section decision), **none** (a fire-safety domain call that neither v1 nor the record gives: K, «no source to decide from»).

| # | Question (record) | Decision | Basis | Reason | Exact change |
|---|---|---|---|---|---|
| 1 | Полон ли перечень мест, которые сверяются между собой? Какие места эксперт сверяет в первую очередь, а какие на практике не сверяются? | **K** | none | The list is a hint, not a list of required findings (the prompt says so in its own words); a place absent from a document yields nothing under condition 5. Which place experts compare first is practice, with no source. Adding a place adds a comparison (widening); dropping one silently hides a class of findings, and nothing in the record shows that a place cannot be a same-document cross-check (X is not justified). | none |
| 2 | Нужно ли отдельное правило для раздела, разнесённого на несколько томов? | **K** | v1 | The profile sees one document's text layer. A value filed in another file of the set is, when the text refers to it, an accepted decision by condition 4; silence is not a finding by condition 5. A rule for a multi-volume section would have to tell the model what the set contains, which it does not know. | none |
| 3 | «REI 60» в одном месте, «EI 60» (или «R 60») в другом для той же конструкции: разные показатели или противоречие? | **K** | none | `REI`, `EI` and `R` occur only in this question, not in the prompt. Whether the two writings are one characteristic depends on which limit states a writing includes: a fire-safety call that v1 and the record do not make. Both ways are unsafe without a source: forbidding the comparison would hide a real discrepancy of two writings for one structure; equating them would present a guess about the norms as fact. What remains is condition 2 («буквально одна и та же характеристика») and the expert who accepts or rejects the observation. The record does not call this a systematic false-positive source. | none (the pair is not added to condition 2) |
| 4 | Здание смешанного назначения имеет несколько классов функциональной пожарной опасности. Достаточно ли условия 1, или сверка по зданию целиком даст систематические ложные находки? | **N** (condition 1, one phrase) | v1 + record | The record names mixed-use buildings as a source of false findings (`PB-PROFILE-01.md`, «Risks»), and the question itself says that different parts carry different classes. v1's list of different objects reads «зданиям, сооружениям, этажам, частям здания, помещениям или конструкциям»; the PB list kept every other v1 kind and added PB's own, but **dropped «частям здания»** (P-10). It is restored. Values that the text attributes to different parts of one building are now named values of different objects. Nothing is added that v1 does not already say: no number, designation or norm; findings only fewer. What a part of a building is in a given document is still read from the text (condition 1: «Ищи в тексте прямое указание на то, к чему относится значение»). | «частям здания,» added to the list of condition 1; the five lines of the condition re-wrap, no other word moves |
| 5 | Категория помещения по взрывопожарной и пожарной опасности и класс зоны указываются с разной детализацией (категория помещения против категории здания). Где граница между «разные признаки» и противоречием? | **K** | v1 | A room and a building are different objects and both are named in condition 1 («зданиям», «помещениям»); whether two writings are one characteristic is condition 2. Where the line runs between a room category, a building category and a zone class is a fire-safety call with no source; a near-miss pair added to condition 2 would be that call written into the prompt. | none |
| 6 | Нумерация этажей (подземные, технический, «-1», «цокольный») различается между текстом, экспликацией и планами. Один объект под разными названиями или разные этажи? | **K** | none | Whether «-1», «цокольный» and «подземный» name one floor is a naming convention of the set; no source. Condition 1 already names floors as different objects and requires a direct indication in the text of what a value refers to. «Different names mean different floors» would hide a discrepancy between two writings of one floor; «equate them» would present a guess as fact. | none |
| 7 | «Принято по специальным техническим условиям», «по СТУ», «в соответствии с расчётом пожарного риска» там, где ожидалось значение: заполнитель или принятое решение? | **K** | v1 + cross | Without a mark of non-completion the phrases are not an `explicit_placeholder` under v1: the category needs a literally left mark («уточнить», «уточняется», «TBD», «XX», «___», «(?)» and the like), and a reference to a document is not one. Where «уточнить» stands beside them, cross-section decision 1 (K) applies: a document outside condition 4's list stays a placeholder, and accepting it is an expert's call. Adding «СТУ» or «расчёт пожарного риска» to condition 4 would accept an outside document as a decision and silence findings. `СТУ` is not written into the prompt. | none |
| 8 | «Уточнить на следующей стадии», «уточняется проектом противодымной защиты»: допустимая отсылка или заполнитель? | **K** | cross | Both carry the root «уточн» and name no table, schedule, specification, sheet, section or volume where the value is given, so under v1 they stay a placeholder unless the text itself shows where the value is (condition 4). Cross-section decision 1. The profile does not see the other volume and cannot tell a legitimate reference from a placeholder; the expert does it by accepting or rejecting the observation. | none |
| 9 | Исключены как расчёт: время эвакуации, значение пожарного риска, расходы и давления. Итоговое значение, прямо записанное в тексте, сравнивается как значение. Устраивает ли граница, или итоговые величины тоже исключить? | **K** | v1 + cross | The prompt compares only values written in the text and recomputes nothing («Сравниваются только значения, прямо записанные в тексте»). Two written totals of one result that differ are an `internal_contradiction` under v1; excluding totals would hide exactly those. Cross-section decision 2: a total against its rows is not recomputed. | none |
| 10 | Нормы названы только как перечень того, что профиль не проверяет: 123-ФЗ и своды правил серии 13130. Нужны ли другие семейства или лучше не называть ни одно? | **K** | v1 + record | v1 already names the families that the question lists, as «СП, СНиП, ГОСТ, техническим регламентам»; building-norm codes are «СП» and equipment standards are «ГОСТ». A further name would be a number or designation that is in neither v1 nor the record. The two identifiers of the record stay: they stand only in the sentence that tells the model what **not** to check, and striking them would weaken that exclusion. Their source is `W57-PLAN.md` and the record, not a pinned file (see the assumptions). | none |
| 11 | Какой раздел эксперт подтверждает тому, где пожарная безопасность изложена главой в `PS`, и не следует ли применять `PB` только к самостоятельному разделу? | **K** | record | The section of a version is fixed by the confirmation of its section (routing), not by the prompt: a version confirmed as `PS` goes to the `PS` profile, one confirmed as `PB` to the `PB` profile (`PB-PROFILE-01.md`). Which section to confirm for such a volume, and whether to restrict the profile, is a decision about confirmation with no source here; the registry and routing are outside the lane's paths. | none |
| A | Audit (not a record question): numerals, norm references and class designations of the prompt against v1's prompt and the record | **K** (nothing to change) | v1 + record | P-09: no token in neither. The prompt has no class designation, no clause number, no limit; `123-ФЗ` and `13130` are the record's. Nothing was removed (`remove nothing that v1 itself says`), and nothing is in the prompt that the record does not say. | none |

Cross-section decisions (the same for every lane; this lane agrees with them and has nothing to report against them):

| # | Question | Decision | PB-specific note |
|---|---|---|---|
| C1 | Site and contractor phrases | **K** | Covers questions 7 and 8. |
| C2 | «Итого» against the sum of rows | **K** | Covers question 9. The prompt has no «Итого» and no recomputation bullet (P-10). |
| C3 | Text read from sheets | **K** | The record names no bullet whose false findings come from detached sheet text. «в подписях значений на планах и схемах» (last hint bullet) stays as it was. |
| C4 | Missing items | **K** | No third kind of observation; condition 5 stays. |

Decisions 3, 5 and 6 (and the part of 1 that asks about practice) are the ones that rest on **none**: the lane did not invent a fire-safety rule, and the report lists them again under the assumptions.

## The prompt change in words

One edit in `system_prompt.md`; everything else is byte for byte what it was (the package tests hold v1's question, categories, conditions and output contract, and the hint block's five areas).

**Condition 1 (question 4).** In the list of different objects the words «частям здания,» are inserted after «зданиям,» and the condition re-wraps over the same five lines. The result reads «Значения относятся к разным зданиям, частям здания, сооружениям, пожарным отсекам, секциям, этажам, лестничным клеткам, эвакуационным выходам, помещениям, зонам противодымной защиты, системам или конструкциям.» The phrase is v1's own (its list reads «…этажам, частям здания, помещениям…»).

New numerals: none. New norm references: none. New designations: none. Findings: only fewer than before, never more. `git diff 82068f3b..HEAD --word-diff -- …/system_prompt.md` shows one inserted token pair, `частям здания,`; `--numstat` is 5 added, 5 removed (the re-wrap). The bundle `content_sha256` moved `69f04bdc…` to `5f7e5b5c…`; the identities `ap_01M5G4NZVKNZJYH722M0SXXP3X` and `pb_01M5G4NZVKHM9GP4EH22JACW2X` are unchanged. The wording of the phrase is pinned **only** by the recording key (rows M5, M8 and M9 below): a change to it without a rebuild is red, and a rebuilt recording over a changed prompt would pass.

`open_questions.md` (not read by the model; the loader reads `system_prompt.md` only): the opening paragraph is rewritten, a «Решение» paragraph follows each of the eleven questions, and the old closing paragraph about the cross-section questions becomes a section «Общие вопросы» with the four decisions. No question was deleted or renumbered, `D-178` is named in the opening paragraph, and the word `draft` is kept there as history («до задачи … профиль был `draft`») so the file reads the same under either status.

## Audit of numerals and designations

PB has no pinned source, so the audit is against v1's prompt and the PB record. Run before the edit (task file P-09) and after it, with the record read **as it stood at the base commit** (so the decisions this lane appended to `open_questions.md` cannot vouch for tokens they introduce): before and after, the digit-bearing tokens are `123-ФЗ` and `13130` and every capital-letter token is in v1's prompt or in the record; no row prints `NEITHER`. With a numeral and designations put into the prompt (mutation M12 below: `(С0, К1)` into condition 2 and `(СП 2.13130, п. 5.4.2)` into condition 1) the script prints `NEITHER` for `'С0'`, `'К1'` and `'13130,'`, so it can fail. The script lives outside the repository:

```python
"""Designation audit for the authored PB prompt: every digit-bearing token and every
capital-letter designation of the PB system prompt must occur in v1's SYSTEM_PROMPT
(src/auditmanager/analysis/text/prompt.py) or in the PB record (PB-PROFILE-01 report,
its task file, and the package's open_questions.md). PB has no pinned legacy source."""
import re, subprocess, sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "src"))
from auditmanager.analysis.text.prompt import SYSTEM_PROMPT as V1

pb = (root / "src/auditmanager/analysis/text/profiles/pb/system_prompt.md").read_text("utf-8")
record_files = [
    "docs/program/PB-PROFILE-01.md",
    "docs/program/tasks/PB-PROFILE-01.md",
    "src/auditmanager/analysis/text/profiles/pb/open_questions.md",
]
BASE = sys.argv[2]  # the record is read as it stood at the base commit
record = "\n".join(subprocess.run(["git", "-C", str(root), "show", f"{BASE}:{f}"], check=True,
                                  capture_output=True).stdout.decode("utf-8") for f in record_files)
body = re.sub(r"(?m)^\s*[1-5]\. ", "", pb)
digit = sorted(set(re.findall(r"[A-Za-zА-ЯЁа-яё]*\d[\d,–\-]*[A-Za-zА-ЯЁа-яё\d]*", body)))
desig = sorted(set(re.findall(r"\b[А-ЯA-Z]{1,4}\d?[\d,]*(?:[–\-][А-ЯA-Z]{0,4}\d+)?\b", body)))
mixed = sorted(set(re.findall(r"\b[A-Za-z]+-[A-Za-zА-Яа-яЁё]+|№\s*\S+", body)))
def row(t):
    in_v1, in_rec = t in V1, t in record
    return f"  {t!r:18} in v1 prompt: {in_v1!s:5}  in PB record: {in_rec!s:5}  {'NEITHER' if not (in_v1 or in_rec) else ''}"
print("digit-bearing tokens:", digit)
for t in digit: print(row(t))
print("capital designations:", desig)
for t in desig: print(row(t))
print("hyphenated Latin / numero tokens:", mixed)
for t in mixed: print(row(t))
```

Limits of the script: a short or single-character token is trivially found by the substring test, and it tests designations and numerals only, not ordinary words. Ordinary words are reported once in P-09 (397 distinct words of four or more letters; 88 share no six-letter stem with v1 or the record; they are the inflected domain vocabulary of the hint block, and none states a rule). The record is itself an authored document, so «in the record» means «written by the authoring lane», not «verified».

## Assumptions an expert would still want to check

Short and honest (`A-7`): none of these was checked by anyone with domain knowledge.

1. **The whole hint block is unverified.** Nine bullets of places to cross-check, five near-miss pairs, the stair types («обычная, незадымляемая, наружная»), «тамбур-шлюзов» and the rest of the vocabulary were authored by `PB-PROFILE-01` from the usual composition of a fire-safety section and have no source. Question 1 (K) leaves them as they are.
2. **Question 3 (K).** «REI 60» against «EI 60» (or «R 60») for one structure is left to condition 2 and to the expert. A model may or may not report it; nothing was measured. An expert may want the pair declared two indicators, or one.
3. **Question 4 (N).** Where the text attributes a class to «a part of the building», a mismatch with the class of the whole is no longer reported. How a model decides that something is a «part» (and how that interacts with «секциям» and «пожарным отсекам», which were already in the list) was not measured. The class designations themselves are not in the prompt.
4. **Questions 5 and 6 (K).** The boundary between room category, building category and zone class, and whether «-1» is the same floor as «цокольный» or «подземный», are not decided. A real discrepancy hidden behind one of these names is reported or not as v1's wording lets the model decide.
5. **Questions 7 and 8 (K).** «По СТУ» and «в соответствии с расчётом пожарного риска» without a mark of non-completion are not reported; «уточнить на следующей стадии» is. An expert may want the first kind noted or the second kind accepted.
6. **Question 9 (K).** Two written totals of one calculation that differ are reported; the calculation is not redone. An expert may want results of calculations left out of the comparison altogether.
7. **Question 10 (K).** `123-ФЗ` and `13130` have no pinned source: they come from the record, which took them from `docs/program/dispatch/W57-PLAN.md` (corpus list), and the norms corpus manifest was not read by either lane. The prompt uses them only as what the model must not check. An expert may want them struck or aligned with the series the corpus holds.
8. **Question 11 (K).** Which section to confirm for a volume that holds fire safety as a chapter is decided by whoever confirms sections, not by this profile.
9. **Nothing was measured.** The recording is synthetic, authored by the builder over the AR corpus; it proves routing and replay and says nothing about how the profile performs on a real fire-safety volume (`A-5`, `A-7`).

## Files changed

| File | Change |
|---|---|
| `src/auditmanager/analysis/text/profiles/pb/system_prompt.md` | the one edit above |
| `src/auditmanager/analysis/text/profiles/pb/profile.json` | `profile_version` `1.0.0` to `1.1.0`; `status` `draft` to `reviewed` |
| `src/auditmanager/analysis/text/profiles/pb/open_questions.md` | opening paragraph rewritten; a decision under each of the eleven questions; the cross-section pointer turned into the section «Общие вопросы» |
| `fixtures/recorded/sections/pb/eb53a861df61d016fcb7280b723e04c32aed367b70c47cc18863f292c9e60775.json` | rebuilt by `build_fixtures.py`; replaces `153d0c01…6ad0.json`; the diff against the old file is exactly three lines: `origin.profile_status` (`reviewed`), `origin.prompt_bundle_sha256` (`5f7e5b5c…`) and `request_sha256`; the authored reply, usage and latency are unchanged |
| `tests/unit/analysis/text_profiles/section_profile_expectations.json` | the `PB` line only: `reviewed`, `1.1.0` |
| `docs/program/tasks/SECTION-PB-FULL-01.md`, this report | records |

The builder writes all fourteen recordings; thirteen came out byte-identical (`git status` showed no other recording). No test file was edited, so no assertion was weakened: there is no before/after of a modified test to give. The one data line the tests read changed from `draft`/`1.0.0` to `reviewed`/`1.1.0`; before, the registry, package, guard, HTTP and web tests asserted that `profile.json` and the served row agree with the line (`draft`, `1.0.0`), after they assert the same agreement with the new values. `test_pb_open_questions_are_listed_in_the_package` asserted before and asserts after: at least eight numbered questions, numbered 1..n without a gap, `D-178` present, no carriage return, final newline, and `` `draft` `` present only while the expectations line says `draft`.

## Mutation table

Each row edits one thing in the committed tree (`a6484e75`), runs the section test set, restores with `git checkout` and proves the restore by a SHA-256 over the five product files (prompt, `profile.json`, `open_questions.md`, expectations, new recording; `restored=True` and a clean `git status --short` every time). The set is `test_text_profile_registry.py`, `tests/unit/analysis/text_profiles`, `tests/integration/sections/test_section_recordings.py` and `tests/contract/analysis_packages` (211 cases). The unmutated tree: `211 passed`. The harness lives outside the repository; one complete run, plus one rerun of M16 after its label and cut were corrected (the first cut left a gap in the numbering instead of three questions; the corrected one is what the table shows).

| Mutation | Result | First red cases |
|---|---|---|
| M1 `profile.json` status `reviewed` back to `draft` (version kept) | 5 failed | registry `test_the_tree_registers_without_error_and_without_an_ar_package`, `test_the_tree_registers_all_fifteen_sections_pb_included`; guard `test_every_line_agrees_with_its_package_profile_json`; packages `test_the_authored_profile_declares_no_source_and_the_expected_status`; recordings `test_the_builder_reports_no_drift` |
| M2 `profile.json` version `1.1.0` back to `1.0.0` (status kept) | 4 failed | the first four of M1 |
| M3 the `PB` expectations line back to `draft` / `1.0.0` (`profile.json` kept) | 4 failed | the first four of M1 |
| M4 the `PB` expectations line, status only back to `draft` | 4 failed | the first four of M1 |
| M5 `system_prompt.md` back to the base text (recording kept) | 7 failed | recordings: `test_each_section_has_one_synthetic_recording_keyed_to_its_own_request[PB]`, `test_the_builder_reports_no_drift`, `test_the_served_adapter_answers_each_recorded_section_and_the_canonical_alone_does_not[PB]`, `test_no_other_directory_answers_a_section_request[PB]`, `test_a_section_reply_filed_under_another_key_is_not_replayed[PB]`, `test_each_recording_replays_through_the_stage_under_its_own_profile[PB]`, `test_every_recording_carries_its_own_authored_usage_signature` |
| M6 the recording back to the base file (new one removed) | 7 failed | the same seven as M5 |
| M7 `origin.profile_status` `reviewed` to `draft` inside the new recording (key kept) | 1 failed | `test_the_builder_reports_no_drift` |
| M8 only the restored phrase «частям здания,» removed from the prompt (recording kept) | 7 failed | the same seven as M5 |
| M9 one character of the restored phrase changed (a full stop inserted; recording kept) | 7 failed | the same seven as M5 |
| M10 the `PB` expectations line back to `draft` / `1.0.0`, on the lane stack | 1 failed, 3 passed | `test_analysis_profiles_over_http.py::test_every_row_is_the_registry_entry_the_application_routes_by` |
| M10 the same, in the web test | 1 failed, 94 passed | `has a line for exactly the packages that exist, with the status and version each declares`: `PB: status draft in the file, reviewed in profile.json` |
| M11 `profile.json` status back to `draft`, on the lane stack | 1 failed, 3 passed | the same HTTP case |
| M11 the same, in the web test | 1 failed, 94 passed | the same web case (`PB: status reviewed in the file, draft in profile.json`) |
| M12 «(С0, К1)» put into condition 2 and «(СП 2.13130, п. 5.4.2)» into condition 1 | the audit script prints `NEITHER` for `'С0'`, `'К1'`, `'13130,'` | not a repository test (see the limit below) |
| M13 `open_questions.md`: `D-178` removed | 1 failed | `test_pb_open_questions_are_listed_in_the_package` |
| M14 `open_questions.md`: the number of question 6 stripped | 1 failed | the same case |
| M15 `open_questions.md`: question 5 deleted (gap in the numbering) | 1 failed | the same case |
| M16 `open_questions.md`: questions 4 to 11 cut (three left) | 1 failed | the same case |
| M17 `open_questions.md`: the decision under question 8 removed, then the check «one decision under every question» run (script outside the repository) | prints `one decision each: False [('8', [])]`, rc 1; on the committed file it prints `True`, kinds `K K K N K K K K K K K`, rc 0 | not a repository test (see the limit below) |

After each restore the SHA-256 was equal to the one taken before and the tests were green again (`211 passed`; HTTP `4 passed`; web `95 passed`). A probe before the rebuild: with the prompt edited and the recording not rebuilt, the builder's `--check` exits 1 listing the new key and the old file as `(stale)`, and the 211-case set has the recording failures of M5.

## Commands and results

From `/root/projects/PDF-Analysis/.local/worktrees/section-pb-full-01`, shared venv, one pytest at a time. `$BS` is `/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages`.

| Command | Result |
|---|---|
| section set (above), base `82068f3b` | `211 passed` |
| section set, after the change and the rebuild | `211 passed` |
| `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py`, then `--check` | rc 0 (`wrote` fourteen, `removed …153d0c01…json`); `--check` rc 0 `fixtures match` |
| `tests/integration/composition/test_analysis_profiles_over_http.py`, lane `.env` exported | `4 passed` |
| `npx vitest run tests/unit/analysis-settings` in `web/` (`node_modules` linked from `gate-night`, untracked) | 7 files, `95 passed` |
| governance one-liner on the task file | `[]` |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, `git diff --check` | see «Final checks» |

Free disk at the start of the lane 1.8 GiB, at the end 1.9 GiB (`df -h /`). No docker command, no push, no model call, no process killed.

## Integration notes

1. **Revert path if the integrator judges ten answers of the kind «no source» too thin for `reviewed`.** Set `draft` in `profile.json` and in the `PB` line, run `build_fixtures.py` (it writes `origin.profile_status` into the recording, so the recording must be rebuilt; the request key does not change because status is in no hash), and `open_questions.md` still reads truthfully (it says the profile was `draft` and names `D-178`). The N edit of question 4 does not depend on the status.
2. **Stale prose outside this lane's paths.** `fixtures/recorded/sections/README.md` lines 63 to 67 («The ПБ recording is for a draft profile … of the **authored, draft** ПБ profile») now name a status that is no longer true; `PB-PROFILE-01.md` («This is a draft, not a reviewed profile») and `BETA-PB-PROFILE-TRUTH-01.md` («ПБ is a draft authored profile») are history of earlier tasks and stay as records; `DEBT_REGISTER.md` `D-178` (row text: all 14 `draft`) and `CURRENT_STATE.md` are the integrator's. The README is the only living document that now misdescribes the tree.
3. **The web label for `reviewed`** was a false statement under `A-7` («проверен экспертом»); the `GP` report records it as already changed on its base by `607ee47a`. This lane touches no web file.
4. **Identity:** `analysis_profile_id` and `prompt_bundle_id` are unchanged (the lane mints none), while the bundle's text and hash and the profile hash changed. A stored run of the draft `PB` profile carries the old `analysis_profile_sha256` and `prompt_bundle_sha256`; the registry resolves by the id pair and serves only the new text. Development stand only, no migration (`R-146ah`). `web/tests/unit/styles/screens.ts:766` names the two identities and stays true.
5. **The recording's `origin`** still names `SECTION-RECORDINGS-01` as its authoring task and now says `profile_status: reviewed`; its statement still says it is not field evidence for the profile's review.
6. **e2e manifest:** the step with the selector `tr[data-profile="draft"]` stays valid while any other section is `draft` (`PT`, `SS`, `ITP` at this base).
7. **Merge:** the expectations file changes on the `PB` line only, and that line is the last of the array (no trailing comma), two lines after the nearest section still `draft` (`ITP`, with `GP` between), so lanes merge without conflict; re-run the section set, the HTTP test, the web test and `build_fixtures.py --check` after the last section merges. This lane's base lacks sections merged later; the builder wrote the thirteen other recordings byte-identically against this base only.
8. **Record:** `W59-SECTION-PROFILES-01.md` has no per-section row for `PB` (it excludes PB on purpose); the decisions live in `open_questions.md` and here. When the record is updated, cite this report and say that no human reviewed the decisions (`A-7`).
9. **Judge:** read decision 4 against v1's condition 1 (`prompt.py` lines 68 to 70) and the record's «Risks» line, not against this lane's summary; read decisions 3, 5 and 6 as «K because no source», not as findings that the current behaviour is right.

## Limits

- No test holds the restored phrase itself. Its wording is held only by the recording's request key (so an edit without a rebuild goes red, rows M5, M8 and M9), and the absence of a designation outside v1 and the record is held only by the manual audit (row M12). That every question of `open_questions.md` carries one decision (row M17) is held by nothing in the repository: a guard that checks each numbered question for a decision, and each profile prompt's numerals and designations against its source or record, would be new tests outside this lane's paths (the `AI`, `TX`, `KM`, `GP` and `EOM` reports say the same of the audit).
- The pin test of `open_questions.md` cannot tell whether the file's prose is true; it checks shape. Its `` `draft` `` clause is vacuous now that the status is `reviewed`; the file keeps the word as history so M1 is caught by the other four tests, not by this one.
- The effect of the N edit on a model's answers is unmeasured; no model was called.
- The profile has no pinned source. An expert may disagree with any decision in the table, and the report says where.

## Forbidden paths untouched

`git diff --name-only --no-renames 82068f3bfdcc54ff1725dc813482112accb17234..HEAD` on the final tree prints exactly these eight paths, all inside the task's allowed paths:

```text
docs/program/SECTION-PB-FULL-01.md
docs/program/tasks/SECTION-PB-FULL-01.md
fixtures/recorded/sections/pb/153d0c01416a33ea996d8031d293f441a3e829a4e5061e111541467e90bb6ad0.json
fixtures/recorded/sections/pb/eb53a861df61d016fcb7280b723e04c32aed367b70c47cc18863f292c9e60775.json
src/auditmanager/analysis/text/profiles/pb/open_questions.md
src/auditmanager/analysis/text/profiles/pb/profile.json
src/auditmanager/analysis/text/profiles/pb/system_prompt.md
tests/unit/analysis/text_profiles/section_profile_expectations.json
```

(Without `--no-renames` git folds the old recording into a rename and prints seven.) No other section's files, no `W59-SECTION-PROFILES-01.md`, registry, `P02_LOCK.json`, `contracts/**`, migration, `web/**` or `infra/**` appears; `build_fixtures.py` and the recordings README are unchanged. The legacy repository was only read (`git status --short` there: 0 lines before and after).

## Final checks

See the lane's final message for the tip SHA. On the committed tree (`git status --short` empty):

| Command | Result |
|---|---|
| `pytest tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` | filled in below |
| governance one-liner on `docs/program/tasks/SECTION-PB-FULL-01.md` | `[]` |
| `git diff --check 82068f3b..HEAD` | filled in below |
