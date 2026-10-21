# Task CFB-INT-DEV-PUBLISH-62 — real saved W57b PDF text acceptance

task_id: CFB-INT-DEV-PUBLISH-62

## Outcome

Publish the completed real PostgreSQL/S3 acceptance of W57b saved PDF text
and OCR exclusion, refresh first-read state, and read back exact `origin/dev`.

## Depends on

- `CFB-INT-DEV-PUBLISH-61`, completed at
  `8c0dc0e708332e73bd3dc5defdae9fa97665f4ac`.
- `W57B-INT-SAVED-TEXT-DB-S3-ACCEPT-01`, completed at source
  `6a884f0ab88f8720c34ec2ba73d355b17509c507`.

## Frozen inputs

- base commit: `8c0dc0e708332e73bd3dc5defdae9fa97665f4ac`
- source parent is this exact base;
- API SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- error catalogue SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations`, `VERSION=0.6.0`;
- `origin/main` and `v0.6.0` `37393a979a430e490843d7f410e9eca9491a4ea1`;
- R-135 focused checks for intermediate dev candidates.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: the accepted reader verifies every PDF text page against
  the immutable Version count; no enumerator changes.

## Captured premise evidence

- premise: dev61 saved-text reader has offline checks but no real DB/S3
  evidence; source task adds only a real-service test and documents.

### P-01 — source paths

- captured_at: 2026-10-16
- command: `git show --format= --name-only 6a884f0ab88f8720c34ec2ba73d355b17509c507`
- captured_output:
  ```text
  docs/program/W57B-INT-SAVED-TEXT-DB-S3-ACCEPT-01.md
  docs/program/tasks/W57B-INT-SAVED-TEXT-DB-S3-ACCEPT-01.md
  tests/integration/runs/test_reference_text_input_db_s3_accept.py
  ```
- interpretation: three additive source paths, no runtime, contract,
  migration, composition root or deployed W55b tree.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W57B-INT-SAVED-TEXT-DB-S3-ACCEPT-01.md`
- `docs/program/tasks/W57B-INT-SAVED-TEXT-DB-S3-ACCEPT-01.md`
- `tests/integration/runs/test_reference_text_input_db_s3_accept.py`
- `docs/program/CURRENT_STATE.md`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-62.md`
- `docs/program/CFB-INT-DEV-PUBLISH-62.md`

## Forbidden hotspots

Runtime, `contracts/**`, migrations, root dependencies/lockfiles,
composition root, global styles, W54/W56/W58/W59 source, production
corpus/DB/S3, credentials, deployment workflow, `origin/main` and tags.

## Non-goals

No served W57b stage/route, rule publication, 0024 seal, qualified W54
corpus, full B3.5 acceptance, full beta gate or deployment.

## Deliverables

One scoped cherry-pick, state refresh, this task/report, focused checks,
exact-path handoff, dev fast-forward and remote readback.

## Required tests

- Source's one targeted real 0023 PostgreSQL/S3 pass and resource cleanup,
  as recorded in its paired report.
- Combined offline saved-text/page bridge, governance and documentation
  fact checks: pass.
- Python compilation, frozen API hash, exact six-path diff, whitespace,
  clean-tree technical handoff: pass.
- Fresh remote refs, fast-forward proof, exact-SHA dev push and readback.
  No intermediate full beta gate under R-135.

## Integration contract

The new test witnesses the production executor's saved/bound text-layer
StageResult, real Blob read under a current Attempt, empty PDF text for
OCR-only pages and forged-token refusal before S3 access. No runtime caller
or policy changes; evidence is synthetic and unserved.

## Failure/idempotency/security cases

Stop on moved dev, dirty tree, expanded paths or failed check. The source
test rolls back rows and its disposable instance/volumes were removed. No
force push, credential or private payload enters Git. Repeating the exact
published SHA is a no-op.

## Rollback / feature flag

Test and documentation only; correct with a reviewed forward commit.
No data rollback or runtime flag is needed.

## Handoff

- changed files: six exact allowed paths;
- contracts: none;
- checks and limits: paired report;
- forbidden hotspots untouched.
