# Task CFB-INT-DEV-PUBLISH-57 — verify W54 build before custody

task_id: CFB-INT-DEV-PUBLISH-57

## Outcome

Publish a clean development candidate whose W54 bundle importer streams
the complete embedding build and checks its digest/counts before DB/S3
custody. Read back the exact `origin/dev` SHA after a fast-forward push.

## Depends on

- `CFB-INT-STATE-56`, completed at `1b2da15da657c6eade0b87739478bde0e5001e94`.
- `W54-BUNDLE-BUILD-PREFLIGHT-01`, completed at source
  `58a7ab6f6170cab89f6d92fb3bb6cd8243cfc4d5`.

## Frozen inputs

- base commit: `1b2da15da657c6eade0b87739478bde0e5001e94`
- W54 source parent `100307cecc47056005d79e388b2dde1a8e4c99ed`;
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

- premise: completed W54 source changes four importer/test/docs paths;
  intervening dev55 and state56 touch only W57b and state documentation.

### P-01 — source paths

- captured_at: 2026-10-16
- command: `git -C /root/projects/PDF-Analysis/.local/worktrees/w54-build-ingress-dev54 show --format= --name-only 58a7ab6f6170cab89f6d92fb3bb6cd8243cfc4d5`
- captured_output:
  ```text
  docs/program/W54-BUNDLE-BUILD-PREFLIGHT-01.md
  docs/program/tasks/W54-BUNDLE-BUILD-PREFLIGHT-01.md
  src/auditmanager/norms/bundle/stand.py
  tests/integration/norms/bundle/test_import_refusals_offline.py
  ```
- interpretation: W54 importer/test and paired documents only; no shared
  contract, migration, composition root or deployed W55b tree.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W54-BUNDLE-BUILD-PREFLIGHT-01.md`
- `docs/program/tasks/W54-BUNDLE-BUILD-PREFLIGHT-01.md`
- `src/auditmanager/norms/bundle/stand.py`
- `tests/integration/norms/bundle/test_import_refusals_offline.py`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-57.md`
- `docs/program/CFB-INT-DEV-PUBLISH-57.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/lockfiles, composition root,
global styles, W56/W57/W58 paths, source corpus/sums, production DB/S3,
credentials, deployment workflow, `origin/main` and tags.

## Non-goals

No paid repair, real bundle import, DB/S3 corpus publication, full beta
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

Before any DB/S3 operation, the importer streams the verified build through
existing chunk/vector readers, checks document refs, canonical order,
vector units, chunk/window counts and embedding-set digest. The existing
transactional `ensure_build` and readback remain. No full build buffer is
introduced. Only this task advances `origin/dev`.

## Failure/idempotency/security cases

Stop on moved dev, dirty tree, path expansion or failed check. Re-signed
invalid vector or divergent digest refuses before custody effects. No force
push, credential or private payload enters Git. Repeating the exact
published SHA is a no-op.

## Rollback / feature flag

Offline importer guard; correct with a reviewed forward commit. No data
rollback or runtime flag is needed.

## Handoff

- changed files: six exact allowed paths;
- contracts: none;
- checks and limits: paired report;
- forbidden hotspots untouched.
