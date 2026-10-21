# PB-PINS-01 — the tests that asserted the ПБ section has no profile say what is now true

Task: `docs/program/tasks/PB-PINS-01.md` (frozen by the integrator in `0c5af605`, copied into this branch byte
for byte). Branch `agent/lane-b-01`; slice 4 of lane B, after `SECTION-RECORDINGS-01` (tip `9df108f4`).
Tests only: no `src/**` change. Container-free except that the web tests ran under `vitest` on the gate
worktree's read-only `node_modules` link the integrator provided.

## Result

Five test files that pinned «ПБ has no profile» now assert what `PB-PROFILE-01` made true: ПБ is in the served
section table with a profile pair of its own, among the executable sections, and a start for a ПБ version pins
that pair. The refusal `section_profile_unavailable` is still proven, now on a registry built without a section.
In the web, the API fixtures mark all fifteen options executable and the «профиль анализа недоступен» states are
built, explicitly, for an imagined profile-less section.

## What changed

| File | Change |
| --- | --- |
| `tests/integration/composition/test_the_served_application_routes_by_section.py` | the table handed to `startRun` covers all fifteen sections and holds ПБ's own pair (replacing `assert "PB" not in ...`); the section port's executable set contains ПБ |
| `tests/integration/runs/test_w59_section_routing_over_http.py` | the review marks all fifteen executable (replacing `"PB" not in executable`); a registry without ПБ marks it not executable; the missing-profile refusal runs on `WITHOUT_PB`; a ПБ start pins ПБ's pair and replays; a КЖ start never pins it |
| `web/tests/unit/styles/screens.ts` | fixtures follow the API: all options executable, ПБ's profile is an authored draft with `source: null`; the unavailable states (confirmed note, corrected panel, refused form, a null profile row) are built for `UNPROFILED` (ГП) |
| `web/tests/unit/sections/classification-panel.test.ts` | the unavailable cases use a review without ГП's profile; new: nothing marked when all fifteen have one, ПБ executable, a chosen or confirmed ПБ carries no unavailable note |
| `web/tests/unit/sections/classification-correction.test.ts` | the unavailable case uses a review without ГП's profile; new: nothing marked when all fifteen have one |
| `docs/program/tasks/PB-PINS-01.md` | the frozen task file, identical bytes to `0c5af605` (`git diff 0c5af605 -- docs/program/tasks/PB-PINS-01.md` is empty) |

## Decisions taken

1. **The seam in `test_w59_section_routing_over_http.py` touches more than the cited lines.** To prove the
   refusal "on a registry built without a section" through the same adapters and routes, `_client` takes the
   registry as a parameter (default the real one) and the module builds `WITHOUT_PB`; that needed the import,
   the helper's signature, the module docstring and the new cases, all in the same file. No other file was
   touched for it.
2. **What a ПБ start asserts.** The task expects `recording_missing` "until `SECTION-RECORDINGS-01`", but this
   module never executes a run: its model adapter is `None` and its carrier only records. So it asserts what
   the code does at start: `202`, the run pinned to ПБ's profile and bundle, one job handed to the carrier, an
   exact replay answering the same run. ПБ's recorded replay is proven container-free by
   `SECTION-RECORDINGS-01` (slice 3, same branch), so `recording_missing` no longer applies to ПБ there.
3. **The profile-less example in the web moves from ПБ to ГП.** The census and the two unit tests needed a
   section without a profile to keep the «недоступен» states reached; ГП stands for "any section the registry
   lacks", named by one constant (`UNPROFILED`) in the census and by the argument of a small helper in each test
   file. ПБ is executable everywhere by default.
4. **`web/tests/unit/sections/fixtures.ts:78` is stale and was not changed** (not an allowed path):
   `executable: code !== 'PB'` still makes the shared `review()` fixture treat ПБ as profile-less. The two
   unit test files do not depend on it (each builds its own review from `review()`, forcing `executable` per
   option), but any other test that reads the default sees the old premise. **Follow-up for the integrator:**
   one line, `executable: true`, and its comment («PB without a registered profile»); after that the
   `reviewWithoutProfile(null, ...)` calls in the two files become `review(...)`.
5. **`section.ts` is untouched**, as ordered: its `analysed` flag is `false` for fourteen sections and the API's
   `executable` decides what can run. No test proved otherwise. The two stale docstrings (`analysis_profiles.py`
   line 8, `section_candidates/metadata.py` line 5) stay: documentation debt.

## Commands and exit statuses

From `/root/projects/PDF-Analysis/.local/worktrees/lane-b`. Python as before (shared venv interpreter,
`nice -n 10`, `-c pyproject.toml --rootdir=. -q -p no:cacheprovider`, status from pytest's own `$?`). Web:
`nice -n 10 npm --prefix web ...`, each redirected to a logfile, `rc=$?` read from it, one at a time, `free -m`
checked before each.

| Command | Result |
| --- | --- |
| `python -m py_compile` of the two Python files | ok |
| `--collect-only` of `test_w59_section_routing_over_http.py` and `test_the_served_application_routes_by_section.py` | rc 0, 20 and 5 tests collected |
| `test_the_served_application_routes_by_section.py`, **run** with dummy values for the six environment names the settings loader requires (`DATABASE_URL` and the five `S3_*`, pointing at `127.0.0.1:1`; no connection is made, the engine is lazy as the file's docstring says) | rc 0, 5 passed. At the base the file errors without those names, as before |
| `test_w59_section_routing_over_http.py` | **not run** (database and object store); compiled and collected only |
| `npm --prefix web run typecheck` | rc 0 |
| `npm --prefix web run lint -- --quiet` | rc 0 |
| `npm --prefix web test -- --run web/tests/unit/sections web/tests/unit/styles` as given | rc 1, "No test files found": with `--prefix web` the filter is relative to `web/` |
| `npm --prefix web test -- --run tests/unit/sections tests/unit/styles` | rc 0, 9 files, 144 tests passed (panel 29 and correction 29; before this slice 26 and 28, by the diff: four tests added). The style census guard, `tests/unit/styles/contrast.test.ts`, is in it: 20 passed |
| `git diff --check` | rc 0 |
| `tests/contract`, `--ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py`, once, clean committed tree `15c3733e`, `<lane-b>/.venv/bootstrap` linked by the integrator | **rc 0, 983 passed, 19283 subtests passed** (63 s to 69 s). Two earlier runs, without the `.venv/bootstrap` link, were rc 1 with 966 passed, 3 failed, 14 setup errors, every one of the 17 for one reason, «the governance interpreter is missing at `<lane-b>/.venv/bootstrap/bin/python`»; the first of them, on a dirty tree, also failed `test_alpha_acceptance_command`, which refuses an uncommitted checkout |

## Mutation probes

Web probes edit a file in place, run vitest on the two section files, restore it and prove the restore by a byte
comparison (`restored=True` every time). The Python probe moves the ПБ package away and back.

| Assertion class | Mutation | Result |
| --- | --- | --- |
| a registry without ПБ reddens the served-table pin | `profiles/pb` moved out of the tree (run with the dummy environment) | rc 1, 2 failed: exactly `test_start_run_passes_the_section_table_and_no_profile` and `test_the_executor_and_the_section_port_get_the_registry`; the three others pass; the directory restored |
| the web all-executable form | the test's review built without ПБ's profile (`reviewWithoutProfile('PB')`) | 1 failed in each of the panel (`marks nothing when every section has a profile`) and the correction file (`marks nothing...`) |
| a chosen ПБ carries no note | same, for the chosen ПБ | 1 failed (`says nothing about a missing profile for a chosen ПБ`) |
| a confirmed ПБ carries no note | same, for the confirmed ПБ | 1 failed (`adds no note to a confirmed ПБ version`) |
| the note follows the review | `version-classification.tsx`: `profileUnavailable = false` | 1 failed (`adds «профиль анализа недоступен» exactly when the review says so`) |
| the form marks by `executable` | `classify-version-form.tsx`: `data-executable` false for ПБ whatever the review says | 2 failed |
| the correction form marks by `executable` | `correct-version-classification-form.tsx`: the marker always empty | 1 failed |
| the census keeps the unavailable states reached | `screens.ts`: the corrected panel built with an all-executable review | **no test failed** (20 passed) |
| the census keeps a null-profile row | `screens.ts`: that row given a profile | **no test failed** (20 passed) |

The last two are honest negatives: `contrast.test.ts` names the colour-bearing rules no screen reaches but does not
fail when these particular states stop being reached, because other screens still reach the same rules. The
fixtures keep the states by design; nothing proves it, and no mutation is claimed for `screens.ts` beyond
`typecheck`.

## Not exercised

- `test_w59_section_routing_over_http.py` and the rest of the database-backed suite: not run here (`R-126`); the
  integrator's gate or a stand runs them. Its new cases are written against the shipped adapters, compiled and
  collected only.
- The web suite beyond the two paths, the live journey and `e2e:pc01` (not authorised for this slice).

## Risks

- `fixtures.ts:78` still tells every other web test that ПБ is not executable (decision 4); a test added later that
  reads the default inherits it.
- The census cannot be shown to need `UNPROFILED`: a later edit could drop the states without a failure.

## Instruction for the integrator

Merge after `PB-PROFILE-01` and `SECTION-RECORDINGS-01` (this slice's tests assume PB's profile). Have
`test_w59_section_routing_over_http.py` run on a stand (the database tests are the only ones not run), and apply
the one-line `fixtures.ts:78` follow-up if you want the shared default to follow the API.
