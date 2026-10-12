# W53C-EDGE-01 — hand-back

Lane `EDGE`, branch `agent/w53c-edge`, base `04de50c` (`W53-CLOSE-PLAN` on `integration/w53-close`).
Code commit `3860085`; this report is the commit after it. Container-free throughout: no docker,
nginx, Next server or browser was started, and no process was killed.

## Per-finding status

Each finding was re-read at its cited location before any change. All five reproduced.

| Finding | Reproduced at base | Change |
|---|---|---|
| C-15 | yes — no `origin`/`sec-fetch`/`referer` read anywhere in `web/src`; sign-in charged the guest bucket at the first line | `isCrossSitePost` in `route.ts`, called first in all four doors |
| C-16 | yes — `openTheSession` never read the request's cookie | the old row is closed after the new one opens |
| C-17 | yes — exchange, status read and registration forwarded `Bearer <AUDITMANAGER_API_TOKEN>`; `UNAUTHENTICATED_OPERATIONS = {issueToken, submitRegistration, readRegistrationStatus}` in `src/auditmanager/api/security.py` confirms the API reads no credential on them | `ForwardTarget.token: string \| null`; `null` sends no header; `getApiToken` no longer imported by `route.ts` |
| C-18 | yes — no `add_header` in either file | four headers at server level in both files; HSTS in `tls-server.conf` only |
| C-19 | yes — refresh only on `PATCH /me`; `initialsOf('ßmith')` gave `SS` | refresh after a self-targeted `PATCH /users/{user_uid}`; `capitalOf` keeps a letter whose capital is longer than one code point |

### Design decisions the integrator should know

- **C-15 refusal shape.** The doors already answer refusals with `303` redirects, so they still do:
  sign-in → `/login?refusal=validation` (no `next`: that would be the other site's choice),
  registration → `/register?refusal=validation`, password → `/account/password?outcome=validation`,
  sign-out → `303 /` with **no** cookie instruction (the session is left alone). `validation` is used
  because the refusal sets are closed and mirrored in `features/*` (another lane's paths); no new
  value was added.
- **C-15 own origin = `Host` header** (nginx sets `$http_host`), or the request URL's authority if
  there is no `Host`. The comparison covers **host and port, not scheme**. With an outer TLS
  terminator (the deferred edge-topology item), `X-Forwarded-Proto` would be `http` while the
  browser's `Origin` is `https`, so comparing schemes would refuse every sign-in on that stand. The
  ports are normalised under the `Origin`'s scheme, so `https://h` and `Host: h:443` match. A post
  with no `Origin` and no `Sec-Fetch-Site` (curl, old browsers) is accepted. `Origin: null` is
  refused.
- **C-17.** Without the signing key, an exchange or a registration on a deployment with no
  `AUDITMANAGER_API_TOKEN` now proceeds. Only a missing upstream counts as `unconfigured`/`upstream`.
  Two existing tests that deleted the token to provoke `unconfigured` were changed to delete only
  the upstream (`bff-session.test.ts`, `registration-door.test.ts`).
- **C-19.** Whether the edit was the session's own is asked of `getMe` (its `user_uid`) after the
  `200`. The register stores no uid, so its format is unchanged. If `getMe` cannot give a subject
  and a uid (it answers `401` because a role change raised the epoch, any other non-200, or a body
  without `user_uid`), the session is closed. This is the same rule `PATCH /me` already follows.
  Sign-in itself does not require `user_uid`.
- **C-18.** `tls-server.conf`'s old "NO HSTS" note was replaced with the reason for the change.
  The header is `max-age=31536000`, with no `includeSubDomains` and no `preload`. Browsers ignore
  HSTS on plain HTTP and on IP literals, so the tunnelled `127.0.0.1` stand is unaffected.
  `test_proxy_tls_path.py`'s drift check now treats `add_header Strict-Transport-Security` as
  transport, the same way it treats `ssl_*`. A new test shows the drift check still catches a
  dropped security header. No `location` has its own `add_header`, so the server-level set reaches
  every location, `@rate_limited` included. The new test computes this the way nginx does.

## 1. Changed files

`git diff --name-only 04de50c..HEAD` (code commit, plus this report):

```
infra/deploy/proxy/nginx.conf
infra/deploy/proxy/tls-server.conf
tests/contract/test_proxy_security_headers.py          (new)
tests/integration/composition/test_proxy_tls_path.py
web/src/app/bff/session/subject.ts
web/src/app/bff/v1/[...path]/route.ts
web/src/shared/api/credentialed-forward.ts
web/tests/unit/api/credentialed-forward.test.ts
web/tests/unit/session/bff-session.test.ts
web/tests/unit/session/edge-closure.test.ts            (new)
web/tests/unit/session/registration-door.test.ts
docs/program/W53C-EDGE-01.md                           (this report)
```

## 2. Checks and results (on `3860085`, from the worktree root)

| Command | Result |
|---|---|
| `git diff --check` | exit 0 |
| `npm --prefix web run lint` | exit 0, no findings |
| `npm --prefix web run typecheck` | exit 0 |
| `cd web && npx vitest run tests/unit/session tests/unit/api tests/unit/qa_w49` | 351 passed |
| `cd web && npx vitest run tests/guards` (read-only guards over `route.ts`/forwarder) | 266 passed |
| `.venv/bin/python -m pytest -q tests/contract/test_proxy_security_headers.py` | 9 passed |
| `.venv/bin/python -m pytest -q tests/integration/composition/test_proxy_tls_path.py tests/contract/test_proxy_rate_limits.py` | 44 passed |
| `.venv/bin/python -m pytest -q tests/contract/api_v1/test_surface_counts_in_prose.py tests/e2e/test_upload_limit_headroom.py` | all passed; this caught one count phrase in the first draft of my `route.ts` prose, now rephrased |
| `.venv/bin/python -m compileall -q` on both changed Python test modules | exit 0 |
| `ruff check` | **not run**: no `ruff` exists in `.venv/bin`, `.venv` as a module, or `PATH` on this host |
| `.venv/bin/python -m pytest -q -rfE tests/contract` (extra, informative) | 699 passed, 70 failed, 126 errors, all in `test_cp00_candidate.py`, `test_cp00_final_state.py` and `test_validate_bootstrap.py`. The causes are `NotADirectoryError: '.../w53c-edge/.git'` (a worktree's `.git` is a file) and `jsonschema` missing from the bootstrap interpreter. Both are worktree/tooling causes. No proxy, BFF or web file is involved. |

**How each new test fails without the fix.**
- **Web:** `route.ts`, `subject.ts` and `credentialed-forward.ts` were restored to their `04de50c`
  content, with the new and changed tests kept. `npx vitest run tests/unit/session/edge-closure.test.ts tests/unit/api/credentialed-forward.test.ts tests/unit/session/bff-session.test.ts tests/unit/session/registration-door.test.ts`
  then gave **31 failed / 89 passed**:
  - all 20 C-15 cross-site cases (5 header shapes × 4 doors);
  - C-16 "deletes the row … here and in the register file";
  - 4 C-17 cases, plus the forwarder's null-credential case and the two strengthened `toBeNull`
    assertions in `bff-session`/`registration-door`;
  - C-19 self-edit refresh and dead-credential close;
  - C-19 initials (`ß`).

  The fixed files were then copied back (`cmp` identical).
- **Proxy configs:** with both conf files at `04de50c`, `test_proxy_security_headers.py` had
  7 failed / 2 passed. With `test_proxy_tls_path.py` at `04de50c` against the new configs,
  `test_the_two_server_bodies_do_not_drift` failed. That proves the transport exclusion is needed.
  The new header file's `test_each_check_can_fail` mutates the configs in six ways: a dropped
  header in each block, a location's own `add_header`, HSTS on plain, HSTS missing on TLS, and a
  header without `always`. Each mutation is caught.

## 3. Contracts

None changed. `contracts/**`, the migration head (`0017_execution_queue`), lock files and the
OpenAPI digest are unchanged. The only API-facing difference is on the wire: three operations with
an empty security requirement no longer receive an `Authorization` header.

## 4. Risks / known limitations

- C-15 trusts `Host`. If a proxy rewrote `Host` to an internal name, every same-origin browser
  post would be refused. Today both configs send `$http_host`. A client that is not a browser can
  bypass the check by omitting both headers. That is by design: CSRF needs a browser.
- C-15 with `Referrer-Policy: same-origin` (C-18): browsers still send the true `Origin` on
  same-origin posts. A page that set `no-referrer` would make same-origin posts send
  `Origin: null`, and those would be refused. No page sets it today.
- C-18 HSTS commits any **host name** that serves the TLS block to HTTPS for a year. This is not
  verified against a running nginx (`nginx -t` was not run, container-free). The directives are
  standard `add_header … always`.
- C-19: if `getMe` fails transiently right after an administrator edits **another** user, the
  administrator's session is closed. This is the same rule `PATCH /me` already follows.
- Per `AGENTS.md` §8.3, an `infra/**` change normally needs one full gate on the lane. `R-84`
  (this wave) assigns lanes light, container-free checks, so no gate was run. The integrator
  decides whether a proxy smoke check (`nginx -t` with both files) is wanted.

## 5. Integrator instructions

Merge `agent/w53c-edge` as is. Overlap with the WEB-ID lane is possible only in
`web/tests/unit/session/*` if that lane edits the same suites. Lines touched here:
- `bff-session.test.ts`: the `unconfigured` case and one `toBeNull` line;
- `registration-door.test.ts`: the `unconfigured` case and one `toBeNull` line.

After merging, the full Vitest run and `pytest tests/contract` cover everything here.
`test_proxy_tls_path.py` lives under `tests/integration/composition/` and is static, so run it
explicitly. `AUDITMANAGER_API_TOKEN` stays in the web container's environment, removing it is a
non-goal, and the BFF no longer reads it.

## 6. Containment proof

- `git diff --name-only 04de50c..HEAD` gives exactly the list in §1. Every path is inside the
  task's allowed paths.
- None of these was touched: `contracts/**`, `db/migrations/**`, lock files, `Makefile`,
  `tests/support/**`, any `conftest.py`, `CURRENT_STATE.md`, `DEBT_REGISTER.md`, or non-BFF web
  code.
- `git status --porcelain -uall` printed nothing after the commit.
- No containers, volumes, worktrees, pushes, merges or tags were created.
