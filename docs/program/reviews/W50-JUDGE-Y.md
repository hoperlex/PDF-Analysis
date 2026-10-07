# W50-JUDGE-Y — independent architecture verdict

**Subject:** `92001f7852266f39ef1f9ab9dd4562c982823a7a` (`integration/w50` = `origin/dev` at the start of this pass).
**Date:** 2026-10-07. **Branch:** `agent/w50-judge-y`.
**Primary verdict:** **PASS with two register findings about prose**. There are no release-blocking or must-fix-before-merge findings. I completed the primary pass and recorded this verdict without reading lane, QA, or Judge X reports.

## Scope and environment

I read `AGENTS.md`, `docs/program/CURRENT_STATE.md`, `docs/program/tasks/W50-JUDGE-Y.md`, its `depends_on` task (`W50-QA-01.md`), `docs/program/dispatch/W50-PLAN.md`, `docs/program/W50-FREEZE-01.md`, and `docs/program/dispatch/W48-JUDGES.md`. The subject matched both `HEAD` and `origin/dev`. I checked the frozen inputs: `git ls-tree HEAD web/package.json web/package-lock.json web/FRONTEND_LOCK.json` returned the P-01 blobs `3ea4aede04af84823821e115f8312c545faec30e`, `3b986e543b1be7fc654d94aee17963382f664143`, and `14fc4b48026640a195f8dd1e66a09a6ff7251666`. `git diff --name-only ead639f HEAD -- contracts db/migrations web/src/_app/providers.tsx web/package.json web/package-lock.json web/FRONTEND_LOCK.json` returned nothing. There are no new contracts; the migration head remains `0015_accounts_roles_registration`.

The toolchain was Node `v22.23.1` and Next `15.5.25`. I measured all builds in one disposable clone, `.local/w50-jy-build`, with one `npm ci --offline` and a clean `web/.next` before each checkout/build. Before every build, `df -B1` showed more than 3 GB available (19–21 GB during this pass), and `ps` found no `make gate`. Every `next build` ran under `flock -x .local/w50-stage-e-build.lock`. I did not run the full `make gate`, following `AGENTS.md` §8. I created no stand services or port reservations. The evidence contains no credential, cookie, or session value.

## Architecture checks

- `web/tests/guards/eslint-boundary.guard.test.ts` tests a deep import, an upward import, raw fetch, and a legal control import. I also inserted `@/widgets/dashboard` into a **copy** of `web/src/entities/account/model/account.ts`: `npm --prefix web run lint -- --quiet` exited 1 with `no-restricted-imports` and `FSD boundary: entities may not import widgets`. Lint exited 0 after restoration. `transport-boundary.guard.test.ts` passed; inserting a direct `fetch` outside `shared/api` in a copy of the frame made that guard red (below).
- `rg -n 'href=' web/src/_app` on the subject found only `HOME_SCREEN`, `SIGN_IN_SCREEN`, `home.address`, and `item.href`; `frame-sources.test.ts` also parses literals in every `_app` TS/TSX module. The frame's sign-out action is `SESSION_CLOSE_PATH` from the feature. Replacing `href={HOME_SCREEN}` with `href="/projects"` in a copy produced the expected red result.
- The registry, the `page.tsx` tree, the journey manifest, and `SEEDS` in `route-screens.ts` cover the same set of **23** screens. For every page, `screen-guard.guard.test.ts` checks the expected `await requireScreen('<own address>', { params, searchParams })`; no executable code under `web/src` retains `requireAChangedPassword`. A one-row drift in each of these four sources turned its guard red and named `/queue` or `/dashboard` (below). The static guards check the real call and the guest/default-credential/incomplete-profile/role decisions. The live registry has only `any` rows, so the role-gated decision uses a fixture, as `R-60` requires.
- `R-66`: `SCREEN_REGISTRY` has the groups and order Work (`Работа`): `/projects`, `/dashboard`, `/section-optimisation`; Knowledge (`Знания`): `/knowledge-base`, `/blocks`, `/norms`; System (`Система`): `/logs`, `/workers`, `/analysis-settings`, `/queue`. `/optimisation` is `hidden`, `inMenu: false`, `session`, and directly reachable. The four new stubs are `session`/`any` and render `RoutePlaceholder` without invented numbers. The relevant registry and QA tests passed.
- Five lazy wrappers use `next/dynamic` and declare typed loading states. `lazy-boundary.guard.test.ts` scans static import edges out of `_pages`, forbids an eager-seam provider in production code, and finds each widget in the census markup. A direct measurement in the disposable clone with a temporary `console.log` yielded **90 screens / 171 light pairs / 171 dark pairs**, above the frozen baseline of **80 / 150 / 150**. Removing one eager provider made the dashboard check red. `rendered-language.guard.test.ts` and `screen-claims-about-the-system.guard.test.ts` passed.
- `styling-layer.test.ts` found a rule for every named `am-` class; removing `.am-app__brand` in a copy made it red. The avatar palette test verified **14 pairs × 2 themes**, text contrast ≥4.5:1, and circle contrast against the page and bar ≥3:1; making the first light background white made it red. `Avatar` receives `colourKey={session.login}` (the e-mail), rather than `displayLabel`. `entities/account` raises `UnknownRoleError` for an unknown role; the frame and home page show explicit fault states, and the BFF refuses malformed `getMe` and session rows. The new code inspection found no business logic in UI components, deep import, or silent fallback.

## Bundle: exact gzip-9 bytes

For every `.../page` entry in `.next/app-build-manifest.json`, I summed `zlib.gzipSync(file, {level: 9}).length` over its listed `.js` files; CSS is excluded. All four builds (`96a1653`, `d0d71ad`, `d8112cb`, and the subject) exited 0. Repeat clean builds of `d8112cb` and the subject produced byte-identical route totals. The first delta below is Stage A → LAZY; the second is Stage B → subject.

For the second delta, `F` is the shared webpack chunk **−4 B** plus the changed client/frame chunk `4229` **+730 B**, totaling **+726 B**. Its cause is the Stage C `_app` navigation/account islands and the move of `screenDecision` into shared config. `N` adds **+23 B** in shared chunk `4327` on routes that list it. Additional changes in `page`, `1423`, and `3543` are stated exactly in the table; they are rebundles of existing page/shared chunks after the same Stage C imports, with no code from another lane. `/_not-found` lists only the changed webpack chunk. `git diff --name-only d8112cb 92001f7852266f39ef1f9ab9dd4562c982823a7a -- web/src` is limited to `_app/*`, `app/layout.tsx`, `app/bff/session/screen-lock.ts`, and `shared/config/*`, leaving no unexplained product delta.

| Route | Stage A | LAZY | Δ A→L | Stage B | Subject | Δ B→S | B→S cause |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `/` | 111388 | 112120 | +732 | 135351 | 136099 | +748 | F+N; page −1 |
| `/403` | 123327 | 124064 | +737 | 126880 | 127606 | +726 | F |
| `/_not-found` | 102681 | 103417 | +736 | 103403 | 103399 | −4 | webpack −4 |
| `/account` | 111388 | 112120 | +732 | 118321 | 119047 | +726 | F |
| `/account/password` | 114756 | 115493 | +737 | 118306 | 119032 | +726 | F |
| `/analysis-settings` | 111388 | 112120 | +732 | 118321 | 119047 | +726 | F |
| `/blocks` | 135389 | 136120 | +731 | 137808 | 138558 | +750 | F+N; 1423 +1 |
| `/dashboard` | 142653 | 117579 | **−25074** | 122651 | 123400 | +749 | F+N |
| `/knowledge-base` | 129496 | 127144 | **−2352** | 132209 | 132953 | +744 | F+N; page −5 |
| `/login` | 111388 | 112120 | +732 | 118321 | 119047 | +726 | F |
| `/logs` | 111388 | 112120 | +732 | 118321 | 119047 | +726 | F |
| `/norms` | 111388 | 112120 | +732 | 118321 | 119047 | +726 | F |
| `/optimisation` | 111388 | 112120 | +732 | 118321 | 119047 | +726 | F |
| `/projects` | 133074 | 133717 | +643 | 135407 | 136156 | +749 | F+N |
| `/projects/[project_uid]` | 138987 | 139719 | +732 | 141408 | 142180 | +772 | F+N; 1423 +1, page +22 |
| `/projects/[project_uid]/documents/[document_uid]` | 134675 | 135407 | +732 | 137096 | 137846 | +750 | F+N; 1423 +1 |
| `/projects/[project_uid]/runs/[run_id]` | 139365 | 131583 | **−7782** | 133285 | 134034 | +749 | F+N |
| `/projects/[project_uid]/runs/[run_id]/review` | 145215 | 146585 | +1370 | 148283 | 149030 | +747 | F+N; 3543 −1, page −1 |
| `/projects/[project_uid]/versions/[version_uid]` | 146274 | 147308 | +1034 | 148997 | 149766 | +769 | F+N; 3543 −1, 1423 +1, page +20 |
| `/projects/[project_uid]/versions/[version_uid]/comparison` | 145911 | 136045 | **−9866** | 137733 | 138483 | +750 | F+N; 1423 +1 |
| `/queue` | 111388 | 112120 | +732 | 118321 | 119047 | +726 | F |
| `/section-optimisation` | 111388 | 112120 | +732 | 118321 | 119047 | +726 | F |
| `/workers` | 111388 | 112120 | +732 | 118321 | 119047 | +726 | F |

The normative Stage A → LAZY comparison satisfies §3.4: the four routes that carried their widget on first load decreased; every other route grew by at most **1370 B**, below **1536 B**. The evidence viewer on `/review` was not a first-load widget; its route's +1370 B falls within the permitted runtime cost.

## Checks and red probes

On the clean subject in the disposable clone:

| Command | Result |
| --- | --- |
| `npm --prefix web ci --offline --no-audit --no-fund` | exit 0, 184 packages, lock unchanged |
| `npm --prefix web run lint -- --quiet` | exit 0 |
| `npm --prefix web run typecheck` | exit 0 |
| `npm --prefix web test -- --run` | exit 0, **105 files / 1660 tests passed** |
| `/root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/e2e/test_pc01_journey_conformance.py tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py tests/contract/program/test_wave_governance.py` | exit 0, **163 passed** |
| `git diff --check` | exit 0 |

The first sandbox run of `npm ci` exited 1: the `esbuild` child returned `spawnSync … EPERM`; the auto-reviewed escalated rerun exited 0. The first sandbox run of `npm test` exited 1 with six fixture failures due to `spawnSync eslint EPERM` and empty child `tsc` output; the escalated rerun above passed in full. These were sandbox subprocess limits, not subject failures.

I made every probe below only in the disposable clone, then restored its file byte for byte; its final `git status --short` was empty. Each listed test ran as `npm --prefix web test -- --run <test>`, except the Python journey and FSD lint probes.

| Mutation in the copy | Red guard and result |
| --- | --- |
| Registry `/queue` → `/queue-drift` | `screen-registry.guard.test.ts` exit 1, 4 failures; `unregistered: /queue`, pageless drift, and R-66 order |
| Removed `await requireScreen('/dashboard', { params, searchParams })` from the dashboard route | `screen-guard.guard.test.ts` exit 1, 2 failures, naming `/dashboard` |
| Frame `href={HOME_SCREEN}` → `href="/projects"` | `frame-sources.test.ts` exit 1, `app-frame.tsx:82: /projects` |
| Added a static dashboard widget import from `_pages` | `lazy-boundary.guard.test.ts` exit 1, naming the static edge |
| Set `DashboardEagerSeam.Provider` to `value: null` | `lazy-boundary.guard.test.ts` exit 1, `dashboard cold does not draw dashboard` |
| Renamed the `.am-app__brand` rule | `styling-layer.test.ts` exit 1, missing `am-app__brand` |
| Made light avatar pair 01 background white | `avatar-palette.test.ts` exit 1, 4 contrast failures |
| Replaced the footer with «Ролей нет.» | `screen-claims-about-the-system.guard.test.ts` exit 1, 2 failures, including the rendered census |
| Inserted `fetch('/api/v1/projects')` in the frame | `transport-boundary.guard.test.ts` exit 1, boundary violation |
| Journey `/queue` → `/queue-drift` | `test_pc01_journey_conformance.py` exit 1, **2 failed / 76 passed**, naming `/queue` |
| Seed `/queue` → `/queue-drift` | `screen-set.guard.test.ts` exit 1, 3 failures, missing `/queue` and orphan `/queue-drift` |
| Upward import `entities/account` → `widgets/dashboard` | `npm --prefix web run lint -- --quiet` exit 1, `no-restricted-imports`: `entities may not import widgets` |

## Findings

**JY-1 — register: the menu decision comment overstates completeness.** `web/src/shared/config/screen-registry.ts:250–254` says the menu cannot hide a screen that `screenDecision` opens. `web/src/_app/navigation.ts:74–80` also filters by `inMenu` and visible menu groups. The registry's `/optimisation` row (`:180–186`) is `session`/`any`, `hidden`, and `inMenu: false`: a complete session can open the direct URL, while the menu correctly hides it. The misleading architecture claim could prompt removal of the hidden route required by R-66. Reproduce by comparing `screenDecision(screenAt('/optimisation'), completeSubject) === 'open'` with `buildNavigation(completeSubject)`, whose addresses exclude it. Correct the comment to say that the menu offers open **inMenu rows in visible groups**; no code change is needed.

**JY-2 — register: the controlling plan contradicts the measured baseline.** After its amendment, `docs/program/dispatch/W50-PLAN.md:108–115` requires first-load JS to fall on “five target routes”, but the same paragraph gives only four negative deltas. The Judge Y task corrects the subject to “four routes that carry their widget on first load”. In my measurement, `/projects/[project_uid]/runs/[run_id]/review` grew by **1370 B** within the allowed bound, while the other four routes fell. A future judge reading only §3.4 could reject a correct build or treat its result as an unexplained exception. Reproduce from the four negative table rows above and `/review` at +1370 B. Correct the plan to name the four first-load routes and separately explain the review fallback/runtime cost. No runtime code change is needed.

## Limits and handoff

This entry point checks topology, source guards, exact bundles, and static rendering. I did not test real browser focus, outside clicks, HTTP status, or stand console output; those are the black-box Judge X/QA scope. The FSD and transport guards have the usual source-scan/ESLint limit: they do not prove the absence of runtime `eval` or generated code, and W50 adds no such path. The bundle comparison is for this Next 15.5.25 build and manifest gzip-9 sizes, rather than network cache behavior.

Integrator: carry the two register items as documentation corrections under a future authorized grant. The integration contract opens `W50-FIX` only for upheld release-blocking findings, and this pass found none. My only changed tracked file is `docs/program/reviews/W50-JUDGE-Y.md`; contracts, migrations, root manifests and locks, the composition root, and all other forbidden hotspots were untouched. Final commit proof: `git diff --name-only 92001f7852266f39ef1f9ab9dd4562c982823a7a..HEAD` names only this file.
