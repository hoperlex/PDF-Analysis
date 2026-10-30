'use client';

import { useEffect, useRef, useState } from 'react';

import styles from './app-frame.module.css';

export type SidebarMode = 'full' | 'compact';
export const SIDEBAR_STORAGE_KEY = 'auditmanager.sidebar';

export interface SidebarStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export function readSidebarMode(storage: SidebarStorage | null): SidebarMode {
  if (storage === null) return 'full';
  try {
    return storage.getItem(SIDEBAR_STORAGE_KEY) === 'compact' ? 'compact' : 'full';
  } catch {
    return 'full';
  }
}

export function writeSidebarMode(storage: SidebarStorage | null, mode: SidebarMode): void {
  try {
    storage?.setItem(SIDEBAR_STORAGE_KEY, mode);
  } catch {
    // The current page still changes mode when browser storage is unavailable.
  }
}

function browserStorage(): SidebarStorage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function SidebarToggle() {
  const [mode, setMode] = useState<SidebarMode>('full');
  const button = useRef<HTMLButtonElement>(null);

  const apply = (next: SidebarMode) => {
    button.current?.closest('.am-app')?.setAttribute('data-sidebar', next);
    setMode(next);
  };

  useEffect(() => {
    const stored = readSidebarMode(browserStorage());
    button.current?.closest('.am-app')?.setAttribute('data-sidebar', stored);
    setMode(stored);
  }, []);

  const toggle = () => {
    const next = mode === 'full' ? 'compact' : 'full';
    apply(next);
    writeSidebarMode(browserStorage(), next);
  };

  return (
    <button
      ref={button}
      className={styles.sidebarToggle}
      type="button"
      onClick={toggle}
      aria-label={mode === 'full' ? 'Свернуть боковую панель' : 'Развернуть боковую панель'}
      aria-pressed={mode === 'compact'}
      title={mode === 'full' ? 'Свернуть панель' : 'Развернуть панель'}
    >
      <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <rect x="2.5" y="3" width="15" height="14" rx="3" stroke="currentColor" strokeWidth="1.5" />
        <path d="M7 3v14" stroke="currentColor" strokeWidth="1.5" />
        <path d="m12 8-2 2 2 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </button>
  );
}
