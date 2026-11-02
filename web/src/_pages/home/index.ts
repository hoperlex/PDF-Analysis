/**
 * Public API of the `home` page slice — the screen at `/`.
 *
 * `HomePage` and `HomePageProps` are `W50-REGISTRY-01`'s contract, which `W50-HOME-01` kept
 * when it built the page: it replaced what the screen shows and changed neither the export
 * nor the props.
 */

export type { HomePageProps } from './ui/home-page';
export { HomePage } from './ui/home-page';

/**
 * The eager seam of the front door's lazy section overview (`W50-LAZY-01`). Provided ONLY by
 * `web/tests/unit/screens/harness.ts`, so a one-pass render sees the overview instead of its
 * loading fallback; nothing under `web/src` mounts it
 * (`web/tests/guards/lazy-boundary.guard.test.ts`).
 */
export { HomeSectionsEagerSeam } from './ui/lazy-home-sections';
