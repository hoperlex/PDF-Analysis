# SECTION-AI-FULL-01 — the АИ (AI) profile answers its open questions and is `reviewed`, without a human review

Task: `docs/program/tasks/SECTION-AI-FULL-01.md`. Branch `agent/section-ai-full-01`, base `0e663fd0` (`integration/ar-close-1026`). Plan item `PROD-14` (section `AI`); owner rulings `R-146ag`, `R-146ah`, `R-146ai`; template `SECTION-<CODE>-FULL-01` of `dispatch/PRODUCTION-WAVE-PW2B.md`.

## Result

The `AI` record in `W59-SECTION-PROFILES-01.md` has four open questions. Each has one written decision below: three are **K** (keep) and one is **N** (narrow). The four cross-section questions are applied as the wave table fixes them (all **K**). One more change was found by an audit the template does not name: a class designation in condition 2 that the section's pinned legacy source does not contain, which is removed. The prompt changed, so `profile_version` is `1.1.0`, the recording is rebuilt, and `profile.json` and the `AI` line of the expectations file say `reviewed`.

**`reviewed` here is not expert verification.** Nobody has reviewed this profile: not an expert, not the owner (`R-146ag`, accepted risk `A-7`). The decisions were taken conservatively from the five hash-pinned legacy files and the record, and nothing was measured on real text. The status must not be quoted anywhere as a human review.

Premise: **match.** Package, status and version, the five source hashes at the pinned commit, the four questions, the four cross-section questions, the expectations line and the one recording are as the brief says (task file, P-01 to P-08).

## Decisions

Quoted question openings are the record's own words. «Condition n» means v1's numbered conditions in the prompt.

| # | Question (record) | Decision | Reason | Exact change |
|---|---|---|---|---|
| 1 | «цвет — по выбору заказчика», «артикул согласовать с заказчиком», «по утверждённому образцу»: placeholder or an accepted decision to defer the choice? | **K** | Cross-section decision (1) applies: a deferral to the customer is the same class as «уточнить по месту»; turning it into an accepted instruction is an expert's call and would silence findings. The placeholder category and the last hint bullet («отметки о незаполненности … на месте марки, артикула, цвета или класса материала») are unchanged, so these phrases are neither added as examples nor excluded; whether the model flags a phrase without a literal marker stays under v1's «и подобное». | none |
| 2 | General height in the general notes («высота помещений в чистоте 2,70 м») against the lower height of a room with a suspended ceiling in the finish schedule: contradiction or a general figure rooms may deviate from? | **K** | The hint bullet compares the height «одного и того же помещения» and conditions 1 and 2 stay in force («Ищи в тексте прямое указание на то, к чему относится значение»). Deciding that a general figure is one rooms may legitimately deviate from is a domain interpretation. The pinned source gives only the items «Высоты помещений» and «высота подвеса» and no such rule, and a narrowing would silence the comparison between the general notes and the finish schedule for ceiling height. No field case exists (`R-146v`) to show the false-positive rate. Listed under assumptions. | none |
| 3 | General notes set a class for evacuation routes («отделка стен и потолков — КМ1»), the finish schedule gives КМ2 for a corridor: internal contradiction or a hidden norm check left for W57? | **K** | The comparison is between two classes written in the document and needs no norm: the exclusion sentence (СП, СНиП, ГОСТ, no judgement whether a decision is right) is unchanged and no required class is stated anywhere in the prompt. The record already reframes the legacy item «классы пожарной опасности … для путей эвакуации» as a same-document cross-check of the class of one material «без нормативных требований к ним». Whether the corridor is on an evacuation route is read from the text only; without a direct indication condition 1 applies. | none |
| 4 | Finish schedule and explications are often made per apartment type and room numbers repeat across floors and types: is condition 1 enough, or does comparing names and areas by room number give systematic false findings? | **N** | Condition 1 is not enough for this bullet, because the bullet itself keyed the object on the number («помещения с одним и тем же номером»), which tells the model to treat equal numbers as one object, so equal numbers on different floors or apartment types are compared as one room. A display number is not an identity (`AGENTS.md` section 4). The change only adds a condition before the comparison; it widens nothing and adds no number, norm or designation. | hint bullet 9, see below |
| A | Audit (not a record question): numerals and class designations of the prompt against the pinned source | **N** | `Г1–Г4` in condition 2 is a class designation that none of the five files contains (`role.md` has only «классы горючести»). The rule forbids it in the section's profile, not only in additions. Removing the designation keeps the pair «класс пожарной опасности (КМ) / группа горючести» as a near-miss, so condition 2 still tells the model not to compare them. | condition 2, see below |

Cross-section decisions (the same for every lane; this lane agrees with them and has nothing to report against them):

| # | Question | Decision | AI-specific note |
|---|---|---|---|
| 1 | Site and contractor phrases | **K** | Covers question 1 above. |
| 2 | «Итого» against the sum of rows | **K** | The prompt has no recomputation bullet; the quantity bullet compares quantities «прямо указанные» in two places and sums nothing. |
| 3 | Text read from sheets | **K** | The record names no bullet whose false findings come from detached sheet text. The bullets that read marks and captions («подписях планов», «марках помещений на планах») are unchanged except bullet 9, narrowed under question 4 for the number-repeat reason, not because it reads sheets. |
| 4 | Missing items | **K** | No third kind of observation; condition 5 stays; the record's excluded list («наличие всех помещений в ведомости отделки» and similar) stays excluded. |

## The prompt change in words

Two edits in `system_prompt.md`; everything else is byte for byte what it was (the package tests hold v1's question, categories, conditions and output contract).

1. **Hint bullet on room name and area (question 4).** The bullet no longer says «помещения с одним и тем же номером». It names what is compared: the name and area of a room in the room explication and in the room marks on the plans, and its name in the finish schedule and the floor explication. A sentence follows: a room number may repeat on different floors, in different sections and apartment types, and an equal number alone does not make two mentions one room; compare them only if the text directly places both mentions on one floor, in one section and in one apartment type, or if the number occurs in the document for one room only.
2. **Condition 2 (audit).** «(Г1–Г4)» after «группа горючести» is removed; the two attributes in that near-miss pair stay.

New numerals: none. New norm references: none. New designations: none. Findings: only narrower than before.

## Audit of numerals and designations

Run before and after the edit (task file P-09 has the base output). After the edit the digit-bearing tokens of the prompt are `Е0,5` (in `project_params.md`) and `Е1,` (in `checklist.md` and `project_params.md`); the capital-letter tokens left are `КМ` and `АИ` (in the source) and v1's own words (`TBD`, `XX`, `ГОСТ`, `СП` and upper-case emphasis). With «(Г1–Г4)» put back, the script reports `'Г1–Г4' in legacy source: False` again, so it can fail. The script that was run (it lives outside the repository; this is its exact text):

```python
"""Audit: every digit-bearing token and capital-letter class designation in a section prompt
must occur in the section's five hash-pinned legacy files (read at the pinned commit)."""
import json, re, subprocess, sys
from pathlib import Path

root = Path(sys.argv[1])           # worktree
code = sys.argv[2]                 # e.g. AI
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

1. **Question 1 (K).** Whether the model flags «цвет — по выбору заказчика» is left to v1's wording. The profile neither lists nor excludes it.
2. **Question 2 (K).** A general height from the general notes and a lower height of a room with a suspended ceiling are still compared when the text ties them to one room. If an expert holds that the general figure is one rooms deviate from, this gives false findings.
3. **Question 3 (K).** КМ1 in the general notes against КМ2 for a corridor is still reported when the text puts the corridor on an evacuation route. The model decides that from the text alone and can be wrong either way.
4. **Question 4 (N).** Where a document gives no floor, section or apartment type and its room numbers repeat, a real mismatch in room name or area is no longer reported. Where the number occurs for one room only, the comparison stays.
5. **Terms from the earlier drafting, not from the source.** The hint bullets carry words such as «площадь помещения», «исполнение (левое или правое)» and «класс эксплуатации» that none of the five files contains. The audit above covers numerals, norm references and class designations only; none of these words is one, and this lane did not remove them.
6. **Nothing was measured.** The recording is synthetic, authored by hand over the AR corpus; it proves routing and replay and says nothing about how the profile performs on a real АИ volume.

## Files changed

| File | Change |
|---|---|
| `src/auditmanager/analysis/text/profiles/ai/system_prompt.md` | the two edits above |
| `src/auditmanager/analysis/text/profiles/ai/profile.json` | `profile_version` `1.0.0` to `1.1.0`; `status` `draft` to `reviewed` |
| `fixtures/recorded/sections/ai/131994ad…1da6.json` | rebuilt by `build_fixtures.py`; replaces `a03cfde3…bf8f.json`; the diff against the old file is `origin.profile_status` (`reviewed`), `origin.prompt_bundle_sha256` (`641ba209…3098`) and `request_sha256`; the authored reply, usage and latency are unchanged |
| `tests/unit/analysis/text_profiles/section_profile_expectations.json` | the `AI` line only: `reviewed`, `1.1.0` |
| `docs/program/tasks/SECTION-AI-FULL-01.md`, this report | records |

The builder writes all fourteen recordings; thirteen came out byte-identical (`git status` shows no other recording). No test file was edited, so no assertion was weakened: there is no before/after of a modified test to give.

## Mutation table

Each row edits one thing in the working tree, runs the section test set, restores the file and proves the restore by a SHA-256 over the four files. The set is `test_text_profile_registry.py`, `tests/unit/analysis/text_profiles`, `tests/integration/sections/test_section_recordings.py` and `tests/contract/analysis_packages` (211 cases). The unmutated tree: `211 passed`.

| Mutation | Result | First red cases |
|---|---|---|
| `profile.json` status `reviewed` back to `draft` (version kept) | 4 failed | registry `test_the_tree_registers_without_error_and_without_an_ar_package`; guard `test_every_line_agrees_with_its_package_profile_json`; packages `test_every_profile_manifest_has_the_text_profile_1_shape` |
| `profile.json` version `1.1.0` back to `1.0.0` (status kept) | 3 failed | the same three |
| the `AI` expectations line back to `draft` / `1.0.0` (`profile.json` kept) | 3 failed | the same three |
| the `AI` expectations line, status only back to `draft` | 3 failed | the same three |
| `system_prompt.md` back to the base text (recording kept) | 8 failed | recordings: `test_each_section_has_one_synthetic_recording_keyed_to_its_own_request[AI]`, `test_the_builder_reports_no_drift`, `test_the_served_adapter_answers_each_recorded_section_and_the_canonical_alone_does_not[AI]` |
| the recording back to the base file (new one removed) | 8 failed | the same three recordings cases |
| `origin.profile_status` `reviewed` to `draft` inside the new recording (key kept) | 1 failed | `test_the_builder_reports_no_drift` |
| the `AI` expectations line back to `draft` / `1.0.0`, on the lane stack | 1 failed, 3 passed | `test_analysis_profiles_over_http.py::test_every_row_is_the_registry_entry_the_application_routes_by` |
| the same, in the web test | 1 failed, 21 passed | `has a line for exactly the packages that exist, with the status and version each declares`: `AI: status draft in the file, reviewed in profile.json` |
| «(Г1–Г4)» put back into condition 2 | the audit script prints `'Г1–Г4' in legacy source: False` | not a repository test (see the limit below) |

After each restore the SHA-256 over the four files was equal to the one taken before (`restored=True`), and the tests were green again (`211 passed`; HTTP `4 passed`; web `95 passed`). Two earlier probes, before the rebuild: with the prompt edited and the recording not rebuilt, the builder's `--check` exits 1 listing the new key and the old file as `(stale)`, and `test_section_recordings.py` has 8 failed, 101 passed.

## Commands and results

From `/root/projects/PDF-Analysis/.local/worktrees/section-ai-full-01`, shared venv, one pytest at a time. `$BS` is `/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages`. Status codes are `PIPESTATUS` of the test process.

| Command | Result |
|---|---|
| section set (above), base `0e663fd0` | rc 0, `211 passed` |
| section set, after the change | rc 0, `211 passed` |
| `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py`, then `--check` | rc 0 (`wrote …131994ad…`, `removed …a03cfde3…`); `--check` rc 0 `fixtures match` |
| `tests/integration/composition/test_analysis_profiles_over_http.py`, lane `.env` exported | rc 0, `4 passed` |
| `npx vitest run tests/unit/analysis-settings` in `web/` | rc 0, 7 files, `95 passed` |
| governance one-liner on the task file | `[]` |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, `git diff --check` | rc 0, `105 passed` (on the committed, clean tree); `git diff --check 0e663fd0..HEAD` rc 0 |

Free disk at the start and at the end of the lane: 1.8 GiB (`df -h /`). No docker command, no push, no model call, no process killed.

## Integration notes

1. **The web label for `reviewed` says «проверен экспертом»** (`web/src/entities/analysis-profile/model/presentation.ts:16`), and the schema docstring of `AnalysisProfileStatus` says «a package an expert has reviewed» (`src/auditmanager/api/schemas/models.py:2437`). With `A-7` that is a false statement the product would show for `AI` as soon as this lane merges. Both are outside this lane's paths (`web/**`, `src/auditmanager/api/**`). **Decide before the first section lane merges**: a label and docstring that say `reviewed` without human review (for example «проверен без экспертной приёмки»), changed once for all fourteen lanes. The web unit test `labels a reviewed profile and shows its own version` asserts the current wording on a synthetic row and will need the same edit.
2. **Identity:** `analysis_profile_id` and `prompt_bundle_id` are unchanged (the lane mints none), while the bundle's text and hash changed and the profile hash changed with the version. A run of the draft `AI` profile that is already stored carries the old `analysis_profile_sha256` and `prompt_bundle_sha256` (`src/auditmanager/analysis/text/stage.py:498-499`); the registry resolves by the id pair and serves only the new text. Development stand only, no migration (`R-146ah`).
3. **The recording's `origin`** still names `W59-ANALYSIS-SETTINGS-01` as its authoring task and now says `profile_status: reviewed`; its statement still says «Not field evidence for the profile's review». The builder (`build_fixtures.py`) is not in this lane's paths and was not touched; every other lane's rebuild leaves `AI` unchanged.
4. **e2e manifest:** the step with the selector `tr[data-profile="draft"]` (named in `PROD-14-0-EXPECTATIONS-01.md`) stays valid while any other section is `draft`.
5. **Merge:** the expectations file changes on the `AI` line only, so lanes merge without conflict; re-run the section set, the HTTP test and the web test after the last section merges.
6. **Debt and ledger:** the record `W59-SECTION-PROFILES-01.md` still says «Every profile is `status: draft`». It is a forbidden path for the lane; the integrator should add the decisions of this report to the record or point to it, without calling the status an expert review.

## Limits

- No test holds the two prompt edits themselves. The wording of question 4 and the absence of a designation outside the source are held only by the recording's request key (so an edit without a rebuild goes red, as the table shows) and by the manual audit; a new guard test is outside this lane's paths. A cross-section guard that checks each prompt's numerals and designations against its pinned source would be a candidate for the integrator.
- The effect of the N edit on a model's answers is unmeasured; no model was called.
- The prompt uses the lane's reading of the text-only setting; an expert may disagree with any decision in the table, and the report says where.

## Forbidden paths untouched

`git diff --name-only 0e663fd0..HEAD` on the final tree prints exactly these seven paths, all inside the task's allowed paths:

```text
docs/program/SECTION-AI-FULL-01.md
docs/program/tasks/SECTION-AI-FULL-01.md
fixtures/recorded/sections/ai/131994ad9877d623894007365c0923105c1021199d0084731743d06f90471da6.json
fixtures/recorded/sections/ai/a03cfde3562613cfc7db02912f3ff883afa88f21719528ce87a13d8b0c04bf8f.json
src/auditmanager/analysis/text/profiles/ai/profile.json
src/auditmanager/analysis/text/profiles/ai/system_prompt.md
tests/unit/analysis/text_profiles/section_profile_expectations.json
```

No other section's files, no `W59-SECTION-PROFILES-01.md`, registry, `P02_LOCK.json`, `contracts/**`, migration, `web/**` or `infra/**` appears; `build_fixtures.py` is unchanged.
