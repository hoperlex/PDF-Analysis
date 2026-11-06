'use client';

/**
 * The section overview of the front door, loaded lazily — `W50-PLAN.md` §3.4, `W50-LAZY-01`.
 *
 * `HomeSectionsOverview` lives in `widgets/dashboard`, whose public API also carries the
 * heavy `Dashboard`, so a static import of it from `home-page.tsx` put the whole dashboard
 * widget into the first-load chunk of `/` and made the `next/dynamic` wrapper beside
 * `_pages/dashboard` decoration (`tests/guards/lazy-boundary.guard.test.ts` held it red).
 * The construction is the same as `_pages/dashboard/ui/lazy-dashboard.tsx`, whose header
 * carries the argument: a `next/dynamic` chunk with a typed `<LoadingState />` fallback and
 * `HomeSectionsEagerSeam`, which only the screen harness provides, so an instrument that
 * renders the page in one synchronous pass sees the overview instead of its fallback. The
 * overview shows its own «Загрузка: разделы проекта…» once loaded, so the fallback names
 * nothing. In the product the context is always `null`.
 *
 * This module holds no static import of the widget.
 */

import dynamic from 'next/dynamic';
import { createContext, useContext } from 'react';
import type { ComponentProps, ComponentType } from 'react';

import { LoadingState } from '@/shared/ui';

const HomeSectionsChunk = dynamic(
  () => import('@/widgets/dashboard').then((widget) => widget.HomeSectionsOverview),
  // `ssr: false`: the server always sends the fallback, never the widget (`D-329`, argued in
  // `_pages/dashboard/ui/lazy-dashboard.tsx`).
  { ssr: false, loading: () => <LoadingState /> },
);

type HomeSectionsProps = ComponentProps<typeof HomeSectionsChunk>;

/** The eager seam. `null` everywhere but the screen harness. */
export const HomeSectionsEagerSeam = createContext<ComponentType<HomeSectionsProps> | null>(null);

export function LazyHomeSections(props: HomeSectionsProps) {
  const Eager = useContext(HomeSectionsEagerSeam);
  return Eager === null ? <HomeSectionsChunk {...props} /> : <Eager {...props} />;
}
