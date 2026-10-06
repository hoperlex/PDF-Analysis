# Task W50-HOME-01 — a real home page at `/`

## Outcome

`/` renders a home page instead of a placeholder: it greets the session by `displayLabel`, lists
the five most recent projects (`listProjects`), shows the dashboard summary tile from
`getDashboardSummary`, and — for a session holding `admin` — a «Заявки на регистрацию» tile with
`pending_total` from `listRegistrations`, without a link in W50. The route, its guard call and the
`HomePage` named export and props fixed by `W50-REGISTRY-01` are unchanged.

## Depends on

- `W50-REGISTRY-01` merged into `integration/w50` (Stage A); runs in parallel with
  `W50-SHELL-UI` and `W50-LAZY-01` on disjoint paths

## Frozen inputs

- API contract: 27 paths / 34 operations / 77 schemas — frozen; W50 makes no contract change
  (`getMe`, `listProjects`, `getDashboardSummary`, `listRegistrations` exist in
  `web/src/shared/api/generated/operations.gen.ts`)
- error catalog: 23 codes; domain candidate revision 9, 29 opaque identities — frozen
- migration head: `0015_accounts_roles_registration` — frozen
- code base: the commit that carries `docs/program/W50-FREEZE-01.md` on `integration/w50` (published to `origin/dev`); lane base:
  `<integration/w50 commit merging W50-REGISTRY-01>` (named by the integrator in the dispatch message)
- controlling plan: `docs/program/dispatch/W50-PLAN.md` at the freeze commit, as amended by owner
  ruling `R-66` (which keeps Проекты as the first item of «Работа»; the order lives in the
  registry, not here)
- from `W50-REGISTRY-01`: `HomePage` and its props in `_pages/home`; `entities/account` (role
  labels, `account.me`); the query namespaces `account`, `users`, `registrations` and their key
  factories; the `/` seed in `web/tests/unit/screens/route-screens.ts`
- rulings: `R-60` (reads need no role; `listRegistrations` is an administrator operation),
  `R-44` (the dashboard summary is one server-side read)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `/` renders nothing of its own at the W49 closure; at this task's base it is the registry's placeholder

### P-01 — the root route before the wave

- captured_at: 2026-10-06
- command: `git grep -n -E 'redirect' ead639f -- web/src/app/page.tsx`
- captured_output:
  ```text
  ead639f:web/src/app/page.tsx:5:import { redirect } from 'next/navigation';
  ead639f:web/src/app/page.tsx:8:  redirect('/projects');
  ```
- interpretation: measured on `ead639f`. `W50-REGISTRY-01` replaces the redirect with a guarded
  `RoutePlaceholder` from `_pages/home`; the lane re-measures `web/src/app/page.tsx` and
  `web/src/_pages/home/**` at its base and records the `HomePage` props it must keep.

### P-02 — the four operations the page reads exist in the generated client

- captured_at: 2026-10-06
- command: `git grep -n -E '^// (getMe|listRegistrations|listProjects|getDashboardSummary) - ' ead639f -- web/src/shared/api/generated/operations.gen.ts`
- captured_output:
  ```text
  ead639f:web/src/shared/api/generated/operations.gen.ts:271:// getDashboardSummary - GET /dashboard
  ead639f:web/src/shared/api/generated/operations.gen.ts:328:// getMe - GET /me
  ead639f:web/src/shared/api/generated/operations.gen.ts:545:// listProjects - GET /projects
  ead639f:web/src/shared/api/generated/operations.gen.ts:567:// listRegistrations - GET /registrations
  ```
- interpretation: no contract change is needed; `RegistrationRequestPage.pending_total` is the
  administrator's badge (`types.gen.ts`).

## Historical evidence

- correction_mode: none
- source_record: `docs/program/dispatch/W50-PLAN.md`
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

From `W50-PLAN.md` §4 Stage B, `HOME allowed paths`, verbatim:

- `web/src/app/page.tsx`
- `web/src/_pages/home/**`
- `web/src/widgets/home-*/**`
- `web/tests/unit/screens/home.test.ts`
- `docs/program/W50-HOME-01.md`

Granted by the integrator at the freeze (no other Stage-B lane writes the manifest):

- `tests/e2e/pc01/journey/manifest.json` — only the `expects_api` of the `root` route and of the
  `sign-in` route (walked with the session cookie, it lands on `/`): declare exactly the calls the
  home page makes, so the live journey does not redden on an undeclared call (`D-108`)

## Forbidden hotspots

- every path not listed above; `contracts/**`; `web/src/shared/**` (including `query-keys.ts`,
  `shared/ui/**`, `shared/config/**`); `web/src/app/globals.css` (`W50-SHELL-UI` only);
  `web/src/entities/**` (consumed, not edited); `web/src/_app/**` (including `providers.tsx`);
  `web/src/app/layout.tsx`; `web/tests/unit/screens/route-screens.ts`;
  `web/tests/unit/styles/**`; `tests/e2e/pc01/journey/manifest.json`; migrations; `src/**`; root
  locks, `web/package.json`, `web/package-lock.json`; refs, tags, deployment and secrets;
  `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`
- `HomePage`'s named export and props are `W50-REGISTRY-01`'s contract: changing them breaks the
  `/` seed this task may not edit — a stop, not an edit
- `tests/e2e/pc01/journey/manifest.json` beyond the two `expects_api` entries granted above

## Non-goals

- no link to `/admin/registrations` (the row arrives in W51); no registration or account screens
- no navigation or frame change; Проекты's place in «Работа» is the registry's, not this page's
- no new query namespace (closed in `W50-REGISTRY-01`); no new dependency; no global CSS

## Deliverables

- `W50-PLAN.md` §3.6 home page: the greeting by `displayLabel` (from the session subject or the
  `account.me` entity, one source, said which in the report); the five most recent projects from
  `listProjects` (the contract's order, `limit` 5), each linked through `routes` in
  `@/shared/lib`; the dashboard summary tile from `getDashboardSummary`; for a session whose roles
  include `admin`, the «Заявки на регистрацию» tile with `pending_total` from
  `listRegistrations`, rendered without a link; `listRegistrations` is never requested for a
  session without `admin`
- each tile has the typed states of `shared/ui/states` (loading, empty, error); an empty project
  list says so; no raw error message, no English
- role labels come from `entities/account`; an unknown role value renders a typed fault, never a
  fallback label
- styling in CSS modules under this task's own paths (`*.module.css`, read by
  `styling-layer.test.ts`), colour only through existing tokens; a long `displayLabel` wraps
  instead of widening the page
- `web/tests/unit/screens/home.test.ts`
- the report `docs/program/W50-HOME-01.md` with the six items of `AGENTS.md` §5, and the exact
  list of API calls the browser makes on `/` for an expert-only and for an admin session (the
  integrator needs it for the live journey's `root` and `sign-in` entries)

## Required tests

- mutations, each red with its output in the report:
  - the admin tile is absent for an expert-only session (and present for `admin`); a session
    without `admin` that requests `listRegistrations` is red
  - an unknown role label is a typed fault
  - a maximum-length `displayLabel` (66 characters: a 60-character last name, a space and `И. О.`) does not
    widen the page at 780 px — asserted in `home.test.ts` on markup and CSS (the long label sits in
    an element whose rule breaks words), and measured in a browser on the lane stand at 780 × 900
    with an existing instrument unchanged (`tests/e2e/pc01/journey/look.mjs` or `width.mjs`),
    `scrollWidth <= innerWidth` quoted verbatim
  - more than five projects in the cache render exactly five; the newest first
  - a failed `getDashboardSummary` renders the typed error state, not a raw message
- `npm --prefix web test -- --run`; `npm --prefix web run lint -- --quiet`;
  `npm --prefix web run typecheck`
- `npm --prefix web run build` succeeds; the `/` row of the route table is quoted in the report
- the live journey on the lane stand (`npm --prefix web run e2e:pc01 -- --phase all`), summary
  quoted verbatim: `root` and `sign-in` are expected to report undeclared calls until the
  manifest moves — the report lists them; it does not edit the manifest
- `git diff --check`; `make gate` with the literal `GATE OK` on the task's head

## Integration contract

`/` renders `HomePage` from `_pages/home` with the props `W50-REGISTRY-01` fixed; the route file
still calls `requireScreen('/', …)` and nothing else changes in it. The home page reads
`getMe` (if used), `listProjects`, `getDashboardSummary` and — for `admin` only —
`listRegistrations`, through the query keys of `query-keys.ts`; the integrator moves the live
journey's `root` and `sign-in` `expects_api` from the list in the report.

## Failure/idempotency/security cases

- lane `gate-w50home`, worktree `.local/worktrees/w50-home`: `FOUNDATION_INSTANCE=gate-w50home`,
  `POSTGRES_PORT=56660`, `S3_API_PORT=60260`, `S3_CONSOLE_PORT=60261`, a lane-unique `POSTGRES_DB`
  and `S3_BUCKET`; each port checked free with `ss -ltn` before use and recorded; any further port
  the stand needs (API, health, `next start`) checked free the same way and recorded; provisioned
  with `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` and `npm --prefix web ci`; the real
  corpus attached read-only before `make gate`
- one full `make gate` on the host at a time — three Stage-B lanes run in parallel, so each asks
  the integrator for its gate slot; never edit the tree while its gate runs
- owned disposable services only; `make down` and remove the lane's own volumes by exact name at
  the end
- never kill a process by pattern — only confirmed-own PIDs
- no credential, cookie, session id or applicant e-mail in evidence; the stand's accounts are
  invented and disposable
- the admin tile shows a count only: no applicant name, e-mail or reason reaches the home page
- a `listRegistrations` refusal (`permission_denied`) for a session whose roles changed since
  sign-in renders the typed error state, never the count of another answer
- the contrast census renders `/` cold through the registry's seed; a colour rule reached only in
  a loaded state is unreached unless the census renders that state, and `web/tests/unit/styles/**`
  is `W50-SHELL-UI`'s — if the home page needs a loaded-state census seed, stop and ask

## Rollback / feature flag

Revert the commits; `/` returns to the registry's placeholder. No flag, no stored data.

## Handoff

- changed files: listed in `docs/program/W50-HOME-01.md` with `git diff --name-only <base>..<sha>`
  and `git status --porcelain -uall` empty
- commands/results: verbatim with exit status; every mutation with its red output; the browser
  width reading
- known limits: listed, never decided silently — at least the live journey's `root`/`sign-in`
  `expects_api`, which this grant does not cover
- integration notes: hand back branch `agent/w50-home-01` at a recorded SHA
