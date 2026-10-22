'use client';

/**
 * `/workers` — «Исполнители» (`W54-WORKERS-WEB`, plan §3.7; the tabs `EXEC-HTTP-01`).
 *
 * Three tabs. «Процессы» is the screen as `W54-WORKERS-WEB` graduated it from the W43
 * placeholder: since `W54-WORKER-01` runs execute in a separate worker service and
 * `listWorkers` answers its registry. Any account holding a role reads it (`R-80`); an
 * administrator may stop a worker taking new runs, or allow it again, after a confirmation
 * step whose idempotency key is minted once per intent and reused on an explicit repeat.
 * «Подключения» lists where the stand sends model work and lets an administrator manage it;
 * «Назначения» names the connection that serves each kind of model work.
 *
 * The screen opens on «Процессы», as it always has, unless the address names a tab (`?tab=`):
 * the redirect from the key form names «Подключения». Refreshed on tab return, after a command,
 * and by «Обновить», which reads again whatever the open tab shows.
 *
 * The key form arrives as a prop: it is a server component rendered by the route, so the key
 * never becomes a JavaScript value (`features/set-executor-secret`).
 */

import { useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import type { ReactNode } from 'react';

import type { ExecutionWorker } from '@/shared/api';
import { newIdempotencyKey, queryKeys } from '@/shared/api';
import { useMe } from '@/entities/account';
import { executionFailure, useWorkers } from '@/entities/execution';
import type { ExecutionFailure } from '@/entities/execution';
import { useSetWorkerIntake } from '@/features/set-worker-intake';
import { ExecutorConnections } from '@/widgets/executor-connections';
import { ExecutorRoutes } from '@/widgets/executor-routes';
import { WorkerList } from '@/widgets/worker-list';
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
  const workers = useWorkers(cursor);
  const account = useMe();
  const client = useQueryClient();
  const intake = useSetWorkerIntake();
  const busy = intake.isPending;
  const roles = account.data?.roles ?? [];
  const readFailure = workers.error === null ? null : executionFailure(workers.error, false);
  const accountFailure = account.error === null ? null : executionFailure(account.error, false);
  const next = workers.data?.page.next_cursor ?? null;

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

  return (
    <PageShell
      title="Исполнители"
      subtitle="Подключения к моделям, процессы, которые выполняют прогоны, и назначения. Данные обновляются при возврате на вкладку, после команды и по запросу."
      actions={<button className="am-button am-button--quiet" type="button" onClick={() => void client.invalidateQueries({ queryKey: queryKeys.execution.all() })}>Обновить</button>}
    >
      <WorkersTabs active={tab} onSelect={openTab}>
      {tab === 'connections' ? (
        <ExecutorConnections roles={roles} secretConnectionId={secretConnectionId} secretForm={secretForm} />
      ) : null}
      {tab === 'routes' ? <ExecutorRoutes roles={roles} /> : null}
      {tab === 'processes' ? (<>
      {account.isPending ? <LoadingState what="права на управление исполнителями" /> : null}
      {accountFailure !== null ? (
        <div data-workers-account-failure={accountFailure.kind}>
          <p role="status" className="am-note" data-workers-controls-withheld>Исполнители показаны без команд: права не прочитаны.</p>
          <ErrorState title="Права на управление исполнителями не прочитаны" detail={accountFailure.detail} correlationId={accountFailure.correlationId} onRetry={() => void account.refetch()} />
        </div>
      ) : null}
      {workers.isPending ? <LoadingState what="исполнителей" /> : null}
      {readFailure !== null ? (
        <div data-workers-read-failure={readFailure.kind}>
          <ErrorState title="Исполнители не прочитаны" detail={readFailure.detail} correlationId={readFailure.correlationId} onRetry={() => void workers.refetch()} />
        </div>
      ) : null}
      {/*
        * As on the queue (`C-27`): the rows do not wait for `getMe`. Until the roles are
        * read, or when that read fails, `roles` is empty and no switch is drawn.
        */}
      {workers.data !== undefined && readFailure === null ? (
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
