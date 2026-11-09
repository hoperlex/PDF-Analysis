'use client';

/**
 * «Процессы» on the advanced page (`W54-WORKERS-WEB`, plan §3.7, moved by `HOSTS-WEB-01`): the registry of the worker
 * service that runs the stand's runs, since `W54-WORKER-01` in a separate process. Any account holding a role reads it
 * (`R-80`); an administrator may stop a worker taking new runs, or allow it again, after a confirmation step whose idempotency
 * key is minted once per intent and reused on an explicit repeat. The list refreshes itself under the operational-list policy
 * while the browser tab is visible, and says when it was last read.
 *
 * Moved, not rewritten: the intake switch works as it did on the tab.
 */

import { useRef, useState } from 'react';

import type { ExecutionWorker, Role } from '@/shared/api';
import { newIdempotencyKey } from '@/shared/api';
import { UpdateTime, executionFailure, useWorkers } from '@/entities/execution';
import type { ExecutionFailure } from '@/entities/execution';
import { useSetWorkerIntake } from '@/features/set-worker-intake';
import { WorkerList } from '@/widgets/worker-list';
import { ErrorState, LoadingState, UnsupportedState } from '@/shared/ui';

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

export function ProcessesSection({ roles }: { readonly roles: readonly Role[] }) {
  const [cursors, setCursors] = useState<string[]>([]);
  const [intent, setIntent] = useState<IntakeIntent | null>(noIntakeIntent);
  const [commandFailure, setCommandFailure] = useState<ExecutionFailure | null>(null);
  const [completed, setCompleted] = useState(false);
  const sequence = useRef(0);
  const cursor = cursors.at(-1);
  const workers = useWorkers(cursor, true);
  const intake = useSetWorkerIntake();
  const busy = intake.isPending;
  const readFailure = workers.error === null ? null : executionFailure(workers.error, false);
  const next = workers.data?.page.next_cursor ?? null;

  function select(worker: ExecutionWorker, enabled: boolean) {
    sequence.current += 1;
    setIntent({ worker, enabled, key: newIdempotencyKey() });
    setCommandFailure(null);
    setCompleted(false);
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
    <>
      <UpdateTime dataUpdatedAt={workers.dataUpdatedAt} failed={workers.isError} />
      {workers.isPending ? <LoadingState what="исполнителей" /> : null}
      {/*
        * A failed read with no data is «не прочитаны». A failed read after a successful one keeps the last list on screen under
        * the stale line (`UpdateTime`), as on the queue: a periodic read that blinked must not erase the registry; the failure
        * is still said, never swallowed.
        */}
      {readFailure === null ? null : (
        <div data-workers-read-failure={readFailure.kind}>
          <ErrorState title={workers.data === undefined ? 'Исполнители не прочитаны' : 'Исполнители не обновились'} detail={readFailure.detail} correlationId={readFailure.correlationId} onRetry={() => void workers.refetch()} />
        </div>
      )}
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
    </>
  );
}
