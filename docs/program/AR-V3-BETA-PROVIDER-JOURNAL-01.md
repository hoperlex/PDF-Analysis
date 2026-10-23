# AR-V3-BETA-PROVIDER-JOURNAL-01 — provider boundary for AR v3

The new `dispatch_v3_provider_call` operation joins the saved-source and verified-set v3 request to the existing `provider_call_effect` / `model_call` journal. It accepts one current group-member Attempt and one bound model adapter. It refuses absent reviewed packs, mismatched provider mode, unpinned live model identity, and a prior non-retryable call before it can dispatch.

The operation commits the intent with the exact provider-body SHA and the original candidate SHA before calling the adapter. It checks the group/set pins again immediately before dispatch. It commits the response SHA, token counts and latency before model identity or downstream citation checks, then rechecks the Attempt and pins and commits the canonical call with provider revision, mode and reported cost. An answer or uncertain live failure is never silently retried. A recorded transport test captures the canonical request bytes and answer text bytes, and checks the journal order.

This is the provider boundary for the later CITE stage, not an activation of the served executor. The existing v3 guard and empty production pack registry remain. The journal retains hashes and usage, not raw prompt or answer text. The returned answer is untrusted and available to CITE during the same execution; if the process dies before CITE publishes its artifact, recovery must fail that Attempt without reissuing the call. A verified raw-answer artifact and grounded review StageResult belong to the CITE owner. Until then, no v3 numerical finding or successful v3 Run is claimed.

## Verification and handoff

- Task: [AR-V3-BETA-PROVIDER-JOURNAL-01](tasks/AR-V3-BETA-PROVIDER-JOURNAL-01.md), frozen from `4c47dbbdcf3c02e13b7e637ed4d486b0dd914410`.
- Changed paths: `src/auditmanager/runs/v3_provider_call.py`, `tests/integration/runs/test_v3_provider_call.py`, this result, the task file, and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`.
- Focused checks: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_provider_call.py tests/integration/runs/test_v3_execution_request.py tests/integration/runs/test_v3_execution_guard.py tests/integration/runs/test_v3_corpus_citation_bridge.py tests/integration/analysis/test_ar_v3_request_delivery.py -x --tb=short` — **69 passed**. The new task's `governance_findings` is empty and `git diff --check` passed.
- New or changed contracts: none. Migration head remains `0032_ar_v3_run_group`.
- Integration: call only after a committed running Run/Job/Attempt with a reviewed pack and active heartbeat. Consume the returned response immediately in the CITE owner; the effect journal is the durable retry fence, not a response-body store.
- Rollback: this operation is not wired into the active executor; the existing v3 refusal remains the feature gate.
- Forbidden hotspots: contracts, migration, root dependencies/locks, composition root, active executor, global styles, provider adapters, normative maps and source data were not changed.
