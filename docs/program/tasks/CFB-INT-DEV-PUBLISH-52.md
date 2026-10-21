# Task CFB-INT-DEV-PUBLISH-52 — verify W54 imported PDF slots

task_id: CFB-INT-DEV-PUBLISH-52

## Outcome

Publish a clean development candidate whose W54 bundle importer refuses
missing, wrong or extra PDF custody anchors before DB/S3 access. Read back
the exact `origin/dev` SHA after a fast-forward push.

## Depends on

- `CFB-INT-DEV-PUBLISH-51`, completed at `ef802c112cd2b61de5ee9aa701739b04eb2d7f36`.
- `W54-BUNDLE-PDF-SLOT-VERIFY-01`, completed at source
  `281cf44918a5f1349a2d8aaa9dd04a45cb46264e`.

## Frozen inputs

- base commit: `ef802c112cd2b61de5ee9aa701739b04eb2d7f36`
- W54 source parent `ee70edaa56c30255558873cb9f0a777daa11ee58`;
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

- premise: the completed W54 importer source changes four paths, disjoint
  from the W56b source-digest integration after its dev50 parent.

### P-01 — source paths

- captured_at: 2026-10-16
- command: `git -C /root/projects/PDF-Analysis/.local/worktrees/w54-bundle-pdf-slot-01 show --format= --name-only 281cf44918a5f1349a2d8aaa9dd04a45cb46264e`
- captured_output:
  ```text
  docs/program/W54-BUNDLE-PDF-SLOT-VERIFY-01.md
  docs/program/tasks/W54-BUNDLE-PDF-SLOT-VERIFY-01.md
  src/auditmanager/norms/bundle/stand.py
  tests/integration/norms/bundle/test_import_refusals_offline.py
  ```
- interpretation: only W54 offline bundle importer, its test and paired
  documents; no shared contract, migration, composition root or deployed
  W55b tree.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W54-BUNDLE-PDF-SLOT-VERIFY-01.md`
- `docs/program/tasks/W54-BUNDLE-PDF-SLOT-VERIFY-01.md`
- `src/auditmanager/norms/bundle/stand.py`
- `tests/integration/norms/bundle/test_import_refusals_offline.py`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-52.md`
- `docs/program/CFB-INT-DEV-PUBLISH-52.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, W56/W57/W58 paths, original corpus and sums, production
DB/S3, credentials, deployment workflow, `origin/main` and tags.

## Non-goals

No new bundle field or manifest format, source PDF byte provenance proof,
paid repair, real bundle export/import, DB/S3 publication, complete beta
gate or deployment.

## Deliverables

One scoped cherry-pick, this task/report, bounded W54 offline checks,
exact-path handoff, dev fast-forward and remote readback.

## Required tests

- Focused importer refusal and bounded offline bundle suites: pass.
- Python compilation, frozen API hash, exact six-path diff, whitespace,
  clean tree and explicit-argv technical handoff: pass.
- Fresh remote dev/main/tag read, fast-forward proof, exact-SHA dev push and
  readback. No intermediate full beta gate under R-135.

## Integration contract

After verified bundle and row reads but before DB/S3, each document row
requires exactly its own PDF custody slot `(norm_document_id,
source_document_ref)`. The existing manifest guard already forbids duplicate
identical slots; this check rejects missing, wrong and extra anchors. Only
this task advances `origin/dev`.

## Failure/idempotency/security cases

Stop on moved dev, dirty tree, path expansion or failed check. Re-signed
malformed bundles refuse before storage side effects. No force push,
credential or private payload enters Git. Repeating the exact published SHA
is a no-op.

## Rollback / feature flag

Offline importer guard; correct with a reviewed forward commit. No data
rollback or runtime flag is needed.

## Handoff

- changed files: six exact allowed paths;
- contracts: none;
- checks and limitations: paired report;
- forbidden hotspots untouched.
