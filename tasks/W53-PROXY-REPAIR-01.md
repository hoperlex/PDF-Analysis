# Task W53-PROXY-REPAIR-01 — truthful 503 outcome and safe refusal logging

## Outcome

For a foreign or unclassified HTTP 503, the proxy adapter must keep `outcome_unknown`/zero automatic replay and must not claim that the upstream call was never made. No arbitrary response-body text may enter service logs. Add regressions for both facts.

## Depends on

- W53-SEAL-01
- W53-EXEC-01 (implementation handback integrated; `W53-EXEC-STOP-01` remains open)
- W53-REHEARSAL-01 (foreign 503 runtime result integrated)

## Frozen inputs

- domain revision 9 / 29 identities; state-machine SHA-256 `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.
- API `1.0.0-draft.1`, 36/43/91; OpenAPI SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`.
- analysis/comparison/event: frozen W53 SEAL set; migration head `0017_execution_queue`.
- base code before this dispatch amendment: `a21f2ffe392dfc4879fd7417b20f0a1d1f130902`, which includes the independent QA report and six red guards. Integrator assigns the exact post-amendment SHA.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

### P-01 — independent X and QA failure, reproduced by integrator

- captured_at: 2026-10-09
- command:
  ```bash
  PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python - <<'PY'
  import io, logging
  from auditmanager.analysis.text.proxy import _classified_http_failure
  buf=io.StringIO(); log=logging.getLogger('auditmanager.analysis.text.proxy'); handler=logging.StreamHandler(buf); log.addHandler(handler); log.setLevel(logging.WARNING)
  try:
      error=_classified_http_failure(503,b'{"error":{"code":"foreign","message":"PRIVATE DOCUMENT CHAIRMAN NOTES"}}',headers={})
  finally:
      log.removeHandler(handler)
  print(error.dispatch_class, error.retry_safe, error.custom_message)
  print('synthetic_secret_in_log=', 'PRIVATE DOCUMENT CHAIRMAN NOTES' in buf.getvalue())
  PY
  ```
- captured_output:
  ```text
  outcome_unknown False the model proxy is saturated; the call was not made
  synthetic_secret_in_log= True
  ```
- interpretation: the classifier is conservative, but the user/persisted message is false and arbitrary body content reaches a warning log. QA independently has two red tests at `/tmp/w53-qa-01/proxy-refusal-boundary.log` (SHA-256 `4cde8cbdbba46d48bfabdfb4c61a2165d5a263cb545a17cb95d8535136fd76a0`). The synthetic marker is not real sensitive data.

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
- `docs/program/W53-PROXY-REPAIR-01.md`

## Forbidden hotspots

- `contracts/**`, migration, `src/auditmanager/analysis/engine/**`, routers, composition root, root dependency/lock, global styles, generated client, QA-owned `tests/integration/qa_w53/**`, release/backup/deployment paths and working stand.

## Non-goals

- Defining an own-proxy 503 discriminator or declaring 503 retry-safe. `W53-EXEC-STOP-01` still needs owner-supplied measured envelope.
- Changing classification/idempotency, the catalog, StageResult persistence, or unrelated status mappings.

## Deliverables

- Narrow source fix and meaningful tests for unclassified 503 message and bounded, body-free refusal diagnostics across statuses. Maintain useful stable status/truncation information without logging untrusted code/message/body.
- New six-item handback report with branch, exact base/HEAD SHA, test commands/results/log hashes and allowed-path proof.

## Required tests

- Run the focused proxy adapter suite. Prove with a synthetic confidential string embedded in an HTTP body that neither logger output nor API/persisted error message contains it. Assert foreign 503 remains `outcome_unknown`, `retry_safe=False`, and public message does not assert non-processing. Preserve 429/no-bytes/400 behavior and existing error codes. Run `git diff --check`, frozen SHA check and exact changed-path audit.
- Run, without editing, `tests/integration/qa_w53/test_proxy_refusal_boundary.py`; its two red assertions at this base must turn green. The QA test path is not granted to this repair lane.
- Before any heavy service run, perform AGENTS.md §8 disk preflight. A pure test needs no new Docker lane. Keep logs under `/tmp/w53-proxy-repair-01/`.

## Integration contract

After the fix, the proxy gives a truthful uncertainty message and logs only safe fixed diagnostics; executor retry policy is unchanged. Integrator will repeat QA's independent red tests on the merged candidate. Any out-of-grant need stops for a new repair grant.

## Failure/idempotency/security cases

- Foreign 503 may have reached provider: never promise otherwise or replay automatically. Body may contain a full prompt, document or credential irrespective of regex patterns: do not emit any arbitrary body bytes.

## Rollback / feature flag

No feature flag. Revert the narrow repair commit if it breaks the sealed error shape; retain conservative 503 behavior.

## Handoff

- changed files; commands/results; contracts; risks; integration instructions; forbidden-hotspot proof — six AGENTS.md §5 items.
