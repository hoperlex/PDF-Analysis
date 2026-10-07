'use client';

/**
 * The evidence viewer, loaded lazily — `W50-PLAN.md` §3.4, `W50-LAZY-01`.
 *
 * The same construction as `_pages/dashboard/ui/lazy-dashboard.tsx`, whose header carries
 * the whole argument: a `next/dynamic` chunk with a typed `<LoadingState />` fallback, and
 * `EvidenceViewerEagerSeam`, which only the screen harness provides, so the instruments
 * that render in one synchronous pass see the viewer rather than its fallback. No static
 * import of the widget.
 *
 * The viewer is mounted only once a finding is selected and its detail has arrived, so the
 * chunk is fetched the first time a reviewer opens a finding, not when the review screen
 * opens — which is the half of the review screen that is not needed to read the list.
 */

import dynamic from 'next/dynamic';
import { createContext, useContext } from 'react';
import type { ComponentProps, ComponentType } from 'react';

import { LoadingState } from '@/shared/ui';

const EvidenceViewerChunk = dynamic(
  () => import('@/widgets/evidence-viewer').then((widget) => widget.EvidenceViewer),
  { loading: () => <LoadingState /> },
);

type EvidenceViewerProps = ComponentProps<typeof EvidenceViewerChunk>;

/** The eager seam. `null` everywhere but the screen harness. */
export const EvidenceViewerEagerSeam = createContext<ComponentType<EvidenceViewerProps> | null>(
  null,
);

export function LazyEvidenceViewer(props: EvidenceViewerProps) {
  const Eager = useContext(EvidenceViewerEagerSeam);
  return Eager === null ? <EvidenceViewerChunk {...props} /> : <Eager {...props} />;
}
