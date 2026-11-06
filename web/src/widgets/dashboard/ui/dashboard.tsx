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

import Link from 'next/link';

import type { ProjectUid } from '@/shared/api';
import { ErrorState, LoadingState } from '@/shared/ui';

import { useDashboardSummary } from '../api/use-dashboard-summary';
import { classifyDashboardFailure } from '../model/dashboard-failure';
import { DocumentsPanel } from './documents-panel';
import { VerdictsPanel } from './verdicts-panel';
import { RunActivityPanel } from './run-activity-panel';
import { SectionsPanel } from './sections-panel';
import styles from './dashboard.module.css';

export interface DashboardProps {
  /**
   * The project the address names (`?project=`), or `null` for «Все проекты». The page reads it
   * from the address; the address is the only source of the project (`UI-PARITY-01`, «Project
   * context»), so the widget keeps no copy of it.
   */
  readonly projectUid?: ProjectUid | null;
  /**
   * Where «Все проекты» leads: this same screen with the project taken out of the address. Built
   * by the page with `switchProject(…, null)`, so every other parameter of the address is kept.
   */
  readonly allProjectsHref?: string;
}

/** The scope the screen states, when it covers every project. */
const ALL_PROJECTS = 'Все проекты';

// Heading ids for `aria-labelledby` only, deliberately not spelled like this stylesheet's
// own class-naming convention: `styling-layer.test.ts` scans every `.tsx` for that pattern
// and expects each hit to be a declared class or modifier, so an id that happened to start
// the same way would read as an undeclared class.
export function Dashboard({ projectUid = null, allProjectsHref = '/dashboard' }: DashboardProps) {
  const summary = useDashboardSummary(projectUid);

  if (summary.isPending) {
    return <div className={styles.showcase} data-dashboard-showcase="true"><LoadingState what="сводку по системе" /></div>;
  }

  if (summary.isError) {
    const failure = classifyDashboardFailure(summary.error, projectUid);
    if (failure.kind === 'project_not_found') {
      // An unknown project is its own state with a way out. It is never a summary of zeros and
      // never «Все проекты»: the reader asked for one project, and is told it is not there.
      return (
        <div className={styles.showcase} data-dashboard-showcase="true" data-dashboard-scope="unknown-project">
          <ErrorState
            title={failure.title}
            detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
            correlationId={failure.correlationId}
          />
          <p className={styles.way}>
            <Link className="am-button am-button--quiet" href={allProjectsHref}>
              {ALL_PROJECTS}
            </Link>
          </p>
        </div>
      );
    }
    return (
      <div className={styles.showcase} data-dashboard-showcase="true">
        <ErrorState
          title={failure.title}
          detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
          correlationId={failure.correlationId}
          {...(failure.retryable
            ? { onRetry: () => void summary.refetch(), retryLabel: 'Повторить' }
            : {})}
        />
      </div>
    );
  }

  const data = summary.data;
  // With a project the server answers that project's one row (`documents_by_project`), name
  // included: the same read, so the name needs no second request and no page of the project list
  // that may not hold it. Were the row ever absent, the uid the address carries is shown as it is,
  // not a name this screen made up.
  const scopeName =
    projectUid === null
      ? ALL_PROJECTS
      : (data.documents_by_project.find((row) => row.project_uid === projectUid)?.name ?? projectUid);

  return (
    <div className={styles.showcase} data-dashboard-showcase="true">
      {/*
        * `UI-PARITY-DENSE`: the original's overview opens on its table; this screen opened on a 220px poster with an
        * eyebrow, a lead and an orbit drawing. One line now: the title and the scope the numbers are read over.
        */}
      <header className={styles.hero}>
        <h2 className={styles.heroTitle}>Сводка по проектам</h2>
        <p className={styles.scope} data-dashboard-scope={projectUid === null ? 'all' : 'project'}>
          <span className={styles.scopeKey}>Охват</span>
          <strong className={styles.scopeValue}>{scopeName}</strong>
        </p>
      </header>
      <div className={styles.grid} data-widget="dashboard">
        <section className={`${styles.panel} ${styles.sections}`} aria-labelledby="dashboard-sections-heading">
          <h2 id="dashboard-sections-heading">Разделы проекта</h2>
          <SectionsPanel rows={data.section_breakdown} projectUid={projectUid} />
        </section>
        <section className={styles.panel} aria-labelledby="dashboard-documents-heading">
          <h2 id="dashboard-documents-heading">Документы по проектам</h2>
          <DocumentsPanel rows={data.documents_by_project} />
        </section>
        <section className={styles.panel} aria-labelledby="dashboard-verdicts-heading">
          <h2 id="dashboard-verdicts-heading">Находки по вердикту, за всё время</h2>
          <VerdictsPanel rows={data.findings_by_verdict} />
        </section>
        <section className={`${styles.panel} ${styles.runs}`} aria-labelledby="dashboard-runs-heading">
          <h2 id="dashboard-runs-heading">Прогоны и расход</h2>
          <RunActivityPanel
            activity={data.run_activity}
            hasProjects={data.documents_by_project.length > 0}
          />
        </section>
      </div>
    </div>
  );
}
