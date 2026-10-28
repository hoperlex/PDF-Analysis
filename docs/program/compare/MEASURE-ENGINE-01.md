# MEASURE-ENGINE-01 — the whole deterministic comparison chain on the real set: admission, page profiles, matrix, series, tile cost

- Task: `tasks/CMP-MEASURE-01.md`. It feeds the dated addendum to ADR-0025 that decision 27 asks for: this report changes no ADR
  value by itself. Earlier figures it is compared with: `MEASURE-RENDER-01.md`, `CMP-ENGINE-01.md` section 6, `CMP-PROFILE-01.md`
  section 6, `CMP-C1-FIX-A.md` section 3 item 8.
- Tree: branch `agent/cmp-measure-01`, base `9861c9f9` on `integration/compare-modules` (contract `1.10.0`, 131 paths / 148
  operations / 432 schemas, head `0039_comparison_core`, engine `cmp-engine/3`, profile `cmp-profile/3`). The chain was run from
  commit `47f8da2d` with a clean tree (`git status --short` empty; `tools/measure/comparison_chain.py` as committed there). Two later
  commits touch only the read-only subcommands `report` (labels) and `bytes` (new); the figures of `tiles` come from `47f8da2d` too.
- Measured on 2026-10-29, 04:00–04:12 (+05:00), on the development host of the programme, which is shared with other projects: 8 vCPU
  (AMD EPYC 9655), 11.6 GiB RAM of which 3.9 GiB available at the start, 16 GiB swap (5.1 GiB used), kernel 6.8.0-147, `df -h /` 8.6 GiB
  free. Python 3.12.3, `numpy` 2.5.4, `opencv-python-headless` 4.14.0.94, `pypdfium2` 5.13.0, `pdfplumber` 0.11.10, `pypdf` 6.18.0,
  Pillow 12.3.0. **Every time is an upper bound: the one-minute load average was 2.66 at the start of the chain, 4.27 to 4.86 during the
  profile and series stages** (other lanes were running); memory figures are not load-sensitive.
- Raw records (JSON lines and JSON, numbers only) are outside git, under `.local/comparison-measure/results-final/chain-01/`
  (the run), `chain-01-as-shipped/` (the run without the shim of section 2) and their `report.txt` (printed by the tool's `report`);
  every figure below is a field of those records or arithmetic on them.
- **The real set** `.local/comparison-measure/13AV-RD-EM2-PA/` (four versions of one ЭМ document; v4 byte-identical to v3; 85 pages;
  sizes A4 to 2A0) was driven through the product by code only. No page, word, text or raster of it was opened, printed, viewed or
  sent to a model; this report holds numbers, hashes, file names and page sizes only. The set was deleted afterwards (section 12).
  **The original never compared this set** (it is an audit project there; `CMP-WAVE-C1.md` section 5 item 4), so there are no original
  statuses to compare the engine's with; the statuses below are a load and a plausibility record, not a verdict.

## 1. Result

1. **The chain does not run as shipped.** The first stage that reads a version admitted through the plain-PDF upload, the page profile,
   fails for every page: `load_source_version` reads the manifest role `source.document`, the upload writes `comparison.source_pdf`
   (section 2). Typed reason `page_profile_source_unreadable`, 4 of 4 `page_profile` items failed after 3 attempts each. It is a
   product defect, found on this set and on the synthetic corpus alike; **FIX-1**. Nothing was patched in `src/`.
2. With a recording shim that widens that one condition in the processes the tool starts (shim S-1, section 2), **the whole chain ran
   to the end on the real set: 85 of 85 pages `ready`, 29 engine children and 26 byte-identical fast paths for 55 pair results, 3
   transitions `completed`, no item and no child ended without a result.** Wall: admission 3.7 s, page profiles 229.6 s, matrix 8.2 s,
   series 158.7 s (400 s in all); CPU of the worker and its children 335 s.
3. **Nothing came near a ceiling.** Worst child address space against its ceiling: render 482.0 MiB of 768 (63 %), extraction 728.4 MiB of
   1024 (71 %), engine 568.6 MiB of 768 (74 %), tile 81.0 MiB of 768, upload reader 92.7 MiB of 768; worst CPU of any child 14.0 s of 300 s,
   worst wall 14.0 s of 600 s; the largest working raster is 39.59 Mpx of 40 and no page was refused; 96.1 MB stored of 8 GiB (1.1 %).
4. **What the ADR does not bound is the worker process itself:** resident set 179 MiB idle, 288 MiB while building profiles, **310 MiB
   in the matrix build, 363 MiB while preparing a pair of two 187 000-segment pages (even on the fast path with no child)**, 284 MiB left
   resident when the chain was done, address space 2.7 GiB; and at one instant the worker plus its extraction child held **912 MiB**.
5. Outcome: matrix 30 rows, 0 unmatched, 0 groups, 0 splits, 0 duplicates, 0 bridges, 14 scan cells; series `completed`; **v3 → v4: 26
   sheets, 26 `same`, verdict `content_same`**; v1 → v2: 11 compared (4 same, 7 `needs_review`), 7 added, 4 removed; v2 → v3: 18
   compared (7 same, 5 different, 6 `needs_review`), 8 added.
6. **ADR defaults:** no marked ceiling or cap should change on this evidence (section 8). One estimate should be replaced (bytes per
   project), the throughput of decision 6 can be written (1 333 pages an hour, 658 engine pairs an hour, one worker slot), and two
   things the ADR leaves open want a decision: the worker's own footprint and the 900 s watchdog against a version-sized
   `page_profile` item.

## 2. The defect found, and the shim

`comparison/profile/source.py::load_source_version` (`:58-72`) takes the manifest entry of role `MANIFEST_ROLE_SOURCE_DOCUMENT` and
raises `analysis_input_invalid` / `source_unreadable` otherwise. `CMP-INGEST-01` admits a plain PDF under the distinct role
`comparison.source_pdf` (`MANIFEST_ROLE_COMPARISON_PDF`, so that a run refuses it: ADR-0025 decision 11). The page-profile builder
(`profile/builder.py:160`), the engine (`engine/service.py:243-244`) and the tile reader (`profile/reader.py:141`) all call that function, so
**a version admitted through the product's own upload cannot be profiled, compared or tiled**. The suites of every lane seed
`source.document` (`tests/integration/comparison/series/conftest.py`, `Lab.seed_sources`) and no test drives the upload into the profile.

Evidence, run on the real set without the shim (`chain-01-as-shipped`, tree `47f8da2d`): admission passed (3.6 s, 4 files `verified`);
the four `page_profile` items ran 3 attempts each (`max_attempts` 3) and ended `failed`, `failure_reason`
`page_profile_source_unreadable`, 12 attempts, 82.2 s of wall (the retry back-off); 0 profile rows; the database holds
`input_manifest_entry` rows of role `comparison.source_pdf` only. The same stop was reproduced on `fixtures/comparison/vs1` (3 versions).

**Shim S-1** (`install_source_role_shim` in the tool): inside the worker and the tile process the tool starts, the module attribute
`load_source_version` of `profile.source`, `profile.builder`, `profile.reader` and `engine.service` is replaced by the product's function
with `item.role in (source.document, comparison.source_pdf)`. No file of `src/` is changed; the run records `shim: source_role` in
`outcome.json`. **Every figure from section 4 on is measured behind the shim**, and is what the product will do once the one condition is
fixed; the shim adds nothing to the cost (it is the same query).

## 3. What was run

```
cd /root/projects/PDF-Analysis/.local/worktrees/cmp-measure-01
sed ... .env.example > .env          # the six lane values: instance auditmanager-cmp-measure-01, ports 57910/61910/61911, db auditmanager_cmp_measure_01, bucket auditmanager-cmp-measure-01
make up FOUNDATION_PYTHON=/usr/bin/python3.12 ; make migrate FOUNDATION_PYTHON=/usr/bin/python3.12      # head 0039, empty database
set -a; . ./.env; set +a; export PYTHONPATH=$PWD/src AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent
R=/root/projects/PDF-Analysis/.local/comparison-measure/results-final
.venv/bin/python tools/measure/comparison_chain.py run --results $R/chain-01-as-shipped --label real-as-shipped      # as shipped (stops at the profiles)
# the stack reset to an empty database: make down; docker volume rm auditmanager-cmp-measure-01-postgres-data auditmanager-cmp-measure-01-s3-data; make up; make migrate
.venv/bin/python tools/measure/comparison_chain.py run --shim --results $R/chain-01 --label real-shim-s1
.venv/bin/python tools/measure/comparison_chain.py tiles  --results $R/chain-01        # 20 pair tiles
.venv/bin/python tools/measure/comparison_chain.py bytes  --results $R/chain-01        # distinct blobs per kind
.venv/bin/python tools/measure/comparison_chain.py report --results $R/chain-01 > $R/chain-01/report.txt
```

**Through the product's own path.** The composed application (`create_app`) runs in the orchestrating process, which is therefore *the API
process*; its routers are driven over HTTP by `starlette.testclient.TestClient` with a signed expert credential: `createProject`,
`createComparisonUpload`, one `uploadComparisonUploadPart` per file (every file is under the 16 MiB part), `completeComparisonUploadFile`
(the product reads each PDF there in two ceilinged children), `getComparisonUploadProposal`, `confirmComparisonUploadSet`,
`listComparisonVersionOrders`, `prepareComparisonMatrix`, `getComparisonMatrix`, `startComparisonSeries`, `getComparisonSeries`,
`listComparisonSheetPairs`. **The worker is the real one**: `python -m auditmanager.workers serve` (`EXECUTION_ROLE=worker`,
`AUDITMANAGER_COMPARISON_MODULES=versions`, one slot) started as a child of the orchestrator through `comparison_chain.py worker`, which
wraps four points and changes nothing else: `SubprocessChildRunner.run` (one record per child: the child's own `VmHWM`, `VmPeak`, wall, CPU),
`profile.builder.profile_page` (per page: status, sizes of the stored members), `engine.service._compute` (per pair) and
`ComparisonWorkRunner.execute` (per work item: wall, CPU of the worker and of its children, the worker's `VmHWM` with the high-water mark
reset at the item's start, `VmPeak`). The transport is in-process: no proxy, no network between client and API.

**Method of each figure.**

| Figure | How |
| --- | --- |
| memory of a child | the child's **own** `VmHWM` (peak resident set) and `VmPeak` (peak address space, the quantity `RLIMIT_AS` limits), read by the child from `/proc/self/status` and sent in its last JSON line; `ru_maxrss` from `wait4` is not used (it carries the parent's resident set at `fork`: `CMP-ENGINE-01` section 6) |
| memory of the worker | per work item, `VmHWM` read after the item with the mark reset (`clear_refs` 5) before it; `VmPeak` cumulative; `VmRSS` at stage ends; a sampler reads the worker, its children and the orchestrator from `/proc` every 50 ms (`samples.jsonl`), from which the largest sum of the worker and its children at one instant is taken |
| CPU of a stage | the worker's `utime + stime` and, apart, that of the children it had waited for (`/proc/<pid>/stat`), at the stage's begin and end; a child's CPU is its `wait4` user + sys |
| wall of a stage | the orchestrator's clock from the request that starts the stage to the poll that sees it terminal (1 s granularity); item and child walls are exact |
| bytes | `pg_database_size`, the sum of `blob.size_bytes`, the bucket listing, `du -sb` of the two docker volumes; per kind from the tables that reference a blob, **each blob counted once** (`bytes`); archive members by name and size only |
| load | `/proc/loadavg` at each stage boundary, at each child and each HTTP call |

A guard ended the worker by its PID if its tree passed 3.5 GiB resident or the host had under 600 MiB available; it did not trip. No process
of another lane was touched.

## 4. Stages

| Stage | Wall s | Load1 start / end | Worker CPU s (self) | Worker's children CPU s | Worker VmHWM MiB (item max) | Worker VmPeak MiB | Worker + children RSS at one instant, max MiB | Blob bytes added | Database added |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| admission (4 files, 40 860 889 B) | 3.7 | 2.66 / 2.66 | 0.0 | 0.0 | idle 179.2 | 2 030.2 | 179.2 | 25 981 824 B (3 blobs) | 0.34 MiB |
| page profiles (85 pages) | 229.6 | 2.66 / 4.27 | 9.8 | 203.2 | 288.4 | 2 210.9 | **911.6** | 64 296 166 B (51 pages' blobs) | 0.45 MiB |
| matrix | 8.2 | 4.27 / 4.30 | 8.1 | 0.0 | 310.1 | 2 698.3 | 310.4 | 0 | 0.07 MiB |
| series (55 pair results) | 158.7 | 4.30 / 4.86 | 18.4 | 95.2 | **362.7** | 2 747.3 | 585.8 | 5 859 749 B (18 masks) | 1.00 MiB |
| the chain | 400.2 | | 36.3 | 298.4 | | | | 96 137 739 B | 1.86 MiB |

The API process (the orchestrator): `VmRSS` 200.4 MiB after the first request, `VmHWM` 238.0 MiB at the end of admission and unchanged to
the end of the series (`VmPeak` 1 945 MiB); 314.7 MiB after the tile reads (section 7). Its CPU in the table of `report.txt` includes the
sampler and the polling and is not an API figure.

### 4.1 Admission (3.7 s)

| Request | Wall s (per file v1, v2, v3, v4) | |
| --- | --- | --- |
| `uploadComparisonUploadPart` (one part each, 8.0, 3.1, 14.9, 14.9 MB) | 0.082, 0.051, 0.108, 0.106 | |
| `completeComparisonUploadFile` (verify the digest; the envelope child; the stamp child) | **1.048, 0.605, 0.818, 0.755** | children of the API process |

The two children of a completion: the envelope reader (`ingest/pdf_reader.py`, comparison policy) `VmHWM` 79.3 MiB, `VmPeak` 92.7 MiB; the
stamp reader `VmHWM` 79.1 MiB, `VmPeak` 92.6 MiB (sampled at 50 ms, each lives under 0.5 s; the ceiling is 768 MiB, 120 s). The API
process grew by 37.6 MiB over the four uploads (the part bodies are held in memory). v4 is stored as the same blob as v3 (3 blobs for 4
versions: the store keeps one object for equal content). **The proposal split the set**: `v1.pdf` alone (warnings `no_stamp_found`,
`scan_without_text`) and `v2.pdf`, `v3.pdf`, `v4.pdf` (`designations_differ`, `scan_without_text`); the stamp reader found no stamp on v1 and
disagreeing designations on the others, so the proposal is two sets and a person has to confirm both: the tool confirms the set of `v1.pdf`
(a new document), then the other set **joining that document** (`existing_document_uid`, the offer was `false`), then reads the order. The
order revision after the two confirmations is revision 2, source `proposal`, `v1, v2, v3, v4`: equal to the file order, so no
`appendComparisonVersionOrder` was needed. Document ordinals 1..4 in that order; all four versions `upload_kind` `comparison_pdf`.

### 4.2 Page profiles (229.6 s)

Four `page_profile` items, one per version, run one after another by the one slot: v1 50.2 s (15 pages), v2 38.7 s (18), v3 64.9 s (26),
v4 63.1 s (26); the sum is 216.9 s, the rest of the stage (12.7 s) is the hand-off: the batch releases the second set only when the first
set's items have ended, by the drive item that polls every 10 s (the longest gap between two items is 11.9 s). 85 children of each kind,
**none ended without a result**, all 85 profile rows `ready`.

| Child | Count | Wall sum / max s | CPU sum / max s | VmHWM max MiB | VmPeak max MiB | Ceiling | Share of ceiling |
| --- | ---: | --- | --- | ---: | ---: | --- | ---: |
| render (preview, thumbnail, mask, pyramid levels 2+) | 85 | 52.9 / 2.6 | 52.8 / 2.6 | 463.1 | **482.0** | 768 MiB | 63 % |
| extract (words, lines, segments, annotations, Merkle) | 85 | 150.8 / 14.0 | 150.4 / 14.0 | 694.8 | **728.4** | 1 024 MiB | 71 % |

By page size class (all four versions; displayed size in mm, long side first; the dpi follows the 40 Mpx rule: 200 up to 891 × 420, 143 for 2102 × 594, 113 for 1682 × 1189 and 1680 × 1190):

| mm | Pages | Render wall sum / max s | Extract wall sum / max s | Render VmHWM / VmPeak max MiB | Extract VmHWM / VmPeak max MiB | Archive + preview + thumbnail, sum / max MiB (per page row, before sharing) |
| --- | ---: | --- | --- | --- | --- | --- |
| 1682 × 1189 | 6 | 9.2 / 2.5 | 37.1 / 14.0 | 452.1 / 471.1 | 668.7 / 701.5 | 9.31 / 3.49 |
| 1680 × 1190 | 8 | 14.5 / 2.6 | 51.9 / 12.5 | 463.1 / 482.0 | 694.8 / 728.4 | 18.09 / 3.57 |
| 2102 × 594 | 4 | 3.7 / 1.0 | 10.9 / 7.0 | 373.3 / 391.8 | 340.7 / 369.6 | 4.47 / 1.17 |
| 891 × 420 | 4 | 3.2 / 0.8 | 15.0 / 4.0 | 228.3 / 247.5 | 243.5 / 271.7 | 4.17 / 1.13 |
| 630 × 297 | 4 | 1.6 / 0.4 | 4.3 / 2.3 | 125.0 / 143.8 | 145.5 / 172.8 | 2.41 / 0.61 |
| 594 × 420 | 4 | 1.9 / 0.5 | 5.3 / 1.9 | 159.3 / 178.1 | 129.9 / 156.3 | 2.92 / 0.77 |
| 421 × 297 | 2 | 0.5 / 0.3 | 1.7 / 1.0 | 72.7 / 92.1 | 85.3 / 110.7 | 0.55 / 0.31 |
| 420 × 297 | 21 | 7.1 / 0.4 | 14.4 / 4.3 | 91.9 / 110.7 | 227.2 / 255.4 | 9.61 / 1.14 |
| 297 × 210 (14 of 32 are scans) | 32 | 11.2 / 0.6 | 10.3 / 0.7 | 83.6 / 102.3 | 84.2 / 116.3 | 52.90 / 3.47 |

**Worst page.** By memory and by extraction: `v3.pdf` page 12 (and its copy in v4), 1680 × 1190 mm, 187 508 vector segments (186 861 drawn lines, 248
rectangles, 547 curves), 2 098 words, working raster 113 dpi 7 475 × 5 295 (39.58 Mpx): extraction 12.5 s, `VmHWM` 694.8 MiB, `VmPeak` **728.4 MiB**;
its render 1.9 s, `VmPeak` 415.5 MiB. By render memory: `v3.pdf` page 13 (1680 × 1190 mm, 4 615 segments: 3 866 drawn lines, 32 rectangles, 465 curves): 2.6 s, `VmHWM` 463.1 MiB, `VmPeak`
**482.0 MiB**. By time: `v1.pdf` page 8 (1682 × 1189 mm, 23 666 drawn lines and 11 650 curves, no text layer): extraction **14.0 s** (the CPU is 14.0 s),
render 1.6 s.

### 4.3 Matrix (8.2 s)

One `matrix_build` item, in the worker process, no child: wall 8.16 s, CPU 7.93 s user + 0.18 s sys, the worker's resident set 219.8 MiB at the
start, **`VmHWM` 310.1 MiB** (+90 MiB), 242.1 MiB resident after it; 30 rows from 85 pages.

### 4.4 Series (158.7 s)

3 transitions, 74 sheet pairs (55 compared, 7 + 8 added, 4 removed), 55 `series_pair` items (item wall sum 114.9 s, median 0.74 s, max 12.8 s) and
one `series_drive` item that polled 7 times. **29 engine children** (wall sum 95.4 s, CPU 95.2 s, none without a result) and 26 pairs on the
byte-identical fast path (v3 → v4: no child). The stage's wall is 158.7 s against 114.9 s of item time: **the other 43.3 s is the gap between
items, 0.80 s on average and 2.01 s at most** (the claim cadence; 27 % of the stage).

| mm | Child pairs | Child wall sum / max s | Child VmHWM / VmPeak max MiB | Masks (pairs with a mask / bytes) |
| --- | ---: | --- | --- | --- |
| 1682 × 1189 | 6 | 49.0 / 10.0 | 305.4 / **568.6** | 6 / 3 480 930 |
| 2102 × 594 | 2 | 15.5 / 8.7 | 216.4 / 486.0 | 2 / 739 637 |
| 594 × 420 | 4 | 11.4 / 3.4 | 160.7 / 424.6 | 4 / 923 984 |
| 420 × 297 | 7 | 10.2 / 1.9 | 163.4 / 425.1 | 4 / 483 498 |
| 630 × 297 | 2 | 4.1 / 2.2 | 184.4 / 441.8 | 2 / 231 700 |
| 297 × 210 | 8 | 5.2 / 0.7 | 130.8 / 393.8 | 0 / 0 |

**Worst pair.** By address space: `v2.pdf` page 13 → `v3.pdf` page 13, 1682 × 1189 mm at 113 dpi (39.59 Mpx), status `needs_review`: child wall 9.8 s,
CPU 9.8 s, `VmHWM` 305.4 MiB, `VmPeak` **568.6 MiB** (74 % of 768), mask 473 027 B. By time: `v2.pdf` page 12 → `v3.pdf` page 12, same size: 10.0 s,
`VmHWM` 233.5 MiB, `VmPeak` 500.7 MiB, mask 472 447 B, **item wall 12.8 s**. The largest mask: `v2.pdf` page 8 → `v3.pdf` page 8, 1 088 523 B (1 523
differences). The worker's own peak during a pair item is not the child's: **352.9 MiB** during `v2` p12 → `v3` p12, and **362.7 MiB for `v3` p12 → `v4` p12
with no child at all** (the item opens the two profiles, 187 508 segments each, to prove the Merkles equal; 1.5 s).

## 5. Bytes and rows

**Stored, each blob once** (the store keeps one object for equal content; 34 of the 85 page profiles share all their blobs with another page,
among them the 26 pages of v4):

| Kind | Blobs | Bytes | Of which |
| --- | ---: | ---: | --- |
| sources (comparison PDFs) | 3 | 25 981 824 | 4 versions declared 40 860 889 B; v3 and v4 are one blob |
| previews (1 400 px PNG) | 51 | 35 274 498 | |
| thumbnails (220 px PNG) | 51 | 1 239 477 | |
| page archives | 51 | 27 782 191 | tiles of levels 2 and up 20 565 938 B (430 tiles); `profile.json` 6 046 877 B stored (39 798 643 raw: words and lines); 36 dpi ink mask 1 112 882 B stored (7 279 407 raw) |
| pair masks (bit-packed, 8 planes) | 18 | 5 859 749 | one per non-`same` result: 37 `same` have none; 21 421 to 1 088 523 B, mean 325 542 B |
| **all blobs** | **174** | **96 137 739** | 91.7 MiB; the bucket lists 174 objects of the same total; no blob is unreferenced |

Counted by page row (85), before the store's sharing: previews 63 721 906 B, thumbnails 2 105 771 B, archives 43 683 705 B, together 109 511 382 B:
**1.29 MB a page on average (1 288 369 B), 3.75 MB at most** (`v3` p12, a 1680 × 1190 mm sheet), **3.6 MB for an A4 scan** (14 scans: the preview
alone is 2.9 MB), 0.83 MB for the other 71 pages; after the sharing the 51 distinct pages' blobs are 64 296 166 B, 0.76 MB per page row. For the 59 pages of v1, v2 and v3 that is 63.5 MiB (66.6 MB), against 66.3 MB
that `CMP-PROFILE-01` measured for the same 59 pages. The database after the chain is 16 471 731 B (`pg_database_size`); the two docker
volumes hold 73.7 MB (PostgreSQL, with its WAL) and 99.9 MB (MinIO).

Rows per table (after the chain; `total bytes` is `pg_total_relation_size`): `comparison_page_profile` 85 (270 336 B; the `profile` summaries
are 80 804 B of `jsonb`), `comparison_sheet_pair_result` 55 (720 896 B; `result` 474 764 B, `channels` 35 768 B), `comparison_sheet_pair` 74 (155 648 B),
`comparison_work` 62, `comparison_work_attempt` 69, `comparison_transition` 3, `comparison_series` 1, `comparison_matrix` 1 (`rows` 4 366 B),
`comparison_version_order` 2, `comparison_upload` 1, `comparison_upload_set` 2, `comparison_upload_file` 4, `comparison_upload_part` 4,
`document` 1, `document_version` 4, `input_manifest_entry` 4, `blob` 174, `command_record` 14, `app_user` 2, `app_user_role` 3,
`audit_event` 1, `project` 1, `worker` 1 (the full list is in `report.txt`).

## 6. Matrix and series outcome

**Matrix** (`ready`, revision `{cmx_..., edit_no 0}`; columns of 15, 18, 26, 26 pages; all 85 pages placed): rows 30, **unmatched 0**, manual 0,
AI 0, **groups 0**, **duplicates 0**, **splits 0**, **bridges 0**, scan cells 14; cells: 85 matched, 35 `absent` (reason `no_candidates`); confidence of the
55 later cells: `high` 52, `medium` 3; rows by the number of versions they appear in: 4 versions 11, 3 versions 7, 2 versions 8, 1 version 4.

**Series** (`completed`, no stale reason):

| Transition | Verdict codes | Sheets | Compared | Same | Zones only | Different (style only) | Needs review | Added | Removed | Failed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v1 → v2 | `composition_changed`, `needs_review` | 22 | 11 | 4 | 0 | 0 | 7 | 7 | 4 | 0 |
| v2 → v3 | `different`, `composition_changed`, `needs_review` | 26 | 18 | 7 | 0 | 5 (1) | 6 | 8 | 0 | 0 |
| **v3 → v4** | **`content_same`** | 26 | 26 | **26** | 0 | 0 | 0 | 0 | 0 | 0 |

The requirement holds: v3 → v4 is 26 of 26 `same` and the single verdict `content_same`. Pair results: 55 (37 `same`, 5 `different`, 13 `needs_review`); the
reasons of the 13: `NO_TEXT_LAYER` 7 (all the large v1 → v2 sheets, which have no text layer), `TEXT_UNREADABLE_IN_DIFF_AREA` 4, `PARTIAL_COVERAGE` 3,
`MATCH_LOW_CONFIDENCE` 3, `ALIGNMENT_PARTIAL` 3. The seven `needs_review` of v1 → v2 carry 122 to 2 000 differences each (2 000 is the cap of the
result). **There is nothing to compare these statuses with**: the original never ran this set; whether the matrix pairing of v1 against v2 (15 pages
against 18: 11 matched, 4 removed, 7 added) is the right one cannot be judged here either.

## 7. The cost of a pair tile (`streamComparisonPairTile`)

20 distinct overlay tiles (layers `main,light_elements,color_change,line_style,service_zones`, the viewer's five defaults) through the routers
of a fresh API process (build, one request, then the tiles), on two pairs: the largest canvas with a mask (`v2` p13 → `v3` p13, 1682 × 1189 mm,
7 483 × 5 290 px, 39.59 Mpx, `needs_review`) and the pair at the median of the 18 by canvas area (594 × 420 mm, 4 678 × 3 308 px, 15.47 Mpx, `needs_review`),
10 tiles each at levels 0 to 3; then two of them again. Host load 4.3.

| Level | Tiles | Median ms | Max ms | Mean ms |
| --- | ---: | ---: | ---: | ---: |
| 0 (rendered on request in a ceilinged child) | 6 | 353 | 864 | 454 |
| 1 (the same) | 6 | 364 | 816 | 459 |
| 2 (stored in the archive) | 4 | 47 | 60 | 46 |
| 3 (stored) | 4 | 40 | 48 | 34 |
| all 20, cold | 20 | | 864 | 290 (5.80 s in all) |
| the same tile again | 2 | 26 and 35 | | |

The tiles are 3 113 to 110 150 B. 40 tile children ran for the 12 cold tiles of levels 0 and 1 (the tile of A and the source tiles of B that the transform needs), none ended without a
result: wall max 0.25 s, **`VmHWM` 67.0 MiB, `VmPeak` 81.0 MiB**. **The API process:** `VmRSS` 200.5 MiB before the first tile, 314.7 MiB after the 20th
(+114 MiB, inside the viewer's cache budgets of 96 + 48 + 32 MiB), `VmHWM` 314.7 MiB, `VmPeak` 2 515 MiB; PDFium was never loaded
in it.

## 8. Against ADR-0025 decisions 8 and 9, and against the earlier figures

### 8.1 Ceilings and caps

| Quantity (decision) | ADR value | Worst measured here | Share | Verdict |
| --- | --- | --- | ---: | --- |
| address space, render child (8; addendum 1) | 768 MiB | 482.0 MiB (`v3` p13, 39.58 Mpx) | 63 % | keep |
| address space, extraction child (8; addendum 1) | 1 024 MiB | 728.4 MiB (`v3` p12, 187 508 segments) | 71 % | keep; **768 would pass by 39.6 MiB (5 %) on this page, which is too thin** |
| address space, engine child (8) | 768 MiB | 568.6 MiB (`v2` p13 → `v3` p13) | 74 % | keep |
| address space, tile child (8) | 768 MiB | 81.0 MiB | 11 % | keep |
| address space, upload reader (addendum 3) | 768 MiB, 120 s | 92.7 MiB, under 0.5 s | 12 % | keep |
| CPU per child (8) | 300 s | 14.0 s (extraction of `v1` p8) | 4.7 % | keep (a backstop for a stuck child) |
| wall per child (8) | 600 s | 14.0 s | 2.3 % | keep |
| wall per work item, against the 900 s watchdog (`jobs/lease.py:21`) | | `page_profile` item (one version) 64.9 s; `series_pair` 12.8 s | 7 % / 1 % | see 8.2 item 3 |
| working raster (9) | 40 Mpx | 39.59 Mpx (1682 × 1189 mm at 113 dpi); no page refused | 99 % | keep: the engine already needs 74 % of its ceiling at this size |
| stored bytes per project (9) | 8 GiB | 96.1 MB for 85 pages / 4 versions | 1.1 % | keep |
| elements of a page at admission (addendum 3) | 1 000 000 | 536 426 (`v1` p7) | 54 % | keep |

### 8.2 What should change or be written into the ADR (for the dated addendum the integrator writes)

1. **Estimate of bytes per project (decision 9, «1.9–6.2 GB for 12 × 100 A1 sheets»).** Replace by measured per-page figures: derived data 1.29 MB a page
   row on average (0.83 MB for a vector page, 3.6 MB for a scan, 3.75 MB at most), 0.76 MB a page after the store's sharing of equal content in this set,
   masks 0.07 MB per page row (0.33 MB per masked pair, 1.09 MB at most), sources 0.48 MB per page row declared. For 1 200 pages of this mix:
   derived 1.55 GB + masks 0.08 GB + sources 0.58 GB ≈ 2.2 GB (2.05 GiB, 26 % of 8 GiB); for 1 200 scans 4.3 GB derived plus sources, which is the case that
   approaches the cap. The 8 GiB cap stays.
2. **Throughput (decision 6, «written by CMP-MEASURE-01»), one slot, host load 2.7 to 4.9:** page profiles **1 333 pages an hour** (85 pages in 229.6 s;
   2.55 s a page of worker time, 2.70 s with the hand-off), engine pairs **658 an hour** (29 child pairs in 158.7 s; 3.29 s a child pair on average, 10.0 s at
   most), pair results 1 248 an hour (55 in 158.7 s, 26 of them on the fast path), matrix build 85 pages in 8.2 s. Calls an hour: not measured (no AI work).
3. **A `page_profile` item is a version, not a page (decisions 4, 6 and 8).** The ADR says «an item is one page or one pair»; `CMP-PROFILE-QUEUE-01` made it one
   version, and the attempt is fenced after 900 s whatever its progress (`comparison/work/heartbeat.py`). Here a version took 38.7 to 64.9 s. At this set's
   2.55 s a page a 500-page version would take about 1 276 s: the first attempt is fenced at 900 s and the second finishes (the builder resumes after the last stored
   page), using 2 of the 3 attempts; at 5.4 s a page (the mix of the 2A0 sheets) the budget of 3 × 900 s would be spent. This is an extrapolation, not a measurement,
   but it is the one place where a measured number comes within an order of magnitude of a limit. Either split the item into ranges of pages or give that kind a
   longer watchdog (decision to the integrator).
4. **The worker's own footprint (decision 8, «one child runs beside the API, the database and the object store»).** The ceilings bound the children; the worker
   process is not bounded and holds 179 MiB idle, up to 310 MiB in the matrix build, 363 MiB preparing a pair of the heaviest pages, 284 MiB left resident
   after the chain (it does not give memory back), 2.7 GiB of address space. The sum at one instant was 912 MiB (worker 217 MiB + extraction child 695 MiB
   resident), plus the API 315 MiB: 1.2 GiB of the 4 GiB host before PostgreSQL and MinIO. That fits; the ADR should say the number, and that the matrix build
   (decision 8 says every computation runs in a child; `CMP-MATRIX-01` section 9 item 1 ran it in the worker) and the worker-side preparation of a pair are
   outside any ceiling. The matrix is measured here only to 85 pages (the lane measured 12 × 400 synthetic pages: 541 MiB).
5. **The claim cadence** is not an ADR value but costs 27 % of the series wall: the gap between two items is 0.80 s on average. If a series of small pairs is the
   common case (31 of the 55 pairs take under a second) the cadence is the throughput limit.

Nothing else in decisions 8 and 9 should change on this evidence. In particular the three ceilings that were chosen without measurement, CPU 300 s, wall 600 s and
the 40 Mpx cap, are confirmed as safe; none is shown to be tight enough to tighten.

### 8.3 Against the earlier figures

| Figure | Earlier | Here |
| --- | --- | --- |
| worst render child (113 dpi, 39.6 Mpx) | `MEASURE-RENDER-01` 5.5: standalone pipeline `v3` p13 RSS 458 / VmPeak 477 MiB, 3.3 s; `CMP-PROFILE-01`: VmPeak 481 MiB, 3.5 s | the product's child (preview, thumbnail, mask, pyramid levels 2+): `VmHWM` 463.1, `VmPeak` 482.0 MiB, 2.6 s |
| worst extraction child | `MEASURE-RENDER-01`: `pdfplumber` alone VmPeak 658 MiB, 11.2 s; `CMP-PROFILE-01`: 727 MiB, 15.5 s; `CMP-C1-FIX-A` item 8 (85 pages): **728.4 MiB** | **728.4 MiB** `VmPeak` (694.8 `VmHWM`), 12.5 s: the same page, the same figure to the digit; +70 MiB over the standalone pass is the segments, annotations and Merkle in the same child |
| worst engine child | `CMP-ENGINE-01` section 6 (59 pairs paired by index, 33 children): VmPeak **568.6 MiB**, VmHWM 300.2 MiB, 10.7 s, masks 6 233 092 B | 29 children on the matrix's 55 pairs: VmPeak **568.6 MiB**, VmHWM 305.4 MiB, 10.0 s, 18 masks 5 859 749 B (the pairing is the matrix's, so the page pairs differ; the worst pair is again `v2` p13 → `v3` p13) |
| stored bytes of the profile (59 pages of v1, v2, v3) | `CMP-PROFILE-01`: 66.3 MB, 1.12 MB a page, 3.74 MB at most | 66.6 MB (63.5 MiB), 1.13 MB a page, 3.75 MB at most (+0.4 %) |
| render of the whole real set | `MEASURE-RENDER-01` section 4.1 (200 dpi, standalone): v1 21.0 s, v2 28.8 s, v3 41.0 s | here at the 40 Mpx dpi, as products: v1 6.8 s, v2 11.9 s, v3 17.3 s (render children only) |
| extraction of the whole real set | `MEASURE-RENDER-01`: v1 41.9 s, v2 21.3 s, v3 35.2 s; `CMP-C1-FIX-A`: 168.2 s for 85 pages | v1 41.5 s, v2 24.2 s, v3 42.7 s, v4 42.4 s: 150.8 s for 85 pages |

Memory is reproduced to the digit by independent runs (the worst extraction and the worst pair are the same figures as two lanes' earlier measurements);
the times follow the host load.

## 9. FIX items

1. **FIX-1 (blocking; a product defect).** `comparison/profile/source.py::load_source_version` must accept the manifest role of a comparison-only version
   (`MANIFEST_ROLE_COMPARISON_PDF`, `comparison.source_pdf`) besides `source.document`; with it the page profile, the engine and the tile path read a version that the
   plain-PDF upload admitted. A test must drive `completeComparisonUploadFile` → `confirmComparisonUploadSet` → the `page_profile` item on one version (every suite
   seeds `source.document` today). Evidence: section 2 and `chain-01-as-shipped`. Until it is fixed, «Сравнение версий» cannot compare anything an expert uploads.
2. **FIX-2 (observation for the screens).** On the real set the proposal was two sets (v1 alone: no stamp read; v2 to v4: `designations_differ`); the order after
   joining was right (`proposal`), but the upload dialog of `CMP-VC-UI-01` has to let an expert join a later set to the first one's document (`existing_document_uid`
   was not offered) and the stamp reader reads few stamps on this set (strokes-only text, `CMP-ENGINE-01` section 6).
3. **FIX-3 (decision for the integrator).** The item size against the 900 s watchdog (8.2 item 3).
4. **FIX-4 (improvement).** Equal source bytes are profiled twice: v4 (identical to v3) cost 63.1 s of wall and 59.2 s of child CPU to produce profiles whose blobs the store
   then shared with v3's; a profile cache keyed by the source blob's SHA-256 would make a re-uploaded version free. The 26 pairs of v3 → v4 cost 1.2 to 1.5 s each of
   worker time (opening the two profiles) though no child ran; the worker peak of 362.7 MiB is that.
5. **FIX-5 (improvement).** The claim cadence and the batch hand-off (0.80 s average gap per item; 11.9 s between the two sets of the batch) are 27 % and 5 % of the
   stage walls.

## 10. Known limits

- **One run, one host, one slot.** The memory figures reproduce; every time is an upper bound under a load of 2.7 to 4.9 (other lanes were running).
- **Behind the shim** (section 2): the stages after the profiles ran with `load_source_version` widened in the tool's processes; the as-shipped run stopped at the profiles.
- **The transport is in-process**: no proxy, no 16 MiB chunk over a network; the API process is the orchestrator, which also polls and samples (its CPU is not an API figure).
  The files were each under one part, so multi-part resumption was not exercised.
- **The upload readers' children are sampled** (50 ms; each lives under 0.5 s), not self-reported; every other child reports its own `VmHWM` and `VmPeak`.
- **The set is one object** (four versions, 85 pages, 14 scans), 40.9 MB; nothing here measures 12 versions of 100 A1 sheets, a 500-page version, the matrix beyond 85 pages, or
  two worker slots. The 500-page and 1 200-page figures above are arithmetic on these pages.
- **No original statuses exist** for this set; the matrix and the statuses are recorded, not judged.
- **No AI work**: no spend, no model call, no calls-an-hour figure.
- The stage walls have the 1 s granularity of the polls; the stage boundary of the page profiles is the first confirmation (the second set's confirmation and the order read are inside it).

## 11. Hotspots and resources

`git diff --name-only 9861c9f9..HEAD` lists `tools/measure/comparison_chain.py` (new), `docs/program/compare/MEASURE-ENGINE-01.md` (new) and `docs/program/tasks/CMP-MEASURE-01.md`
(new), and nothing else: no file of `src/`, `contracts/`, `db/`, `tests/`, `web/`, `infra/`, no lock or dependency file. The lane's stack: `auditmanager-cmp-measure-01` (PostgreSQL 57910,
MinIO 61910/61911, database `auditmanager_cmp_measure_01`, bucket `auditmanager-cmp-measure-01`), `df -h /` read before the stack (9.2 GiB free) and before each run
(8.4 to 8.8 GiB). The stack was reset to an empty database between the runs (`make down`, the two volumes removed by their exact names, `make up`, `make migrate`).

## 12. Cleanup

(written at the end of the lane: see the task file's Handoff)
