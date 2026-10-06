/**
 * `/account` — the route file for the account's profile, a placeholder in W50.
 *
 * `W50-PLAN.md` §3.2, decision three, sends a session whose profile is incomplete here, so
 * the screen registry's row is `open-to-default-credential`: a session is required, and one
 * that has not completed its profile — or is still on its seeded password — may open it.
 * Without that, the guard's redirect would land on a screen that redirects again.
 *
 * Delegation-only: the guard returns the session's subject, and the one field the
 * placeholder needs from it — whether the profile is complete — is handed down as a prop.
 * Declared `force-dynamic` because the guard reads a cookie.
 */

import { AccountPage } from '@/_pages/account';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function AccountRoute({ params, searchParams }: ScreenRouteProps) {
  const subject = await requireScreen('/account', { params, searchParams });
  return <AccountPage profileComplete={subject.profileComplete} />;
}
