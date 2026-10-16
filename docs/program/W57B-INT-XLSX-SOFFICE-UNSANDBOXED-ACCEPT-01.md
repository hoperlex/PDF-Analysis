# W57B-INT-XLSX-SOFFICE-UNSANDBOXED-ACCEPT-01 — synthetic import addendum

## Decision

The existing dev60 W57b **synthetic independent LibreOffice import/cell probe passes** when the installed LibreOffice 24.2.7 runs outside the tool sandbox. The script and test are unchanged from `2fe82f40f4ac2bf82f9778c28b2fd2a2b8e8deab`. This is an addendum to the original report, which accurately recorded three earlier exit-1 launches and an unverified probe at that time. It does not declare full W57b B3.5 PASS.

## Bounded diagnosis on 2026-10-16

Two real, headless `soffice` conversions used separate private `HOME`, `XDG_RUNTIME_DIR`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME` and `-env:UserInstallation` directories under `/tmp/w57b-soffice-triage.wuYvV7`, with a 45-second timeout. They changed no host service, package or shared cache.

| Input | LibreOffice exit | Converted file | Source/imported semantic cells |
| --- | ---: | --- | --- |
| Independently assembled minimal OOXML `simple.xlsx` | 0 | `simple-output/simple.xlsx`, 5,389 bytes | 2/2, equal; sheet `Simple` |
| Existing W57b test fixture `w57b.xlsx` | 0 | `w57b-output/w57b.xlsx`, 8,054 bytes | 54/54, equal; sheets `Сводка`, `Замечания` |

The W57b source SHA-256 was `66a1b24d63b37c6e335258801acc69cd15a9bd5ebfd528c06510e0a6cf78b524`; the reimported file SHA-256 was `a9df07250b8fb2fa292de110c4c8131ef81481e6336e67baa5a58ac54ea242be`. The files differ as ZIP bytes, while independently parsed sheet names and all 54 nonempty cell types and values match. The simple source/imported SHA-256 values were `2adc852fdc4a30862591520118752bfeaabf29a7344e3c42db6b326ec7406d5b` and `51000d6a17a958fc2f061fef60de6a7b5689746cebb31362a752dfdbbaf89081`.

Both successful conversions still printed `Warning: failed to launch javaldx - java may not function correctly`. Thus that warning alone was not the cause of the earlier exit-1 result. The difference between the three failed constrained launches and these successful runs is the sandbox execution boundary; the evidence supports an environment restriction as the likely cause, not an XLSX incompatibility. It does not isolate a specific denied system call.

The exact original opt-in command was then repeated once outside the tool sandbox, without editing code:

```text
W57B_RUN_SOFFICE=1 PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/exports/test_xlsx_soffice_probe.py::test_real_soffice_roundtrip
.                                                                        [100%]
1 passed in 0.95s
```

This exercises `probe_xlsx` end to end, including its temporary profile, real conversion, reimport and semantic cell comparison. The two manual conversions and this one opt-in rerun are the only real LibreOffice launches in this addendum. The original three failed launches are not erased or relabelled.

Programme governance checks on this docs-only addendum: **16 passed**, with five warnings from cleanup of shared `/tmp/pytest-of-root/garbage-*` directories. The two frozen probe/test file hashes match the task; the repository diff contains only this task and result report.

## Boundary

The accepted evidence concerns a synthetic W57b workbook only. The final XLSX API route, role, qualified corpus/Run/Blob custody and actual user export bytes remain open under B3.5. The probe compares sheet names and nonempty cell values, not layout, styles, print settings or recalculation. No public contract, migration, runtime code, dependency, remote ref or tag changes here. Rollback is a documentation revert.
