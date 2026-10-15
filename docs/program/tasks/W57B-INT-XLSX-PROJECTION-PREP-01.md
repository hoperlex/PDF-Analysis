# Task W57B-INT-XLSX-PROJECTION-PREP-01 — pure finding-to-workbook projection

task_id: W57B-INT-XLSX-PROJECTION-PREP-01

## Outcome

Typed, complete read rows for a run project into one `WorkbookInput` finding row
per canonical finding. Tests prove canonical membership, full member partition
and order, page labels, citations and the current expert verdict.

## Depends on

- `W57B-INT-XLSX-WRITER-PREP-01` — completed pure typed XLSX writer.

## Frozen inputs

- base commit and `origin/dev`: `3a9b64c0796e6d61ad33a6c9f87ff842525712f6`.
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

- premise: The completed writer accepts `WorkbookInput` but no projection of canonical findings, member observations or current expert verdict exists at the pinned base.

### P-01 — pinned base and absent projection paths

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/exports/xlsx/projection.py tests/integration/exports/test_xlsx_projection_prep.py docs/program/tasks/W57B-INT-XLSX-PROJECTION-PREP-01.md docs/program/W57B-INT-XLSX-PROJECTION-PREP-01.md`
- captured_output:
  ```text
  3a9b64c0796e6d61ad33a6c9f87ff842525712f6
  3a9b64c0796e6d61ad33a6c9f87ff842525712f6
  ```
- interpretation: An additive projection can prepare the writer's input without an API, SQL or contract change.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/exports/xlsx/projection.py`
- `tests/integration/exports/test_xlsx_projection_prep.py`
- `docs/program/tasks/W57B-INT-XLSX-PROJECTION-PREP-01.md`
- `docs/program/W57B-INT-XLSX-PROJECTION-PREP-01.md`

## Forbidden hotspots

Existing writer, CSV/export query and service, routes, contracts, migrations,
composition root, root dependencies/locks, global styles, corpus,
`CURRENT_STATE.md`, tags and remote refs.

## Non-goals

No database query, endpoint, role/state check, filename, normative conclusion,
`soffice` probe, complete gate, publication or beta acceptance.

## Deliverables

Typed pure projection, focused tests, task report and exact changed-path proof.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/exports/test_xlsx_projection_prep.py tests/integration/exports/test_xlsx_writer_prep.py` — pass;
- Python compilation, direct task governance, whitespace and exact changed-path proof — pass;
- no `make gate` under R-135.

## Integration contract

The future `W57B-XLSX-01` reader supplies one consistent, complete ordered
`FindingRead` tuple for one run. It must obtain the canonical observation ID,
the allocating run ID,
all grouped observations, their zero-based ordered evidence and display page labels,
current verdict and decided severity from the expert projection, ordered norm
citations and run identity. `member_observation_ids` lists every noncanonical
observation exactly once in display order. The projection validates the total
partition and returns one `FindingRow` per `FindingRead`, preserving finding
order. It never infers a missing canonical observation or page label.

## Failure/idempotency/security cases

Wrong run/finding/observation association, missing or duplicate canonical/member
identities, incomplete member partition, missing or out-of-order evidence,
empty page labels, invalid citations and inconsistent verdict/severity fail
closed. Repeat input returns equal `WorkbookInput`; the writer emits literal
text, including formula-like strings. A rejected finding has no decided
severity; a model proposal remains explicitly labelled as a proposal.

## Rollback / feature flag

Remove the additive projection and test before runtime wiring; no data
rollback or feature flag is needed.

## Handoff

- changed files/checks/limits: see report;
- contracts: none;
- next: `W57B-XLSX-01` owns the DB reader, API seal, role/state enforcement and independent spreadsheet probe.
