'use client';

/**
 * The two views of a chosen version: «Блоки портала» and «Строки текста» (`W55B-WEB-BLOCKS`).
 *
 * The WAI-ARIA tabs pattern, with automatic activation: a `tablist` of two `tab` buttons,
 * each naming the `tabpanel` it controls (`aria-controls`) and saying whether it is the open
 * one (`aria-selected`); only the open tab is in the tab order (`tabIndex` 0, the other -1),
 * and the arrow keys, Home and End move the selection AND the focus (`tabAfterKey`, which is
 * the whole keyboard contract as a pure function). Each panel is labelled by its tab.
 *
 * Both panels are always in the document, the closed one `hidden` and EMPTY: its content is
 * mounted only while it is open, so the text-line index is not read until a reader asks for
 * it, and «Блоки портала» is the view a reader lands on. Nothing here survives a reload.
 *
 * No shared tabs primitive exists in `shared/ui`, and this is the only screen with tabs; it
 * is local to the page rather than a primitive one consumer would justify.
 */

import { useId, useRef } from 'react';
import type { KeyboardEvent, ReactNode } from 'react';

import { BLOCK_TABS, BLOCK_TAB_LABELS, tabAfterKey } from '../model/tabs';
import type { BlockTab } from '../model/tabs';

import styles from './blocks-page.module.css';

export interface BlocksTabsProps {
  readonly active: BlockTab;
  readonly onSelect: (tab: BlockTab) => void;
  /** What each tab shows; only the open one is rendered. */
  readonly panels: Readonly<Record<BlockTab, ReactNode>>;
}

export function BlocksTabs({ active, onSelect, panels }: BlocksTabsProps) {
  const base = useId();
  const buttons = useRef<Partial<Record<BlockTab, HTMLButtonElement | null>>>({});
  const tabId = (tab: BlockTab): string => `${base}-tab-${tab}`;
  const panelId = (tab: BlockTab): string => `${base}-panel-${tab}`;

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const next = tabAfterKey(active, event.key);
    if (next === null) return;
    event.preventDefault();
    onSelect(next);
    buttons.current[next]?.focus();
  };

  return (
    <div className={styles.tabs}>
      <div role="tablist" aria-label="Что показать для этой версии" className={styles.tablist}>
        {BLOCK_TABS.map((tab) => (
          <button
            key={tab}
            ref={(element) => {
              buttons.current[tab] = element;
            }}
            type="button"
            role="tab"
            id={tabId(tab)}
            aria-selected={tab === active}
            aria-controls={panelId(tab)}
            tabIndex={tab === active ? 0 : -1}
            className={styles.tab}
            data-block-tab={tab}
            onClick={() => onSelect(tab)}
            onKeyDown={onKeyDown}
          >
            {BLOCK_TAB_LABELS[tab]}
          </button>
        ))}
      </div>
      {BLOCK_TABS.map((tab) => (
        <div
          key={tab}
          role="tabpanel"
          id={panelId(tab)}
          aria-labelledby={tabId(tab)}
          hidden={tab !== active}
          tabIndex={0}
          className={styles.panel}
          data-block-panel={tab}
        >
          {tab === active ? panels[tab] : null}
        </div>
      ))}
    </div>
  );
}
