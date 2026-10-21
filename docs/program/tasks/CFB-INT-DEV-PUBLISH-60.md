# Task CFB-INT-DEV-PUBLISH-60 — W57b real catalogue and exact text pages

task_id: CFB-INT-DEV-PUBLISH-60

## Outcome

Publish a clean development candidate with W57b's real PostgreSQL/S3
catalogue acceptance and exact text-layer-to-reference-page bridge. Refresh
the first-read state and read back the exact `origin/dev` SHA.

## Depends on

- `CFB-INT-STATE-59`, completed at
  `2b0a8a04a7ef2ce050e3ec3df9dd5414c68651be`.
- `W57B-INT-CATALOGUE-DB-S3-ACCEPT-01`, completed at source
  `ab956e94e0c150498d9e0b8140f8a5335569b9cb`.
- `W57B-INT-TEXT-PAGE-BRIDGE-01`, completed at source
  `6ebecf347348a212a2fa9c8c9f5c16e7fe9e5546`.

## Frozen inputs

- base commit: `2b0a8a04a7ef2ce050e3ec3df9dd5414c68651be`
- catalogue test source parent `85d9936a8faacc00df3687b32ba51797439f2736`;
- text-page source parent `2b0a8a04a7ef2ce050e3ec3df9dd5414c68651be`;
- API SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- error catalogue SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations`, `VERSION=0.6.0`;
- `origin/main` and `v0.6.0` `37393a979a430e490843d7f410e9eca9491a4ea1`;
- R-135 focused checks for intermediate dev candidates.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: W57b catalogue reader checks snapshot document count;
  text-page bridge checks one ordered page per independently supplied Version
  count. Neither changes an enumerator.

## Captured premise evidence

- premise: the source commits are additive and disjoint; `CURRENT_STATE.md`
  still describes W57b catalogue custody as fake-port only.

### P-01 — source paths and live prose

- captured_at: 2026-10-16
- command: `git show --format= --name-only ab956e94e0c150498d9e0b8140f8a5335569b9cb; git show --format= --name-only 6ebecf347348a212a2fa9c8c9f5c16e7fe9e5546; rg -n 'fake ports|Real catalogue DB/S3' docs/program/CURRENT_STATE.md`
- captured_output:
  ```text
  docs/program/W57B-INT-CATALOGUE-DB-S3-ACCEPT-01.md
  docs/program/tasks/W57B-INT-CATALOGUE-DB-S3-ACCEPT-01.md
  tests/integration/norms/references/test_catalogue_input_db_s3_accept.py
  docs/program/W57B-INT-TEXT-PAGE-BRIDGE-01.md
  docs/program/tasks/W57B-INT-TEXT-PAGE-BRIDGE-01.md
  src/auditmanager/norms/references/text_pages.py
  tests/integration/norms/references/test_text_pages.py
  catalogue custody reader checked with fake ports
  Real catalogue DB/S3 custody and served callers
  ```
- interpretation: seven source paths plus state and this integration pair;
  the state needs a narrow evidence-backed correction.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W57B-INT-CATALOGUE-DB-S3-ACCEPT-01.md`
- `docs/program/tasks/W57B-INT-CATALOGUE-DB-S3-ACCEPT-01.md`
- `tests/integration/norms/references/test_catalogue_input_db_s3_accept.py`
- `docs/program/W57B-INT-TEXT-PAGE-BRIDGE-01.md`
- `docs/program/tasks/W57B-INT-TEXT-PAGE-BRIDGE-01.md`
- `src/auditmanager/norms/references/text_pages.py`
- `tests/integration/norms/references/test_text_pages.py`
- `docs/program/CURRENT_STATE.md`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-60.md`
- `docs/program/CFB-INT-DEV-PUBLISH-60.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/lockfiles, composition root,
global styles, W54/W56/W58/W59 source, production corpus/DB/S3,
credentials, deployment workflow, `origin/main` and tags.

## Non-goals

No served W57b stage/route, rule publication, 0024 seal, qualified W54
corpus, full beta gate or deployment.

## Deliverables

Two scoped cherry-picks, state refresh, this task/report, focused checks,
exact-path handoff, dev fast-forward and remote readback.

## Required tests

- Catalogue source's targeted real 0023 PostgreSQL/S3 test: one pass on its
  isolated instance, with cleanup, as recorded in source report.
- Combined offline catalogue, text-page, reference-pipeline, governance and
  documentation fact checks: pass.
- Python compilation, frozen API hash, exact ten-path diff, whitespace,
  clean-tree technical handoff: pass.
- Fresh remote refs, fast-forward proof, exact-SHA dev push and readback.
  No intermediate full beta gate under R-135.

## Integration contract

The new real-service test proves the existing unserved catalogue reader's
SQL/S3 custody and Attempt fencing on synthetic data. The pure bridge maps
an independently Version-bound `TextLayer` to `ReferencePage` with exact
Unicode offsets and empty-page marking. Future callers still own artifact
custody, authorization, reviewed unparsed slugs and publication authority.

## Failure/idempotency/security cases

Stop on moved dev, dirty tree, path expansion or failed check. No force push,
credential or private payload enters Git. The source test rolls back rows and
removes its temporary bucket. Repeating the published SHA is a no-op.

## Rollback / feature flag

Additive test and unserved mapper; correct with reviewed forward commit.
No data rollback or runtime flag is needed.

## Handoff

- changed files: ten exact allowed paths;
- contracts: none;
- checks and limits: paired report;
- forbidden hotspots untouched.
