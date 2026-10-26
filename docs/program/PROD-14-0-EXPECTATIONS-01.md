# PROD-14-0-EXPECTATIONS-01 — the section status and version pins are read from one file

Task: `docs/program/tasks/PROD-14-0-EXPECTATIONS-01.md`. Branch `agent/prod-14-0-expectations-01`, base `749e2efc` (`integration/ar-close-1026`). Plan item `PROD-14.0` of `PRODUCTION-READINESS-PLAN-01.md`; owner rulings `R-146l`, `R-146v`.

## Result

Four shared test files no longer pin `draft` / `1.0.0` for the real section packages. They read `tests/unit/analysis/text_profiles/section_profile_expectations.json`, one physical line per package, and a section lane that moves its profile out of `draft` changes its own `profile.json` and that one line. No product behaviour changes: `src/**` is untouched and every package is still `draft` at `1.0.0`.

Premise: **match.** The four files and every pin the plan names exist (`test_text_profile_packages.py:173-174` and `:197`, `test_analysis_profiles_over_http.py:98` and `:105`, `test_text_profile_registry.py:195`, `analysis-settings.test.ts:43-44`), and all fourteen `profile.json` declare `draft` at `1.0.0` (outputs in the task file, P-01 and P-02). Three things the plan did not name were also found and are handled below: the literal ``draft`` asserted in `pb/open_questions.md` (`test_text_profile_packages.py:324`), the web fixture's baked-in `TX` 1.2.0 and `POS` reviewed, and the e2e selector `tr[data-profile="draft"]`.

## Files changed

| File | Change |
|---|---|
| `tests/unit/analysis/text_profiles/section_profile_expectations.json` | new: format `section-profile-expectations/1`, 14 lines (`code`, `status`, `profile_version`) in the registry order `AI, PS, POS, TX, KJ, KM, OV, VK, PT, EOM, SS, ITP, GP, PB`; no AR line (AR is `builtin`, has no package) |
| `tests/unit/analysis/text_profiles/test_section_profile_expectations.py` | new: 5 cases that hold the file itself and its agreement with every `profile.json` |
| `tests/unit/analysis/test_text_profile_registry.py` | the two real-tree cases read the file |
| `tests/unit/analysis/text_profiles/test_text_profile_packages.py` | three cases read the file; one test renamed |
| `tests/integration/composition/test_analysis_profiles_over_http.py` | the served rows are compared with the file |
| `web/tests/unit/analysis-settings/analysis-settings.test.ts` | fixture built from the file; 4 new cases; 3 wording cases moved onto synthetic variants |
| `docs/program/tasks/PROD-14-0-EXPECTATIONS-01.md`, this report | records |

One file, not two: the web test reads the same JSON through `REPO_ROOT` and `readJson` from `web/tests/guards/lib/repo.ts`, which several other web unit tests already use for files outside `web/`. No second copy exists, so no identity test between copies is needed.

The file, as the section lanes will see it (one line each):

```json
    {"code": "AI", "status": "draft", "profile_version": "1.0.0"},
```

## What each assertion was before and after

`test_text_profile_registry.py` (33 cases before and after)

- `test_the_tree_registers_without_error_and_without_an_ar_package`: before, for every non-AR entry, `package == code.lower()`, `status in {"draft", "reviewed"}` and the prompt equals the file. After, all of that still holds, plus a package set equal to the file's code set in both directions and `(status, profile_version) == expected[code]` for every package. Nothing removed.
- `test_the_tree_registers_all_fifteen_sections_pb_included`: before, `entry.status == "draft"` for PB. After, `entry.status` and `entry.profile.profile_version` equal PB's line. The version equality is new; the pin on the value `draft` is gone by design. The message "no expert review exists" was a claim, not an assertion, and is removed.
- Unchanged by design: the cases that write a synthetic package to a temporary directory and load it (`_profile` defaults `draft` / `1.0.0` at `:42-43`, `:92`, `:248`). They test the loader, not the tree.

`test_text_profile_packages.py` (12 cases before and after)

- `test_exactly_the_thirteen_legacy_sections_and_pb_have_a_package`: before, the package codes equal the 13 + PB set. After, also equal to the file's code set in both directions (a package without a line, a line without a package).
- `test_every_profile_manifest_has_the_text_profile_1_shape`: before, `profile_version == "1.0.0"` and `status == "draft"` for every legacy package. After, both equal that package's line, and a package without a line fails by name; the failure message now carries both values.
- `test_the_authored_profile_declares_no_source_and_is_a_draft` is now `..._and_the_expected_status`: the same two assertions, on PB's line.
- `test_pb_open_questions_are_listed_in_the_package`: before, the literal ``draft`` and `D-178` were asserted in `pb/open_questions.md` always. After, `D-178` always, and ``draft`` only while PB's line is `draft`. **This is the one loosening**: it is identical today, and it lets the PB lane rewrite the sentence it owns once PB leaves `draft`. The `>= 8` open questions assertion next to it is unchanged and is flagged under known limitations.

`test_analysis_profiles_over_http.py` (4 cases before and after)

- before, `profile["status"] == "draft"` for every non-AR row and for PB; `profile_version` was only compared with the registry entry. After, `(status, profile_version) == expected[code]` for every non-AR row and for PB (the version comparison with the file is new), the registry comparison is kept, and the served package set equals the file's code set in both directions.

`analysis-settings.test.ts` (18 cases before, 22 after)

- fixture: before, the base rows baked `TX` at 1.2.0, `POS` as reviewed and the rest `draft` at 1.0.0. After, the base rows are the file's lines (AR `builtin`); a missing line throws `expectations file: no line for <CODE>` (no silent default).
- `marks a draft as needing an expert review, in words`, `shows the authored ПБ draft and its required expert review`, `labels a reviewed profile and shows its own version`: the same strings are asserted (label, `data-profile`, version), now on a synthetic variant of one row built by `withProfile`, so they hold whatever any real section's status is.
- new: `has a line for exactly the packages that exist, with the status and version each declares` (reads every `profile.json`); `can fail: ...` (hermetic synthetic maps; the check sees a changed status, a changed version, a missing line and a line without a package); `renders every package row with the status, its words and the version its line names`; `shows the authored ПБ profile as its line names it, with no legacy source`.
- unchanged: the label cases (`ANALYSIS_PROFILE_STATUS_LABELS` keys `builtin`, `draft`, `reviewed`; `analysisProfileStatusLabel('draft')`) test the renderer's vocabulary, not a section.

## Mutation table (every guard shown failing)

Each row is one uncommitted edit of the expectations file, applied alone, one test file run, the file restored byte for byte (its SHA-256 checked) and the test run again. All 40 cells went red; all five files were green after restoring. Run: `python3 .../scratchpad/prod14/mutate.py registry,packages,guard,http,web <8 mutations>`, output kept as the lane's `final-matrix.txt`. The mutation edits the expectation, never a `profile.json`: the comparison is an equality, so "the file says reviewed, the package says draft" and the reverse are the same observation.

| Mutation | registry | packages | http (needs the stack) | web | the guard file |
|---|---|---|---|---|---|
| status `AI` draft to reviewed | red 1: `AI: the registry and the expectations file disagree on (status, profile_version)` | red 1: `AI: profile.json declares status 'draft', the expectations file 'reviewed'` | red 1: `AI: the served (status, profile_version) is not the expectations file's` | red 1: `AI: status reviewed in the file, draft in profile.json` | red 1: `profile.json and the expectations file disagree` |
| version `AI` 1.0.0 to 1.0.1 | red 1: same as above | red 1: `AI: profile.json declares version '1.0.0', the expectations file '1.0.1'` | red 1: same | red 1: `AI: version 1.0.1 in the file, 1.0.0 in profile.json` | red 1: same |
| status `PB` draft to reviewed | red 2: the generic loop and the PB case | red 1: `PB: profile.json declares status 'draft', the expectations file 'reviewed'` | red 1: `PB: the served ...` | red 1 | red 1 |
| version `PB` 1.0.0 to 1.0.1 | red 2 | red 1: `PB: ... version '1.0.0', ... '1.0.1'` | red 1 | red 1 | red 1 |
| delete the `KJ` line | red 1: `a registered package has no line in the expectations file` | red 2: `a package has no line in the expectations file` and `KJ: no line in the expectations file` | red 1: `a served package has no line in the expectations file` | the suite fails at load: `expectations file: no line for KJ` | red 2 |
| delete the `PB` line | red 2 (the second is `KeyError: 'PB'` in the PB case) | red 3 | red 1 | fails at load: `no line for PB` | red 2 |
| add a `ZZ` line (no package) | red 1: `a line of the expectations file has no registered package` | red 1: `a line of the expectations file has no package` | red 1: `a line of the expectations file has no served package` | red 2: `ZZ: a line of the expectations file has no package`, `no row for ZZ` | red 2 |
| add an `AR` line (`builtin`) | red 1: same | red 1: same | red 1: same | red 2 | red 3 (also the vocabulary and the AR rule) |

Six more mutations apply to the guard file alone (what only it holds); all red, and green after restoring: a duplicated `KJ` line (`a section is written twice`), `KJ` and `KM` swapped (`codes == REGISTRY_ORDER`), the format string `/2`, two sections on one physical line (`each section must be written on a line of its own`), a status `approved` (vocabulary), a version `1.0` (three-part version).

## Test results

Run in the lane worktree on the tree being committed, one pytest at a time; the Python environment was `PYTHONPATH=src:<bootstrap site-packages>` with the repo `.venv`.

| Command | Result |
|---|---|
| `pytest -q` on `test_text_profile_registry.py`, `test_text_profile_packages.py`, `test_section_profile_expectations.py` | `50 passed` (33 + 12 + 5) |
| `pytest -q tests/integration/composition/test_analysis_profiles_over_http.py`, the lane `.env` exported | `4 passed` |
| `pytest -q tests/integration/sections/test_section_recordings.py` | `109 passed` |
| `npx vitest run tests/unit/analysis-settings` (in `web/`) | `7 files, 95 passed` (the analysis-settings file: 22) |
| `npx tsc --noEmit`, `npx eslint tests/unit/analysis-settings/analysis-settings.test.ts` | exit 0, exit 0 |
| `git diff --check` | exit 0 |
| governance one-liner on the task file | `[]` |
| `pytest -q tests/contract/program` on the committed tree | CONTRACT_PROGRAM_RESULT |

No full gate and no live journey was run (`R-135`: the complete gate comes after the code series).

## For a section lane: to move section X out of `draft` you change

1. `src/auditmanager/analysis/text/profiles/<x>/profile.json`: `status` (`reviewed`) and `profile_version` (a three-part version), and the edits to `system_prompt.md` the expert decided. Your directory.
2. `fixtures/recorded/sections/<x>/**`: rebuild the synthetic recording with the builder (editing a prompt orphans it; `SECTION-RECORDINGS-01.md`). Your directory.
3. **One line** of `tests/unit/analysis/text_profiles/section_profile_expectations.json`: the line of code `<X>`, for example `{"code": "KJ", "status": "reviewed", "profile_version": "1.1.0"}`. Keep it on its own line and in place.

Nothing else in any test file. Then run `pytest -q tests/integration/sections/test_section_recordings.py tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles/test_text_profile_packages.py tests/unit/analysis/text_profiles/test_section_profile_expectations.py`, and on the lane stack `tests/integration/composition/test_analysis_profiles_over_http.py`, and in `web/` `npx vitest run tests/unit/analysis-settings`. If you forget the line, or edit only the line, the guard names the section and both values. Because each section edits a different line of the file, section lanes merge without a conflict in it.

## Known limitations

- `pb/open_questions.md` is still pinned by content in `test_text_profile_packages.py`: at least eight numbered questions and the id `D-178`. The PB lane answers those questions (plan item 14.PB) and must decide, in its own review, what that case should hold; this task made only the ``draft`` sentence conditional.
- `tests/e2e/pc01/journey/manifest.json` has a step with the selector `tr[data-profile="draft"]` on the settings screen. It stays green until the last package leaves `draft`; the lane that moves the last section (or `PROD-18`) must revise that selector. It is outside this task's paths and is not run here (the live journey is deferred by `R-135`).
- `fixtures/recorded/sections/*/*.json` carry `origin.profile_status: "draft"`. Nothing asserts it (`rg profile_status` finds it only in those fixtures), so it is informational; a section lane's rebuild updates it.
- The HTTP case needs the lane stack and the lane `.env`; it was run against the integrator's `ar-close-1026` stack, which this lane did not start or stop.
- The wording cases of the web test use `draft`, `reviewed` and the versions `7.3.1` / `1.2.0` as synthetic inputs of one row; those literals are not pins on a section and remain.
- The file's `about` key is prose for the reader; the guard requires it to be non-empty and nothing more.
- `PROD-11` (removal of `builtin` from the web test) must rebase onto this task; the plan already orders them so.
