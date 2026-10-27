# MEASURE-RENDER-01 — render and extraction cost of comparison pages

- Task: `tasks/CMP-MEASURE-01A.md`. Feeds `CMP-SEAL-C0` and `CMP-PROFILE-01`, which fix the values that ADR-0025 decisions 8 and 9
  marked «decided by CMP-ADR-01, revisable by CMP-MEASURE-01». ADR-0025 changes only by a dated addendum that cites this report
  (decision 27); this report changes no ADR value by itself.
- Tree: branch `agent/cmp-measure-01a`, base `121387bb` on `integration/compare-modules`; the measuring script is
  `tools/measure/comparison_render.py` at commit `64f7e2f0` (clean tree when the final pass started, `git status --short` empty).
- Measured on 2026-10-27, 19:44–20:13 (+05:00), on the development host of the programme (section 2), which is shared with other
  projects. Interpreter `/root/projects/PDF-Analysis/.venv/bin/python` (Python 3.12.3), `pypdfium2` 5.13.0 (PDFium 153.0.7999.0),
  `pdfplumber` 0.11.10 with `pdfminer.six` 20260107, Pillow 12.3.0. No dependency was installed; `numpy` and OpenCV are not in this
  venv, so no comparison engine is measured (task non-goal).
- Raw records (JSON lines, numbers only) are outside git, under `.local/comparison-measure/results-final/`
  (`main`, `diag`, `floor`, `cap`, `probe`); every figure below is a field of those records or arithmetic on them, and the tables
  are printed by the script's own `table`, `levels` and `fit` subcommands.
- The real set `.local/comparison-measure/13AV-RD-EM2-PA/` is client-like data. This report holds only numbers for it: page sizes,
  element counts, times, bytes and memory. Nothing of its text or images was printed, copied or sent anywhere.

## 1. What the numbers are

**The unit of measurement is one page in one child process**, run one at a time (never in parallel). `run` starts, for every page of
every input, a fresh child for each of:

| job | what it does | figures taken |
| --- | --- | --- |
| `scan` (once per file) | page count, displayed size and rotation of every page, drawing elements counted with the rule of `ingest/pdf_reader.py::_elements` (a path by its segments, form XObjects walked) | as below |
| `render` at 200, 150, 100 dpi | `pypdfium2` renders the page (pipeline `lean`: `RGBx`, 4 bytes a pixel, shared with Pillow without a copy), then from that raster a **1400 px preview PNG**, a **220 px thumbnail PNG** and a **512 px tile pyramid** (`reduce(2)` down to one tile; every tile of every level is encoded as PNG, so the pyramid bytes are measured, not estimated; Pillow defaults, compress level 6, RGB) | wall time, CPU time, peak RSS, peak address space, pixels, bytes |
| `extract` | `pdfplumber` `extract_words()` with boxes, then `lines` (the same parse yields rects, curves and chars, whose counts are recorded) | the same |
| `baseline` (once) | the interpreter with the three libraries imported, no page | the same |

Every child sets, before it imports anything, what `ingest/pdf_reader.py::_limit` sets: `RLIMIT_CORE` 0, **`RLIMIT_AS` 768 MiB**
(`--address-space-mib`, settable) and **`RLIMIT_CPU` 300 s** (`--cpu-seconds`); the parent adds a **600 s wall clock**
(`--wall-seconds`) and signals only its own child, by its PID, when that passes. No product module is imported; the product's
`PDFIUM_LOCK` guards PDFium inside one process and has nothing to guard in a child with one thread.

Figures per job: **wall** = parent clock from spawn to reap; **CPU** = child user+sys from `wait4`; **RSS** = `ru_maxrss` from
`wait4` (the task's figure); **VmHWM** and **VmPeak** = read by the child itself from `/proc/self/status` (VmPeak is the
address-space peak, the quantity `RLIMIT_AS` limits). `ru_maxrss` and `VmHWM` differ by at most 0.3 MiB on every completed job here
(the parent is a standard-library process that never loads a page, so no inherited high-water mark), and VmPeak is 13 to 32 MiB
above VmHWM, so the tables print RSS and, where the ceiling is the question, VmPeak too. A job that ends without a result is
recorded with its status: `overrun` (a `MemoryError`, including one that `pdfplumber` re-raises inside `PdfminerException`),
`signal:NAME`, `cpu`, `wall` or `exit:N`. With `--escalate` a failed job is re-run at each larger ceiling until one passes, and the
record says which: the evidence that the failure was the ceiling.

The empty interpreter with the three libraries imported is **43 MiB RSS and 75 MiB VmPeak**, 0.08 s (`baseline`).

## 2. Host facts

Commands run by the driver at the start of the final pass (2026-10-27T19:44:21+05:00) and at its end (20:06:02):

```
$ free -g                       # 2026-10-27T19:44:21+05:00, start of the final pass
               total        used        free      shared  buff/cache   available
Mem:              11           8           0           0           3           3
Swap:             15           7           8
$ nproc
8
$ df -h /
Filesystem      Size  Used Avail Use% Mounted on
/dev/vda3       119G  109G  4.0G  97% /
$ cat /proc/loadavg
3.23 3.50 4.30 6/1636 3969908
$ uname -r
6.8.0-147-generic
$ free -g | head -2             # 20:06:02, end of the final pass
               total        used        free      shared  buff/cache   available
Mem:              11           6           2           0           3           5
$ df -h /                       # 20:06:02
/dev/vda3       119G  109G  4.2G  97% /
$ cat /proc/loadavg             # 20:06:02
9.21 9.83 8.20 4/1636 4151456
```

`lscpu`: 8 vCPU (1 socket, 8 cores, 1 thread each), AMD EPYC 9655. `swapon --show`: a 16 GiB swap file, 7 GiB in use at the start, 12 GiB at the busiest moment (`free -m`, 19:59) and 10 GiB at 20:10. The ceilings are set per child; the driver shell itself has no limit. Free disk when the realistic A1 was generated was 4.4 to
4.6 GiB (the stop rule is 1.5 GiB); the generated PDFs (about 20 MB in all) were written to a temporary directory outside the
repository and deleted afterwards; the measurement writes no rasters (they live in the child's memory).

**The host was not quiet.** The one-minute load average at the start of a job was 3.2 to 6.9 (median 4.4) in the main pass and 8 to 19
in the later diagnostic passes (other projects' `tsc`, `vitest` and `pytest` were running), with swap in use. In the main pass the
CPU time equals the wall time to within 31 % on every job longer than half a second, so the times are CPU-bound figures, not queueing
figures; the diagnostic passes ran under heavier load and are used for memory, not time. One job was visibly disturbed (section 5.4).

Record counts (one record = one child; the four escalation re-runs are folded into their records):

| file | records | ok | not ok |
| --- | ---: | ---: | --- |
| `main.jsonl` | 450 | 450 | - |
| `diag.jsonl` | 52 | 50 | overrun 2 |
| `floor.jsonl` | 97 | 61 | cpu 2, overrun 30, signal:SIGABRT 3, signal:SIGTRAP 1 |
| `cap.jsonl` | 36 | 36 | - |
| `probe.jsonl` | 7 | 4 | cpu 1, overrun 1, wall 1 |
| total | 642 | | |

## 3. Findings

1. **Every page of every input passes the defaults.** In the main pass all 450 child processes (17 scans, 324 renders, 108
   extractions, 1 baseline) ended `ok` under 768 MiB, 300 s CPU and 600 s wall: the real set (59 pages of v1, v2, v3), VS-1 (32
   pages), SP-1 (12 pages), the two producers of the realistic A1, the light realistic A1 and a 400 001-element realistic A1. **No
   page overran the ceiling in the main pass.** The margin is thin where the pixel count is high.
2. **Worst render, by memory:** real `v3.pdf` p13, 1680 × 1190 mm, at **150 dpi**, 69.7 Mpx: 4.2 s, **RSS 717 MiB, VmPeak 736 MiB**
   (96 % of the 768 MiB ceiling). **By time:** real `v1.pdf` p8, 1682 × 1189 mm, at **200 dpi**, 124.0 Mpx: **8.5 s** (render
   4.8 s, tile pyramid 3.0 s), RSS 663 MiB. The same size at 200 dpi in `v3.pdf` p13: 5.5 s, RSS 684 MiB, VmPeak 704 MiB.
3. **The realistic A1 at 200 dpi** (30.44 Mpx; the CropBox inset makes it 835 × 588 mm): **1.8 s, RSS 196 MiB, VmPeak 216 MiB**; the
   smallest ceiling that passed is 224 MiB (192 MiB fails). Its preview is **396 665 B**, thumbnail **18 006 B**, tile pyramid
   **182 tiles, 3 905 287 B** (producer B: 403 695, 18 098, 4 004 355).
4. **Peak memory is not a function of the pixel count alone, and it is elastic under the ceiling.** A linear fit of RSS on megapixels
   over the 324 render jobs (`fit`) gives 5.94 MiB per Mpx + 41 MiB with a residual of up to 262 MiB, so it predicts nothing; PDFium
   adds working memory that depends on the page's content and, when the ceiling is lower, takes less: `v3.pdf` p13 at 150 dpi uses
   717 MiB under 768 MiB but passes at **448 MiB** with 416 MiB RSS, and its output bytes at 640 MiB equal those at 768 MiB (section 5.2). The RSS in the tables is
   therefore what the process used when allowed; the smallest ceiling that passes is the figure to size from.
5. **Extraction** (`pdfplumber`, words with boxes and lines): slowest real page `v1.pdf` p8, 14.9 s, 302 MiB (23 666 lines and 11 650
   curves); largest real memory `v3.pdf` p12, 1680 × 1190 mm, 382 424 elements, 198 694 `pdfplumber` objects: **11.2 s, RSS 632 MiB,
   VmPeak 658 MiB**; the 400 001-element realistic A1: **17.4 s CPU, RSS 654 MiB, VmPeak 674 MiB**. Memory follows the number of
   `pdfplumber` objects (lines, rects, curves, chars) at **3.0 to 3.5 KiB each** for lines, rects and chars and about **16 KiB per
   curve** — not the element count. The two heaviest extractions pass at 704 MiB and fail at 640 MiB: with 768 MiB
   the margin is 64 to 128 MiB.
6. **The tile pyramid is the byte cost, not the preview.** Per page at 200 dpi: preview 0.04 to 0.46 MB for A3 to A1 vector pages, up to
   0.77 MB for a 124 Mpx page and 2.9 MB for an A4 scan; thumbnail 3 to 34 kB for vector pages and 64 kB for the scan; the whole
   pyramid 0.2 to 5.1 MB for A3 to A1 vector pages, 8.5 MB for the 77 Mpx page, 6.6 to 22 MB for 124 Mpx pages and 9.8 MB for an A4
   scan; levels 0 and 1 are 84 to 94 % of the pyramid (section 6.3). For 12 versions × 100 sheets (1 200 pages) the whole pyramid is
   4.7 to 6.1 GB for vector pages, 7.2 GB for the v3 mix (7 of 26 pages scans) and 11.8 GB for all-scan pages; preview and thumbnail
   together are 0.4 to 0.6 GB for vector pages, 1.3 GB for the v3 mix and 3.6 GB for scans.
7. **At the 40 Mpx cap the worst page needs far less.** Rendering at the dpi that makes the page 39.6 Mpx (113 dpi for 1682 × 1189 mm,
   143 dpi for 2102 × 594 mm), all nine heavy pages passed at **384 MiB** (RSS ≤ 343 MiB, VmPeak ≤ 363 MiB) and at 768 MiB their worst
   was RSS 458 MiB, VmPeak 477 MiB, 4.0 s.
8. **How a ceiling hit looks.** Of the 36 ladder jobs that did not pass, 30 ended as a `MemoryError`, 4 as `SIGABRT` (3) or
   `SIGTRAP` (1) from PDFium, and 2 as `pdfplumber` extractions that ran to the CPU ceiling instead of failing (2 of the 3 attempts at
   576 MiB: 298 s of CPU, and the 60 s limit of the repeat) — the CPU ceiling is the backstop, and a hit can cost up to 300 s
   (section 5.4).
9. **The envelope does not admit this set.** `v1.pdf` p7 (2102 × 594 mm) has **536 426** drawing elements by the product reader's own
   rule; `PAGE_ELEMENTS_MAX` in `ingest/envelope.py` is 400 000, so the existing envelope would refuse that version
   (`page_elements`), and the comment there that the largest real page has 75 486 elements is out of date: 13 of the 59 pages are
   above it, 6 above 300 000 and 1 above 400 000. Decision 9 names the existing envelope for version admission; if comparison admission
   applies its element ceilings, this set cannot be uploaded, and `CMP-INGEST-01` must either keep them and refuse such sets or set a
   comparison-specific ceiling (the ADR does not say). The measurement here bypassed the envelope.

## 4. Tables per input

Columns: `mm` = displayed size by PDFium in mm (long x short), `elements` = the product reader's count, `Mpx at 200` = pixels of the
200 dpi raster, `worst ...` = the largest over the pages of the row, `preview / thumbnail / tiles B median (max)` = PNG bytes at the
highest dpi that completed (200 dpi here), `jobs over the ceiling` = jobs that did not end `ok` (render at three dpi, extraction).
Seconds are wall seconds of the whole child (start, imports, render, preview, thumbnail, every tile of the pyramid).

### 4.1 The real set (figures only)

Four versions of one object, 85 pages in all. `v4.pdf` is byte-identical to `v3.pdf` (the same SHA-256, checked with `sha256sum`), so
it was **not measured again** and `v3.pdf` stands for it. The displayed sizes by PDFium differ from the page-size summary in the set's
own README for some pages (for example a 2102 × 594 mm page is not in that summary); the tables use PDFium's, which is what the
render uses. `v3.pdf` p20–26 are seven A4 pages of 8 drawing elements each with 2.9 MB previews (scan-like raster pages).

**real / v1.pdf (15 pages)**

| mm | pages | max elements | Mpx at 200 | worst render s at 200/150/100 dpi | worst peak RSS MiB at 200/150/100 | preview B median (max) | thumbnail B median (max) | tiles B median (max) | worst extract s | worst extract RSS MiB | jobs over the ceiling |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 1682x1189 | 2 | 377155 | 124.00 | 8.5 / 3.8 / 2.3 | 663 / 400 / 196 | 359182 (408792) | 17698 (18900) | 8453033 (10318894) | 14.9 | 302 | 0 |
| 2102x594 | 1 | 536426 | 77.43 | 2.4 / 1.7 / 1.0 | 417 / 248 / 129 | 211920 (211920) | 10704 (10704) | 7012449 (7012449) | 7.0 | 331 | 0 |
| 594x420 | 2 | 137745 | 15.47 | 0.9 / 0.6 / 0.5 | 112 / 81 / 58 | 374311 (388289) | 20769 (21450) | 1946111 (2018524) | 2.0 | 122 | 0 |
| 630x297 | 1 | 180153 | 11.60 | 0.7 / 0.5 / 0.3 | 90 / 68 / 51 | 313107 (313107) | 15392 (15392) | 1694816 (1694816) | 2.3 | 139 | 0 |
| 421x297 | 2 | 65281 | 7.76 | 0.4 / 0.3 / 0.2 | 75 / 59 / 46 | 180209 (206923) | 16459 (17099) | 577137 (655797) | 0.9 | 79 | 0 |
| 420x297 | 3 | 341550 | 7.75 | 0.7 / 0.5 / 0.4 | 76 / 60 / 46 | 213499 (763417) | 16071 (30069) | 676921 (2486871) | 4.4 | 221 | 0 |
| 297x210 | 4 | 1030 | 3.87 | 0.3 / 0.3 / 0.2 | 57 / 48 / 36 | 183233 (309453) | 10498 (15720) | 453702 (816809) | 0.2 | 47 | 0 |

**real / v2.pdf (18 pages)**

| mm | pages | max elements | Mpx at 200 | worst render s at 200/150/100 dpi | worst peak RSS MiB at 200/150/100 | preview B median (max) | thumbnail B median (max) | tiles B median (max) | worst extract s | worst extract RSS MiB | jobs over the ceiling |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 1682x1189 | 4 | 368019 | 124.00 | 5.5 / 4.2 / 2.5 | 659 / 706 / 373 | 351671 (752282) | 17703 (32362) | 10358456 (21535465) | 10.8 | 609 | 0 |
| 2102x594 | 1 | 24945 | 77.43 | 3.2 / 2.0 / 1.2 | 698 / 406 / 197 | 241600 (241600) | 12122 (12122) | 8198713 (8198713) | 1.1 | 97 | 0 |
| 594x420 | 2 | 15111 | 15.47 | 1.2 / 0.8 / 0.4 | 161 / 103 / 61 | 382270 (398374) | 20781 (21500) | 1944736 (2020712) | 0.7 | 64 | 0 |
| 630x297 | 1 | 8079 | 11.60 | 0.7 / 0.5 / 0.3 | 127 / 83 / 52 | 319456 (319456) | 15669 (15669) | 1679690 (1679690) | 0.4 | 57 | 0 |
| 420x297 | 6 | 7010 | 7.74 | 0.6 / 0.5 / 0.3 | 94 / 64 / 48 | 220135 (788012) | 15933 (30318) | 635879 (2226984) | 0.4 | 62 | 0 |
| 297x210 | 4 | 1030 | 3.87 | 0.3 / 0.3 / 0.2 | 56 / 48 / 36 | 183233 (309453) | 10498 (15720) | 453702 (816809) | 0.2 | 40 | 0 |

**real / v3.pdf (26 pages)**

| mm | pages | max elements | Mpx at 200 | worst render s at 200/150/100 dpi | worst peak RSS MiB at 200/150/100 | preview B median (max) | thumbnail B median (max) | tiles B median (max) | worst extract s | worst extract RSS MiB | jobs over the ceiling |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 1680x1190 | 4 | 382424 | 123.96 | 6.4 / 4.9 / 2.9 | 684 / 717 / 384 | 525350 (774313) | 20858 (33768) | 14630442 (21979077) | 11.2 | 632 | 0 |
| 2102x594 | 1 | 24391 | 77.43 | 3.2 / 2.0 / 1.2 | 700 / 408 / 200 | 248990 (248990) | 12529 (12529) | 8484560 (8484560) | 1.2 | 96 | 0 |
| 891x420 | 2 | 112347 | 23.21 | 1.4 / 0.9 / 0.6 | 230 / 142 / 82 | 329527 (368303) | 14644 (15178) | 3212597 (3775605) | 3.2 | 214 | 0 |
| 630x297 | 1 | 8131 | 11.60 | 0.8 / 0.5 / 0.4 | 127 / 83 / 52 | 325204 (325204) | 15870 (15870) | 1709296 (1709296) | 0.5 | 57 | 0 |
| 420x297 | 6 | 7010 | 7.74 | 0.6 / 0.5 / 0.3 | 94 / 65 / 48 | 224613 (788249) | 17050 (30393) | 664942 (2223501) | 0.5 | 62 | 0 |
| 297x210 | 12 | 15425 | 3.87 | 1.4 / 0.9 / 0.5 | 86 / 73 / 64 | 2863621 (2941056) | 62340 (65347) | 9589566 (9935492) | 0.5 | 55 | 0 |

The per-page tables for the three files are in Appendix A. The heaviest renders by phase (the whole of one child):

| page | dpi | Mpx | open s | render s | preview s | thumbnail s | tile pyramid s | child total s | parent wall s | CPU s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| realistic A1 (A) | 200 | 30.4 | 0.08 | 0.29 | 0.35 | 0.03 | 0.97 | 1.73 | 1.8 | 1.8 |
| realistic A1 (B) | 200 | 30.4 | 0.04 | 0.28 | 0.35 | 0.03 | 0.98 | 1.69 | 1.8 | 1.8 |
| 400k-element A1 | 200 | 30.4 | 0.17 | 0.41 | 0.35 | 0.03 | 1.13 | 2.13 | 2.2 | 2.2 |
| real v3 p13 | 200 | 124.0 | 0.01 | 1.91 | 0.31 | 0.10 | 3.02 | 5.35 | 5.5 | 5.5 |
| real v3 p12 | 200 | 124.0 | 0.06 | 0.97 | 0.42 | 0.08 | 4.73 | 6.27 | 6.4 | 6.4 |
| real v1 p8 | 200 | 124.0 | 0.16 | 4.82 | 0.31 | 0.10 | 3.00 | 8.39 | 8.5 | 8.4 |
| real v3 p7 | 200 | 77.4 | 0.02 | 0.80 | 0.19 | 0.06 | 2.04 | 3.10 | 3.2 | 3.2 |
| real v3 p20 (A4 scan) | 200 | 3.9 | 0.00 | 0.13 | 0.24 | 0.01 | 0.83 | 1.22 | 1.3 | 1.3 |

Whole-file totals (sum of per-page wall seconds, the sum of the pages' separate children, so imports repeat):

| input | pages | source bytes | render 200 dpi s | render 150 dpi s | render 100 dpi s | extraction s | extraction CPU s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| real / v1.pdf | 15 | 8052267 | 21.0 | 12.4 | 7.9 | 41.9 | 41.8 |
| real / v2.pdf | 18 | 3050492 | 28.8 | 21.8 | 13.1 | 21.3 | 21.1 |
| real / v3.pdf | 26 | 14879065 | 41.0 | 30.0 | 17.9 | 35.2 | 35.1 |

### 4.2 VS-1 (`fixtures/comparison/vs1/*.pdf`, five versions, 32 pages)

All 32 pages have at most 474 elements. They are A4 to A3 vector sheets, one A1 sheet per file (841 × 594 mm, 30.98 Mpx, 472
elements) and, in v4 and v5, one A3 scan. The A1 sheet is the only page above 8 Mpx.

**vs1 / v1.pdf (6 pages)**

| mm | pages | max elements | Mpx at 200 | worst render s at 200/150/100 dpi | worst peak RSS MiB at 200/150/100 | preview B median (max) | thumbnail B median (max) | tiles B median (max) | worst extract s | worst extract RSS MiB | jobs over the ceiling |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 841x594 | 1 | 472 | 30.98 | 1.2 / 0.8 / 0.4 | 187 / 117 / 73 | 187156 (187156) | 11933 (11933) | 1421039 (1421039) | 0.2 | 38 | 0 |
| 420x297 | 4 | 250 | 7.74 | 0.4 / 0.3 / 0.2 | 73 / 57 / 45 | 62614 (134088) | 6085 (6264) | 243772 (285514) | 0.2 | 38 | 0 |
| 297x210 | 1 | 48 | 3.87 | 0.3 / 0.2 / 0.1 | 54 / 46 / 34 | 141251 (141251) | 8828 (8828) | 323707 (323707) | 0.1 | 39 | 0 |

**vs1 / v2.pdf (6 pages)**

| mm | pages | max elements | Mpx at 200 | worst render s at 200/150/100 dpi | worst peak RSS MiB at 200/150/100 | preview B median (max) | thumbnail B median (max) | tiles B median (max) | worst extract s | worst extract RSS MiB | jobs over the ceiling |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 841x594 | 1 | 472 | 30.98 | 1.3 / 0.8 / 0.5 | 188 / 117 / 74 | 187633 (187633) | 12026 (12026) | 1420194 (1420194) | 0.2 | 39 | 0 |
| 420x297 | 4 | 250 | 7.74 | 0.4 / 0.3 / 0.2 | 73 / 57 / 45 | 62592 (134066) | 6075 (6263) | 243424 (284732) | 0.2 | 38 | 0 |
| 297x210 | 1 | 48 | 3.87 | 0.3 / 0.2 / 0.1 | 55 / 46 / 34 | 141251 (141251) | 8828 (8828) | 323707 (323707) | 0.1 | 39 | 0 |

**vs1 / v3.pdf (6 pages)**

| mm | pages | max elements | Mpx at 200 | worst render s at 200/150/100 dpi | worst peak RSS MiB at 200/150/100 | preview B median (max) | thumbnail B median (max) | tiles B median (max) | worst extract s | worst extract RSS MiB | jobs over the ceiling |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 841x594 | 1 | 472 | 30.98 | 1.2 / 0.8 / 0.4 | 188 / 117 / 73 | 189001 (189001) | 12050 (12050) | 1421204 (1421204) | 0.1 | 38 | 0 |
| 420x297 | 3 | 252 | 7.74 | 0.4 / 0.3 / 0.2 | 73 / 57 / 45 | 68428 (134418) | 6263 (6266) | 264082 (286468) | 0.2 | 38 | 0 |
| 297x210 | 2 | 106 | 3.87 | 0.3 / 0.2 / 0.2 | 55 / 47 / 35 | 139477 (146730) | 10006 (11050) | 319663 (334025) | 0.2 | 39 | 0 |

**vs1 / v4.pdf (6 pages)**

| mm | pages | max elements | Mpx at 200 | worst render s at 200/150/100 dpi | worst peak RSS MiB at 200/150/100 | preview B median (max) | thumbnail B median (max) | tiles B median (max) | worst extract s | worst extract RSS MiB | jobs over the ceiling |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 841x594 | 1 | 474 | 30.98 | 1.2 / 0.8 / 0.4 | 187 / 117 / 73 | 189380 (189380) | 12281 (12281) | 1422715 (1422715) | 0.1 | 38 | 0 |
| 420x297 | 3 | 252 | 7.74 | 0.4 / 0.3 / 0.2 | 73 / 57 / 45 | 68192 (134418) | 6266 (6269) | 263193 (286468) | 0.1 | 38 | 0 |
| 297x210 | 2 | 106 | 3.87 | 0.3 / 0.2 / 0.1 | 55 / 47 / 35 | 157998 (183771) | 11283 (11516) | 355918 (406534) | 0.2 | 39 | 0 |

**vs1 / v5.pdf (8 pages)**

| mm | pages | max elements | Mpx at 200 | worst render s at 200/150/100 dpi | worst peak RSS MiB at 200/150/100 | preview B median (max) | thumbnail B median (max) | tiles B median (max) | worst extract s | worst extract RSS MiB | jobs over the ceiling |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 594x420 | 2 | 256 | 15.47 | 0.7 / 0.4 / 0.3 | 108 / 78 / 55 | 174494 (174643) | 11340 (11504) | 760107 (760461) | 0.1 | 38 | 0 |
| 420x297 | 4 | 252 | 7.74 | 0.4 / 0.3 / 0.2 | 73 / 57 / 45 | 68192 (134418) | 6267 (6269) | 263193 (286468) | 0.2 | 38 | 0 |
| 297x210 | 2 | 106 | 3.87 | 0.3 / 0.2 / 0.2 | 55 / 47 / 35 | 163986 (193812) | 11527 (11960) | 366607 (425788) | 0.2 | 39 | 0 |

### 4.3 SP-1 (`fixtures/comparison/sp1/*.pdf`, 12 pages)

**sp1 / new_r1.pdf (3 pages)**

| mm | pages | max elements | Mpx at 200 | worst render s at 200/150/100 dpi | worst peak RSS MiB at 200/150/100 | preview B median (max) | thumbnail B median (max) | tiles B median (max) | worst extract s | worst extract RSS MiB | jobs over the ceiling |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 420x297 | 3 | 67 | 7.74 | 0.4 / 0.3 / 0.2 | 73 / 57 / 45 | 43299 (51182) | 3711 (4287) | 201052 (227086) | 0.1 | 38 | 0 |

**sp1 / new_r2.pdf (1 pages)**

| mm | pages | max elements | Mpx at 200 | worst render s at 200/150/100 dpi | worst peak RSS MiB at 200/150/100 | preview B median (max) | thumbnail B median (max) | tiles B median (max) | worst extract s | worst extract RSS MiB | jobs over the ceiling |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 420x297 | 1 | 52 | 7.74 | 0.4 / 0.3 / 0.2 | 73 / 57 / 45 | 60547 (60547) | 4326 (4326) | 253245 (253245) | 0.1 | 38 | 0 |

**sp1 / new_r3.pdf (2 pages)**

| mm | pages | max elements | Mpx at 200 | worst render s at 200/150/100 dpi | worst peak RSS MiB at 200/150/100 | preview B median (max) | thumbnail B median (max) | tiles B median (max) | worst extract s | worst extract RSS MiB | jobs over the ceiling |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 420x297 | 2 | 47 | 7.74 | 0.4 / 0.3 / 0.2 | 73 / 57 / 45 | 42838 (43869) | 3331 (3380) | 193727 (194814) | 0.1 | 38 | 0 |

**sp1 / old_p.pdf (6 pages)**

| mm | pages | max elements | Mpx at 200 | worst render s at 200/150/100 dpi | worst peak RSS MiB at 200/150/100 | preview B median (max) | thumbnail B median (max) | tiles B median (max) | worst extract s | worst extract RSS MiB | jobs over the ceiling |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 420x297 | 5 | 67 | 7.74 | 0.4 / 0.3 / 0.2 | 73 / 57 / 45 | 42142 (50707) | 3406 (4209) | 193135 (225237) | 0.2 | 38 | 0 |
| 297x210 | 1 | 41 | 3.87 | 0.3 / 0.2 / 0.1 | 54 / 46 / 34 | 84913 (84913) | 6187 (6187) | 202755 (202755) | 0.1 | 38 | 0 |

### 4.4 The realistic A1 (generated outside the repository, deleted afterwards)

Generated with `tools/fixtures/comparison/realistic_a1.py`: `heavy_a.pdf` and `heavy_b.pdf` (producers A and B,
`--paint-ops 76000`: 185 983 elements by the reader's count), `light_a.pdf` and `light_b.pdf` (`--paint-ops 0 --second`: 75 001
elements), and `max_a.pdf` (`--paint-ops 150000 --elements 400000`: 400 001 elements, 9.9 MB). All are `/Rotate 90` with a CropBox
inset of 8.5 pt, no text layer (0 words), one hidden optional-content layer.

**a1 / heavy_a.pdf (1 pages)**

| p | mm | elements | Mpx at 200 | render s at 200/150/100 dpi | peak RSS MiB at 200/150/100 | preview B | thumbnail B | tiles | tiles B | at dpi | words | lines | extract s | extract RSS MiB |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 835x588 | 185983 | 30.44 | 1.8 / 1.6 / 0.8 | 196 / 132 / 96 | 396665 | 18006 | 182 | 3905287 | 200 | 0 | 74773 | 7.1 | 303 |

**a1 / heavy_b.pdf (1 pages)**

| p | mm | elements | Mpx at 200 | render s at 200/150/100 dpi | peak RSS MiB at 200/150/100 | preview B | thumbnail B | tiles | tiles B | at dpi | words | lines | extract s | extract RSS MiB |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 835x588 | 185983 | 30.44 | 1.8 / 1.3 / 0.8 | 193 / 129 / 89 | 403695 | 18098 | 182 | 4004355 | 200 | 0 | 74773 | 4.7 | 287 |

**a1 / light_a.pdf (1 pages)**

| p | mm | elements | Mpx at 200 | render s at 200/150/100 dpi | peak RSS MiB at 200/150/100 | preview B | thumbnail B | tiles | tiles B | at dpi | words | lines | extract s | extract RSS MiB |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 835x588 | 75001 | 30.44 | 1.6 / 1.1 / 0.7 | 190 / 124 / 79 | 333004 | 15855 | 182 | 2835433 | 200 | 0 | 19282 | 2.4 | 121 |

**a1 / light_b.pdf (1 pages)**

| p | mm | elements | Mpx at 200 | render s at 200/150/100 dpi | peak RSS MiB at 200/150/100 | preview B | thumbnail B | tiles | tiles B | at dpi | words | lines | extract s | extract RSS MiB |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 835x588 | 75001 | 30.44 | 1.7 / 1.1 / 0.7 | 185 / 119 / 79 | 337570 | 15887 | 182 | 2846100 | 200 | 0 | 19282 | 1.6 | 117 |

**a1max / max_a.pdf (1 pages)**

| p | mm | elements | Mpx at 200 | render s at 200/150/100 dpi | peak RSS MiB at 200/150/100 | preview B | thumbnail B | tiles | tiles B | at dpi | words | lines | extract s | extract RSS MiB |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 835x588 | 400001 | 30.44 | 2.2 / 1.6 / 1.1 | 240 / 189 / 153 | 455846 | 19064 | 182 | 5087798 | 200 | 0 | 181782 | 17.4 | 654 |

Tile pyramid of `heavy_a.pdf` and of `max_a.pdf` at 200 dpi, by level (level 0 = the 200 dpi raster):

**a1 heavy_a.pdf p1 200 dpi, 30.442 Mpx: preview 396665 B, thumbnail 18006 B**

| level | px | tiles | PNG bytes | largest tile B |
| ---: | --- | ---: | ---: | ---: |
| 0 | 6575x4630 | 130 | 2529381 | 102912 |
| 1 | 3288x2315 | 35 | 878088 | 79210 |
| 2 | 1644x1158 | 12 | 339725 | 71727 |
| 3 | 822x579 | 4 | 122527 | 79173 |
| 4 | 411x290 | 1 | 35566 | 35566 |
| all | | 182 | 3905287 | |

**a1max max_a.pdf p1 200 dpi, 30.442 Mpx: preview 455846 B, thumbnail 19064 B**

| level | px | tiles | PNG bytes | largest tile B |
| ---: | --- | ---: | ---: | ---: |
| 0 | 6575x4630 | 130 | 3368294 | 187467 |
| 1 | 3288x2315 | 35 | 1123360 | 128321 |
| 2 | 1644x1158 | 12 | 412154 | 100164 |
| 3 | 822x579 | 4 | 143367 | 94643 |
| 4 | 411x290 | 1 | 40623 | 40623 |
| all | | 182 | 5087798 | |

## 5. Diagnostics

### 5.1 Repeatability

Three repeats of the heaviest jobs (`diag`, labels `rep1` to `rep3`, lean, 768 MiB): peak RSS is the same to within 1 MiB each time
(`v3` p13 at 200 dpi 684 / 684 / 683; at 150 dpi 716 / 716 / 716; `v3` p7 at 200 dpi 700 / 699 / 699; `v1` p8 at 200 dpi 662 ×3;
`v3` p12 extraction 631 ×3; realistic A1 render 196 / 196 / 195, extraction 302 ×3). Wall time moves with host load (`v1` p8 at 200
dpi 8.2 / 8.9 / 12.4 s at one-minute load averages of 4.8 / 8.5 / 15.3) while CPU time stays within 8.2 to 8.7 s. Memory figures are reproducible; wall
times are not, and the CPU column is the steadier one.

### 5.2 The smallest ceiling that passes (the floor)

Each job re-run at a ladder of ceilings (MiB), one child at a time. A cell is `ok RSS/VmPeak` in MiB, `over` (a `MemoryError`),
`SIGABRT` or `SIGTRAP` (PDFium aborted), or `CPU-stall` (ran to the CPU ceiling); an empty cell was not tried.

| job | 128 | 160 | 192 | 224 | 256 | 320 | 384 | 448 | 512 | 576 | 640 | 704 | 768 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| realistic A1 (producer A), 200 dpi, 30.4 Mpx | over | over | over | ok 196/216 | ok 196/216 | ok 196/216 |  |  |  |  |  |  | ok 196/216 |
| realistic A1 (producer B), 200 dpi, 30.4 Mpx | over | over | over | ok 193/213 | ok 193/213 | ok 193/213 |  |  |  |  |  |  | ok 193/213 |
| real v3 p13, 150 dpi, 69.7 Mpx |  |  |  |  |  | SIGABRT | SIGABRT | ok 416/435 | ok 416/435 | ok 416/435 | ok 415/435 | ok 651/670 | ok 717/736 |
| real v3 p7 (2102x594 mm), 200 dpi, 77.4 Mpx |  |  |  |  |  | over | over | ok 424/443 | ok 424/443 | ok 424/443 | ok 424/443 | ok 626/645 | ok 700/719 |
| real v3 p12 (1680x1190 mm), 200 dpi, 124.0 Mpx |  |  |  |  |  | over | over | over | over | over | over | ok 659/679 | ok 659/679 |
| real v3 p13, 200 dpi, 124.0 Mpx |  |  |  |  |  | over | over | over | over | SIGABRT | over | ok 684/704 | ok 684/704 |
| real v1 p8 (1682x1189 mm), 200 dpi, 124.0 Mpx |  |  |  |  |  | over | over | over | over | SIGTRAP | over | ok 663/682 | ok 663/682 |
| real v3 p12, pdfplumber words + lines |  |  |  |  |  |  |  |  | over | CPU-stall | over | ok 631/658 | ok 632/658 |
| 400 000-element A1, pdfplumber words + lines |  |  |  |  |  |  |  |  | over | over | over | ok 654/674 | ok 654/674 |

Reading: the realistic A1 needs 224 MiB; a 124 Mpx page at 200 dpi needs 704 MiB (it fails at 640; at 576 two of the three die by signal and the third by `MemoryError`); the
69.7 Mpx page at 150 dpi and the 77.4 Mpx page at 200 dpi need only 448 MiB although they use 717 and 700 MiB when allowed, and with
byte-identical output (the preview, thumbnail and tile bytes are the same at 640 and 768 MiB for both). The two heaviest
`pdfplumber` extractions need 704 MiB.

### 5.3 Other raster pipelines, heaviest pages (768 MiB)

`naive` is `to_pil()` of the default 3-byte `BGR` bitmap (a copy: about 7 bytes a pixel at the peak); `gray` is a 1-byte raster.

| pipeline | page | dpi | Mpx | status at 768 MiB | peak RSS / VmPeak MiB | ceiling that passed |
| --- | --- | ---: | ---: | --- | --- | --- |
| naive | v3.pdf p7 | 200 | 77.4 | ok | 643 / 662 | 768 |
| naive | v3.pdf p7 | 150 | 43.5 | ok | 376 / 395 | 768 |
| naive | v3.pdf p8 | 200 | 124.0 | OVERRUN | 1010 / 1030 (at 1536) | 1536 (failed at 1024) |
| naive | v3.pdf p8 | 150 | 69.7 | ok | 590 / 610 | 768 |
| naive | v3.pdf p13 | 200 | 124.0 | OVERRUN | 1064 / 1084 (at 1536) | 1536 (failed at 1024) |
| naive | v3.pdf p13 | 150 | 69.7 | ok | 651 / 670 | 768 |
| naive | v1.pdf p5 | 200 | 31.0 | ok | 270 / 290 | 768 |
| gray | v3.pdf p7 | 200 | 77.4 | ok | 477 / 495 | 768 |
| gray | v3.pdf p7 | 150 | 43.5 | ok | 282 / 301 | 768 |
| gray | v3.pdf p8 | 200 | 124.0 | ok | 748 / 768 | 768 |
| gray | v3.pdf p8 | 150 | 69.7 | ok | 436 / 456 | 768 |
| gray | v3.pdf p13 | 200 | 124.0 | ok | 710 / 729 | 768 |
| gray | v3.pdf p13 | 150 | 69.7 | ok | 518 / 537 | 768 |

The `naive` pipeline overruns the ceiling on both 124 Mpx pages and needs 1536 MiB (1024 MiB fails); the `lean` pipeline is what
the table in 4.1 measures. `gray` is not leaner on a 124 Mpx page (748 MiB, VmPeak 768 MiB, on the ceiling): PDFium's own working
memory, not the output raster, dominates there.

### 5.4 The guards, shown failing

Each guard of the script and the ceiling itself, with the quoted probe and its result (records in `probe`, `floor`, `diag`):

| guard | probe | result |
| --- | --- | --- |
| the address-space ceiling ends a job | A1 sheet of `vs1/v1.pdf` at 200 dpi, `--address-space-mib 120` | `overrun` after 0.08 s (last stage `render`) |
| the same, with the `RLIMIT_AS` call removed (a copy of the script with that line replaced by `pass`) | same command | **`ok`**, RSS 187 MiB: the ceiling is what ended the job |
| escalation proves the ceiling was the cause | `naive` pipeline, `v3` p8 and p13 at 200 dpi | `overrun` at 768, fails at 1024, `ok` at 1536 (RSS 1010 and 1064 MiB) |
| the CPU ceiling | `--cpu-seconds 2` on the 11 s extraction of `v3` p12 | `cpu` (SIGXCPU) at 2.2 s |
| the wall clock | `--wall-seconds 0.05` on a scan | `wall` at 0.052 s, the child killed by its own PID |
| a `MemoryError` inside `pdfplumber` is an overrun | `v3` p12 extraction at 640 MiB | `overrun` (before this classification was added the same failure was recorded as `error:PdfminerException`, in an earlier exploratory pass that is not used here) |
| a death by signal is a failure, not a result | two 124 Mpx pages at 200 dpi under 576 MiB; the 69.7 Mpx page at 150 dpi under 320 and 384 MiB | `signal:SIGABRT` (3) / `signal:SIGTRAP` (1) recorded, no figures |

One disturbed job: the `pdfplumber` extraction of `v3` p12 at 576 MiB ran to the CPU ceiling (298 s of CPU, 322 s wall) while the host
was swapping heavily (the child had 447 MB in swap at 110 MB RSS and its system time was three times its user time); two repeats
under a 60 s CPU limit gave `cpu` once and `overrun` (10.9 s) once, and an earlier exploratory pass gave `overrun` in 11 s. The outcome near the
ceiling is therefore not deterministic; the CPU ceiling bounds the cost. No figure in the tables comes from this job.

### 5.5 Rendering at the 40 Mpx dpi

The registration dpi that keeps a page at or under 40 Mpx is `floor(sqrt(40e6 / (width_in x height_in)))`: 143 for 2102 × 594 mm
and 113 for 1682 × 1189 mm. Nine heavy pages rendered at that dpi (`cap`, lean; bytes from the 768 MiB run):

| page | mm | dpi | Mpx | ceiling 768: s | RSS / VmPeak MiB | ceiling 512: RSS MiB | ceiling 384: RSS / VmPeak MiB | preview B | thumbnail B | tile pyramid B (tiles) |
| --- | --- | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | ---: |
| v1.pdf p8 | 1682x1189 | 113 | 39.6 | 3.3 | 240 / 260 | 240 | 240 / 260 | 429057 | 20231 | 5332360 (230) |
| v1.pdf p9 | 1682x1189 | 113 | 39.6 | 2.2 | 234 / 254 | 234 | 234 / 254 | 326321 | 17682 | 3511635 (230) |
| v2.pdf p12 | 1682x1189 | 113 | 39.6 | 4.0 | 380 / 401 | 381 | 343 / 363 | 824287 | 34733 | 11260031 (230) |
| v2.pdf p13 | 1682x1189 | 113 | 39.6 | 3.4 | 447 / 466 | 447 | 258 / 277 | 290292 | 17116 | 4384047 (230) |
| v3.pdf p7 | 2102x594 | 143 | 39.6 | 2.2 | 374 / 393 | 374 | 336 / 355 | 249423 | 12687 | 5459827 (234) |
| v3.pdf p8 | 1680x1190 | 113 | 39.6 | 2.9 | 376 / 396 | 376 | 338 / 358 | 635923 | 24117 | 8780722 (230) |
| v3.pdf p9 | 1680x1190 | 113 | 39.6 | 2.6 | 373 / 392 | 373 | 335 / 354 | 536392 | 19350 | 5804995 (230) |
| v3.pdf p12 | 1680x1190 | 113 | 39.6 | 3.9 | 380 / 401 | 381 | 343 / 363 | 840645 | 35875 | 11429586 (230) |
| v3.pdf p13 | 1680x1190 | 113 | 39.6 | 3.3 | 458 / 477 | 458 | 270 / 288 | 343407 | 19392 | 5062095 (230) |

Compare the same pages at 200 dpi (77.4 and 124.0 Mpx): 626 to 700 MiB RSS and 704 MiB needed for the 124 Mpx ones.

### 5.6 Pixels against peak memory

All lean render jobs that ended `ok` at 768 MiB (every dpi of the main pass plus the nine 40 Mpx runs), by pixel count:

| Mpx | jobs | largest Mpx | worst peak RSS MiB | worst VmPeak MiB | slowest wall s | most CPU s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0-4 | 142 | 3.9 | 86 | 104 | 1.4 | 1.4 |
| 4-8 | 106 | 7.8 | 153 | 173 | 1.1 | 1.1 |
| 8-16 | 17 | 15.5 | 161 | 180 | 1.2 | 1.2 |
| 16-32 | 33 | 31.0 | 384 | 403 | 2.9 | 2.9 |
| 32-48 | 12 | 43.5 | 458 | 477 | 4.0 | 3.6 |
| 48-80 | 13 | 77.4 | 717 | 736 | 4.9 | 4.8 |
| 80-130 | 10 | 124.0 | 684 | 704 | 8.5 | 8.4 |

The envelope of the worst page rises with pixels but not smoothly: the 48 to 80 Mpx bucket is the tightest relative to the ceiling
(736 MiB), above the 80 to 130 Mpx one (704 MiB), because the content of the page decides how much working memory PDFium takes.

### 5.7 Extraction: which pages are heavy

The eight pages with the largest extraction memory (the 43 MiB baseline is subtracted for the per-object figure):

| input | page | mm | elements | words | lines | rects | curves | pdfplumber objects | wall s | CPU s | peak RSS MiB | VmPeak MiB | KiB per object |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 400k-element A1 | max_a.pdf p1 | 835x588 | 400001 | 0 | 181782 | 169 | 1416 | 183367 | 17.4 | 17.4 | 654 | 674 | 3.41 |
| real set | v3.pdf p12 | 1680x1190 | 382424 | 2098 | 186861 | 248 | 547 | 198694 | 11.2 | 11.2 | 632 | 658 | 3.03 |
| real set | v2.pdf p12 | 1682x1189 | 368019 | 1979 | 179802 | 248 | 527 | 191144 | 10.8 | 10.7 | 609 | 628 | 3.03 |
| real set | v3.pdf p8 | 1680x1190 | 254059 | 1431 | 124225 | 254 | 276 | 132779 | 7.4 | 7.4 | 439 | 464 | 3.06 |
| real set | v1.pdf p7 | 2102x594 | 536426 | 0 | 4757 | 9 | 17557 | 22323 | 7.0 | 7.0 | 331 | 355 | 13.22 |
| realistic A1 | heavy_a.pdf p1 | 835x588 | 185983 | 0 | 74773 | 169 | 1416 | 76358 | 7.1 | 7.1 | 303 | 323 | 3.48 |
| real set | v1.pdf p8 | 1682x1189 | 376921 | 0 | 23666 | 40 | 11650 | 35356 | 14.9 | 14.8 | 302 | 324 | 7.49 |
| real set | v1.pdf p9 | 1682x1189 | 377155 | 0 | 22994 | 57 | 11281 | 34332 | 5.7 | 5.6 | 289 | 312 | 7.34 |

## 6. Recommendation for ADR-0025 decisions 8 and 9

Against a 4 GiB production host with one worker slot (decision 8: one child beside the API, the database and the object store). The
host's other occupants are not measured here (`PROD-05a`); every ceiling below is a child's own, and the sum with the API, the
database and the object store is `PROD-05a`'s to check. «Now» is the ADR's value.

### 6.1 Decision 8 — the child's ceilings

| Item | Now | Measured | Recommended |
| --- | --- | --- | --- |
| Address space, a render / registration / tile child | 768 MiB | at the 40 Mpx cap: worst VmPeak 477 MiB, passes at 384 MiB; realistic A1 at 200 dpi: VmPeak 216 MiB, passes at 224 MiB | **keep 768 MiB** (1.6 times the worst capped page, 3.5 times an A1) |
| Address space, a child that runs `pdfplumber` words and lines | 768 MiB | worst VmPeak 658 MiB (real) and 674 MiB (400 001-element A1); passes at 704, fails at 640; fitted on the 108 pages: `VmPeak ≈ 70 MiB + (3.3 KiB x (lines + rects + chars) + 16 KiB x curves) / 1024`, which is within −1 % to +15 % on the 16 pages above 150 MiB; measured only to 198 694 objects | **1024 MiB for this child**, or keep 768 MiB and refuse before extraction a page whose PDFium-counted lines + rects + chars + 5 x curves exceed ~200 000 (the model puts 768 MiB at ~216 000 and 1024 MiB at ~296 000; the model is an extrapolation above 198 694) |
| CPU | 300 s | most CPU of any job: 17.4 s (extraction), 8.4 s (render + pyramid) | **keep 300 s** |
| Wall | 600 s | longest successful job 17.4 s in the main pass (load 3 to 7), 17.9 s in a repeat (load 13) | **keep 600 s** — below the 900 s watchdog |
| What one item is | not fixed | a real 26-page file: 41 s of rendering at 200 dpi plus 35 s of extraction (section 4.1); at the same per-page average 600 s covers about 200 pages and a 500-page file would take ~24 min | **one page per child** (or a few); a whole 500-page file in one child cannot meet 600 s |
| An overrun | «typed `needs_review` with reason `RENDER_FAILED`» | the child ended as `MemoryError`, `SIGABRT` or `SIGTRAP`, or ran to the CPU ceiling (and, once in an exploratory pass, exited with status 1) | **any end without a result is `RENDER_FAILED`** (not only a `MemoryError`); a hit can cost up to the 300 s CPU ceiling, so the ceiling is also what bounds the wasted time |
| Ceiling of the upload reader | 512 MiB | not measured here | unchanged |

### 6.2 Decision 9 — pixels

| Quantity | Now | Measured | Recommended |
| --- | --- | --- | --- |
| Working raster per page | at most 40 Mpx | 124.0 Mpx at 200 dpi passes at 768 MiB with RSS 662 to 684 MiB and needs 704 MiB (64 MiB of margin); a 69.7 Mpx page reached VmPeak 736 MiB (96 % of the ceiling); 39.6 Mpx pages: VmPeak ≤ 477 MiB, floor ≤ 384 MiB; A1: 30.4 to 31.0 Mpx | **keep 40 Mpx**: the measurement alone would allow more for a render, but above the cap the margin is 32 to 64 MiB and depends on the page's content, and the engine's several rasters per pair are not measured yet (`CMP-ENGINE-01`) |
| Registration downsample | fixed by `CMP-PROFILE-01` and `CMP-ENGINE-01` | rendering at the cap dpi needs ≤ 477 MiB; rendering at 200 dpi and shrinking needs up to 704 MiB | **render at `dpi = min(200, floor(sqrt(40e6 / (width_in x height_in))))`**: 200 dpi for every page up to 891 × 420 mm (23.2 Mpx) and for A1 (30.4 to 31.0 Mpx); 143 for 2102 × 594 mm; 113 for 1682 × 1189 mm; 160 for A0 (1189 × 841 mm, computed, not measured) |
| Pages refused | typed state | no page in the set exceeded the cap after downsampling | unchanged |

### 6.3 Decision 9 — bytes (per page, 200 dpi, PNG)

| kind of page | pages | Mpx | preview B | thumbnail B | tile pyramid B (all levels) | levels 0 / 1 / 2+ B | tiles |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| realistic A1, producer A (strokes-only text, 185 983 elements) | 1 | 30.44 | 396665 | 18006 | 3905287 | 2529381 / 878088 / 497818 | 182 |
| realistic A1, producer B | 1 | 30.44 | 403695 | 18098 | 4004355 | 2617567 / 890421 / 496367 | 182 |
| realistic A1, 75 001 elements (`--paint-ops 0`), producer A | 1 | 30.44 | 333004 | 15855 | 2835433 | 1794902 / 645955 / 394576 | 182 |
| realistic A1, 400 001 elements | 1 | 30.44 | 455846 | 19064 | 5087798 | 3368294 / 1123360 / 596144 | 182 |
| VS-1 A1 sheet (synthetic, sparse) | 1 | 30.98 | 187156 | 11933 | 1421039 | 878259 / 335443 / 207337 | 182 |
| real A3 vector (420x297 mm), v3 | 6 | 7.74 | 304130 | 18535 | 880308 | 531979 / 216488 / 131841 | 52 |
| real 891x420 mm vector, v3 | 2 | 23.21 | 329528 | 14644 | 3212597 | 1945288 / 795824 / 471484 | 137 |
| real A4 scan (297x210 mm), v3 p20-26 | 7 | 3.86 | 2911466 | 63937 | 9806356 | 7174317 / 2016896 / 615143 | 29 |
| real 2102x594 mm (77.4 Mpx), v3 p7 | 1 | 77.43 | 248990 | 12529 | 8484560 | 5118878 / 2039173 / 1326509 | 458 |
| real 2A0-size (1680x1190 mm, 124 Mpx) at 200 dpi, v3 p8,9,12,13 | 4 | 123.96 | 541388 | 23404 | 15484142 | 9505458 / 3767021 / 2211663 | 676 |

Levels 0 and 1 of the pyramid are the 200 dpi and 100 dpi rasters; they are 84 to 94 % of the bytes. Rendering a tile of level 0 or
1 on request was not timed here (a whole page costs 1.7 s for the A1 including the preview and pyramid, of which the render itself is
0.3 s); that is `CMP-VIEWER-01`'s to measure.

Per project of **12 versions × 100 sheets = 1 200 pages**, the stored derived bytes for different page profiles (1 GB = 10^9 bytes;
`pages x bytes per page`, the per-page figures averaged over the profile's measured pages):

| page profile | preview + thumbnail | + tile levels 2 and up | whole tile pyramid | everything |
| --- | ---: | ---: | ---: | ---: |
| realistic A1 (A and B averaged) | 0.50 GB | 1.10 GB | 4.75 GB | 5.25 GB |
| realistic A1, 400 001 elements | 0.57 GB | 1.29 GB | 6.11 GB | 6.68 GB |
| real set v2 mix (18 pages) | 0.40 GB | 1.08 GB | 4.65 GB | 5.05 GB |
| real set v3 mix (26 pages, 7 scans) | 1.26 GB | 2.04 GB | 7.15 GB | 8.42 GB |
| all A4 scans (v3 p20-26) | 3.57 GB | 4.31 GB | 11.77 GB | 15.34 GB |

| Quantity | Now | Measured | Recommended |
| --- | --- | --- | --- |
| Preview and thumbnail per page | «once per page» | vector A3 to A1: 0.05 to 0.48 MB; 124 Mpx page: 0.57 MB; A4 scan: 2.98 MB | store both, once per page; a scan costs 6 times the heaviest vector sheet measured (0.48 MB) and more than 9 times any other |
| Tile pyramid | «a level kept as a blob or rendered on request, left to `CMP-PROFILE-01` and `CMP-VIEWER-01`; the bytes it keeps count in the page budget» | the whole pyramid is 4.7 to 6.1 GB per 1 200 vector pages, 7.2 GB for the v3 mix and 11.8 GB for scans, i.e. 54 to 137 % of the 8 GiB project cap before sources (1–2 GB) and masks (0.5–3 GB) | **do not keep the whole pyramid as blobs.** Keep levels 2 and up if the viewer needs a stored overview (+0.5 to 0.8 GB), and render levels 0 and 1 again on request in the child |
| Derived bytes per project (preview, thumbnail, levels 2+) | ADR estimate: previews and thumbnails 0.4–1.2 GB | 0.4 to 1.3 GB (vector, v3 mix with 7 of 26 pages as scans), 1.1 to 2.0 GB with levels 2+, 4.3 GB for an all-scan project | the ADR's 1.9–6.2 GB total holds for vector sets; **the 8 GiB cap stays**; an all-scan project is the case that approaches it (4.3 GB derived + sources + masks) |
| Stored bytes per project cap | 8 GiB | | unchanged |

Masks are written by the engine and are not measured here.

## 7. Known limits

- **One host, one run, shared.** Times depend on load (section 2); memory figures repeated to within 1 MiB. RSS counts resident pages;
  with swap in use a child's pages could be out of RSS, which the VmPeak column (virtual, unaffected) cross-checks: VmPeak − VmHWM is
  13 to 32 MiB on all 601 completed jobs of the final pass.
- **The elasticity (section 5.2) is observed, not explained.** PDFium or the allocator keeps up to ~300 MiB more when allowed; the
  report does not say which. The floors are in steps of 32 to 64 MiB and only for nine jobs.
- **No engine.** `numpy` and OpenCV are absent; the 40 Mpx cap is a policy that this measurement supports for rendering only. The
  engine's own rasters, masks and bytes per pair are `CMP-ENGINE-01`'s.
- **Tiles on request are not timed**, only a whole page with its whole pyramid.
- **PNG only, Pillow defaults.** JPEG or WebP previews were not compared; scans are where the byte difference would be.
- **The realistic A1 is synthetic**: strokes-only text, no images, no transparency, no patterns beyond hatches. The real 2A0 pages
  show how much content decides PDFium's memory; a real A1 may differ from the generated one in either direction.
- **One real set** of one object (4 versions, 85 pages, 7 scans); `v4` equals `v3`. Its size summary in the README does not match PDFium's
  displayed sizes for some pages.
- **Extraction was measured only to 198 694 `pdfplumber` objects**; the per-object extrapolations in 6.1 are not measurements.
  Characters (pages with a text layer of tens of thousands of words) were not stressed: the heaviest real text pages have ~2 000 words.
- **Each child is cold** (interpreter start and imports are in every wall time); the page cache of the PDF is warm.
- **The exploratory passes before the final one are not used.** The script differed from the committed one only in how a wrapped
  `MemoryError` was classified, in `--dpi ""` (no render) and in how tables were printed; every figure above is from the final pass on `64f7e2f0`.

## 8. How to reproduce

```
PY=/root/projects/PDF-Analysis/.venv/bin/python; M=tools/measure/comparison_render.py; R=.local/comparison-measure/13AV-RD-EM2-PA
df -h /                                            # stop under 1.5 GiB free
$PY tools/fixtures/comparison/realistic_a1.py OUT/heavy_a.pdf --second OUT/heavy_b.pdf             # outside the repository
$PY tools/fixtures/comparison/realistic_a1.py OUT/light_a.pdf --second OUT/light_b.pdf --paint-ops 0
$PY tools/fixtures/comparison/realistic_a1.py OUT/max_a.pdf --paint-ops 150000 --elements 400000
$PY $M run --label vs1  --results main.jsonl --escalate 1024,1536 fixtures/comparison/vs1/v{1,2,3,4,5}.pdf
$PY $M run --label sp1  --results main.jsonl --escalate 1024,1536 --skip-baseline fixtures/comparison/sp1/{old_p,new_r1,new_r2,new_r3}.pdf
$PY $M run --label a1   --results main.jsonl --escalate 1024,1536,2048 --skip-baseline OUT/{heavy_a,heavy_b,light_a,light_b}.pdf
$PY $M run --label a1max --results main.jsonl --escalate 1024,1536,2048 --skip-baseline OUT/max_a.pdf
$PY $M run --label real --results main.jsonl --escalate 1024,1536,2048 --skip-baseline $R/v{1,2,3}.pdf
$PY $M run --label floor --results floor.jsonl --skip-baseline --address-space-mib 640 --no-extract --dpi 200 --pages 13 $R/v3.pdf   # a ladder: 704 ... 320
$PY $M run --label cap40 --results cap.jsonl --skip-baseline --no-extract --dpi 113 --pages 8,9,12,13 $R/v3.pdf
$PY $M table --results main.jsonl --label real --by class      # or --by page
$PY $M levels --results main.jsonl --label a1 --file heavy_a.pdf --page 1
$PY $M fit --results main.jsonl
```

The main pass (450 children) took 6.7 minutes; the whole final pass with its diagnostics took 22 minutes. The generated A1 PDFs were
deleted after the pass. The real set itself is still at `.local/comparison-measure/13AV-RD-EM2-PA/`; its README says to delete it after
the measurement, which is the integrator's call (`CMP-MEASURE-01` may still need it). The records of this pass hold numbers only.

## Appendix A. The real set, per page

Columns as in section 4; `render s` and `peak RSS MiB` are `200 / 150 / 100 dpi`; bytes are from the 200 dpi job.

**real / v1.pdf (15 pages)**

| p | mm | elements | Mpx at 200 | render s at 200/150/100 dpi | peak RSS MiB at 200/150/100 | preview B | thumbnail B | tiles | tiles B | at dpi | words | lines | extract s | extract RSS MiB |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 210x297 | 144 | 3.87 | 0.3 / 0.2 / 0.2 | 56 / 47 / 36 | 141770 | 8722 | 29 | 332186 | 200 | 55 | 0 | 0.2 | 47 |
| 2 | 210x297 | 158 | 3.87 | 0.3 / 0.2 / 0.2 | 56 / 47 / 36 | 164664 | 9971 | 29 | 388587 | 200 | 62 | 0 | 0.1 | 47 |
| 3 | 210x297 | 143 | 3.87 | 0.3 / 0.2 / 0.1 | 56 / 47 / 35 | 201803 | 11025 | 29 | 518818 | 200 | 52 | 0 | 0.1 | 47 |
| 4 | 210x297 | 1030 | 3.87 | 0.3 / 0.3 / 0.2 | 57 / 48 / 36 | 309453 | 15720 | 29 | 816809 | 200 | 70 | 0 | 0.2 | 47 |
| 5 | 630x297 | 180153 | 11.60 | 0.7 / 0.5 / 0.3 | 90 / 68 / 51 | 313107 | 15392 | 74 | 1694816 | 200 | 0 | 454 | 2.3 | 139 |
| 6 | 420x297 | 341550 | 7.74 | 0.7 / 0.5 / 0.4 | 76 / 60 / 46 | 763417 | 30069 | 52 | 2486871 | 200 | 0 | 106 | 4.4 | 221 |
| 7 | 2102x594 | 536426 | 77.43 | 2.4 / 1.7 / 1.0 | 417 / 248 / 129 | 211920 | 10704 | 458 | 7012449 | 200 | 0 | 4757 | 7.0 | 331 |
| 8 | 1682x1189 | 376921 | 124.00 | 8.5 / 3.8 / 2.3 | 663 / 400 / 196 | 408792 | 18900 | 676 | 10318894 | 200 | 0 | 23666 | 14.9 | 302 |
| 9 | 1682x1189 | 377155 | 124.00 | 4.0 / 2.5 / 1.5 | 656 / 392 / 190 | 309572 | 16496 | 676 | 6587172 | 200 | 0 | 22994 | 5.7 | 289 |
| 10 | 594x420 | 137745 | 15.47 | 0.9 / 0.6 / 0.5 | 112 / 81 / 58 | 388289 | 21450 | 99 | 2018524 | 200 | 0 | 2378 | 2.0 | 122 |
| 11 | 594x420 | 134520 | 15.47 | 0.9 / 0.6 / 0.4 | 112 / 81 / 58 | 360333 | 20089 | 99 | 1873698 | 200 | 0 | 1855 | 2.0 | 119 |
| 12 | 420x297 | 71775 | 7.75 | 0.5 / 0.3 / 0.2 | 75 / 58 / 46 | 213499 | 16071 | 52 | 676921 | 200 | 0 | 267 | 1.0 | 82 |
| 13 | 421x297 | 44456 | 7.76 | 0.4 / 0.3 / 0.2 | 74 / 58 / 45 | 153495 | 15819 | 52 | 498478 | 200 | 0 | 520 | 0.7 | 68 |
| 14 | 421x297 | 65281 | 7.76 | 0.4 / 0.3 / 0.2 | 75 / 59 / 46 | 206923 | 17099 | 52 | 655797 | 200 | 0 | 416 | 0.9 | 79 |
| 15 | 420x297 | 42032 | 7.75 | 0.4 / 0.3 / 0.2 | 74 / 58 / 45 | 137217 | 12480 | 52 | 457390 | 200 | 0 | 282 | 0.6 | 67 |

**real / v2.pdf (18 pages)**

| p | mm | elements | Mpx at 200 | render s at 200/150/100 dpi | peak RSS MiB at 200/150/100 | preview B | thumbnail B | tiles | tiles B | at dpi | words | lines | extract s | extract RSS MiB |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 210x297 | 144 | 3.87 | 0.3 / 0.2 / 0.2 | 56 / 47 / 36 | 141770 | 8722 | 29 | 332186 | 200 | 55 | 0 | 0.2 | 39 |
| 2 | 210x297 | 158 | 3.87 | 0.3 / 0.2 / 0.2 | 56 / 48 / 36 | 164664 | 9971 | 29 | 388587 | 200 | 62 | 0 | 0.2 | 39 |
| 3 | 210x297 | 143 | 3.87 | 0.3 / 0.2 / 0.2 | 56 / 47 / 35 | 201803 | 11025 | 29 | 518818 | 200 | 52 | 0 | 0.2 | 39 |
| 4 | 210x297 | 1030 | 3.87 | 0.3 / 0.3 / 0.2 | 56 / 48 / 36 | 309453 | 15720 | 29 | 816809 | 200 | 70 | 0 | 0.2 | 40 |
| 5 | 630x297 | 8079 | 11.60 | 0.7 / 0.5 / 0.3 | 127 / 83 / 52 | 319456 | 15669 | 74 | 1679690 | 200 | 405 | 3157 | 0.4 | 57 |
| 6 | 420x297 | 7010 | 7.74 | 0.6 / 0.5 / 0.3 | 94 / 64 / 48 | 788012 | 30318 | 52 | 2226984 | 200 | 894 | 2762 | 0.4 | 62 |
| 7 | 2102x594 | 24945 | 77.43 | 3.2 / 2.0 / 1.2 | 698 / 406 / 197 | 241600 | 12122 | 458 | 8198713 | 200 | 1962 | 8171 | 1.1 | 97 |
| 8 | 1682x1189 | 70139 | 124.00 | 4.1 / 3.3 / 1.8 | 652 / 631 / 297 | 396804 | 18440 | 676 | 10277656 | 200 | 1196 | 32748 | 2.3 | 156 |
| 9 | 1682x1189 | 71161 | 124.00 | 3.7 / 2.9 / 1.7 | 653 / 631 / 298 | 306539 | 16236 | 676 | 6597972 | 200 | 1185 | 33121 | 2.4 | 157 |
| 10 | 594x420 | 15111 | 15.47 | 1.0 / 0.6 / 0.4 | 161 / 103 / 61 | 398374 | 21500 | 99 | 2020712 | 200 | 438 | 6377 | 0.7 | 64 |
| 11 | 594x420 | 13810 | 15.47 | 1.2 / 0.8 / 0.4 | 161 / 102 / 61 | 366167 | 20062 | 99 | 1868760 | 200 | 414 | 5775 | 0.6 | 62 |
| 12 | 1682x1189 | 368019 | 124.00 | 5.5 / 4.2 / 2.5 | 659 / 653 / 307 | 752282 | 32362 | 676 | 21535465 | 200 | 1979 | 179802 | 10.8 | 609 |
| 13 | 1682x1189 | 11624 | 124.00 | 5.1 / 4.1 / 2.5 | 658 / 706 / 373 | 289372 | 16967 | 676 | 10439256 | 200 | 799 | 3746 | 0.6 | 64 |
| 14 | 420x297 | 3453 | 7.74 | 0.5 / 0.4 / 0.3 | 93 / 64 / 47 | 224219 | 16245 | 52 | 670266 | 200 | 202 | 1403 | 0.3 | 46 |
| 15 | 420x297 | 1547 | 7.74 | 0.5 / 0.3 / 0.2 | 93 / 64 / 46 | 165240 | 15609 | 52 | 498005 | 200 | 155 | 521 | 0.2 | 42 |
| 16 | 420x297 | 1430 | 7.74 | 0.5 / 0.5 / 0.3 | 93 / 64 / 46 | 216051 | 16990 | 52 | 630664 | 200 | 206 | 417 | 0.2 | 42 |
| 17 | 420x297 | 1047 | 7.74 | 0.5 / 0.3 / 0.2 | 93 / 64 / 46 | 150245 | 12993 | 52 | 466861 | 200 | 155 | 284 | 0.2 | 41 |
| 18 | 420x297 | 1395 | 7.74 | 0.5 / 0.4 / 0.3 | 93 / 64 / 46 | 225752 | 15622 | 52 | 641094 | 200 | 198 | 426 | 0.2 | 43 |

**real / v3.pdf (26 pages)**

| p | mm | elements | Mpx at 200 | render s at 200/150/100 dpi | peak RSS MiB at 200/150/100 | preview B | thumbnail B | tiles | tiles B | at dpi | words | lines | extract s | extract RSS MiB |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 210x297 | 144 | 3.87 | 0.3 / 0.2 / 0.2 | 56 / 47 / 36 | 141770 | 8722 | 29 | 332186 | 200 | 55 | 0 | 0.2 | 38 |
| 2 | 210x297 | 158 | 3.87 | 0.3 / 0.2 / 0.2 | 56 / 48 / 36 | 164664 | 9971 | 29 | 388587 | 200 | 62 | 0 | 0.2 | 39 |
| 3 | 210x297 | 143 | 3.87 | 0.3 / 0.2 / 0.2 | 56 / 47 / 36 | 201803 | 11025 | 29 | 518818 | 200 | 52 | 0 | 0.2 | 38 |
| 4 | 210x297 | 1030 | 3.87 | 0.4 / 0.3 / 0.2 | 57 / 48 / 36 | 309453 | 15720 | 29 | 816809 | 200 | 70 | 0 | 0.2 | 40 |
| 5 | 630x297 | 8131 | 11.60 | 0.8 / 0.5 / 0.4 | 127 / 83 / 52 | 325204 | 15870 | 74 | 1709296 | 200 | 419 | 3171 | 0.5 | 57 |
| 6 | 420x297 | 7010 | 7.74 | 0.6 / 0.5 / 0.3 | 94 / 65 / 48 | 788249 | 30393 | 52 | 2223501 | 200 | 896 | 2762 | 0.5 | 62 |
| 7 | 2102x594 | 24391 | 77.43 | 3.2 / 2.0 / 1.2 | 700 / 408 / 200 | 248990 | 12529 | 458 | 8484560 | 200 | 1954 | 8051 | 1.2 | 96 |
| 8 | 1680x1190 | 254059 | 123.96 | 4.8 / 3.9 / 2.1 | 657 / 636 / 306 | 572449 | 22494 | 676 | 17310146 | 200 | 1431 | 124225 | 7.4 | 439 |
| 9 | 1680x1190 | 137427 | 123.96 | 4.1 / 3.4 / 1.9 | 654 / 633 / 299 | 478251 | 18131 | 676 | 10696608 | 200 | 1452 | 65861 | 4.2 | 261 |
| 10 | 891x420 | 99194 | 23.21 | 1.4 / 0.9 / 0.6 | 230 / 142 / 82 | 368303 | 15178 | 137 | 3775605 | 200 | 516 | 48157 | 3.0 | 193 |
| 11 | 891x420 | 112347 | 23.21 | 1.3 / 0.9 / 0.5 | 229 / 142 / 79 | 290752 | 14110 | 137 | 2649589 | 200 | 492 | 54765 | 3.2 | 214 |
| 12 | 1680x1190 | 382424 | 123.96 | 6.4 / 4.9 / 2.9 | 659 / 641 / 307 | 774313 | 33768 | 676 | 21979077 | 200 | 2098 | 186861 | 11.2 | 632 |
| 13 | 1680x1190 | 12557 | 123.96 | 5.5 / 4.2 / 2.5 | 684 / 717 / 384 | 340541 | 19223 | 676 | 11950739 | 200 | 1006 | 3866 | 0.6 | 67 |
| 14 | 420x297 | 3544 | 7.74 | 0.5 / 0.4 / 0.3 | 94 / 64 / 47 | 233212 | 17102 | 52 | 699313 | 200 | 208 | 1441 | 0.3 | 46 |
| 15 | 420x297 | 1549 | 7.74 | 0.5 / 0.4 / 0.2 | 93 / 64 / 46 | 165184 | 15594 | 52 | 498185 | 200 | 155 | 521 | 0.2 | 42 |
| 16 | 420x297 | 1432 | 7.74 | 0.5 / 0.3 / 0.2 | 93 / 64 / 46 | 216014 | 16999 | 52 | 630572 | 200 | 206 | 417 | 0.2 | 42 |
| 17 | 420x297 | 1049 | 7.74 | 0.5 / 0.3 / 0.2 | 93 / 64 / 46 | 150189 | 13002 | 52 | 467040 | 200 | 155 | 284 | 0.2 | 41 |
| 18 | 420x297 | 1680 | 7.74 | 0.5 / 0.4 / 0.3 | 93 / 64 / 46 | 271929 | 18122 | 52 | 763239 | 200 | 243 | 531 | 0.2 | 44 |
| 19 | 210x297 | 15425 | 3.87 | 0.3 / 0.2 / 0.2 | 62 / 50 / 37 | 199251 | 14628 | 29 | 442326 | 200 | 125 | 0 | 0.5 | 55 |
| 20 | 210x297 | 8 | 3.86 | 1.3 / 0.9 / 0.5 | 85 / 73 / 64 | 2842138 | 64164 | 29 | 9470615 | 200 | 0 | 0 | 0.1 | 40 |
| 21 | 210x297 | 8 | 3.86 | 1.2 / 0.8 / 0.5 | 86 / 73 / 64 | 2934020 | 64205 | 29 | 9906076 | 200 | 0 | 0 | 0.1 | 40 |
| 22 | 210x297 | 8 | 3.86 | 1.2 / 0.8 / 0.5 | 86 / 73 / 64 | 2914795 | 64057 | 29 | 9829852 | 200 | 0 | 0 | 0.1 | 40 |
| 23 | 210x297 | 8 | 3.86 | 1.2 / 0.8 / 0.5 | 86 / 73 / 64 | 2937355 | 65108 | 29 | 9925952 | 200 | 0 | 0 | 0.2 | 40 |
| 24 | 210x297 | 8 | 3.86 | 1.4 / 0.8 / 0.5 | 86 / 73 / 64 | 2941056 | 65347 | 29 | 9935492 | 200 | 0 | 0 | 0.2 | 40 |
| 25 | 210x297 | 8 | 3.86 | 1.3 / 0.9 / 0.5 | 86 / 72 / 64 | 2885104 | 62806 | 29 | 9708517 | 200 | 0 | 0 | 0.1 | 40 |
| 26 | 210x297 | 8 | 3.86 | 1.3 / 0.8 / 0.5 | 86 / 73 / 64 | 2925793 | 61874 | 29 | 9867989 | 200 | 0 | 0 | 0.1 | 40 |
