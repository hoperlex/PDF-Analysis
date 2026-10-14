# GATE-PKG-01 — gate preflight, one host slot, cheap steps first; lane cleanup

Task: `docs/program/tasks/GATE-PKG-01.md`. Branch `agent/gate-pkg-01` from `origin/dev`
`9da3ea06`. Executor: session `pdf-analysis-4a`, on the owner's direct instruction of 2026-10-14
(integrator records `R-124`..`R-127`, `OWNER_RULINGS` §3.34 on `integration/w55b` `9d1b5d1a`).

## 1. What changed

**Why.** The W48–W55a records contain about 22 complete gates that failed or were voided. About
two thirds failed on the host, not on the code:

- the corpus link or `web/node_modules` was missing: W48 AUDIT, FIX and INT-MAIN-02, W50-FIX, W53 G5;
- the host ran out of capacity: `StorageUnavailableError`, OOM `137`, disk pressure, a MinIO
  restart (W49 `c53fabe`, W50 SHELL-FRAME and REGISTRY, W52 MAIN-SEAL ×2).

The rest were real reds found only after the full battery: W52 MAIN-01's 170 setup errors, W53's
13 failures, W55a's 17 database failures. Each such run cost 15–40 minutes before it said
anything, because the base gate brought up containers and ran the whole battery before lint,
typecheck or the `node_modules` check (task P-01).

**`make gate` is now** `gate: gate-preflight gate-slot gate-static foundation`, then the battery.
`.NOTPARALLEL` runs the prerequisites left to right.

| Step | What it does | Containers |
|---|---|---|
| `gate-preflight` | `scripts/gate_host.py preflight`. Refuses in seconds when `.venv/bin/python`, `web/node_modules`, `.local/norms/corpus` or `.env` is missing, when the tree is dirty, or when free disk on the worktree or the Docker data filesystem is under `GATE_MIN_FREE_DISK_MIB` (6144). It prints each disk measurement with its time, as AGENTS.md §8 asks. | none |
| `gate-slot` | `gate_host.py slot --owner-pid $$PPID`. Takes `<git common dir>/gate-slot.flock`, one slot shared by every worktree. While holding it, it waits until `MemAvailable` ≥ `GATE_MIN_AVAILABLE_MIB` (3072), the optional `GATE_MAX_LOAD` is met and no other `make gate` runs on the host, with a heartbeat every `GATE_HEARTBEAT_S` (300 s) and at most `GATE_WAIT_MAX_S` (4 h). A detached holder then keeps the slot for exactly as long as this `make` lives and samples `MemAvailable` into `<git common dir>/gate-runs/`. | none |
| `gate-static` | `check_whitespace`, `run_frontend` (lint → typecheck → Vitest, unchanged), then `load_env`, `require_env_coherence` and `run_contract`: `tests/contract` with the battery's three CP-00 ignores verbatim. | none |
| `foundation` | unchanged | yes |
| `gate` | `run_battery`. It first runs the integration suites of the contexts changed since the merge base with `origin/main` (or `GATE_BASE`); a red there stops the gate. It then runs the rest with those suites and `tests/contract` ignored. `gate_memory_report` prints the lowest sampled `MemAvailable`, then the unchanged `GATE OK` sentinel. | yes |

The gate still runs the same set of tests, with no duplicates and none dropped. Only the order
changed. `docs/program/dispatch/OPERATING_CONSTRAINTS.md` §7 names the Makefile as the authority
on composition, and its canonical command still describes the same set. A refusal prints
`GATE NOT STARTED: <reason>` and is never a test result.

**Other gates on the host** are found by their argv (`make … gate`), never by a pattern over a
command line. A `make gate` that is queued on this repository's slot (it has a
`gate_host.py slot` descendant) does not count, because counting it would deadlock two waiting
gates. Gates from trees without this task do count, and the slot waits for them.

**`scripts/worktree_cleanup.py`** reports by default. With `--apply` it removes:

- **Lane worktrees** that meet every condition: under `.local/worktrees/`, clean, contained in
  each `--merged-into` ref (default `origin/dev`), idle for `--idle-hours` (24), not locked, not
  `plan/*` or another `--keep` glob, no process with its cwd inside, no other worktree's `.venv`,
  `web/node_modules` or corpus symlinked into it, and no container in its compose project.
  Docker is always asked; an unreachable docker keeps the worktree. Removal is
  `git worktree remove`, never `--force`, and branches stay.
- **Volumes** (`--docker`): the volumes of removed worktrees, and orphan volumes that carry this
  repository's compose signature (`<project>-postgres-data` or `<project>-s3-data` with that
  project label and a `gate-`/`auditmanager-` prefix), have no container of any state and are
  named by no remaining `.env`. `auditmanager-promotion*` is protected.
- **Mutation copies** (`--mutation-copies`): `/root/*-mut*` directories with no `.git`, with
  `src/auditmanager` and this project's `pyproject.toml`. `rmtree` does not follow their symlinks
  into the tree. Older copies without `pyproject.toml` are listed as "inspect by hand".

Build cache, images and anonymous volumes are shared with other projects on this host and are
only counted.

## 2. Checks and results

All runs are in `.local/worktrees/gate-pkg` (`.venv` and `web/node_modules` linked from `w54-int`;
the uv.lock and package-lock are identical at `9da3ea06` and `64080abf`).

| Command | Tree | Result |
|---|---|---|
| `git diff --check` | working tree before the first commit | exit 0 |
| `.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py -p no:cacheprovider` | `3a441e99`, clean | exit 0, **658 passed**, 50 subtests, 58.7 s |
| `npm --prefix web test -- --run tests/guards/query-key-shape.guard.test.ts` | `3a441e99`, clean | exit 0, 14 passed (the guard reads `run_frontend` in the Makefile) |
| `make -n gate` | `3a441e99` | prints preflight → slot → static → foundation → battery; runs nothing |
| `make gate-preflight` (no `.env` yet) | `3a441e99` | exit 2 after **3.6 s**: `GATE NOT STARTED: .env is missing; …` (both disk lines printed first) |
| `make gate-preflight` (lane `.env`: `gate-pkg01`, ports 57600 / 61200 / 61201) | `3a441e99` | `GATE PREFLIGHT OK: 3a441e99…` |
| `GATE_WAIT_MAX_S=20 make gate-slot` | `3a441e99` | `GATE SLOT HELD: … holder pid 1271547 while make pid 1271519 lives; MemAvailable 6813 MiB`. Two seconds after `make` ended, `flock -n` on the lock succeeded, the holder had exited and its record was gone; one sample was written. |
| `scripts/worktree_cleanup.py --docker --mutation-copies` (dry run) | host at 2026-10-14 13:40 +05 | marks 15 merged lane worktrees (`w54-*`, `w55a-*`), 10 orphan volumes (`gate-w51final`, `gate-w51hotfix`, `gate-w52r`, `gate-w52s`, `gate-w53seal`) and 3 mutation copies. Keeps every `w55b-*`, `plan-*`, `w59-*`, `version-history-ui` (active), `w54-int` (it provides `.venv` and `node_modules` to `w55b-int` and to this lane), `auditmanager-w19a` (running), `auditmanager-w55b-fix` and `gate-b0` (named by a live `.env`). Nothing was removed. |
| complete `make gate` | **owed**: the integrator frees the host slot after W55b's gate and this branch merges that `origin/dev` first | — |

The first full contract run on an uncommitted tree failed exactly one test,
`test_release_command_cannot_turn_skips_recorded_mode_or_outage_into_pass`:
`manual-alpha-check.sh` refuses a checkout with uncommitted changes. A dirty tree could
therefore never pass `make gate`, which is why the preflight now refuses it in seconds.

## 3. Mutation proofs

Every proof ran against a mirror at `/root/gatepkg-mut`, which was removed afterwards. The mirror
copied the Makefile, the three scripts and the two new test modules, and linked `src`,
`tests/support` and `tests/integration` read-only. No tracked file was edited. The runner,
kept outside the tree, rebuilt the mirror for each mutation, asserted that the anchor occurs
exactly once, and ran the named tests. Baseline: `test_gate_host.py` 27 passed,
`test_worktree_cleanup.py` 12 passed.

| Mutation | Red tests |
|---|---|
| M1 preflight ignores a dirty tree (`elif False:`) | `test_a_dirty_tree_is_refused…` (1 failed) |
| M2 a gate queued on the slot counts as foreign | `test_foreign_gates_skip_this_gate_and_gates_queued…` (1) |
| M3 no memory floor (`free < 0`) | `test_headroom_names_each_missing_condition`, `test_the_slot_waits_for_memory…` (2) |
| M4 no holder keeps the slot (`os.close(fd); os._exit(0)`) | `test_the_slot_is_held_while_make_lives…` (1) |
| M5 corpus link not checked | `test_a_fresh_worktree_is_refused…` (1) |
| M6 `gate-static` drops `run_contract` | `test_the_gate_runs_cheap_refusals_first…` (1) |
| M7 the battery no longer ignores `tests/contract` | `test_tests_contract_moves_out_of_the_battery…` (1) |
| M8 cleanup forgets a borrowed `.venv` | `test_a_worktree_another_lane_borrows_its_venv_from_is_kept` (1) |
| M9 cleanup skips the container check | `test_a_running_stack_is_kept…` (1) |
| M10 cleanup ignores uncommitted work | `test_uncommitted_work_is_kept` (1) |
| M11 the promotion database unprotected | `test_orphan_volumes_need_the_signature…` (1) |
| M12 cleanup ignores unmerged commits | `test_unmerged_commits_are_kept` (1) |

## 4. Known limits

- **Other load.** Only `make gate` processes are recognised as gates. A battery run by hand, or
  another project's test run, is covered only by the memory floor.
- **Memory during the run.** The holder samples memory but cannot reserve it. Its samples are the
  evidence a void classification under `R-125` can cite; the resumed gate itself is not
  implemented here.
- **Thresholds.** They come from the environment. Lowering one removes the wait; it cannot make
  a red test green, and the effective values are printed.
- **Battery order.** It needs `origin/main` locally, or `GATE_BASE`; without either the battery
  runs in its usual order and says so.
- **Vitest.** It still runs as one process. The two-part workaround for a loaded host is
  unchanged.
- **Leftovers the cleanup does not remove.** `<git common dir>/gate-runs/*.mem.tsv` accumulate
  (tens of bytes each) and are not pruned. Of the 20 `/root/*-mut*` copies, 17 are W10–W12
  copies without `pyproject.toml` and are listed for a person to judge. `/root/w*-logs` are wave
  evidence and are out of scope.

## 5. Instructions for the integrator

1. After W55b's gate, merge the published `origin/dev` into `agent/gate-pkg-01`. The lane then
   runs its one complete `make gate` (R-70 case 3) and appends the result to §2.
2. Merge the branch. From then on, every gate on every worktree of this repository shares the
   slot, and a lane needs a clean committed tree plus `.env`, `.venv`, `web/node_modules` and the
   corpus link before the gate will start.
3. Ports `57600` and `61200/61201` (instance `gate-pkg01`) are in use by this lane. Please add the
   row to `docs/program/dispatch/PORT_REGISTRY.md`; it is outside this task's paths.
4. Cleanup, when you choose:
   `python3 scripts/worktree_cleanup.py --docker --mutation-copies --sizes`, read the report, then
   the same command with `--apply`.
5. AGENTS.md §8's "measure free space and record it beside the log" is now printed by the
   preflight. Its wording can say so in W56a's rule task, next to `R-126`.

## 6. Forbidden hotspots

`git diff --name-only 9da3ea06..HEAD` lists only the paths in the task's Allowed paths: the
Makefile, the two new scripts, the two new test modules, the two pinned contract tests, and the
task and report files. Nothing under `contracts/`, `db/migrations/`, the lock files, the
composition root, AGENTS.md or the policy files was touched, and no `w55b-*` worktree, port or ref.
