'use client';

/**
 * The strip «Очередь запуска» of a project and the installation's «Очередь «ИИ-описание изменений»»
 * (`frontend/static/js/version-comparison-projects.js:136-151`; `version-comparison.js:76-79`, `:949-960`).
 *
 * The launch queue runs one step at a time across the sets of the project and is controlled here by an expert: «Пауза очереди»,
 * «Продолжить очередь», «Очистить», «Список», «✕» on a waiting entry. The AI queue is a read of the AI jobs that wait anywhere in
 * the installation; it starts nothing and has no controls (a job is controlled in its own cell). A queue the module does not serve
 * yet is the module's state, drawn small; the page works without it.
 */

import type { ComparisonAiQueue, ComparisonLaunchEntry, ComparisonLaunchQueue, ComparisonOverviewSet } from '@/shared/api';
import type { ComparisonFailure } from '@/entities/version-series';
import {
  AI_QUEUE_TITLE,
  LAUNCH_ENTRY_STATE_LABELS,
  LAUNCH_QUEUE_STATE_LABELS,
  LAUNCH_QUEUE_TITLE,
  LAUNCH_QUEUE_TONES,
  TONE_BADGES,
  aiQueueItemLine,
  aiQueueText,
  canRemoveEntry,
  entryLabel,
  launchControls,
  launchCountsLine,
} from '@/entities/version-series';

import { CommandRefusal } from './module-state';
import styles from './ai-steps.module.css';

export type LaunchAct = 'pause' | 'resume' | 'clear';

export interface LaunchQueueStripProps {
  readonly queue: ComparisonLaunchQueue;
  readonly sets: readonly ComparisonOverviewSet[];
  readonly mayAct: boolean;
  readonly busy: boolean;
  readonly open: boolean;
  readonly failure: ComparisonFailure | null;
  readonly onToggle: () => void;
  readonly onAct: (act: LaunchAct) => void;
  readonly onRemove: (entry: ComparisonLaunchEntry) => void;
  /** «Подтвердить…» of an entry that waits for the reader's word: the step is started from its own dialog. */
  readonly onConfirm: (entry: ComparisonLaunchEntry) => void;
}

export function LaunchQueueStrip({ queue, sets, mayAct, busy, open, failure, onToggle, onAct, onRemove, onConfirm }: LaunchQueueStripProps) {
  const controls = launchControls(queue);
  const tone = LAUNCH_QUEUE_TONES[queue.state];
  return (
    <section className={styles.strip} aria-label={LAUNCH_QUEUE_TITLE} data-launch-queue={queue.state}>
      <div className={styles.stripHead}>
        <strong className={styles.stripTitle}>{LAUNCH_QUEUE_TITLE}</strong>
        <span className={`am-badge am-badge--${TONE_BADGES[tone.tone]}`} data-launch-queue-state={queue.state}>
          {tone.icon} {LAUNCH_QUEUE_STATE_LABELS[queue.state]}
        </span>
        <span className="am-note">{launchCountsLine(queue)}</span>
        <span className={styles.spacer} />
        {mayAct && controls.pause ? (
          <button type="button" className="am-button am-button--small am-button--quiet" disabled={busy} data-queue-act="pause" title="Текущий шаг — на паузу (начатое доводится), следующие не начинаются." onClick={() => onAct('pause')}>
            ⏸ Пауза очереди
          </button>
        ) : null}
        {mayAct && controls.resume ? (
          <button type="button" className="am-button am-button--small" disabled={busy} data-queue-act="resume" title="Текущий шаг — с того же места, затем следующие." onClick={() => onAct('resume')}>
            ▶ Продолжить очередь
          </button>
        ) : null}
        {mayAct && controls.clear ? (
          <button type="button" className="am-button am-button--small am-button--quiet" disabled={busy} data-queue-act="clear" title="Убрать ждущие шаги и историю; идущий шаг продолжит работу." onClick={() => onAct('clear')}>
            Очистить
          </button>
        ) : null}
        <button type="button" className="am-button am-button--small am-button--quiet" title="Показать или скрыть список шагов в очереди." aria-expanded={open} onClick={onToggle}>
          {open ? 'Скрыть список' : 'Список'}
        </button>
      </div>
      <CommandRefusal failure={failure} />
      {open ? (
        <ol className={styles.stripList}>
          {queue.entries.map((entry) => (
            <li key={entry.entry_id} className={styles.stripEntry} data-launch-entry-state={entry.state}>
              <span className={styles.entryState}>{LAUNCH_ENTRY_STATE_LABELS[entry.state]}</span> {entryLabel(entry, sets)}
              {mayAct && entry.state === 'needs_consent' ? (
                <>
                  {' '}
                  <button type="button" className="am-button am-button--small am-button--quiet" title="Показать оценку и подтвердить передачу: шаг будет запущен из своего окна." onClick={() => onConfirm(entry)}>
                    Подтвердить…
                  </button>
                </>
              ) : null}
              {mayAct && canRemoveEntry(entry) ? (
                <>
                  {' '}
                  <button type="button" className="am-button am-button--small am-button--quiet" disabled={busy} title="Убрать из очереди" aria-label="Убрать из очереди" data-queue-remove="" onClick={() => onRemove(entry)}>
                    ✕
                  </button>
                </>
              ) : null}
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}

export interface AiQueueStripProps {
  readonly queue: ComparisonAiQueue;
  readonly sets: readonly ComparisonOverviewSet[];
}

/** «Очередь «ИИ-описание изменений»: идёт «шифр» · далее: «шифр» → «шифр»» (`aiQueueText`). */
export function AiQueueStrip({ queue, sets }: AiQueueStripProps) {
  return (
    <section className={styles.strip} aria-label={AI_QUEUE_TITLE} data-ai-queue="">
      <div className={styles.stripHead}>
        <strong className={styles.stripTitle}>{AI_QUEUE_TITLE}:</strong>
        <span className="am-note">{aiQueueText(queue, sets)}</span>
      </div>
      <ul className={styles.stripList}>
        {queue.items.map((item) => (
          <li key={item.job_id} className={styles.stripEntry} data-ai-job-state={item.state} data-ai-method={item.method}>
            {aiQueueItemLine(item)}
          </li>
        ))}
      </ul>
    </section>
  );
}
