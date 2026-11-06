/**
 * `/section-optimisation` — the route file for «Оптимизация разделов» (`R-66`).
 *
 * Delegation-only: the route decides nothing. `@/_pages/section-optimisation` shows, for a
 * section, the combined Form-7 specification of the current versions of every project whose
 * document set an expert confirmed in it, since `W63-SECTION-FORM7-01` graduated it from the
 * honest stub it was; since `UI-B-20` it reads `?section=`, `?project=` and `?tab=` from its address and hands them to the page.
 *
 * `W50-PLAN.md` §3.2: the route awaits `requireScreen` with its own address, `params` and
 * `searchParams` before it renders; the registry's row is `session`, roles `any-role`. Declared
 * `force-dynamic` because the guard reads a cookie, and a screen served from a cache is a
 * screen showing somebody else's session.
 */

import { SectionOptimisationPage, readSectionOptimisationAddress } from '@/_pages/section-optimisation';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

const first = (value: string | string[] | undefined): string | undefined =>
  Array.isArray(value) ? value[0] : value;

export default async function SectionOptimisationRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/section-optimisation', { params, searchParams });
  // `UI-B-20`: `?section=<code>&project=<project_uid>&tab=accepted` opens the screen on that section, project and tab.
  const query = searchParams === undefined ? {} : await searchParams;
  return (
    <SectionOptimisationPage
      initial={readSectionOptimisationAddress({
        section: first(query.section),
        project: first(query.project),
        tab: first(query.tab),
      })}
    />
  );
}
