'use client';

/**
 * The tabs of «Исполнители» (`EXEC-HTTP-01`): «Подключения», «Процессы», «Назначения».
 *
 * The WAI-ARIA tabs pattern with automatic activation, as the tabs of «Блоки» are: a `tablist`
 * of `tab` buttons, each naming the `tabpanel` it controls and saying whether it is the open
 * one; only the open tab is in the tab order, and the arrow keys, Home and End move the
 * selection and the focus. One panel is drawn, for the open tab, with the open tab's content as
 * its children: nothing of a closed tab is mounted, so a closed tab reads nothing from the API.
 */

import { useId, useRef } from 'react';
import type { KeyboardEvent, ReactNode } from 'react';

import { WORKERS_TABS, WORKERS_TAB_LABELS, tabAfterKey } from '../model/tabs';
import type { WorkersTab } from '../model/tabs';

import styles from './workers-page.module.css';

export interface WorkersTabsProps {
  readonly active: WorkersTab;
  readonly onSelect: (tab: WorkersTab) => void;
  /** What the open tab shows. */
  readonly children: ReactNode;
}

export function WorkersTabs({ active, onSelect, children }: WorkersTabsProps) {
  const base = useId();
  const buttons = useRef<Partial<Record<WorkersTab, HTMLButtonElement | null>>>({});
  const tabId = (tab: WorkersTab): string => `${base}-tab-${tab}`;

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const next = tabAfterKey(active, event.key);
    if (next === null) return;
    event.preventDefault();
    onSelect(next);
    buttons.current[next]?.focus();
  };

  return (
    <div className={styles.tabs}>
      <div role="tablist" aria-label="Разделы экрана исполнителей" className={styles.tablist}>
        {WORKERS_TABS.map((tab) => (
          <button
            key={tab}
            ref={(element) => {
              buttons.current[tab] = element;
            }}
            type="button"
            role="tab"
            id={tabId(tab)}
            aria-selected={tab === active}
            aria-controls={`${base}-panel`}
            tabIndex={tab === active ? 0 : -1}
            className={styles.tab}
            data-workers-tab={tab}
            onClick={() => onSelect(tab)}
            onKeyDown={onKeyDown}
          >
            {WORKERS_TAB_LABELS[tab]}
          </button>
        ))}
      </div>
      <div
        role="tabpanel"
        id={`${base}-panel`}
        aria-labelledby={tabId(active)}
        tabIndex={0}
        className={styles.panel}
        data-workers-panel={active}
      >
        {children}
      </div>
    </div>
  );
}
