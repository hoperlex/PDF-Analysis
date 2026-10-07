/** Public API of the `stage-comparison` screen. */

export type { StageComparisonPageProps } from './ui/stage-comparison-page';
export { StageComparisonPage } from './ui/stage-comparison-page';

/**
 * The eager seam of this page's lazy widget (`W50-LAZY-01`). Provided ONLY by
 * `web/tests/unit/screens/harness.ts`, so a one-pass render sees the widget instead of its
 * loading fallback; nothing under `web/src` mounts it
 * (`web/tests/guards/lazy-boundary.guard.test.ts`).
 */
export { StageComparisonEagerSeam } from './ui/lazy-stage-comparison';
