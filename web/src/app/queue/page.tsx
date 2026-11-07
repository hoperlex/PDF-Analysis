/**
 * `/queue` — the route file for the durable execution queue.
 *
 * Delegation-only: the route decides nothing. `@/_pages/queue` reads the sealed
 * execution projection and handles commands through the session BFF.
 *
 * `W50-PLAN.md` §3.2: the route awaits `requireScreen` with its own address, `params` and
 * `searchParams` before it renders; the registry's row is `session`, roles `expert` and `admin` (`R-150w`). Declared
 * `force-dynamic` because the guard reads a cookie, and a screen served from a cache is a
 * screen showing somebody else's session.
 *
 * **The filter is in the address** (`?state=failed&period=week`, second UX pass): a link from «Исполнители», a
 * counter or a pasted address opens the queue already narrowed. The route reads it here, on the server, and hands the
 * page the parsed value, so the first read of the queue is the filtered one and no unfiltered request precedes it. A value
 * outside the closed sets is dropped by `readQueueAddress`, never echoed.
 */

import { QueuePage, readQueueAddress } from '@/_pages/queue';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

// An expression body, not a block: `screen-guard.guard.test.ts` reads the file for the first
// `return` and wants the `requireScreen` await before it.
const first = (value: string | string[] | undefined): string | undefined =>
  Array.isArray(value) ? value[0] : value;

export default async function QueueRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/queue', { params, searchParams });

  const query = searchParams === undefined ? {} : await searchParams;
  const named = new URLSearchParams();
  for (const [name, value] of Object.entries(query)) {
    const one = first(value);
    if (one !== undefined) named.set(name, one);
  }
  return <QueuePage initialAddress={readQueueAddress(named)} />;
}
