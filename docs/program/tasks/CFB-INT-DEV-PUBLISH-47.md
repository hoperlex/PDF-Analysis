# Task CFB-INT-DEV-PUBLISH-47 — integrate W54 export guard and W57b XLSX sources

task_id: CFB-INT-DEV-PUBLISH-47

## Outcome

Publish a clean development candidate that binds the W54 bundle crop index
to source checksums before staging and carries W57a certified citation
partitions into the existing W57b XLSX package input. Read back the exact
`origin/dev` SHA after a fast-forward push.

## Depends on

- `CFB-INT-DEV-PUBLISH-46`, completed at `95de4f6b4e10a8b60f57ae84ab66156917c7b96c`.
- `W54-BUNDLE-DROP-CROP-COVERAGE-01`, completed at source `b616f85a973ced27dc662f564b602f690bb292fa`.
- `W57B-INT-XLSX-CERTIFIED-SOURCES-PREP-01`, completed at corrected source `50edcd0ce9a6f1082266e0e47c54f0c700bedc2d`.

## Frozen inputs

- base commit: `95de4f6b4e10a8b60f57ae84ab66156917c7b96c`
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- development API 48 paths / 55 operations / 131 schemas, errors 25, migration head `0023_norm_citations`;
- W54 source listing SHA-256: `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`;
- `origin/main` and `v0.6.0`: `37393a979a430e490843d7f410e9eca9491a4ea1`;
- R-135: focused checks on intermediate dev candidates, final complete beta gate later.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the source commits are completed on the same exact dev46 base and
  touch disjoint W54 and W57b paths. The corrected W57b SHA supersedes its
  earlier local source SHA.

### P-01 — source task path sets

- captured_at: 2026-10-16
- command: `git -C /root/projects/PDF-Analysis/.local/worktrees/w54-bundle-crop-coverage-01 show --format= --name-only b616f85a973ced27dc662f564b602f690bb292fa; git -C /root/projects/PDF-Analysis/.local/worktrees/w57b-xlsx-certified-sources show --format= --name-only 50edcd0ce9a6f1082266e0e47c54f0c700bedc2d`
- captured_output:
  ```text
  docs/program/W54-BUNDLE-DROP-CROP-COVERAGE-01.md
  docs/program/tasks/W54-BUNDLE-DROP-CROP-COVERAGE-01.md
  src/auditmanager/norms/bundle/export.py
  tests/integration/norms/bundle/test_export_offline.py
  docs/program/W57B-INT-XLSX-CERTIFIED-SOURCES-PREP-01.md
  docs/program/tasks/W57B-INT-XLSX-CERTIFIED-SOURCES-PREP-01.md
  src/auditmanager/exports/xlsx/certified_sources.py
  tests/integration/exports/test_xlsx_certified_sources.py
  ```
- interpretation: the eight source paths do not overlap and touch no shared
  contract, migration, composition root or deployed W55b tree.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W54-BUNDLE-DROP-CROP-COVERAGE-01.md`
- `docs/program/tasks/W54-BUNDLE-DROP-CROP-COVERAGE-01.md`
- `src/auditmanager/norms/bundle/export.py`
- `tests/integration/norms/bundle/test_export_offline.py`
- `docs/program/W57B-INT-XLSX-CERTIFIED-SOURCES-PREP-01.md`
- `docs/program/tasks/W57B-INT-XLSX-CERTIFIED-SOURCES-PREP-01.md`
- `src/auditmanager/exports/xlsx/certified_sources.py`
- `tests/integration/exports/test_xlsx_certified_sources.py`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-47.md`
- `docs/program/CFB-INT-DEV-PUBLISH-47.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, stage registry, served provider/API/UI, W56b paths, original
corpus, production DB/S3, credentials, deployment workflow, `origin/main`
and tags.

## Non-goals

No paid repair, embedding build, qualified bundle or DB/S3 corpus
publication; no W57b 0024 seal, API/role/route, real corpus custody or XLSX
download; no complete beta gate, acceptance or deployment.

## Deliverables

Two scoped cherry-picks, this task/report, bounded offline W54 and W57b
checks, exact-path handoff, dev fast-forward and remote readback.

## Required tests

- W54 offline export and bounded bundle tests; W57b XLSX source/package and
  reader tests; programme governance: pass.
- Frozen API hash, exact ten-path diff, whitespace, clean tree and
  `scripts/task_handoff.py` with explicit check argv: pass.
- Fresh remote dev/main/tag read, fast-forward proof, exact-SHA dev push and
  readback. No intermediate full gate under R-135.

## Integration contract

The W54 exporter refuses a mismatched index or missing listed crop before
staging. Complete source rehash and qualified corpus promotion remain
separate. W57b uses certified citation partitions as supplied; a future
caller must prove their reader provenance, authorization and consistent
transaction. Only this task advances `origin/dev`.

## Failure/idempotency/security cases

Stop on moved dev, dirty tree, path expansion or failed check. No force push,
credential, private corpus payload or log enters Git. Repeating the exact
published SHA is a no-op.

## Rollback / feature flag

Offline export guard and unserved XLSX adapter; correct with a reviewed
forward commit. No data rollback or runtime flag is needed.

## Handoff

- changed files: ten exact allowed paths;
- contracts: no public product contract changes;
- checks and limits: paired report;
- forbidden hotspots untouched.
