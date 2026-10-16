# W57B-INT-CERTIFIED-EXPORT-CHAIN-PREP-01 — unserved XLSX use-case result

## Result

The new `prepare_certified_xlsx_package` entrypoint connects the completed XLSX run/page preflight, a caller-injected W57a verified-citation read, the certified-source adapter and the existing package renderer. It checks the caller-supplied export decision shape before any source read, compares persisted Run/project/version/state/profile/snapshot/set identity to the returned citation read, and rechecks the Run pin after rendering. An absent or changed pin refuses the candidate bytes.

This is route preparation only. The caller still owns the consistent read transaction, the real principal/role decision, registered v3 profile identity and citation-reader port. Constructed DTOs and decision references do not independently prove those claims.

## Changed files

- `src/auditmanager/exports/xlsx/certified_package.py`
- `tests/integration/exports/test_xlsx_certified_package.py`
- `docs/program/tasks/W57B-INT-CERTIFIED-EXPORT-CHAIN-PREP-01.md`
- `docs/program/W57B-INT-CERTIFIED-EXPORT-CHAIN-PREP-01.md`

## Verification

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/exports/test_xlsx_certified_package.py tests/integration/exports/test_xlsx_certified_sources.py tests/integration/exports/test_xlsx_package.py` — **33 passed**. The new tests inspect actual rendered XLSX citation/page cells and prove refusal for a foreign preflight Run, foreign citation snapshot, pin changed after rendering and denied decision before source reads. They fake only the already separately tested page/Blob preflight and the not-yet-public citation-reader port; they do not exercise real DB/S3.
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/program/test_wave_governance.py` — **16 passed**; pytest reported 10 shared `/tmp/pytest-of-root` cleanup warnings from other concurrent test directories.
- `python3 -m py_compile src/auditmanager/exports/xlsx/certified_package.py tests/integration/exports/test_xlsx_certified_package.py` — **PASS**.
- Frozen API/stage/domain/error/0023 and four predecessor source SHA-256 values match the task; whitespace and exact changed-path proof are in the SHA-bound handoff.

## Integration and limits

The later XLSX API/service owner injects a findings-public wrapper around `read_verified_citations`, supplies its sealed v3 profile ID and established `_EXPERT` decision, and calls this use case in the same consistent read transaction as the verified Blob reader. The HTTP router receives only the returned bytes and the CSV filename source; it does no SQL or storage access. The 0024 contract/role seal must precede serving. This chain is not a grant of authorization or an assertion that the corpus, source PDF bindings or Run/Blob data exist on a stand.

The W57b B3.5 independent LibreOffice probe remains failed/unverified on this host as recorded in `W57B-INT-XLSX-SOFFICE-PROBE-01.md`; no `soffice` process was run for this task. There is no API route, migration, contract, composition-root, dependency, UI, DB/S3 or remote-ref change. No full gate was run under R-135. Rollback is a revert of the four additive files; no runtime flag or data rollback is needed.
