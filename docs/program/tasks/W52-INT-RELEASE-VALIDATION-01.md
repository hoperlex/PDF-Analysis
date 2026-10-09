# Task W52-INT-RELEASE-VALIDATION-01 — validate the W51/W52 release candidate

task_id: W52-INT-RELEASE-VALIDATION-01

## Outcome

Produce an exact, clean W52 candidate with recorded W51/W52 QA and a complete `make gate`
ending in literal `GATE OK`, or record precise blockers without a release claim. Publish a
validated candidate to `origin/dev` only after a proved fast-forward. `origin/main` remains a
separate publication task after the owner names the exact SHA.

## Depends on

- `W52-INT-VALIDATION-ENTRY-01`, completed at `d0bcb258bdc1c0d10b3fb753622128421dc1c89d`.

## Frozen inputs and contracts

- Development base and remote readback: `d0bcb258bdc1c0d10b3fb753622128421dc1c89d`.
- Main readback: `21eba6eb44bfcea91348a021fa5ae84c9ab26fca`; histories diverge at
  `3fc0dcfa1fbe59c2e00007fdbd7159e43c2d3551`.
- `VERSION=0.3.0`; API 30 paths / 37 operations / 83 schemas; 23 error codes;
  domain revision 9 / 29 identities; migration head `0016_release_notes`;
  `contract_version=1.0.0-draft.1`.
- `docs/program/dispatch/W51-PLAN.md` §4–5, `W52-PLAN.md` §4–5,
  `MAIN_AUTODEPLOY_POLICY.md` and D-137–D-140 are controlling inputs.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: `tests/support/expected_facts.json`; this task changes no member.

## Captured premise evidence

- premise: development and main are separate, and W51/W52 validation is open.

### P-01 — remote refs and common ancestor

- captured_at: 2026-10-09
- command: `git ls-remote origin refs/heads/dev refs/heads/main; git merge-base origin/dev origin/main`
- captured_output:
  ```text
  d0bcb258bdc1c0d10b3fb753622128421dc1c89d refs/heads/dev
  21eba6eb44bfcea91348a021fa5ae84c9ab26fca refs/heads/main
  3fc0dcfa1fbe59c2e00007fdbd7159e43c2d3551
  ```
- interpretation: neither ref is a descendant of the other; validation and reconciliation
  are required before a release candidate exists.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- This task and `docs/program/W52-INT-RELEASE-VALIDATION-01.md` for evidence.
- `tests/integration/qa_w52/**`, `web/tests/unit/qa_w51/**`, `web/tests/unit/qa_w52/**`
  for QA only after a current-tree inventory.
- An explicit follow-up integration grant must name any of the eight main-only test
  paths before semantic reconciliation; this task grants read-only comparison.
- Ignored `.env`, `.venv/**`, `web/node_modules/**`, `.local/validation/w52-release/**`
  in the development worktree for isolated checks.

## Forbidden hotspots

`contracts/**`, migrations, root dependencies and lock files, composition root, global
styles, runtime code, generated clients, the owner's stand, `origin/main` and tags.
Any source or contract correction requires a separate exact-path task.

## Non-goals

No inferred independent judge or human manual verdict; no deployment, release tag, debt
closure without its named evidence, or main publication under this task.

## Deliverables and checks

- Exact remote-ref, contract and forbidden-hotspot inventory.
- QA inventory and executable focused tests for the W51/W52 cases in scope.
- Isolated, unique PostgreSQL/S3 gate environment and complete `make gate` log tied to
  one clean SHA, with the literal sentinel or exact failure recorded.
- `git diff --check`, changed-path audit, clean candidate status, and a six-part report.

## Integration contract

The current task can publish a fully checked candidate to `origin/dev` after QA and gate
evidence, provided the remote ref is still the frozen ancestor. Main-only changes are
reconciled under a later exact-path grant and the complete gate is rerun on the combined
SHA. A distinct `W52-INT-MAIN-01` task may update `origin/main` only after the owner gives
a separate direct instruction naming that exact gated SHA and the auto-deploy policy is met.

## Failure, rollback and feature flag

A red QA/gate check, moved ref, unowned edit or changed frozen contract stops
publication. Isolated services are removed after measurement. Documentation can be
corrected by a forward commit on dev. No runtime feature flag or data rollback applies.
