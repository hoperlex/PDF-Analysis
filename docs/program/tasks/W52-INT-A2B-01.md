# Task W52-INT-A2B-01 — accept Stage A and grant Stage B

task_id: W52-INT-A2B-01

## Outcome

The accepted Stage-A SHA is read back on `origin/dev`, live programme records name that boundary, and `W52-SEAL-01` has a current-tree grant that passes the pin sweep before Stage B starts.

## Depends on

- `W52-GATE-01`, complete at `6d2ae471132e78268d3af8ca872560491ec57233` on `origin/dev`.

## Frozen inputs

- Base: clean `integration/w51` and read-back `origin/dev` at `6d2ae471132e78268d3af8ca872560491ec57233`.
- W52 Stage-A freeze: domain revision 9 / 29 identities, API 27 paths / 34 operations / 77 schemas, 23 error codes, migration head `0015_accounts_roles_registration`.
- `dispatch/W52-PLAN.md` §3–§5, R-70–R-74 and D-137–D-140. Development publication only; no release verdict.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: Stage A is the published development base for the next grant.

### P-01 — accepted Stage-A SHA

- captured_at: 2026-10-08
- command: `git ls-remote origin refs/heads/dev refs/heads/main`
- captured_output:
  ```text
  6d2ae471132e78268d3af8ca872560491ec57233 refs/heads/dev
  1e9bb1308b7b97cd75eef28e206b23c569871b68 refs/heads/main
  ```
- interpretation: the checked fixture-only candidate is published to development, not deployed.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W52-INT-A2B-01.md`, `docs/program/tasks/W52-SEAL-01.md`
- `docs/program/W52-INT-A2B-01.md`
- `docs/program/CURRENT_STATE.md` — active W52 block only
- `docs/program/dispatch/W52-PLAN.md` — status and integration-order sentences only
- `docs/program/dispatch/PORT_REGISTRY.md` — exact W52 rows only
- clean `integration/w51` ref, `origin/dev` fast-forward and local Stage-B branch/worktree setup

## Forbidden hotspots

Every other tracked path, especially contracts, migrations, product code/tests, root dependencies/locks, composition roots, global styles, deployment, `origin/main` and tags. Do not rewrite historical reports.

## Non-goals

No SEAL implementation, new contract, migration application, QA, full gate, live/manual acceptance or release.

## Deliverables

Current-tree `W52-SEAL-01` task with `pin_sweep --check` green, exact Stage-A integration evidence, updated live status and port row, clean docs-only candidate on `origin/dev` with remote readback.

## Required tests

- `python3 tools/plan/pin_sweep.py reseal-surface migration table --check docs/program/tasks/W52-SEAL-01.md`
- Focused governance/prose/surface tests, `git diff --check`, grant-path diff and clean tree.
- No complete `make gate`: D-140 owns it under the owner-confirmed W52 development exception.

## Integration contract

Stage B begins only from the docs-grant SHA read back from `origin/dev`; `W52-SEAL-01` alone owns its contract/migration/composition slot. The integrator re-sweeps at hand-back and grants Stage C/C2 only after the preceding merge.

## Failure/idempotency/security cases

A missing pin grant stops dispatch; a changed remote dev ref stops publication. `gate-w52s` uses only its reserved ports and disposable credentials. `origin/main` stays unchanged.

## Rollback / feature flag

Revert the docs-only grant commit if its boundary is wrong. No runtime behavior or flag changes.

## Handoff

Report changed files, check results, contract changes (none), limits, next integrator steps and forbidden-hotspot proof.
