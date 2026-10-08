# W52-DEBT-CODE-125 — corpus snapshot read verification

## Result

The snapshot pass now retains each raw document fingerprint. Both
`CorpusProjection.iter_documents` (the database loader path) and `segment_corpus`
compare the bytes and source identity they re-read with that fingerprint before
segmenting or yielding a document. Changed sources raise `CorpusUnavailable`. The
loader's existing nested transaction rolls back any earlier inserts on that error.

## Changed files

- `src/auditmanager/norms/corpus_source.py` — paired snapshot/fingerprint derivation
  and check at each projection read.
- `tests/integration/norms/test_repair_projection.py` — local fixture cases for
  changed markdown, source identity, later documents and repaired/repeated reads.
- `docs/program/W52-DEBT-CODE-125.md` — this handoff.

## Checks

- `pytest -q tests/integration/norms/test_repair_projection.py` — 16 passed.
- `python -m compileall -q src/auditmanager/norms/corpus_source.py tests/integration/norms/test_repair_projection.py` — passed.
- `npm run lint` in the integration worktree's `web` directory — passed.
- `git diff --check` — passed.

No database, real-corpus, temporary-stand, QA or full-gate run was made. Those
checks remain D-139/D-140 under the owner's 2026-10-08 deferral.

## Contracts and limits

No wire, domain, migration or snapshot-ID contract changed. The internal
`CorpusProjection` value now retains the base fingerprints. A source changed after
its final read cannot alter the bytes already projected; a later source change is
detected when that document is read. The full 674-document corpus and database
SAVEPOINT were not exercised here.

## Integrator handoff

Merge the clean executor branch from the exact dispatch SHA, run the basic
governance/prose checks on the integration docs, then publish to `origin/dev`
only after exact remote-ref and fast-forward checks. Narrow D-125 to deferred
validation without claiming a full-gate result. Roll back by reverting the code
commit; no feature flag is needed.

Only the task's three allowed paths changed. Forbidden contracts, migration
head, root dependency/lock files, composition root and global styles are untouched.
