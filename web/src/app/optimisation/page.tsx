/**
 * `/optimisation` — the route file for the tuning section.
 *
 * Delegation-only: the route decides nothing.
 *
 * `R-50`: the route awaits `requireAChangedPassword()` before it renders. A session still
 * on the password this deployment was seeded with is sent to `/account/password` instead,
 * and the API refuses this screen's data calls independently -- so what the reviewer would
 * otherwise meet here is a screen that cannot load. Declared `force-dynamic` because the
 * check reads a cookie, and a screen served from a cache is a screen showing somebody
 * else's session.
 */

import { OptimisationPage } from '@/_pages/optimisation';

import { requireAChangedPassword } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function OptimisationRoute() {
  await requireAChangedPassword();
  return <OptimisationPage />;
}
