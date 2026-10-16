# Task CFB-INT-DEV-PUBLISH-38 — publish W55b candidate gate evidence

task_id: CFB-INT-DEV-PUBLISH-38

## Outcome

The two completed W55b main-preparation reports, including the exact
`37393a979a430e490843d7f410e9eca9491a4ea1` R-125 gate completion,
are visible on a clean fast-forward `origin/dev` commit. This is evidence
publication only and does not deploy W55b or alter the release candidate.

## Depends on

- `CFB-INT-DEV-PUBLISH-37` — published `origin/dev` at
  `f0580e089867ba6a9380a48dfca19a23e47f6788`;
- `W55B-INT-MAIN-PREP-02` — failed-gate report at `d02b5ae4`;
- `W55B-INT-MAIN-PREP-03` — R-125 completed-gate report at `9b83331d`.

## Frozen inputs

- direct remote read, 2026-10-16: `origin/dev=f0580e089867ba6a9380a48dfca19a23e47f6788`;
- direct remote read, 2026-10-16: `origin/main=23fd729dbb06c642be0588017f6b195305e2e53e`;
- W55b release candidate: `37393a979a430e490843d7f410e9eca9491a4ea1`;
- W55 plan SHA-256 `9f4e0f204284347bc3ead59423a5cff830bbc9298ceaa2d47e1412f640b92b64`;
- main policy SHA-256 `1be97f93e6a8573ff88bc58a75a4166403d0db8badf401dd8e4fe39972fbf818`;
- W55b close SHA-256 `8354713829a671c68a6c77fad22dd055b7ea742e37542f4ede63c5e07fe4ace9`;
- development surface at base: `VERSION=0.6.0`, API 48 paths / 55
  operations / 131 schemas, errors 25, migration head `0023`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the exact `origin/dev` predecessor does not contain the two
  completed W55b main-preparation reports.

### P-01 — remote predecessor

- captured_at: 2026-10-16
- command: `git ls-remote origin refs/heads/dev refs/heads/main`
- captured_output:
  ```text
  f0580e089867ba6a9380a48dfca19a23e47f6788 refs/heads/dev
  23fd729dbb06c642be0588017f6b195305e2e53e refs/heads/main
  ```
- interpretation: re-read both refs before the fast-forward push; stop if
  either moved.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev` only;
- origin_main_authority: none.

## Allowed paths

- `docs/program/tasks/CFB-INT-DEV-PUBLISH-38.md`;
- `docs/program/CFB-INT-DEV-PUBLISH-38.md`;
- `docs/program/CURRENT_STATE.md`;
- `docs/program/tasks/W55B-INT-MAIN-PREP-02.md`;
- `docs/program/W55B-INT-MAIN-PREP-02.md`;
- `docs/program/tasks/W55B-INT-MAIN-PREP-03.md`;
- `docs/program/W55B-INT-MAIN-PREP-03.md`.

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, application/runtime/test source, corpus source, production
DB/S3, `origin/main`, tags and deployment workflow.

## Non-goals

No W55b deployment, release tag, paid corpus repair, DB/S3 import, beta gate
or beta verdict. The separate exact-SHA instruction and deployment checks
remain the responsibility of `W55B-INT-MAIN-01`.

## Deliverables

These four preparation documents, this task, a concise integration report,
a leading current-state note and exact `origin/dev` push read-back.

## Required tests

- exact source-document and frozen-digest readback;
- whitespace, direct task governance and staged-path scope;
- clean candidate, fresh remote refs, fast-forward proof and push read-back.
  The candidate's gate is already measured on its separate exact SHA.

## Integration contract

Only this integration task may fast-forward the checked documentation
candidate to `origin/dev`. Its publication cannot satisfy the separate
`origin/main` instruction. The W55b candidate stays the exact `37393a97`
tree; no development SHA inherits its full-gate evidence.

## Failure/idempotency/security cases

Stop if the remote moves, the tree is dirty or any source report changes.
Keep ignored gate logs and credentials outside Git. No force-push. A retry
that finds the exact candidate already on `origin/dev` performs no push.

## Rollback / feature flag

The only change is documentation. Correct errors in a forward commit; no
runtime flag or deployment rollback applies.

## Handoff

- changed files: exactly the seven allowed documentation paths;
- contracts: none;
- next: `W55B-INT-MAIN-01` only after the owner names the exact gated SHA;
- forbidden hotspots remain untouched.
