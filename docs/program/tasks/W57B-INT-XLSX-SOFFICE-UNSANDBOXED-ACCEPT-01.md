# Task W57B-INT-XLSX-SOFFICE-UNSANDBOXED-ACCEPT-01 — synthetic import acceptance addendum

task_id: W57B-INT-XLSX-SOFFICE-UNSANDBOXED-ACCEPT-01

## Outcome

Record a reproducible, real LibreOffice acceptance of the existing W57b synthetic XLSX cell probe on the published development tree. This closes only the independent synthetic import uncertainty left by the original probe report; the live B3.5 export, route, role and custody acceptance remain open.

## Depends on

- `W57B-INT-XLSX-SOFFICE-PROBE-01` — completed probe and original failed host evidence.
- `CFB-INT-DEV-PUBLISH-60` — completed development base containing that probe.

## Frozen inputs

- base commit: `2fe82f40f4ac2bf82f9778c28b2fd2a2b8e8deab`
- API v1 SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`
- migration head: `0023_norm_citations`
- probe script SHA-256: `b5800e371fea6c51a2d8912837f4ba451b5ede49d250530de4dc769eb79472f9`
- opt-in test SHA-256: `b35d28f22ba5318a3ae79fa5fd91707ca7c15c22b0dd9ef2dbbb4654a55acb69`
- W57 plan B3.5 and R-135; no contract or runtime code change.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the dev60 probe's real LibreOffice test remained red in three prior constrained launches, and neither the script nor the test has changed.

### P-01 — exact base and frozen probe

- captured_at: 2026-10-16
- command: `git rev-parse HEAD; sha256sum scripts/rehearsal/w57b/xlsx_soffice_probe.py tests/integration/exports/test_xlsx_soffice_probe.py`
- captured_output:
  ```text
  2fe82f40f4ac2bf82f9778c28b2fd2a2b8e8deab
  b5800e371fea6c51a2d8912837f4ba451b5ede49d250530de4dc769eb79472f9  scripts/rehearsal/w57b/xlsx_soffice_probe.py
  b35d28f22ba5318a3ae79fa5fd91707ca7c15c22b0dd9ef2dbbb4654a55acb69  tests/integration/exports/test_xlsx_soffice_probe.py
  ```
- interpretation: both the code and test under acceptance are identical to dev60; this does not by itself establish import success.

### P-02 — original failed observation

- captured_at: 2026-10-16
- command: `rg -n 'Real command:|Attempt three:' docs/program/W57B-INT-XLSX-SOFFICE-PROBE-01.md`
- captured_output:
  ```text
  22:- Real command: `W57B_RUN_SOFFICE=1 PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/exports/test_xlsx_soffice_probe.py::test_real_soffice_roundtrip` — exit `1` on three bounded attempts. Attempts two and three ran this argv through a small external `psutil` wrapper solely to sample process tree RSS and host available memory.
  25:- Attempt three: same isolation plus a subprocess-only private `HOME` and `SAL_USE_VCLPLUGIN=svp`. Exit `1` in 0.24 seconds with the same warning. Peak tree RSS 163.1 MiB; minimum host available 5044.8 MiB. No further LibreOffice process was started.
  ```
- interpretation: this addendum records new evidence without rewriting the original failed observation.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/W57B-INT-XLSX-SOFFICE-PROBE-01.md`
- addendum_path: `docs/program/W57B-INT-XLSX-SOFFICE-UNSANDBOXED-ACCEPT-01.md`

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W57B-INT-XLSX-SOFFICE-UNSANDBOXED-ACCEPT-01.md`
- `docs/program/W57B-INT-XLSX-SOFFICE-UNSANDBOXED-ACCEPT-01.md`

## Forbidden hotspots

- `scripts/rehearsal/w57b/xlsx_soffice_probe.py` and `tests/integration/exports/test_xlsx_soffice_probe.py`;
- `contracts/**`, `db/migrations/**`, root dependencies and lockfiles;
- XLSX writer, API/routers, bootstrap/composition root and global styles;
- `CURRENT_STATE.md`, corpus, remote refs and tags.

## Non-goals

No live Run or Blob evidence, qualified corpus, `0024_norm_references` seal, XLSX API route or download authorization, visual spreadsheet inspection, full gate, beta or deployment claim.

## Deliverables

This task and its result addendum only. The unchanged opt-in test executes the actual probe with LibreOffice in a temporary profile. The report records both successful manual conversions, their output paths, semantic cell comparison and the opt-in test result.

## Required tests

- `W57B_RUN_SOFFICE=1 PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/exports/test_xlsx_soffice_probe.py::test_real_soffice_roundtrip` outside the tool sandbox: one PASS required.
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/program/test_wave_governance.py`: PASS.
- `git diff --check`, exact two-path diff, clean committed tree and `scripts/task_handoff.py` PASS.

## Integration contract

The integrator may cite a passing independent synthetic LibreOffice import/cell probe on dev60. The integrator must retain B3.5 as open until an actual export route, role and final rendered bytes with qualified data are accepted. The original three failed launches remain historical evidence; this report supplies the successful execution-context comparison.

## Failure/idempotency/security cases

Prior sandboxed attempts exited 1 and yielded no converted file. Two bounded conversions with private HOME/XDG/UserInstallation outside that boundary exited 0, including the deterministic W57b workbook. The same `javaldx` warning appeared on success, so it is not by itself a failure diagnosis. The opt-in test's normal refusal behavior and temporary cleanup are unchanged; no credentials or services are used.

## Rollback / feature flag

Documentation-only evidence addendum; revert this commit if its recorded facts are disproven. No runtime feature flag, migration or data rollback applies.

## Handoff

- changed files: the two exact allowed documentation paths;
- commands/results: the result report and ignored technical handoff;
- known limits: synthetic workbook, no live export or beta acceptance;
- integration notes: cherry-pick only onto a descendant with unchanged probe/test hashes and keep the original report immutable.
