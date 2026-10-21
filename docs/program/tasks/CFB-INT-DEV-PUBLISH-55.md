# Task CFB-INT-DEV-PUBLISH-55 — compose certified W57b XLSX sources

task_id: CFB-INT-DEV-PUBLISH-55

## Outcome

Publish a clean development candidate with the completed unserved W57b
certified XLSX composition use case. Read back the exact `origin/dev` SHA
after a fast-forward push.

## Depends on

- `CFB-INT-DEV-PUBLISH-54`, completed at `100307cecc47056005d79e388b2dde1a8e4c99ed`.
- `W57B-INT-CERTIFIED-EXPORT-CHAIN-PREP-01`, completed at source
  `1adf7a6a1ad20048b15e154a3dd79d88685e555a`.

## Frozen inputs

- base commit: `100307cecc47056005d79e388b2dde1a8e4c99ed`
- W57b source parent `110d632343b35d77b9d55a5c8ae453bbeca14ef5`;
- API SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- `origin/main` and `v0.6.0` `37393a979a430e490843d7f410e9eca9491a4ea1`;
- development API 48 paths / 55 operations / 131 schemas, errors 25,
  migration head `0023_norm_citations`, `VERSION=0.6.0`;
- R-135 focused checks for intermediate dev candidates; W57b B3.5 remains
  failed/unverified on the current host.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the completed W57b source adds a new use-case module/test and
  paired documents; dev54 changed only W54 importer and fixture paths.

### P-01 — source paths

- captured_at: 2026-10-16
- command: `git -C /root/projects/PDF-Analysis/.local/worktrees/w57b-certified-export-chain-dev53 show --format= --name-only 1adf7a6a1ad20048b15e154a3dd79d88685e555a`
- captured_output:
  ```text
  docs/program/W57B-INT-CERTIFIED-EXPORT-CHAIN-PREP-01.md
  docs/program/tasks/W57B-INT-CERTIFIED-EXPORT-CHAIN-PREP-01.md
  src/auditmanager/exports/xlsx/certified_package.py
  tests/integration/exports/test_xlsx_certified_package.py
  ```
- interpretation: no shared contract, migration, composition root, existing
  XLSX writer or deployed W55b tree is edited.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W57B-INT-CERTIFIED-EXPORT-CHAIN-PREP-01.md`
- `docs/program/tasks/W57B-INT-CERTIFIED-EXPORT-CHAIN-PREP-01.md`
- `src/auditmanager/exports/xlsx/certified_package.py`
- `tests/integration/exports/test_xlsx_certified_package.py`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-55.md`
- `docs/program/CFB-INT-DEV-PUBLISH-55.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, existing XLSX writer/package/preflight/source adapters,
findings internals, W54/W56/W58 paths, corpus and production DB/S3,
credentials, deployment workflow, `origin/main` and tags.

## Non-goals

No 0024 seal, XLSX route/role, real authorization decision, qualified
corpus, B3.5 PASS, complete beta gate or deployment.

## Deliverables

One scoped cherry-pick, this task/report, focused W57b composition checks,
exact-path handoff, dev fast-forward and remote readback.

## Required tests

- New composition, certified sources, XLSX package and programme
  governance suites: pass.
- Python compilation, frozen API hash, exact six-path diff, whitespace,
  clean tree and explicit-argv technical handoff: pass.
- Fresh remote dev/main/tag read, fast-forward proof, exact-SHA dev push and
  readback. No intermediate full beta gate under R-135.

## Integration contract

The future authorized caller owns one consistent read transaction, v3
profile identity, Blob reader and findings-public citation callback. The
unserved use case checks the persisted Run/profile/snapshot/set identity
before and after composing verified page and citation sources into XLSX
bytes. It does not grant a role, open a transaction or store output. Only
this task advances `origin/dev`.

## Failure/idempotency/security cases

Stop on moved dev, dirty tree, path expansion or failed check. Denied or
foreign authorization, inconsistent pins, missing citation partition and
changed Run refuse without output. No force push, credential or private
payload enters Git. Repeating the exact published SHA is a no-op.

## Rollback / feature flag

Unserved additive use case; correct with a reviewed forward commit. No data
rollback or runtime flag is needed.

## Handoff

- changed files: six exact allowed paths;
- contracts: none;
- checks and limits: paired report;
- forbidden hotspots untouched.
