'use client';

/**
 * `/workers` — «Исполнители» (`W54-WORKERS-WEB`, plan §3.7; the tabs `EXEC-HTTP-01`).
 *
 * Six tabs. «Обзор» (`UI-PARITY` UI-B-63, UI-B-64) is the first: the tiles and the queue line that sat over
 * «Процессы», each tile linking to the tab or the screen it summarises. «Процессы» is the screen as
 * `W54-WORKERS-WEB` graduated it from the W43 placeholder: since `W54-WORKER-01` runs execute in a separate worker service and
 * `listWorkers` answers its registry. Any account holding a role reads it (`R-80`); an
 * administrator may stop a worker taking new runs, or allow it again, after a confirmation
 * step whose idempotency key is minted once per intent and reused on an explicit repeat.
 * «Подключения» lists where the stand sends model work and lets an administrator manage it;
 * «Назначения» names the connection that serves each kind of model work.
 *
 * `EXEC2-WEB-GROUPS-01` (ADR-0026 decisions 10, 11 and 17): «Группы» holds the homogeneous groups of
 * interchangeable executors, with their capacity; «Правила» holds the six rules that point a kind of
 * model work at a group, the routing mode, and the cut-over from the legacy routes. The legacy routes
 * of «Назначения» are drawn read-only inside «Правила» while the mode is `legacy` (the slot below), and
 * become history on their own tab once rules are in force.
 *
 * The screen opens on «Процессы», as it always has, unless the address names a tab (`?tab=`):
 * the redirect from the key form names «Подключения», a link to the overview names `overview`. The overview and the
 * worker list of «Процессы» refresh themselves under the operational-list policy (`OPERATIONAL_LIST_POLLING`,
 * `web/docs/PC01_UI_SEAM.md` §7.1) while the browser tab is visible, as the queue and the journal do, and says when it was last
 * read («Обновлено ЧЧ:ММ:СС», or that the data may be out of date). Everything is also refreshed on
 * tab return, after a command, and by «Обновить», which reads again whatever the open tab shows.
 *
 * The key form arrives as a prop: it is a server component rendered by the route, so the key
 * never becomes a JavaScript value (`features/set-executor-secret`).
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import type { ReactNode } from 'react';

import type { ExecutionWorker } from '@/shared/api';
import { newIdempotencyKey, queryKeys } from '@/shared/api';
import { useMe } from '@/entities/account';
import { UpdateTime, executionFailure, queueQueryOptions, useWorkers, workersOverview } from '@/entities/execution';
import type { ExecutionFailure } from '@/entities/execution';
import { useSetWorkerIntake } from '@/features/set-worker-intake';
import { ExecutorConnections } from '@/widgets/executor-connections';
import { ExecutorGroups } from '@/widgets/executor-groups';
import { ExecutorRoutes } from '@/widgets/executor-routes';
import { ExecutorRules } from '@/widgets/executor-rules';
import { WorkerList, WorkersOverviewSections, WorkersOverviewView } from '@/widgets/worker-list';
import { ErrorState, LoadingState, PageShell, UnsupportedState } from '@/shared/ui';

import { DEFAULT_WORKERS_TAB, WORKERS_TAB_PARAM } from '../model/tabs';
import type { WorkersTab } from '../model/tabs';
import { WorkersTabs } from './workers-tabs';

export interface WorkersPageProps {
  /** The tab the address named; the screen opens on «Процессы» when it names none. */
  readonly initialTab?: WorkersTab | undefined;
  /** The connection the key form was opened for, from the address. */
  readonly secretConnectionId?: string | null | undefined;
  /** The server-rendered key form for `secretConnectionId`. */
  readonly secretForm?: ReactNode | undefined;
}

export interface IntakeIntent {
  readonly worker: ExecutionWorker;
  readonly enabled: boolean;
  readonly key: string;
}

/** The lazy initial value of the pending intent. Exported so a test can seed a confirmation. */
export function noIntakeIntent(): IntakeIntent | null {
  return null;
}

export function intakeIntentLabel(intent: IntakeIntent): string {
  return intent.enabled
    ? `Разрешить исполнителю ${intent.worker.worker_id} брать новые прогоны?`
    : `Запретить исполнителю ${intent.worker.worker_id} брать новые прогоны? Прогоны, которые он уже выполняет, он доведёт до конца.`;
}

/** A definite refusal: the server answered and nothing changed, so no retry will help. */
function refused(failure: ExecutionFailure): boolean {
  return ['permission', 'transition', 'conflict', 'refusal'].includes(failure.kind);
}

export function WorkersPage({ initialTab, secretConnectionId = null, secretForm }: WorkersPageProps = {}) {
  const [tab, setTab] = useState<WorkersTab>(initialTab ?? DEFAULT_WORKERS_TAB);
  const [cursors, setCursors] = useState<string[]>([]);
  const [intent, setIntent] = useState<IntakeIntent | null>(noIntakeIntent);
  const [commandFailure, setCommandFailure] = useState<ExecutionFailure | null>(null);
  const [completed, setCompleted] = useState(false);
  const sequence = useRef(0);
  const cursor = cursors.at(-1);
  // The list is read, and polled, only while a tab that shows it is open: «Процессы» pages through it, «Обзор» counts
  // the first page.
  const workers = useWorkers(tab === 'processes' ? cursor : undefined, tab === 'processes' || tab === 'overview');
  const account = useMe();
  const client = useQueryClient();
  const intake = useSetWorkerIntake();
  const busy = intake.isPending;
  const roles = account.data?.roles ?? [];
  const readFailure = workers.error === null ? null : executionFailure(workers.error, false);
  const accountFailure = account.error === null ? null : executionFailure(account.error, false);
  const next = workers.data?.page.next_cursor ?? null;
  // M-17 (`R-151t`): the queue's counts for the overview tiles and line, read only while «Обзор» is open.
  const queue = useQuery({ ...queueQueryOptions(undefined, {}), enabled: tab === 'overview' });
  const queueFailure = queue.error === null ? null : executionFailure(queue.error, false);

  function select(worker: ExecutionWorker, enabled: boolean) {
    sequence.current += 1;
    setIntent({ worker, enabled, key: newIdempotencyKey() });
    setCommandFailure(null);
    setCompleted(false);
  }

  /** A tab is a place in the address, so a reload or a shared link comes back to it. */
  function openTab(next: WorkersTab) {
    setTab(next);
    try {
      window.history.replaceState(null, '', `?${WORKERS_TAB_PARAM}=${next}`);
    } catch {
      // No history to write (a preview, a sandboxed frame): the tab still changes.
    }
  }

  async function execute(chosen: IntakeIntent) {
    const mine = sequence.current;
    try {
      await intake.mutateAsync({
        workerId: chosen.worker.worker_id, enabled: chosen.enabled, idempotencyKey: chosen.key,
      });
      if (mine !== sequence.current) return;
      setCommandFailure(null);
      setCompleted(true);
      setIntent(null);
    } catch (error) {
      if (mine !== sequence.current) return;
      setCommandFailure(executionFailure(error, true));
      setCompleted(false);
    }
  }

  // What «Обзор» and «Процессы» both say about the read of the registry.
  const updateTime = <UpdateTime dataUpdatedAt={workers.dataUpdatedAt} failed={workers.isError} />;
  const workersLoading = workers.isPending ? <LoadingState what="исполнителей" /> : null;
  /*
   * A failed read with no data is «не прочитаны». A failed read after a successful one keeps
   * the last list on screen under the stale line (`UpdateTime`), as on the queue: a periodic
   * read that blinked must not erase the registry; the failure is still said, never swallowed.
   */
  const workersFailure = readFailure === null ? null : (
    <div data-workers-read-failure={readFailure.kind}>
      <ErrorState title={workers.data === undefined ? 'Исполнители не прочитаны' : 'Исполнители не обновились'} detail={readFailure.detail} correlationId={readFailure.correlationId} onRetry={() => void workers.refetch()} />
    </div>
  );

  return (
    <PageShell
      title="Исполнители"
      subtitle="Обзор исполнителей и очереди, подключения к моделям, процессы, которые выполняют прогоны, группы исполнителей, правила и назначения. Обзор и список процессов обновляются автоматически, пока вкладка открыта; остальные данные — при возврате на вкладку, после команды и по запросу."
      actions={<button className="am-button am-button--quiet" type="button" onClick={() => void client.invalidateQueries({ queryKey: queryKeys.execution.all() })}>Обновить</button>}
    >
      <WorkersTabs active={tab} onSelect={openTab}>
        {tab === 'overview' ? (<>
        {updateTime}
        {workersLoading}
        {workersFailure}
        {workers.data !== undefined ? (
          <WorkersOverviewView
            workers={workersOverview(workers.data.items, next !== null)}
            queue={queue.data?.overview}
            processesHref={`?${WORKERS_TAB_PARAM}=processes`}
            onOpenProcesses={() => openTab('processes')}
          />
        ) : null}
        {/* The servers, the nearest queued jobs and what needs attention, from the two first pages the tiles already read. */}
        {workers.data !== undefined ? (
          <WorkersOverviewSections
            workers={workers.data.items}
            workersPartial={next !== null}
            jobs={queue.data?.items}
            jobsPartial={(queue.data?.page.next_cursor ?? null) !== null}
            processesHref={`?${WORKERS_TAB_PARAM}=processes`}
            onOpenProcesses={() => openTab('processes')}
          />
        ) : null}
        {/* The queue's figures are read apart from the registry's, so a failed queue read leaves the servers on screen and says so. */}
        {queue.isPending ? <LoadingState what="очередь" /> : null}
        {queueFailure !== null ? (
          <div data-workers-queue-failure={queueFailure.kind}>
            <ErrorState title={queue.data === undefined ? 'Очередь не прочитана' : 'Очередь не обновилась'} detail={queueFailure.detail} correlationId={queueFailure.correlationId} onRetry={() => void queue.refetch()} />
          </div>
        ) : null}
        </>) : null}
        {tab === 'connections' ? (
          <ExecutorConnections roles={roles} secretConnectionId={secretConnectionId} secretForm={secretForm} />
        ) : null}
        {tab === 'groups' ? <ExecutorGroups roles={roles} /> : null}
        {tab === 'rules' ? <ExecutorRules roles={roles} legacyRoutes={<ExecutorRoutes roles={roles} history />} /> : null}
        {tab === 'routes' ? <ExecutorRoutes roles={roles} /> : null}
        {tab === 'processes' ? (<>
        {updateTime}
        {account.isPending ? <LoadingState what="права на управление исполнителями" /> : null}
        {accountFailure !== null ? (
          <div data-workers-account-failure={accountFailure.kind}>
            <p role="status" className="am-note" data-workers-controls-withheld>Исполнители показаны без команд: права не прочитаны.</p>
            <ErrorState title="Права на управление исполнителями не прочитаны" detail={accountFailure.detail} correlationId={accountFailure.correlationId} onRetry={() => void account.refetch()} />
          </div>
        ) : null}
        {workersLoading}
        {workersFailure}
        {/*
          * As on the queue (`C-27`): the rows do not wait for `getMe`. Until the roles are
          * read, or when that read fails, `roles` is empty and no switch is drawn.
          */}
        {workers.data !== undefined ? (
          <WorkerList
            items={workers.data.items}
            roles={roles}
            busy={busy}
            onIntake={select}
            onPrevious={cursors.length === 0 ? null : () => setCursors((current) => current.slice(0, -1))}
            onNext={next === null ? null : () => setCursors((current) => [...current, next])}
          />
        ) : null}
        {intent !== null ? (
          <section role="group" aria-label="Подтверждение команды исполнителю" data-workers-intent={intent.enabled ? 'allow' : 'stop'}>
            <p>{intakeIntentLabel(intent)}</p>
            <button type="button" className="am-button" disabled={busy || (commandFailure !== null && commandFailure.kind !== 'unknown_outcome')} onClick={() => void execute(intent)}>
              {commandFailure?.kind === 'unknown_outcome' ? 'Повторить с тем же ключом' : 'Подтвердить'}
            </button>{' '}
            <button type="button" className="am-button am-button--quiet" disabled={busy} onClick={() => { sequence.current += 1; setIntent(null); setCommandFailure(null); }}>Отмена</button>
          </section>
        ) : null}
        {commandFailure !== null ? (
          <div data-workers-action-failure={commandFailure.kind}>
            {refused(commandFailure) ? (
              <>
                <UnsupportedState title="Команда исполнителю отклонена" detail={commandFailure.detail} />
                {commandFailure.correlationId !== null
                  ? <p>Идентификатор корреляции <code>{commandFailure.correlationId}</code></p>
                  : null}
              </>
            ) : (
              <ErrorState title={commandFailure.kind === 'unknown_outcome' ? 'Исход команды исполнителю неизвестен' : 'Команда исполнителю не выполнена'} detail={commandFailure.detail} correlationId={commandFailure.correlationId} />
            )}
          </div>
        ) : null}
        {completed ? <p role="status" className="am-note">Команда исполнителю выполнена.</p> : null}
        </>) : null}
      </WorkersTabs>
    </PageShell>
  );
}
