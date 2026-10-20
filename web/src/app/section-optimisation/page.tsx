/**
 * `/section-optimisation` — the route file for «Оптимизация разделов» (`R-66`).
 *
 * Delegation-only: the route decides nothing. `@/_pages/section-optimisation` shows, for a
 * section, the combined Form-7 specification of the current versions of every project whose
 * document set an expert confirmed in it, since `W63-SECTION-FORM7-01` graduated it from the
 * honest stub it was.
 *
 * `W50-PLAN.md` §3.2: the route awaits `requireScreen` with its own address, `params` and
 * `searchParams` before it renders; the registry's row is `session`, roles `any-role`. Declared
 * `force-dynamic` because the guard reads a cookie, and a screen served from a cache is a
 * screen showing somebody else's session.
 */

import { SectionOptimisationPage } from '@/_pages/section-optimisation';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function SectionOptimisationRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/section-optimisation', { params, searchParams });
  return <SectionOptimisationPage />;
}
