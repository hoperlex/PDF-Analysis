# AR-V3-BETA-REPLY-REPLAY-01 — CITE reply readback

`read_v3_reply` reads the private reply Blob with storage verification and independently checks its byte count and SHA. It accepts only the `ar-v3-provider-reply/1` envelope with the exact Run, model-call, provider, candidate, provider-body and response digests supplied from a completed call. It reconstructs `ModelResponse`, recomputes its canonical response SHA, and returns a `SuppliedV3Response` for deterministic citation review. Duplicate keys, nonfinite numbers, malformed usage, extra fields and substituted answer text refuse. The reader never calls a model or grants a normative verdict.

The positive test reads a Blob written by the v3 provider-call path; separate tests reseal altered envelopes to prove that checking only the Blob SHA would be insufficient. The next CITE integration must read canonical `model_call` and `provider_call_effect` rows, compare their ownership and state, rebuild the sealed request from saved Run/set bytes, then use this reader and bind the reply ref with the review StageResult.

## Verification and handoff

- Task: [AR-V3-BETA-REPLY-REPLAY-01](tasks/AR-V3-BETA-REPLY-REPLAY-01.md), frozen from `985e3a1cd0a6543c35ffcbf7dd2a872cb21f5832`.
- Changed paths: `src/auditmanager/runs/v3_reply_custody.py`, `tests/integration/runs/test_v3_reply_custody.py`, `tests/integration/runs/test_v3_provider_call.py`, this result, task file and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`.
- Focused checks: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_reply_custody.py tests/integration/runs/test_v3_provider_call.py -x --tb=short` — **27 passed**. With the existing request, guard, corpus and delivery suites: **84 passed**. Task governance is empty, `git diff --check` passed, and all six changed paths match the task allowlist.
- New or changed contracts: none in `contracts/**`; consumes internal private reply format `ar-v3-provider-reply/1` from the previous task.
- Risk: the reader's expectation is a claim until the CITE owner obtains it from a completed, matching DB call/effect. A Blob alone is not provider provenance.
- Integration: call the reader only with verified Blob ref and canonical call/effect facts; pass its `supplied_response` to `plan_v3_beta_citation_review` under the same pinned saved set and project text.
- Rollback: unserved and read-only; the existing v3 executor guard remains.
- Forbidden hotspots: contracts, migrations, root dependencies/lockfiles, composition root, active executor, global styles, adapters and normative maps/source data were not changed.
