# Task CFB-INT-DEV-PUBLISH-33 — integrate W56b, W57a and W58 code

task_id: CFB-INT-DEV-PUBLISH-33

## Outcome

A clean fast-forward `origin/dev` candidate carries an unserved W56b
Run/Attempt crop reader, an unserved guarded W57a CITE transaction writer,
and an opt-in W58 synthetic restore fixture/runner CLI. Real DB/S3 acceptance
and served activation remain separate.

## Depends on

- `CFB-INT-DEV-PUBLISH-32` — complete at
  `5fa9473c54a5fb009ec8c0a6a45327a3a7f1dc15`;
- `W56B-INT-RUN-CROP-READ-01` — complete at
  `79c726ad2d427f3e55c00093213c9b20987cff28`;
- `W57A-INT-CITE-TXN-PREP-01` — complete at
  `5da5f98f96feb113c3a5f45d2ece4b0b92ef4c7c`;
- `W58-INT-SYNTHETIC-DRILL-CLI-01` — complete at
  `283cb1ce7602267fe8e60d1c2f94ac854b7ab843`.

## Frozen inputs

- integration base and published `origin/dev`:
  `5fa9473c54a5fb009ec8c0a6a45327a3a7f1dc15`;
- `origin/main` at preparation: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- all three source parents equal the integration base and change disjoint
  five/four/six-path sets;
- API 48 paths / 55 operations / 131 schemas, SHA-256
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256
  `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain IDs SHA-256
  `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256
  `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- crop manifest schema SHA-256
  `0a745c5477bf83a4ba1b14de9b42023525b29b862a3b7104e70fed91a63c4968`;
- migration head `0023_norm_citations`; R-135 defers the complete beta gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the three completed sources are direct children of dev32 with
  disjoint task-granted paths; W56b can fast-forward and the W57a/W58 patches
  can be cherry-picked without payload edits.

### P-01 — exact source parent and path set

- captured_at: 2026-10-16
- command: `git show --format='%H %P' --name-only 79c726ad2d427f3e55c00093213c9b20987cff28`
- captured_output:
  ```text
  79c726ad2d427f3e55c00093213c9b20987cff28 5fa9473c54a5fb009ec8c0a6a45327a3a7f1dc15
  docs/program/W56B-INT-RUN-CROP-READ-01.md
  docs/program/tasks/W56B-INT-RUN-CROP-READ-01.md
  src/auditmanager/analysis/public.py
  src/auditmanager/runs/geometry_crop_input.py
  tests/integration/runs/test_geometry_crop_input.py
  ```
- interpretation: integration can preserve the exact source commit; the
  path list includes no contract, migration or served composition change.

### P-02 — W57a CITE source path set

- captured_at: 2026-10-16
- command: `git show --format='%H %P' --name-only 5da5f98f96feb113c3a5f45d2ece4b0b92ef4c7c`
- captured_output:
  ```text
  5da5f98f96feb113c3a5f45d2ece4b0b92ef4c7c 5fa9473c54a5fb009ec8c0a6a45327a3a7f1dc15
  docs/program/W57A-INT-CITE-TXN-PREP-01.md
  docs/program/tasks/W57A-INT-CITE-TXN-PREP-01.md
  src/auditmanager/findings/citation_publication.py
  tests/integration/findings/test_w57a_citation_publication_offline.py
  ```
- interpretation: the new findings adapter has no shared facade, migration
  or composition overlap with W56b.

### P-03 — W58 synthetic CLI source path set

- captured_at: 2026-10-16
- command: `git show --format='%H %P' --name-only 283cb1ce7602267fe8e60d1c2f94ac854b7ab843`
- captured_output:
  ```text
  283cb1ce7602267fe8e60d1c2f94ac854b7ab843 5fa9473c54a5fb009ec8c0a6a45327a3a7f1dc15
  docs/program/W58-INT-SYNTHETIC-DRILL-CLI-01.md
  docs/program/tasks/W58-INT-SYNTHETIC-DRILL-CLI-01.md
  scripts/recovery/synthetic_drill_fixture.py
  scripts/recovery/synthetic_drill_runner.py
  tests/integration/recovery/test_synthetic_drill_fixture.py
  tests/integration/recovery/test_synthetic_drill_runner.py
  ```
- interpretation: the operator CLI is opt-in, touches no existing recovery
  helper and has no real service proof in its source task.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W56B-INT-RUN-CROP-READ-01.md`;
- `docs/program/tasks/W56B-INT-RUN-CROP-READ-01.md`;
- `src/auditmanager/analysis/public.py`;
- `src/auditmanager/runs/geometry_crop_input.py`;
- `tests/integration/runs/test_geometry_crop_input.py`;
- `docs/program/W57A-INT-CITE-TXN-PREP-01.md`;
- `docs/program/tasks/W57A-INT-CITE-TXN-PREP-01.md`;
- `src/auditmanager/findings/citation_publication.py`;
- `tests/integration/findings/test_w57a_citation_publication_offline.py`;
- `docs/program/W58-INT-SYNTHETIC-DRILL-CLI-01.md`;
- `docs/program/tasks/W58-INT-SYNTHETIC-DRILL-CLI-01.md`;
- `scripts/recovery/synthetic_drill_fixture.py`;
- `scripts/recovery/synthetic_drill_runner.py`;
- `tests/integration/recovery/test_synthetic_drill_fixture.py`;
- `tests/integration/recovery/test_synthetic_drill_runner.py`;
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-33.md`;
- `docs/program/CFB-INT-DEV-PUBLISH-33.md`;
- `docs/program/CURRENT_STATE.md`.

## Forbidden hotspots

All other paths, especially `contracts/**`, migrations, root dependencies
and locks, composition root, existing Runs/Jobs/storage adapters, API/UI,
other W54/W55/W57a/W58 paths, global styles, production DB/S3, `origin/main`,
tags and deployment workflow.

## Non-goals

No provider/vision call or effect journal, model budget, W56b stage
registration, served route, qualified W57a corpus set, live DB/S3 acceptance,
full source-S3 metadata recovery, corpus publication, W55b deployment or
beta verdict. W57a's new DB writer is not activated.

## Deliverables

Exact fifteen-path W56b/W57a/W58 source payload, bounded state update, this task/report
and direct published-dev SHA readback.

## Required tests

- integrated W56b crop input, W57a CITE/grounding, W58 synthetic CLI and
  programme suites;
- direct task governance, compilation, frozen hash/path readback, whitespace,
  clean tree, fresh remote fast-forward and post-push readback;
- no Docker/PG/S3 or complete beta gate while W55b owns the host.

## Integration contract

Fast-forward exact W56b source, cherry-pick exact W57a and W58 patches, then
add only integration records. The future W56b stage must supply a transaction, authoritative current
Attempt and BlobStore, then recheck/journal the provider effect separately
after this read. W57a needs a real PostgreSQL commit/deferred-constraint
test and Blob custody reader before its CITE writer serves. W58 CLI requires
an explicitly isolated service lane, capacity check and operator identity
proof before invocation. A moved remote ref stops publication; never force-push.

## Failure/idempotency/security cases

Stale Attempt, non-running/changed Run, absent/duplicate/changed stage,
foreign VersionUid, excessive input bytes or corrupt/missing Blob refuse the
whole read. No partial result or silent fallback is returned. The read holds
row locks during Blob streaming and must be kept short. W57a rejects stale
authority or out-of-set citations before INSERT; the caller must roll back
on a later DB failure. W58 refuses unsafe target config or nonempty bucket
before restore and leaves failed disposable targets for inspection.

## Rollback / feature flag

No served caller exists. Remove the additive adapters/tests, narrow facade
exports and opt-in CLI through a reviewed forward commit if abandoned. No
data rollback follows from this integration alone.

## Handoff

- changed files: fifteen source paths plus this task, report and state;
- contracts: none; no forbidden hotspots touched;
- next: real isolated W57a/W58 DB/S3 acceptance, W56b provider/budget/effect
  policy and explicit served integration tasks.
