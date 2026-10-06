# W48-PROXY-01 — completion report

## Result

**DONE.** The base URL's path now decides where the proxy adapter sends a call:

| Base URL | Call URL |
| --- | --- |
| `https://<proxy>` or `https://<proxy>/` | `https://<proxy>/api/v1/chat/completions`, unchanged |
| `https://<proxy>/agent/v1` or `.../agent/v1/` | `https://<proxy>/agent/v1/chat/completions` |

`ProxySettings` refuses a base URL that contains `?` or `#` with `INTERNAL_ERROR` before the
adapter is built. That includes the query-string workaround `.../agent/v1/chat/completions?x=`
and a bare trailing `?`. No API, catalog, migration or composition change. `norms/__main__.py`
and `bootstrap/composition.py` pick up the rule through `ProxySettings` unedited.

Code commit: `63cb3ca` on `agent/w48-proxy-01`, base `fb5ba44` (`integration/w48-1`).

## Changed files

`git diff --name-only fb5ba44..HEAD`:

- `src/auditmanager/analysis/text/proxy.py`: `_completions_url` (the rule), the two path
  constants that replace `_PATH`, and the `?`/`#` refusal in `ProxySettings.__post_init__`
- `tests/integration/analysis_text/test_proxy_adapter.py`: class
  `TestTheBaseUrlNamesTheEndpoint`, 9 cases. No existing test edited; the diff only adds lines.
- `infra/deploy/env/provider.env.example`: the `proxy` mode comment block, covering both forms,
  the path each one calls, the `/api/` IP-allowlist note, and the `?`/`#` refusal
- `docs/program/W48-PROXY-01.md`: this report

`git status --porcelain -uall` is empty at hand-back.

## Tests

| Case | Asserts |
| --- | --- |
| `test_an_origin_keeps_the_portal_path_it_always_called` × 2 | `https://proxy.example` and `.../` call `https://proxy.example/api/v1/chat/completions`. This pins today's URL. |
| `test_a_base_with_a_path_is_called_at_its_completions` × 2 | `.../agent/v1` and `.../agent/v1/` call `.../agent/v1/chat/completions` |
| `test_a_query_or_a_fragment_is_refused_at_construction` × 5 | `.../agent/v1/chat/completions?x=`, `?x=1`, a bare `?`, `#f`, `.../agent/v1#f` each raise `INTERNAL_ERROR` |

`test_a_url_that_names_a_host_still_constructs` already includes a path-bearing URL
(`https://proxy.example.invalid/openai/v1`) and stays green, so it is the control for the refusal.

## Mutations (each applied to `proxy.py`, run, then restored from a byte copy; `cmp` clean)

| Mutation | Result |
| --- | --- |
| M1 (granted): always append `/api/v1/chat/completions` | red, **2 failed, 50 passed**: `test_a_base_with_a_path_is_called_at_its_completions[https://proxy.example/agent/v1]` and `[.../agent/v1/]`, `AssertionError: assert 'https://prox...t/completions' == 'https://prox...t/completions'` |
| M2 (granted): accept a query (refuse only `#`) | red, **3 failed, 49 passed**: `test_a_query_or_a_fragment_is_refused_at_construction[...?x=]`, `[...?x=1]`, `[...?]` |
| M3 (extra): an origin also gets `/chat/completions` | red, **2 failed, 50 passed**: `test_an_origin_keeps_the_portal_path_it_always_called[https://proxy.example]` and `[https://proxy.example/]` |

After restoring: `52 passed`.

## Checks

- `git diff --check`: clean
- `.venv/bin/python -m pytest tests/integration/analysis_text/test_proxy_adapter.py tests/integration/analysis_text/test_proxy_truncation_reaches_partial.py -q -p no:cacheprovider`
  → **54 passed in 0.89s**, exit 0
- full gate: run by the integrator on the merged candidate (host contention, integrator's call).
  The host was at load ~120 with the OOM killer active, and the integrator's W49 gate was
  killed (exit 137). The integrator's pre-`origin/main` gate on the merged candidate covers this
  lane, so no lane gate was run.

## Contracts

None changed: 17 paths / 20 operations / 61 schemas, catalog 22, migration head `0014`.

## Risks and known limitations

- **Reading of the rule.** The grant names an empty or `/` path; the code tests
  `not path.strip("/")`. The two agree on every URL the grant names. They differ only on a
  pathological base such as `https://p//`, which keeps today's portal URL instead of being sent
  to `https://p/chat/completions`. That matches the outcome's "an origin-only base URL keeps
  `<origin>/api/v1/chat/completions` byte for byte". Flagged to the integrator.
- **The fix only routes the call.** On the stand it also needs the owner's host steps:
  `PROXY_LLM_BASE_URL=https://proxyllm.fvds.ru/agent/v1` and an explicit `PROXY_LLM_MODEL`.
  This task did not verify whether the gateway honours `PROXY_LLM_MODEL` (non-goal). Measured
  2026-10-06: the key's default model on the gateway is not Claude (`provider_name: Meta` in an
  upstream error).
- **Not repaired here** (non-goals; registered by the integrator):
  - `_map_http_failure` folds 403/402/404/5xx into `analysis_failed`;
  - the proxy's error body is discarded except for 400/401;
  - the stage error message is not exposed to an operator.
- Nothing here can verify the agent gateway's response shape. The adapter reads it through the
  same `_from_openai_response` path, and the live acceptance run after deployment is the
  measurement.

## Forbidden-hotspot proof

`git diff --name-only fb5ba44..HEAD` lists exactly the four allowed paths above. No
`contracts/**`, migration, `web/**`, lock, `.github/**`, `CURRENT_STATE.md`,
`DEBT_REGISTER.md`, `OWNER_RULINGS_*.md` or `PORT_REGISTRY.md` path. The host's `provider.env` and
every key were neither read nor printed. Lane `gate-w48proxy` (ports 56730 / 60330 / 60331,
free by `ss -ltn`) started no services, so it has no containers or volumes to remove.

## Integration notes

Merge `agent/w48-proxy-01` into `integration/w48-1`. The code is one commit, `63cb3ca`; the
report is the commit after it. Rollback: revert the code commit. An origin-only base URL already
behaves as before, so no flag is needed.
