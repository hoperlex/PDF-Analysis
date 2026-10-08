# W52-PINSWEEP-01 — executor handoff

Task: `docs/program/tasks/W52-PINSWEEP-01.md`. Base: `88ea1cd284c473cdf6bf10e1c639496d21baafec`.
This is code preparation for the proposed W52 plan; no W52 freeze or release is asserted.

## Result

`tools/plan/pin_sweep.py` accepts the six declared change events and prints sorted,
repository-relative grant candidates with a reason for each. The list combines the versioned
pin registry, the planned hand-written facts-file fields, exact-set paths and bounded pattern
searches. A `/**` entry represents a family that needs a grant before future members exist.
`--check TASK.md` reports every path not covered by an exact grant or a containing `/**`
grant, exits 1 and does not edit the task. Invalid inputs exit 2.

Examples:

```sh
python3 tools/plan/pin_sweep.py reseal-surface error-code
python3 tools/plan/pin_sweep.py migration table --check docs/program/tasks/W52-SEAL-01.md
python3 tools/plan/pin_sweep.py route contract-version
```

The W49 fixture records the pre-seal registry and source excerpts from
`7d06e67bfb5026ba36f3e04f01ea6850b53b725c`. It partitions the changed files of
`e86bfbe`, `633a83a`, `48099d9`, `220638d` and `0dbb418` into a 28-file independent-pin
subset and 117 path-specific written exclusions. The tests check that
`reseal-surface error-code` and `migration table` include their subsets, and that the route
inventory names the five explicit identity-plan judging holes. Tests read only the embedded
JSON and a temporary tree, never Git history.

## Changed files

- `tools/plan/pin_sweep.py`
- `tests/contract/tools/test_pin_sweep.py`
- `tests/contract/tools/fixtures/pin_sweep/w49_before_seal.json`
- `docs/program/W52-PINSWEEP-01.md`

## Checks

- Focused `pytest`: 7 passed.
- `npm --prefix web run lint`: passed using the already installed dependencies of the
  adjacent integration worktree; the temporary `node_modules` symlink was removed.
- Python syntax compilation and `git diff --check`: passed.
- No temporary stand, live QA or full gate run, per the owner's 2026-10-08 direction;
  those checks remain in `D-137` and `D-138`.

## Contracts and integration

No application contract, migration, dependency or runtime path changed. Merge the clean executor
commit into the integration line and publish to `origin/dev` as preparation only. At the later
W52 freeze, create the Stage-B/C/C2 task files and run `--check` against each before dispatch.
Those task files do not yet exist on this base, so the held-out grant check remains due. The
facts-file schema is checked if the file exists; until `W52-FACTS-01`, the path and planned
fields remain advisory. Pattern results are conservative grant candidates and need human review
of the cause of each match.

Forbidden hotspots are untouched: the changed-file list is wholly inside the task's four
`allowed_paths` entries. Rollback is a revert of the executor commit; runtime behavior is
unchanged.
