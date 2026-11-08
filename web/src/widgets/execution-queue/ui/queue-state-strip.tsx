'use client';

/**
 * `UI-B-51`, `UI-B-69`: the original's «Активные / Завершённые / Ошибки» over the queue, each heading with its count and under it the
 * states that group holds, each a press that narrows the list to that state (the page writes it onto the address, `?state=`).
 *
 * The strip is a view over the state filter and sets the same value the «Состояние задачи» select sets. The numbers are the page's
 * `overview` (`UI-PARITY-P0M`): the server's count of every state over the period. A state with no job is not drawn, so the strip
 * stays one line, unless it is the state the list is narrowed to (a filter must always show what it is). The server filters by one
 * state, so a group heading is a caption with its total and not a press (`D-370`).
 */

import type { ExecutionQueueStateCount } from '@/shared/api';
import { QUEUE_STATE_GROUPS, jobStateLabel } from '@/entities/execution';
import type { ExecutionQueueState } from '@/entities/execution';

import styles from './execution-queue.module.css';

export interface QueueStateStripProps {
  /** The server's count of every state over the period. */
  readonly overview: readonly ExecutionQueueStateCount[];
  /** The state the list is narrowed to; `''` is every state. */
  readonly selected: ExecutionQueueState | '';
  readonly onSelect: (state: ExecutionQueueState | '') => void;
}

function countOf(overview: readonly ExecutionQueueStateCount[], state: ExecutionQueueState): number {
  return overview.find((entry) => entry.state === state)?.count ?? 0;
}

export function QueueStateStrip({ overview, selected, onSelect }: QueueStateStripProps) {
  const total = overview.reduce((sum, entry) => sum + entry.count, 0);
  return (
    <div className={styles.stateStrip} role="group" aria-label="Задачи по состоянию" data-queue-overview="" data-queue-state-strip={selected}>
      <button
        type="button"
        className={selected === '' ? 'am-button am-button--small' : 'am-button am-button--quiet am-button--small'}
        aria-pressed={selected === ''}
        data-queue-state-chip=""
        onClick={() => onSelect('')}
      >
        Все {total}
      </button>
      {QUEUE_STATE_GROUPS.map((group) => {
        const groupTotal = group.states.reduce((sum, state) => sum + countOf(overview, state), 0);
        const shown = group.states.filter((state) => countOf(overview, state) > 0 || state === selected);
        return (
          <span key={group.key} className={styles.stateGroup} data-queue-group={group.key} data-queue-group-total={groupTotal}>
            <span className={styles.stateGroupLabel}>{group.label} {groupTotal}</span>
            {shown.map((state) => (
              <button
                key={state}
                type="button"
                className={selected === state ? 'am-button am-button--small' : 'am-button am-button--quiet am-button--small'}
                aria-pressed={selected === state}
                data-queue-state-chip={state}
                data-queue-state-total={countOf(overview, state)}
                onClick={() => onSelect(state)}
              >
                {jobStateLabel(state)} {countOf(overview, state)}
              </button>
            ))}
          </span>
        );
      })}
    </div>
  );
}
