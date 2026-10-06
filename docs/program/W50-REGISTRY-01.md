# W50-REGISTRY-01 — completion report

## Result

**DONE.** Branch `agent/w50-registry-01` from base
`9506dbe` (`W50-FREEZE-01`, = `origin/dev` = `integration/w50`). Every `page.tsx` under
`web/src/app` is a row of `web/src/shared/config/screen-registry.ts` and awaits
`requireScreen('<its own address>', { params, searchParams })`; the five decisions of
`W50-PLAN.md` §3.2 are redirects in order; sign-in lands on `/` or on a validated `next`; `/`,
`/403`, `/account` and the four `R-66` stubs are registered screens; `entities/account` and
the query namespaces `account`, `users`, `registrations` exist. No contract change.

Code commits: `4d4c9a3` (the change), `17742cd` (one code comment the mutations asked for),
`e9d39d4` (the home greeting doubled the period of the name form — found by the lane stand's
journey, §2.8). This report is a docs-only commit on top of `e9d39d4`, which the gate measured
(§2.7, §2.9).

## 1. Changed files

`git diff --name-only 9506dbe..e9d39d4` (75 paths; `e9d39d4` edits two of them; the report
adds the 76th):

```
docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md
scripts/manual-alpha-check.sh
tests/contract/test_alpha_acceptance_command.py
tests/e2e/pc01/journey/fixtures/redden-write-bound.manifest.json
tests/e2e/pc01/journey/fixtures/redden-write.manifest.json
tests/e2e/pc01/journey/fixtures/redden.manifest.json
tests/e2e/pc01/journey/manifest.json
tests/e2e/pc01/journey/verify-acceptance.mjs
web/docs/PC01_UI_SEAM.md
web/src/_pages/account/index.ts
web/src/_pages/account/ui/account-page.tsx
web/src/_pages/analysis-settings/index.ts
web/src/_pages/analysis-settings/ui/analysis-settings-page.tsx
web/src/_pages/forbidden/index.ts
web/src/_pages/forbidden/ui/forbidden-page.tsx
web/src/_pages/home/index.ts
web/src/_pages/home/ui/home-page.tsx
web/src/_pages/norms/index.ts
web/src/_pages/norms/ui/norms-page.tsx
web/src/_pages/queue/index.ts
web/src/_pages/queue/ui/queue-page.tsx
web/src/_pages/section-optimisation/index.ts
web/src/_pages/section-optimisation/ui/section-optimisation-page.tsx
web/src/_pages/sign-in/ui/sign-in-page.tsx
web/src/app/403/page.tsx
web/src/app/account/page.tsx
web/src/app/account/password/page.tsx
web/src/app/analysis-settings/page.tsx
web/src/app/bff/session/screen-lock.ts
web/src/app/bff/v1/[...path]/route.ts
web/src/app/blocks/page.tsx
web/src/app/dashboard/loading.tsx
web/src/app/dashboard/page.tsx
web/src/app/error.tsx
web/src/app/knowledge-base/loading.tsx
web/src/app/knowledge-base/page.tsx
web/src/app/login/page.tsx
web/src/app/logs/page.tsx
web/src/app/norms/page.tsx
web/src/app/not-found.tsx
web/src/app/optimisation/page.tsx
web/src/app/page.tsx
web/src/app/projects/[project_uid]/documents/[document_uid]/page.tsx
web/src/app/projects/[project_uid]/loading.tsx
web/src/app/projects/[project_uid]/page.tsx
web/src/app/projects/[project_uid]/runs/[run_id]/page.tsx
web/src/app/projects/[project_uid]/runs/[run_id]/review/page.tsx
web/src/app/projects/[project_uid]/versions/[version_uid]/comparison/page.tsx
web/src/app/projects/[project_uid]/versions/[version_uid]/page.tsx
web/src/app/projects/loading.tsx
web/src/app/projects/page.tsx
web/src/app/queue/page.tsx
web/src/app/section-optimisation/page.tsx
web/src/app/workers/page.tsx
web/src/entities/account/api/use-me.ts
web/src/entities/account/index.ts
web/src/entities/account/model/account.ts
web/src/features/sign-in/index.ts
web/src/features/sign-in/model/exchange.ts
web/src/features/sign-in/ui/sign-in-form.tsx
web/src/shared/api/query-keys.ts
web/src/shared/config/index.ts
web/src/shared/config/screen-registry.ts
web/tests/guards/default-credential-screens.guard.test.ts
web/tests/guards/prepared-sections.guard.test.ts
web/tests/guards/screen-guard.guard.test.ts
web/tests/guards/screen-registry.guard.test.ts
web/tests/guards/screen-set.guard.test.ts
web/tests/unit/api/configuration-and-cache-keys.test.ts
web/tests/unit/entities/account.test.ts
web/tests/unit/screens/route-screens.ts
web/tests/unit/screens/routes.test.ts
web/tests/unit/session/bff-session.test.ts
web/tests/unit/session/login-route.test.ts
web/tests/unit/session/return-path.test.ts
```

`default-credential-screens.guard.test.ts` is the rename source of `screen-guard.guard.test.ts`
(`git mv`, then rewritten). Every path is inside the task file's `allowed_paths`, checked by a
script against the grant's patterns (0 outside). `web/src/shared/api/index.ts` was edited once
by mistake during the work and reverted before the first commit; it is not in the diff.

## 2. Checks and their results

### 2.1 The apply-and-see probe, before implementing

A disposable `git clone --shared` of `9506dbe` at `/root/w50reg-probe` (node_modules and venv
symlinked from the worktree), with a registry stub, `/projects` switched to a stub
`requireScreen`, and `/` switched to a `RoutePlaceholder` from `_pages/home`.

- `npm --prefix web test -- --run --maxWorkers=2` on the probe:
  `Test Files 3 failed | 85 passed (88)`, `Tests 4 failed | 1292 passed (1296)`, `Errors 3`.
  The four reds — `default-credential-screens.guard.test.ts` (each address calls the lock or is
  registered open), `screen-set.guard.test.ts` (the opt-out proof), `routes.test.ts` twice
  (`/projects renders the projects screen`, `/ starts the journey at the project list`) — and
  the three unhandled rejections (`NEXT_REDIRECT` from the `/` case, `cookies was called
  outside a request scope` twice from the opt-out proof) are all in files the grant names.
- `.venv/bin/pytest tests/e2e tests/contract --ignore=<the three CP-00 files> -q` on the base
  worktree: `4 failed, 566 passed, 5 skipped, 48 errors` — every failure and error is in
  `tests/e2e/p02/*` and `tests/e2e/pc01/test_acceptance.py`, which need a live database and no
  stand was up. On the probe the same set plus one: `test_release_command_cannot_turn_skips…`,
  which refused the probe's **uncommitted** checkout (`FAIL: checkout содержит незакоммиченные
  изменения`); committed in the clone, `test_alpha_acceptance_command.py` and
  `test_pc01_journey_conformance.py` were `94 passed`.

No red outside the grant. (The probe could not see the rendered-language red of §4.1: it is
caused by `app/error.tsx`, which the probe did not create.)

### 2.2 Frontend suite, by file

`npm --prefix web test -- --run --maxWorkers=2`: base `9506dbe` **88 files / 1296 tests**, all
passed; head `4d4c9a3` **91 files / 1398 tests**, all passed; `e9d39d4` adds one case to
`routes.test.ts` (the gate's count, §2.7, is on `e9d39d4`). Files whose count changed between
the base and `4d4c9a3` (every other file is unchanged):

| file | base | head |
|---|---|---|
| `tests/guards/default-credential-screens.guard.test.ts` | 9 | — (renamed) |
| `tests/guards/screen-guard.guard.test.ts` | — | 34 |
| `tests/guards/screen-registry.guard.test.ts` | — | 13 |
| `tests/guards/prepared-sections.guard.test.ts` | 14 | 18 |
| `tests/unit/api/configuration-and-cache-keys.test.ts` | 20 | 21 |
| `tests/unit/entities/account.test.ts` | — | 8 |
| `tests/unit/screens/routes.test.ts` | 32 | 33 (34 at `e9d39d4`) |
| `tests/unit/session/bff-session.test.ts` | 39 | 50 |
| `tests/unit/session/login-route.test.ts` | 5 | 6 |
| `tests/unit/session/return-path.test.ts` | — | 38 |

### 2.3 Lint, typecheck, `git diff --check`

`npm --prefix web run lint -- --quiet` and `npm --prefix web run typecheck` — no output, exit 0
(on `4d4c9a3`; `17742cd` changes one comment). `git diff --check 9506dbe..HEAD` — clean.

### 2.4 The required Python files

`.venv/bin/pytest tests/e2e/test_pc01_journey_conformance.py
tests/contract/test_alpha_acceptance_command.py tests/contract/program/test_wave_governance.py -q`
on `4d4c9a3`: **114 passed in 6.34s**.

### 2.5 `next build`

`NEXT_PUBLIC_API_BASE_URL=/bff/v1 NEXT_PUBLIC_INSTANCE_LABEL=w50reg npm --prefix web run build`
on `17742cd`: exit 0, `✓ Compiled successfully`, `Checking validity of types` passed (Next's own
check of every page's props). The route table, first-load JS per route — the freeze recorded
none, so this is the first reading with the six new routes:

```
┌ ƒ /                                                            201 B         111 kB
├ ƒ /_not-found                                                  127 B         103 kB
├ ƒ /403                                                         578 B         123 kB
├ ƒ /account                                                     201 B         111 kB
├ ƒ /account/password                                            184 B         115 kB
├ ƒ /analysis-settings                                           201 B         111 kB
├ ƒ /bff/v1/[...path]                                            127 B         103 kB
├ ƒ /blocks                                                    2.11 kB         135 kB
├ ƒ /dashboard                                                 4.23 kB         143 kB
├ ƒ /knowledge-base                                            2.76 kB         129 kB
├ ƒ /login                                                       201 B         111 kB
├ ƒ /logs                                                        201 B         111 kB
├ ƒ /norms                                                       201 B         111 kB
├ ƒ /optimisation                                                201 B         111 kB
├ ƒ /projects                                                  3.51 kB         133 kB
├ ƒ /projects/[project_uid]                                    5.71 kB         139 kB
├ ƒ /projects/[project_uid]/documents/[document_uid]            1.4 kB         135 kB
├ ƒ /projects/[project_uid]/runs/[run_id]                      3.76 kB         139 kB
├ ƒ /projects/[project_uid]/runs/[run_id]/review               9.61 kB         145 kB
├ ƒ /projects/[project_uid]/versions/[version_uid]             4.13 kB         146 kB
├ ƒ /projects/[project_uid]/versions/[version_uid]/comparison  3.77 kB         146 kB
├ ƒ /queue                                                       201 B         111 kB
├ ƒ /section-optimisation                                        201 B         111 kB
└ ƒ /workers                                                     201 B         111 kB
+ First Load JS shared by all                                   103 kB
```

### 2.6 Mutations, each red

Run one at a time in a disposable `git clone --shared` of `4d4c9a3` at `/root/w50reg-mut`
(node_modules and venv symlinked), by `mutate.py <id>` (one exact replacement that must match
once), the named test files, then `git checkout -- .` and a clean `git status` before the next.
The unmutated clone first: the nine target vitest files `211 passed (211)`, the two Python files
`99 passed`.

| id | mutation | red (verbatim summary) |
|---|---|---|
| M01 | `/queue`'s route drops its `requireScreen` call | `screen-guard … every route file awaits requireScreen …` — `"/queue does not call requireScreen (web/src/app/queue/page.tsx)"`; 1 failed / 33 passed |
| M02 | a registry row `/ghost` with no page | `screen-registry … has no page without a row and no row without a page` — `expected [ '/ghost' ] to deeply equal []` |
| M03 | the `/norms` row removed (page stays) | 5 failed, among them `… web/src/app serves these addresses and the screen registry has no row for them …: expected [ '/norms' ] to deeply equal []` |
| M19 | the `queue` route removed from `manifest.json` | `FAILED test_pc01_journey_conformance.py::test_the_journey_walks_every_screen_the_application_offers` — `screen(s) exist that the PC-01 journey does not walk: ['/queue']` |
| M05c | the 512-character limit removed | 3 failed: `takes exactly the maximum length, and not one character more`, `a 513-character value`, and the BFF case `drops /projects?q=aaa…` — `expected '/projects?q=aaa…' to be '/'` |
| M05d | the registry-shape check removed | 9 failed, among them `an address this application does not serve` — `expected '/nowhere' to be null`, and the BFF's `drops /nowhere …` — `expected '/nowhere' to be '/'` |
| M05a, M05b | the explicit `//` (resp. `/\`) refusal removed, alone | **survive** (88 passed): the shape check refuses both on its own — an empty segment or a backslash never matches a registered segment. Equivalent mutants; the code comment added in `17742cd` says so |
| M05g | the explicit `//`/`/\` line **and** the shape check removed | 14 failed / 74 passed, among them `another origin, protocol-relative`, `a backslash read as a slash`, and the BFF's `drops //evil.example …` — `expected '//evil.example' to be '/'`, `drops /\evil …` — `expected '/\evil' to be '/'` |
| M05e | the BFF strips the query from `next` | `lands on next, with its query` — `expected '/projects' to be '/projects?x=1'` |
| M05f | the BFF trusts `next` without validating it | 6 failed: `expected '//evil.example' to be '/'`, `expected 'https://evil.example' to be '/'`, `expected '/\evil' to be '/'`, the 513-character value, `/nowhere`, `/projects#top` |
| M06a | `ForbiddenPage` ignores the roles it is given | `an expert sent here from /admin/users sees «Администратор»` — `expected '<section class="am-page">…' to contain '«Администратор»'` |
| M06b | `/queue` gains `roles: ['admin']` in the live registry | `R-60: the role-gated set is as measured …` — `expected [ '/queue' ] to deeply equal []`; `the four stubs are session screens …` |
| M08-1 | decision 1 removed (a guest passes) | 5 failed: `expected null to be '/login?next=%2Fprojects%3Fx%3D1'`, `… '/login?next=%2Faccount%2Fpassword'`, `… '/login'` |
| M08-2 | decision 2 removed | `expected null to be '/account/password'`; `comes before the profile` — `expected '/account' to be '/account/password'` |
| M08-3 | decision 3 removed | `is sent from a session screen to /account` — `expected null to be '/account'` |
| M08-4 | decision 4 removed | 2 failed — `expected null to be '/403?from=%2Fadmin%2Fusers'` |
| M08-5 | decision 5 removed | `screen-guard … sends a signed-in visit to /login to /` — `expected null to be '/'`; `login-route … sends a live session to /` |
| M09 | `/` redirects to `/projects` again after the guard | `routes.test … renders the home page with the name and roles the session carries` — `Error: NEXT_REDIRECT` |
| M10a | the queue stub's promise says «в волне 55» | `prepared-sections … 'queue' shows no number at all` |
| M10b | the norms stub loses its promise (component default) | `none of the three falls back to the generic sentence` — `norms shows the generic sentence` |
| M11a | `/optimisation` in group `system`, `inMenu: true` | `the menu is exactly the ruling …` — `group system: expected [ '/logs', '/workers', …(3) ] …`; `/optimisation is registered, reachable, hidden and out of the menu` — `expected 'system' to be 'hidden'` |
| M11b | the `/optimisation` row removed | 4 failed, among them `/optimisation is unregistered; R-66 keeps it a reachable screen until W59: expected undefined to be defined` |
| M13 | `app/error.tsx` renders `error.message` | `§3.3 … the error boundary shows none of what was thrown …` — `the boundary rendered Cannot read` |
| M14 | `account.me` drops its unknown-role check | `fails with a typed fault when getMe lists a role outside the contract set` — `promise resolved … instead of rejecting` |
| M15 | `roleLabel` falls back to «Роль» | `is a typed fault for a value outside the set, never a fallback label` — `expected function to throw an error, but it didn't` |
| M16 | the `/` seed becomes an opt-out again | `screen-set … runs every opt-out claim …` — `an address is excused from both instruments …: expected [ '/' ] to deeply equal []` |
| M17 | the preflight accepts `/projects` (or `/login` with any query) | 4 failed: `[/login-False]`, `[/login?next=%2F%2Fevil.example-False]`, `[/login?next=%2F&next=%2Fprojects-False]`, `[/projects-False]` |
| M18 | the verifier against a one-route-short envelope | envelope 22 routes: `exit=0 verdict=PASS coldRoutes PASS 22/22`; envelope 21: `exit=1 verdict=FAIL`, findings `read phase does not declare exactly the 22 routes of the manifest`, `read phase did not check 22/22 cold routes`, `journey has no record for every route`. Manifest moved away: `exit=1`, `FAIL`, `journey manifest is unavailable: ENOENT …` |

| M20 | the home headline closes the greeting with a period again (on `e9d39d4`) | `routes.test … greets by the name form without doubling the period it ends with` — `expected '<section class="am-page">…' not to match /\.\./`; 1 failed / 33 passed |

Every logged run ended `restored clean`. Logs: `/root/w50reg-mut-logs/<id>.log`.

### 2.7 The full gate

Host checked before each start (`free -g`, `uptime`, `pgrep -x make` with cmdline and cwd): no
`make gate` running; the slot was given by the integrator after its own gate on `3a54108`.

- **Run 1, `e9d39d4`, 19:46:36 → 20:10:47 — void.** Foundation `35 passed`; battery
  `1 failed, 3182 passed, 6 skipped, 298 subtests passed in 1375.99s (0:22:55)`, the one failure
  `tests/integration/composition/test_deploy_image_identity.py::TestAnImageWhoseContentChangedNeverKeepsAnOldIdentity::test_the_pin_is_taken_before_the_build_or_there_is_nothing_to_compare`
  (`assert 0 == 2`, no `tag … :deploy-previous` call recorded), load 16–25 during the run.
  `OPERATING_CONSTRAINTS.md` §4.6 names this test as the contention red; run alone right after on
  the same tree: `23 passed in 27.57s`. This diff touches nothing under `infra/`, `src/` or
  `tests/integration/`. Log `/root/w50reg-gate-run1-void.log`.
- **Run 2, `e9d39d4`, 20:11:48 → 20:29:04 — the result** (load ≈ 1.5 at start, 5–6 GB
  available). Foundation `35 passed in 25.41s`; battery `3183 passed, 6 skipped, 4 warnings, 298
  subtests passed in 964.23s (0:16:04)`; `eslint .` and `tsc --noEmit` clean; frontend
  `Test Files 91 passed (91)`, `Tests 1399 passed (1399)`; then, verbatim:

```
GATE OK: battery, foundation, frontend lint/typecheck/tests and whitespace all pass
```

`make gate` exit 0; `git status --porcelain -uall` empty before and after. Log
`/root/w50reg-gate.log`.

### 2.8 The live journey and the guest `curl`s, on the lane stand

The stand, served from this worktree at `17742cd` (the `next build` of §2.5): lane services
`make up` / `make migrate` (instance `gate-w50reg`, PostgreSQL `56640`, MinIO `60240/60241`,
migration head `0015`); API `PYTHONPATH=src .venv/bin/python infra/deploy/serve.py`,
`AUDITMANAGER_PROVIDER_MODE=recorded`, a disposable `AUDITMANAGER_API_TOKEN`, API `56641`,
health `56642`, bind `127.0.0.1` (PID `3178170`, cwd the worktree; startup line `auditmanager:
wired, provider_mode=recorded, operations=34`); web `next start -p 56643 -H 127.0.0.1` (PID
`3178171`, cwd `…/w50-reg/web`). Ports `56641`–`56643` were checked free with `ss -ltn` before
use and are held by no row of `PORT_REGISTRY.md`. Both PIDs were stopped by PID after the run
(cwd confirmed), `make down` ran, and the volumes `gate-w50reg-postgres-data` and
`gate-w50reg-s3-data` were removed by exact name before the gate.

**The account.** The migration's seeded `admin` (roles `admin`, `expert` by `0015`'s backfill),
through the API as a reviewer would: `POST /auth/token 200` (`is_default_credential: true`),
`POST /auth/password 200` (`false`), `PATCH /me 200` with names and an e-mail →
`profile_complete: true`, login the e-mail, label `Проверкина А. С.`. The new password lives in
a `0600` file outside the tree and appears nowhere here.

**The journey**, `E2E_PC01_LOGIN=<that e-mail> E2E_PC01_PASSWORD=<from the file>
E2E_PC01_CHROME=<chrome-for-testing> npm --prefix web run e2e:pc01 -- --origin
http://127.0.0.1:56643 --phase all --out /root/w50reg-stand/journey-out`, exit 0, verbatim:

```
sign-in: ok at /login -- carrying 'am_session' (HttpOnly=true, SameSite=Strict) into every cold browser
write half: 3 step(s), fixture fixtures/synthetic/ar/ar_baseline.pdf
ok  create-project   api=3 {"project_uid":"prj_01M48SKYFK4RDNQ9XHZS7468V8"}
ok  upload-document  api=4 {"project_uid":"prj_01M48SKYFK4RDNQ9XHZS7468V8","version_uid":"ver_01M48SMZB2V7ZRDX1WSQZNSE92"}
ok  start-run        api=5 {"project_uid":"prj_01M48SKYFK4RDNQ9XHZS7468V8","run_id":"run_01M48SNYE8FYZF3GN93CYMGA7C"} terminal=published in 1518ms/150000ms
ok  root           200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  projects       200  api=1 auth=0 console=0 jar=[am_session] w=780/780 {"project_uid":"prj_01M48SKYFK4RDNQ9XHZS7468V8"}
ok  project        200  api=1 auth=0 console=0 jar=[am_session] w=765/780 {"document_uid":"doc_01M48SMZAHJFQ0C9H0SZNHYESJ"}
ok  document       200  api=1 auth=0 console=0 jar=[am_session] w=780/780 {"version_uid":"ver_01M48SMZB2V7ZRDX1WSQZNSE92"}
ok  version        200  api=2 auth=0 console=0 jar=[am_session] w=765/780 {"run_id":"run_01M48SNYE8FYZF3GN93CYMGA7C"}
ok  comparison     200  api=1 auth=0 console=0 jar=[am_session] w=780/780
ok  run            200  api=1 auth=0 console=0 jar=[am_session] w=765/780
ok  review         200  api=5 auth=0 console=0 jar=[am_session] w=765/780
ok  sign-in        200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  knowledge-base 200  api=1 auth=0 console=0 jar=[am_session] w=780/780
ok  change-password 200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  blocks         200  api=1 auth=0 console=0 jar=[am_session] w=780/780
ok  optimisation   200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  logs           200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  workers        200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  dashboard      200  api=1 auth=0 console=0 jar=[am_session] w=765/780
ok  forbidden      200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  account        200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  section-optimisation 200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  norms          200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  analysis-settings 200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  queue          200  api=0 auth=0 console=0 jar=[am_session] w=780/780
envelope: /root/w50reg-stand/journey-out/journey.json
write steps checked: 3/3
routes checked: 22/22
e2e:pc01 OK
```

From the envelope: `routesDeclared 22`, `routesChecked 22`, `failures 0`; `root` document chain
`200 /` (no redirect); `sign-in` chain `307 /login -> 200 /`, landed on `/` as its
`redirects_to` declares. The sign-in landed on `/` (`session.lands_on`). The envelope's
rendered text of `/` read `Здравствуйте, Проверкина А. С.. Начальная страница ещё не готова` —
the doubled period `e9d39d4` repairs (the stand ran `17742cd`; the repair is one headline
string and its unit case, M20).

**Guest `curl -sI`**, one or more addresses per access level, `Location` quoted:

```
GET /                                         307 Location: /login?next=%2F
GET /projects                                 200 (no Location)
GET /projects?x=1                             200 (no Location)
GET /projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B  200 (no Location)
GET /queue                                    307 Location: /login?next=%2Fqueue
GET /optimisation                             307 Location: /login?next=%2Foptimisation
GET /account/password                         307 Location: /login?next=%2Faccount%2Fpassword
GET /account                                  307 Location: /login?next=%2Faccount
GET /login                                    200 (no Location)
GET /403                                      200 (no Location)
GET /403?from=/admin/users                    200 (no Location)
GET /login?next=//evil.example                200 (no Location)
```

`session` (`/`, `/queue`, `/optimisation`) and `open-to-default-credential` (`/account`,
`/account/password`) answer `307` to `/login?next=<the address>`; `public` (`/login`, `/403`)
answer `200`. **`/projects`, its dynamic children, `/dashboard` and `/knowledge-base` answer
`200` with no `Location`** — see §4.10: their bodies carry Next's streamed redirect, `<meta
id="__next-page-redirect" http-equiv="refresh" content="1;url=/login?next=%2Fprojects">` and the
RSC instruction `NEXT_REDIRECT;replace;/login?next=%2Fprojects;307;` (same for the other three;
`/blocks`, which has no `loading.tsx`, answers a plain `307`). A cold guest browser driven
through the journey's own `cdp.mjs` lands on the sign-in screen with the validated `next` in the
hidden field for every one of them:

```
/projects                                     -> /login?next=%2Fprojects  sign-in form=1  hidden next=/projects
/dashboard                                    -> /login?next=%2Fdashboard  sign-in form=1  hidden next=/dashboard
/knowledge-base                               -> /login?next=%2Fknowledge-base  sign-in form=1  hidden next=/knowledge-base
/projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B      -> /login?next=%2Fprojects%2Fprj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B  sign-in form=1  hidden next=/projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B
/blocks                                       -> /login?next=%2Fblocks  sign-in form=1  hidden next=/blocks
/                                             -> /login?next=%2F  sign-in form=1  hidden next=/
```

### 2.9 What the gate measured

The gate measured the code commit `e9d39d4`. The commit that adds this report changes
`docs/program/W50-REGISTRY-01.md` only (`git diff --name-only e9d39d4..HEAD` names that one
file); no gate ran after it, and none is needed for a docs-only commit by the brief's rule.

## 3. New and changed contracts

No file under `contracts/**`, `web/openapi/**` or `web/src/shared/api/generated/**` changed:
the API surface is still 27 paths / 34 operations / 77 schemas. The internal seams this task
fixes for Stage B and C:

- **`web/src/shared/config/screen-registry.ts`** — `SCREEN_REGISTRY` (22 rows of `{ address,
  label, group, access, roles, inMenu }`, `as const satisfies readonly ScreenEntry[]`), the
  types `ScreenEntry`, `ScreenAddress` (the registry's own address union), `ScreenAccess`,
  `ScreenGroup`, `ScreenRoles` (`'any' | readonly [Role, ...Role[]]`), the redirect targets,
  `safeReturnPath(candidate, registry?)` (the one `next`/`from` validator), `concreteAddress`,
  `screenAt`, `screenMatching`, `requiredRolesFor(from, registry?)`. Exported through
  `@/shared/config`. Groups exactly as `R-66` amends §3.1; `/optimisation` in `hidden`,
  `inMenu: false`; the screens under a project in `work`, `inMenu: false`; no `admin` row.
- **`requireScreen(address, { params, searchParams })`** in
  `web/src/app/bff/session/screen-lock.ts` — returns the session's `SessionAccount` (typed
  non-null on every non-`public` address, `SessionAccount | null` on a `public` one) or
  redirects; `enforceScreen(entry, props)` is the same five decisions over one row, exported for
  the guard's tests. `requireAChangedPassword` no longer exists.
- **`HomePage` props** (`web/src/_pages/home`) — `{ displayLabel: string; roles: readonly
  Role[] }`, from the subject `requireScreen` returns. `W50-HOME-01` keeps the export and these
  props; the `/` seed renders `HomePage` with `{ displayLabel: 'Петрова А. С.', roles:
  ['expert'] }`.
- **`entities/account`** — `ROLE_LABELS` (Эксперт, Администратор), `roleLabel`/`roleLabels`
  (throw `UnknownRoleError` for a value outside the contract set), `isKnownRole`,
  `displayLabelOf` (throws `MalformedAccountError` on an empty label), `initialsOf` (held to the
  session's own `initialsOf` by a test), `meQueryOptions()`/`useMe()` under
  `queryKeys.account.me()`.
- **Query namespaces** — eight and closed: `projects`, `versions`, `runs`, `findings`,
  `dashboard`, `account`, `users`, `registrations`; new factories `account.all/me`,
  `users.all/list/detail`, `registrations.all/list`; `PC01_UI_SEAM.md` §6 carries their rows.
- **Sign-in** — `SIGN_IN_LANDING_PATH` = `AFTER_SIGN_IN` = `session.lands_on` = `/`;
  `SIGN_IN_NEXT_FIELD = 'next'`; `SignInPage`/`SignInForm` take `next`.
- **Journey manifest** — 22 routes; `root` without `redirects_to` and with `expects_api: []`;
  `sign-in` with `redirects_to: "/"`; six new entries, each `expects_api: []`.
- **Release acceptance** — the verifier's route count is `manifest.json`'s `routes.length`;
  the preflight's `HTTP-root` passes only a same-origin `307/308` to exactly `/login?next=/`.

## 4. Risks and known limitations

1. **`rendered-language.guard.test.ts` (outside the grant) does not render the error
   boundary.** Its branch scan lists every literal `title="…"` on a state component in
   `web/src`, and its matrix renders screens plus a hand-written list that includes
   `not-found` but no error boundary. With `app/error.tsx`'s title written as a literal, the
   guard was red: `"При построении экрана произошла ошибка."  (web/src/app/error.tsx)` unreached.
   I did not edit the guard. `error.tsx` holds its words in module constants, so the literal
   scan does not list them, and `screen-guard.guard.test.ts` §3.3 renders the boundary and
   asserts no thrown text and no Latin word (M13 shows it red). The guard's own matrix should
   gain `{ name: 'error-boundary', make: … }` beside `not-found` — **open question for the
   integrator** (a later lane's grant).
2. **`next` is not kept across a refused sign-in.** The refusal redirect
   (`/login?refusal=<code>`) is outside "the after-sign-in redirect only", so a guest who
   mistypes loses `next` and lands on `/` after the next attempt.
3. **`next` is not carried across the default-credential detour.** A default credential lands
   on `/account/password` whatever `next` says (the plan's rule); after the change it navigates
   from there.
4. **`/account/password` and `/login` changed audience.** The change screen is now
   `open-to-default-credential`, so a guest is sent to sign in (it used to render a signed-out
   form); a session opening `/login` is sent to `/` (decision five), so the sign-in screen's
   sign-out panel is reachable only through the frame's «Выйти». Both components keep the
   branches and their tests.
5. **The registry does not import `shared/lib/routes.ts`.** `W50-PLAN.md` §3.1 says it
   "imports it and does not replace it". It does not replace it (untouched), but it writes its
   templates as literals so `ScreenAddress` is a compile-time union; `routes`' builders return
   `string`. Builders and the tree are held together by `routes.test.ts`'s `D-94` cases, the
   tree and the registry by `screen-registry.guard.test.ts` — **open question** whether that
   satisfies the plan's wording.
6. **Prose this change makes stale, outside the grant (not edited):**
   `web/src/shared/lib/routes.ts:30` («The journey starts here and `/` redirects to it»);
   `tests/e2e/pc01/journey/journey.mjs:304` («`/` is a redirect»);
   `tests/e2e/pc01/journey/README.md:150–152` (a seeded sign-in stops «not at `/projects`»);
   `web/src/app/bff/session/store.ts:487–490` (the legacy `openSession` form is «kept for
   exactly one caller», naming the renamed guard file — `session-store.test.ts:177–178` is its
   remaining caller); the `root` route's `$comment` and `expects_api: listProjects` in
   `fixtures/redden-write.manifest.json` and `redden-write-bound.manifest.json` (the grant moves
   only `lands_on` and `redirects_to`; both fixtures run `--phase write`, which does not walk
   `root`); the case titles of `prepared-sections.guard.test.ts` that still say "three" while
   the cases iterate seven sections (the grant names `SECTIONS`, the route-file case and one
   line of the navigation case).
7. **A pin in the task's table that does not move:** `configuration-and-cache-keys.test.ts:224`
   `toHaveLength(5)` is the length of `decisionCacheKeys(…)`, not a namespace count; it is
   unchanged and green.
8. **`UserListFilters` and `RegistrationListFilters`** are exported from `query-keys.ts` but
   not from the `@/shared/api` barrel (outside the grant); a consumer can rely on inference
   from `queryKeys.users.list(…)`, or `W51` adds the export.
9. **Not in the gate:** `next build` (run here, §2.5) and the live journey (§2.8). The gate
   does not see `expects_api` (`D-108`).
10. **A guest's direct request to a segment with a `loading.tsx` answers `200`, not `307`.**
   Measured on the stand (§2.8): `/projects`, `/projects/*`, `/dashboard` and `/knowledge-base`
   — the four segments `W50-PLAN.md` §3.3 gives a `loading.tsx` — commit a `200` with the
   loading state, and the guard's redirect travels inside the stream (`<meta http-equiv=
   "refresh">` and the RSC `NEXT_REDIRECT`). A browser lands on `/login?next=…` with the
   validated `next`, so the decision holds; the HTTP status and `Location` do not, which is what
   `curl`, a probe or a monitor reads (`D-28`'s concern), and what `W50-QA-01` ("guest redirect
   for every registered `session` screen") and `W50-JUDGE-X` (black-box) will meet. It is the
   plan's two requirements meeting — the guard in each page (§3.2: middleware and layout guards
   are ruled out) and a segment loading boundary above the page (§3.3) — not a defect in either
   file. Before this task those four addresses answered a guest `200` with the screen itself.
   **Open question for the integrator:** accept the streamed redirect; or have `W50-LAZY-01`
   put the loading state inside the page, below the guard (a `Suspense`/`next/dynamic`
   `loading`, which §3.4 already requires), and drop the segment `loading.tsx`, which restores
   a real `307` on all four; the release preflight checks only `/`, which has no loading
   boundary.

## 5. Instructions to the integrator

- Merge `agent/w50-registry-01` at the SHA in the hand-back into `integration/w50`; Stage B
  (`W50-SHELL-UI` ∥ `W50-HOME-01` ∥ `W50-LAZY-01`) starts from that merge.
- `W50-HOME-01`: keep `HomePage`'s export and props; the `root` and `sign-in` `expects_api`
  entries are yours to fill (both `[]` now).
- `W50-SHELL-FRAME`: build the menu from `SCREEN_REGISTRY` rows with `inMenu: true`, grouped
  by `group`, filtered by `roles`; the `/account` and `/account/password` rows are in group
  `account` with `inMenu: false` for the account menu; `prepared-sections.guard.test.ts`'s
  navigation case iterates only the three original sections (`stub: false`) until then.
- `W50-LAZY-01`: the four `loading.tsx` render `<LoadingState />`; §2.5 is a route-table
  reading on this branch, if a baseline before Stage B is wanted.
- Decide §4.1 (a grant for the rendered-language guard's hand-written list), §4.5 and §4.10
  (the loading boundary turns a guest's `307` into a streamed redirect on four segments).

## 6. Forbidden hotspots untouched

`git diff --name-only 9506dbe..HEAD` contains nothing under `contracts/**`, `web/openapi/**`,
`web/src/shared/api/generated/**`, `src/**`, `db/**`, `web/src/_app/**`,
`web/src/app/layout.tsx`, `web/src/app/globals.css`, `web/src/shared/ui/**`,
`web/src/shared/lib/routes.ts`, `web/package.json`, `web/package-lock.json`,
`web/FRONTEND_LOCK.json`, root lock files, `CURRENT_STATE.md`, `DEBT_REGISTER.md`,
`OWNER_RULINGS_*.md`, `PORT_REGISTRY.md` or `CHECKPOINT_REGISTRY.md`. No ref was pushed, no tag
created, no deployment touched.

## Appendix A — pins moved, with their new values

| pin | was | now |
|---|---|---|
| `web/tests/guards/screen-set.guard.test.ts` opt-out case | `toBe(1)` | the excused addresses `toEqual([])`, plus a case proving the hold-check names an unheld claim |
| `web/tests/unit/screens/route-screens.ts` | `root-redirect` opt-out; 16 seeds | `/` seed `home` (`HomePage`); six new seeds (`forbidden`, `account-incomplete`, `analysis-settings`, `norms`, `queue`, `section-optimisation`); 22 seeds |
| `web/tests/unit/screens/routes.test.ts` | empty cookie jar; routes called without `searchParams`; `/` → `/projects` | a full-subject session in the jar; every route called with `searchParams`; `/` renders `HomePage` with the subject's name and roles, and a guest is sent to `/login?next=%2F` |
| `web/tests/guards/prepared-sections.guard.test.ts` | `SECTIONS` 3; empty jar | `SECTIONS` 7 (the four stubs `stub: true`); the route-file case opens a session and passes `searchParams`; the navigation case iterates `stub: false` |
| `tests/e2e/pc01/journey/manifest.json` | `lands_on: "/projects"`; `root` → `/projects` + `listProjects`; 16 routes | `lands_on: "/"`; `root` no redirect, `expects_api: []`; `sign-in` `redirects_to: "/"`; 22 routes |
| `tests/e2e/pc01/journey/verify-acceptance.mjs` 129, 130, 132, 176, 177, 181 | `=== 16` | `=== declaredRoutes` (`manifest.json` `routes.length`, read beside the verifier; unreadable → FAIL) |
| `tests/contract/test_alpha_acceptance_command.py` | 16-route fixtures; stub root `Location: /projects`; parametrisation on `/projects` | `ROUTES` from the manifest; stub `/login?next=%2F`; 15 cases on `/login?next=/` (every rejecting origin case kept) |
| `scripts/manual-alpha-check.sh` 28, 453–454, 245–286, 438 | «16 cold routes»; «16 экранов»; root → `/projects`; «вход приводит на /projects» | «все cold routes из journey manifest»; «все экраны»/«список A09»; root → same-origin `/login?next=/` exactly; «вход приводит на /» |
| `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` 65, 87, 119, A09 | `307/308` на `/projects`; «все 16»; «открыт `/projects`»; 16 items | `307/308` на `/login?next=%2F`; «все cold routes из journey manifest»; «открыт `/`»; 22 items |
| `fixtures/redden*.manifest.json` | `lands_on: "/projects"`; root `redirects_to: "/projects"` | `lands_on: "/"`; no `redirects_to` |
| `web/tests/unit/session/bff-session.test.ts:356` | `'/projects'` | `'/'` |
| `web/tests/unit/api/configuration-and-cache-keys.test.ts` 176–177 | five roots | eight roots |
| `web/docs/PC01_UI_SEAM.md` §2 `/` row | «redirect to `/projects`» | the front door, a placeholder from `_pages/home`; a guest goes to `/login?next=%2F` |
## Appendix B — the data shape of each `R-66` stub, checked against the frozen contract

`R-23`'s addendum (`OWNER_RULINGS_2026-09-17.md` §3.11) asks a stub's promise to say what will be
there and asks the data shape to be written down and checked against the contract. Measured on
this branch with:

```
python3 - <<'EOF'
import json
d=json.load(open('contracts/api/v1/openapi.json'))
ops=[(m.upper(),p,o.get('operationId')) for p,v in d['paths'].items() for m,o in v.items() if m in('get','post','put','patch','delete')]
print('paths',len(d['paths']),'operations',len(ops))
for word in ['queue','norm','profile','section','optimi','setting','preset','corpus','paragraph']:
    print(f"{word!r}: {[f'{m} {p} {i}' for m,p,i in ops if word in (p+i).lower()]}")
EOF
```

```
paths 27 operations 34
'queue': []
'norm': []
'profile': ['PATCH /me updateMyProfile']
'section': []
'optimi': []
'setting': []
'preset': []
'corpus': []
'paragraph': []
```

- **«Очередь» `/queue`.** Would read: each analysis waiting to be executed — its state, its
  priority and how long it has waited. The contract has no operation over waiting work: no path
  or operation id carries `queue`; the word occurs in the document only as the registration
  conflict value `queue_full` and as the run state `queued` on a single run's status. Promise:
  with durable execution of analyses.
- **«Нормы» `/norms`.** Would read: the list of normative documents and each document's text
  paragraph by paragraph. No path or operation id carries `norm`, `corpus` or `paragraph`; the
  string `norm` occurs only inside `normal`/`normalised`, the error code
  `required_norm_unavailable` and the stage id `norm_verification`. Promise: after the
  normative corpus moves onto the stand.
- **«Настройки анализа» `/analysis-settings`.** Would read: the presets of models and stages an
  administrator keeps and an expert picks from. The contract names an analysis profile only as
  the opaque `analysis_profile_id` field on a stage record (three occurrences, all
  `$ref: AnalysisProfileId`); no operation lists, reads or edits one (`profile` matches only
  `updateMyProfile`, the account's own profile). Promise: together with the АР section in
  working order.
- **«Оптимизация разделов» `/section-optimisation`.** Would read: an optimisation across all the
  documents of one documentation section. No path or operation id carries `section` or
  `optimi`; `section` occurs only as a field of a project/document (three occurrences). Promise:
  after all sections are implemented.

Each screen shows no number and invents no row; the prepared-sections guard holds them to that.
