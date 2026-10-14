# W55B-REHEARSAL-01 — report (the two halves of W55b at their limits, and the real export once)

- Task: the wave integrator's brief for lane `W55B-REHEARSAL-01` and its addendum (a hard memory cap, from JUDGE-X X-1/X-2);
  owner ruling `R-122` (`OWNER_RULINGS_2026-09-17.md` §3.33 on `integration/w55b`): runs at once, in parallel with the judges
  and QA, on a disposable stack of this host; figures on a loaded host and on the tree before `W55B-FIX` are accepted; each
  figure records its tree, load and available memory. F-7 and `R-119`: the owner's export is read only, this report holds
  counts only, nothing derived from it is committed.
- Branch `agent/w55b`, worktree `.local/worktrees/w55b-exec`, base `e1233e7a` (the WEB-BLOCKS report). The product code
  measured is `e1233e7a`'s: this lane changed no file outside its grant.
- Written by one writer (a Claude Opus 5.5 delegate of the wave executor). Nothing is pushed, merged or tagged.
- **Result in one line.** (a) a 500-page text-rich bundle uploads in 0.8 to 1.1 s and its start is refused up front
  (`422 analysis_input_budget_exceeded`, 1 786 430 > 152 361 characters, nothing created); (b) a 500-page low-text bundle
  (210 MiB) uploads in 1.8 s (API `VmHWM` +342 MiB), `source_preparation` takes 1.4 s and `page_geometry_extraction` 108 to
  111 s, the API peaks at 586 MiB RSS (cgroup `memory.peak` 0.75 to 0.76 GiB under a 3 GiB cap), 500 crops of 396.6 MiB, and «Блоки»
  loads all 1 500 blocks in 14 presses of about 0.2 s each; (c) the owner's export runs both stages (15.3 s and 23.6 s,
  peak RSS 1.0 GiB for 30 pages) and **all 47 crops show the region their block marks** (47/47 by eye, 47/47 by the numeric
  control, 0 blank). **Two findings for `W55B-FIX`:** the pdfplumber pass keeps about 24 MiB per drawing page (the export's
  mean), so a 500-page drawing set was killed by the 3 GiB cap at page 126 three times and then failed as plain
  `analysis_failed`; and the Next BFF's resident set grows by about the upload's size (+231 to +242 MiB for 210 MiB).
  **Owed:** the real set's live input-token count (no live call, `R-29`).

## 1. Changed files

`git diff --name-only e1233e7a..HEAD` (ten paths, all new; the grant is `scripts/rehearsal/w55b/**` and this file):

```text
docs/program/W55B-REHEARSAL-01.md                 this report
scripts/rehearsal/w55b/common.py                  outputs, the context every figure carries, the capacity gate, the cap, guards
scripts/rehearsal/w55b/build_bundles.py           the deterministic generators: text-rich, low-text, vector; `check`
scripts/rehearsal/w55b/sampler.py                 VmRSS/VmHWM and cgroup memory every 0.25 s; `control` (a known allocation)
scripts/rehearsal/w55b/stack.py                   API and Next started in capped systemd scopes, stopped by their own PID; `capped`
scripts/rehearsal/w55b/instrumented_serve.py      serve.py run unchanged, with the resident set recorded per page of each stage
scripts/rehearsal/w55b/drive.py                   account, upload (API or BFF), start-refused, run, blocks, fetch, recovery, scope
scripts/rehearsal/w55b/browser_blocks.mjs         «Блоки» in a cold browser through the journey's own cdp.mjs/session.mjs
scripts/rehearsal/w55b/crop_fidelity.py           each crop against the same region of a whole-page render; contact sheets
scripts/rehearsal/w55b/figures.py                 the report's tables from the phase figures
```

No file under `src/`, `web/`, `tests/`, `contracts/`, `fixtures/`, `tools/`, `infra/` or the root was edited; `tools/fixtures`
is imported, never changed. No generated bundle, figure, crop, sheet or log is committed: they lived under
`.local/rehearsal-w55b/` (git-ignored, `git check-ignore` confirmed) and were deleted with the stack (section 6).

## 2. What was run, and what it measured

### 2.0 Method (the decisions, each open to the integrator's veto)

1. **One private stack, recorded provider mode, no paid call.** `.env` from `.env.example` with only
   `FOUNDATION_INSTANCE=auditmanager-w55b-rehearsal`, `POSTGRES_PORT=57480`, `DATABASE_URL` (same port), `S3_API_PORT=61080`,
   `S3_CONSOLE_PORT=61081`, `S3_ENDPOINT_URL=http://127.0.0.1:61080`; `make up`, `make migrate`, `make check-db` (exit 0 each,
   head `0021_portal_bundles`). API: `infra/deploy/serve.py` on `57580` (health `57581`), `AUDITMANAGER_PROVIDER_MODE=recorded`,
   a generated `AUDITMANAGER_API_TOKEN` held in a mode-0600 file under `.local/rehearsal-w55b/` and passed by environment only.
   `EXECUTION_ROLE` unset, i.e. `all`: the run carrier is a thread of the serving process (`runs/carrier.py`,
   `DurableCarrier`), so **every stage ran inside the API process whose memory was sampled** (on the stand the worker process
   runs them). Web: `NEXT_PUBLIC_API_BASE_URL=/bff/v1 NEXT_PUBLIC_INSTANCE_LABEL=w55b-rehearsal npm --prefix web run build`,
   then `npx next start -p 31680 -H 127.0.0.1` with `AUDITMANAGER_API_UPSTREAM=http://127.0.0.1:57580` and the same secret.
   Account: the migration's seeded `admin`, password changed through `POST /auth/password`, profile completed through
   `PATCH /me` (`drive.py account`), as INGEST did.
2. **The hard memory cap (the integrator's addendum).** Every process of this lane that can grow ran in a transient systemd
   scope, `systemd-run --scope -p MemoryMax=<N> -p MemorySwapMax=0` (cgroup v2, the system manager; checked first with a
   64 MiB scope that the kernel killed a 200 MiB allocation inside it and nothing else). `N` = min(ceiling, `MemAvailable`
   − 1 GiB) at the start, recorded with that `MemAvailable`: the API 3 GiB at every one of its 15 starts (`MemAvailable`
   4 405 to 6 965 MiB); Next 1.5 GiB (one start at 2 787 MiB available — Next starts at about 130 MiB, so it was not held for
   the 3 GiB floor; noted); the browser drives 2 GiB; the bundle builds and the fidelity check 2 to 3 GiB; the web build
   2 335 MiB (`MemAvailable` 3 359 MiB). The API was restarted before each heavy phase so its scope's `memory.peak` (which
   this 6.8 kernel cannot reset) is that phase's.
3. **Memory per phase, three readings.** (i) the kernel's high-water mark, reset right before the phase
   (`echo 5 > /proc/<pid>/clear_refs`) and read after (`VmHWM`); (ii) `VmRSS` and the scope's `memory.current`/`memory.peak`
   sampled every 0.25 s with wall-clock time, aligned with each stage's `started_at`/`finished_at` in `stage_result`;
   (iii) **per page**: `instrumented_serve.py` runs `serve.py` unchanged and wraps, in that process only, the pdfplumber page
   step (`extraction._extract_page`, used by both stages), PDFium's page-box read, each crop render and each crop publish,
   appending the resident set after each (one `/proc/self/status` read and one short line per page; no product file edited).
   PostgreSQL/MinIO: `docker stats --no-stream`; the store: the available blobs by media type (database) and `du -sb` of the
   S3 volume.
4. **The sampler was proved first** (`sampler.py control --mib 300`, in a capped scope, clean tree `ae85ab20`): a child that
   touches 300 MiB was seen as +300.0 MiB sampled, +300.0 MiB by `VmHWM`, the scope's `memory.peak` 294.5 MiB over the
   baseline resident set (cgroup accounting), and 0.0 MiB after the free. All three readings agree to within 2 %.
5. **Generators** (`build_bundles.py`): deterministic given a seed, built only from `tools/fixtures` (the AR corpus PDF writer
   and its embedded Cyrillic font subset, the portal-bundle builders, the reference validator, which must accept the archive)
   and then read by the product's own `extract_bundle` + `admit_bundle`, whose counts are recorded with the input budget
   `analysis.public.input_budget_characters` gives (`claude-opus-5`, $1.00: **152 361**). Checked: `build_bundles.py check`
   (each variant at a few pages built twice: same SHA-256; another seed: other bytes; exit 0), and every measured 500-page
   archive rebuilt by the committed generator on a clean tree to the same SHA-256 (text-rich seeds 55 and 56, low-text seed 55).
6. **Every figure carries its context**: the worktree `HEAD` and whether the tree was clean, `/proc/loadavg`, `MemAvailable`
   (at the start of uploads and runs from `ae85ab20` on; at the end otherwise). Before each heavy step the tools waited for
   `MemAvailable >= 3 GiB`, `/` free `>= 5 GiB` and no `make gate` (`common.capacity_gate`). The host was shared and loaded:
   1-minute load 1.0 to 18.4, `MemAvailable` 2.1 to 6.8 GiB over the session.

The commands (with `.local/rehearsal-w55b/secrets.env` sourced for the three secrets; every heavy one inside
`stack.py capped` or a capped scope started by `stack.py`):

```text
python scripts/rehearsal/w55b/sampler.py control --mib 300
python scripts/rehearsal/w55b/stack.py capped --unit build-... --ceiling-gib 2|3 -- python scripts/rehearsal/w55b/build_bundles.py text-rich|low-text|vector [--seed S] [--segments 7500]
python scripts/rehearsal/w55b/stack.py api-start | api-stop | web-start | web-stop
python scripts/rehearsal/w55b/drive.py upload --bundle B --phase P [--project-uid U] [--via-bff] [--redact]
python scripts/rehearsal/w55b/drive.py start-refused --phase P --version-uid V
python scripts/rehearsal/w55b/drive.py run --phase P --version-uid V [--redact]
python scripts/rehearsal/w55b/drive.py blocks --phase P --version-uid V [--redact]
python scripts/rehearsal/w55b/drive.py recovery --phase P --run-id R --restarts 2 --window 600
python scripts/rehearsal/w55b/stack.py capped --unit browser-... --ceiling-gib 2 -- node scripts/rehearsal/w55b/browser_blocks.mjs --project-name N --version-uid V --phase P --crops sample:40|all [--counts-only]
python scripts/rehearsal/w55b/drive.py fetch --version-uid V --into .local/rehearsal-w55b/<dir>
python scripts/rehearsal/w55b/stack.py capped --unit fidelity-c --ceiling-gib 3 -- python scripts/rehearsal/w55b/crop_fidelity.py .local/rehearsal-w55b/<dir> --sheets
python scripts/rehearsal/w55b/figures.py
```

### 2.1 Part (a): the 500-page text-rich bundle

**The bundle** (`build_bundles.py text-rich`, seed 55; seed 56 for the second upload): 500 A4 pages of dense Cyrillic text
(46 lines a page, about 3 570 characters a page, the AR corpus font), one TEXT block per page whose recognised text is the
page's layer as the independent extractor reads it. Archive 11 877 599 B (11.33 MiB), PDF member 8 178 124 B, `_results.md`
3 410 276 B, `_blocks.json` 288 467 B. The product's envelope: accepted, 500 pages, `text_character_count` **1 786 430**
(seed 56: 1 787 740), 0 text-less pages, 500 blocks; **11.7 times the budget of 152 361**.

| Phase (tree, load, `MemAvailable`) | Answer | Wall | API `VmHWM` growth | API sampled peak RSS | API scope `memory.peak` |
| --- | --- | ---: | ---: | ---: | ---: |
| upload 1, a fresh API process (`acadd039`, 2.2, 6.0 GiB) | `201`, 500 pages | 1.05 s | +28.8 MiB | 150.8 MiB | 151.7 MiB |
| upload 2, other bytes (seed 56) | `201` | 0.84 s | +6.0 MiB | 155.6 MiB | 157.3 MiB |
| upload 3, the bytes of upload 1 again | `201` | 0.82 s | +3.2 MiB | 156.0 MiB | 157.3 MiB |
| `startRun` on version 1 (`acadd039`, 1.7, 6.0 GiB) | **`422` `analysis_input_budget_exceeded`**, `retryable: false`, `details` `{character_count: 1786430, budget_characters: 152361}` | 0.008 s | | | |
| `startRun` on version 2 | `422`, the same code, `{character_count: 1787740, budget_characters: 152361}` | 0.009 s | | | |

**Nothing created by either refusal**: the rows of `audit_run`, `job`, `attempt`, `command_record`, `stage_result`,
`model_call`, `provider_call_effect` and `lease` were counted before and after each call and did not change; `listRuns` of the
version answered 0 runs before and after. The first upload's +28.8 MiB is a fresh process's first upload and includes its
first use of the reader and PDFium; the next two are the steady figure. All three were loopback API calls with no BFF and no nginx.

### 2.2 Part (b): the 500-page low-text bundle

**The bundle** (`build_bundles.py low-text`, seed 55, SHA-256 `4489809e...`): 500 pages, each one 300 dpi grayscale JPEG
(quality 60; A4, every fifth page landscape) of scan-like content — paper grain from a seeded generator, a framed plan with
axes and bubbles, walls, door swings, hatching, dimension lines, word-like marks in a notes area and a title block, a blur
for the optics and dust; 334 pages carry a thin text layer (a sheet label of 6 to 8 characters), 166 none. Every page has an
IMAGE block over the drawing (the drawing's size varies, every tenth block a polygon), a TEXT block over the notes with
recognised text, and a STAMP block over the title block. JPEG per page min/median/max 366 064 / 436 028 / 509 867 B. Archive
**220 269 888 B (210.07 MiB)**, PDF member 218 170 583 B (208.06 MiB, stored), `_blocks.json` 743 666 B, `_results.md`
1 355 032 B: under the 250 MiB member and 300 MiB total limits; nothing compressed, so the ratio is 1. The product's
envelope: accepted, `text_character_count` 2 600 (under the budget), 500 text-less pages (all under 50 characters, each
admitted for its portal blocks), `recognised_character_count` 422 170, 1 500 blocks (500 IMAGE, 500 TEXT, 500 STAMP).

**Upload** (`4d6187ec`, load 1.5, 5.4 GiB available): `201` in **1.79 s**; API `VmHWM` 125.1 → 467.2 MiB, **+342.1 MiB**;
the resident set stayed at 427.5 MiB after the answer (anon 400.6 MiB: about 300 MiB kept by the process); the scope's
`memory.peak` 885.9 MiB includes about 208 MiB of page cache of the temporary members (file pages are charged to the scope).

**The run, twice** (a fresh API scope each; `startRun`, `getRunStatus` every 2 s). Both deterministic stages succeeded; the
run then ended `failed` at `text_analysis` with `analysis_input_invalid`, `terminal_detail.reason: recording_missing` — the
recorded provider has no recording for a synthetic document, which is expected (`R-29`, no live call) and is not a defect.

| Run (tree, load, `MemAvailable` at start) | Stage | `duration_ms` | RSS at start → peak | Growth |
| --- | --- | ---: | --- | ---: |
| 1 (`4d6187ec`, 1.4, 5.6 GiB) | `source_preparation` | **1 357** | 124.9 → 370.1 MiB | +245.2 MiB |
| | `page_geometry_extraction` | **111 200** | 370.1 → 585.9 MiB | +215.8 MiB |
| | `document_context_build`, `text_analysis` | 54, — | 586.0 MiB | 0 |
| 2 (`4d4d37d1`, 6.1, 5.2 GiB) | `source_preparation` | **1 450** | 125.1 → 366.8 MiB | +241.7 MiB |
| | `page_geometry_extraction` | **107 564** | 366.6 → 586.2 MiB | +219.6 MiB |

Whole run: 114.8 s and 110.9 s from `startRun` to the terminal state (queued 2.1 s, then running); API `VmHWM` +461.5 and
+461.8 MiB; the scope's `memory.peak` **806 133 760 and 813 748 224 B (0.75 and 0.76 GiB) of the 3 GiB cap**; no OOM event.
Metrics (both runs): `crop_count` **500**, `crop_blob_count` **500**, `geometry_mismatch_page_count` **0**,
`crop_skipped_for_mismatch_count` 0, `portal_block_count` 1 500, `portal_image_block_count` 500. Crops: **415 881 211 B of
PNG (396.6 MiB)** in the store, 500 blobs; pixels per crop min / median / max 831 303 / 2 161 168 / 3 996 666, **23 at the
4 000 000-pixel cap**. During run 1 PostgreSQL held 65 MiB and MinIO 395 MiB (`docker stats`), 70 and 420 MiB after. The
second run published no new blob (equal crops, content-addressed), yet the S3 volume grew from 901 to 1 320 MB: MinIO's own
`.minio.sys/tmp/.trash` held 645 MB of deleted temporaries at the reading (staged objects copied and deleted), while the
bucket's data was 674 MB (the PDFs, PNGs and JSON).

**Resident set per page** (`instrumented_serve.py`; MiB after page or crop 1 / 10 / 50 / 100 / 250 / 500; run 1, run 2 within
0.5 MiB of it):

| Pass | After 1 | 10 | 50 | 100 | 250 | 500 | Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `source_preparation`, pdfplumber | 150.8 | 154.8 | 172.1 | 193.6 | 257.7 | 366.0 | **+0.43 MiB a page, kept** |
| `page_geometry_extraction`, pdfplumber | 367.9 | 371.8 | 388.5 | 409.3 | 471.6 | 578.0 | **+0.42 MiB a page, kept** |
| `page_geometry_extraction`, PDFium page boxes | 585.1 | 585.1 | 585.1 | 585.1 | 585.1 | 585.1 | flat |
| `page_geometry_extraction`, crop render + publish (500 crops, 109.7 s) | 585.7 | 585.8 | 585.8 | 585.9 | 585.9 | 585.9 | flat |

So on raster pages the crop half is flat (one crop at a time, as GEOMETRY designed) and all the growth is the pdfplumber
passes: the first stage's pages are not given back before the second stage's pass, which adds as much again. 0.43 MiB a page
on these pages; on drawing pages it is 23 to 24 MiB a page (2.3 and 2.4).

**«Блоки» over the API** (`drive.py blocks`, limit 100): 1 500 listed, 1 500 distinct, 0 repeated, 15 pages of 50 to 76 ms
each, every block `geometry: ok`, 500 with a crop.

**«Блоки» in the browser** (`browser_blocks.mjs`, cold Chrome for Testing 154 at 1280 × 900, signed in through the real
screen, the project and version chosen through the screen's own buttons):

| Drive (tree, load, `MemAvailable`) | Blocks | Presses | First page | A press: min / median / max | Last press | All loaded | DOM | JS heap | Crops | Scope peak |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |
| 1 (`84da38a7`, 3.2, 5.3 GiB) | 1 500 / 1 500 | 14 | 322 ms | 155 / 188 / 288 ms | 221 ms | 3.27 s | 15 239 elements | 22.5 MiB | 40 of 40 sampled (first 20, last 20) loaded, slowest 109 ms | 1 385 MiB |
| 2 (`84da38a7`, 3.2, 4.8 GiB) | 1 500 / 1 500 | 14 | 130 ms | 158 / 183 / 241 ms | 241 ms | 3.04 s | 15 239 elements | 21.7 MiB | **500 of 500** scrolled into view and loaded in 19.4 s, slowest 214 ms, every natural size equal to the declared one | 1 722 MiB |

On the screen after the last press: 500 page sections in page order, 3 blocks in each (one per type), 1 500 cards, 500
distinct crop addresses, 500 recognised texts, 500 descriptions, no mismatch sentence, no «Показать ещё» left, no horizontal
overflow: **no block lost or repeated**. Each press costs about 1 000 DOM elements and 0.2 s, flat to the end (no slowdown
at 1 500 blocks). One console error per load, counted and not read (INGEST §2.7 and WEB-BLOCKS record one such line per
route on a lane build, `NEXT_PUBLIC_WEB_BUILD_ID` missing, which this build is too); 0 page errors. The browser's cost: the capped scope's `memory.peak` (Chrome and the Node driver) 1.39 GiB
with 40 crops and 1.72 GiB with all 500 crops decoded once; the summed RSS of Chrome's processes, which double-counts shared
pages, was 1.9 to 2.0 GB.

**How long a user waits for «Блоки»** on this bundle: the portal tab has blocks once `page_geometry_extraction` succeeds,
about **115 s** after «Запустить прогон» (2 s queued, 1.4 s preparation, 108 to 111 s geometry); then 0.1 to 0.3 s for the
first 100 blocks and about 0.2 s per further 100.

**Through the BFF** (an extra, for INGEST's owed "memory figures on the stand", which this lane cannot reach: the same
210 MiB bundle posted to Next's `/bff/v1/projects/{p}/documents` with a session from its own sign-in form, `drive.py upload
--via-bff`, Next restarted before each): `201` in 3.03 s and 1.44 s; **Next's `VmHWM` +241.9 and +231.1 MiB** (Next scope
`memory.peak` 376 and 346 MiB); for the 11.33 MiB text-rich bundle +33.3 MiB. The Next process grows by about the body's
size; see 4.2.

### 2.3 Part (b′): a 500-page vector drawing set, under the cap (the integrator's addendum)

The low-text raster pages never came near the cap, but the owner's export (2.4) costs about 24 MiB a page in the pdfplumber
pass, and drawing sets are the real case. So a third bundle was measured: `build_bundles.py vector --segments 7500` — 500 A3
landscape vector sheets, each 7 500 path objects (CAD's unit) over the drawing area, a sheet label as the thin text layer on
two pages of three, an IMAGE and a STAMP block per page. Archive 46 424 181 B (44.27 MiB), 1 000 blocks, 2 600 characters.
**Calibration**: a 10-page pilot at 10 000 segments cost 31 MiB a page; 7 500 was chosen to come near the export's measured
mean of 24.0 MiB a page (2.4), and the 500-page run then measured 23.0 MiB a page.

| Step (tree `98ac7be0`, load 2.6 to 2.7, `MemAvailable` 6.6 to 6.8 GiB) | Result |
| --- | --- |
| upload | `201` in 2.55 s, API `VmHWM` +110.5 MiB |
| run, API scope `MemoryMax` 3 221 225 472 B (derived from 6 916 MiB available) | **killed by the cap after 58.4 s**, inside `source_preparation`'s pdfplumber pass **after page 126 of 500**; RSS after page 1 / 10 / 50 / 100 / 126: 213.8 / 421.2 / 1 342.9 / 2 495.0 / 3 094.2 MiB; the kernel log: `oom-kill:constraint=CONSTRAINT_MEMCG`, `oom_memcg` this lane's scope, the killed task the lane's API, nothing else on the host touched |
| the run as left | `audit_run` `running`, `job` `running`, one `attempt` `running`, no `stage_result` row |
| the product's own recovery (`drive.py recovery`: restart the API after each kill, reconcile nothing) | each start reclaimed the expired lease (60 s) and, the run having no provider effect, **resumed it**: attempt 2 killed at page 126 again, attempt 3 killed at page 126 again; at the third reclaim (`count >= 3`) the job went to `dead_letter` and the run to `failed` |
| what a user sees | `getRunStatus`: `state: failed`, **`terminal_reason: analysis_failed`, `terminal_detail` absent, no stage listed** |

Three OOM kills of the serving process, about 3 × 58 s of a pinned process at 3 GiB plus the lease waits, before a terminal
state that says nothing about memory. On the stand the worker would be killed the same way; without a container limit
(`infra/deploy/compose.server.yml` sets none) the host's OOM killer, not a cgroup's, would choose the victim.

### 2.4 Part (c): the owner's real export (counts only, F-7)

**Read only.** The file was never copied, extracted into the repository or committed; the upload streamed it from its place.
Its SHA-256 prefix `a56f08684d055795`, size 9 035 796 B and modification time `2026-10-13 12:25:48.959992192 +0500` were
recorded before the first read and found identical after the last (and again at teardown, section 6). Every derived byte (the
version's PDF read back from the API, the 47 crops, the contact sheets, the descriptions) lived under
`.local/rehearsal-w55b/real/` and was deleted as soon as the fidelity work was done, before teardown.

| Step (tree, load, `MemAvailable` at start) | Result |
| --- | --- |
| upload (`a81ff836`, 8.9, 5.0 GiB) | `201` in **0.76 s**, 30 pages, API `VmHWM` +32.9 MiB |
| run (`a81ff836`, 10.8, 4.5 GiB) | 39.5 s to the terminal state; both deterministic stages succeeded; `failed` at `text_analysis` with `recording_missing` (expected, as in (b)) |
| `source_preparation` | **15 301 ms**; RSS 124.8 → 843.5 MiB, **+718.6 MiB for 30 pages (24.0 MiB a page)**; per page: 147.6 MiB after page 1, 234.7 after page 10, 842.1 after page 30 (single pages up to +124 MiB) |
| `page_geometry_extraction` | **23 590 ms** (its pdfplumber pass 15.1 s, the 47 crops 8.0 s); RSS 843.5 → 1 003.3 MiB peak (the second pass reuses the first pass's freed heap, then +160 MiB); `crop_count` **47**, `crop_blob_count` **47**, `geometry_mismatch_page_count` **0**, `portal_block_count` 129, `portal_image_block_count` 47; 25 004 608 B of PNG (GEOMETRY's figure, to the byte); 23 crops at the pixel cap |
| the whole run | API `VmHWM` +881.5 MiB; scope `memory.peak` 1 045 655 552 B (0.97 GiB) of 3 GiB |
| «Блоки» over the API | 129 listed, 129 distinct, 2 pages, by type 56 TEXT / 26 STAMP / 47 IMAGE, 47 with a crop, all `geometry: ok` |
| «Блоки» in the browser (`--counts-only`, `a81ff836`, 5.8, 4.0 GiB) | **129 / 129 blocks** after 1 press (first page 129 ms, the press 123 ms, all 273 ms); 30 page sections; 56 recognised texts; 47 descriptions; **47 of 47 crops loaded** (scrolled into view, slowest 72 ms, 1.45 s for all, natural size = declared size for all 47); DOM 1 655 elements; JS heap 6.2 MiB; 0 page errors; scope peak 1 072 MiB |

**Do the crops depict what their blocks mark? Numerically** (`crop_fidelity.py`): for each crop the WHOLE page was rendered
with pypdfium2 at the crop's scale — estimated from the crop's size and the block's box (three estimates, best kept), never
read from the product — and the block's region compared with the crop at the best alignment within ±2 px; the control is the
same comparison against a region displaced by half the crop.

| Measure (47 crops) | Value |
| --- | --- |
| mean absolute difference per channel, crop vs its region (0..255): min / p10 / p50 / p90 / max | 0.0 / 0.72 / **2.18** / 5.80 / 8.08 |
| the same, crop vs the displaced control region | 7.35 / 10.22 / **19.31** / 38.78 / 41.51 |
| crops whose own region beats the control | **47 of 47** (per crop the control is at least 4.3 times larger) |
| best alignment at 0 or 1 px; crop size equal to the region's within 2 px | 46 of 47; 46 of 47 (the one other: a 3 855 px-wide crop, 2 px, the scale estimate's rounding) |
| estimated scale, px per point (min / p50 / max); x/y agreement | 2.2156 / 4.1670 / 4.1701; within 0.17 % |
| share of non-white pixels (< 250) in the crop, min / p50 / max; of dark ones (< 128) | 3.8 % / 8.7 % / 18.5 %; 1.5 % / 4.4 % / 10.1 % — the crop's share equals its page region's to within about 1 point |
| blank crops (under 0.1 % non-white) | **0** |

The tool was proved first on the synthetic pilot's ten crops (`pilot-crop-fidelity`): own region 2.2 to 3.5, control 20.5
to 34.2 (every control above, the smallest control 5.8 times the largest own figure); the residual on both sets is
resampling at an estimated scale and, on the scans, the grain. **By eye**: twelve contact sheets, each row the page scaled
down with the block's box drawn on it beside the crop, labelled by a running number only; all 47 viewed, and each portal
description's summary read beside its crop.

| Verdict (counts only) | Count |
| --- | --- |
| crop shows the region its block marks | **47 of 47** |
| blank crop | 0 |
| crop of a wrong region | 0 |
| the portal's own box takes in part of a neighbouring drawing or table at its edge (the crop reproduces the box faithfully) | 3 |
| the portal's IMAGE description fits its crop | 44 |
| fits in subject, with a wrong drawing-type label | 2 |
| fits in subject, naming elements the crop does not show | 1 |
| describes another drawing | 0 |

### 2.5 The checks of this lane's own tools

| Check | Result |
| --- | --- |
| `sampler.py control --mib 300` (clean tree) | exit 0; 300.0 / 300.0 / 294.5 MiB seen; 0.0 after free |
| `build_bundles.py check` | exit 0, `check: OK` (same seed same bytes; another seed other bytes; over/under budget as built) |
| rebuild of every measured 500-page bundle on a clean tree | the same SHA-256 (`d4d64b34...`, `d694a0de...`, `4489809e...`) |
| `crop_fidelity.py` on the synthetic pilot | 10 of 10 own regions beat their control by at least 5.8 times |
| the browser drive's bookkeeping | the counter, the card count, the page sections and the crop addresses all equal to `block_count` in every drive |
| `python -m compileall -q scripts/rehearsal/w55b`; `node --check` of the drive | exit 0; exit 0 |
| `git diff --check e1233e7a..HEAD` | exit 0 |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py`, clean committed tree `ac485de0` (the scripts are tracked, so the surface-count guard read them) | exit 0, **752 passed, 18 927 subtests** in 49 s |

Two defects of the tools themselves were found while running and are fixed in their commits: the first recovery watch took
a killed child (a zombie) for a live API and waited out its window (`ffa3e75e`); the first `start-refused` read `code`
where the envelope says `error_code` (`acadd039`; the refusal was re-measured on the clean tree). Figures taken on a tree
whose uncommitted diff touched only these tools are marked dirty in the figures and were re-measured clean where they are
quoted (the bundles by rebuild, the refusals and uploads by repetition).

## 3. Contracts

**None changed.** No file under `contracts/**`, no migration, no lock file, no composition root, no web file. The sealed
surface is as `W55B-SEAL-01` left it: **47 paths / 54 operations / 123 schemas**; the error catalog is 24 entries; the
migration head is `0021_portal_bundles`. The error codes this lane met were all registered ones
(`analysis_input_budget_exceeded`, `analysis_input_invalid` with `recording_missing`, `analysis_failed`).

## 4. Risks, limitations, what is owed, and what the figures say about the bounds

### 4.1 Limits of the figures

1. **A loaded, shared host.** Load 1.0 to 18.4 and 2.1 to 6.8 GiB available over the session; other projects' and this
   wave's other sessions' containers ran throughout. Timings are therefore noisy upwards: the two 500-page runs agree to
   4 % (111.2 and 107.6 s), the three text-rich uploads within 0.2 s, the two BFF uploads differ by 2 times (3.03 and
   1.44 s). Memory figures are not load-sensitive and agree to within 1 % across repeats.
2. **The API ran the stages in-process** (`EXECUTION_ROLE=all`); on the stand the worker does, with no API traffic beside it,
   so the stand's worker would show these stage figures minus the serving process's own 125 MiB. Loopback API, a local
   MinIO, no nginx; the BFF figure has no nginx either.
3. **The API ran through `instrumented_serve.py`** (per-page records; no product file changed). Its cost is one
   `/proc/self/status` read and one line per page or crop; not measured separately.
4. **Synthetic raster content** is grain, lines and word-like marks: realistic for JPEG and PNG sizes and for render time,
   not for OCR, real scans' skew, colour scans or larger sheets (A1/A0 at 300 dpi are 8 to 16 times an A4's pixels). The
   **vector set** reproduces the export's mean per-page memory cost, not its layout or text.
5. **The fidelity metric's own residual** (0.7 to 8.1 on line drawings) is resampling at an estimated scale; it separates
   the right region from a displaced one per crop, it does not certify a pixel-exact clip (GEOMETRY's tests do that on
   synthetic pages).
6. **The per-phase scope `memory.peak`** counts file pages (the temporary members) as well as the process; it is the right
   figure for a container limit, not for the process's heap.

### 4.2 Findings — the bounds measured against the figures

1. **The pdfplumber pass does not fit a 500-page drawing set (confirms JUDGE-X X-2 at real scale).** Measured: 24.0 MiB a
   page on the owner's export (+718.6 MiB for 30 pages in `source_preparation` alone); 23.0 MiB a page on the vector set,
   killed by the 3 GiB cap at page 126 of 500; 0.43 MiB a page on raster pages. Both stages make the pass; the memory of
   the first is kept by the process. **A 500-page set of the export's density needs about 11.7 GiB in one pass**
   (extrapolated from the measured rate, not measured); the largest that fits a 3 GiB worker is about 120 pages, a 2 GiB
   one about 80. The low-text 500-page run fits easily
   (0.59 GiB). The "before" figures for `W55B-FIX` are the per-page tables in 2.2 to 2.4.
2. **A run killed for memory is retried twice, then fails mute.** The lease recovery resumes a run with no provider effect,
   so the same pages kill the process three times before `attempt_budget_exhausted` dead-letters the job; the run then
   shows `analysis_failed` with no detail and no stage. On the stand that is three worker deaths per such upload, and
   whatever else the worker held dies with it.
3. **The stand's worker has no memory limit** (`compose.server.yml` sets none), so the host's OOM killer, not the
   container's, chooses the victim when 4.2.1 happens there.
4. **The BFF holds about the whole upload** (+231 to +242 MiB of Next resident set for a 210 MiB body, +33 MiB for
   11.3 MiB), although `credentialed-forward.ts` hands the request's own stream to `fetch` with `duplex: 'half'` and STREAM's
   test asserts that call shape. Where the bytes are held (Next's request handling, undici's buffering) was not decomposed.
   At 250 MiB it is about 290 MiB per concurrent upload in the web process.
5. **The API keeps about 300 MiB after a 210 MiB, 500-page upload** (`VmHWM` +342 MiB, 427.5 MiB resident afterwards),
   more than INGEST's one-page 244 MiB figure (+147 MiB), so the per-page envelope pass adds memory (the X-1 area); not
   decomposed per page (the envelope's page loop was not instrumented).
6. **Time is within its bounds.** The 210 MiB upload answers in 1.8 to 3.0 s (the plan's bound is about 240 s); the
   500-crop geometry stage takes 108 to 111 s, about 0.22 s a crop, linear; a user waits about two minutes after starting a
   run for «Блоки» on a 500-page scanned set, and about 40 s for the 30-page export.
7. **The browser side holds.** 1 500 blocks in 14 presses at about 0.2 s each, flat; 15 239 DOM elements; 22 MiB of JS heap;
   1.7 GiB for Chrome with all 500 crops decoded once. No paging defect (no loss, no repetition). A 2 000-block version would
   be 20 presses and about 20 000 elements: usable, not virtualised.
8. **The store.** 500 crops of 2.2 Mpx median are 396.6 MiB of PNG beside a 208 MiB PDF: a scanned 500-page version costs
   about 0.6 GB per version, content-addressed across reruns; MinIO's trash briefly holds deleted temporaries as large again.
9. **A killed stage leaves its temporary PDF behind.** Each of the three cap kills in 2.3 left one `am-source-*.pdf` of
   45 448 500 B in `/tmp` (found at teardown and deleted by name): the stage's temporary file is removed by its context
   manager, which a SIGKILL never reaches. On the stand that is up to 250 MiB of the worker's `/tmp` per kill, never reclaimed.
10. **The crops are right on the real export** (47/47 both ways) and the portal's descriptions mostly fit (44 fully, 3 with an
   inaccuracy, none of another drawing) — they are shown "not used by analysis", which this supports.

### 4.3 Owed

- **The real set's live input-token count** (`W55B-BUDGET-01` §6 item 4): no live model call was made (no proxy key,
  `R-29`); it stays owed to a run with the live model.
- **The stand's own figures** (nginx in front, the worker process, the stand's host): this lane had a disposable stack only
  (`R-122`).
- **The envelope's per-page cost at upload** (4.2.5) and **where the BFF holds the body** (4.2.4): measured as totals, not
  decomposed.

## 5. Integrator instructions

1. Merge `agent/w55b` through this report's commit: ten new paths, all in the grant; no contract, migration, lock or product
   file.
2. **Heavy steps owed: none of this lane's.** A full gate runs once at the end, on the final W55b candidate. This lane's
   stack is down and its volumes removed (section 6); the `RELNOTES` lane may start.
3. **Recommended `W55B-FIX` candidates** (recommendations only; nothing was changed here):
   - **X-2 (memory per page in `extract_document`)** — evidence 4.2.1: 24.0 MiB a page on the real export, a 500-page
     drawing set killed at page 126 under 3 GiB. After the fix, rerun `drive.py run` on `build_bundles.py vector
     --segments 7500` (seed 55, SHA-256 `2d339455...`) and compare the per-page table of 2.3; the raster table of 2.2 is the
     second reference.
   - **A memory kill should end the run with a reason and should not be resumed twice** — evidence 4.2.2: three kills,
     then `analysis_failed` with no detail.
   - **A memory limit on the stand's worker container** — evidence 4.2.3; with the fix in place the figures above say how
     much (0.6 GiB for the 500-page raster set; the drawing case depends on the fix).
   - **The BFF upload's memory** — evidence 4.2.4; measure Next's resident set with a 250 MiB body after any change.
   - **Temporary PDFs left by a killed stage** — evidence 4.2.9; a sweep of stale `am-source-*`/`am-geometry-*` files at
     worker start would bound it.
4. Questions for the owner: none. The figures are on a loaded host and on the tree before `W55B-FIX`, as `R-122` accepts.

## 6. Containment and teardown

`git diff --name-only e1233e7a..HEAD` is the ten paths of section 1, all inside the grant (`scripts/rehearsal/w55b/**` and
this file). Forbidden hotspots untouched: `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `web/**` (including
`package.json`, the lock and `FRONTEND_LOCK.json`), the composition root, `tests/**`, `fixtures/**`, `tools/**`, `infra/**`,
`VERSION`, the release notes. No other worktree, branch, ref or port was touched; nothing was pushed, merged or tagged.

### 6.1 Teardown (2026-10-14, after the last measurement)

| Step | Evidence |
| --- | --- |
| Next and the API stopped by their own PID (`stack.py web-stop`, `api-stop`: the PID file's process group, after its cwd and the port's holder were checked) | `web: process group 721576 stopped; port 31680 free: True`; `api: process group 789186 stopped; port 57580 free: True` |
| the four failed transient scopes (three API scopes the cap killed, the 64 MiB probe) | `systemctl reset-failed` on each by name; `systemctl list-units --all 'w55b-rehearsal*'`: 0 |
| `make down` | exit 0; containers and the network `auditmanager-w55b-rehearsal-net` removed |
| `docker volume rm auditmanager-w55b-rehearsal-postgres-data auditmanager-w55b-rehearsal-s3-data` | exit 0 (the owner's export's copy in the object store went with the S3 volume) |
| `rm -f .env`; `rm -rf .local/rehearsal-w55b web/.next` (`web/.next` did not exist before this lane built it) | both gone; `.local/rehearsal-w55b/real/` (every byte derived from the export) had already been deleted after the fidelity work |
| temporary files | three `/tmp/am-source-*.pdf` left by the killed stages (4.2.9) deleted by name; the browser profiles were removed by `cdp.mjs` itself; the session scratchpad emptied |
| readback | `docker ps -a`, `docker volume ls`, `docker network ls` with `w55b-rehearsal`: 0, 0, 0; `ss -ltn` on 57480, 61080, 61081, 57580, 57581, 31680: 0 listening; the QA stack and the other projects' containers still up, untouched |
| the owner's export | SHA-256 prefix `a56f08684d055795`, 9 035 796 B, modified `2026-10-13 12:25:48.959992192 +0500`: identical to the reading before the first use |
