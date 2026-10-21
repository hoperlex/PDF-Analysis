# Task W55B-INT-MAIN-PREP-03 — verify exact D-142-repaired W55b candidate

task_id: W55B-INT-MAIN-PREP-03

## Outcome

The clean isolated W55b candidate `37393a979a430e490843d7f410e9eca9491a4ea1`
receives a complete canonical `make gate` result. A report records the exact
SHA, full log digest, verdict and remaining conditions for a separate
`origin/main` publication decision. This task updates no remote ref.

## Depends on

- `W55B-INT-CLOSE` — completed at `6d63802ab465a0317839c9b57abd5e90f3d91769`;
- `W55B-INT-GATE-TIMEOUT-01` — completed at `d3acd511c608dbff94d448b95ebb826cf5437c75`;
- `W55B-INT-D142-GATE-REPAIR-01` — completed at `37393a979a430e490843d7f410e9eca9491a4ea1`.

## Frozen inputs

- exact candidate: `37393a979a430e490843d7f410e9eca9491a4ea1`;
- remote `main` at preparation read: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- remote `dev` at preparation read: `c3527fd969c4512441971d9a1f6e2c68a52b9a13`;
- W55 plan SHA-256 `9f4e0f204284347bc3ead59423a5cff830bbc9298ceaa2d47e1412f640b92b64`;
- main auto-deploy policy SHA-256 `1be97f93e6a8573ff88bc58a75a4166403d0db8badf401dd8e4fe39972fbf818`;
- candidate `VERSION=0.6.0`, migration head `0021_portal_bundles`,
  API 47 paths / 54 operations / 123 schemas, error catalogue 24 codes;
- the fourth full gate on predecessor `d3acd511` failed at D-142 after
  4,168 passes; the repair changes one integration test and task/report only;
- owner confirmed alpha had only generated test data on 2026-10-16; the
  R-110 waiver condition must be rechecked immediately before deployment.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: D-142 publication identity is Attempt-scoped, and the new test
  selector names the original crashed Attempt.

### P-01 — exact repair and fast-forward ancestry

- captured_at: 2026-10-16
- command: `git diff --name-only d3acd511..37393a97 && git merge-base --is-ancestor 23fd729d 37393a97`
- captured_output:
  ```text
  docs/program/W55B-INT-D142-GATE-REPAIR-01.md
  docs/program/tasks/W55B-INT-D142-GATE-REPAIR-01.md
  tests/integration/runs/test_durable_effect_boundaries.py
  ```
- interpretation: the repair is test-only and preserves the current main
  lineage; reread remote `main` before any later publication.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none; an owner instruction naming this exact
  gate-checked SHA remains required.

## Allowed paths

- `docs/program/tasks/W55B-INT-MAIN-PREP-03.md`;
- `docs/program/W55B-INT-MAIN-PREP-03.md`;
- ignored isolated `.local/worktrees/w55b-main-candidate/**` for exact
  checkout, locked test environment, disposable services and log evidence.

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, application/runtime/test source, production DB/S3, corpus
source, `origin/main`, `origin/dev`, tags and deployment workflow.

## Non-goals

No remote push, deployment host edit, stand copy, production migration,
workflow launch, live acceptance, release tag, normative corpus publication
or beta verdict. Current W56–W59 dev slices are outside this W55b candidate.

## Deliverables

An exact clean candidate worktree, full-gate log and digest, this task and
an evidence report with remaining deployment conditions.

## Required tests

- clean exact tree, frozen contract and migration readback, current main ref
  and fast-forward proof;
- complete `make gate` on unchanged candidate with literal `GATE OK`, or
  infrastructure-voided completion on that same clean SHA and stand under
  `R-125`, with whole failed directories and the exact unrun remainder;
- focused report governance, whitespace and exact-path proof.

## Integration contract

Only a later `W55B-INT-MAIN-01` with a direct owner instruction naming the
exact gate-checked SHA may publish to `origin/main`. It must reread the
remote, prove fast-forward, reconfirm the R-110 test-data-only condition or
take the stand copy, follow `MAIN_AUTODEPLOY_POLICY.md`, and verify workflow
and deployed same-SHA tree. A changed candidate needs a new full gate.

## Failure/idempotency/security cases

If the full gate fails without an `R-125` infrastructure-voided completion,
record the failed exact candidate without a deployment claim; focused tests
do not substitute for `GATE OK`. Keep
ignored `.env`, logs and disposable DB/S3 outside Git. Repeat preparation
without altering remote refs. R-46 readiness findings need an owner ruling.

## Rollback / feature flag

Remove the isolated ignored worktree and these two preparation documents if
abandoned. This task changes no product behavior.

## Handoff

- changed files: this task and its report only;
- contracts: none;
- next integration owner: `W55B-INT-MAIN-01` after exact owner instruction;
- forbidden hotspots and remote refs remain untouched by this task.
