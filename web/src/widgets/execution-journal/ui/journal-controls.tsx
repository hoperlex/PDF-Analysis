'use client';

/**
 * The journal's own controls (`UI-B-43`): «Автообновление», «Скопировать» and the count of the page.
 *
 * «Автообновление» is the switch for the timed re-read the queue and the journal already have
 * (`OPERATIONAL_LIST_POLLING`): on, the journal is read again at that cadence while the tab is
 * visible; off, it is read when the screen opens, when the page changes and on «Обновить». The
 * screen holds the switch and hands it to the read; this component only draws it and says, in the
 * interval the policy declares, what the switch does.
 *
 * «Скопировать» puts the rows of the page in view on the clipboard as text, in the closed
 * projection the page draws (`journalCopyText`). It is client-side: nothing is requested. A browser
 * that refuses the clipboard (no permission, an insecure context) is told so, and the rows stay on
 * the screen to be selected by hand. The confirmation belongs to the text that was copied: when the
 * page changes under it, the message goes, so «Скопировано» never describes rows that are gone.
 */

import { useState } from 'react';

import type { ExecutionJournalEntry } from '@/shared/api';
import { OPERATIONAL_LIST_POLLING } from '@/shared/config';
import { journalCopyText } from '@/entities/execution';

import { browserClipboard, copyToClipboard } from '../model/copy-to-clipboard';
import styles from './journal-controls.module.css';

export interface JournalControlsProps {
  /** The rows of the page in view; `undefined` until the first read has answered. */
  readonly entries: readonly ExecutionJournalEntry[] | undefined;
  /** The run the journal is narrowed to; `null` for every run. */
  readonly runId: string | null;
  readonly autoRefresh: boolean;
  readonly onAutoRefresh: (on: boolean) => void;
}

/** The outcome of the last «Скопировать», with the text it concerned. */
interface CopyOutcome {
  readonly text: string;
  readonly copied: boolean;
}

const INTERVAL_SECONDS = OPERATIONAL_LIST_POLLING.intervalMs / 1000;

export function JournalControls({ entries, runId, autoRefresh, onAutoRefresh }: JournalControlsProps) {
  const [outcome, setOutcome] = useState<CopyOutcome | null>(null);
  const rows = entries ?? [];
  const text = journalCopyText(rows, { runId });
  const shown = outcome !== null && outcome.text === text ? outcome : null;

  async function copy() {
    // A refusal (no permission, no clipboard) is said below, never swallowed.
    setOutcome({ text, copied: await copyToClipboard(text, browserClipboard()) });
  }

  return (
    <>
      <div className={styles.controls} data-journal-controls>
        <label className={styles.toggle}>
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(event) => onAutoRefresh(event.target.checked)}
            data-journal-auto-refresh={autoRefresh ? 'on' : 'off'}
          />
          <span>Автообновление</span>
        </label>
        <button
          type="button"
          className="am-button am-button--quiet am-button--small"
          disabled={rows.length === 0}
          onClick={() => void copy()}
          data-journal-copy
        >
          Скопировать
        </button>
        <span className={styles.count} data-journal-count={entries === undefined ? 'unknown' : entries.length}>
          {`Записей на странице: ${entries === undefined ? '—' : entries.length}`}
        </span>
      </div>
      <div className={styles.notes}>
        <p className="am-form__hint" data-journal-auto-refresh-note={autoRefresh ? 'on' : 'off'}>
          {autoRefresh
            ? `Журнал читается заново раз в ${INTERVAL_SECONDS} с, пока вкладка видна; после сбоя реже.`
            : 'Автообновление выключено: журнал обновится при нажатии «Обновить» и при смене страницы.'}
        </p>
        {shown === null ? null : shown.copied ? (
          <p className="am-form__hint" role="status" data-journal-copy-result="copied">
            {`Скопировано записей: ${rows.length}.`}
          </p>
        ) : (
          <p className="am-form__problem" role="alert" data-journal-copy-result="refused">
            Не удалось скопировать: браузер не дал доступ к буферу обмена. Выделите строки журнала и скопируйте вручную.
          </p>
        )}
      </div>
    </>
  );
}
