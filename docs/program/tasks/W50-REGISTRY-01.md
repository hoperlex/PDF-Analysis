# Task W50-REGISTRY-01 — one screen registry, the server guard, its redirects and the account entity

## Outcome

Every `page.tsx` under `web/src/app` is a row of `web/src/shared/config/screen-registry.ts` and
calls `requireScreen(address, { params, searchParams })`; a guest, a default credential, an
incomplete profile, a missing role and a signed-in visit to `/login` are each sent where
`W50-PLAN.md` §3.2 says, by a redirect and never by a thrown framework error; a validated `next`
survives sign-in and an invalid one is dropped; sign-in lands on `/`; `/403`, the `/account`
placeholder, the home placeholder and the four stubs of owner ruling `R-66` are registered
screens; `web/src/entities/account/**` and the query namespaces `account`, `users`,
`registrations` exist. No contract change.

## Depends on

- `W50-FREEZE-01` (records the base, ruling `R-66` and the `next build` route table)

## Frozen inputs

- API contract: 27 paths / 34 operations / 77 schemas — frozen; W50 makes no contract change
- error catalog: 23 codes; domain candidate revision 9, 29 opaque identities — frozen
- migration head: `0015_accounts_roles_registration` — frozen
- code base: the commit that carries `docs/program/W50-FREEZE-01.md` on `integration/w50` (published to `origin/dev`)
- controlling plan: `docs/program/dispatch/W50-PLAN.md` at the freeze commit, as amended by owner
  ruling `R-66`
- owner ruling `R-66` (navigation amendment A-6, amends `W50-PLAN.md` §3.1 groups), recorded by
  `W50-FREEZE-01`:
  - **Работа** = Проекты `/projects`, Дашборд `/dashboard`, «Оптимизация разделов»
    `/section-optimisation` (stub);
  - **Знания** = База знаний `/knowledge-base`, Блоки `/blocks`, «Нормы» `/norms` (stub);
  - **Система** = Журнал выполнения `/logs`, Исполнители `/workers`, «Настройки анализа»
    `/analysis-settings` (stub), «Очередь» `/queue` (stub);
  - `/optimisation` leaves the Система menu; it stays a registered, reachable screen in group
    `hidden` until W59 (project optimisation later becomes a project tab — not in W50);
  - the stubs are honest placeholders (`R-23`: structure first, a stub says it is not
    implemented, never invents data), rendered with the existing `RoutePlaceholder`; access
    `session`, roles `any`
- session subject (W49, `web/src/app/bff/session/subject.ts` `SessionAccount`, extended by
  `store.ts` `SessionSubject`): `login`, `displayLabel`, `initials`, `roles`,
  `isDefaultCredential`, `profileComplete`. There is no separate e-mail field: `login` is the
  normalised e-mail once the profile is complete, and a legacy login before that.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `web/src/shared/config/screen-registry.ts` (the set of screens; mirrored by `tests/e2e/pc01/journey/manifest.json` `routes` and `web/tests/unit/screens/route-screens.ts` `SEEDS`) and `web/src/shared/api/query-keys.ts` `QUERY_NAMESPACES` (the query namespaces; authority `web/docs/PC01_UI_SEAM.md` §6)
- enumerator_owner: `W50-REGISTRY-01` (Stage A, alone; no other W50 lane writes either set)
- totality_query: the addresses of every `page.tsx` under `web/src/app` (the walker `routeAddresses()` in `web/tests/unit/screens/route-screens.ts`) equal the registry's addresses in both directions (`web/tests/guards/screen-registry.guard.test.ts`), equal the manifest's `page_module` set (`tests/e2e/test_pc01_journey_conformance.py`) and have one seed each (`web/tests/guards/screen-set.guard.test.ts`); `QUERY_NAMESPACES` equals the first segments of the `PC01_UI_SEAM.md` §6 table and the set `queryKeys` produces (`web/tests/contract/narrow-sets.contract.test.ts`)

## Captured premise evidence

- premise: the base has 16 screens, each guarded by `requireAChangedPassword()` or registered open; literal route counts and the `/` → `/projects` redirect are pinned outside the plan's grant

### P-01 — the route tree the registry must equal

- captured_at: 2026-10-06
- command: `git ls-tree -r --name-only ead639f web/src/app | grep -c 'page.tsx$'`
- captured_output:
  ```text
  16
  ```
- interpretation: measured on the W49 closure `ead639f`; the freeze commit adds no `page.tsx`, so
  the lane re-measures 16 at its base. After this task the count is 22 (`/403`, `/account` and the
  four `R-66` stubs).

### P-02 — the guard call each route makes today

- captured_at: 2026-10-06
- command: `git grep -c 'requireAChangedPassword()' ead639f -- 'web/src/app/*page.tsx'`
- captured_output:
  ```text
  ead639f:web/src/app/account/password/page.tsx:1
  ead639f:web/src/app/blocks/page.tsx:2
  ead639f:web/src/app/dashboard/page.tsx:2
  ead639f:web/src/app/knowledge-base/page.tsx:2
  ead639f:web/src/app/logs/page.tsx:2
  ead639f:web/src/app/optimisation/page.tsx:2
  ead639f:web/src/app/projects/[project_uid]/documents/[document_uid]/page.tsx:2
  ead639f:web/src/app/projects/[project_uid]/page.tsx:2
  ead639f:web/src/app/projects/[project_uid]/runs/[run_id]/page.tsx:2
  ead639f:web/src/app/projects/[project_uid]/runs/[run_id]/review/page.tsx:2
  ead639f:web/src/app/projects/[project_uid]/versions/[version_uid]/comparison/page.tsx:2
  ead639f:web/src/app/projects/[project_uid]/versions/[version_uid]/page.tsx:2
  ead639f:web/src/app/projects/page.tsx:2
  ead639f:web/src/app/workers/page.tsx:2
  ```
- interpretation: thirteen routes carry the call in a comment and in code; `/account/password`
  only mentions it in its docstring (it is registered open), and `/` and `/login` do not mention
  it. Every one of the sixteen changes in this task.

### P-03 — literal route counts outside the plan's grant

- captured_at: 2026-10-06
- command: `git grep -n -E '\b16\b' ead639f -- tests/e2e/pc01/journey/verify-acceptance.mjs tests/contract/test_alpha_acceptance_command.py scripts/manual-alpha-check.sh docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`
- captured_output:
  ```text
  ead639f:docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md:87:Команда выполняет preflight, вход через экран приложения, все 3 write-шага PC-01, все 16
  ead639f:docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md:192:### A09 — 16 экранов и ширина
  ead639f:docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md:211:16. `/dashboard`.
  ead639f:scripts/manual-alpha-check.sh:28:  --automated         Выполнить sign-in, 3 записи, 16 cold routes и 6 отказов.
  ead639f:scripts/manual-alpha-check.sh:453:record_manual "A09" "16 экранов и 780px" \
  ead639f:scripts/manual-alpha-check.sh:454:  "Все 16 маршрутов открываются после cold reload; нет console error и горизонтального overflow."
  ead639f:tests/contract/test_alpha_acceptance_command.py:118:        "routesChecked": 16 if phase != "write" else 0,
  ead639f:tests/contract/test_alpha_acceptance_command.py:119:        "routesDeclared": 16,
  ead639f:tests/contract/test_alpha_acceptance_command.py:126:            for index in range(16 if phase != "write" else 0)
  ead639f:tests/contract/test_alpha_acceptance_command.py:215:        'routesChecked': 16,
  ead639f:tests/contract/test_alpha_acceptance_command.py:216:        'routesDeclared': 16,
  ead639f:tests/contract/test_alpha_acceptance_command.py:221:        }} for i in range(16)],
  ead639f:tests/e2e/pc01/journey/verify-acceptance.mjs:129:  expect(journey.routesDeclared === 16, 'read phase does not declare exactly 16 routes');
  ead639f:tests/e2e/pc01/journey/verify-acceptance.mjs:130:  expect(journey.routesChecked === 16, 'read phase did not check 16/16 cold routes');
  ead639f:tests/e2e/pc01/journey/verify-acceptance.mjs:132:  expect(Array.isArray(journey.records) && journey.records.length === 16, 'journey has no record for every route');
  ead639f:tests/e2e/pc01/journey/verify-acceptance.mjs:176:  journey?.routesChecked === 16 &&
  ead639f:tests/e2e/pc01/journey/verify-acceptance.mjs:177:  journey?.routesDeclared === 16;
  ead639f:tests/e2e/pc01/journey/verify-acceptance.mjs:181:  journey?.records?.length === 16 &&
  ```
- interpretation: the deployed acceptance (`make alpha-acceptance`) asserts exactly sixteen
  routes; the manifest will declare 22. The gate does not run the verifier against a real
  journey, so the gate stays green while the release acceptance would fail — these move here.

### P-04 — the root opt-out the plan turns into a seed is counted literally

- captured_at: 2026-10-06
- command: `git grep -n -E 'toBe\(1\);' ead639f -- web/tests/guards/screen-set.guard.test.ts`
- captured_output:
  ```text
  ead639f:web/tests/guards/screen-set.guard.test.ts:165:    expect(excused.length, 'the opt-out list is empty; this case has stopped measuring').toBe(1);
  ```
- interpretation: the only opt-out is `root-redirect`; once `/` renders a placeholder the
  opt-out list is empty and this literal is red.

### P-05 — the acceptance preflight requires `/` to redirect to `/projects`

- captured_at: 2026-10-06
- command: `git grep -n -E 'HTTP-root|exact_route = ' ead639f -- scripts/manual-alpha-check.sh`
- captured_output:
  ```text
  ead639f:scripts/manual-alpha-check.sh:273:exact_route = target.path == "/projects" and not target.query and not target.fragment
  ead639f:scripts/manual-alpha-check.sh:282:  record_auto "HTTP-root" "PASS" "$ROOT_STATUS -> $ROOT_LOCATION"
  ead639f:scripts/manual-alpha-check.sh:284:  record_auto "HTTP-root" "BLOCKED" "origin недоступен по сети/TLS"
  ead639f:scripts/manual-alpha-check.sh:286:  record_auto "HTTP-root" "FAIL" "expected 307/308 -> /projects; got status=$ROOT_STATUS location=${ROOT_LOCATION:-none}"
  ```
- interpretation: after this task a guest's `GET /` answers a redirect to `/login?next=…`, so the
  preflight's root check and its contract test (`test_root_redirect_must_resolve_to_projects_on_the_declared_origin`)
  must move with the behaviour.

### P-06 — the subject fields the guard reads exist

- captured_at: 2026-10-06
- command: `git grep -n -E 'readonly (login|displayLabel|initials|roles|isDefaultCredential|profileComplete):' ead639f -- web/src/app/bff/session/subject.ts`
- captured_output:
  ```text
  ead639f:web/src/app/bff/session/subject.ts:30:  readonly login: string;
  ead639f:web/src/app/bff/session/subject.ts:32:  readonly displayLabel: string;
  ead639f:web/src/app/bff/session/subject.ts:34:  readonly initials: string;
  ead639f:web/src/app/bff/session/subject.ts:36:  readonly roles: readonly Role[];
  ead639f:web/src/app/bff/session/subject.ts:46:  readonly isDefaultCredential: boolean;
  ead639f:web/src/app/bff/session/subject.ts:48:  readonly profileComplete: boolean;
  ```
- interpretation: `store.ts` imports this interface and its `SessionSubject` extends it; the
  guard reads it only through `subjectOf`, never `credentialOf`.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/dispatch/W50-PLAN.md`
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

From `W50-PLAN.md` §4 `W50-REGISTRY-01`, verbatim:

- `web/src/shared/config/screen-registry.ts`, `web/src/shared/config/index.ts`
- `web/src/app/bff/session/screen-lock.ts`
- `web/src/app/bff/v1/[...path]/route.ts` (the after-sign-in redirect only)
- every `web/src/app/**/page.tsx` (the guard call with the page's `params`/`searchParams`, nothing
  else)
- `web/src/app/403/**`, `web/src/app/not-found.tsx`, `web/src/app/error.tsx`
- `web/src/app/**/loading.tsx` (empty typed placeholders; LAZY fills them)
- `web/src/_pages/forbidden/**`
- `web/src/_pages/account/**` (the placeholder of §3.2 step 3)
- `web/src/app/account/page.tsx` (new placeholder route)
- `web/src/features/sign-in/**` and `web/src/_pages/sign-in/**` (the hidden `next` field)
- `web/src/entities/account/**`
- `web/src/_pages/home/**` (placeholder module exporting `HomePage`; HOME replaces its content and
  keeps the named export and its props)
- `tests/e2e/pc01/journey/manifest.json`
- `web/src/shared/api/query-keys.ts`
- `web/docs/PC01_UI_SEAM.md` (§6, and the §2 route-table row for `/`, granted by the integrator at the freeze)
- `web/tests/unit/api/configuration-and-cache-keys.test.ts`
- `web/tests/contract/narrow-sets.contract.test.ts`
- `web/tests/guards/query-key-shape.guard.test.ts` (the query namespaces `account`, `users`,
  `registrations` are a closed set checked against `PC01_UI_SEAM.md` §6 and a unit literal — they
  enter once, here, so no later lane touches them)
- `web/tests/unit/screens/route-screens.ts`
- `web/tests/guards/default-credential-screens.guard.test.ts` → `screen-guard.guard.test.ts`
- `web/tests/guards/screen-registry.guard.test.ts` (new)
- `web/tests/unit/session/**`
- `web/tests/unit/entities/account.test.ts` (new)
- `docs/program/W50-REGISTRY-01.md`

Owner ruling `R-66` (navigation amendment A-6):

- `web/src/app/section-optimisation/page.tsx`, `web/src/app/norms/page.tsx`,
  `web/src/app/analysis-settings/page.tsx`, `web/src/app/queue/page.tsx` (new)
- `web/src/_pages/section-optimisation/**`, `web/src/_pages/norms/**`,
  `web/src/_pages/analysis-settings/**`, `web/src/_pages/queue/**` (new placeholder modules)
- their four entries in `tests/e2e/pc01/journey/manifest.json` (already granted above)

Pins this task's change moves (each listed with its lines in "Pins the new routes move" below;
only the named lines and the cases they sit in):

- `web/tests/guards/screen-set.guard.test.ts` — the opt-out count case only
- `web/tests/unit/screens/routes.test.ts` — the route-invocation cases and the `/` describe only
- `web/tests/guards/prepared-sections.guard.test.ts` — `SECTIONS`, the route-file case, and the
  one line that keeps the navigation case iterating the three existing sections only
- `tests/e2e/pc01/journey/verify-acceptance.mjs` — the route-count assertions only
- `tests/contract/test_alpha_acceptance_command.py` — the route-count fixtures and the root
  redirect stub and parametrisation only
- `scripts/manual-alpha-check.sh` — the route-count sentences and the `HTTP-root` check only
- `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` — lines 65, 87, 119 and the A09 section only
  (Russian, like the rest of the file)
- `tests/e2e/pc01/journey/fixtures/redden.manifest.json`,
  `tests/e2e/pc01/journey/fixtures/redden-write.manifest.json`,
  `tests/e2e/pc01/journey/fixtures/redden-write-bound.manifest.json` — `session.lands_on` and the
  `root` route's `redirects_to` only

Two scope notes the plan implies and states elsewhere: `web/src/app/page.tsx` becomes the
registered `session` placeholder delegating to `_pages/home` (Deliverables), and
`web/src/app/login/page.tsx` hands the validated `next` to the sign-in page; neither is more than
that.

## Pins the new routes move

Measured on `ead639f` with `git grep -n` and `git show ead639f:<path> | grep -n`; the lane
re-measures each on its base before editing. "Moves" means the literal or the case must change in
this task, or a guard turns red (gate) or the release acceptance fails (deployed).

| Pin | Lines at `ead639f` | What it pins | Moves? | Why |
| --- | --- | --- | --- | --- |
| `web/tests/guards/screen-set.guard.test.ts` | 165 | opt-out count `toBe(1)` | **yes** — literal count | the `root-redirect` opt-out becomes an ordinary seed, the count becomes 0; the case must still be able to fail (an opt-out added later is red unless it carries a proof) |
| `web/tests/unit/screens/route-screens.ts` | 211–234 (`root-redirect` seed), 92 (`RootPage` import), `SEEDS` list | the seed list | **yes** — list (granted by the plan) | `/` becomes an ordinary seed; six new addresses need seeds |
| `web/tests/unit/screens/routes.test.ts` | 242–254 (`/` → `/projects`, literal destination); 74–239 (route files called with no `searchParams` and an empty cookie jar) | the root redirect and the routes' call shape | **yes** — literal destination and invocation list | a guest is redirected by `requireScreen`, so each case needs a session in the jar and the page props; the root case asserts the placeholder instead |
| `web/tests/guards/prepared-sections.guard.test.ts` | 96–112 (`SECTIONS`), 257–268 (`await routeFile()` with an empty jar) | the prepared-section list; the route-file case | **yes** — list | the four `R-66` stubs join rules 1–3 (no digits, an own promise, no false "yet"); the route-file case needs a session and props. The navigation case (248–255) keeps its meaning: the frame is `W50-SHELL-FRAME`'s, so it still iterates only the three existing sections (the frame does not link the stubs before Stage C) |
| `tests/e2e/pc01/journey/manifest.json` | 76 (`session.lands_on: "/projects"`), 110–124 (`root`: `redirects_to`, `expects_api` `listProjects`), 272 (`sign-in`) | landing, root, sign-in | **yes** (granted by the plan) | `lands_on` becomes `/`; `root` loses `redirects_to` and its `listProjects` claim (the placeholder calls nothing); the `sign-in` route is walked with the session cookie and now lands on `/`, so it declares `redirects_to: "/"`; six new routes |
| `tests/e2e/pc01/journey/verify-acceptance.mjs` | 129, 130, 132, 176, 177, 181 | `=== 16` routes | **yes** — literal count | the manifest declares 22; either the literal moves to 22 or it is derived from `manifest.json` `routes.length` — the report says which and shows the assertion can still fail |
| `tests/contract/test_alpha_acceptance_command.py` | 118, 119, 126, 215, 216, 221 (16-route fixtures); 156 (stub root `Location` `/projects`); 412–428 (root-redirect parametrisation, `/projects`) | synthetic journey envelopes; the root-redirect rule | **yes** — literal count and literal destination | moves with the verifier and the preflight; every rejecting case of the parametrisation (foreign origin, scheme, port, userinfo, suffix host) is kept for the new destination |
| `scripts/manual-alpha-check.sh` | 28, 453, 454 (count prose); 245–286 (`root_redirect_is_same_origin_projects`, `HTTP-root`); 438 («вход приводит на /projects») | runbook command | **yes** — literal count and destination | a guest's root answer becomes `307/308` to `/login?next=…` on the same origin; sign-in lands on `/` |
| `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` | 65 (root answer `307/308` на `/projects`), 87 («все 16 cold routes»), 119 («после входа открыт `/projects`»), 192 (A09 heading), 196–211 (list of 16) | the release runbook | **yes** — literal count and list | 22 screens; item 1 becomes `/` (home placeholder); the six new addresses are listed |
| `tests/e2e/pc01/journey/fixtures/redden.manifest.json` | 52 | `lands_on: "/projects"` | **yes** — literal | a redden fixture that fails at sign-in for the wrong reason proves nothing |
| `tests/e2e/pc01/journey/fixtures/redden-write.manifest.json` | 55, 73–75 | `lands_on`, root `redirects_to` | **yes** — literal | as above |
| `tests/e2e/pc01/journey/fixtures/redden-write-bound.manifest.json` | 52, 70–72 | `lands_on`, root `redirects_to` | **yes** — literal | as above |
| `web/tests/unit/session/bff-session.test.ts` | 356 | `SIGN_IN_LANDING_PATH === '/projects'` | **yes** (granted by the plan, `web/tests/unit/session/**`) | landing becomes `/` |
| `web/tests/unit/api/configuration-and-cache-keys.test.ts` | 176–177 («exactly the five roots»), 224 (`toHaveLength(5)`) | namespace literal | **yes** (granted by the plan) | eight namespaces |
| `web/tests/guards/default-credential-screens.guard.test.ts` | 112 | `>= 16` routes | no — a floor | the file is renamed and rewritten here anyway |
| `web/tests/guards/screen-set.guard.test.ts` | 128, 180 (`> 10`), 182 (relation) | floors and a relation | no | adding screens satisfies them |
| `web/tests/unit/styles/contrast.test.ts` | 334 (`> 10`) | floor | no | as above |
| `web/docs/PC01_UI_SEAM.md` | 59 (`/` row: «redirect to `/projects`») | §2 route table | **yes** — granted by the integrator at the freeze | the row states what `/` now does |
| `docs/program/CURRENT_STATE.md` | 162 («16/16 routes») | a dated measurement | no | historical record, integrator-owned |
| `tests/e2e/pc01/journey/session.mjs`; `tests/e2e/test_pc01_journey_conformance.py` | 5, 35, 43, 93; 79, 1523, 1573, 1651 | prose «fifteen» / «2 of 15» | no | history of `D-92`, not a live count |
| `web/tests/unit/screens/forms-and-pages.test.ts` | 189 (`href="/projects"` in the guest frame) | the frame's brand link | no — not this task | the frame is unchanged here; `W50-SHELL-FRAME` owns it |

## Forbidden hotspots

- every path not listed above; `contracts/**`; `web/openapi/**`; `web/src/shared/api/generated/**`;
  `web/FRONTEND_LOCK.json`; migrations; `src/**`; root locks, `web/package.json`,
  `web/package-lock.json`; `web/src/_app/**` (including the composition root `providers.tsx`);
  `web/src/app/layout.tsx`; `web/src/app/globals.css`; `web/src/shared/ui/**`;
  `web/src/shared/lib/routes.ts` (imported, not replaced); refs, tags, deployment and secrets;
  `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`,
  `CHECKPOINT_REGISTRY.md`
- a pin, digest or prose guard that turns red outside the files above is a stop: report it with
  its output, do not edit it

## Non-goals

- no navigation, account menu, avatar or frame change (`W50-SHELL-UI`, `W50-SHELL-FRAME`); the
  frame keeps its hard-coded links until Stage C
- no home content beyond the placeholder (`W50-HOME-01`); no lazy loading and no `loading.tsx`
  body beyond a typed placeholder (`W50-LAZY-01`)
- no registration, account or administration screens (W51); `/account` is a placeholder; no
  `/admin/*` row
- no middleware, no layout-level guard (`W50-PLAN.md` §3.2 says why)
- no change to the session register format, the subject, or what the API authorises
- no new dependency

## Deliverables

- `W50-PLAN.md` §3.1–§3.3 and §3.6's entity:
  - the registry: one array of `{ address, label, group, access, roles, inMenu }`, the only list
    of screens; groups as `R-66` amends §3.1 (Главная `/`; Работа, Знания, Система as listed in
    Frozen inputs, in that order, Проекты first in Работа; Администрирование with no row in W50);
    `/optimisation` in `hidden` with `inMenu: false`; the four stubs `session`/`any`
  - `requireScreen(address, { params, searchParams })` in `screen-lock.ts`, the five decisions of
    §3.2 in order; `requireAChangedPassword()` removed; every `page.tsx` calls it with its own
    props
  - one exported `next`/`from` validator (unit-tested): exactly one leading `/`, not `//…` or
    `/\…`, no scheme, at most 512 characters, path matching a registry address shape; anything
    else dropped, never echoed. The fragment is not preserved, and the code says so
  - `/403` (registered `public`, Russian, names the role the registry requires for a valid
    `from`), `app/error.tsx`, the four `loading.tsx` placeholders (`projects`,
    `projects/[project_uid]`, `dashboard`, `knowledge-base`) rendering a typed state from
    `shared/ui/states`, `not-found.tsx` with no English and no raw error
  - sign-in: the validated `next` in a hidden field of the form, re-validated by the BFF's
    after-sign-in redirect; `AFTER_SIGN_IN` (`route.ts`), `SIGN_IN_LANDING_PATH`
    (`features/sign-in/model/exchange.ts`) and `session.lands_on` in `manifest.json` move to `/`
    together; a default credential still lands on `/account/password`
  - `app/page.tsx` becomes a registered `session` placeholder (`RoutePlaceholder`) rendered from
    `_pages/home`, whose `HomePage` named export and props are the contract `W50-HOME-01` keeps;
    because HOME may change neither the props nor the `/` seed, the props already carry what the
    home page needs from the session (at least `displayLabel` and `roles`, from the subject
    `requireScreen` returns or the route reads through `subjectOf`), written down in the report; the `root-redirect` opt-out
    seed becomes an ordinary seed
  - `/account` placeholder (`_pages/account`) that says what is missing (§3.2 step 3)
  - the four `R-66` stubs: each `page.tsx` follows the existing stub pattern
    (`web/src/app/logs/page.tsx` → `@/_pages/logs` → `web/src/_pages/logs/ui/logs-page.tsx`, which
    renders `RoutePlaceholder` from `@/shared/ui` with `screen`, `route` and an own `promise`;
    `web/src/_pages/workers/ui/workers-page.tsx` is the pattern for a section that is not on its
    way, with `unavailability` and `headline`), `export const dynamic = 'force-dynamic'`, and the
    new guard call instead of `requireAChangedPassword()`; each `_pages/<name>` exports
    `<Name>Page` from `index.ts`; no number, no invented data, Russian only. `R-23`'s addendum
    (`OWNER_RULINGS_2026-09-17.md` §3.11) asks a promise to say what will be here, not only
    "not implemented", and asks the data shape to be written down and checked against the
    contract: the report carries one paragraph per stub naming what the section would read and
    showing the frozen contract has no such operation. **The owner ruled the wording (`R-66`,
    direct poll 2026-10-06):** every stub is *on its way* (the default "yet" wording, never the
    `/workers` "not decided" wording); its promise says in one or two sentences what will be here
    and *when, named by an event in words, never by a number* — the prepared-sections guard's
    no-digits rule stands. The events: «Очередь» `/queue` — with durable execution of analyses
    (state, priority and age of each queued analysis); «Нормы» `/norms` — after the normative
    corpus moves onto the stand (browsing the norm documents and their paragraphs); «Настройки
    анализа» `/analysis-settings` — together with the АР section in working order (the presets
    of models and stages an administrator keeps and an expert picks from); «Оптимизация
    разделов» `/section-optimisation` — after all sections are implemented (optimisation across
    a section's documents). The lane writes the sentences in that sense; the owner may reword
    them at acceptance
  - `entities/account/**`: the `getMe` consumer, `displayLabel`/`initials` helpers, Russian role
    labels (Эксперт, Администратор), query key `account.me`; an unknown role value is a typed
    fault, never a fallback label
  - the three query namespaces `account`, `users`, `registrations` with their key factories in
    `query-keys.ts`, the §6 table rows in `PC01_UI_SEAM.md`, and the unit literal
  - the manifest: six new routes, `root` and `sign-in` as in the pins table, `lands_on: "/"`
  - the moved pins of the table above
- the report `docs/program/W50-REGISTRY-01.md` with the six items of `AGENTS.md` §5, the
  frontend test counts by file before and after, and the list of pins moved with their new values

## Required tests

- first, before implementing: an apply-and-see probe on a disposable copy (registry stub, one
  route switched to the new guard, `/` switched to a placeholder) that runs the frontend suite and
  the battery's `tests/e2e` and `tests/contract` files, so every red outside the grant is known on
  day one; its output goes in the report; a red outside the grant is a stop
- mutations, each red with its output in the report:
  - a `page.tsx` without `requireScreen` is red naming its address
  - a registry row without a page is red; a page without a row is red
  - a page missing from `manifest.json` is red (`test_pc01_journey_conformance.py`)
  - `next=//evil.example`, `next=https://evil.example`, `next=/\evil`, a 513-character `next` and
    `next=/nowhere` are dropped; `next=/projects?x=1` survives sign-in with its query
  - an expert on `/403?from=/admin/users` sees «Администратор» — W50 registers no `/admin/*` row,
    so this case runs the `/403` resolver against a fixture registry that has one, and a second
    case asserts the live registry's role-gated set as measured (empty in W50, by `R-60`)
  - a signed-in visit to `/login` redirects to `/`
  - each of the five decisions of §3.2 has a test, driven against the real register
    (`openSession` with a full subject), and each test is red when its decision is removed
  - a `/` that redirects again is red; an `R-66` stub that renders a digit or the component's
    generic promise is red; `/optimisation` in the menu is red; `/optimisation` unregistered is red
  - the moved verifier count is red against a 21-route envelope
- `npm --prefix web test -- --run`; `npm --prefix web run lint -- --quiet`;
  `npm --prefix web run typecheck`
- `.venv/bin/pytest tests/e2e/test_pc01_journey_conformance.py tests/contract/test_alpha_acceptance_command.py tests/contract/program/test_wave_governance.py -q`
- the live journey on the lane stand, signed in as a complete-profile account with a changed
  password: `npm --prefix web run e2e:pc01 -- --phase all` (the gate does not see `expects_api`,
  `D-108`), summary quoted verbatim; a guest `curl -sI` of `/` and of one route per access level,
  `Location` headers quoted
- `git diff --check`; `make gate` with the literal `GATE OK` on the task's head

## Integration contract

- `screen-registry.ts` exports the registry array and its types; it is the only list of screens.
  `W50-SHELL-FRAME` builds the menu from it (rows with `inMenu: true`, grouped, filtered by the
  session's roles); `W51-ROUTES-01` adds rows to it. No other W50 lane edits it.
- `requireScreen(address, { params, searchParams })` is called by every `page.tsx`; decisions are
  redirects or a normal return, in the order of §3.2.
- `_pages/home` exports `HomePage` with the props this task fixes; `W50-HOME-01` changes the
  content only. The `/` seed in `route-screens.ts` renders it with those props.
- `entities/account` exports the role labels, the `displayLabel`/`initials` helpers and the
  `account.me` query; `W50-HOME-01` and `W50-SHELL-FRAME` consume it.
- query namespaces are eight and closed: `projects`, `versions`, `runs`, `findings`, `dashboard`,
  `account`, `users`, `registrations`; later lanes add key factories inside them only.
- the four `loading.tsx` files exist with a typed placeholder body; `W50-LAZY-01` fills them.
- the frame is untouched: it still links `/optimisation` and none of the four stubs until Stage C.

## Failure/idempotency/security cases

- lane `gate-w50reg`, worktree `.local/worktrees/w50-reg`: `FOUNDATION_INSTANCE=gate-w50reg`,
  `POSTGRES_PORT=56640`, `S3_API_PORT=60240`, `S3_CONSOLE_PORT=60241`, a lane-unique `POSTGRES_DB`
  and `S3_BUCKET`; each port checked free with `ss -ltn` before use and recorded; any further port
  the stand needs (API, health, `next start`) is checked free the same way, recorded in the report,
  and never one another lane's row holds; provisioned with
  `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` and `npm --prefix web ci`; the real corpus
  attached read-only before `make gate`
- one full `make gate` on the host at a time: confirm with the integrator that no other gate is
  measuring before starting; never edit the tree while its gate runs; a commit after the gate needs
  a new gate
- owned disposable services only; at the end `make down` and remove the lane's own volumes by
  exact name
- never kill a process by pattern — only confirmed-own PIDs, recorded when started
- no credential, cookie value, session id or `docker compose config` output in evidence; the
  journey's sign-in pair comes from the environment and never appears in the report
- `next` is never echoed when invalid (not in a redirect, not in markup, not in a log line); no
  status reason travels in a URL; no redirect cycle: `/login`, `/account/password`, `/account` and
  `/403` are `public` or `open-to-default-credential`, `/` is `session`
- an unknown role value from the register is a typed fault, never treated as `any`
- repeated sign-in with the same `next` lands on the same address (idempotent); a stale session
  (closed by an upstream 401) is a guest to the guard

## Rollback / feature flag

Revert the commits. No flag: a half-guarded tree is the defect the registry exists to prevent.
No stored data changes; the session register format (version 2) is untouched, so a revert signs
nobody out.

## Handoff

- changed files: listed in `docs/program/W50-REGISTRY-01.md` with `git diff --name-only <base>..<sha>`
  and `git status --porcelain -uall` empty
- commands/results: verbatim with exit status; every mutation with its red output; the probe's
  output; the journey summary
- known limits: listed, never decided silently — at least whether `next` is kept across a refused sign-in attempt (the refusal redirect is outside
  "the after-sign-in redirect only")
- integration notes: hand back branch `agent/w50-registry-01` at a recorded SHA
