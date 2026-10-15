# W57B-INT-XLSX-PACKAGE-PREP-01 — XLSX package composition result

## Result

`exports/xlsx/package.py` now composes the existing SELECT-only run reader,
typed projection and deterministic XLSX writer. Its inputs name the exact run
and principal, a caller-owned `exportRunXlsx` allow decision/reference, and
caller-verified page labels, ordered citations and their source references.
The result includes XLSX bytes, media type, XML replacement count and the
decision/page/citation references. A missing run returns `None`.

The service refuses a missing or denied decision, wrong operation, missing
source reference, invalid page label and invalid citation mapping before SQL.
The reader refuses missing labels or incomplete citation partitions, and the
projection refuses incomplete findings before rendering. An explicit empty
citation tuple is permitted; absence of a citation entry is not.

## Checks

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/exports/test_xlsx_package.py tests/integration/exports/test_xlsx_read_query.py tests/integration/exports/test_xlsx_projection_prep.py tests/integration/exports/test_xlsx_writer_prep.py` — **48 passed**.
- `../../../.venv/bin/python -m compileall -q src/auditmanager/exports/xlsx/package.py tests/integration/exports/test_xlsx_package.py` — pass.
- Direct `governance_findings` on the task — `[]`.
- `git diff --check` — pass for tracked changes; newly added files were checked for trailing whitespace and terminal newlines.
- No full `make gate` under R-135; no live PostgreSQL read, HTTP policy check or `soffice` probe was run.

The focused tests inspect the generated ZIP and worksheet cells, including
canonical/member order, citation text and a literal `=literal` cell without a
formula element. Denied and missing source inputs are exercised as mutations
of an otherwise valid request and fail before SQL.

## Changed files

- `src/auditmanager/exports/xlsx/package.py`
- `tests/integration/exports/test_xlsx_package.py`
- `docs/program/tasks/W57B-INT-XLSX-PACKAGE-PREP-01.md`
- `docs/program/W57B-INT-XLSX-PACKAGE-PREP-01.md`

These four additive files are the task's exact allowlist. Other agents have
separate changes visible in the shared tree. This task did not edit existing
query, projection, writer, CSV or runtime files, and did not touch
`contracts/**`, migrations, provider lock, composition root, root dependencies
or global styles. It did not stage, commit or push.

## Contracts, limits and integration

No contract changed. `PreparedXlsx` is an internal composition result, not an
HTTP response or authorization grant. An `allow` value and source references
are assertions supplied by the future sealed caller: this module cannot
verify a principal's role, the run's exportable state, citation grounding or
page-label custody. The future W57b API/seal work must perform those checks,
provide a consistent transaction, reuse the CSV filename source and run a
spreadsheet application probe. Deleting the additive files before runtime
wiring is the rollback; no data migration or feature flag is needed.
