# AR-V3-BETA-REQUEST-CUSTODY-01 — request custody bridge

The read-only `prepare_v3_execution_request` now joins one current Job Attempt to its persisted six-Run group member, installed pack, exact verified retrieval-set Blob, scoped v3 profile and transport-independent `ModelRequest`. It returns both the local candidate SHA and provider-body SHA. It checks the group's pins again after the Blob read and request construction. Wrong provider mode, source text version, Run pins, set custody or changed group authority refuses before dispatch.

The result is deliberately unserved. Production has no installed reviewed pack, and `execute_run` continues to refuse v3 before Job or provider effects. The future executor must supply a text layer from the saved deterministic source stage, verify the provider-selected model identity, journal both SHA values, and recheck current Attempt/set authority immediately before dispatch and after response. This bridge does not record a call, response, CITE stage or finding.

## Verification

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_execution_request.py tests/integration/runs/test_v3_corpus_citation_bridge.py tests/integration/analysis/test_ar_v3_request_delivery.py -x --tb=short`: **48 passed**.
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_execution_guard.py tests/integration/analysis/test_ar_v3_profile_seal.py -x --tb=short`: **26 passed**.
- New task's `governance_findings`: empty. The broader `tests/contract/program` run reached 40 passing checks, then failed on three pre-existing task documents (`EXEC-ENV-OPENROUTER-01`, `EXEC-SSH-CROPS-01`, `EXEC-SSH-TUNNEL-CROPS-01`) with missing governance declarations. Those files are outside this task's allowed paths.
- `git diff --check`: passed.
- Changed paths are exactly the six `allowed_paths` in the task. No contract, migration, composition root, dependency/lockfile, global style, provider transport, executor or norm-map/source data changed.

## Integration note

The full `AR-V3-BETA-EXECUTE-01` owner calls this after committing a current Job/Attempt and reading the saved source-stage text. The returned object is valid only for that Attempt and is not a durable provider intent. It must be followed by the existing provider journal boundary and renewed authority checks. `AR-V3-BETA-CITE-01` remains separate. No beta acceptance is claimed.
