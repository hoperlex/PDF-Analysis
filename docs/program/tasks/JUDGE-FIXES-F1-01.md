# Task JUDGE-FIXES-F1-01 — two findings of an independent judge: one `access.sign_in_blocked` event per cooling-off period under overlap, and a paid answer the model probe cannot assess is counted, not a traceback

task_id: JUDGE-FIXES-F1-01
status: completed in development candidate (see the report)

## Outcome

Finding 5 (access audit, found by reading): `UserRepository._note_a_failed_sign_in` journalled `access.sign_in_blocked` whenever the `UPDATE` returned a non-NULL `sign_in_blocked_until`, on the stated ground that this means "this attempt shut the account, so exactly one per cooling-off period". Under overlap it does not: two attempts that are in flight while the account is open both pass the blocked check; the second `UPDATE` waits for the first's row lock, re-evaluates `failed + 1 >= allowance` on the row the first wrote, extends the block and returns a non-NULL value too. Reproduced on a real database with two connections (two events, `failures` 5 and 6, for one period). The statement now returns, from the same statement, whether the row held no block or a spent one **before** it ran, and the event is written only then, in the transaction of the change. The comments that promised more than the code guaranteed are corrected.

Finding 7 (model-identity probe tool): `call_once` ran `assess()` outside its `try`, and its docstring said nothing there raises. A 200 answer with `usage.cost` of `"1e1000000"` raised `decimal.Overflow` after the paid call; the run aborted with a traceback and that call's cost was never counted or reported. `assess()` is now guarded: on an `Exception` the block is a fresh `no_verdict` whose `verdict_reason` names the exception type, the adapter outcome is kept, and the call is counted at its worst case. A narrower variant (29 digits at the top exponent) that overflowed later, in the running total, is closed at its source.

## Depends on

- `PROD-06-ACCESS-AUDIT-01` — completed (the event, its allow-list, ADR-0023 section 4).
- `PROD-13A-MODEL-IDENTITY-PROBE-TOOL-01` — completed (the tool and its stub transport).

## Frozen inputs

- domain contract: not_applicable
- API contract: unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: the `access.sign_in_blocked` event type, its payload keys and the rule "a failed sign-in is journalled only when it starts a cooling-off period" (ADR-0023 section 4) are unchanged
- migration head: `0033_ar_v3_cite_stage_id`, unchanged
- base commit: `b0644fd3` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: both places are as the judge described them at the base commit; nothing differs. Re-read at `b0644fd3` before any edit.

### P-01 — the statement and the comment that claims one event per period (finding 5)

- captured_at: 2026-10-26
- command: `git show b0644fd3:src/auditmanager/access/repository.py | sed -n 399,413p; git show b0644fd3:src/auditmanager/access/repository.py | sed -n 696,706p`
- captured_output:
  ```text
  _NOTE_A_FAILED_SIGN_IN = text(
      f"""
      UPDATE app_user SET
          failed_sign_ins = {_NEXT_FAILED_SIGN_INS},
          last_failed_sign_in_at = now(),
          sign_in_blocked_until = CASE
              WHEN ({_NEXT_FAILED_SIGN_INS}) >= :allowance
                  THEN now() + (:cooling * interval '1 second')
              WHEN sign_in_blocked_until IS NOT NULL AND sign_in_blocked_until <= now()
                  THEN NULL
              ELSE sign_in_blocked_until
          END
      WHERE login = :login AND {_ACTIVE}
      RETURNING {_PUBLIC_COLUMNS}
      """
          # Non-NULL here means *this attempt shut it*: a live block is refused before this
          # statement runs, and a spent one is set to NULL by it. So there is exactly one of
          # these per cooling-off period, however hard anybody knocks.
          #
          # `PROD-06`: that is also why this is the one failed attempt the journal records. An
          # attacker guessing cannot grow the table: at most one row per account per cooling-off
          # period. Both callers (the sign-in and the password change's proof of the current
          # password, C-10) move this one brake, so both are journalled here and nowhere else.
          record_sign_in_blocked(
              session, subject_uid=str(record.user_uid), failures=record.failed_sign_ins
          )
  ```
- interpretation: the event is written on the one fact "the returned `sign_in_blocked_until` is non-NULL". The `CASE` returns a non-NULL block for every `UPDATE` whose recomputed count reaches the allowance, including one that runs on a row another transaction has just shut, and the "refused before this statement runs" check is a separate earlier statement. The premise is as described; the comment is false under concurrency.

### P-02 — `assess()` outside the `try`, and the docstring (finding 7)

- captured_at: 2026-10-26
- command: `git show b0644fd3:scripts/model_probe/probe.py | sed -n 302,303p; git show b0644fd3:scripts/model_probe/probe.py | sed -n 318,322p; git show b0644fd3:src/auditmanager/executors/identity.py | sed -n 113,120p`
- captured_output:
  ```text
  def call_once(planned: _Planned, run_id: str) -> ModelResult:
      """One call, no retry. Nothing here raises: every failure is a verdict in the result."""
          outcome, dispatch_class = getattr(error.code, "value", str(error.code)), "outcome_unknown"
      except Exception as error:  # noqa: BLE001 - reported by type name only: no message can leak
          outcome, dispatch_class = "unexpected_" + type(error).__name__, "outcome_unknown"
      assess(result, planned, planned.capture.document(), outcome, dispatch_class)
      return result
      if not reported.is_finite() or reported < 0:
          return "not_reported"
      expected = (
          Decimal(tokens_in) * Decimal(str(input_per_mtok_usd))
          + Decimal(tokens_out) * Decimal(str(output_per_mtok_usd))
      ) / Decimal(1_000_000)
      tolerance = max(expected * _TOLERANCE_RATIO, _TOLERANCE_FLOOR_USD)
      return "checked" if abs(reported - expected) <= tolerance else "mismatch"
  ```
- interpretation: `assess` is called after the `try` block, so nothing it raises is caught, and `assess` calls `rate_check`, whose `reported - expected` overflows for `Decimal("1e1000000")`. The tool's vocabulary for "no verdict" already exists (`verdict: no_verdict`, `cost_basis: bound`), so no new vocabulary is invented for the verdict or the cost basis.

### P-03 — the vocabulary of the report block (finding 7)

- captured_at: 2026-10-26
- command: `git show b0644fd3:scripts/model_probe/probe.py | grep -n 'verdict: str\|cost_basis: str\|"no_verdict"\|"bound"'`
- captured_output:
  ```text
  179:    verdict: str = "not_called"  # match | mismatch | no_verdict | not_called
  188:    cost_basis: str = "none"
  295:        result.verdict, result.reason = "no_verdict", "no_answer_body"
  299:        result.counted_cost, result.cost_basis = planned.worst_case, "bound"
  310:        result.counted_cost, result.cost_basis = planned.worst_case, "bound"
  ```
- interpretation: `no_verdict` with `cost_basis: bound` (the call's worst case) is what the tool already says for a call whose answer it could not use. The only new word is a `verdict_reason`, `assessment_failed_<ExceptionType>`, because `no_answer_body` would be false (there was a body) and a bare `no_verdict` would swallow the cause.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/access/repository.py`
- `tests/unit/access/**`
- `tests/integration/access/**`
- `scripts/model_probe/probe.py`
- `tests/unit/scripts/test_model_probe.py`
- `docs/program/tasks/JUDGE-FIXES-F1-01.md`
- `docs/program/JUDGE-FIXES-F1-01.md`

## Lane resources

Private clones of the integrator's lane stack only (`tests/integration/db/conftest.py` creates and drops them); the shared lane database is never reset or dropped.

- foundation_instance: `auditmanager-ar-close` (the integrator's, shared, read-only for this lane)
- postgres_db: `auditmanager_ar_close` (template source only; every test works in its own clone)

## Forbidden hotspots

- `contracts/**`, migrations (the head stays `0033_ar_v3_cite_stage_id`), root dependency/lock files, composition roots, global styles
- `infra/**`, every other `src/**` file (`src/auditmanager/executors/identity.py` is read, not changed)
- `src/auditmanager/access/registrations.py` (it shares `_NEXT_FAILED_SIGN_INS` and is not journalled)
- `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs

## Non-goals

- Widening what is journalled (ADR-0023 section 4: a failed sign-in is journalled only when it starts a cooling-off period).
- Changing the lockout arithmetic, including the extension of the block by an overlapping attempt (see the report, limits).
- Changing `rate_check` or the product adapter, or bounding the printed size of a finite but absurd reported cost (see the report, limits).

## Deliverables

- the guarded statement and the corrected comments in `src/auditmanager/access/repository.py`;
- `tests/integration/access/test_sign_in_blocked_concurrency.py` (new, two-connection interleaving built in the test);
- the guarded `assess` in `scripts/model_probe/probe.py` and its tests in `tests/unit/scripts/test_model_probe.py`;
- `docs/program/JUDGE-FIXES-F1-01.md` (files, mutation table, before/after of tests, commands, limits).

## Required tests

- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/access tests/unit/access tests/unit/scripts/test_model_probe.py`
- expected: all green; the new tests red on the base commit (shown in the report).

## Integration contract

Provider/consumer behaviour the integrator can rely on: `access.sign_in_blocked` has the same type, aggregate, payload keys and trigger as before; it is now written at most once per cooling-off period under any overlap of attempts, and not written by an attempt that found the account already shut. No migration, no port or contract change. `scripts/model_probe/probe.py` writes one more `verdict_reason` value (`assessment_failed_<ExceptionType>`) and otherwise the same report.

## Failure/idempotency/security cases

- the attempt that shut the account rolls back: its block and event go together; the next attempt that finds the account open journals (tested);
- a password-change proof of the current password is the second caller of the same brake (tested as the overlapping attempt);
- a spent (expired, not yet cleared) block that an attempt shuts again is a new period and is journalled (tested with an allowance of one);
- the probe's failed-assessment reason carries the exception type only, never its message; the credential never reaches the report, the console or the log (tested with an exception whose message holds the credential).

## Rollback / feature flag

Not applicable: no behaviour that a flag would gate. Reverting the lane's commits restores the previous statement and tool; no data is changed by either.

## Handoff

- changed files: see the report
- commands/results: see the report
- known limits: see the report
- integration notes: see the report
