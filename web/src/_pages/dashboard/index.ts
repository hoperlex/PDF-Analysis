/**
 * Public API of the `dashboard` page slice.
 *
 * The route file at `web/src/app/dashboard/page.tsx` delegates here.
 */

export { DashboardPage } from './ui/dashboard-page';

/**
 * The eager seam of this page's lazy widget (`W50-LAZY-01`). Provided ONLY by
 * `web/tests/unit/screens/harness.ts`, so a one-pass render sees the widget instead of its
 * loading fallback; nothing under `web/src` mounts it
 * (`web/tests/guards/lazy-boundary.guard.test.ts`).
 */
export { DashboardEagerSeam } from './ui/lazy-dashboard';
