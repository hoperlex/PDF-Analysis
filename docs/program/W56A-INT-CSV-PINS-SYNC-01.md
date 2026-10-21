# W56A-INT-CSV-PINS-SYNC-01 — nineteen-column CSV pins

## Result

The current CSV seam and its Python/web guards now list nineteen columns in
the server's exact order: OD-11's first seventeen, then `severity` and
`severity_proposed`. Current manual acceptance instructions and CSV docstrings
use the same count. No CSV query, serializer or runtime behavior changed.

The pinned no-decision five-row PC-01 export derives to **4288 bytes** from its
historical 4251-byte measurement: the ASCII header suffix adds 27 bytes and
the two empty severity cells add two delimiters to each of five v1 rows
(4251 + 27 + 10). The old accept/reject manual figure derives from 4525 to
4562 bytes under the same empty-cell condition. Both new byte figures still
need PostgreSQL confirmation; they are calculations, not new measurements.

## Changed files

- Contract description: `docs/program/P02_SEAMS.md` §6.
- Web guard/copy: `web/tests/contract/csv-columns.contract.test.ts`,
  `web/tests/guards/rendered-language.guard.test.ts`,
  `web/tests/unit/export/export-panel.test.ts`,
  `web/src/widgets/export-panel/ui/export-panel.tsx`.
- Python guards and comments: `tests/contract/domain_p02/test_seam_register.py`,
  `tests/e2e/pc01/test_acceptance.py`, `tests/e2e/p02/test_journey.py`,
  `tests/e2e/p02/test_journey_figures_pinned.py`,
  `tests/integration/p02_journey/test_journey_figures.py`,
  `tests/integration/exports/test_csv_contract.py`,
  `tests/integration/exports/test_frozen_column_list.py`,
  `src/auditmanager/api/routers/ports.py`,
  `src/auditmanager/exports/query.py`.
- Current manual text: `docs/manual-tests/PC-01_prototype.md`,
  `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`,
  `docs/program/ALPHA_ROADMAP.md`.
- Task and report: `docs/program/tasks/W56A-INT-CSV-PINS-SYNC-01.md`, this file.

## Checks

- Static server/seam/frontend ordered-column parity: **19 exact matches**.
- Focused Python structural CSV seam guard: passed after aligning its
  nineteen-column assertion; the integrator's combined no-DB run passed
  85 tests overall, with two DB-backed cases deselected.
- Byte arithmetic and current pin assertions: **4288/4562 derived**.
- Direct `governance_findings` for this task: `[]`.
- `python3 -m compileall -q` on the touched Python files: passed.
- `git diff --check`: passed.
- Frozen W56 plan, API, error catalog, stage registry and provider-lock SHA-256
  values match the task's frozen inputs.
- The task lane could not run pytest with `/usr/bin/python3`; the integrator
  ran the focused structural guard with `../../../.venv/bin/python`.
  Web tests could not run: `web/node_modules` is
  absent. DB-backed journey and the complete gate remain unverified under
  R-135; `DATABASE_URL` is unset.

## Contracts and limits

`P02_SEAMS.md` §6 is synchronized with the existing additive CSV projection.
No `contracts/**`, migration, API surface, root dependency/lock file,
composition root, global style or provider lock changed.

The historical checkpoint and characterization record 12 still contain the
seventeen-column bytes. They are not rewritten by this task. The current
characterization test may need an explicitly owned permitted exception or
rebaseline before the full gate can pass; this task does not claim that gate.

## Integration instruction

On an isolated PostgreSQL migrated through 0022, run the focused CSV,
PC-01 and P02 journeys, verify the derived 4288/4562-byte figures, then
resolve characterization record 12 under a separate exact task if its current
test is red. Run the web CSV contract and export-panel tests after restoring
Node dependencies. Preserve the historical checkpoint bytes.

## Ownership proof

The lane and integrator edited only the exact paths in this task's `Allowed
paths`; the four additional live stale references and the frozen-column seam
assertion were explicitly added to that allowlist.
Historical reviews, dispatch records and characterization record 12 were not
edited. No Git ref, checkpoint or tag was created by this lane.
