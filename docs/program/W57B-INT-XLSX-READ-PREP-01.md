# W57B-INT-XLSX-READ-PREP-01 — read-only XLSX query result

## Result

`exports/xlsx/query.py` reads a run, pinned snapshot content key, canonical
findings, every grouped observation and ordered evidence, plus the current
expert verdict and decided severity, into the existing projection DTOs. The
query uses the caller's session and performs only SELECT. It retains rows for
corrupt findings with missing observations, evidence or verdict so those cases
fail explicitly rather than disappearing from the export.

The 0022 schema does not store XLSX display page labels or finding-level norm
citations. The adapter requires a page-number-to-label mapping and a citation
tuple for every finding, including an explicit empty tuple. It never derives a
label from a page number or assumes missing citation data means no citations.
The caller must verify both external inputs. It also supplies attribution.

Findings, observations and evidence have stable `COLLATE "C"`/ordinal order.
The source merge ordinal is not persisted, so observation IDs establish display
order only; they do not reconstruct the original merge plan. The adapter runs
the pure projection validator before returning the typed values.

## Checks

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/exports/test_xlsx_read_query.py tests/integration/exports/test_xlsx_projection_prep.py tests/integration/exports/test_xlsx_writer_prep.py` — **32 passed**.
- `../../../.venv/bin/python -m compileall -q src/auditmanager/exports/xlsx/query.py tests/integration/exports/test_xlsx_read_query.py` — pass.
- `git diff --check` — pass. Direct `governance_findings` on the task — `[]`.
  All four new files have a terminal newline and no trailing whitespace.
  `../../../.venv/bin/ruff` is absent, so Ruff was not run.
- PostgreSQL read, API policy, spreadsheet application opening and full
  `make gate` were not run; R-135 defers the complete gate.

## Changed files

- `src/auditmanager/exports/xlsx/query.py`
- `tests/integration/exports/test_xlsx_read_query.py`
- `docs/program/tasks/W57B-INT-XLSX-READ-PREP-01.md`
- `docs/program/W57B-INT-XLSX-READ-PREP-01.md`

The four additive paths are the task's exact allowlist; direct ownership check
found no fifth path edited by this task. Existing writer,
projection, CSV/runtime files, `contracts/**`, migrations, provider lock,
composition root, root dependencies and global styles were not edited by this
task. Other agents' changes may be visible in the shared worktree. This task
does not stage, commit or push.

## Integration contract and limits

The future sealed XLSX service supplies a consistent transaction, explicit
verified page labels and citations, attribution, role/state policy and a
download name from the CSV route's single source. Current DB schema cannot
prove the truth of supplied labels/citations. No API export or beta acceptance
is claimed. Remove the additive files before wiring to roll back.
