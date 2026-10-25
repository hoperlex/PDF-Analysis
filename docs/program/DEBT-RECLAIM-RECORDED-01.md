# DEBT-RECLAIM-RECORDED-01 — D-150 and D-152 were already closed in code; now they are pinned

Task: `docs/program/tasks/DEBT-RECLAIM-RECORDED-01.md`. Base `354a9092`. Branch `agent/debt-reclaim-recorded-01`.

## Finding

The lane was dispatched to change `reclaim_expired` for recorded Runs (D-150) and to isolate the serving-lifespan composition test (D-152). Both were implemented by `W54-WORKER-01` (`3ff68419`, 2026-10-12) and only the register rows were never struck:

- `src/auditmanager/jobs/repository.py::reclaim_expired` already settles a lost Attempt's `prepared` effect with `provider_mode = 'recorded'` as `not_processed`/`not_sent` (journal `provider.not_processed`), excludes recorded effects from the ambiguity test, and requeues the Job. A live effect keeps `outcome_unknown`, the Run fails with `provider_outcome_unknown`. The QA test `test_lease_reclaim_journals_the_effect_outcome` was already changed to the recorded outcome in that commit.
- `test_serving_lifespan_dispatches_an_ordinary_run_adapter_submission` already reclaims before the application starts, parks every foreign queued Job again right before unpausing, and gives its own Job priority 100.

So no product code changed (`repository.py` is untouched). What was missing was proof that the mechanisms hold and tests that fail when one is removed. The register's own wording ("QA test pins `outcome_unknown`") describes the tree before `3ff68419`.

The discriminator is the effect row's `provider_mode`, not `audit_run.provider_mode`. They are equal for any effect the executor wrote: `runs/executor.py` refuses an adapter whose mode differs from the Run's, at binding and again at the final check. I kept the existing rule rather than rewrite working code to a different key.

## What was added (tests only)

| File | Addition |
|---|---|
| `tests/integration/jobs/test_d150_and_worker_claims.py` | `test_a_settled_recorded_effect_lets_a_fresh_attempt_retry_the_call`: after reclaim the next Attempt claims, `require_recorded_stage_call_available` accepts, the same request is prepared again; first effect `not_processed`, second `prepared`, first Attempt `lost`. |
| `tests/integration/qa_w53/test_queue_and_effect_journal.py` | `test_lease_reclaim_of_a_live_effect_journals_outcome_unknown` beside the recorded case (state, `dispatch_class`, `provider.outcome_unknown` event, no `provider.not_processed`, Run `failed`); the recorded case also asserts the Job is `queued`; `_queued_run` takes `mode`. The recorded assertion was not weakened. |
| `tests/integration/composition/test_the_run_leaves_the_request_thread.py` | Helpers `_quiet_the_queue`, `_resume_with_this_run_first`, `_restore_the_queue` extracted from the serving test (same statements, same order); tests `test_a_leftover_reclaimed_after_the_parking_still_sorts_behind_this_run`, `test_quieting_the_queue_reclaims_an_expired_leftover_before_it_parks`, `test_a_job_queued_between_the_quieting_and_the_resume_is_parked_and_remembered`. Each cancels the Runs it made and restores availability and the pause flag. |

## Checks (lane stack `auditmanager-debt-reclaim`, PostgreSQL 58620, S3 62120)

| Command | Result |
|---|---|
| `make up && make migrate && make check-services` | `FOUNDATION-CHECK OK check-services`, head `0032_ar_v3_run_group` |
| `pytest -q -p no:cacheprovider tests/integration/jobs tests/integration/qa_w53/test_queue_and_effect_journal.py -x` on the base tree | exit 0, 86 passed |
| `pytest -q -p no:cacheprovider tests/integration/composition/test_the_run_leaves_the_request_thread.py` on the base tree | exit 0, 13 passed |
| same three paths together on the final tree, twice in a row | exit 0 both times, 104 passed each (30 s); after the first of them the lane database held 39 queued and 14 running Jobs left by earlier tests |
| `pytest --collect-only` on the same paths | exit 0, 104 collected |
| governance check of the task file | `[]` |
| `git diff --check 354a9092` | exit 0 |

## Mutations (each guard shown red, then reverted)

Product code, `src/auditmanager/jobs/repository.py`:

| Mutation | Red |
|---|---|
| M1: the recorded settle writes `state = 'outcome_unknown'`, `dispatch_class = 'outcome_unknown'` | 3 failed: the recorded D-150 test, the new retry test, the QA recorded test |
| M2: drop `AND provider_mode <> 'recorded'` from the ambiguity test and make the settle match `provider_mode = 'never'` (the pre-W54 rule) | 4 failed: the recorded state test (`('failed', 'failed') == ('running', 'queued')`), the retry test, the completed-effect test, the QA recorded test |
| M3: drop `AND provider_mode = 'recorded'` from the settle (every mode settles `not_processed`) | 2 failed: the jobs live test and the new QA live twin |

Test helpers, `test_the_run_leaves_the_request_thread.py` (the D-152 fix itself):

| Mutation | Red |
|---|---|
| MA: `priority = 100` becomes `priority = 0`, which is the pre-fix helper | `test_a_leftover_reclaimed_after_the_parking_still_sorts_behind_this_run` (`next_queued_run` returns the older foreign Run) |
| MB: delete the reclaim before the parking in `_quiet_the_queue` | `test_quieting_the_queue_reclaims_an_expired_leftover_before_it_parks` (the lost Job is still `running`) |
| MC: the second parking becomes `available_at = available_at` | `test_a_job_queued_between_the_quieting_and_the_resume_is_parked_and_remembered` (a priority-100 arrival is picked first) |
| MD: stop remembering the second-parked rows (`parked +=` removed) | the same test (the arrival is not in `parked`) |

An intermediate run of MC before the arrival test existed stayed green on three tests, and a `git checkout` of the test file in the same loop discarded the uncommitted test; it was rewritten and committed before the mutations above were repeated on the committed tree.

The real D-152 race (the carrier's first reclaim pass against the test's parking) is timing-dependent, so it was not reproduced as a red run. MA and MB are the two pre-fix omissions; each is made deterministic by the new tests.

## Not run

- The register's own check for D-152, `pytest tests/integration/runs tests/integration/composition` twice on one lane database, is outside this lane's bounded scope (R-135). The bounded set passed twice in a row on a database that held leftover Jobs.
- `ruff` is not installed in the shared virtualenv, so no lint ran on the edited tests.

## Integration

Merge after the base; the three test files do not overlap other lanes. On a DB lane, re-run the three paths above on the merged candidate. Nothing else depends on this change.

## Proposed register text (the orchestrator is the only writer of `DEBT_REGISTER.md`)

Table row for D-150:

```text
| ~~D-150~~ | a recorded run's prepared effect still reclaims as `outcome_unknown` | **closed in code 2026-10-12** by `W54-WORKER-01` (`3ff68419`, decided at `W54-FREEZE-01`), found stale and re-proved 2026-10-26 by `DEBT-RECLAIM-RECORDED-01`: reclaim settles a recorded `prepared` effect `not_processed`/`not_sent` and requeues the Job, a live one stays `outcome_unknown`; check `rg -n settled_recorded src/auditmanager/jobs/repository.py` and `pytest -q tests/integration/jobs/test_d150_and_worker_claims.py tests/integration/qa_w53/test_queue_and_effect_journal.py` |
```

Table row for D-152:

```text
| ~~D-152~~ | one composition test is order-sensitive to leftover queued Jobs | **closed in the test 2026-10-12** by `W54-WORKER-01` (reclaim before the application starts, a second parking right before unpausing, own Job at priority 100), pinned 2026-10-26 by `DEBT-RECLAIM-RECORDED-01` with three deterministic leftover tests; check `pytest -q tests/integration/composition/test_the_run_leaves_the_request_thread.py -k "leftover or quieting or between or serving_lifespan"` |
```

Replacement body for `### D-150` and `### D-152` (strike the titles the same way as `D-146`):

```text
### ~~D-150~~ — closed

`W54-FREEZE-01` decided that a recorded call spends nothing; `W54-WORKER-01` (`3ff68419`) made lease reclaim settle a recorded `prepared` effect `not_processed`/`not_sent`, keep recorded effects out of the ambiguity test and requeue the Job. A live effect still becomes `outcome_unknown` and fails the Run. The independent QA test asserts the recorded outcome. `DEBT-RECLAIM-RECORDED-01` added the retry proof and the live twin.

### ~~D-152~~ — closed

The serving-lifespan test reclaims before the application starts, parks every foreign queued Job again right before unpausing and puts its own Job first. `DEBT-RECLAIM-RECORDED-01` extracted those steps and pinned each with a deterministic leftover scenario.
```
