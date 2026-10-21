# RUN-ROBUSTNESS-01 — what a run reads is checked at the upload, a killed run says where, a killed stage's files are reclaimed

**Status:** code, tests and quoted mutations done on a lane stack; nothing pushed, no ref moved.
**Base:** `origin/dev` `3a90f5b9` (migration head `0028_classification_corrections`, surface 73 / 83 / 242).
**Debts:** `D-159`, `D-160`, `D-169`, `D-170`, `D-177` (`DEBT_REGISTER.md`). **No new error code, constraint, contract, OpenAPI
operation, migration, dependency or web file.**

## 1. Decisions

| Debt | Chosen route | Why not the other |
|---|---|---|
| `D-159` an IMAGE block too small to crop fails the whole run | **Refuse at the upload** (`blocks_json_invalid`, the debt's own remedy: "move the refusal to the upload"). | A recorded per-block skip is a crop-less IMAGE block: `R-121` ruled "no crop-less block in W55b", and a skip needs a field in `geometry.page_crops` / `geometry.portal_blocks`, which is a contract change another lane owns. |
| `D-160` ingest reads with pypdfium2, the run with pypdf and pdfplumber | **Ingest asks the run's readers** in a child process under the envelope's own ceilings, for every document PDFium accepted. | "One reader" would replace pdfplumber in the stage (analysis) or PDFium in ingest, each a behavioural change to text offsets or to the 0.5 s/30-page budget (`W55B-INGEST-01`). |
| `D-169` a killed worker is resumed twice, then the run fails mute | Lease recovery **names the stage** when the last two lost Attempts died in the same one; the budget (3) is unchanged. | Failing at the second loss would turn two deploy restarts in one long stage into a failed run. |
| `D-170` a killed stage leaves its temporary PDF | **Sweep at process start** of the three exact names, older than the attempt watchdog + 60 s. | — |
| `D-177` ~11 GiB of crops per version; U+2028/2029 and Hangul fillers in a name | A **2 GiB crop byte budget** around the stage's store; the scrub widened. | An ingest-time byte bound cannot know a PNG's size (it varies ×10 with the picture); a stage change was outside the grant. |

## 2. What changed

| File | Change |
|---|---|
| `ingest/stage_reader.py` (new) | A second program, started like `pdf_reader.py` (same ceilings, wall clock, bare environment, inherited descriptor): `pypdf` opens the document and counts pages; `pdfplumber` opens it as `extract_document` does, builds the pages and **decodes every content stream** (no interpretation); the three counts (`pypdf`, `pdfplumber`, PDFium) agree. Answers `readable` or a rule. |
| `ingest/envelope.py` | Runs it after the PDFium reader accepts (rule 9); `_run_reader` is the one process runner of both; `PdfFacts.page_geometry`. A failure is `parseable_pdf` with the two sentences the previous (pypdf / pdfplumber) implementation used: pypdf or a count disagreement with PDFium → "could not be parsed"; pdfplumber or a pypdf/pdfplumber disagreement → "could not be read for its text layer". |
| `ingest/pdf_reader.py` | Each page also reports its displayed width, height (CropBox clipped to MediaBox, exchanged for a quarter-turn `/Rotate`) and rotation: what `PdfiumDocument.page_geometry` reads for the run. |
| `ingest/crop_geometry.py` (new) | `page_agrees` (= `maths.check_page`) and `cannot_cut` (= `maths.plan_crop` raising `DegenerateCrop` or failing arithmetically), restated because ingest may not import `analysis` (`tests/contract/architecture`). `uncuttable_image_block` evaluates every page's check (an overflowing raster fails the run on a page with no block at all) and then every IMAGE block of a page that agrees. |
| `ingest/bundle_envelope.py` | Rule 5: `blocks_json_invalid` (existing constraint, a sentence of its own) when `uncuttable_image_block`. |
| `ingest/bundle_members.py` | The display-name scrub also replaces `Zl`, `Zp` (U+2028/2029) and U+115F, U+1160, U+3164, U+FFA0. |
| `runs/crop_budget.py` (new), `runs/executor.py` | `CropByteBudget` decorates each deterministic stage's publication store: a `put_blob` of a crop image that would take the stage past `MAX_CROP_BYTES` (2 GiB) raises `analysis_input_invalid` with `reason: portal_crops_over_budget` **before** the inner store journals, stages or uploads it. |
| `jobs/temporaries.py` (new), `jobs/public.py` | `sweep_stale_temporaries`. |
| `runs/public.py`, `workers/__main__.py` | The sweep runs when a serving carrier starts (API, all-in-one) and when `workers serve` has accepted its configuration; `fail_reclaimed_run` takes an optional `terminal_detail`. |
| `jobs/repository.py` | `reclaim_expired`: at an exhausted budget, `terminal_detail = {stage_id}` when the last two lost Attempts died in the same stage (the committed `stage.started` journal, per Attempt window). |

## 3. The numbers behind the choices

* **Which PDFs.** Built here from the failure descriptions, each shown by the libraries (not by the envelope) to open in PDFium
  and to fail or disagree in the stage's own `extract_document` (`pypdf` 6.18.0, `pdfplumber` 0.11.10, `pdfminer.six` 20260107,
  `pypdfium2` 5.13.0): a page tree listing itself as a kid (`source_unreadable`), a page listed twice (`page_count_disagreement`),
  a content stream with an unknown filter and an LZW stream that does not decode (`PdfminerException`, which the stage does not
  even type), a `/Count` the tree does not bear out (PDFium 1 page, the extractor 2).
* **Cost.** The second program adds about 0.3 s to an upload (Python start and the libraries' imports; 70 MB of address space
  at import against the 512 MiB ceiling). A 240 MiB document is read in about 0.3 s.
* **Crops.** 0.79 MiB a crop measured on the 500-sheet scanned set (`W55B-REHEARSAL-01` 4.2.8), 0.77 GiB for the 1 000 the
  ceiling allows, 11.4 MiB for a high-entropy crop at the pixel cap (`W55B-JUDGE-X` p7): the budget of 2 GiB is 2.6 × the first
  and 1/5 of the second's 11 GiB.
* **Temporaries.** `STALE_AFTER_SECONDS = ATTEMPT_WATCHDOG_SECONDS + 60 = 960`. A file is written after its Attempt was claimed
  and the watchdog fences that Attempt 900 s after the claim, so an older file belongs to an Attempt that holds no authority.

## 4. What this does **not** do

1. **`D-160` is narrowed, not closed.** The run's readers *interpret* pages (operators, fonts, layout); the second program does
   not (that is the 18 s / 30 pages the envelope left `pdfplumber` for). A document that only the interpreter fails on, and
   Y-1 (d) — PDFium sees text on a page, `pdfplumber` none, and no block covers it, so `validation_failed` at every run — still
   reach a run. Closing them needs either the full `pdfplumber` pass at upload (minutes at 500 pages) or a stage that records the
   page instead of failing; both are the owner's cost/behaviour decision.
2. **Versions already accepted are not touched.** A version accepted before this change that holds a sub-pixel IMAGE block, or a
   document the run cannot read, still fails every run (immutable). The stand's existing versions can be audited with
   `admit_bundle` over their stored members; no such audit was run (no stand access in this lane).
3. **`D-169`: the resume budget is unchanged** (three Attempts). Naming the stage is what makes the failure legible; stopping
   at the second loss is a separate decision (it would fail a run whose worker was merely restarted twice in one stage).
   `interrupted_reason` stays `attempt_budget_exhausted`; the web prints it raw and shows the stage only in the comparison
   widget's "Уточнение причины" count, so showing the stage on the run page is a web change.
4. **`D-170`: the API's multipart spool is not swept.** Starlette names it `tmp` plus random characters, which no exact prefix
   tells from anyone's file. `am-source-*`, `am-geometry-*` and `auditmanager-bundle-*` are. The sweep runs at process start
   only; a file a kill leaves is reclaimed by the next start *after* it is 16 minutes old, not by the restart that follows the
   kill within seconds. A periodic sweep in the worker's reclaim cadence would close that gap; it was left out as a change to
   `workers/service.py`.
5. **`D-177`: the name is scrubbed where ingest derives it** (`source_filename_of`). The document title an uploader types
   (`api/routers/multipart.py`) is outside the grant. The Default_Ignorable marks that are not letters or format characters
   (U+034F, U+17B4/17B5, variation selectors, U+2800) are not scrubbed; some are legitimate in names.
6. **The crop budget lives in `runs`, not in the stage**, so the grant on `analysis/**` (degenerate-block handling only) was
   not exceeded: `analysis/**` is unchanged. A refused stage leaves the crops it had already published (content-addressed
   blobs, as every failed stage does).
