# Task W52-DEBT-GUARDS-128A — close four D-128 guard blind spots

task_id: W52-DEBT-GUARDS-128A

## Outcome

The four existing contract guards detect W48-JUDGE-Z findings F-3 through F-6 with
focused regression probes. This is a code preparation, not W52 freeze or debt closure.

## Depends on

- `W52-INT-133-01` — docs integration published at `ae6019fbce4cb93b45ce503baf782cc7266fdd8f`.

## Frozen inputs

- Exact base `ae6019fbce4cb93b45ce503baf782cc7266fdd8f`; domain revision 9 / 29
  identities, API 27 paths / 34 operations / 77 schemas, error catalog 23, migration
  head `0015_accounts_roles_registration`.
- D-128 and `reviews/W48-JUDGE-Z.md` F-3…F-6; proposed W52 plan at
  `2b45a11ec558df1452a4822149e54d2fe0ddb57e` grants these four test files.
- Owner direction 2026-10-08: proceed without approval; only basic tests and lint;
  stand, QA and full gate remain D-139/D-140.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: all four guard sites are present on the exact base.

### P-01 — base and guard sites

- captured_at: 2026-10-08
- command: `git rev-parse HEAD && rg -n 'if target == "origin/main"|attested_deployed_sha|def workflow_shape_findings|def _targets' tests/contract/program/test_wave_governance.py tests/contract/test_alpha_acceptance_command.py tests/contract/test_deploy_auto_workflow.py tests/contract/architecture/test_alr05_boundaries.py | head -12`
- captured_output:
  ```text
  ae6019fbce4cb93b45ce503baf782cc7266fdd8f
  tests/contract/architecture/test_alr05_boundaries.py:51:def _targets(node: ast.AST, path: Path) -> tuple[str, ...]:
  tests/contract/test_deploy_auto_workflow.py:35:def workflow_shape_findings(text: str) -> set[str]:
  tests/contract/test_alpha_acceptance_command.py:294:        assert f"- attested_deployed_sha: {head}" in report
  tests/contract/program/test_wave_governance.py:100:        if target == "origin/main":
  ```
- interpretation: these are the exact existing guard entry points; the judge's mutations
  prove their present blind spots, not a live-deployment fault.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tests/contract/program/test_wave_governance.py`
- `tests/contract/test_alpha_acceptance_command.py`
- `tests/contract/test_deploy_auto_workflow.py`
- `tests/contract/architecture/test_alr05_boundaries.py`
- `docs/program/W52-DEBT-GUARDS-128A.md`

## Forbidden hotspots

Every other path, especially the workflow, acceptance script, contracts, migration head,
dependencies/locks, application code, composition root, global styles and D-128 F-1/F-2.

## Non-goals

No full W52-DEBT-GUARDS lane, D-128 closure, W52 freeze, QA, stand, full gate, tag,
or `origin/main` publication. No claim that a task-file citation alone authorises a push.

## Deliverables

- F-3: `origin_main_authority` is `none` unless target is `origin/main`; a main reference
  binds an exact 40-hex candidate SHA to a direct owner instruction.
- F-4: acceptance report tests reject positive served-revision proof claims even when
  the attestation lines remain.
- F-5: workflow guard rejects job-level permissions and additional SSH host-key lines.
- F-6: ALR-05 guard sees literal dynamic cross-context imports.
- Each finding gets a focused local regression probe that would fail under its old guard.

## Required tests

- `.venv/bin/python -m pytest -q tests/contract/program/test_wave_governance.py tests/contract/test_alpha_acceptance_command.py tests/contract/test_deploy_auto_workflow.py tests/contract/architecture/test_alr05_boundaries.py`
- `git diff --check`; frontend lint if available. No stand or full gate.

## Integration contract

Hand back a clean branch from the exact dispatch SHA with only allowed paths and the
focused checks. Integrator may publish this code preparation to `origin/dev` after exact
remote-ref and fast-forward verification. F-1/F-2/F-7/F-10/F-11 remain open.

## Failure/idempotency/security cases

An unauthorised main marker, a report claiming measured deployment without measuring,
write permissions in a nested job, a third known host and a literal dynamic deep import
must each produce a distinct guard failure. Existing valid files remain green.

## Rollback / feature flag

Revert this test-only commit. No runtime feature flag.

## Handoff

- changed files, commands/results, contracts, risks, integration notes, forbidden-hotspot proof.
