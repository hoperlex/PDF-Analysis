# Task W57B-INT-XLSX-SOFFICE-PROBE-01 — independent spreadsheet import check

task_id: W57B-INT-XLSX-SOFFICE-PROBE-01

## Outcome

An isolated, bounded LibreOffice probe opens W57b XLSX bytes and compares the semantic cell values in both worksheets before an export can be accepted. A focused synthetic workbook includes citations, member rows, severity totals, Unicode and formula-like text. The probe is offline and does not expose an API.

## Depends on

- `W57B-INT-XLSX-WRITER-PREP-01` — completed deterministic two-sheet XLSX writer.
- `W57B-INT-XLSX-PACKAGE-PREP-01` — completed export package composition.
- `W57B-INT-XLSX-CERTIFIED-SOURCES-PREP-01` — completed citation-to-XLSX source projection.
- `CFB-INT-DEV-PUBLISH-47` — completed development base `394a728f8a6f64ecb849f98fccdad687b79f282a`.

## Frozen inputs

- base commit: `394a728f8a6f64ecb849f98fccdad687b79f282a`
- API v1 SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain IDs SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations` SHA-256: `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- XLSX writer SHA-256: `4b34527038c246f957cebaa87534df6f4e14686b2caa0a71d3fe97ac9beabca1`;
- certified sources SHA-256: `f969187899a7eb794a258ede07e2777998854393813e68deed1503b69af93e90`;
- `docs/program/dispatch/W57-PLAN.md` B3.5 and R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: dev47 has a deterministic XLSX writer and citation source adapter, while its W57b plan still requires an independent `soffice` cell-by-cell import check.

### P-01 — exact base and open spreadsheet probe

- captured_at: 2026-10-16
- command: `git rev-parse HEAD; rg -n 'through .soffice --headless.|independent .soffice. cell-by-cell probe' docs/program/dispatch/W57-PLAN.md docs/program/W57B-INT-XLSX-WRITER-PREP-01.md; git ls-tree -r --name-only HEAD scripts/rehearsal/w57b/xlsx_soffice_probe.py tests/integration/exports/test_xlsx_soffice_probe.py`
- captured_output:
  ```text
  394a728f8a6f64ecb849f98fccdad687b79f282a
  docs/program/W57B-INT-XLSX-WRITER-PREP-01.md:57:independent `soffice` cell-by-cell probe. This pure writer cannot establish
  docs/program/dispatch/W57-PLAN.md:595:through `soffice --headless` under its own `-env:UserInstallation`, compared cell by cell.
  ```
- interpretation: the prior result names the missing independent probe and no corresponding script/test exists at the base. This says nothing about corpus qualification, sealed API or a successful spreadsheet import.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/rehearsal/w57b/xlsx_soffice_probe.py`
- `tests/integration/exports/test_xlsx_soffice_probe.py`
- `docs/program/tasks/W57B-INT-XLSX-SOFFICE-PROBE-01.md`
- `docs/program/W57B-INT-XLSX-SOFFICE-PROBE-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies and lockfiles;
- existing XLSX writer/query/package/source adapter, CSV and findings modules;
- API/routers, bootstrap/composition root, W54/W56b modules;
- `CURRENT_STATE.md`, UI/global styles, corpus, remote refs and tags.

## Non-goals

No `0024_norm_references` seal, XLSX API route/role, qualified corpus, real Run/Blob citation custody, production export, database or provider call, full gate or beta claim. A synthetic workbook passing LibreOffice does not certify a live user export.

## Deliverables

A standalone bounded XLSX-to-LibreOffice-to-XLSX cell comparison probe, focused mocked-runner tests and one real isolated probe after the integrator releases the host gate lane; task and result report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/exports/test_xlsx_soffice_probe.py -k 'not real_soffice'` while the host gate runs;
- after the integrator reports gate completion: `W57B_RUN_SOFFICE=1 PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/exports/test_xlsx_soffice_probe.py::test_real_soffice_roundtrip`;
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/program/test_wave_governance.py`;
- `python3 -m py_compile scripts/rehearsal/w57b/xlsx_soffice_probe.py tests/integration/exports/test_xlsx_soffice_probe.py`;
- `git diff --check`, frozen SHA-256 and `scripts/task_handoff.py` PASS.

## Observed acceptance status

- The real command was `W57B_RUN_SOFFICE=1 PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/exports/test_xlsx_soffice_probe.py::test_real_soffice_roundtrip`. It exited `1` on three bounded attempts; see the result report for the changing isolated subprocess environment and captured warning. W57b plan B3.5 is **not PASS**.
- The fake-runner tests and governance are green. The actual LibreOffice roundtrip remains open. No route, corpus or deployment acceptance can rely on this task yet.

## Integration contract

The future XLSX owner passes already rendered bytes to the probe during offline acceptance. The probe writes them only in a temporary directory, starts `soffice --headless` with its own `-env:UserInstallation`, a timeout and output directory, then reads both source and reopened workbook cells independently. It compares both sheet names, every nonempty cell's type/value and absence of formulas; empty cells may be omitted by the spreadsheet serializer. A mismatch or import failure raises a specific refusal and leaves no persistent artifact. The probe does not authorize the underlying data or download.

## Failure/idempotency/security cases

Missing binary, timeout, nonzero exit, absent converted file, malformed ZIP/XML, formula element or semantic cell difference all refuse. The temporary profile avoids another LibreOffice session. Formula-like user strings must remain strings. Repeated bytes produce the same comparison result.

## Rollback / feature flag

Unserved additive rehearsal tool; revert its bounded commit. No runtime feature flag or data rollback.

## Handoff

- changed files: four exact allowed paths;
- commands/results: result report and ignored technical handoff;
- known limits: synthetic workbook and offline import only;
- integration notes: cherry-pick after dev47; rerun against the final XLSX API output during W57b acceptance.
