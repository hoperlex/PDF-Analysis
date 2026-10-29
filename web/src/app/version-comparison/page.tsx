/**
 * `/version-comparison` — the route file for «Сравнение версий» (`CMP-VC-UI-01`).
 *
 * Delegation-only: the route decides nothing. `@/_pages/version-compare` reads the comparison operations and sends its
 * commands through the session BFF.
 *
 * `W50-PLAN.md` §3.2: the route awaits `requireScreen` with its own address, `params` and `searchParams` before it renders;
 * the registry's row is `session`, roles `any-role`. Declared `force-dynamic` because the guard reads a cookie, and a screen
 * served from a cache is a screen showing somebody else's session.
 */

import { VersionComparePage } from '@/_pages/version-compare';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function VersionComparisonRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/version-comparison', { params, searchParams });
  return <VersionComparePage />;
}
