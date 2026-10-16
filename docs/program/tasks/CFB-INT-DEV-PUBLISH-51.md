# Task CFB-INT-DEV-PUBLISH-51 — bind W56b OCR digests to Version manifest

task_id: CFB-INT-DEV-PUBLISH-51

## Outcome

Publish a clean development candidate whose unserved W56b OCR-region reader
checks saved source digests against the exact Version manifest. Read back the
exact `origin/dev` SHA after a fast-forward push.

## Depends on

- `CFB-INT-DEV-PUBLISH-50`, completed at `ee70edaa56c30255558873cb9f0a777daa11ee58`.
- `W56B-INT-PORTAL-MANIFEST-DIGEST-01`, completed at source
  `adf43d6adb76c687e964062dc000087755ca74e4`.

## Frozen inputs

- base commit: `ee70edaa56c30255558873cb9f0a777daa11ee58`
- W56b source parent `3a7c558a862d975f5305f6c54b15c6dfa5e9dca6`;
- API SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
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

- premise: the completed W56b source has four paths, disjoint from the
  intervening state and W54 bundle changes after its dev48 parent.

### P-01 — source paths

- captured_at: 2026-10-16
- command: `git -C /root/projects/PDF-Analysis/.local/worktrees/w56b-portal-manifest-digest-01 show --format= --name-only adf43d6adb76c687e964062dc000087755ca74e4`
- captured_output:
  ```text
  docs/program/W56B-INT-PORTAL-MANIFEST-DIGEST-01.md
  docs/program/tasks/W56B-INT-PORTAL-MANIFEST-DIGEST-01.md
  src/auditmanager/runs/recognised_region_input.py
  tests/integration/runs/test_recognised_region_input.py
  ```
- interpretation: only W56b saved reader, its test and paired documents;
  no shared contract, migration, composition root or deployed W55b tree.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W56B-INT-PORTAL-MANIFEST-DIGEST-01.md`
- `docs/program/tasks/W56B-INT-PORTAL-MANIFEST-DIGEST-01.md`
- `src/auditmanager/runs/recognised_region_input.py`
- `tests/integration/runs/test_recognised_region_input.py`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-51.md`
- `docs/program/CFB-INT-DEV-PUBLISH-51.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, W54/W57/W58 paths, producer modules, jobs/storage/documents
adapters, provider/rate adapters, API/UI, production DB/S3, credentials,
deployment workflow, `origin/main` and tags.

## Non-goals

No original portal Blob reread, provider/citation/cost policy, finding write,
served route, real DB/S3 acceptance, corpus publication, complete beta gate
or deployment.

## Deliverables

One scoped cherry-pick, this task/report, focused W56b checks, exact-path
handoff, dev fast-forward and remote readback.

## Required tests

- Saved OCR region, pure OCR candidate and programme governance suites: pass.
- Python compilation, frozen API hash, exact six-path diff, whitespace,
  clean tree and explicit-argv technical handoff: pass.
- Fresh remote dev/main/tag read, fast-forward proof, exact-SHA dev push and
  readback. No intermediate full beta gate under R-135.

## Integration contract

The unserved reader requires one markdown and one structured companion
manifest entry with valid roles, media types, SHA-256 and positive size.
After checking the two saved derived Blobs, it compares their inner source
digests to those entries and retains the second Attempt/Run/Version/stage
fence. Matching identity does not prove original Blob availability. Only
this task advances `origin/dev`.

## Failure/idempotency/security cases

Stop on moved dev, dirty tree, path expansion or failed check. Missing,
duplicate or malformed source entries, mismatched digests and changed
Version refuse without a candidate. No force push, credential or private
payload enters Git. Repeating the exact published SHA is a no-op.

## Rollback / feature flag

Unserved additive reader guard; correct with a reviewed forward commit. No
data rollback or runtime flag is needed.

## Handoff

- changed files: six exact allowed paths;
- contracts: none;
- checks and limitations: paired report;
- forbidden hotspots untouched.
