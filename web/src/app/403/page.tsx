/**
 * `/403` — the route file for the screen a session is sent to when it lacks a role.
 *
 * `W50-PLAN.md` §3.2, decision four. The screen registry's row is `public`, so the guard
 * lets anyone through and no redirect can loop here. The one read is `from`, the address the
 * session asked for: passed through the registry's validator and resolved to the roles that
 * address's row requires, which the screen names. An invalid `from` resolves to nothing and
 * is never echoed.
 *
 * Declared `force-dynamic` because the guard reads a cookie.
 */

import { ForbiddenPage } from '@/_pages/forbidden';
import { FROM_PARAM, requiredRolesFor } from '@/shared/config';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function ForbiddenRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/403', { params, searchParams });
  const query = searchParams === undefined ? {} : await searchParams;
  const asked = query[FROM_PARAM];
  return <ForbiddenPage requiredRoles={requiredRolesFor(Array.isArray(asked) ? asked[0] : asked)} />;
}
