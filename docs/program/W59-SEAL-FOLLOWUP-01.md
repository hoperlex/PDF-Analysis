# W59-SEAL-FOLLOWUP-01 — the suites the section seal could not reach classify before they run

**Base:** `77aa55bd` (`integration/night-1020`; the task freeze, a docs-only child of the frozen
base `979632af`), branch `agent/w59-seal-followup-01`, isolated worktree `w59-seal-followup`.
Lane: instance `auditmanager-w59-seal-followup`, PostgreSQL 57540, MinIO 61140/61141, database
`auditmanager_w59_seal_followup`, bucket `auditmanager-w59-seal-followup`, migrated to
`0024_version_classification`. **Status:** development candidate under `R-135`. No full gate, no
live journey, no paid provider call. No push, merge or tag.

| commit | what |
|---|---|
| `38244a7e` | `tests/integration/qa_w55b/**`: the three probe flows that run what they upload now classify it first |
| `16c1649b` | `tests/characterization/w13_baseline/**`: case `02b-classifyDocumentVersion.success` and its record; README amendment |
| `a37e5c0a` | records 13, 32, 33 move by the projected classification and nothing else, asserted by digest (separable, see finding F-2) |
| this commit | this report |

## Result

Both suites now start runs the way the product requires since `W59-SECTION-SEAL-01`: the
version is classified as project stage `P`, section `AR`, by an expert account, before
`startRun`. **`tests/integration/qa_w55b` passes completely on the lane: 67 passed.** **The
characterization baseline is unblocked but not green: 60 passed, 5 failed.** All five
failures are one pre-existing drift unrelated to classification (finding F-1). It was hidden
because no run of this corpus had reached a finished run since `W57A-SEAL-01B`. This lane
reports it and does not absorb it.

## Before and after, on the lane's own containers

Command, run from the worktree root (the qa probes need their API ports moved, because 57500
is `auditmanager-w59-version-compare`'s PostgreSQL):

```
PY=/root/projects/PDF-Analysis/.local/worktrees/w55b-main-candidate/.venv/bin/python
$PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/characterization -rA
W55B_QA_API_PORT=57542 W55B_QA_HEALTH_PORT=57543 \
  $PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/qa_w55b -rA
```

| suite | tree | passed | failed | errors | exit |
|---|---|---|---|---|---|
| characterization | `77aa55bd` (before) | 13 | 0 | 50 | 1 |
| characterization | `16c1649b` | 56 | 8 | 0 | 1 |
| characterization | `a37e5c0a` (after) | 60 | 5 | 0 | 1 |
| qa_w55b | `77aa55bd` (before) | 26 | 12 | 29 | 1 |
| qa_w55b | `38244a7e` (after) | 67 | 0 | 0 | 0 |

### Before: characterization (50 errors, one cause)

Every error is the session fixture `exchanges`. It raised `KeyError: 'run_id'` at
`journey.py:1065`, because case 03's `startRun` answered `422 required_norm_unavailable`
(`reference_kind: version_classification`). The 50 tests behind that fixture:
`test_the_response_reproduces_the_record` × 36, `test_the_record_set_and_the_journey_agree`,
`test_the_comparison_reddens_on_a_planted_difference`,
`test_a_content_length_that_does_not_describe_the_body_is_reported`, the four `O1` permutation
tests × 2 records, `test_the_findings_specific_differences_o1_must_still_catch`, and the two
ordering-rule tests. The 13 static tests passed.

### Before: qa_w55b (41 failures and errors, one cause)

All 41 failed `assert 422 == 202`, and each body was `required_norm_unavailable` with
`details: {"reference_kind": "version_classification"}`.

- `test_p2_run_to_portal_blocks.py`: all 12 tests failed (every one runs what it uploads).
- `test_p3_input_budget.py`: 4 errors from the `world` fixture
  (`test_the_stored_count_is_the_unit_the_budget_compares`, the low-ceiling refusal, the
  low-ceiling start and re-audit, and the exact-budget boundary).
  `test_the_application_refuses_to_start_at_a_ceiling_whose_budget_cannot_hold_the_ar_set`
  passed, since it starts no run.
- `test_p4_portal_block_access.py`: 25 errors from the `produced` fixture (11 + 11 standings,
  the two upload-role cases, and the unknown-version case).
- `test_p1_upload_to_version.py` (20) and `test_p5_upload_gate.py` (5) passed, since neither
  starts a run.

### After: characterization at `a37e5c0a` (5 failed)

`test_the_response_reproduces_the_record` for `04-startRun.replay`,
`05-startRun.replay_with_normalised_property`, `06-getRunStatus.success`,
`07-getRunStatus.correlation_supplied` and `34-listRuns.success`. Each one is the same single
value, `text_analysis`'s `"stage_version": "1.0.0"` recorded against `"1.1.0"` served. That
is finding F-1, which is pre-existing and unrelated to classification, so it was left red.
At `16c1649b` the same five plus records 13, 32 and 33 failed (the projected
classification, F-2).

### After: qa_w55b at `38244a7e`

67 passed in 344.8 s. The 500-page probe printed `run failed in 182.0 s ... 'text_analysis':
'failed'`. That probe asserts only that `source_preparation` and `page_geometry_extraction`
succeed, and in `recorded` mode there is no recording for that request. The observation is
noted here and not investigated, because it is outside this task.

## What changed in each suite

**qa_w55b.** `qa_support.classify(uploaded, token)` sends
`PUT /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/classification`
with `{"project_stage": "P", "section_code": "AR"}` (the literal `CLASSIFICATION`). It takes the
`uploadDocument` answer and asserts `200`, the same version, and exactly the stage and section
asked for. It is called by the expert that uploaded the version, immediately after upload, in
`test_p2`'s `_uploaded` (every p2 probe runs what it uploads), in `test_p3`'s `world` (both
versions), and in `test_p4`'s `produced`. p1 and p5 start no run and are unchanged. No fixture
or `conftest.py` changed.

**Characterization.** Case `02b-classifyDocumentVersion.success` runs between case 02 and
case 03. It is the same `PUT` and body, sent with the credential every case presents (the
journey's account has been a complete `expert` since `W49-SEAL-01`). The case is recorded,
and it carries no exception block, under `W18-SEAL`'s rule that adding an operation adds a
case and a record. The supporting changes:

- `SIXTEEN_OPERATIONS` (renamed from `FIFTEEN_OPERATIONS`, with its test) names
  `classifyDocumentVersion`.
- `confirmed_at` is added to `TIMESTAMP_FIELDS` by name.
- The confirmer is tokenised as `{{user_uid}}`. The value comes from
  `journey.presented_account_uid()`, the row the journey provisions, so it is a value the
  journey supplied. It is tokenised only after the response is asserted to name exactly that
  account.

`run_journey`'s docstring now says `startRun` is the fourth request.

## What was re-captured, and why

`capture.py` was **not** run. On this tree it would rewrite every record, which has two
effects. Record 12 would go back to the 19-column CSV, which `W56A` instead projects in
memory against a pinned digest. And every request's `Authorization` would become a freshly
minted credential instead of the literal `Bearer w13-baseline-static-token` that
`test_the_baseline_records_the_authenticated_era` requires. Either would make the
comparison vacuous.

Instead, a scratch script drove the journey once into a scratch directory, wrote each case
with `journey.to_record`, and compared it against the committed record in two ways: with
`journey.differences` (the suite's own comparison, with record 12 going through its
projection) and key by key over the whole file. The 36 existing records:

| result | records |
|---|---|
| response reproduced byte for byte | 28: 01, 02, 03, 05b, 05c, 08–12, 14–31 |
| `DocumentVersion` body gained `classification` | 13, 32, 33 (F-2) |
| `text_analysis` `stage_version` `1.0.0` → `1.1.0` | 04, 05, 06, 07, 34 (F-1) |
| differ outside `response` | every record's request `Authorization` (minted against literal); records 10 and 11's `exception` block, which `W49-SEAL-01` added to the files by hand and `journey.py` does not pass |

What was taken from the scratch capture:

1. **Record 02b (new), in `16c1649b`.** The capture's record, with only its `Authorization`
   header written in the corpus's literal form, as every other record has it.
2. **Records 13, 32 and 33, in `a37e5c0a`.** Each committed file is kept, and only
   `exception`, `response` and `tokens` are replaced. Before writing, the script asserted
   all of the following:
   - status and headers are unchanged;
   - the new body equals the old body plus exactly one fragment, `, "classification":
     {"version_uid": "{{version_uid}}", "project_stage": "P", "section_code": "AR",
     "confirmed_by_user_uid": "{{user_uid}}", "confirmed_at": "{{ts_6}}"}`, appended after
     `display_title`;
   - the old body's SHA-256 is its digest at `77aa55bd`;
   - every existing token and its reason is unchanged, and only `{{ts_6}}` and
     `{{user_uid}}` are added;
   - the request side is unchanged apart from the minted-against-literal credential.

   The three records are entered in `PERMITTED_EXCEPTIONS` under `D-181`, with
   `journey.EXCEPTION_W59SEAL` (ruling `R-139`, decided by `bd08e03c`; the property was
   declared by `a23433ed`). `test_the_three_version_records_moved_by_the_classification_and_nothing_else`
   removes the fragment and requires each body's digest at `77aa55bd`, which is
   `W49-SEAL-01`'s method for records 10 and 11.

Nothing else in `records/` changed.

## Findings

- **F-1 (pre-existing, not absorbed): five records pin `text_analysis` `stage_version`
  `1.0.0`.** `56efead4` (`W57A-SEAL-01B`, 2026-10-16) set `STAGE_VERSION = "1.1.0"` in
  `src/auditmanager/analysis/text/stage.py`, and its report says that the active v1 text
  stage identity became `1.1.0`. Records 04, 05, 06, 07 and 34 render a finished run's
  stages and still pin `1.0.0`. The drift was invisible until now because the seal stopped
  the journey at case 03 before any finished run was read. The classification step neither
  causes nor touches it: `git log -S'STAGE_VERSION = "1.1.0"'` names only `56efead4`, which
  predates `bd08e03c`. The fix belongs to whoever owns the corpus's exceptions. Either move
  the five records under a cited decision (`56efead4`/`W57A-SEAL-01B`) with a digest test,
  as F-2 does, or leave them red with a debt row. This lane did neither.
- **F-2 (a consequence of the classify step, handled in a separate commit): records 13, 32
  and 33 gain the projected classification.** `W59-SECTION-SEAL-01` projects the stored
  classification onto every `DocumentVersion` read. Those three records read the journey's
  version after case 02b, so they cannot stay byte-equal unless they are captured before the
  classification. That would mean reordering the journey so it records the unclassified
  state, which this lane judged to be fitting the corpus around the change. The brief
  allowed re-capturing only the classify exchange itself, so the move is a separate commit
  (`a37e5c0a`) with a digest proof that nothing else moved. **The integrator decides.**
  Merging `16c1649b` without `a37e5c0a` leaves records 13, 32 and 33 red for this named
  reason.
- **F-3 (pre-existing): `capture.py` cannot be run on this tree without vacating the
  corpus**, for the two reasons above (record 12's projected CSV, and minted credentials in
  request headers). It is also out of step with the records in one more way: `journey.py`
  passes no `exception` for cases 10 and 11. Not changed here.

## Mutation probes (each reverted from git, files compared with `cmp` afterwards)

| mutation | result |
|---|---|
| record 13's body changed outside the fragment (`"page_count": 8` → `9`) | `test_the_three_version_records_moved_by_the_classification_and_nothing_else` fails with "moved by more than its appended classification", and record 13's comparison fails: 2 failed |
| the journey classifies section `KJ` instead of `AR` | case 03's existing AR profile pin fails (`AssertionError: ap_01M5AXG1K82P9BCJ1NRYSTC2NY`, the KJ profile), and 37 tests error |
| `presented_account_uid()` returns another user id | case 02b's assertion fails ("names a confirmer other than the account this journey presents") |
| qa flows without the classify call | the "before" run above: 41 failures and errors, all `422 version_classification` |

## Other checks

- `git diff --check`: clean on each commit.
- `tests/contract/api_v1/test_doc_prose_facts.py`, `test_surface_counts_in_prose.py`,
  `tests/contract/program/test_wave_governance.py` (the guards that scan `tests/**/*.py`,
  `docs/**/*.md` and task files): 93 passed, on the tree with the test changes and on the
  tree with this report.

## Deferred (`R-135`)

The complete `make gate`, the live PC-01 journey, and the whole contract battery. `D-181`'s
live-journey half (`classify-version` in `e2e:pc01`) is not touched here.

## Risks and limits

- The characterization suite is still red, on F-1. A complete gate run on this candidate
  goes red there, for a reason that is now named.
- Record 02b pins the classification response shape (`version_uid`, `project_stage`,
  `section_code`, `confirmed_by_user_uid`, `confirmed_at`, in that order). A future
  correction workflow (`D-182`) that changes that body will move this record.
- The classification uses stage `P`, as the brief asked. `tests/integration/composition`
  uses `R`. Neither suite depends on the stage.

## Integrator instructions

1. Merge `38244a7e` (qa_w55b). It is self-contained and green.
2. Merge `16c1649b` (the characterization case). Decide F-2: either take `a37e5c0a` as well,
   which leaves 5 red records, or not, which leaves 8.
3. Register F-1. Either a `D-` row, or a follow-up that moves records 04–07 and 34 under
   `56efead4` with a digest test. Re-measure first: `$PY -m pytest ... tests/characterization`
   on the merged tree should fail only on the records named above.
4. `D-181`: the suite half is done for qa_w55b, and for the characterization baseline apart
   from F-1. The live-journey half remains.

## Hotspot proof

`git diff --name-only 77aa55bd..HEAD` lists only:

- `tests/integration/qa_w55b/qa_support.py`, `test_p2_run_to_portal_blocks.py`,
  `test_p3_input_budget.py`, `test_p4_portal_block_access.py`;
- `tests/characterization/w13_baseline/README.md`, `journey.py`,
  `test_response_baseline.py`, and `records/02b-…`, `13-…`, `32-…`, `33-…`;
- `docs/program/W59-SEAL-FOLLOWUP-01.md`.

All of these are inside the task's allowed paths. Not touched: `src/**`, `contracts/**`,
migrations, `tests/support/**`, any `conftest.py` (including the two in the allowed
directories), `web/**`, dependency files, `CURRENT_STATE.md`, the task file, refs and tags.

## Follow-up: F-1 moved (integrator instruction after the merge)

The integrator merged the branch, including `a37e5c0a`. It then told this lane to move
records 04, 05, 06, 07 and 34 under `56efead4` (`W57A-SEAL-01B`) with a digest test, on the
same branch, allowed paths and lane. The lane was brought up again on fresh volumes and
migrated to `0024`.

**Commit `374985f3`.** Each of the five bodies moves by one value: the `text_analysis`
stage's `"stage_version": "1.0.0"` becomes `"1.1.0"`. That value is served because the
sealed `contracts/analysis/v1/stage-registry.json` and `analysis/text/stage.py`
`STAGE_VERSION` both say `1.1.0`. The records were built from a scratch capture of the
journey. Only `exception` and `response` were replaced, after asserting the following:

- status, headers, body `length`, tokens and the request side are unchanged (apart from the
  minted-against-literal credential);
- the new body equals the old one with exactly that one substring replaced;
- the old body matches its digest at `77aa55bd`.

The exception blocks:

- Records 04–07 carry `EXCEPTION_W57ASEAL_RUN_STATUS`. That is `EXCEPTION_W18SEAL`'s debts
  (`D-19`, `D-21`), its `R-5` ruling and its text unchanged, plus the third move, with
  `decided_by` set to `56efead4`.
- Record 34 carries its first block, `EXCEPTION_W57ASEAL_LIST_RUNS`.
- The debt named is `D-181`, the register row whose resolution ("update those suites") this
  performs. No row names the drift itself, and this lane may not write the register.
  `W57A-SEAL-01B`'s task file cites no owner ruling, and both blocks say so.
- `PERMITTED_EXCEPTIONS` now has 13 entries.

`test_the_five_run_records_moved_by_the_text_stage_version_and_nothing_else` restores
`1.0.0`, requires each body's digest at `77aa55bd`, and requires the other three stages to
still say `1.0.0`.

| check | result |
|---|---|
| scratch capture against the records before the move | 32 of 37 reproduced byte for byte; only 04–07 and 34 differed |
| `tests/characterization` at `374985f3` | **66 passed, 0 failed**, exit 0 |
| probe: another stage (`source_preparation`) also moved in record 06 | digest test fails ("another stage moved"), and so does record 06's comparison |
| probe: a byte outside the stage changed in record 34 (`cost_micros` 34400 → 34401) | digest test fails ("moved by more than the text stage's version"), and so does record 34's comparison |
| probe: record 04 back to `1.0.0` | digest test fails, and so does record 04's comparison |

Each probe was reverted, and the files were compared with `cmp` afterwards.

**What remains.** The characterization baseline and qa_w55b are both green on the lane, so
`D-181`'s suite half is closed. Its live-journey half (`classify-version` in `e2e:pc01`) is
still deferred to the complete gate. If the integrator registers a dedicated debt row for the
stage-version drift, the `D-181` entry for these five records should be replaced with that row
in four places: the two blocks in `journey.py`, the five record files, `PERMITTED_EXCEPTIONS`,
and the digest test's `debt[-1]` assertion. F-3 (`capture.py` cannot be re-run on this tree) is unchanged.
