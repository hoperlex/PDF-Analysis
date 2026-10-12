# W53-CLOSE — debt and findings closure for waves 48–53

**Status:** revision 1, 2026-10-12, integrator `pdf-analysis-62`, under owner rulings `R-80`…`R-84`
(`OWNER_RULINGS_2026-09-17.md` §3.28). Base: `origin/dev` `872266038a83568b56f6302f01b97771b9aaf281`
(W53 development candidate, full `make gate` `GATE OK` recorded in the W53 integrator handoff).

## 1. Why this wave exists

On 2026-10-12 six independent read-only reviewers analysed the W48–W53 code at `8722660`. They
found no Critical or High defect. They did confirm a set of Medium/Low defects, and the owner then
answered four design questions (`R-80`…`R-83`). `R-84` orders one closure wave that is
implemented by parallel subagent lanes and accepted with light checks. The wave sits between
W53 and W54 and changes no contract, migration, dependency or lock file. The roadmap's
W54–W62 order is unchanged (`ROADMAP-TO-BETA.md` §4).

## 2. Scope: findings closed here

| ID | Finding (review slice) | Lane |
|---|---|---|
| C-01 | A pause that races a claim crash-fails a queued run (`run_to_terminal` sends `CONFLICT` to `_record_crash`) — W53 | EXEC |
| C-02 | `R-82`: re-audit stamps the source run's profile, bundle, digest and mode but runs the current ones — W53 | EXEC |
| C-03 | `_run_status_view` reads `reaudit_of_run_id` with raw SQL in the composition root — W53 | EXEC |
| C-04 | A malformed 200 proxy body escapes effect classification (`AttributeError`/`TypeError`; empty `choices`) — W48/W53 | EXEC |
| C-05 | Recorded replays journalled as possibly-paid `outcome_unknown`, blocking resume — W48 | EXEC |
| C-06 | Stale W48 prose and data after W53 (`ABSENT_CAPABILITIES` says no cancel; heartbeat/resume "absent"); dead `LEASE_SECONDS`; `finish_execution -> str` returns `None` — W48/W53 | EXEC |
| C-07 | `R-80`: an account without roles reads product data — W49 | IDENTITY (API), WEB-ID (screens) |
| C-08 | `updateUser` with names and roles locks target before the admin set (deadlock → 500) — W49 | IDENTITY |
| C-09 | An empty `PATCH /users/{uid}` on an archived account answers 200 (`R-62` gap) — W49 | IDENTITY |
| C-10 | The current-password check of `changePassword` is not braked — W49 | IDENTITY |
| C-11 | `AccountRepository.revoke_role` is dead and ignores `R-62` — W49 | IDENTITY |
| C-12 | Rejecting an analysis-artifact intent bans that version's content-addressed artifacts forever — W48 | STORE |
| C-13 | A release revision written by a newer image makes `listReleases` 500 after a rollback — W52 | STORE |
| C-14 | Rehearsal scripts lack target guards (`process_recovery` global reconcile; `assert` safety checks) — W53 | STORE |
| C-15 | No Origin / `Sec-Fetch-Site` check on the BFF form doors (login and logout CSRF) — W49 BFF | EDGE |
| C-16 | Re-sign-in over a live session leaves the old session row valid — W49 BFF | EDGE |
| C-17 | The API signing key is sent as `Authorization` on the three `security: []` forwards — W47/W49 | EDGE |
| C-18 | No security response headers at the edge (nosniff, frame-ancestors, Referrer-Policy; HSTS on TLS) | EDGE |
| C-19 | The session subject is not refreshed after a self-targeted `updateUser`; web initials expand `ß` | EDGE |
| C-20 | Frame keeps a stale session after a profile save (no `router.refresh()`) — W50/W51 | WEB-ID |
| C-21 | No link to registration from sign-in — W51 | WEB-ID |
| C-22 | No double-submit lock on the three no-JS POST forms — W51 | WEB-ID |
| C-23 | Raw English `error.message` on account/user screens; four disagreeing failure mappers — W51 | WEB-ID |
| C-24 | Archive and reject without confirmation; `/admin/users/<garbage>` answers 200; no `global-error.tsx` — W51 | WEB-ID |
| C-25 | W51 literal addresses bypass the registry/`routes`; dead branches and stale comments — W51 | WEB-ID |
| C-26 | Queue/journal stale for 30 s; starting a run does not invalidate execution reads — W53 web | WEB-OPS |
| C-27 | Queue hidden when `getMe` fails though everyone may read it — W53 web | WEB-OPS |
| C-28 | «История версий» offered to sessions that can never read it — W52 web | WEB-OPS |
| C-29 | Duplicate version/release fetches; a missing build id crashes every page; unknown note kind throws — W52 web | WEB-OPS |
| C-30 | Journey evidence records a stale navigation-attempt count after a CDP rejection — W52 | WEB-OPS |

## 3. Deferred, with a register row each (integrator writes them at `W53-CLOSE-INT`)

Each needs a contract, a migration, a dependency, production access or an owner decision:
heartbeat blocked by the final transaction (W53 F4 → W54 worker service); artifact intent
settlement state (W48 F2, migration → W54 custody); content-addressed blob rejection redesign
(W48 F1 full fix → W54 custody); edge topology — shared guest bucket and missing `Secure`
behind an outer TLS terminator (needs a production probe); re-audit control keyed to run state
(needs an `ExecutionQueueItem` field → W58 contract); concurrent blob insert race (W48 F5);
pending request vs active account holding one login (W49 L-4); effect-table INSERT triggers (W48
F8); interaction-test layer for web islands (jsdom is a dependency change); W53 owner stops
`W53-EXEC-STOP-01`, `-02`, Y-04 and `W53-RELNOTES-STOP-01`.

## 4. Lanes, ownership and order

All six lanes start in parallel from the plan commit on `integration/w53-close`. Each lane works
in `.local/worktrees/w53c-<lane>` on branch `agent/w53c-<lane>`, commits only there, never
pushes, never merges. Shared file `src/auditmanager/bootstrap/adapters.py` is split by class:
EXEC owns `ExecutionAdapter`, `RunAdapter` and `_run_status_view`; IDENTITY owns
`AccountAdapter`; nobody else edits it. Task files: `docs/program/tasks/W53C-*.md`.

| Lane | Task | Private ports |
|---|---|---|
| EXEC | `W53C-EXEC-01` | PostgreSQL `57020`, S3 `60620/60621` |
| IDENTITY | `W53C-IDENTITY-01` | PostgreSQL `57030`, S3 `60630/60631` |
| STORE | `W53C-STORE-01` | PostgreSQL `57040`, S3 `60640/60641` |
| EDGE | `W53C-EDGE-01` | none (container-free) |
| WEB-ID | `W53C-WEB-ID-01` | none |
| WEB-OPS | `W53C-WEB-OPS-01` | none |
| integrator | `W53-CLOSE-INT` | PostgreSQL `57010`, S3 `60610/60611` |

## 5. Checks (`R-84`)

Lanes: `git diff --check`; `ruff` on changed Python; `python -m compileall` of changed modules;
container-free tests they touch; backend lanes may run only their touched DB-backed modules on
their private ports, one run at a time, and remove their containers and volumes afterwards.
Web lanes: `npm --prefix web run lint`, `npm --prefix web run typecheck`, Vitest on touched test
files. The integrator, after merging all lanes: web lint + typecheck + full Vitest; `pytest
tests/contract`; the integration directories of the changed backend contexts on its private
lane. No full `make gate`. Publication target: `origin/dev`. No `origin/main`, no tag, no
`VERSION` change.

## 6. Exit

`W53-CLOSE-INT` merges the accepted lanes, runs §5, writes the deferred register rows,
records the result in `docs/program/W53-CLOSE-INT.md` and publishes `origin/dev` by a proven
fast-forward. The next wave is W54 per `ROADMAP-TO-BETA.md` §4.
