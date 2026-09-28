'use client';

/**
 * The dashboard: four panels, one read. `R-44`, wired at `W46-WIRE`.
 *
 * **All four panels read `getDashboardSummary` and nothing else.** This file holds the
 * one query (`useDashboardSummary`) and hands each panel its own slice of the one
 * response; no panel below opens a second source. Before this wave the aggregate existed
 * with no consumer and the four panels walked three separate client-side sources instead
 * (`F-3b`, `docs/program/reviews/W46-JUDGE-A.md` §5) — `useProjectList`,
 * `useDecisionJournal`, and a bespoke `useRunActivityWalk` this wave deletes.
 *
 * **One loading state, one error state, for the whole grid.** With three independent
 * queries a failed one could not be allowed to blank the three panels beside it; with one
 * read that no longer applies — all four panels are the same request, so they are the
 * same state by construction, and rendering that once here rather than four times is not
 * a behaviour change, just where the branch lives now.
 */

import { ErrorState, LoadingState } from '@/shared/ui';

import { useDashboardSummary } from '../api/use-dashboard-summary';
import { classifyDashboardFailure } from '../model/dashboard-failure';
import { DocumentsPanel } from './documents-panel';
import { VerdictsPanel } from './verdicts-panel';
import { RunActivityPanel } from './run-activity-panel';
import { SectionsPanel } from './sections-panel';
import styles from './dashboard.module.css';

// Heading ids for `aria-labelledby` only, deliberately not spelled like this stylesheet's
// own class-naming convention: `styling-layer.test.ts` scans every `.tsx` for that pattern
// and expects each hit to be a declared class or modifier, so an id that happened to start
// the same way would read as an undeclared class.
export function Dashboard() {
  const summary = useDashboardSummary();

  if (summary.isPending) return <LoadingState what="сводку по системе" />;

  if (summary.isError) {
    const failure = classifyDashboardFailure(summary.error);
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

  const data = summary.data;

  return (
    <div className={styles.grid} data-widget="dashboard">
      <section className={styles.panel} aria-labelledby="dashboard-documents-heading">
        <h2 id="dashboard-documents-heading">Документы по проектам</h2>
        <DocumentsPanel rows={data.documents_by_project} />
      </section>
      <section className={styles.panel} aria-labelledby="dashboard-verdicts-heading">
        <h2 id="dashboard-verdicts-heading">Находки по вердикту</h2>
        <VerdictsPanel rows={data.findings_by_verdict} />
      </section>
      <section className={styles.panel} aria-labelledby="dashboard-runs-heading">
        <h2 id="dashboard-runs-heading">Прогоны и расход</h2>
        <RunActivityPanel
          activity={data.run_activity}
          hasProjects={data.documents_by_project.length > 0}
        />
      </section>
      <section className={styles.panel} aria-labelledby="dashboard-sections-heading">
        <h2 id="dashboard-sections-heading">Разбивка по разделам</h2>
        <SectionsPanel rows={data.section_breakdown} />
      </section>
    </div>
  );
}
