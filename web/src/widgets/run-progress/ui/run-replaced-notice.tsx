'use client';

/** @jsxRuntime automatic */

/**
 * «Прогон перезапущен» (`RUN-RESTART-01`, `R-155g`): the line at the top of the page of a run a restart replaced. The new run published,
 * the old one was deleted from the lists (its data stays), and this page is only reached by an old link or from the new run's own line;
 * the one thing a reader wants here is the way to the new run, so it is the only thing offered.
 */

import Link from 'next/link';

import { routes } from '@/shared/lib';

import styles from './run-progress.module.css';

export interface RunReplacedNoticeProps {
  readonly projectUid: string;
  readonly replacedByRunId: string;
}

export function RunReplacedNotice({ projectUid, replacedByRunId }: RunReplacedNoticeProps) {
  return (
    <section className={styles.replaced} aria-label="Прогон перезапущен" data-run-replaced={replacedByRunId}>
      <strong className={styles.replacedTitle}>Прогон перезапущен</strong>
      <Link className="am-button am-button--small" href={routes.run(projectUid, replacedByRunId)} data-run-replaced-link="">
        Открыть новый прогон
      </Link>
    </section>
  );
}
