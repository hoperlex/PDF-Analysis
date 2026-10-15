# Task W57A-INT-SNAPSHOT-EVIDENCE-READ-01 — SELECT-only snapshot evidence

task_id: W57A-INT-SNAPSHOT-EVIDENCE-READ-01

## Outcome

A read-only adapter returns canonical snapshot, catalogue-document and mapped
paragraph evidence for a later W57a retrieval-set builder. It refuses a missing
or changed snapshot/content key, incomplete document or paragraph reads, and
unknown reliability. It makes no qualification, review or custody claim.

## Depends on

- `W57A-INT-SET-ARTIFACT-PREP-01` — completed pure byte builder at `129168691f692fd24e38565b87fc27117f5384cc`.
- `W57A-INT-TARGET-RESOLUTION-PREP-01` — completed pure target resolver at `0bcef49dc4e0dd0899a2d6bfc099c3f9d0e7cf9f`.

## Frozen inputs

- base commit: `0c9f2d644a5a89c930ee61ff6e14ae3d8e9733e4`
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §A3.2.
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`.
- migration head `0022_findings_v2`; `norms_snapshot`, `norm_document`, `norm_paragraph` and SQL-generated `designation_tokens` as stored there.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the pure artifact builder requires canonical rows, while its task expressly leaves DB totality and qualification to a later reader.

### P-01 — exact base and absent reader

- captured_at: 2026-10-15
- command: `git rev-parse 0c9f2d644a5a89c930ee61ff6e14ae3d8e9733e4 && git ls-tree -r --name-only 0c9f2d644a5a89c930ee61ff6e14ae3d8e9733e4 src/auditmanager/norms/retrieval/source_reader.py && git show 0c9f2d644a5a89c930ee61ff6e14ae3d8e9733e4:src/auditmanager/norms/retrieval/artifact.py | rg -n 'caller owns|qualification|canonical paragraphs'`
- captured_output:
  ```text
  0c9f2d644a5a89c930ee61ff6e14ae3d8e9733e4
  3:The caller owns review, snapshot qualification, DB totality and custody. This
  158:        raise ArtifactRefused("mapped documents have no canonical paragraphs")
  ```
- interpretation: no existing source reader is present at the exact base; the pure builder expressly leaves DB totality and qualification to a later adapter. Stored snapshot, document and paragraph rows can be read by opaque identity, with SQL-generated designation tokens and explicit paragraph reliability. Migration head `0022` has no W57a verified-set row.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/retrieval/source_reader.py`
- `tests/integration/norms/retrieval/test_source_reader.py`
- `docs/program/tasks/W57A-INT-SNAPSHOT-EVIDENCE-READ-01.md`
- `docs/program/W57A-INT-SNAPSHOT-EVIDENCE-READ-01.md`

## Forbidden hotspots

`contracts/**`, migrations, other retrieval modules, norms repository,
provider lock, public API, composition root, root dependencies, global styles,
corpus source, `CURRENT_STATE.md`, stand, tags and Git refs.

## Non-goals

No reviewed map authoring, edition/designation choice, qualified snapshot,
embedding-build check, ranking-window read, set row, custody, runtime wiring,
provider call, production DB/S3 publication or beta acceptance.

## Deliverables

One SELECT-only evidence adapter, fake-session tests and task report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/retrieval/test_source_reader.py` — pass;
- Python compilation, whitespace and exact allowed-path proof — pass;
- complete `make gate` deferred under R-135.

## Integration contract

The caller supplies an independently reviewed map's exact `ns_` identity,
content key and mapped `ndoc_` IDs, and owns one consistent read transaction.
The adapter reads all catalogue documents, all paragraphs of mapped documents,
and aggregate counts using only SELECT statements. It returns raw stored slug,
title, page label, clause, text and reliability, with text SHA-256. A later
reviewed projection must supply the designation used by `RetrievalParagraph`;
the adapter never infers it from a slug. Qualification requires an independent
complete embedding build, owner review, expected digests and custody.

## Failure/idempotency/security cases

Missing/mismatched snapshot, duplicate/foreign documents, incomplete ordinals,
paragraph count mismatch, unknown reliability and malformed row values refuse.
`norms_snapshot.unreliable_count` counts unrepaired blocks, so it is not equated
to the count of unreliable paragraphs. Identical
database rows yield identical output. No side effect or corpus text enters Git.

## Rollback / feature flag

Remove the additive adapter before wiring; no data rollback or flag.
