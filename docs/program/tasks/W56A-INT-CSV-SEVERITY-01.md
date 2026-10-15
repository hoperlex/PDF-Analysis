# Task W56A-INT-CSV-SEVERITY-01 — append expert and model severity to CSV

task_id: W56A-INT-CSV-SEVERITY-01

## Outcome

The existing CSV export appends `severity` (expert decision) and
`severity_proposed` (canonical observation proposal), preserving the first
seventeen OD-11 columns, byte format, order and v1 empty-cell behavior. Export
uses the canonical observation when one is recorded on the finding.

## Depends on

- `W56A-INT-SEAL-01` — completed contract and migration `0022_findings_v2`.

## Frozen inputs

- base commit and `origin/dev`: `960da9e1b7cfc5eda75fc3a1d52714bb66be8176`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`, §A3.2;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
  error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
  analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
  provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: migration 0022 supplies the two severity values, but the CSV still emits only the older seventeen columns.

### P-01 — migration values and current CSV columns

- captured_at: 2026-10-15
- command: `git grep -n -E 'proposed_severity|decided_severity|canonical_observation_id|decision_recorded_at|severity_proposed' HEAD -- db/migrations/versions/20261015_0022_findings_v2.py src/auditmanager/exports/serializer.py`
- captured_output:
  ```text
  HEAD:db/migrations/versions/20261015_0022_findings_v2.py:60:        "AS decided_severity"
  HEAD:db/migrations/versions/20261015_0022_findings_v2.py:76:               l.recorded_at AS decision_recorded_at,
  HEAD:db/migrations/versions/20261015_0022_findings_v2.py:128:    op.execute("ALTER TABLE finding_observation ADD COLUMN proposed_severity text NULL")
  HEAD:db/migrations/versions/20261015_0022_findings_v2.py:130:        "ALTER TABLE finding_observation ADD CONSTRAINT ck_finding_observation_proposed_severity "
  HEAD:db/migrations/versions/20261015_0022_findings_v2.py:131:        f"CHECK (proposed_severity IS NULL OR proposed_severity IN ({severities}))"
  HEAD:db/migrations/versions/20261015_0022_findings_v2.py:143:    op.execute("ALTER TABLE finding ADD COLUMN canonical_observation_id text NULL")
  HEAD:db/migrations/versions/20261015_0022_findings_v2.py:161:        "UPDATE finding f SET canonical_observation_id = o.finding_observation_id "
  HEAD:db/migrations/versions/20261015_0022_findings_v2.py:166:        "FOREIGN KEY (finding_uid, canonical_observation_id) "
  HEAD:db/migrations/versions/20261015_0022_findings_v2.py:192:    op.execute("ALTER TABLE finding DROP COLUMN canonical_observation_id")
  HEAD:db/migrations/versions/20261015_0022_findings_v2.py:197:    op.execute("ALTER TABLE finding_observation DROP CONSTRAINT ck_finding_observation_proposed_severity")
  HEAD:db/migrations/versions/20261015_0022_findings_v2.py:198:    op.execute("ALTER TABLE finding_observation DROP COLUMN proposed_severity")
  HEAD:src/auditmanager/exports/serializer.py:54:    "decision_recorded_at",
  ```
- interpretation: the CSV projection can be extended without a new migration or API reseal.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/exports/query.py`
- `src/auditmanager/exports/serializer.py`
- `src/auditmanager/exports/service.py`
- `web/src/shared/api/csv-columns.ts`
- `tests/integration/exports/test_frozen_column_list.py`
- `tests/integration/exports/test_csv_contract.py`
- `tests/integration/exports/test_v2_csv_severity.py` (new)
- `docs/program/tasks/W56A-INT-CSV-SEVERITY-01.md`
- `docs/program/W56A-INT-CSV-SEVERITY-01.md` (new)

## Forbidden hotspots

`contracts/**`, migrations, decision ledger, finding query, bootstrap adapters,
root dependency and lock files, composition root, global styles, provider,
stand, `CURRENT_STATE.md`, tags and Git refs.

## Non-goals

No model calls, AR v2 runtime activation, XLSX wiring, contract reseal,
corpus operation, full gate or beta acceptance.

## Deliverables

CSV query and serializer change, web column copy, focused checks and report.

## Required tests

- focused CSV tests and static first-seventeen pin;
- direct task governance, compile, whitespace and exact allowed-path proof;
- no full `make gate` under R-135.

## Integration contract

The first seventeen names and byte format remain OD-11. The appended `severity`
comes from `finding_current_verdict.decided_severity`; `severity_proposed`
comes from the finding's canonical observation. A missing canonical identity
uses the sole legacy observation's value only for pre-merge compatibility; v2
publication must set a canonical identity before export. This task does not
make a finding's model proposal an expert decision.

## Failure/idempotency/security cases

The export remains a read in one transaction with the existing published-run
policy and deterministic ordering. SQL still joins through `finding` and
`document_version`, so ungrounded observations do not appear. Repeated reads
of unchanged canonical data yield byte-identical bytes.

## Rollback / feature flag

Revert this additive CSV projection before clients depend on the columns. No
data migration or runtime flag is needed.
