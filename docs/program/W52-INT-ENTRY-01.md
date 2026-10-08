# W52-INT-ENTRY-01 — development-entry reconciliation

**Date:** 2026-10-08. **Base:** clean `integration/w51` at
`4159d4e8d831b4aa7ea8eaefa5bc21bb77ed43d5` (the local
`origin/dev` tracking ref at the start of this task). **Planning input:** tracked files at
`plan/roadmap-to-beta` SHA `2b45a11ec558df1452a4822149e54d2fe0ddb57e`.
The planning worktree and its untracked W58 files were not edited.

## Result

The judged W52 plan, its roadmap and its judging summary are copied onto
the development line. The judging summary is byte-identical to the planning
source. The plan and roadmap carry dated adoption amendments; their original
design and owner-answer history remain visible.

The W52 plan no longer treats W51's deferred `GATE OK` as a completed or
required **code-entry** condition. W51 implementation closed at `4159d4e`;
W51 QA, built-stand/manual acceptance and full gate remain D-137/D-138.
W52 and later code-only candidates retain D-139/D-140. W52 Stage A/B/C code
work still requires `W52-RULE-01` and `W52-FREEZE-01` before dispatch; the
already merged FACTS/PINSWEEP and other preparations do not count as that
freeze. The later validation stage owns audit/attack, independent QA/judges,
live/manual acceptance, exact-candidate full gate and corrections. A release
or `origin/main` update requires a separate direct owner instruction.

## Checks

- `git diff --check`: passed.
- Focused governance and live-prose/surface guards:
  `.venv/bin/pytest -q tests/contract/program/test_wave_governance.py
  tests/contract/api_v1/test_doc_prose_facts.py
  tests/contract/api_v1/test_surface_counts_in_prose.py` → **93 passed**.
- The first focused run found `PREMISE_OUTPUT_REQUIRED` for the new task;
  after adding the captured-output block, the same command passed.
- `W52-PLAN-JUDGING.md` matches the planning source byte for byte.
- No complete `make gate`, QA, temporary stand or live/manual acceptance was
  run in this documentation integration. No `GATE OK` is claimed.

## Open work and integration instruction

`W52-RULE-01` still needs the owner confirmations named in W52 §4: the
hand-written facts file with live prose outside it, the serial-only W52 gate
speed change, and unchanged `contract_version` until beta freeze. Record the
rulings before `W52-FREEZE-01`. That freeze re-sweeps current pins, grants,
debt rows and the frozen contract set, and records the code-only validation
boundary. D-137–D-140 remain release-blocking until the separate validation
stage supplies exact-candidate evidence.

The local `git ls-remote origin refs/heads/dev refs/heads/main` failed with
`Could not resolve host: github.com`. Do not publish this commit until the
remote is reachable, its refs are re-read, and an exact fast-forward is
proved. No `origin/main` authority exists here.

## Scope and rollback

Changed paths: `docs/program/tasks/W52-INT-ENTRY-01.md`, this report,
`docs/program/dispatch/W52-PLAN.md`,
`docs/program/dispatch/ROADMAP-TO-BETA.md`,
`docs/program/reviews/W52-PLAN-JUDGING.md` and
`docs/program/CURRENT_STATE.md`. Contracts remain domain revision 9 / 29
identities, API 27/34/77, 23 errors and migration head
`0015_accounts_roles_registration`. No contract, migration, root lock/dependency,
composition root, global style, product code/test, planning-worktree, tag or
deployment path changed. Revert this docs-only commit if its entry boundary
is superseded; no feature flag or runtime rollback is needed.
