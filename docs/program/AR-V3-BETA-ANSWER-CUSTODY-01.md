# AR-V3-BETA-ANSWER-CUSTODY-01 — durable AR v3 reply

The AR v3 provider boundary now publishes the parsed `ModelResponse` as a private, verified Blob after committing the response digest and usage. The artifact has internal format `ar-v3-provider-reply/1` and role `analysis.v3_provider_reply`. Its canonical JSON carries exact answer text, stop reason, reported model and cost, provider, model-call ID, request/candidate/response digests and usage. The SHA of this envelope is separate from the existing canonical `ModelResponse.response_sha256` and from any raw HTTP wire-body SHA.

Publication uses the existing Attempt-scoped `analysis_artifact_publication` outbox: declaration and intent commit before external upload, verification before canonical publication, and exact readback before `model_call` completion. The completed call's parameters include reply Blob ID, SHA and size; the returned receipt includes the `ArtifactRef`. If publishing or readback fails, the already committed `response_received` effect remains and no successful call is recorded. The CITE owner can verify the Blob, check its hashes against the completed call and bind this reply ref with its review StageResult. An interrupted Attempt is never replayed automatically.

The active executor guard remains and the production trusted-pack registry is empty. No model call is served yet. CITE StageResult, answer interpretation, expert review and numerical publication remain open.

## Verification and handoff

- Task: [AR-V3-BETA-ANSWER-CUSTODY-01](tasks/AR-V3-BETA-ANSWER-CUSTODY-01.md), frozen from `a86e7cf16e77e33b9c7a7e10004b0b2d6830d69e`.
- Changed paths: `src/auditmanager/runs/v3_provider_call.py`, `tests/integration/runs/test_v3_provider_call.py`, this result, the task file, and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`.
- Focused checks: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_provider_call.py tests/integration/runs/test_v3_execution_request.py tests/integration/runs/test_v3_execution_guard.py tests/integration/runs/test_v3_corpus_citation_bridge.py tests/integration/analysis/test_ar_v3_request_delivery.py -x --tb=short` — **71 passed**. The new task's `governance_findings` is empty and `git diff --check` passed.
- New or changed contracts: no `contracts/**` change; internal private reply format `ar-v3-provider-reply/1` added.
- Integration: CITE must read the reply Blob with `verify=True`, compare call ID, request/candidate/response hashes, scope/set pins, and bind the reply artifact in the same transaction as its review StageResult. Do not infer a legal verdict from the raw answer.
- Rollback: this slice is unserved behind the existing v3 executor guard; no production data was created.
- Forbidden hotspots: contracts, migration, root dependencies/lockfiles, composition root, active executor, global styles, provider adapters and normative maps/source data were not changed.
