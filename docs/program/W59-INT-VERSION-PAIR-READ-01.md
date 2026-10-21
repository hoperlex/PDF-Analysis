# W59-INT-VERSION-PAIR-READ-01 — exact version-pair preflight

## Result

`read_ordered_version_pair` reads two explicitly named published
`DocumentVersion` rows in one SELECT, joins each to its parent `Document`,
checks the caller's ProjectUid and DocumentUid, and requires the source's
per-document ordinal to be lower than the target's. The domain glossary
defines `Document` as the logical documentation/drawing set with an identity
that persists across versions; migration `0002` gives each version a
`document_uid` foreign key, unique ordinal within that document and an
immutable-row trigger. The reader returns immutable value objects with the
exact version UIDs, ordinals, SHA-256, byte sizes, page counts and PDF media
types. It never uses filenames, titles, labels or ordinals as identity.

The preflight validates only membership and requested order. It reads no
approved SheetLink, source text or Blob, and makes no pairing, AI or decision.
`document.project_uid` is read from the current parent row at the SELECT
snapshot. The schema does not make that column immutable, so later comparison
steps must use a consistent transaction or revalidate before publishing.

## Changed files

- `src/auditmanager/comparison/version_reader.py`;
- `tests/integration/comparison/test_version_reader.py`;
- `docs/program/tasks/W59-INT-VERSION-PAIR-READ-01.md`;
- this report.

## Checks

- `nice -n 19 ionice -c3 ../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/comparison/test_version_reader.py` — **21 passed** in 0.24 s.
- Python AST compilation for both new Python files, direct task governance
  `[]`, seven frozen SHA-256 values, owned-file whitespace and
  `git diff --check`: passed. The four task paths were absent from captured
  base `248179be`; concurrent W57a/W58 untracked paths in the shared
  worktree are outside this task.
- No Docker, live database, network or complete `make gate` under R-135.

## Contracts and limitations

No contract, migration, existing comparison/document module, public boundary,
router/API/UI, worker, dependency, composition root, global style,
`CURRENT_STATE.md` or Git ref changed. The fake-session tests prove refusal
logic and SELECT-only query shape; a later owner must test against a real
transaction and approved links. This slice is not W59 runtime activation or
beta acceptance.

## Integration instruction

Integrate only the four new task paths. The comparison owner should call the
reader with exact IDs under the same consistent transaction used to load the
approved link revision and source bytes. Persist raw diff evidence separately
from derived AI synthesis, and require expert confirmation for any decision
carryover.
