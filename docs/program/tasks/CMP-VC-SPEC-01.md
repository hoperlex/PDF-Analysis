# Task CMP-VC-SPEC-01 — specifications of a version comparison: deterministic positions by GOST 21.110 (part A) and the AI whole-specification comparison (part B)

## Outcome
Part A (deterministic, no AI job): a specification page is found from the page profile's words and vector lines (the profile keeps the
edges of rectangles and the straight steps of paths since `CMP-C1-FIX-A` item 8); its positions (`Поз.`, `Наименование`, `Тип, марка`,
`Код`, `Завод`, `Ед. изм.`, `Кол.`, `Масса`, `Примечание`) are read, and the positions of one version are assembled across its pages. The
engine's `spec_positions` channel is `checked` with the number of position differences when both pages of a specification pair yield
positions (it is `unchecked` with its reason otherwise), `ALGO_VERSION` is bumped, and two reads answer instead of `503`:
`getVersionPageSpecPositions` and `getComparisonSheetPairSpecPositions`. On the corpus the pair V4 to V5, sheet E07, reports the key's
three position differences (added 7, removed 6, quantity of 3 from 2 to 3).

Part B (after `CMP-AI-JOBS-01`): the whole specification of a version is marked up by a model through «Исполнители» (`comparison_spec_extraction`,
content-keyed, never re-sent), the program checks coverage, quotes and values, and the two versions of a transition are compared
order-independently (`comparison_spec_comparison`, methods «полное сравнение» / «листовой ИИ»); the operations `listComparisonSpecifications`,
`getComparisonSpecification`, `listComparisonSpecificationChanges`, `estimateComparisonSpecification`, `startComparisonSpecification` and
`cancelComparisonSpecification` run through the AI-job core (method `spec`, work kind `comparison_spec`).

## Depends on
- CMP-SEAL-C2, CMP-PROFILE-01, CMP-ENGINE-01, CMP-SERIES-01, CMP-C1-FIX-A (all merged on `integration/compare-modules`), CMP-SPEND-01, CMP-WORK-01
- part B only: CMP-AI-JOBS-01 (the integrator messages its commit and API; until then part A and the deterministic parts of part B)

## Frozen inputs
- domain contract: `contracts/domain/v1/**` at the wave base (prefixes `cse`, `cscp`, `cai`, `ctn`, `cpr`, `csp` are in the catalogue)
- API contract: `contracts/api/v1/openapi.json` `1.11.0`, 176 paths / 198 operations / 517 schemas (this lane changes none)
- analysis/comparison/event contract: ADR-0025 decisions 3, 4, 10, 11, 12, 14, 15, 16, 17 to 23 and both addenda; wave brief
  `docs/program/dispatch/CMP-WAVE-C2.md` section 1; `docs/program/CMP-SEAL-C2.md` sections 3, 4, 8, 9 (row `CMP-VC-SPEC-01`) and 10
- migration head: `0040_comparison_ai_reports` (tables `comparison_spec_extraction` and `comparison_spec_comparison` exist and are empty; the lane writes them)
- base commit: `901914a5520a2d90b22b0c5c3fcdae1fa3f6e438` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `tests/integration/composition/test_router_answers.py` (`SEALED_STUB_GETS`, `SEALED_STUB_QUERY`), `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` (`SEALED_STUB_ADDRESSED`, `SEALED_STUB_COLLECTIONS`, `EXPECTED_ADDRESSED`), `tests/integration/composition/test_comparison_ai_stub_operations.py` (`WIRED`) and `scripts/recovery/grant_classification.py` (`SEALED_NOT_YET_WRITTEN`)
- enumerator_owner: CMP-VC-SPEC-01 for the eight rows of its operations and the two tables `comparison_spec_extraction`, `comparison_spec_comparison` only (wave brief section 1, plan 4.0 rules 1 and 3); merge order AI-JOBS, SPEC, AIPAIR, AISHEET, REPORT, QUEUE
- totality_query: `grep -n "spec-positions\|specification" tests/integration/composition/test_router_answers.py tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` prints no stub row of the eight operations, and `grep -n "comparison_spec" scripts/recovery/grant_classification.py` prints no member of `SEALED_NOT_YET_WRITTEN`

## Captured premise evidence
- premise: contract `1.11.0`, 176 paths / 198 operations / 517 schemas, head `0040_comparison_ai_reports`, base `901914a5`; the eight operations are sealed stubs of `ComparisonSpecificationAdapter(comparison_modules=...)`; the original's `spec.py`, `specification_compare.py`, `specification_run.py`, `specification_structure.py` and the spec phase of `jobs.py` exist at the pinned commit `23f379fd`

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas')"; cat VERSION; grep -n "^revision: str" db/migrations/versions/20261029_0040_comparison_ai_reports.py`
- captured_output:
  ```text
  901914a5520a2d90b22b0c5c3fcdae1fa3f6e438
  contract 1.11.0 176 paths 198 operations 517 schemas
  0.9.0
  69:revision: str = "0040_comparison_ai_reports"
  ```
- interpretation: equal to the premise of the wave brief (`1.11.0`, 176 / 198 / 517, head `0040_comparison_ai_reports`), so the lane did not STOP

### P-02 — the engine reports `spec_positions` unchecked for a changed specification sheet
- captured_at: 2026-10-29
- command: `sed -n 430,438p src/auditmanager/comparison/engine/child/job.py; grep -n 'ALGO_VERSION: Final' src/auditmanager/comparison/engine/child/settings.py; grep -n 'E07", "spec_positions"' tests/unit/comparison/engine/test_against_the_answer_keys.py`
- captured_output:
  ```text
  430:    is_spec = "spec" in (classify_kind(words_a_all, (a.get("stamp") or {}).get("designation"), a["height_pt"]),
  431:                         classify_kind(words_b_all, (b.get("stamp") or {}).get("designation"), b["height_pt"]))
  432:    if is_spec:
  433:        channels["spec_positions"] = (st.checked(0) if main_diffs == 0 else st.unchecked("позиции спецификации не сравнивались"))
  434:    else:
  435:        channels["spec_positions"] = st.not_applicable("не спецификация")
  26:ALGO_VERSION: Final[str] = "cmp-engine/3"
  29:    ("V4->V5", "E07", "spec_positions"),
  ```
- interpretation: the channel is `unchecked` whenever a specification pair has a main-channel difference, and the answer-key test names that as a disagreement it expects to disappear when the channel is built; `ALGO_VERSION` is `cmp-engine/3` and is in the content key of every stored result

### P-03 — the original's specification sources (the local clone does not exist)
- captured_at: 2026-10-29
- command: `ls /root/projects/PDF-proverka 2>&1 | head -1; for f in spec specification_run specification_compare specification_structure specification_view specification_portions specification_prepare jobs; do printf "%s.py " $f; curl -sSf "https://raw.githubusercontent.com/SU10KAZ/PDF-proverka/23f379fd/backend/app/services/version_comparison/$f.py" | wc -l; done`
- captured_output:
  ```text
  ls: cannot access '/root/projects/PDF-proverka': No such file or directory
  spec.py 571
  specification_run.py 688
  specification_compare.py 724
  specification_structure.py 549
  specification_view.py 143
  specification_portions.py 332
  specification_prepare.py 246
  jobs.py 1222
  ```
- interpretation: the files are read as data from the public repository at the pinned commit into a scratch directory outside git; every rule the lane ports cites the file and line of that copy; nothing of it is copied into the repository

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/specification/**`
- `src/auditmanager/comparison/engine/**`
- `src/auditmanager/comparison/public.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/api/routers/ports.py`
- `scripts/recovery/grant_classification.py`
- `tests/unit/comparison/specification/**`
- `tests/integration/comparison/specification/**`
- `tests/unit/comparison/engine/test_against_the_answer_keys.py`
- `tests/unit/comparison/engine/test_handler_unit.py`
- `tests/unit/comparison/engine/test_key_and_outcome.py`
- `tests/unit/comparison/engine/test_spec_positions_channel.py`
- `tests/unit/comparison/work/test_composition_unit.py`
- `tests/integration/composition/test_router_answers.py`
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`
- `tests/integration/composition/test_comparison_ai_stub_operations.py`
- `docs/program/CMP-VC-SPEC-01.md`
- `docs/program/tasks/CMP-VC-SPEC-01.md`

## Lane resources
- foundation_instance: `auditmanager-cmp-vc-spec-01`
- postgres_port: `57950`
- s3_api_port: `61950`
- s3_console_port: `61951`
- postgres_db: `auditmanager_cmp_vc_spec_01`
- s3_bucket: `auditmanager-cmp-vc-spec-01`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json`, `web/**`, `infra/**`, the `Makefile`
- `src/auditmanager/comparison/profile/**`, `src/auditmanager/comparison/matrix/**`, `src/auditmanager/comparison/tiles/**`, `src/auditmanager/comparison/series/**`, `src/auditmanager/comparison/work/**`, `src/auditmanager/comparison/spend/**`, `src/auditmanager/comparison/ai_jobs/**` (read through `comparison/public.py` names only), `src/auditmanager/executors/**`, `src/auditmanager/optimisation/**` (the Form-7 extractor is not used), `src/auditmanager/storage/**`, `src/auditmanager/jobs/**`
- `src/auditmanager/comparison/engine/**` beyond the `spec_positions` channel and `ALGO_VERSION` (and the engine tests the channel change reddens)
- `bootstrap/adapters.py` outside the body of `ComparisonSpecificationAdapter` (and the imports it needs); `bootstrap/composition.py` outside the one constructor line of that adapter
- `HANDLER_FACTORIES` of `comparison/public.py` and its pins only by the lane's own kind (`comparison_spec`)

## Non-goals
- the doubtful-pair check (AIPAIR), the sheet descriptions (AISHEET), the MD summary and PDF report (REPORT), the launch queue (QUEUE), the screens (VC-UI-02)
- the engine's other channels, the status rules, the masks: read, never changed
- a cross-page rewrite of a pair's status from the positions (the original's `_positions_status`, `jobs.py:801-815`): the series lane owns the post-phases and this lane does not touch them
- a contract or migration change: a missing field or table is a STOP to the FIX slot
- a live model call: every test runs in recorded mode

## Deliverables
- `src/auditmanager/comparison/specification/**`: the pure parser of a specification page and the stream across pages, the order-independent comparison, the reader of a version's positions, the two part-A reads; for part B the prompt input and the prompt, the program checks (coverage, quotes, values), the content key, the repositories of the two tables, the comparison of two extractions, the reads, and the work handler
- the engine channel `spec_positions` and `ALGO_VERSION` `cmp-engine/4`
- `ComparisonSpecificationAdapter` (replaces the stub bodies as far as each operation is built), one constructor line, the rows of the composition enumerators and of `SEALED_NOT_YET_WRITTEN`, the appended names and the handler factory of `comparison/public.py`
- unit and integration tests, the corpus proof against the answer keys, the mutation proofs
- the report `docs/program/CMP-VC-SPEC-01.md`

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q --basetemp=/tmp/pytest-cmp-vc-spec-01/unit tests/unit/comparison/specification tests/unit/comparison/engine`
- expected: all pass, no container needed
- command: `set -a; . ./.env; set +a; AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q --basetemp=/tmp/pytest-cmp-vc-spec-01/integ tests/integration/comparison/specification tests/integration/comparison tests/integration/composition`
- expected: all pass on the lane's own stack (`make up`, `make migrate`); `tests/integration/comparison` in one process
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q --basetemp=/tmp/pytest-cmp-vc-spec-01/all tests/unit tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_validate_bootstrap.py --ignore=tests/contract/test_cp00_final_state.py`
- expected: all pass (after the last code commit)

## Integration contract
The integrator can rely on: the pure parser reads only the profile's words, lines and stamp zone and never calls a model or PDFium;
a value of a position is the text of the sheet, joined and never summed, rounded or normalised; a row whose type the parser cannot
decide is flagged `ambiguous` and never guessed; `spec_positions` is `checked` with a count only when both pages of the pair yield
positions (or the pair's main channels have no difference), and `unchecked` with a reason otherwise; the two part-A reads are
deterministic and read-only; in part B a stored extraction is looked up by its content key (project, prompt version, source digest,
model identity) before any request and is never re-requested; a quoted position that the extracted text does not contain is never a
confirmed change; the text of any model answer carries the unconfirmed label; every command is behind the module gate, keyed and an
expert's act.

## Failure/idempotency/security cases
- an unknown page profile, sheet pair, transition, series or job: `404`; a job of another method: `404`
- a page with no specification header, a scan, a page with no text layer: `is_specification: false`, no positions, never a guess
- a column that cannot be found, a table with no row rules: `is_specification: true` with no positions and the reason in the engine channel
- a side that cannot be read completely makes the comparison `incomplete`: no addition, removal or absence of change is published
- the versions module off: every operation answers `503 dependency_unavailable` naming `comparison_modules` before anything is read

## Rollback / feature flag
The operations stay behind the `versions` module flag (`AUDITMANAGER_COMPARISON_MODULES`, default `none`). Rollback is not merging the
lane: the operations then answer the sealed `503`; the engine's new `ALGO_VERSION` makes stored `cmp-engine/3` results be compared again
(the key changes), which is the intended effect.

## Handoff
- changed files: (written with the report as the last commit)
- commands/results: (written with the report)
- known limits: (written with the report)
- integration notes: (written with the report)
