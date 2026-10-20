/**
 * `/dispatcher` — the route file for «Диспетчер» (`W61-DISPATCHER-01`).
 *
 * Delegation-only: the route decides nothing about assignments. It hands the screen the
 * session's roles — the guard has just read them, and the screen draws the administrator's
 * controls only for `admin` — and the API decides every read and move on its own evidence.
 *
 * `W50-PLAN.md` §3.2: the route awaits `requireScreen` with its own address, `params` and
 * `searchParams` before it renders; the registry's row is `session`, roles `any-role`
 * (`R-80`). Declared `force-dynamic` because the guard reads a cookie, and a screen served
 * from a cache is a screen showing somebody else's session.
 */

import { DispatcherPage } from '@/_pages/dispatcher';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function DispatcherRoute({ params, searchParams }: ScreenRouteProps) {
  const subject = await requireScreen('/dispatcher', { params, searchParams });
  return <DispatcherPage roles={subject.roles} />;
}
