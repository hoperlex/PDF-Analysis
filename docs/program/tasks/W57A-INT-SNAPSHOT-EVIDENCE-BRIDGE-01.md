# Task W57A-INT-SNAPSHOT-EVIDENCE-BRIDGE-01 — reviewed snapshot projection

task_id: W57A-INT-SNAPSHOT-EVIDENCE-BRIDGE-01

## Outcome

A pure adapter projects SELECT-read `SnapshotEvidence` into the existing
`SnapshotBinding`, `SourceParagraph` and `TargetParagraph` inputs. It binds a
digest-exact map, pinned snapshot and caller-reviewed document designations,
refusing changed identities, labels, content digests or reliability.

## Depends on

- `W57A-INT-SNAPSHOT-EVIDENCE-READ-01` — completed SELECT-only evidence reader at `ecf5f56f`.
- `W57A-INT-SET-ARTIFACT-PREP-01` — completed pure set and catalogue builders at `129168691f692fd24e38565b87fc27117f5384cc`.
- `W57A-INT-TARGET-RESOLUTION-PREP-01` — completed target resolver at `0bcef49dc4e0dd0899a2d6bfc099c3f9d0e7cf9f`.

## Frozen inputs

- base commit: `6b2e9ade4967b0c225e7e4be63b19a74e8cd2b3e`.
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §A3.1–A3.2.
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`.
- migration head `0022_findings_v2`; no migration change.
- existing `SnapshotEvidence`, `SetIdentity`, `SnapshotBinding`, `SourceParagraph`, `RetrievalParagraph`, `TargetParagraph` interfaces on the base commit.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the completed reader returns raw slug/title and paragraph rows, while the pure set builder needs a designation-bearing `RetrievalParagraph`; there is no bridge at the base.

### P-01 — base and missing bridge

- captured_at: 2026-10-15
- command: `git rev-parse HEAD`
- captured_output:
  ```text
  6b2e9ade4967b0c225e7e4be63b19a74e8cd2b3e
  ```
- interpretation: task was prepared against this exact local development commit.

### P-02 — existing input types

- captured_at: 2026-10-15
- command: `rg -n 'class SnapshotEvidence|class SnapshotBinding|class SourceParagraph|class PromptSelection' src/auditmanager/norms/retrieval/source_reader.py src/auditmanager/norms/retrieval/artifact.py src/auditmanager/norms/retrieval/ranking.py`
- captured_output:
  ```text
  src/auditmanager/norms/retrieval/ranking.py:82:class PromptSelection:
  src/auditmanager/norms/retrieval/source_reader.py:56:class SnapshotEvidenceRefused(ValueError):
  src/auditmanager/norms/retrieval/source_reader.py:83:class SnapshotEvidence:
  src/auditmanager/norms/retrieval/artifact.py:43:class SnapshotBinding:
  src/auditmanager/norms/retrieval/artifact.py:61:class SourceParagraph:
  ```
- interpretation: the type seams exist; the reader's raw evidence still needs reviewed designation projection. The query does not prove snapshot qualification or review.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/retrieval/evidence_bridge.py`
- `tests/integration/norms/retrieval/test_evidence_bridge.py`
- `docs/program/tasks/W57A-INT-SNAPSHOT-EVIDENCE-BRIDGE-01.md`
- `docs/program/W57A-INT-SNAPSHOT-EVIDENCE-BRIDGE-01.md`

## Forbidden hotspots

`contracts/**`, migrations, other retrieval modules, norms repository,
provider lock, public API, composition root, root dependencies, global styles,
corpus source, `CURRENT_STATE.md`, stand, tags and Git refs.

## Non-goals

No map authoring or owner review, legal edition choice, qualified embedding
build, vector/window read, prompt selection, verified set row, custody,
runtime wiring, DB/S3 publication, provider call or beta acceptance.

## Deliverables

One pure evidence bridge, focused tests and task report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/retrieval/test_evidence_bridge.py` — pass;
- Python compilation, direct task governance, whitespace and exact allowed-path proof — pass;
- complete `make gate` deferred under R-135.

## Integration contract

The future W57a owner supplies bytes of the reviewed map, its `SetIdentity`,
one `SnapshotEvidence` from a consistent SELECT transaction, and separately
reviewed `(ndoc_, stored slug, designation)` labels for every mapped document.
The bridge checks map SHA and identity, source snapshot, catalogue membership,
slug, paragraph ordinals, reliability and text SHA before projecting. The
returned `source_paragraphs` feed the set builder and ranking; returned
`target_paragraphs` feed target resolution. The caller separately proves the
complete embedding build and owner review, reads windows/vectors, selects a
prompt, compares expected artifact digests and performs custody. The bridge
does not confer qualification by matching an embedding-build string.

## Failure/idempotency/security cases

Changed map/snapshot, missing or duplicate mapped labels, slug drift, foreign
paragraphs, sparse ordinals, unknown reliability and content-digest mismatch
refuse. Repeated identical inputs produce equal immutable outputs. The
snapshot's unreliable count is of unrepaired blocks and is not compared to
unreliable paragraph count. No corpus content or credentials enter Git.

## Rollback / feature flag

Remove the additive adapter before runtime wiring; no data rollback or flag.

## Handoff

- changed files: four exact allowed paths.
- commands/results: focused suite and checks in result report.
- known limits: map/designation review and snapshot qualification remain caller-owned.
- integration notes: do not publish or pin a retrieval set from this adapter alone.
