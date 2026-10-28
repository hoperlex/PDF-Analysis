# Task CMP-MEASURE-01 — the whole deterministic comparison chain on the real set: admission, page profiles, matrix, series, tile cost, against the ceilings of ADR-0025 decisions 8 and 9

## Outcome
`docs/program/compare/MEASURE-ENGINE-01.md` gives, for the real four-version set
`/root/projects/PDF-Analysis/.local/comparison-measure/13AV-RD-EM2-PA/` driven through the product's own path on the lane's own
stack (the plain-PDF upload, the worker's `page_profile` items, `prepareComparisonMatrix` → `matrix_build`,
`startComparisonSeries` → `series_*` and `pair_result` items), per stage: wall time, CPU, peak RSS and peak address space of
the worker and of every child (`VmHWM` / `VmPeak` read from `/proc`, not `ru_maxrss`), bytes stored per kind, database rows per
table, the worst page and the worst pair, any item that ended without a result; the matrix and the series outcome; one
single-tile cost (20 pair tiles through `streamComparisonPairTile`, time and API-process RSS); a comparison with the ceilings and
caps of ADR-0025 decisions 8 and 9 and with the earlier figures, and the ADR defaults that should change, with numbers. The
original never compared this set (it is an audit project there), so no original statuses exist to compare against; the report
says so. After the measurement the real set directory is deleted (the owner's rule) and the lane's volumes are removed.

## Depends on
- CMP-SEAL-C0, CMP-SEAL-C1, CMP-WORK-01, CMP-PROFILE-01, CMP-PROFILE-QUEUE-01, CMP-INGEST-01, CMP-INGEST-02, CMP-MATRIX-01,
  CMP-ENGINE-01, CMP-VIEWER-01, CMP-SERIES-01, CMP-C1-FIX-A (all merged on `integration/compare-modules`)
- CMP-MEASURE-01A (`docs/program/compare/MEASURE-RENDER-01.md`, the render and extraction figures this report is compared with)

## Frozen inputs
- domain contract: `contracts/domain/v1/**` at the base
- API contract: `contracts/api/v1/openapi.json` `1.10.0`, 131 paths / 148 operations / 432 schemas (not changed)
- analysis/comparison/event contract: ADR-0025 decisions 8, 9 and both addenda; wave brief
  `docs/program/dispatch/CMP-WAVE-C1.md` sections 4 and 5; the reports `CMP-ENGINE-01.md` (sections 6, 10), `CMP-PROFILE-01.md`,
  `CMP-PROFILE-QUEUE-01.md`, `CMP-MATRIX-01.md`, `CMP-SERIES-01.md`, `CMP-INGEST-01.md`, `CMP-INGEST-02.md`, `CMP-WORK-01.md`,
  `CMP-VIEWER-01.md`, `CMP-C1-FIX-A.md`
- migration head: `0039_comparison_core` (not changed)
- base commit: `9861c9f9` on `integration/compare-modules` (engine `cmp-engine/3`, profile `cmp-profile/3`)

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: contract `1.10.0`, 131 paths / 148 operations / 432 schemas, head `0039_comparison_core`, the engine `cmp-engine/3` and the profile `cmp-profile/3`; the real set is four files (v4 byte-identical to v3) in a directory outside git

### P-01 — the base facts, re-read before any edit
- captured_at: 2026-10-29
- command: `.venv/bin/python -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas')"; cat VERSION; grep -n '^revision: str' db/migrations/versions/20261028_0039_comparison_core.py; grep -n '^ALGO_VERSION' src/auditmanager/comparison/engine/child/settings.py src/auditmanager/comparison/profile/limits.py; git rev-parse HEAD`
- captured_output:
  ```text
  contract 1.10.0 131 paths 148 operations 432 schemas
  0.9.0
  79:revision: str = "0039_comparison_core"
  src/auditmanager/comparison/engine/child/settings.py:20:ALGO_VERSION: Final[str] = "cmp-engine/3"
  src/auditmanager/comparison/profile/limits.py:59:ALGO_VERSION: Final[str] = "cmp-profile/3"
  9861c9f9d3faf64627737fda3280206805df110b
  ```
- interpretation: equal to the premise of the lane's brief (`1.10.0`, 131 / 148 / 432, head `0039_comparison_core`, base `9861c9f9`), so the lane did not STOP

### P-02 — the real set, by hashes and sizes only
- captured_at: 2026-10-29
- command: `sha256sum /root/projects/PDF-Analysis/.local/comparison-measure/13AV-RD-EM2-PA/v1.pdf /root/projects/PDF-Analysis/.local/comparison-measure/13AV-RD-EM2-PA/v2.pdf /root/projects/PDF-Analysis/.local/comparison-measure/13AV-RD-EM2-PA/v3.pdf /root/projects/PDF-Analysis/.local/comparison-measure/13AV-RD-EM2-PA/v4.pdf; stat -c '%s %n' /root/projects/PDF-Analysis/.local/comparison-measure/13AV-RD-EM2-PA/v?.pdf`
- captured_output:
  ```text
  973c76e7f8491ecb24e5e17e16cbbf7a1f04c25b3595f6605c371e6e4f459b45  /root/projects/PDF-Analysis/.local/comparison-measure/13AV-RD-EM2-PA/v1.pdf
  e19acb1db3651ee1d0e8995dacbfdd37ea3073c65d682f8e72c6d4aae4a95eaa  /root/projects/PDF-Analysis/.local/comparison-measure/13AV-RD-EM2-PA/v2.pdf
  614f23b15ee3235538a4574adf1a710ea184c6cdcd54f326ead2096469f57e3f  /root/projects/PDF-Analysis/.local/comparison-measure/13AV-RD-EM2-PA/v3.pdf
  614f23b15ee3235538a4574adf1a710ea184c6cdcd54f326ead2096469f57e3f  /root/projects/PDF-Analysis/.local/comparison-measure/13AV-RD-EM2-PA/v4.pdf
  8052267 /root/projects/PDF-Analysis/.local/comparison-measure/13AV-RD-EM2-PA/v1.pdf
  3050492 /root/projects/PDF-Analysis/.local/comparison-measure/13AV-RD-EM2-PA/v2.pdf
  14879065 /root/projects/PDF-Analysis/.local/comparison-measure/13AV-RD-EM2-PA/v3.pdf
  14879065 /root/projects/PDF-Analysis/.local/comparison-measure/13AV-RD-EM2-PA/v4.pdf
  ```
- interpretation: the set is the one the README describes (v3 and v4 share a SHA-256); nothing but hashes and sizes was read from it

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `tools/measure/**`
- `docs/program/compare/MEASURE-ENGINE-01.md`
- `docs/program/tasks/CMP-MEASURE-01.md`

## Lane resources
- foundation_instance: `auditmanager-cmp-measure-01`
- postgres_port: `57910`
- s3_api_port: `61910`
- s3_console_port: `61911`
- postgres_db: `auditmanager_cmp_measure_01`
- s3_bucket: `auditmanager-cmp-measure-01`

## Forbidden hotspots
- `src/**`, `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json`, `web/**`, `infra/**`,
  the `Makefile`, `scripts/**`, `tests/**`, `fixtures/**`; no new dependency; no change of any product value

## Non-goals
- no change of product code: if the chain fails on the real set, the lane records where and why with the typed reason, stops
  that stage and reports a FIX item
- no comparison with the original's statuses (the original never compared this set)
- no AI layer, no spend, no model call; no UI; nothing is pushed or merged
- the real set is never opened, read or viewed by a tool that shows content to the model, never sent to a model, never committed;
  neither is any raster, tile, preview, thumbnail or mask made from it; the report carries numbers, hashes and page sizes only

## Deliverables
- `tools/measure/comparison_chain.py`: the orchestrator (stack check, project and expert account, the upload over HTTP on the
  composed application, the real worker started as a child of the orchestrator with a recording wrapper, stage clocks, a `/proc`
  sampler of the worker's and the API process's trees, database and blob census) and the single-tile cost subcommand
- `docs/program/compare/MEASURE-ENGINE-01.md`: commands, tree, host load, every number with its method, the ADR defaults to
  change with numbers, FIX items
- records (numbers only) under `.local/comparison-measure/results-final/` (outside git)
- the task file's Handoff, as the last commit
- the real set directory deleted, the lane's containers and its two volumes removed by exact name

## Required tests
- command: `git diff --check`; `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/contract/program --basetemp=/tmp/pytest-cmp-measure-01/governance`
- expected: no output; governance tests pass

## Integration contract
The report's figures are the evidence for a dated addendum to ADR-0025 (decision 27: a value marked «revisable by
CMP-MEASURE-01» is revised only by an addendum that gives the measured figure, the command and the tree). The integrator writes
the addendum; this lane changes no ADR value by itself.

## Failure/idempotency/security cases
- stop if free disk is under 1.5 GiB (wait and re-check under 2.0 GiB); the host is shared: timings are upper bounds, the host
  load is recorded with every timing
- never kill a process the lane did not start; the lane signals only its own worker by PID
- the real set is client-like data: numbers only; nothing from it is committed or printed

## Rollback / feature flag
Not applicable (a measurement; no behaviour changes).

## Handoff
- changed files: `tools/measure/comparison_chain.py` (new: subcommands `run`, `tiles`, `bytes`, `report`, `worker`), `docs/program/compare/MEASURE-ENGINE-01.md` (new),
  `docs/program/tasks/CMP-MEASURE-01.md` (this file). `git diff --name-only 9861c9f9..HEAD` lists these three and nothing else: no `src/`, contract, migration, lock, dependency,
  `tests/`, `web/` or `infra/` file. Raw records (numbers only) are outside git in `.local/comparison-measure/results-final/chain-01/` (the run behind shim S-1) and
  `chain-01-as-shipped/` (the run as shipped).
- commands/results: run from the clean tree `47f8da2d` on the lane's own stack (host load 2.7 to 4.9, times are upper bounds). **As shipped the chain stops at the first page
  profile: `load_source_version` reads the manifest role `source.document`, the plain-PDF upload writes `comparison.source_pdf`; 4 of 4 `page_profile` items failed with
  `page_profile_source_unreadable` after 3 attempts (FIX-1).** Behind shim S-1 (a wrapper in the tool's processes that widens that one condition; `src/` untouched) the whole
  chain ran: admission 3.7 s; page profiles 229.6 s (85 of 85 pages `ready`; render child worst VmPeak 482.0 MiB, extraction child worst VmPeak 728.4 MiB, worst CPU and wall
  14.0 s; worker plus child 911.6 MiB at one instant); matrix 8.2 s (worker VmHWM 310.1 MiB; 30 rows, 0 unmatched, 0 groups, 0 splits, 0 duplicates, 0 bridges); series 158.7 s
  (29 engine children, worst VmPeak 568.6 MiB and 10.0 s; 26 fast-path pairs; worker VmHWM 362.7 MiB); v3 → v4 26 of 26 `same`, verdict `content_same`; no item or child ended without
  a result. Stored 96 137 739 B (sources 25 981 824, previews 35 274 498, thumbnails 1 239 477, archives 27 782 191 of which tiles 20 565 938, masks 5 859 749). 20 pair tiles:
  levels 0 and 1 about 350 ms, levels 2 and 3 about 45 ms, API process 200.5 → 314.7 MiB. No original statuses exist for this set. `git diff --check` clean; `tests/contract/program`
  28 passed; `tests/contract` minus the three `D-220` files 1 310 passed.
- known limits: one run on a shared host; the stages behind the defect are measured behind the shim; in-process HTTP transport; the upload readers' children are sampled at 50 ms,
  every other child reports its own VmHWM/VmPeak; one object of 85 pages (no 12 × 100 sheets, no 500-page version, no second slot); no AI work.
- integration notes: (1) FIX-1 is blocking and is a one-condition change in `comparison/profile/source.py::load_source_version` plus a test from the upload to the profile; until it
  is fixed no uploaded version can be compared. (2) ADR-0025 changes only by a dated addendum: no marked ceiling or cap needs to change (768 / 1024 MiB, 300 s, 600 s, 40 Mpx, 8 GiB all
  confirmed with the shares in report section 8.1); the bytes-per-project estimate should be replaced and the throughput written (section 8.2 items 1 and 2); the integrator decides
  the two open items (the worker's own footprint; a version-sized `page_profile` item against the 900 s watchdog). (3) FIX-2..5 of the report are observations and improvements, not
  blockers. (4) The real set directory is deleted and the lane's volumes are removed (report section 12).
