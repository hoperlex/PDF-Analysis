# W59-INT-DECISION-CARRYOVER-PREP-01 — development result

Added an inert, pure W59 offer and confirmation plan for prior-version expert
verdicts. An input must name an explicit one-to-one finding match, immutable
matching evidence checksum/revision, the source's current verdict-bearing
decision and both event counts. Only `accepted` or `rejected` can be offered;
a target with any prior event is refused. The offer digest binds every input
field. Single and bulk confirmation rederive current offers and refuse a stale
or unknown selection as a whole. The returned plan is not a ledger event or
permission to append one.

## Checks

- At a short CPU/RAM window, `timeout 60s .venv/bin/python -m pytest -q -p
  no:cacheprovider tests/integration/comparison/test_decision_carryover.py`
  passed: **14 passed in 0.28s**. `timeout 10s .venv/bin/python -m compileall
  -q` on both changed Python files exited 0. The host remained below the W54
  disk floor, so neither check competed with a corpus restore.
- `git status --short` showed exactly the four new paths below. `git diff
  --no-index --check /dev/null <file>` for each emitted no whitespace
  diagnostics (exit 1 denotes the expected new-file diff).
- No Docker, DB, network, paid call or full gate was run.

## Contracts, limits and integration

No contract, migration, runtime route, storage, expert decision ledger or raw
comparison evidence changed. The comparison owner must authenticate the expert,
load persisted authoritative matches, source verdict and target event counts
under one transaction, and recheck them during an idempotent append with source
decision provenance. The future API must display source-version provenance as
«из версии N» without treating that label as identity. This module deliberately
does not pick matching rules, make a finding resolved, infer that an unmatched
finding was fixed, copy a severity/comment, or decide event payload semantics.
Those rules need the W59 comparison contract/migration owner after SECTION-SEAL.
The target-event-zero guard is conservative: any previous target comment also
blocks an offer until the owner defines a more precise conflict policy.

Changed paths are exactly the task allowlist:

- `src/auditmanager/comparison/decision_carryover.py`
- `tests/integration/comparison/test_decision_carryover.py`
- `docs/program/tasks/W59-INT-DECISION-CARRYOVER-PREP-01.md`
- `docs/program/W59-INT-DECISION-CARRYOVER-PREP-01.md`

Forbidden hotspots, including
`contracts/**`, migrations, existing comparison/decision files, root locks,
composition root, global styles, `CURRENT_STATE.md`, refs and tags, were not
edited. Remove these additive files to roll back before runtime wiring.
