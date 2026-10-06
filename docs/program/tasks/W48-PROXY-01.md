# Task W48-PROXY-01 — address the model proxy's agent gateway by its base path

## Outcome

When `PROXY_LLM_BASE_URL` carries a path (for example `https://proxyllm.fvds.ru/agent/v1`), the
proxy adapter POSTs to `<base>/chat/completions`, the OpenAI `base_url` convention the proxy's own
client guide documents; an origin-only base URL keeps `<origin>/api/v1/chat/completions` byte for
byte. A base URL with a query or a fragment is refused when the settings are built.

## Depends on

- `W48-INT-MAIN-01` (`alpha-w48` at `23e0579`); this task file's commit on `integration/w48-1` is
  the base

## Frozen inputs

- API contract: 17 paths / 20 operations / 61 schemas — unchanged
- error catalog: 22 codes — unchanged (no new code, no new detail key)
- migration head: `0014_durable_analysis_effects` — unchanged
- code base: `23e0579` (`alpha-w48`), the deployed revision
- owner decision, direct poll 2026-10-06 (two polls: one taken by the acceptance session
  `pdf-analysis-61`, one by the integrator): repair in code, not by a query-string URL workaround
  and not by waiting for the proxy operator's allowlist; delivered as a hotfix of `alpha-w48`
  before the identity waves reach the stand

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the adapter appends a fixed `/api/v1/chat/completions` to the base URL, so the agent gateway's path cannot be addressed

### P-01 — the fixed path

- captured_at: 2026-10-06
- command: `git grep -n -E "_PATH|rstrip" 23e0579 -- src/auditmanager/analysis/text/proxy.py`
- captured_output:
  ```text
  23e0579:src/auditmanager/analysis/text/proxy.py:50:_PATH: Final[str] = "/api/v1/chat/completions"
  23e0579:src/auditmanager/analysis/text/proxy.py:123:            self._settings.base_url.rstrip("/") + _PATH,
  ```
- interpretation: a base URL of `https://proxyllm.fvds.ru/agent/v1` would be called as
  `/agent/v1/api/v1/chat/completions` and answer 404.

### P-02 — the stand is refused before any key is read (measured by `pdf-analysis-61`)

- interpretation: run `run_01M48AN1Z1AMCCR0MXEKCZFWE6` (evidence
  `.local/worktrees/w48-close/.local/manual-alpha/20261006T100100Z-1825258`) failed in
  `text_analysis` with `analysis_failed` in 230 ms; the stored stage error is "the model proxy
  answered with status 403". The nginx in front of the proxy allowlists IPs on `location /api/`;
  from the stand an unauthenticated POST gets nginx's HTML 403, from this host the application's
  JSON 401. The agent gateway `/agent/v1/chat/completions` has no IP gate: from the stand,
  unauthenticated → JSON 401 `invalid_api_key`, keyed → an upstream 400 (the key passed).

## Historical evidence

- correction_mode: none
- source_record: the acceptance session's report to the integrator, 2026-10-06
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/proxy.py` — the URL the adapter calls and the `ProxySettings`
  validation only
- `tests/integration/analysis_text/test_proxy_adapter.py`
- `infra/deploy/env/provider.env.example` — the comment block of the `proxy` mode: the two URL
  forms, which path each one calls, and the IP-allowlist note
- `docs/program/W48-PROXY-01.md` (report)

## Forbidden hotspots

- every path not listed above; `contracts/**`; migrations; `src/**` outside `proxy.py`
  (`norms/__main__.py`, `bootstrap/settings.py` and `bootstrap/composition.py` inherit the rule
  through `ProxySettings` and are not edited); `web/**`; root locks; `infra/deploy/**` outside the
  one example file; `.github/**`; refs, tags, `origin/*`; `CURRENT_STATE.md`, `DEBT_REGISTER.md`,
  `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`
- the host's `provider.env` and any credential: never read, copied or printed

## Non-goals

- the error mapping: `_map_http_failure` folding 403/402/404/5xx into `analysis_failed`, the
  discarded proxy error body, and the stage error message no operator can see are registered by
  the integrator, not repaired here
- choosing a model: whether the agent gateway honours `PROXY_LLM_MODEL` is an operator
  measurement, not this task's
- no retry or timeout change; no change for an origin-only URL

## Deliverables

- the call URL rule: if `urlsplit(base_url).path` is empty or `/`, the URL is
  `<origin>/api/v1/chat/completions` exactly as today; otherwise it is
  `<base_url without a trailing slash>/chat/completions`
- `ProxySettings` refuses a base URL with a query or a fragment (`INTERNAL_ERROR`, a message that
  names the rule), before any call
- the `provider.env.example` comment states both forms and that the `/api/` form may be
  IP-allowlisted by the proxy's operator

## Required tests

- origin-only base (with and without a trailing slash) → `/api/v1/chat/completions` (pins today's
  URL); `/agent/v1` and `/agent/v1/` → `/agent/v1/chat/completions`; `?x=` and `#f` refused at
  construction; the existing adapter tests unchanged and green
- two mutations, each red with its output in the report: always append `/api/v1/chat/completions`;
  accept a query
- `git diff --check`; a full `make gate` on the task's head with the literal `GATE OK`

## Integration contract

The integrator merges `agent/w48-proxy-01` into `integration/w48-1`, gates the merged candidate,
and — on the owner's direct instruction naming the exact SHA — publishes it to `origin/main` for
deployment, then merges the hotfix line into `integration/w50`.

## Failure/idempotency/security cases

- lane `gate-w48proxy`: ports `56730`, `60330/60331`, taken with `ss -ltn` and recorded; owned
  disposable services only; `make down` and remove the lane's own volumes by exact name at the end
- before a full gate: no other `make gate` on the host (`pgrep -x make` and its cmdline, never
  `pgrep -f`) and at least 3 GB available
- never kill a process by pattern — only confirmed-own PIDs; no credential, key or proxy response
  body in evidence

## Rollback / feature flag

Revert the commit; an origin-only base URL already restores today's behaviour without a flag.

## Handoff

- changed files: listed in `docs/program/W48-PROXY-01.md` with `git diff --name-only <base>..<sha>`
  and `git status --porcelain -uall` empty
- commands/results: verbatim with exit status; every mutation with its red output
- known limits: listed, never decided silently
- integration notes: hand back branch `agent/w48-proxy-01` at a recorded SHA
