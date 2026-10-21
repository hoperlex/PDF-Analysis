# Task CFB-INT-DEV-PUBLISH-25 — integrate W58 isolated restore drill code

task_id: CFB-INT-DEV-PUBLISH-25

## Outcome

A clean fast-forward `origin/dev` candidate carries the W58 offline
PostgreSQL-plus-Blob restore coordinator and its migration-0023-aware
closed Blob-reference audit. This is code preparation, not a real restore
drill or recovery acceptance.

## Depends on

- `CFB-INT-DEV-PUBLISH-24` — completed at `7d522a598c173bb4090c8f9f3e1e548c6c89a738`;
- `W58-INT-ISOLATED-DB-BLOB-DRILL-CODE-01` — completed at
  `81208e721b296692fde005a95f6383e7a04ab609`.

## Frozen inputs

- integration base and directly read `origin/dev`:
  `7d522a598c173bb4090c8f9f3e1e548c6c89a738`;
- directly read `origin/main`: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- W58 source base `e70c91ef7064c8e36f377bd3995960a0e93acf35` is
  an ancestor of dev24; source commit `81208e721b296692fde005a95f6383e7a04ab609`;
- W58 source had exactly six task-granted paths, 33 focused tests and 140
  recovery/governance tests; no real DB/S3 service start;
- development API 47 paths / 54 operations / 124 schemas, 25 error codes,
  domain candidate revision 14 and migration head `0023_norm_citations`;
- API/stage SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`,
  `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315b2c1239453ba3a`;
- R-135 defers complete beta gate; W55b release gate is separate and pending.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `scripts/recovery/blob_reference_audit.py`
- enumerator_owner: `W58-INT-ISOLATED-DB-BLOB-DRILL-CODE-01`
- totality_query: `_CATALOG` SQL enumerates every schema-declared Blob
  column/FK; audit compares its complete result with `_CATALOG_EXPECTED`
  and focused missing/extra-column tests refuse.

The completed source owner alone changed the W58 closed source registry.
This integration cherry-picks those exact bytes without editing them.

## Captured premise evidence

- premise: current-head DB audit lacks two 0023 Blob references; the source
  commit adds those references and an unactivated coordinator on an
  ancestor of dev24.

### P-01 — exact source path scope

- captured_at: 2026-10-16
- command: `git diff --name-only e70c91ef..81208e72`
- captured_output:
  ```text
  docs/program/W58-INT-ISOLATED-DB-BLOB-DRILL-CODE-01.md
  docs/program/tasks/W58-INT-ISOLATED-DB-BLOB-DRILL-CODE-01.md
  scripts/recovery/blob_reference_audit.py
  scripts/recovery/isolated_restore_drill.py
  tests/integration/recovery/test_blob_reference_audit.py
  tests/integration/recovery/test_isolated_restore_drill.py
  ```
- interpretation: accept the source as-is; the real drill still needs an
  operator-owned isolated DB/S3 lane and fingerprint proof.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/CFB-INT-DEV-PUBLISH-25.md`
- `docs/program/CFB-INT-DEV-PUBLISH-25.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/W58-INT-ISOLATED-DB-BLOB-DRILL-CODE-01.md`
- `docs/program/tasks/W58-INT-ISOLATED-DB-BLOB-DRILL-CODE-01.md`
- `scripts/recovery/blob_reference_audit.py`
- `scripts/recovery/isolated_restore_drill.py`
- `tests/integration/recovery/test_blob_reference_audit.py`
- `tests/integration/recovery/test_isolated_restore_drill.py`

## Forbidden hotspots

`contracts/**`, migrations, application source/composition root, other
recovery files, root dependencies/locks, global styles, production DB/S3,
`origin/main`, tags and deployment workflow.

## Non-goals

No real restore callback, target isolation proof, PostgreSQL/S3 drill,
RPO/recovery verdict, served behavior, corpus publication, W55b deployment
or beta acceptance.

## Deliverables

Exact six-path source payload, bounded current-state update, this task/report
and direct read-back of the published dev SHA.

## Required tests

- integrated W58 recovery and programme suites, source 33/140 focused
  results, direct governance;
- exact path and frozen contract/head checks, whitespace, clean-tree, fresh
  remote fast-forward and post-push read-back;
- complete beta `make gate` deferred by R-135; W55b gate is separate.

## Integration contract

Cherry-pick exact source commit without payload edits. The coordinator
refuses invalid local copy before restore callback and DB/reference failure
before target write; it verifies complete isolated target bytes and every
available DB Blob before return. The caller must independently prove empty
isolated DB target, same isolated bucket, `pg_restore`, fingerprint and
read-only repeatable-read Session. No real drill is inferred from fakes.
A moved remote ref or changed source stops publication; never force-push.

## Failure/idempotency/security cases

Missing either new set/catalogue Blob, bad fingerprint, extra target key
or changed bytes refuses. Retry may preserve exact verified target prefix;
it never overwrites existing objects. No credential or Blob bytes enter Git.

## Rollback / feature flag

No served behavior is activated. Revert the six source paths and these
integration documents through a reviewed forward commit if abandoned.

## Handoff

- source files: exactly six W58 task paths;
- integration files: this task, report and bounded state update;
- contracts: none; recovery acceptance still needs real isolated drill;
- forbidden hotspots and `origin/main` remain untouched.
