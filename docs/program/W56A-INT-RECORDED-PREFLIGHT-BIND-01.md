# W56A-INT-RECORDED-PREFLIGHT-BIND-01 — result

The executor-side recorded preflight now resolves the immutable AR v2
profile/bundle registration through `analysis.public` and verifies its reviewed
material before comparing persisted run identity, state and recorded adapter
mode. A well-formed but unregistered identity and changed material both fail
before any effect. The current `execute_run` still does not call this helper.

## Changed files

- `src/auditmanager/analysis/public.py` — public recorded descriptor resolver
  and pinned IDs;
- `src/auditmanager/runs/executor.py` — binding from preflight to resolver;
- `tests/integration/runs/test_v2_recorded_executor.py` — registered identity,
  unknown identity and content-drift checks;
- this report and `tasks/W56A-INT-RECORDED-PREFLIGHT-BIND-01.md`.

## Checks

- Profile, preflight and recorded chain: **25 passed**. Pytest emitted five
  warnings while cleaning unrelated stale `/tmp/pytest-of-root` directories;
  no test failed.
- Python compilation and whitespace: pass.
- Direct governance, frozen hashes and exact path proof: recorded at integration.
- No DB acceptance or full `make gate` under R-135.

## Contracts and limits

No contract, migration, provider lock, root dependency, composition root,
global style, v1 execution path or recording changed. This strengthens a
read-only preflight; it does not start a v2 run or authorize a provider call.
The next owner must build the v2 recorded request/checksum, artifact, stage
result and run transaction under its own task. Revert these public exports
and binding to roll back before activation.
