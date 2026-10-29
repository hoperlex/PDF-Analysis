'use client';

/**
 * The tabs of «Сравнение версий»: «Проекты и этапы» and «Сравнение листов». The WAI-ARIA tabs pattern with automatic
 * activation, as the tabs of «Блоки» and «Исполнители» are: a `tablist` of `tab` buttons, each naming the `tabpanel` it
 * controls; only the open tab is in the tab order, and the arrow keys, Home and End move the selection and the focus. One
 * panel is drawn, for the open tab: nothing of a closed tab is mounted, so a closed tab reads nothing from the API.
 */

import { useId, useRef } from 'react';
import type { KeyboardEvent, ReactNode } from 'react';

import { COMPARE_TABS, COMPARE_TAB_HINTS, COMPARE_TAB_LABELS, tabAfterKey } from '../model/tabs';
import type { CompareTab } from '../model/tabs';

import styles from './version-compare-page.module.css';

export interface CompareTabsProps {
  readonly active: CompareTab;
  readonly onSelect: (tab: CompareTab) => void;
  /** A tab that cannot be opened yet, with the reason it says on hover. */
  readonly disabled?: Partial<Record<CompareTab, string>>;
  /** What is added to a tab's label: the number of document sets, the name of the open one. */
  readonly suffix?: Partial<Record<CompareTab, string>>;
  readonly children: ReactNode;
}

export function CompareTabs({ active, onSelect, disabled = {}, suffix = {}, children }: CompareTabsProps) {
  const base = useId();
  const buttons = useRef<Partial<Record<CompareTab, HTMLButtonElement | null>>>({});
  const tabId = (tab: CompareTab): string => `${base}-tab-${tab}`;

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const next = tabAfterKey(active, event.key);
    if (next === null || disabled[next] !== undefined) return;
    event.preventDefault();
    onSelect(next);
    buttons.current[next]?.focus();
  };

  return (
    <div className={styles.tabs}>
      <div role="tablist" aria-label="Разделы сравнения версий" className={styles.tablist}>
        {COMPARE_TABS.map((tab) => {
          const reason = disabled[tab];
          return (
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
              disabled={reason !== undefined}
              title={reason ?? COMPARE_TAB_HINTS[tab]}
              data-compare-tab={tab}
              onClick={() => onSelect(tab)}
              onKeyDown={onKeyDown}
            >
              {COMPARE_TAB_LABELS[tab]}
              {suffix[tab] === undefined ? null : <span className={styles.suffix}> · {suffix[tab]}</span>}
            </button>
          );
        })}
      </div>
      <div
        role="tabpanel"
        id={`${base}-panel`}
        aria-labelledby={tabId(active)}
        tabIndex={0}
        className={styles.panel}
        data-compare-panel={active}
      >
        {children}
      </div>
    </div>
  );
}
