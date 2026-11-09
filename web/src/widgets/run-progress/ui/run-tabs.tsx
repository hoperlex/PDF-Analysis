'use client';

/** @jsxRuntime automatic */

/**
 * «Обзор» and «Журнал» (`RUN-SCREEN-01a`): the WAI-ARIA tabs pattern with automatic activation, as the tabs of «Блоки» and «Исполнители»
 * are. A `tablist` of `tab` buttons, each naming the panel it controls and saying whether it is the open one; only the open tab is in the
 * tab order, and the arrow keys, Home and End move the selection and the focus (`tabAfterKey`). One panel is drawn, for the open tab,
 * with the open tab's content as its children: nothing of a closed tab is mounted, so the journal is not read until it is asked for.
 */

import { useId, useRef } from 'react';
import type { KeyboardEvent, ReactNode } from 'react';

import { RUN_TAB_LABELS, tabAfterKey } from '../model/run-tabs';
import type { RunTab } from '../model/run-tabs';

import styles from './run-progress.module.css';

export interface RunTabsProps {
  /** The tabs shown, in order; a tab the reader may not have is simply absent. */
  readonly tabs: readonly RunTab[];
  readonly active: RunTab;
  readonly onSelect: (tab: RunTab) => void;
  /** What the open tab shows. */
  readonly children: ReactNode;
}

export function RunTabs({ tabs, active, onSelect, children }: RunTabsProps) {
  const base = useId();
  const buttons = useRef<Partial<Record<RunTab, HTMLButtonElement | null>>>({});
  const tabId = (tab: RunTab): string => `${base}-tab-${tab}`;

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const next = tabAfterKey(tabs, active, event.key);
    if (next === null) return;
    event.preventDefault();
    onSelect(next);
    buttons.current[next]?.focus();
  };

  return (
    <div className={styles.tabs}>
      <div role="tablist" aria-label="Разделы экрана прогона" className={styles.tablist}>
        {tabs.map((tab) => (
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
            data-run-tab={tab}
            onClick={() => onSelect(tab)}
            onKeyDown={onKeyDown}
          >
            {RUN_TAB_LABELS[tab]}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`${base}-panel`} aria-labelledby={tabId(active)} tabIndex={0} className={styles.panelBody} data-run-panel={active}>
        {children}
      </div>
    </div>
  );
}
