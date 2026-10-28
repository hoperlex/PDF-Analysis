/**
 * «было → стало» (`CMP-VIEWER-01`): the two texts of a change with an arrow between them only when there are two. A text
 * that was added has nothing before it and a text that was removed nothing after it; an arrow pointing at nothing says
 * something that is not so.
 */

import type { ReactNode } from 'react';

import styles from './comparison-viewer.module.css';

export function BeforeAfter({ before, after }: { readonly before?: ReactNode | undefined; readonly after?: ReactNode | undefined }) {
  const hasBefore = before !== undefined && before !== '';
  const hasAfter = after !== undefined && after !== '';
  if (!hasBefore && !hasAfter) return null;
  return (
    <span className={styles.beforeAfter}>
      {hasBefore ? before : null}
      {hasBefore && hasAfter ? <span className={styles.arrow}>→</span> : null}
      {hasAfter ? after : null}
    </span>
  );
}
