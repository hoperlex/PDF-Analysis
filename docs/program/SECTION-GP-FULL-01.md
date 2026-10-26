# SECTION-GP-FULL-01 — the ГП (GP) profile answers its open questions and is `reviewed`, without a human review

Task: `docs/program/tasks/SECTION-GP-FULL-01.md`. Branch `agent/section-gp-full-01`, base `3c80af0e62c71f04d1e5b1178e0afbe7db6f7d6c` (`integration/ar-close-1026`), product commit `02f30999`. Plan item `PROD-14` (section `GP`); owner rulings `R-146ag`, `R-146ah`, `R-146ai`; accepted risk `A-7`; template `SECTION-<CODE>-FULL-01` of `dispatch/PRODUCTION-WAVE-PW2B.md`. Executor: a Sonnet lane. No push, no tag, no container command, no model call.

**Read this first (`A-7`).** Nobody reviewed this section: not an expert, not the owner. The status `reviewed` on the GP profile means a lane wrote a decision for every open question of its record and rebuilt its recording. It is **not** expert verification and must not be quoted as one.

## Result

The `GP` record in `W59-SECTION-PROFILES-01.md` has five open questions and the four cross-section questions. Each has one written decision: **K** for GP-1, GP-3, GP-5 and for cross-section 1, 2 and 4; **N** for GP-2 and GP-4, and cross-section 3 resolves to **N for the GP-4 bullet only**; **X** never. The N decisions are two edits of `gp/system_prompt.md` (one more near-miss pair in condition 2; one sentence at the end of one hint bullet); nothing else in the prompt moved. `profile_version` is `1.1.0`, `status` is `reviewed` in `profile.json` and in the `GP` line of the expectations file, and the recording is rebuilt by `build_fixtures.py`. The audit the template does not name (every numeral and class designation of the prompt against the pinned source) found no designation outside the source; it found one notation, `0,000`, which is kept and disclosed.

Premise: **match.** The package, the five open questions, the four cross-section questions, the legacy repository at `16ba8e5d…` with all five hashes equal to `gp/profile.json`, the `GP` expectations line and a green baseline (211 and 4 passed, `fixtures match`) were as the brief says (task file, P-01 to P-07). Nothing to stop for.

## Decisions

Quoted question openings are the record's own words. «Condition n» means v1's numbered conditions in the prompt.

| # | Question (record, shortened) | Decision | Reason | Exact change |
|---|---|---|---|---|
| GP-1 | Sum of the balance items is not 100 % or not the site area: a finding? | **K** | Cross-section rule 2. The checklist formula («застройка + озеленение + покрытия + прочее = 100%») is an arithmetic recomputation, which the record lists as excluded and the prompt excludes («Сравниваются только значения, прямо записанные в тексте»). The first hint bullet compares the written value of one balance position in м² and in % between places; it adds nothing up. Two totals that are both written in the text and differ stay an `internal_contradiction` under v1; only counting the rows stays out. | none |
| GP-2 | Site area by the ГПЗУ, area within the landscaping boundary (including landscaping outside the site) and area within the design boundary are given side by side: does the balance bullet give systematic false findings? | **N** | A stated false-positive source. Condition 2 named only one pair, the site area against the area within the landscaping boundary; the third area, within the design boundary, is not named, while the first hint bullet tells the model to compare «площадь земельного участка» across the balance table, the ТЭП, the note and the general data. Naming the second pair removes comparisons only; it adds no number, norm or designation, and does not say that the site area by the ГПЗУ differs from the site area (it does not mention the ГПЗУ). | condition 2 gets the pair «площадь земельного участка и площадь в границах проектирования» |
| GP-3 | ТЭП values per stage (queue) and for the whole complex: is condition 1 enough to keep them apart? | **K** | Condition 1 names «этапам или очередям строительства» and ends with «Ищи в тексте прямое указание на то, к чему относится значение»; the first bullet asks for «одной и той же позиции», and a stage column or row carries its own label. No bullet tells the model to compare a stage value with a total. A «whole complex» line is not named as an object, which is listed under assumptions, but no field case (`A-5`) shows a false finding to remove, and adding an object to condition 1 is a wording change the record does not demonstrate as needed. | none |
| GP-4 | Elevations and slopes in the text layer of plans and profiles are detached from what they belong to: is the comparison «в подписях плана организации рельефа» reliable, or should it be limited to the note, the profiles and the schedules? | **N** (this bullet only) | Cross-section rule 3: K unless the section's own record names a bullet, then N for that bullet only. The record names this one (a doubt about its reliability, not a measured rate). Dropping the place from the list would silence the comparison even when the label names its element; the sentence keeps that case and removes the anonymous one. It restates, for this bullet, the last sentence of condition 1. Other bullets that mention labels («в подписях разбивочного плана» for the fire-access width and for the parking counts, «в подписях сводного плана сетей» for pipe designations) are not named by the record and stay as they were (K). | hint bullet on design elevations and the longitudinal slope, one sentence added (below) |
| GP-5 | «уточнить по результатам инженерных изысканий», «по согласованию с владельцами сетей», «ассортимент растений уточнить на стадии Р», «отметки уточнить по месту»: placeholder or an accepted instruction? | **K** | Cross-section rule 1: turning a deferral into an accepted instruction is an expert's call and would silence findings. Under v1's wording a phrase carrying «уточнить» is an explicit placeholder unless condition 4 applies (a reference to the table, sheet, section or volume where the value is given); «по согласованию с владельцами сетей» carries no unfilled mark and is decided by v1's definition as before. | none |
| A-1 | Audit (not a record question): numerals and class designations of the prompt against the pinned source | **K** (disclosed) | `В1`, `К1`, `К2`, `Т1` (pipe designations) are in `project_params.md`; `МГН`, `СП`, `ГОСТ`, `ГП` are in the source; no `Г1–Г4`-type designation is present. One token is not in the source: `0,000`, the notation of the zero mark of a building in the second hint bullet. It is not a norm, a threshold or a class designation and states no value to compare. Removing it would change what the bullet tells the model with no stated false-positive source, so it stays. | none |

Cross-section decisions (the same for every lane; this lane agrees with the table and has nothing to report against it):

| # | Question | Decision | GP-specific note |
|---|---|---|---|
| 1 | Site and contractor phrases | **K** | Covers GP-5. |
| 2 | «Итого» against the sum of rows | **K** | Covers GP-1. The prompt has no bullet that recomputes a total. |
| 3 | Text read from sheets | **N**, for the GP-4 bullet only | The record names that one bullet. The other label bullets (listed under GP-4) are not named and stay under v1. |
| 4 | Missing items | **K** | No third kind of observation; condition 5 stays; the excluded list (what must be present) stays excluded. |

## The prompt change in words

`git diff 3c80af0e HEAD -- src/auditmanager/analysis/text/profiles/gp/system_prompt.md`: 7 lines added and 4 removed (the removed lines are the old last line of the bullet and the three re-wrapped lines of condition 2). The opening, the question, the two categories, conditions 1 and 3 to 5, the exclusion paragraph and the output contract are byte for byte as before; the package test holds them.

1. **Condition 2 (GP-2).** The list of near-miss pairs now reads «площадь земельного участка и площадь в границах благоустройства, площадь земельного участка и площадь в границах проектирования, площадь озеленения и площадь газонов, требуемое по расчёту и фактически размещённое количество машино-мест». The pair «площадь земельного участка и площадь в границах проектирования» is new; the closing sentence («убедись, что это буквально одна и та же характеристика») is unchanged.
2. **Hint bullet on design elevations and the longitudinal slope (GP-4).** The bullet ends, after «в пояснительной записке», with: «отметку или уклон из подписи плана организации рельефа сопоставляй с другими местами, только если сама подпись называет этот проезд, тротуар или путь, а отметка или уклон без такого названия к нему не привязаны». The list of places in the bullet is unchanged.

`profile.json`: `status` `draft` to `reviewed`, `profile_version` `1.0.0` to `1.1.0` (the prompt text changed). Identities unchanged; the bundle's `content_sha256` moved with the text (`prompt_bundle_sha256` in the recording: `b17d6129…91dd` to `fab79a6b…00be`).

New numerals: none. New norm references: none. New class designations: none. Findings: only narrower than before.

## Audit of numerals and designations

Run before the edit (task file P-07) and after it. After the edit the digit-bearing tokens of the prompt are the same five: `0,000`, `В1`, `К1`, `К2`, `Т1`; the capital-letter tokens are v1's own words (`TBD`, `XX`, `ГОСТ`, `СП`, upper-case emphasis), `ГП`, `МГН` and the pipe designations. Put `(класс Г1–Г4)` after condition 2 and the script prints `'Г1–Г4' in legacy source: False`, so it can fail (mutation A1 below). The script (it lives outside the repository; this is its exact text):

```python
"""Audit: every digit-bearing token and capital-letter class designation in a section prompt
must occur in the section's five hash-pinned legacy files (read at the pinned commit)."""
import json, re, subprocess, sys
from pathlib import Path

root = Path(sys.argv[1])           # worktree
code = sys.argv[2]                 # e.g. GP
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

Its tokenizer keeps a trailing comma, so `В1,`, `К1,` and `К2,` print `False`; the same designations without the comma print `True`. A direct grep over the five files for the words the lane may have leaned on (`ГПЗУ`, `в границах проектирования`, `в границах благоустройства`, `подпис…`, `0,000`, `абсолютн…`, `перечётн…`, `колодц…`) returns 0 in every file (P-04). The words in the new text («в границах проектирования», «подпись») come from the record's own questions and are plain words, not numbers, norms or designations.

## Assumptions an expert would still want to check

Short and honest (`A-7`): none of these was checked by anyone with domain knowledge.

1. **GP-1 (K).** A balance whose items do not add up to 100 % or to the site area is still not reported, unless the document writes two incompatible totals itself.
2. **GP-2 (N).** A real mismatch between the site area and a figure the document calls the area «в границах проектирования» is no longer reported when they are written as different areas. The lane did not say that an area «по ГПЗУ» is a different attribute from the site area, and did not name the ГПЗУ.
3. **GP-3 (K).** Whether the model keeps a whole-complex total apart from a stage or queue value rests on condition 1 and on the row or column label; a «whole complex» line is not named as an object. Unmeasured.
4. **GP-4 (N).** A mark or slope in a relief-plan label that does not name its road, pavement or path is no longer compared with the profile or the note; a real mismatch there is missed. A label that names its element is still compared. The other label-reading bullets are unchanged.
5. **GP-5 (K).** Whether a model flags «по согласованию с владельцами сетей» (no literal mark) is left to v1's definition.
6. **Terms from the earlier drafting, not from the source.** The second hint bullet (the absolute elevation taken as the zero mark of a building, `0,000`, and the adopted system of coordinates and heights) has no counterpart in the five files beyond «привязки … к координатам/осям» and «Проектные отметки». It states no value to compare and the lane kept it: it is not an open question, and the record does not show that it cannot be a same-document cross-check. The audit covers numerals, norms and class designations only.
7. **Nothing was measured.** The recording is synthetic, authored by hand over the AR corpus (its reply talks about evacuation exits and fire resistance, not about a general plan); it proves routing and replay and says nothing about how the profile performs on a real ГП volume.

## Files changed

| File | Change |
|---|---|
| `src/auditmanager/analysis/text/profiles/gp/system_prompt.md` | the two edits above |
| `src/auditmanager/analysis/text/profiles/gp/profile.json` | `profile_version` `1.0.0` to `1.1.0`; `status` `draft` to `reviewed` |
| `fixtures/recorded/sections/gp/9dbe139a3b025683b91448992b6890a0a7bd54750e95969a3a396c60b7a8b959.json` | rebuilt by `build_fixtures.py`; replaces `d6e106170da12a9a764a218a5bdb7207a355b02563d25e759663e2fcc2f7466e.json`; the diff against the old file is exactly three lines: `origin.profile_status` (`reviewed`), `origin.prompt_bundle_sha256` (`fab79a6b…00be`) and `request_sha256`; the authored reply, usage and latency are unchanged |
| `tests/unit/analysis/text_profiles/section_profile_expectations.json` | the `GP` line only: `reviewed`, `1.1.0` |
| `docs/program/tasks/SECTION-GP-FULL-01.md`, this report | records |

The builder writes all fourteen recordings; thirteen came out byte-identical (`git status` showed only the GP directory).

## Before and after of modified tests

No test file is modified. The one data line that the tests read changed from `{"code": "GP", "status": "draft", "profile_version": "1.0.0"}` to `{"code": "GP", "status": "reviewed", "profile_version": "1.1.0"}`. Before, the pin tests (registry, package shape, the expectations guard, the HTTP list, the web fixture test) asserted that `profile.json` and the registry agree with the line (`draft`, `1.0.0`); after, they assert the same agreement with `reviewed`, `1.1.0`. Every assertion still compares the package with the line; nothing is weakened.

## Mutation table

Each row edits one thing in the committed tree (`02f30999`), runs the guard, restores with `git checkout` and proves the restore by a SHA-256 over the four product files (`restored=True`, `git status --short` empty). «Set» is the 211-case set: `test_text_profile_registry.py`, `tests/unit/analysis/text_profiles`, `tests/integration/sections/test_section_recordings.py`, `tests/contract/analysis_packages`. The unmutated tree: `211 passed`.

| # | Mutation | Guard | Result when mutated |
|---|---|---|---|
| M1 | `profile.json` status `reviewed` back to `draft` (version kept) | set | `4 failed, 207 passed`: registry `test_the_tree_registers_without_error_and_without_an_ar_package`; `test_every_line_agrees_with_its_package_profile_json`; packages `test_every_profile_manifest_has_the_text_profile_1_shape`; recordings `test_the_builder_reports_no_drift` |
| M2 | `profile.json` version `1.1.0` back to `1.0.0` (status kept) | set | `3 failed, 208 passed` (the first three of M1) |
| M3 | the `GP` expectations line back to `draft` / `1.0.0` (`profile.json` kept) | set | `3 failed, 208 passed` (the same three) |
| M4 | the `GP` expectations line, status only back to `draft` | set | `3 failed, 208 passed` (the same three) |
| M5 | `system_prompt.md` back to the base text (recording kept) | set | `7 failed, 204 passed`: five recordings tests for `[GP]` (keyed to its own request, served adapter, no other directory answers, filed under another key, replays through the stage) plus `test_the_builder_reports_no_drift` and `test_every_recording_carries_its_own_authored_usage_signature` |
| M6 | only the new condition-2 pair removed | set | `7 failed, 204 passed` (the same seven) |
| M7 | only the new relief-label sentence removed | set | `7 failed, 204 passed` (the same seven) |
| M7b | one comma added inside the relief-label sentence | set | `7 failed, 204 passed` (the same seven) |
| M8 | the recording back to the base file (new one removed) | set | `7 failed, 204 passed` (the same seven) |
| M9 | `origin.profile_status` `reviewed` to `draft` inside the new recording (key kept) | set | `1 failed, 210 passed`: `test_the_builder_reports_no_drift` |
| M9b | `system_prompt.md` back to the base text | `build_fixtures.py --check` | rc 1: the old key listed as the file the script would write, the new one `(stale)` |
| M10 | the `GP` expectations line back to `draft` / `1.0.0`, on the lane stack | `test_analysis_profiles_over_http.py` | `1 failed, 3 passed`: `test_every_row_is_the_registry_entry_the_application_routes_by` |
| M11 | the same, in the web test | `npx vitest run tests/unit/analysis-settings` | `1 failed, 94 passed`: `has a line for exactly the packages that exist, with the status and version each declares` |
| M12 | `profile.json` status `draft` (version kept), on the lane stack | HTTP test | `1 failed, 3 passed` (as M10) |
| M13 | `profile.json` status `draft` (version kept) | web test | `1 failed, 94 passed` (as M11) |
| A1 | `(класс Г1–Г4)` put back into condition 2 | the audit script | prints `'Г1–Г4' in legacy source: False` (not a repository test; see the limit below) |

After each restore the guards were green again (`211 passed`; HTTP `4 passed`; web `95 passed`).

**What the table says about the new wording.** No test reads the two added sentences; their only guard is the recording key, which is the digest of the exact prompt bytes, so any change to the N wording is red until the recording is rebuilt (M5 to M8). The reverse also holds: a rebuilt recording over a changed prompt would pass. A test that pins the two edits by content needs a file outside this lane's allowed paths and is not written.

## Commands and results

From `/root/projects/PDF-Analysis/.local/worktrees/section-gp-full-01`, shared venv, one pytest at a time, `PYTHONDONTWRITEBYTECODE=1`, `$BS` = `/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages`. Results are read from the pytest output, not from a pipe.

| Command | Base `3c80af0e` | After the change |
|---|---|---|
| section set (above) | `211 passed` | `211 passed` |
| the same, after the prompt edit and before the rebuild | not run | `test_section_recordings.py`: `7 failed, 102 passed`; `--check` rc 1 |
| `build_fixtures.py --check` | `fixtures match` | `fixtures match` (rc 0) after the rebuild |
| `tests/integration/composition/test_analysis_profiles_over_http.py`, lane `.env` exported | `4 passed` | `4 passed` |
| `npx vitest run tests/unit/analysis-settings` in `web/` (`node_modules` linked from `gate-night`, untracked) | not run | `7 files, 95 passed` |
| governance one-liner on the task file | not run | `[]` |

The final contract run, `git diff --check` and the path proof are under «Final checks» below.

Free disk (`df -h /`): 1.9 GiB at the start. No docker command, no push, no model call, no process killed.

## Integration notes

1. **The web label for `reviewed`** was a false statement under `A-7` («проверен экспертом»); it is already changed on this base by `607ee47a` (`fix(web): the reviewed profile label no longer claims expert verification`). This lane touches no web file.
2. **Identity:** `analysis_profile_id` and `prompt_bundle_id` are unchanged, while the bundle's text and hash changed and the profile hash changed with the version. A stored run of the draft GP profile carries the old `analysis_profile_sha256` and `prompt_bundle_sha256`; the registry resolves by the id pair and serves only the new text. Development stand only, no migration (`R-146ah`).
3. **The recording's `origin`** still names `SECTION-RECORDINGS-01` as its authoring task and now says `profile_status: reviewed`; its statement still says «Not field evidence for the profile's review». The builder was not touched.
4. **e2e manifest:** the step with the selector `tr[data-profile="draft"]` stays valid while any other section is `draft` (ten of the fourteen sections are, after this lane).
5. **Merge:** the expectations file changes on the `GP` line only, so lanes merge without conflict. If another lane's merge changes `build_fixtures.py` output, re-run `build_fixtures.py --check`, the section set, the HTTP test and the web test after the last section merges.
6. **Record:** `W59-SECTION-PROFILES-01.md` still says every profile is `draft` and lists the five GP questions as open. It is a forbidden path for the lane; the integrator should point it at this report without calling the status an expert review.
7. **Judge:** read the decisions table against the five legacy files named in P-03 and P-04, not against this lane's summary.

## Limits

- No expert or owner reviewed any decision (`A-7`); no field case (`A-5`); the recording is synthetic.
- No test holds the two prompt edits by content; the audit script is run by hand and is not a repository guard. A cross-section guard that checks each prompt's numerals and designations against its pinned source would be a candidate for the integrator.
- The effect of the N edits on a model's answers is unmeasured; no model was called.
- `0,000` stays in a bullet although the source does not contain it (see Assumptions, 6).

## Forbidden paths untouched

`git diff --name-only --no-renames 3c80af0e62c71f04d1e5b1178e0afbe7db6f7d6c..HEAD` on the tip of the branch prints exactly these seven paths, all inside the task's allowed paths (without `--no-renames` git folds the old recording into a rename and prints six):

```text
docs/program/SECTION-GP-FULL-01.md
docs/program/tasks/SECTION-GP-FULL-01.md
fixtures/recorded/sections/gp/9dbe139a3b025683b91448992b6890a0a7bd54750e95969a3a396c60b7a8b959.json
fixtures/recorded/sections/gp/d6e106170da12a9a764a218a5bdb7207a355b02563d25e759663e2fcc2f7466e.json
src/auditmanager/analysis/text/profiles/gp/profile.json
src/auditmanager/analysis/text/profiles/gp/system_prompt.md
tests/unit/analysis/text_profiles/section_profile_expectations.json
```

No other section's files, no `W59-SECTION-PROFILES-01.md`, registry, `P02_LOCK.json`, `contracts/**`, migration, `web/**`, `infra/**` or test file appears; `build_fixtures.py` is unchanged. The legacy repository was only read (`git -C /root/projects/PDF-proverka status --short | wc -l` prints `0` before and after).

## Final checks

On the committed tree (`git status --short` empty), at the commit before this paragraph:

| Command | Result |
|---|---|
| `pytest tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` | `105 passed` |
| governance one-liner on `docs/program/tasks/SECTION-GP-FULL-01.md` | `[]` |
| `git diff --check 3c80af0e..HEAD` | rc 0 |
| section set, `build_fixtures.py --check`, HTTP test, web test | `211 passed`; `fixtures match`; `4 passed`; `95 passed` |
