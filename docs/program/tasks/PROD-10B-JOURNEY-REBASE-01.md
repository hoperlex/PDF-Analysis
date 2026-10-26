# Task PROD-10B-JOURNEY-REBASE-01 — the live journey, its fixtures and the manual protocol run on a section that stays

task_id: PROD-10B-JOURNEY-REBASE-01
status: completed in development candidate, **unverified live** (no browser and no stand in this lane; see the report)

## Outcome

The browser journey (`tests/e2e/pc01/journey/`), its Python twin (`tests/e2e/pc01/driver.py`, `test_acceptance.py`, `test_live_text_analysis.py`), the six write fixtures (`redden-write*`, `w28-live/*`) and the manual protocol (`docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`) confirm their baseline set as **ПБ** instead of АР, so that nothing in the main flow starts a run on an АР version, which `PROD-11` makes impossible. What cannot move (the «Оптимизация» tab and the АР Form-7, which exist for АР only and read the saved text of a published АР run) is named in `write.ar_bound` of the manifest and held there by a static test. The two stale pins of `D-226` follow the contract through the suite's own facts source.

## Depends on

- `PROD-10-AR-V2-EXTRACT-01` — completed (its follow-up table is this task's scope), `PROD-11A-V3-TEXT-LAYER-PROBE-01` and `D-222`/`D-225` — completed (what feeds the АР-bound steps after `PROD-11`).
- `SECTION-RECORDINGS-01` — completed (the fourteen section recordings over the baseline text layer).

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.6.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable
- migration head: `0033_ar_v3_cite_stage_id`, unchanged
- base commit: `2aec42072c7ba81be59570206e99e29bfd9e041c` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `tests/e2e/pc01/journey/manifest.json` (the write steps and, under `write.ar_bound`, the steps that may name АР)
- enumerator_owner: this task for the wave; `PROD-11` is the next editor of `write.ar_bound`
- totality_query: `python3 -c "import json;m=json.load(open('tests/e2e/pc01/journey/manifest.json'));print(len(m['write']['steps']), len(m['write']['ar_bound']['steps']), len(m['write']['ar_bound']['needs_published_run']))"` prints `112 33 15`, and `tests/e2e/test_pc01_journey_section.py::test_only_the_named_steps_may_name_ar_or_run_an_ar_version` finds no step outside the list that names АР

## Captured premise evidence

- premise: the dispatch (`PRODUCTION-WAVE-PW3.md`, lane J) and the follow-up table of `PROD-10-AR-V2-EXTRACT-01.md` were written from reading, not from a run. Re-captured at the base commit: the journey and its twin classify as АР; the recordings of the fourteen sections; the АР-only reach of the optimisation code; the stale pins of `D-226`. **Deviation:** the report counts four steps that press «Запустить прогон»; there are five (the fifth, `queue-start-a-run-while-paused`, runs the third version and follows its classification, so it moves with the rest).

### P-01 — what the journey and its twin do at the base commit

- captured_at: 2026-10-26
- command: `git rev-parse, git show | wc -l, a python3 walk of the base manifest, git grep at the base commit (the dollar line of each block in the captured output is the exact command)`
- captured_output:
  ```text
  $ git rev-parse 2aec4207
  2aec42072c7ba81be59570206e99e29bfd9e041c
  $ git show 2aec4207:tests/e2e/pc01/journey/manifest.json | wc -l
  7490
  $ python3 (steps of the base manifest that press «Запустить прогон», and the section chosen/echoed)
  write steps: 109
  run start: 4 start-run
  run start: 11 start-second-run
  run start: 17 start-third-run
  run start: 37 start-specification-run
  run start: 85 queue-start-a-run-while-paused
  $ git grep -nE "data-section-choice|section_code.*AR|equals.: .AR" 2aec4207 -- tests/e2e/pc01/journey/manifest.json
  tests/e2e/pc01/journey/manifest.json:1101:            "selector": "input[data-section-choice=\"AR\"]"
  tests/e2e/pc01/journey/manifest.json:1131:            "equals": "AR"
  tests/e2e/pc01/journey/manifest.json:1488:            "selector": "input[data-section-choice=\"AR\"]"
  tests/e2e/pc01/journey/manifest.json:1520:            "equals": "AR"
  tests/e2e/pc01/journey/manifest.json:1858:            "selector": "input[data-section-choice=\"AR\"]"
  tests/e2e/pc01/journey/manifest.json:1883:            "equals": "AR"
  tests/e2e/pc01/journey/manifest.json:3028:            "selector": "input[data-section-choice=\"AR\"]"
  tests/e2e/pc01/journey/manifest.json:6082:              "\"section_code\":\"AR\"",
  tests/e2e/pc01/journey/manifest.json:6102:            "equals": "AR"
  $ git grep -c "data-section-choice" 2aec4207 -- the six write fixtures
  0 redden-write
  0 redden-write-bound
  0 w28-measure
  0 w28-proxy
  0 w28-recorded
  0 w28-recorded-redden
  $ git grep -n -i "classif\|Подтвердить раздел" 2aec4207 -- docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md | head
  2aec4207:docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md:279:    search narrow the rows and never a project's totals; a version nobody classified is listed
  (the only hit is the section-optimisation item of A09: the protocol at the base never says «Подтвердить раздел»)
  $ git grep -n "\"AR\"\|AR baseline\|1.0.0\|set(mutating)" 2aec4207 -- tests/e2e/pc01/driver.py tests/e2e/pc01/test_acceptance.py | head
  tests/e2e/pc01/driver.py:204:        title: str = "AR baseline",
  tests/e2e/pc01/driver.py:243:        project_stage: str = "R", section_code: str = "AR",
  tests/e2e/pc01/driver.py:248:        a version that has none, so the journey classifies its AR baseline before it runs.
  tests/e2e/pc01/test_acceptance.py:496:    assert set(mutating) == {
  tests/e2e/pc01/test_acceptance.py:568:        journey.version_uid, "AR",
  tests/e2e/pc01/test_acceptance.py:1345:        assert payload["contract_version"] == "1.0.0"
  ```
- interpretation: the manifest has 109 write steps; four classify as АР (`classify-version`, `-second-`, `-third-` and the specification set) and the correction step echoes АР; five press «Запустить прогон». None of the six write fixtures ever classified a version (they predate `W59-SECTION-SEAL-01`, which refuses an unclassified version), and the manual protocol never confirms a section between A03 and A04. `driver.py` and `test_acceptance.py` pin АР and the two stale values of `D-226`.

### P-02 — the recordings of the fourteen sections against the canonical АР recording

- captured_at: 2026-10-26
- command: `a python3 walk over fixtures/recorded/sections/*/*.json and the canonical recording, then grep and sed on the optimisation and dashboard sources, the RECORDED_SECTIONS line and tests/support/expected_facts.json (the dollar line of each block in the captured output is the exact command)`
- captured_output:
  ```text
  $ python3 (shape of every section recording against the canonical AR recording; sorted category + (page, quote))
  AR canonical: findings=3 evidence=5 categories=['explicit_placeholder', 'internal_contradiction', 'internal_contradiction']
  AI   findings=1 evidence=1 identical-to-AR=False
  EOM  findings=1 evidence=2 identical-to-AR=False
  GP   findings=2 evidence=4 identical-to-AR=False
  ITP  findings=1 evidence=2 identical-to-AR=False
  KJ   findings=1 evidence=2 identical-to-AR=False
  KM   findings=1 evidence=2 identical-to-AR=False
  OV   findings=2 evidence=3 identical-to-AR=False
  PB   findings=3 evidence=5 identical-to-AR=True
  POS  findings=1 evidence=2 identical-to-AR=False
  PS   findings=1 evidence=2 identical-to-AR=False
  PT   findings=2 evidence=3 identical-to-AR=False
  SS   findings=1 evidence=1 identical-to-AR=False
  TX   findings=2 evidence=3 identical-to-AR=False
  VK   findings=1 evidence=1 identical-to-AR=False
  $ rg -n "SECTION_AR|section_not_ar" src/auditmanager/optimisation | head
  src/auditmanager/optimisation/proposals/commands.py:48:    SECTION_AR,
  src/auditmanager/optimisation/proposals/commands.py:221:        if entry.section_code == SECTION_AR
  src/auditmanager/optimisation/project_match.py:52:    "SECTION_AR",
  src/auditmanager/optimisation/project_match.py:57:    "STATE_SECTION_NOT_AR",
  src/auditmanager/optimisation/project_match.py:69:SECTION_AR: Final[str] = "AR"
  src/auditmanager/optimisation/project_match.py:75:STATE_SECTION_NOT_AR: Final[str] = "section_not_ar"
  src/auditmanager/optimisation/project_match.py:84:    STATE_SECTION_NOT_AR,
  src/auditmanager/optimisation/project_match.py:281:    if classification.section_code != SECTION_AR:
  $ sed -n 114,131p src/auditmanager/dashboard/repository.py
  #: Published documents by the section their **current version** is confirmed in
  #: (`SECTION-READ-MODEL-01`, `W59-SECTION-IDENTITY-DECISION-01`). ``document.current_version_uid``
  #: selects the version -- the same join ``DocumentRepository._LIST_PROJECTS`` counts through,
  #: so "a document" means one with a published current version here as in every other count
  #: this contract publishes -- and that version's row in ``version_classification_current`` is
  #: its confirmed section: the latest revision, so a section an expert corrected
  #: (`CLASSIFICATION-CORRECTION-01`) counts under the corrected one and never under the original.
  #: The ``LEFT JOIN`` is the unclassified rule: a current version no
  #: expert has classified has no row, so ``section_code`` is NULL and ``GROUP BY`` puts every
  #: such document in one NULL group, which SQL already groups together, rather than this query
  #: having to special-case it. The legacy ``document.section`` is **not read at all**: it is
  #: the old document-level label, not an expert's confirmation, and an older version's
  #: classification never counts for the set whose head moved on.
  _DOCUMENTS_BY_SECTION = text(
      "SELECT c.section_code, count(*) "
      "FROM document d JOIN document_version v ON v.version_uid = d.current_version_uid "
      "LEFT JOIN version_classification_current c ON c.version_uid = v.version_uid "
      "GROUP BY c.section_code"
  $ grep -n RECORDED_SECTIONS tests/integration/runs/test_w59_section_profile_recorded.py | head -2
  56:RECORDED_SECTIONS = ("AI", "PS", "POS", "TX")
  $ python3 (tests/support/expected_facts.json: contract_version and the PUT/PATCH/DELETE operations)
  1.6.0 0033_ar_v3_cite_stage_id
  ['classifyDocumentVersion', 'markReleaseNotesRead', 'purgeUser', 'setCurrentNormSnapshot', 'setExecutionPaused', 'setExecutorRoute', 'setGlobalVendorList', 'setJobPriority', 'setProjectVendorList', 'setWorkerIntake', 'updateMyProfile', 'updateUser']
  $ python3 -c ... json.load(\"tests/e2e/pc01/journey/manifest.json\") steps 33-36 (the base): names
  ['blocks-upload-a-document-no-run-has-read', 'blocks-a-version-no-run-has-read-says-so', 'upload-specification-set', 'classify-specification-set', 'start-specification-run']
  ```
- interpretation: only **ПБ** carries the АР baseline recording's findings (three findings, five pieces of evidence, the same categories, pages and quotations); every other section answers with one or two. The acceptance suite's pins (`EXPECTED_FINDING_COUNT = 3`, `EXPECTED_CSV_ROWS = 5`, the categories, the pages, "at least two seeded issues located") therefore hold for ПБ unchanged and would have to be re-derived for any other. `project_match.py` line 281 refuses a set that is not АР (`section_not_ar`) and `proposals/commands.py` reads АР sets, so the optimisation steps cannot leave АР: a pass over the journey's own set, once ПБ, would be refused. The dashboard counts documents by the section confirmed for the current version. The database-level end-to-end test covers АИ, ПЗ, ПОС and ТХ only (`RECORDED_SECTIONS`); ПБ's recording replays through the real stage container-free (`tests/integration/sections/test_section_recordings.py`) but a ПБ run through the executor has not run on a database: that is a "verify live" item.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `tests/e2e/**`
- `docs/manual-tests/**`
- `docs/program/tasks/PROD-10B-JOURNEY-REBASE-01.md`
- `docs/program/PROD-10B-JOURNEY-REBASE-01.md`

## Forbidden hotspots

- `src/**`, `web/src/**`, `contracts/**`, `db/migrations/**`, `infra/**`
- `fixtures/**` (no fixture is edited: the journey reads `fixtures/synthetic/ar/bundles/ar_baseline.zip`, `fixtures/synthetic/ar_specification/**` and the recordings as they are, and other tests read them too)
- `tests/support/**` (the facts source `FACTS` is read, not edited), `scripts/**`, `Makefile`, root dependency and lock files, the composition root, global styles
- `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs

## Non-goals

- running a browser, a stand, a database or a paid call (this lane has none; what that leaves is listed in the report as "verify live" with its exact command)
- deciding what feeds the АР-bound steps after `PROD-11` (a v3 group run, or dropping them): named and held, not decided
- editing a recording, a profile, a prompt or a fixture; changing `web/src`, the contract or any `src/` file
- changing `scripts/manual-alpha-check.sh` (its three mentions are file names of the bundle, not of a section)

## Deliverables

- `tests/e2e/pc01/journey/manifest.json`, the six write fixtures, `README.md`, the comments of `journey.mjs` and `write.mjs`
- `tests/e2e/pc01/driver.py` (`JOURNEY_SECTION`), `test_acceptance.py` (section and the two `D-226` pins), `test_live_text_analysis.py` (section, marked unmeasured)
- `tests/e2e/test_pc01_journey_section.py` (10 tests, controls included)
- `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` (A03a, A05, A09 item 21)
- this file and `docs/program/PROD-10B-JOURNEY-REBASE-01.md`

## Required tests

- command: `PYTHONPATH=src:<bootstrap site-packages> .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/e2e/test_pc01_journey_conformance.py tests/e2e/test_pc01_journey_section.py tests/integration/sections/test_section_recordings.py`
- expected: `145 passed` for the first two files and `109 passed` for the third (counts in the report), `node --test write.test.mjs navigation-retry.test.mjs` 12 passed, `tests/e2e/pc01/journey/prove_the_guard_can_fail.py` 126 RED and the one GREEN the base tree has too

## Integration contract

- the integrator can rely on: `write.ar_bound` is the complete list of steps that may name АР, classify as АР or run an АР version; `PROD-11` edits that block and nothing else of the main flow; `JOURNEY_SECTION` in `driver.py` is the one place the section is chosen for the Python suite, and the manifest, README and manual protocol are held equal to it by `test_pc01_journey_section.py`
- the integrator must add `tests/e2e/test_pc01_journey_section.py` to `scripts/light_acceptance.py` (it names `test_pc01_journey_conformance.py` only; the file is outside this task's paths)

## Failure/idempotency/security cases

- a classification step that names another section, a run on an АР version outside the block, a specification or a pass asked of a document no earlier step confirmed as АР, an unlisted step that names АР, a recording that no longer equals the АР baseline's, a document that names another section: each is red under a quoted mutation (report)
- no credential, token or password is added to any file; the journey inputs are unchanged

## Rollback / feature flag

Not applicable: test, manifest and documentation files only; `git revert` of the lane's commits restores the АР journey, which is valid until `PROD-11` merges.

## Handoff

- changed files, commands and results, known limits and integration notes: `docs/program/PROD-10B-JOURNEY-REBASE-01.md`
