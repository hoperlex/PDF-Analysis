# W52-DEBT-CODE-128F11 — executor handoff

Task: `docs/program/tasks/W52-DEBT-CODE-128F11.md`. Exact dispatch base:
`409b2c6ed816284f392185b536296cec95290a98`. This repairs D-128 F-11 only.

`analysis.public` exports the text stage's existing version under the precise name
`TEXT_STAGE_VERSION`. The sole cross-context consumer, `runs.executor`, imports that
name without a local alias. A focused contract test compares its value with the
text-stage source, verifies the public export set, rejects the broad old name, and
imports the executor. The internal version constant and persisted value are unchanged.

Changed files: `src/auditmanager/analysis/public.py`,
`src/auditmanager/runs/executor.py`,
`tests/contract/architecture/test_analysis_public_stage_version.py`, and this report.
The two focused architecture files passed 3 tests; Python syntax compilation,
frontend lint and `git diff --check` passed. No temporary stand, QA or full gate was
run under D-139/D-140. The rename is a Python public-module change, so untracked
external importers of `STAGE_VERSION` would need the precise name; the repository scan
found only the updated executor importer.

No wire contract, migration, dependency/lock, API root, bootstrap composition root or
global style changed. D-128 remains open for F-1/F-10 and validation. The integrator
may merge this clean code preparation to `origin/dev` after exact ancestry and basic
checks. Rollback is the code commit's revert; no runtime feature flag.
