# Task GATE-PKG-01 — a gate that refuses an unfit host in seconds, and a cleanup of finished lanes

task_id: GATE-PKG-01

## Outcome

`make gate` on an unfit host or checkout stops in seconds with `GATE NOT STARTED: <reason>`,
instead of voiding 15–40 minutes later. The reasons are a missing toolchain or corpus link, a
dirty tree, too little disk, too little memory, or another gate running. It waits, with a
heartbeat, for memory headroom and for this repository's single gate slot. It runs the
container-free reds before any container: whitespace, frontend lint/typecheck/tests and
`tests/contract`. In the battery it runs the changed contexts' integration suites first. The
set of tests and the literal `GATE OK` sentinel are unchanged. `scripts/worktree_cleanup.py`
reports, and on `--apply` removes, merged idle lane worktrees, this repository's orphan compose
volumes and recognised mutation copies. It never removes work in progress.

## Depends on

- `W55A-INT-GATE-01` — completed; the last complete gate whose voids and late reds this task
  counts.

## Frozen inputs

- domain contract: unchanged (no contract path touched)
- API contract: unchanged
- analysis/comparison/event contract: unchanged
- migration head: unchanged
- base commit: `origin/dev` `9da3ea06` (0.5.1)
- owner instruction: direct, 2026-10-14, to the session `pdf-analysis-4a`: build the gate
  package (preflight, cheap steps first, a slot that waits for resources) as a separate task
  before W56a, while W55b is integrated. It also asks for a free-memory check before the gate
  and a cleanup script for abandoned worktrees. Recorded with the poll answers by the
  integrator as `R-124`..`R-127` (`OWNER_RULINGS` §3.34, `integration/w55b` `9d1b5d1a`).

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the base gate brings up containers and runs the whole battery before lint, typecheck and the node_modules check

### P-01 — base gate composition
- captured_at: 2026-10-14
- command: `git show 9da3ea06:Makefile | grep -n -A9 '^gate: foundation'`
- captured_output:
  ```text
  1043:gate: foundation
  1044-	@$(GUARDS)
  1045-	freeze_paths
  1046-	require_runtime_env
  1047-	load_env
  1048-	require_env_coherence
  1049-	run_battery
  1050-	run_frontend
  1051-	check_whitespace
  1052-	printf '%s\n' "GATE OK: battery, foundation, frontend lint/typecheck/tests and whitespace all pass"
  ```
- interpretation: `foundation` is a prerequisite, so the containers and the cross-provider suite
  run first. `run_battery` comes before `run_frontend`, which holds the `web/node_modules`
  check, lint and typecheck. This proves the order only; the failure counts are in the report.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths

- `Makefile` (the `gate` target, three new prerequisite targets, `run_battery`,
  `run_contract`, `gate_memory_report`, `.PHONY`)
- `scripts/gate_host.py` (new)
- `scripts/worktree_cleanup.py` (new)
- `tests/contract/test_gate_host.py` (new)
- `tests/contract/test_worktree_cleanup.py` (new)
- `tests/contract/test_light_acceptance_command.py` (the gate-composition pin only)
- `tests/contract/test_alpha_acceptance_command.py` (the `gate:` line pin only)
- `docs/program/tasks/GATE-PKG-01.md`, `docs/program/GATE-PKG-01.md`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, root dependency/lock files
- the composition root, global styles
- `AGENTS.md`, `docs/program/MAIN_AUTODEPLOY_POLICY.md`, `OWNER_RULINGS_*.md` (integrator-owned)
- every `w55b-*` worktree, branch, port and ref

## Non-goals

- Changing which tests the gate runs, or the `GATE OK` sentinel.
- Implementing the resumed gate after an infrastructure void (`R-125`). That policy is recorded
  by the integrator; this task only adds the memory samples a void classification can cite.
- Pruning docker build cache, images or anonymous volumes: they are shared with other
  projects on this host.
- Running `worktree_cleanup.py --apply`: removal is the integrator's act.

## Deliverables

- code, tests, the two pin updates, and the report `docs/program/GATE-PKG-01.md`

## Required tests
- command: `.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py`
- expected: exit 0 on the committed tree
- command: `npm --prefix web test -- --run tests/guards/query-key-shape.guard.test.ts`
- expected: exit 0 (the guard reads `run_frontend` in the Makefile)
- command: `make gate` (R-70 case 3: this task touches the Makefile), after the integrator frees the
  host slot and `origin/dev` with W55b is merged in
- expected: literal `GATE OK`
- every new guard shown failing under a quoted mutation (report §3)

## Integration contract

`make gate` keeps its name, its sentinel and its test set. New refusals print `GATE NOT
STARTED:` and exit non-zero before any container starts. Thresholds come from the environment,
and the defaults are printed in each run: `GATE_MIN_AVAILABLE_MIB` 3072,
`GATE_MIN_FREE_DISK_MIB` 6144, `GATE_MAX_LOAD` off, `GATE_WAIT_MAX_S` 14400,
`GATE_HEARTBEAT_S` 300. `GATE_BASE` overrides the merge base with `origin/main` for the
battery order. The slot is the lock `<git common dir>/gate-slot.flock`. It is held by a
detached holder for exactly as long as the calling `make` lives, and that holder writes
`MemAvailable` samples to `<git common dir>/gate-runs/`. `worktree_cleanup.py` changes
nothing without `--apply`.

## Failure/idempotency/security cases
- Two gates from two worktrees: the second waits on the lock. A gate queued on the slot is not
  counted as a running foreign gate, so two waiting gates cannot deadlock.
- An old-style gate (a tree without this task) is seen by its argv and waited for.
- `make` killed by SIGKILL or Ctrl-C: the holder notices within a second and frees the slot.
- Cleanup: dirty, unmerged, recently active, locked, protected (`plan/*`), in use by a process,
  providing a symlinked `.venv`/`node_modules`/corpus, or under a compose project with
  containers → kept. An unreachable docker is not taken as "no containers". The instance
  `auditmanager-promotion*` is never removed. `rmtree` does not follow symlinks.

## Rollback / feature flag

Revert the task's commits. No data, contract or migration changes; the lock and samples live
under the git common directory and can be deleted at any time.

## Handoff
- changed files: see Allowed paths
- commands/results: report §2
- known limits: report §4
- integration notes: report §5
