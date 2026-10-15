# W56A-INT-RECORDED-EXECUTOR-01 — result

The run executor now has an additive `plan_recorded_v2_execution` preflight.
It checks that a persisted run's profile and bundle match separately supplied
registered identities, that the run, adapter and provider configuration all
say `recorded`, and that the run is executable. It explicitly rejects the v1
profile. The returned intent has no DB, blob or provider effect.

## Changed files

- `src/auditmanager/runs/executor.py` — inert preflight and typed intent;
- `tests/integration/runs/test_v2_recorded_executor.py` — recorded acceptance
  and rejection probes;
- this report and `tasks/W56A-INT-RECORDED-EXECUTOR-01.md`.

## Checks

- Focused no-DB executor preflight and recorded finding-chain suite: **14 passed**
  (`9` preflight, `5` chain).
- Python compilation, direct governance (`[]`), `git diff --check` and
  whitespace over all four owned paths: passed.
- PostgreSQL acceptance and complete `make gate`: deferred under R-135.

## Contracts and limits

No contract, migration, provider lock, findings or analysis module, existing
run repository/commands, composition root, root dependency/lock file, global
style, historical fixture or Git ref changed. The existing v1 `execute_run`
path and its provider-effect boundaries are unchanged. The preflight is **not
called** by `execute_run` and does not activate AR v2.

Full runtime wiring is blocked by the absent immutable AR v2 profile/bundle,
recorded request path and stage/artifact semantics. `run_text_analysis` still
uses v1's profile, schema and recording directory; terminal selection still
uses `PC01_STAGES` and v1 publication. The recorded response-to-publication
chain is not exported on `findings.public`. These require separate owners and
PostgreSQL tests. A caller-provided registration cannot authenticate itself;
the later runtime must source it from a pinned profile registry and verify
recording checksum, model-call provenance and idempotency.

## Integration instruction

Stage only the four owned paths on `e4cf264b`. Keep the v1 path untouched.
Wire this preflight only after immutable v2 profile and request/stage owners
are integrated; source profile/bundle IDs independently from the run row and
connect publication through the findings public seam. Do not infer provider
or beta authorization from this preflight.
