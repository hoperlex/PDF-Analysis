# W57B-INT-XLSX-SOFFICE-PROBE-01 — independent XLSX import result

## Result

Added an offline rehearsal probe for the deterministic W57b workbook. It writes supplied rendered bytes to a temporary XLSX, invokes LibreOffice with a private `UserInstallation` profile, then independently reads the converted XLSX. The probe compares the two expected worksheet names and every nonempty cell's semantic type and value, including explicit numeric zero, Unicode, multiline citations and formula-like strings. It refuses a formula element, changed cell, failed conversion or missing output. All temporary files and the profile are removed when the check exits.

This tool is unserved. A successful synthetic import is evidence of spreadsheet interoperability only; it does not qualify corpus bytes, seal `0024`, authorize a download route or approve deployment.

## Files

- `scripts/rehearsal/w57b/xlsx_soffice_probe.py`
- `tests/integration/exports/test_xlsx_soffice_probe.py`
- `docs/program/tasks/W57B-INT-XLSX-SOFFICE-PROBE-01.md`
- `docs/program/W57B-INT-XLSX-SOFFICE-PROBE-01.md`

## Verification

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/exports/test_xlsx_soffice_probe.py -k 'not real_soffice'`: **4 passed**.
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/program/test_wave_governance.py`: **16 passed**.
- `python3 -m py_compile scripts/rehearsal/w57b/xlsx_soffice_probe.py tests/integration/exports/test_xlsx_soffice_probe.py`: **PASS**.
- Full focused test module without the opt-in environment variable: **4 passed, 1 skipped**.
- Real command: `W57B_RUN_SOFFICE=1 PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/exports/test_xlsx_soffice_probe.py::test_real_soffice_roundtrip` — exit `1` on three bounded attempts. Attempts two and three ran this argv through a small external `psutil` wrapper solely to sample process tree RSS and host available memory.
- Attempt one: exit `1` in 0.42 seconds; no imported workbook and original refusal lacked stdout/stderr. The probe now includes a bounded diagnostic.
- Attempt two: isolated `XDG_RUNTIME_DIR`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME` and `UserInstallation` in a temporary directory. Exit `1` in 0.23 seconds with `Warning: failed to launch javaldx - java may not function correctly`. Peak pytest/LibreOffice tree RSS 163.2 MiB; minimum host available 5061.9 MiB.
- Attempt three: same isolation plus a subprocess-only private `HOME` and `SAL_USE_VCLPLUGIN=svp`. Exit `1` in 0.24 seconds with the same warning. Peak tree RSS 163.1 MiB; minimum host available 5044.8 MiB. No further LibreOffice process was started.
- Frozen contract, writer, adapter and migration hashes: match the task values.

## Integration contract and limits

The independent import gate remains **unverified; W57b B3.5 is not PASS**. The warning alone does not prove whether the cause is host LibreOffice setup or incompatibility in the generated XLSX; the current host cannot settle that distinction. Run the opt-in `test_real_soffice_roundtrip` after resolving the import failure and compare final rendered export bytes when the API route and qualified data are available. This synthetic result alone cannot certify live Run/Blob custody. The probe accepts at most 32 MiB and bounds LibreOffice to 45 seconds. It compares cell values and sheet names, not visual layout, styles, formulas, print settings or spreadsheet recalculation.

The change has no runtime wiring, contract or migration edits, feature flag, database operation or remote publication. Rollback is a revert of the bounded task commit.
