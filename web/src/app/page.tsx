/**
 * `/` — the application's front door (`W50-PLAN.md` §3.2, §3.6).
 *
 * It no longer redirects to `/projects`: a completed sign-in lands here, and the screen
 * registry gives `/` a `session` row of its own. Delegation-only, like every other route:
 * the guard decides who may open it and returns the session's subject, and the two fields
 * the home page needs from it — the name and the roles — are handed down as props. The
 * subject carries no credential; `credentialOf` is the forwarder's alone.
 *
 * Declared `force-dynamic` because the guard reads a cookie, and a home page served from a
 * cache is a home page greeting somebody else.
 */

import { HomePage } from '@/_pages/home';

import type { ScreenRouteProps } from './bff/session/screen-lock';
import { requireScreen } from './bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function RootPage({ params, searchParams }: ScreenRouteProps) {
  const subject = await requireScreen('/', { params, searchParams });
  return <HomePage displayLabel={subject.displayLabel} roles={subject.roles} />;
}
