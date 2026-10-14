# W55B-FIX — repairs of the W55b judges' and QA's findings

**Writer:** `W55B-FIX`, 2026-10-14. **Branch:** `agent/w55b-fix`, worktree `.local/worktrees/w55b-fix`.
**Base:** `9bfa1da3` (`integration/w55b`: the W55b wave on dev 0.5.1, the judge and QA records).
**Inputs:** `reviews/W55B-JUDGE-X.md`, `reviews/W55B-JUDGE-Y.md`, `W55B-QA-01.md`, `OWNER_RULINGS_2026-09-17.md`
§3.32–§3.33 (`R-116`…`R-123`), `W55B-FREEZE-01.md`, the five lane reports, and the integrator's two addenda
(`W55B-REHEARSAL-01`'s two findings; the «Блоки» empty-state sentence).

Nothing was pushed, merged, tagged or stashed. No other worktree or branch was written. The owner's export was read only
through `python -I` over the archive in memory (F-7); nothing derived from its bytes is in the tree.

## 0. Findings and commits

| Finding | Status | Commit(s) | The test that fails without the repair |
| --- | --- | --- | --- |
| X-1 (Blocker) PDFium work unbounded, lock held per document | **repaired** | `a069fdf6`, `4395f08b` | `tests/integration/ingest/test_pdf_reader_bounds.py` (11) |
| X-2 (Blocker) `extract_document` keeps every page | **repaired** | `88a62caf`, `d0940f7f` | `tests/integration/analysis/test_extraction_releases_each_page.py` (4) |
| X-3 = QA-1 (Major) upload slot and body taken before authentication | **repaired** | `951a55ad`, `5ea70112` | `tests/integration/qa_w55b/test_p5_upload_gate.py` (3 red probes, unmodified); `test_multipart_rules.py::TestTheUploadRouteHasAFrontDoor`, `::TestTheUploadFormIsParsedUnderSmallBounds` |
| X-4 (Major) no block ceiling; crop not cacheable | **repaired** | `fdc7ca1d` (ceilings), `2318015f` (crop headers), `81b52b3a` (BFF forwards them, comment made true) | `tests/integration/ingest/test_block_ceilings.py`; `tests/integration/api/test_portal_block_routes.py::test_the_crop_carries_its_digest_as_its_tag_and_a_private_hour`; `web/tests/unit/api/credentialed-forward.test.ts` |
| X-5 (Minor) inflate loop checks size and ratio only at the end | **repaired** | `7493c6e9` | `test_bundle_archive.py::test_a_small_archive_that_declares_a_small_pdf_is_refused_before_it_inflates_its_bomb`, `::test_the_ratio_is_judged_while_the_member_is_inflated_not_after`, `::test_a_header_that_says_less_is_refused_at_its_word_before_the_counted_total_is_reached` |
| X-6 (Minor) `_blocks.json` parse cost | **repaired** | `fdc7ca1d` | `test_block_ceilings.py::test_a_block_list_over_its_own_bound_is_a_member_over_its_size` |
| X-7 = Y-1(a) (Minor) integral floats | **repaired** | `ca8c4d50` | `tests/integration/ingest/test_one_integer_rule.py` |
| X-8 (Minor) `plan_crop` arithmetic errors | **repaired** | `231173bc` | `test_geometry_maths.py::test_a_box_ingest_admits_whose_arithmetic_fails_is_degenerate_never_an_untyped_error`; `test_geometry_stage.py::test_a_degenerate_image_block_is_refused_and_leaves_no_file` (3 boxes) |
| X-10 (Minor) bidi and format characters in the title | **repaired** | `b9d19abd` | `tests/integration/ingest/test_display_name_scrub.py` |
| Y-2 (Minor) crop address built outside the seam | **repaired** | `81b52b3a` | `web/tests/guards/crop-address-seam.guard.test.ts` |
| Y-4 (Minor) unregistered PDF-member constraints, bare token on screen | **repaired, one deviation** (§4.3) | `81b52b3a` | `tests/contract/api_v1/test_w55b_fix_constraints.py`; `web/tests/unit/projects/upload-failure.test.ts`, `upload-envelope.test.ts` |
| O-1 (QA) busy refusal shown as a generic dependency failure | **repaired** | `81b52b3a` | `upload-failure.test.ts` (busy), `transport-rules.test.ts` (`Retry-After`) |
| Addendum 1.1: X-2 on the rehearsal's vector drawing set | **repaired, measured** | `d0940f7f` | the drawing-sheet case of the X-2 test; the stage run in §2.3 |
| Addendum 1.2: the BFF holds about the whole upload | **repaired, measured** | `2b75d7d9` | `credentialed-forward.test.ts` (no `tee` through the real `fetch`; call shape) |
| Addendum 2: «Блоки» promised blocks to a version no run can reach | **repaired** | `fb4a2fad` | `web/tests/unit/blocks/portal-states.test.ts` |

## 1. Changed files

`git diff --name-only 9bfa1da3..HEAD` (the deleted `web/src/entities/block/api/crop-url.ts` shows as its rename to
`web/src/shared/api/crop-address.ts`):

```text
contracts/domain/v1/error-codes.json                         catalogue note of validation_failed only
src/auditmanager/analysis/geometry/maths.py                  X-8
src/auditmanager/analysis/stages/extraction.py               X-2
src/auditmanager/api/app.py                                  X-3 (wires the credential pre-check)
src/auditmanager/api/routers/blocks.py                       X-4 (crop ETag, Cache-Control)
src/auditmanager/api/routers/documents.py                    X-3 (upload route declared with UploadRoute)
src/auditmanager/api/routers/multipart.py                    X-3 (front door, bounded form parser)
src/auditmanager/api/security.py                             X-3 (build_credential_precheck only)
src/auditmanager/ingest/bundle_archive.py                    X-5, X-6, blocks_count message
src/auditmanager/ingest/bundle_envelope.py                   X-4 ceilings, X-7
src/auditmanager/ingest/bundle_members.py                    X-10
src/auditmanager/ingest/envelope.py                          X-1 (parent side)
src/auditmanager/ingest/pdf_reader.py                        X-1 (new: the reader process)
tests/contract/api_v1/test_w55b_fix_constraints.py           Y-4 (new)
tests/integration/analysis/geometry/test_geometry_maths.py   X-8
tests/integration/analysis/geometry/test_geometry_stage.py   X-8
tests/integration/analysis/test_extraction_releases_each_page.py  X-2 (new)
tests/integration/api/test_multipart_rules.py                X-3
tests/integration/api/test_portal_block_routes.py            X-4
tests/integration/ingest/test_block_ceilings.py              X-4, X-6 (new)
tests/integration/ingest/test_bundle_archive.py              X-5, X-6
tests/integration/ingest/test_display_name_scrub.py          X-10 (new)
tests/integration/ingest/test_envelope_differential.py       X-1 (the two lock tests rewritten)
tests/integration/ingest/test_one_integer_rule.py            X-7 (new)
tests/integration/ingest/test_pdf_reader_bounds.py           X-1 (new)
tools/fixtures/portal_bundle/archive_negatives.py            X-4 (a blocks_count negative)
tools/fixtures/portal_bundle/portal_format.py                X-4 (the ceilings, restated)
tools/fixtures/portal_bundle/schemacheck.py                  X-7
tools/fixtures/portal_bundle/validate.py                     X-4, X-5
web/src/entities/block/index.ts                              Y-2
web/src/entities/document-version/model/upload-failure.ts    Y-4, O-1
web/src/shared/api/credentialed-forward.ts                   addendum 1.2, X-4, O-1
web/src/shared/api/crop-address.ts                           Y-2, X-4 (moved from entities/block/api/crop-url.ts)
web/src/shared/api/errors.ts                                 O-1
web/src/shared/api/index.ts                                  Y-2
web/src/shared/api/transport.ts                              O-1
web/src/widgets/portal-blocks/ui/portal-block-card.tsx       Y-2
web/src/widgets/portal-blocks/ui/portal-blocks.tsx           Y-2, addendum 2
web/tests/guards/crop-address-seam.guard.test.ts             Y-2 (new)
web/tests/guards/rendered-language.guard.test.ts             Y-2, Y-4, O-1
web/tests/unit/api/credentialed-forward.test.ts              addendum 1.2, X-4, O-1
web/tests/unit/api/transport-rules.test.ts                   O-1
web/tests/unit/blocks/blocks-tabs.test.ts                    addendum 2
web/tests/unit/blocks/portal-blocks.test.ts                  Y-2
web/tests/unit/blocks/portal-paging.test.ts                  Y-2
web/tests/unit/blocks/portal-states.test.ts                  addendum 2
web/tests/unit/projects/upload-envelope.test.ts              Y-4, X-4
web/tests/unit/projects/upload-failure.test.ts               Y-4, O-1
web/tests/unit/styles/screens.ts                             Y-2
docs/program/W55B-FIX.md                                     this report
```

### What each repair does

- **X-1.** `inspect_pdf` keeps its cheap rules in the API (name, non-empty, magic, size) and runs the PDF rules in
  `auditmanager.ingest.pdf_reader`, a program started per document as `python -I -B pdf_reader.py <settings>`, handed
  the file as an inherited descriptor (a bundle member is already a regular file; a byte string is copied to an
  anonymous temporary file with `readinto` in 1 MiB pieces). The reader sets `RLIMIT_AS` 512 MiB, `RLIMIT_CPU` 60 s and
  `RLIMIT_CORE` 0 before it imports `pypdfium2`, gets a bare environment (`PATH` only: none of the API's secrets),
  says `ready`, and answers one JSON line. The API waits with a 60 s wall clock and kills its own child when it runs
  out. Per page, in order: drawing elements (each path counted by its segments, every other object as one, recursing
  into form XObjects) within the page and document ceilings, then characters (`FPDFText_CountChars`, before the text is
  read) within the page ceiling, then the document's characters. Refusals, all `field: content`: `pdf_page_content`,
  `pdf_document_content`, `pdf_reader_limits` (memory, CPU or wall clock). A reader that never says `ready` is a
  `RuntimeError` (a server fault, `500`), never blamed on the document. Every refusal the envelope had keeps its
  field, constraint and message (`test_envelope_differential.py`, 70 passed, rewritten only for the lock).
- **X-2.** `extract_document` opens pdfplumber with pdfminer's document cache off and releases each page after reading
  it: `page.close()`, the page's decoded content list emptied, and one `gc.collect()` (pdfminer's content parser is a
  reference cycle that owns the decoded stream). Both deterministic stages use this function.
- **X-3.** `BodyCapMiddleware` gains a front door on the upload route, after the two header refusals it already made
  (`max_bytes` by `Content-Length`, a multipart body without a boundary) and before the gate and any body read: no
  bearer credential this deployment signed and that has not expired (`security.build_credential_precheck`, the seam's
  `TokenSigner.verify`, no database) is answered `401`; a signed request whose body is not `multipart/form-data` takes
  no slot and is handed to the application with an empty body, so the seam (registers) and the strict pass
  (`media_type`) answer it as before without a byte of the caller's being read; only a signed multipart request takes a
  slot. The upload route is declared with `UploadRoute`, whose request parses its form under 2 files, 4 text parts and
  16 KiB a text part (Starlette's defaults are 1 000, 1 000 and 1 MiB).
- **X-4.** Ingest refuses `blocks_count` over 100 blocks on a page, 3 000 in a bundle or 1 000 IMAGE blocks.
  `streamVersionPortalBlockCrop` answers with `ETag: "<sha256>"` and `Cache-Control: private, max-age=3600`; the BFF
  forwards both; `crop-address.ts`'s caching sentence is now true.
- **X-5.** In the inflate loop, a member that produces more bytes than its header declared is refused at once with its
  role's size constraint (`bundle_member_size`; `stamp_audit_invalid` for the stamp audit), and the ratio is judged
  against the compressed bytes consumed so far plus one 64 KiB piece. The reference validator agrees.
- **X-6.** `_blocks.json` has its own 4 MiB member bound (`BLOCKS_MEMBER_BYTES`); the markdown keeps 16 MiB.
- **X-7.** `_is_integer` is a JSON integer as written (no `3.0`, no booleans), applied to `rotation` and
  `schema_version` too; `schemacheck` reads `integer`, and integer `const`/`enum` options, the same way.
- **X-8.** `plan_crop` turns every `ArithmeticError` into `DegenerateCrop`. No upload-time size check (`R-121`).
- **X-10.** `source_filename_of` replaces every `Cc` and `Cf` code point with `_` (C1 controls, zero-width characters,
  bidi overrides, embeddings and isolates included).
- **Y-2.** `portalBlockCropUrl` lives in `web/src/shared/api/crop-address.ts` (exported from `@/shared/api`).
  `PortalBlockListView` and `PortalBlockCard` take `versionUid`, `CropFigureView` takes `versionUid` and
  `portalBlockId`; none takes an address. A guard holds both rules (the API base read only under `src/shared/`, no
  `*Src`/`*Url` prop in the «Блоки» widget).
- **Y-4.** The catalogue note names `parseable_pdf`, `non_empty`, `plain_base_name` and the four new constraints; the
  upload panel states a Russian sentence for each (`uploadRuleSentence`, §4.3).
- **O-1.** `ApiError.retryAfterSeconds` carries a delta-seconds `Retry-After`; the BFF forwards `retry-after`; a `503`
  with `dependency: upload_capacity` reads «Сервер сейчас принимает другие загрузки.» / «Одновременно принимаются не
  больше двух загрузок, и обе заняты. Повторите загрузку через 5 с. …».
- **Addendum 1.2 (BFF).** Cause found: undici's `fetch` clones a request unless it has no window and refuses
  redirects, and the clone tees the body; the branch kept for a redirect holds every byte. The streamed forward now sets
  `redirect: 'error'` and `window: null`. Not in Next: Next 15.5.25's adapter hands the route
  `new NextRequest(url, { body: <IncomingMessage>, duplex: 'half' })`, which drains with a flat peak (§2.4).
- **Addendum 2.** «Блоки портала появятся после первого запуска анализа этой версии, который дойдёт до разметки
  страниц.» with the detail «… Если запуск отклонён — например, текст версии больше допустимого объёма, — блоков не
  будет. …». No new data or contract.

## 2. Checks

Every check ran on the committed tree it names, one at a time, with `rc` captured as `cmd > log 2>&1; rc=$?`. Before
each heavy step: `free -g` showed 3 to 7 GiB available, `df -h /` 15 to 16 GiB free, and no `make gate` was running.
Stack: compose project `auditmanager-w55b-fix`, PostgreSQL 57400, S3 61000/61001, migrated to `0021_portal_bundles`;
the QA harness's API on 57500/57501. Host load 1 to 4 during the runs.

### 2.1 Light acceptance

| Check | Command | Result | rc |
| --- | --- | --- | --- |
| whitespace | `git diff --check 9bfa1da3..HEAD` | clean | 0 |
| bytecode | `.venv/bin/python -m compileall -q src tests tools` | clean | 0 |
| contract | `.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` | 767 passed, 19 278 subtests (rerun on the final tree, §2.5) | 0 |
| ingest | `set -a; . ./.env; set +a; .venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/ingest` | 635 passed in 144 s | 0 |
| api | same, `tests/integration/api` | 590 passed in 248 s (a first run had 16 red, §4.6; repaired by `5ea70112`) | 0 |
| analysis | same, `tests/integration/analysis` | 588 passed in 197 s | 0 |
| budget calibration (uses `inspect_pdf`) | same, `tests/integration/analysis_text/test_input_budget_calibration.py` | 10 passed | 0 |
| QA, whole directory | `.venv/bin/python -m pytest -p no:cacheprovider -q --tb=short -rf tests/integration/qa_w55b` | **67 passed** in 349 s (log SHA-256 `cd8a349f4ac56819…`) | 0 |
| QA probe 5 alone | same, `tests/integration/qa_w55b/test_p5_upload_gate.py` | 5 passed (the 3 QA-1 probes green, unmodified) | 0 |
| web lint | `npm --prefix web run lint` | clean | 0 |
| web types | `npm --prefix web run typecheck` | clean | 0 |
| Vitest, touched files | `npx vitest run tests/unit/blocks tests/unit/api tests/unit/projects tests/guards/crop-address-seam.guard.test.ts tests/guards/rendered-language.guard.test.ts` | all passed | 0 |
| Vitest, part 1 | `npx vitest run --exclude tests/guards/query-key-shape.guard.test.ts` | 136 files, 2 031 tests passed | 0 |
| Vitest, part 2 | `npx vitest run tests/guards/query-key-shape.guard.test.ts` | 16 passed | 0 |

The contract and ingest runs were on `81b52b3a`; the two later commits (`5ea70112`, `fb4a2fad`) touch
`api/routers/multipart.py`, its test and one web sentence, which the api, analysis, QA and web runs after them cover, and
the contract suite was run again on the final tree (§6).

### 2.2 Mutation table

Each row: the repaired file put back to its `9bfa1da3` content (`git show 9bfa1da3:<path> > <path>`) or the one named
line disabled, the named tests run, the file restored and its SHA-256 compared (byte-identical every time). Script:
`.local/fix/revert_run.sh` (scratch).

| Finding | Mutation | Tests run | Result |
| --- | --- | --- | --- |
| X-1 | `ingest/envelope.py` at base, under `prlimit --as=3 GiB` | `test_pdf_reader_bounds.py`, test by test | text bomb, text bomb in a form, dense text, 500 pages of paths, wall clock, short clock, reader never starts, no secret, recorded figures: each **failed**; the base accepted the text bomb after 23 s and the paths after 9.5 s; the long-strings case **aborted the test process** (`Fatal Python error: Aborted`, PDFium out of memory in-process); the real-page case passed (it is a non-regression check) |
| X-2 | `stages/extraction.py` at base | `test_extraction_releases_each_page.py` | 3 **failed**: +239 MiB (shared paths), +78 MiB (padded streams), +91 MiB (drawing sheets) from one page to five |
| X-2 | each of `page.close()`/emptying `contents`/`gc.collect()`/`caching = False` disabled alone | padded case | each **failed**, +64 MiB |
| X-3 | `_front_door` returns `None` | `TestTheUploadRouteHasAFrontDoor` | 10 failed |
| X-3 | `UploadRoute` passes the plain request | `TestTheUploadFormIsParsedUnderSmallBounds` | 3 failed |
| X-3 | the empty-body branch removed | `…takes_no_slot_and_none_of_its_body_is_read` | 4 failed |
| X-3 | (base) | QA's 3 probes | red at `9bfa1da3` per `W55B-QA-01`; green on this tree |
| X-4 | `ingest/bundle_envelope.py` at base | `test_block_ceilings.py` | 5 failed |
| X-4 | `api/routers/blocks.py` at base | `test_the_crop_carries_its_digest_as_its_tag_and_a_private_hour` | failed |
| X-5 | `ingest/bundle_archive.py` at base | the three X-5 tests | 3 failed |
| X-6 | both `blocks_member_bytes` checks disabled | `…over_its_own_bound…` | the honest-header case failed (a lying header is caught by X-5's rule as well) |
| X-7 | `ingest/bundle_envelope.py` at base; separately `schemacheck.py` at base | `test_one_integer_rule.py` | 8 of 9 failed each time |
| X-8 | `geometry/maths.py` at base | the arithmetic test | 2 of 4 boxes failed (`OverflowError`, `ZeroDivisionError`); the other two were already typed |
| X-10 | `ingest/bundle_members.py` at base | `test_display_name_scrub.py` | 4 of 6 failed |
| Y-2 | `widgets/portal-blocks/ui/portal-block-card.tsx` at base | `crop-address-seam.guard.test.ts` | failed: `url-prop cropSrc` |
| Y-4 | `contracts/domain/v1/error-codes.json` at base | `test_w55b_fix_constraints.py` | 8 of 15 failed |
| Y-4, O-1 | `upload-failure.ts` at base | `upload-failure.test.ts` | 8 failed (2 busy, 6 sentences) |
| O-1 | `shared/api/transport.ts` at base | `transport-rules.test.ts` | the `Retry-After` test failed |
| Addendum 1.2 | `credentialed-forward.ts` at base | `credentialed-forward.test.ts` | 2 failed: no `redirect`; `tee` called once through the real `fetch` |
| Addendum 2 | `portal-blocks.tsx` at base | `portal-states.test.ts` | the sentence test failed |

### 2.3 X-2 on the rehearsal's vector drawing set (addendum 1.1)

Generator: `scripts/rehearsal/w55b/build_bundles.py` and `common.py` of `.local/worktrees/w55b-exec` (commit `98ac7be0`
line), copied to `.local/fix/rehearsal/` with `ROOT` pointed at this worktree. `vector --pages 500 --segments 7500
--seed 55` produced the same bytes the rehearsal measured: 46 424 181 B, SHA-256
`2d339455b2cfb35e3c15581912ce8e018b1e6f02dd615391295cecb672712b1f`; this tree's envelope admits it (6.3 s).

Method: `.local/fix/x2_stages.py` publishes the three members to the lane's S3 and runs `source_preparation` then
`page_geometry_extraction` through `analysis.public.run_stage`, unchanged; `_extract_page`, `page_geometry` and
`CropPublisher.publish` are wrapped in this process only to log `VmRSS` after each page or crop (the rehearsal's
`instrumented_serve.py` method). Run under `systemd-run --user --scope -p MemoryMax=3G -p MemorySwapMax=0`.

| Tree | Result | RSS (MiB) after page 1 / 10 / 50 / 100 / 200 / 300 / 400 / 500 |
| --- | --- | --- |
| before (`extraction.py` at `9bfa1da3`) | **killed by the 3 GiB cap after 58.7 s at page 127** of `source_preparation` | 171.9 / 379.2 / 1 300.9 / 2 452.9 / — (3 075.1 at page 127) |
| after, `source_preparation` | succeeded, 306.9 s, `VmHWM` 174 MiB | 171.6 / 171.6 / 171.9 / 171.9 / 171.9 / 171.9 / 171.9 / 171.7 |
| after, `page_geometry_extraction` pdfplumber pass | succeeded (stage 414.9 s, `VmHWM` 291 MiB) | 216.7 / 217.4 / 217.4 / 217.4 / 217.1 / 217.1 / 217.1 / 199.9 |
| after, page boxes | | 202.5 / 202.6 / 202.6 / 202.6 / 202.6 / 202.9 / 211.4 / 220.0 |
| after, crops (500 crops, 500 blobs, 1 000 portal blocks) | | 237.2 / 261.9 / 261.8 / 277.0 / 292.2 / 261.8 / 292.2 / 292.2 |

The rehearsal's own before figures on `e1233e7a` (213.8 / 421.2 / 1 342.9 / 2 495.0 / 3 094.2 at 1/10/50/100/126) agree.
In isolation (`.local/fix/x2_vector_time.py`, 60 pages, `extract_document` alone): base 0.45 s a page and RSS 208 →
1 568 MiB; after 0.51 s a page and 208 MiB flat. On the owner's export (30 pages, `extract_document` in a process of its
own): peak 794 → 220 MiB, time about 14 → 18 s.

### 2.4 The BFF's memory (addendum 1.2)

Probe (`.local/fix/bff/`): an HTTP front that builds the route's request the way Next's adapter does
(`new Request(url, { body: <IncomingMessage>, duplex: 'half' })`) and calls the product's `forwardWithCredential`
(bundled from the source with the repository's esbuild) with the runtime's real `fetch`; a stand-in API that reads and
counts the body; a client posting one multipart body of N MiB with a `Content-Length`. Each process started and stopped
by its own PID; the front's `VmHWM` read before and after. Under `systemd-run --user --scope -p MemoryMax=1G
-p MemorySwapMax=0`, Node 22.23.1:

| Body | Front's `VmHWM` growth, base forward | after `2b75d7d9` |
| --- | ---: | ---: |
| 16 MiB | +43 MiB | +27 MiB |
| 64 MiB | +96 MiB | +42 MiB |
| 256 MiB | +286 MiB | +45 MiB |

Decomposition (same probe, variants): draining the request's body with `for await` +44 MiB at 256 MiB; piping with
`node:http` +42 MiB; `fetch` with the request's stream +297 MiB; `fetch` with `Readable.toWeb` +290 MiB; either `fetch`
with `redirect: 'error', window: null` +49 to +52 MiB; a forced GC every 250 ms did not lower the base figure
(`arrayBuffers` 184 MiB live). So the bytes were held by `fetch`'s request clone, not by Next or by garbage.

### 2.5 The final tree

On the report's commit: `git diff --check 9bfa1da3..HEAD`, `compileall` and the contract suite (same command as §2.1)
were run again; results in §6.

## 3. Contracts

| Surface | Before (`9bfa1da3`) | After |
| --- | --- | --- |
| `contracts/api/v1/openapi.json` | 47 paths, 54 operations, 123 schemas | **unchanged** (byte-identical; no generated client, pin or lock touched) |
| error codes (`error-codes.json`) | 24 | 24 |
| `validation_failed` portal-bundle registered values (`field: file`) | 18 | 19: **`blocks_count`** added |
| PDF member / upload name constraints named in the note | `pdf_magic_bytes`, `not_encrypted`, the two bounds, `every_page_has_extractable_text`, `max_bytes` | + **`parseable_pdf`**, **`non_empty`**, **`plain_base_name`** (raised before, now registered) and **`pdf_page_content`**, **`pdf_document_content`**, **`pdf_reader_limits`** (new) |
| `bundle_member_size` | "declared or actual" | the same, plus: a member past its own declared size is refused as soon as it is, and `_blocks.json` is bound at 4 MiB |

Only the catalogue note changed in `contracts/`. The crop response's two new headers are not declared in the OpenAPI:
not required (the content operation's `Accept-Ranges` is undeclared the same way) and no conformance test reads them. No
`304` is answered, so no response was added. The block-list schema (`contracts/analysis/v1/portal-blocks.schema.json`)
is unchanged: JSON Schema cannot tell `3` from `3.0`, so the integer rule is the readers' (§4.4).

## 4. Risks, limits and the figures behind every new limit

### 4.1 The new limits

Real maxima measured with the product's own counting on the 674 corpus bundles under `.local/norms/corpus/` (28 251
pages; `MANIFEST.json`) and on the owner's export (30 pages; F-7, in memory). Scripts in `.local/fix/` (scratch).

| Limit | Value | Largest real value measured (where) | Margin |
| --- | ---: | ---: | ---: |
| drawing elements on a page (`PAGE_ELEMENTS_MAX`) | 400 000 | 75 486 (export) | ×5.3 |
| drawing elements in a document (`DOCUMENT_ELEMENTS_MAX`) | 8 000 000 | 1 300 705 (corpus); export at its density over 500 pages ≈ 6.2 M; rehearsal vector set 7.5 M (synthetic, admitted) | ×6.2 over the real maximum |
| characters on a page (`PAGE_CHARACTERS_MAX`) | 200 000 | 19 132 (export) | ×10.5 |
| characters in a document (`DOCUMENT_CHARACTERS_MAX`) | 20 000 000 | 1 892 768 (corpus) | ×10.6; 2³¹ is ×107 above |
| reader address space (`READER_ADDRESS_SPACE`) | 512 MiB | every real PDF reads inside 64 MiB (all 674 and the export; 48 MiB fails) | ×8 |
| reader CPU time and wall clock (`READER_SECONDS`) | 60 s | 2.93 s (corpus, 500 pages, read in-process); 0.05 s slowest page; the export 0.24 s through the reader | ×20 |
| blocks on a page (`MAX_BLOCKS_PER_PAGE`) | 100 | 9 (export) | ×11 |
| blocks in a bundle (`MAX_BLOCKS`) | 3 000 | 500 (corpus, 500 pages); 129 (export); export density over 500 pages ≈ 2 150 | ×6 |
| IMAGE blocks in a bundle (`MAX_IMAGE_BLOCKS`) | 1 000 | 47 (export); ≈ 783 at its density over 500 pages | ×21 |
| `_blocks.json` member (`BLOCKS_MEMBER_BYTES`) | 4 MiB | 283 408 B (corpus); 77 152 B (export); largest real block 869 B | ×14.8 |
| upload form: files / text parts / text part | 2 / 4 / 16 KiB | the operation declares 1 / 2; a 400-character title is ≤ 1 600 B | — |
| crop `Cache-Control` | `private, max-age=3600` | — | the credential's lifetime |

Also measured: the owner's export through every repaired rule in memory — admitted; `text_character_count` 93 690
(unchanged); worst compression ratio of any prefix of any member 6.2 (X-5's bound is 100). `_blocks.json` parse peak for
a pathological list: 404 MiB at 16 MiB, 100 MiB at 4 MiB (25× its size). Corpus and export integer fields: no
integer-valued float anywhere (X-7).

### 4.2 Bounded, but not small

- **Two reader processes at once** can hold up to 2 × 512 MiB on the API's host, whatever the PDFs do; a bomb that
  fills it is refused in about a second (the long-strings probe peaked at 498 MiB and answered in 1.0 s). One Python
  start per PDF costs about 55 ms.
- **A page at the element ceiling** costs pdfplumber about 400 000 × 2 KiB ≈ 800 MiB in the worker, once per page now
  (X-2). The ceiling is five times the export's busiest page.
- **Run time near the watchdog.** The vector set's two deterministic stages took 307 s and 415 s on this loaded host
  (722 s) against `ATTEMPT_WATCHDOG_SECONDS` 900; X-2's release costs about 13 % (0.45 → 0.51 s a page: pdfminer's cache
  off and one collection a page). A 500-page set at the element ceiling could pass 900 s. The memory side is fixed; the
  time side is a debt for the integrator (§5).
- **pdfplumber still loads every page's compressed content streams** when it builds its page list; that is bounded by
  the PDF member (250 MiB), not by the page count.
- **The BFF figure is Next's adapter, not `next start`.** The probe reproduces the route's request construction and the
  product's forward; the stand's `next start` behind nginx was not run. Next 15.5.25's body handling was read: the
  cloneable body tees only for middleware or a rewrite proxy, and this application has neither.

### 4.3 Readings and deviations (each open to the integrator's veto)

1. **X-1: no lock in the reader.** The brief asked for the lock per page "as `render.py` does". The envelope now runs
   PDFium in a separate process, so the API never holds `PDFIUM_LOCK` for an upload at all (`test_the_envelope_never_takes_the_pdfium_lock`
   holds the lock in the test and probes beside it). The reader is single-threaded and owns its PDFium; the lock stays
   the process's one lock for the geometry renderer.
2. **X-1: elements, not objects.** Counting page objects let a real drawing page (the export's busiest: 396 top-level
   objects, 5 450 counted into its forms, 75 486 elements) look cheap while pdfplumber pays per path segment, and an
   object ceiling of the size the brief suggested would have refused the rehearsal's realistic 500-sheet set at ingest.
   The ceilings are on elements (path segments plus other objects).
3. **X-3: a signed, non-multipart upload is not refused by the door.** The brief said to refuse everything but a
   signed multipart request. Doing so answered `422 media_type` before the seam for an archived, role-less, seeded or
   incomplete account, and `test_role_register` / `test_authorization` (16 cases) hold that the registers' `401`/`403`
   come first. Such a request now takes no slot and none of its body is read (the application gets an empty body), and
   the seam, then the strict pass, answer it as they always did. The door's other half is as briefed.
4. **X-5: the reclassification.** A header that lies small is now `bundle_member_size` (its role's size constraint)
   as soon as its count passes the declaration, where it was `bundle_unreadable` if the lie stayed under the bound and
   `bundle_member_size` if it crossed it. The counted member, text, stamp and total bounds can no longer be the first to
   speak (every declaration is held to them first); they stay as a second line. `test_the_counted_total…` was rewritten
   accordingly.
5. **Y-4: where the sentences live.** `uploadConstraintSentence` and its table are in
   `web/src/entities/document-version/model/upload-envelope.ts`, which is **outside the grant** (the grant names
   `upload-failure.ts`). Per the brief's rule that file was not edited: the seven sentences are in `upload-failure.ts`
   (`uploadRuleSentence`, consulted after `uploadConstraintSentence`), which is what the panel prints, and the web tests
   check them there. Moving the table into `upload-envelope.ts` is a one-table edit for its owner.
6. **X-4: no `304`.** The port verifies the PNG before its digest could be compared, so a conditional answer would save
   the transfer and none of the work, and the contract declares no `304`; the browser does not ask again within the
   hour. A `304` belongs with a digest-only read on the port (`api/routers/ports.py`, outside the grant) and a reseal.
7. **The rendered-language guard sets the API base for its pass.** A crop's address is now built in the seam from the
   configured base, so `renderedScreens` and the styles census set `NEXT_PUBLIC_API_BASE_URL=/bff/v1` for their render
   and restore it.

### 4.4 Not done, or done only as far as the grant goes

- The block-list schema still reads `integer` as JSON Schema does (it admits `3.0`); the product's readers and the
  fixtures' checker are stricter. A line in the schema's `x-envelope-rules` at the next contract revision would say so.
- `tests/e2e/pc01/journey/manifest.json` (outside the grant) quotes the old «Блоки» sentence in prose that "is checked
  by nothing"; it should be updated with the new one.
- Two other widgets take a `documentUrl` (an object URL of a `Blob`, `evidence-viewer`, `norm-document`); the Y-2 guard
  is scoped to `portal-blocks`.
- Out of grant by the brief, untouched: Y-1(c)/(d), Y-3, Y-5, Y-6, Y-7, X-9 and nginx, an API `mem_limit`, O-3,
  `R-121`'s upload-time check.

### 4.5 Host and data

The owner's export was read only by `python -I` scripts over the archive in memory (the PDF reached the reader process
through a `memfd`); only counts and verdicts left them. The corpus was read in place, read-only. Generated bundles and
logs are under `.local/fix/` (ignored). One temporary PDF (`/tmp/am-source-*.pdf`, 45 MB) left by the deliberate cap kill
of the before-run was deleted by name.

### 4.6 The first api run

On `81b52b3a` the api directory had 16 red: the door's first form refused a signed JSON upload as `media_type` ahead of
the seam (4.3 item 3). `5ea70112` repaired it; the api directory then passed whole (590) and QA's 67 stayed green.

## 5. Instructions for the integrator

1. Merge `agent/w55b-fix` (fifteen commits and this report's). It touches `api/app.py` and `api/security.py` but no
   `bootstrap/**`, `contracts/**` beyond the catalogue note, migration, lock, `conftest.py` or `infra/**`. The final W55b
   `make gate` covers it.
2. The QA directory now passes whole (67); the three QA-1 probes need no change.
3. Register as debts: the run time of a 500-page drawing set against the 900 s watchdog (§4.2); a `304` with a
   digest-only crop read (§4.3 item 6); the integer rule in `x-envelope-rules` (§4.4); the journey manifest's stale
   sentence (§4.4); moving `uploadRuleSentence`'s seven sentences into `upload-envelope.ts` (§4.3 item 5); the BFF
   figure on the stand with `next start` and nginx (§4.2).
4. On the stand, re-measure with a 250 MiB body through the BFF (the rehearsal's instruction) and the vector drawing
   set through a run (`drive.py run` on `build_bundles.py vector --segments 7500`, seed 55).

## 6. Containment

`git diff --name-only 9bfa1da3..HEAD` is the list of §1 and this report; every path is inside the grant:
`src/auditmanager/ingest/**`; `analysis/stages/extraction.py`; `analysis/geometry/**`;
`api/routers/{multipart,documents,blocks}.py`; `api/app.py`; `api/security.py` (one function,
`build_credential_precheck`); `contracts/domain/v1/error-codes.json` (catalogue note only);
`tools/fixtures/portal_bundle/**`; `web/src/shared/api/**`; `web/src/entities/block/**`;
`web/src/widgets/portal-blocks/**`; `web/src/entities/document-version/model/upload-failure.ts`; `web/tests/**`;
`tests/integration/{ingest,api,analysis}/**` (no `conftest.py`); `tests/contract/**`; this report. Not touched:
`db/migrations/**`, `pyproject.toml`, `uv.lock`, `P02_LOCK.json`, `VERSION`, `release-notes/**`, `scripts/**`,
`tests/support/**`, any `conftest.py`, `tests/integration/qa_w55b/**`, `infra/**`, `bootstrap/**`, the three program
documents, the generated client, `web/openapi/**`, `FRONTEND_LOCK.json`, `web/src/_pages/**`.

`git status --porcelain -uall` after the report's commit: empty. The stack: `make down`; the two volumes of project
`auditmanager-w55b-fix` removed; `.env` deleted; every process started for a probe stopped by its own PID.
