'use client';

/**
 * The home page's summary tile: four figures from the dashboard's one read (`R-44`), and the
 * way to the dashboard itself.
 */

import Link from 'next/link';

import type { ScreenAddress } from '@/shared/config';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';

import { useHomeSummary } from '../api/home-reads';
import { classifySummaryFailure } from '../model/read-failure';
import { summaryFigures } from '../model/summary-figures';
import { INCOMPLETE_SUMMARY_DETAIL, INCOMPLETE_SUMMARY_TITLE } from './copy';
import styles from './home-tiles.module.css';

/** A registered address, checked by the compiler against the screen registry. */
const DASHBOARD_SCREEN = '/dashboard' satisfies ScreenAddress;

function Body() {
  const summary = useHomeSummary();

  if (summary.isPending) return <LoadingState what="общую сводку" />;

  if (summary.isError) {
    const failure = classifySummaryFailure(summary.error);
    return (
      <ErrorState
        title={failure.title}
        detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
        correlationId={failure.correlationId}
        {...(failure.retryable
          ? { onRetry: () => void summary.refetch(), retryLabel: 'Повторить' }
          : {})}
      />
    );
  }

  const figures = summaryFigures(summary.data);
  if (figures === null) {
    return (
      <div data-home-fault="incomplete">
        <ErrorState title={INCOMPLETE_SUMMARY_TITLE} detail={INCOMPLETE_SUMMARY_DETAIL} />
      </div>
    );
  }

  if (figures.projects === 0) {
    return (
      <EmptyState
        title="Сводка появится вместе с первым проектом."
        detail="Пока в системе нет ни одного проекта, считать нечего."
      />
    );
  }

  return (
    <dl className={styles.figures}>
      <dt>Проекты</dt>
      <dd data-summary-figure="projects">{figures.projects}</dd>
      <dt>Документы</dt>
      <dd data-summary-figure="documents">{figures.documents}</dd>
      <dt>Находки, ожидающие решения</dt>
      <dd data-summary-figure="pending-findings">{figures.pendingFindings}</dd>
      <dt>Прогоны</dt>
      <dd data-summary-figure="runs">{figures.runs}</dd>
    </dl>
  );
}

export function SummaryTile() {
  return (
    <section className={styles.tile} aria-labelledby="home-summary" data-home-tile="summary">
      <h2 id="home-summary">Сводка</h2>
      <Body />
      <p className={styles.more}>
        <Link href={DASHBOARD_SCREEN}>Открыть дашборд</Link>
      </p>
    </section>
  );
}
