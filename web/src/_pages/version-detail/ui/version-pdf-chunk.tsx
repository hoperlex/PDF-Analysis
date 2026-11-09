'use client';

/**
 * The version's PDF drawer, loaded lazily — `UI-A-27`, written as the other lazy boundaries are (`W50-PLAN.md` §3.4,
 * `W50-LAZY-01`; `_pages/review/ui/lazy-evidence-viewer.tsx` carries the whole argument).
 *
 * A `next/dynamic` chunk with a typed `<LoadingState />` fallback below the page's guard, and `DocumentViewerEagerSeam`, a context only the
 * screen harness provides, so the instruments that render in one synchronous pass see the drawer rather than its fallback. No static import
 * of the widget: `tests/guards/lazy-boundary.guard.test.ts` reads the import graph of `_pages` for one.
 *
 * The page mounts this only after «Просмотр PDF» is pressed, so the chunk (and pdf.js behind it, and the document's bytes) are asked for on
 * that press and not when the version page opens — the original creates its `<iframe>` the same way (`v-if="showVersionPdf"`).
 *
 * **`ssr: false`** (`D-329`, argued in `_pages/dashboard/ui/lazy-dashboard.tsx`): the drawer exists only on the client, so the server never
 * writes a streamed boundary the client could disagree with. It is mounted after a press, never in the server's first pass, so this
 * costs nothing here; it is stated so that this boundary is built like the five it copies.
 *
 * Named for its use rather than `lazy-*.tsx`: the files of that name belong to the hydration lane (`D-329`) and were not touched.
 */

import dynamic from 'next/dynamic';
import { createContext, useContext } from 'react';
import type { ComponentProps, ComponentType } from 'react';

import { LoadingState } from '@/shared/ui';

const DocumentViewerChunk = dynamic(
  () => import('@/widgets/evidence-viewer').then((widget) => widget.DocumentViewer),
  { ssr: false, loading: () => <LoadingState /> },
);

type DocumentViewerProps = ComponentProps<typeof DocumentViewerChunk>;

/** The eager seam. `null` everywhere but the screen harness. */
export const DocumentViewerEagerSeam = createContext<ComponentType<DocumentViewerProps> | null>(null);

export function LazyDocumentViewer(props: DocumentViewerProps) {
  const Eager = useContext(DocumentViewerEagerSeam);
  return Eager === null ? <DocumentViewerChunk {...props} /> : <Eager {...props} />;
}
