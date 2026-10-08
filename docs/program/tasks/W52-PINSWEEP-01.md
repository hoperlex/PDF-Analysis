# Task W52-PINSWEEP-01 — code preparation for pin-impact inventory

task_id: W52-PINSWEEP-01

## Outcome

`tools/plan/pin_sweep.py` reports the files a declared change event can make stale and
checks that a task grants those paths. Embedded fixtures prove that the inventory finds
historical pin-caused changes and known holes without consulting Git history at test time.

## Depends on

- `W51-E2E-01` — implementation merged at `4400e81c66170a32afea15b333ab947bd1bc4770` and published on `origin/dev` through `d734ad067fb4e6b5ad82d2e7bb1f3e301fb7b7a1`.

## Frozen inputs

- Exact code base `d734ad067fb4e6b5ad82d2e7bb1f3e301fb7b7a1`; start from the docs-only dispatch SHA containing this task, named by the integrator.
- W51 frozen domain `1.0.0-draft.1` revision 9 / 29 identities; API 27 paths / 34 operations / 77 schemas; error catalog 23; migration head `0015_accounts_roles_registration`. This task changes none of them.
- Proposed `W52-PLAN.md` §3.6 and §4 at planning commit `2b45a11ec558df1452a4822149e54d2fe0ddb57e`; `docs/program/CONTRACT_PIN_REGISTRY.md` version 1 and its consuming test. The planning branch is an input, not a frozen W52 release claim.
- Owner direction 2026-10-08: prioritize implementation; QA, temporary stand and full gate are deferred as `D-137`/`D-138`. This is independent code preparation. `W52-RULE-01` and `W52-FREEZE-01` remain due before any W52 contract, migration or release lane uses this tool.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `tools/plan/pin_sweep.py`
- enumerator_owner: `W52-PINSWEEP-01`
- totality_query: `python -m pytest -q tests/contract/tools/test_pin_sweep.py`

The task owns the tool's six-event vocabulary and its mapping catalogue. It does not
change the application's screen, operation, error or migration enumerators.

## Captured premise evidence

- premise: the current development tree has a machine-readable registry and no pin-sweep tool.

### P-01 — base and pin registry

- captured_at: 2026-10-08
- command: `git rev-parse HEAD && rg -n '^```json$|"registry_version"' docs/program/CONTRACT_PIN_REGISTRY.md`
- captured_output:
  ```text
  d734ad067fb4e6b5ad82d2e7bb1f3e301fb7b7a1
  13:```json
  15:  "registry_version": 1,
  ```
- interpretation: this tree has a versioned registry block and is the exact task base; it does not prove the registry is complete.

### P-02 — proposed lane grant

- captured_at: 2026-10-08
- command: `git show 2b45a11:docs/program/dispatch/W52-PLAN.md | sed -n '310p;318p'`
- captured_output:
  ```text
  **`W52-PINSWEEP-01`** (A4). `tools/plan/pin_sweep.py <event>…` with events `reseal-surface`,
  Fixtures are non-`.py` data, and no surface-count phrase is written in `tools/plan/**`
  ```
- interpretation: the planning branch proposes this code-only lane; its W52 freeze and owner confirmations remain unfulfilled on the development line.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tools/plan/**`
- `tests/contract/tools/test_pin_sweep.py`
- `tests/contract/tools/fixtures/pin_sweep/**` — non-`.py` data only
- `docs/program/W52-PINSWEEP-01.md`

## Forbidden hotspots

Everything else, especially `contracts/**`, migrations, root dependency/lock files,
`Makefile`, backend and web application code, composition root, global styles,
`docs/program/CONTRACT_PIN_REGISTRY.md`, `docs/program/dispatch/W52-PLAN.md`, integration
refs, tags and `origin/**`.

## Non-goals

- No W52 freeze, owner-ruling substitution, expected-facts rewrite, gate acceleration,
  temporary stand, QA, full gate, release tag or `origin/main` publication.
- No automatic task grant mutation: `--check` reports omissions and exits nonzero.
- No Git-history read during fixture tests; fixture data records its source commits.

## Deliverables

- CLI events `reseal-surface`, `error-code`, `migration`, `table`, `route`, `contract-version`.
  It merges registry paths, the planned facts-file path and explicitly declared pattern
  catalogue; prints stable, repository-relative paths with reasons, and fails for unknown
  events or missing registry inputs.
- `--check <task file>` parses `Allowed paths`, accepts an exact file or containing `/**`
  grant and reports every missing path without editing the task. Directories whose content
  must be re-swept are reported even if they are empty at the current SHA.
- Embedded historical fixture with pin-caused subsets of W49 reseal/migration commits,
  written exclusion reasons, and known identity-plan judging holes. A negative fixture
  proves each missing grant is detected.

## Required tests

- Basic focused `python -m pytest -q tests/contract/tools/test_pin_sweep.py` and `git diff --check`.
- No stand, live acceptance or full `make gate` under the owner direction. No gate result is claimed.

## Integration contract

Hand back a clean `agent/w52-pinsweep-01` at an exact SHA with only allowed paths. The
integrator reviews basic checks and may publish this preparation to `origin/dev` without
claiming W52 freeze or closure. Its outputs are advisory until the later `W52-FREEZE-01`
re-sweeps the plan and grants. No executor push, tag, checkpoint or deployment.

## Failure/idempotency/security cases

- Unknown event, malformed registry, duplicate or non-repository path, absent task file and
  a missing grant fail closed. Output order and exit code are deterministic.
- The CLI reads text files only and never executes task-file content or rewrites a grant.

## Rollback / feature flag

Revert the code-preparation commit. No runtime behavior or stored state changes; no feature
flag is applicable.

## Handoff

- changed files, commands/results, contracts, risks, integration notes, forbidden-hotspot proof.
