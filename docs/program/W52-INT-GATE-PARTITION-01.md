# W52-INT-GATE-PARTITION-01 — foundation selected once by gate

Code commit `066815f` builds on clean `origin/dev` base `2c2e7d8`. The
`run_battery` command in `Makefile` now ignores exactly
`tests/integration/foundation`; `gate: foundation` and the `test-foundation`
target remain unchanged. The gate's distinct foundation step still runs its
cross-provider checks before the battery.

## Checks

- Before the edit, a battery `--collect-only` attempt returned exit 2 because
  the foundation suite deliberately refuses collection-only runs. It listed
  **3,216** non-foundation IDs and no foundation IDs before that refusal.
  This attempt is not a passing test run.
- After the exact ignore, battery collection exited 0 with **3,216** IDs; the
  ordered ID list equals the pre-edit non-foundation list byte for byte, has no
  duplicate and contains no foundation ID. It does not by itself prove outcome
  parity; that JUnit comparison remains with `W52-GATE-01`/D-140.
- On clean code commit `066815f`, the alpha-acceptance command, light-acceptance
  command, programme governance and live-prose contract tests: **91 passed**.
  The same command on the earlier dirty tree had 90 passes and one expected
  refusal by the acceptance script's clean-checkout precondition.
- Frontend lint and `git diff --check`: passed.
- Full `make gate`, JUnit outcome parity, timing, QA and live/manual acceptance:
  not run. No `GATE OK` is claimed.

The earlier `W52-INT-VALIDATE-01` gate measured 35 foundation passes and
3,245 Python passes on the old selection. This patch removes only the duplicate
foundation selection; it does not assert a new duration or green whole gate.

## Handoff

Changed tracked files: `Makefile` (`run_battery` selection and adjacent comment),
`docs/program/tasks/W52-INT-GATE-PARTITION-01.md`, this report,
`docs/program/CURRENT_STATE.md`, and `docs/program/DEBT_REGISTER.md`. No
contract, migration, root lock/dependency, composition root, global style,
test fixture or runtime application path changed. D-139/D-140 stay open.
Integrator may publish the docs follow-up and code commit together as a
fast-forward of `origin/dev` after exact remote-ref review. `origin/main` has
no publication authority in this task. Revert the integration commits to
restore the previous duplicate selection.
