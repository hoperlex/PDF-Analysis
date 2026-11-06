'use client';

/** @jsxRuntime automatic */

/**
 * The finding opened under its row of the table (`UI-A-68`).
 *
 * When it opens, the row it belongs to is brought to the top of the screen, so the row and the page under it are
 * in sight together and a long table does not leave the finding below the fold. It mounts once per opened row, so
 * the move happens when a row is opened (or when a saved link opens on one) and never while the expert works in it.
 */

import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';

import styles from './review-page.module.css';

export function OpenedFinding({ children }: { readonly children: ReactNode }) {
  const holder = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const row = holder.current?.closest('tr')?.previousElementSibling;
    if (row instanceof HTMLElement && typeof row.scrollIntoView === 'function') row.scrollIntoView({ block: 'start' });
  }, []);
  return (
    <div ref={holder} className={styles.expansion}>
      {children}
    </div>
  );
}
