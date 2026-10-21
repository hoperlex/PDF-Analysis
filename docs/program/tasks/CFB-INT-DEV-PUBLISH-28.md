# Task CFB-INT-DEV-PUBLISH-28 — integrate W58 restore adapter and W54 replay check

task_id: CFB-INT-DEV-PUBLISH-28

## Outcome

A clean fast-forward `origin/dev` candidate carries an unactivated guarded
PostgreSQL restore callback for W58 and a W54 embedding-build replay check
that re-reads persisted window metadata. Neither is a real restore drill or
normative corpus publication.

## Depends on

- `CFB-INT-DEV-PUBLISH-27` — complete at
  `746311c9ac5760b1658b6862f629471fa0cf15b4`;
- `W58-INT-ISOLATED-POSTGRES-ADAPTER-CODE-01` — complete at
  `559bddd9b3af353cd9cd87f0e96a3fde5a824b6a`;
- `W54-D127-REPLAY-INTEGRITY-01` — complete at
  `26edea8607ebb9ff845f547dff872bedd14ccd58`.

## Frozen inputs

- integration base and directly read `origin/dev`:
  `746311c9ac5760b1658b6862f629471fa0cf15b4`;
- directly read `origin/main`: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- W58 source parent `3d131d2966e0efeea7b53d9662785f253165a9a4`,
  commit `559bddd9b3af353cd9cd87f0e96a3fde5a824b6a`, four paths,
  24 targeted fake-runner tests;
- W54 source parent `4efd756c67b5160aeca3dbc58903f72df6c93636`,
  commit `26edea8607ebb9ff845f547dff872bedd14ccd58`, four paths,
  13 targeted offline tests;
- current API 48 paths / 55 operations / 131 schemas, SHA-256
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
  stage SHA-256
  `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
  domain IDs SHA-256
  `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`,
  error catalogue SHA-256
  `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`,
  migration head `0023_norm_citations`;
- R-135 defers complete beta gate; W55b main release gate is separate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: both completed source patches are bounded and disjoint; W58
  consumes the dev25 coordinator and W54 repairs a persisted-window replay
  defect without a schema change.

### P-01 — exact source path sets

- captured_at: 2026-10-16
- command: `git show --format= --name-only 559bddd9b3af353cd9cd87f0e96a3fde5a824b6a; git show --format= --name-only 26edea8607ebb9ff845f547dff872bedd14ccd58`
- captured_output:
  ```text
  docs/program/W58-INT-ISOLATED-POSTGRES-ADAPTER-CODE-01.md
  docs/program/tasks/W58-INT-ISOLATED-POSTGRES-ADAPTER-CODE-01.md
  scripts/recovery/isolated_postgres_restore.py
  tests/integration/recovery/test_isolated_postgres_restore.py
  docs/program/W54-D127-REPLAY-INTEGRITY-01.md
  docs/program/tasks/W54-D127-REPLAY-INTEGRITY-01.md
  src/auditmanager/norms/embedding_repository.py
  tests/integration/norms/embedding/test_repository_offline.py
  ```
- interpretation: accept the source commits as-is; no shared or migration
  conflict exists. Each source task owns its own exact four paths.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W58-INT-ISOLATED-POSTGRES-ADAPTER-CODE-01.md`;
- `docs/program/tasks/W58-INT-ISOLATED-POSTGRES-ADAPTER-CODE-01.md`;
- `scripts/recovery/isolated_postgres_restore.py`;
- `tests/integration/recovery/test_isolated_postgres_restore.py`;
- `docs/program/W54-D127-REPLAY-INTEGRITY-01.md`;
- `docs/program/tasks/W54-D127-REPLAY-INTEGRITY-01.md`;
- `src/auditmanager/norms/embedding_repository.py`;
- `tests/integration/norms/embedding/test_repository_offline.py`;
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-28.md`;
- `docs/program/CFB-INT-DEV-PUBLISH-28.md`;
- `docs/program/CURRENT_STATE.md`;
- ignored `.venv` link to the existing Python environment for focused tests.

## Forbidden hotspots

All other paths, especially `contracts/**`, migrations, root dependencies
and locks, composition root, other recovery/embedding files, global styles,
production DB/S3, `origin/main`, tags and deployment workflow.

## Non-goals

No real PostgreSQL/S3 drill, target-isolation or bucket proof, embedding
build over the real corpus, repaired snapshot, qualified bundle, DB/S3
publication, W55b deployment or beta acceptance.

## Deliverables

Exact eight-path source payload, bounded state update, this task/report and
direct published-dev SHA readback.

## Required tests

- integrated W58 recovery/programme suite and W54 offline repository
  regression; direct governance;
- exact source patch/path and frozen contract checks, whitespace,
  clean-tree, fresh remote fast-forward and post-push readback;
- real DB/S3 drill and complete beta gate deferred by host lane/R-135;
  W55b release gate is separate.

## Integration contract

Cherry-pick exact W58 then W54 source commits without editing their
payloads. The W58 adapter is only passed to the coordinator for an
operator-proven empty isolated PostgreSQL target and matching disposable
bucket; its loopback guard does not prove absence of a tunnel. W54 replay
streams stored window metadata before `created=False`; it does not
rehash vector bytes. Publish only to `origin/dev` after fresh remote read;
never force-push.

## Failure/idempotency/security cases

W58 refuses unsafe/nonempty target, altered dump, mismatched fingerprint or
failed read-only mode. W54 refuses missing, changed or extra persisted
window rows on replay. A moved ref, source conflict or failing focused
check stops publication. No credential or corpus bytes enter Git.

## Rollback / feature flag

W58 adapter is unactivated. Revert the eight source paths and these three
integration documents through a reviewed forward commit if abandoned;
no schema or data rollback.

## Handoff

- source files: two exact four-path task grants;
- integration files: this task, report and bounded state update;
- contracts: none; real service acceptance remains open;
- forbidden hotspots and `origin/main` remain untouched.
