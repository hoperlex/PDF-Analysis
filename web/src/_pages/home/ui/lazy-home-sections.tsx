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
 * **The object (`UIP-S01-01`).** This container is where the front door's table learns which object it is counted over:
 * `useCurrentProject`, the reader «Дашборд» uses (`UIP-G-06`), gives the object the address names and, where the address is
 * silent, the one the account chose last; it is handed to the overview as a property, and this module reads no address of its
 * own. While `getMe` is on its way the table is drawn for «Все объекты» and moves to the account's object when the answer
 * comes, as the dashboard does; that read is the one the tile under it already shares (`queryKeys.dashboard.summary(null)`).
 *
 * This module holds no static import of the widget.
 */

import dynamic from 'next/dynamic';
import { createContext, useContext } from 'react';
import type { ComponentProps, ComponentType } from 'react';

import { HOME_SCREEN } from '@/shared/config';
import { ALL_PROJECTS_PARAM, withProjectParam } from '@/shared/lib';
import { LoadingState } from '@/shared/ui';
import { useCurrentProject } from '@/entities/project';

const HomeSectionsChunk = dynamic(
  () => import('@/widgets/dashboard').then((widget) => widget.HomeSectionsOverview),
  // `ssr: false`: the server always sends the fallback, never the widget (`D-329`, argued in
  // `_pages/dashboard/ui/lazy-dashboard.tsx`).
  { ssr: false, loading: () => <LoadingState /> },
);

type HomeSectionsProps = ComponentProps<typeof HomeSectionsChunk>;

/** The eager seam. `null` everywhere but the screen harness. */
export const HomeSectionsEagerSeam = createContext<ComponentType<HomeSectionsProps> | null>(null);

/** «Все объекты» of the front door: this screen with the object chosen away (`?project=all`; the bare address would bring the last one back). */
const ALL_PROJECTS_HREF = withProjectParam(HOME_SCREEN, ALL_PROJECTS_PARAM);

export function LazyHomeSections() {
  const Eager = useContext(HomeSectionsEagerSeam);
  // Outside the app router there is no address; `HOME_SCREEN` stands in for the screen's own.
  const { projectUid } = useCurrentProject(HOME_SCREEN);
  const props: HomeSectionsProps = { projectUid, allProjectsHref: ALL_PROJECTS_HREF };
  return Eager === null ? <HomeSectionsChunk {...props} /> : <Eager {...props} />;
}
