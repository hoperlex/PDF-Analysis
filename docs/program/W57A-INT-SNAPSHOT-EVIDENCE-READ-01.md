# W57A-INT-SNAPSHOT-EVIDENCE-READ-01 — canonical snapshot evidence reader

## Result

`norms/retrieval/source_reader.py` adds a SELECT-only reader under a
caller-owned consistent transaction. It binds a requested `ns_` ID to the
independently expected content key, returns all catalogue documents with
stored SQL designation tokens, and reads all canonical paragraphs for the
specified mapped `ndoc_` IDs. The adapter checks document and paragraph
counts, dense ordinal order, permitted reliability/kind values, opaque
identities and NFC text. Every returned
paragraph retains its explicit reliability and a SHA-256 of stored text.
The snapshot's `unreliable_count` records unrepaired blocks, which can each
produce multiple unreliable paragraphs; the adapter preserves it without
equating those different counts.

The reader leaves designation as raw slug/title evidence. A later reviewed
projection must supply the designation used by the pure retrieval builder.
No MAP-01 review, complete embedding build or verified W57a set row exists
in this task, so this result does not qualify the base corpus.

## Checks

- Focused fake-session suite: **9 passed** (including two unreliable paragraphs
  from one unrepaired block).
- Python compilation of the adapter and its test: passed.
- Direct task `governance_findings`: `[]`.
- Task parser accepted the exact base and four allowed paths; all four new
  files pass trailing-space/newline checks, and `git status --short` lists
  exactly those four untracked paths after integration of unrelated W56a.
- Ruff was unavailable in the lock-matched local Python environment.
- Complete `make gate` deferred under R-135.

## Contracts and limits

No shared contract, migration, public API, dependency, composition or runtime
path changed. The adapter's additive Python interface accepts exact snapshot
ID, reviewed content key and mapped document IDs, then returns raw evidence;
it does not assert its own review or DB qualification. Its count checks rely
on the caller keeping all SELECTs in one consistent read transaction. It does
not load ranking windows, model vectors or the full text of unmapped documents.

## Integration instruction

Keep this reader behind the future W57a MAP/RETRIEVAL owner. After an owner
review of map, snapshot and designation choices and a separately verified
complete embedding build, read the evidence in a consistent DB view. Project
the reviewed designation into `RetrievalParagraph`, use the pure ranking and
artifact builders, compare independent expected digests, then conduct W57
custody and verified-row workflow. Do not pin or publish a set from this
adapter alone.

## Ownership proof

Only four new task-owned paths were written. `contracts/**`, migration head,
other retrieval modules, norms repository, provider lock, composition root,
root dependencies, global styles, corpus, `CURRENT_STATE.md`, stand and Git
refs were untouched by this task.

The task froze from `0c9f2d644a5a89c930ee61ff6e14ae3d8e9733e4`.
Integrator commit `6a1d915c76e9de3d14c6c81967ddb38d91f90242` landed on the
shared branch while this independent slice was being prepared. Thus a broad
base-to-HEAD path check includes W56a ownership; the integrator should stage
and inspect only the four exact paths above for this task's commit.
