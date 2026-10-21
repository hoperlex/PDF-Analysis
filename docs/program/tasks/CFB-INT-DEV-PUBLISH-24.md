# Task CFB-INT-DEV-PUBLISH-24 — retain W55b D-142 repair on dev

task_id: CFB-INT-DEV-PUBLISH-24

## Outcome

A clean fast-forward `origin/dev` candidate contains the exact W55b
Attempt-specific D-142 test correction and its source evidence, preserving
the repaired W55b release candidate as an ancestor of the development line.
No production behavior or deployment ref changes.

## Depends on

- `CFB-INT-DEV-PUBLISH-23` — completed at `e70c91ef7064c8e36f377bd3995960a0e93acf35`;
- `W55B-INT-D142-GATE-REPAIR-01` — completed at `37393a979a430e490843d7f410e9eca9491a4ea1`.

## Frozen inputs

- integration base and directly read `origin/dev`:
  `e70c91ef7064c8e36f377bd3995960a0e93acf35`;
- directly read `origin/main`: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- source commit `37393a979a430e490843d7f410e9eca9491a4ea1`
  is on `d3acd511c608dbff94d448b95ebb826cf5437c75`, an ancestor of dev23;
- dev23 has API 47 paths / 54 operations / 124 schemas, 25 error codes,
  migration head `0023_norm_citations`; source W55b candidate retains
  47 / 54 / 123, 24 codes and head `0021_portal_bundles`;
- source D-142 fresh isolated PostgreSQL/S3 check passed 2/2; the separate
  full W55b gate on this source SHA is waiting for host RAM/load window.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the repair changes exactly one integration test and its task and
  report; the source parent is already in the development ancestry.

### P-01 — exact source payload

- captured_at: 2026-10-16
- command: `git diff --name-only d3acd511..37393a97; git merge-base --is-ancestor d3acd511 e70c91ef`
- captured_output:
  ```text
  docs/program/W55B-INT-D142-GATE-REPAIR-01.md
  docs/program/tasks/W55B-INT-D142-GATE-REPAIR-01.md
  tests/integration/runs/test_durable_effect_boundaries.py
  ```
- interpretation: merge this completed source commit without payload edits
  so future dev candidates contain its exact history.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/CFB-INT-DEV-PUBLISH-24.md`
- `docs/program/CFB-INT-DEV-PUBLISH-24.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/W55B-INT-D142-GATE-REPAIR-01.md`
- `docs/program/tasks/W55B-INT-D142-GATE-REPAIR-01.md`
- `tests/integration/runs/test_durable_effect_boundaries.py`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root,
global styles, other application/tests, production DB/S3, W55b gate
worktree, `origin/main`, tags and deployment workflow.

## Non-goals

No W55b full-gate claim, remote main push, release tag, served AR v2/CITE,
corpus DB/S3 publication or beta verdict. W57A 01A's domain contract and
0023 head remain byte-identical.

## Deliverables

Exact source merge ancestry, bounded current-state update, this task/report
and direct read-back of the published dev SHA.

## Required tests

- source 2/2 real-service D-142 result; integrated container-free test
  collection, programme governance and direct task governance;
- exact three-path source payload, frozen contracts/head, whitespace,
  clean-tree, fresh remote fast-forward and post-push read-back;
- complete beta gate deferred by R-135; separate W55b full gate on source
  SHA remains mandatory before any main-publication decision.

## Integration contract

Merge the exact repair commit with `--no-ff` so `37393a97` becomes a dev
ancestor. Its test selects the crashed and rerun publications by Attempt,
stage, Blob and role. A moved remote ref or changed source stops
publication; never force-push. This task grants no `origin/main` authority.

## Failure/idempotency/security cases

The test still fails for missing publication, wrong state or absent
abandonment timestamp. No credential, Blob byte or gate log enters Git.
Retry reads remote and no-ops if already equal.

## Rollback / feature flag

This is test-only; no feature flag or data rollback. Corrections use a
reviewed forward commit.

## Handoff

- source files: exactly the three W55b repair paths;
- integration files: this task/report and bounded state update;
- contracts: none; W55b full gate still pending; `origin/main` untouched.
