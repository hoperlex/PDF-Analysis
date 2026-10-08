# Task W52-DEBT-CODE-133 — classify and record proxy HTTP failures

task_id: W52-DEBT-CODE-133

## Outcome

The model-proxy adapter classifies non-model HTTP failures by existing error codes and reads,
bounds, redacts and logs the proxy error body without putting it in a client envelope.
Focused local-stub tests prove each new status mapping and body handling.

## Depends on

- `W52-FACTS-01` — integrated at `b5be37e56745f9d9ebecdd5e14fce64e5f58afdd`.
- `W52-INT-PREP-01` — published on `origin/dev` at `4fb6aca581c6c1e8647678309357008da9b5e567`.

## Frozen inputs

- Exact base `4fb6aca581c6c1e8647678309357008da9b5e567` plus the docs-only dispatch SHA
  named by the integrator. Domain revision 9 / 29 identities; API 27 paths / 34 operations /
  77 schemas; error catalog 23; migration head `0015_accounts_roles_registration`.
- Proposed `W52-PLAN.md` §4 at `2b45a11ec558df1452a4822149e54d2fe0ddb57e` and D-133.
  This is D-133's independent code-only half, not the full W52-DEBT-CODE lane or W52 freeze.
- Owner direction 2026-10-08: proceed without approval; QA, stand and full gate deferred
  to D-139/D-140; run only basic tests and lint.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No new error code is permitted; this task only maps statuses to the frozen catalog.

## Captured premise evidence

- premise: the current adapter has one default `analysis_failed` mapping and the plan grants
  the two code paths for D-133.

### P-01 — exact base and mapping

- captured_at: 2026-10-08
- command: `git rev-parse HEAD && rg -n '^def _map_http_failure|^    if exc.code in \(429, 503\)' src/auditmanager/analysis/text/proxy.py`
- captured_output:
  ```text
  4fb6aca581c6c1e8647678309357008da9b5e567
  302:def _map_http_failure(exc: urllib.error.HTTPError, model: str) -> DomainError:
  349:    if exc.code in (429, 503):
  ```
- interpretation: this identifies the exact implementation input; it does not prove the
  status table is complete.

### P-02 — plan grant

- captured_at: 2026-10-08
- command: `git show 2b45a11:docs/program/dispatch/W52-PLAN.md | sed -n '381p;394p;395p'`
- captured_output:
  ```text
  Also **`D-133`'s code-only half** (slotted to this lane by the integrator, 2026-10-07):
  Allowed adds: `src/auditmanager/analysis/text/proxy.py`,
  `tests/integration/analysis_text/test_proxy_adapter.py` (its `TestFailuresMapToTheCatalog` table is
  ```
- interpretation: the proposed plan isolates this code half from later RunStatus and
  model-configuration decisions.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/proxy.py`
- `tests/integration/analysis_text/test_proxy_adapter.py`
- `docs/program/W52-DEBT-CODE-133.md`

## Forbidden hotspots

Everything else, especially `contracts/**`, migration head, dependency/lock files,
`src/auditmanager/api/**`, access references, composition root, global styles and the
separate W56 RunStatus/model configuration work.

## Non-goals

- No D-128 F-7/F-10/F-11 repairs, RunStatus message, `PROXY_LLM_MODEL` startup refusal,
  new catalog code, W52 freeze, QA, stand, gate, release or `origin/main` publication.
- Keep existing 429/503/504 mappings, whose dispatch decisions belong to W53.

## Deliverables

- Map 402/403/404 and unclassified 5xx by whether a call was provably unprocessed and
  whether retry can help. For unknown outcomes fail nonretryable, never claim a model answered.
- Read at most a bounded body for every non-200 response; redact token-shaped strings and
  sensitive URLs before a server-side diagnostic log. Keep body out of `DomainError` messages
  and envelope details.
- Parametrized old-mapping-red tests per new status, plus a bounded/redacted log test and
  a no-client-leak test using only a local stub.

## Required tests

- `/root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/analysis_text/test_proxy_adapter.py`
- Python syntax compilation and `git diff --check`; no stand or full gate.

## Integration contract

Hand back a clean `agent/w52-debt-code-133` from the exact dispatch SHA with only allowed
paths. Integrator reviews the focused checks and may publish code preparation to `origin/dev`.
D-133 narrows only after the remaining W56 half is explicitly recorded.

## Failure/idempotency/security cases

Malformed or oversized bodies still produce a safe nonretryable/known mapping. Log input is
bounded and redacted; no raw body, token, URL or prompt reaches the API envelope. Same
status/body yields the same classification; logging does not change external effects.

## Rollback / feature flag

Revert the code commit. The change is a failure-classification correction with no new flag.

## Handoff

- changed files, commands/results, contracts, risks, integration notes, forbidden-hotspot proof.
