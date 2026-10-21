# Task W57B-INT-XLSX-READ-PREP-01 — read-only XLSX finding adapter

task_id: W57B-INT-XLSX-READ-PREP-01

## Outcome

A read-only SQL adapter assembles the existing XLSX projection DTOs from one
run's canonical findings, all grouped observations, evidence, current expert
verdict and pinned snapshot key. It refuses missing display labels, citation
inputs and incomplete reads without rendering an export.

## Depends on

- `W57B-INT-XLSX-PROJECTION-PREP-01` — completed typed pure projection.

## Frozen inputs

- base commit: `9e3ec73e3be2ba3326380ca2c8e77bda6ad1bb7d`.
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §B3.5.
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

- premise: the pinned base has a typed projection but no DB read adapter; the
  0022 schema has canonical observations and verdict severity but no persisted
  XLSX page label or finding citation field.

### P-01 — adapter absent at base

- captured_at: 2026-10-15
- command: `git rev-parse HEAD && git ls-tree -r --name-only HEAD src/auditmanager/exports/xlsx/query.py tests/integration/exports/test_xlsx_read_query.py`
- captured_output:
  ```text
  9e3ec73e3be2ba3326380ca2c8e77bda6ad1bb7d
  ```
- interpretation: both adapter and focused test are additive to the pinned base.

### P-02 — available persisted fields

- captured_at: 2026-10-15
- command: `rg -n 'canonical_observation_id|proposed_severity|decided_severity|page_number' db/migrations/versions/20261015_0022_findings_v2.py db/migrations/versions/20260910_0002_pc01_schema.py`
- captured_output:
  ```text
  db/migrations/versions/20260910_0002_pc01_schema.py:990:            page_number      integer NOT NULL,
  db/migrations/versions/20260910_0002_pc01_schema.py:1001:            CONSTRAINT ck_finding_evidence_page_number CHECK (page_number >= 1),
  db/migrations/versions/20261015_0022_findings_v2.py:60:        "AS decided_severity"
  db/migrations/versions/20261015_0022_findings_v2.py:128:    op.execute("ALTER TABLE finding_observation ADD COLUMN proposed_severity text NULL")
  db/migrations/versions/20261015_0022_findings_v2.py:130:        "ALTER TABLE finding_observation ADD CONSTRAINT ck_finding_observation_proposed_severity "
  db/migrations/versions/20261015_0022_findings_v2.py:131:        f"CHECK (proposed_severity IS NULL OR proposed_severity IN ({severities}))"
  db/migrations/versions/20261015_0022_findings_v2.py:143:    op.execute("ALTER TABLE finding ADD COLUMN canonical_observation_id text NULL")
  db/migrations/versions/20261015_0022_findings_v2.py:161:        "UPDATE finding f SET canonical_observation_id = o.finding_observation_id "
  db/migrations/versions/20261015_0022_findings_v2.py:166:        "FOREIGN KEY (finding_uid, canonical_observation_id) "
  db/migrations/versions/20261015_0022_findings_v2.py:192:    op.execute("ALTER TABLE finding DROP COLUMN canonical_observation_id")
  db/migrations/versions/20261015_0022_findings_v2.py:197:    op.execute("ALTER TABLE finding_observation DROP CONSTRAINT ck_finding_observation_proposed_severity")
  db/migrations/versions/20261015_0022_findings_v2.py:198:    op.execute("ALTER TABLE finding_observation DROP COLUMN proposed_severity")
  ```
- interpretation: the SQL read can use these fields. A separate schema review
  found no persisted finding citation or display page label; this task requires
  both as explicit caller inputs and does not claim their source is sealed.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/exports/xlsx/query.py`
- `tests/integration/exports/test_xlsx_read_query.py`
- `docs/program/tasks/W57B-INT-XLSX-READ-PREP-01.md`
- `docs/program/W57B-INT-XLSX-READ-PREP-01.md`

## Forbidden hotspots

Existing projection/writer, CSV, routes, services, contracts, migrations,
composition root, root dependencies/locks, global styles, corpus and remote refs.

## Non-goals

No export API, role/state policy, filename, norm-citation persistence, page
label extraction, transaction ownership, live DB test, complete gate, release
or beta acceptance.

## Deliverables

Read adapter, focused fake-session tests, task report and exact path proof.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/exports/test_xlsx_read_query.py tests/integration/exports/test_xlsx_projection_prep.py tests/integration/exports/test_xlsx_writer_prep.py` — pass;
- compile, direct governance, whitespace and exact changed-path proof — pass;
- no `make gate` under R-135.

## Integration contract

`read_xlsx_projection(session, run_id, page_labels=..., citations_by_finding=...,
attribution=...)` returns `(RunRead, tuple[FindingRead, ...])` or `None` for
an absent run. The caller owns a consistent read transaction, sealed role and
state checks, verified page labels and ordered citation material. Every finding
must have an explicit citation tuple, including `()` when verified absent;
every evidence page must have an explicit label. The adapter reads the pinned
snapshot content key where present and emits an empty key only for a run with
no snapshot. Findings and members sort by opaque ID using `COLLATE "C"`; this
is display order, not a restored merge ordinal. It runs the pure projection
validator before return.

## Failure/idempotency/security cases

Missing canonical observation, evidence, verdict, label, citation entry or
cross-run association refuses. The adapter performs only SELECT and does not
commit. Repeating an unchanged transaction and supplied external material
returns equal DTOs. The future caller must verify citations and labels against
their authoritative sources; this module cannot.

## Rollback / feature flag

Remove the additive adapter and test before runtime wiring; no data rollback or
feature flag is needed.

## Handoff

- changed files/checks/limits: see report;
- contracts: none;
- next: W57b seal and export service own citation storage/read, label source,
  role/state policy and spreadsheet application acceptance.
