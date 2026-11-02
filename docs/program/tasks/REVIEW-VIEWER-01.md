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
- changed files:
- commands/results:
- known limits:
- integration notes:
