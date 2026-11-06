/**
 * `/schedule` — the route file for «График работ» (`UI-PARITY-P0P`).
 *
 * Delegation-only: it hands the screen the session's roles — the screen draws the administrator's controls only for
 * `admin` — and the tab, month, reserve start and engineer the address names. The API decides every read and move.
 *
 * `W50-PLAN.md` §3.2: the route awaits `requireScreen` with its own address before it renders; the registry's row is
 * `session`, roles `expert` and `admin`. Declared `force-dynamic` because the guard reads a cookie.
 */

import { WorkSchedulePage, readScheduleAddress } from '@/_pages/work-schedule';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

const first = (value: string | string[] | undefined): string | undefined =>
  Array.isArray(value) ? value[0] : value;

export default async function WorkScheduleRoute({ params, searchParams }: ScreenRouteProps) {
  const subject = await requireScreen('/schedule', { params, searchParams });
  const query = searchParams === undefined ? {} : await searchParams;
  return (
    <WorkSchedulePage
      roles={subject.roles}
      initial={readScheduleAddress({
        tab: first(query.tab),
        month: first(query.month),
        start: first(query.start),
        engineer: first(query.engineer),
      })}
    />
  );
}
