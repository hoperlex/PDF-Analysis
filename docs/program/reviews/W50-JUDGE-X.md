# W50-JUDGE-X — independent black-box verdict

**Subject:** `92001f7852266f39ef1f9ab9dd4562c982823a7a` (`integration/w50`, `origin/dev` at dispatch).
**Date:** 2026-10-07. **Branch:** `agent/w50-judge-x`.
**Verdict:** **ACCEPT** for the W50 release candidate. No release-blocking or must-fix-before-merge finding. One register-level wording/transport discrepancy is below. No repair was made.

## Independence and environment

I read `AGENTS.md`, `CURRENT_STATE.md`, the task and its `W50-QA-01` dependency, the frozen W50 plan and freeze before testing. I did **not** read lane or QA reports, nor Judge Y's report, as premise evidence. The first product pass was against the built subject over HTTP. Source inspection came after that pass.

The disposable stand used only worktree `.local/worktrees/w50-jx`, Compose project `gate-w50jx`, database `auditmanager_gate_w50jx` on PostgreSQL `56700`, private bucket `auditmanager-gate-w50jx` on S3 `60300`/console `60301`, subject API `56800`, health `56801`, and `next start` `31300`. All six ports had no listener in `ss -ltn` before use; the API, health and web ports were checked again immediately before their starts. The first sandboxed `ss`/socket attempt was denied by sandbox permissions; the authorized host check succeeded. Before the build, `free -b` reported **4,331,933,696 available bytes**, and `ps` found no `make gate`. The build ran under `flock /root/projects/PDF-Analysis/.local/w50-stage-e-build.lock`. The public alpha stand was not used. All accounts, passwords, cookies and tokens were disposable; their values are omitted here.

| Command or probe invocation | Result |
| --- | --- |
| `git rev-parse HEAD`; `git status --short --branch` | `92001f7852266f39ef1f9ab9dd4562c982823a7a`; clean `agent/w50-judge-x`, exit 0 |
| `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` | `bootstrap OK`, exit 0 |
| `npm --prefix web ci --no-audit --no-fund` | 184 pinned packages installed, exit 0 |
| `make up` | three `gate-w50jx` services healthy, exit 0 |
| `make migrate && make check-db && make check-services` | migration head `0015_accounts_roles_registration`; `FOUNDATION-CHECK OK check-db` and `check-services`, exit 0 |
| `flock /root/projects/PDF-Analysis/.local/w50-stage-e-build.lock npm --prefix web run build` | production Next 15.5.25 build, 22 UI routes and BFF, exit 0 |
| `.venv/bin/python infra/deploy/serve.py` and `npm --prefix web run start -- -p 31300 -H 127.0.0.1` | own API/health and production web listeners ready; `GET /healthz` returned 200 |
| `/tmp/w50jx-blackbox1.py`, `/tmp/w50jx-blackbox2.py`, `/tmp/w50jx-redirects.py`, `/tmp/w50jx-auth.py` | route/lock/redirect HTTP probes described below, each exit 0 |
| `/tmp/w50jx-keyboard.mjs` | first exit 1 from **two erroneous probe expectations** that previously open disclosures remain open after focus leaves; corrected expectations and full rerun exit 0 |
| `/tmp/w50jx-routes.mjs`, `/tmp/w50jx-r66.mjs` | complete browser route sweep and R-66 stub probe, each exit 0 |
| `/tmp/w50jx-lock-probe.py`, `/tmp/w50jx-lock-probe-fresh.py`, `/tmp/w50jx-prefetch-inspect.py` | temporary disposable-DB state probes, each exit 0; old columns restored in `finally` |

The `/tmp/w50jx-*` scripts and all temporary credentials were removed after the pass. They were harnesses for this subject, not submitted product changes. The findings below give requests and observed responses without credential material.

## Registry and navigation

The subject registry has **22 rows: 18 `session`, two `open-to-default-credential`, two `public`**. Its live **role-gated set is empty**: all 22 rows have `roles: 'any'` (`web/src/shared/config/screen-registry.ts:75-196`). Therefore there is no live address on which to navigate with “the other role”; this is a measured vacuity, not a role-denial pass. The direct-access matrix covered all 22 rows, including the six dynamic templates with well-formed, nonexistent opaque IDs.

For each of the 20 protected concrete addresses, including a `?view=table&page=2` query, a guest got **307** to `/login?next=<encoded exact path and query>`. `/login` and `/403` returned 200. A fresh default-credential session got 307 to `/account/password` at all 18 `session` addresses, while `/account` and `/account/password` returned 200; `/login` redirected to `/`. A fresh changed-password but incomplete-profile session got 307 to `/account` at all 18 `session` addresses; the two account screens returned 200 and `/login` redirected to `/`. A complete-profile administrator opened all 20 protected addresses (200), `/403` (200), and was redirected from `/login` to `/`. There was no redirect cycle or framework error.

The concrete set was `/`, `/403`, `/account`, `/account/password`, `/analysis-settings`, `/blocks`, `/dashboard`, `/knowledge-base`, `/login`, `/logs`, `/norms`, `/optimisation`, `/projects`, the project detail and its document, run, run review, version and comparison children, `/queue`, `/section-optimisation`, and `/workers`. Representative exact results:

```text
guest GET /projects?view=table&page=2 -> 307 /login?next=%2Fprojects%3Fview%3Dtable%26page%3D2
guest GET /projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8A?view=table&page=2 -> 307 /login?next=%2Fprojects%2Fprj_01J9ZQ8K7NHVXW3T2R5M6P4Q8A%3Fview%3Dtable%26page%3D2
default GET /projects -> 307 /account/password
incomplete GET /projects -> 307 /account
complete GET /projects -> 200
complete GET /login -> 307 /
```

The browser independently visited every one of the 22 concrete addresses as guest and as the complete administrator at **780 × 900**. Each landed at the expected path; each produced **0 new console errors, 0 uncaught page exceptions, no “Application error”, and `scrollWidth <= innerWidth`**. The six dynamic detail addresses used nonexistent IDs: this proves shell/guard/error-state stability, not successful loading of a real project or run.

The visible menu has the R-66 order: **Работа** — Проекты, Дашборд, Оптимизация разделов; **Знания** — База знаний, Блоки, Нормы; **Система** — Журнал выполнения, Исполнители, Настройки анализа, Очередь. `/optimisation` is absent from all menu links but opened by direct address with a complete session. Each of `/section-optimisation`, `/norms`, `/analysis-settings`, `/queue` rendered a `role=status` `RoutePlaceholder` at its own `data-route`, with “не готов”/“недоступен”, no digit and no table/row; no console or page error.

## Redirect and lock probes

Each value below was sent as `GET /login?next=<value>`, as the sign-in form's `next`, and as `POST /bff/v1/session`'s `next`. The same invalid values were sent as `/403?from=<value>`. An invalid value was absent from the form's hidden `next` field, absent from visible `/403` text, and never became an external `Location`.

| Input class | Concrete value | Form hidden field | BFF after sign-in |
| --- | --- | --- | --- |
| protocol-relative | `//attacker.example/x` | absent | `303 /` |
| slash/backslash | `/\attacker.example/x` | absent | `303 /` |
| schemes | `https://attacker.example/x`, `javascript:alert(1)` | absent | `303 /` |
| encoded separators in path | `/%2F%2Fattacker.example`, `/%5Cattacker.example` | absent | `303 /` |
| encoded CR/LF in path | `/projects%0D%0ALocation:%20https://attacker.example` | absent | `303 /` |
| literal CR/LF | `/projects?x=\r\nLocation: https://attacker.example` | absent | `303 /` |
| over 512 characters | `/projects?x=` plus 510 `a`s | absent | `303 /` |
| unregistered address | `/ghost` | absent | `303 /` |
| valid path/query | `/projects?x=1` | present, exact | `303 /projects?x=1` |
| valid path, hostile query value | `/projects?return=https://attacker.example&x=%0d%0aLocation%3Aevil` | present, exact | `303` to the same relative `/projects?...` |

The hostile query remains after `?` in a same-origin relative path. Encoded CR/LF is not an HTTP header break; a **literal** CR/LF was refused. A stale cookie captured before changing the disposable account's password got `307 /login?next=%2Fprojects` on `/projects`; the old session did not open the page. Direct `GET /bff/v1/projects` was 403 for both the default and incomplete profile; `GET /bff/v1/me` remained 200 so each account could see its own state.

For prefetch, I set and later restored the two account-state columns in **only the disposable database**, then signed in afresh in each state. Ordinary `GET /projects`, `/projects?next=%2Fqueue` and `/queue` answered 307 to the proper lock screen. Requests with `Next-Router-Prefetch: 1` and `RSC: 1` answered **200 `text/x-component`**, with a 163-byte router-tree header and no protected page text, no `Location` and no redirect marker. Thus the transport does not return a literal HTTP redirect for prefetch, but the prefetch did not expose a screen, and subsequent ordinary navigation and direct BFF calls remained blocked. A separate deliberately unsupported mutation changed those DB flags under an **already open** cookie without moving its credential epoch: the cached web subject rendered the shell (200), while the API still answered 403. Real password change revoked the cookie, and no supported product operation here reverts a completed profile; this synthetic state change is recorded as a limitation of that probe, not an observed product bypass.

## Keyboard and width

Real Chrome DevTools key events, not synthetic DOM events, drove the production shell. At 780 px, Tab reached the stacked **Меню** disclosure; Enter opened it. Each of Работа, Знания and Система opened by Space/Enter and showed exactly its R-66 links in order. The previous disclosure closed on focus leaving it; this explained the two false failures in the initial exploratory script, and the corrected full rerun exited 0. The account trigger opened by Enter and Space, focused Профиль, moved with ArrowDown/ArrowUp, jumped to Выйти/Профиль with End/Home, closed on Escape with focus returned to the trigger, closed on Tab and on an outside click, and submitted Выйти by keyboard. A following `/projects` navigation landed on `/login`. At 1280 px the groups displayed in one row; Enter and Escape opened/closed a group.

The disposable profile supplied an actual **66-character `displayLabel`** and **254-character e-mail**. At 780 × 900, `document.documentElement.scrollWidth` was 780 or less in closed stacked navigation, each open group, the open account menu and every registered route. At 1280 × 900 the row state measured `scrollWidth=1280`. Browser console/page errors remained `0/0` throughout the keyboard drive.

## Findings and limitations

### Register R1 — invalid query input appears in Next's raw Flight metadata

`web/src/app/login/page.tsx:36-49`, `web/src/app/403/page.tsx:21-25`; the claim is at `web/src/shared/config/screen-registry.ts:326-329`. Reproduction: `GET /login?next=https%3A%2F%2Fattacker.example%2Fx` and `GET /403?from=https%3A%2F%2Fattacker.example%2Fx`. Both returned 200; the invalid raw string occurred inside Next's escaped `__PAGE__?{...}` router-state script in the HTML (`raw_in_html=True`), while `raw_in_visible=False`, no hidden `next` input was rendered, and a direct BFF sign-in with that `next` returned `303 /`. Consequence: the absolute statement “never echoed” is false for raw framework transport bytes. I found no visible UI injection, external redirect, or protected-data exposure. A canonicalizing redirect before render would be needed if the raw-byte promise is intended. **Register only**; this does not block the W50 candidate.

No release-blocking or must-fix-before-merge finding was reproduced. The role-denial path cannot be exercised on a real W50 row because the measured role-gated set is empty. The dynamic-route browser pass used nonexistent domain IDs and did not exercise business data. The 200 RSC prefetch is an internal transport observation, not a rendered-screen bypass. The first browser probe's two red assertions were probe mistakes and the corrected complete rerun was green. Cross-examination with Judge Y is pending until that independent primary report is available; it was not used to reach this verdict.

## Cleanup, contracts, handoff

Only the judge-owned API and Next PIDs were stopped after confirming their command lines. `make down` removed only `gate-w50jx` containers/network; `docker volume rm gate-w50jx-postgres-data gate-w50jx-s3-data` removed only its two volumes. A final `ss -ltn` found no listener on any of the six assigned ports; Docker container and volume lists had no `gate-w50jx-` entry. The mode-0600 temporary account, cookie, token and e-mail files, stand session store, `.env`, `web/.env.local`, temporary probes, and the worktree's ignored build artifacts were removed. No credential, cookie, session ID or token appears in this report.

**Changed tracked file:** `docs/program/reviews/W50-JUDGE-X.md` only. **New/changed contracts:** none. **Forbidden hotspots:** untouched. **Integrator:** accept `agent/w50-judge-x` at the report commit for the primary verdict; treat R1 as register-level and arrange the independent X/Y cross-examination after both primary reports. No merge, push, tag or deployment is authorized by this judge task.
