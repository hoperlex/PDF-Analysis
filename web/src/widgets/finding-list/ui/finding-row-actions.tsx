/**
 * The decision field of a finding (`R-151n`, `UIP-S06-02`): ✓ green, ✕ red and a one-line «Причина», as the original's row
 * has them, recorded as our journal records a decision.
 *
 * Pure markup around the entity's `DecisionReasonControl`; the same field stands in the table's «Решение» column, in a list
 * row and in the side column of the full-screen view, so the three places cannot drift apart. Each press is one decision
 * event at once (the page connects it to `appendDecision`) and the text of the field goes in that same event: there is no
 * client draft, no batch and no state between the press and the write. A press that would repeat the finding's current
 * verdict is not offered, so a double press does not append a second identical event. The line under the field is what
 * happened to the last press: recorded, refused before sending, or failed with the server's reason. The «Добавить
 * комментарий» of the decision panel is another command and is not here.
 *
 * The field is emptied from outside, by the row that owns the press: `recordedKey` changes when a press has been written,
 * and a changed key mounts the field afresh. Nothing else empties it -- a refusal before sending and a failure keep the
 * text, so the next press can send it again.
 */

import type { DecisionIntent, DecisionNote } from '@/entities/expert-decision';
import { DecisionReasonControl } from '@/entities/expert-decision';
import type { Verdict } from '@/shared/api';

import styles from './finding-list.module.css';

export type RowIntent = DecisionIntent;

export type RowNote = DecisionNote;

export interface FindingRowActionsProps {
  readonly verdict: Verdict;
  /** The press on its way, if any. */
  readonly sending: RowIntent | null;
  readonly note: RowNote | null;
  /** ✓. The argument is the field's text, trimmed; an empty string is no reason. */
  readonly onAccept: (reason: string) => void;
  /** ✕. Same argument as `onAccept`. */
  readonly onReject: (reason: string) => void;
  /** Changes when a press has been written: the field is emptied then and only then. Absent until the first write. */
  readonly recordedKey?: string | undefined;
}

export function FindingRowActions({ verdict, sending, note, onAccept, onReject, recordedKey }: FindingRowActionsProps) {
  return (
    <div className={styles.rowActions} data-row-actions="">
      <DecisionReasonControl
        key={recordedKey ?? ''}
        verdict={verdict}
        sending={sending}
        note={note}
        onAccept={onAccept}
        onReject={onReject}
      />
    </div>
  );
}
