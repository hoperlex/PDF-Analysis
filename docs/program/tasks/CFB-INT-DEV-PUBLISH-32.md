# Task CFB-INT-DEV-PUBLISH-32 — integrate W59 route and W58 Blob readback fix

task_id: CFB-INT-DEV-PUBLISH-32

## Outcome

A clean fast-forward `origin/dev` candidate carries the completed W59 pure
version/stage/section/profile route pin and the W58 correction that puts a
sealed digest in copied target S3 object metadata. Neither is activated in
served runtime or establishes real recovery acceptance.

## Depends on

- `CFB-INT-DEV-PUBLISH-31` — complete at
  `69b923156ea3988dbad3cc378644b9799a6bdd23`;
- `W59-INT-STAGED-ROUTE-PREP-01` — complete at
  `1f34b01cceb0688989d80b1977c1619ffb260166`;
- `W58-INT-TARGET-DIGEST-METADATA-01` — complete at
  `844c7213916c69c10974ce2f02ff1495baee4a1b`.

## Frozen inputs

- integration base and published `origin/dev`:
  `69b923156ea3988dbad3cc378644b9799a6bdd23`;
- `origin/main` at preparation: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- both source parents exactly equal the integration base; W59 adds four
  paths and W58 adds five disjoint paths;
- API 48 paths / 55 operations / 131 schemas, SHA-256
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256
  `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain IDs SHA-256
  `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256
  `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations`; R-135 defers the complete beta gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: both source commits are direct children of dev31 with disjoint
  task-granted paths, so W59 can fast-forward and W58 can be cherry-picked
  without a payload edit.

### P-01 — source identity and path set

- captured_at: 2026-10-16
- command: `git show --format='%H %P' --name-only 1f34b01cceb0688989d80b1977c1619ffb260166`
- captured_output:
  ```text
  1f34b01cceb0688989d80b1977c1619ffb260166 69b923156ea3988dbad3cc378644b9799a6bdd23
  docs/program/W59-INT-STAGED-ROUTE-PREP-01.md
  docs/program/tasks/W59-INT-STAGED-ROUTE-PREP-01.md
  src/auditmanager/sections/staged_routing.py
  tests/integration/sections/test_staged_routing.py
  ```
- interpretation: there is no source patch overlap with integration records
  or frozen contracts; no runtime routing authority follows from this.

### P-02 — W58 source path set

- captured_at: 2026-10-16
- command: `git show --format='%H %P' --name-only 844c7213916c69c10974ce2f02ff1495baee4a1b`
- captured_output:
  ```text
  844c7213916c69c10974ce2f02ff1495baee4a1b 69b923156ea3988dbad3cc378644b9799a6bdd23
  docs/program/W58-INT-TARGET-DIGEST-METADATA-01.md
  docs/program/tasks/W58-INT-TARGET-DIGEST-METADATA-01.md
  scripts/recovery/target_object_restore.py
  tests/integration/recovery/test_isolated_restore_drill.py
  tests/integration/recovery/test_target_object_restore.py
  ```
- interpretation: W58's source patch is separate from the W59 route and
  frozen contracts; it remains an unactivated offline helper correction.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W59-INT-STAGED-ROUTE-PREP-01.md`;
- `docs/program/tasks/W59-INT-STAGED-ROUTE-PREP-01.md`;
- `src/auditmanager/sections/staged_routing.py`;
- `tests/integration/sections/test_staged_routing.py`;
- `docs/program/W58-INT-TARGET-DIGEST-METADATA-01.md`;
- `docs/program/tasks/W58-INT-TARGET-DIGEST-METADATA-01.md`;
- `scripts/recovery/target_object_restore.py`;
- `tests/integration/recovery/test_isolated_restore_drill.py`;
- `tests/integration/recovery/test_target_object_restore.py`;
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-32.md`;
- `docs/program/CFB-INT-DEV-PUBLISH-32.md`;
- `docs/program/CURRENT_STATE.md`.

## Forbidden hotspots

All other paths, especially `contracts/**`, migrations, root dependencies
and locks, composition root, existing production route/Run/profile code,
other W54/W55/W58 files, global styles, production DB/S3, `origin/main`, tags and
deployment workflow.

## Non-goals

No SECTION-SEAL, authoritative persisted stage/confirmation read, actor
authorization, executable profile registration, Run pin write, served route,
real PostgreSQL/S3 drill, full source S3 metadata preservation, provider call,
corpus publication, W55b deployment or beta acceptance.

## Deliverables

Exact nine-path W59/W58 source payload, bounded state update, this task/report
and directly read published-dev SHA.

## Required tests

- integrated staged route, section and W58 recovery suites, programme governance;
- direct task governance, compilation, frozen hashes, source/path equality,
  whitespace, clean tree, fresh remote fast-forward and post-push readback;
- no Docker/PG/S3 or complete beta gate while W55b owns the heavy host lane.

## Integration contract

Fast-forward the exact W59 source commit, cherry-pick the exact W58 patch,
then add only the integration records. A future SECTION-SEAL owner must obtain saved version membership,
stage and expert confirmation in one authorized transaction, use a sealed
executable profile map and pin the returned tuple with the Run. The earlier
section-only route must not remain as a bypass. W58 operator code must later
prove a real positive-Blob drill and decide full source metadata policy. A
moved remote ref stops publication; never force-push.

## Failure/idempotency/security cases

Missing, invalid, foreign-version or stage-mismatched supplied facts refuse.
An unavailable profile never falls back to AR. Identical valid input returns
an equal immutable pin. This pure check proves no DB or actor provenance.
W58 rehashes local mirror bytes before conditional PutObject and later
readback refuses absent or wrong `content-sha256` metadata.

## Rollback / feature flag

Both modules are unserved; remove their source/tests and these integration records
through a reviewed forward commit if abandoned. No data rollback is needed.

## Handoff

- changed files: the four W59 and five W58 paths plus this task, report and state;
- contracts: none; no forbidden hotspots touched;
- next: W58 positive-Blob service drill, SECTION-SEAL and authoritative run-start integration.
