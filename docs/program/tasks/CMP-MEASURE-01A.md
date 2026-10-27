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
- changed files:
- commands/results:
- known limits:
- integration notes:
