# AR v3 executor refusal guard — development result

**Task:** [AR-V3-BETA-EXECUTE-GUARD-01](tasks/AR-V3-BETA-EXECUTE-GUARD-01.md). **Base:** published `origin/dev` `1b605f9d4597927942a5a8951d3203ffa75bb191`. **Target:** `origin/dev` only.

## Result

The Run executor now recognizes either sealed AR v3 beta identity field and refuses before it creates a Job, starts a stage, reads a Blob or calls a provider. This includes a mismatched profile/bundle pair and a direct in-process caller with no text-profile registry. Previously that caller selected the AR v1 profile for a v3 Run. The public analysis facade exports the same identity pair as the immutable v3 resolver, so the Run boundary does not import an internal profile module.

This is a fail-closed preparation for `AR-V3-BETA-EXECUTE-01`. Production still has no reviewed pack or v3 executor; new group starts remain disabled. A prematurely activated pack would leave queued v3 Runs awaiting the future executor, so pack activation must be integrated with that executor rather than deployed by itself.

## Changed files and checks

- `src/auditmanager/analysis/public.py` — public sealed v3 identity constants.
- `src/auditmanager/runs/executor.py` — pre-effect refusal for either v3 identity field.
- `tests/integration/runs/test_v3_execution_guard.py` — exact/mismatched pair, absent/malicious resolver, zero-effect and historical v1 cases.
- Task file, this report and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md` — ownership and next-step status.

Focused Run suite including the recorded-v2 bridge: **20 passed**. Analysis package and API seal contracts: **56 passed**. `git diff --check` and the exact allowed-path inventory passed, with zero paths outside the task. Full `make gate` remains with the final beta candidate under `R-135`.

## Integration and rollback

No contract, migration, composition root, root dependency/lock file, global style, normative source/map, provider adapter, CITE publication, `origin/main`, tag or deployment host changed. The later full executor must replace this stop with a path that verifies the Run's group/pack/set and current Attempt, commits authority before dispatch, records provider bytes/provenance and refuses any missing pin without AR v1 fallback. Until then, retain the guard. A revert is safe only with that verified replacement in the same tree.
