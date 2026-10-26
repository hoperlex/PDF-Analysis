# Task HARDEN-01 — the findings of EXPOSURE-REVIEW-02 that are a line or a small check: F-03, F-12, F-13, F-16, F-17 (and F-23, nothing of it is one line)

task_id: HARDEN-01
status: completed in development candidate (nothing run against a host or a real compose project; see the report)

## Outcome

Lane H of `PRODUCTION-WAVE-PW3.md` (`D-234`, `D-235`, `D-240`, `D-242` of `EXPOSURE-REVIEW-02`): the `web` container no longer receives the key that signs every user credential and nothing in `web/src` needs it (`F-03`); the database engine hides SQL parameters (`F-12`, with the residual named in the report); an `internal_error` answer leaves one log line with the exception's type, where it was raised and the correlation id, never the message (`F-13`); the proxy offers only ECDHE + AEAD suites for TLS 1.2 and prints no version in `Server` (`F-16`); `verify-deployed.sh` judges HSTS, the four security headers, the `Server` banner and the `Secure` flag of the session cookie on the answer the proxy gives on the served name (`F-17`, new exit 9). `F-23` has no part that is one line inside this lane's paths.

## Depends on

- `PROD-04-DB-ROLES-01` (merged into the base; its `compose.server.yml`), `PROD-01-TLS-ACME-01` (the TLS block, the ACME one-off container, section 4 of `verify-deployed.sh`) and `PROD-02-03-DEPLOY-GATES-01` (section 5).
- `EXPOSURE-REVIEW-02` findings `F-03`, `F-12`, `F-13`, `F-16`, `F-17`, `F-23`; register rows `D-234`, `D-235`, `D-240`, `D-242`; `R-146k` (no new observability beyond the accepted items: this lane adds one log line, no format, no redaction layer, no metric).

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.7.0` (`info.version`), unchanged (`contracts/**` is not touched; the log line is in no response)
- analysis/comparison/event contract: not_applicable
- migration head: unchanged (`0033_ar_v3_cite_stage_id`)
- base commit: `9cdad455` (`integration/ar-close-1026`), branch `agent/harden-01`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

`verify-deployed.sh` gains one exit code (`9`) and four marked steps (`served-hsts`, `served-security-headers`, `served-no-version`, `served-secure-cookie`); they are enumerated by `TestEachStepIsShownAbleToFail`, which fails if a step is not marked exactly once. No route, screen, error code or migration is added.

## Captured premise evidence

- premise: every file, symbol and line the brief and `EXPOSURE-REVIEW-02` name, re-read at the base `9cdad455`. All are present; two line numbers drifted (the `web` token line is 353, not 342; the failure middleware is `handlers.py:469-514` still, its re-raise sentence at 480 and its `envelope_response` line at 513). Nothing differed in substance, so the lane went on.

### P-01 — the `web` service receives the signing key (F-03)
- captured_at: 2026-10-27
- command: `git grep -n "AUDITMANAGER_API_TOKEN" 9cdad455 -- infra/deploy/compose.server.yml | sed "s/^9cdad455://"`
- captured_output:
  ```text
  infra/deploy/compose.server.yml:234:      AUDITMANAGER_API_TOKEN: ${AUDITMANAGER_API_TOKEN:?AUDITMANAGER_API_TOKEN is unset. The seam is fail-closed; see infra/deploy/env/alpha.env.example.}
  infra/deploy/compose.server.yml:353:      AUDITMANAGER_API_TOKEN: ${AUDITMANAGER_API_TOKEN:?AUDITMANAGER_API_TOKEN is unset. The web tier forwards it; without it every operation answers 401.}
  ```
- interpretation: line 234 is the `api` service, line 353 the `web` service, under a comment that says the web tier forwards it. No `env_file` on `web` and no other compose file under `infra/` names the variable (`test_web_service_holds_no_signing_key.py` walks every compose file).

### P-02 — nothing under `web/src` calls a reader of it, and one module reads it (F-03: "verify that claim by search first")
- captured_at: 2026-10-27
- command: `git grep -n -E "getApiToken|hasServerCredential" 9cdad455 -- web/src | sed "s/^9cdad455://"; git grep -n "process.env.AUDITMANAGER_API_TOKEN" 9cdad455 -- web/src | sed "s/^9cdad455://"`
- captured_output:
  ```text
  web/src/shared/config/server-env.ts:99:export function getApiToken(): string {
  web/src/shared/config/server-env.ts:112:export function hasServerCredential(): boolean {
  web/src/shared/config/server-env.ts:100:  const raw = process.env.AUDITMANAGER_API_TOKEN;
  web/src/shared/config/server-env.ts:113:  const token = process.env.AUDITMANAGER_API_TOKEN;
  ```
- interpretation: the claim holds: the two readers are defined in `server-env.ts` and called nowhere (tests import them). The BFF forwards only `token: null` (the three anonymous operations, `W53-CLOSE` `C-17`) or a session's own credential: `git grep -c "forwardWithCredential(" 9cdad455 -- "web/src/app/bff/v1/[...path]/route.ts"` counts 7 forward sites, each given `token: null` or a session's credential, and none reads the environment. **The runbook (section 2) still said the web tier forwards the key on the sign-in exchange; that was true until `C-17` and is corrected here.**

### P-03 — the engine is built without `hide_parameters` (F-12)
- captured_at: 2026-10-27
- command: `git show 9cdad455:src/auditmanager/shared/db/engine.py | sed -n 29,38p`
- captured_output:
  ```text
      return create_engine(
          settings.url,
          pool_size=settings.pool_size,
          max_overflow=settings.max_overflow,
          pool_timeout=settings.pool_timeout,
          pool_recycle=settings.pool_recycle,
          pool_pre_ping=True,
          echo=settings.echo,
          future=True,
      )
  ```
- interpretation: as the review says (lines 29-38). Reproduced red: `tests/unit/shared/test_engine_hides_parameters.py` on the base engine fails 3 of 4 (the exception string and the echo log print the sentinel; the control, which builds an engine without the flag, passes by design). `create_database_engine` is the only caller of `create_engine` under `src/` (`rg -n "create_engine\(" src` lists this one).

### P-04 — no logger is called in the API's request path (F-13)
- captured_at: 2026-10-27
- command: `git grep -n -E "_log\.|logging\." 9cdad455 -- src/auditmanager/api | sed "s/^9cdad455://"; git show 9cdad455:src/auditmanager/api/routers/handlers.py | grep -n "declines to re-raise\|response = envelope_response(to_domain_error"`
- captured_output:
  ```text
  src/auditmanager/api/app.py:57:_log = logging.getLogger(__name__)
  src/auditmanager/api/app.py:341:        _log.info(
  src/auditmanager/api/app.py:347:            _log.warning(
  480:    carrying ``X-Correlation-Id``. It also declines to re-raise: a client is owed an answer,
  513:            response = envelope_response(to_domain_error(exc), current_correlation_id())
  ```
- interpretation: only the startup lines log. `FailureEnvelopeMiddleware` (the handler module the brief asks to name: `src/auditmanager/api/routers/handlers.py`) answers `internal_error` and does not re-raise; `to_domain_error` (`routers/errors.py:77-93`) keeps nothing of the original. Reproduced red: `tests/unit/api/test_internal_error_leaves_a_log_line.py` on the base fails 8 of 10 (the two that pass assert there is NO line for a typed refusal and that the envelope is unchanged). Where the line is visible: with the root logger unconfigured (the API image configures none) Python's last-resort handler prints a `WARNING`-or-above record to stderr, i.e. to `docker logs`; measured on a throw-away app, the line is printed.

### P-05 — the TLS 1.2 vocabulary is the image default and the banner names a version (F-16), reproduced against a real nginx
- captured_at: 2026-10-27
- command: `git grep -n -E "ssl_ciphers|server_tokens" 9cdad455 -- infra; openssl ciphers -v 'HIGH:!aNULL:!MD5' | grep ' TLSv1.2 ' | grep -vc 'Mac=AEAD'`; then the base `nginx.conf` and `tls-server.conf` (ports and upstreams rewritten for loopback, one self-signed pair) under the host's `nginx 1.24.0` on `127.0.0.1:28443`, asked with `curl -sk -D - https://127.0.0.1:28443/` and `openssl s_client -tls1_2 -cipher ECDHE-RSA-AES256-SHA384`
- captured_output:
  ```text
  (no line for ssl_ciphers or server_tokens)
  20
  Server: nginx/1.24.0 (Ubuntu)
  New, TLSv1.2, Cipher is ECDHE-RSA-AES256-SHA384
  ```
- interpretation: no directive exists; the default list has 20 non-AEAD TLS 1.2 suites with OpenSSL 3.0.13 (the review's figure); the base configuration negotiated a CBC suite and printed the version. After the change, the same harness: `Server: nginx`, the CBC suite answers `sslv3 alert handshake failure`, `ECDHE-RSA-AES256-GCM-SHA384` negotiates for TLS 1.2 and `TLS_AES_256_GCM_SHA384` for TLS 1.3. The host's nginx is 1.24, the image's 1.27; the comparison is of directives that both versions implement (`http2 on;` was removed from the temporary copy because 1.24 predates it). Both throw-away processes were stopped by their own PIDs.

### P-06 — no script asserts the served answer (F-17)
- captured_at: 2026-10-27
- command: `git grep -n -i -E "nosniff|X-Frame|set-cookie|cookie|strict-transport" 9cdad455 -- infra/deploy/verify-deployed.sh infra/deploy/deploy.sh`
- captured_output:
  ```text
  (no line)
  ```
- interpretation: as the review says. What the probe relies on, read in the source: `GET /bff/v1/me` with `Cookie: am_session=<64 hex digits>` reaches `staleSession` (`route.ts:447-458`), which answers `401` and sets the cleared session cookie with `clearedSessionCookie(requestIsSecure(request))` (`store.ts:711-717`); `requestIsSecure` reads `X-Forwarded-Proto`, which `tls-server.conf` sets to `$scheme` (`https`). The cookie's `Secure` attribute is therefore a live test of the proxy header and the web tier together, with no credential. Observed once end to end: the same request through the new TLS block to a stub that implements `requestIsSecure` returned `HTTP/1.1 401`, `Set-Cookie: am_session=; ...; Max-Age=0; Secure` and every header.

### P-07 — F-23, part by part
- captured_at: 2026-10-27
- command: `git grep -n -i "no-store" 9cdad455 -- src web/src infra/deploy/proxy | sed "s/^9cdad455://" | cut -c1-140; grep -n "add_header" infra/deploy/proxy/nginx.conf | head -6`
- captured_output:
  ```text
  src/auditmanager/api/routers/runner.py:143:                                  ("Cache-Control", "no-store")), content)
  web/src/app/bff/version/route.ts:13:    return new Response(null, { status: 401, headers: { 'Cache-Control': 'no-store' } });
  web/src/app/bff/version/route.ts:17:    { headers: { 'Cache-Control': 'no-store' } },
  web/src/shared/api/version-check.ts:25:      cache: 'no-store',
  282:    # `add_header` from the enclosing level only when a level declares none, so one
  283:    # `add_header` inside a `location` silently drops all four for that location. A location
  290:    add_header X-Content-Type-Options "nosniff" always;
  291:    add_header X-Frame-Options "DENY" always;
  292:    add_header Content-Security-Policy "frame-ancestors 'none'" always;
  293:    add_header Referrer-Policy "same-origin" always;
  ```
- interpretation: the three parts of `F-23` are `getProductVersion` open to any complete account (an authorisation policy, in `src/auditmanager/api/**`), the caller-chosen correlation id of audit rows (`routers/correlation.py`, `access/audit.py`) and the absence of `Cache-Control: no-store` on authenticated JSON. None is a one-line change inside this lane's paths: the first two are outside them and are policy; the third would need an `add_header` in a `location`, which drops the four inherited security headers (the file's own rule, held by `test_proxy_security_headers.py`) unless they are restated there, or one at server level that also covers the immutable `_next/static` assets. Nothing was changed for `F-23`.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

The lane commits to `agent/harden-01` and pushes nothing. `origin/main` triggers a deployment (`AGENTS.md` section 6) and is not touched.

## Allowed paths

- `infra/deploy/compose.server.yml`
- `infra/deploy/proxy/**`
- `infra/deploy/verify-deployed.sh`
- `src/auditmanager/shared/db/engine.py`
- `src/auditmanager/api/routers/handlers.py`
- `web/src/shared/config/server-env.ts`
- `web/tests/**`
- `tests/integration/composition/**`
- `tests/unit/**`
- `docs/program/DEPLOYMENT_RUNBOOK.md`
- `docs/program/tasks/HARDEN-01.md`
- `docs/program/HARDEN-01.md`

`tests/unit/**` and `web/tests/**` were used only for new tests and for the web guard (`web/tests/guards/**`). `tests/integration/composition/test_deployed_stack_probe.py` is the shared harness of the older `verify-deployed` cases and was extended with one default branch (the report lists what it asserted before and after). The runbook was edited in three places (the signing-key paragraph of section 2 and two refusal rows).

## Forbidden hotspots

- `contracts/**`, migrations and the migration head
- `infra/deploy/{deploy.sh,reset.sh,copy-serve.sh}` (another lane owns the erase wrapper)
- root dependency/lock files
- `docs/program/DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs
- everything else under `src/**`, `infra/**` (`infra/acme/**`, `infra/deploy/env/**`, `README.md`) and `web/**` outside the allowed paths

## Non-goals

- the database server's own `DETAIL` line in an exception string (`Failing row contains (...)`, `Key (...)=(...)`), see the report; and the two `_log.exception` sinks (`runs/carrier.py`, `workers/service.py`) that print it
- removing `getApiToken`/`hasServerCredential` and their two unit tests (a follow-up; they have no caller and a test now fails if one appears)
- every other finding of the review; the stale sentences in files outside the allowed paths (listed in the report)
- anything on a live host: no `reload-proxy.sh`, no deploy, no network; the live observation of `F-16`/`F-17` is the cutover step the review lists

## Deliverables

- `src/auditmanager/shared/db/engine.py` (`hide_parameters=True`), `src/auditmanager/api/routers/handlers.py` (`_answer_for`, `_record_internal_error`)
- `infra/deploy/compose.server.yml` (no key on `web`), `infra/deploy/proxy/{nginx.conf,tls-server.conf}` (`server_tokens off`, `ssl_ciphers`, the comment corrected), `infra/deploy/verify-deployed.sh` (section 4b, exit 9)
- `web/src/shared/config/server-env.ts` (text only), `web/tests/guards/lib/credential-scan.ts` and `web/tests/guards/server-credential.guard.test.ts` (text, one rule, two cases)
- new tests: `tests/unit/shared/test_engine_hides_parameters.py`, `tests/unit/api/test_internal_error_leaves_a_log_line.py`, `tests/integration/composition/{test_proxy_hardening,test_verify_deployed_served_headers,test_web_service_holds_no_signing_key}.py`; modified: the shared harness (one branch), the web guard (above)
- `docs/program/DEPLOYMENT_RUNBOOK.md` (section 2 paragraph, two refusal rows), the report `docs/program/HARDEN-01.md`

## Required tests

- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/shared tests/unit/api tests/integration/composition/test_proxy_hardening.py tests/integration/composition/test_verify_deployed_served_headers.py tests/integration/composition/test_web_service_holds_no_signing_key.py`
- expected: all pass; the counts are in the report
- command: the neighbours that read the files touched: `tests/integration/composition/{test_proxy_tls_path,test_acme_overlay,test_acme_deploy_guards,test_default_credential_gate,test_exposure_text_is_current,test_session_register_volume,test_verify_deployed_certificate,test_deployed_stack_probe}.py tests/contract/test_proxy_security_headers.py tests/contract/test_proxy_rate_limits.py`
- expected: all pass
- command: on a private migrated database (dropped afterwards) `tests/integration/api/{test_error_envelope,test_database_refusals,test_no_framework_body_reaches_a_client,test_two_blob_faults_are_two_envelopes,test_router_and_body_rules}.py`
- expected: all pass
- command: `cd web && npx vitest run tests/guards tests/unit/api && npx tsc --noEmit && npx eslint src/shared/config/server-env.ts tests/guards/lib/credential-scan.ts tests/guards/server-credential.guard.test.ts`
- expected: green
- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` (after the last commit)
- expected: green

## Integration contract

What the integrator can rely on:

- `compose.server.yml`: the `web` service has `AUDITMANAGER_API_UPSTREAM`, `AUDITMANAGER_SESSION_STORE` and `AUDITMANAGER_BEHIND_PROXY` and no signing key; `api` still receives `AUDITMANAGER_API_TOKEN`. An existing `alpha.env` needs no change (the variable is still required, by `api`). A running stack gets the change on its next `up -d`; **the owner must recreate `web`** (`docker compose ... up -d web`) for the key to leave the running container.
- `verify-deployed.sh`: with `ALPHA_CERT_NAME` set, after the certificate is accepted it runs one more one-off container call (`--entrypoint sh acme -c <probe> served-headers-probe <name> proxy:8443 <64 zeros>`). Exit 9 = the answer lacks a promised header or the cookie is not `Secure`; exit 4 = no readable answer or no session cookie to judge. Without a name the script is what it was. **A stack whose proxy still runs the old configuration will end red at exit 9 until `reload-proxy.sh` (a `Server` banner with a version and no cipher list are not checked by it; the headers and the cookie are, and the live stand is the one that previously lacked them).** The probe needs the web tier up; a down web tier is exit 4, not a pass.
- `handlers.py`: one `ERROR` line from logger `auditmanager.api.routers.handlers` per `internal_error` answer: `internal_error: <module>.<Class> raised at <module>:<line> in <function> (correlation_id=<id>)`. No message, no arguments, no traceback text, no `exc_info`.
- `engine.py`: every engine built by `create_database_engine` has `hide_parameters=True`.
- no file under `contracts/**`, `db/migrations/**`, `.github/**`, the lock files, `infra/deploy/{deploy.sh,reset.sh,copy-serve.sh}` is touched.

## Failure/idempotency/security cases

- the log line is built from the type, the origin frame and the correlation id only; four sentinels (message, argument, cause, a `DomainError` reason) are planted and read back through every attribute of the record
- the probe asks nothing before the certificate is accepted and nothing without a name; an unreadable answer or a missing session cookie is exit 4 and claims nothing
- a header found only in the body, a lower-cased header name, a cookie attribute in a different position or case, and `SecureX` are each decided correctly
- every new guard is shown failing under a quoted mutation (the table in the report)

## Rollback / feature flag

No flag. Reverting the commits restores the previous behaviour: the key on `web` (re-add the line), the engine without the flag, no log line, the default cipher list and banner, and a `verify-deployed.sh` without section 4b. None of it is data; nothing needs a migration.

## Handoff

- changed files: see the report, section 2
- commands/results: see the report, section 6
- known limits: see the report, section 8
- integration notes: see the report, section 7
