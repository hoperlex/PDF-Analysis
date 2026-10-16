# W57B-INT-SAVED-TEXT-SOURCE-01 — result

**Status:** completed unserved source slice on frozen dev60
`2fe82f40f4ac2bf82f9778c28b2fd2a2b8e8deab`; no remote publication.

## Changed files

- `src/auditmanager/runs/reference_text_input.py` — caller-transaction-owned
  current Run/Attempt reader for one saved `prepared.text_layer` Blob.
- `src/auditmanager/analysis/text/source_bytes.py` — factor the existing W56b
  canonical byte validator into a pure no-chunk function; W56b still calls it
  before its unchanged chunk partition.
- `src/auditmanager/analysis/public.py` — expose the pure validator and its
  refusal type at the analysis boundary.
- `tests/integration/runs/test_reference_text_input_offline.py` — exact Blob,
  Version, page, Attempt and stream refusal cases plus W57b bridge roundtrip.
- `docs/program/tasks/W57B-INT-SAVED-TEXT-SOURCE-01.md` — task freeze.
- `docs/program/W57B-INT-SAVED-TEXT-SOURCE-01.md` — this report.

## Checks

- Focused W57b reader/bridge and existing W56b text suites: **76 passed**.
- Task governance: **16 passed**, with five pytest warnings while removing
  other workers' shared `/tmp/pytest-of-root/garbage-*` directories.
- Owned Python compiled; `git diff --check` passed.
- Frozen API, migration and code-first order file hashes matched the task;
  the six exact task paths are the only source-commit delta.
- No full `make gate` under R-135's intermediate code-candidate rule; no real
  DB/S3, paid model or served W57b journey was run.

## Integration contract and limits

`load_saved_reference_text` needs a caller-owned transaction, current
`AttemptAuthority`, public `BlobStore` and explicit byte cap. It verifies a
running Run and its Version, one succeeded registry-versioned source stage and
its complete saved artifact set; reads exact text bytes under a bounded buffer;
checks digest, size, canonical JSON, page identity, Unicode offsets and declared
count; then repeats Attempt, Run, Version and stage reads. It returns the
validated `TextLayer` with independently verified Version UID and page count.
The W57b `reference_pages_from_text_layer` bridge consumes these three values
without PDF text mutation, including a Cyrillic/emoji page and an empty page.

The pure validator now rejects a contiguous but misnumbered 2..N+1 page set
as well as wrong page count; this strengthens the prior W56b byte-validation
precondition and leaves its chunk budget and window behavior intact. The
reader cannot reserve authority for a later effect, prove real DB/S3 custody,
qualify the normative corpus or publish references. A served caller still
needs its own effect gate and result transaction.

No shared contract, migration, lockfile, composition root, global style,
API route, provider, finding, tag or remote ref changed. Revert the six owned
paths before activation if needed; no persisted data or feature flag applies.

## Integrator note

Review the six-path source commit and run the focused checks on its integration
candidate. Wire only when the W57b deterministic-stage caller can supply the
current Attempt and an approved byte cap; this source task grants no
`origin/dev` or `origin/main` publication authority.
