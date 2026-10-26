# JUDGE-FIXES-F1-01 — report

Task: `docs/program/tasks/JUDGE-FIXES-F1-01.md`. Branch `agent/judge-fixes-f1-01`, base `b0644fd3` (`integration/ar-close-1026`). Two findings of an independent judge, both reproduced red before the fix and green after.

## Files

| File | Change |
| --- | --- |
| `src/auditmanager/access/repository.py` | `_NOTE_A_FAILED_SIGN_IN` gains a `previous` CTE (`FOR UPDATE`, `MATERIALIZED`) and returns one more column: whether the block was NULL or spent before the statement; `_note_a_failed_sign_in` journals (and logs "now shut") only when that is true and the returned block is set. The comments that claimed "exactly one per cooling-off period, however hard anybody knocks" now say what is guaranteed and why. |
| `tests/integration/access/test_sign_in_blocked_concurrency.py` | new, 6 tests: two connections, the interleaving built in the test (no hook in product code) |
| `scripts/model_probe/probe.py` | `assess()` is guarded in `call_once`; new `_assessment_failed`; `_decimal` rounds to the context |
| `tests/unit/scripts/test_model_probe.py` | 5 new test items (4 functions, one parametrized twice); no existing test touched (0 deleted lines) |
| `docs/program/tasks/JUDGE-FIXES-F1-01.md`, this file | deliverables |

## Finding 5 — `access.sign_in_blocked` under overlapping attempts

**Premise** (re-read at `b0644fd3`, printed in the task file, P-01): as described. The event was written on "the returned `sign_in_blocked_until` is non-NULL"; the "a live block is refused before this statement runs" check is an earlier, separate statement.

**Reproduction** (real PostgreSQL 17, private clone, two connections). Account at `allowance - 1` committed failures. Attempt A runs to its `UPDATE` and stays uncommitted (row lock held, its block invisible to others). Attempt B starts in a thread, passes the blocked check on the committed row, and is observed in `pg_stat_activity` with `wait_event_type = 'Lock'`. Then A commits and B is released. Red on the base, for both a second failed sign-in and a second failed password proof (the other caller of the same brake): `assert 2 == 1`, events with `failures` 5 and 6, and two "now shut until" log lines 130 ms apart.

**Fix.** The statement is `WITH previous AS MATERIALIZED (SELECT user_uid, sign_in_blocked_until ... FOR UPDATE) UPDATE app_user ... FROM previous ... RETURNING <public columns>, (previous.blocked_until IS NULL OR previous.blocked_until <= now())`. Under READ COMMITTED a locker that waited for a concurrent writer is handed the row as that writer committed it, so `previous` is the true "before" even for the loser, and the same statement's `UPDATE` is applied to that latest version (verified by the tests, not assumed). PostgreSQL 17 has no `OLD` in `RETURNING` (18 does); the CTE is the portable spelling. The event is written in the caller's session, so in the transaction of the change. The condition is "NULL or spent" (the task's words), so an allowance of one that shuts the account again over a spent block also journals.

**Guaranteed after the fix:** at most one `access.sign_in_blocked` per cooling-off period under any overlap; an attempt that did not shut the account neither journals nor logs "now shut"; if the attempt that shut it rolls back, its block and event vanish together and the next attempt that finds the account open journals. **Not guaranteed (unchanged):** the overlapping attempt is still counted and still extends the block by the length of the overlap (milliseconds to seconds; one in-flight request per attempt). The event table is what no longer grows. ADR-0023 section 4 is unchanged: still only the attempt that starts a cooling-off period is journalled.

### Tests added (`test_sign_in_blocked_concurrency.py`) and mutation table

Run: `tests/integration/access/test_sign_in_blocked_concurrency.py` plus `tests/integration/access/test_access_audit.py` (33 tests) with each mutation applied to `repository.py` alone, tree restored after each.

| # | Test | Asserts |
| --- | --- | --- |
| T1 (x2) | `test_two_attempts_in_flight_together_journal_one_event` | one event with `failures == allowance`; the second attempt returned `None`; block set |
| T2 (x2) | `test_when_the_attempt_that_shut_the_account_rolls_back_the_next_one_journals` | winner rolled back: one event, `failed_sign_ins == allowance` (the winner left no trace) |
| T3 | `test_a_new_period_after_the_last_one_ended_journals_again` | a second period is a second event |
| T4 | `test_an_attempt_that_finds_a_spent_block_and_shuts_the_account_again_journals` | allowance 1, spent non-NULL block: new period, second event |

| Mutation (on `repository.py`) | Result | Red tests |
| --- | --- | --- |
| M5-1 journal whenever the returned block is set (the base behaviour) | 2 failed, 31 passed | T1 x2 |
| M5-2 condition inverted (journal the attempts that did not find it open) | 10 failed | T1-T4 and 4 existing `test_access_audit` tests |
| M5-3 "open" = `previous IS NULL` only (spent block is not a new period) | 1 failed | T4 |
| M5-4 `FOR UPDATE` removed (previous read from the statement snapshot) | 2 failed | T1 x2 (two events again) |
| M5-5 "open" judged by an in-process set instead of the row | 4 failed | T2 x2, T3, T4 |
| M5-6 previous inverted (journal when the block was live before) | 10 failed | T1-T4 and 4 existing audit tests |
| M5-7 every failed attempt journalled (widens the journal) | 12 failed | T1 (password proof), T2 x2, T3 and 7 existing audit tests (below-allowance writes nothing; refused change; refused operation; scan) |
| M5-8 previous always true | 2 failed | T1 x2 |

Stability: the new file run three times in a row, 6 passed each time (6.5 s).

## Finding 7 — model probe: `assess()` outside the `try`

**Premise** (task file P-02, P-03): as described. `assess` was called after the `try` in `call_once`, whose docstring said nothing there raises; `rate_check` (`src/auditmanager/executors/identity.py:120`) overflows on `Decimal("1e1000000")`. Reproduced through the stub transport: `decimal.Overflow` escapes `main`, before the block is written and before the call is counted. (The product adapter accepted the same answer, `adapter_outcome: answered`, so the failure is in the tool's own assessment.)

**Fix.** A second `try/except Exception` around `assess` in `call_once` (decided by the lane: a sibling `try`, not the same one, because the first `try`'s handlers map adapter errors to an outcome and would have classified an assessment error as an adapter error and run `assess` again). On an `Exception` the result is built fresh by `_assessment_failed`: `verdict: no_verdict`, `verdict_reason: assessment_failed_<ExceptionType>` (type name only, never the message, the tool's own convention for `unexpected_<Type>`), the adapter outcome kept, `counted_cost_usd` = the call's worst case, `cost_basis: bound`. Fresh, because `assess` fills `result` field by field (`reported_model`, `reported_cost`, a verdict of `match`) before `rate_check` raises, and none of that may survive into a `no_verdict` block. An `Interrupt` is not an `Exception` and still stops the run. The existing vocabulary (`no_verdict`, `bound`) is reused; the only new word is the `verdict_reason`. The docstring is corrected.

**A second reproduction found while fixing, same class.** `"9.9999999999999999999999999995e999999"` (29 digits at the largest exponent): `rate_check`'s subtraction rounds it down and succeeds, `outcome.spent += cost` in `run_calls` rounds it up to `1e1000000` and overflowed outside `assess`. `_decimal` now returns `+number` (the context's own rounding), so such a cost fails inside the guarded assessment. For every in-range cost `+number` is the number itself (28 digits is far beyond a cost).

### Tests added (`test_model_probe.py`, 53 -> 58) and mutation table

| # | Test | Asserts |
| --- | --- | --- |
| P1 (x2) | `test_an_answer_the_assessment_cannot_hold_is_a_failed_assessment_not_a_traceback` ("1e1000000", and the 29-digit variant) | exit 1, `no_verdict`, `assessment_failed_Overflow`, adapter outcome kept, nothing half-assessed in the block, counted at the worst case, the run goes on, the summary adds the spend, the cost string is not in the report |
| P2 | `test_the_worst_case_of_a_failed_assessment_counts_against_the_ceiling` | with a ceiling that the worst case plus the next projection passes, the run stops after the failed call (exit 3) |
| P3 | `test_a_failed_assessment_names_the_exception_type_only_and_never_the_credential` | `rate_check` raising `RuntimeError("boom <token>")`: reason is `assessment_failed_RuntimeError`, the token and "boom" appear nowhere in the report, console or error stream, `credential_guard: clean` |
| P4 | `test_an_interrupt_in_the_assessment_is_not_swallowed` | `KeyboardInterrupt` propagates (guards against widening to `BaseException`) |

Red on the base: P1 (both), P2, P3 failed (`decimal.Overflow` at `identity.py:120`; the 29-digit one at `probe.py:365`, `outcome.spent += result.counted_cost`); P4 passes on the base by design (it guards the fix from over-reaching).

| Mutation (on `probe.py`) | Result | Red tests |
| --- | --- | --- |
| M7-1 no `try` around `assess` | 4 failed | P1 x2, P2, P3 |
| M7-2 `except BaseException` | 1 failed | P4 |
| M7-3 failed call counted at zero / `none` | 4 failed | P1 x2, P2, P3 |
| M7-4 half-filled result reused (verdict patched) | 2 failed | P1 x2 |
| M7-5 reason carries the exception message | 3 failed | P1 x2, P3 |
| M7-6 reason reported as `no_answer_body` (silent) | 3 failed | P1 x2, P3 |
| M7-7 verdict stays `match` | 3 failed | P1 x2, P3 |
| M7-8 adapter outcome dropped | 3 failed | P1 x2, P3 |
| M7-9 `_decimal` without the rounding | 1 failed | P1 (29-digit variant) |

Credentials: P3 and the existing `test_the_credential_never_reaches_the_report_or_the_console` / `test_a_gateway_that_echoes_the_credential_is_redacted_and_exits_5` all pass; the failed-assessment path prints a type name only. The lane made no network call, read no credential file and spent nothing.

## Before / after of tests

No existing test was modified or deleted in either file (`git diff b0644fd3..HEAD -- tests/unit/scripts/test_model_probe.py` has 0 removed lines; `test_access_audit.py` untouched). New tests only; nothing weakened.

## Commands and counts (tree `cb6c1adf` plus the two docs files)

`BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages)`; stack runs prefixed `env $(grep -v '^#' .env | grep -v '^$' | xargs)`; every run `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <files>`, one at a time.

| Files | Result |
| --- | --- |
| `tests/unit/scripts/test_model_probe.py` | 58 passed (53 before) |
| `tests/integration/access tests/unit/access` | 367 passed (the new file is 6 of them) |
| `tests/integration/auth/test_sign_in_throttle.py tests/integration/db/test_app_user_repository.py` | 68 passed |
| `tests/integration/api/test_registration_flow.py tests/integration/api/qa_w49/test_qa_w49_status_read.py tests/integration/auth/test_the_exchange_over_real_users.py` | 39 passed |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, governance one-liner, `git diff --check` | see the lane's final message |

Red-on-base runs: concurrency file 2 failed / 4 passed (T1 x2; T2-T4 are guards that pass on the base by design); probe file 3 failed / 54 passed for the first version of P1-P3, and the 29-digit variant of P1 red separately at `probe.py:365`.

## Integration notes

- No migration, no contract, no port, no composition change. The database interface is one statement; its returned row has one more trailing column (nothing else reads `_NOTE_A_FAILED_SIGN_IN`; `registrations.py` imports only `_NEXT_FAILED_SIGN_INS`, unchanged).
- Prose that is now true by construction and that this lane may not edit: ADR-0023 section 4 ("by construction happens at most once per account per 300 seconds"), `access/audit.py:226` ("at most once per period"), `docs/program/PROD-06-ACCESS-AUDIT-01.md`. No sentence there needed a correction; none states the false mechanism the repository comment stated.
- Tests that open two sessions and wait on `pg_stat_activity` need a PostgreSQL where the test role can read its own backends' `wait_event_type` (the default); they time out after 30 s with a message naming the barrier if the second attempt never waits.
- The probe's report gains one `verdict_reason` value, `assessment_failed_<ExceptionType>`. An operator reading `lock_candidate` is unaffected: a `no_verdict` block is never a lock candidate.

## Decisions taken by the lane (decided by the lane)

1. The event condition is "previous NULL or `<= now()`" (the task's words), not "previous NULL", so a spent non-NULL block that is shut again with an allowance of one journals (T4 proves the difference).
2. An attempt that did not shut the account also skips the "now shut" warning log, not only the event: the log line is the operator's mirror of the event.
3. The loser's extension of the block is left alone (see limits).
4. A sibling `try` around `assess`, not the same `try` as the adapter call (reason above).
5. The failed-assessment reason is `assessment_failed_<ExceptionType>`; a fresh result rather than patching the half-filled one.
6. `_decimal` rounds with `+number` to close the 29-digit variant at its source rather than adding a second guard around the running total.
7. Not widened: ADR-0023's journalling rule, `rate_check`, the lock arithmetic.

## Limits

- **Overlap still extends the block.** An attempt that was in flight with the one that shut the account re-evaluates `failed + 1 >= allowance` and moves `sign_in_blocked_until` to its own `now() + 300 s`, and `failed_sign_ins` goes to `allowance + 1`. The statement's comment now says so ("not reached for an account that is blocked *when the caller looked*"); `authenticate`'s comment about attempts that arrive after the block is committed stays true. Closing this would change the lockout arithmetic (a `WHEN previous is live THEN previous` branch and a cap on the count); not done, not asked for. Bounded by the in-flight requests, as the judge noted.
- **A finite but absurd reported cost still prints in full.** `usage.cost` of `"1e999999"` is accepted (it is representable), counted, stops the run with exit 3, and is written as a 1,000,000-digit number three times: a 3 MB report. Not a crash and not silent; bounding the printed figure is a presentation change in `_usd`, left for the integrator to decide.
- The interleaving relies on `pg_stat_activity.wait_event_type`; it is observation of the database, not a sleep, but it needs the tests' PostgreSQL to report lock waits (every supported version does).
- The scratchpad scripts the lane used (`mutate.py`, `muts5.py`, `muts7.py`, `repro7*.py`) live in the session scratchpad; if a file of the same name existed there from another lane it was overwritten.

## Forbidden paths untouched

`git diff --name-only b0644fd3..HEAD` lists exactly six paths, all allowed (`src/auditmanager/access/repository.py`, `tests/integration/access/test_sign_in_blocked_concurrency.py`, `scripts/model_probe/probe.py`, `tests/unit/scripts/test_model_probe.py`, the two docs files); no `contracts/**`, migration, `infra/**`, other `src/**`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, plan, ruling or ADR.
