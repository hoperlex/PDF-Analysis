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
 * **Old addresses keep working (`HOSTS-WEB-01`).** «Исполнители» has two tabs, «Серверы» and «Модели по этапам»; the former
 * tabs «Подключения», «Группы», «Правила», «Назначения» and «Процессы» are on `/workers/advanced`. An address that names one
 * of them (`?tab=connections`), or a connection for the key form (`?connection=`, where the BFF's `executor-secret` door sends
 * the person back with how the last key post ended, `?secret=`), is redirected there with its parameters; the key form itself
 * is rendered on that page, on the server. Every value read from the address is validated against a closed set or a pattern
 * first; a value that fails is dropped, never echoed. «Обзор» became the summary line of «Серверы»: its old address opens
 * the screen on the default tab.
 */

import { redirect } from 'next/navigation';

import { WORKERS_ADVANCED_ADDRESS, WORKERS_TAB_PARAM, WorkersPage, isWorkersTab, legacyAdvancedTab } from '@/_pages/workers';
import {
  EXECUTOR_SECRET_CONNECTION_PARAM,
  EXECUTOR_SECRET_OUTCOME_PARAM,
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
  const legacy = legacyAdvancedTab(tab);

  if (connectionId !== null || legacy !== null) {
    const forward = new URLSearchParams();
    forward.set(WORKERS_TAB_PARAM, connectionId !== null ? 'connections' : (legacy as string));
    if (connectionId !== null) {
      forward.set(EXECUTOR_SECRET_CONNECTION_PARAM, connectionId);
      if (isExecutorSecretOutcome(outcome)) forward.set(EXECUTOR_SECRET_OUTCOME_PARAM, outcome);
    }
    redirect(`${WORKERS_ADVANCED_ADDRESS}?${forward.toString()}`);
  }

  return <WorkersPage initialTab={isWorkersTab(tab) ? tab : undefined} />;
}
