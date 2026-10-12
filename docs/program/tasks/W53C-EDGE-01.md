# Task W53C-EDGE-01 — The BFF form doors refuse cross-site requests

## Outcome
The BFF form doors refuse cross-site requests, a re-sign-in closes the previous session, the API signing key no longer rides on unauthenticated forwards, the edge sends security headers, and the session subject follows a self-edit (C-15…C-19).

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

The lane commits only on `agent/w53c-edge`; the integrator merges and publishes.

## Allowed paths
- `web/src/app/bff/**`
- `web/src/shared/api/credentialed-forward.ts`, `web/src/shared/config/proxy-trust.ts`
- `infra/deploy/proxy/nginx.conf`, `infra/deploy/proxy/tls-server.conf`
- `web/tests/unit/session/**`, `web/tests/unit/api/**`, new files under `web/tests/unit/qa_w49/`
- `tests/contract/test_proxy_rate_limits.py`, `tests/integration/composition/test_proxy_tls_path.py`, new `tests/contract/test_proxy_security_headers.py`
- `docs/program/W53C-EDGE-01.md` (hand-back report)

## Forbidden hotspots
- `contracts/**` (no API, domain, event or error-catalog change in this wave)
- `db/migrations/**` (head stays `0017_execution_queue`)
- root dependency and lock files (`pyproject.toml`, `uv.lock`, `requirements/**`, `web/package.json`, `web/package-lock.json`)
- `Makefile`, `tests/support/**`, every `conftest.py`, global styles (`web/src/app/globals.css`)
- `VERSION`, `release-notes/**`, `docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`
- any path owned by another `W53C-*` lane (see `docs/program/dispatch/W53-CLOSE-PLAN.md` §4)

## Non-goals
- the outer TLS topology, guest-throttle keying and `Secure` behind an outer terminator (needs a production probe; deferred)
- removing `AUDITMANAGER_API_TOKEN` from the web container's environment (compose change; later)

## Deliverables
- C-15: `/bff/v1/session`, `/bff/v1/session/end`, `/bff/v1/session/password` and `/bff/v1/registration` refuse a request whose `Sec-Fetch-Site` is `cross-site`, or whose `Origin` is present and not the request's own origin, **before** the throttle or the form body is read; same-origin and header-less (curl, no-JS same-site) requests still work. Tests for cross-site refusal and same-origin acceptance on each door.
- C-16: opening a session closes the session id the request already carries (row deleted, file rewritten). Test.
- C-17: the three `security: []` operations (token exchange, registration status, registration submit) are forwarded **without** an `Authorization` header; reconcile the contradictory comments. Tests assert the header is absent.
- C-18: nginx adds `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` plus `Content-Security-Policy: frame-ancestors 'none'`, `Referrer-Policy: same-origin` on every proxied response (`always`), and `Strict-Transport-Security` only in `tls-server.conf`. Mind nginx's `add_header` inheritance (a location with its own `add_header` drops the server-level ones). A static test pins them.
- C-19: the BFF refreshes the session subject after a successful self-targeted `PATCH /users/{uid}` (same as `PATCH /me`); `subject.ts` initials take the first upper-case code point without locale expansion (`ß` stays one letter).

## Required tests
- command: `git diff --check`; `.venv/bin/ruff check` on changed Python; `.venv/bin/python -m compileall -q` on changed modules; for web, `npm --prefix web run lint`, `npm --prefix web run typecheck` and `npx --prefix web vitest run <touched test files>`; for backend, the touched test modules (DB-backed ones on the private ports below, one run at a time)
- expected: all exit 0; every new behaviour has a test that fails without the change (state how you showed it)
- private ports: none — container-free

## Integration contract
The integrator merges `agent/w53c-edge` as is after reading the diff and the report. Everything outside the allowed paths is unchanged; no contract, migration, dependency or published ref moves.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; kill only PIDs you started. Never touch the working stand, another lane's ports or containers, the main checkout or any published ref.
- Remove your private containers and volumes before handing back; prove containment with `git status --porcelain -uall` and `git diff --name-only <base>..HEAD`.
