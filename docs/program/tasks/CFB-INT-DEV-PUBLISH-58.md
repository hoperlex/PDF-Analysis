# Task CFB-INT-DEV-PUBLISH-58 — persisted OCR acceptance and catalogue custody

task_id: CFB-INT-DEV-PUBLISH-58

## Outcome

Publish a clean development candidate with the completed W56b real DB/S3
acceptance test and W57b unserved verified-catalogue reader. Read back the
exact `origin/dev` SHA after a fast-forward push.

## Depends on

- `CFB-INT-DEV-PUBLISH-57`, completed at
  `44a2ceec616b8f03194080d4d117dfeec9e0e8ef`.
- `W56B-INT-RECOGNISED-REGION-DB-S3-ACCEPT-01`, completed at source
  `a1d90d207f7e15ba31cc4d0894248d7b0a1c4a58`.
- `W57B-INT-CATALOGUE-CUSTODY-READ-01`, completed at source
  `6380e3af39073aaa8258874ec43cf34da030c9a1`.

## Frozen inputs

- base commit: `44a2ceec616b8f03194080d4d117dfeec9e0e8ef`
- W56b source parent `ef802c112cd2b61de5ee9aa701739b04eb2d7f36`;
- W57b source parent `63fa3a40ef54a645dcc57ed99cfd1099b0574774`;
- API SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- error catalogue SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations`, `VERSION=0.6.0`;
- `origin/main` and `v0.6.0` `37393a979a430e490843d7f410e9eca9491a4ea1`;
- R-135 focused checks for intermediate dev candidates.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: the W57b reader checks stored `norm_document` count against
  the pinned snapshot count; no enumerator changes.

## Captured premise evidence

- premise: both completed source commits are additive, disjoint from dev57
  and each other, and neither owns a shared contract or migration hotspot.

### P-01 — source paths

- captured_at: 2026-10-16
- command: `git show --format= --name-only a1d90d207f7e15ba31cc4d0894248d7b0a1c4a58; git show --format= --name-only 6380e3af39073aaa8258874ec43cf34da030c9a1`
- captured_output:
  ```text
  docs/program/W56B-INT-RECOGNISED-REGION-DB-S3-ACCEPT-01.md
  docs/program/tasks/W56B-INT-RECOGNISED-REGION-DB-S3-ACCEPT-01.md
  tests/integration/runs/test_recognised_region_db_s3_accept.py
  docs/program/W57B-INT-CATALOGUE-CUSTODY-READ-01.md
  docs/program/tasks/W57B-INT-CATALOGUE-CUSTODY-READ-01.md
  src/auditmanager/norms/references/catalogue_input.py
  tests/integration/norms/references/test_catalogue_input.py
  ```
- interpretation: exactly seven independent source paths, with no contract,
  migration, dependency, composition root or deployed W55b tree.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W56B-INT-RECOGNISED-REGION-DB-S3-ACCEPT-01.md`
- `docs/program/tasks/W56B-INT-RECOGNISED-REGION-DB-S3-ACCEPT-01.md`
- `tests/integration/runs/test_recognised_region_db_s3_accept.py`
- `docs/program/W57B-INT-CATALOGUE-CUSTODY-READ-01.md`
- `docs/program/tasks/W57B-INT-CATALOGUE-CUSTODY-READ-01.md`
- `src/auditmanager/norms/references/catalogue_input.py`
- `tests/integration/norms/references/test_catalogue_input.py`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-58.md`
- `docs/program/CFB-INT-DEV-PUBLISH-58.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/lockfiles, composition root,
global styles, W54/W58/W59 source, production corpus/DB/S3, credentials,
deployment workflow, `origin/main` and tags.

## Non-goals

No served W56b or W57b route, paid provider call, qualified W54 corpus, 0024
seal, full beta gate or deployment.

## Deliverables

Two scoped cherry-picks, this task/report, focused checks, exact-path
handoff, dev fast-forward and remote readback.

## Required tests

- W56b source real PostgreSQL/S3 acceptance evidence: one targeted test pass
  on isolated 0023 instance, reviewed in its paired report. No second
  instance is needed for this test-only cherry-pick.
- W57b catalogue reader and canonical query focused tests plus programme
  governance: pass on the combined tree.
- Python compilation, frozen API hash, exact nine-path diff, whitespace,
  clean tree and explicit-argv technical handoff: pass.
- Fresh remote dev/main/tag read, fast-forward proof, exact-SHA dev push and
  readback. No intermediate full beta gate under R-135.

## Integration contract

The W56b test witnesses saved OCR-region evidence on real DB/S3 without
runtime change. The W57b reader is read-only and unserved; a future caller
must own authorization, short consistent transaction, reviewed unparsed-slug
list and publication fence. Integration changes no shared schema or API.

## Failure/idempotency/security cases

Stop on moved dev, dirty tree, path expansion or failed check. W57b reader
refuses stale Attempt, inconsistent pin, custody or Blob. No force push,
credential or private payload enters Git. Repeating the exact published SHA
is a no-op.

## Rollback / feature flag

Additive test and unserved reader; correct with a reviewed forward commit.
No data rollback or runtime flag is needed.

## Handoff

- changed files: nine exact allowed paths;
- contracts: none;
- checks and limits: paired report;
- forbidden hotspots untouched.
