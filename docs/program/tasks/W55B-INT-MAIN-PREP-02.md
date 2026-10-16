# Task W55B-INT-MAIN-PREP-02 — verify repaired exact W55b candidate

task_id: W55B-INT-MAIN-PREP-02

## Outcome

The isolated clean `d3acd511c608dbff94d448b95ebb826cf5437c75` W55b
candidate receives a complete canonical `make gate` result after the measured
serving-carrier test correction. The report identifies the exact checked SHA
and every condition for a later separate `W55B-INT-MAIN-01` publication
decision. This task does not update a remote ref.

## Depends on

- `W55B-INT-CLOSE` — completed at `6d63802ab465a0317839c9b57abd5e90f3d91769`;
- `W55B-INT-GATE-TIMEOUT-01` — completed at `d3acd511c608dbff94d448b95ebb826cf5437c75`.

## Frozen inputs

- repaired candidate: `d3acd511c608dbff94d448b95ebb826cf5437c75`;
- remote `main` at preparation read: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- remote `dev` at preparation read: `c157ee0d4601f2bf81c68708ebf556b95b87acd5`;
- W55 plan SHA-256 `9f4e0f204284347bc3ead59423a5cff830bbc9298ceaa2d47e1412f640b92b64`;
- main auto-deploy policy SHA-256 `1be97f93e6a8573ff88bc58a75a4166403d0db8badf401dd8e4fe39972fbf818`;
- W55b close report SHA-256 `8354713829a671c68a6c77fad22dd055b7ea742e37542f4ede63c5e07fe4ace9`;
- candidate `VERSION=0.6.0`, migration head `0021_portal_bundles`,
  API 47 paths / 54 operations / 123 schemas, error catalogue 24 codes;
- prior exact `6d63802a` gate attempts had no `GATE OK`; the repair changes
  only one test plus task/report, not production behavior;
- owner confirmed on 2026-10-16 that alpha contains only generated test data;
  this R-110 condition must be rechecked immediately before any publication.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the 30-second serving-carrier test wait failed after a measured
  37.9-second pre-provider path; the repaired SHA has a 120-second test wait.

### P-01 — exact predecessor and scope

- captured_at: 2026-10-16
- command: `git merge-base --is-ancestor 23fd729d d3acd511 && git diff --name-only 6d63802a..d3acd511`
- captured_output:
  ```text
  docs/program/W55B-INT-GATE-TIMEOUT-01.md
  docs/program/tasks/W55B-INT-GATE-TIMEOUT-01.md
  tests/integration/composition/test_the_run_leaves_the_request_thread.py
  ```
- interpretation: reread `origin/main` and rerun ancestry immediately before
  a future publication; this task grants none.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none; an owner instruction naming the exact
  gate-checked candidate remains required.

## Allowed paths

- `docs/program/tasks/W55B-INT-MAIN-PREP-02.md`;
- `docs/program/W55B-INT-MAIN-PREP-02.md`;
- ignored isolated `.local/worktrees/w55b-main-candidate/**` for exact checkout,
  locked test environments, disposable gate services and evidence only.

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, application/runtime/test source, production DB/S3, corpus
source, `origin/main`, `origin/dev`, tags and deployment workflow.

## Non-goals

No remote push, deployment host edit, stand copy, production migration,
workflow launch, live acceptance, release tag, normative corpus publication or
beta verdict. Current W56–W59 dev slices are outside this W55b candidate.

## Deliverables

An exact candidate worktree, full-gate log and digest, this task and a report
with remaining deployment conditions.

## Required tests

- clean exact worktree, frozen contract and migration read-back, current main
  ref and fast-forward proof;
- complete `make gate` on unchanged candidate with literal `GATE OK` for a
  successful preparation verdict;
- focused report governance, whitespace and exact-path proof.

## Integration contract

Only a later `W55B-INT-MAIN-01` with a direct owner instruction naming the
exact gate-checked SHA may publish to `origin/main`. It must reread the remote,
prove fast-forward, reconfirm the test-data-only R-110 condition or take the
stand copy, follow `MAIN_AUTODEPLOY_POLICY.md`, and verify workflow and the
deployed same-SHA tree after push. A changed candidate needs a new full gate.

## Failure/idempotency/security cases

If the full gate fails, record the failed exact candidate without a deployment
claim; focused tests do not substitute for `GATE OK`. Keep ignored `.env`, logs
and disposable DB/S3 outside Git. Repeat preparation without altering remote
refs. Readiness findings under R-46 require an explicit owner ruling, not a
silent local pass claim.

## Rollback / feature flag

Remove the isolated ignored worktree and revert these two documents if the
candidate is abandoned. This preparation changes no product behavior.

## Handoff

- changed files: this task and its report only;
- contracts: none;
- next integration owner: `W55B-INT-MAIN-01` after an exact owner instruction;
- forbidden hotspots and remote refs remain untouched by this task.
