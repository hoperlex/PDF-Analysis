# Task W57A-INT-SET-ARTIFACT-PREP-01 — pure retrieval set and catalogue bytes

task_id: W57A-INT-SET-ARTIFACT-PREP-01

## Outcome

Pure builders emit canonical UTF-8 bytes and SHA-256 for one W57a retrieval set
and its snapshot catalogue. They bind the reviewed map digest, content key,
`ns_` identity, embedding build and algorithm version; fail-closed checks cover
prompt rows, full reliable rebinding text and every supplied snapshot document.

## Depends on

- `W57A-INT-RETRIEVAL-RANK-PREP-01` — completed deterministic prompt selection.
- `W57A-INT-TARGET-RESOLUTION-PREP-01` — completed mapped target preparation.

## Frozen inputs

- base commit and `origin/dev`: `960da9e1b7cfc5eda75fc3a1d52714bb66be8176`.
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §A3.2.
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`.
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
  error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
  analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
  provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`.
- migration head `0022_findings_v2`; no head movement.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W57 §A3.2 requires deterministic set and catalogue artifacts, while those modules are absent on the frozen base.

### P-01 — exact base and absent artifact paths

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/norms/retrieval/artifact.py src/auditmanager/norms/retrieval/catalogue.py tests/integration/norms/retrieval/test_artifact.py tests/integration/norms/retrieval/test_catalogue.py`
- captured_output:
  ```text
  960da9e1b7cfc5eda75fc3a1d52714bb66be8176
  960da9e1b7cfc5eda75fc3a1d52714bb66be8176
  ```
- interpretation: new pure files can be added without claiming a promoted snapshot or custody admission.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/retrieval/artifact.py`
- `src/auditmanager/norms/retrieval/catalogue.py`
- `tests/integration/norms/retrieval/test_artifact.py`
- `tests/integration/norms/retrieval/test_catalogue.py`
- `docs/program/tasks/W57A-INT-SET-ARTIFACT-PREP-01.md`
- `docs/program/W57A-INT-SET-ARTIFACT-PREP-01.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, existing ranking and target modules,
custody tables/roles, public API, composition root, root dependencies, global
styles, corpus source, stand, tags, `origin/main` and `origin/dev` publication.

## Non-goals

No DB read, claim of snapshot totality or qualification, reviewed map authoring,
custody admission, runtime activation, provider call, corpus read or beta acceptance.

## Deliverables

New pure artifact/catalogue modules, focused tests and task report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/retrieval/test_artifact.py tests/integration/norms/retrieval/test_catalogue.py` — pass;
- compilation, direct task governance, whitespace and exact allowed-path proof — pass;
- no `make gate` under R-135.

## Integration contract

The later W57A-RETRIEVAL owner reads a qualified promoted snapshot and an
owner-reviewed map, supplies all canonical paragraphs for every mapped
document and every catalogue document from that snapshot, and checks the
independent set/catalogue expected digests before custody. The builder returns
bytes plus digest only; it cannot assert row qualification, totality or verified
custody. Its version is part of the future set identity and must change with
algorithm or serialization changes.

## Failure/idempotency/security cases

Duplicate identities, malformed map/snapshot binding, non-NFC text, missing
or mismatched text digests and prompt rows are refused. Repeated identical
inputs yield byte-identical output. No corpus text or credentials enter Git.

## Rollback / feature flag

Revert the additive modules before runtime wiring; no data rollback or flag.
