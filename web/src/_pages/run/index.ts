/** Public API of the `run` page slice. */

export type { RunPageProps } from './ui/run-page';
export { RunPage } from './ui/run-page';

/**
 * The eager seam of this page's lazy widget (`W50-LAZY-01`). Provided ONLY by
 * `web/tests/unit/screens/harness.ts`, so a one-pass render sees the widget instead of its
 * loading fallback; nothing under `web/src` mounts it
 * (`web/tests/guards/lazy-boundary.guard.test.ts`).
 */
export { RunProgressEagerSeam } from './ui/lazy-run-progress';
