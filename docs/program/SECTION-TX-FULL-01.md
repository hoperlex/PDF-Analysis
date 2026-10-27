# SECTION-TX-FULL-01 — the ТХ (TX) profile answers its open questions and is `reviewed`, without a human review

Task: `docs/program/tasks/SECTION-TX-FULL-01.md`. Branch `agent/section-tx-full-01`, base `3c80af0e` (`integration/ar-close-1026`, with `AI`, `PS` and `KJ` already `reviewed`). Plan item `PROD-14` (section `TX`); owner rulings `R-146ag`, `R-146ah`, `R-146ai`; template `SECTION-<CODE>-FULL-01` of `dispatch/PRODUCTION-WAVE-PW2B.md`. Executor: a Sonnet lane. No push, no tag, no container command, no model call, no process killed.

## Result

The `TX` record in `W59-SECTION-PROFILES-01.md` has five open questions; the last asks two things, so there are six decisions: **K** five times and **N** once (question 2). The four cross-section questions are applied as the wave table fixes them (all **K**). No **X**. The N decision is one sentence appended to condition 1 of `system_prompt.md`; nothing else in the prompt moved. The prompt changed, so `profile_version` is `1.1.0`, the recording is rebuilt, and `profile.json` and the `TX` line of the expectations file say `reviewed`.

**`reviewed` here is not expert verification.** Nobody has reviewed this profile: not an expert, not the owner (`R-146ag`, accepted risk `A-7`). The decisions were taken conservatively from the five hash-pinned legacy files and the record, and nothing was measured on real text. The status must not be quoted anywhere as a human review.

Premise: **match.** Package, status and version, the five source hashes at the pinned commit, the five questions, the four cross-section questions, the expectations line and the one recording are as the brief says (task file, P-01 to P-08). The audit of numerals and class designations that the `AI` lane found necessary (P-09) is clean for `TX`: the prompt has no digit-bearing token and no class designation, so nothing had to be removed.

## Decisions

Quoted question openings are the record's own words. «Condition n» means v1's numbered conditions in the prompt.

| # | Question (record) | Decision | Reason | Exact change |
|---|---|---|---|---|
| 1 | «технологическое оборудование подбирается арендатором», «марка оборудования уточняется на стадии РД»: placeholder (as v1 reads it) or an accepted split of the design scope? | **K** | Cross-section decision (1) applies. «уточняется» is one of v1's literal markers, and condition 4 forgives only a reference to a table, schedule, specification, sheet, section or volume where the value is given; «на стадии РД» is a deferral to a later stage, not that place. «подбирается арендатором» carries no mark, so v1's definition (a literal mark of unfilled) decides it as before and the profile neither lists nor excludes it. Turning a deferral into an accepted instruction is an expert's call and would silence findings. | none |
| 2 | Equipment position numbers repeat in the explications of different rooms and enterprises: is «одна и та же позиция» enough, or does an equal number in different rooms give systematic false findings (condition 1)? | **N** | Condition 1 lists «позициям оборудования» among the different objects but never says what makes two mentions one position, and three hint bullets (lines 21, 23, 26 of the base prompt) identify the object only by «одной и той же позиции». In an explication «позиция» is the item number, which restarts in every room, enterprise and specification, so the model is led to treat an equal number as one object. A number is not an identity (`AGENTS.md` section 4). The sentence only adds a condition before a comparison: it widens nothing and adds no number, norm or designation. Where the number is unique in the document the comparison stays as in v1. | one sentence appended to condition 1, see below |
| 3 | Total power or water flow in the записка against the sum of rows of the specification or the load table: a finding? | **K** | Cross-section decision (2). Counting rows is arithmetic, which the exclusion paragraph keeps out («НЕ выполняешь и не перепроверяешь инженерные расчёты»). The one bullet about totals (line 36) compares totals «прямо указанные» in the записка, the general data and the summary load tables: two written totals that differ stay an `internal_contradiction` under v1; a total against its rows does not. | none |
| 4 | An equipment position in the plan explication with no row in the specification (or the reverse): is such a finding wanted? | **K** | Cross-section decision (4): no third kind of observation (it would be a contract change). Condition 5 stays («Утверждения просто нет … это не находка»); bullet 1 compares the brand and the quantity of a position that is written in both places and has nothing to compare when one place lacks it. | none |
| 5a | Is the list of places complete for a typical TX set of a residential building with built-in premises and parking? | **K** | The list is a hint, not a list of required findings; a place with no values yields nothing under condition 5. Every sheet type of `drawing_types.md` that carries attribute values maps onto a bullet (table below). The one without a dedicated bullet, `section` («высоты оборудования»), is partly covered by «габариты» of bullet 2; a new bullet for heights would add a comparison, which is widening. | none |
| 5b | Drop the parking, waste-removal and cargo-lift bullets if their values are usually given only in other volumes? | **K** (not X) | The record states a condition («если … обычно»), not a fact. Each of the three bullets names places inside the TX document itself (the записка, the general data, the specification and the summary tables), and the prompt already forbids other volumes («Чертежей, внешних норм и других разделов у тебя нет»). If the values are not written in the document the bullets yield nothing (condition 5); if they are, dropping the bullets would silence real in-document contradictions. The source names all three as TX subject: `role.md` («Требования к мусороудалению», «Погрузочно-разгрузочные зоны, грузовые лифты»), `checklist.md` («Паркинг», «Мусороудаление») and `project_params.md` (`parking_*`, `waste_system`, `loading_dock_count`). | none |

Cross-section decisions (the same for every lane; this lane agrees with them and has nothing to report against them):

| # | Question | Decision | TX-specific note |
|---|---|---|---|
| C1 | Site and contractor phrases | **K** | Covers question 1. |
| C2 | «Итого» against the sum of rows | **K** | Covers question 3: the prompt has no recomputation bullet. |
| C3 | Text read from sheets | **K** | The record names no bullet whose false findings come from detached sheet text, and the prompt has none (task file P-10: no «подпис», «штамп», «выноск», «надпис»). The bullets read explications, specifications and tables. |
| C4 | Missing items | **K** | Covers question 4; condition 5 stays; the record's excluded list («наличие … требуется») stays excluded. |

Places of question 5a, by sheet type of `drawing_types.md` and bullet of the prompt (bullets numbered from the top of the hint block):

| Sheet types | Bullet(s) |
|---|---|
| `equipment_layout`, `floor_plan_tech`, `food_service_plan`, `medical_plan` (explications on plans) | 1, 2, 4, 5, 8 |
| `parking_layout` | 6 |
| `loading_zone` | 10 |
| `waste_room` | 9 |
| `utility_connections` | 3, 11 |
| `specification` | 1, 2, 3, 8, 9, 10, 11 |
| `title_block`, `general_notes` (general data) | 5, 6, 7, 9, 10 |
| `section` (heights of equipment) | none dedicated; «габариты» in 2 |
| `process_flow` | none: flows are drawn relations, judging them is excluded |
| `detail`, `other` | none: no attribute values to compare |

## The prompt change in words

One edit in `system_prompt.md`; everything else is byte for byte what it was (the package tests hold v1's question, categories, conditions and output contract).

**Condition 1 (question 2).** After the sentence «Ищи в тексте прямое указание на то, к чему относится значение.» four lines are added: a position number of equipment does not by itself make two mentions the same position, because it may repeat in the explications and specifications of different rooms and enterprises; compare such mentions only if the text directly places both in one room, enterprise or technological zone, or if in the document the number belongs to one position only.

New numerals: none. New norm references: none. New designations: none. Findings: only narrower than before.

`git diff 3c80af0e..HEAD -- src/auditmanager/analysis/text/profiles/tx/system_prompt.md` is 5 added lines and 1 removed (the last line of condition 1 is the same text, now continued).

## Audit of numerals and designations

Run before and after the edit (task file P-09 has the base output). Before and after, the prompt has no digit-bearing token, and the capital-letter tokens are `МГН`, `СП`, `ТХ` (all in the source) and v1's own words (`TBD`, `XX`, `ГОСТ` and upper-case emphasis). With a designation put into condition 2 (mutation M12 below) the script reports `'Г1–Г4' in legacy source: False`, so it can fail. The script that was run (it lives outside the repository; this is its exact text):

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

## Assumptions an expert would still want to check

Short and honest (`A-7`): none of these was checked by anyone with domain knowledge.

1. **Question 1 (K).** «Марка оборудования уточняется на стадии РД» is still reported as a placeholder, and a document that legitimately defers equipment choice to the tenant will show such findings; the lane chose over-reporting to silencing. Whether «подбирается арендатором» is flagged is left to v1's wording.
2. **Question 2 (N).** Where a document gives no room, enterprise or zone for repeated position numbers, a real mismatch of brand or quantity is no longer reported; where the number is unique in the document the comparison stays. The edit covers equipment position numbers only. Room numbers were not touched: the room bullets identify a room by name and purpose, not by number, and the record does not ask.
3. **Question 3 (K).** A записка total against the sum of the specification or load-table rows is not reported; an expert may want that arithmetic case.
4. **Question 4 (K).** A position in the explication with no specification row is not reported. A real omission stays the expert's to find.
5. **Question 5 (K, K).** The parking, waste and cargo-lift bullets stay; if an expert knows those values never stand in a TX document they cost nothing but a few tokens. Heights of equipment on the technological section have no bullet of their own.
6. **Vocabulary not from the source.** Attribute names in the hint bullets that none of the five files contains, observed with the same script and not changed because they are not numbers, norm references or class designations and no question touches them: «вместимость», «масса», «напряжение», «грузоподъёмность» (cargo lifts), «число смен», «холодильной камеры» (the source says «холодильное оборудование»), «класс чистоты» (the source says «Классы чистоты»). An expert may want them aligned or struck.
7. **Nothing was measured.** The recording is synthetic, authored by hand over the AR corpus; it proves routing and replay and says nothing about how the profile performs on a real ТХ volume.

## Files changed

| File | Change |
|---|---|
| `src/auditmanager/analysis/text/profiles/tx/system_prompt.md` | the one edit above |
| `src/auditmanager/analysis/text/profiles/tx/profile.json` | `profile_version` `1.0.0` to `1.1.0`; `status` `draft` to `reviewed` |
| `fixtures/recorded/sections/tx/1fa3402c…9313.json` | rebuilt by `build_fixtures.py`; replaces `e1dcf36b…c6df.json`; the differences against the old file are `origin.profile_status` (`reviewed`), `origin.prompt_bundle_sha256` (`734b5c3e…bb12`) and `request_sha256`; the authored reply, usage and latency are unchanged |
| `tests/unit/analysis/text_profiles/section_profile_expectations.json` | the `TX` line only: `reviewed`, `1.1.0` |
| `docs/program/tasks/SECTION-TX-FULL-01.md`, this report | records |

The builder writes all fourteen recordings; thirteen came out byte-identical (`git status` shows no other recording). No test file was edited, so no assertion was weakened: there is no before/after of a modified test to give. The one data line the tests read changed from `draft`/`1.0.0` to `reviewed`/`1.1.0`; before, the registry, package, guard, HTTP and web tests asserted that `profile.json` and the served row agree with the line, after they assert the same agreement with the new values.

## Mutation table

Each row edits one thing in the committed tree (`3bf852be`), runs the section test set, restores with `git checkout` and proves the restore by a SHA-256 over the four files (prompt, `profile.json`, expectations, new recording; `restored=True` every time). The set is `test_text_profile_registry.py`, `tests/unit/analysis/text_profiles`, `tests/integration/sections/test_section_recordings.py` and `tests/contract/analysis_packages` (211 cases). The unmutated tree: `211 passed`.

| Mutation | Result | First red cases |
|---|---|---|
| M1 `profile.json` status `reviewed` back to `draft` (version kept) | 4 failed | registry `test_the_tree_registers_without_error_and_without_an_ar_package`; guard `test_every_line_agrees_with_its_package_profile_json`; packages `test_every_profile_manifest_has_the_text_profile_1_shape`; recordings `test_the_builder_reports_no_drift` |
| M2 `profile.json` version `1.1.0` back to `1.0.0` (status kept) | 3 failed | the first three of M1 |
| M3 the `TX` expectations line back to `draft` / `1.0.0` (`profile.json` kept) | 3 failed | the first three of M1 |
| M4 the `TX` expectations line, status only back to `draft` | 3 failed | the first three of M1 |
| M5 `system_prompt.md` back to the base text (recording kept) | 7 failed | recordings: `test_each_section_has_one_synthetic_recording_keyed_to_its_own_request[TX]`, `test_the_builder_reports_no_drift`, `test_the_served_adapter_answers_each_recorded_section_and_the_canonical_alone_does_not[TX]` and four more |
| M6 the recording back to the base file (new one removed) | 7 failed | the same recordings cases |
| M7 `origin.profile_status` `reviewed` to `draft` inside the new recording (key kept) | 1 failed | `test_the_builder_reports_no_drift` |
| M8 only the added N sentence removed from the prompt (recording kept) | 7 failed | the same recordings cases as M5 |
| M9 one character of the N sentence changed (a full stop inserted; recording kept) | 7 failed | the same recordings cases as M5 |
| M10 the `TX` expectations line back to `draft` / `1.0.0`, on the lane stack | 1 failed, 3 passed | `test_analysis_profiles_over_http.py::test_every_row_is_the_registry_entry_the_application_routes_by`: `TX: the served (status, profile_version) is not the expectations file's` |
| M10 the same, in the web test | 1 failed, 94 passed | `has a line for exactly the packages that exist, with the status and version each declares`: `TX: status draft in the file, reviewed in profile.json` |
| M11 `profile.json` status back to `draft`, on the lane stack | 1 failed, 3 passed | the same HTTP case |
| M11 the same, in the web test | 1 failed, 94 passed | `TX: status reviewed in the file, draft in profile.json` |
| M12 «(Г1–Г4)» inserted into condition 2 | the audit script prints `'Г1–Г4' in legacy source: False` | not a repository test (see the limit below) |

After each restore the SHA-256 was equal to the one taken before and the tests were green again (`211 passed`; HTTP `4 passed`; web `95 passed`). A probe before the rebuild: with the prompt edited and the recording not rebuilt, the builder's `--check` exits 1 listing the new key and the old file as `(stale)`, and the 211-case set has 7 failed, 204 passed.

## Commands and results

From `/root/projects/PDF-Analysis/.local/worktrees/section-tx-full-01`, shared venv, one pytest at a time. `$BS` is `/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages`.

| Command | Result |
|---|---|
| section set (above), base `3c80af0e` | `211 passed` |
| section set, after the change and the rebuild | `211 passed` |
| `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py`, then `--check` | rc 0 (`wrote` fourteen, `removed …e1dcf36b…c6df.json`); `--check` rc 0 `fixtures match` |
| `tests/integration/composition/test_analysis_profiles_over_http.py`, lane `.env` exported | `4 passed` |
| `npx vitest run tests/unit/analysis-settings` in `web/` (`node_modules` linked from `gate-night`) | 7 files, `95 passed` |
| governance one-liner on the task file | `[]` |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, `git diff --check` | see «Final checks» |

Free disk at the start of the lane 1.8 GiB, at the end 1.7 GiB (`df -h /`). No docker command, no push, no model call, no process killed.

## Integration notes

1. **The web label for `reviewed` still says «проверен экспертом»** and the `AnalysisProfileStatus` docstring says «a package an expert has reviewed» (see the `AI` report, integration note 1). Both are outside this lane (`web/**`, `src/auditmanager/api/**`); the decision is the integrator's, once for all fourteen lanes.
2. **Identity:** `analysis_profile_id` and `prompt_bundle_id` are unchanged (the lane mints none), while the bundle's text and hash and the profile hash changed. A stored run of the draft `TX` profile carries the old `analysis_profile_sha256` and `prompt_bundle_sha256`; the registry resolves by the id pair and serves only the new text. Development stand only, no migration (`R-146ah`).
3. **The recording's `origin`** still names `W59-ANALYSIS-SETTINGS-01` as its authoring task and now says `profile_status: reviewed`; its statement still says «Not field evidence for the profile's review».
4. **e2e manifest:** the step with the selector `tr[data-profile="draft"]` stays valid while any other section is `draft` (`POS`, `KM`, `OV`, `VK`, `PT`, `EOM`, `SS`, `ITP`, `GP`, `PB` at this base).
5. **Merge:** the expectations file changes on the `TX` line only, so lanes merge without conflict; re-run the section set, the HTTP test, the web test and `build_fixtures.py --check` after the last section merges.
6. **Record:** `W59-SECTION-PROFILES-01.md` still says «Every profile is `status: draft`» and lists the five questions as open (forbidden path for the lane). When it is updated, cite this report and say that no human reviewed the decisions (`A-7`).

## Limits

- No test holds the added sentence itself. Its wording is held only by the recording's request key (so an edit without a rebuild goes red, rows M5, M8 and M9), and the absence of a designation outside the source is held only by the manual audit (row M12); a new guard test is outside this lane's paths. A cross-section guard that checks each prompt's numerals and designations against its pinned source is a candidate for the integrator (the `AI` report says the same).
- The effect of the N edit on a model's answers is unmeasured; no model was called.
- An expert may disagree with any decision in the table, and the report says where.

## Forbidden paths untouched

`git diff --name-only --no-renames 3c80af0e..HEAD` on the final tree prints exactly these seven paths, all inside the task's allowed paths (without `--no-renames` git folds the old recording into a rename and prints six):

```text
docs/program/SECTION-TX-FULL-01.md
docs/program/tasks/SECTION-TX-FULL-01.md
fixtures/recorded/sections/tx/1fa3402cd61588729135e440bdd0143a3d6f0e222785048771f08fcca89d9313.json
fixtures/recorded/sections/tx/e1dcf36b471442c200c94895345eb856c99ed77daa3a94f5d7c912989b99c6df.json
src/auditmanager/analysis/text/profiles/tx/profile.json
src/auditmanager/analysis/text/profiles/tx/system_prompt.md
tests/unit/analysis/text_profiles/section_profile_expectations.json
```

No other section's files, no `W59-SECTION-PROFILES-01.md`, registry, `P02_LOCK.json`, `contracts/**`, migration, `web/**` or `infra/**` appears; `build_fixtures.py` is unchanged. The legacy repository was only read (`git status --short` there: 0 lines before and after).

## Final checks

On the committed tree (`git status --short` empty), the last commit before this paragraph being `ecb15035`:

| Command | Result |
|---|---|
| `pytest tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` | `105 passed` |
| governance one-liner on `docs/program/tasks/SECTION-TX-FULL-01.md` | `[]` |
| `git diff --check 3c80af0e..HEAD` | rc 0 |
| section set, `build_fixtures.py --check`, HTTP test (lane `.env`), `vitest` analysis-settings | `211 passed`; `fixtures match` rc 0; `4 passed`; `95 passed` |

This paragraph is the only text added after `ecb15035`; the contract run above was repeated on the tree that contains it (see the lane's final message for the tip SHA).
