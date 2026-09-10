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
