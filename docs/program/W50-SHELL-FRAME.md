# W50-SHELL-FRAME — completion report

## Result

**DONE, with open questions (§7).** Branch `agent/w50-shell-frame` from base `d8112cb`
(= `origin/dev`, the Stage-B merge the integrator gated `GATE OK`). Two code commits, `ca8674c`
(the frame) and `8bad678` (the instruments' administrator home, Q3/Q4); this report is a docs-only
commit on top, and the gate measured `8bad678` (§2.8, §2.9).

The frame (`web/src/_app/app-frame.tsx`, still a server component that reads no cookie):

- **Navigation from the registry only.** `Главная`, then the groups «Работа», «Знания»,
  «Система» in `R-66`'s order — and «Администрирование» when the session may open one of its
  rows (W50 has none). A row is offered exactly when `screenDecision` — the function
  `requireScreen` asks — answers `open` for the session; a group with no such row is absent. A
  guest, a default credential and an incomplete profile see no group.
- **Two layout states.** At or above 960 px the groups sit in the bar in one row (each an APG
  disclosure from `@/shared/ui`); below it they collapse into one stacked list behind a «Меню»
  disclosure with the groups as inline disclosures. The 780 px floor shows «Меню». Measured in a
  browser: no state of either layout widens the page, and the bar is one row in every state
  (§2.7).
- **The current page.** The group holding it carries `aria-current="true"`, the item that is it
  `aria-current="page"`, read from `usePathname` in the navigation island and matched against the
  registry's address shapes (a run under a project marks «Работа»).
- **The account menu, top right.** A generated avatar (initials from the subject, colour keyed by
  the e-mail) opens the APG menu button from `@/shared/ui`; the header names the account
  (`displayLabel`), its e-mail (the subject's `login`) and its roles (Эксперт, Администратор; «Роли
  не назначены.» for an empty set; a typed fault for a value the build cannot name); the items are
  Профиль `/account`, Сменить пароль `/account/password` and Выйти — a POST to
  `/bff/v1/session/end`, unchanged. A guest sees one «Вход» link and no menu.
- **No hand-written address in `_app`**, and **no browser-side API call** from the frame.
- **The footer** now reads «Альфа-версия. Изменять данные может эксперт, управлять учётными
  записями — администратор.» (proposed, §4.1), and the claims guard refuses a sentence that
  denies roles or a separation of access while the contract declares `Role`.

**Grants.** The task file at `d8112cb`, plus four message grants from the integrator
(`pdf-analysis-73`) on 2026-10-07, all recorded in `docs/program/tasks/W50-SHELL-FRAME.md` on
`integration/w50` @ `df120a8` (lines 126–147 there):

- **Q1** — the pure `screenDecision` in `shared/config/screen-registry.ts`, exported from
  `shared/config/index.ts`; `enforceScreen` maps its answers to the existing redirects;
  `screen-guard.guard.test.ts` green unedited as the proof; one reordering mutation red (M10).
- **Q2** — the granted line numbers (measured at `ead639f`) read by content.
- **Q3** — `route-screens.ts`: the `home-admin` seed and `derivedScreens()` yielding every seed of
  an address; the language guard's loaded state seeds the home page's two reads; one new coverage
  case; the census delta reported (§2.5).
- **Q4** — `screen-set.guard.test.ts`: only the per-address count, with a can-fail.

## 1. Changed files

`git diff --name-status d8112cb..8bad678` (22 paths; this report adds the 23rd,
`docs/program/W50-SHELL-FRAME.md`):

```
A	web/src/_app/account-menu.tsx
A	web/src/_app/app-frame.module.css
M	web/src/_app/app-frame.tsx
A	web/src/_app/frame-navigation.tsx
M	web/src/_app/index.ts
A	web/src/_app/navigation.ts
M	web/src/app/bff/session/screen-lock.ts
M	web/src/app/layout.tsx
M	web/src/shared/config/index.ts
M	web/src/shared/config/screen-registry.ts
M	web/tests/guards/prepared-sections.guard.test.ts
M	web/tests/guards/rendered-language.guard.test.ts
M	web/tests/guards/screen-claims-about-the-system.guard.test.ts
M	web/tests/guards/screen-set.guard.test.ts
M	web/tests/unit/screens/forms-and-pages.test.ts
M	web/tests/unit/screens/route-screens.ts
A	web/tests/unit/shell/frame-sources.test.ts
A	web/tests/unit/shell/frame.test.ts
A	web/tests/unit/shell/navigation.test.ts
A	web/tests/unit/shell/screen-decision.test.ts
A	web/tests/unit/shell/subjects.ts
M	web/tests/unit/styles/screens.ts
```

Each path is inside the grant — the task's allowed paths, the freeze and Stage-B widenings, and
Q1/Q3/Q4 — checked mechanically:

```
git diff --name-only d8112cb HEAD | grep -v -E '^(web/src/_app/[^/]+$|web/src/app/layout\.tsx$|web/tests/unit/shell/|web/tests/guards/(screen-claims-about-the-system|rendered-language|prepared-sections|screen-set)\.guard\.test\.ts$|web/tests/unit/screens/(forms-and-pages\.test|route-screens)\.ts$|web/tests/unit/styles/screens\.ts$|web/src/shared/config/(screen-registry|index)\.ts$|web/src/app/bff/session/screen-lock\.ts$|docs/program/W50-SHELL-FRAME\.md$)'
```

prints nothing. Within the line-granted files the hunks are: `forms-and-pages.test.ts` only inside
`describe('the application frame')` (lines 185–232 at the base); `prepared-sections.guard.test.ts`
only the navigation case (lines 295–302 at `d8112cb`, 248–255 at `ead639f`; the `SECTIONS` rows
untouched); `styles/screens.ts` the three `AppFrame` fixtures (lines 205, 214–217, 239–240 at
`d8112cb`) plus the imports and the frame's open-state seeds the grant names; `rendered-language`
the frame fixtures (lines 1049, 1056–1060), `error.tsx` beside `not-found`, the Q3 fixtures and
case; `screen-set` only the Q4 assertion; `route-screens.ts` only the Q3 seed and
`derivedScreens()`. `git status --porcelain -uall` is empty (§2.9).

## 2. Checks and their results

### 2.1 The premises, re-measured at the base

```
git grep -n 'href="/' d8112cb -- web/src/_app
d8112cb:web/src/_app/app-frame.tsx:50:        <Link className="am-app__brand" href="/projects">
d8112cb:web/src/_app/app-frame.tsx:69:        <Link className="am-app__nav" href="/knowledge-base">
d8112cb:web/src/_app/app-frame.tsx:82:        <Link className="am-app__nav" href="/account/password">
d8112cb:web/src/_app/app-frame.tsx:118:        <Link className="am-app__nav" href="/blocks">
d8112cb:web/src/_app/app-frame.tsx:121:        <Link className="am-app__nav" href="/optimisation">
d8112cb:web/src/_app/app-frame.tsx:124:        <Link className="am-app__nav" href="/logs">
d8112cb:web/src/_app/app-frame.tsx:127:        <Link className="am-app__nav" href="/workers">
d8112cb:web/src/_app/app-frame.tsx:136:        <Link className="am-app__nav" href="/dashboard">
d8112cb:web/src/_app/app-frame.tsx:142:         * This was an unconditional `<Link href="/login">Вход</Link>`: a signed-in reviewer
d8112cb:web/src/_app/app-frame.tsx:157:          <Link className="am-app__signin" href="/login">

git grep -n 'Один проверяющий' d8112cb -- web/src
d8112cb:web/src/_app/app-frame.tsx:205:        Альфа-версия. Один проверяющий, без разделения доступа между учётными записями.
```

The same lines as the task file's P-01/P-02 at `ead639f`. At `8bad678`: `git grep -n 'href="/'
8bad678 -- web/src/_app` prints nothing, and `rg -n "href=" web/src/_app` prints only registry
values:

```
web/src/_app/app-frame.tsx:82:        <Link className="am-app__brand" href={HOME_SCREEN}>
web/src/_app/app-frame.tsx:105:            <Link className="am-app__signin" href={SIGN_IN_SCREEN}>
web/src/_app/frame-navigation.tsx:67:      href={home.address}
```

(the groups' links are `Disclosure`'s, from `item.address`; the account menu's are `Menu`'s, from
`PROFILE_SCREEN` and `CHANGE_PASSWORD_SCREEN`). The old footer survives at `8bad678` only inside
the comment that says why it was replaced.

The access predicate was the one grant hole the premises did not show: it lived inline in
`enforceScreen`, under `web/src/app/**`, outside the grant — Q1.

### 2.2 The predicate moved (Q1)

`screenDecision(screen, subject | null)` answers `open`, `sign-in`, `change-password`,
`complete-profile` or `forbidden` — `enforceScreen`'s decisions 1–4 in their order; an unknown
role matches no row. `enforceScreen` calls it and maps each answer to the redirect it already
had; decision 5 (`/login` with a session → `/`) stays in `enforceScreen`. The proof is the guard's
own unedited suite, on the worktree after the move: `npm --prefix web test -- --run
tests/guards/screen-guard.guard.test.ts` → `Tests 30 passed (30)` (30 at `d8112cb` too, since
`W50-LAZY-01` removed its four loading cases). M10 (§2.6) reorders two decisions inside the
function and turns that suite red.

`web/tests/unit/shell/screen-decision.test.ts` (8 tests) drives the function with a fixture row
of each access level and an admin-only row, an unknown role, and the live registry — whose
role-gated set is asserted to be empty in W50 (`[]`), so the day W51 adds one, the assertion
says the menu's role filter now matters on the live registry.

### 2.3 Frontend suite, lint, typecheck, whitespace

On the worktree at `8bad678` (`/root/w50frame-logs/vitest-full-1.log`):

```
npm --prefix web test -- --run          exit=0
 Test Files  101 passed (101)
      Tests  1555 passed (1555)
npm --prefix web run typecheck          exit=0
npm --prefix web run lint -- --quiet    exit=0
git diff --check d8112cb HEAD           clean
```

The base `d8112cb` is 97 files / 1,506 tests (the integrator's Stage-B gate). Per file, the delta is 1,506 + 49 = 1,555: the four new files under
`web/tests/unit/shell/` (`frame.test.ts` 17, `navigation.test.ts` 16, `screen-decision.test.ts` 8,
`frame-sources.test.ts` 3 — 44), `rendered-language.guard.test.ts` 22 → 24 (the Q3 case and its
can-fail), `screen-claims-about-the-system.guard.test.ts` 3 → 6 (the roles half); the other
changed test files keep their counts (`screen-set.guard.test.ts` 11, `prepared-sections` 18,
`forms-and-pages` 20). The base counts were read in a disposable clone at `d8112cb` with
`npm --prefix web test -- --run <those five files>` (`74 passed`), the head's from
`--reporter=json` on the worktree (`/root/w50frame-logs/vitest-head.json`).

### 2.4 `next build`: the route table and the exact bytes

`NEXT_PUBLIC_API_BASE_URL=/bff/v1 NEXT_PUBLIC_INSTANCE_LABEL=w50frame npm --prefix web run build`
on the worktree at `8bad678`: exit 0, `✓ Compiled successfully in 13.6s`, `Checking validity of
types` passed (`/root/w50frame-logs/build-head.log`):

```
Route (app)                                                       Size  First Load JS
┌ ƒ /                                                          3.37 kB         136 kB
├ ƒ /_not-found                                                  132 B         103 kB
├ ƒ /403                                                         592 B         128 kB
├ ƒ /account                                                     212 B         119 kB
├ ƒ /account/password                                            197 B         119 kB
├ ƒ /analysis-settings                                           212 B         119 kB
├ ƒ /bff/v1/[...path]                                            132 B         103 kB
├ ƒ /blocks                                                    2.11 kB         139 kB
├ ƒ /dashboard                                                 1.67 kB         123 kB
├ ƒ /knowledge-base                                            3.05 kB         133 kB
├ ƒ /login                                                       212 B         119 kB
├ ƒ /logs                                                        212 B         119 kB
├ ƒ /norms                                                       212 B         119 kB
├ ƒ /optimisation                                                212 B         119 kB
├ ƒ /projects                                                  3.42 kB         136 kB
├ ƒ /projects/[project_uid]                                    5.73 kB         142 kB
├ ƒ /projects/[project_uid]/documents/[document_uid]            1.4 kB         138 kB
├ ƒ /projects/[project_uid]/runs/[run_id]                      4.13 kB         134 kB
├ ƒ /projects/[project_uid]/runs/[run_id]/review                 12 kB         149 kB
├ ƒ /projects/[project_uid]/versions/[version_uid]             6.24 kB         150 kB
├ ƒ /projects/[project_uid]/versions/[version_uid]/comparison  2.04 kB         138 kB
├ ƒ /queue                                                       212 B         119 kB
├ ƒ /section-optimisation                                        212 B         119 kB
└ ƒ /workers                                                     212 B         119 kB
+ First Load JS shared by all                                   103 kB
```

**Against the base, in exact bytes** (`W50-LAZY-01`'s method: `/root/w50lazy-logs/first-load.mjs`
sums the gzip-9 size of every `.js` file a route's entry lists in `app-build-manifest.json`), the
base built the same way, label included, in a disposable clone at `d8112cb`
(`/root/w50frame-logs/fl-base-d8112cb.tsv`, `fl-head-worktree.tsv`):

| route | base `d8112cb` | head `8bad678` | Δ bytes |
|---|---:|---:|---:|
| `/projects/[project_uid]` | 141,402 | 142,163 | +761 |
| `/projects/[project_uid]/versions/[version_uid]` | 148,997 | 149,753 | +756 |
| `/blocks`, `/projects/[project_uid]/versions/[version_uid]/comparison` | 137,805 / 137,731 | 138,547 / 138,473 | +742 |
| `/projects/[project_uid]/documents/[document_uid]`, `/projects/[project_uid]/runs/[run_id]`, `/projects` | 137,093 / 133,281 / 135,401 | 137,834 / 134,022 / 136,142 | +741 |
| `/`, `/dashboard` | 135,349 / 122,649 | 136,089 / 123,389 | +740 |
| `/knowledge-base`, `/projects/[project_uid]/runs/[run_id]/review` | 132,206 / 148,287 | 132,944 / 149,025 | +738 |
| `/403` | 126,874 | 127,593 | +719 |
| `/account`, `/account/password`, `/analysis-settings`, `/login`, `/logs`, `/norms`, `/optimisation`, `/queue`, `/section-optimisation`, `/workers` | 118,319 (118,304) | 119,035 (119,020) | +716 |
| `/_not-found`, `/bff/v1/[...path]` | 103,405 | 103,400 | −5 |

Every page route grows by 716…761 gzip bytes: the frame is in the root layout, and its client
islands (the navigation, `Menu`, `Disclosure`, the avatar) now load on every page. That is inside
`W50-PLAN.md` §3.4's amended bound (≤ 1.5 kB per route), which §7 makes a stop for any route.
The rounded table reads +7 kB against `W50-LAZY-01`'s, which was taken before `W50-SHELL-UI` and
`W50-HOME-01` merged; against `d8112cb` it is +1 kB per row.

### 2.5 The census (Q3: the delta)

`/root/w50lazy-logs/census-counts.probe.test.ts` (the probe `W50-LAZY-01`'s report quotes
whole), copied into `web/tests/guards/`, run, deleted:

| tree | screens | pairs (light / dark) |
|---|---:|---:|
| base `d8112cb` (disposable clone) | 86 | 172 / 172 |
| `ca8674c` (the frame, its fixtures, three open-state seeds) | 89 | 171 / 171 |
| `8bad678` (+ the `home-admin` seed) | 90 | 171 / 171 |

**+4 screens:** the account menu open and the navigation drawn open twice (`/` and `/blocks`
current), and the administrator's home. **−1 pair:** a probe that dumps the light palette's keys
on both trees (`/root/w50frame-logs/census-keys.probe.test.ts`) differs in exactly one,
`text|--am-accent|--am-paper|hover|-`, and its only site at the base was
`AppFrame with an open session header.am-app__bar > form > button.am-app__signin {:hover}` — the
old bar's `Выйти` button, which no longer exists (`Выйти` is a `Menu` item, measured as
`li.am-menu__entry > form.am-menu__form > button.am-menu__item`). No element the product still
renders lost its measurement; `W50-PLAN.md` §7 nevertheless lists "the census shrinks" as a stop,
so it is §7 Q1. The `home-admin` seed adds a screen and no pair: cold, the administrator's tile is
a loading state whose classes other screens already wear. `W50-LAZY-01`'s floor (80 / 150 / 150)
holds.

The census reads `@media` blocks flattened, so it always sees the stacked state; the one-row
state's colours are the `Disclosure` rules `W50-SHELL-UI` seeded in the bar.

### 2.6 Mutations, each red

A disposable `git clone --shared` at `8bad678`, `/root/w50frame-mut` (`web/node_modules`
symlinked to the worktree's), driven by `/root/w50frame-mut-logs/run.sh <id> <files>`: one
mutation by `mutate.py <id>` (every replacement must match exactly once; M11 drops one whole
block), run the named files, `git checkout -- . && git clean -fdq -e web/node_modules`, and an
empty status (`restored clean` after every case). Unmutated baseline over the nine files involved:
`Test Files 9 passed (9)`, `Tests 142 passed (142)`. Logs: `/root/w50frame-mut-logs/<id>.log`.

| id | mutation | files run | red (verbatim) |
|---|---|---|---|
| M01 *(required: `roles: []` shows no admin group)* | the menu ignores `screenDecision`: every `inMenu` row for everyone | navigation, frame | `7 failed \| 26 passed`: `the administration group, for a session without admin — roles [] included`; a guest: `expected [ '/', '/', '/projects', …(21) ] to deeply equal [ '/', '/login' ]`; `expected { home: { address: '/', …(1) }, …(1) } to deeply equal { home: null, groups: [] }` |
| M02 *(required: a group with no openable row is absent)* | every group pushed, an empty one as an empty heading | navigation, frame | `9 failed \| 24 passed`: `expected { home: null, …(1) } to deeply equal { home: null, groups: [] }`; `expected '<div class="am-app"><header class="am…' not to contain '<nav'`; the live registry is no longer `R-66` (an empty «Администрирование» appears) |
| M03a *(required)* | `/optimisation` back in the menu (`group: 'work', inMenu: true`) | navigation, frame, prepared-sections | `5 failed \| 46 passed`: `expected [ '/projects', '/dashboard', …(9) ] to not include '/optimisation'`; the `R-66` outline; prepared-sections' navigation case |
| M03b *(required)* | an `R-66` stub missing from its group (`/queue` `inMenu: false`) | navigation | `2 failed \| 14 passed`: `expected [ 'Главная /', …(3) ] to deeply equal [ 'Главная /', …(3) ]` (the «Система» row lacks «Очередь») |
| M04 *(required: the long header does not widen the frame)* | the header's own `overflow-wrap: anywhere` removed | frame | `1 failed \| 16 passed`: `expected '\n  margin: 0;\n  min-width: 0;\n' to match /overflow-wrap\s*:\s*anywhere/`. **Browser (M04b, §2.7):** with the header set to `white-space: nowrap`, the account menu open at 780×900 reads `scrollWidth=2417 innerWidth=780` |
| M05 *(required: the stacked state has no horizontal overflow)* | the breakpoint no longer hides the one-row state (both shown at the floor) | frame | `1 failed \| 16 passed`: `expected '\n  .stacked {\n    display: block;\n…' to match /\.row\s*\{\s*display\s*:\s*none;?\s*\}/` |
| M06 *(required)* | a literal `href="/"` on the brand in `_app` | frame-sources | `1 failed \| 2 passed`: `an address in _app is written by hand; take it from the screen registry (@/shared/config) or, for the session door, from @/features/sign-in: expected [ 'app-frame.tsx:82: /' ] to deeply equal []` |
| M07 *(required: `Выйти` as a link is red)* | `Выйти` as a `link` item to the session door (a GET) | frame | `3 failed \| 14 passed`: the POST form is missing; `эксперт@пример.испытание links /bff/v1/session/end: expected false to be true` (a link to a non-screen address) |
| M08 *(required: a `div` trigger is red)* | the account menu replaced by a `div role="button" aria-haspopup="menu"` trigger | frame | `8 failed \| 9 passed`: `opens from a button holding the avatar, named by the account, never from a div`; the header and the items are gone with the menu |
| M09 *(required: the old footer is red in the claims guard)* | `FRAME_FOOTER` back to «Альфа-версия. Один проверяющий, без разделения доступа между учётными записями.» | claims guard, frame, forms-and-pages | `4 failed \| 39 passed`: `These rendered states deny roles or a separation of access, while components.schemas.Role declares a role set. …: expected [ { screen: 'AppFrame', …(1)`; the frame's and forms-and-pages' footer cases |
| M10 *(Q1)* | two decisions reordered inside `screenDecision` (the profile before the password) | **screen-guard (unedited)**, screen-decision | `4 failed \| 34 passed`: screen-guard `comes before the profile: a default credential with no profile changes the password first` — `expected '/account' to be '/account/password'`; and the function's own order cases |
| M11 *(Q3)* | the `home-admin` seed dropped (the whole block, 13 lines) | rendered-language, screen-set | `1 failed \| 34 passed`: `no state renders this home-page branch: the \`home-admin\` seed in route-screens.ts or the loaded state's home keys are gone, and the language guard no longer reads it: expected [ 'data-home-tile="registrations"' ] to deeply equal []` — and screen-set stays green (every address is still rendered) |
| M12 | the current page never marked (`currentScreen` always `null`) | navigation | `4 failed \| 12 passed`: `expected [] to deeply equal [ 'Знания', 'Меню', 'Знания' ]`; `expected [] to deeply equal [ '/', '/' ]` |
| M13 | an unknown role named in the header instead of the fault | frame | `1 failed \| 16 passed`: the typed fault `data-account-fault="closed-vocabulary"` is missing |

Q4's can-fail is a case of its own rather than a mutation: `screen-set.guard.test.ts` asserts that
the same screens with every seed of `/` removed render one address fewer.

### 2.7 The lane stand: widths, the keyboard, the current page, the live journey

**Stand.** Lane `gate-w50frame`, worktree `.local/worktrees/w50-frame`, `.env` copied from the
`w49-int` worktree with exactly the lane's values (`FOUNDATION_INSTANCE=gate-w50frame`,
`POSTGRES_PORT=56680`, `S3_API_PORT=60280`, `S3_CONSOLE_PORT=60281`,
`POSTGRES_DB=auditmanager_w50frame`, `S3_BUCKET=auditmanager-w50frame`, both sides of
`DATABASE_URL`/`S3_ENDPOINT_URL`). Ports checked free with `ss -ltn` before use: `56680`,
`60280`, `60281` (the lane's `PORT_REGISTRY.md` row), `56681` (API), `56682` (health), `56683`
(`next start`, head), `56684` (`next start`, the M04b mutant). `make up` and `make migrate` exit 0
(head `0015_accounts_roles_registration`). API: `PYTHONPATH=src .venv/bin/python
infra/deploy/serve.py`, `AUDITMANAGER_PROVIDER_MODE=recorded`, a disposable API token in a `0600`
file outside the tree, bound to `127.0.0.1` (PID 876167, cwd the worktree); web: `next start -p
56683 -H 127.0.0.1` over the §2.4 build (PID 876541, cwd `…/w50-frame/web`).

**Account — the worst case of the task's width rule.** The migration's seeded `admin`, through the
API (the stand's API serves at the root path): `POST /auth/token 200 is_default_credential=True`,
`POST /auth/password 200`, `POST /auth/token 200 is_default_credential=False`, `PATCH /me 200` with
a **60-letter last name** and a **254-character e-mail** invented under `example.test`
(`'a'*64@'b'*63.'c'*63.'d'*48.example.test`) → `profile_complete: True`, `roles: ['admin',
'expert']`, `display_label` of **66 characters** (`Ж…Ж И. О.`). The password lives in a `0600`
file outside the tree; no credential, cookie or session id appears here. Below, the 60-letter
name is abbreviated `Ж…`.

**Widths, every menu state** — `/root/w50frame-logs/frame-pass.mjs --mode width` (outside the
tree): one cold Chrome (chrome-for-testing 154.0.8037.92) over CDP, signed in through the real
`/login` form, the viewport set before navigation, each state opened by clicking its control and
read with the journey's own, unchanged `MEASUREMENT` (`tests/e2e/pc01/journey/width.mjs`);
`barRows` counts the bar's visual rows (a child starts a new row only below the bottom of every
child of the row before it). At the **780 × 900 floor** (stacked):

```
signed in; landed on /; viewport 780x900
closed                             scrollWidth=765 innerWidth=780 clientWidth=765 offenders=0 barRows=1 open=[]
layout: row display=none, stacked display=block
«Меню» open                        scrollWidth=765 innerWidth=780 clientWidth=765 offenders=0 barRows=1 open=[Меню]
«Меню» open, «Работа» open         scrollWidth=765 innerWidth=780 clientWidth=765 offenders=0 barRows=1 open=[Меню | Работа]
«Меню» open, «Знания» open         scrollWidth=765 innerWidth=780 clientWidth=765 offenders=0 barRows=1 open=[Меню | Знания]
«Меню» open, «Система» open        scrollWidth=765 innerWidth=780 clientWidth=765 offenders=0 barRows=1 open=[Меню | Система]
account menu open                  scrollWidth=765 innerWidth=780 clientWidth=765 offenders=0 barRows=1 open=[Учётная запись: Ж… И. О.]
```

At **960 × 900** (the breakpoint; one row):

```
signed in; landed on /; viewport 960x900
closed                             scrollWidth=960 innerWidth=960 clientWidth=960 offenders=0 barRows=1 open=[]
layout: row display=flex, stacked display=none
«Работа» open                      scrollWidth=960 innerWidth=960 clientWidth=960 offenders=0 barRows=1 open=[Работа]
«Знания» open                      scrollWidth=960 innerWidth=960 clientWidth=960 offenders=0 barRows=1 open=[Знания]
«Система» open                     scrollWidth=960 innerWidth=960 clientWidth=960 offenders=0 barRows=1 open=[Система]
account menu open                  scrollWidth=960 innerWidth=960 clientWidth=960 offenders=0 barRows=1 open=[Учётная запись: Ж… И. О.]
```

At **1280 × 900** (one row):

```
signed in; landed on /; viewport 1280x900
closed                             scrollWidth=1280 innerWidth=1280 clientWidth=1280 offenders=0 barRows=1 open=[]
layout: row display=flex, stacked display=none
«Работа» open                      scrollWidth=1280 innerWidth=1280 clientWidth=1280 offenders=0 barRows=1 open=[Работа]
«Знания» open                      scrollWidth=1280 innerWidth=1280 clientWidth=1280 offenders=0 barRows=1 open=[Знания]
«Система» open                     scrollWidth=1280 innerWidth=1280 clientWidth=1280 offenders=0 barRows=1 open=[Система]
account menu open                  scrollWidth=1280 innerWidth=1280 clientWidth=1280 offenders=0 barRows=1 open=[Учётная запись: Ж… И. О.]
```

In every state at every width `scrollWidth <= innerWidth` (765 at 780 is the page less its
scrollbar, `clientWidth`), no element crosses the right edge, and the bar is one row.

**The reading can fail (M04b).** The clone with the header's rule set to `white-space: nowrap;
overflow-wrap: normal`, built the same way and served on `56684` (PID 970039, cwd
`/root/w50frame-mut/web`), against the same API, same command:

```
signed in; landed on /; viewport 780x900
closed                             scrollWidth=765 innerWidth=780 clientWidth=765 offenders=0 barRows=1 open=[]
layout: row display=none, stacked display=block
«Меню» open                        scrollWidth=765 innerWidth=780 clientWidth=765 offenders=0 barRows=1 open=[Меню]
«Меню» open, «Работа» open         scrollWidth=765 innerWidth=780 clientWidth=765 offenders=0 barRows=1 open=[Меню | Работа]
«Меню» open, «Знания» open         scrollWidth=765 innerWidth=780 clientWidth=765 offenders=0 barRows=1 open=[Меню | Знания]
«Меню» open, «Система» open        scrollWidth=765 innerWidth=780 clientWidth=765 offenders=0 barRows=1 open=[Меню | Система]
account menu open                  scrollWidth=2417 innerWidth=780 clientWidth=765 offenders=0 barRows=1 open=[Учётная запись: Ж… И. О.]
```

The open account menu widens the page to 2,417 px; no element box crosses the edge because it is
the header's text that runs out of its box, which the instrument reports the same way the
journey does. The mutant server was stopped by PID after its cwd was confirmed, and the clone
restored clean.

**Keyboard only** — `frame-pass.mjs --mode keyboard`: Tab from the top of the page, then each
control driven with `Input.dispatchKeyEvent` (Enter, Space, Escape, the arrows, Home, End) and one
outside click; after every step, which element holds focus and which disclosure or menu is open,
read from the page. At **780 × 900** (stacked):

```
signed in; landed on /; viewport 780x900
start                                    focus=body open=[]
Tab #1                                   focus=a "AuditManager" open=[]
Tab #2                                   focus=button "Меню" open=[]
  Enter on «Меню»                        focus=button "Меню" open=[Меню]
  Tab into the list                      focus=a "Главная" open=[Меню]
  Tab                                    focus=button "Работа" open=[Меню]
  Space on the focused group             focus=button "Работа" open=[Меню | Работа]
  Escape (one level)                     focus=button "Работа" open=[Меню]
  Escape (second level)                  focus=button "Меню" open=[]
Tab #3                                   focus=button "Светлая" open=[]
Tab #4                                   focus=button "Тёмная" open=[]
Tab #5                                   focus=button "Учётная запись: Ж… И. О." open=[]
  ArrowDown opens on the first item      focus=a[role=menuitem] "Профиль" open=[Учётная запись: Ж… И. О.]
  ArrowDown                              focus=a[role=menuitem] "Сменить пароль" open=[Учётная запись: Ж… И. О.]
  End                                    focus=button[role=menuitem] "Выйти" open=[Учётная запись: Ж… И. О.]
  Home                                   focus=a[role=menuitem] "Профиль" open=[Учётная запись: Ж… И. О.]
  ArrowUp wraps to the last              focus=button[role=menuitem] "Выйти" open=[Учётная запись: Ж… И. О.]
  Escape returns focus to the trigger    focus=button "Учётная запись: Ж… И. О." open=[]
  Enter opens                            focus=a[role=menuitem] "Профиль" open=[Учётная запись: Ж… И. О.]
  click outside closes                   focus=body open=[]
```

At **1280 × 900** (one row):

```
signed in; landed on /; viewport 1280x900
start                                    focus=body open=[]
Tab #1                                   focus=a "AuditManager" open=[]
Tab #2                                   focus=a "Главная" open=[]
Tab #3                                   focus=button "Работа" open=[]
  Enter on «Работа» opens                focus=button "Работа" open=[Работа]
  Tab into its first link                focus=a "Проекты" open=[Работа]
  Escape closes, focus back on the button focus=button "Работа" open=[]
  Space opens                            focus=button "Работа" open=[Работа]
  click outside closes                   focus=body open=[]
  (focus put back on «Работа»)           focus=button "Работа" open=[]
Tab #4                                   focus=button "Знания" open=[]
Tab #5                                   focus=button "Система" open=[]
Tab #6                                   focus=button "Светлая" open=[]
Tab #7                                   focus=button "Тёмная" open=[]
Tab #8                                   focus=button "Учётная запись: Ж… И. О." open=[]
  ArrowDown opens on the first item      focus=a[role=menuitem] "Профиль" open=[Учётная запись: Ж… И. О.]
  ArrowDown                              focus=a[role=menuitem] "Сменить пароль" open=[Учётная запись: Ж… И. О.]
  End                                    focus=button[role=menuitem] "Выйти" open=[Учётная запись: Ж… И. О.]
  Home                                   focus=a[role=menuitem] "Профиль" open=[Учётная запись: Ж… И. О.]
  ArrowUp wraps to the last              focus=button[role=menuitem] "Выйти" open=[Учётная запись: Ж… И. О.]
  Escape returns focus to the trigger    focus=button "Учётная запись: Ж… И. О." open=[]
  Enter opens                            focus=a[role=menuitem] "Профиль" open=[Учётная запись: Ж… И. О.]
  click outside closes                   focus=body open=[]
```

Each behaviour the task names holds: Tab reaches each group (and «Меню»); Enter and Space open a
disclosure; Escape closes one level per press and returns focus to its button; the account menu
opens on its first item with ArrowDown, walks with the arrows, Home and End and wraps; Escape
returns focus to the avatar button; an outside click closes. The theme control sits between the
navigation and the avatar in the tab order.

**The current page, in the browser** — `frame-pass.mjs --mode current` at 1280 × 900, one path
after another in the same signed-in browser:

```
signed in; landed on /; viewport 1280x900
/                                                                      current group=[] current page links=[/ | / (in a closed panel)]
/blocks                                                                current group=[Знания] current page links=[/blocks (in a closed panel) | /blocks (in a closed panel)]
/projects/prj_01M4ANXYNFXZ8486VA4AYD0S2P                               current group=[Работа | АР Архитектурные решения] current page links=[]
/optimisation                                                          current group=[] current page links=[]
```

`/` marks `Главная` (its link in the one-row state and its copy in the closed «Меню» panel);
`/blocks` marks «Знания» and «Блоки»; a project page marks «Работа» and no item (the second
`aria-current="true"` there is the project page's own section control, not the frame's); the
hidden `/optimisation` marks nothing.

**The live journey** — `E2E_PC01_CHROME=<chrome-for-testing 154.0.8037.92>
E2E_PC01_LOGIN=<file> E2E_PC01_PASSWORD=<file> npm --prefix web run e2e:pc01 -- --origin
http://127.0.0.1:56683 --phase all --out /root/w50frame-stand/journey-head`, signed in as that
complete-profile account with a changed password, exit 0, verbatim:

```
sign-in: ok at /login -- carrying 'am_session' (HttpOnly=true, SameSite=Strict) into every cold browser
write half: 3 step(s), fixture fixtures/synthetic/ar/ar_baseline.pdf
ok  create-project   api=3 {"project_uid":"prj_01M4ANXYNFXZ8486VA4AYD0S2P"}
ok  upload-document  api=4 {"project_uid":"prj_01M4ANXYNFXZ8486VA4AYD0S2P","version_uid":"ver_01M4ANYT12FFSQJQM9FB6VTCP1"}
ok  start-run        api=5 {"project_uid":"prj_01M4ANXYNFXZ8486VA4AYD0S2P","run_id":"run_01M4ANZMQNP56SWJ6NWDJRP00H"} terminal=published in 1506ms/150000ms
ok  root           200  api=3 auth=0 console=0 jar=[am_session] w=765/780
ok  projects       200  api=1 auth=0 console=0 jar=[am_session] w=780/780 {"project_uid":"prj_01M4ANXYNFXZ8486VA4AYD0S2P"}
ok  project        200  api=1 auth=0 console=0 jar=[am_session] w=765/780 {"document_uid":"doc_01M4ANYT0Z217XE2F1XNVY7BQ6"}
ok  document       200  api=1 auth=0 console=0 jar=[am_session] w=780/780 {"version_uid":"ver_01M4ANYT12FFSQJQM9FB6VTCP1"}
ok  version        200  api=2 auth=0 console=0 jar=[am_session] w=765/780 {"run_id":"run_01M4ANZMQNP56SWJ6NWDJRP00H"}
ok  comparison     200  api=1 auth=0 console=0 jar=[am_session] w=780/780
ok  run            200  api=1 auth=0 console=0 jar=[am_session] w=765/780
ok  review         200  api=5 auth=0 console=0 jar=[am_session] w=765/780
ok  sign-in        200  api=3 auth=0 console=0 jar=[am_session] w=765/780
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
envelope: /root/w50frame-stand/journey-head/journey.json
write steps checked: 3/3
routes checked: 22/22
e2e:pc01 OK
exit=0
```

Every route `ok` at 780 × 900 with no width, console, authorization or undeclared-call finding:
the frame adds no API call (`root` and `sign-in` make the home page's three, which the manifest
declares since the Stage-B merge).

**Teardown of the stand**, before the gate: web PID 876541 and API PID 876167 stopped by PID after
confirming each cwd; ports `56681`–`56684` closed; `make down` exit 0; volumes
`gate-w50frame-postgres-data` and `gate-w50frame-s3-data` removed by exact name.

### 2.8 The full gate

Run from the worktree on a clean tree at `8bad678`, through the integrator's Stage-B wrapper
(the lock `/root/projects/PDF-Analysis/.local/w50-stage-b-gate.lock`, ≥ 3 GB available, no other
`make gate` or `make alpha-acceptance`), output to `.local/worktrees/w50-frame/.local/gate.log`.

**Run 1 — VOID.** `08:12:20Z` → `08:39:46Z`, `exit=2`: foundation `35 passed`; battery `1 failed,
3170 passed, 6 skipped, 7 warnings, 12 errors, 298 subtests passed in 1564.84s (0:26:04)`, every
failure and error in `tests/integration/exports/*` and every one
`StorageUnavailableError: dependency_unavailable: Object storage is unavailable. Nothing was
created. [dependency='blob_storage']`. The lane's containers had been recreated at `08:36:18Z`,
mid-battery (`docker inspect`: `restarts=0`, `oom=false` — a test recreated the stack), with the
host's load at 20–28 from other projects' runs, and the export tests met a MinIO that was not
ready. Void under the lane's rule (`StorageUnavailableError` under load), and shown so: on the same
lane right after, `pytest -c pyproject.toml --rootdir=. -q tests/integration/exports` →
`43 passed in 73.67s`. This diff holds no Python and no infrastructure file. Log:
`/root/w50frame-logs/gate-run1-VOID.log`.

**Run 2 — `GATE OK`.** The lane brought down and its volumes removed by exact name, then the same
wrapper with one more wait, load1 ≤ 12:

```
gate start 2026-10-07T08:45:16Z head=8bad67883d7b91b0206b6bbbada6e6eb613426ce avail=4 load=10.66 20.42 19.99
```

Foundation `35 passed in 29.52s`; battery `3183 passed, 6 skipped, 6 warnings, 298 subtests passed
in 2437.66s (0:40:37)` (the host's load rose to 34 during it); `eslint .` and `tsc --noEmit` with no
output; frontend `Test Files  101 passed (101)`, `Tests  1555 passed (1555)`; then, verbatim:

```
GATE OK: battery, foundation, frontend lint/typecheck/tests and whitespace all pass
gate end 2026-10-07T09:28:24Z
exit=0
```

The six warnings are one `starlette` `DeprecationWarning`, two `pydantic`
`UnsupportedFieldAttributeWarning`s attributed to the first tests that build that schema (an
order effect; `W50-HOME-01`'s run had one), and three `SAWarning`s in
`tests/integration/runs/harness.py`. `git status --porcelain -uall` was empty before and after,
and `HEAD` was `8bad678` throughout. Log: `/root/w50frame-logs/gate-run2-OK.log`.

The integrator (`pdf-analysis-67`) accepted run 2 and noted for the record the owner's ruling of
2026-10-07 (to be recorded as `R-70` at this merge) that limits the full gate to scheduled windows,
`origin/main` publications and changes to contracts, migrations, infrastructure, the `Makefile`,
locks, the composition root or shared test fixtures; this lane's full gate stands as its evidence.

### 2.9 What the gate measured

The gate measured the code commit `8bad678`. The commit that adds this report changes
`docs/program/W50-SHELL-FRAME.md` only (`git diff --name-only 8bad678..HEAD` names that one file).
On the tree carrying this report, the battery's tests that read `docs/`, run the gate's way
(`.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q tests/contract/program
tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py
tests/contract/api_v1/test_openapi_conformance.py tests/contract/api_v1/test_finding_detail_composition.py
tests/contract/domain_p02/test_openapi_document.py tests/e2e/test_pc01_journey_conformance.py`):
`311 passed`, before the commit and again on it.

### 2.10 Cleanup

After the gate: `make down` exit 0 (`FOUNDATION_INSTANCE=gate-w50frame`; containers
`gate-w50frame-{postgres,s3,s3-init}-1` and network `gate-w50frame-net` gone); volumes
`gate-w50frame-postgres-data` and `gate-w50frame-s3-data` removed by exact name; the disposable
clones `/root/w50frame-base` and `/root/w50frame-mut` removed after confirming each was clean (the
worktree's `web/node_modules` intact); the stand's token, password and login files deleted after
confirming neither secret value appears in any kept artefact; ports `56680`–`56689`, `60280`,
`60281` free; no lane process left. Every process stopped in this lane was stopped by PID after its
cwd was confirmed (§2.7). Kept for the record: `/root/w50frame-logs/` (build logs, byte tables,
census probes and key lists, browser readings, the driver, both gate logs),
`/root/w50frame-mut-logs/` (driver and per-mutation logs), `/root/w50frame-stand/` (start scripts,
the journey envelope and log).

## 3. New and changed contracts

No file under `contracts/**`, `web/openapi/**` or `web/src/shared/api/generated/**` changed: still
27 paths / 34 operations / 77 schemas, error catalog 23, migration head
`0015_accounts_roles_registration`. No dependency, no global CSS, no registry row, no manifest
entry. Internal seams:

- **`screenDecision` and its types** (`ScreenDecision`, `ScreenDecisionSubject`) in
  `@/shared/config` — the one answer to "may this session open this screen". `requireScreen`
  and the frame's menu both ask it; nothing else decides.
- **`AppFrame({ children, session })`** now takes the whole subject: `AppFrameSession` =
  `{ login, displayLabel, initials, roles, isDefaultCredential, profileComplete }` (exported
  from `@/_app` with `FRAME_FOOTER`). `app/layout.tsx` passes those six fields by name and never
  the register's instants.
- **`_app/navigation.ts`**: `buildNavigation(subject, registry?)`, `currentScreen(pathname,
  registry?)`, `MENU_GROUPS` (`work`, `knowledge`, `system`, `admin`) and their labels — the only
  thing the frame adds to the registry is the groups' names and order.
- **`_app/frame-navigation.tsx`**: the `FrameNavigation` island and its pure
  `FrameNavigationView({ navigation, pathname, disclosure? })`; `disclosure` lets an instrument
  that cannot click draw the disclosures open (the census and the language guard do).
- **`_app/account-menu.tsx`**: `AccountMenu` and `accountMenuProps(session)` — the instruments
  render the menu open from the very props the bar uses.
- **Tests' seams:** `derivedScreens()` yields one entry per SEED (Q3); `screen-set`'s
  relationship moved from "exactly one screen per address" to "every non-excused address
  rendered at least once, names unique" (Q4).

## 4. Risks and known limitations

1. **The footer sentence is proposed, not ruled.** «Альфа-версия. Изменять данные может эксперт,
   управлять учётными записями — администратор.» Its evidence: `R-60` ("Product mutations …
   require `expert`. Account and request management requires `admin`") and the contract's own
   `Role` description ("`expert` makes product changes … `admin` manages accounts and registration
   requests. Reading product data needs no role"). It says nothing about reading, which needs no
   role. The owner may want other words (§7 Q2).
2. **The header for `roles: []`** says «Роли не назначены.» — the home page's sentence for the
   same fact (§7 Q3). The navigation for such a session is the full `R-66` menu, because no W50
   row is role-gated and `requireScreen` opens every row to it.
3. **«Сменить пароль»** is the task's wording for the item; the registry's label for
   `/account/password` is «Смена пароля» (the item takes its address from the registry, its words
   from the task) (§7 Q4). «Профиль» is the registry's label.
4. **An unknown role** shows the typed fault in the account header and leaves the menu as
   `screenDecision` answers it: rows open to `any` stay offered, as the guard opens them.
5. **The menu hides what a session cannot open; that is presentation.** The guard and the API
   refuse on their own evidence; a stale subject shows a menu its holder cannot use.
6. **The administration group is never rendered on the live registry in W50** — it has no row.
   It is exercised on a fixture registry with an admin-only row (`navigation.test.ts`), and
   `screen-decision.test.ts` asserts the live role-gated set is empty so W51 sees the moment it
   changes.
7. **The census measures the stacked state only** (flattened `@media`, §2.5); the one-row state
   is covered by `W50-SHELL-UI`'s bar seeds and by the browser readings of §2.7.
8. **The islands are not exercised in a DOM by the unit suite** (node environment): keyboard,
   focus and outside click are walked in the browser on the lane stand (§2.7), with the
   primitives' own transition tests behind them.
9. **The breakpoint is 960 px, chosen by measurement**: at 960 the one-row bar holds every state
   in one row with the longest label (§2.7); below it, «Меню». The 780 px floor therefore never
   shows the one-row state.
10. **First-load JS +0.7 kB on every page route** (§2.4) — the frame's islands; inside the
    amended bound.
11. **Not in the gate:** `next build`, the browser readings and the live journey (`D-108`).

## 5. Instructions to the integrator

- Merge `agent/w50-shell-frame` into `integration/w50` (Stage C); it is based on `d8112cb`. The
  Q1–Q4 grants are already in the task file at `df120a8`; `df120a8` changes no path this branch
  touches (AGENTS/README, the hotfix line, release records), so no overlap is expected.
- `W50-QA-01` and the judges should walk the menus in a browser at 780 and 1280 px; the driver
  used here is `/root/w50frame-logs/frame-pass.mjs` (outside the tree).
- §7's questions are yours or the owner's; nothing in this branch decides them silently.
- For `W50-FIX` (optional): raise `lazy-boundary.guard.test.ts`' census floor to the merged
  count, as `W50-LAZY-01` suggested; it reads 90 / 171 / 171 here.

## 6. Forbidden hotspots untouched

`git diff --name-only d8112cb HEAD | grep -E '^web/src/_app/providers\.tsx$|globals\.css|^contracts/|^src/|package|FRONTEND_LOCK|^tests/e2e/'`
prints nothing: no composition root, no global CSS, no contract, no backend, no lock or package
file, no journey instrument (the browser driver lives outside the tree and imports
`tests/e2e/pc01/journey/cdp.mjs` and `width.mjs` unchanged). `.am-app__bar` keeps
`flex-wrap: wrap` in `globals.css`. No `web/src/shared/**` file changed beyond Q1's two, no
`web/src/app/**` beyond `layout.tsx` and Q1's `screen-lock.ts`, no `_pages/**`, `widgets/**`,
`entities/**` or `features/**` file. No ref, tag, push, merge or worktree removal.

## 7. Open questions

1. **The census lost one pair (§2.5).** It belonged to an element this task removed by design
   (the bar `Выйти` button); `W50-PLAN.md` §7 lists "the census shrinks" as a stop. Accept as an
   expected delta, or require a replacement measurement?
2. **The footer wording (§4.1)** — the owner's to confirm or reword.
3. **«Сменить пароль» against the registry's «Смена пароля» (§4.3)** — keep the task's verb, or
   take the registry label for consistency?
4. **The header for an empty role set (§4.2)** — «Роли не назначены.» as on the home page?
