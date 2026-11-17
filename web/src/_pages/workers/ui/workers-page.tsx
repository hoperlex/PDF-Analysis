'use client';

/**
 * `/workers` — «Диспетчер» (`W54-WORKERS-WEB`; two tabs since `HOSTS-WEB-01`, ADR-0028, plan 2026-11-09 §7; four since `UIP-S15-06`).
 *
 * Four tabs, «Обзор · Серверы · Задачи · Модели по этапам», and the screen opens on «Обзор». **«Обзор»**: a strip of five numbers
 * (servers on line, running, queued, errors, free places) and the servers in a short form. **«Серверы»**: the servers the stand
 * sends model work to, a card each, with what each is doing now. **«Задачи»**: the queue's jobs as «Активные», «Завершённые» and
 * «Ошибки», read only, with the period of the completed ones. **«Модели по этапам»**: a table of six rows, «строка — модель ·
 * усилие», read-only for an expert and editable for an administrator. For an administrator only, a quiet link «Расширенные ▸»
 * leads to a separate page that keeps the former tabs, `/workers/advanced`. The tab is in the address, `?tab=overview|servers|
 * tasks|models`, so a reload or a shared link comes back to it.
 *
 * Nothing is read until the account's roles are: the viewer sees none of the tabs' data (`R-150w`), and a role that is read late
 * must not first send a read the API refuses. Only the open tab is mounted, so a closed tab reads nothing. The reads refresh
 * themselves under the operational-list policy while the browser tab is visible, and everything is refreshed on tab return, after a
 * command and by «Обновить».
 *
 * The key form of a connection (`?connection=`) arrives at `/workers/advanced`; the route sends an old address there.
 */

import { useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { useState } from 'react';

import { queryKeys } from '@/shared/api';
import { useMe } from '@/entities/account';
import { canExecute, executionFailure } from '@/entities/execution';
import { ExecutorHosts, ExecutorHostsOverview, ExecutorHostTasks } from '@/widgets/executor-hosts';
import { ExecutorStageModels } from '@/widgets/executor-stage-models';
import { ErrorState, LoadingState, PageShell } from '@/shared/ui';

import { ADVANCED_LINK_LABEL, WORKERS_ADVANCED_ADDRESS } from '../model/advanced';
import { DEFAULT_WORKERS_TAB, WORKERS_TAB_PARAM } from '../model/tabs';
import type { WorkersTab } from '../model/tabs';
import { WorkersTabs } from './workers-tabs';

export interface WorkersPageProps {
  /** The tab the address named; the screen opens on «Обзор» when it names none. */
  readonly initialTab?: WorkersTab | undefined;
}

export function WorkersPage({ initialTab }: WorkersPageProps = {}) {
  const [tab, setTab] = useState<WorkersTab>(initialTab ?? DEFAULT_WORKERS_TAB);
  const account = useMe();
  const client = useQueryClient();
  const roles = account.data?.roles ?? [];
  const accountFailure = account.error === null ? null : executionFailure(account.error, false);

  /** A tab is a place in the address, so a reload or a shared link comes back to it. */
  function openTab(next: WorkersTab) {
    setTab(next);
    try {
      window.history.replaceState(null, '', `?${WORKERS_TAB_PARAM}=${next}`);
    } catch {
      // No history to write (a preview, a sandboxed frame): the tab still changes.
    }
  }

  return (
    <PageShell
      title="Диспетчер"
      subtitle="Серверы, что на них сейчас идёт и какая модель у каждого этапа."
      actions={(
        <>
          {canExecute(roles, 'connections') ? (
            <Link className="am-button am-button--quiet" href={WORKERS_ADVANCED_ADDRESS} data-workers-advanced-link>{ADVANCED_LINK_LABEL}</Link>
          ) : null}
          <button className="am-button am-button--quiet" type="button" onClick={() => void client.invalidateQueries({ queryKey: queryKeys.execution.all() })}>Обновить</button>
        </>
      )}
    >
      <WorkersTabs active={tab} onSelect={openTab}>
        {account.isPending ? <LoadingState what="права доступа" /> : null}
        {accountFailure !== null ? (
          <div data-workers-account-failure={accountFailure.kind}>
            <ErrorState title="Права доступа не прочитаны" detail={accountFailure.detail} correlationId={accountFailure.correlationId} onRetry={() => void account.refetch()} />
          </div>
        ) : null}
        {account.data !== undefined && tab === 'overview' ? <ExecutorHostsOverview roles={roles} onShowServers={() => openTab('servers')} /> : null}
        {account.data !== undefined && tab === 'servers' ? <ExecutorHosts roles={roles} /> : null}
        {account.data !== undefined && tab === 'tasks' ? <ExecutorHostTasks roles={roles} /> : null}
        {account.data !== undefined && tab === 'models' ? <ExecutorStageModels roles={roles} /> : null}
      </WorkersTabs>
    </PageShell>
  );
}
