'use client';

/**
 * The section table of the front door (`UIP-S01-01`): «Разделы объекта», counted over the object the front door works in.
 *
 * The object comes in as a property, `null` for «Все объекты»; the container beside the page (`_pages/home`) takes it from
 * `useCurrentProject`, the same reader «Дашборд» uses, so this widget reads no address of its own. With an object the rows are
 * links to that object's section pages and «Не запускались» links to the section narrowed to those documents; with «Все объекты»
 * a row unfolds its details, as it did before. The three tiles under the table keep counting every object.
 */

import Link from 'next/link';

import type { ProjectUid } from '@/shared/api';
import { ErrorState, LoadingState } from '@/shared/ui';

import { useDashboardSummary } from '../api/use-dashboard-summary';
import { classifyDashboardFailure } from '../model/dashboard-failure';
import styles from './dashboard.module.css';
import { SectionsPanel } from './sections-panel';

/** «Все объекты» of the front door, when the container names no other way. */
const ALL_PROJECTS_HREF = '/?project=all';

export interface HomeSectionsOverviewProps {
  /** The object the table is counted over, or `null` for «Все объекты». Absent is `null`. */
  readonly projectUid?: ProjectUid | null;
  /**
   * Where «Все объекты» leads from an object the server does not know. The container builds it, because it is the one that
   * knows the address of the front door.
   */
  readonly allProjectsHref?: string;
}

/** The same section breakdown as the dashboard, visible on the front door. */
export function HomeSectionsOverview({ projectUid = null, allProjectsHref = ALL_PROJECTS_HREF }: HomeSectionsOverviewProps) {
  const summary = useDashboardSummary(projectUid);
  const failure = summary.isError ? classifyDashboardFailure(summary.error, projectUid) : null;

  return (
    <section data-home-sections="" data-home-scope={projectUid === null ? 'all' : 'project'}>
      <h2>Разделы объекта</h2>
      {summary.isPending ? <LoadingState what="разделы объекта" /> : null}
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
      {failure?.kind === 'project_not_found' ? (
        // An object the server does not know is its own state, with the way out the detail above names; never a table of zeros.
        <p className={styles.way}>
          <Link className="am-button am-button--quiet" href={allProjectsHref}>
            Все объекты
          </Link>
        </p>
      ) : null}
      {summary.isSuccess ? <SectionsPanel rows={summary.data.section_breakdown} projectUid={projectUid} /> : null}
    </section>
  );
}
