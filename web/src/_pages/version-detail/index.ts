/** Public API of the `version-detail` page slice. */

export type { VersionDetailPageProps } from './ui/version-detail-page';
export { VersionDetailPage } from './ui/version-detail-page';

/**
 * The eager seam of this page's lazy PDF drawer (`UI-A-27`). Provided ONLY by `web/tests/unit/screens/harness.ts`, so a one-pass render
 * sees the drawer instead of its loading fallback; nothing under `web/src` mounts it (`web/tests/guards/lazy-boundary.guard.test.ts`).
 */
export { DocumentViewerEagerSeam } from './ui/version-pdf-chunk';
