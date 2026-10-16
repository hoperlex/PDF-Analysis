# Task CFB-INT-DEV-PUBLISH-12 — publish checked code-first integrations to dev

task_id: CFB-INT-DEV-PUBLISH-12

## Outcome

One clean, fast-forward development candidate containing the completed W56–W59
code-first preparations is published to `origin/dev` with exact SHA read-back.
Its state entry distinguishes these inert code slices from W55b release and
from beta or normative-corpus acceptance.

## Depends on

- `CFB-INT-STATE-11` — completed at `248179be`;
- `W57A-INT-RETRIEVAL-CANDIDATE-01` — completed at `6d2ef67f`;
- `W58-INT-OFFLINE-RESTORE-AUDIT-01` — completed at `cb26ee31`;
- `W59-INT-VERSION-PAIR-READ-01` — completed at `8b50a6a5`.

## Frozen inputs

- base code-first commit: `8b50a6a5f7d2e683f2c60b5d76dfe2edefea7ab3`;
- `origin/dev`: `8069220909e40c39e2329d5f5cb9585a5a5714ec` at the preparation read;
- `origin/main`: `23fd729dbb06c642be0588017f6b195305e2e53e` at the preparation read;
- code-first plan SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`;
- W58–W63 scope SHA-256 `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the local branch is 27 commits ahead of the exact remote `dev`
  predecessor, with all source task commits completed and no shared hotspot
  changes in this integration task.

### P-01 — publication ancestry

- captured_at: 2026-10-16
- command: `git rev-parse origin/dev; git rev-parse 8b50a6a5f7d2e683f2c60b5d76dfe2edefea7ab3`
- captured_output:
  ```text
  8069220909e40c39e2329d5f5cb9585a5a5714ec
  8b50a6a5f7d2e683f2c60b5d76dfe2edefea7ab3
  ```
- interpretation: the publication worktree starts at the completed code
  commit; the exact remote ref and fast-forward proof are rechecked before
  pushing the documentation commit.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/CURRENT_STATE.md` — one leading paragraph;
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-12.md`;
- `docs/program/CFB-INT-DEV-PUBLISH-12.md`;
- exact fast-forward update of `origin/dev` after checks.

## Forbidden hotspots

`contracts/**`, migration head, root dependency/lock files, composition
root, global styles, runtime/test code, corpus source, production DB,
`origin/main`, tags and deployment workflow.

## Non-goals

No W55b main release, production corpus import, live/provider call, full
`make gate`, beta verdict or deployment. Later unfinished slices are not
included in this candidate.

## Deliverables

The leading state entry, this task, an evidence report and exact remote
`origin/dev` SHA read-back.

## Required tests

- combined focused W57a/W58/W59 tests on the clean candidate;
- direct task governance, frozen SHA checks and `git diff --check`;
- clean-tree, remote-ref, fast-forward and exact pushed SHA proofs;
- full `make gate` deferred by R-135 until all beta code.

## Integration contract

The integration owner alone pushes the exact checked candidate as a
fast-forward to `origin/dev`. A moved remote ref or changed worktree stops the
push. Source modules remain unactivated; W55b's `origin/main` candidate is a
different exact tree requiring its own complete gate and deployment task.

## Failure/idempotency/security cases

Do not silently include untracked, incomplete agent work. A push mismatch
refuses; never force-push. A rerun reads the remote SHA and does not create a
second publication if it already equals the candidate. No corpus bytes or
secrets enter Git.

## Rollback / feature flag

No runtime behavior is switched on. A later correction uses a reviewed
forward commit; no history rewrite or force push.

## Handoff

- changed files: three exact documentation paths;
- contracts: none;
- next: continue code-first slices and W54 resource-gated restore verification;
- forbidden hotspots are untouched by this integration task.
