# W57B-INT-XLSX-PROJECTION-PREP-01 — finding-to-workbook result

## Result

`exports/xlsx/projection.py` converts complete, ordered, typed run reads to the
existing `WorkbookInput`. It emits one main row per finding, chooses only the
declared canonical observation for text, recommendation, proposed severity and
main evidence location, then emits every other observation in the caller's
explicit member order. Every evidence page label is displayed in ordinal
order, starting at the database's ordinal zero. Ordered norm citations, the
current expert verdict, decided severity and latest comment are copied into
the writer input.

The projection rejects a wrong run or finding association, absent canonical
observation, duplicate or omitted member, missing or out-of-order evidence,
blank page label, bad citation and verdict/severity mismatch. Rejection has
no decided severity; its canonical proposal stays separately labelled as a
proposal. A run with zero findings produces an explicit empty workbook input.

## Checks

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/exports/test_xlsx_projection_prep.py tests/integration/exports/test_xlsx_writer_prep.py` — **19 passed**.
- `../../../.venv/bin/python -m compileall -q src/auditmanager/exports/xlsx/projection.py tests/integration/exports/test_xlsx_projection_prep.py` — pass.
- Direct `governance_findings` on the task — `set()`.
- `git diff --check` — pass. The new files also passed explicit trailing-whitespace and terminal-newline checks.
- Full `make gate` deferred under R-135; no database read, web suite, live route or `soffice` probe was run.

The tests render the projected value through the existing writer and read the
XLSX cell values. They also exercise broken canonical/member partitions,
cross-run data, evidence labels and rejection severity.

## Changed files

- `src/auditmanager/exports/xlsx/projection.py`
- `tests/integration/exports/test_xlsx_projection_prep.py`
- `docs/program/tasks/W57B-INT-XLSX-PROJECTION-PREP-01.md`
- `docs/program/W57B-INT-XLSX-PROJECTION-PREP-01.md`

These four additive paths are the task's exact allowlist. Existing writer,
CSV/runtime files, `contracts/**`, migrations, provider lock, composition
root, root dependencies and global styles were not changed by this task.
Other agents' changes remain visible in the shared worktree; this task did
not stage, commit or push.

## Integration contract and limits

The future W57b XLSX reader must supply a consistent complete finding set for
one run, canonical and member observation IDs, all ordered evidence with
display page labels, ordered norm citations and the current expert verdict
from the ledger projection. It owns database access, role/state policy,
filename reuse, API contract seal and spreadsheet application validation.
The projection has no database dependency and cannot verify the correctness
of a supplied page label or citation against their external sources. There is
no silent v1 fallback. Removing these additive files before runtime wiring
is the rollback; no data migration or flag is needed.
