# Task W53C-IDENTITY-01 — An account without roles reads no product data (`R-80`)

## Outcome
An account without roles reads no product data (`R-80`), `updateUser` cannot deadlock or answer an archived account, the current-password check is braked, and dead role code is gone (C-07 API half, C-08…C-11).

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

The lane commits only on `agent/w53c-identity`; the integrator merges and publishes.

## Allowed paths
- `src/auditmanager/access/**`
- `src/auditmanager/api/security.py`
- `src/auditmanager/bootstrap/adapters.py` — only `AccountAdapter`
- `tests/integration/access/**`, `tests/integration/auth/**`
- `tests/integration/api/test_role_register.py`, `tests/integration/api/test_authorization.py`, `tests/integration/api/test_user_management.py`, `tests/integration/api/test_identity_rules.py`
- any other existing test that literally pins the operation-role map, **only** its role-map literal lines — name each in the report
- `docs/program/W53C-IDENTITY-01.md` (hand-back report)

## Forbidden hotspots
- `contracts/**` (no API, domain, event or error-catalog change in this wave)
- `db/migrations/**` (head stays `0017_execution_queue`)
- root dependency and lock files (`pyproject.toml`, `uv.lock`, `requirements/**`, `web/package.json`, `web/package-lock.json`)
- `Makefile`, `tests/support/**`, every `conftest.py`, global styles (`web/src/app/globals.css`)
- `VERSION`, `release-notes/**`, `docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`
- any path owned by another `W53C-*` lane (see `docs/program/dispatch/W53-CLOSE-PLAN.md` §4)

## Non-goals
- screens (WEB-ID owns the web half of `R-80`); `R-81` self-grant stays allowed
- the pending-request vs account login collision; email verification; the admin-known temporary password (D-130)

## Deliverables
- C-07 (`R-80`): in `api/security.py` every product-data read (projects, documents, versions, blocks, runs, findings, decisions, dashboard, `listExecutionQueue`, `listExecutionJournal`) requires **any one** role (`expert` or `admin`); `getMe`, `updateMyProfile`, `changePassword`, `markReleaseNotesRead`, `getProductVersion`, `listReleases` stay open to any complete account. Refusal is the existing `permission_denied` with a `required_capability`. Update the literal register in `test_role_register.py` with a comment citing `R-80`. An empty role set stays settable.
- C-08: `AccountAdapter.update_account` takes the admin-set lock before writing names whenever `roles` is present (e.g. apply roles first, or lock first); add a test that a combined names+roles PATCH follows the documented order (two-connection test if cheap, otherwise an order assertion).
- C-09: an empty update (both fields absent) on an archived account answers `not_found` like `update_names`; test it.
- C-10: a wrong current password in `changePassword` counts against the same per-account brake as a failed sign-in; test the lockout after the brake's limit.
- C-11: delete `AccountRepository.revoke_role` (no production caller) or make it refuse archived accounts; prefer deletion.

## Required tests
- command: `git diff --check`; `.venv/bin/ruff check` on changed Python; `.venv/bin/python -m compileall -q` on changed modules; for web, `npm --prefix web run lint`, `npm --prefix web run typecheck` and `npx --prefix web vitest run <touched test files>`; for backend, the touched test modules (DB-backed ones on the private ports below, one run at a time)
- expected: all exit 0; every new behaviour has a test that fails without the change (state how you showed it)
- private ports: PostgreSQL `57030`, S3 `60630/60631`, instance `gate-w53c-identity`

## Integration contract
The integrator merges `agent/w53c-identity` as is after reading the diff and the report. Everything outside the allowed paths is unchanged; no contract, migration, dependency or published ref moves.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; kill only PIDs you started. Never touch the working stand, another lane's ports or containers, the main checkout or any published ref.
- Remove your private containers and volumes before handing back; prove containment with `git status --porcelain -uall` and `git diff --name-only <base>..HEAD`.
