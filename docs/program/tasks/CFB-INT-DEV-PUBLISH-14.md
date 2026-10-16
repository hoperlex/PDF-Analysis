# Task CFB-INT-DEV-PUBLISH-14 — publish checked W56a stage preparation

task_id: CFB-INT-DEV-PUBLISH-14

## Outcome

One exact clean fast-forward `origin/dev` candidate contains the completed,
unactivated W56a durable recorded stage port. Its SHA is read back after push.
The separate W55b release candidate and `origin/main` remain unchanged.

## Depends on

- `CFB-INT-DEV-PUBLISH-13` — completed prior dev publication at `6d6cec7c`;
- `W56A-INT-DURABLE-RECORDED-STAGE-01` — completed source port at `89d3798a`.

## Frozen inputs

- source commit: `89d3798a628b752d7259a5535be9cf756460bf09`;
- remote `dev`: `6d6cec7cae3847696dabcb9f1a08846cefdcd58a` at preparation read;
- remote `main`: `23fd729dbb06c642be0588017f6b195305e2e53e` at preparation read;
- code-first plan SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- migration head `0022_findings_v2`; W55b main candidate `6d63802a`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the source commit is ahead of the exact dev predecessor, passes
  focused checks and does not activate the runtime path.

### P-01 — current remote predecessor

- captured_at: 2026-10-16
- command: `git ls-remote origin refs/heads/dev refs/heads/main`
- captured_output:
  ```text
  6d6cec7cae3847696dabcb9f1a08846cefdcd58a refs/heads/dev
  23fd729dbb06c642be0588017f6b195305e2e53e refs/heads/main
  ```
- interpretation: reread the remote before push and refuse any moved ref.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/CURRENT_STATE.md` — one leading paragraph;
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-14.md`;
- `docs/program/CFB-INT-DEV-PUBLISH-14.md`;
- exact fast-forward update of `origin/dev` after checks.

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, application/runtime/test source in this integration commit,
corpus bytes, production DB/S3, `origin/main`, tags and deployment workflow.

## Non-goals

No W55b main deployment, W54 restore or paid repair, live AR v2 activation,
real PostgreSQL/S3 acceptance, full beta gate or beta verdict.

## Deliverables

The leading state entry, this task, integration report and exact pushed
`origin/dev` SHA read-back.

## Required tests

- integrated focused W56a recorded artifact/call/stage and program-governance
  suite; direct task governance, frozen inputs and whitespace;
- clean tree, fresh remote ref, fast-forward proof and exact push read-back;
- complete beta `make gate` deferred under R-135. The W55b release candidate
  owns its own complete gate at a different SHA.

## Integration contract

Only this integration task updates `origin/dev` with the exact checked tree.
Stop if the remote moved or the candidate is dirty. A later executor owner
must perform real DB/S3 acceptance, failure recovery and runtime activation
under a separate task. This slot grants no `origin/main` authority.

## Failure/idempotency/security cases

Exclude the untracked W55b main-preparation documents and all ignored local
promotion/secret artefacts. Never force-push. A retry rereads the remote and
does nothing if it already equals the candidate.

## Rollback / feature flag

The port is unactivated; corrections use a reviewed forward commit. No
history rewrite, deployment rollback or feature flag is needed here.

## Handoff

- changed files: exactly the three integration documentation paths above;
- contracts: none;
- next: executor/recovery owner and W54 restore verification;
- forbidden hotspots remain untouched by this integration commit.
