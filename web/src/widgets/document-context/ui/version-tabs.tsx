'use client';

/**
 * The tab row of the document frame (`UI-A-22`, `R-151m`, `UIP-G-09`): the original's strip on the right of the
 * breadcrumb, «Инфо · Блоки N · Лог · Разбор N · Оптимизация N». It reads the version's runs with the key the run list and
 * the block tiles already use, so a cold load makes no request of its own on the version page, and the account for «Лог»,
 * which is the operator's tab. The numbers of «Блоки» and «Оптимизация» are the frame's, from the version's own read
 * (`useVersionFigures`, `UIP-S04-02`), handed in. The tabs are links; the open one is text with `aria-current`.
 */

import Link from 'next/link';

import type { VersionUid } from '@/shared/api';
import { useMe } from '@/entities/account';
import { useRunList } from '@/entities/audit-run';

import { mayReadLogOf, versionTabs } from '../model/version-tabs';
import type { VersionTab, VersionTabFacts } from '../model/version-tabs';
import styles from './document-context.module.css';

export interface VersionTabsViewProps {
  readonly tabs: readonly VersionTab[];
}

/** The row itself, from tabs already worked out. Pure, so the markup is tested without a query client. */
export function VersionTabsView({ tabs }: VersionTabsViewProps) {
  return (
    <nav className={styles.tabs} aria-label="Разделы версии" data-version-tabs="">
      {tabs.map((tab) => {
        const text = tab.count === null ? tab.label : (
          <>{tab.label} <span className={styles.tabCount}>{tab.count}</span></>
        );
        if (tab.current) return <span key={tab.key} className={styles.tabCurrent} aria-current="page" title={tab.title ?? undefined} data-version-tab={tab.key}>{text}</span>;
        if (tab.href === null) {
          return (
            <span key={tab.key} className={styles.tabOff} title={tab.title ?? undefined} data-version-tab={tab.key} data-version-tab-off="">
              {text}
            </span>
          );
        }
        return (
          <Link key={tab.key} href={tab.href} className={styles.tab} title={tab.title ?? undefined} data-version-tab={tab.key}>
            {text}
          </Link>
        );
      })}
    </nav>
  );
}

export function VersionTabs(facts: Omit<VersionTabFacts, 'runs' | 'mayReadLog'>) {
  const runs = useRunList(facts.versionUid as VersionUid);
  const me = useMe();
  return (
    <VersionTabsView tabs={versionTabs({ ...facts, runs: runs.data?.items, mayReadLog: mayReadLogOf(me.data?.roles) })} />
  );
}
