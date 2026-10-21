# BETA-LIVE-JOURNEY-01 — the PC-01 browser journey over the night window's screens

**Base:** `origin/dev` `06591a52`, then real merges of `508d7ba1` (the integrator's addendum), `3c62533b` (the committed specification set,
edge hardening, access/search hardening) and `8edcc3bc` (migration head `0029`, the 0.7.0 record).
**Branch:** `agent/beta-live-journey-01`, worktree `.local/worktrees/beta-live-journey`.
**Tested tree:** `93ff8900` (every figure below); the commit after it is this report, docs only.
**Task:** `docs/program/tasks/BETA-LIVE-JOURNEY-01.md`; the integrator's addendum orders items (1)–(6) of
`docs/program/BETA-MATRIX-01.md` §B12, `D-180` and `tests/e2e/pc01/qa_w50/r66.mjs`.
**Status:** the journey walks every screen the night window added and the destinations the matrix listed,
each with a case it must refuse, and runs green on this lane's own stack, directly and through the production nginx
configuration. It uploads the committed `SPEC-TABLE-RECORDING-01` set, reaches the oracle's four `cheaper_analog` proposals,
decides them and downloads the CSVs. Recorded provider only; no spend.

## The green run

```
E2E_PC01_LOGIN=<administrator> E2E_PC01_PASSWORD=<password> E2E_PC01_CHROME=<chrome-for-testing 154> \
  npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:61322 --phase all \
  --out /root/projects/PDF-Analysis/.local/worktrees/beta-live-journey/.local/evidence/run-3
```

Measured 2026-10-21 14:13–14:19 +05 on `93ff8900`: **exit `0`**, `write steps checked: 95/95`, `routes checked: 29/29`, `e2e:pc01 OK`,
124 `ok` lines, **5 min 14 s** (`real 5m13.764s`). `--phase core` on the same tree: exit `0`, 4 write steps and 29 routes, 69 s.

**Through the production edge.** The same `--phase all` against `http://127.0.0.1:61340`, where a stock `nginx:1.27-alpine` container ran
`infra/deploy/proxy/nginx.conf` with only the two upstream addresses and the listen port rewritten (`api:8000` → `127.0.0.1:61320`,
`web:3000` → `127.0.0.1:61322`, `8080` → `127.0.0.1:61340`): **exit `0`**, 95/95, 29/29, `e2e:pc01 OK`, 5 min 24 s. The locations that carry
`auth_request /_edge/credential/web` (`^/bff/v1/projects/[^/]+/documents(?:/[^/]+/versions)?$`) answered the journey's uploads
`POST …/documents` ×2 → `201` (the baseline and the specification set) and `POST …/documents/{d}/versions` ×2 → `201`; an unauthenticated
`POST` to the same address got nginx's `401 authentication_required` envelope (one `curl`, before the run). Nothing was throttled
(`429`) or refused (`413`/`500`) by the edge; the only nginx warning is the expected «request body is buffered to a temporary file».
The container and its config directory are removed. What this does not cover: the TLS server body, the compose network, the real web image.

Stack: PostgreSQL 57700 and MinIO 61300/61301 from `make up` (migrations to `0029`); the API from `infra/deploy/serve.py` on 61320 with
`EXECUTION_ROLE=api`, a worker (`python -m auditmanager.workers serve`), and `next start` on 61322 built with `NEXT_PUBLIC_API_BASE_URL=/bff/v1`,
all host processes started by PID and stopped by PID; `AUDITMANAGER_PROVIDER_MODE=recorded`. The administrator's seeded password was changed
(R-50) and its profile completed; `seed_norms.py` ran before every journey. The host was busy (load 4.5–11, `MemAvailable` 2.3–4.8 GB at the starts;
the integrator's floor of 2.5 GB was missed by 0.2 GB at the start of the first full run, which was red for two findings that are
fixed below).

The envelope is `/root/projects/PDF-Analysis/.local/worktrees/beta-live-journey/.local/evidence/run-3/journey.json` (untracked `.local`; the
other envelopes were deleted on 2026-10-21 14:40 at the integrator's request for disk): the sign-in, the accounts the journey made, the 95 write
steps with every exchange, request body (passwords scrubbed) and response body, the saved export files' facts (`csvColumns`, `csvDataRows`,
`formulaLikeCells`), and the 29 routes.

## What was walked, and what each screen refused

Every step carries `screen` and `case` (`action` or `refused`); `test_the_night_window_steps_agree_with_the_contract_and_with_each_other`
requires, for each of the 25 screens, an action and a refusal (or a written reason there can be none).

| screen | action | refused |
|---|---|---|
| stage and section | confirm АР/П (button pressed twice: one `PUT`); third version as Р | admin-only sees the read-only sentence, no form; stage without section is a disabled button |
| next version | upload a bundle as version 2 and 3, and the committed specification set | a bare PDF is refused by the browser, nothing sent |
| comparison, П→Р, carried decision | compare 1↔2; carry the verdict; compare П↔Р | admin-only gets the read-only sentence; П against Р refused without the switch; the carried row offers nothing again |
| «Настройки анализа» | fifteen sections and their profiles | no form, field or select; an expert reads the same |
| «Диспетчер», «Мои задачи» | assign, take, complete; the admin reads the finished work and its history | admin-only cannot take the work; an expert has no creation form; a return needs a reason |
| price lists | the committed CSV (twice: one revision, ten positions); a second revision with formula-named vendors, a priceless row (skipped, listed) and an analog | admin-only has no upload; an empty file; a table with no columns → 422 |
| vendor lists | global (administrator), project «Завод Север» (expert), then the formula-named vendor added | an expert has no global button; a row with no vendor |
| «Спецификация и цены» | seven rows read over two sheets, five matched, four counted — RUB 464278 — three left out with their reasons (the oracle's figures) | `price_list_missing` before any list |
| «Предложения» | a pass (pressed twice) → the oracle's four proposals; accept (twice); accept then reject (history of two); revise with a comment that begins with `=`; the decision filter; CSV with the decisions (4 rows) | a pass without a price list → `409 conflict` and its sentence; a pass over the set with no table → 0 proposals and a header-only CSV; admin-only starts nothing and decides nothing; «На доработку» needs a comment |
| «Оптимизация разделов» | the АР section across projects, our project a member | a section with no members |
| dashboard section panel | АР counts the confirmed set | read-only (reason written in the manifest) |
| «Нормы» | designate a snapshot, search, catalogue + filter | an unqualified snapshot has no button; an expert has no designation; an empty query |
| run exports | CSV (BOM) and Excel (`PK`, `xl/workbook.xml`), read from the saved file | admin-only → `403 permission_denied` |
| «Очередь» | pause dispatch, a run waits, priority, cancel (expert), re-audit (expert), resume | an expert has no priority or pause; priority 500 is out of range, nothing sent |
| «Исполнители» | intake off and on | an expert has no switch |
| profile, password, sign-out, history | save the patronymic; change the password; «Выйти»; «История версий» | a surname is required; mismatch and wrong current password; the old pass is refused after a change; the signed-out cookie opens nothing |
| «Пользователи» | archive, restore, reset password | the temporary password and its repeat must match |

Proposals are real and they are the oracle's. The journey uploads `fixtures/synthetic/ar_specification/ar_specification.zip` and
`ar_specification_prices.csv` themselves (digests checked against `expected_specification.json`) and the run replays the committed
recording; nothing is installed or written into the checkout. With the project's vendor list «Завод Север» the pass holds seven rows, five
matched, four proposals — savings RUB 16000, 15600, 650 and **absent** (never `0`) for the foam whose quantity is a dash — and
`proposal-revise-needs-a-comment` reads them from `listOptimisationProposals` at exactly those figures. The decisions are driven through
the cards (accept, accept then reject, revise with the comment `=СУММ(A1:A9)`), the first CSV carries them (`,accept,`, `,reject,`, `,revise,`,
`,pending,`) with the comment as `'=СУММ(A1:A9)`. A second revision of the price list (`prices_hostile.csv`: the committed bytes plus a cheaper
membrane sold by `=HYPERLINK("http://example.invalid/x","мембрана")`, a row without a price, and vendors beginning with `+`, `@`, `-`), the
same name added to the project's list and a second pass give five proposals and a second CSV with `'=HYPERLINK`. Both files are checked
cell by cell (`csv_no_formula_cells`), by width (42) and by data rows (4 and 5; 0 for the empty pass), after being read from the browser's saved file.

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
* **The read walk named no route for `NORM-REFS-RUN-01`.** A terminal run's page now reads `getRunNormReferences`; the `run` route declared
  only `getRunStatus`, so the walk of the merged tree failed with «made 1 API call(s) no route in the manifest declares». The route declares
  it. (The first full run on the merged tree found it.)
* **The decision filter's buttons have no handle of their own** (`data-decision-filter` is on the `nav`, and a button's text is «не решено (1)»
  — the count is in the words, so an exact text cannot be written statically). The step addresses the second button by place and says so.
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

* `tests/e2e/pc01/journey/`: `manifest.json` (95 write steps, `accounts`, route `constants`), `write.mjs` (select / goto / wait / secrets,
  refusals and counts, saved-file downloads with the CSV's width and data rows, binding, the spend guard), `cdp.mjs` (`select`, `click.times`, label-addressed fields,
  downloads, the keyring flag), `journey.mjs` (`--phase core`, `--steps`/`--routes`/`--seed` partial runs that exit 3, lazy accounts, secret
  scrubbing), `accounts.mjs`, `seed_norms.py`, `fixtures/optimisation/{empty,no-columns,prices_hostile}.csv`, `write.test.mjs`,
  `verify-acceptance.mjs`, `prove_the_guard_can_fail.py`, `README.md`.
* `tests/e2e/pc01/qa_w50/r66.mjs` (repaired).
* `tests/e2e/test_pc01_journey_conformance.py` — **outside the letter of `allowed_paths`** (`tests/e2e/pc01/**`, `tests/contract/**`), but it is the
  conformance file the task names as required and it goes red on any manifest change; edited in place: the new vocabulary, the dataflow of
  captured identifiers, session and secret names, constants against contract enumerations, screen × case coverage, the declared figures
  against `expected_specification.json`, the uploads against the committed digests and tracked recording, the hostile price list against the
  committed one, the norms seed's refusal, the spend guard. 118 tests now.
* **Removed:** the interim `build_specification_bundle.py`, its zip and `prices.csv` (the committed set replaced them; the untracked recording
  and its `--install-recording` are gone).
* `web/src/features/{carry-over-decision,upload-price-list}`, `web/src/widgets/version-comparison` and three vitest files (the three repairs).

No contract, migration, dependency, lock file, `web/FRONTEND_LOCK.json`, `web/openapi`, provider root, global style or `CURRENT_STATE.md` was touched
(`git diff --name-only 508d7ba1..HEAD` is the list above; none matches a forbidden hotspot).

## What a lane needs to run it

See `tests/e2e/pc01/journey/README.md`, «The night window's screens»: a worker beside the API (`EXECUTION_ROLE=api`), `seed_norms.py` before each
run, a web tier built with `NEXT_PUBLIC_API_BASE_URL=/bff/v1` (without it the browser's calls never leave the page and the first step fails with
«нечто, что не смог разобрать»), and a real browser. Nothing else: the specification set and its recording are committed.

## Checks (light acceptance, `AGENTS.md` §8; the complete gate was not run, `R-135`)

Run on the exact tree `93ff8900`; the host's disk was the binding resource, so the last checks were run before the stack was torn down.

| command | result |
|---|---|
| `npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:61322 --phase all --out …/run-3` | exit **0**, 95/95 write steps, 29/29 routes (above) |
| the same against the nginx edge (`--origin http://127.0.0.1:61340`) | exit **0**, 95/95, 29/29 (above) |
| `… --phase core` | exit 0, 4 + 29, 69 s |
| the first full run on the merged tree (`run-2`, before `93ff8900`) | exit 1 with 3 findings from two defects of the instrument: one write step red (the decision filter's text handle) and one route red (the run route's undeclared `getRunNormReferences`); 94 of the 95 write steps and 28 of the 29 routes were green; both fixed in `93ff8900` |
| `git diff --check` | exit 0 |
| `npm --prefix web run lint -- --quiet`, `npm --prefix web run typecheck` | exit 0, exit 0 |
| `npx vitest run` in `web/` (all) | 164 files, **2 414 tests passed** (includes `rendered-language.guard.test.ts`, which reads this journey's click texts) |
| `.venv/bin/python -m pytest tests/e2e/test_pc01_journey_conformance.py` | 118 passed |
| `node --test tests/e2e/pc01/journey/write.test.mjs` | 5 passed |
| `python3 tests/e2e/pc01/journey/prove_the_guard_can_fail.py` | 80 mutations, **80 red**, 0 green, exit 0 |
| `QA_W50_ACCOUNTS=… node tests/e2e/pc01/qa_w50/r66.mjs --origin http://127.0.0.1:61322` | `R-66 OK` |
| `.venv/bin/python -m pytest tests/contract` | 1 110 passed, **72 failed lines in `-rfE` (pytest's own summary: 82 failed), 126 errors** — every one in `test_cp00_candidate.py`, `test_cp00_final_state.py`, `test_validate_bootstrap.py`, the same three files and counts (82 + 126) as on a detached checkout of `508d7ba1` earlier in this lane; `8edcc3bc` itself was not re-run. `test_alpha_acceptance_command.py` now passes without the recording having to be removed first |

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
  unredacted → red; `bind` ignored when computing what a step needs → red (four mutations, four reds). `csvShape` (the data-row count) is covered by an
  empty file, a header alone, a quoted line break and a ragged file; an empty file once counted as `-1` rows and the control caught it.
* **`r66.mjs`**: «Диспетчер» renamed in the expected menu → 2 failures; `/optimisation` expected at the wrong address for an account with no role → 1 failure.
* **The three web repairs**: each vitest case run against the pre-repair file: *called 1 times, but got 2 times* (twice) and *expected … to contain
  'data-carryover-state="carried"'*.
* **The committed set** (conformance controls, `test_control_*`): a figure the oracle does not hold (5 proposals, another total, `rows.total` 8, a step that
  declares nothing) is found; a journey that attaches its own copy, a directory with no or an untracked recording is found; a hostile price list that does not
  begin with the committed bytes, has a `;` inside a cell, lacks a formula vendor or a priceless row, or whose analog is not cheaper is found. Four of the
  80 `prove_the_guard_can_fail.py` mutations are new: a wrong proposal count, no row count on the CSV, a copy of the bundle, a download of an operation the step
  never makes.
* **The spend guard in the live journey**: shown refusing above (exit 1, nothing made or started).

## Risks and limits

* Evidence is a recorded local stack, not stand evidence (`BETA-MATRIX-01`): a live provider, the real norms corpus and the deployed build are untouched.
* The full gate was not run; no `make gate` claim is made. `web` full vitest and the whole contract battery were run once on this tree (below).
* The journey now writes a lot on an origin: accounts, assignments, price lists, passes, a paused-and-resumed dispatch, a designated snapshot. It is
  for a lane or a test-data stand. A stand that spends is protected by the `recorded` check, not by trust.
* A host disk-full window (a neighbour's build) panicked this lane's PostgreSQL once at 11:31; it recovered and the data was intact. At 14:40 the
  host was at 2.4 GB free and the lane freed 1.7 GB (envelopes, `web/.next`, `web/node_modules`, volumes) on the integrator's request; no run was
  started after that.
* The edge run used the production `nginx.conf` with three rewrites; it does not exercise the TLS server body or the compose network.
* The journey's `proposal-accept` step still sends two identical `POST`s on a double press (both `201`, one decision id) — the benign duplicate recorded above.

## Instructions for the integrator

1. Merge `agent/beta-live-journey-01` (a real merge; `git merge-base --is-ancestor <tip> HEAD`). No generated artifact is touched.
2. Decide the stand's acceptance call: `scripts/manual-alpha-check.sh` → `--phase core`, or leave `all` and accept that it refuses.
3. `D-180`'s row can be closed against `fee74158` and this journey's `dashboard-sections-panel` step.
4. The follow-up the specification set's README left to this lane is done: `POST /optimisation-proposals/{id}/decisions` and
   `GET /optimisation-passes/{id}/export.csv` are walked with their refusals. If `SPEC-TABLE-RECORDING-01`'s PDF, the AR prompt bundle or the extractor
   changes, the recording's key moves and `start-specification-run` (and everything after it) goes red as `recording_missing`; re-run the recording's builder.
5. On the merged tree re-run the walk on a fresh lane: worker, `seed_norms.py`, a web build with `NEXT_PUBLIC_API_BASE_URL=/bff/v1`, then the command above.
   If a later screen changed its markup, the conformance file names the handle that moved.
