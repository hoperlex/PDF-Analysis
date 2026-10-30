'use client';

import { ErrorState, LoadingState } from '@/shared/ui';

import { useDashboardSummary } from '../api/use-dashboard-summary';
import { classifyDashboardFailure } from '../model/dashboard-failure';
import { SectionsPanel } from './sections-panel';

/** The same section breakdown as the dashboard, visible on the front door. */
export function HomeSectionsOverview() {
  const summary = useDashboardSummary();
  const failure = summary.isError ? classifyDashboardFailure(summary.error) : null;

  return (
    <section data-home-sections="">
      <h2>Разделы проекта</h2>
      {summary.isPending ? <LoadingState what="разделы проекта" /> : null}
      {failure === null ? null : (
        <ErrorState
          title={failure.title}
          detail={failure.detail}
          correlationId={failure.correlationId}
          {...(failure.retryable
            ? { onRetry: () => void summary.refetch(), retryLabel: 'Повторить' }
            : {})}
        />
      )}
      {summary.isSuccess ? <SectionsPanel rows={summary.data.section_breakdown} /> : null}
    </section>
  );
}
