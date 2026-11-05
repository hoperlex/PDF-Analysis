'use client';

/**
 * `UI-A-62`: «Отменить» on the run page, as the original's stop button beside a running audit. A run that
 * has not ended can be cancelled by an expert or an administrator (`cancelRun`, the same sets the queue
 * uses); the screen asks once more before it sends, and one intent carries one idempotency key, so a
 * double press or a retry after a network error is the same command. A viewer, and anyone once the run
 * has ended, sees nothing here. While the account is not known yet the control stays drawn and the server
 * answers for itself.
 */

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import type { RunId, RunState } from '@/shared/api';
import { failureMessage } from '@/shared/api';
import { useIntentKey } from '@/shared/lib';
import { useMe } from '@/entities/account';
import { runStatusQueryOptions } from '@/entities/audit-run';

import { useCancelRun } from '../model/use-cancel-run';

const ENDED: ReadonlySet<RunState> = new Set<RunState>(['published', 'partial', 'failed', 'cancelled']);

/** A run that has not ended may be cancelled; an ended one may not. */
export function cancellable(state: RunState | undefined): boolean {
  return state !== undefined && !ENDED.has(state);
}

/** The roles `cancelRun` admits; an unknown account is left to the server. */
export function mayCancel(roles: readonly string[] | undefined): boolean {
  return roles === undefined || roles.includes('expert') || roles.includes('admin');
}

export function CancelRunControl({ runId }: { readonly runId: string }) {
  const me = useMe();
  const run = useQuery(runStatusQueryOptions(runId as RunId));
  const cancel = useCancelRun();
  const [confirming, setConfirming] = useState(false);
  const key = useIntentKey(`cancel:${runId}`);

  if (!mayCancel(me.data?.roles) || !cancellable(run.data?.state)) return null;

  if (!confirming) {
    return (
      <button type="button" className="am-button am-button--quiet" data-run-cancel="offer" onClick={() => setConfirming(true)}>
        Отменить прогон
      </button>
    );
  }
  return (
    <div className="am-form__field" role="group" aria-label="Отмена прогона" data-run-cancel="confirm">
      <p className="am-note">Прогон будет остановлен. Уже потраченные вызовы модели не возвращаются.</p>
      <div>
        <button
          type="button"
          className="am-button"
          disabled={cancel.isPending}
          onClick={() => {
            cancel.mutate({ runId, idempotencyKey: key }, { onSuccess: () => setConfirming(false) });
          }}
        >
          Подтвердить отмену
        </button>{' '}
        <button type="button" className="am-button am-button--quiet" disabled={cancel.isPending} onClick={() => setConfirming(false)}>
          Не отменять
        </button>
      </div>
      {cancel.error === null ? null : (
        <p className="am-note" role="alert">
          Прогон не отменён: {failureMessage(cancel.error)}
        </p>
      )}
    </div>
  );
}
