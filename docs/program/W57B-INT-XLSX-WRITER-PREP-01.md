# W57B-INT-XLSX-WRITER-PREP-01 — pure XLSX writer result

## Result

`src/auditmanager/exports/xlsx/writer.py` emits a typed, deterministic XLSX
package using only the Python standard library. The ordered parts are stored
without compression and carry the fixed earliest ZIP timestamp. «Сводка»
contains project, version, run, profile, snapshot key, attribution and totals
computed from the same canonical finding rows as «Замечания». Totals prefer
decided severity; proposed severity is used when no decision exists. The
five sealed severity values appear even at zero, followed by an explicit
unassigned count; category totals use lexical order.

«Замечания» has the eleven §B3.5 columns in order. It writes one main row per
finding, then one «также найдено» row per supplied member; the rows retain the
finding's severity fill. Multiple citations occupy newline-separated document
and quote cells. Both sheets have fixed widths and a frozen header.

User text is always an inline string, including `=`, `+`, `-` and `@` prefixes.
There are no formula elements. XML-forbidden codepoints become U+FFFD and
`RenderedWorkbook.replacement_count` reports each replacement. Values over
Excel's 32,767-character cell maximum raise `xlsx_cell_too_long`. Duplicate
finding identities and unsupported severity values fail closed.

## Checks

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/exports/test_xlsx_writer_prep.py` — **5 passed**.
- `../../../.venv/bin/python -m compileall -q src/auditmanager/exports/xlsx tests/integration/exports/test_xlsx_writer_prep.py` — pass.
- Direct `governance_findings` on the new task — `[]`.
- `git diff --check` — pass for tracked changes; new files are additionally checked for trailing whitespace during final path review.
- No full `make gate` under R-135. No `soffice` probe was run.

The tests read every XML member with `ElementTree`, verify the exact ZIP part
order, `ZIP_STORED`, fixed timestamps, workbook sheet names, cell values,
severity styling, header freeze, multi-citation and member rows, formula
literal safety, forbidden-character replacement, the cell limit and invalid
input refusal.

## Changed files

- `src/auditmanager/exports/xlsx/__init__.py`
- `src/auditmanager/exports/xlsx/writer.py`
- `tests/integration/exports/test_xlsx_writer_prep.py`
- `docs/program/tasks/W57B-INT-XLSX-WRITER-PREP-01.md`
- `docs/program/W57B-INT-XLSX-WRITER-PREP-01.md`

No contract, migration, provider lock or shared hotspot was changed by this
task. Other parallel agents have separate, visible untracked/modified paths
in the common worktree; this task did not stage or commit any file.

## Integration contract and limits

The eventual `W57B-XLSX-01` owner projects grounded canonical findings and
current expert decisions into `WorkbookInput`, preserving the caller's finding
order and supplying each member location. That owner adds the API role/state
policy, run query, existing CSV filename source, sealed contract and an
independent `soffice` cell-by-cell probe. This pure writer cannot establish
source provenance, authorize a download, or prove Excel application import.
Its hardcoded five severity values are the currently sealed W56a vocabulary;
the future seal owner must check them against the final contract.

Rollback is deletion of these additive files before runtime wiring. No data
rollback or feature flag is required.
