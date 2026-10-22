# Task EDGE-HARDEN-02 — the proxy believes the outer terminator's scheme, bounds upload connections, and the service is ready only when it can answer

task_id: EDGE-HARDEN-02

## Outcome

Three exposure residuals of `EXPOSURE-REVIEW-01` close in the repository, each with a test that fails under a quoted mutation:

1. `D-191` E-2 / `D-144`: behind the host's TLS terminator the container proxy no longer overwrites `X-Forwarded-Proto` with its own
   `$scheme`. The header is passed on only when the TCP peer (`$realip_remote_addr`) is one of the trusted proxies of
   `ALPHA_TRUSTED_PROXY_CIDRS` (the same list `trusted-proxies.sh` already turns into `conf.d/`), and is otherwise `$scheme` as today;
   with nothing trusted (the default) behaviour is byte-for-byte what it is now. When the believed scheme is `https`, the plain listener
   also sends `Strict-Transport-Security` (and the web tier's `requestIsSecure` therefore issues a `Secure` session cookie). A forged
   `X-Forwarded-Proto: https` from an untrusted peer buys neither.
2. `D-165`: the two upload locations carry a per-client connection limit (`limit_conn_zone` keyed by the client address in the same
   http-level file as the other zones, `limit_conn` in both upload locations, a 429-class refusal with the same status the zones use
   today), so one client cannot hold the whole 260 MiB buffering budget open with parallel slow bodies. The figure is argued in the
   file's comment in the style of the neighbouring ones (a person uploads one or two documents at once).
3. `D-196`: `infra/deploy/serve.py` binds the API socket before the health plane can report ready (or `/readyz` depends on the API
   socket); a test starts the real `serve.py` many times and calls the instant `/readyz` first answers, and counts refusals of the
   first call (old behaviour measured by `GATE-REPAIR-01`: 8 of 60 refused; the repaired code must show 0 of at least 60).

Debts: `D-144`, `D-165`, `D-191` (E-2 and the proto half of E-3), `D-196`. The operator-side facts (the host server block, certificate
renewal, which CIDR to list on the stand) stay with the owner: this task documents the exact lines the host block must send, it does
not touch the host.

## Depends on

- `REAL-IP-EDGE-01`, `HARDEN-AUTH-EDGE-01`, `GATE-REPAIR-01` — completed and on `origin/dev`.

## Frozen inputs

- base: the integration branch `integration/beta-main` tip at the freeze commit of this file (it contains `origin/dev` `a5b83f64`
  and the beta lanes B–I; not yet in `origin/dev`);
- migration head `0029_routing_refusal_codes`; API 73/83/242; 27 error codes; contract `1.0.0`; this task changes no contract and adds no
  migration;
- rulings: `R-135`, `AGENTS.md` §8.3 (an `infra/**` change needs the complete gate: the integrator runs it, not this lane), `R-144d`,
  and the owner's standing order of 2026-10-22 «гони до беты без вопросов»: a choice that no recorded decision blocks is taken with
  the conservative default and reported under "Decisions taken", not asked.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/proxy/tls-server.conf`
- `infra/deploy/proxy/trusted-proxies.sh`
- `infra/deploy/serve.py`
- `infra/deploy/README.md`
- `infra/deploy/env/alpha.env.example`
- `tests/contract/test_proxy_rate_limits.py`
- `tests/contract/test_proxy_security_headers.py`
- `tests/integration/composition/test_proxy_config_follows_checkout.py`
- `tests/integration/composition/test_proxy_tls_path.py`
- `tests/integration/composition/test_real_client_address_at_the_edge.py`
- `tests/integration/composition/test_edge_credential_gate.py`
- `tests/integration/composition/test_edge_scheme_and_connection_limits.py` (new)
- `tests/integration/composition/test_serve_is_ready_only_when_it_can_answer.py` (new)
- `docs/program/EDGE-HARDEN-02.md`
- `docs/program/tasks/EDGE-HARDEN-02.md`

## Lane resources

- the host `nginx` binary (`/usr/sbin/nginx`) for the live half, as `test_real_client_address_at_the_edge.py` already does;
- a database is needed only if the `serve.py` test cannot start the real application without one: then use foundation_instance
  `auditmanager-lane-h`, postgres_port `57680`, s3_api_port `61480`, s3_console_port `61481` (reserved, unused; below the kernel's
  ephemeral range, `D-189`), started from images already pulled, **never built** (the host disk is near 2.5 GB free: check
  `df -m /` first and stop below 2000 MiB); never 57500-57501, 28500-28501, 28520-28521, 57600, 57650, 57690, 57700;
- kill only a process you started, by a PID you confirmed; the host is shared with other projects.

## Forbidden hotspots

Every `src/**`, `web/**`, `contracts/**`, `db/migrations/**`, `Makefile`, `.github/**`, dependency and lock files,
`infra/deploy/compose.server.yml`, `infra/deploy/deploy.sh`, `infra/deploy/verify-deployed.sh`, `tests/support/**`, any `conftest.py`,
`docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`, `docs/program/EXPOSURE-REVIEW-01.md`, refs, tags and the stand. If the
trusted-proto list needs a new compose mount or a new variable passed by the compose file, stop and report it to the integrator with the
exact lines; do not edit `compose.server.yml`.

## Non-goals

No change to the host's own nginx (outside the repository); no certificate work; no CSP or other header changes beyond HSTS; no change to
the rate figures of the existing zones; no unbuffered-upload switch (`proxy_request_buffering off`) — that changes the auth-gate
subrequest timing and is a separate, measured decision (record it as a follow-up if you think it is warranted); no web tier change (the
`Secure` flag follows from the header already).

## Work

1. Read `infra/deploy/proxy/nginx.conf` (the REAL-IP block at the top, the zones, both upload locations), `tls-server.conf`,
   `trusted-proxies.sh`, `tests/integration/composition/test_real_client_address_at_the_edge.py` (its live harness with recording stubs is
   the model for the new live test), `infra/deploy/serve.py`, and `docs/program/EXPOSURE-REVIEW-01.md` E-2/E-3/E-7.
2. Reproduce first: a live test that sends `X-Forwarded-Proto: https` to the real configuration and shows the stub still receives
   `$scheme` today (red on the base for the trusted case); and a start loop of the real `serve.py` showing refused first calls on the base
   (write the loop so the count is printed).
3. Trusted scheme: extend `trusted-proxies.sh` to also write a `geo $realip_remote_addr $trusted_peer { default 0; <cidr> 1; }` (or an
   equivalent that cannot be forged and that keeps the default-nothing-trusted file valid), derive the believed scheme with a `map`, and
   use it in every `proxy_set_header X-Forwarded-Proto` (the file has several, in both server bodies). HSTS through an empty-valued
   `add_header` when the scheme is not https. The existing `tls-server.conf` HSTS stays as it is.
4. Connection limit: `limit_conn_zone` + `limit_conn` for the two upload locations, `limit_conn_status` consistent with `limit_req_status`.
   A live test opens more slow uploads from one address than the limit and sees the refusal; a second address is unaffected.
5. `serve.py`: bind and listen on the API socket first, then start the health thread; keep the existing refusal when the two ports are
   equal and the signal handling. The start-loop test passes with 0 refused first calls in at least 60 starts.
6. Static guards in the existing contract tests follow the committed text (every `X-Forwarded-Proto` line, the zone declarations, the
   byte-for-byte equality of the two server bodies where a test pins it); each new guard is shown failing under a quoted mutation.
7. Write `docs/program/EDGE-HARDEN-02.md`: what changed, the exact lines the host's server block must send (`X-Forwarded-For`,
   `X-Forwarded-Proto $scheme`), the operator setting (`ALPHA_TRUSTED_PROXY_CIDRS` on the stand), the commands run with exit status, the
   counts of the start loop before and after, "Decisions taken", and what is NOT proven (no stand probe).

## Deliverables

The changed proxy files and `serve.py`, the new and extended tests, and `docs/program/EDGE-HARDEN-02.md`.

## Required tests

One at a time, each redirected to a file with `$?` read from it, `nice -n 10`: `python3 -m pytest -q tests/contract/test_proxy_rate_limits.py
tests/contract/test_proxy_security_headers.py`; `python3 -m pytest -q tests/integration/composition/test_proxy_config_follows_checkout.py
tests/integration/composition/test_proxy_tls_path.py tests/integration/composition/test_real_client_address_at_the_edge.py
tests/integration/composition/test_edge_credential_gate.py tests/integration/composition/test_edge_scheme_and_connection_limits.py
tests/integration/composition/test_serve_is_ready_only_when_it_can_answer.py`; `nginx -t` against the committed configuration through the
tests' own harness; `git diff --check`; `python3 -m pytest -q tests/contract` with the complete gate's own three ignores
(`test_cp00_candidate.py`, `test_cp00_final_state.py`, `test_validate_bootstrap.py`) at the end.

## Integration contract

Merged by the integrator (not by the executor) as a real merge. Because the slice changes `infra/**`, the integrator runs the complete
`make gate` on the combined beta tree before any publication (`AGENTS.md` §8.3); the lane gate is waived. Commit after every solid step;
hand back with a SendMessage to "main" (the report is the last commit).

## Failure/idempotency/security cases

A forged `X-Forwarded-Proto: https` from a peer that is not trusted changes nothing (no HSTS, no `Secure`). A trusted peer that sends no
header is believed to be what `$scheme` says. A malformed CIDR still stops the container (the existing rule). A request over the connection
limit gets the contract-neutral refusal and the next one from the same address succeeds once a slot frees. Starting `serve.py` with the
two ports equal still refuses without binding anything.

## Rollback / feature flag

Revert the merge. With `ALPHA_TRUSTED_PROXY_CIDRS` empty the scheme logic is inert (the default); no flag.
