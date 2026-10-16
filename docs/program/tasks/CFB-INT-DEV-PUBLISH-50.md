# Task CFB-INT-DEV-PUBLISH-50 — verify duplicate W54 source paths

task_id: CFB-INT-DEV-PUBLISH-50

## Outcome

Publish a clean development candidate whose W54 bundle exporter verifies
each named source path before granting a custody slot for a deduplicated
object. Read back the exact `origin/dev` SHA after a fast-forward push.

## Depends on

- `CFB-INT-STATE-49`, completed at `04ffe00ee9fa81dac1f1009ebd0c674307d975bd`.
- `W54-BUNDLE-DUPLICATE-SOURCE-VERIFY-01`, completed at source
  `3b28e265e988f20a82ac02fc62e45c7575ecf3ab`.

## Frozen inputs

- base commit: `04ffe00ee9fa81dac1f1009ebd0c674307d975bd`
- W54 source parent `394a728f8a6f64ecb849f98fccdad687b79f282a`;
- API SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- W54 source listing SHA-256 `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`;
- `origin/main` and `v0.6.0` `37393a979a430e490843d7f410e9eca9491a4ea1`;
- development API 48 paths / 55 operations / 131 schemas, errors 25,
  migration head `0023_norm_citations`, `VERSION=0.6.0`;
- R-135 focused checks for intermediate dev candidates.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the completed source commit changes four W54 paths and the
  intervening dev48/state49 candidates change W56b/documentation paths.

### P-01 — source paths

- captured_at: 2026-10-16
- command: `git -C /root/projects/PDF-Analysis/.local/worktrees/w54-bundle-duplicate-source-01 show --format= --name-only 3b28e265e988f20a82ac02fc62e45c7575ecf3ab`
- captured_output:
  ```text
  docs/program/W54-BUNDLE-DUPLICATE-SOURCE-VERIFY-01.md
  docs/program/tasks/W54-BUNDLE-DUPLICATE-SOURCE-VERIFY-01.md
  src/auditmanager/norms/bundle/export.py
  tests/integration/norms/bundle/test_export_offline.py
  ```
- interpretation: source code and tests are the existing W54 exporter only;
  no shared contract, migration, composition root or deployed W55b tree.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W54-BUNDLE-DUPLICATE-SOURCE-VERIFY-01.md`
- `docs/program/tasks/W54-BUNDLE-DUPLICATE-SOURCE-VERIFY-01.md`
- `src/auditmanager/norms/bundle/export.py`
- `tests/integration/norms/bundle/test_export_offline.py`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-50.md`
- `docs/program/CFB-INT-DEV-PUBLISH-50.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, W56/W57/W58 paths, original corpus and checksums, production
DB/S3, credentials, deployment workflow, `origin/main` and tags.

## Non-goals

No paid repair, real bundle export, embedding build, DB/S3 corpus import,
served analysis, complete beta gate or deployment.

## Deliverables

One scoped cherry-pick, this task/report, bounded W54 bundle checks,
exact-path handoff, dev fast-forward and remote readback.

## Required tests

- Focused exporter regression and bounded offline bundle suite: pass.
- Python compilation, frozen API hash, exact six-path diff, whitespace,
  clean tree and explicit-argv technical handoff: pass.
- Fresh remote dev/main/tag read, fast-forward proof, exact-SHA dev push and
  readback. No intermediate full beta gate under R-135.

## Integration contract

Every repeated expected digest source path is hashed against the supplied
W54 `SHA256SUMS` before a slot is added. Equal bytes still share one object.
The operator remains responsible for complete source checksum and qualified
corpus promotion. Only this task advances `origin/dev`.

## Failure/idempotency/security cases

Stop on moved dev, dirty tree, path expansion or failed check. A missing or
changed duplicate source refuses before output publication. No force push,
credential or private corpus bytes enter Git. Repeating the exact published
SHA is a no-op.

## Rollback / feature flag

Offline exporter correction; fix forward with a reviewed commit. No data
rollback or runtime flag is needed.

## Handoff

- changed files: six exact allowed paths;
- contracts: none;
- checks and limitations: paired report;
- forbidden hotspots untouched.
