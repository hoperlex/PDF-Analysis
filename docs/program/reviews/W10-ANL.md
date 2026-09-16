# `W10-ANL` — mutation sweep of `src/auditmanager/analysis/**`

- Session `W10-ANL`, worktree `/root/w10anl`, branch `agent/w10-anl`.
- **HEAD on arrival: `e08da85`** (`docs: the wave 10 dispatch — five parallel sweeps of the
  rule surface`). The brief names base `fb30e96`; `e08da85` is one commit later on the same
  line, so the base premise holds.
- Worktree found already bootstrapped by the killed first attempt: `.venv`, `.env` (instance
  `gate-w10a`, ports 55590/59190/59191, db `audit_w10a`, bucket `auditmanager-gate-w10a`)
  and `web/node_modules` all present. Nothing committed by that attempt.
- Surface confirmed: 32 files, 5005 lines under `src/auditmanager/analysis/`.

## Sweep table

(appended per batch; see below)

## Baseline

`make gate` at `7fcd4d3` (= `e08da85` + this file): **816 passed, 5 skipped, 116 subtests
passed in 192.20s**, `GATE OK`. The brief's expected figure is exact.

### Harness

Mutations are applied to `/root/w10anl-mut/src`, a `cp -a` of the worktree `src/`, with
`contracts/`, `docs/` and `fixtures/` symlinked beside it. Runs go through
`pytest -p mutprobe -o pythonpath=/root/w10anl-mut/src`; `mutprobe` is a plugin whose
`pytest_configure` prints `auditmanager.__file__` and **aborts the run** unless it resolves
under `/root/w10anl-mut/src/`. Every result below is from a run that printed

    [PROBE] auditmanager.__file__ = /root/w10anl-mut/src/auditmanager/__init__.py

Every mutation is applied by a script that refuses a pattern matching other than exactly
once, refuses a no-op replacement, and **prints the mutated line back out of the file on
disk** before the suite runs — the `frozenset() or frozenset({...})` failure mode is
mechanically excluded.

Suite sets:

- `FAST` = `tests/integration/analysis_engine tests/integration/analysis_text` — 143 tests,
  5.8s green at baseline.
- `WIDE` = `FAST` + `tests/replay tests/integration/findings tests/integration/p02_journey
  tests/integration/exports tests/integration/composition tests/contract/analysis_packages`.

Anything green under `FAST` is re-run under `WIDE` before it is called unguarded.

**A measurement error worth recording:** running `tests/integration` wholesale *without*
`make foundation` first produces 11 failures in `foundation/test_idempotency.py`,
`foundation/test_restart_persistence.py` and `p02_journey/test_truncated_end_to_end.py`.
These are migration-state dependent, not a defect and not another session's interference —
`make gate` sequences `make foundation` ahead of the battery and they pass. `WIDE` therefore
excludes `tests/integration/foundation`.
