'use client';

import { usePathname } from 'next/navigation';

import type { ScreenGroup } from '@/shared/config';
import { screenMatching } from '@/shared/config';

import styles from './app-frame.module.css';

const GROUP_LABELS: Readonly<Record<ScreenGroup, string>> = {
  home: 'Обзор',
  work: 'Работа',
  knowledge: 'Знания',
  system: 'Система',
  admin: 'Администрирование',
  account: 'Учётная запись',
  hidden: 'Разделы',
};

export function ScreenContextView({ pathname }: { readonly pathname: string | null }) {
  const screen = pathname === null ? undefined : screenMatching(pathname);
  if (screen === undefined) {
    return <div className={styles.screenContext} aria-label="Текущий раздел"><span className={styles.contextCurrent}>AuditManager</span></div>;
  }
  const group = GROUP_LABELS[screen.group];
  return (
    <div className={styles.screenContext} aria-label="Текущий раздел">
      {group === screen.label ? null : <><span className={styles.contextGroup}>{group}</span><span className={styles.contextDivider} aria-hidden="true">›</span></>}
      <strong className={styles.contextCurrent}>{screen.label}</strong>
    </div>
  );
}

export function ScreenContext() {
  return <ScreenContextView pathname={usePathname()} />;
}
