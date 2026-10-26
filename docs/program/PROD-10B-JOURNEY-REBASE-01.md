# PROD-10B-JOURNEY-REBASE-01 — the live journey, its fixtures and the manual protocol run on a section that stays

Task: `docs/program/tasks/PROD-10B-JOURNEY-REBASE-01.md`. Branch `agent/prod-10b-journey-rebase-01`, base `2aec42072c7ba81be59570206e99e29bfd9e041c` (`integration/ar-close-1026`). Step 4 of `PROD-10` (`AD-12`, `R-146w`) that `PROD-10-AR-V2-EXTRACT-01` left; wave `PW3`, lane J. The lane had no browser, no stand and no database: **nothing below says the journey ran.** What was checked is static or driver-level; what was not is listed under "Verify live" with its exact command.

## Result

The main flow of the journey (the three runs, the decision, the comparisons and the carried decision, the exports, the blocks, the queue, the dashboard, the correction of a classification), the Python acceptance suite, the live-provider test, the six write fixtures and the manual protocol now confirm the baseline set as **ПБ**. Nothing outside `write.ar_bound` names АР, classifies as АР or starts a run on an АР version, and a static test refuses a regression. The «Оптимизация» tab and the АР Form-7 cannot leave АР (they read АР sets only and the saved text of a published АР run): they stay as they were, are named, and are the part of the journey `PROD-11` breaks. The two stale pins of `D-226` follow the suite's facts source and pass against the real router.

### Why ПБ (decided by the lane; the choice is one constant, `JOURNEY_SECTION` in `tests/e2e/pc01/driver.py`)

| Candidate | Findings / evidence of its recording over the baseline text | Verdict |
|---|---|---|
| **ПБ** | 3 / 5, the same categories, pages (2, 6, 3, 7, 8) and quotations as the canonical АР recording (`identical-to-AR=True`) | chosen: every figure the acceptance suite measured on the АР run holds, none is re-derived |
| ГП, ОВ, ПТ, ТХ | 2 / 3 or 4 | the `accept` + `reject` pair would still work, the pins would all change |
| АИ, СС, ВК | 1 / 1 | cannot reject one finding and accept another (`test_acceptance` needs two) |
| ПЗ, ПОС, КЖ, КМ, ЭОМ, ИТП | 1 / 2 | same |
| КЖ | also the section `section-form7-without-members` uses as its empty one | excluded for that reason too |

ПБ is also the one section whose prompt names the seeded defects' subjects: `grep -ci эвакуац` over the fourteen `system_prompt.md` files counts lines: 8 for ПБ and 0 for every other, and `grep -ci огнестойк` is 5 for ПБ (3 for ОВ; 1 for КЖ, КМ, ПТ, АИ, ПЗ; 0 for the rest). That matters for the manual protocol, where a live model reads the same text, and it is only a reason to expect, not a measurement. Costs, stated: ПБ's profile is authored (no legacy source) and `reviewed` without any human review (`R-146ag`, `A-7`); its recording replays through the real stage container-free (109 passed) but a ПБ run through the executor on a database has not been run (the database test covers АИ, ПЗ, ПОС, ТХ only); what a live model finds under the ПБ profile is unmeasured.

## Premise: the follow-up table of `PROD-10`, row by row

Evidence in the task file (P-01, P-02). Deviation: **five** steps press «Запустить прогон», not four (`queue-start-a-run-while-paused` is the fifth; it runs the third version and follows its classification). No other deviation.

| Row of the follow-up table | Done |
|---|---|
| Section of the three analysis runs, `classification-correction` | `classify-version`, `-second-`, `-third-`: choice and echoed `section_code` АР→ПБ; `classification-correction`: request body and answer АР→ПБ |
| The specification set (`upload-`, `classify-`, `start-specification-run`) | **held on АР**: `write.ar_bound` (see below). Not decided: what feeds it after `PROD-11` |
| Settings screen `tr[data-section="AR"][data-profile="builtin"]` | kept (`registry_pins`: `PROD-11` removes `builtin`); a ПБ row `reviewed` with the label «рабочая версия, проверка человеком не проводилась» is asserted beside it (the expectations file gives ПБ `reviewed`) |
| Counts that assume the set is АР | `dashboard-sections-panel`: АР→ПБ; `section-form7` held on АР (members are АР sets); `section-form7-without-members` keeps КЖ and is held different from the journey's section |
| Static pins | `driver.py` default, `test_acceptance.py`, `test_live_text_analysis.py`, the six write fixtures, `README.md`, comments of `journey.mjs` and `write.mjs`. `test_pc01_journey_conformance.py` is **unchanged**: its АР hits are the generic enumeration checks and the committed specification set |
| Manual protocol | A03a (confirm П and ПБ) added, A05 reworded, A09 item 21 corrected to the labels the screen now has. `scripts/manual-alpha-check.sh` is outside the paths; its three mentions are file names of the bundle |
| `D-223` says the manifest selects `tr[data-profile="draft"]` | already false at the base (`git grep` finds none); nothing to do |

## What `write.ar_bound` is, and the three steps added

`manifest.json` → `write.ar_bound` lists (`steps`, 33) every step that may name АР, (`needs_published_run`, 15) the subset that cannot pass without a published АР run, directly or through the pass it produced (read from the steps' expectations, **not measured**), and (`registry_pins`, 1) the step that names the АР registry row.

The step `optimisation-pass-over-a-set-without-a-table` used the journey's own first set, now ПБ. A pass over a set of another section is refused (`409`, `section_not_ar`, `project_match.py:281`), so it and `proposals-csv-of-an-empty-pass` (which uses its pass) were silently bound to a set that can no longer serve them. Three steps were added before the specification set (the same bundle as a new document, confirmed АР, run with the canonical АР recording, as the journey's first set was before this lane) and the pass is bound to them. They are in `ar_bound` and are the first thing `PROD-11` deletes. The write steps are 112 (109 + 3); the pinned-steps guard (95 names, in order) is untouched.

## Files changed (`git diff --stat 2aec4207..HEAD`, 15 files, no file outside the allowed paths)

| Path | Change |
|---|---|
| `tests/e2e/pc01/journey/manifest.json` | classification pins АР→ПБ (4 places + the correction), `ar_bound`, 3 new steps, bind of the empty-pass step, ПБ row in settings, dashboard ПБ, comments, two free-text work descriptions |
| `tests/e2e/pc01/journey/fixtures/redden-write*.manifest.json`, `fixtures/w28-live/w28-{measure,proxy,recorded,recorded-redden}.manifest.json` | a `classify-version` step (П, ПБ) before `start-run`, and a note; `redden-write-bound`'s comment says which step carries the 1 ms bound |
| `tests/e2e/pc01/journey/README.md`, `journey.mjs`, `write.mjs` | section ПБ in the intro and the `classify-version` row; a section on the choice and `ar_bound`; a note on the six fixtures; two comments |
| `tests/e2e/pc01/driver.py` | `JOURNEY_SECTION = "PB"`; `classify_version` defaults to it |
| `tests/e2e/pc01/test_acceptance.py` | the journey fixture's comment; two pins of `D-226`; one `"AR"` pin (below) |
| `tests/e2e/pc01/test_live_text_analysis.py` | comment: ПБ, marked not yet measured live |
| `tests/e2e/test_pc01_journey_section.py` | new, 10 tests (recording equality, classification steps, `ar_bound` guard, documents, controls) |
| `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` | A03a, A05, A09 item 21 |
| `docs/program/tasks/PROD-10B-JOURNEY-REBASE-01.md`, this file | records |

## Modified tests: what each asserted before and after

| Test / step | Before | After |
|---|---|---|
| `test_c3_the_surface_declares_no_operation_that_can_mutate_a_version` | `set(mutating) ==` a hand-written list of 11 names (red: the router serves 12) | `set(mutating) ==` the operation ids of `FACTS.operations` with PUT, PATCH or DELETE (`tests/support/expected_facts.json`, the file criterion 1 already counts against); the checks that no mutating operation but `classifyDocumentVersion` addresses `/versions` or `/documents`, and that the version admits no mutating method, are unchanged |
| `test_c10_every_failure_leaves_the_edge_as_one_typed_envelope` | `payload["contract_version"] == "1.0.0"` | `== FACTS.contract_version` (`1.6.0`) |
| `test_c3_a_second_upload_publishes_a_new_identity…` | the classification's `section_code == "AR"` | `== driver.JOURNEY_SECTION` |
| `journey` fixture of `test_acceptance.py`, `live_run` of `test_live_text_analysis.py` | classify as АР (driver default) | classify in `JOURNEY_SECTION` (driver default); every figure asserted afterwards is unchanged (see recording equality) |
| manifest `classify-version`, `-second-`, `-third-` | click АР; answer `section_code` equals `AR` | click ПБ; equals `PB`; nothing removed |
| manifest `classification-correction` | request body `section_code":"AR"`, answer `AR` | `PB`, `PB`; nothing removed |
| manifest `dashboard-sections-panel` | `li[data-section="AR"] strong` is a positive integer | the same for `PB`. **The АР count is no longer asserted** (decided by the lane: it was the count of the journey's own set; the АР sets are in `ar_bound`, which `PROD-11` rebuilds) |
| manifest `analysis-settings-lists-the-profiles` | five presence checks | the same five plus the ПБ row; nothing removed |
| manifest `optimisation-pass-over-a-set-without-a-table` | pass over `{document_uid}` (the journey's first set) | the same assertions over `ar_document_uid`; nothing removed |

No assertion of any other test was touched. **Weakened:** the АР dashboard count (stated above) and, in the manual protocol, the A05 threshold "at least two of the three issues are found", which was measured under the АР profile and has never been measured under ПБ: it is no longer a PASS condition until a live ПБ run has set a baseline (the number found is to be reported). This is a protocol sentence, not a test.

## The guard and its mutation table

`tests/e2e/test_pc01_journey_section.py` reads the files with `json` and `ast` and executes nothing. It holds: (1) the recording of `JOURNEY_SECTION` equals the canonical АР recording in category, page and quotation, and the two figures `test_acceptance.py` states as literals (`EXPECTED_FINDING_COUNT`, `EXPECTED_CSV_ROWS`) equal what it carries; (2) every classification step and the correction name that one section, the dashboard counts it, the expectations file gives it `reviewed`, and the «empty section» step names another; (3) only `ar_bound` steps may name АР (leaf strings, prose excluded), classify as АР or run an АР version; every `startRun` is on a version an earlier step classified (aliases followed through `bind`), and a pass or a specification read is asked of a document classified АР; (4) the README row and the manual protocol name the same section. Each check has a control over mutated copies; the real-file mutations below were applied alone, the tests run, the file restored (restore proved by a byte comparison), baseline `10 passed`.

| Mutation (real file) | Red |
|---|---|
| M1 manifest: `classify-version` clicks АР | 4 failed (classification names, guard, both controls) |
| M2 manifest: `start-specification-run` leaves `ar_bound` | 3 failed |
| M3 manifest: the empty-pass step loses its `bind` | 2 failed (`startOptimisationPass is asked of 'document_uid'`) |
| M5 driver: `JOURNEY_SECTION = "KJ"` | 5 failed (recording, classification, documents) |
| M6 expectations file: ПБ is `draft` | 2 failed |
| M7 README row chooses АР | 2 failed |
| M8 manual protocol A03a confirms АР | 2 failed |
| M9 / M9b `EXPECTED_FINDING_COUNT = 2` / `EXPECTED_CSV_ROWS = 4` | 1 failed each |
| M10 manifest: `ar_bound` removed | 5 failed |
| M11 manifest: `norms-search` gains `tr[data-vendor-section="AR"]` | 2 failed |
| M12 ПБ recording: a quotation moves from page 7 to page 5 | 1 failed |

The existing instrument that mutates the real manifest, `tests/e2e/pc01/journey/prove_the_guard_can_fail.py`: **126 RED, 1 GREEN** on this tree and **126 RED, 1 GREEN on the base** (a detached worktree of `2aec4207`); the one GREEN is the same mutation both times, `expect a word the proposal form no longer prints` (`proposal-revise-needs-a-comment`, text `Revise`, a step this lane did not touch): a vacuous mutation that predates the lane. Not fixed here.

### The two `D-226` pins, run as the real test functions

The tests need a database for `static_token()` and for reading a stored version. Driver-level, the real functions were run against the real application composed on addresses nothing listens on, with only two things stubbed (the bearer token, a bogus one, so requests meet authentication or routing; and `get_version`, a read of a stored version, answering 200): HEAD version `test_c3…` FAIL (the 12th operation `setExecutorRoute`), `test_c10…` FAIL (`1.6.0` against `1.0.0`); working version both PASS. Under a mutated facts source (in memory, no file touched): `contract_version` `1.5.0` → c10 FAIL; `setExecutorRoute` not listed → c3 FAIL; an invented PUT listed → c3 FAIL. The same cases ran for all four failure shapes of c10 (404 no route, 404 wrong method, 401 on the bad body and on the unknown finding because the token is bogus): each envelope carries `contract_version` `1.6.0`. **This is not the pytest run of the file**, which needs the lane stack: `D-226`'s own check (`pytest -q tests/e2e/pc01/test_acceptance.py` prints `0 failed`) is a "verify live" item.

## Commands and counts (this worktree, one pytest at a time, shared venv interpreter, no stack)

| Command | Result |
|---|---|
| `pytest tests/e2e/test_pc01_journey_conformance.py` | base 135 passed; after the manifest rebase 135 passed |
| `pytest tests/e2e/test_pc01_journey_conformance.py tests/e2e/test_pc01_journey_section.py` | 145 passed |
| `node --test write.test.mjs navigation-retry.test.mjs` (in `tests/e2e/pc01/journey`) | 12 passed |
| `node --check journey.mjs`, `write.mjs` | ok |
| `pytest tests/integration/sections/test_section_recordings.py` (container-free; includes the ПБ replay through the real stage) | 109 passed |
| `PYTHONPATH=src python fixtures/recorded/sections/build_fixtures.py --check` | `fixtures match` (no recording touched) |
| `prove_the_guard_can_fail.py` | 126 RED, 1 GREEN (same at base) |
| JSON validity of the manifest and the six fixtures | ok |
| `git diff --check` | exit 0 |
| docs guards `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` | see "Guards" below |

## Verify live (not done: no browser, no stand, no database in this lane)

1. **The journey** on a lane stand in recorded mode, with the lane's administrator: `E2E_PC01_LOGIN=<login> E2E_PC01_PASSWORD=<password> npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:PORT --phase all` (`PROD-18`'s window). Observe: 112 write steps, exit 0. In particular: `start-run`, `-second-`, `-third-` end `published`/`partial` under ПБ with three findings; `compare-versions-read-only` has a «Без изменений» row (the carried decision needs it); `carry-over-decision` offers and carries; `run-exports` downloads; `dashboard-sections-panel` shows ПБ at least 1; `analysis-settings-lists-the-profiles` shows the ПБ row `reviewed`; the three new steps end with the АР run `published` and `optimisation-pass-over-a-set-without-a-table` answering `201` with zero rows; the rest of the АР-bound steps as before. A step that was not reached is a finding.
2. **The Python suite** on the lane stack (`.env` copied): `pytest -q tests/e2e/pc01/test_acceptance.py`, expecting `0 failed` (`D-226`; criteria 4, 5, 7 under ПБ).
3. **A ПБ run through the executor on a database**: add `"PB"` to `RECORDED_SECTIONS` in `tests/integration/runs/test_w59_section_profile_recorded.py` (outside this lane's paths: a one-line change for whoever owns it) and run that file.
4. **A live model under the ПБ profile** (paid, owner): `C2_PC01_LIVE=1 pytest tests/e2e/pc01/test_live_text_analysis.py -s`. The number of seeded issues located is a measurement (the file's assertion is still "at least two").
5. **The redden fixtures**, to re-measure the figures the README documents: the two `--manifest …/redden-write.manifest.json` and `…/redden-write-bound.manifest.json` commands of the README, `--phase write`; the expectation is exit 1 with the same findings as before and the tally one higher.
6. **The manual protocol** A03a to A05 on the public stand.

## Integration notes

- Merge before `PROD-11`. `PROD-11` must: replace or delete the steps of `write.ar_bound` (and the block, and the `registry_pins`), after the owner's decision of what feeds them (a v3 group run needs an installed reviewed pack, `D-204`, and in recorded mode a verifiable cost, `D-225` piece 2 / lane C of `PW3`; or drop them); the guard then forbids any АР pin in the rest of the half.
- Add `tests/e2e/test_pc01_journey_section.py` to `scripts/light_acceptance.py` (it names only the conformance file; outside this lane's paths).
- If `section-form7-without-members` or the dashboard ever need another section, `JOURNEY_SECTION` and the README/protocol sentence move together; the test says which side is missing.
- The register: `D-226` closes on the check in item 2 above; `D-223`'s sentence about `draft` in the manifest is already false; the proof harness' one GREEN mutation is a new low row if the integrator wants it.

## Known limits

1. Nothing in the main flow was run: the manifest agrees with the contract and with `web/src` (conformance) and with the recordings (the new test), not with a browser.
2. The АР-bound steps have no source of a published АР run after `PROD-11`; this lane names them and does not solve it.
3. `needs_published_run` is read from the steps, not measured.
4. The six write fixtures were already stale beyond the classification (English labels in the `w28` ones, figures measured before `W59`); only the classification was added, and the README says their figures are not re-measured.
5. `write.test.mjs` keeps `constants: { section_code: 'AR' }` (a unit test of template constants) and `qa_w50/r66.mjs` keeps `/bff/v1/sections/AR/specification` (the opening section of a screen): neither is a journey assertion.
6. ПБ's recording is authored (`origin.kind: synthetic`): it proves routing and parsing, never a profile's quality.

## Forbidden paths untouched

```text
$ git diff --name-only 2aec4207..HEAD | grep -vE '^(tests/e2e/|docs/manual-tests/|docs/program/(tasks/)?PROD-10B-JOURNEY-REBASE-01\.md$)'
(no output)
$ git diff --name-only 2aec4207..HEAD | grep -E '^(src/|web/|contracts/|db/|infra/|fixtures/|scripts/|tests/support/|Makefile|pyproject|uv\.lock|requirements)|DEBT_REGISTER|CURRENT_STATE'
(no output)
```
