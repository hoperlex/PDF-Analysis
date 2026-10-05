# Task W49-EDGE-01 — proxy rate limit and the proxy flag

## Outcome

`POST /api/v1/registrations` and `POST /api/v1/registrations/status` are rate-limited at the proxy with the `rate_limited` envelope, and the `web` service runs with `AUDITMANAGER_BEHIND_PROXY=1`.

## Depends on

- `W49-SEAL-01` merged

## Frozen inputs

- domain contract: revision 8, 27 opaque identities (moves only in `W49-SEAL-01`)
- API contract: 17 / 20 / 61 (moves only in `W49-SEAL-01`)
- error catalog: 22 codes (moves only in `W49-SEAL-01`: `rate_limited`)
- migration head: `0014_durable_analysis_effects` (moves only in `W49-ACCESS-01`)
- code base: `23e0579`, the W48 closure published to `origin/dev`
- controlling plan: `docs/program/dispatch/W49-PLAN.md` at the freeze commit

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: no rate limit exists at the proxy

### P-01 — base measurement

- captured_at: 2026-10-05
- command: `grep -c 'limit_req' infra/deploy/proxy/nginx.conf infra/deploy/proxy/tls-server.conf`
- captured_output:
  ```text
  infra/deploy/proxy/nginx.conf:0
  infra/deploy/proxy/tls-server.conf:0
  ```
- interpretation: measured on the code base before dispatch; the lane re-measures it first.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/dispatch/W49-PLAN.md`
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `infra/deploy/proxy/nginx.conf`, `infra/deploy/proxy/tls-server.conf`
- `infra/deploy/compose.server.yml` — the one `AUDITMANAGER_BEHIND_PROXY=1` line on `web`
- `tests/contract/test_proxy_rate_limits.py` (new)
- `docs/program/W49-EDGE-01.md`

## Forbidden hotspots

- every path not listed above; `contracts/**` outside `W49-SEAL-01`; root locks; refs, tags, deployment and secrets; `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md` except an exact sentence named here

## Non-goals

- no other proxy or compose change; no new `/api/v1` location

## Deliverables

- `W49-PLAN.md` §3.5 proxy throttle: zone and map once in `nginx.conf` keyed by `$request_method:$uri`, `limit_req` and `@rate_limited` in both server bodies, the envelope with `$request_id`

## Required tests

- the new contract test reads both proxy files and the compose file and checks the `error_code` against the catalog
- `nginx -t` in the pinned nginx image with both files under `conf.d/` and a throwaway self-signed pair at `/etc/nginx/tls/`
- `tests/integration/composition/test_proxy_tls_path.py`; `make gate` with literal `GATE OK`

## Integration contract

The proxy answers only the two registration operations with 429; nothing else is throttled.

## Failure/idempotency/security cases

- unique lane ports taken with `ss -ltn` and recorded; owned disposable services only; never kill a process by pattern; no credential in evidence

## Rollback / feature flag

Revert the commit.

## Handoff

- changed files: listed in `docs/program/W49-EDGE-01.md` with `git diff --name-only <base>..<sha>`
- commands/results: verbatim with exit status; every mutation with its red output
- known limits: listed, never decided silently
- integration notes: hand back branch `agent/w49-edge-01` at a recorded SHA
