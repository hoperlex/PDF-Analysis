/**
 * ✓/✕ in a finding's row (`R-151n`): the original's quick accept and reject, as our journal records them.
 *
 * Pure markup. Each press is one decision event at once (the page connects it to `appendDecision`); there is no
 * client draft and no batch. The comment stays in the decision panel. A press that would repeat the finding's
 * current verdict is not offered, so a double press does not append a second identical event. The note under the
 * buttons is what happened to the last press: recorded, refused before sending, or failed with the server's reason.
 */

import type { Verdict } from '@/shared/api';

import styles from './finding-list.module.css';

export type RowIntent = 'accept' | 'reject';

export interface RowNote {
  readonly tone: 'ok' | 'fail';
  readonly text: string;
}

export interface FindingRowActionsProps {
  readonly verdict: Verdict;
  /** The press on its way, if any. */
  readonly sending: RowIntent | null;
  readonly note: RowNote | null;
  readonly onAccept: () => void;
  readonly onReject: () => void;
}

export function FindingRowActions({ verdict, sending, note, onAccept, onReject }: FindingRowActionsProps) {
  const busy = sending !== null;
  return (
    <div className={styles.rowActions} data-row-actions="">
      <button
        type="button"
        className={`am-button am-button--small ${styles.rowAccept}`}
        aria-label="Принять"
        aria-pressed={verdict === 'accepted'}
        title="Принять: замечание подтверждено"
        disabled={busy || verdict === 'accepted'}
        onClick={onAccept}
      >
        {sending === 'accept' ? '…' : '✓'}
      </button>
      <button
        type="button"
        className={`am-button am-button--small ${styles.rowReject}`}
        aria-label="Отклонить"
        aria-pressed={verdict === 'rejected'}
        title="Отклонить: замечание не подтверждено"
        disabled={busy || verdict === 'rejected'}
        onClick={onReject}
      >
        {sending === 'reject' ? '…' : '✕'}
      </button>
      {note === null ? null : (
        <span className={note.tone === 'ok' ? styles.rowNote : styles.rowNoteFail} role={note.tone === 'ok' ? 'status' : 'alert'}>
          {note.text}
        </span>
      )}
    </div>
  );
}
