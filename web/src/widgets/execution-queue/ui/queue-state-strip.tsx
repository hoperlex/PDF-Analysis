'use client';

/**
 * `UI-B-51`, `UI-B-69`, `D-370`: the original's «Активные / Завершённые / Ошибки» over the queue, each heading with its count — a press
 * that lists the whole group (the page writes it onto the address, `?group=`; the server takes `state_group`) — and under it the states
 * that group holds, each a press that narrows the list to that state (`?state=`).
 *
 * The strip is a view over the state and group filters; a state's press sets the value the «Состояние задачи» select sets. The numbers are
 * the page's `overview` (`UI-PARITY-P0M`): the server's count of every state over the period. A state with no job is not drawn, so the
 * strip stays one line, unless it is the state the list is narrowed to (a filter must always show what it is). A group is always drawn,
 * with its total, which is the number of rows its press lists.
 */

import type { ExecutionQueueStateCount } from '@/shared/api';
import { QUEUE_STATE_GROUPS, jobStateLabel } from '@/entities/execution';
import type { ExecutionQueueState, ExecutionQueueStateGroup } from '@/entities/execution';

import styles from './execution-queue.module.css';

export interface QueueStateStripProps {
  /** The server's count of every state over the period. */
  readonly overview: readonly ExecutionQueueStateCount[];
  /** The state the list is narrowed to; `''` is every state. */
  readonly selected: ExecutionQueueState | '';
  /** The group the list is narrowed to (`D-370`); `''` for none. */
  readonly selectedGroup?: ExecutionQueueStateGroup | '';
  readonly onSelect: (state: ExecutionQueueState | '') => void;
  /** A group's press: list every job of the group. */
  readonly onSelectGroup?: (group: ExecutionQueueStateGroup) => void;
}

function countOf(overview: readonly ExecutionQueueStateCount[], state: ExecutionQueueState): number {
  return overview.find((entry) => entry.state === state)?.count ?? 0;
}

export function QueueStateStrip({ overview, selected, selectedGroup = '', onSelect, onSelectGroup }: QueueStateStripProps) {
  const total = overview.reduce((sum, entry) => sum + entry.count, 0);
  const noFilter = selected === '' && selectedGroup === '';
  return (
    <div
      className={styles.stateStrip}
      role="group"
      aria-label="Задачи по состоянию"
      data-queue-overview=""
      data-queue-state-strip={selected}
      data-queue-group-strip={selectedGroup}
    >
      <button
        type="button"
        className={noFilter ? 'am-button am-button--small' : 'am-button am-button--quiet am-button--small'}
        aria-pressed={noFilter}
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
            {onSelectGroup === undefined ? (
              <span className={styles.stateGroupLabel}>{group.label} {groupTotal}</span>
            ) : (
              <button
                type="button"
                className={selectedGroup === group.key ? 'am-button am-button--small' : 'am-button am-button--quiet am-button--small'}
                aria-pressed={selectedGroup === group.key}
                data-queue-group-chip={group.key}
                title={`Показать все задачи группы: ${group.states.map(jobStateLabel).join(', ')}`}
                onClick={() => onSelectGroup(group.key)}
              >
                {group.label} {groupTotal}
              </button>
            )}
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
