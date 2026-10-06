/** Public API of the `knowledge-base` page slice. */

export { KnowledgeBasePage } from './ui/knowledge-base-page';

/**
 * The eager seam of this page's lazy widget (`W50-LAZY-01`). Provided ONLY by
 * `web/tests/unit/screens/harness.ts`, so a one-pass render sees the widget instead of its
 * loading fallback; nothing under `web/src` mounts it
 * (`web/tests/guards/lazy-boundary.guard.test.ts`).
 */
export { KnowledgeBaseEagerSeam } from './ui/lazy-knowledge-base';
