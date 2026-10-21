# Task W56A-INT-CSV-PINS-SYNC-01 — align CSV seam and guards with 19 columns

task_id: W56A-INT-CSV-PINS-SYNC-01

## Outcome

The current CSV seam, visible copy and executable structural pins agree with
the W56a exporter: the original seventeen columns remain in order, followed by
`severity` and `severity_proposed`. The no-decision PC-01 byte pin is adjusted
by a derivation that preserves the original five-row evidence.

## Depends on

- `W56A-INT-CSV-SEVERITY-01` — completed CSV implementation and focused tests.

## Frozen inputs

- base commit: `eca8597b4b59a06371cfaf709df7bee8509a604f`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`, §A3.2 and §A4 DECIDE;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: docs/program/P02_SEAMS.md
- enumerator_owner: W56A-INT-CSV-PINS-SYNC-01
- totality_query: `sed -n '760,786p' docs/program/P02_SEAMS.md`

## Captured premise evidence

- premise: the W56a CSV serializer emits nineteen columns while the seam and several guards still assert seventeen.

### P-01 — stale structural pins on the exact base

- captured_at: 2026-10-15
- command: `rg -n 'Seventeen columns|toHaveLength\(17\)|EXPECTED_CSV_COLUMNS = 17|csv_columns.*17|len\(header\) == 17' docs/program/P02_SEAMS.md web/tests/contract/csv-columns.contract.test.ts tests/e2e/pc01/test_acceptance.py tests/e2e/p02/test_journey_figures_pinned.py tests/integration/p02_journey/test_journey_figures.py`
- captured_output:
  ```text
  tests/e2e/pc01/test_acceptance.py:82:EXPECTED_CSV_COLUMNS = 17
  docs/program/P02_SEAMS.md:762:Seventeen columns, in this order. This is the frozen list; `B5` produces it and `B8`
  web/tests/contract/csv-columns.contract.test.ts:42:    expect(fromDocument).toHaveLength(17);
  tests/integration/p02_journey/test_journey_figures.py:151:    assert len(header) == 17
  tests/e2e/p02/test_journey_figures_pinned.py:58:    "csv_columns": 17,
  ```
- interpretation: these consumers require synchronization with the already changed W56a exporter; this output does not prove service-backed acceptance.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/P02_SEAMS.md`
- `web/tests/contract/csv-columns.contract.test.ts`
- `web/tests/guards/rendered-language.guard.test.ts`
- `src/auditmanager/api/routers/ports.py`
- `web/src/widgets/export-panel/ui/export-panel.tsx`
- `web/tests/unit/export/export-panel.test.ts`
- `tests/e2e/p02/test_journey.py`
- `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`
- `tests/integration/exports/test_csv_contract.py`
- `tests/integration/exports/test_frozen_column_list.py`
- `src/auditmanager/exports/query.py`
- `docs/manual-tests/PC-01_prototype.md`
- `docs/program/ALPHA_ROADMAP.md`
- `tests/contract/domain_p02/test_seam_register.py`
- `tests/e2e/pc01/test_acceptance.py`
- `tests/integration/p02_journey/test_journey_figures.py`
- `tests/e2e/p02/test_journey_figures_pinned.py`
- `docs/program/tasks/W56A-INT-CSV-PINS-SYNC-01.md`
- `docs/program/W56A-INT-CSV-PINS-SYNC-01.md`

## Forbidden hotspots

`contracts/**`, migrations, serializer and query behavior, service, decisions, bootstrap,
root dependency/lock files, composition root, global styles,
`CURRENT_STATE.md`, characterization record 12, tags and Git refs.

## Non-goals

No CSV behavior change, historical characterization rebaseline, DB migration,
provider activation, full gate or beta acceptance.

## Deliverables

Current CSV seam, stale documentation and structural test pins, mathematically
derived no-decision byte pin, and an evidence report.

## Required tests

- direct task governance, static CSV seam/serializer parity, focused no-DB Python tests;
- web contract/unit guards if Node dependencies are available;
- `git diff --check` and exact allowed-path proof;
- DB-backed PC-01 and P02 journeys when an isolated PostgreSQL is available;
- full `make gate` deferred under R-135.

## Integration contract

Columns 1–17 retain OD-11's names/order; 18 is `severity` from
`finding_current_verdict.decided_severity`, 19 is `severity_proposed` from
the canonical observation. In a v1 PC-01 journey both new values are null.
The old no-decision export was 4251 bytes over five rows. Adding the ASCII
header suffix `,severity,severity_proposed` adds 27 bytes and two empty-cell
delimiters per row add 10, yielding 4288 bytes; DB confirmation remains due.

## Failure/idempotency/security cases

Seam and frontend lists must match the serializer exactly. The two appended
cells never convert a model proposal into an expert decision. Old
characterization record 12 remains historical evidence, not a current pin.

## Rollback / feature flag

Revert this pin synchronization with the corresponding additive CSV behavior.
No runtime flag is introduced.
