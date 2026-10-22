'use client';

/**
 * «Архивировать» (`archiveExecutorConnection`, `EXEC-HTTP-01`).
 *
 * Asks first (`C-24`): an archived connection cannot be probed, routed or given a key, and a
 * connection a route still names is refused by the server (`connection_routed`). Nothing is
 * sent until the confirmation is pressed.
 */

import { useState } from 'react';

import type { ExecutorConnectionId } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { connectionFailure } from '@/entities/executor-connection';

import { useCommandKey } from '../model/use-command-key';
import { useArchiveExecutorConnection } from '../model/use-manage-executor-connection';
import { CommandFailure } from './command-failure';

export interface ArchiveControlProps {
  readonly connectionId: ExecutorConnectionId;
  readonly name: string;
}

export function ArchiveControl({ connectionId, name }: ArchiveControlProps) {
  const archive = useArchiveExecutorConnection();
  const keys = useCommandKey();
  const [asking, setAsking] = useState(false);
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);

  async function confirm() {
    setFailure(null);
    try {
      await archive.mutateAsync({ connectionId, idempotencyKey: keys.keyFor(connectionId) });
      keys.release();
      setAsking(false);
    } catch (error) {
      const failed = connectionFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  return (
    <>
      {asking ? (
        <div role="group" aria-label="Подтверждение архивирования подключения">
          <p className="am-note">
            Архивировать подключение «{name}»? Его нельзя будет проверить, назначить или дополнить
            ключом. Подключение, на которое ещё указывает назначение, архивировать нельзя.
          </p>
          <button className="am-button" type="button" disabled={archive.isPending} onClick={() => void confirm()}>
            {failure?.kind === 'unknown_outcome' ? 'Повторить с тем же ключом' : 'Подтвердить архивирование'}
          </button>{' '}
          <button
            className="am-button am-button--quiet"
            type="button"
            disabled={archive.isPending}
            onClick={() => { setAsking(false); setFailure(null); keys.release(); }}
          >
            Отмена
          </button>
        </div>
      ) : (
        <button className="am-button am-button--quiet" type="button" onClick={() => setAsking(true)}>
          Архивировать
        </button>
      )}
      {failure !== null ? <CommandFailure failure={failure} /> : null}
    </>
  );
}
