# W50-HOME-01 — completion report

## Result

**DONE, with open questions (§7).** Branch `agent/w50-home-01` from base `96a1653`
(= `origin/dev` = `integration/w50`, the commit carrying the integrator's rulings at the
`W50-REGISTRY-01` merge). One code commit, `f6c55ba`; this report is a docs-only commit on top
of it, and the gate measured `f6c55ba` (§2.8, §2.9).

`/` now renders a home page instead of the registry's placeholder:

- a greeting by `displayLabel` — `Здравствуйте, <displayLabel>!` in the page heading — and the
  session's roles with `entities/account`'s labels (`Роли: Эксперт, Администратор.`);
- **«Последние проекты»**: the five most recent projects from `listProjects` (`limit` 5, the
  contract's order, sliced to five as well), each linked through `routes.project` from
  `@/shared/lib`, and a link to all projects (`routes.projects()`);
- **«Сводка»**: four figures from `getDashboardSummary` — projects, documents, findings awaiting
  a decision, runs — and a link to `/dashboard`;
- **«Заявки на регистрацию»**, for a session whose roles include `admin` only: `pending_total`
  from `listRegistrations`, without a link (the registry has no `/admin/registrations` row);
- each tile has the loading, empty and error states of `shared/ui/states`; an unknown role is a
  typed fault (no label, no tile, no request).

**One source for the name and the roles: the session subject.** `requireScreen('/')` returns it
and `app/page.tsx` hands `displayLabel` and `roles` down as `HomePage`'s props (unchanged); the
page does not call `getMe`. `web/src/app/page.tsx` is not in the diff; `HomePage`'s named export
and props `{ displayLabel: string; roles: readonly Role[] }` are unchanged.

**The browser's API calls on `/`** (measured on the lane stand, §2.7, and by the unit test's
recording `fetch`, §2.6 M01b/M10):

| session | calls, as the browser makes them | journey templating |
|---|---|---|
| expert only (`['expert']`) | `GET /bff/v1/projects?limit=5`, `GET /bff/v1/dashboard` | `GET /bff/v1/projects`, `GET /bff/v1/dashboard` |
| holding `admin` (`['admin','expert']`, also `['admin']`) | the two above and `GET /bff/v1/registrations?limit=1&status=pending` | adds `GET /bff/v1/registrations` |

No `getMe`, no write, nothing else. `sign-in` (a session opening `/login`, sent to `/`) makes
exactly the same calls as `root`.

## 1. Changed files

`git diff --name-only 96a1653..f6c55ba` (15 paths; this report adds the 16th,
`docs/program/W50-HOME-01.md`):

```
web/src/_pages/home/index.ts
web/src/_pages/home/ui/home-page.module.css
web/src/_pages/home/ui/home-page.tsx
web/src/widgets/home-tiles/api/home-reads.ts
web/src/widgets/home-tiles/index.ts
web/src/widgets/home-tiles/model/read-failure.ts
web/src/widgets/home-tiles/model/recent-projects.ts
web/src/widgets/home-tiles/model/registrations-screen.ts
web/src/widgets/home-tiles/model/summary-figures.ts
web/src/widgets/home-tiles/ui/copy.ts
web/src/widgets/home-tiles/ui/home-tiles.module.css
web/src/widgets/home-tiles/ui/pending-registrations-tile.tsx
web/src/widgets/home-tiles/ui/recent-projects-tile.tsx
web/src/widgets/home-tiles/ui/summary-tile.tsx
web/tests/unit/screens/home.test.ts
```

Each path is under `web/src/_pages/home/**`, `web/src/widgets/home-*/**` or is
`web/tests/unit/screens/home.test.ts` — the grant's `HOME allowed paths`; checked by
`git diff --name-only 96a1653..HEAD | grep -v -E '^(web/src/_pages/home/|web/src/widgets/home-[^/]+/|web/tests/unit/screens/home\.test\.ts$|docs/program/W50-HOME-01\.md$)'`
— no output. `git status --porcelain -uall` is empty (§2.9).

## 2. Checks and their results

### 2.1 The premise, re-measured at the base

`git grep -n -E 'requireScreen|HomePage' 96a1653 -- web/src/app/page.tsx`:

```
96a1653:web/src/app/page.tsx:14:import { HomePage } from '@/_pages/home';
96a1653:web/src/app/page.tsx:17:import { requireScreen } from './bff/session/screen-lock';
96a1653:web/src/app/page.tsx:22:  const subject = await requireScreen('/', { params, searchParams });
96a1653:web/src/app/page.tsx:23:  return <HomePage displayLabel={subject.displayLabel} roles={subject.roles} />;
```

`git grep -n -E 'export (function|interface)|readonly (displayLabel|roles)' 96a1653 -- 'web/src/_pages/home/**'`:

```
96a1653:web/src/_pages/home/ui/home-page.tsx:19:export interface HomePageProps {
96a1653:web/src/_pages/home/ui/home-page.tsx:21:  readonly displayLabel: string;
96a1653:web/src/_pages/home/ui/home-page.tsx:23:  readonly roles: readonly Role[];
96a1653:web/src/_pages/home/ui/home-page.tsx:26:export function HomePage({ displayLabel }: HomePageProps) {
```

The route is the registry's guarded `/` and the props are the two this task keeps; both hold at
`f6c55ba` (`routes.test.ts`' `/` cases are unchanged and green).

### 2.2 Frontend suite, by file

Measured in the disposable clone of §2.6 with `npm --prefix web test -- --run
--reporter=json`, once at each commit: base `96a1653` **91 files / 1399 tests**, all passed;
head `f6c55ba` **92 files / 1426 tests**, all passed. The only file whose count changed is
`tests/unit/screens/home.test.ts` (— → 27). The worktree's own run on `f6c55ba` before the commit:
`Test Files 92 passed (92)`, `Tests 1426 passed (1426)`.

### 2.3 Lint, typecheck, whitespace

On the worktree, `f6c55ba`'s tree: `npm --prefix web run lint -- --quiet` exit 0, no output;
`npm --prefix web run typecheck` exit 0, no output; `git diff --cached --check` before the
commit — clean; `git diff --check 96a1653..HEAD` — clean.

### 2.4 The journey's static conformance

`.venv/bin/pytest tests/e2e/test_pc01_journey_conformance.py -q` on the tree of `f6c55ba`:
`78 passed in 0.69s`.

### 2.5 `next build`, the `/` row

`NEXT_PUBLIC_API_BASE_URL=/bff/v1 NEXT_PUBLIC_INSTANCE_LABEL=w50home npm --prefix web run build`
on `f6c55ba`: exit 0, `✓ Compiled successfully in 7.3s`, `Checking validity of types` passed.
The `/` row, verbatim:

```
┌ ƒ /                                                          3.36 kB         133 kB
```

The base, built the same way (same `NEXT_PUBLIC_INSTANCE_LABEL`, which is inlined into the
client bundle and moves every size) in the clone of §2.6 at `96a1653`:
`┌ ƒ /    202 B    111 kB` (`W50-REGISTRY-01` §2.5 read `201 B / 111 kB` on `17742cd` with
another label). The two route tables, every row whose first-load JS moved:

| route | base `96a1653` | head `f6c55ba` |
|---|---|---|
| `/` | `202 B / 111 kB` | `3.36 kB / 133 kB` |
| First Load JS shared by all | `102 kB` | `103 kB` |
| `/_not-found` | `127 B / 102 kB` | `132 B / 103 kB` |
| `/bff/v1/[...path]` | `127 B / 102 kB` | `132 B / 103 kB` |
| `/account/password` | `185 B / 114 kB` | `188 B / 115 kB` |
| `/dashboard` | `4.22 kB / 142 kB` | `4.23 kB / 143 kB` |
| `/knowledge-base` | `2.75 kB / 129 kB` | `2.76 kB / 130 kB` |
| `/projects/[project_uid]/documents/[document_uid]` | `1.4 kB / 134 kB` | `1.4 kB / 135 kB` |
| `/projects/[project_uid]/versions/[version_uid]/comparison` | `3.77 kB / 145 kB` | `3.77 kB / 146 kB` |

The other sixteen rows' first-load JS is unchanged; their own sizes are unchanged or move by up
to 60 B (`/review` `9.56 kB → 9.62 kB`, the largest) with no change to their code. The +1 kB is the
shared root chunks crossing a rounding step, not new code in them: read from each build's
`.next/build-manifest.json` `rootMainFiles`, their raw size is `350,676` → `350,712` bytes
(**+36 B**: the webpack runtime `3422 → 3444`, the main app chunk `554 → 560`, the two library
chunks `+1` and `+7`), and their gzip size `102,035` → `102,585` (+550 B, almost all in the
second library chunk, `45,873 → 46,407`, whose raw size moved by 7 B — the modules were renumbered
and reordered by the larger chunk graph, which compresses differently). See §4.4.

### 2.6 Mutations, each red

A disposable `git clone --shared` of the worktree at `f6c55ba`, `/root/w50home-mut`
(`web/node_modules` symlinked to the worktree's), mutated by
`/root/w50home-mut-logs/mutate.py <id>` — one exact replacement that must match once — then
`npm --prefix web test -- --run tests/unit/screens/home.test.ts tests/unit/screens/routes.test.ts
tests/guards/rendered-language.guard.test.ts`, then `git checkout -- .` and an empty
`git status --porcelain -uall` (0 lines after every case). Unmutated baseline:
`Test Files 3 passed (3)`, `Tests 83 passed (83)`. Logs: `/root/w50home-mut-logs/<id>.log`.

| id | mutation | red (verbatim) |
|---|---|---|
| M01 *(required)* | the admin tile gated on `roles.length > 0` instead of `roles.includes('admin')` — present for an expert-only session | `1 failed | 82 passed`: `an expert-only session: no tile, and listRegistrations is never requested` — `expected '<section class="am-page" data-screen=…' not to contain 'data-home-tile="registrations"'` |
| M01b *(required)* | an expert-only session requests `listRegistrations` with no tile on screen (the projects tile also calls `usePendingRegistrationTotal()`) | `2 failed | 81 passed`: `an expert-only session: …` and `decides by admin alone, and an empty role set is not admin` — `expected [ 'GET /bff/v1/dashboard', …(2) ] to deeply equal [ 'GET /bff/v1/dashboard', …(1) ]`, received `+ "GET /bff/v1/registrations?limit=1&status=pending"` |
| M02 *(required)* | an unknown role rendered as text: `labelsOf` returns `roles.map(String)` instead of the fault | `3 failed | 80 passed`: `shows the fault in place of the roles and the tiles` — `no element carries data-home-fault="closed-vocabulary": expected null not to be null`; `holds when the unknown value sits beside admin` — `expected '<section …' to contain 'data-home-fault="closed-vocabulary"'`; `shows no Latin word …` — `+ "auditor"` |
| M03 *(required)* | `overflow-wrap: anywhere` removed from `.greeting` | unit: `1 failed | 82 passed`: `sits, whole, in a heading whose own rule breaks words, in a box that may shrink` — `expected '\n  min-width: 0;\n' to match /overflow-wrap\s*:\s*anywhere/`. **Browser** (§2.7): `RED root 200 api=3 … w=1083/780` — `root: the screen scrolls sideways at the declared width. scrollWidth 1083 > innerWidth 780 (clientWidth 765), overflowing by 303 px.` |
| M04a *(required)* | no slice: the tile shows the whole cached page | `1 failed`: `shows exactly five out of a cache holding seven, newest first, …` — `expected '<section …' to contain 'data-recent-project-count="5"'` |
| M04b *(required)* | `slice(-5)`: the five oldest | `1 failed`: same case — `expected [ 'Проект номер 5', …(4) ] to deeply equal [ 'Проект номер 7', …(4) ]` |
| M05 *(required)* | the summary tile's error detail prints `summary.error.message` | `3 failed | 80 passed`: `a failed getDashboardSummary renders the typed error state, not a raw message` — `expected 'data-home-tile="summary"><h2 id="home…' not to contain 'Сырое сообщение сервера, которого на …'`; `never prints a thrown message`; `shows no Latin word …` |
| M06 | the cached count is shown before the error branch (a refused re-read keeps the earlier answer) | `3 failed | 80 passed`: `a refusal is the error state, never the count of an earlier answer` — `expected 'data-home-tile="registrations"><h2 id…' to contain 'Вам не разрешено читать заявки на рег…'`; `says so when nothing waits`; `renders every word the language guard cannot reach` |
| M07 | the verdict completeness check removed from `summaryFigures` | `2 failed | 81 passed`: `shows no partial count when a breakdown arrives incomplete` — `expected { projects: 2, documents: 5, …(2) } to be null`; `renders every word …` — `expected [ 'INCOMPLETE_SUMMARY_TITLE', …(1) ] to deeply equal []` |
| M08 | English in a constant the language guard cannot see (`NO_PENDING_REGISTRATIONS_TITLE = 'No requests are waiting.'`) | `1 failed | 82 passed`: `shows no Latin word but the two the product already prints` — `+ "No", "requests", "are", "waiting"` (state `empty, administrator`). **`rendered-language.guard.test.ts (22 tests)` stayed green** — §4.2 |
| M09 | the tile always links to `/admin/registrations` | `1 failed`: `links nowhere in W50, because the registry has no row …` — `expected 'data-home-tile="registrations"><h2 id…' not to contain '<a '` |
| M10 | `listProjects` asked for 50 instead of 5 | `3 failed | 80 passed`: the three request cases — `expected [ 'GET /bff/v1/dashboard', …(1) ] to deeply equal [ 'GET /bff/v1/dashboard', …(1) ]` |

`routes.test.ts` and the language guard stayed green under every case: none of the twelve is
visible to them, which is what `home.test.ts` is for.

### 2.7 The lane stand: two live journeys, the width reading and M03 in a browser

Lane `gate-w50home`, worktree `.local/worktrees/w50-home`, `.env` copied from the `w49-int`
worktree with exactly the lane's values changed (`FOUNDATION_INSTANCE=gate-w50home`,
`POSTGRES_PORT=56660`, `S3_API_PORT=60260`, `S3_CONSOLE_PORT=60261`, `POSTGRES_DB` and
`S3_BUCKET` renamed, both sides of `DATABASE_URL`/`S3_ENDPOINT_URL`). Ports `56660`, `60260`,
`60261` and the stand's own `56661` (API), `56662` (health), `56663` (`next start`), `56664`
(the M03 build) were checked free with `ss -ltn` before use; they sit in this lane's
`PORT_REGISTRY.md` block (`56660…`) and no row holds `56661`–`56664`.

`make up` / `make migrate` (head `0015_accounts_roles_registration`); the API
`PYTHONPATH=src .venv/bin/python infra/deploy/serve.py` with the `.env` values,
`AUDITMANAGER_PROVIDER_MODE=recorded`, a disposable `AUDITMANAGER_API_TOKEN` in a `0600` file
outside the tree, bind `127.0.0.1` (PID `3837006`, cwd the worktree); web `next start -p 56663
-H 127.0.0.1` from the §2.5 build (PID `3838435`, cwd `…/w50-home/web`). A guest `curl -sI /`:
`HTTP/1.1 307 Temporary Redirect`, `location: /login?next=%2F`.

**Accounts**, through the API (no credential appears here; passwords live in `0600` files under
`/root/w50home-stand/`):

- the migration's seeded `admin`: `POST /auth/token 200 is_default_credential=True`,
  `POST /auth/password 200`, `PATCH /me 200 profile_complete=True roles=['admin', 'expert']
  label_length=66` — names `Иван Олегович` and a **60-letter last name**, so `display_label` is
  the maximum-length name form `<60 letters> И. О.`;
- an expert-only account the way one comes to exist: `POST /registrations 201`, the
  administrator's `POST /registrations/<id>/approve 200` with `roles: ['expert']`, then
  `GET /me (expert) 200 roles=['expert'] profile_complete=True default=False
  label=Экспертова А. С.`;
- one more application left pending: `GET /registrations?status=pending&limit=1 200
  pending_total=1 items=1`.

**Journey as the administrator**, `E2E_PC01_CHROME=<chrome-for-testing 154.0.8037.92>
E2E_PC01_LOGIN=<file> E2E_PC01_PASSWORD=<file> npm --prefix web run e2e:pc01 -- --origin
http://127.0.0.1:56663 --phase all --out /root/w50home-stand/journey-admin`, exit 1, verbatim:

```
sign-in: ok at /login -- carrying 'am_session' (HttpOnly=true, SameSite=Strict) into every cold browser

write half: 3 step(s), fixture fixtures/synthetic/ar/ar_baseline.pdf

ok  create-project   api=3 {"project_uid":"prj_01M48Z3K4DKJE5EZQA3Y1V54DQ"}
ok  upload-document  api=4 {"project_uid":"prj_01M48Z3K4DKJE5EZQA3Y1V54DQ","version_uid":"ver_01M48Z4EBZHE2THDNS2794SXQ1"}
ok  start-run        api=5 {"project_uid":"prj_01M48Z3K4DKJE5EZQA3Y1V54DQ","run_id":"run_01M48Z596241SXX5VV3KAS652E"} terminal=published in 1506ms/150000ms

RED root           200  api=3 auth=0 console=0 jar=[am_session] w=765/780
ok  projects       200  api=1 auth=0 console=0 jar=[am_session] w=780/780 {"project_uid":"prj_01M48Z3K4DKJE5EZQA3Y1V54DQ"}
ok  project        200  api=1 auth=0 console=0 jar=[am_session] w=765/780 {"document_uid":"doc_01M48Z4EBY3WBXGTA8WTCGMD9S"}
ok  document       200  api=1 auth=0 console=0 jar=[am_session] w=780/780 {"version_uid":"ver_01M48Z4EBZHE2THDNS2794SXQ1"}
ok  version        200  api=2 auth=0 console=0 jar=[am_session] w=765/780 {"run_id":"run_01M48Z596241SXX5VV3KAS652E"}
ok  comparison     200  api=1 auth=0 console=0 jar=[am_session] w=780/780
ok  run            200  api=1 auth=0 console=0 jar=[am_session] w=765/780
ok  review         200  api=5 auth=0 console=0 jar=[am_session] w=765/780
RED sign-in        200  api=3 auth=0 console=0 jar=[am_session] w=765/780
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

envelope: /root/w50home-stand/journey-admin/journey.json
write steps checked: 3/3
routes checked: 22/22

e2e:pc01 FAILED -- 2 finding(s):

  - root: made 3 API call(s) no route in the manifest declares: GET /bff/v1/projects | GET /bff/v1/dashboard | GET /bff/v1/registrations
  - sign-in: made 3 API call(s) no route in the manifest declares: GET /bff/v1/projects | GET /bff/v1/dashboard | GET /bff/v1/registrations
```

The two findings are the ones the task file predicts: `root` and `sign-in` declare
`expects_api: []` until the manifest moves (§4.1). Every other route is `ok`, and both reds are
undeclared-call findings only — no width, console, status or authorization finding.

**The width reading with the maximum-length name**, from the envelope's `root` record
(`journey.json`, `records[name=root].width`), verbatim:

```
{'scrollWidth': 765, 'clientWidth': 765, 'innerWidth': 780, 'bodyScrollWidth': 765, 'offenders': [], 'offenderCount': 0}
```

`scrollWidth 765 <= innerWidth 780` at the manifest's `780 × 900`, measured by
`tests/e2e/pc01/journey/width.mjs` through `journey.mjs`, both unchanged. The rendered heading
read `Здравствуйте, Длиннофамильнаялиннофамильнаялиннофамильнаялиннофамильнаялин И. О.!`, and
the page `Роли: Эксперт, Администратор.`, the most recent project, the summary (`Проекты 1`,
`Документы 1`, `Находки, ожидающие решения 3`, `Прогоны 1`) and `Заявки на регистрацию —
Ожидают решения 1`. The exact requests (`records[name=root].exchanges`): `GET
/bff/v1/projects?limit=5 200`, `GET /bff/v1/dashboard 200`, `GET
/bff/v1/registrations?limit=1&status=pending 200`.

**Journey as the expert-only account**, read phase (`--phase read --out
/root/w50home-stand/journey-expert`), exit 1, verbatim from the walk on:

```
phase: read only -- the write half was NOT run.
RED root           200  api=2 auth=0 console=0 jar=[am_session] w=780/780
ok  projects       200  api=1 auth=0 console=0 jar=[am_session] w=780/780 {"project_uid":"prj_01M48Z3K4DKJE5EZQA3Y1V54DQ"}
…
RED sign-in        200  api=2 auth=0 console=0 jar=[am_session] w=780/780
…
routes checked: 22/22

e2e:pc01 FAILED -- 2 finding(s):

  - root: made 2 API call(s) no route in the manifest declares: GET /bff/v1/projects | GET /bff/v1/dashboard
  - sign-in: made 2 API call(s) no route in the manifest declares: GET /bff/v1/projects | GET /bff/v1/dashboard
```

(the twenty elided lines are `ok`, the same routes as above). The exact requests on `/`:
`GET /bff/v1/projects?limit=5 200`, `GET /bff/v1/dashboard 200` — **no `listRegistrations`**,
and the page shows no registration tile (`Роли: Эксперт.`).

**M03 in a browser.** The clone with M03 applied, built the same way and served by `next start
-p 56664` (PID `4066553`, cwd `/root/w50home-mut/web`) against the same API, walked as the
administrator with `--phase read`:

```
RED root           200  api=3 auth=0 console=0 jar=[am_session] w=1083/780
RED sign-in        200  api=3 auth=0 console=0 jar=[am_session] w=1083/780
…
  - root: the screen scrolls sideways at the declared width. scrollWidth 1083 > innerWidth 780 (clientWidth 765), overflowing by 303 px. 0 element(s) cross the right edge; widest: (no element crosses the edge, so the overflow is in a margin, a shadow or a scroll container rather than in a box). D-93: AppFrame is global, so this is every screen in the product and not this one.
```

So the rule is load-bearing: without it the 66-character name widens `/` by 303 px at 780 px.
The clone was restored (`git checkout -- .`, 0 lines of status) afterwards.

**Teardown.** PIDs `3838435`, `3837006` and `4066553` stopped by PID after confirming each one's
cwd; ports `56661`–`56664` released; `make down`; volumes `gate-w50home-postgres-data` and
`gate-w50home-s3-data` removed by exact name — all before the gate.

### 2.8 The full gate

Host checked first (`free -g`: 5 GB available; `pgrep -x make`: none). Run once, from the
worktree on a clean tree at `f6c55ba`, through the integrator's wrapper verbatim (the lock
`/root/projects/PDF-Analysis/.local/w50-stage-b-gate.lock`, ≥ 3 GB available, no other
`make gate`), output to `.local/worktrees/w50-home/.local/gate.log`:
`2026-10-06T16:31:23Z` → `2026-10-06T16:47:52Z` (the lock was free; no wait).

Foundation `35 passed in 24.59s`; battery `3183 passed, 6 skipped, 5 warnings, 298 subtests
passed in 907.08s (0:15:07)`; `eslint .` and `tsc --noEmit` with no output; frontend
`Test Files  92 passed (92)`, `Tests  1426 passed (1426)`; then, verbatim:

```
GATE OK: battery, foundation, frontend lint/typecheck/tests and whitespace all pass
exit=0
```

The battery's five warnings (`W50-REGISTRY-01`'s run had four) are one `starlette` deprecation,
one `pydantic` `UnsupportedFieldAttributeWarning` attributed to the first test that builds that
schema (`qa_w49/test_qa_w49_restore_collision.py`), and three `SAWarning`s in
`tests/integration/runs/harness.py`; this diff holds no Python file. `git status --porcelain
-uall` was empty before and after, and `HEAD` was `f6c55ba` throughout.

### 2.9 What the gate measured

The gate measured the code commit `f6c55ba`. The commit that adds this report changes
`docs/program/W50-HOME-01.md` only (`git diff --name-only f6c55ba..HEAD` names that one file).

## 3. New and changed contracts

No file under `contracts/**`, `web/openapi/**` or `web/src/shared/api/generated/**` changed: the
surface is still 27 paths / 34 operations / 77 schemas. No query namespace, no dependency, no
global CSS, no registry row, no manifest entry. Internal seams:

- **`HomePage` (`@/_pages/home`)** — unchanged export and props; it now renders the page above.
  It is a server component and imports `@/widgets/home-tiles` only (none of the five widgets
  `W50-LAZY-01` makes lazy).
- **`@/widgets/home-tiles`** (new widget slice): `RecentProjectsTile`, `SummaryTile`,
  `PendingRegistrationsTile({ href })`; the pure parts `recentProjects`, `RECENT_PROJECT_LIMIT`
  (5), `summaryFigures`, `classifySummaryFailure`, `classifyRegistrationsFailure`,
  `registrationsScreenLink(registry = SCREEN_REGISTRY)`, `REGISTRATIONS_SCREEN`
  (`/admin/registrations`), and `HOME_TILE_COPY`.
- **Query keys used**, all existing factories, each filled with the generated client's model
  (never the envelope): `projects.list(undefined, 5)`; `dashboard.summary()` — the same entry,
  `queryFn` answer and shape as `widgets/dashboard`'s, so every invalidation that reaches the
  dashboard reaches the home tile; `registrations.list({ status: 'pending', limit: 1 })`, whose
  page is cached whole and from which the tile `select`s `pending_total`.

## 4. Risks and known limitations

1. **The journey manifest's `root` and `sign-in` entries are not moved** (both still
   `expects_api: []`), so the live journey reports the findings of §2.7 until they move. Not
   edited, for two reasons — §7 Q1: the task file both grants the two `expects_api` entries and
   says the lane "does not edit the manifest", and the correct declaration needs `optional_api`,
   which the grant does not name. The exact entries are in §5.
2. **The language guard cannot reach three of the home page's branches.**
   `rendered-language.guard.test.ts` renders `/` only through the seed in `route-screens.ts`
   (`roles: ['expert']`) over cache states keyed for the projects screen's page of fifty. So the
   administrator's tile is never mounted by it, the recent-projects tile is pending in every
   state, and an incomplete summary is not modelled. Those branches' words are held in
   `widgets/home-tiles/ui/copy.ts` and passed as expressions, not as literal `title="…"`, so the
   guard's literal scan does not require a state it cannot render (the shape `error.tsx` took at
   Stage A, and of the existing `UNKNOWN_*_TITLE` constants). `home.test.ts` renders every
   branch, requires every constant to appear, and requires no Latin word — **M08 shows the
   guard green and this file red** over English in such a constant. Every branch the guard
   *can* reach is a literal it does judge (`Загрузка: последние проекты…`,
   `Загрузка: общую сводку…`, `Сводка появится вместе с первым проектом.`; the language suite
   is green on `f6c55ba`). An administrator's `/` seed and the home key in the guard's states
   would close it; both files are outside this grant (§7 Q2).
3. **`listRegistrations` returns at most one request to the browser.** `limit` cannot be 0 (the
   contract's minimum is 1) and the contract has no count-only read, so the one-item page is
   cached; the tile selects `pending_total` and renders nothing else (asserted: no name,
   e-mail or reason in the markup). Removing the item from the browser needs a contract change,
   which W50 forbids.
4. **`/`'s first-load JS grew from 111 kB to 133 kB** (§2.5): the placeholder became a screen
   with three client tiles. And the shared root chunks crossed a rounding step, `102 kB` →
   `103 kB`, so seven other routes read +1 kB of first-load JS — +36 B raw, +550 B gzip, from
   the chunk graph renumbering modules, not from code of theirs. `W50-LAZY-01` records the route
   table "before and after" on the Stage-A base and stops on "a route's first-load JS gets
   worse"; read against a tree that includes this branch, `/` and those seven rows will be worse
   than that baseline because of this task, not because of lazy loading. The integrator should
   take the baseline from the merged HOME, or read the comparison with this in hand (§7 Q4).
5. **The link rule is derived from the registry, so it pre-wires `W51`.** `/admin/registrations`
   has no row in W50, so the tile has no link (M09 is red over a link); the moment `W51` adds a
   row at that exact address, the tile links to it without an edit here. If `W51` registers the
   screen at another address, the tile stays linkless and nothing reddens (§7 Q3).
6. **An unknown role hides every tile.** The page keeps the greeting and shows the fault, and
   mounts no tile — so it makes no request — because the role set decides what the page asks.
   The BFF already refuses such a `getMe` answer at sign-in; this is the second line.
7. **The greeting and the roles are the subject recorded at sign-in** (refreshed by the BFF
   only after the account's own profile or password change). An administrator's later change to
   this account (W51) shows after its next sign-in; a role taken away meanwhile makes
   `listRegistrations` answer `permission_denied`, which the tile shows as its error state, never
   as the earlier count (M06).
8. **The frame's footer still says «Альфа-версия. Один проверяющий, без разделения доступа между
   учётными записями.»** under a page that now names roles (seen in both envelopes).
   `W50-SHELL-FRAME` replaces it (§3.5); outside this grant.
9. **Not in the gate:** `next build` (§2.5), the live journey and the width reading (§2.7).
   `expects_api` is seen only by the live journey (`D-108`).

## 5. Instructions to the integrator

- Merge `agent/w50-home-01` at the SHA in the hand-back into `integration/w50` after
  `W50-SHELL-UI` and before `W50-LAZY-01` (`W50-PLAN.md` §5).
- **Move the journey manifest** (`tests/e2e/pc01/journey/manifest.json`), the same block on
  both `root` and `sign-in` (and their `$comment`s, which still say the screen "calls nothing"):

  ```json
  "expects_api": [
    { "method": "GET", "path": "/projects", "operationId": "listProjects" },
    { "method": "GET", "path": "/dashboard", "operationId": "getDashboardSummary" }
  ],
  "optional_api": [
    { "method": "GET", "path": "/registrations", "operationId": "listRegistrations" }
  ]
  ```

  `listRegistrations` is made only by a session holding `admin`, and the journey asserts
  `expects_api` in both directions, so declaring it required reds an expert-only walk and
  leaving it out reds the seeded administrator's walk (both measured in §2.7).
  `journey.mjs` already matches `optional_api` by shape and the conformance test reads both
  groups (`test_pc01_journey_conformance.py:168`). If `optional_api` is not wanted, the
  alternative is to fix the journey's account to one role and declare accordingly.
- Decide §7 Q1–Q4.

## 6. Forbidden hotspots untouched

`git diff --name-only 96a1653..HEAD` contains nothing under `contracts/**`, `src/**`,
migrations, `web/src/shared/**` (including `query-keys.ts`, `shared/ui/**`,
`shared/config/**`), `web/src/app/globals.css`, `web/src/entities/**`, `web/src/_app/**`,
`web/src/app/layout.tsx`, `web/src/app/page.tsx` (in the grant, unchanged),
`web/tests/unit/screens/route-screens.ts`, `web/tests/unit/styles/**`, `web/tests/guards/**`,
`tests/e2e/pc01/journey/manifest.json`, `web/package.json`, `web/package-lock.json`, root lock
files, `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md` or `PORT_REGISTRY.md`. No ref
was pushed, merged or tagged; no deployment, secret or other lane's worktree or container was
touched; every process stopped was one this lane started, by PID.

## 7. Open questions

1. **The manifest grant contradicts itself.** `Allowed paths` grants "the `expects_api` of the
   `root` route and of the `sign-in` route", and `W50-PLAN.md` "Grants widened at
   `W50-FREEZE-01`" and `W50-REGISTRY-01` §5 say the same; `Required tests` says the report
   lists the undeclared calls and "does not edit the manifest", `Integration contract` says the
   integrator moves them, and `Handoff` says the grant does not cover them. And the correct
   declaration needs `optional_api`, which no sentence grants. I did not edit it; §5 has the
   entries. Which reading holds for later lanes?
2. **Language-guard coverage of the administrator's home** (§4.2): add an administrator's `/`
   seed (`route-screens.ts`, `W50-REGISTRY-01`'s, frozen for Stage B) and/or the home keys to
   `rendered-language.guard.test.ts`'s cache states (its fixtures are `W50-SHELL-FRAME`'s in
   Stage C) — to whom, if anyone?
3. **The registry-derived link** (§4.5): keep it, or should W50 carry no link code at all and
   `W51` add the link with its row?
4. **`/`'s route-table baseline for `W50-LAZY-01`** (§4.4).
