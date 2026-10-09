# W53-PROXY-REPAIR-01 — truthful foreign 503 and body-free diagnostics

Branch: `agent/w53-proxy-repair-01`. Assigned base:
`5eed1b04a50162fb9180141609be4288c9c4e7f5`. The exact handback HEAD is
read back and sent to the integrator after this report is committed.

## 1. Changed files

- `src/auditmanager/analysis/text/proxy.py`: an unclassified 503 now says the
  model-call outcome is unknown; refusal warnings include only numeric status
  and the bounded-read truncation flag, never response-body text.
- `tests/integration/analysis_text/test_proxy_adapter.py`: checks body-free
  logs and envelopes across refusal statuses, unchanged 503 dispatch safety,
  and the 4097-byte read bound.
- `docs/program/W53-PROXY-REPAIR-01.md`: this handback.

## 2. Checks and results

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/pytest -q
  tests/integration/analysis_text/test_proxy_adapter.py
  tests/integration/qa_w53/test_proxy_refusal_boundary.py`: **91 passed** in
  0.21 s. Log `/tmp/w53-proxy-repair-01/focused.log`, SHA-256
  `b91a86aa07ce6c7d7fb75a7003358ee9d6980bcc96a3e674a6f3644925f97aaa`.
  The two QA tests were run unchanged. Synthetic private prose in HTTP error
  bodies appears in neither warning records nor returned envelopes.
- `python3 -m compileall -q` on the changed Python source and test: passed.
- `git diff --check`: passed. Base-to-handback changed-path audit contains
  exactly the three paths in §1.
- Frozen OpenAPI SHA-256: `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`.
  Frozen domain state-machine SHA-256:
  `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.
  Both equal the assigned task's pins.

## 3. Contracts

No API, domain, migration, error-code or wire-shape contract changed.
HTTP 503 remains `outcome_unknown`, `retry_safe=False`, with no automatic
replay. The 429, pre-send and definite-refusal classifications stay as they
were. Only the misleading 503 message and unsafe warning content changed.

## 4. Risks and known limitations

The genuine own-proxy 503 discriminator is still missing; this repair does
not infer one from response text or mark any 503 safe to retry. The catalog's
`dependency_unavailable` envelope retains its existing retryable flag, while
the execution policy uses `ProxyDispatchError.retry_safe=False` for 503.
`W53-EXEC-STOP-01` therefore remains open. The focused test is pure and did
not need a Docker service or a heavy-run disk preflight.

## 5. Integrator instructions

Cherry-pick the clean handback HEAD, verify the exact three-path diff, then
rerun the unedited independent QA proxy boundary tests on the merged SHA.
Keep `W53-EXEC-STOP-01` open until the owner supplies a measured own-proxy
envelope. Perform the final full gate only under the disk preflight rule.

## 6. Forbidden-hotspot proof

The base-to-HEAD path list is exactly the three §1 paths, all allowed by
`tasks/W53-PROXY-REPAIR-01.md`. No contract, migration, composition root,
router, dependency/lock file, global style, generated client, QA-owned test,
release, backup or deployment path changed. No ref or tag was published,
no working stand was touched and no shared Docker data was pruned.
