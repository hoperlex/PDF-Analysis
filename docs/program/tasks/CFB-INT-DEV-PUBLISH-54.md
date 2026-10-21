# Task CFB-INT-DEV-PUBLISH-54 — validate W54 rows before custody

task_id: CFB-INT-DEV-PUBLISH-54

## Outcome

Publish a clean development candidate whose W54 importer validates complete
snapshot row semantics before DB/S3 custody operations. Read back the exact
`origin/dev` SHA after a fast-forward push.

## Depends on

- `CFB-INT-DEV-PUBLISH-53`, completed at `110d632343b35d77b9d55a5c8ae453bbeca14ef5`.
- `W54-BUNDLE-ROW-VALIDATION-INGRESS-01`, completed at source
  `2396a9e437830660ae8e3140d8e6ab4ff18a7755`.

## Frozen inputs

- base commit: `110d632343b35d77b9d55a5c8ae453bbeca14ef5`
- W54 source parent `eaf58965cd8bedc229f464866e3d5768b1f05797`;
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

- premise: completed W54 source changes its importer and offline fixture/tests;
  dev53 added only W57b diagnostic paths after the source's dev52 parent.

### P-01 — source paths

- captured_at: 2026-10-16
- command: `git -C /root/projects/PDF-Analysis/.local/worktrees/w54-row-validate-dev52 show --format= --name-only 2396a9e437830660ae8e3140d8e6ab4ff18a7755`
- captured_output:
  ```text
  docs/program/W54-BUNDLE-ROW-VALIDATION-INGRESS-01.md
  docs/program/tasks/W54-BUNDLE-ROW-VALIDATION-INGRESS-01.md
  src/auditmanager/norms/bundle/stand.py
  tests/integration/norms/bundle/support.py
  tests/integration/norms/bundle/test_import_refusals_offline.py
  ```
- interpretation: five W54 paths and no shared contract, migration,
  composition root or deployed W55b tree.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W54-BUNDLE-ROW-VALIDATION-INGRESS-01.md`
- `docs/program/tasks/W54-BUNDLE-ROW-VALIDATION-INGRESS-01.md`
- `src/auditmanager/norms/bundle/stand.py`
- `tests/integration/norms/bundle/support.py`
- `tests/integration/norms/bundle/test_import_refusals_offline.py`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-54.md`
- `docs/program/CFB-INT-DEV-PUBLISH-54.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, W56/W57/W58 paths, original corpus and sums, production
DB/S3, credentials, deployment workflow, `origin/main` and tags.

## Non-goals

No new bundle format, paid repair, real bundle import, DB/S3 corpus
publication, complete beta gate or deployment.

## Deliverables

One scoped cherry-pick, this task/report, bounded W54 offline checks,
exact-path handoff, dev fast-forward and remote readback.

## Required tests

- Focused importer refusal and bounded offline bundle suites: pass.
- Python compilation, frozen API hash, exact seven-path diff, whitespace,
  clean tree and explicit-argv technical handoff: pass.
- Fresh remote dev/main/tag read, fast-forward proof, exact-SHA dev push and
  readback. No intermediate full beta gate under R-135.

## Integration contract

The importer calls the existing `validate_snapshot_rows` after verified
rows and before the first DB/S3 action; semantic failures become internal
`bundle_rows_invalid`. Transactional validation remains. The synthetic
fixture uses a valid paragraph kind. Only this task advances `origin/dev`.

## Failure/idempotency/security cases

Stop on moved dev, dirty tree, path expansion or failed check. A re-signed
bundle with invalid row count/ordinals refuses before custody effects. No
force push, credential or private payload enters Git. Repeating the exact
published SHA is a no-op.

## Rollback / feature flag

Offline importer guard; correct with a reviewed forward commit. No data
rollback or runtime flag is needed.

## Handoff

- changed files: seven exact allowed paths;
- contracts: none;
- checks and limitations: paired report;
- forbidden hotspots untouched.
