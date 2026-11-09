'use client';

/**
 * «Удалить» (`HOSTS-WEB-01`): archives a server. One-way, so it asks once, in words, what it does: the server's token is
 * revoked, and the runs already bound to it finish as they can. The idempotency key belongs to the intent and is released when
 * the command settles.
 */

import { useState } from 'react';

import type { ExecutorHostId } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { hostFailure } from '@/entities/executor-host';
import { useCommandKey } from '@/features/manage-executor-connection';

import { DELETE_CANCEL_LABEL, DELETE_CONFIRM_LABEL, deleteQuestion } from '../model/words';
import { useArchiveExecutorHost } from '../model/use-manage-executor-host';
import { HostFailure } from './host-failure';

export interface DeleteHostViewProps {
  readonly name: string;
  readonly pending: boolean;
  readonly failure: ExecutionFailure | null;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}

export function DeleteHostView({ name, pending, failure, onConfirm, onCancel }: DeleteHostViewProps) {
  return (
    <section role="group" aria-label={`Удаление сервера ${name}`} data-host-delete>
      <p>{deleteQuestion(name)}</p>
      <div className="am-form__row">
        <button className="am-button" type="button" disabled={pending} data-host-delete-confirm onClick={onConfirm}>
          {DELETE_CONFIRM_LABEL}
        </button>
        <button className="am-button am-button--quiet" type="button" disabled={pending} onClick={onCancel}>
          {DELETE_CANCEL_LABEL}
        </button>
      </div>
      {failure === null ? null : <HostFailure failure={failure} />}
    </section>
  );
}

export interface DeleteHostControlProps {
  readonly hostId: ExecutorHostId;
  readonly name: string;
  readonly onClose: () => void;
}

export function DeleteHostControl({ hostId, name, onClose }: DeleteHostControlProps) {
  const archive = useArchiveExecutorHost();
  const keys = useCommandKey();
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);

  async function confirm() {
    setFailure(null);
    try {
      await archive.mutateAsync({ hostId, idempotencyKey: keys.keyFor(hostId) });
      keys.release();
      onClose();
    } catch (error) {
      const failed = hostFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  return (
    <DeleteHostView name={name} pending={archive.isPending} failure={failure} onConfirm={() => void confirm()} onCancel={onClose} />
  );
}
