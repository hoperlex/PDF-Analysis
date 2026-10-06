'use client';

/**
 * The run-progress widget, loaded lazily — `W50-PLAN.md` §3.4, `W50-LAZY-01`.
 *
 * The same construction as `_pages/dashboard/ui/lazy-dashboard.tsx`, whose header carries
 * the whole argument: a `next/dynamic` chunk with a typed `<LoadingState />` fallback below
 * the page's guard, and `RunProgressEagerSeam`, which only the screen harness provides, so
 * the instruments that render in one synchronous pass see the widget rather than its
 * fallback. No static import of the widget.
 */

import dynamic from 'next/dynamic';
import { createContext, useContext } from 'react';
import type { ComponentProps, ComponentType } from 'react';

import { LoadingState } from '@/shared/ui';

const RunProgressChunk = dynamic(
  () => import('@/widgets/run-progress').then((widget) => widget.RunProgress),
  { loading: () => <LoadingState /> },
);

type RunProgressProps = ComponentProps<typeof RunProgressChunk>;

/** The eager seam. `null` everywhere but the screen harness. */
export const RunProgressEagerSeam = createContext<ComponentType<RunProgressProps> | null>(null);

export function LazyRunProgress(props: RunProgressProps) {
  const Eager = useContext(RunProgressEagerSeam);
  return Eager === null ? <RunProgressChunk {...props} /> : <Eager {...props} />;
}
