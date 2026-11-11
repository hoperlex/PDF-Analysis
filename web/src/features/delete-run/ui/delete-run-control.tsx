'use client';

/**
 * `RUN-DELETE-01`: «Удалить прогон» — the run leaves every list, its findings and the expert's decisions stay stored.
 *
 * Offered only for a run that ended without a clean result (`partial`, `failed`, `cancelled`) and only to an expert or an
 * administrator, the roles that may cancel it; anyone else, and every other state, sees nothing. Deleting asks once, in words, what
 * it does; one intent carries one idempotency key, so a double press or a retry after a network error is the same command.
 *
 * Two places use it. The run page does not know the state in advance and reads it from the run's status (the cache the page already
 * fills); a row of the list passes the state it already has (`state`), so a list of fifty rows reads nothing more. While the account
 * is not known yet the control stays drawn and the server answers for itself, as the cancel control does.
 */

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import type { RunId, RunState, RunStatus } from '@/shared/api';
import { useIntentKey } from '@/shared/lib';
import { useMe } from '@/entities/account';
import { runStatusQueryOptions } from '@/entities/audit-run';

import { deleteFailureText } from '../model/failure';
import { deletable, mayDelete } from '../model/deletable';
import { useDeleteRun } from '../model/use-delete-run';
import {
  DELETE_RUN_CANCEL,
  DELETE_RUN_CONFIRM,
  DELETE_RUN_DONE,
  DELETE_RUN_NOTE,
  DELETE_RUN_OFFER,
  DELETE_RUN_OFFER_SHORT,
  DELETE_RUN_QUESTION,
} from '../model/words';

import styles from './delete-run-control.module.css';

export interface DeleteRunConfirmProps {
  readonly pending: boolean;
  /** The sentence of a refused or failed command, or `null`. */
  readonly failure: string | null;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}

/** The open confirmation. Drawn from plain data, so a test and a preview can show it as the screen does. */
export function DeleteRunConfirm({ pending, failure, onConfirm, onCancel }: DeleteRunConfirmProps) {
  return (
    <div className={styles.confirm} role="group" aria-label="Удаление прогона" data-run-delete="confirm">
      <p className={styles.question}>{DELETE_RUN_QUESTION}</p>
      <p className={styles.note}>{DELETE_RUN_NOTE}</p>
      <div className={styles.buttons}>
        <button type="button" className="am-button am-button--small" disabled={pending} data-run-delete-confirm="" onClick={onConfirm}>
          {DELETE_RUN_CONFIRM}
        </button>
        <button type="button" className="am-button am-button--quiet am-button--small" disabled={pending} onClick={onCancel}>
          {DELETE_RUN_CANCEL}
        </button>
      </div>
      {failure === null ? null : (
        <p className={styles.note} role="alert" data-run-delete-failure="">
          {failure}
        </p>
      )}
    </div>
  );
}

export interface DeleteRunControlProps {
  readonly runId: string;
  /** The state the screen already has (a row of the list). Absent, the run's status is read (the run page). */
  readonly state?: RunState | undefined;
  /** A row of the list: the short word «Удалить» and a small button. */
  readonly compact?: boolean | undefined;
  /** Called with the server's answer once the run is deleted; the run page leaves for the version from here. */
  readonly onDeleted?: ((run: RunStatus) => void) | undefined;
  /** Test seam: the control starts with the confirmation open. */
  readonly initiallyConfirming?: boolean | undefined;
}

export function DeleteRunControl({ runId, state, compact = false, onDeleted, initiallyConfirming = false }: DeleteRunControlProps) {
  const me = useMe();
  const status = useQuery({ ...runStatusQueryOptions(runId as RunId), enabled: state === undefined });
  const remove = useDeleteRun();
  const [confirming, setConfirming] = useState(initiallyConfirming);
  const key = useIntentKey(`delete:${runId}`);

  if (!mayDelete(me.data?.roles) || !deletable(state ?? status.data?.state)) return null;

  if (remove.isSuccess) {
    return <span className={styles.done} role="status" data-run-delete="done">{DELETE_RUN_DONE}</span>;
  }

  if (!confirming) {
    return (
      <button
        type="button"
        className={compact ? 'am-button am-button--quiet am-button--small' : 'am-button am-button--quiet'}
        data-run-delete="offer"
        onClick={() => setConfirming(true)}
      >
        {compact ? DELETE_RUN_OFFER_SHORT : DELETE_RUN_OFFER}
      </button>
    );
  }
  return (
    <DeleteRunConfirm
      pending={remove.isPending}
      failure={remove.error === null ? null : deleteFailureText(remove.error)}
      onConfirm={() => remove.mutate({ runId, idempotencyKey: key }, { onSuccess: (run) => onDeleted?.(run) })}
      onCancel={() => { remove.reset(); setConfirming(false); }}
    />
  );
}
