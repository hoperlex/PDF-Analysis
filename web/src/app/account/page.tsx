/**
 * `/account` — the route file for the account's profile.
 *
 * `W50-PLAN.md` §3.2, decision three, sends a session whose profile is incomplete here, so
 * the screen registry's row is `open-to-default-credential`: a session is required, and one
 * that has not completed its profile — or is still on its seeded password — may open it.
 * Without that, the guard's redirect would land on a screen that redirects again.
 *
 * Delegation-only: the guard returns the session's subject and the validated `next`
 * destination is handed to the profile screen for the completion handoff.
 * Declared `force-dynamic` because the guard reads a cookie.
 */

import { AccountPage } from '@/_pages/account';
import { NEXT_PARAM, safeReturnPath } from '@/shared/config';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function AccountRoute({ params, searchParams }: ScreenRouteProps) {
  const subject = await requireScreen('/account', { params, searchParams });
  const query = searchParams === undefined ? {} : await searchParams;
  const asked = query[NEXT_PARAM];
  return <AccountPage profileComplete={subject.profileComplete} next={safeReturnPath(Array.isArray(asked) ? asked[0] : asked)} />;
}
