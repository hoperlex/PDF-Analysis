# BETA-LIVE-JOURNEY-01 — the PC-01 browser journey over the night window's screens

**Base:** `origin/dev` `06591a52`, then a real merge of `508d7ba1` (the integrator's addendum: docs only).
**Branch:** `agent/beta-live-journey-01`, worktree `.local/worktrees/beta-live-journey`.
**Tested tree:** `f44bd935` (every figure below); the commit after it is this report, docs only.
**Task:** `docs/program/tasks/BETA-LIVE-JOURNEY-01.md`; the integrator's addendum orders items (1)–(6) of
`docs/program/BETA-MATRIX-01.md` §B12, `D-180` and `tests/e2e/pc01/qa_w50/r66.mjs`.
**Status:** the journey walks every screen the night window added and the destinations the matrix listed,
each with a case it must refuse, and runs green on this lane's own stack. Recorded provider only; no spend.

## The green run

```
E2E_PC01_LOGIN=<administrator> E2E_PC01_PASSWORD=<password> E2E_PC01_CHROME=<chrome-for-testing 154> \
  npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:61322 --phase all \
  --out /root/projects/PDF-Analysis/.local/worktrees/beta-live-journey/.local/evidence/final-2
```

Measured 2026-10-21 12:27–12:32 +05 on `f44bd935`: **exit `0`**, `write steps checked: 86/86`, `routes checked: 29/29`,
`e2e:pc01 OK`, 115 `ok` lines, **5 min 05 s** (`real 5m4.8s`). `--phase core` on the same tree: exit `0`, 4 write steps and 29 routes, 59 s.
The run is repeatable: before this one the whole write half passed on four earlier trees with only the findings listed below.

Stack (staggered per the common brief; `free -m` available ≥ 6 GB, load < 3 at every start): PostgreSQL 57700 and
MinIO 61300/61301 from `make up`; the API from `infra/deploy/serve.py` on 61320 with `EXECUTION_ROLE=api`, a worker
(`python -m auditmanager.workers serve`), and `next start` on 61322, all host processes started by PID and stopped
by PID; `AUDITMANAGER_PROVIDER_MODE=recorded`. The administrator's seeded password was changed (R-50) and its profile
completed before the first run.

The envelope is ``/root/projects/PDF-Analysis/.local/worktrees/beta-live-journey/.local/evidence/final-2/journey.json` (94 MB, 3 727 exchanges)` (the lane's untracked `.local`): the sign-in, the accounts the journey made,
86 write steps with every exchange, request body (passwords scrubbed) and response body, the saved export files'
facts, and the 29 routes.

## What was walked, and what each screen refused

Every step carries `screen` and `case` (`action` or `refused`); `test_the_night_window_steps_agree_with_the_contract_and_with_each_other`
requires, for each of the 25 screens, an action and a refusal (or a written reason there can be none).

| screen | action | refused |
|---|---|---|
| stage and section | confirm АР/П (button pressed twice: one `PUT`); third version as Р | admin-only sees the read-only sentence, no form; stage without section is a disabled button |
| next version | upload a bundle as version 2 and 3, and a specification set | a bare PDF is refused by the browser, nothing sent |
| comparison, П→Р, carried decision | compare 1↔2; carry the verdict; compare П↔Р | admin-only gets the read-only sentence; П against Р refused without the switch; the carried row offers nothing again |
| «Настройки анализа» | fifteen sections and their profiles | no form, field or select; an expert reads the same |
| «Диспетчер», «Мои задачи» | assign, take, complete; the admin reads the finished work and its history | admin-only cannot take the work; an expert has no creation form; a return needs a reason |
| price lists | CSV upload (twice), parse report with its skipped row | admin-only has no upload; an empty file; a table with no columns → 422 |
| vendor lists | global (administrator), project (expert) | an expert has no global button; a row with no vendor |
| «Спецификация и цены» | three Form-7 rows read, matched, counted in RUB | `price_list_missing` before any list |
| «Предложения» | a pass → one proposal; accept; revise with a comment; history; CSV | admin-only starts nothing and decides nothing; «На доработку» needs a comment |
| «Оптимизация разделов» | the АР section across projects, our project a member | a section with no members |
| dashboard section panel | АР counts the confirmed set | read-only (reason written in the manifest) |
| «Нормы» | designate a snapshot, search, catalogue + filter | an unqualified snapshot has no button; an expert has no designation; an empty query |
| run exports | CSV (BOM) and Excel (`PK`, `xl/workbook.xml`), read from the saved file | admin-only → `403 permission_denied` |
| «Очередь» | pause dispatch, a run waits, priority, cancel (expert), re-audit (expert), resume | an expert has no priority or pause; priority 500 is out of range, nothing sent |
| «Исполнители» | intake off and on | an expert has no switch |
| profile, password, sign-out, history | save the patronymic; change the password; «Выйти»; «История версий» | a surname is required; mismatch and wrong current password; the old pass is refused after a change; the signed-out cookie opens nothing |
| «Пользователи» | archive, restore, reset password | the temporary password and its repeat must match |

Proposals are real: the specification set's text carries a table, the price list holds a cheaper analog (МЩ-2,
12 000 against 15 000, ×2 = 6 000 saving) from a vendor whose name begins with `=`, and the proposals CSV contains
that vendor with an apostrophe in front (`csv_no_formula_cells` over every cell, plus `body_contains "'=HYPERLINK"`).

## Defects

### Found in the application, fixed here (each with a vitest case that fails without the repair)

1. **A double press on «Подтвердить перенос» sent two `POST`s and the screen said the decision had been carried
   earlier.** The second answered `replayed: true` and the screen shows the latest answer. `useCarryOverDecision` now
   joins a request already in flight for the same intent. Test: `web/tests/unit/comparison/carry-over-command.test.ts`
   «sends ONE request…» — under revert: *expected "spy" to be called 1 times, but got 2 times*.
2. **A double press on «Загрузить прайс-лист» sent two `POST`s under one key; the second met the first still executing
   (`409 idempotency_key_in_progress`) and the form showed «Прайс-лист не загружен» over a stored revision.**
   `useUploadPriceList` joins the request in flight for the same key. Test: `web/tests/unit/optimisation/commands.test.ts`
   — under revert: *called 1 times, but got 2 times*.
3. **After a carry the comparison is read again and no longer lists the row as a candidate, so the confirmation vanished
   and a «—» stood where the button had been.** The widget keeps the answer by the finding that received the decision
   (`ComparisonResult` with `carried`) and shows it in the row's place. Test: `web/tests/unit/comparison/decision-carryover.test.ts`
   «a carried decision stays on the screen…» — under revert: *expected '<div data-comparison-outcome="compare…' to contain
   'data-carryover-state="carried"'*.

### Found in the instrument, fixed here

* **The read walk had not completed since the night window.** `section-optimisation` declares a call whose path needs
  `{section_code}` and nothing supplied it, so `journey.mjs` threw `route needs {section_code}` and **12 routes after it were
  never walked**; `comparison` (`getMe`), `sign-in` (`listAssignments`) and `optimisation` (now a pointer that replaces itself with
  `/projects`) made calls the manifest did not declare. Routes may now declare `constants` (a member of an enumeration the contract
  publishes, never an identity); the three were re-declared.
* **Every cold browser took 25 s.** On Chrome 154 the first cookie-store access of a fresh profile waited for a desktop keyring that
  is not there; `--password-store=basic` makes a launch 0.3 s and the whole walk four minutes instead of about forty.
* **`prove_the_guard_can_fail.py` addressed steps by position** (`steps[2]` was `start-run` before W59 put `classify-version` ahead of it):
  ten of its original mutations mutated the wrong step. Now by name.
* **`tests/e2e/pc01/qa_w50/r66.mjs` was stale** (BETA-MATRIX-01 §B12, `D-186`): run on this stack it failed 19 checks — «Диспетчер» in «Работа»,
  the administrator's «Администрирование», `R-80`'s role-less account that sees «Главная» alone, `/optimisation` as a pointer, and
  four screens that are no stubs. It is retyped from `screen-registry.ts` and prints `R-66 OK`; two quoted mutations show it can fail.
* **`D-180`** (the dashboard section panel groups by the legacy field): the walk's `dashboard-sections-panel` step reads
  `li[data-section="AR"] strong` and requires a positive count for a set that exists only as a confirmed classification.
  It passes on this tree (`fee74158`, `SECTION-READ-MODEL-01`): the debt row looks stale.

### Recorded, not repaired

* **Benign duplicate requests.** The same double press sends two identical requests in `assign-work` (2×`200`, one assignment),
  `my-tasks-complete-the-work` (2×`200`), `optimisation-pass` (2×`201`, one pass), `proposal-accept` (2×`201`, one decision id) and
  `norms-designate-the-current-snapshot` (2×`200`). The server answers both identically, so nothing on the screen is wrong; each
  step asserts `same_response_at` so the day one stops being identical it reddens. A shared in-flight helper would belong in
  `web/src/shared`, outside this lane's paths.
* **The norms document with a PDF page** is not walked: the seeded snapshot's PDFs are bound by rows and have no object in the store, so the
  page would show the seed's store error, not the screen's.
* **The `vendor_list_missing` refusal of a pass** is global state (a list, once set for the section, stays) and cannot be asserted repeatably on
  a lane; `tests/integration/optimisation/proposals` holds it.
* **`scripts/manual-alpha-check.sh` and `make alpha-acceptance` call `--phase all`** (outside this lane's paths). On the published stand,
  which bills per run, `all` now refuses — loudly, before making an account or starting a run — because the first run reports a provider
  mode other than `recorded`. Switch the script to `--phase core` (the journey as it stood before: four write steps and the 29 routes;
  `verify-acceptance.mjs` already counts what the phase declares) or pass `--allow-spend` knowingly.

## What changed

* `tests/e2e/pc01/journey/`: `manifest.json` (86 write steps, `accounts`, route `constants`), `write.mjs` (select / goto / wait / secrets,
  refusals and counts, saved-file downloads, binding, the spend guard), `cdp.mjs` (`select`, `click.times`, label-addressed fields,
  downloads, the keyring flag), `journey.mjs` (`--phase core`, `--steps`/`--routes`/`--seed` partial runs that exit 3, lazy accounts, secret
  scrubbing), `accounts.mjs`, `seed_norms.py`, `build_specification_bundle.py` + `fixtures/optimisation/*`, `write.test.mjs`,
  `verify-acceptance.mjs`, `prove_the_guard_can_fail.py`, `README.md`.
* `tests/e2e/pc01/qa_w50/r66.mjs` (repaired).
* `tests/e2e/test_pc01_journey_conformance.py` — **outside the letter of `allowed_paths`** (`tests/e2e/pc01/**`, `tests/contract/**`), but it is the
  conformance file the task names as required and it goes red on any manifest change; edited in place: the new vocabulary, the dataflow of
  captured identifiers, session and secret names, constants against contract enumerations, screen × case coverage, the specification bundle's
  builder, the norms seed's refusal, the spend guard. 115 tests now.
* `web/src/features/{carry-over-decision,upload-price-list}`, `web/src/widgets/version-comparison` and three vitest files (the three repairs).

No contract, migration, dependency, lock file, `web/FRONTEND_LOCK.json`, `web/openapi`, provider root, global style or `CURRENT_STATE.md` was touched
(`git diff --name-only 508d7ba1..HEAD` is the list above; none matches a forbidden hotspot).

## What a lane needs to run it

See `tests/e2e/pc01/journey/README.md`, «The night window's screens»: a worker beside the API (`EXECUTION_ROLE=api`), `seed_norms.py`
before each run, `build_specification_bundle.py --install-recording` (an **untracked** recording file in `fixtures/recorded/text_analysis/`,
filed under the specification bundle's request checksum, with the baseline's own checksum reproduced first as the control), and a real browser.

## Checks (light acceptance, `AGENTS.md` §8; the complete gate was not run, `R-135`)

Run on the exact tree `f44bd935` unless a line says otherwise; a host disk-full window at 11:31 (see Risks) preceded every line below.

| command | result |
|---|---|
| `npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:61322 --phase all --out …/final-2` | exit **0**, 86/86 write steps, 29/29 routes (above) |
| `… --phase core` | exit 0, 4 + 29, 59 s |
| a partial run that has seen no run (`--steps record-decision,queue-pause-dispatch,…`) | exit 1 «night-window steps … provider mode unknown, not 'recorded'»; no account made, nothing started |
| `git diff --check` | exit 0 |
| `npm --prefix web run lint -- --quiet`, `npm --prefix web run typecheck` | exit 0, exit 0 |
| `npx vitest run` in `web/` (all) | 161 files, **2 354 tests passed** (no `web/src` change after it) |
| `.venv/bin/python -m pytest tests/e2e/test_pc01_journey_conformance.py` | 115 passed |
| `node --test tests/e2e/pc01/journey/write.test.mjs` | 4 passed |
| `python3 tests/e2e/pc01/journey/prove_the_guard_can_fail.py` | 76 mutations, **76 red**, 0 green, exit 0 |
| `QA_W50_ACCOUNTS=… node tests/e2e/pc01/qa_w50/r66.mjs --origin http://127.0.0.1:61322` | `R-66 OK` (19 failures before the repair) |
| `.venv/bin/python -m pytest tests/contract` | 1 089 passed, **82 failed, 126 errors** — all in `test_cp00_candidate.py`, `test_cp00_final_state.py`, `test_validate_bootstrap.py`, **the same 82 + 126 on a detached checkout of `508d7ba1`** with the same interpreter: this environment's checkpoint/git-layout tests, not this lane's. The installed recording (an untracked file) had to be removed first: `test_alpha_acceptance_command.py` refuses a tree with one |

Skipped, stated: the complete `make gate` (`R-135`), the Python integration suites (no `src/` file changed), the manual acceptance, any live provider
call, the stand.

## Mutations (every new guard shown failing)

* **The manifest's guard, against the real manifest**: `prove_the_guard_can_fail.py` rewrites `manifest.json` 76 ways (an unknown session, a template no
  earlier step produced, a constant outside the contract's enumeration, a refusal expecting an unpublished error code, a door of the web tier that is a
  contract operation, a relabelled button, a renamed marker, a missing fixture, an unbounded wait, a read-only precondition that presses a control, a
  screen with its refusal removed, no step deciding a proposal …) and asserts 76 reds. **Three of my first mutations were vacuous as written** — «Assign» is
  a substring of `assignmentFailure`, so the handle check could not see the relabel (`D-61`'s class, caught by this very run), a second label likewise,
  and removing one of two steps left the operation declared by the other — and were rewritten until red. The ten original mutations addressed steps by position
  and had been mutating the wrong step since `classify-version` joined the half; now by name.
* **`write.mjs` pure functions** (`write.test.mjs`): `nightWindowMayRun` always true → red; the CSV formula check without `@` → red; JSON password bodies left
  unredacted → red; `bind` ignored when computing what a step needs → red (four mutations, four reds).
* **`r66.mjs`**: «Диспетчер» renamed in the expected menu → 2 failures; `/optimisation` expected at the wrong address for an account with no role → 1 failure.
* **The three web repairs**: each vitest case run against the pre-repair file: *called 1 times, but got 2 times* (twice) and *expected … to contain
  'data-carryover-state="carried"'*.
* **The specification bundle**: a flipped byte → `--check` exits 1 «differs»; the norms seed with an `auditmanager_alpha` database → exit 1 «refusing to write»,
  with a lane-shaped name it gets past the refusal (conformance controls).
* **The spend guard in the live journey**: shown refusing above (exit 1, nothing made or started).

## Risks and limits

* Evidence is a recorded local stack, not stand evidence (`BETA-MATRIX-01`): a live provider, the real norms corpus and the deployed build are untouched.
* The full gate was not run; no `make gate` claim is made. `web` full vitest and the whole contract battery were run once on this tree (below).
* The journey now writes a lot on an origin: accounts, assignments, price lists, passes, a paused-and-resumed dispatch, a designated snapshot. It is
  for a lane or a test-data stand. A stand that spends is protected by the `recorded` check, not by trust.
* A host disk-full window (a neighbour's build) panicked this lane's PostgreSQL once at 11:31; it recovered and the data was intact. Every
  figure above is from runs after it.

## Instructions for the integrator

1. Merge `agent/beta-live-journey-01` (a real merge; `git merge-base --is-ancestor <tip> HEAD`). No generated artifact is touched.
2. Decide the stand's acceptance call: `scripts/manual-alpha-check.sh` → `--phase core`, or leave `all` and accept that it refuses.
3. `D-180`'s row can be closed against `fee74158` and this journey's `dashboard-sections-panel` step.
4. On the merged tree re-run the walk on a fresh lane: worker, `seed_norms.py`, `--install-recording`, then the command above. If `CLASSIFICATION-CORRECTION-01`
   or `NORM-REFS-RUN-01` changed a screen's copy or markup, the conformance file names the handle that moved.
