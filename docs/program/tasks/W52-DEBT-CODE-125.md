# Task W52-DEBT-CODE-125 — verify corpus bytes when projecting a snapshot

task_id: W52-DEBT-CODE-125

## Outcome

A corpus load refuses any document whose bytes or source identity change after the
snapshot was derived, before it can enter that immutable snapshot. The direct
`segment_corpus` projection has the same fail-closed check.

## Depends on

- `W52-INT-129F4-01` — published at
  `015c6f14868f00e26682c42e9cbb5e439ed8013d`.

## Frozen inputs

- Exact base `015c6f14868f00e26682c42e9cbb5e439ed8013d`; domain revision 9 / 29
  identities, API 27 paths / 34 operations / 77 schemas, error catalog 23, migration
  head `0015_accounts_roles_registration`.
- D-125 in `docs/program/DEBT_REGISTER.md` and current `CorpusProjection` read path.
- Owner direction 2026-10-08: basic tests and lint only; QA, temporary stand and full
  gate are deferred to D-139/D-140.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the snapshot is derived before documents are re-read for projection.

### P-01 — exact base and read path

- captured_at: 2026-10-08
- command: `git rev-parse HEAD; rg -n 'def iter_documents|document = read_document\(directory\)|base_snapshot = snapshot_of\(root\)|def segment_corpus' src/auditmanager/norms/corpus_source.py`
- captured_output:
  ```text
  015c6f14868f00e26682c42e9cbb5e439ed8013d
  87:    def iter_documents(self) -> Iterator[ProjectedCorpusDocument]:
  89:            document = read_document(directory)
  174:def segment_corpus(
  180:    base_snapshot = snapshot_of(root)
  194:        document = read_document(directory)
  339:    base_snapshot = snapshot_of(root)
  ```
- interpretation: both consumers read after the snapshot pass; neither compares the
  bytes it then projects to the bytes that determined its identity.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/corpus_source.py`
- `tests/integration/norms/test_repair_projection.py`
- `docs/program/W52-DEBT-CODE-125.md`

## Forbidden hotspots

Every other path, especially contracts, migration head, root dependencies/locks,
composition root and global styles.

## Non-goals

No corpus source mutation, new snapshot identity format, database schema, full corpus
run, QA, temporary stand, full gate, release, tag or `origin/main` publication.

## Deliverables

- Retain the raw per-document fingerprints from the snapshot pass and check each
  re-read before segmentation, including the repaired projection path.
- Fail loudly on changed bytes/source identity and prove it with a local corpus
  fixture. Preserve normal and repaired projection behavior.
- Record focused checks, limitations and integration instructions.

## Required tests

- Run focused fixture tests, Python compilation, frontend lint and
  `git diff --check`. Do not run database/full-corpus tests, a stand or full gate.

## Integration contract

Hand back a clean branch from the exact dispatch SHA with only allowed paths.
The integrator may publish to `origin/dev` after exact ref and fast-forward checks.
An affected load raises `CorpusUnavailable`; `load_corpus`'s existing SAVEPOINT
boundary rolls back any earlier inserted documents.

## Failure/idempotency/security cases

Change `results.md` without changing dates, change `blocks.json` source identity,
or change a later document after an earlier one was yielded: all must refuse.
Unchanged sources remain re-iterable. No silent fallback.

## Rollback / feature flag

Revert the code commit. No runtime feature flag is needed for a fail-closed read.

## Handoff

- changed files, commands/results, contracts, risks, integration notes and proof
  that forbidden hotspots were untouched.
