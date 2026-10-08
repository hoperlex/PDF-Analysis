/**
 * Public API of the review page.
 *
 * `src/app/.../review/page.tsx` delegates to `ReviewPage` and imports nothing deeper.
 */

export type { ReviewPageProps } from './ui/review-page';
export { ReviewPage } from './ui/review-page';

export type { PresentFailureOptions } from './model/present-failure';
export { presentFailure, presentFailureOrNull } from './model/present-failure';

export type { ReviewSelection } from './model/selection';
export { resolveSelection, selectFinding, selectPage } from './model/selection';

/**
 * The eager seam of this page's lazy widget (`W50-LAZY-01`). Provided ONLY by
 * `web/tests/unit/screens/harness.ts`, so a one-pass render sees the widget instead of its
 * loading fallback; nothing under `web/src` mounts it
 * (`web/tests/guards/lazy-boundary.guard.test.ts`).
 */
export { EvidenceViewerEagerSeam } from './ui/lazy-evidence-viewer';
