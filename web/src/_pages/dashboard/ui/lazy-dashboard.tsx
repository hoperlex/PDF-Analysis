'use client';

/**
 * The dashboard widget, loaded lazily — `W50-PLAN.md` §3.4, `W50-LAZY-01`.
 *
 * **Why lazily.** The four panels and their aggregation are the heaviest code `/dashboard`
 * carries, and none of it is needed to draw the page's frame and title. `next/dynamic`
 * puts the widget in a chunk of its own, so the route's first-load JS no longer carries it;
 * the `next build` route table before and after is in `docs/program/W50-LAZY-01.md`.
 *
 * **Why the loading state is here and not in `app/dashboard/loading.tsx`.** A segment
 * `loading.tsx` wraps the route's `page.tsx` in a Suspense boundary, so the guard inside
 * the page (`requireScreen`) redirected a guest from INSIDE a stream that had already
 * answered `200` — a browser followed the streamed redirect, and `curl`, a probe or a
 * monitor read `200` with no `Location`. The segment file is deleted; the loading state
 * lives below the guard, around the one widget that is actually slow, and a guest gets a
 * real `307` (`W50-REGISTRY-01` §4.10, the integrator's ruling 1 at its merge).
 *
 * **Why `<LoadingState />` without `what`.** The fallback is a typed state from
 * `shared/ui` and reads «Загрузка…». It names nothing on purpose: the widget, once loaded,
 * shows its own `Загрузка: сводку по системе…` while its query is in flight, and a second
 * noun here would put two loading sentences about one thing on a reader's screen.
 *
 * **The eager seam.** The screen harness, the contrast census and the language guards
 * render a screen in ONE synchronous server pass, and in one pass a dynamic import never
 * resolves: every one of those instruments would see this fallback instead of the widget
 * and go on passing — the census blind to every colour the dashboard draws, which is the
 * `D-88` defect in a new costume. So the wrapper reads `DashboardEagerSeam`: when a
 * component is provided there, it is rendered instead of the lazy one. Only
 * `web/tests/unit/screens/harness.ts` provides it, with the widget it imports itself;
 * nothing under `web/src` mounts the seam, and
 * `web/tests/guards/lazy-boundary.guard.test.ts` holds both halves of that sentence. In the
 * product the context is always `null` and the lazy branch is the only one taken.
 *
 * **Why `ssr: false` (`D-329`, React error #418 on the first page load after a start).** The
 * widget draws only a loading state on the server — every query it reads starts after mount —
 * so the server has nothing of it to send, but a server render of a `next/dynamic` chunk is
 * not the same thing on every request. In a process that has not yet loaded the chunk the
 * import is still in flight when the shell is written, so React sends the fallback and streams
 * the widget behind it; from the second request on the module is resolved and the widget is in
 * the first bytes. The streamed variant is revealed after the first paint (React holds a reveal
 * back by about 300 ms) and hydrates only then. By that time a sibling that mounted with the
 * page (a tile on `/`, the run header on `/projects/.../runs/...`) has often filled the SAME
 * query-cache entry, so the widget's first client render shows data where the server wrote
 * «Загрузка: …»: a text or an HTML mismatch, the whole tree regenerated and #418 in the
 * console — on the first load of a route per start, and nowhere else. With `ssr: false` the
 * server writes the fallback on every request and the client renders the widget itself once
 * its chunk is in, so there is no server markup of the widget to disagree with and no
 * dependence on what the process has loaded.
 * `web/tests/unit/lazy/lazy-boundary-ssr.test.tsx` renders every wrapper before and after the
 * module is resolved and holds that the two are the same bytes.
 *
 * This module holds no static import of the widget — the widget's type reaches it through
 * the loader's inferred return type — so the page's chunk stays free of it.
 */

import dynamic from 'next/dynamic';
import { createContext, useContext } from 'react';
import type { ComponentProps, ComponentType } from 'react';

import { LoadingState } from '@/shared/ui';

const DashboardChunk = dynamic(
  () => import('@/widgets/dashboard').then((widget) => widget.Dashboard),
  // `ssr: false`: the server always sends the fallback, never the widget (`D-329`, argued in
  // `_pages/dashboard/ui/lazy-dashboard.tsx`).
  { ssr: false, loading: () => <LoadingState /> },
);

type DashboardProps = ComponentProps<typeof DashboardChunk>;

/** The eager seam. `null` everywhere but the screen harness — see the header. */
export const DashboardEagerSeam = createContext<ComponentType<DashboardProps> | null>(null);

export function LazyDashboard(props: DashboardProps) {
  const Eager = useContext(DashboardEagerSeam);
  return Eager === null ? <DashboardChunk {...props} /> : <Eager {...props} />;
}
