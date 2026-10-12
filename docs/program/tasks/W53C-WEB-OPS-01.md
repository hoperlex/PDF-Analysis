# Task W53C-WEB-OPS-01 — Execution screens show fresh data and stay readable when the account read fails

## Outcome
Execution screens show fresh data and stay readable when the account read fails, release notices fetch once, survive a missing build id and unknown note kinds, and the history item appears only where it can work (C-26…C-30).

## Depends on
- `W53-CLOSE-PLAN` (this wave's plan commit on `integration/w53-close`)

## Frozen inputs
- domain contract: `contracts/domain/v1` at base, unchanged
- API contract: `contracts/api/v1/openapi.json` at base (SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`), unchanged
- analysis/comparison/event contract: unchanged
- migration head: `0017_execution_queue`
- base commit: the `W53-CLOSE-PLAN` commit on `integration/w53-close`, itself on `origin/dev` `872266038a83568b56f6302f01b97771b9aaf281`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: none

The findings come from the 2026-10-12 static review of `872266038a83568b56f6302f01b97771b9aaf281`; `docs/program/dispatch/W53-CLOSE-PLAN.md` §2 lists them. Re-read each cited location before changing it and report any finding that no longer reproduces instead of changing code for it.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

The lane commits only on `agent/w53c-web-ops`; the integrator merges and publishes.

## Allowed paths
- `web/src/_app/release-notices.tsx`, `web/src/_app/release-notices.module.css`, `web/src/_app/account-menu.tsx`
- `web/src/entities/release/**`, `web/src/entities/execution/**`
- `web/src/features/{mark-release-notes-read,cancel-run,pause-execution,reaudit-run,set-job-priority,start-run}/**`
- `web/src/widgets/{execution-queue,execution-journal,version-history}/**`
- `web/src/_pages/{queue,logs}/**`
- `web/src/shared/api/version-check.ts`, `web/src/shared/config/env.ts`
- `tests/e2e/pc01/journey/cdp.mjs`, `tests/e2e/pc01/journey/write.mjs`
- `web/tests/unit/**` test files covering the files above (existing or new)
- `docs/program/W53C-WEB-OPS-01.md` (hand-back report)

## Forbidden hotspots
- `contracts/**` (no API, domain, event or error-catalog change in this wave)
- `db/migrations/**` (head stays `0017_execution_queue`)
- root dependency and lock files (`pyproject.toml`, `uv.lock`, `requirements/**`, `web/package.json`, `web/package-lock.json`)
- `Makefile`, `tests/support/**`, every `conftest.py`, global styles (`web/src/app/globals.css`)
- `VERSION`, `release-notes/**`, `docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`
- any path owned by another `W53C-*` lane (see `docs/program/dispatch/W53-CLOSE-PLAN.md` §4)

## Non-goals
- re-audit visibility keyed to run state (needs an API field; deferred); identity screens (WEB-ID); BFF routes (EDGE)

## Deliverables
- C-26: queue and journal queries use `staleTime: 0` (still refetch on focus and on request); `useStartRun` also invalidates `queryKeys.execution.all()`. Test the invalidation set.
- C-27: the queue renders its rows when `getMe` fails; only the controls are withheld, with a short Russian note.
- C-28: «История версий» is offered only to sessions with a complete profile and a changed credential (the same condition the API applies).
- C-29: `ReleaseNotices` uses one focus/visibility listener and no mount-time `refetch`; a missing web build id disables the update banner instead of throwing during render; an unknown release-note kind renders with a generic label instead of throwing.
- C-30: `cdp.mjs` records the navigation-attempt count on rejection as well, so `write.mjs` never reports the previous route's count.

## Required tests
- command: `git diff --check`; `.venv/bin/ruff check` on changed Python; `.venv/bin/python -m compileall -q` on changed modules; for web, `npm --prefix web run lint`, `npm --prefix web run typecheck` and `npx --prefix web vitest run <touched test files>`; for backend, the touched test modules (DB-backed ones on the private ports below, one run at a time)
- expected: all exit 0; every new behaviour has a test that fails without the change (state how you showed it)
- private ports: none — container-free

## Integration contract
The integrator merges `agent/w53c-web-ops` as is after reading the diff and the report. Everything outside the allowed paths is unchanged; no contract, migration, dependency or published ref moves.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; kill only PIDs you started. Never touch the working stand, another lane's ports or containers, the main checkout or any published ref.
- Remove your private containers and volumes before handing back; prove containment with `git status --porcelain -uall` and `git diff --name-only <base>..HEAD`.
