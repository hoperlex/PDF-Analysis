# Task CFB-INT-PARALLEL-01 — integrate five code-first preparation slices

task_id: CFB-INT-PARALLEL-01

## Outcome

The development branch contains the W56a expert-severity and CSV projections,
W57a retrieval set/catalogue preparation, and W57b normative-reference and
XLSX writer preparation as one reviewed candidate. The current state names
their exact limits without claiming beta or runtime activation.

## Depends on

- `W56A-INT-SEAL-01` — completed 0022 and optional severity contract;
- `W57A-INT-RETRIEVAL-RANK-PREP-01` — completed prompt ranking;
- `W57A-INT-TARGET-RESOLUTION-PREP-01` — completed target resolution;
- `W55A-SEARCH-01` — completed SQL designation token function.

## Frozen inputs

- base commit and `origin/dev`: `960da9e1b7cfc5eda75fc3a1d52714bb66be8176`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
  W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`;
  code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
  error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
  analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
  provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`; `origin/main=23fd729dbb06c642be0588017f6b195305e2e53e` is outside this task.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the five independently scoped preparations share the frozen development base and need one integration owner for state and `origin/dev` publication.

### P-01 — exact shared base

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev`
- captured_output:
  ```text
  960da9e1b7cfc5eda75fc3a1d52714bb66be8176
  960da9e1b7cfc5eda75fc3a1d52714bb66be8176
  ```
- interpretation: all five slices can be reviewed together without rebasing a changed development ref.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/bootstrap/adapters.py` — finding and decision mapping only;
- `src/auditmanager/decisions/ledger.py`
- `src/auditmanager/decisions/projection.py`
- `src/auditmanager/decisions/journal.py`
- `src/auditmanager/exports/query.py`
- `src/auditmanager/exports/serializer.py`
- `src/auditmanager/exports/service.py`
- `src/auditmanager/exports/xlsx/__init__.py`
- `src/auditmanager/exports/xlsx/writer.py`
- `src/auditmanager/norms/retrieval/artifact.py`
- `src/auditmanager/norms/retrieval/catalogue.py`
- `src/auditmanager/norms/references/__init__.py`
- `src/auditmanager/norms/references/families.json`
- `src/auditmanager/norms/references/families.py`
- `src/auditmanager/norms/references/resolution.py`
- `src/auditmanager/norms/references/tokens.py`
- `web/src/shared/api/csv-columns.ts`
- `tests/integration/decisions/test_v2_severity_semantics.py`
- `tests/integration/decisions/test_v2_severity_db.py`
- `tests/integration/exports/test_csv_contract.py`
- `tests/integration/exports/test_frozen_column_list.py`
- `tests/integration/exports/test_v2_csv_severity.py`
- `tests/integration/exports/test_xlsx_writer_prep.py`
- `tests/integration/norms/retrieval/test_artifact.py`
- `tests/integration/norms/retrieval/test_catalogue.py`
- `tests/integration/norms/references/test_reference_resolution.py`
- `docs/program/tasks/W56A-INT-DECIDED-SEVERITY-01.md`
- `docs/program/W56A-INT-DECIDED-SEVERITY-01.md`
- `docs/program/tasks/W56A-INT-CSV-SEVERITY-01.md`
- `docs/program/W56A-INT-CSV-SEVERITY-01.md`
- `docs/program/tasks/W57A-INT-SET-ARTIFACT-PREP-01.md`
- `docs/program/W57A-INT-SET-ARTIFACT-PREP-01.md`
- `docs/program/tasks/W57B-INT-XLSX-WRITER-PREP-01.md`
- `docs/program/W57B-INT-XLSX-WRITER-PREP-01.md`
- `docs/program/tasks/W57B-INT-REFERENCE-RESOLUTION-PREP-01.md`
- `docs/program/W57B-INT-REFERENCE-RESOLUTION-PREP-01.md`
- `docs/program/tasks/CFB-INT-PARALLEL-01.md`
- `docs/program/CFB-INT-PARALLEL-01.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, provider lock, corpus source and promotion outputs, stand,
`VERSION`, tags and `origin/main`.

## Non-goals

No runtime v2/v3 activation, reviewed map, qualified snapshot, custody
admission, W57b seal/API, provider call, corpus promotion, full gate,
deployment or beta acceptance.

## Deliverables

The five task-owned diffs and reports, this integration report, an updated
current state and an exact development commit/ref readback.

## Required tests

- focused no-DB tests, compilation, direct governance and whitespace checks;
- frozen hash and exact changed-path comparison;
- record DB/bootstrap/soffice environment-limited checks accurately;
- no full `make gate` under R-135.

## Integration contract

Stage only the listed paths. Recheck remote `origin/dev`, commit the reviewed
candidate, prove it fast-forwards the exact remote SHA, push only that commit
to `origin/dev`, then read back the remote ref. No `origin/main` update.
Later W56/W57 owners run the deferred DB and corpus gates before activating
or advertising the functionality.

## Failure/idempotency/security cases

Unexpected changed paths, changed frozen digests, a moved remote ref, a
non-fast-forward, or a focused test failure stops publication. No source norm
text or credential enters Git. Repeated pure inputs stay deterministic.

## Rollback / feature flag

Revert this development commit before runtime activation; 0022 is already
the base schema and is not downgraded by this task. No feature flag changed.
