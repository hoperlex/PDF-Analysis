'use client';

import { useRef } from 'react';
import type { KeyboardEvent } from 'react';

import { CRITIC_QUEUES, queueAfterKey } from './critic-queues';
import styles from './extended-review.module.css';

export interface CriticQueueTabsProps {
  /** The chosen queue's value. */
  readonly value: string;
  readonly onChange: (value: string) => void;
  /** Each queue's whole count over the record, never one page of it. */
  readonly total: Readonly<Record<string, number>>;
  /** Each queue's count under the list's other filters: the original's «видимо». */
  readonly visible: Readonly<Record<string, number>>;
  /** The id of the list the tabs control; the tab ids are derived from it. */
  readonly panelId: string;
}

/** The id of the tab of `value`, for the panel to name it as its label. */
export function queueTabId(panelId: string, value: string): string {
  return `${panelId}-tab-${value}`;
}

/**
 * The critic's queues as the tabs pattern (UI-B-78): one tab per queue with «видимо / всего», the chosen one the only
 * stop of the Tab key, `←` `→` `Home` `End` moving between them and choosing as they go, as a click does.
 */
export function CriticQueueTabs({ value, onChange, total, visible, panelId }: CriticQueueTabsProps) {
  const tabs = useRef(new Map<string, HTMLButtonElement>());
  const choose = (next: string) => {
    onChange(next);
    tabs.current.get(next)?.focus();
  };
  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const next = queueAfterKey(value, event.key);
    if (next === null) return;
    event.preventDefault();
    choose(next);
  };
  return (
    <div className={styles.queues} role="tablist" aria-label="Очереди критика" data-critic-queues="">
      {CRITIC_QUEUES.map(([queue, label]) => {
        const selected = value === queue;
        return (
          <button
            key={queue}
            ref={(node) => {
              if (node === null) tabs.current.delete(queue);
              else tabs.current.set(queue, node);
            }}
            type="button"
            role="tab"
            id={queueTabId(panelId, queue)}
            aria-selected={selected}
            aria-controls={panelId}
            tabIndex={selected ? 0 : -1}
            className={selected ? 'am-button am-button--small' : 'am-button am-button--quiet am-button--small'}
            title={`${label}: по фильтрам ${visible[queue] ?? 0} из ${total[queue] ?? 0}`}
            onClick={() => { onChange(queue); }}
            onKeyDown={onKeyDown}
          >
            {label} <span className={styles.queueCount}>{visible[queue] ?? 0} / {total[queue] ?? 0}</span>
          </button>
        );
      })}
    </div>
  );
}
