# Task CFB-INT-DEV-PUBLISH-61 — saved reference text and XLSX probe evidence

task_id: CFB-INT-DEV-PUBLISH-61

## Outcome

Publish a clean development candidate with W57b's current-Attempt saved PDF
text reader and the immutable addendum proving the independent synthetic
LibreOffice XLSX probe passes outside sandbox. Refresh the first-read state
and read back the exact `origin/dev` SHA.

## Depends on

- `CFB-INT-DEV-PUBLISH-60`, completed at
  `2fe82f40f4ac2bf82f9778c28b2fd2a2b8e8deab`.
- `W57B-INT-SAVED-TEXT-SOURCE-01`, completed at source
  `f581e7fc78e4235d0a936e0ee2f09a3bb5a0db93`.
- `W57B-INT-XLSX-SOFFICE-UNSANDBOXED-ACCEPT-01`, completed at source
  `233c6e9cf570e1949f0d5bb9be4b6a6b59e97604`.

## Frozen inputs

- base commit: `2fe82f40f4ac2bf82f9778c28b2fd2a2b8e8deab`
- both source parents are this exact base;
- API SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- error catalogue SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- XLSX probe SHA-256 `b5800e371fea6c51a2d8912837f4ba451b5ede49d250530de4dc769eb79472f9`;
- XLSX opt-in test SHA-256 `b35d28f22ba5318a3ae79fa5fd91707ca7c15c22b0dd9ef2dbbb4654a55acb69`;
- migration head `0023_norm_citations`, `VERSION=0.6.0`;
- `origin/main` and `v0.6.0` `37393a979a430e490843d7f410e9eca9491a4ea1`;
- R-135 focused checks for intermediate dev candidates.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: the saved text reader checks every page against the
  independently loaded Version count; no enumerator changes.

## Captured premise evidence

- premise: the six-path saved-text source and two-path LibreOffice addendum
  are disjoint; the latter leaves the original failed observation unchanged.

### P-01 — source paths

- captured_at: 2026-10-16
- command: `git show --format= --name-only f581e7fc78e4235d0a936e0ee2f09a3bb5a0db93; git show --format= --name-only 233c6e9cf570e1949f0d5bb9be4b6a6b59e97604`
- captured_output:
  ```text
  docs/program/W57B-INT-SAVED-TEXT-SOURCE-01.md
  docs/program/tasks/W57B-INT-SAVED-TEXT-SOURCE-01.md
  src/auditmanager/analysis/public.py
  src/auditmanager/analysis/text/source_bytes.py
  src/auditmanager/runs/reference_text_input.py
  tests/integration/runs/test_reference_text_input_offline.py
  docs/program/W57B-INT-XLSX-SOFFICE-UNSANDBOXED-ACCEPT-01.md
  docs/program/tasks/W57B-INT-XLSX-SOFFICE-UNSANDBOXED-ACCEPT-01.md
  ```
- interpretation: exactly eight source paths, no public contract, migration,
  dependency, composition root or deployed W55b tree.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W57B-INT-SAVED-TEXT-SOURCE-01.md`
- `docs/program/tasks/W57B-INT-SAVED-TEXT-SOURCE-01.md`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/analysis/text/source_bytes.py`
- `src/auditmanager/runs/reference_text_input.py`
- `tests/integration/runs/test_reference_text_input_offline.py`
- `docs/program/W57B-INT-XLSX-SOFFICE-UNSANDBOXED-ACCEPT-01.md`
- `docs/program/tasks/W57B-INT-XLSX-SOFFICE-UNSANDBOXED-ACCEPT-01.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-61.md`
- `docs/program/CFB-INT-DEV-PUBLISH-61.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/lockfiles, composition root,
global styles, W54/W56/W58/W59 source, production corpus/DB/S3,
credentials, XLSX script/test and original failure report, deployment
workflow, `origin/main` and tags.

## Non-goals

No served W57b stage/route, rule publication, 0024 seal, qualified W54
corpus, full B3.5 acceptance, full beta gate or deployment.

## Deliverables

Two scoped cherry-picks, state refresh, this task/report, focused checks,
exact-path handoff, dev fast-forward and remote readback.

## Required tests

- Source saved-text W57b/W56b focused suites: pass on combined tree.
- Source unchanged opt-in real LibreOffice test outside sandbox: one pass,
  with original three constrained failures retained as historical evidence.
- Combined offline XLSX probe, governance and documentation fact checks:
  pass.
- Python compilation, frozen API and probe/test hashes, exact eleven-path
  diff, whitespace and clean-tree technical handoff: pass.
- Fresh remote refs, fast-forward proof, exact-SHA dev push and readback.
  No intermediate full beta gate under R-135.

## Integration contract

The W57b reader reuses factored strict canonical text-layer byte validation
and leaves W56b window partitioning intact. A caller supplies a current
Attempt, transaction, Version and explicit byte cap, then passes the returned
TextLayer to the pure page bridge. The addendum closes only the independent
synthetic LibreOffice import/cell probe; live export, role and corpus custody
under B3.5 remain open.

## Failure/idempotency/security cases

Stop on moved dev, dirty tree, path expansion or failed check. The reader
refuses stale Attempt, changed Run/Version/stage or mismatched Blob bytes
without fallback. No force push, credential or private payload enters Git.
Repeating the published SHA is a no-op.

## Rollback / feature flag

Unserved reader and evidence addendum; correct with reviewed forward commit.
No data rollback or runtime flag is needed.

## Handoff

- changed files: eleven exact allowed paths;
- contracts: none;
- checks and limits: paired report;
- forbidden hotspots untouched.
