# W51-ROUTES-01 — five guarded screen addresses

## Result and changed files

From the frozen `5e20fa9f34c8c98d392c22065fedee9a7e3d05c3` base, the route tree,
registry, renderer seeds and PC-01 manifest now enumerate 27 real screens. The
production build also shows the synthetic `/_not-found` row. The three administrator
screens are `session`/`['admin']`; the two registration screens are public, in
`account`, and out of the menu. Administrator menu order is `/admin/users` then
`/admin/registrations`. All five new screens render `RoutePlaceholder` without an
API call. The dynamic user detail receives an opaque `userUid` and uses
`routes.user(userUid)`.

Changed files, grouped by purpose:

- Registry, builder and public filter exports:
  `web/src/shared/config/screen-registry.ts`,
  `web/src/shared/lib/routes.ts`, `web/src/shared/api/index.ts`.
- Route files: `web/src/app/register/page.tsx`,
  `web/src/app/register/submitted/page.tsx`,
  `web/src/app/admin/users/page.tsx`,
  `web/src/app/admin/users/[user_uid]/page.tsx`,
  `web/src/app/admin/registrations/page.tsx`.
- Placeholder slices: `web/src/_pages/register/{index.ts,ui/register-page.tsx}`,
  `web/src/_pages/register-submitted/{index.ts,ui/register-submitted-page.tsx}`,
  `web/src/_pages/admin-users/{index.ts,ui/admin-users-page.tsx}`,
  `web/src/_pages/admin-user/{index.ts,ui/admin-user-page.tsx}`,
  `web/src/_pages/admin-registrations/{index.ts,ui/admin-registrations-page.tsx}`.
- Journey and conformance: `tests/e2e/pc01/journey/manifest.json`,
  `tests/e2e/pc01/journey/journey.mjs`,
  `tests/e2e/test_pc01_journey_conformance.py`.
- Renderer and guard tests: `web/tests/unit/screens/route-screens.ts`,
  `web/tests/guards/screen-registry.guard.test.ts`,
  `web/tests/guards/screen-guard.guard.test.ts`,
  `web/tests/guards/lazy-boundary.guard.test.ts`.
- Live registry pins and route tests: `web/tests/unit/screens/home.test.ts`,
  `web/tests/unit/screens/routes.test.ts`,
  `web/tests/unit/session/return-path.test.ts`,
  `web/tests/unit/shell/navigation.test.ts`,
  `web/tests/unit/shell/screen-decision.test.ts`,
  `web/tests/unit/shell/frame.test.ts`,
  `web/tests/unit/qa_w50/guest-redirects.test.ts`,
  `web/tests/unit/qa_w50/role-gated.test.ts`,
  `web/tests/unit/qa_w50/r66-navigation.test.ts`.
- This report: `docs/program/W51-ROUTES-01.md`.

The integrator's written grants `W51-ROUTES-01-G1` and `W51-ROUTES-01-G2`
on `integration/w51` authorize the three additional test-instrument paths above.
G1 allows only a validated `usr_<ULID>` sample for the no-call user detail placeholder.
The journey takes a captured real identity first, and API expectations never use the
sample. G2 allows only the two new public addresses in the lazy-boundary guard's
public-route expectation. No task, plan or grant file was edited in this lane.

## Verification

Commands ran from `.local/worktrees/W51-ROUTES-01` unless noted:

| Command | Result |
| --- | --- |
| `rg --files web/src/app -g 'page.tsx' \| wc -l` | 27 real route files |
| `.venv/bin/pytest -q tests/e2e/test_pc01_journey_conformance.py` | 81 passed; route/manifest equality and sample rules |
| `npm --prefix web run lint -- --quiet` | exit 0 |
| `npm --prefix web run typecheck` | exit 0 |
| `npm --prefix web test -- --run` | 105 files, 1672 tests passed under escalated execution; unprivileged nested `eslint`/`tsc` spawn was denied by the sandbox |
| `NEXT_PUBLIC_API_BASE_URL=/bff/v1 NEXT_PUBLIC_INSTANCE_LABEL=gate-w51routes npm --prefix web run build` | exit 0; 27 real page rows plus `/_not-found` |
| `git diff --check` | exit 0 |
| `make light-acceptance BASE=d8ea61351489fcf08c7ebfe8ff90045b2127b559` on the final clean branch SHA | `LIGHT ACCEPTANCE OK` |

The lane's own production stand used `gate-w51routes` with PostgreSQL 56760,
MinIO 60360/60361, API 56860 and Next 31360. A socket bind proved all five
ports free immediately before `make up`. `make migrate` reached head
`0015_accounts_roles_registration`; `make check-services` ended
`FOUNDATION-CHECK OK check-services`. The seeded administrator changed its
password and completed its profile through the local API; its returned account
retained `admin`. The stand used an external 0600 credential directory and an
ignored `.env` symlink. `E2E_PC01_ORIGIN`, `E2E_PC01_LOGIN`,
`E2E_PC01_PASSWORD` and the installed Chrome for Testing path were supplied
at runtime. The live `npm --prefix web run e2e:pc01 -- --phase all` preflight
ended `write steps checked: 3/3`, `routes checked: 27/27`,
`e2e:pc01 OK`; each new placeholder recorded `api=0`. Guest GETs to all
three administrator addresses returned real HTTP 307 redirects to
`/login?next=<encoded requested address>`, including a preserved query on
`/admin/users?x=1`.

## Mutation controls

Each mutation was temporary and restored in a `finally` block before the next
run. Commands and red results on this lane:

| Mutation | Controlling command and red result |
| --- | --- |
| Remove the `/register` registry row | `npm --prefix web test -- --run tests/guards/screen-registry.guard.test.ts`: exit 1; `/register` page has no registry row |
| Omit `requireScreen` from `/admin/users` | `npm --prefix web test -- --run tests/guards/screen-guard.guard.test.ts`: exit 1; `/admin/users does not call requireScreen` |
| Offer `/admin/users` to an expert | `npm --prefix web test -- --run tests/unit/qa_w50/role-gated.test.ts tests/guards/screen-registry.guard.test.ts`: exit 1; expert menu and exact admin-role set fail |
| Make `routes.user` ignore its UID | `npm --prefix web test -- --run tests/unit/screens/routes.test.ts`: exit 1; opaque ID delegation and builder totality fail |
| Remove, malform or misname the manifest `user_uid` sample | Three runs of `.venv/bin/pytest -q tests/e2e/test_pc01_journey_conformance.py -k test_user_detail_sample_is_only_for_the_no_call_placeholder`: each exit 1 with its specific sample finding |
| Remove the journey's use of the sample | `.venv/bin/pytest -q tests/e2e/test_pc01_journey_conformance.py -k test_the_journey_consumes_the_declared_sample_only_for_route_address`: exit 1; the journey no longer consumes the declared sample |

The W50 synthetic role controls and R-66 group-order checks remain. The live tests
also refuse expert, empty and unknown role sets on each administrator route.

## Contracts, limits, cleanup and integration

No domain, API, error-catalog, migration, dependency or query-key contract changed.
These are addresses and placeholders only; registration and administrator behavior
belongs to the Stage-B lanes. G1's sample is temporary until ADMIN-USERS renders
a real user link; that lane must replace it with captured identity.

The stand's API and Next processes were stopped by their recorded PIDs. Only
`gate-w51routes` containers, network and named volumes were removed; the external
stand credential directory and the ignored `.env` symlink were deleted. No secret
was put in a tracked file, report or message.

Integrator: inspect and merge the exact clean `agent/w51-routes-01` SHA handed
back with this report onto the grant-bearing `integration/w51` tip. Run the
post-merge R-70 acceptance there. The executor did not merge, push, tag or deploy.

Forbidden-hotspot proof: `git diff --name-only
5e20fa9f34c8c98d392c22065fedee9a7e3d05c3..HEAD` lists only the files in
the changed-file groups above; all product files are within the original grant,
and the three added instrument paths are within G1/G2. No `contracts/**`,
`db/migrations/**`, backend, `infra/**`, Makefile, root lock/dependency,
composition root, global style, `web/src/app/admin/loading.tsx`,
`web/src/shared/api/query-keys.ts`, W50 report, or programme ruling/register
path changed.

Open questions: none.
