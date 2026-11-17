'use client';

/** @jsxRuntime automatic */

/**
 * The decision field (`UIP-S06-01`): ✓ and ✕ with a one-line «Причина», and the line that says what the last press did.
 *
 * One component for the three places that decide: a finding's row on «Разбор», a proposal on «Оптимизация», a record on
 * «База знаний». It lives with the entity that owns the decision, not in `shared/ui`, because it is not general: it is about an
 * expert's verdict. It sends nothing. A press hands the text of the field to the handler the screen gave it, and the screen
 * decides what a decision is (the intent key, the request, the refusal before sending); this file knows only the markup and the
 * three rules that belong to the verdict itself:
 *
 *   - ✓ and ✕ are both held while a press is on its way, so one click cannot become two events;
 *   - the button of the verdict already in force is held too (a press that repeats the verdict is not offered), and it is
 *     marked pressed, so ✓ in force reads as «принято» without a second badge;
 *   - the reason is optional here. A screen that needs one for a particular verdict says so in its own refusal, because that
 *     rule belongs to the screen (S09's «На доработку»), not to every decision.
 *
 * There is no draft, no «save all» and no un-press (`Г9-B`): a press is one decision at once, and the field is only the text
 * that goes with it. Further actions of a screen («На доработку», «Снять решение») stand in the `extra` slot, after ✕.
 */

import { useState } from 'react';
import type { ReactNode } from 'react';

import type { Verdict } from '@/shared/api';

import styles from './decision-reason-control.module.css';

export type DecisionIntent = 'accept' | 'reject';

/** What the last press did: recorded (`ok`) or refused / failed with the reason (`fail`). */
export interface DecisionNote {
  readonly tone: 'ok' | 'fail';
  readonly text: string;
}

export interface DecisionReasonControlProps {
  /** The verdict in force; the press that would repeat it is held. */
  readonly verdict: Verdict;
  /** The press on its way, if any: both buttons are held until it comes back. */
  readonly sending: DecisionIntent | null;
  /** The line under the field: «Записано» as `ok`, the refusal or the server's reason as `fail`. */
  readonly note: DecisionNote | null;
  /** ✓. The argument is the field's text with the ends trimmed; an empty string is no reason. */
  readonly onAccept: (reason: string) => void;
  /** ✕. Same argument as `onAccept`. */
  readonly onReject: (reason: string) => void;
  /** Further actions of the screen, drawn after ✕ in the same row. */
  readonly extra?: ReactNode | undefined;
}

export function DecisionReasonControl({ verdict, sending, note, onAccept, onReject, extra }: DecisionReasonControlProps) {
  const [reason, setReason] = useState('');
  const busy = sending !== null;
  return (
    <div className={styles.control} data-decision-control="">
      <div className={styles.buttons}>
        <button
          type="button"
          className={`am-button am-button--quiet am-button--small ${styles.accept}`}
          aria-label="Принять"
          aria-pressed={verdict === 'accepted'}
          title="Принять"
          data-intent="accept"
          disabled={busy || verdict === 'accepted'}
          onClick={() => {
            onAccept(reason.trim());
          }}
        >
          {sending === 'accept' ? '…' : '✓'}
        </button>
        <button
          type="button"
          className={`am-button am-button--quiet am-button--small ${styles.reject}`}
          aria-label="Отклонить"
          aria-pressed={verdict === 'rejected'}
          title="Отклонить"
          data-intent="reject"
          disabled={busy || verdict === 'rejected'}
          onClick={() => {
            onReject(reason.trim());
          }}
        >
          {sending === 'reject' ? '…' : '✕'}
        </button>
        {extra}
      </div>
      <input
        type="text"
        className={styles.reason}
        aria-label="Причина"
        placeholder="Причина"
        autoComplete="off"
        value={reason}
        data-decision-reason=""
        onChange={(event) => {
          setReason(event.target.value);
        }}
      />
      {note === null ? null : (
        <span className={note.tone === 'ok' ? styles.noteOk : styles.noteFail} role={note.tone === 'ok' ? 'status' : 'alert'}>
          {note.text}
        </span>
      )}
    </div>
  );
}
