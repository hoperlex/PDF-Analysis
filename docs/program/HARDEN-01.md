# HARDEN-01 — the small findings of EXPOSURE-REVIEW-02

Lane H of `PRODUCTION-WAVE-PW3.md`; task file `tasks/HARDEN-01.md`. Branch `agent/harden-01`, base `9cdad455` (`integration/ar-close-1026`), no push, no tag, nothing on `origin/main`. Date 2026-10-27.

## 1. Result in one paragraph

Five of the six findings are fixed, each reproduced red first and shown failing under a mutation: `F-03` (the `web` service no longer receives the key that signs every user credential; nothing in `web/src` called it), `F-12` (the engine hides SQL parameters; **a residual is named in section 8 and is not closed**), `F-13` (an `internal_error` answer leaves one log line: type, origin frame, correlation id), `F-16` (TLS 1.2 is ECDHE + AEAD only; `Server: nginx` carries no version; the false comment is corrected), `F-17` (`verify-deployed.sh` judges HSTS, the four security headers, the `Server` banner and the `Secure` flag of the session cookie on the proxy's answer on the served name; new exit 9). `F-23` has no part that is one line inside this lane's paths; nothing was changed for it.

## 2. Files

Changed (`git diff --name-only 9cdad455..HEAD`, section 9 has the list as run):

| File | What |
| --- | --- |
| `src/auditmanager/shared/db/engine.py` | `hide_parameters=True`; the docstring names the residual |
| `src/auditmanager/api/routers/handlers.py` | `_answer_for` (classify, record, render), `_record_internal_error`, `_origin_of`; the three paths that can end in `internal_error` (registered `DomainError` handler, `on_unhandled`, `FailureEnvelopeMiddleware`) use it |
| `infra/deploy/compose.server.yml` | `AUDITMANAGER_API_TOKEN` removed from `web`; the comment explains why |
| `infra/deploy/proxy/nginx.conf` | `server_tokens off;` once, at http level |
| `infra/deploy/proxy/tls-server.conf` | `ssl_ciphers` (six ECDHE + AEAD suites); the comment at the old lines 74-78 corrected |
| `infra/deploy/verify-deployed.sh` | section 4b (four marked steps), exit 9, header comment |
| `web/src/shared/config/server-env.ts` | text only (module note, `API_TOKEN_VARIABLE`, `getApiToken`, `hasServerCredential`); behaviour unchanged except the text of the `MissingConfigurationError` that `getApiToken` throws |
| `web/tests/guards/lib/credential-scan.ts`, `web/tests/guards/server-credential.guard.test.ts` | text corrected; rule 5 `signing-key-reader-called` |
| `docs/program/DEPLOYMENT_RUNBOOK.md` | section 2 signing-key paragraph (it said `web` forwards the key on sign-in: false since `C-17`), two refusal rows |
| `tests/integration/composition/test_deployed_stack_probe.py` | the shared harness's `docker` stub answers the headers probe (default: a good answer) |
| new: `tests/unit/shared/test_engine_hides_parameters.py`, `tests/unit/api/test_internal_error_leaves_a_log_line.py`, `tests/integration/composition/test_proxy_hardening.py`, `test_verify_deployed_served_headers.py`, `test_web_service_holds_no_signing_key.py` | the guards |
| new: `docs/program/tasks/HARDEN-01.md`, this report | |

## 3. Premise result

All present; two line numbers drifted and nothing differed in substance (task file P-01 to P-07). Of note: the claim "no `web/src` module reads the key" was verified by search before the removal, and the runbook's contrary statement (section 2, "`web` forwards it in an `Authorization: Bearer` header on the sign-in exchange") was found stale since `C-17`/`W53-CLOSE` and corrected.

## 4. Decisions taken by the lane (the owner asked for no questions)

1. **TLS 1.2 list**: six ECDHE suites, AES-128/256-GCM and CHACHA20-POLY1305, for both an RSA and an ECDSA pair (the key type is whatever the pinned ACME client issues). No DHE suite, so no `ssl_dhparam` file is needed. Decided by the lane.
2. **`server_tokens off` once at http level** in `nginx.conf` (the file nginx always loads); the TLS and challenge blocks inherit it. `Server: nginx` remains (removing the header needs `headers-more`, not in the stock image).
3. **The log line** (`F-13`): level `ERROR`, logger `auditmanager.api.routers.handlers`, `internal_error: <module>.<Class> raised at <module>:<line> in <function> (correlation_id=<id>)`. The origin frame is added to the brief's "type and correlation id" because a type alone (`DomainError`, `RuntimeError`) cannot be acted on in a storm; a frame is code, never data. Also logged: a `DomainError` that itself carries `internal_error` (several call sites raise one with a `reason`; they were invisible 500s). Not logged: every other code (the caller's doing). No `exc_info`, so no traceback text, which ends with the message.
4. **`F-17` design**: one request, `GET /bff/v1/me` with a well-formed session cookie that names no session, to `proxy:8443` from the ACME one-off container (the host has no `openssl`), through `openssl s_client`; the headers are judged on the host in bash. The web tier answers that request `401` with a cleared `am_session` cookie whose `Secure` attribute comes from `requestIsSecure` (`X-Forwarded-Proto`), the same decision as the sign-in cookie, so the flag is observed through the whole chain without a password in the script. An unreadable answer or a missing cookie is exit 4, never a pass. HSTS: `max-age >= 31536000`, neither `includeSubDomains` nor `preload` (`ADR-0021`). The `Server` banner check (no digit) is added to the brief's list as the regression guard of `F-16` on the served answer.
5. **`F-03` scope**: the readers `getApiToken`/`hasServerCredential` and their two unit tests were **kept**; only their text changed. A new guard rule (web) and a new composition test (deployment side) fail the day a `web/src` module calls them. Removing them is a follow-up.
6. **Runbook**: edited in three places because each statement was false after this lane (section 2) or is a new refusal (two rows). `R-29` section 2 is quoted in the runbook as reserving "who can mint a credential" to the owner; the removal only narrows reach, the `PW3` window message of 2026-10-26 gave the permissions in advance and lane H names `F-03`, and the paragraph says the integrator confirms it against `R-29`. **This is the one decision the integrator should look at.**
7. **Shared harness**: a default branch in the `docker` stub of `test_deployed_stack_probe.py` rather than editing every older case that sets a certificate name.

## 5. Mutation table

Each mutation was applied to the committed file, the named tests run, the file restored with `git checkout`, and the tree shown clean. "Red" = the count of failing tests.

| # | Guard | Mutation | Tests run | Result |
| --- | --- | --- | --- | --- |
| M1 | `F-12` flag | delete `hide_parameters=True` | `test_engine_hides_parameters.py` | red: 3 failed, 1 passed (the control) |
| M2 | `F-13` records | `_answer_for` no longer calls `_record_internal_error` | `test_internal_error_leaves_a_log_line.py` | red: 8 failed, 2 passed |
| M3 | `F-13` no traceback | `exc_info=exc` added to the log call | same | red: 4 failed |
| M4 | `F-13` no message | `+ str(exc)` appended to the format | same | red: 4 failed |
| M5 | `F-13` middleware path | middleware renders without `_answer_for` | same | red: 5 failed |
| M6 | `F-13` `on_unhandled` path | bypasses `_answer_for` | same | red: 1 failed |
| M7 | `F-13` `DomainError` path | `on_domain_error` bypasses `_answer_for` | same | red: 2 failed |
| M8 | `F-13` only `internal_error` | condition `if True` | same | red: 1 failed (a typed refusal logged) |
| M9 | `F-16` list exists | delete the `ssl_ciphers` line | `test_proxy_hardening.py` | red: 9 failed, 8 passed |
| M10 | `F-16` AEAD only | add `ECDHE-RSA-AES256-SHA384` | same | red: 2 failed |
| M11 | `F-16` banner | `server_tokens on;` | same | red: 3 failed |
| M12 | `F-16` banner | delete `server_tokens off;` | same | red: 3 failed |
| M13 | `F-03` compose | put the variable back on `web` | `test_web_service_holds_no_signing_key.py` | red: 3 failed |
| M14 | `F-03` web side | `route.ts` imports and calls `getApiToken` | same / `server-credential.guard.test.ts` | red: 1 failed / 1 failed |
| M14b | `F-03` rule 5 | the scanner regex never matches | `server-credential.guard.test.ts` | red: 2 failed (the two new cases) |
| M15 | `F-17` verdict | `HEADER_PROBLEMS` never fails | `test_verify_deployed_served_headers.py` | red: 22 failed |
| M16 | `F-17` HSTS floor | 31536000 lowered to 300 | same | red: 1 failed |
| M17 | `F-17` request | cookie header `am_session` renamed | same | red: 1 failed |
| M18 | `F-17` request | SNI name replaced | same | red: 1 failed |
| M19 | `F-17` exit code | 9 replaced by 5 | same | red: 22 failed |
| M20 | `F-17` no cookie | missing-cookie condition inverted | same | red: 27 failed |
| M21 | `F-17` body | body not cut from the header block | same | red: 1 failed |
| M22 | `F-17` cookie flag | `Secure` matched as a substring | same | red: 1 failed (`SecureX`) |
| M23 | `F-17` name gate | a default name when none is set | same | red: 1 failed, 33 passed |
| M24 | `F-17` listener | the probe asks `proxy:8080` | same | red: 1 failed, 33 passed |
| S1-S4 | `F-17` four steps | each marked step deleted from the script (inside the test) | `TestEachStepIsShownAbleToFail` | each: the finding is reported with the step, absent without it |

The "red first" states: `test_engine_hides_parameters.py` against the base engine failed 3 of 4; `test_internal_error_leaves_a_log_line.py` against the base handlers failed 8 of 10.

## 6. Commands and counts

All with `PYTHONPATH=src:$BS`, `-c pyproject.toml --rootdir=. -q -p no:cacheprovider`, one pytest at a time; nothing needed docker (a `docker` stub that exits 0 was put first on `PATH` for the composition batch that could reach it).

| Command (tests) | Result |
| --- | --- |
| `tests/unit/shared tests/unit/api tests/integration/composition/{test_proxy_hardening,test_verify_deployed_served_headers,test_web_service_holds_no_signing_key}.py` | 108 passed |
| neighbours that read the touched files: `test_proxy_tls_path`, `test_acme_overlay`, `test_acme_deploy_guards`, `test_default_credential_gate`, `test_exposure_text_is_current`, `test_session_register_volume`, `test_verify_deployed_certificate`, `test_deployed_stack_probe`, `tests/contract/test_proxy_security_headers.py`, `tests/contract/test_proxy_rate_limits.py` | 486 passed |
| composition batch 2: `test_deploy_script_refusals`, `test_deploy_image_identity`, `test_readiness_command`, `test_reset_script_refusals`, `test_stand_copy_refusals`, `test_db_roles_deploy_guards`, `test_apply_grants_script`, `test_api_token_channel`, `test_minio_image_contract`, `test_pgvector_image_contract`, `test_bundle_transport_refusals`, `tests/unit/scripts/test_manual_scan.py` | 667 passed, 1 skipped (662 passed and 5 failed when run without the lane `.env`: `test_api_token_channel.py::TestAMissingTokenRefusesAtConstruction` asserts `DATABASE_URL` is loaded; rerun with the `.env` loaded, 10 passed) |
| private migrated database (created and dropped by the run): `tests/integration/api/{test_error_envelope,test_database_refusals,test_no_framework_body_reaches_a_client,test_two_blob_faults_are_two_envelopes,test_router_and_body_rules}.py` | 54 passed |
| web: `npx vitest run tests/guards tests/unit/api` | 28 files, 423 tests passed |
| web: `npx tsc --noEmit`; `npx eslint` on the three touched web files | no output, exit 0; exit 0 |
| `bash -n` and `shellcheck -S warning infra/deploy/verify-deployed.sh` | clean |
| `nginx -t` on the two changed proxy files (host nginx 1.24, upstreams and `http2 on;` rewritten, throw-away pair) | `syntax is ok`, `test is successful` |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, `git diff --check` | CONTRACT_PENDING |

The governance one-liner for `tasks/HARDEN-01.md` prints `[]`.

**Measured against a real nginx on loopback** (host nginx 1.24, ports and upstreams rewritten, one self-signed pair, a stub web tier; every process stopped by its own PID): base files: `Server: nginx/1.24.0 (Ubuntu)` and a TLS 1.2 handshake restricted to `ECDHE-RSA-AES256-SHA384` was accepted; changed files: `Server: nginx`, the same handshake got `sslv3 alert handshake failure`, `ECDHE-RSA-AES256-GCM-SHA384` negotiated for TLS 1.2 and `TLS_AES_256_GCM_SHA384` for 1.3. The probe command itself, run against that listener, returned `HTTP/1.1 401`, the cleared `am_session` cookie with `Secure`, HSTS and the four headers.

## 7. Modified tests, before and after

| Test | Before | After |
| --- | --- | --- |
| `tests/integration/composition/test_deployed_stack_probe.py` (the harness's `docker` stub; no case changed) | no branch for the headers probe | one branch, reached only when a certificate name makes the script send the probe; default answer is a good one. The 47 cases of this file and of `test_verify_deployed_certificate.py` pass unchanged. |
| `web/tests/guards/server-credential.guard.test.ts` | 16 tests: 4 rule ids, 6 mutation cases, header comment describing the key in the web tier | 19 tests: 5 rule ids (`signing-key-reader-called` added), 8 mutation cases (2 added), 1 new "does not fire on prose or the definition"; header comment corrected. No assertion removed or loosened; the `SERVER_ONLY_VARIABLES` literals are unchanged. |
| `web/tests/guards/lib/credential-scan.ts` (the scanner, not a test) | rules 1-4 | rules 1-4 unchanged, rule 5 added; header text corrected |

## 8. Known limits and findings seen and not fixed

1. **`F-12` is only partly closed.** `hide_parameters` removes SQLAlchemy's `[parameters: ...]`. The database server's own message still travels in the same string, measured on the lane's PostgreSQL: a CHECK refusal prints `DETAIL:  Failing row contains (k2, forbidden).` and a unique refusal `DETAIL:  Key (a)=(k1) already exists.` So a column of the refused row (`D-225`: the model output of a `stage_result` insert) can still reach a log line that prints `str(exc)`, i.e. the two `_log.exception` sinks the review names (`runs/carrier.py`, `workers/service.py`; outside this lane). `D-240`'s check (`rg hide_parameters`) passes and its harm is not gone. Options for the integrator: a `connect` event on the engine setting libpq's error verbosity to terse (`dbapi_connection.pgconn.set_error_verbosity(...)`; the product reads only structured `diag` fields, `constraint_name`, never the message text, but operators lose `DETAIL`/`HINT`/`CONTEXT` everywhere), or scrub at the two sinks. Not done: it changes every database error an operator reads.
2. **`F-23`**: nothing is one line in this lane's paths (task file P-07). The version endpoint's audience and the caller-chosen audit correlation id are policy in files outside the lane; `Cache-Control: no-store` on authenticated JSON needs either the API/BFF (outside the lane) or an `add_header` in a `location`, which drops the four inherited headers.
3. **Stale sentences outside the allowed paths** (not edited): `web/.env.example:49-57` (calls the key "THE CREDENTIAL ... one deployment secret handed to two processes"; it is a `next dev` file, harmless, wrong), `infra/deploy/env/alpha.env.example` around line 277 ("The web tier forwards server-side ..."), and the web `route.ts` comments are history and accurate. `getApiToken`/`hasServerCredential` can be deleted with their two unit tests (follow-up).
4. **`F-17` covers the stack's own TLS listener** (`proxy:8443`), the one `check-served.sh` judges. A stack fronted by the host's nginx (`D-227` item 2) or one without `ALPHA_CERT_NAME` is not covered; the live cutover observation (review section 9 step 1) stays the owner's. The probe needs the `acme` service built and the web tier up.
5. **Not run on a live host or a real compose project**: no `reload-proxy.sh`, no deploy, no `docker compose config`. An existing stack keeps the key in the running `web` container until `web` is recreated.
6. `getApiToken` still throws in a deployed container; that is its design now and its text says so.
7. A harness trap met and recorded: the shared `docker` stub matches the substring `find` in the whole call line, and a pytest `tmp_path` carries the test's name, so a test named `..._finding_...` turned the stub's `find` branch on. The new tests avoid the word.

## 9. Integration notes

- **Order and conflicts.** Lane W also edits `infra/deploy/compose.server.yml` (logging and memory per service, including `web`) and `DEPLOYMENT_RUNBOOK.md`. This lane's compose hunk is the `web` comment plus the removal of one `environment` line; expect an adjacent-hunk conflict if W adds `logging:` to `web`. The runbook hunks are in section 2 (a paragraph) and the refusal table (two rows after the exit-7 rows).
- **After merging, the owner (not this lane)**: `docker compose ... up -d web` so the key leaves the running container; `infra/deploy/reload-proxy.sh` so the proxy reads the new files; then `verify-deployed.sh` (exit 9 names anything still wrong). Neither is a deploy-script change.
- `verify-deployed.sh` has a new exit, 9. Callers (the deploy workflow) test only for non-zero.
- Register wording for the integrator: `D-235` (`F-03`) built; `D-240` `F-13` built, `F-12` built with the residual of section 8 item 1; `D-242` `F-16` built; `D-234` `F-17` built in the tree and unobserved on the live name.

## 10. Proof that the forbidden paths are untouched

`git diff --name-only 9cdad455..HEAD` lists only paths under the allowed set; none under `contracts/**`, `db/migrations/**`, `.github/**`, `infra/deploy/{deploy.sh,reset.sh,copy-serve.sh}`, `infra/acme/**`, `infra/deploy/env/**`, the lock files, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings or the ADRs:

```text
docs/program/DEPLOYMENT_RUNBOOK.md
docs/program/HARDEN-01.md
docs/program/tasks/HARDEN-01.md
infra/deploy/compose.server.yml
infra/deploy/proxy/nginx.conf
infra/deploy/proxy/tls-server.conf
infra/deploy/verify-deployed.sh
src/auditmanager/api/routers/handlers.py
src/auditmanager/shared/db/engine.py
tests/integration/composition/test_deployed_stack_probe.py
tests/integration/composition/test_proxy_hardening.py
tests/integration/composition/test_verify_deployed_served_headers.py
tests/integration/composition/test_web_service_holds_no_signing_key.py
tests/unit/api/test_internal_error_leaves_a_log_line.py
tests/unit/shared/test_engine_hides_parameters.py
web/src/shared/config/server-env.ts
web/tests/guards/lib/credential-scan.ts
web/tests/guards/server-credential.guard.test.ts
```
