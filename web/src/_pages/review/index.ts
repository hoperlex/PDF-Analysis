/**
 * Public API of the review page.
 *
 * `src/app/.../review/page.tsx` delegates to `ReviewPage` and imports nothing deeper.
 */

export type { ReviewPageProps } from './ui/review-page';
export { ReviewPage } from './ui/review-page';

export type { PresentFailureOptions } from './model/present-failure';
export { presentFailure, presentFailureOrNull, presentFindingsFailure } from './model/present-failure';

export type { ReviewSelection } from './model/selection';
export { resolveSelection, selectFinding, selectPage } from './model/selection';

/**
 * The eager seam of this page's lazy widget (`W50-LAZY-01`). Provided ONLY by
 * `web/tests/unit/screens/harness.ts`, so a one-pass render sees the widget instead of its
 * loading fallback; nothing under `web/src` mounts it
 * (`web/tests/guards/lazy-boundary.guard.test.ts`).
 */
export { EvidenceViewerEagerSeam } from './ui/lazy-evidence-viewer';
export { ReviewRowActions, acceptNeedsSeverity } from './ui/review-row-actions';
/** «Во весь экран», exported so the styling census renders it open. */
export { ReviewViewerAside, ReviewViewerDialog } from './ui/review-viewer-dialog';
export type { ReviewViewerAsideProps, ReviewViewerDialogProps } from './ui/review-viewer-dialog';
export type { ReviewRowActionsProps } from './ui/review-row-actions';
/** «Блоки страницы N» under the page (`UI-A-74`), exported so the styling census renders its view. */
export { PageBlocksStrip, ReviewPageBlocks } from './ui/page-blocks';
export type { PageBlocksShown, PageBlocksStripProps, ReviewPageBlocksProps } from './ui/page-blocks';
export { readPageBlocks, stripPageOf } from './model/page-blocks';
export type { PageBlocksReading, PageBlocksSource } from './model/page-blocks';
/** «Блоки замечания» under the page (`UI-PARITY-C6`), exported so the styling census renders its view. */
export { FindingBlocksStrip, ReviewFindingBlocks } from './ui/finding-blocks';
export type { FindingBlocksShown, FindingBlocksStripProps, ReviewFindingBlocksProps } from './ui/finding-blocks';
export { readFindingBlocks } from './model/finding-blocks';
export type { FindingBlocksReading, FindingBlocksSource } from './model/finding-blocks';
/** The card of a block finding (`F8-WEB`, `D-683`): the page with a frame at each block, exported so the census and the preview render its view. */
export { BlockEvidence, BlockEvidenceView } from './ui/block-evidence';
export type { BlockEvidenceProps, BlockEvidenceViewProps } from './ui/block-evidence';
export { BLOCK_FRAME_SENTENCES, blockCardsOnPage, blockFrameOf, blockPages } from './model/block-targets';
export type { BlockCard, BlockFrame } from './model/block-targets';
