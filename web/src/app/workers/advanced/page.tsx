/**
 * `/workers/advanced` — the route file for the administrator's advanced page of the executors section (`HOSTS-WEB-01`).
 *
 * `W50-PLAN.md` §3.2: the route awaits `requireScreen` with its own address, `params` and `searchParams` before it renders;
 * the screen registry's row decides who may open it (an administrator only). Declared `force-dynamic` because the guard reads a
 * cookie.
 *
 * **Two things beyond delegation, both about the key form (`EXEC-HTTP-01`).** The address may name a section (`?tab=`) and a
 * connection (`?connection=`) and carry how the last key post ended (`?secret=`): the BFF's `executor-secret` door redirects
 * to `/workers`, which sends the person here. When the address names a connection, this route renders the key form **on the
 * server** and hands the element to the page as a prop. The form is a server component with no handler, so the key an
 * administrator pastes is never a JavaScript value. Every value read from the address is validated against a closed set or a
 * pattern first; a value that fails is dropped, never echoed.
 */

import { WORKERS_TAB_PARAM, WorkersAdvancedPage, isAdvancedSection } from '@/_pages/workers';
import {
  EXECUTOR_SECRET_CONNECTION_PARAM,
  EXECUTOR_SECRET_OUTCOME_PARAM,
  SetExecutorSecretForm,
  isExecutorConnectionId,
  isExecutorSecretOutcome,
} from '@/features/set-executor-secret';

import type { ScreenRouteProps } from '../../bff/session/screen-lock';
import { requireScreen } from '../../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

// An expression body, not a block: `screen-guard.guard.test.ts` reads the file for the first
// `return` and wants the `requireScreen` await before it.
const first = (value: string | string[] | undefined): string | undefined =>
  Array.isArray(value) ? value[0] : value;

export default async function WorkersAdvancedRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/workers/advanced', { params, searchParams });

  const query = searchParams === undefined ? {} : await searchParams;
  const tab = first(query[WORKERS_TAB_PARAM]);
  const connection = first(query[EXECUTOR_SECRET_CONNECTION_PARAM]);
  const outcome = first(query[EXECUTOR_SECRET_OUTCOME_PARAM]);
  const connectionId = isExecutorConnectionId(connection) ? connection : null;

  return (
    <WorkersAdvancedPage
      // A key form is in «Подключения», whatever else the address says.
      initialTab={connectionId !== null ? 'connections' : isAdvancedSection(tab) ? tab : undefined}
      secretConnectionId={connectionId}
      secretForm={
        connectionId === null ? undefined : (
          <SetExecutorSecretForm
            connectionId={connectionId}
            outcome={isExecutorSecretOutcome(outcome) ? outcome : null}
          />
        )
      }
    />
  );
}
