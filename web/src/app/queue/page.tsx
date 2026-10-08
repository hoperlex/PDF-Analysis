/**
 * `/queue` — the route file for «Очередь», a section on its way (`R-66`).
 *
 * Delegation-only: the route decides nothing. The screen is an honest stub built the way
 * `/logs` is — `@/_pages/queue` renders `RoutePlaceholder` with a promise of its own.
 *
 * `W50-PLAN.md` §3.2: the route awaits `requireScreen` with its own address, `params` and
 * `searchParams` before it renders; the registry's row is `session`, roles `any`. Declared
 * `force-dynamic` because the guard reads a cookie, and a screen served from a cache is a
 * screen showing somebody else's session.
 */

import { QueuePage } from '@/_pages/queue';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function QueueRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/queue', { params, searchParams });
  return <QueuePage />;
}
