# Task REVIEW-VIEWER-01 — custom page viewer with target highlights on the review screen

## Outcome
On the review screen (`/projects/{project_uid}/runs/{run_id}/review`) a reviewer sees the cited
PDF page as a drawn image in a custom viewer: no browser PDF toolbar, thumbnails or side panes.
Each place a finding points to is highlighted and framed on the page, the viewer opens focused
on it, and the reviewer can pan and zoom with the mouse, touch or keyboard. A place that cannot be
located is stated beside its quotation, never guessed. Both PDF panes of the screen use this
viewer: the evidence viewer and the extended-review source inspector.

## Depends on
- none (owner instruction 2026-11-02, session pdf-analysis-56; builds on the unmerged
  `agent/pdfjs-viewer-01` lane, owner decision `OD-09` → pdf.js, `R-145`)

## Frozen inputs
- domain contract: unchanged, as on `origin/dev` `4ab29560`
- API contract: unchanged; reads `getVersionBlocks` (`VersionBlockIndex`, `BlockGeometry`) and
  `streamDocumentVersionContent` as generated in `web/src/shared/api`
- analysis/comparison/event contract: unchanged
- migration head: unchanged
- base commit: `origin/dev` `4ab29560`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the review screen draws its PDF pages with the browser's own viewer in two places

### P-01 — two `<object type="application/pdf">` panes on the review screen
- captured_at: 2026-11-02
- command: `git grep -n "<object" origin/dev -- web/src/widgets/evidence-viewer web/src/widgets/extended-review`
- captured_output:
  ```text
  origin/dev:web/src/widgets/evidence-viewer/ui/evidence-viewer.tsx:173:              <object
  origin/dev:web/src/widgets/extended-review/ui/source-inspector.tsx:54:      {pageUrl === null ? null : <><p><a href={pageUrl} target="_blank" rel="noopener noreferrer">Открыть PDF на странице {page} отдельно</a></p><object key={`${version}:${page}`} className={styles.pdfPage} data={pageUrl} type="application/pdf" aria-label={`Исходный PDF, физическая страница ${page}`}><p>Встроенный просмотр PDF недоступен; откройте страницу по ссылке выше.</p></object><p>Навигация по физической странице PDF, без подсветки или утверждения координат. Браузер может показать документ с первой страницы; сверяйте номер в его панели.</p></>}
  ```
- interpretation: both panes are the browser reader; neither draws a highlight.

### P-02 — the block index carries line geometry in the evidence character space
- captured_at: 2026-11-02
- command: `git show origin/dev:contracts/api/v1/openapi.json` (schema `BlockGeometry`)
- captured_output:
  ```text
  "char_start": "Document-global offset into the version's prepared text layer, counted in
  Unicode code points -- the same sequence `Evidence.char_start` indexes."
  "bbox": "Points, top-left origin, y increasing downward"
  ```
- interpretation: a quotation's lines can be located from server geometry by intersecting
  `[char_start, char_end)` on the declared page; `status: not_produced` means no geometry exists.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none (the integrator merges into `origin/dev` after the review-fix wave
  of pdf-analysis-8c is published)
- origin_main_authority: none

## Allowed paths
- `docs/program/tasks/REVIEW-VIEWER-01.md`
- `web/package.json`
- `web/package-lock.json`
- `web/src/features/open-evidence/**`
- `web/src/widgets/evidence-viewer/**`
- `web/src/widgets/extended-review/ui/source-inspector.tsx`
- `web/src/widgets/extended-review/ui/extended-review.module.css`
- `web/src/_pages/review/**`
- `web/src/app/globals.css` (only `am-evidence*` / `am-quotation*` rules this task makes dead or changes)
- `web/tests/unit/review/**`
- `web/tests/unit/styles/screens.ts`
- `web/tests/unit/**` files that assert the two replaced panes

## Forbidden hotspots
- `contracts/**`, `db/**`, `src/**`, `infra/**`, `Makefile`, root locks
- `web/FRONTEND_LOCK.json` until the review-fix wave of pdf-analysis-8c is on `origin/dev`; the
  integrator re-measures it after that merge
- `web/src/shared/api/**`, every other widget, page and feature
- refs, tags, pushes and deployment stand

## Non-goals
- text selection, thumbnails, a page list beyond the declared pages, printing, search box
- the norm-document and specification-panel PDF panes (other screens)
- any backend, contract or migration change

## Deliverables
- `PageViewer` in `features/open-evidence`: pdf.js page image, targets, pan/zoom, minimal controls
- evidence viewer and source inspector switched to it; quotation cards linked to their frames
- pure-model and component tests; style census entries
- this task card with the handoff section filled

## Required tests
- `npx vitest run tests/unit/review tests/unit/styles tests/guards` in `web/`
- `npm run lint -- --quiet`, `npm run typecheck`
- `npx vitest run` (whole web suite); `frontend-lock.guard` is expected red until the lock is
  re-measured by the integrator — report it, do not fix it here
- real Chrome screenshots of the viewer on a real project PDF (harness outside `src/`, not committed)
- `git diff --check origin/dev`

## Integration contract
`PageViewer` takes a `blob:` URL, a page number and a list of targets (line rectangles in PDF
points, a normalised region, or a quotation to search in the page text). It resolves each target
in that order of authority, reports how each was located, and draws nothing for a target it
could not place. Evidence quotations stay byte-identical (`data-evidence-quote`). No API change.

## Failure/idempotency/security cases
- failed pdf.js load, failed page draw and a page beyond the document are explicit states with retry
- a rectangle outside the page bounds is refused, not clipped into place
- superseded renders are cancelled; documents and workers are destroyed on unmount
- no bytes are persisted client-side; the blob URL lifetime is unchanged

## Rollback / feature flag
Revert the branch merge together with its `web/package.json` and `web/package-lock.json` changes
and the re-measured `web/FRONTEND_LOCK.json`. No feature flag.

## Handoff
- changed files (all under the allowed paths; `web/FRONTEND_LOCK.json`, `contracts/**`, `src/**`, `db/**`, `infra/**`
  and `web/src/shared/api/**` untouched):
  - new, `web/src/features/open-evidence/`: `model/{pdfjs-runtime,page-geometry,locate-quotation,view-state,targets,
    use-pdf-document,use-page-content,use-element-size,use-version-block-index}.ts`,
    `ui/{page-viewer,page-viewer-view,viewer-marks,viewer-controls}.tsx`, `ui/page-viewer.module.css`;
    `index.ts` and `model/page-url.ts` (header) changed
  - new, `web/src/widgets/evidence-viewer/`: `model/quotation-targets.ts`, `ui/quotation-card.tsx`,
    `ui/evidence-viewer.module.css`; `ui/evidence-viewer.tsx`, `index.ts` rewritten
  - `web/src/widgets/extended-review/ui/source-inspector.tsx` (viewer instead of `<object>`),
    `extended-review.module.css` (dead `.pdfPage` removed)
  - `web/src/_pages/review/ui/review-page.tsx` (`useVersionBlockIndex`, `blockIndex` handed down)
  - `web/src/app/globals.css` (`am-evidence__panes` columns on wide screens, `am-evidence__page`; `am-evidence__object`
    kept: the norm document still uses it)
  - tests: `web/tests/unit/review/{view-state,targets,page-geometry,page-viewer-view,quotation-cards,locate-quotation,
    locate-quotation-pdf}.test.ts` and `mini-pdf.ts` new; `evidence-viewer.test.ts` and `viewer-and-panels.test.ts`
    rewritten (the `<object>`/`#page=` assertions now assert the viewer, same intent); `web/tests/unit/styles/screens.ts`
    (viewer states, quotation cards, `NormPdf`)
- commands/results (host load average 12-19 throughout; `df` 1.3 GB free before the whole-suite runs; nothing
  built, installed or pushed):
  - `npx vitest run` whole suite on the final tree: 29 files / 110 tests red. The same suite on a clean archive of the
    base `4ab29560` (same `node_modules`): 29 files / 108 red. The two extra are `contrast.test.ts` cases that timed out
    at the 120 s limit under load (baseline passed them at 109 s and 71 s) and pass alone on this tree (101 s, 63 s).
    Every other red is identical in both runs: `frontend-lock.guard` (2, expected: `pdfjs-dist` is a new dependency),
    `query-key-shape.guard` typecheck, `lazy-boundary.guard` (a) (`_pages/home` imports `widgets/dashboard`),
    `rendered-language.guard` (5), 8 in `tests/unit/styles`, the AR v3 run-list screens, upload envelope, error codes
    and others. None names the review viewer.
  - `tests/unit/styles` alone, this tree vs base: the same 8 reds. Their detail differs only by: `.pdfPage` (dead,
    removed) no longer unreached; two more *sites* of the already-failing `am-state__loading-lines` pair (the viewer's
    loading state); no pair of the viewer is below its threshold in either palette.
  - `npm run lint -- --quiet`: 2 errors, both `no-control-regex` in `export-evidence-package/model/package.ts` (not
    touched). `npm run typecheck`: exit 2, one error, `stage-comparison/model/saved-results.ts(199,29)` (not touched).
    `git diff --check 4ab29560`: clean. (`origin/dev` has since moved to `9617c759`, one docs commit, no overlap.)
  - 7 mutation probes, each reddened a test and was reverted: lines the text contradicts accepted; closed instead of
    half-open character range; no right-edge bounds check; the whole page accepted as a region; no bleed on a cut text
    box; no absolute cap on automatic focus; pan not clamped.
  - real Chrome 156 (headless shell) over CDP against a throwaway Vite harness mounting the real `EvidenceViewer` and
    `SourceInspector` with the real hooks, on the AR section PDF of `synthetic-project-mayak-7` and variants of it (wide
    sheet, `/Rotate 90`, crop box off the origin), with the block index built by the backend's own `extract_document` and
    `_build_blocks`: 25 screenshots in `.local/reports/review-viewer-01/`; frames sit on the lines (pixel check of the
    canvas ink inside each frame, margins symmetric); the point under the cursor stays under it on ctrl+wheel
    (0.2864 -> 0.2862 of the page); plain wheel not taken; drag, keys `+ - 0` and arrows, double click, tab order,
    touch pinch (1.35x -> 5.42x) and one-finger pan, keyboard focus on the pill. Harness and its server removed.
- known limits:
  - the server measures from the media box and pdf.js from the crop box. A page whose crop box does not start at the
    origin would put every server line a fixed distance off; this is caught only when the page text contains the
    quotation (the lines are then refused and the text decides). On a scan with such a crop box the lines stand,
    shifted. A `/Rotate` page agreed with the server in the one case measured.
  - text-layer boxes for a quotation that starts or ends inside a text item are a character-fraction estimate widened by
    half a character on the cut sides: they can include a sliver of the neighbouring glyph, never clip the last one.
  - the whole page is drawn as one bitmap capped at 16 M pixels, re-drawn when a zoom settles; a very large sheet at
    the maximum zoom is stretched past the cap (softer, never blank). No tiled rendering.
  - pdf.js is given no `wasmUrl`, `cMapUrl`, `standardFontDataUrl` or `iccUrl`: JPX/JBIG2 images, CJK CMaps and
    non-embedded standard fonts may draw wrongly. The project PDFs measured here embed what they use.
  - `bbox_norm` is read in the orientation pdf.js draws (rotation applied); not measured on a rotated portal page.
  - narrow panes (420 px) open on the active target at 1.2 px/pt, the line wider than the pane; the reader pans along it.
  - the contract stays: the character range and `block_id` are never rendered; the hint line says «Ctrl», which no
    rendered-language screen reaches today.
- integration notes:
  - re-measure `web/FRONTEND_LOCK.json` after merging (new dependency `pdfjs-dist` 6.4.299); the guard is red until then.
  - `next build` was not run (no disk): the worker is addressed as `new URL('pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url)`, which Next must emit as an asset; `npm run build` is the check, as the old lane noted.
  - `useVersionBlockIndex` uses the key `queryKeys.versions.blocks` like «Блоки»; no API or contract change.
