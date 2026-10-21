# Task CFB-INT-DEV-PUBLISH-19 — integrate isolated W58 target restore

task_id: CFB-INT-DEV-PUBLISH-19

## Outcome

A clean fast-forward `origin/dev` candidate carries the completed, unactivated
W58 sealed-mirror-to-isolated-target helper and its focused evidence. The
result remains recovery preparation, not a live DB/Blob restore or beta claim.

## Depends on

- `CFB-INT-DEV-PUBLISH-18` — completed at `c157ee0d4601f2bf81c68708ebf556b95b87acd5`;
- `W58-INT-ISOLATED-TARGET-OBJECT-RESTORE-01` — completed at `822a4b3bf01ad6e5d1512044e473ffeb618ba8d4`.

## Frozen inputs

- integration base and `origin/dev` at dispatch: `c157ee0d4601f2bf81c68708ebf556b95b87acd5`;
- `origin/main` at dispatch: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- exact source commit: `822a4b3bf01ad6e5d1512044e473ffeb618ba8d4`;
- W58 source task scope, tests and limitations as committed in that source;
- API/domain/error/stage SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`, `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`, `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`, `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315b2c1239453ba3a`;
- migration head `0022_findings_v2`; R-135 defers the complete beta gate;
- W55b `d3acd511` full gate is a separate main-candidate preparation, with no authority from this task.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the completed W58 source commit adds exactly one recovery helper,
  its focused test, task and report on the current published dev base.

### P-01 — source and remote predecessor

- captured_at: 2026-10-16
- command: `git show --format='%H%n%s' --name-only --no-renames 822a4b3bf01ad6e5d1512044e473ffeb618ba8d4`
- captured_output:
  ```text
  822a4b3bf01ad6e5d1512044e473ffeb618ba8d4
  feat(recovery): prepare isolated target object restore

  docs/program/W58-INT-ISOLATED-TARGET-OBJECT-RESTORE-01.md
  docs/program/tasks/W58-INT-ISOLATED-TARGET-OBJECT-RESTORE-01.md
  scripts/recovery/target_object_restore.py
  tests/integration/recovery/test_target_object_restore.py
  ```
- interpretation: only these four source paths may be cherry-picked; a fresh
  `ls-remote` must still confirm the dev predecessor before publication.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/CFB-INT-DEV-PUBLISH-19.md`
- `docs/program/CFB-INT-DEV-PUBLISH-19.md`
- `docs/program/CURRENT_STATE.md`
- `scripts/recovery/target_object_restore.py`
- `tests/integration/recovery/test_target_object_restore.py`
- `docs/program/tasks/W58-INT-ISOLATED-TARGET-OBJECT-RESTORE-01.md`
- `docs/program/W58-INT-ISOLATED-TARGET-OBJECT-RESTORE-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, root dependencies and lock files,
composition root, global styles, existing application source, W55b main
candidate, production DB/S3, corpus source, proxy credential, `origin/main`,
tags and deployment workflow. The W58 source's four new files retain their
own task grant.

## Non-goals

No real target S3 call, PostgreSQL restore, source quiescence, live stand
copy, corpus publication, W56 activation, W57 seal, W55b main deployment or
beta acceptance.

## Deliverables

The exact W58 source payload, a concise current-state update, this task,
integration report and direct remote read-back of the published SHA.

## Required tests

- W58 focused and whole recovery suites, program governance and source
  exact-path checks;
- frozen contract and migration read-back, clean tree and whitespace checks;
- fresh remote `dev` ref, fast-forward proof and exact post-push read-back;
- complete beta `make gate` deferred by R-135; W55b's separate gate is not
  reusable for this development candidate.

## Integration contract

This task alone may publish its exact checked SHA to `origin/dev` after
cherry-picking the completed W58 source without payload edits. The new helper
stays unconnected to runtime. Its caller must later prove an isolated target,
freeze the mirror, restore DB separately and audit Blob references/readback.
An explicit W58 drill task owns those actions. A moved dev ref or source diff
stops this integration for review; never force-push.

## Failure/idempotency/security cases

Do not include ignored logs, S3 credentials, corpus bytes or Docker volumes.
Do not start S3 or DB here while W55b gate owns the resource lane. A retry
must reread the remote and do nothing if already equal. No false acceptance
marker or deployed-state claim is written.

## Rollback / feature flag

The helper is unactivated; no flag or deployment rollback is needed. A
correction uses a reviewed forward commit, not a force update.

## Handoff

- changed integration files: this task, its report and a bounded current-state paragraph;
- source files: only the four exact W58 source paths;
- contracts: none; next owner: isolated real MinIO/PG recovery drill;
- forbidden hotspots remain untouched and `origin/main` is not updated.
