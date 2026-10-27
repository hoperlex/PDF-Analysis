# SMALL-HARDENING-02 — report

Lane S1 of wave PW5, parts (a) and (b) of `PRODUCTION-WAVE-PW5.md` section 4. Task file: `docs/program/tasks/SMALL-HARDENING-02.md` (the premise blocks, with real output, are there). Branch `agent/small-hardening-02`, base `9e42c18a`.

## What changed

### (a) The run CSV (`R-146ax`, `F-11`)

`src/auditmanager/exports/serializer.py`: a text cell whose first character is `=`, `+`, `-`, `@`, tab or carriage return gets one leading `'` (`FORMULA_TRIGGERS`, `FORMULA_NEUTRALISER`, `neutralise_formula`, applied to every non-integer, non-date cell in `_cell`). Every other byte is unchanged; the `OD-11` format (BOM, CRLF, comma, minimal quoting, empty cell for null, `Z` dates) is untouched.

Decisions, recorded here and in the module docstring:

| Question | Decision | Why |
| --- | --- | --- |
| Which text columns | all of them (17 of 19), not a list of the four free-text ones | a list kept by hand loses the next column added; the rule is per cell |
| Negative numbers | an integer is written as digits and never altered; a negative number inside a text column (`-5` as a quotation) is text and is neutralised | the CSV has one integer column, `evidence_page`, `CHECK (page_number >= 1)` (P-04), so no numeric column legitimately starts with `-` and nothing readable is lost; XLSX likewise refuses a negative count |
| Leading space (` =1+1`) | not a trigger | the ruling names the first character; the optimisation CSV is stricter and looks past spaces, this file keeps the bytes of every cell the ruling does not name |
| Line feed first | not a trigger | not one of the ruling's six (the optimisation CSV adds it) |
| Cell already starting with `'` | unchanged (never doubled) | `'` is not a trigger |
| Equivalence with XLSX | same intent, different road | XLSX stores every string as `inlineStr`, which is text whatever its first character (`writer.py:136-141`) |

**Frozen references touched: none.** The byte-for-byte record `tests/characterization/w13_baseline/records/12-exportRunCsv.success.json` (5 rows, 17 columns decoded) holds no cell starting with any of the six characters (P-05), so it is not edited; `test_csv_contract.py`, `test_v2_csv_severity.py`, `test_frozen_column_list.py` assert on the recorded run's real cells, none of which starts with a trigger (asserted by the new end-to-end test), and are unedited and green. The brief's expectation that some reference cells would change did not materialise: no reference cell starts with a trigger.

### (b) Open registration (`R-146ay`, `F-19`)

`src/auditmanager/access/registrations.py` only (no other file of `access/`): `MAX_REQUESTS_PER_DAY = 40`, `REQUEST_WINDOW_HOURS = 24`; `submit` counts the rows with `submitted_at > now() - 24 hours`, in any state, after the three existing checks and under the same queue lock, and refuses at 40 with the existing `conflict` / `conflict_reason = queue_full`. No migration, no new code, no new field, no contract change. The answer does not depend on the login, so it adds nothing to the disclosure of `E-9`.

1. **The day cap: 40.** Chosen against the two things it must separate. Below the pending cap of 100: a flood that nobody stops needs at least 100 / 40 = 2.5 days to fill the queue, where P-07 shows it takes minutes (45 requests in 5.6 s at the base; a quarter of an hour at the edge's 6 r/m). Above any legitimate day: the users are the organisation's employees (`R-146al`); 40 accounts opened in one rolling day is an onboarding event, not a normal day. Counting every state, not only pending, is deliberate: otherwise a flood-and-reject cycle refills the day for free. The cost is stated: while 40 requests stand in the window nobody can apply, and rejecting them does not free the day (it frees the queue).
2. **The short life of a pending request: NOT built, as the brief instructs.** The states are `pending`, `approved`, `rejected`, closed by a CHECK, by the contract's machine and by the guard trigger, and a decided row must name `decided_by`, a foreign key to a person (P-08). No existing state carries "expired" or "withdrawn", and rejecting a stale request from the anonymous submit path would need a decider that is not a person. Options for the owner, none of them in this lane's paths: (i) computed ageing only, state-free: a pending request older than N days stops counting towards the 100-cap but stays `pending` and decidable (about five lines in this file; with N = 7 a queue left by a flood frees itself a week after the flood ends, but it does not help while a flood continues at 40 a day, since 40 x 7 = 280 > 100); (ii) a new state `expired` (migration + contract + web); (iii) a system decider (migration). I recommend (i) if the owner wants the short life at all.
3. **The nginx zone: nothing to change.** `POST /api/v1/registrations` and `POST /api/v1/registrations/status` are keyed into one zone, `guest_registration`, 6 r/m per address, burst 10, `nodelay`, in both server bodies, and `tests/contract/test_proxy_rate_limits.py` binds both operations to it (P-10). The registration call is exactly as tight as the status call and no test pins a tighter intent, so `infra/deploy/proxy/*.conf` and its test are untouched. Note for the integrator: the browser's registration goes through `/bff/v1` to the API on the compose network and never meets this zone (nginx.conf 107-108); the day cap is what protects that path. A `limit_req` on `/bff/v1/registration` is `F-18` / `PROD-05`, another lane's.

## Mutation tables

(a) Run with `tests/unit/exports/test_csv_formula_neutralisation.py` (60) and `tests/integration/exports/test_csv_formula_neutralisation_over_a_run.py` (1): green is `61 passed`. Each mutation edits `serializer.py` only and is reverted.

| Mutation | Result |
| --- | --- |
| M-a1 `=` un-neutralised | 23 failed, 38 passed |
| M-a2 `+` un-neutralised | 6 failed, 55 passed |
| M-a3 `-` un-neutralised | 7 failed, 54 passed |
| M-a4 `@` un-neutralised | 6 failed, 55 passed |
| M-a5 tab un-neutralised | 6 failed, 55 passed |
| M-a6 carriage return un-neutralised | 6 failed, 55 passed |
| M-a7 text cells bypass the rule | 45 failed, 16 passed |
| M-a8 integers neutralised too (`-5` page becomes `'-5`) | 1 failed |
| M-a9 empty cell becomes a lone `'` | 1 failed |
| M-a10 looks past leading spaces | 1 failed |
| M-a11 line feed added to the triggers | 1 failed |
| M-a12 the prefix is a space, not `'` | 45 failed, 16 passed |
| M-a13 the prefix goes after the first character | 45 failed, 16 passed |

Also: the new unit file run against the base serializer: 44 failed, 16 passed (the 16 are the "bytes unchanged" tests, including the golden bytes of a row with no trigger, which therefore pin the old bytes too).

(b) Run with `tests/integration/access/test_registration_day_cap.py` (7), `tests/integration/api/qa_w49/test_qa_w49_queue_cap.py` (4) and `test_the_queue_holds_100_and_refuses_the_101st` (1): green is `12 passed`.

| Mutation | Result |
| --- | --- |
| M-b1 day cap removed (flooding allowed) | 6 failed, 6 passed |
| M-b2 off by one (`>` for `>=`) | 6 failed, 6 passed |
| M-b3 only pending requests count | 1 failed (`test_decided_requests_still_count_towards_the_day`) |
| M-b4 window 23 hours | 2 failed (numbers test, `just-inside-the-window`) |
| M-b5 window 25 hours | 2 failed (numbers test, `just-outside-the-window`) |
| M-b6 no window (all time) | 5 failed (the two outside-the-window cases and the queue-of-100 tests, which count old rows as today's) |
| M-b7 cap raised to 100 | 5 failed |
| M-b8 other conflict reason | 6 failed |
| M-b9 queue lock not taken in `submit` | 2 failed (both races: the pending cap's and the day's) |

## Modified tests: before and after

None weakened; no assertion edited. Both edits change only the **age of the filler rows**, because with a day cap of 40 a queue filled in one instant is refused by the day cap before the pending cap those tests exercise.

| Test | Before | After |
| --- | --- | --- |
| `tests/integration/access/test_registrations.py::TestSubmit::test_the_queue_holds_100_and_refuses_the_101st` | 99 filler rows inserted with the default `submitted_at = now()`; the 100th through `submit` is accepted; the 101st is `queue_full`. With the day cap and the old fillers: red (run before the edit). | same 99 rows inserted with `submitted_at = now() - interval '3 days'`; every assertion is the old one; green |
| `tests/integration/api/qa_w49/test_qa_w49_queue_cap.py::test_the_hundredth_is_accepted_the_hundred_and_first_is_queue_full` | `_fill(engine, 98)` wrote rows at `now()`; the 99th and 100th over HTTP are 201, the 101st is 409 `queue_full`, a rejection and an approval each free one place. With the day cap and the old fillers: red | `_fill` takes `age` (default `3 days`) and writes `now() - age`; assertions identical; green |
| `...::test_two_applications_racing_for_the_last_place_get_one` | `_fill(engine, 99)` at `now()`; one 201 and one 409 `queue_full`, 100 pending. With the day cap and the old fillers: red | same call, rows three days old; assertions identical; green |

Added: `tests/unit/exports/test_csv_formula_neutralisation.py` (60), `tests/integration/exports/test_csv_formula_neutralisation_over_a_run.py` (1), `tests/integration/access/test_registration_day_cap.py` (7), and in `test_qa_w49_queue_cap.py` `test_the_forty_first_application_of_a_day_is_queue_full_over_http` and `test_two_applications_racing_for_the_last_place_of_the_day_get_one` (the race forced exactly as the existing one).

## Commands and counts

Private database `auditmanager_sh02` created on the lane stack's PostgreSQL, migrated to head (`0035_comparison_records`) and dropped at the end; the stack's main database was not written. `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <paths>` with the stack's `.env` variables and `DATABASE_URL`/`POSTGRES_DB` pointed at the private database. One pytest at a time.

| Paths | Base | After |
| --- | --- | --- |
| `tests/unit/exports tests/integration/exports` | 225 passed, 2 skipped | 286 passed, 2 skipped |
| `tests/unit/access tests/integration/access` | 396 passed | 403 passed |
| `tests/integration/api` | not run at the base | 668 passed |
| `tests/contract` without `test_cp00_candidate.py`, `test_validate_bootstrap.py`, `test_cp00_final_state.py` | not run at the base | 1175 passed, 19283 subtests passed |

The governance one-liner for the task file printed `[]`. `git diff --check` clean.

## Integration notes

- Contract prose, for the contract slot: `contracts/api/v1/openapi.json` (`submitRegistration`: «100 pending requests in all `queue_full`») and `contracts/domain/v1/state-machines.json` («at most 100 pending requests in all») now omit the day cap; `exportRunCsv` says nothing of the apostrophe. No shape changed, so no reseal is forced; amend the prose at the next contract slot. `docs/program/P02_SEAMS.md` section 6 likewise.
- `queue_full` is rendered by the browser as «Очередь заявок заполнена. Попробуйте позже.» (`web/src/features/register/model/exchange.ts:26`); that stays true for a spent day. Reword it only if the owner wants the two told apart (web is outside this lane).
- Release note / `CURRENT_STATE.md` / `DEBT_REGISTER.md` rows for `F-11` (`D-241`: `rg -n "escape_formula" src/auditmanager/exports/serializer.py` has no hit; the check now is `rg -n "neutralise_formula" src/auditmanager/exports/serializer.py`) and `F-19` are the integrator's.
- Both parts are single-commit reverts: `79f42492` (a), `42ea4768` (b).

## Limits

- The short life of a pending request is not built (above); `F-19`'s "an administrator must clear it" is therefore still true once the queue is at 100, but the queue now takes at least 2.5 days of undisturbed flooding to fill.
- The day cap is global, not per address: the application never sees the address. A flood of 40 a day keeps registration closed to everyone for as long as it lasts; the administrator can still approve what is pending. This is the trade of `R-146ay` made visible, not removed.
- `E-9` (disclosure of existing logins), `F-09` (the account brake) and `F-18` (the BFF doors at the edge) are untouched.
- `tests/characterization/w13_baseline` needs its database journey and was not run; the static decode of its CSV record (P-05) is the evidence that it is unaffected.
- A leading-space trigger (` =1+1`) and a leading line feed are not neutralised, by the ruling's wording; the optimisation CSV is stricter on both.

## Proof that nothing forbidden was touched

`git diff --name-only 9e42c18a..HEAD` lists only: `src/auditmanager/access/registrations.py`, `src/auditmanager/exports/serializer.py`, `tests/integration/access/test_registration_day_cap.py`, `tests/integration/access/test_registrations.py`, `tests/integration/api/qa_w49/test_qa_w49_queue_cap.py`, `tests/integration/exports/test_csv_formula_neutralisation_over_a_run.py`, `tests/unit/exports/test_csv_formula_neutralisation.py`, `docs/program/tasks/SMALL-HARDENING-02.md`, `docs/program/SMALL-HARDENING-02.md`. No `contracts/**`, `db/migrations/**`, `src/auditmanager/bootstrap/**`, `web/**`, `infra/**`, section, АР or comparison file.
