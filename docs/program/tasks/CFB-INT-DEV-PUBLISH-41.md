# Task CFB-INT-DEV-PUBLISH-41 — publish W54 checksum and W56b cohort slices

task_id: CFB-INT-DEV-PUBLISH-41

## Outcome

Fast-forward `origin/dev` from the v0.6.0 evidence record to a clean candidate
containing the reviewed W54 offline checksum guard and W56b unserved TEXT
window reply cohort binder. Read back the exact remote SHA.

## Depends on

- `W55B-INT-TAG-01`, completed at `72fa7f69afc93890b9e0c50fb1b4ccd66ee810e8`.
- `W54-CORPUS-SUMS-BINDING-01`, completed at source `503428cfc3cd8adacda43ab0af4c4dd170ccebaa`.
- `W56B-INT-WINDOW-COHORT-PREP-01`, completed at source `4c2a8b24f830489a75a7a29baca3aac96927b967`.

## Frozen inputs

- base commit: `72fa7f69afc93890b9e0c50fb1b4ccd66ee810e8`
- W54 source commit: `503428cfc3cd8adacda43ab0af4c4dd170ccebaa`;
- W56b source commit: `4c2a8b24f830489a75a7a29baca3aac96927b967`;
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- API 48 paths / 55 operations / 131 schemas, errors 25, migration head `0023_norm_citations`;
- `origin/main` and `v0.6.0` target: `37393a979a430e490843d7f410e9eca9491a4ea1`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the candidate adds only the two checked slices on top of the published development base.

### P-01 — exact integration paths before this task/report

- captured_at: 2026-10-16
- command: `git diff 72fa7f69afc93890b9e0c50fb1b4ccd66ee810e8..HEAD --name-only`
- captured_output:
  ```text
  docs/program/W54-CORPUS-SUMS-BINDING-01.md
  docs/program/W56B-INT-WINDOW-COHORT-PREP-01.md
  docs/program/tasks/W54-CORPUS-SUMS-BINDING-01.md
  docs/program/tasks/W56B-INT-WINDOW-COHORT-PREP-01.md
  scripts/norms/corpus_preflight.py
  src/auditmanager/analysis/text/window_anchor.py
  src/auditmanager/analysis/text/window_cohort.py
  tests/integration/analysis_text/test_window_cohort.py
  tests/integration/norms/test_corpus_preflight.py
  ```
- interpretation: the source cherry-picks fit their respective allowlists; this task adds only its own two records.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W54-CORPUS-SUMS-BINDING-01.md`
- `docs/program/W56B-INT-WINDOW-COHORT-PREP-01.md`
- `docs/program/tasks/W54-CORPUS-SUMS-BINDING-01.md`
- `docs/program/tasks/W56B-INT-WINDOW-COHORT-PREP-01.md`
- `scripts/norms/corpus_preflight.py`
- `src/auditmanager/analysis/text/window_anchor.py`
- `src/auditmanager/analysis/text/window_cohort.py`
- `tests/integration/analysis_text/test_window_cohort.py`
- `tests/integration/norms/test_corpus_preflight.py`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-41.md`
- `docs/program/CFB-INT-DEV-PUBLISH-41.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, served routes, worker/provider wiring, original source corpus,
promotion DB/S3, credentials, deployment workflow, `origin/main` and tags.

## Non-goals

No paid repair, corpus rehash/import, authenticated provider reply, W56b
policy freeze, route activation, beta acceptance or main deployment.

## Deliverables

Two clean cherry-picks, this task/report, combined focused and governance
checks, exact changed-path handoff, dev fast-forward and remote readback.

## Required tests

- Combined `tests/integration/norms/test_corpus_preflight.py`, W56b cohort,
  window anchor, chunk preflight and governance suites: pass.
- Frozen API SHA, exact changed paths, `git diff --check` and clean tree.
- `.venv/bin/python scripts/task_handoff.py --task docs/program/tasks/CFB-INT-DEV-PUBLISH-41.md --worktree .` with explicit check argv.
- Fresh remote dev/main/tag read, fast-forward proof, exact-SHA dev push and
  readback. R-135 defers the complete beta gate for these unserved slices.

## Integration contract

Only this integration task advances `origin/dev`. The W54 guard checks the
listing digest during cheap offline preflight; it does not rehash source
files. The W56b binder accepts supplied claims only; a future caller must
prove provider reply and Run/Attempt provenance before using them as
evidence. Neither slice changes the deployed v0.6.0 tree.

## Failure/idempotency/security cases

If dev moves, the candidate is dirty, a forbidden path changes or focused
checks fail, stop. Never force-push. No source document text or credentials
enter the report. Repeating the exact already-published SHA is a no-op.

## Rollback / feature flag

Both changes are offline or unserved. Correct through a forward commit;
no runtime flag or data rollback is required.

## Handoff

- changed files: exact eleven allowed paths;
- contracts: unchanged;
- checks: combined focused and governance, path/whitespace/handoff;
- limits: no source-byte verification, provider authentication or beta gate;
- forbidden hotspots: untouched.
