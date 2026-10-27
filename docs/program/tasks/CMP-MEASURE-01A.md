# Task CMP-MEASURE-01A — render and extraction cost of comparison pages, measured before SEAL-C0

## Outcome
`docs/program/compare/MEASURE-RENDER-01.md` gives measured time, peak RSS and bytes for rendering and text/line
extraction of comparison pages (real set, synthetic corpus, realistic A1) inside a child process under a kernel
memory ceiling, so that SEAL-C0 and CMP-PROFILE-01 fix the values ADR-0025 decisions 8 and 9 marked «revisable by
CMP-MEASURE-01» from measurement.

## Depends on
- CMP-FIXTURES-01 (merged, `121387bb`), ADR-0025 (merged)

## Frozen inputs
- domain contract: not changed
- API contract: not changed
- analysis/comparison/event contract: not changed
- migration head: not changed
- base commit: `121387bb` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `tools/measure/comparison_render.py`
- `docs/program/compare/MEASURE-RENDER-01.md`
- `docs/program/tasks/CMP-MEASURE-01A.md`

## Forbidden hotspots
- `src/**`, contracts, migrations, root locks, `web/**`, tests, fixtures; no new dependency

## Non-goals
- no comparison engine (numpy/OpenCV are not installed yet); render, rasterise to PNG, words and lines only

## Deliverables
- a measurement script that, per page, in a child process under `resource.RLIMIT_AS` (default 768 MiB, settable),
  renders with `pypdfium2` at 200, 150 and 100 dpi, records wall time, peak RSS of the child (`ru_maxrss`), pixel count,
  the size of a 1400 px preview PNG, a 220 px thumbnail PNG and a 512 px tile pyramid estimate, and separately the time
  and RSS of `pdfplumber` words-with-boxes plus lines extraction; a page that overruns the ceiling is reported as such
- the report with the commands, the host facts (`free -g`, `nproc`, `df -h /` at run time) and tables per input:
  the real set `/root/projects/PDF-Analysis/.local/comparison-measure/13AV-RD-EM2-PA/` (figures only: page sizes, times,
  bytes — never text or images of its content), `fixtures/comparison/vs1/*.pdf`, `fixtures/comparison/sp1/*.pdf`, and
  the realistic A1 generated into a temporary directory by `tools/fixtures/comparison/realistic_a1.py` (both producers)
- a recommendation table for ADR-0025 decisions 8 and 9: per-item ceiling, pixel cap per page, registration downsample
  dpi, bytes per page and per 12-version × 100-sheet project, against a 4 GiB production host

## Required tests
- command: `git diff --check`
- expected: no output; the script runs end to end on the inputs above with the main venv

## Integration contract
SEAL-C0 and CMP-PROFILE-01 cite the report's figures; ADR-0025 values change only by a dated addendum citing it.

## Failure/idempotency/security cases
- the real set is client-like data: nothing of its content leaves the host or enters the repository; only numbers
- stop if free disk is under 1.5 GiB; never kill processes other than the measurement's own children

## Rollback / feature flag
Not applicable (a measurement).

## Handoff
- changed files: `tools/measure/comparison_render.py` (new, commit `64f7e2f0`), `docs/program/compare/MEASURE-RENDER-01.md` (new),
  `docs/program/tasks/CMP-MEASURE-01A.md` (this section). `git diff --name-only 121387bb..HEAD` lists these three and nothing else
  (the task file itself arrived with `a3bde34a`): no `src/**`, contract, migration, root lock, `web/**`, test or fixture file; no
  dependency added (the venv's `pypdfium2`, `pdfplumber`, Pillow only).
- commands/results: the final pass ran from the clean tree at `64f7e2f0` (19:44-20:06 +05:00, one child at a time, host load 3 to 19):
  `tools/measure/comparison_render.py run|table|levels|fit` over the real set (v1, v2, v3; v4 equals v3 by SHA-256), VS-1, SP-1 and the
  generated realistic A1 (producers A and B, light, and a 400 001-element variant); 642 child records, host facts and commands in the
  report. Main pass: 450 of 450 children `ok` under 768 MiB / 300 s / 600 s, no page overran. Worst render by memory: real v3 p13
  (1680x1190 mm) at 150 dpi, 69.7 Mpx, 4.2 s, RSS 717 MiB / VmPeak 736 MiB; by time: real v1 p8 (1682x1189 mm) at 200 dpi, 124.0 Mpx,
  8.5 s, RSS 663 MiB. Realistic A1 at 200 dpi: 1.8 s, RSS 196 MiB, preview 396 665 B, thumbnail 18 006 B, 182-tile pyramid 3 905 287 B.
  Extraction: worst real 11.2 s / RSS 632 MiB (198 694 pdfplumber objects), 400 001-element A1 17.4 s / RSS 654 MiB. Ceilings: a 124 Mpx
  page needs 704 MiB, the 40 Mpx-capped pages pass at 384 MiB, the heaviest extractions need 704 MiB. `git diff --check`: no output.
  Guards shown failing in report section 5.4 (ceiling removed from a copy of the script: the 120 MiB job passes; CPU and wall probes).
- known limits: one shared host (times depend on load; memory repeats within 1 MiB); no engine (numpy/OpenCV absent), so the 40 Mpx cap
  is supported for rendering only; tiles on request not timed; PNG only; realistic A1 is synthetic; one real set; extraction measured
  to 198 694 objects, larger figures in the report are a fitted model; RSS under a ceiling is elastic (section 5.2).
- integration notes: (1) ADR-0025 changes only by a dated addendum citing the report: candidate values are in report section 6
  (keep 768 MiB for render/tile children; 1024 MiB or a pre-check for the child that runs pdfplumber; any end without a result is
  `RENDER_FAILED`; keep 40 Mpx with the dpi formula; do not keep the whole tile pyramid as blobs: 4.7-6.1 GB per 1 200 vector pages,
  11.8 GB for scans). (2) `CMP-INGEST-01`: real set page `v1.pdf` p7 has 536 426 elements, above `PAGE_ELEMENTS_MAX` 400 000, so the
  envelope would refuse that version; 13 of 59 pages exceed the 75 486 the envelope comment calls the real maximum. (3) The real set is
  still in `.local/comparison-measure/13AV-RD-EM2-PA/`; its README says to delete it after the measurement. The generated A1 PDFs were
  deleted. Raw records: `.local/comparison-measure/results-final/` (numbers only, outside git).
