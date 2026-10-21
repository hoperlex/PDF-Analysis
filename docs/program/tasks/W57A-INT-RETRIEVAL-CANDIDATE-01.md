# Task W57A-INT-RETRIEVAL-CANDIDATE-01 — pure set/catalogue candidate

task_id: W57A-INT-RETRIEVAL-CANDIDATE-01

## Outcome

A pure assembler joins canonical snapshot evidence, the reviewed-label
projection, complete window evidence and caller-supplied query items into
deterministic retrieval-set and catalogue candidate bytes/digests. It refuses
identity, mapped-document or item mismatches before returning either blob.

## Depends on

- `W57A-INT-SNAPSHOT-EVIDENCE-BRIDGE-01` — completed pure source projection at `a311a2f0`.
- `W57A-INT-RETRIEVAL-WINDOW-READ-01` — completed SELECT-only window evidence at `3e029301`.
- `W57A-INT-SET-ARTIFACT-PREP-01` — completed pure set/catalogue builders at `129168691f692fd24e38565b87fc27117f5384cc`.
- `W57A-INT-RETRIEVAL-RANK-PREP-01` — completed deterministic selector.

## Frozen inputs

- base commit: `248179be684395170311c8c2fea604ddea165bb5`.
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §A3.1–A3.2.
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`.
- migration head `0022_findings_v2`; no migration change.
- existing `SnapshotEvidence`, `WindowEvidence`, `SetIdentity`, `RetrievalItem`, `PromptSelection` and `CanonicalBlob` interfaces on the base commit.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: completed pure components expose all pieces needed to assemble set/catalogue bytes; no candidate assembler exists at the base.

### P-01 — exact base

- captured_at: 2026-10-15
- command: `git rev-parse HEAD`
- captured_output:
  ```text
  248179be684395170311c8c2fea604ddea165bb5
  ```
- interpretation: the task is frozen on this integrated development commit.

### P-02 — component entry points

- captured_at: 2026-10-15
- command: `rg -n '^def (project_snapshot_evidence|read_retrieval_windows|select_prompt_part|build_retrieval_set|build_catalogue)' src/auditmanager/norms/retrieval/*.py`
- captured_output:
  ```text
  src/auditmanager/norms/retrieval/catalogue.py:33:def build_catalogue(
  src/auditmanager/norms/retrieval/artifact.py:210:def build_retrieval_set(
  src/auditmanager/norms/retrieval/ranking.py:169:def select_prompt_part(
  src/auditmanager/norms/retrieval/evidence_bridge.py:104:def project_snapshot_evidence(
  src/auditmanager/norms/retrieval/window_reader.py:154:def read_retrieval_windows(
  ```
- interpretation: these functions are available to compose without editing their owners. The output does not prove owner map approval, independent query-vector digest or corpus qualification.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/retrieval/candidate.py`
- `tests/integration/norms/retrieval/test_candidate.py`
- `docs/program/tasks/W57A-INT-RETRIEVAL-CANDIDATE-01.md`
- `docs/program/W57A-INT-RETRIEVAL-CANDIDATE-01.md`

## Forbidden hotspots

`contracts/**`, migrations, existing retrieval modules, norms repository,
provider lock, public API, composition root, root dependencies, global styles,
corpus source, `CURRENT_STATE.md`, runner, stand, tags and Git refs.

## Non-goals

No map approval or target/vector provenance proof, legal edition choice,
embedding qualification, independent expected set/catalogue digest comparison,
verified set row, custody, runtime wiring, DB/S3 publication, provider call or
beta acceptance.

## Deliverables

One pure candidate assembler, focused tests and task report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/retrieval/test_candidate.py` — pass;
- Python compilation, direct task governance, whitespace and exact allowed-path proof — pass;
- complete `make gate` deferred under R-135.

## Integration contract

The caller supplies one `SnapshotEvidence`, a `WindowEvidence` obtained by
passing this map's reviewed content key to the SELECT reader, a digest-exact
`SetIdentity`/map, reviewed designation labels and caller-verified
`RetrievalItem` query vectors/targets. The assembler checks the source
snapshot ID/content key/build against the map, the window snapshot ID/build,
that every window belongs to the map's exact mapped document set, has a unique
`(ndoc_, chunk ordinal, window ordinal)` key, and that query item IDs and
target-document coverage match the map. It runs pure selection and the
existing set/catalogue builders, returning canonical bytes/SHA and selection.
`WindowEvidence` does not itself retain the read content key, so its provenance
depends on calling `read_retrieval_windows` with the same reviewed key.

## Failure/idempotency/security cases

Changed source, map, window identity, foreign/duplicate/missing mapped windows,
item IDs/target-doc mismatch, invalid vectors or artifact rows refuse without
partial output. Identical inputs yield equal blobs and selection. Map review,
query-vector digest and target span approval stay caller-owned; this assembler
does not infer or silently repair them. No corpus content or credentials enter
Git.

## Rollback / feature flag

Remove the additive assembler before runtime wiring; no data rollback or flag.

## Handoff

- changed files: four exact allowed paths.
- commands/results: focused suite and checks in result report.
- known limits: no qualification, owner review or expected digest comparison.
- integration notes: never publish candidate bytes without later verified-row workflow.
