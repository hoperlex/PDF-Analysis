/**
 * `/workers` — the route file for the executors section.
 *
 * `W50-PLAN.md` §3.2: the route awaits `requireScreen` with its own address, `params` and
 * `searchParams` before it renders, and the screen registry's row for that address decides
 * who may open it: a guest is sent to sign in and comes back here, a default credential
 * goes to `/account/password`, an incomplete profile to `/account`. Declared
 * `force-dynamic` because the guard reads a cookie, and a screen served from a cache is a
 * screen showing somebody else's session.
 *
 * **Two things beyond delegation, both about the key form (`EXEC-HTTP-01`).** The address may
 * name a tab (`?tab=`) and a connection (`?connection=`) and carry how the last key post ended
 * (`?secret=`): the BFF's `executor-secret` door redirects here. When it names a connection, this
 * route renders the key form **on the server** and hands the element to the page as a prop. The
 * form is a server component with no handler, so the key an administrator pastes is never a
 * JavaScript value; the page, a client component, only decides where the element sits. Every
 * value read from the address is validated against a closed set or a pattern first; a value
 * that fails is dropped, never echoed.
 */

import { WORKERS_TAB_PARAM, WorkersPage, isWorkersTab } from '@/_pages/workers';
import {
  EXECUTOR_SECRET_CONNECTION_PARAM,
  EXECUTOR_SECRET_OUTCOME_PARAM,
  SetExecutorSecretForm,
  isExecutorConnectionId,
  isExecutorSecretOutcome,
} from '@/features/set-executor-secret';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

// An expression body, not a block: `screen-guard.guard.test.ts` reads the file for the first
// `return` and wants the `requireScreen` await before it.
const first = (value: string | string[] | undefined): string | undefined =>
  Array.isArray(value) ? value[0] : value;

export default async function WorkersRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/workers', { params, searchParams });

  const query = searchParams === undefined ? {} : await searchParams;
  const tab = first(query[WORKERS_TAB_PARAM]);
  const connection = first(query[EXECUTOR_SECRET_CONNECTION_PARAM]);
  const outcome = first(query[EXECUTOR_SECRET_OUTCOME_PARAM]);
  const connectionId = isExecutorConnectionId(connection) ? connection : null;

  return (
    <WorkersPage
      // A key form is on the «Подключения» tab, whatever else the address says.
      initialTab={connectionId !== null ? 'connections' : isWorkersTab(tab) ? tab : undefined}
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
