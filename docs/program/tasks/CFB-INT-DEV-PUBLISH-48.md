# Task CFB-INT-DEV-PUBLISH-48 — integrate saved OCR region read

task_id: CFB-INT-DEV-PUBLISH-48

## Outcome

Publish a clean development candidate with the completed W56b read-only
Run/Attempt-fenced recognised-region evidence service. Read back the exact
`origin/dev` SHA after a fast-forward push.

## Depends on

- `CFB-INT-DEV-PUBLISH-47`, completed at `394a728f8a6f64ecb849f98fccdad687b79f282a`.
- `W56B-INT-RUN-RECOGNISED-REGION-READ-01`, completed at source
  `ca1696fe16f51ebd9c754f90ecaaf920797a3c24`.

## Frozen inputs

- base commit: `394a728f8a6f64ecb849f98fccdad687b79f282a`;
- W56b source parent: `95de4f6b4e10a8b60f57ae84ab66156917c7b96c`;
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- development API 48 paths / 55 operations / 131 schemas, errors 25,
  migration head `0023_norm_citations`, `VERSION=0.6.0`;
- `origin/main` and `v0.6.0`: `37393a979a430e490843d7f410e9eca9491a4ea1`;
- R-135: focused checks on intermediate dev candidates, final complete beta
  gate later.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the finished W56b source and intervening W54/W57b integration have
  disjoint paths, so the W56b commit can be reviewed as a scoped cherry-pick.

### P-01 — source paths

- captured_at: 2026-10-16
- command: `git -C /root/projects/PDF-Analysis/.local/worktrees/w56b-run-recognised-region-read-01 show --format= --name-only ca1696fe16f51ebd9c754f90ecaaf920797a3c24`
- captured_output:
  ```text
  docs/program/W56B-INT-RUN-RECOGNISED-REGION-READ-01.md
  docs/program/tasks/W56B-INT-RUN-RECOGNISED-REGION-READ-01.md
  src/auditmanager/analysis/public.py
  src/auditmanager/runs/recognised_region_input.py
  tests/integration/runs/test_recognised_region_input.py
  ```
- interpretation: exactly five W56b source paths; no shared contract,
  migration, composition root or deployed W55b tree.

### P-02 — intervening dev47 paths

- captured_at: 2026-10-16
- command: `git diff --name-only 95de4f6b4e10a8b60f57ae84ab66156917c7b96c..394a728f8a6f64ecb849f98fccdad687b79f282a`
- captured_output:
  ```text
  docs/program/CFB-INT-DEV-PUBLISH-47.md
  docs/program/W54-BUNDLE-DROP-CROP-COVERAGE-01.md
  docs/program/W57B-INT-XLSX-CERTIFIED-SOURCES-PREP-01.md
  docs/program/tasks/CFB-INT-DEV-PUBLISH-47.md
  docs/program/tasks/W54-BUNDLE-DROP-CROP-COVERAGE-01.md
  docs/program/tasks/W57B-INT-XLSX-CERTIFIED-SOURCES-PREP-01.md
  src/auditmanager/exports/xlsx/certified_sources.py
  src/auditmanager/norms/bundle/export.py
  tests/integration/exports/test_xlsx_certified_sources.py
  tests/integration/norms/bundle/test_export_offline.py
  ```
- interpretation: dev47 does not touch any W56b source path.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W56B-INT-RUN-RECOGNISED-REGION-READ-01.md`
- `docs/program/tasks/W56B-INT-RUN-RECOGNISED-REGION-READ-01.md`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/runs/recognised_region_input.py`
- `tests/integration/runs/test_recognised_region_input.py`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-48.md`
- `docs/program/CFB-INT-DEV-PUBLISH-48.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, stage registry, provider/rate adapters, API/UI, W54/W57/W58
paths, production DB/S3, credentials, deployment workflow, `origin/main`
and tags.

## Non-goals

No W56b citation policy, provider call, finding write, served route,
real DB/S3 acceptance, corpus publication, complete beta gate or deployment.

## Deliverables

One scoped cherry-pick, this task/report, focused W56b/architecture checks,
exact-path handoff, dev fast-forward and remote readback.

## Required tests

- Saved OCR region, pure region binder and analogous TEXT/crop read suites;
  architecture and task governance: pass.
- Python compilation, frozen API hash, exact seven-path diff, whitespace,
  clean tree and `scripts/task_handoff.py` with explicit check argv: pass.
- Fresh remote dev/main/tag read, fast-forward proof, exact-SHA dev push and
  readback. No intermediate full beta gate under R-135.

## Integration contract

The service is unserved and read-only. The future caller owns its transaction,
passes current Attempt authority and an explicit aggregate byte ceiling,
and must repeat authorization before any effect. The service validates saved
Run, Version, source and geometry StageResults and the two Blob documents
before returning an OCR-region candidate. Only this task advances `origin/dev`.

## Failure/idempotency/security cases

Stop on moved dev, dirty tree, path expansion or failed check. Stale Attempt,
changed provenance, malformed or oversized saved evidence must refuse with
no partial candidate. No force push, credential or private corpus payload
enters Git. Repeating the exact published SHA is a no-op.

## Rollback / feature flag

Unserved additive code; correct with a reviewed forward commit. No data
rollback or runtime flag is needed.

## Handoff

- changed files: seven exact allowed paths;
- contracts: no public product contract changes;
- checks and limits: paired report;
- forbidden hotspots untouched.
