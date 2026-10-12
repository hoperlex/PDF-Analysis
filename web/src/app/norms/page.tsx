/**
 * `/norms` — the route file for «Нормы» (`W55A-WEB-NORMS`; was the `R-66` stub).
 *
 * Delegation-only: the route decides nothing about norms. It hands the screen the session's
 * roles — the guard has just read them, and the screen draws the administrator's controls
 * only for `admin`, as the home page draws its tiles — and the search the address carries in
 * `?q=`, so a search is an address that survives a reload.
 *
 * `W50-PLAN.md` §3.2: the route awaits `requireScreen` with its own address, `params` and
 * `searchParams` before it renders; the registry's row is `session`, roles `any-role`
 * (`R-80`). Declared `force-dynamic` because the guard reads a cookie, and a screen served
 * from a cache is a screen showing somebody else's session.
 */

import { NormsPage } from '@/_pages/norms';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function NormsRoute({ params, searchParams }: ScreenRouteProps) {
  const subject = await requireScreen('/norms', { params, searchParams });
  const query = searchParams === undefined ? {} : await searchParams;
  const q = typeof query.q === 'string' ? query.q.trim() : '';
  return <NormsPage roles={subject.roles} query={q.length === 0 ? null : q} />;
}
