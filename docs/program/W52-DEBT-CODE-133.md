# W52-DEBT-CODE-133 — executor handoff

Task: `docs/program/tasks/W52-DEBT-CODE-133.md`. Dispatch base:
`cff79e451d1900d5b0ee5a62d8aefc18e13e940d`. This is D-133's independent code half,
not the full W52-DEBT-CODE or a W52 release claim.

## Result

The proxy adapter now sends every non-200 response through one mapper. It reads at most
4097 bytes of a failure body, logs one bounded/redacted diagnostic line, and keeps raw
body content out of `DomainError` and the API envelope. Malformed JSON still maps.

The new status rule uses only existing catalog codes:

| Proxy status | Catalog result | Reason |
|---|---|---|
| 403 | `dependency_credential_refused` | access/allowlist/key policy is an operator repair |
| 402, 404, unclassified 5xx and other unknown statuses | `internal_error` | no confirmed model answer or proof that replay is safe |
| 429, 503, 504 | `dependency_unavailable` | existing mapping preserved for W53 dispatch ownership |

401, 400 and 413 keep their previous catalog mappings. A direct HTTPError and a returned
non-200 response follow the same rule. The body is logged only after URL, bearer, email,
token-shaped and long opaque fragments are replaced; control characters are flattened.

## Changed files

- `src/auditmanager/analysis/text/proxy.py`
- `tests/integration/analysis_text/test_proxy_adapter.py`
- `docs/program/W52-DEBT-CODE-133.md`

## Checks and limits

- Focused local-stub proxy tests: 64 passed. Each newly mapped status differs from the old
  `analysis_failed` default; tests also prove bounded read, redacted log, no envelope leak,
  malformed body handling and unchanged retryability of 429/503/504.
- Python syntax compilation, frontend lint and `git diff --check`: passed.
- No temporary stand, live provider call, QA or full gate, under D-139/D-140.

No contract, migration, root dependency/lock, API router, composition root or global style
changed. D-133 remains open for the W56 RunStatus message and configured-model startup
decision. The status policy for 429/503/504 still belongs to W53. Future validation should
exercise the same statuses through the deployed proxy before making a release claim.

Merge this clean executor commit into the integration line and publish only to `origin/dev`.
All changed files are within the task's `allowed_paths`; forbidden hotspots are untouched.
Rollback is a revert of the executor commit; no feature flag applies.
