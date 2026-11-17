'use client';

/**
 * `UIP-S13-02`: «Фильтры ▾», the one button that holds the two lists the queue's first row used to carry: the state of the task and the
 * period. Its panel opens under the button and closes on a press outside it, on Escape and when the reader goes on; the choices are the
 * address's (the page writes them), so a link, a reload and Back keep them. The groups of states are the chips beside it, not here.
 *
 * The button says how many of the two are narrowed («Фильтры (1) ▾»), so a filter that is set is not hidden by being folded.
 */

import { useEffect, useRef } from 'react';

import type { ExecutionQueueStateCount } from '@/shared/api';
import { QUEUE_STATE_OPTIONS, queueStateCount } from '@/entities/execution';
import type { ExecutionQueueState } from '@/entities/execution';

import { QUEUE_PERIOD_OPTIONS } from '../model/period';
import type { QueuePeriod } from '../model/period';
import styles from './queue-page.module.css';

export interface QueueFiltersProps {
  readonly state: ExecutionQueueState | '';
  readonly period: QueuePeriod;
  /** The page's counts, so each state says how many jobs it would list; absent, the states are named alone. */
  readonly overview: readonly ExecutionQueueStateCount[] | undefined;
  readonly onState: (value: string) => void;
  readonly onPeriod: (value: string) => void;
}

export function QueueFilters({ state, period, overview, onState, onPeriod }: QueueFiltersProps) {
  const root = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const node = root.current;
    if (node === null) return undefined;
    const outside = (event: Event) => {
      if (node.open && event.target instanceof Node && !node.contains(event.target)) node.open = false;
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || !node.open) return;
      node.open = false;
      node.querySelector('summary')?.focus();
    };
    document.addEventListener('pointerdown', outside);
    document.addEventListener('keydown', escape);
    return () => {
      document.removeEventListener('pointerdown', outside);
      document.removeEventListener('keydown', escape);
    };
  }, []);
  const narrowed = (state === '' ? 0 : 1) + (period === 'all' ? 0 : 1);
  return (
    <details ref={root} className={styles.filters} data-queue-filters={narrowed}>
      <summary className={`am-button am-button--quiet am-button--small ${styles.filtersTrigger}`}>
        {narrowed === 0 ? 'Фильтры' : `Фильтры (${narrowed})`} <span aria-hidden="true">▾</span>
      </summary>
      <div className={styles.filtersPanel}>
        <label>
          Состояние задачи
          <select
            name="queue-state"
            data-queue-state-filter
            value={state}
            onChange={(event) => onState(event.currentTarget.value)}
          >
            <option value="">Все состояния</option>
            {QUEUE_STATE_OPTIONS.map((option) => {
              // `UI-PARITY-P0M`: each state with its count, so the filter says what it would list.
              const count = queueStateCount(overview, option.value);
              return <option key={option.value} value={option.value}>{count === null ? option.label : `${option.label} (${count})`}</option>;
            })}
          </select>
        </label>
        <label>
          Период
          <select name="queue-period" data-queue-period-filter value={period} onChange={(event) => onPeriod(event.currentTarget.value)}>
            {QUEUE_PERIOD_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
      </div>
    </details>
  );
}
