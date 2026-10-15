# Task W57B-INT-XLSX-WRITER-PREP-01 — pure deterministic Excel writer

task_id: W57B-INT-XLSX-WRITER-PREP-01

## Outcome

A pure typed writer emits repeatable, valid XLSX bytes for the W57b «Сводка»
and «Замечания» layout, including severity/category totals, citations and
«также найдено» member rows. It has no database, service or HTTP dependency.

## Depends on

- `W56A-INT-MERGE-INPUT-PREP-01` — completed dense canonical finding input
  preparation; this writer remains independent of its runtime activation.

## Frozen inputs

- base commit and `origin/dev`: `960da9e1b7cfc5eda75fc3a1d52714bb66be8176`.
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

- premise: W57 §B3.5 requires a deterministic standard-library writer; its additive module and focused test are absent on the pinned base.

### P-01 — exact base and absent writer paths

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/exports/xlsx tests/integration/exports/test_xlsx_writer_prep.py`
- captured_output:
  ```text
  960da9e1b7cfc5eda75fc3a1d52714bb66be8176
  960da9e1b7cfc5eda75fc3a1d52714bb66be8176
  ```
- interpretation: a new pure writer can be prepared without changing the existing CSV or claiming W57b seal/runtime completion.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/exports/xlsx/**` (new)
- `tests/integration/exports/test_xlsx_writer_prep.py` (new)
- `docs/program/tasks/W57B-INT-XLSX-WRITER-PREP-01.md`
- `docs/program/W57B-INT-XLSX-WRITER-PREP-01.md`

## Forbidden hotspots

Existing CSV/service/API/frontend, `contracts/**`, migrations, provider lock,
composition root, root dependencies/locks, global styles, corpus, stand, tags
and both remote refs.

## Non-goals

No `exportRunXlsx` endpoint, role grant, query wiring, contract seal, DB read,
actual `soffice` probe, full gate, publication or beta acceptance.

## Deliverables

Typed pure workbook input and deterministic XLSX bytes, focused XML/ZIP and
edge-case tests, task report and exact changed-path proof.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/exports/test_xlsx_writer_prep.py` — pass;
- compilation, direct task governance, whitespace and exact allowed-path proof — pass;
- no `make gate` under R-135; no `soffice` on this host.

## Integration contract

The later W57B-XLSX owner reads canonical grounded findings and current expert
decisions, projects one typed finding per canonical finding, supplies ordered
citations and member sheet/page locations, and invokes the pure writer. It must
reuse the CSV route's download-name source and enforce the sealed role/state
policy. The writer computes totals from supplied finding rows, writes no data
and never supplies a filename or authorizes a download.

## Failure/idempotency/security cases

Invalid severity, duplicate finding identity, invalid row data and cells beyond
the Excel limit fail closed. Forbidden XML characters become U+FFFD and are
counted. Every user value is an inline string, with no formula element, even
when it begins with `=`, `+`, `-` or `@`. Repeat input gives equal bytes.

## Rollback / feature flag

Revert these additive files before runtime wiring; no data rollback or flag.
