'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';

import type { ExecutionQueueItem, RunStatus } from '@/shared/api';
import { newIdempotencyKey } from '@/shared/api';
import { routes } from '@/shared/lib';
import { useMe } from '@/entities/account';
import { canExecute, executionFailure, useExecutionQueue } from '@/entities/execution';
import type { ExecutionFailure } from '@/entities/execution';
import { useCancelRun } from '@/features/cancel-run';
import { useReauditRun } from '@/features/reaudit-run';
import { useSetJobPriority } from '@/features/set-job-priority';
import { usePauseExecution } from '@/features/pause-execution';
import { ExecutionQueue } from '@/widgets/execution-queue';
import { ErrorState, LoadingState, PageShell, UnsupportedState } from '@/shared/ui';

interface RunIntent {
  readonly kind: 'cancel' | 'reaudit';
  readonly item: ExecutionQueueItem;
  readonly key: string;
}

interface PriorityIntent {
  readonly kind: 'priority';
  readonly item: ExecutionQueueItem;
  readonly priority: number;
  readonly key: string;
}

interface PauseIntent {
  readonly kind: 'pause';
  readonly paused: boolean;
  readonly key: string;
}

type Intent = RunIntent | PriorityIntent | PauseIntent;
type NewIntent =
  | { readonly kind: 'cancel' | 'reaudit'; readonly item: ExecutionQueueItem }
  | { readonly kind: 'priority'; readonly item: ExecutionQueueItem; readonly priority: number }
  | { readonly kind: 'pause'; readonly paused: boolean };

export function intentLabel(intent: Intent): string {
  switch (intent.kind) {
    case 'cancel': return `Отменить прогон ${intent.item.run_id}?`;
    case 'reaudit': return `Начать повторный аудит прогона ${intent.item.run_id}?`;
    case 'priority': return `Установить приоритет ${intent.priority} для прогона ${intent.item.run_id}?`;
    case 'pause': return intent.paused ? 'Приостановить выдачу задач?' : 'Возобновить выдачу задач?';
  }
}

export function QueuePage() {
  const [cursors, setCursors] = useState<string[]>([]);
  const [intent, setIntent] = useState<Intent | null>(null);
  const [commandFailure, setCommandFailure] = useState<ExecutionFailure | null>(null);
  const [lastRun, setLastRun] = useState<RunStatus | null>(null);
  const [completed, setCompleted] = useState(false);
  const [asOf, setAsOf] = useState<number | null>(null);
  const sequence = useRef(0);
  const cursor = cursors.at(-1);
  const queue = useExecutionQueue(cursor);
  const account = useMe();
  const cancel = useCancelRun();
  const reaudit = useReauditRun();
  const priority = useSetJobPriority();
  const pause = usePauseExecution();
  const busy = cancel.isPending || reaudit.isPending || priority.isPending || pause.isPending;
  const roles = account.data?.roles ?? [];
  const readFailure = queue.error === null ? null : executionFailure(queue.error, false);
  const accountFailure = account.error === null ? null : executionFailure(account.error, false);
  const next = queue.data?.page.next_cursor ?? null;

  useEffect(() => {
    const refreshAge = () => setAsOf(Date.now());
    refreshAge();
    window.addEventListener('focus', refreshAge);
    return () => window.removeEventListener('focus', refreshAge);
  }, []);

  function select(nextIntent: NewIntent) {
    sequence.current += 1;
    setIntent({ ...nextIntent, key: newIdempotencyKey() });
    setCommandFailure(null);
    setCompleted(false);
    setLastRun(null);
  }

  async function execute(chosen: Intent) {
    const mine = sequence.current;
    try {
      let run: RunStatus | null = null;
      switch (chosen.kind) {
        case 'cancel': run = await cancel.mutateAsync({ runId: chosen.item.run_id, idempotencyKey: chosen.key }); break;
        case 'reaudit': run = await reaudit.mutateAsync({ runId: chosen.item.run_id, idempotencyKey: chosen.key }); break;
        case 'priority': await priority.mutateAsync({
          jobId: chosen.item.job_id, priority: chosen.priority,
          idempotencyKey: chosen.key,
        }); break;
        case 'pause': await pause.mutateAsync({ paused: chosen.paused, idempotencyKey: chosen.key }); break;
      }
      if (mine !== sequence.current) return;
      setLastRun(run);
      setCommandFailure(null);
      setCompleted(true);
      setIntent(null);
      setCursors([]);
    } catch (error) {
      if (mine !== sequence.current) return;
      setCommandFailure(executionFailure(error, true));
      setCompleted(false);
    }
  }

  return (
    <PageShell
      title="Очередь"
      subtitle="Устойчивые задачи прогонов. Данные обновляются при возврате на вкладку и по запросу."
      actions={<button className="am-button am-button--quiet" type="button" onClick={() => { setAsOf(Date.now()); void queue.refetch(); }}>Обновить</button>}
    >
      {readFailure === null && queue.data?.paused === true ? <p role="status" className="am-note" data-execution-paused>Выдача задач приостановлена.</p> : null}
      {readFailure === null && account.data !== undefined && canExecute(roles, 'pause') && queue.data !== undefined ? (
        <button
          type="button"
          className="am-button am-button--quiet"
          disabled={busy}
          onClick={() => select({ kind: 'pause', paused: !queue.data.paused })}
        >
          {queue.data.paused ? 'Возобновить выдачу' : 'Приостановить выдачу'}
        </button>
      ) : null}
      {account.isPending ? <LoadingState what="права на управление очередью" /> : null}
      {accountFailure !== null ? <div data-execution-account-failure={accountFailure.kind}><ErrorState title="Права не прочитаны" detail={accountFailure.detail} correlationId={accountFailure.correlationId} onRetry={() => void account.refetch()} /></div> : null}
      {queue.isPending ? <LoadingState what="очередь" /> : null}
      {readFailure !== null ? <div data-execution-read-failure={readFailure.kind}><ErrorState title="Очередь не открылась" detail={readFailure.detail} correlationId={readFailure.correlationId} onRetry={() => void queue.refetch()} /></div> : null}
      {queue.data !== undefined && readFailure === null && account.data !== undefined ? (
        <ExecutionQueue
          items={queue.data.items}
          roles={roles}
          asOf={asOf}
          busy={busy}
          onCancel={(item) => select({ kind: 'cancel', item })}
          onReaudit={(item) => select({ kind: 'reaudit', item })}
          onPriority={(item, value) => select({ kind: 'priority', item, priority: value })}
          onPrevious={cursors.length === 0 ? null : () => setCursors((current) => current.slice(0, -1))}
          onNext={next === null ? null : () => setCursors((current) => [...current, next])}
        />
      ) : null}
      {intent !== null ? (
        <section role="group" aria-label="Подтверждение команды выполнения" data-execution-intent={intent.kind}>
          <p>{intentLabel(intent)}</p>
          <button type="button" className="am-button" disabled={busy || (commandFailure !== null && commandFailure.kind !== 'unknown_outcome')} onClick={() => void execute(intent)}>
            {commandFailure?.kind === 'unknown_outcome' ? 'Повторить с тем же ключом' : 'Подтвердить'}
          </button>{' '}
          <button type="button" className="am-button am-button--quiet" disabled={busy} onClick={() => { sequence.current += 1; setIntent(null); setCommandFailure(null); }}>Отмена</button>
        </section>
      ) : null}
      {commandFailure !== null ? (
        <div data-execution-action-failure={commandFailure.kind}>
          {commandFailure.kind === 'permission' || commandFailure.kind === 'transition' || commandFailure.kind === 'conflict' ? (
            <UnsupportedState title="Команда отклонена" detail={commandFailure.kind === 'transition' && intent?.kind === 'cancel' ? 'Текущее состояние сохранено. Отмена на этапе проверки недоступна.' : commandFailure.detail} />
          ) : (
            <ErrorState title={commandFailure.kind === 'unknown_outcome' ? 'Исход команды неизвестен' : 'Команда не выполнена'} detail={commandFailure.detail} correlationId={commandFailure.correlationId} />
          )}
          {['permission', 'transition', 'conflict'].includes(commandFailure.kind) &&
          commandFailure.correlationId !== null
            ? <p>Идентификатор корреляции <code>{commandFailure.correlationId}</code></p>
            : null}
        </div>
      ) : null}
      {completed ? <p role="status" className="am-note">Команда выполнена.</p> : null}
      {lastRun !== null ? <p><Link href={routes.run(lastRun.project_uid, lastRun.run_id)}>Открыть прогон {lastRun.run_id}</Link></p> : null}
    </PageShell>
  );
}
