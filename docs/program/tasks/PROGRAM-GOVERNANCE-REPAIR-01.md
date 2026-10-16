# Task PROGRAM-GOVERNANCE-REPAIR-01 — reconcile historical task governance

task_id: PROGRAM-GOVERNANCE-REPAIR-01

## Outcome

The code-first tree's complete program governance test passes, with truthful
retrospective premise, history and publication declarations on ten existing
W54/W56A/W59 task documents. The original implementation scopes and frozen
contract inputs remain byte-identical within those sections.

## Depends on

- `CFB-INT-DEV-PUBLISH-12` — completed code-first development publication.
- `W58-INT-TARGET-BLOB-READBACK-PREP-01` — completed latest source commit at this base.

## Frozen inputs

- base commit: `e61fc4570e49d0411b72e5363a2bafd5eeb5da97`
- program governance test SHA-256: `cd34978d63c13e2e174b019ac666bf797caf78e36a86c8dca030a408558a193e`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- API/domain/error/stage registry SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`, `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`, `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`, `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- migration head: `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: at the exact base, a W54 task made a premise claim without the
  captured command and output required by the active governance rule.

### P-01 — exact base document

- captured_at: 2026-10-16
- command: `git show e61fc4570e49d0411b72e5363a2bafd5eeb5da97:docs/program/tasks/W54-CORPUS-OPERATE-01.md | rg -n 'premise|captured_at|command|captured_output'`
- captured_output:
  ```text
  30:## Captured premise evidence
  32:- premise: the source was inventoried, but its bytes were not verified; the
  102:- changed files, commands/results, contracts, limits and untouched hotspots:
  ```
- interpretation: the base task recorded a premise without an executable
  capture. This correction adds retrospective evidence and labels it as such;
  the old resource reading cannot authorize a new heavy W54 step.

## Historical evidence

- correction_mode: addendum
- source_record: ten task files at base `e61fc457` listed under Allowed paths
- addendum_path: docs/program/PROGRAM-GOVERNANCE-REPAIR-01.md

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W54-CORPUS-OPERATE-01.md`
- `docs/program/tasks/W54-CORPUS-PROMOTION-01.md`
- `docs/program/tasks/W56A-INT-GENERATOR-01.md`
- `docs/program/tasks/W56A-INT-MATCHER-CORE-01.md`
- `docs/program/tasks/W56A-INT-MERGE-CORE-01.md`
- `docs/program/tasks/W56A-INT-SEAL-01.md`
- `docs/program/tasks/W56A-MATCHER-CORE-PREP-01.md`
- `docs/program/tasks/W56A-MERGE-CORE-PREP-01.md`
- `docs/program/tasks/W59-INT-DECISION-CARRYOVER-PREP-01.md`
- `docs/program/tasks/W59-INT-PROFILE-READINESS-GAP-01.md`
- `docs/program/tasks/PROGRAM-GOVERNANCE-REPAIR-01.md`
- `docs/program/PROGRAM-GOVERNANCE-REPAIR-01.md`

## Forbidden hotspots

- `contracts/**`, migrations, source/runtime/tests, fixture data, provider lock;
- root dependency/lock files, composition root, global styles, `VERSION`;
- `docs/program/CURRENT_STATE.md`, other task/report files, corpus bytes,
  Docker/DB/S3, credentials, deployment and remote refs.

## Non-goals

- No new source task grant, W54 capacity clearance, W56a model/probe result,
  W59 executable profile, release candidate, main deployment or beta verdict.
- No rewriting original task outcomes, frozen hashes, dependencies, allowed
  paths, checks or implementation reports.

## Deliverables

- Ten metadata corrections, this formal task and one historical addendum report.

## Required tests

- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.venv/bin/python -m pytest tests/contract/program/test_wave_governance.py -q -p no:cacheprovider` — all 16 pass;
- direct `governed_task_findings()` — empty;
- `git diff --check`, exact changed-path containment and inspection of original
  scope/frozen-input sections. Full product gate remains separately owned.

## Integration contract

The integrator may fast-forward this docs-only commit into code-first work
after verifying the exact base and path containment. The historical task
metadata says what those tasks authorized when written; it confers no new
publication or resource permission. Retrospective captures include the date
of this correction and are tied to immutable source records or frozen Git
trees. The paired addendum lists the original findings and measured repair.

## Failure/idempotency/security cases

- Any changed frozen input or original task scope blocks this correction.
- Reapplying the same metadata must be a no-op; no runtime or external state
  is touched. A changed source record requires a new dated correction.

## Rollback / feature flag

Revert this docs-only commit if a correction proves false; governance would
return to its prior red result. No application feature flag or DB rollback.

## Handoff

- changed files: the 12 Allowed paths;
- checks/results and known limits: paired addendum report;
- contracts: none changed;
- integration note: no push, tag, deployment or W54 launch authority.
