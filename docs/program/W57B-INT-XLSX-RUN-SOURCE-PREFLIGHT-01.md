# W57B-INT-XLSX-RUN-SOURCE-PREFLIGHT-01 — exportable run and verified XLSX page source

## Result

`read_xlsx_run_source_preflight` now reads one exact run's state and version,
applies the existing CSV export rule from the frozen terminal semantics, and
reads verified page labels from that version's immutable portal companion. It
returns the run identity, version identity, state and `VerifiedPageLabels` as an
immutable value. The caller supplies one consistent read transaction and the
Blob reader. The preflight performs no SQL write or transaction commit.

The run and source checks happen in order: invalid input before SQL; missing or
mismatched run and non-publishing state before any source or Blob read; version
identity before source lookup; manifest/Blob and every page label before a
result. A `partial` run is exportable under the same policy as CSV.

## Checks

- `nice -n 19 ionice -c3 ../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/exports/test_xlsx_preflight.py tests/integration/exports/test_xlsx_source_labels.py tests/integration/exports/test_xlsx_package.py` — **43 passed**.
- `../../../.venv/bin/python -m compileall -q src/auditmanager/exports/xlsx/preflight.py tests/integration/exports/test_xlsx_preflight.py` — pass.
- Direct `governance_findings` on the task — `[]`.
- `git diff --check` and the exact allowed-path comparison — pass.
- No real PostgreSQL/S3 read, `soffice` probe or complete `make gate` was run;
  R-135 defers the full gate, and this is an unactivated read preflight.

## Changed files

- `src/auditmanager/exports/xlsx/preflight.py`
- `tests/integration/exports/test_xlsx_preflight.py`
- `docs/program/tasks/W57B-INT-XLSX-RUN-SOURCE-PREFLIGHT-01.md`
- `docs/program/W57B-INT-XLSX-RUN-SOURCE-PREFLIGHT-01.md`

The four paths exactly match this task's allowlist. Existing XLSX and CSV
modules, API security/routes, contracts, migrations, composition, root locks,
global styles, corpus, `CURRENT_STATE.md`, tags and remote refs were not edited.

## Contracts, limits and integration

No shared contract or migration changed. This result can supply page labels
and their source reference to the existing XLSX package only after the future
sealed caller establishes the guarded principal, the exact run, verified
citations and attribution. The preflight neither grants `exportRunXlsx` nor
creates an `ExportAuthorization`; the current API and role register still have
no such operation. At migration head `0022_findings_v2`, persisted per-finding
normative citations are absent, so the package and this preflight remain
unexposed. The portal companion must label every page unambiguously; a bare
PDF or an unlabelled page refuses.

W57a and W57b seal owners must first add the normative citation relation and
XLSX operation/role. Then one XLSX API owner can bind citations, guarded role,
state, source labels and package bytes within one consistent read, reuse the
CSV route's download-name source and run the independent spreadsheet probe.
Removing these additive files before runtime wiring is the rollback; no data
rollback or feature flag is needed.
