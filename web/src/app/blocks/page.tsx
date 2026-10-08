/**
 * `/blocks` — the route file for the block-markup section.
 *
 * Delegation-only: the route decides nothing.
 *
 * `W50-PLAN.md` §3.2: the route awaits `requireScreen` with its own address, `params` and
 * `searchParams` before it renders, and the screen registry's row for that address decides
 * who may open it: a guest is sent to sign in and comes back here, a default credential
 * goes to `/account/password`, an incomplete profile to `/account`. Declared
 * `force-dynamic` because the guard reads a cookie, and a screen served from a cache is a
 * screen showing somebody else's session.
 */

import { BlocksPage } from '@/_pages/blocks';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function BlocksRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/blocks', { params, searchParams });
  return <BlocksPage />;
}
