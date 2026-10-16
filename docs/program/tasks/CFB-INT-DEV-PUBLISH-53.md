# Task CFB-INT-DEV-PUBLISH-53 — publish W57b diagnostic XLSX probe

task_id: CFB-INT-DEV-PUBLISH-53

## Outcome

Publish the bounded, unserved W57b LibreOffice spreadsheet import probe as
a development diagnostic tool. Preserve the observed failure of the real
host probe and leave B3.5 unverified. Read back the exact `origin/dev` SHA
after a fast-forward push.

## Depends on

- `CFB-INT-DEV-PUBLISH-52`, completed at `eaf58965cd8bedc229f464866e3d5768b1f05797`.
- `W57B-INT-XLSX-SOFFICE-PROBE-01`, completed as a diagnostic tool at source
  `34b74ef0827da9078271ba1384e4757a8b8689f3`; its real import
  acceptance remains failed/unverified.

## Frozen inputs

- base commit: `eaf58965cd8bedc229f464866e3d5768b1f05797`
- W57b source parent `394a728f8a6f64ecb849f98fccdad687b79f282a`;
- API SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- `origin/main` and `v0.6.0` `37393a979a430e490843d7f410e9eca9491a4ea1`;
- development API 48 paths / 55 operations / 131 schemas, errors 25,
  migration head `0023_norm_citations`, `VERSION=0.6.0`;
- R-135 focused checks for intermediate dev candidates; W57b B3.5 still
  requires successful independent real spreadsheet import.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the completed W57b source adds only a standalone rehearsal
  script, its test and paired documents; the source report records three
  real LibreOffice failures and does not assert B3.5 PASS.

### P-01 — source paths

- captured_at: 2026-10-16
- command: `git -C /root/projects/PDF-Analysis/.local/worktrees/w57b-xlsx-soffice-probe show --format= --name-only 34b74ef0827da9078271ba1384e4757a8b8689f3`
- captured_output:
  ```text
  docs/program/W57B-INT-XLSX-SOFFICE-PROBE-01.md
  docs/program/tasks/W57B-INT-XLSX-SOFFICE-PROBE-01.md
  scripts/rehearsal/w57b/xlsx_soffice_probe.py
  tests/integration/exports/test_xlsx_soffice_probe.py
  ```
- interpretation: no existing product module, shared contract, migration,
  composition root or deployed W55b tree is edited.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W57B-INT-XLSX-SOFFICE-PROBE-01.md`
- `docs/program/tasks/W57B-INT-XLSX-SOFFICE-PROBE-01.md`
- `scripts/rehearsal/w57b/xlsx_soffice_probe.py`
- `tests/integration/exports/test_xlsx_soffice_probe.py`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-53.md`
- `docs/program/CFB-INT-DEV-PUBLISH-53.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, existing XLSX writer/package/source adapters, W54/W56/W58
paths, source corpus, production DB/S3, credentials, deployment workflow,
`origin/main` and tags.

## Non-goals

No B3.5 PASS, XLSX route/role, 0024 seal, qualified corpus, actual export,
complete beta gate or deployment. This diagnostic publication does not
waive the failed real LibreOffice import check.

## Deliverables

One scoped cherry-pick, this task/report, light fake-runner and governance
checks, exact-path handoff, dev fast-forward and remote readback. The three
failed real attempts remain recorded and are not rerun during integration.

## Required tests

- Focused probe fake-runner tests and programme governance: pass.
- Python compilation, frozen API hash, exact six-path diff, whitespace,
  clean tree and explicit-argv technical handoff: pass.
- Fresh remote dev/main/tag read, fast-forward proof, exact-SHA dev push and
  readback. No intermediate full beta gate under R-135.

## Integration contract

The rehearsal script is unserved and accepts local rendered bytes at most
32 MiB. It isolates LibreOffice in a temporary profile and checks worksheet
names, semantic nonempty cell values and absence of formulas with a timeout.
Any nonzero import refuses. A future W57b acceptance task must resolve the
host failure and run the real import on final export bytes. Only this task
advances `origin/dev`.

## Failure/idempotency/security cases

Stop on moved dev, dirty tree, path expansion or failed light check.
Missing binary, timeout, nonzero exit, malformed XLSX or mismatched cells
refuse. No force push, credential or private payload enters Git. Repeating
the exact published SHA is a no-op.

## Rollback / feature flag

Unserved additive diagnostic tool; correct with a reviewed forward commit.
No data rollback or runtime flag is needed.

## Handoff

- changed files: six exact allowed paths;
- contracts: none;
- real LibreOffice acceptance remains failed/unverified;
- checks and limitations: paired report;
- forbidden hotspots untouched.
