'use client';

/**
 * The stage-comparison widget, loaded lazily — `W50-PLAN.md` §3.4, `W50-LAZY-01`.
 *
 * The same construction as `_pages/dashboard/ui/lazy-dashboard.tsx`, whose header carries
 * the whole argument: a `next/dynamic` chunk with a typed `<LoadingState />` fallback below
 * the page's guard, and `StageComparisonEagerSeam`, which only the screen harness provides,
 * so the instruments that render in one synchronous pass see the widget rather than its
 * fallback. No static import of the widget.
 */

import dynamic from 'next/dynamic';
import { createContext, useContext } from 'react';
import type { ComponentProps, ComponentType } from 'react';

import { LoadingState } from '@/shared/ui';

const StageComparisonChunk = dynamic(
  () => import('@/widgets/stage-comparison').then((widget) => widget.StageComparison),
  { loading: () => <LoadingState /> },
);

type StageComparisonProps = ComponentProps<typeof StageComparisonChunk>;

/** The eager seam. `null` everywhere but the screen harness. */
export const StageComparisonEagerSeam = createContext<ComponentType<StageComparisonProps> | null>(
  null,
);

export function LazyStageComparison(props: StageComparisonProps) {
  const Eager = useContext(StageComparisonEagerSeam);
  return Eager === null ? <StageComparisonChunk {...props} /> : <Eager {...props} />;
}
