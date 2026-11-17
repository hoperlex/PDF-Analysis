'use client';

/** @jsxRuntime automatic */

/**
 * The decision field of a finding (`R-151n`, `UIP-S06-02`, `UIP-S06-08`): ✓ green, ✕ red and a one-line «Причина», as the original's
 * row has them, recorded as our journal records a decision, and, for a finding whose severity the model proposed, the choice
 * «Критичность» beside ✓.
 *
 * Pure markup around the entity's `DecisionReasonControl`; the same field stands in the table's «Решение» column, in a list
 * row and in the side column of the full-screen view, so the three places cannot drift apart. Each press is one decision
 * event at once (the page connects it to `appendDecision`) and the text of the field goes in that same event: there is no
 * client draft, no batch and no state between the press and the write. A press that would repeat the finding's current
 * verdict is not offered, so a double press does not append a second identical event. The line under the field is what
 * happened to the last press: recorded, refused before sending, or failed with the server's reason. The «Добавить
 * комментарий» of the decision panel is another command and is not here.
 *
 * **The choice of severity (`UIP-S06-08`, `R-151j`).** The model's proposal is not the expert's decision, so the select starts
 * empty, with an empty first item, and the proposal is never put into it; the row hands the select its value and takes the choice
 * back, and ✓ sends it in the same event as the reason. A finding the model proposed no severity for has no select. Whether ✓ may go
 * without a choice is not decided here: that rule belongs to `features/record-verdict`, which refuses in words, and this file
 * shows its sentence in the row's own line. The select is held while a press is on its way and once the finding is accepted (✓ is
 * not offered then), and it still reads the severity the expert chose.
 *
 * The field is emptied from outside, by the row that owns the press: `recordedKey` changes when a press has been written,
 * and a changed key mounts the field afresh. Nothing else empties it -- a refusal before sending and a failure keep the
 * text, so the next press can send it again.
 */

import type { DecisionIntent, DecisionNote } from '@/entities/expert-decision';
import { DecisionReasonControl } from '@/entities/expert-decision';
import { SEVERITY_LABELS } from '@/entities/finding';
import type { Severity, Verdict } from '@/shared/api';
import { SEVERITY_VALUES } from '@/shared/api';

import styles from './finding-list.module.css';

export type RowIntent = DecisionIntent;

export type RowNote = DecisionNote;

/** The expert's choice of severity beside ✓: its value (empty until chosen) and how the row takes a change back. */
export interface RowSeverityChoice {
  /** `''` until the expert chooses; never the model's proposal. */
  readonly value: Severity | '';
  readonly onChange: (next: Severity | '') => void;
  /** ✓ needs a severity the expert has not chosen yet, so the select says it is required. */
  readonly required: boolean;
  /** The last ✓ was refused for want of a choice: the select says it is the field that is wrong. */
  readonly invalid: boolean;
}

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
  /** The choice of severity beside ✓, for a finding the model proposed one for. Absent, no select is drawn. */
  readonly severity?: RowSeverityChoice | undefined;
}

/** A value of the select as a severity, or the empty choice: anything outside the five is no choice. */
function severityOf(value: string): Severity | '' {
  return (SEVERITY_VALUES as readonly string[]).includes(value) ? (value as Severity) : '';
}

export function FindingRowActions({ verdict, sending, note, onAccept, onReject, recordedKey, severity }: FindingRowActionsProps) {
  return (
    <div className={styles.rowActions} data-row-actions="">
      {severity === undefined ? null : (
        <select
          className={styles.severityChoice}
          aria-label="Критичность"
          aria-required={severity.required ? true : undefined}
          aria-invalid={severity.invalid ? true : undefined}
          value={severity.value}
          disabled={sending !== null || verdict === 'accepted'}
          data-row-severity=""
          onChange={(event) => {
            severity.onChange(severityOf(event.target.value));
          }}
        >
          <option value="">Критичность</option>
          {SEVERITY_VALUES.map((value) => (
            <option key={value} value={value}>
              {SEVERITY_LABELS[value]}
            </option>
          ))}
        </select>
      )}
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
